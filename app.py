from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import database
import os
from datetime import datetime

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
        return str(resp), 200, {'Content-Type': 'application/xml'}
    
    # 5. Route by Role
    role = tenant['role'] if 'role' in tenant.keys() else 'TENANT'
    
    if role == 'MANAGER':
        handle_manager(resp, incoming_msg, conn, sender_phone, raw_from) # Pass raw_from for bot number
    else:
        handle_tenant(resp, tenant, incoming_msg, num_media, conn)

    conn.close()
    
    # Ensure correct content type for Twilio
    return str(resp), 200, {'Content-Type': 'application/xml'}

# --- Tenant Logic ---

tenant_state = {}

def handle_tenant(resp, tenant, msg, num_media, conn):
    name = tenant['name']
    apt = tenant['apartment_number']
    rent_amt = tenant['rent_amount']
    # Ensure we get the correct phone column or pass it in
    sender_phone = tenant['phone_number'] 
    msg_lower = msg.lower()

    # --- STATE MACHINE for Payment ---
    state = tenant_state.get(sender_phone)
    
    if state:
        step = state.get('step')
        data = state.get('data', {})
        
        if step == 'payment_method':
            if msg_lower == 'upi' or msg_lower == 'cash':
                data['method'] = msg_lower.upper()
                state['step'] = 'amount'
                # Update state in dict
                tenant_state[sender_phone] = state
                
                resp.message(f"💰 You selected **{data['method']}**.\n\nPlease enter the **Amount Paid** (e.g., {rent_amt}):")
                return
            elif msg_lower in ['cancel', 'stop', 'exit']:
                del tenant_state[sender_phone]
                resp.message("❌ Payment cancelled.")
                return
            else:
                resp.message("❌ Invalid option. Please reply with **UPI** or **Cash** (or 'cancel').")
                return

        elif step == 'amount':
            try:
                amount = float(msg)
                
                # Insert Transaction
                # Use standard SQL. For SQLite 'date' is string usually, but we can pass object.
                # Just use ISO format for safety.
                now_str = datetime.now().isoformat()
                
                database.execute_query(conn,
                    "INSERT INTO transactions (tenant_id, amount, type, status, date) VALUES (?, ?, ?, 'PENDING', ?)",
                    (tenant['id'], amount, data['method'], now_str)
                )
                conn.commit()
                
                resp.message(f"✅ **Payment Recorded!**\nReceived ₹{amount} via {data['method']}.\nWaiting for manager verification.")
                
                # Clear state
                del tenant_state[sender_phone]
                return
            except ValueError:
                resp.message("❌ Invalid amount. Please enter a number (e.g., 15000).")
                return

    # 1. Image Upload
    if num_media > 0:
        resp.message(f"📸 Thanks {name}! I've received your payment screenshot. Pending manager approval.")
        return

    # 2. Interactive Logic
    # Start payment flow
    if (msg_lower == 'pay rent' or msg == '1') and not state:
        # Start State Machine
        tenant_state[sender_phone] = {'step': 'payment_method', 'data': {}}
        body = f"💰 **Rent Due:** ₹{rent_amt}\n\nSelect a payment method:"
        resp.message(body)
        resp.message("Reply *UPI* or *Cash*")
        return

    elif msg_lower == 'upload screenshot' or msg == '2':
        resp.message("📸 Please tap the 📎 icon to attach your payment screenshot.")

    elif msg_lower == 'report issue' or msg == '3':
        resp.message("🔧 **Report Issue:**\nPlease reply with a description of the problem (e.g., 'Leaking tap') and attach a photo.")

    elif msg_lower == 'wifi password' or msg == '4':
        resp.message(f"📶 **WiFi Details:**\nNetwork: `{WIFI_SSID}`\nPassword: `{WIFI_PASS}`")

    elif msg_lower == 'my history' or msg == '5':
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
        # 1. Get all active tenants
        cur = database.execute_query(conn, "SELECT id, name, apartment_number, rent_amount FROM tenants WHERE role='TENANT'")
        all_tenants = cur.fetchall()
        total_tenants = len(all_tenants)
        
        # 2. Get verified payments for current month
        # Using SQLite/Postgres compatible date check (simple string match for YYYY-MM)
        current_month = datetime.now().strftime('%Y-%m')
        
        # Note: In SQLite date is string. In Postgres it's timestamp.
        # This query works best if date column is TEXT (ISO8601).
        # If TIMESTAMP type, we need extraction function.
        # For cross-compatibility in MVP, we fetch relevant txs and filter in Python.
        
        cur = database.execute_query(conn, "SELECT tenant_id, amount FROM transactions WHERE status='VERIFIED'")
        all_txs = cur.fetchall()
        
        paid_tenants = set()
        total_collected = 0.0
        
        for tx in all_txs:
            # tx['date'] might be datetime object or string depending on driver
            # Let's assume we filter all for now or check date if available in row
            # Fetch date too
            pass 

        # Let's do a cleaner query for current month
        # Since we have `database.execute_query`, let's try a standard SQL approach
        # casting date to text to match YYYY-MM
        
        # Simplified logic:
        # Get IDs of tenants who paid > 0 this month
        paid_ids = set()
        
        # We need to act differently for SQLite vs Postgres for date functions
        # Hack: Just fetch all verified transactions and filter in Python (safe for <1000 records)
        cur = database.execute_query(conn, "SELECT tenant_id, amount, date FROM transactions WHERE status='VERIFIED'")
        txs = cur.fetchall()
        
        for tx in txs:
            # Handle date string vs datetime object
            d = tx['date']
            if isinstance(d, str):
                d_str = d[:7] # YYYY-MM
            else:
                d_str = d.strftime('%Y-%m')
            
            if d_str == current_month:
                paid_ids.add(tx['tenant_id'])
                total_collected += tx['amount']

        # 3. Calculate Lists
        pending_list = []
        for t in all_tenants:
            if t['id'] not in paid_ids:
                pending_list.append(f"🔴 {t['apartment_number']} - {t['name']} (₹{t['rent_amount']})")

        paid_count = len(paid_ids)
        pending_count = total_tenants - paid_count
        
        # 4. Format Output
        report = f"📊 **{datetime.now().strftime('%B')} Rent Report**\n\n"
        report += f"✅ **Paid:** {paid_count}/{total_tenants} (₹{total_collected:,.0f})\n"
        report += f"❌ **Pending:** {pending_count} Units\n\n"
        
        if pending_list:
            report += "**Defaulters List:**\n"
            report += "\n".join(pending_list[:10]) # Show top 10 to avoid limit
            if len(pending_list) > 10:
                report += f"\n...and {len(pending_list)-10} more."
        else:
            report += "🎉 All rents collected!"

        resp.message(report)

    elif msg_lower == 'add tenant' or msg_lower == 'add':
        # Start State Machine
        manager_state[sender_phone] = {'step': 'name', 'data': {}}
        resp.message("➕ **New Tenant Setup**\n\nFirst, what is the Tenant's **Name**?")

    else:
        # MANAGER MENU
        menu = "👋 **Manager Mode**\n"
        menu += "Select an action:\n\n"
        menu += "1. Pending Approvals\n"
        menu += "2. System Status (Rent Roll)\n"
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
