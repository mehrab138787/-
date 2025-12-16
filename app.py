import requests
import json
import os
from flask import Flask, request, jsonify, redirect, url_for
from urllib.parse import quote, urlencode

app = Flask(__name__)

# ===================================================================
# 🔑 پیکربندی محیط تست بازارپی
# ===================================================================
BASE_URL = "https://api.bazaar-pay.ir/badje/v1" 
# TEST_TOKEN: از نمونه cURL در payment.md استخراج شد
TEST_TOKEN = "some_auth_token"  
# TEST_DESTINATION_NAME: مقدار فرضی - اگر خطا داد باید از پشتیبانی بخواهید
TEST_DESTINATION_NAME = "test_merchant_name" 

# آدرس عمومی (Public URL) سرور شما که باید توسط Ngrok تنظیم شود
# اگر متغیر محیطی تنظیم نشود، به صورت پیش‌فرض روی لوکال می‌ماند اما تست پرداخت کار نخواهد کرد.
YOUR_DOMAIN = os.environ.get("FLASK_PUBLIC_URL", "http://127.0.0.1:5000")
# ===================================================================

# **************** مسیرهای start_checkout و bazaarpay_callback ****************
# **************** (کدهای این دو مسیر همان کدهای پاسخ قبلی هستند) **************

@app.route('/api/v1/start_checkout', methods=['POST'])
def start_checkout():
    """شروع فرآیند پرداخت و دریافت URL هدایت"""
    # ... (کد start_checkout دقیقا مشابه پاسخ قبلی است) ...
    # (برای سادگی نمایش اینجا حذف شده است، اما شما کل کد قبلی را قرار دهید)
    try:
        data = request.json
        amount_rial = data.get('amount', 10000)
        user_phone = data.get('phone', '09123456789')
        
        callback_url_path = url_for('bazaarpay_callback')
        callback_url = f"{YOUR_DOMAIN}{callback_url_path}" 

        payload = {
            "checkout_type": "checkout_server_to_server",
            "amount": amount_rial,
            "description": "شارژ حساب کاربری Cyrus",
            "destination_name": TEST_DESTINATION_NAME,
            "callback_url": callback_url
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {TEST_TOKEN}" 
        }

        response = requests.post(f"{BASE_URL}/init/", headers=headers, data=json.dumps(payload))
        response.raise_for_status() 

        response_data = response.json()
        checkout_token = response_data.get('checkout_token')
        payment_url_base = response_data.get('payment_url')

        final_payment_url = f"{payment_url_base}?token={checkout_token}&phone={user_phone}&redirect_url={quote(callback_url)}"
        
        return jsonify({
            "status": "success",
            "checkout_token": checkout_token,
            "redirect_url": final_payment_url
        })

    except requests.exceptions.HTTPError as e:
        error_message = f"خطای API بازارپی: {e}. (بررسی کنید که TEST_TOKEN و TEST_DESTINATION_NAME صحیح باشند)."
        details = response.text if 'response' in locals() else "No response received."
        return jsonify({"status": "error", "message": error_message, "details": details}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/bazaarpay/callback', methods=['GET', 'POST'])
def bazaarpay_callback():
    """بررسی وضعیت پرداخت (Trace) و نهایی کردن تراکنش (Commit)"""
    # ... (کد bazaarpay_callback دقیقا مشابه پاسخ قبلی است) ...
    # (برای سادگی نمایش اینجا حذف شده است، اما شما کل کد قبلی را قرار دهید)
    checkout_token = request.args.get('token') or request.form.get('token')
        
    if not checkout_token:
        return "<html><body><h1>خطا: توکن پرداخت پیدا نشد.</h1></body></html>", 400

    trace_url = f"{BASE_URL}/trace/"
    trace_payload = {"checkout_token": checkout_token}
    
    try:
        trace_response = requests.post(trace_url, headers={"Content-Type": "application/json"}, data=json.dumps(trace_payload))
        trace_response.raise_for_status()
        trace_status = trace_response.json().get('status')
        
        if trace_status == 'paid_not_committed':
            commit_url = f"{BASE_URL}/commit/"
            commit_payload = {"checkout_token": checkout_token}
            commit_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {TEST_TOKEN}"
            }
            
            commit_response = requests.post(commit_url, headers=commit_headers, data=json.dumps(commit_payload))
            
            if commit_response.status_code == 204: 
                final_status = "success"
                message = "تراکنش با موفقیت انجام و تأیید شد."
            else:
                final_status = "error"
                message = f"پرداخت موفق، اما خطا در تأیید نهایی (Commit). کد: {commit_response.status_code}"

        elif trace_status == 'unpaid':
            final_status = "pending"
            message = "پرداخت هنوز نهایی نشده است. (ممکن است تا ۱۵ دقیقه طول بکشد)."
        else:
            final_status = "failed"
            message = f"پرداخت ناموفق. وضعیت: {trace_status}"

    except requests.exceptions.RequestException as e:
        final_status = "error"
        message = f"خطا در ارتباط با سرور بازارپی: {e}"
        
    return f"""
    <html>
        <head><title>نتیجه پرداخت</title></head>
        <body>
            <div dir="rtl" style="text-align: center; font-family: Tahoma, sans-serif;">
                <h1>نتیجه پرداخت ({'موفق' if final_status == 'success' else 'ناموفق'})</h1>
                <p>وضعیت نهایی: <b>{final_status}</b></p>
                <p>پیام: {message}</p>
                <p>توکن: {checkout_token}</p>
                <hr>
                <p>این صفحه جهت نمایش نتیجه سمت سرور شما است. برنامه Cyrus باید این وضعیت را مدیریت کند.</p>
            </div>
        </body>
    </html>
    """


if __name__ == '__main__':
    # این آدرس در ترمینال پرینت می‌شود.
    print(f"Server is running. Public URL must be set to: {YOUR_DOMAIN}")
    print(f"Test POST endpoint: {YOUR_DOMAIN}/api/v1/start_checkout")
    app.run(host='0.0.0.0', port=5000, debug=True)