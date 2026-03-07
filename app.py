from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import database
import os

# Set a secret key for session management
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Configuration ---
WIFI_SSID = "Building_Guest"
WIFI_PASS = "WelcomeHome2024"

# Twilio Client (For outbound reminders)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
    except:
        print("Warning: Twilio Client init failed")

def get_sender_phone(raw_from):
    if raw_from.startswith("whatsapp:"):
        return raw_from.split(":")[1]
    return raw_from

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    """Respond to incoming WhatsApp messages."""
    
    # 1. Get request details
    raw_from = request.values.get('From', '')
    sender_phone = get_sender_phone(raw_from)
    incoming_msg = request.values.get('Body', '').strip() # Keep case for names
    incoming_msg_lower = incoming_msg.lower()
    num_media = int(request.values.get('NumMedia', '0'))
    
    # 2. Database Lookup
    conn = database.get_db_connection()
    cur = database.execute_query(
        conn, 
        "SELECT * FROM tenants WHERE phone_number = ?", 
        (sender_phone,)
    )
    tenant = cur.fetchone()

    # 3. Start Response
    resp = MessagingResponse()

    # 4. Unknown User Logic
    if not tenant:
        conn.close()
        resp.message(f"🚫 Sorry, I don't recognize the number {sender_phone}. Please contact the Property Manager.")
        return str(resp)
    
    # 5. Route by Role
    role = tenant['role'] if 'role' in tenant.keys() else 'TENANT'
    
    if role == 'MANAGER':
        handle_manager(resp, incoming_msg, conn, sender_phone, raw_from) # Pass raw_from for bot number
    else:
        handle_tenant(resp, tenant, incoming_msg, num_media, conn)

    conn.close()
    return str(resp)

# --- Tenant Logic ---

def handle_tenant(resp, tenant, msg, num_media, conn):
    name = tenant['name']
    apt = tenant['apartment_number']
    rent_amt = tenant['rent_amount']
    msg_lower = msg.lower()

    # 1. Image Upload
    if num_media > 0:
        resp.message(f"📸 Thanks {name}! I've received your payment screenshot. Pending manager approval.")
        return

    # 2. Interactive Logic
    if msg_lower == 'pay rent':
        body = f"💰 **Rent Due:** ₹{rent_amt}\n\nSelect a payment method:"
        # Sending text for now as true buttons need templates in prod
        resp.message(body)
        resp.message("Reply *UPI* or *Cash*")
        return

    elif msg_lower == 'wifi password':
        resp.message(f"📶 **WiFi Details:**\nNetwork: `{WIFI_SSID}`\nPassword: `{WIFI_PASS}`")

    elif msg_lower == 'report issue':
        resp.message("🔧 **Report Issue:**\nPlease reply with a description of the problem (e.g., 'Leaking tap') and attach a photo.")

    elif msg_lower == 'my history':
         # Show last 3 payments
        cur = database.execute_query(conn, "SELECT * FROM transactions WHERE tenant_id = ? ORDER BY date DESC LIMIT 3", (tenant['id'],))
        txs = cur.fetchall()
        if not txs:
            resp.message("No payment history found.")
        else:
            history = "📜 **Recent Payments:**\n"
            for tx in txs:
                status_icon = "✅" if tx['status'] == 'VERIFIED' else "⏳"
                history += f"{status_icon} {tx['date'][:10]}: ₹{tx['amount']} ({tx['type']})\n"
            resp.message(history)

    else:
        # MAIN MENU (Tenant)
        menu = f"👋 **Welcome Home, {name}!**\n"
        menu += "Tap an option below (or type it):\n\n"
        menu += "1. Pay Rent\n"
        menu += "2. Upload Screenshot\n"
        menu += "3. Report Issue\n"
        menu += "4. WiFi Password\n"
        menu += "5. My History"
        
        resp.message(menu)

# --- Manager Logic (Conversational) ---

manager_state = {} 

