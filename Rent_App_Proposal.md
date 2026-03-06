# 🏢 Smart Rent & Maintenance Tracker
## Automated WhatsApp-Based Property Management System

---

### 1. Executive Summary
**Goal:** Streamline rent collection and maintenance tracking for a 60-unit rental portfolio.
**Solution:** A "No-App" experience for tenants using **WhatsApp** as the primary interface, powered by an **AI Backend** to automate bookkeeping and reconciliation.
**Key Benefit:** Eliminates manual data entry, centralizes records, and provides a real-time financial snapshot.

---

### 2. Core Workflows

#### A. Rent Collection (The "Happy Path")
*   **Tenant Action:** Sends a UPI/Bank Transfer screenshot to the Building WhatsApp Number.
*   **System Action:**
    1.  **AI Analysis:** Extracts `Amount`, `Date`, `Transaction ID (UTR)`, and `Sender Name` from the image.
    2.  **Validation:** Checks against the tenant's due amount.
    3.  **Ledger Update:** Records the payment in the database.
*   **Outcome:** Tenant receives an instant "Payment Received" receipt. Manager dashboard updates automatically.

#### B. Cash Payments (The "Handshake")
*   **Scenario:** Tenant pays cash to the manager.
*   **Manager Action:** Messages the bot: *"Collected 15k cash from Apt 101."*
*   **Verification:** Bot messages the **Tenant** to confirm: *"Manager reported collecting ₹15,000. Confirm? [Yes/No]"*
*   **Outcome:** Ledger updates only after Tenant confirmation, preventing disputes.

#### C. Maintenance Requests
*   **Tenant Action:** Sends a photo/text: *"Leaking tap in bathroom."*
*   **System Action:**
    1.  AI categorizes it as a **Maintenance Ticket**.
    2.  Assigns a Priority (Low/High).
    3.  Notifies the Manager with a summary.
*   **Outcome:** Organized list of open issues instead of scattered chat history.

---

### 3. Fraud Prevention (The "Guard Rails")
**Goal:** Zero financial loss from fake screenshots or duplicate uploads.

#### Layer 1: The "Unique ID" Lock (Automated)
Every UPI transaction has a 12-digit **UTR Number** (e.g., `3284759201`).
*   **How it works:** The AI extracts this number from every screenshot.
*   **The Guard Rail:** The database stores every UTR ever seen. If a tenant tries to upload the same screenshot again (even if cropped or edited), the system rejects it immediately: *"Duplicate Transaction ID detected."*

#### Layer 2: The "Pending" Buffer (Trust but Verify)
We never mark a payment as **"Settled"** instantly based on a screenshot.
*   **Status:** When a tenant uploads a screenshot, the status in your database becomes `VERIFICATION_PENDING`.
*   **Bot Reply:** *"Received your screenshot for ₹15,000. Verification in progress."*
*   **Why:** This acknowledges the tenant's action without legally confirming you have the money in the bank.

#### Layer 3: The "Bank SMS" Matcher (The Gold Standard)
The only way to be 100% sure is to check your actual bank account.
*   **Mechanism:** You install a tiny "SMS Forwarder" app on your phone.
*   **The Match:** When you get a bank SMS (*"Acct XX1234 Credited ₹15,000"*), the system matches it to the Tenant's screenshot (Amount + Time).
*   **Result:** Only when the **SMS matches the Screenshot** does the status flip to `PAID`.

---

### 4. Technical Architecture
The "Stack" required to build and run this system.

*   **User Interface:** **WhatsApp Business API** (via Twilio or Meta Direct).
*   **The "Brain" (Logic):** **Python / Node.js** backend running on the cloud.
*   **Intelligence (AI):** **OpenAI GPT-4o** or **Google Gemini** (for reading screenshots & understanding text).
*   **The "Ledger" (Database):** **Supabase (PostgreSQL)**. Secure, relational database for financial records.
*   **Hosting:** **Railway** or **Render** (keeps the bot running 24/7).

---

### 5. Data Structure (The Schema)
A glimpse into how data is organized.

*   **Tenants Table:** `Name`, `Phone`, `Apartment ID`, `Rent Amount`, `Current Balance`.
*   **Transactions Table:** `Date`, `Amount`, `Type (UPI/Cash)`, `UTR Number`, `Screenshot Evidence`, `Status (Pending/Verified)`.
*   **Maintenance Table:** `Ticket ID`, `Issue Description`, `Photo URL`, `Status (Open/Fixed)`, `Cost`.

---

### 6. Manager Dashboard (How You Manage)
You don't need to read raw database rows.
*   **Option A (Simple):** **Daily WhatsApp Summary** (*"Today: collected ₹1.5L from 12 tenants. 3 pending maintenance requests."*)
*   **Option B (Visual):** A web-based **Admin Panel** (using Supabase or Streamlit) to view:
    *   🔴 Tenants who haven't paid yet.
    *   🟢 Total Revenue this month.
    *   🔧 Open Maintenance Tickets.

---

### 7. Next Steps
1.  **Setup:** Acquire **Twilio** (WhatsApp) and **OpenAI/Gemini** (AI) API keys.
2.  **Build:** Deploy the Database Schema and Python Backend.
3.  **Test:** Run a pilot with 1-2 friendly tenants.
4.  **Launch:** Onboard all 60 units.
