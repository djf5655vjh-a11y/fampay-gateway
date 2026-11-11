from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24).hex() # Secure random session key

# Enterprise State Management
gateway_state = {
    "admin_user": "",
    "admin_pass": "",
    "gmail_user": "",
    "gmail_pass": "",
    "upi_id": "",
    "is_installed": False,     # Admin account created or not
    "is_setup_done": False,    # Gmail & UPI configured or not
    "total_revenue": 0.0,
    "transactions": []
}

@app.route('/')
def index():
    # Agar admin setup nahi hua, toh pehle registration/setup page dikhayein
    if not gateway_state["is_installed"]:
        return render_template('setup_auth.html', step="register")
    
    # Agar logged in nahi hai, toh login page dikhayein
    if not session.get("logged_in"):
        return render_template('setup_auth.html', step="login")
    
    # Agar gateway setup nahi hua, toh gateway configuration page dikhayein
    if not gateway_state["is_setup_done"]:
        return render_template('setup_auth.html', step="gateway_config")
    
    # Main Dashboard
    return render_template(
        'index.html', 
        upi_id=gateway_state["upi_id"],
        total_revenue=gateway_state["total_revenue"],
        transactions=gateway_state["transactions"]
    )

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required."})
        
    gateway_state["admin_user"] = username
    gateway_state["admin_pass"] = password
    gateway_state["is_installed"] = True
    session["logged_in"] = True
    
    return jsonify({"status": "success", "message": "Admin account created successfully!"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == gateway_state["admin_user"] and password == gateway_state["admin_pass"]:
        session["logged_in"] = True
        return jsonify({"status": "success", "message": "Login successful!"})
    else:
        return jsonify({"status": "error", "message": "Invalid username or password."})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop("logged_in", None)
    return jsonify({"status": "success", "message": "Logged out successfully."})

@app.route('/api/setup-gateway', methods=['POST'])
def setup_gateway():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized access."})
        
    data = request.json
    gmail_user = data.get('gmail_user')
    gmail_pass = data.get('gmail_pass')
    upi_id = data.get('upi_id')
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_pass)
        mail.logout()
        
        gateway_state["gmail_user"] = gmail_user
        gateway_state["gmail_pass"] = gmail_pass
        gateway_state["upi_id"] = upi_id
        gateway_state["is_setup_done"] = True
        
        return jsonify({"status": "success", "message": "Gateway configured successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gmail authentication failed: {str(e)}"})

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    if not session.get("logged_in") or not gateway_state["is_setup_done"]:
        return jsonify({"status": "error", "message": "Unauthorized or gateway not configured."})
    
    data = request.json
    expected_amount = float(data.get('amount', 0))
    tx_id = 'FP_TXN_' + os.urandom(3).hex().upper()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gateway_state["gmail_user"], gateway_state["gmail_pass"])
        mail.select("inbox")
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            status, messages = mail.search(None, 'ALL')
            
        latest_emails = messages[0].split()[-10:]
        
        payment_verified = False
        matched_details = ""

        for email_id in reversed(latest_emails):
            res, msg_data = mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                        
                    if str(expected_amount) in body or gateway_state["upi_id"].lower() in body.lower():
                        payment_verified = True
                        matched_details = f"Alert: {subject}"
                        break
            if payment_verified:
                break
                
        mail.logout()
        
        if payment_verified:
            gateway_state["total_revenue"] += expected_amount
            timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
            tx_record = {
                "tx_id": tx_id, 
                "amount": expected_amount, 
                "status": "Success", 
                "time": timestamp,
                "details": matched_details
            }
            gateway_state["transactions"].insert(0, tx_record)
            return jsonify({"status": "verified", "message": "Payment verified successfully!", "tx": tx_record})
        else:
            return jsonify({"status": "pending", "message": "Waiting for payment notification..."})
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Verification error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
