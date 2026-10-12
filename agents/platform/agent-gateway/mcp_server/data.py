"""Enterprise Synthetic Banking Data Plane.

Provides realistic multi-tier banking customer profiles, in-memory transactional ledger,
concurrency locks, and state management compatible with the Google Cloud Agent Gateway codelab.
"""

from __future__ import annotations

import copy
import datetime
import re
import threading
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class CustomerTier(str, Enum):
    STANDARD = "STANDARD"
    PREMIUM_VIP = "PREMIUM_VIP"
    CORPORATE_TREASURY = "CORPORATE_TREASURY"


class TransactionType(str, Enum):
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    BILL_PAYMENT = "BILL_PAYMENT"
    DEPOSIT = "DEPOSIT"
    INITIAL_BALANCE = "INITIAL_BALANCE"


class TransactionRecord(BaseModel):
    transaction_id: str = Field(default_factory=lambda: f"TX-{uuid.uuid4().hex[:8].upper()}")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    transaction_type: str
    amount: float
    currency: str = "USD"
    counterparty: str
    balance_after: float
    status: str = "COMPLETED"
    reference_note: Optional[str] = None


class CustomerRecord(BaseModel):
    customer_id: str
    name: str
    tier: CustomerTier
    phone: str
    email: str
    balance: float
    currency: str = "USD"
    daily_limit: float
    risk_score: int  # 0 to 100 risk score
    account_status: str = "ACTIVE"
    aliases: List[str] = Field(default_factory=list)
    transaction_history: List[Dict[str, Any]] = Field(default_factory=list)


