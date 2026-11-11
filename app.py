from flask import Flask, render_template_string, request, jsonify, session
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Master State Storage
gateway_state = {
    "admin_user": "",
    "admin_pass": "",
    "gmail_user": "",
    "gmail_pass": "",
    "upi_id": "",
    "api_key": "",
    "is_installed": False,
    "is_setup_done": False,
    "total_revenue": 0.0,
    "transactions": []
}

# Unified Glassmorphism CSS & Styles
GLOBAL_CSS = """
:root {
    --bg-primary: #f8fafc;
    --glass-bg: rgba(255, 255, 255, 0.85);
    --glass-border: rgba(255, 255, 255, 0.9);
    --primary-blue: #0284c7;
    --primary-blue-hover: #0369a1;
    --text-main: #0f172a;
    --text-sub: #475569;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Segoe UI', sans-serif; }
body { background: var(--bg-primary); min-height: 100vh; display: flex; justify-content: center; align-items: center; position: relative; overflow-x: hidden; color: var(--text-main); padding: 20px; }
.background-glow { position: absolute; width: 500px; height: 500px; background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%); filter: blur(100px); border-radius: 50%; z-index: 0; opacity: 0.3; }
.glass-container { position: relative; z-index: 1; background: var(--glass-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 28px; padding: 35px; width: 100%; max-width: 460px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08); transition: max-width 0.3s ease; }
.wide-container { max-width: 860px; }
.dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
@media(max-width: 768px) { .dashboard-grid { grid-template-columns: 1fr; } .wide-container { max-width: 460px; } }
.gateway-header { text-align: center; margin-bottom: 25px; }
.logo-icon { font-size: 28px; color: var(--primary-blue); background: rgba(2, 132, 199, 0.08); width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; border-radius: 50%; margin: 0 auto 12px auto; }
.gateway-header h1 { font-size: 22px; font-weight: 700; }
.gateway-header p { font-size: 13px; color: var(--text-sub); margin-top: 2px; }
.panel-top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.btn-text { background: none; border: none; color: #ef4444; font-size: 13px; cursor: pointer; font-weight: 600; }
.panel h2 { font-size: 16px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px; }
.subtitle { font-size: 13px; color: var(--text-sub); margin-bottom: 20px; }
.input-group { margin-bottom: 16px; text-align: left; }
.input-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.input-group label i { color: var(--primary-blue); margin-right: 4px; }
.input-group input { width: 100%; padding: 12px 16px; border: 1px solid #cbd5e1; background: rgba(255, 255, 255, 0.95); border-radius: 12px; font-size: 14px; outline: none; transition: all 0.3s ease; }
.input-group input:focus { border-color: var(--primary-blue); box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15); }
.input-group small { display: block; font-size: 11px; color: var(--text-sub); margin-top: 4px; }
.btn-primary { width: 100%; background: var(--primary-blue); color: #ffffff; border: none; padding: 14px; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 10px; }
.btn-primary:hover { background: var(--primary-blue-hover); }
.btn-secondary { background: #e2e8f0; border: none; color: #334155; padding: 10px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }
.payment-box { background: rgba(255, 255, 255, 0.5); border: 1px solid rgba(255, 255, 255, 0.9); border-radius: 16px; padding: 20px; }
.api-key-box { display: flex; gap: 8px; }
.stats-card { background: rgba(255, 255, 255, 0.7); border: 1px solid rgba(255, 255, 255, 0.9); border-radius: 14px; padding: 16px; margin-bottom: 15px; text-align: center; }
.stats-card span { font-size: 11px; color: var(--text-sub); text-transform: uppercase; font-weight: 700; }
.stats-card h3 { font-size: 26px; color: var(--primary-blue); margin-top: 4px; }
.logs-title { font-size: 14px; margin-bottom: 10px; color: var(--text-main); text-align: left; }
.table-container { max-height: 160px; overflow-y: auto; background: rgba(255, 255, 255, 0.6); border-radius: 10px; border: 1px solid #e2e8f0; }
table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
th, td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; }
th { background: rgba(2, 132, 199, 0.05); font-weight: 600; color: var(--text-sub); }
.badge-success { background: rgba(16, 185, 129, 0.15); color: #059669; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.no-tx { font-size: 12px; color: var(--text-sub); text-align: center; padding: 20px; }
.message { margin-top: 15px; font-size: 13px; text-align: center; font-weight: 600; }
"""

