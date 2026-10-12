"""Google Cloud Agent Gateway & Policy Simulator Module.

Provides the high-fidelity 5-step Google Cloud Agent Gateway governance pipeline:
  Step 1: Agent Identity Verification (cryptographic bearer token & SPIFFE/Service Account identity)
  Step 2: Agent Registry Catalog Check (allowlisted MCP tools catalog)
  Step 3: Model Armor Payload Inspection (prompt injection defense & sensitive PII detection)
  Step 4: IAM Unified Access Policy (roles/iap.egressor verification)
  Step 5: Semantic Governance Policy (SGP) Engine (AML limits, risk score watchlist, velocity)
"""

try:
    from .simulator import (
        AuditLogEntry,
        GatewayRequest,
        GatewayResponse,
        GatewaySimulator,
        PolicyDecision,
        create_simulator,
    )
except ImportError:
    from gateway.simulator import (
        AuditLogEntry,
        GatewayRequest,
        GatewayResponse,
        GatewaySimulator,
        PolicyDecision,
        create_simulator,
    )

__all__ = [
    "AuditLogEntry",
    "GatewayRequest",
    "GatewayResponse",
    "GatewaySimulator",
    "PolicyDecision",
    "create_simulator",
]
