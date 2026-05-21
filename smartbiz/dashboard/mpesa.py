import base64
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


class MpesaError(Exception):
    pass


def get_mpesa_base_url():
    env = getattr(settings, "MPESA_ENV", "sandbox").lower()
    if env == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def normalize_phone_number(phone_number):
    digits = "".join(char for char in str(phone_number or "") if char.isdigit())
    if not digits:
        raise MpesaError("Phone number is required for M-Pesa payments.")
    if digits.startswith("0"):
        digits = f"254{digits[1:]}"
    elif digits.startswith("7") and len(digits) == 9:
        digits = f"254{digits}"
    elif digits.startswith("1") and len(digits) == 9:
        digits = f"254{digits}"
    elif digits.startswith("254"):
        pass
    else:
        raise MpesaError("Phone number must be in 07XXXXXXXX or 2547XXXXXXXX format.")

    if len(digits) != 12:
        raise MpesaError("Phone number must resolve to a valid 12-digit Kenyan number.")
    return digits


def generate_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def generate_password(shortcode, passkey, timestamp):
    raw_value = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw_value.encode("utf-8")).decode("utf-8")


def _make_request(url, method="GET", headers=None, payload=None):
    request = Request(url, data=payload, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise MpesaError(f"M-Pesa request failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise MpesaError(f"Could not reach M-Pesa API: {exc.reason}") from exc


def get_access_token():
    consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
    consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
    if not consumer_key or not consumer_secret:
        raise MpesaError("M-Pesa credentials are missing. Set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET.")

    credentials = f"{consumer_key}:{consumer_secret}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("utf-8")
    url = f"{get_mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
    }
    response = _make_request(url, headers=headers)
    token = response.get("access_token")
    if not token:
        raise MpesaError("M-Pesa access token was not returned.")
    return token


def initiate_stk_push(*, phone_number, amount, account_reference, transaction_desc, callback_url):
    shortcode = getattr(settings, "MPESA_SHORTCODE", "174379")
    passkey = getattr(settings, "MPESA_PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
    transaction_type = getattr(settings, "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline")

    if not shortcode or not passkey:
        raise MpesaError("M-Pesa shortcode or passkey is missing. Set MPESA_SHORTCODE and MPESA_PASSKEY.")

    timestamp = generate_timestamp()
    token = get_access_token()
    normalized_phone = normalize_phone_number(phone_number)
    sanitized_amount = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    payload = {
        "BusinessShortCode": shortcode,
        "Password": generate_password(shortcode, passkey, timestamp),
        "Timestamp": timestamp,
        "TransactionType": transaction_type,
        "Amount": int(sanitized_amount),
        "PartyA": normalized_phone,
        "PartyB": shortcode,
        "PhoneNumber": normalized_phone,
        "CallBackURL": "https://smartbiz-bfko.onrender.com/mpesa/callback/",
        "AccountReference": str(account_reference)[:12],
        "TransactionDesc": str(transaction_desc)[:50],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = _make_request(
        f"{get_mpesa_base_url()}/mpesa/stkpush/v1/processrequest",
        method="POST",
        headers=headers,
        payload=json.dumps(payload).encode("utf-8"),
    )
    response["normalized_phone_number"] = normalized_phone
    response["request_payload"] = payload
    return response


def extract_callback_metadata(callback_metadata):
    items = callback_metadata.get("Item", []) if isinstance(callback_metadata, dict) else []
    extracted = {}
    for item in items:
        name = item.get("Name")
        if name:
            extracted[name] = item.get("Value")
    return extracted


def parse_stk_callback(payload):
    stk_callback = payload.get("Body", {}).get("stkCallback", {})
    metadata = extract_callback_metadata(stk_callback.get("CallbackMetadata", {}))
    return {
        "merchant_request_id": stk_callback.get("MerchantRequestID"),
        "checkout_request_id": stk_callback.get("CheckoutRequestID"),
        "result_code": stk_callback.get("ResultCode"),
        "result_description": stk_callback.get("ResultDesc"),
        "metadata": metadata,
    }
