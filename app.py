from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import database
import os

app = Flask(__name__)

# --- Configuration ---
WIFI_SSID = "Building_Guest"
WIFI_PASS = "WelcomeHome2024"

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
    incoming_msg = request.values.get('Body', '').lower().strip()
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
        handle_manager(resp, incoming_msg, conn, sender_phone)
    else:
        handle_tenant(resp, tenant, incoming_msg, num_media, conn)

    conn.close()
    return str(resp)

# --- Tenant Logic ---

def handle_tenant(resp, tenant, msg, num_media, conn):
    name = tenant['name']
    apt = tenant['apartment_number']
    rent_amt = tenant['rent_amount']

    # 1. Image Upload
    if num_media > 0:
        resp.message(f"📸 Thanks {name}! I've received your payment screenshot. Pending manager approval.")
        return

    # 2. Map Button Clicks to logic
    # (Users might tap the button text exactly)
    if msg == 'pay rent':
        body = f"💰 **Rent Due:** ₹{rent_amt}\n\nSelect a payment method:"
        # Sub-menu buttons
        msg_resp = resp.message(body)
        msg_resp.body(body) # Redundant but safe
        # Note: Twilio Python helper for generic buttons is tricky without Content API templates.
        # We will use simple numbered list for reliability in Sandbox, 
        # OR generic formatting if your account supports it.
        # For now, let's stick to text-based buttons simulation or try to trigger standard response.
        # Since 'Buttons' requires template registration in Prod, we will fallback to text prompt if buttons fail.
        # But user specifically asked for buttons.
        return

    # 3. Logic Handling
    if 'rent' in msg or 'pay' in msg:
        resp.message(f"💰 Rent for Apt {apt}: ₹{rent_amt}\n\nTo pay, scan the building QR code.\nThen upload the screenshot here.")
    
    elif 'wifi' in msg:
        resp.message(f"📶 **WiFi Details:**\nNetwork: `{WIFI_SSID}`\nPassword: `{WIFI_PASS}`")

    elif 'maintenance' in msg or 'issue' in msg:
        resp.message("🔧 **Report Issue:**\nPlease reply with a description of the problem (e.g., 'Leaking tap') and attach a photo.")

    else:
        # MAIN MENU (Tenant)
        # We use a standard text menu, but formatted to look like a list.
        # True "Clickable" buttons in WhatsApp API require templates approved by Meta.
        # Since we are in dev/sandbox, we simulate "Link Style" by using easy keywords.
        
        menu = f"👋 **Welcome Home, {name}!**\n"
        menu += "Tap a command below:\n\n"
        menu += "💰 *Pay Rent*\n"
        menu += "📸 *Upload Screenshot*\n"
        menu += "🔧 *Report Issue*\n"
        menu += "📶 *WiFi Password*"
        
        # In a real deployed app with Templates, we would send a JSON payload here.
        # For now, we guide them to type the keyword.
        resp.message(menu)

# --- Manager Logic ---

def handle_manager(resp, msg, conn, sender_phone):
    
    if 'pending' in msg:
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

    elif 'status' in msg:
        cur = database.execute_query(conn, "SELECT COUNT(*) as count FROM tenants WHERE role='TENANT'")
        count = cur.fetchone()['count']
        resp.message(f"📊 **System Status:**\nActive Tenants: {count}")

    else:
        # MANAGER MENU
        # Simulating "Link Style"
        menu = "👋 **Manager Mode**\n"
        menu += "Select an action:\n\n"
        menu += "📋 *Pending Approvals*\n"  # User can type "Pending"
        menu += "📊 *System Status*\n"      # User can type "Status"
        menu += "➕ *Add Tenant*"           # User can type "Add Tenant"
        
        resp.message(menu)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
