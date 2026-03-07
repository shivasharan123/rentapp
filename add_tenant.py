import sqlite3
import sys

def add_tenant(phone_number, name="New Tenant", apt="101", rent=10000):
    conn = sqlite3.connect('rent_app.db')
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT * FROM tenants WHERE phone_number = ?", (phone_number,))
    existing = c.fetchone()
    
    if existing:
        print(f"User {phone_number} already exists with role: {existing[6]}")
        # Update role to TENANT if needed
        if existing[6] != 'TENANT':
            c.execute("UPDATE tenants SET role = 'TENANT' WHERE phone_number = ?", (phone_number,))
            conn.commit()
            print(f"Updated role to TENANT for {phone_number}")
    else:
        c.execute("INSERT INTO tenants (phone_number, name, apartment_number, rent_amount, role) VALUES (?, ?, ?, ?, 'TENANT')",
                  (phone_number, name, apt, rent))
        conn.commit()
        print(f"Added new tenant: {name} ({phone_number}) in Apt {apt}")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        add_tenant(sys.argv[1])
    else:
        print("Usage: python3 add_tenant.py <PHONE_NUMBER>")
