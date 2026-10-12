"""Unit and Integration Test Suite for Banking FastMCP Server and Data Plane.

Validates:
1. Synthetic enterprise banking data integrity (Standard, VIP, Corporate Treasury).
2. Direct tool execution (get_account, lookup_customer_by_phone, transfer_to_phone, pay_bill, get_transaction_history).
3. Edge case error handling (insufficient funds, negative amounts, self transfers, limit breaches, invalid IDs).
4. FastMCP HTTP endpoints (/, /tools, /toolspec.json, /mcp Streamable HTTP protocol).

Can be executed directly via:
    uv run python agents/platform/agent-gateway/mcp_server/test_mcp.py
or through standard test runners:
    uv run pytest agents/platform/agent-gateway/mcp_server/test_mcp.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
from typing import Any, Dict

# Ensure agents/platform/agent-gateway is on sys.path
_PLATFORM_DIR = Path(__file__).resolve().parent.parent
if str(_PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_DIR))

from starlette.testclient import TestClient

from mcp_server import data, server
from mcp_server.data import (
    CustomerTier,
    check_balance,
    execute_bill_payment,
    execute_transfer,
    find_customer_by_phone,
    get_customer,
    list_customers,
    reset_database,
)
from mcp_server.server import (
    app,
    get_account,
    get_transaction_history,
    lookup_customer_by_phone,
    pay_bill,
    transfer_to_phone,
)


class TestSyntheticDataPlane(unittest.TestCase):
    """Test suite for data models, querying, balance checks, and state resets."""

    def setUp(self) -> None:
        reset_database()

    def test_customer_tiers_and_counts(self) -> None:
        """Verify 10 synthetic enterprise customers across all tiers."""
        customers = list_customers()
        self.assertEqual(len(customers), 10, "Expected exactly 10 customer accounts")

        # Tiers distribution
        standard = [c for c in customers if c["tier"] == CustomerTier.STANDARD.value]
        vip = [c for c in customers if c["tier"] == CustomerTier.PREMIUM_VIP.value]
        corporate = [c for c in customers if c["tier"] == CustomerTier.CORPORATE_TREASURY.value]

        self.assertEqual(len(standard), 4, "Expected 4 Standard tier accounts")
        self.assertEqual(len(vip), 4, "Expected 4 Premium/VIP tier accounts")
        self.assertEqual(len(corporate), 2, "Expected 2 Corporate Treasury tier accounts")

    def test_codelab_identities_presence(self) -> None:
        """Verify key identities required by the Google Cloud codelab are present."""
        c1 = get_customer("CUST001")
        self.assertIsNotNone(c1)
        self.assertEqual(c1["name"], "Alice Smith")
        self.assertEqual(c1["phone"], "555-0001")

        c2 = get_customer("CUST002")
        self.assertIsNotNone(c2)
        self.assertEqual(c2["name"], "Bob Jones")
        self.assertEqual(c2["phone"], "555-0002")

        c5 = get_customer("CUST005")
        self.assertIsNotNone(c5)
        self.assertIn("Eve Davis", c5.get("aliases", []))
        self.assertEqual(c5["phone"], "555-0005")
        self.assertEqual(c5["balance"], 28750.00)

        # Corporate account
        c9 = get_customer("CUST009")
        self.assertIsNotNone(c9)
        self.assertEqual(c9["name"], "Acme Corp Treasury")
        self.assertEqual(c9["balance"], 1450000.00)
        self.assertEqual(c9["daily_limit"], 500000.00)

    def test_phone_normalization_lookup(self) -> None:
        """Verify phone lookup handles standard and variant input strings."""
        cust = find_customer_by_phone("555-0002")
        self.assertIsNotNone(cust)
        self.assertEqual(cust["customer_id"], "CUST002")

        # Digits only
        cust_digits = find_customer_by_phone("5550002")
        self.assertIsNotNone(cust_digits)
        self.assertEqual(cust_digits["customer_id"], "CUST002")

        # Nonexistent
        self.assertIsNone(find_customer_by_phone("555-9999"))

    def test_check_balance_helper(self) -> None:
        """Verify check_balance helper function logic."""
        ok, msg, bal = check_balance("CUST001", 100.0)
        self.assertTrue(ok)
        self.assertEqual(bal, 4850.00)

        ok, msg, bal = check_balance("CUST001", 99999.0)
        self.assertFalse(ok)
        self.assertIn("Insufficient funds", msg)

        ok, msg, _ = check_balance("CUST999", 50.0)
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_database_reset(self) -> None:
        """Verify reset_database cleanly restores original state after mutations."""
        execute_transfer("CUST001", "555-0002", 500.0)
        c1_mutated = get_customer("CUST001")
        self.assertEqual(c1_mutated["balance"], 4350.00)

        reset_database()
        c1_restored = get_customer("CUST001")
        self.assertEqual(c1_restored["balance"], 4850.00)


class TestDirectToolExecution(unittest.TestCase):
    """Test suite for direct execution of banking MCP tools."""

    def setUp(self) -> None:
        reset_database()

    def test_get_account_valid(self) -> None:
        """Verify get_account returns accurate customer profile."""
        res = get_account(customer_id="CUST001")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["customer_id"], "CUST001")
        self.assertEqual(res["name"], "Alice Smith")
        self.assertEqual(res["balance"], 4850.00)
        self.assertEqual(res["daily_limit"], 2500.00)
        self.assertEqual(res["account_status"], "ACTIVE")

    def test_lookup_customer_by_phone_valid(self) -> None:
        """Verify lookup_customer_by_phone resolves account details."""
        res = lookup_customer_by_phone(phone="555-0002")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["customer_id"], "CUST002")
        self.assertEqual(res["name"], "Bob Jones")

    def test_transfer_to_phone_success(self) -> None:
        """Verify successful money transfer between accounts."""
        # Initial balances: CUST001 has 4850, CUST002 has 1250
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=50.0,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["amount"], 50.0)
        self.assertEqual(res["sender_id"], "CUST001")
        self.assertEqual(res["recipient_id"], "CUST002")
        self.assertEqual(res["new_balance"], 4800.00)

        # Check recipient balance updated
        recipient = get_customer("CUST002")
        self.assertEqual(recipient["balance"], 1300.00)

        # Check transaction history recorded for both
        history_sender = get_transaction_history(customer_id="CUST001")
        self.assertTrue(any(tx["amount"] == 50.0 for tx in history_sender["transactions"]))

        history_recipient = get_transaction_history(customer_id="CUST002")
        self.assertTrue(any(tx["amount"] == 50.0 for tx in history_recipient["transactions"]))

    def test_pay_bill_success(self) -> None:
        """Verify bill payment execution and confirmation code generation."""
        res = pay_bill(
            customer_id="CUST001",
            biller_name="Cloud Electric",
            account_number="ELEC-88219",
            amount=150.0,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["amount"], 150.0)
        self.assertEqual(res["new_balance"], 4700.00)
        self.assertTrue(res["confirmation_code"].startswith("AUTH-"))

        # Verify reflected in transaction history
        history = get_transaction_history(customer_id="CUST001")
        self.assertTrue(
            any("Cloud Electric" in tx.get("counterparty", "") for tx in history["transactions"])
        )


class TestEdgeCasesAndValidations(unittest.TestCase):
    """Test suite for edge cases, security guardrails, and validation errors."""

    def setUp(self) -> None:
        reset_database()

    def test_invalid_customer_id(self) -> None:
        """Verify proper error when customer ID does not exist."""
        res = get_account(customer_id="CUST999")
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "CUSTOMER_NOT_FOUND")

    def test_nonexistent_phone_lookup(self) -> None:
        """Verify error when querying an unmapped phone number."""
        res = lookup_customer_by_phone(phone="555-9999")
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "PHONE_NOT_FOUND")

    def test_transfer_negative_amount(self) -> None:
        """Verify negative transfer amounts are rejected."""
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=-25.0,
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "INVALID_AMOUNT")

    def test_transfer_zero_amount(self) -> None:
        """Verify zero transfer amounts are rejected."""
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=0.0,
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "INVALID_AMOUNT")

    def test_transfer_to_self(self) -> None:
        """Verify transferring to one's own phone is rejected."""
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0001",  # Alice's own phone
            amount=50.0,
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "INVALID_TRANSFER")

    def test_transfer_nonexistent_target_phone(self) -> None:
        """Verify transfer to an unregistered phone returns RECIPIENT_NOT_FOUND."""
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-9999",
            amount=50.0,
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "RECIPIENT_NOT_FOUND")

    def test_transfer_insufficient_funds(self) -> None:
        """Verify transfer exceeding customer account balance is blocked."""
        # CUST002 balance is 1250, daily limit is 2000
        res = transfer_to_phone(
            customer_id="CUST002",
            target_phone="555-0001",
            amount=1500.0,  # Below daily limit of 2000, but exceeds balance 1250
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "INSUFFICIENT_FUNDS")

    def test_transfer_exceeds_daily_limit(self) -> None:
        """Verify transfer exceeding customer's daily limit is blocked."""
        # CUST001 has balance 4850, but daily limit is 2500
        res = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=3000.0,  # Exceeds daily limit
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "EXCEEDS_DAILY_LIMIT")

    def test_cumulative_daily_limit_enforcement(self) -> None:
        """Verify cumulative transfers and bill payments are tracked against daily limit."""
        # CUST001 has balance 4850, daily limit 2500
        # 1. First transfer of 1500 should succeed
        res1 = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=1500.0,
        )
        self.assertEqual(res1["status"], "SUCCESS")

        # 2. Bill payment of 800 should succeed (cumulative = 2300 / 2500)
        res2 = pay_bill(
            customer_id="CUST001",
            biller_name="City Power",
            account_number="ACC-991",
            amount=800.0,
        )
        self.assertEqual(res2["status"], "SUCCESS")

        # 3. Transfer of 300 should fail because 2300 + 300 = 2600 > 2500
        res3 = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=300.0,
        )
        self.assertEqual(res3["status"], "ERROR")
        self.assertEqual(res3["error_code"], "EXCEEDS_DAILY_LIMIT")
        self.assertIn("exceeds available daily limit", res3["message"])

        # 4. Transfer of exactly remaining 200 should succeed
        res4 = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=200.0,
        )
        self.assertEqual(res4["status"], "SUCCESS")

        # 5. Even 1 dollar now fails
        res5 = transfer_to_phone(
            customer_id="CUST001",
            target_phone="555-0002",
            amount=1.0,
        )
        self.assertEqual(res5["status"], "ERROR")
        self.assertEqual(res5["error_code"], "EXCEEDS_DAILY_LIMIT")

    def test_pay_bill_invalid_inputs(self) -> None:
        """Verify validations on negative amounts, missing biller, or missing account."""
        res1 = pay_bill(
            customer_id="CUST001",
            biller_name="",
            account_number="123",
            amount=50.0,
        )
        self.assertEqual(res1["status"], "ERROR")
        self.assertEqual(res1["error_code"], "INVALID_BILLER")

        res2 = pay_bill(
            customer_id="CUST001",
            biller_name="Water Co",
            account_number="",
            amount=50.0,
        )
        self.assertEqual(res2["status"], "ERROR")
        self.assertEqual(res2["error_code"], "INVALID_INPUT")

        res3 = pay_bill(
            customer_id="CUST001",
            biller_name="Water Co",
            account_number="123",
            amount=-10.0,
        )
        self.assertEqual(res3["status"], "ERROR")
        self.assertEqual(res3["error_code"], "INVALID_AMOUNT")


