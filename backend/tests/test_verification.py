import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.verifier import Verifier


@pytest.mark.asyncio
async def test_verification_success():
    source_data = {
        "invoice_id": "INV-1024",
        "company": "Acme",
        "amount": "₹48,500",
        "due_date": "2026-10-15"
    }

    dummy_browser_mgr = MagicMock()
    dummy_browser_mgr.get_page = AsyncMock()
    dummy_browser_mgr.capture_screenshot = AsyncMock(return_value=("/tmp/shot.png", "desc"))

    ledger_record = {
        "record_id": "BILL-7842",
        "invoice_id": "INV-1024",
        "company": "Acme",
        "amount": "₹48,500",
        "due_date": "2026-10-15"
    }

    with patch("app.agent.verifier.BillingTools.search_billing_record", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"found": True, "record": ledger_record}

        result, shot = await Verifier.verify_record(dummy_browser_mgr, source_data)

        assert result["verified"] is True
        assert result["record_id"] == "BILL-7842"
        assert result["amount_matches"] is True
        assert result["company_matches"] is True
        assert result["due_date_matches"] is True


@pytest.mark.asyncio
async def test_verification_mismatch_amount():
    source_data = {
        "invoice_id": "INV-1024",
        "company": "Acme",
        "amount": "₹48,500",
        "due_date": "2026-10-15"
    }

    dummy_browser_mgr = MagicMock()
    dummy_browser_mgr.get_page = AsyncMock()
    dummy_browser_mgr.capture_screenshot = AsyncMock(return_value=("/tmp/shot.png", "desc"))

    # Tampered amount in ledger
    ledger_record = {
        "record_id": "BILL-7842",
        "invoice_id": "INV-1024",
        "company": "Acme",
        "amount": "₹99,999",
        "due_date": "2026-10-15"
    }

    with patch("app.agent.verifier.BillingTools.search_billing_record", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"found": True, "record": ledger_record}

        result, shot = await Verifier.verify_record(dummy_browser_mgr, source_data)

        assert result["verified"] is False
        assert result["amount_matches"] is False
        assert result["company_matches"] is True


@pytest.mark.asyncio
async def test_verification_not_found():
    source_data = {
        "invoice_id": "INV-9999",
        "company": "Acme",
        "amount": "₹10,000",
        "due_date": "2026-10-15"
    }

    dummy_browser_mgr = MagicMock()
    dummy_browser_mgr.get_page = AsyncMock()
    dummy_browser_mgr.capture_screenshot = AsyncMock(return_value=("/tmp/shot.png", "desc"))

    with patch("app.agent.verifier.BillingTools.search_billing_record", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"found": False, "record": None}

        result, shot = await Verifier.verify_record(dummy_browser_mgr, source_data)

        assert result["verified"] is False
        assert result["record_id"] is None