# Baseline Enterprise Dataset: 10 accounts across 3 distinct tiers
INITIAL_CUSTOMERS_DATA: List[Dict[str, Any]] = [
    # Standard Tier
    {
        "customer_id": "CUST001",
        "name": "Alice Smith",
        "tier": CustomerTier.STANDARD.value,
        "phone": "555-0001",
        "email": "alice.smith@example.com",
        "balance": 4850.00,
        "currency": "USD",
        "daily_limit": 2500.00,
        "risk_score": 15,
        "account_status": "ACTIVE",
        "aliases": ["Alice Smith", "A. Smith"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-001A",
                "timestamp": "2026-10-01T09:00:00Z",
                "transaction_type": TransactionType.INITIAL_BALANCE.value,
                "amount": 5000.00,
                "currency": "USD",
                "counterparty": "Payroll Direct Deposit - Enterprise Tech",
                "balance_after": 5000.00,
                "status": "COMPLETED",
                "reference_note": "Monthly Salary Deposit",
            },
            {
                "transaction_id": "TX-INIT-001B",
                "timestamp": "2026-10-04T14:32:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 150.00,
                "currency": "USD",
                "counterparty": "Cloud Utilities Power Corp",
                "balance_after": 4850.00,
                "status": "COMPLETED",
                "reference_note": "Utility Bill",
            },
        ],
    },
    {
        "customer_id": "CUST002",
        "name": "Bob Jones",
        "tier": CustomerTier.STANDARD.value,
        "phone": "555-0002",
        "email": "bob.jones@example.com",
        "balance": 1250.00,
        "currency": "USD",
        "daily_limit": 2000.00,
        "risk_score": 22,
        "account_status": "ACTIVE",
        "aliases": ["Bob Jones", "Robert Jones"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-002A",
                "timestamp": "2026-10-02T10:15:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 1400.00,
                "currency": "USD",
                "counterparty": "Freelance Client Services",
                "balance_after": 1400.00,
                "status": "COMPLETED",
                "reference_note": "Invoice #4401 Settlement",
            },
            {
                "transaction_id": "TX-INIT-002B",
                "timestamp": "2026-10-06T18:40:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 150.00,
                "currency": "USD",
                "counterparty": "Metro Broadband Internet",
                "balance_after": 1250.00,
                "status": "COMPLETED",
                "reference_note": "Fiber Internet Monthly",
            },
        ],
    },
    {
        "customer_id": "CUST003",
        "name": "Charlie Brown",
        "tier": CustomerTier.STANDARD.value,
        "phone": "555-0003",
        "email": "charlie.b@example.com",
        "balance": 820.50,
        "currency": "USD",
        "daily_limit": 1500.00,
        "risk_score": 28,
        "account_status": "ACTIVE",
        "aliases": ["Charlie Brown"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-003A",
                "timestamp": "2026-10-03T11:00:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 900.00,
                "currency": "USD",
                "counterparty": "Part-Time Consulting Stipend",
                "balance_after": 900.00,
                "status": "COMPLETED",
                "reference_note": "Contract Stipend",
            },
            {
                "transaction_id": "TX-INIT-003B",
                "timestamp": "2026-10-05T16:22:00Z",
                "transaction_type": TransactionType.TRANSFER_OUT.value,
                "amount": 79.50,
                "currency": "USD",
                "counterparty": "Campus Book Supplies",
                "balance_after": 820.50,
                "status": "COMPLETED",
                "reference_note": "Educational Supplies",
            },
        ],
    },
    {
        "customer_id": "CUST004",
        "name": "Diana Prince",
        "tier": CustomerTier.STANDARD.value,
        "phone": "555-0004",
        "email": "diana.p@themyscira-labs.com",
        "balance": 3400.00,
        "currency": "USD",
        "daily_limit": 3000.00,
        "risk_score": 10,
        "account_status": "ACTIVE",
        "aliases": ["Diana Prince"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-004A",
                "timestamp": "2026-10-01T08:30:00Z",
                "transaction_type": TransactionType.INITIAL_BALANCE.value,
                "amount": 4000.00,
                "currency": "USD",
                "counterparty": "Research Institute Grant",
                "balance_after": 4000.00,
                "status": "COMPLETED",
                "reference_note": "Laboratory Grant Disbursement",
            },
            {
                "transaction_id": "TX-INIT-004B",
                "timestamp": "2026-10-07T12:00:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 600.00,
                "currency": "USD",
                "counterparty": "Scientific Optics Supplier",
                "balance_after": 3400.00,
                "status": "COMPLETED",
                "reference_note": "Hardware Lab Invoice",
            },
        ],
    },
    # Premium / VIP Tier
    {
        "customer_id": "CUST005",
        "name": "Eve Davis",
        "tier": CustomerTier.PREMIUM_VIP.value,
        "phone": "555-0005",
        "email": "eve.davis@vip-enterprise.com",
        "balance": 28750.00,
        "currency": "USD",
        "daily_limit": 15000.00,
        "risk_score": 8,
        "account_status": "ACTIVE",
        "aliases": ["Eve Davis", "E. Davis", "Eve D."],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-005A",
                "timestamp": "2026-10-01T10:00:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 30000.00,
                "currency": "USD",
                "counterparty": "Global Advisory Retainer",
                "balance_after": 30000.00,
                "status": "COMPLETED",
                "reference_note": "Q4 Executive Retainer",
            },
            {
                "transaction_id": "TX-INIT-005B",
                "timestamp": "2026-10-04T19:15:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 1250.00,
                "currency": "USD",
                "counterparty": "First Class Executive Travel",
                "balance_after": 28750.00,
                "status": "COMPLETED",
                "reference_note": "Conference Travel Booking",
            },
        ],
    },
    {
        "customer_id": "CUST006",
        "name": "Frank Castle",
        "tier": CustomerTier.PREMIUM_VIP.value,
        "phone": "555-0006",
        "email": "frank.castle@private-security.com",
        "balance": 45200.00,
        "currency": "USD",
        "daily_limit": 20000.00,
        "risk_score": 35,
        "account_status": "ACTIVE",
        "aliases": ["Frank Castle"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-006A",
                "timestamp": "2026-10-02T13:45:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 50000.00,
                "currency": "USD",
                "counterparty": "Global Logistics Escrow Payout",
                "balance_after": 50000.00,
                "status": "COMPLETED",
                "reference_note": "Escrow Settlement",
            },
            {
                "transaction_id": "TX-INIT-006B",
                "timestamp": "2026-10-05T09:30:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 4800.00,
                "currency": "USD",
                "counterparty": "Armored Logistics Services",
                "balance_after": 45200.00,
                "status": "COMPLETED",
                "reference_note": "Security Fleet Maintenance",
            },
        ],
    },
    {
        "customer_id": "CUST007",
        "name": "Grace Hopper",
        "tier": CustomerTier.PREMIUM_VIP.value,
        "phone": "555-0007",
        "email": "grace.hopper@navy-tech.org",
        "balance": 92400.00,
        "currency": "USD",
        "daily_limit": 30000.00,
        "risk_score": 5,
        "account_status": "ACTIVE",
        "aliases": ["Grace Hopper", "Admiral Hopper"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-007A",
                "timestamp": "2026-10-01T11:00:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 100000.00,
                "currency": "USD",
                "counterparty": "Computing Foundation Fellowship",
                "balance_after": 100000.00,
                "status": "COMPLETED",
                "reference_note": "Annual Computing Research Endowment",
            },
            {
                "transaction_id": "TX-INIT-007B",
                "timestamp": "2026-10-06T15:00:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 7600.00,
                "currency": "USD",
                "counterparty": "Semiconductor Prototyping Fab",
                "balance_after": 92400.00,
                "status": "COMPLETED",
                "reference_note": "ASIC Verification Run",
            },
        ],
    },
    {
        "customer_id": "CUST008",
        "name": "Hector Salamanca",
        "tier": CustomerTier.PREMIUM_VIP.value,
        "phone": "555-0008",
        "email": "hector.s@albuquerque-holdings.com",
        "balance": 64000.00,
        "currency": "USD",
        "daily_limit": 10000.00,
        "risk_score": 82,  # Elevated Risk Watchlist
        "account_status": "ACTIVE",
        "aliases": ["Hector Salamanca"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-008A",
                "timestamp": "2026-10-03T16:00:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 75000.00,
                "currency": "USD",
                "counterparty": "Cash Courier Deposit Bureau",
                "balance_after": 75000.00,
                "status": "COMPLETED",
                "reference_note": "Commercial Cash Inflow",
            },
            {
                "transaction_id": "TX-INIT-008B",
                "timestamp": "2026-10-05T17:15:00Z",
                "transaction_type": TransactionType.TRANSFER_OUT.value,
                "amount": 11000.00,
                "currency": "USD",
                "counterparty": "Offshore Distribution S.A.",
                "balance_after": 64000.00,
                "status": "COMPLETED",
                "reference_note": "Wholesale Freight Settlement",
            },
        ],
    },
    # Corporate Treasury Tier
    {
        "customer_id": "CUST009",
        "name": "Acme Corp Treasury",
        "tier": CustomerTier.CORPORATE_TREASURY.value,
        "phone": "555-0009",
        "email": "treasury@acmecorp.internal",
        "balance": 1450000.00,
        "currency": "USD",
        "daily_limit": 500000.00,
        "risk_score": 12,
        "account_status": "ACTIVE",
        "aliases": ["Acme Corp Treasury", "Acme Corporation", "Sarah Connor (Treasurer)"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-009A",
                "timestamp": "2026-10-01T08:00:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 2000000.00,
                "currency": "USD",
                "counterparty": "Federal Reserve ACH Settlement",
                "balance_after": 2000000.00,
                "status": "COMPLETED",
                "reference_note": "Quarterly Working Capital Injection",
            },
            {
                "transaction_id": "TX-INIT-009B",
                "timestamp": "2026-10-04T11:45:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 550000.00,
                "currency": "USD",
                "counterparty": "Enterprise Cloud Computing Corp",
                "balance_after": 1450000.00,
                "status": "COMPLETED",
                "reference_note": "Global Infrastructure Services",
            },
        ],
    },
    {
        "customer_id": "CUST010",
        "name": "Apex Global Logistics",
        "tier": CustomerTier.CORPORATE_TREASURY.value,
        "phone": "555-0010",
        "email": "finance@apexlogistics.global",
        "balance": 3820000.00,
        "currency": "USD",
        "daily_limit": 1000000.00,
        "risk_score": 14,
        "account_status": "ACTIVE",
        "aliases": ["Apex Global Logistics", "Apex Freight Systems"],
        "transaction_history": [
            {
                "transaction_id": "TX-INIT-010A",
                "timestamp": "2026-10-01T07:30:00Z",
                "transaction_type": TransactionType.DEPOSIT.value,
                "amount": 4500000.00,
                "currency": "USD",
                "counterparty": "International Maritime Syndicate",
                "balance_after": 4500000.00,
                "status": "COMPLETED",
                "reference_note": "Container Fleet Charter Proceeds",
            },
            {
                "transaction_id": "TX-INIT-010B",
                "timestamp": "2026-10-05T14:10:00Z",
                "transaction_type": TransactionType.BILL_PAYMENT.value,
                "amount": 680000.00,
                "currency": "USD",
                "counterparty": "Global Bunker Fuel Supplies",
                "balance_after": 3820000.00,
                "status": "COMPLETED",
                "reference_note": "Pacific Fleet Fuel Allocation",
            },
        ],
    },
]