class TestFastMCPHttpEndpoints(unittest.TestCase):
    """Integration test suite for FastMCP Starlette endpoints and Streamable HTTP protocol."""

    client: TestClient
    _client_cm: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = server.create_app()
        cls._client_cm = TestClient(cls._app)
        cls.client = cls._client_cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._client_cm.__exit__(None, None, None)

    def setUp(self) -> None:
        reset_database()

    def test_root_endpoint(self) -> None:
        """Verify GET / returns health status and endpoint map."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["service"], "banking-mcp-server")
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["tools_count"], 5)
        self.assertIn("/tools", data["endpoints"]["tools"])
        self.assertIn("/toolspec.json", data["endpoints"]["toolspec"])
        self.assertIn("/mcp", data["endpoints"]["mcp"])

    def test_tools_endpoint(self) -> None:
        """Verify GET /tools returns array of 5 tool specifications matching codelab expectation."""
        res = self.client.get("/tools")
        self.assertEqual(res.status_code, 200)
        tools = res.json()
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 5)

        tool_names = {t["name"] for t in tools}
        expected_tools = {
            "get_account",
            "lookup_customer_by_phone",
            "transfer_to_phone",
            "pay_bill",
            "get_transaction_history",
        }
        self.assertEqual(tool_names, expected_tools)

        # Check inputSchema presence for get_account
        get_account_spec = next(t for t in tools if t["name"] == "get_account")
        self.assertIn("inputSchema", get_account_spec)
        self.assertIn("customer_id", get_account_spec["inputSchema"]["properties"])

    def test_toolspec_endpoint(self) -> None:
        """Verify GET /toolspec.json wraps tools in {'tools': [...]} for Agent Registry."""
        res = self.client.get("/toolspec.json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tools", data)
        self.assertEqual(len(data["tools"]), 5)

    def test_streamable_http_mcp_handshake_and_invocation(self) -> None:
        """Verify MCP 2.0 Streamable HTTP initialize and tool invocation over /mcp."""
        # 1. MCP Initialize
        init_res = self.client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "governed-agent-test", "version": "1.0"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )
        self.assertEqual(init_res.status_code, 200)
        self.assertIn("banking-mcp-server", init_res.text)

        session_id = init_res.headers.get("mcp-session-id")
        headers = {"Accept": "application/json, text/event-stream"}
        if session_id:
            headers["mcp-session-id"] = session_id

        # 2. tools/list over MCP
        list_res = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=headers,
        )
        self.assertEqual(list_res.status_code, 200)
        self.assertIn("transfer_to_phone", list_res.text)

        # 3. tools/call over MCP
        call_res = self.client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_account",
                    "arguments": {"customer_id": "CUST001"},
                },
            },
            headers=headers,
        )
        self.assertEqual(call_res.status_code, 200)
        self.assertIn("Alice Smith", call_res.text)
        self.assertIn("4850", call_res.text)


def run_tests() -> bool:
    """Run test suites with clean verbose output and return success boolean."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestSyntheticDataPlane))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectToolExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCasesAndValidations))
    suite.addTests(loader.loadTestsFromTestCase(TestFastMCPHttpEndpoints))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
