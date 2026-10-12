"""Google Cloud Agent Gateway & Policy Simulator.

Implements the high-fidelity 5-step Google Cloud Agent Gateway governance pipeline:
  Step 1: Agent Identity Verification (cryptographic bearer token & SPIFFE/Service Account identity)
  Step 2: Agent Registry Catalog Check (allowlisted MCP tools catalog)
  Step 3: Model Armor Payload Inspection (prompt injection defense & sensitive PII detection)
  Step 4: IAM Unified Access Policy (roles/iap.egressor verification)
  Step 5: Semantic Governance Policy (SGP) Engine:
          - SGP-01 AML: Block transfers > $1,000 for standard accounts, or risk_score > 50
          - SGP-02 Daily Limit: Block transfers/payments exceeding cumulative 24-hr daily limits

Provides thread-safe in-memory audit logging, dynamic policy toggle switches,
and dual in-process / HTTP ASGI execution modes.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

# Ensure agents/platform/agent-gateway is on sys.path for robust cross-directory imports
_PLATFORM_DIR = Path(__file__).resolve().parent.parent
if str(_PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_DIR))

from mcp_server.data import (
    CustomerTier,
    get_customer,
    get_daily_spent,
    reset_database,
)
from mcp_server.server import (
    get_account,
    get_transaction_history,
    lookup_customer_by_phone,
    pay_bill,
    transfer_to_phone,
)

logger = logging.getLogger("gateway_simulator")


# ==============================================================================
# Pipeline Decision & Request / Response Models
# ==============================================================================


class PolicyDecision(BaseModel):
    """Structured decision outcome from a single governance pipeline step."""

    step: str
    name: str
    status: str  # "PERMITTED" or "BLOCKED"
    rule_id: Optional[str] = None
    details: str
    latency_ms: float = 0.0


class GatewayRequest(BaseModel):
    """Inbound request to the Google Cloud Agent Gateway."""

    request_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:12]}")
    caller_identity: str = "service-123456789012@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    bearer_token: Optional[str] = "ya29.c.b0_test_token_valid"
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    caller_roles: List[str] = Field(default_factory=lambda: ["roles/iap.egressor"])
    prompt_context: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class GatewayResponse(BaseModel):
    """Outbound response returned by the Google Cloud Agent Gateway."""

    request_id: str
    status_code: int
    outcome: str  # "PERMITTED" or "BLOCKED"
    error_code: Optional[str] = None
    message: str
    tool_result: Optional[Dict[str, Any]] = None
    step_decisions: List[PolicyDecision] = Field(default_factory=list)
    latency_ms: float = 0.0
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class AuditLogEntry(BaseModel):
    """Immutable structured audit log record for security, observability, and compliance."""

    request_id: str
    timestamp: str
    caller_identity: str
    tool_name: str
    tool_args: Dict[str, Any]
    status_code: int
    outcome: str
    error_code: Optional[str] = None
    message: str
    step_decisions: List[Dict[str, Any]]
    latency_ms: float
    tool_result_preview: Optional[str] = None


# ==============================================================================
# Model Armor Security Patterns
# ==============================================================================

# Prompt injection and jailbreak heuristic regular expressions
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?prior\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+DAN\b", re.IGNORECASE),
    re.compile(r"bypass\s+safety\s+(?:guidelines|filters|guards)", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?your\s+rules", re.IGNORECASE),
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
]

# Sensitive Data Protection (SDP): US Social Security Number patterns
SSN_PATTERNS = [
    re.compile(r"\b(?!000|666|9\d{2})\d{3}[- ]\d{2}[- ]\d{4}\b"),
    re.compile(r"\bssn[:=\s]+\d{9}\b", re.IGNORECASE),
    re.compile(r"\bssn[:=\s]+\d{3}-\d{2}-\d{4}\b", re.IGNORECASE),
]


# ==============================================================================
# Gateway Simulator Implementation
# ==============================================================================


class GatewaySimulator:
    """Production-grade simulator for Google Cloud Agent Gateway and SGP Engine."""

    def __init__(
        self,
        enable_identity_check: bool = True,
        enable_registry_check: bool = True,
        enable_model_armor: bool = True,
        enable_iam_check: bool = True,
        enable_sgp: bool = True,
        standard_transfer_limit: float = 1000.0,
        max_allowed_risk_score: int = 50,
        required_iam_role: str = "roles/iap.egressor",
        max_audit_logs: int = 1000,
        policy_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """Initialize the Gateway Simulator with toggleable governance controls."""
        # Toggle switches
        self.enable_identity_check = enable_identity_check
        self.enable_registry_check = enable_registry_check
        self.enable_model_armor = enable_model_armor
        self.enable_iam_check = enable_iam_check
        self.enable_sgp = enable_sgp

        # Governance parameters
        self.standard_transfer_limit = standard_transfer_limit
        self.max_allowed_risk_score = max_allowed_risk_score
        self.required_iam_role = required_iam_role

        # Declarative policies store
        self.policy_dir: Optional[Path] = None
        self.sgp_rules: List[Dict[str, Any]] = []
        self.model_armor_policy: Dict[str, Any] = {}
        self.iap_policy: Dict[str, Any] = {}
        self.prompt_injection_patterns: List[re.Pattern] = list(PROMPT_INJECTION_PATTERNS)
        self.ssn_patterns: List[re.Pattern] = list(SSN_PATTERNS)

        # Tool Registry
        self.registered_tools: Dict[str, Callable[..., Any]] = {
            "get_account": get_account,
            "lookup_customer_by_phone": lookup_customer_by_phone,
            "transfer_to_phone": transfer_to_phone,
            "pay_bill": pay_bill,
            "get_transaction_history": get_transaction_history,
        }

        # Identity patterns allowlist
        self._identity_patterns = [
            re.compile(r"^service-\d+@gcp-sa-[a-z0-9\-]+\.iam\.gserviceaccount\.com$"),
            re.compile(r"^[a-z0-9\-]+@[a-z0-9\-]+\.iam\.gserviceaccount\.com$"),
            re.compile(r"^spiffe://[a-zA-Z0-9.\-]+/[a-zA-Z0-9/_.\-]+$"),
            re.compile(r"^allAuthenticatedUsers$"),
        ]

        # Load declarative policies if available
        if policy_dir is not None:
            self.load_policies_from_dir(policy_dir)
        else:
            default_policy_dir = Path(__file__).resolve().parent / "policies"
            if default_policy_dir.is_dir():
                self.load_policies_from_dir(default_policy_dir)

        # Thread-safe in-memory audit log
        self._audit_lock = threading.RLock()
        self._audit_logs: List[AuditLogEntry] = []
        self._max_audit_logs = max_audit_logs

    def load_policies_from_dir(self, policy_dir: Union[str, Path]) -> None:
        """Load and parse declarative JSON policies dynamically from directory."""
        p_dir = Path(policy_dir)
        if not p_dir.is_dir():
            return
        self.policy_dir = p_dir

        # Load SGP AML policy
        sgp_file = p_dir / "sgp_aml_policy.json"
        if sgp_file.is_file():
            try:
                with open(sgp_file, "r", encoding="utf-8") as f:
                    sgp_data = json.load(f)
                self.sgp_rules = sgp_data.get("rules", [])
                for rule in self.sgp_rules:
                    if rule.get("ruleId") == "SGP-01":
                        params = rule.get("parameters", {})
                        if "standardTierTransferLimitUsd" in params:
                            self.standard_transfer_limit = float(params["standardTierTransferLimitUsd"])
                        if "maxAllowedRiskScore" in params:
                            self.max_allowed_risk_score = int(params["maxAllowedRiskScore"])
            except Exception as e:
                logger.warning("Failed to load SGP policy from %s: %s", sgp_file, e)

        # Load Model Armor policy
        ma_file = p_dir / "model_armor_policy.json"
        if ma_file.is_file():
            try:
                with open(ma_file, "r", encoding="utf-8") as f:
                    self.model_armor_policy = json.load(f)
                filter_cfg = self.model_armor_policy.get("filterConfig", {})
                pi_settings = filter_cfg.get("piAndJailbreakFilterSettings", {})
                patterns = pi_settings.get("heuristicPatterns", [])
                for pat in patterns:
                    escaped = re.escape(pat)
                    compiled = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                    if compiled not in self.prompt_injection_patterns:
                        self.prompt_injection_patterns.append(compiled)
            except Exception as e:
                logger.warning("Failed to load Model Armor policy from %s: %s", ma_file, e)

        # Load IAM Unified Access policy
        iap_file = p_dir / "iap_access_policy.json"
        if iap_file.is_file():
            try:
                with open(iap_file, "r", encoding="utf-8") as f:
                    self.iap_policy = json.load(f)
            except Exception as e:
                logger.warning("Failed to load IAM policy from %s: %s", iap_file, e)

    # --------------------------------------------------------------------------
    # Tool Catalog Management
    # --------------------------------------------------------------------------

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """Register a new tool into the allowlisted Agent Registry catalog."""
        self.registered_tools[name] = func

    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the Agent Registry catalog."""
        return self.registered_tools.pop(name, None) is not None

    def list_catalog(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self.registered_tools.keys())

    # --------------------------------------------------------------------------
    # Audit Logging Management
    # --------------------------------------------------------------------------

    def _record_audit_log(self, entry: AuditLogEntry) -> None:
        """Thread-safely append an audit entry."""
        with self._audit_lock:
            self._audit_logs.append(entry)
            if len(self._audit_logs) > self._max_audit_logs:
                self._audit_logs.pop(0)

    def get_audit_logs(
        self,
        limit: int = 50,
        filter_outcome: Optional[str] = None,
        filter_tool: Optional[str] = None,
    ) -> List[AuditLogEntry]:
        """Retrieve audit log records with optional filtering."""
        with self._audit_lock:
            results = list(self._audit_logs)

        if filter_outcome:
            results = [e for e in results if e.outcome == filter_outcome]
        if filter_tool:
            results = [e for e in results if e.tool_name == filter_tool]

        return results[-limit:]

    def clear_audit_logs(self) -> None:
        """Clear all in-memory audit records."""
        with self._audit_lock:
            self._audit_logs.clear()

    def get_audit_stats(self) -> Dict[str, Any]:
        """Return statistical metrics across the audit history."""
        with self._audit_lock:
            total = len(self._audit_logs)
            if total == 0:
                return {
                    "total_requests": 0,
                    "permitted": 0,
                    "blocked": 0,
                    "blocked_by_step": {},
                    "average_latency_ms": 0.0,
                }

            permitted = sum(1 for e in self._audit_logs if e.outcome == "PERMITTED")
            blocked = total - permitted
            avg_latency = sum(e.latency_ms for e in self._audit_logs) / total

            blocked_by_step: Dict[str, int] = {}
            for e in self._audit_logs:
                if e.outcome == "BLOCKED" and e.error_code:
                    blocked_by_step[e.error_code] = (
                        blocked_by_step.get(e.error_code, 0) + 1
                    )

            return {
                "total_requests": total,
                "permitted": permitted,
                "blocked": blocked,
                "blocked_by_step": blocked_by_step,
                "average_latency_ms": round(avg_latency, 3),
            }

    # --------------------------------------------------------------------------
    # Pipeline Step 1: Agent Identity Verification
    # --------------------------------------------------------------------------

    def _evaluate_step_1_identity(
        self, request: GatewayRequest
    ) -> Tuple[bool, PolicyDecision, Optional[GatewayResponse]]:
        """Verify cryptographic bearer token and recognized service account identity."""
        t0 = time.perf_counter()
        if not self.enable_identity_check:
            dt = (time.perf_counter() - t0) * 1000.0
            return (
                True,
                PolicyDecision(
                    step="step_1_identity",
                    name="Agent Identity Verification",
                    status="PERMITTED",
                    details="Agent Identity check bypassed by policy toggle.",
                    latency_ms=dt,
                ),
                None,
            )

        token = (request.bearer_token or "").strip()
        identity = (request.caller_identity or "").strip()

        # Token checks
        if not token:
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_1_identity",
                name="Agent Identity Verification",
                status="BLOCKED",
                rule_id="IDENTITY_MISSING_TOKEN",
                details="Missing cryptographic bearer token. Authentication rejected.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=401,
                outcome="BLOCKED",
                error_code="AGENT_IDENTITY_REJECTED",
                message="Missing cryptographic bearer token. Cryptographic agent identity token is required.",
                step_decisions=[decision],
            )
            return False, decision, resp

        # Detect forged / tampered tokens
        if (
            token.lower().startswith("forged")
            or token.lower().startswith("invalid")
            or "tampered" in token.lower()
        ):
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_1_identity",
                name="Agent Identity Verification",
                status="BLOCKED",
                rule_id="IDENTITY_FORGED_TOKEN",
                details=f"Cryptographic signature check failed for bearer token '{token[:12]}...'.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=401,
                outcome="BLOCKED",
                error_code="AGENT_IDENTITY_REJECTED",
                message="Invalid or forged bearer token. Cryptographic signature verification failed.",
                step_decisions=[decision],
            )
            return False, decision, resp

        # Identity checks
        if not identity:
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_1_identity",
                name="Agent Identity Verification",
                status="BLOCKED",
                rule_id="IDENTITY_MISSING_PRINCIPAL",
                details="Caller principal identity is missing or empty.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=401,
                outcome="BLOCKED",
                error_code="AGENT_IDENTITY_REJECTED",
                message="Caller identity is missing or empty.",
                step_decisions=[decision],
            )
            return False, decision, resp

        # Verify against allowed identity patterns
        identity_matched = any(p.match(identity) for p in self._identity_patterns)
        if not identity_matched or identity.lower().startswith(("rogue", "attacker")):
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_1_identity",
                name="Agent Identity Verification",
                status="BLOCKED",
                rule_id="IDENTITY_UNRECOGNIZED_PRINCIPAL",
                details=f"Unrecognized principal '{identity}'. Must match GCP service account or SPIFFE ID.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=401,
                outcome="BLOCKED",
                error_code="AGENT_IDENTITY_REJECTED",
                message=f"Unrecognized caller identity '{identity}'. Only verified GCP service agents and SPIFFE principals are permitted.",
                step_decisions=[decision],
            )
            return False, decision, resp

        dt = (time.perf_counter() - t0) * 1000.0
        decision = PolicyDecision(
            step="step_1_identity",
            name="Agent Identity Verification",
            status="PERMITTED",
            details=f"Verified cryptographic token and principal: {identity}",
            latency_ms=dt,
        )
        return True, decision, None

    # --------------------------------------------------------------------------
    # Pipeline Step 2: Agent Registry Catalog Check
    # --------------------------------------------------------------------------

    def _evaluate_step_2_registry(
        self, request: GatewayRequest, prior_decisions: List[PolicyDecision]
    ) -> Tuple[bool, PolicyDecision, Optional[GatewayResponse]]:
        """Verify tool is cataloged in the allowlisted Agent Registry tool catalog."""
        t0 = time.perf_counter()
        if not self.enable_registry_check:
            dt = (time.perf_counter() - t0) * 1000.0
            return (
                True,
                PolicyDecision(
                    step="step_2_registry",
                    name="Agent Registry Catalog Check",
                    status="PERMITTED",
                    details="Agent Registry catalog check bypassed by policy toggle.",
                    latency_ms=dt,
                ),
                None,
            )

        if request.tool_name not in self.registered_tools:
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_2_registry",
                name="Agent Registry Catalog Check",
                status="BLOCKED",
                rule_id="REGISTRY_UNLISTED_TOOL",
                details=f"Tool '{request.tool_name}' is not in allowlisted Agent Registry catalog.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=404,
                outcome="BLOCKED",
                error_code="TOOL_NOT_REGISTERED",
                message=f"Tool '{request.tool_name}' is not registered in Google Cloud Agent Registry catalog. Egress blocked.",
                step_decisions=prior_decisions + [decision],
            )
            return False, decision, resp

        dt = (time.perf_counter() - t0) * 1000.0
        decision = PolicyDecision(
            step="step_2_registry",
            name="Agent Registry Catalog Check",
            status="PERMITTED",
            details=f"Tool '{request.tool_name}' verified in Agent Registry catalog.",
            latency_ms=dt,
        )
        return True, decision, None

    # --------------------------------------------------------------------------
    # Pipeline Step 3: Model Armor Payload Inspection
    # --------------------------------------------------------------------------

    def _extract_all_text_fragments(self, obj: Any) -> List[str]:
        """Recursively collect all string values from input arguments."""
        fragments: List[str] = []
        if isinstance(obj, str):
            fragments.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    fragments.append(k)
                fragments.extend(self._extract_all_text_fragments(v))
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                fragments.extend(self._extract_all_text_fragments(item))
        return fragments

    def _evaluate_step_3_model_armor(
        self, request: GatewayRequest, prior_decisions: List[PolicyDecision]
    ) -> Tuple[bool, PolicyDecision, Optional[GatewayResponse]]:
        """Inspect prompt and arguments for prompt injection and sensitive PII (SSN)."""
        t0 = time.perf_counter()
        if not self.enable_model_armor:
            dt = (time.perf_counter() - t0) * 1000.0
            return (
                True,
                PolicyDecision(
                    step="step_3_model_armor",
                    name="Model Armor Payload Inspection",
                    status="PERMITTED",
                    details="Model Armor inspection bypassed by policy toggle.",
                    latency_ms=dt,
                ),
                None,
            )

        text_fragments = self._extract_all_text_fragments(request.tool_args)
        if request.prompt_context:
            text_fragments.append(request.prompt_context)

        full_payload_text = " \n ".join(text_fragments)

        # 1. Prompt Injection and Jailbreak Defense
        for pat in self.prompt_injection_patterns:
            match = pat.search(full_payload_text)
            if match:
                dt = (time.perf_counter() - t0) * 1000.0
                detected_text = match.group(0)
                decision = PolicyDecision(
                    step="step_3_model_armor",
                    name="Model Armor Payload Inspection",
                    status="BLOCKED",
                    rule_id="MODEL_ARMOR_INJECTION",
                    details=f"Prompt injection / jailbreak detected: '{detected_text}'",
                    latency_ms=dt,
                )
                resp = GatewayResponse(
                    request_id=request.request_id,
                    status_code=403,
                    outcome="BLOCKED",
                    error_code="MODEL_ARMOR_VIOLATION",
                    message=f"Model Armor violation: Prompt injection or jailbreak pattern detected ('{detected_text}'). Ingress payload sanitized and rejected.",
                    step_decisions=prior_decisions + [decision],
                )
                return False, decision, resp

        # 2. Sensitive Data Protection (SDP): Raw Social Security Numbers
        for pat in self.ssn_patterns:
            match = pat.search(full_payload_text)
            if match:
                dt = (time.perf_counter() - t0) * 1000.0
                decision = PolicyDecision(
                    step="step_3_model_armor",
                    name="Model Armor Payload Inspection",
                    status="BLOCKED",
                    rule_id="MODEL_ARMOR_PII_SSN",
                    details="Sensitive Data Protection triggered: Raw US Social Security Number detected in payload.",
                    latency_ms=dt,
                )
                resp = GatewayResponse(
                    request_id=request.request_id,
                    status_code=403,
                    outcome="BLOCKED",
                    error_code="MODEL_ARMOR_VIOLATION",
                    message="Model Armor violation: Sensitive PII (US Social Security Number) detected in payload. Egress blocked to prevent data exfiltration.",
                    step_decisions=prior_decisions + [decision],
                )
                return False, decision, resp

        dt = (time.perf_counter() - t0) * 1000.0
        decision = PolicyDecision(
            step="step_3_model_armor",
            name="Model Armor Payload Inspection",
            status="PERMITTED",
            details="Payload passed Model Armor inspection (no prompt injection or sensitive PII detected).",
            latency_ms=dt,
        )
        return True, decision, None

    # --------------------------------------------------------------------------
    # Pipeline Step 4: IAM Unified Access Policy
    # --------------------------------------------------------------------------

    def _evaluate_step_4_iam(
        self, request: GatewayRequest, prior_decisions: List[PolicyDecision]
    ) -> Tuple[bool, PolicyDecision, Optional[GatewayResponse]]:
        """Verify caller holds the required egress IAM role."""
        t0 = time.perf_counter()
        if not self.enable_iam_check:
            dt = (time.perf_counter() - t0) * 1000.0
            return (
                True,
                PolicyDecision(
                    step="step_4_iam",
                    name="IAM Unified Access Policy",
                    status="PERMITTED",
                    details="IAM Unified Access check bypassed by policy toggle.",
                    latency_ms=dt,
                ),
                None,
            )

        caller_roles = set(request.caller_roles or [])
        allowed_roles = {
            self.required_iam_role,
            "roles/agentgateway.serviceAgent",
            "roles/owner",
            "roles/editor",
        }

        if not (caller_roles & allowed_roles):
            dt = (time.perf_counter() - t0) * 1000.0
            decision = PolicyDecision(
                step="step_4_iam",
                name="IAM Unified Access Policy",
                status="BLOCKED",
                rule_id="IAM_PERMISSION_DENIED",
                details=f"Principal '{request.caller_identity}' lacks required IAM role '{self.required_iam_role}'.",
                latency_ms=dt,
            )
            resp = GatewayResponse(
                request_id=request.request_id,
                status_code=403,
                outcome="BLOCKED",
                error_code="IAM_PERMISSION_DENIED",
                message=f"Caller '{request.caller_identity}' lacks required IAM permission '{self.required_iam_role}' on endpoint. Egress denied.",
                step_decisions=prior_decisions + [decision],
            )
            return False, decision, resp

        dt = (time.perf_counter() - t0) * 1000.0
        decision = PolicyDecision(
            step="step_4_iam",
            name="IAM Unified Access Policy",
            status="PERMITTED",
            details=f"IAM Unified Access verified. Caller has '{self.required_iam_role}' role.",
            latency_ms=dt,
        )
        return True, decision, None

    # --------------------------------------------------------------------------
    # Pipeline Step 5: Semantic Governance Policy (SGP) Engine
    # --------------------------------------------------------------------------

    def _evaluate_step_5_sgp(
        self, request: GatewayRequest, prior_decisions: List[PolicyDecision]
    ) -> Tuple[bool, PolicyDecision, Optional[GatewayResponse]]:
        """Evaluate natural language Semantic Governance Policies (SGP-01 AML & SGP-02 Daily Limit)."""
        t0 = time.perf_counter()
        if not self.enable_sgp:
            dt = (time.perf_counter() - t0) * 1000.0
            return (
                True,
                PolicyDecision(
                    step="step_5_sgp",
                    name="Semantic Governance Policy Engine",
                    status="PERMITTED",
                    details="Semantic Governance Policy engine bypassed by policy toggle.",
                    latency_ms=dt,
                ),
                None,
            )

        # Extract transaction parameters if applicable
        tool_name = request.tool_name
        args = request.tool_args or {}

        if tool_name in ("transfer_to_phone", "pay_bill"):
            customer_id = args.get("customer_id")
            amount_val = args.get("amount")

            if customer_id and amount_val is not None:
                try:
                    amount = float(amount_val)
                except (ValueError, TypeError):
                    amount = 0.0

                customer = get_customer(str(customer_id))
                if customer:
                    tier = customer.get("tier")
                    risk_score = customer.get("risk_score", 0)
                    daily_limit = float(customer.get("daily_limit", 0.0))

                    # Dynamically evaluate declarative rules if loaded
                    if self.sgp_rules:
                        for rule in self.sgp_rules:
                            target_tools = rule.get("target", {}).get("tools", [])
                            if target_tools and tool_name not in target_tools:
                                continue
                            rule_id = rule.get("ruleId", "SGP")
                            params = rule.get("parameters", {})

                            # SGP-01: AML Risk Watchlist & High-Value Limits
                            if rule_id == "SGP-01":
                                rule_max_risk = params.get("maxAllowedRiskScore", self.max_allowed_risk_score)
                                if risk_score > rule_max_risk:
                                    dt = (time.perf_counter() - t0) * 1000.0
                                    reason = (
                                        f"SGP-01 AML Watchlist: Customer '{customer_id}' has elevated AML risk score "
                                        f"({risk_score} > {rule_max_risk}). All automated outbound "
                                        f"transactions are suspended."
                                    )
                                    decision = PolicyDecision(
                                        step="step_5_sgp",
                                        name="Semantic Governance Policy Engine",
                                        status="BLOCKED",
                                        rule_id="SGP-01",
                                        details=reason,
                                        latency_ms=dt,
                                    )
                                    resp = GatewayResponse(
                                        request_id=request.request_id,
                                        status_code=403,
                                        outcome="BLOCKED",
                                        error_code="SGP_POLICY_DENIED",
                                        message=reason,
                                        step_decisions=prior_decisions + [decision],
                                    )
                                    return False, decision, resp

                                rule_std_limit = params.get("standardTierTransferLimitUsd", self.standard_transfer_limit)
                                if (
                                    tool_name == "transfer_to_phone"
                                    and tier == CustomerTier.STANDARD.value
                                    and amount > rule_std_limit
                                ):
                                    dt = (time.perf_counter() - t0) * 1000.0
                                    reason = (
                                        f"SGP-01 AML Policy: Transfer amount of ${amount:,.2f} USD exceeds the maximum "
                                        f"allowed limit of ${rule_std_limit:,.2f} USD for STANDARD tier "
                                        f"accounts. Escalate to compliance."
                                    )
                                    decision = PolicyDecision(
                                        step="step_5_sgp",
                                        name="Semantic Governance Policy Engine",
                                        status="BLOCKED",
                                        rule_id="SGP-01",
                                        details=reason,
                                        latency_ms=dt,
                                    )
                                    resp = GatewayResponse(
                                        request_id=request.request_id,
                                        status_code=403,
                                        outcome="BLOCKED",
                                        error_code="SGP_POLICY_DENIED",
                                        message=reason,
                                        step_decisions=prior_decisions + [decision],
                                    )
                                    return False, decision, resp

                            # SGP-02: Cumulative Daily Limit Velocity Rule
                            elif rule_id == "SGP-02":
                                daily_spent = get_daily_spent(str(customer_id))
                                remaining = max(0.0, daily_limit - daily_spent)
                                if (daily_spent + amount) > daily_limit:
                                    dt = (time.perf_counter() - t0) * 1000.0
                                    reason = (
                                        f"SGP-02 Daily Limit Policy: Transaction of ${amount:,.2f} USD would exceed "
                                        f"cumulative 24-hour limit of ${daily_limit:,.2f} USD (already spent: "
                                        f"${daily_spent:,.2f} USD, remaining: ${remaining:,.2f} USD)."
                                    )
                                    decision = PolicyDecision(
                                        step="step_5_sgp",
                                        name="Semantic Governance Policy Engine",
                                        status="BLOCKED",
                                        rule_id="SGP-02",
                                        details=reason,
                                        latency_ms=dt,
                                    )
                                    resp = GatewayResponse(
                                        request_id=request.request_id,
                                        status_code=403,
                                        outcome="BLOCKED",
                                        error_code="SGP_POLICY_DENIED",
                                        message=reason,
                                        step_decisions=prior_decisions + [decision],
                                    )
                                    return False, decision, resp
                    else:
                        # 1. SGP-01 AML Watchlist Rule: Elevated Risk Score
                        if risk_score > self.max_allowed_risk_score:
                            dt = (time.perf_counter() - t0) * 1000.0
                            reason = (
                                f"SGP-01 AML Watchlist: Customer '{customer_id}' has elevated AML risk score "
                                f"({risk_score} > {self.max_allowed_risk_score}). All automated outbound "
                                f"transactions are suspended."
                            )
                            decision = PolicyDecision(
                                step="step_5_sgp",
                                name="Semantic Governance Policy Engine",
                                status="BLOCKED",
                                rule_id="SGP-01",
                                details=reason,
                                latency_ms=dt,
                            )
                            resp = GatewayResponse(
                                request_id=request.request_id,
                                status_code=403,
                                outcome="BLOCKED",
                                error_code="SGP_POLICY_DENIED",
                                message=reason,
                                step_decisions=prior_decisions + [decision],
                            )
                            return False, decision, resp

                        # 2. SGP-01 AML High-Value Transfer Threshold for Standard Accounts
                        if (
                            tool_name == "transfer_to_phone"
                            and tier == CustomerTier.STANDARD.value
                            and amount > self.standard_transfer_limit
                        ):
                            dt = (time.perf_counter() - t0) * 1000.0
                            reason = (
                                f"SGP-01 AML Policy: Transfer amount of ${amount:,.2f} USD exceeds the maximum "
                                f"allowed limit of ${self.standard_transfer_limit:,.2f} USD for STANDARD tier "
                                f"accounts. Escalate to compliance."
                            )
                            decision = PolicyDecision(
                                step="step_5_sgp",
                                name="Semantic Governance Policy Engine",
                                status="BLOCKED",
                                rule_id="SGP-01",
                                details=reason,
                                latency_ms=dt,
                            )
                            resp = GatewayResponse(
                                request_id=request.request_id,
                                status_code=403,
                                outcome="BLOCKED",
                                error_code="SGP_POLICY_DENIED",
                                message=reason,
                                step_decisions=prior_decisions + [decision],
                            )
                            return False, decision, resp

                        # 3. SGP-02 Daily Limit Velocity Rule
                        daily_spent = get_daily_spent(str(customer_id))
                        remaining = max(0.0, daily_limit - daily_spent)
                        if (daily_spent + amount) > daily_limit:
                            dt = (time.perf_counter() - t0) * 1000.0
                            reason = (
                                f"SGP-02 Daily Limit Policy: Transaction of ${amount:,.2f} USD would exceed "
                                f"cumulative 24-hour limit of ${daily_limit:,.2f} USD (already spent: "
                                f"${daily_spent:,.2f} USD, remaining: ${remaining:,.2f} USD)."
                            )
                            decision = PolicyDecision(
                                step="step_5_sgp",
                                name="Semantic Governance Policy Engine",
                                status="BLOCKED",
                                rule_id="SGP-02",
                                details=reason,
                                latency_ms=dt,
                            )
                            resp = GatewayResponse(
                                request_id=request.request_id,
                                status_code=403,
                                outcome="BLOCKED",
                                error_code="SGP_POLICY_DENIED",
                                message=reason,
                                step_decisions=prior_decisions + [decision],
                            )
                            return False, decision, resp

        dt = (time.perf_counter() - t0) * 1000.0
        decision = PolicyDecision(
            step="step_5_sgp",
            name="Semantic Governance Policy Engine",
            status="PERMITTED",
            details="Request evaluated against Semantic Governance Policies (SGP-01 AML and SGP-02 Daily Limit). Verdict: PERMITTED.",
            latency_ms=dt,
        )
        return True, decision, None

    # --------------------------------------------------------------------------
    # Forwarding & Main Pipeline Orchestration
    # --------------------------------------------------------------------------

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        """Execute the 5-step Google Cloud Agent Gateway governance pipeline."""
        start_time = time.perf_counter()
        decisions: List[PolicyDecision] = []

        # Step 1: Agent Identity
        passed, dec_1, err_resp = self._evaluate_step_1_identity(request)
        decisions.append(dec_1)
        if not passed and err_resp is not None:
            err_resp.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._record_audit_log(
                AuditLogEntry(
                    request_id=request.request_id,
                    timestamp=err_resp.timestamp,
                    caller_identity=request.caller_identity,
                    tool_name=request.tool_name,
                    tool_args=request.tool_args,
                    status_code=err_resp.status_code,
                    outcome=err_resp.outcome,
                    error_code=err_resp.error_code,
                    message=err_resp.message,
                    step_decisions=[d.model_dump() for d in decisions],
                    latency_ms=err_resp.latency_ms,
                )
            )
            return err_resp

        # Step 2: Agent Registry Catalog Check
        passed, dec_2, err_resp = self._evaluate_step_2_registry(request, decisions)
        decisions.append(dec_2)
        if not passed and err_resp is not None:
            err_resp.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._record_audit_log(
                AuditLogEntry(
                    request_id=request.request_id,
                    timestamp=err_resp.timestamp,
                    caller_identity=request.caller_identity,
                    tool_name=request.tool_name,
                    tool_args=request.tool_args,
                    status_code=err_resp.status_code,
                    outcome=err_resp.outcome,
                    error_code=err_resp.error_code,
                    message=err_resp.message,
                    step_decisions=[d.model_dump() for d in decisions],
                    latency_ms=err_resp.latency_ms,
                )
            )
            return err_resp

        # Step 3: Model Armor Payload Inspection
        passed, dec_3, err_resp = self._evaluate_step_3_model_armor(request, decisions)
        decisions.append(dec_3)
        if not passed and err_resp is not None:
            err_resp.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._record_audit_log(
                AuditLogEntry(
                    request_id=request.request_id,
                    timestamp=err_resp.timestamp,
                    caller_identity=request.caller_identity,
                    tool_name=request.tool_name,
                    tool_args=request.tool_args,
                    status_code=err_resp.status_code,
                    outcome=err_resp.outcome,
                    error_code=err_resp.error_code,
                    message=err_resp.message,
                    step_decisions=[d.model_dump() for d in decisions],
                    latency_ms=err_resp.latency_ms,
                )
            )
            return err_resp

        # Step 4: IAM Unified Access Policy
        passed, dec_4, err_resp = self._evaluate_step_4_iam(request, decisions)
        decisions.append(dec_4)
        if not passed and err_resp is not None:
            err_resp.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._record_audit_log(
                AuditLogEntry(
                    request_id=request.request_id,
                    timestamp=err_resp.timestamp,
                    caller_identity=request.caller_identity,
                    tool_name=request.tool_name,
                    tool_args=request.tool_args,
                    status_code=err_resp.status_code,
                    outcome=err_resp.outcome,
                    error_code=err_resp.error_code,
                    message=err_resp.message,
                    step_decisions=[d.model_dump() for d in decisions],
                    latency_ms=err_resp.latency_ms,
                )
            )
            return err_resp

        # Step 5: Semantic Governance Policy Engine
        passed, dec_5, err_resp = self._evaluate_step_5_sgp(request, decisions)
        decisions.append(dec_5)
        if not passed and err_resp is not None:
            err_resp.latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._record_audit_log(
                AuditLogEntry(
                    request_id=request.request_id,
                    timestamp=err_resp.timestamp,
                    caller_identity=request.caller_identity,
                    tool_name=request.tool_name,
                    tool_args=request.tool_args,
                    status_code=err_resp.status_code,
                    outcome=err_resp.outcome,
                    error_code=err_resp.error_code,
                    message=err_resp.message,
                    step_decisions=[d.model_dump() for d in decisions],
                    latency_ms=err_resp.latency_ms,
                )
            )
            return err_resp

        # ----------------------------------------------------------------------
        # All 5 Checks Passed: Route Egress to Target Tool
        # ----------------------------------------------------------------------
        target_tool = self.registered_tools[request.tool_name]
        try:
            tool_output = target_tool(**request.tool_args)
            if not isinstance(tool_output, dict):
                tool_output = {"result": tool_output}
        except Exception as e:
            logger.exception("Underlying tool execution threw an exception")
            tool_output = {
                "status": "ERROR",
                "error_code": "TOOL_EXECUTION_EXCEPTION",
                "message": str(e),
            }

        total_latency = (time.perf_counter() - start_time) * 1000.0

        success_response = GatewayResponse(
            request_id=request.request_id,
            status_code=200,
            outcome="PERMITTED",
            message="Tool invocation successfully evaluated and executed by Agent Gateway.",
            tool_result=tool_output,
            step_decisions=decisions,
            latency_ms=total_latency,
        )

        preview_text = str(tool_output)[:200]
        self._record_audit_log(
            AuditLogEntry(
                request_id=request.request_id,
                timestamp=success_response.timestamp,
                caller_identity=request.caller_identity,
                tool_name=request.tool_name,
                tool_args=request.tool_args,
                status_code=200,
                outcome="PERMITTED",
                message=success_response.message,
                step_decisions=[d.model_dump() for d in decisions],
                latency_ms=total_latency,
                tool_result_preview=preview_text,
            )
        )

        return success_response

    # Convenience method
    def invoke_tool(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        caller_identity: str = "service-123456789012@gcp-sa-aiplatform-re.iam.gserviceaccount.com",
        bearer_token: str = "ya29.c.b0_test_token_valid",
        caller_roles: Optional[List[str]] = None,
        prompt_context: Optional[str] = None,
    ) -> GatewayResponse:
        """Convenience helper to invoke a tool through the governed gateway."""
        req = GatewayRequest(
            tool_name=tool_name,
            tool_args=args or {},
            caller_identity=caller_identity,
            bearer_token=bearer_token,
            caller_roles=caller_roles or ["roles/iap.egressor"],
            prompt_context=prompt_context,
        )
        return self.invoke(req)

    # --------------------------------------------------------------------------
    # ASGI / Starlette HTTP Application Construction
    # --------------------------------------------------------------------------

    def create_asgi_app(self) -> Any:
        """Construct a lightweight ASGI Starlette application representing the Gateway HTTP endpoint."""
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def health_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(
                {
                    "status": "UP",
                    "version": "1.0.0",
                    "service": "Google Cloud Agent Gateway Simulator",
                    "registered_tools": self.list_catalog(),
                    "active_policies": {
                        "identity_check": self.enable_identity_check,
                        "registry_check": self.enable_registry_check,
                        "model_armor": self.enable_model_armor,
                        "iam_check": self.enable_iam_check,
                        "semantic_governance": self.enable_sgp,
                    },
                }
            )

        async def invoke_endpoint(request: Request) -> JSONResponse:
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(
                    {"error": "Invalid JSON body"}, status_code=400
                )

            # Map JSON body to GatewayRequest
            try:
                gw_req = GatewayRequest(**body)
            except Exception as e:
                return JSONResponse(
                    {"error": f"Invalid GatewayRequest schema: {e}"}, status_code=422
                )

            gw_resp = self.invoke(gw_req)
            return JSONResponse(
                gw_resp.model_dump(), status_code=gw_resp.status_code
            )

        async def audit_endpoint(request: Request) -> JSONResponse:
            limit = int(request.query_params.get("limit", 50))
            filter_outcome = request.query_params.get("outcome")
            filter_tool = request.query_params.get("tool")
            logs = self.get_audit_logs(
                limit=limit, filter_outcome=filter_outcome, filter_tool=filter_tool
            )
            stats = self.get_audit_stats()
            return JSONResponse(
                {
                    "stats": stats,
                    "entries": [e.model_dump() for e in logs],
                }
            )

        async def toggle_endpoint(request: Request) -> JSONResponse:
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(
                    {"error": "Invalid JSON body"}, status_code=400
                )

            if "enable_identity_check" in body:
                self.enable_identity_check = bool(body["enable_identity_check"])
            if "enable_registry_check" in body:
                self.enable_registry_check = bool(body["enable_registry_check"])
            if "enable_model_armor" in body:
                self.enable_model_armor = bool(body["enable_model_armor"])
            if "enable_iam_check" in body:
                self.enable_iam_check = bool(body["enable_iam_check"])
            if "enable_sgp" in body:
                self.enable_sgp = bool(body["enable_sgp"])
            if "standard_transfer_limit" in body:
                self.standard_transfer_limit = float(body["standard_transfer_limit"])
            if "max_allowed_risk_score" in body:
                self.max_allowed_risk_score = int(body["max_allowed_risk_score"])

            return JSONResponse(
                {
                    "status": "UPDATED",
                    "active_policies": {
                        "identity_check": self.enable_identity_check,
                        "registry_check": self.enable_registry_check,
                        "model_armor": self.enable_model_armor,
                        "iam_check": self.enable_iam_check,
                        "semantic_governance": self.enable_sgp,
                        "standard_transfer_limit": self.standard_transfer_limit,
                        "max_allowed_risk_score": self.max_allowed_risk_score,
                    },
                }
            )

        routes = [
            Route("/gateway/health", health_endpoint, methods=["GET"]),
            Route("/gateway/invoke", invoke_endpoint, methods=["POST"]),
            Route("/gateway/audit", audit_endpoint, methods=["GET"]),
            Route("/gateway/policies/toggle", toggle_endpoint, methods=["POST"]),
        ]

        return Starlette(routes=routes)


# ==============================================================================
# Factory Function
# ==============================================================================


def create_simulator(
    enable_identity_check: bool = True,
    enable_registry_check: bool = True,
    enable_model_armor: bool = True,
    enable_iam_check: bool = True,
    enable_sgp: bool = True,
    standard_transfer_limit: float = 1000.0,
    max_allowed_risk_score: int = 50,
    policy_dir: Optional[Union[str, Path]] = None,
) -> GatewaySimulator:
    """Instantiate a configured Google Cloud Agent Gateway Simulator."""
    return GatewaySimulator(
        enable_identity_check=enable_identity_check,
        enable_registry_check=enable_registry_check,
        enable_model_armor=enable_model_armor,
        enable_iam_check=enable_iam_check,
        enable_sgp=enable_sgp,
        standard_transfer_limit=standard_transfer_limit,
        max_allowed_risk_score=max_allowed_risk_score,
        policy_dir=policy_dir,
    )
