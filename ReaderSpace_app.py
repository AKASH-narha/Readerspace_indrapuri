import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd

# Optional: Twilio SMS
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

FILENAME = "library_users.json"
MONTHLY_FEE = 500  # 💰 Monthly Fee

# ---------- Helpers ----------
def load_data():
    if os.path.exists(FILENAME):
        with open(FILENAME, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(FILENAME, "w") as f:
        json.dump(data, f, indent=4)

def send_sms(contact, message):
    """Send SMS via Twilio if available, otherwise skip safely"""
    if not TWILIO_AVAILABLE:
        return
    try:
        account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
        auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
        twilio_number = st.secrets["TWILIO_PHONE_NUMBER"]

        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=twilio_number,
            to=contact
        )
    except Exception as e:
        st.error(f"❌ SMS sending failed: {e}")

def generate_report(data):
    """Generate Pandas DataFrame for export"""
    rows = []
    for code, user in data.items():
        for pay in user["payments"]:
            rows.append({
                "Library Code": code,
                "Name": user["name"],
                "Father's Name": user["father_name"],
                "Address": user["address"],
                "Contact": user["contact"],
                "Admission Date": user["admission_date"],
                "Payment Date": pay["date"],
                "Amount Paid": pay["amount"]
            })
    return pd.DataFrame(rows)

# ---------- Main App ----------
st.title("📚 ReaderSpace Library Management System")
data = load_data()

menu = ["New User Registration", "Existing User Login", "Check Pending Payments", "Record Payment", "Download Reports"]
choice = st.sidebar.selectbox("Menu", menu)

# --- New User ---
if choice == "New User Registration":
    st.subheader("🆕 Register New User")
    name = st.text_input("Full Name")
    father_name = st.text_input("Father's Name")
    address = st.text_area("Address")
    email = st.text_input("Email")
    contact = st.text_input("Contact Number (with +91)")
    seatno = st.text_input("Seat Number")
    admission_date = datetime.now().strftime("%Y-%m-%d")

    if st.button("Register"):
        if not name or not father_name or not contact:
            st.error("⚠ Name, Father's Name, and Contact are required!")
        else:
            library_code = "L" + str(len(data) + 2025001)
            data[library_code] = {
                "name": name,
                "father_name": father_name,
                "address": address,
                "email": email,
                "contact": contact,
                "seatno": seatno,
                "admission_date": admission_date,
                "last_payment": admission_date,
                "payments": [{"date": admission_date, "amount": MONTHLY_FEE}]
            }
            save_data(data)
            st.success(f"✅ User registered! Library Code: {library_code}")

            msg = f"Welcome {name}! Your Library Code is {library_code}. Admission Date: {admission_date}. First payment of ₹{MONTHLY_FEE} recorded."
            send_sms(contact, msg)

# --- Existing User ---
elif choice == "Existing User Login":
    st.subheader("🔑 Login")
    library_code = st.text_input("Enter Library Code")
    if st.button("Login"):
        if library_code in data:
            st.json(data[library_code])
        else:
            st.error("❌ Invalid Library Code")

# --- Check Pending Payments ---
elif choice == "Check Pending Payments":
    st.subheader("💰 Pending Payments")
    today = datetime.now()
    for code, user in data.items():
        last_payment = datetime.strptime(user["last_payment"], "%Y-%m-%d")
        months_due = (today.year - last_payment.year) * 12 + (today.month - last_payment.month)

        if months_due > 0:
            due_amount = months_due * MONTHLY_FEE
            st.warning(f"{user['name']} (Code: {code}) owes ₹{due_amount} ({months_due} months)")
            msg = f"Dear {user['name']}, you have {months_due} month(s) due. Total = ₹{due_amount}. Please pay soon."
            send_sms(user["contact"], msg)
        else:
            st.info(f"{user['name']} (Code: {code}) is up to date ✅")

# --- Record Payment ---
elif choice == "Record Payment":
    st.subheader("💵 Record Payment")
    library_code = st.text_input("Enter Library Code")
    if st.button("Fetch User"):
        if library_code in data:
            user = data[library_code]
            st.write(f"👤 {user['name']} ({library_code})")

            last_payment = datetime.strptime(user["last_payment"], "%Y-%m-%d")
            months_due = (datetime.now().year - last_payment.year) * 12 + (datetime.now().month - last_payment.month)
            st.write(f"📅 Months Due: {months_due}")

            months_paid = st.number_input("Months Paying For", min_value=1, value=1)
            total_amount = months_paid * MONTHLY_FEE
            st.write(f"💰 Payment Amount: ₹{total_amount}")

            if st.button("Confirm Payment"):
                new_payment_date = datetime.now().strftime("%Y-%m-%d")
                user["last_payment"] = new_payment_date
                user["payments"].append({"date": new_payment_date, "amount": total_amount})
                save_data(data)
                st.success(f"✅ Payment of ₹{total_amount} recorded.")

                msg = f"Payment received: ₹{total_amount}. Thank you {user['name']}! Next due will be next month."
                send_sms(user["contact"], msg)
        else:
            st.error("❌ Invalid Library Code")

# --- Download Reports ---
elif choice == "Download Reports":
    st.subheader("📊 Download Reports")
    df = generate_report(data)

    if not df.empty:
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download CSV Report", csv, "library_report.csv", "text/csv")

        excel = df.to_excel("library_report.xlsx", index=False)
        with open("library_report.xlsx", "rb") as f:
            st.download_button("⬇ Download Excel Report", f, "library_report.xlsx")
    else:
        st.info("ℹ No data available yet.")
