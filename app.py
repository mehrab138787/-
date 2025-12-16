import requests
import json
import os
from flask import Flask, request, jsonify, redirect, url_for
from urllib.parse import quote, urlencode

app = Flask(__name__)

# ===================================================================
# 🔑 پیکربندی محیط تست بازارپی (آدرس ثابت)
# ===================================================================
BASE_URL = "https://api.bazaar-pay.ir/badje/v1"
# توکن فرضی: فقط برای Commit/Refund استفاده می‌شود
TEST_TOKEN = "some_auth_token"
# Destination Name فرضی: برای Init استفاده می‌شود
TEST_DESTINATION_NAME = "developers"

# آدرس عمومی ثابت و صحیح Render شما
YOUR_DOMAIN = "https://6rgalxwl9g.onrender.com"
# ===================================================================

@app.route('/api/v1/start_checkout', methods=['POST'])
def start_checkout():
    """شروع فرآیند پرداخت و دریافت URL هدایت (Initiate Checkout)"""
    try:
        # 1. دریافت داده‌ها از درخواست POST کلاینت
        data = request.json
        amount_rial = data.get('amount', 10000)
        user_phone = data.get('phone', '09123456789')
        
        # 2. ساخت URL Callback
        callback_url_path = url_for('bazaarpay_callback')
        callback_url = f"{YOUR_DOMAIN}{callback_url_path}"

        # 3. ساخت Payload بر اساس مستندات بازارپی
        payload = {
            "amount": amount_rial,
            "service_name": "شارژ حساب کاربری Cyrus",
            "destination": TEST_DESTINATION_NAME, 
            "callback_url": callback_url
        }

        # 4. حذف هدر Authorization: Token برای init-checkout (مطابق مستندات)
        headers = {
            "Content-Type": "application/json",
            # Authorization در اینجا نیاز نیست
        }

        # 5. ارسال درخواست به API بازارپی (Init)
        response = requests.post(f"{BASE_URL}/checkout/init/", headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        response_data = response.json()
        checkout_token = response_data.get('checkout_token')
        payment_url_base = response_data.get('payment_url') # این لینک خودش شامل ?token=... است

        # 6. ساخت لینک نهایی پرداخت (اصلاح شده)
        # فقط پارامترهای اضافی (phone و redirect_url) را با & به لینک پایه اضافه می‌کنیم.
        
        query_params = {
            "phone": user_phone,
            "redirect_url": callback_url
        }
        
        encoded_params = urlencode(query_params, quote_via=quote)

        # ترکیب لینک پایه و پارامترهای اضافی (با & به جای ؟)
        final_payment_url = f"{payment_url_base}&{encoded_params}"
        
        return jsonify({
            "status": "success",
            "checkout_token": checkout_token,
            "redirect_url": final_payment_url
        })

    except requests.exceptions.HTTPError as e:
        error_message = f"خطای API بازارپی: {e}."
        details = response.text if 'response' in locals() else "No response received."
        return jsonify({"status": "error", "message": error_message, "details": details}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/bazaarpay/callback', methods=['GET', 'POST'])
def bazaarpay_callback():
    """بررسی وضعیت پرداخت (Trace) و نهایی کردن تراکنش (Commit)"""
    checkout_token = request.args.get('token') or request.form.get('token')
        
    if not checkout_token:
        return "<html><body><h1>خطا: توکن پرداخت پیدا نشد.</h1></body></html>", 400

    trace_url = f"{BASE_URL}/trace/"
    trace_payload = {"checkout_token": checkout_token}
    
    try:
        # 1. مرحله Trace: بررسی وضعیت توکن پرداخت (بدون نیاز به توکن احراز هویت)
        trace_response = requests.post(trace_url, headers={"Content-Type": "application/json"}, data=json.dumps(trace_payload))
        trace_response.raise_for_status()
        trace_status = trace_response.json().get('status')
        
        final_status = ""
        message = ""

        if trace_status == 'paid_not_committed':
            # 2. مرحله Commit: اگر پرداخت انجام شده ولی Commit نشده
            commit_url = f"{BASE_URL}/commit/"
            commit_payload = {"checkout_token": checkout_token}
            commit_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {TEST_TOKEN}" # ⬅️ توکن برای Commit نگه داشته شده
            }
            
            commit_response = requests.post(commit_url, headers=commit_headers, data=json.dumps(commit_payload))
            
            if commit_response.status_code == 204:
                final_status = "success"
                message = "تراکنش با موفقیت انجام و تأیید (Commit) شد."
            else:
                final_status = "error"
                message = f"پرداخت موفق، اما خطا در تأیید نهایی (Commit). کد: {commit_response.status_code}. پاسخ: {commit_response.text}"

        elif trace_status == 'unpaid':
            final_status = "pending"
            message = "پرداخت هنوز نهایی نشده است."
        else:
            final_status = "failed"
            message = f"پرداخت ناموفق. وضعیت: {trace_status}"

    except requests.exceptions.RequestException as e:
        final_status = "error"
        message = f"خطا در ارتباط با سرور بازارپی در مرحله Trace یا Commit: {e}"
        
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
                <p>این صفحه جهت نمایش نتیجه سمت سرور شما است.</p>
            </div>
        </body>
    </html>
    """


if __name__ == '__main__':
    print(f"Server is running. Public URL is fixed to: {YOUR_DOMAIN}")
    print(f"Test POST endpoint: {YOUR_DOMAIN}/api/v1/start_checkout")
    app.run(host='0.0.0.0', port=5000, debug=True)