@app.route('/')
def index():
    if not gateway_state["is_installed"]:
        return render_template_string(AUTH_PAGE_TEMPLATE, mode="register")
    if not session.get("logged_in"):
        return render_template_string(AUTH_PAGE_TEMPLATE, mode="login")
    if not gateway_state["is_setup_done"]:
        return render_template_string(AUTH_PAGE_TEMPLATE, mode="gateway")
    
    # Render host URL dynamic detection for API endpoint display
    host_url = request.host_url.rstrip('/')
    endpoint_url = f"{host_url}/api/v1/verify-payment"
    
    return render_template_string(
        DASHBOARD_TEMPLATE, 
        upi_id=gateway_state["upi_id"],
        total_revenue=gateway_state["total_revenue"],
        transactions=gateway_state["transactions"],
        api_key=gateway_state["api_key"],
        endpoint_url=endpoint_url
    )

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    data = request.json
    if not data.get('username') or not data.get('password'):
        return jsonify({"status": "error", "message": "Username and password required."})
    gateway_state["admin_user"] = data.get('username')
    gateway_state["admin_pass"] = data.get('password')
    gateway_state["is_installed"] = True
    session["logged_in"] = True
    return jsonify({"status": "success", "message": "Admin account created successfully!"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == gateway_state["admin_user"] and data.get('password') == gateway_state["admin_pass"]:
        session["logged_in"] = True
        return jsonify({"status": "success", "message": "Login successful!"})
    return jsonify({"status": "error", "message": "Invalid username or password."})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop("logged_in", None)
    return jsonify({"status": "success", "message": "Logged out successfully."})

@app.route('/api/setup-gateway', methods=['POST'])
def setup_gateway():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized."})
    data = request.json
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(data.get('gmail_user'), data.get('gmail_pass'))
        mail.logout()
        
        gateway_state["gmail_user"] = data.get('gmail_user')
        gateway_state["gmail_pass"] = data.get('gmail_pass')
        gateway_state["upi_id"] = data.get('upi_id')
        gateway_state["is_setup_done"] = True
        
        if not gateway_state["api_key"]:
            gateway_state["api_key"] = "fp_live_" + os.urandom(12).hex()
            
        return jsonify({"status": "success", "message": "Gateway configured successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gmail auth failed: {str(e)}"})

@app.route('/api/generate-key', methods=['POST'])
def generate_key():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized."})
    gateway_state["api_key"] = "fp_live_" + os.urandom(12).hex()
    return jsonify({"status": "success", "api_key": gateway_state["api_key"]})

# ==========================================
# EXTERNAL MERCHANT API ENDPOINT (Public)
# ==========================================
@app.route('/api/v1/verify-payment', methods=['POST'])
def external_verify_payment():
    data = request.json or {}
    incoming_api_key = data.get('api_key')
    expected_amount = float(data.get('amount', 0))
    
    if not incoming_api_key or incoming_api_key != gateway_state["api_key"]:
        return jsonify({"status": "rejected", "message": "Invalid or missing API key."}), 401
        
    if not gateway_state["is_setup_done"]:
        return jsonify({"status": "rejected", "message": "Gateway not configured."}), 400
        
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
                "status": "Approved", 
                "time": timestamp,
                "details": matched_details
            }
            gateway_state["transactions"].insert(0, tx_record)
            return jsonify({"status": "approved", "message": "Payment verified successfully.", "tx_id": tx_id, "amount": expected_amount})
        else:
            return jsonify({"status": "pending", "message": "Payment not found yet."})
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server verification error: {str(e)}"})

# HTML Templates Embedded Directly in Python File
AUTH_PAGE_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Gateway Authentication</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>{GLOBAL_CSS}</style>
</head>
<body>
    <div class="background-glow"></div>
    <div class="glass-container">
        <header class="gateway-header">
            <div class="logo-icon"><i class="fa-solid fa-shield-halved"></i></div>
            <h1>Private Access Portal</h1>
            <p>Secure Gateway Protection</p>
        </header>

        {% if mode == "register" %}
        <div class="panel">
            <h2><i class="fa-solid fa-user-shield"></i> Create Admin Account</h2>
            <p class="subtitle">Set up private credentials to secure your payment gateway.</p>
            <form onsubmit="handleAuth(event, '/api/register-admin')">
                <div class="input-group">
                    <label><i class="fa-solid fa-user"></i> Admin Username</label>
                    <input type="text" id="username" required placeholder="Choose username">
                </div>
                <div class="input-group">
                    <label><i class="fa-solid fa-key"></i> Admin Password</label>
                    <input type="password" id="password" required placeholder="Choose password">
                </div>
                <button type="submit" class="btn-primary">Create Secure Account <i class="fa-solid fa-arrow-right"></i></button>
            </form>
            <div id="auth-msg" class="message"></div>
        </div>
        {% elif mode == "login" %}
        <div class="panel">
            <h2><i class="fa-solid fa-lock"></i> Admin Login</h2>
            <p class="subtitle">Enter your private credentials to access the dashboard.</p>
            <form onsubmit="handleAuth(event, '/api/login')">
                <div class="input-group">
                    <label><i class="fa-solid fa-user"></i> Username</label>
                    <input type="text" id="username" required placeholder="Username">
                </div>
                <div class="input-group">
                    <label><i class="fa-solid fa-key"></i> Password</label>
                    <input type="password" id="password" required placeholder="Password">
                </div>
                <button type="submit" class="btn-primary">Login Securely <i class="fa-solid fa-right-to-bracket"></i></button>
            </form>
            <div id="auth-msg" class="message"></div>
        </div>
        {% elif mode == "gateway" %}
        <div class="panel">
            <h2><i class="fa-solid fa-sliders"></i> Gateway Setup</h2>
            <p class="subtitle">Link your Gmail App Password and FamPay UPI ID.</p>
            <form onsubmit="handleGateway(event)">
                <div class="input-group">
                    <label><i class="fa-solid fa-envelope"></i> Gmail Address</label>
                    <input type="email" id="gmail_user" required placeholder="merchant@gmail.com">
                </div>
                <div class="input-group">
                    <label><i class="fa-solid fa-lock"></i> Google App Password</label>
                    <input type="password" id="gmail_pass" required placeholder="16-character app password">
                </div>
                <div class="input-group">
                    <label><i class="fa-solid fa-wallet"></i> Receiver UPI ID</label>
                    <input type="text" id="upi_id" required placeholder="username@fampay">
                </div>
                <button type="submit" class="btn-primary">Activate Gateway <i class="fa-solid fa-bolt"></i></button>
            </form>
            <div id="auth-msg" class="message"></div>
        </div>
        {% endif %}
    </div>
    <script>
        async function handleAuth(e, endpoint) {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            btn.disabled = true;
            btn.innerHTML = 'Processing...';
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: document.getElementById('username').value, password: document.getElementById('password').value })
            });
            const result = await res.json();
            const msg = document.getElementById('auth-msg');
            if(result.status === 'success') {
                msg.style.color = '#10b981'; msg.textContent = result.message;
                setTimeout(() => location.reload(), 1000);
            } else {
                msg.style.color = '#ef4444'; msg.textContent = result.message;
                btn.disabled = false; btn.innerHTML = 'Try Again';
            }
        }
        async function handleGateway(e) {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            btn.disabled = true;
            btn.innerHTML = 'Configuring...';
            const res = await fetch('/api/setup-gateway', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gmail_user: document.getElementById('gmail_user').value,
                    gmail_pass: document.getElementById('gmail_pass').value,
                    upi_id: document.getElementById('upi_id').value
                })
            });
            const result = await res.json();
            const msg = document.getElementById('auth-msg');
            if(result.status === 'success') {
                msg.style.color = '#10b981'; msg.textContent = result.message;
                setTimeout(() => location.reload(), 1000);
            } else {
                msg.style.color = '#ef4444'; msg.textContent = result.message;
                btn.disabled = false; btn.innerHTML = 'Activate Gateway';
            }
        }
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FamPay Enterprise Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>{GLOBAL_CSS}</style>
</head>
<body>
    <div class="background-glow"></div>
    <div class="glass-container wide-container">
        <header class="gateway-header">
            <div class="logo-icon"><i class="fa-solid fa-chart-line"></i></div>
            <h1>FamPay Enterprise</h1>
            <p>Merchant API & Verification Gateway</p>
        </header>

        <div class="dashboard-grid">
            <div class="panel">
                <div class="panel-top-bar">
                    <h2><i class="fa-solid fa-code"></i> Developer API Settings</h2>
                    <button onclick="logoutAdmin()" class="btn-text" title="Logout"><i class="fa-solid fa-right-from-bracket"></i> Logout</button>
                </div>
                
                <div class="payment-box">
                    <div class="input-group">
                        <label>Your API Endpoint URL</label>
                        <input type="text" readonly value="{{ endpoint_url }}">
                    </div>
                    <div class="input-group">
                        <label>Your Secret API Key</label>
                        <div class="api-key-box">
                            <input type="text" readonly value="{{ api_key }}" id="api-key-val">
                            <button onclick="generateNewKey()" class="btn-secondary">New Key</button>
                        </div>
                    </div>
                    <small>Use this endpoint and API key in your external web applications for automatic payment verification.</small>
                </div>
            </div>

            <div class="panel analytics-panel">
                <h2><i class="fa-solid fa-wallet"></i> Live Revenue Stats</h2>
                <div class="stats-card">
                    <span>Total Collected Balance</span>
                    <h3>₹ {{ total_revenue }}</h3>
                </div>

                <h3 class="logs-title"><i class="fa-solid fa-clock-rotate-left"></i> Verified Transactions</h3>
                <div class="table-container">
                    {% if transactions %}
                    <table>
                        <thead>
                            <tr>
                                <th>Tx ID</th>
                                <th>Amount</th>
                                <th>Status</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for tx in transactions %}
                            <tr>
                                <td><code>{{ tx.tx_id }}</code></td>
                                <td>₹{{ tx.amount }}</td>
                                <td><span class="badge-success">{{ tx.status }}</span></td>
                                <td><small>{{ tx.time }}</small></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <p class="no-tx">No verified transactions yet.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <script>
        async function generateNewKey() {
            const res = await fetch('/api/generate-key', { method: 'POST' });
            const result = await res.json();
            if(result.status === 'success') {
                document.getElementById('api-key-val').value = result.api_key;
            }
        }
        async function logoutAdmin() {
            await fetch('/api/logout', { method: 'POST' });
            location.reload();
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