# Global in-memory storage and thread lock for concurrent safe operations
_CUSTOMERS_DB: Dict[str, Dict[str, Any]] = {}
_DB_LOCK = threading.RLock()


def _normalize_phone(raw_phone: str) -> str:
    """Normalize phone string for flexible matching (e.g. 555-0001, (555) 0001, 5550001)."""
    digits = re.sub(r"\D", "", raw_phone)
    if len(digits) == 7 and digits.startswith("555"):
        return f"{digits[:3]}-{digits[3:]}"
    if len(digits) == 10 and digits.startswith("1555"):
        return f"{digits[1:4]}-{digits[4:7]}"
    if len(digits) == 10:
        return f"{digits[3:6]}-{digits[6:]}" if digits.startswith("555") else digits
    return raw_phone.strip()


def reset_database() -> None:
    """Reset the banking data store to its pristine baseline state."""
    global _CUSTOMERS_DB
    with _DB_LOCK:
        _CUSTOMERS_DB = {
            item["customer_id"]: copy.deepcopy(item)
            for item in INITIAL_CUSTOMERS_DATA
        }


# Initialize DB on module load
reset_database()


def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve deep copy of a customer record by ID (case-insensitive)."""
    with _DB_LOCK:
        cleaned_id = customer_id.strip().upper() if customer_id else ""
        record = _CUSTOMERS_DB.get(cleaned_id)
        if record:
            return copy.deepcopy(record)

        # Fallback check against aliases
        for cust in _CUSTOMERS_DB.values():
            for alias in cust.get("aliases", []):
                if cleaned_id.lower() == alias.lower():
                    return copy.deepcopy(cust)
        return None


def find_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Look up a customer account by phone number."""
    if not phone:
        return None
    normalized_target = _normalize_phone(phone)
    with _DB_LOCK:
        for cust in _CUSTOMERS_DB.values():
            if cust.get("phone") == phone.strip() or _normalize_phone(cust.get("phone", "")) == normalized_target:
                return copy.deepcopy(cust)
        return None