def handle_manager(resp, msg, conn, sender_phone, bot_whatsapp_id):
    state = manager_state.get(sender_phone)
    msg_lower = msg.lower()

    # --- STATE MACHINE for Add Tenant ---
    if state:
        step = state['step']
        data = state['data']

        if step == 'name':
            data['name'] = msg
            state['step'] = 'phone'
            resp.message("📱 Enter Tenant's **Phone Number** (e.g., +91...):")
            return
        
        elif step == 'phone':
            data['phone'] = msg
            state['step'] = 'apt'
            resp.message("🏠 Enter **Apartment Number**:")
            return

        elif step == 'apt':
            data['apt'] = msg
            state['step'] = 'rent'
            resp.message("💰 Enter **Monthly Rent** (Amount only):")
            return

        elif step == 'rent':
            try:
                rent = float(msg)
                # Save to DB
                database.execute_query(conn,
                    "INSERT INTO tenants (name, phone_number, apartment_number, rent_amount, role) VALUES (?, ?, ?, ?, 'TENANT')",
                    (data['name'], data['phone'], data['apt'], rent)
                )
                conn.commit()
                resp.message(f"✅ **Success!**\nAdded {data['name']} (Apt {data['apt']}) with rent ₹{rent}.")
            except ValueError:
                resp.message("❌ Invalid amount. Please enter a number (e.g., 15000).")
                return # Keep state, retry
            except Exception as e:
                resp.message(f"❌ Error: {str(e)}")
            
            # Clear state
            del manager_state[sender_phone]
            return

    # --- REMINDER LOGIC ---
    if msg_lower.startswith('remind '):
        try:
            target_apt = msg.split('remind ')[1].strip()
            
            # Find tenant
            cur = database.execute_query(conn, "SELECT * FROM tenants WHERE apartment_number = ?", (target_apt,))
            target = cur.fetchone()
            
            if not target:
                resp.message(f"❌ No tenant found in Apt {target_apt}")
                return
            
            # Send Outbound Message
            if twilio_client:
                reminder_body = f"👋 **Friendly Reminder:**\nHi {target['name']}! Rent for this month is due (₹{target['rent_amount']}).\nPlease pay via UPI or Cash soon to avoid late fees."
                
                # 'From' must be the Twilio Sandbox/Production number (extracted from incoming request 'To' usually, but here hardcoded/env var is better)
                # We'll use the 'To' from the incoming request as the 'From' for the outbound message.
                bot_number = request.values.get('To') 
                
                twilio_client.messages.create(
                    from_=bot_number,
                    body=reminder_body,
                    to=f"whatsapp:{target['phone_number']}"
                )
                resp.message(f"✅ Reminder sent to {target['name']} ({target['phone_number']}).")
            else:
                resp.message("❌ Twilio Client not configured. Check env vars.")

        except Exception as e:
            resp.message(f"❌ Error sending reminder: {str(e)}")
        return

    # --- STANDARD COMMANDS ---

    if msg_lower == 'pending approvals' or msg_lower == 'pending':
        cur = database.execute_query(conn, 
            """SELECT t.id, t.amount, t.type, ten.name 
               FROM transactions t 
               JOIN tenants ten ON t.tenant_id = ten.id 
               WHERE t.status = 'PENDING'"""
        )
        txs = cur.fetchall()
        
        if not txs:
            resp.message("✅ No pending payments.")
        else:
            reply = "📋 **Pending Approvals:**\n"
            for tx in txs:
                reply += f"- ID {tx['id']}: ₹{tx['amount']} from {tx['name']}\n"
            reply += "\nType `approve [ID]` to verify."
            resp.message(reply)

    elif msg.startswith('approve '):
        try:
            tx_id = int(msg.split()[1])
            database.execute_query(conn, "UPDATE transactions SET status = 'VERIFIED' WHERE id = ?", (tx_id,))
            conn.commit()
            resp.message(f"✅ Transaction #{tx_id} approved.")
        except:
            resp.message("❌ Usage: `approve [ID]`")

    elif msg_lower == 'system status' or msg_lower == 'status':
        cur = database.execute_query(conn, "SELECT COUNT(*) as count FROM tenants WHERE role='TENANT'")
        count = cur.fetchone()['count']
        resp.message(f"📊 **System Status:**\nActive Tenants: {count}")

    elif msg_lower == 'add tenant' or msg_lower == 'add':
        # Start State Machine
        manager_state[sender_phone] = {'step': 'name', 'data': {}}
        resp.message("➕ **New Tenant Setup**\n\nFirst, what is the Tenant's **Name**?")

    else:
        # MANAGER MENU
        menu = "👋 **Manager Mode**\n"
        menu += "Select an action:\n\n"
        menu += "1. Pending Approvals\n"
        menu += "2. System Status\n"
        menu += "3. Add Tenant\n" 
        menu += "4. Send Reminder (Type `remind [Apt]`)"
        
        # Hint logic to match keywords if they type "1"
        if msg == '1': handle_manager(resp, 'pending', conn, sender_phone, bot_whatsapp_id)
        elif msg == '2': handle_manager(resp, 'status', conn, sender_phone, bot_whatsapp_id)
        elif msg == '3': handle_manager(resp, 'add tenant', conn, sender_phone, bot_whatsapp_id)
        else:
            resp.message(menu)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
