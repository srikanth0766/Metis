import hashlib
import hmac

from app.services import webhook_service


def test_webhook_signature_verification(monkeypatch):
    monkeypatch.setattr(webhook_service.settings, "RAZORPAY_WEBHOOK_SECRET", "test-secret")
    payload = b'{"event":"payment.captured"}'
    signature = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
    assert webhook_service.verify_webhook_signature(payload, signature)
    assert not webhook_service.verify_webhook_signature(payload, "invalid")
