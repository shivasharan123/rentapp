from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import database

app = Flask(__name__)

def get_sender_phone(raw_from):
    """Extract phone number from Twilio 'whatsapp:+123...' format."""
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
    
    # Use helper to handle ? vs %s and conn.cursor() differences
    cur = database.execute_query(
        conn, 
        "SELECT * FROM tenants WHERE phone_number = ?", 
        (sender_phone,)
    )
    tenant = cur.fetchone()
    conn.close()

    # 3. Start Response
    resp = MessagingResponse()

    # 4. Logic Branching
    if not tenant:
        # Unknown User
        resp.message(f"🚫 Sorry, I don't recognize the number {sender_phone}. Please contact the Property Manager to register.")
        return str(resp)
    
    # Known Tenant
    tenant_name = tenant['name']
    apt_num = tenant['apartment_number']

    if num_media > 0:
        # Image Received (Assume Payment Screenshot)
        # TODO: Add AI Analysis here later
        resp.message(f"📸 Thanks {tenant_name} (Apt {apt_num})! I've received your screenshot. I'll verify the payment shortly.")
    
    elif 'rent' in incoming_msg or 'balance' in incoming_msg:
        # Check Balance
        rent_amt = tenant['rent_amount']
        # For now, just show the base rent. Later: calculate outstanding balance.
        resp.message(f"💰 Hi {tenant_name}. Your monthly rent for Apt {apt_num} is ₹{rent_amt}. Please upload a payment screenshot to clear dues.")
        
    elif 'help' in incoming_msg:
        resp.message(f"👋 Hi {tenant_name}!\n\nI can help with:\n1. 💰 Type 'rent' to check dues.\n2. 📸 Send a screenshot to pay.\n3. 🔧 Type 'maintenance' to report an issue.")

    else:
        # Default Greeting
        resp.message(f"👋 Hello {tenant_name} from Apt {apt_num}! How can I help you today? (Type 'help' for options)")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
