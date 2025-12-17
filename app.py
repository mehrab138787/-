import requests
import json
from flask import Flask, request, jsonify, url_for, render_template_string
from urllib.parse import quote, urlencode

app = Flask(__name__)

# ===================================================================
# 🔑 تنظیمات واقعی و تایید شده (مختص دامنه 6rgalxwl9g)
# ===================================================================
BASE_URL = "https://api.bazaar-pay.ir/badje/v1"
AUTH_TOKEN = "01f16b92299ad730cb405e22ebf9a9f14b11b970"
DESTINATION_NAME = "kodular_bazaar"
YOUR_DOMAIN = "https://6rgalxwl9g.onrender.com"
# ===================================================================

@app.route('/')
def index():
    """صفحه تست ساده با دکمه پرداخت"""
    return render_template_string('''
        <div style="text-align:center; margin-top:100px; font-family:tahoma; direction:rtl;">
            <h2>تست درگاه واقعی بازارپی</h2>
            <p>مبلغ تست: ۵,۰۰۰ تومان</p>
            <button onclick="startPay()" style="padding:15px 30px; font-size:20px; cursor:pointer; background:#2ecc71; color:white; border:none; border-radius:10px;">
                پرداخت و تست نهایی
            </button>
        </div>
        <script>
            function startPay() {
                fetch('/api/v1/start_checkout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({amount: 50000, phone: '09120000000'})
                })
                .then(res => res.json())
                .then(data => {
                    if(data.redirect_url) window.location.href = data.redirect_url;
                    else alert('خطا در شروع پرداخت: ' + (data.message || 'unknown error'));
                })
                .catch(err => alert('خطا در ارتباط با سرور'));
            }
        </script>
    ''')

@app.route('/api/v1/start_checkout', methods=['POST'])
def start_checkout():
    try:
        data = request.json
        amount_rial = data.get('amount', 50000) # ۵۰,۰۰۰ ریال = ۵ هزار تومان
        user_phone = data.get('phone', '09120000000')
        
        callback_url = f"{YOUR_DOMAIN}/bazaarpay/callback"

        payload = {
            "amount": amount_rial,
            "service_name": "تست سرویس مهران",
            "destination": DESTINATION_NAME, 
            "callback_url": callback_url
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/checkout/init/", headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        response_data = response.json()
        payment_url_base = response_data.get('payment_url') 
        
        query_params = {"phone": user_phone, "redirect_url": callback_url}
        encoded_params = urlencode(query_params, quote_via=quote)
        
        return jsonify({
            "status": "success",
            "redirect_url": f"{payment_url_base}&{encoded_params}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/bazaarpay/callback', methods=['GET', 'POST'])
def bazaarpay_callback():
    checkout_token = request.args.get('token') or request.form.get('token')
    if not checkout_token:
        return "توکن پرداخت یافت نشد", 400

    try:
        # ۱. استعلام وضعیت (Trace)
        trace_response = requests.post(f"{BASE_URL}/trace/", 
                                       headers={"Content-Type": "application/json"}, 
                                       data=json.dumps({"checkout_token": checkout_token}))
        trace_data = trace_response.json()
        trace_status = trace_data.get('status')
        
        if trace_status == 'paid_not_committed':
            # ۲. تایید نهایی (Commit)
            commit_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {AUTH_TOKEN}" 
            }
            commit_res = requests.post(f"{BASE_URL}/commit/", 
                                       headers=commit_headers, 
                                       data=json.dumps({"checkout_token": checkout_token}))
            
            if commit_res.status_code == 204:
                return "<h1 style='color:green; text-align:center; font-family:tahoma;'>✅ پرداخت موفقیت‌آمیز بود!</h1>"
        
        return f"<h1 style='text-align:center; font-family:tahoma;'>وضعیت پرداخت: {trace_status}</h1>"
    except Exception as e:
        return f"<h1>خطای سیستم: {str(e)}</h1>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)