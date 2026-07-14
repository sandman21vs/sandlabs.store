"""Tests for services/service_coupons.py (server-side discount logic)."""

from datetime import date, timedelta

import pytest


def _mk(tmp_db, **kwargs):
    from models.model_coupons import create_coupon, get_coupon
    defaults = dict(code="SAVE", discount_type="percent", discount_value=10)
    defaults.update(kwargs)
    create_coupon(**defaults)
    return get_coupon(defaults["code"])


class TestComputeDiscount:
    def test_percent(self, tmp_db):
        from services.service_coupons import compute_discount_sats
        coupon = _mk(tmp_db, code="P10", discount_type="percent", discount_value=10)
        assert compute_discount_sats(coupon, 10000) == 1000

    def test_percent_floors(self, tmp_db):
        from services.service_coupons import compute_discount_sats
        coupon = _mk(tmp_db, code="P33", discount_type="percent", discount_value=33)
        assert compute_discount_sats(coupon, 100) == 33

    def test_fixed_clamped_to_subtotal(self, tmp_db):
        from services.service_coupons import compute_discount_sats
        coupon = _mk(tmp_db, code="F", discount_type="fixed_sats", discount_value=9999)
        assert compute_discount_sats(coupon, 5000) == 5000

    def test_zero_subtotal(self, tmp_db):
        from services.service_coupons import compute_discount_sats
        coupon = _mk(tmp_db, code="Z", discount_type="percent", discount_value=50)
        assert compute_discount_sats(coupon, 0) == 0


class TestEvaluateCoupon:
    def test_valid_percent(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        _mk(tmp_db, code="WELCOME", discount_type="percent", discount_value=20)
        coupon, discount, error = evaluate_coupon("welcome", 10000)
        assert error is None
        assert coupon["code"] == "WELCOME"
        assert discount == 2000

    def test_empty_code_is_not_an_error(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        coupon, discount, error = evaluate_coupon("", 10000)
        assert (coupon, discount, error) == (None, 0, None)

    def test_unknown_code_invalid(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        _, discount, error = evaluate_coupon("NOPE", 10000)
        assert error == "invalid" and discount == 0

    def test_inactive(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        _mk(tmp_db, code="OFF", discount_value=10, active=False)
        _, _, error = evaluate_coupon("OFF", 10000)
        assert error == "inactive"

    def test_expired(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        _mk(tmp_db, code="OLD", discount_value=10, expires_at=yesterday)
        _, _, error = evaluate_coupon("OLD", 10000)
        assert error == "expired"

    def test_not_expired_on_expiry_day(self, tmp_db):
        from services.service_coupons import evaluate_coupon
        today = date.today().isoformat()
        _mk(tmp_db, code="TODAY", discount_value=10, expires_at=today)
        coupon, discount, error = evaluate_coupon("TODAY", 10000)
        assert error is None and discount == 1000

    def test_exhausted(self, tmp_db):
        from models.model_coupons import increment_usage
        from services.service_coupons import evaluate_coupon
        _mk(tmp_db, code="LIMIT", discount_value=10, max_uses=1)
        increment_usage("LIMIT")
        _, _, error = evaluate_coupon("LIMIT", 10000)
        assert error == "exhausted"