def list_customers() -> List[Dict[str, Any]]:
    """Return copies of all customer accounts."""
    with _DB_LOCK:
        return [copy.deepcopy(cust) for cust in _CUSTOMERS_DB.values()]


def set_standard_daily_limit(daily_limit: float, min_only: bool = False) -> None:
    """Update the 24-hour cumulative daily limit for STANDARD tier accounts."""
    with _DB_LOCK:
        for cust in _CUSTOMERS_DB.values():
            if cust.get("tier") == CustomerTier.STANDARD.value:
                current = float(cust.get("daily_limit", 2500.0))
                if not min_only or daily_limit > current:
                    cust["daily_limit"] = float(daily_limit)


def check_balance(customer_id: str, amount: float) -> Tuple[bool, str, float]:
    """Check if customer has adequate funds and meets basic requirements.

    Returns:
        (has_funds: bool, reason: str, current_balance: float)
    """
    cust = get_customer(customer_id)
    if not cust:
        return False, f"Customer '{customer_id}' not found", 0.0

    current_balance = cust.get("balance", 0.0)
    if amount <= 0:
        return False, "Amount must be strictly positive", current_balance

    if current_balance < amount:
        return False, f"Insufficient funds. Balance: ${current_balance:.2f}, Requested: ${amount:.2f}", current_balance

    return True, "Funds available", current_balance


def get_daily_spent(customer_id: str, date_prefix: Optional[str] = None) -> float:
    """Calculate cumulative outbound transfers and bill payments for a given UTC date (default: today)."""
    if not date_prefix:
        date_prefix = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    cust = get_customer(customer_id)
    if not cust:
        return 0.0
    total = 0.0
    for tx in cust.get("transaction_history", []):
        if tx.get("status") == "COMPLETED" and tx.get("transaction_type") in (
            TransactionType.TRANSFER_OUT.value,
            TransactionType.BILL_PAYMENT.value,
        ):
            if tx.get("timestamp", "").startswith(date_prefix):
                total += tx.get("amount", 0.0)
    return round(total, 2)


def execute_transfer(
    sender_id: str,
    target_phone: str,
    amount: float,
    reference_note: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute funds transfer between two customers via phone lookup with full validations."""
    with _DB_LOCK:
        if amount <= 0:
            return {
                "status": "ERROR",
                "error_code": "INVALID_AMOUNT",
                "message": f"Transfer amount must be strictly greater than $0.00 (received: {amount}).",
            }

        sender = get_customer(sender_id)
        if not sender:
            return {
                "status": "ERROR",
                "error_code": "CUSTOMER_NOT_FOUND",
                "message": f"Sender account '{sender_id}' not found.",
            }

        recipient = find_customer_by_phone(target_phone)
        if not recipient:
            return {
                "status": "ERROR",
                "error_code": "RECIPIENT_NOT_FOUND",
                "message": f"No active banking recipient found registered to phone '{target_phone}'.",
            }

        if sender["customer_id"] == recipient["customer_id"]:
            return {
                "status": "ERROR",
                "error_code": "INVALID_TRANSFER",
                "message": "Transfer cannot be made to the same source account.",
            }

        # Cumulative daily limit enforcement
        daily_limit = sender.get("daily_limit", 2500.0)
        daily_spent = get_daily_spent(sender["customer_id"])
        if (daily_spent + amount) > daily_limit:
            remaining = max(0.0, daily_limit - daily_spent)
            return {
                "status": "ERROR",
                "error_code": "EXCEEDS_DAILY_LIMIT",
                "message": (
                    f"Transfer amount of ${amount:,.2f} exceeds available daily limit of ${remaining:,.2f} "
                    f"(Daily limit: ${daily_limit:,.2f}, already spent today: ${daily_spent:,.2f})."
                ),
            }

        # Balance check
        if sender["balance"] < amount:
            return {
                "status": "ERROR",
                "error_code": "INSUFFICIENT_FUNDS",
                "message": (
                    f"Insufficient funds. Current balance: ${sender['balance']:,.2f}, "
                    f"transfer requested: ${amount:,.2f}."
                ),
            }

        # Mutate records atomically
        tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
        iso_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Update sender
        sender_db_record = _CUSTOMERS_DB[sender["customer_id"]]
        sender_db_record["balance"] = round(sender_db_record["balance"] - amount, 2)
        sender_tx = {
            "transaction_id": tx_id,
            "timestamp": iso_time,
            "transaction_type": TransactionType.TRANSFER_OUT.value,
            "amount": amount,
            "currency": "USD",
            "counterparty": f"{recipient['name']} ({recipient['phone']})",
            "balance_after": sender_db_record["balance"],
            "status": "COMPLETED",
            "reference_note": reference_note or "Peer-to-peer phone transfer",
        }
        sender_db_record["transaction_history"].append(sender_tx)

        # Update recipient
        recipient_db_record = _CUSTOMERS_DB[recipient["customer_id"]]
        recipient_db_record["balance"] = round(recipient_db_record["balance"] + amount, 2)
        recipient_tx = {
            "transaction_id": f"{tx_id}-IN",
            "timestamp": iso_time,
            "transaction_type": TransactionType.TRANSFER_IN.value,
            "amount": amount,
            "currency": "USD",
            "counterparty": f"{sender['name']} ({sender['phone']})",
            "balance_after": recipient_db_record["balance"],
            "status": "COMPLETED",
            "reference_note": reference_note or f"Inbound transfer from {sender['name']}",
        }
        recipient_db_record["transaction_history"].append(recipient_tx)

        return {
            "status": "SUCCESS",
            "transaction_id": tx_id,
            "sender_id": sender["customer_id"],
            "sender_name": sender["name"],
            "recipient_id": recipient["customer_id"],
            "recipient_name": recipient["name"],
            "target_phone": target_phone,
            "amount": amount,
            "currency": "USD",
            "new_balance": sender_db_record["balance"],
            "timestamp": iso_time,
            "message": (
                f"Successfully transferred ${amount:,.2f} USD to {recipient['name']} ({target_phone}). "
                f"New balance: ${sender_db_record['balance']:,.2f}."
            ),
        }


def execute_bill_payment(
    customer_id: str,
    biller_name: str,
    account_number: str,
    amount: float,
) -> Dict[str, Any]:
    """Execute utility/merchant bill payment with invoice audit confirmation."""
    with _DB_LOCK:
        if amount <= 0:
            return {
                "status": "ERROR",
                "error_code": "INVALID_AMOUNT",
                "message": f"Bill payment amount must be strictly positive (received: {amount}).",
            }

        if not biller_name or not biller_name.strip():
            return {
                "status": "ERROR",
                "error_code": "INVALID_BILLER",
                "message": "Biller name must be provided.",
            }

        if not account_number or not account_number.strip():
            return {
                "status": "ERROR",
                "error_code": "INVALID_INPUT",
                "message": "Account/Invoice reference number must be provided.",
            }

        cust = get_customer(customer_id)
        if not cust:
            return {
                "status": "ERROR",
                "error_code": "CUSTOMER_NOT_FOUND",
                "message": f"Customer account '{customer_id}' not found.",
            }

        # Cumulative daily limit enforcement
        daily_limit = cust.get("daily_limit", 2500.0)
        daily_spent = get_daily_spent(cust["customer_id"])
        if (daily_spent + amount) > daily_limit:
            remaining = max(0.0, daily_limit - daily_spent)
            return {
                "status": "ERROR",
                "error_code": "EXCEEDS_DAILY_LIMIT",
                "message": (
                    f"Payment amount of ${amount:,.2f} exceeds available daily limit of ${remaining:,.2f} "
                    f"(Daily limit: ${daily_limit:,.2f}, already spent today: ${daily_spent:,.2f})."
                ),
            }

        if cust["balance"] < amount:
            return {
                "status": "ERROR",
                "error_code": "INSUFFICIENT_FUNDS",
                "message": (
                    f"Insufficient funds. Current balance: ${cust['balance']:,.2f}, "
                    f"payment requested: ${amount:,.2f}."
                ),
            }

        pay_id = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        auth_code = f"AUTH-{uuid.uuid4().hex[:6].upper()}"
        iso_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        db_record = _CUSTOMERS_DB[cust["customer_id"]]
        db_record["balance"] = round(db_record["balance"] - amount, 2)
        bill_tx = {
            "transaction_id": pay_id,
            "timestamp": iso_time,
            "transaction_type": TransactionType.BILL_PAYMENT.value,
            "amount": amount,
            "currency": "USD",
            "counterparty": f"{biller_name.strip()} (Acc #{account_number.strip()})",
            "balance_after": db_record["balance"],
            "status": "COMPLETED",
            "reference_note": f"Auth confirmation code: {auth_code}",
        }
        db_record["transaction_history"].append(bill_tx)

        return {
            "status": "SUCCESS",
            "payment_id": pay_id,
            "customer_id": cust["customer_id"],
            "customer_name": cust["name"],
            "biller_name": biller_name.strip(),
            "account_number": account_number.strip(),
            "amount": amount,
            "currency": "USD",
            "new_balance": db_record["balance"],
            "confirmation_code": auth_code,
            "timestamp": iso_time,
            "message": (
                f"Bill payment of ${amount:,.2f} USD to {biller_name.strip()} "
                f"(Account #{account_number.strip()}) confirmed. Confirmation: {auth_code}."
            ),
        }
