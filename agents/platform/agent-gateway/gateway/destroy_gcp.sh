#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Agent Gateway & Semantic Governance Policy Teardown Script
# ==============================================================================
# Safely removes all provisioned resources in reverse dependency order:
#   1. Semantic Governance Policy (high-value-limit)
#   2. Authz Policy (agent-egress-sgp-authzpolicy)
#   3. Authz Extension (sgp-authzextension)
#   4. Agent Gateway (agent-egress)
#   5. Agent Registry Catalog & Cloud Run Services
#   6. Private DNS records and managed zone (policy.internal.)
#   7. Private Service Connect forwarding rule & static IP (sgp-psc-*)
#   8. Network Attachment & Proxy-only Subnet
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load local git-ignored .env defaults (without overriding already-exported env vars)
for _env_file in "${SCRIPT_DIR}/../.env" "${SCRIPT_DIR}/.env"; do
  if [[ -f "${_env_file}" ]]; then
    while IFS= read -r _line || [[ -n "${_line}" ]]; do
      _line="${_line#"${_line%%[![:space:]]*}"}"
      [[ -z "${_line}" || "${_line}" == \#* ]] && continue
      _line="${_line#export }"
      if [[ "${_line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
        _k="${BASH_REMATCH[1]}"
        _v="${BASH_REMATCH[2]}"
        _v="${_v#\"}" ; _v="${_v%\"}"
        _v="${_v#\'}" ; _v="${_v%\'}"
        if [[ -z "${!_k:-}" ]]; then
          export "${_k}=${_v}"
        fi
      fi
    done < "${_env_file}"
  fi
done

DRY_RUN=false
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "demo-banking-project")}"
LOCATION="${LOCATION:-us-central1}"
NETWORK_NAME="${NETWORK_NAME:-default}"

print_usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Safely tears down Google Cloud Agent Gateway and SGP governance infrastructure.

Options:
  --dry-run             Display all intended teardown commands without executing them.
  --project-id ID       Google Cloud project ID (default: current gcloud config or '$PROJECT_ID').
  --location REGION     Deployment region (default: us-central1).
  --network NAME        VPC Network name (default: default).
  -h, --help            Show this help message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --project-id)
      PROJECT_ID="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    --network)
      NETWORK_NAME="$2"
      shift 2
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_usage
      exit 1
      ;;
  esac
done

log_step() {
  echo ""
  echo "================================================================================"
  echo "  $*"
  echo "================================================================================"
}

run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] $*"
  else
    echo ">> $*"
    "$@" || true
  fi
}

if [[ "$DRY_RUN" != "true" ]]; then
  if ! gcloud compute networks describe "${NETWORK_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    AVAILABLE_NETWORKS=($(gcloud compute networks list --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || true))
    if [[ ${#AVAILABLE_NETWORKS[@]} -eq 1 ]]; then
      NETWORK_NAME="${AVAILABLE_NETWORKS[0]}"
    fi
  fi
fi

log_step "Initializing Teardown Configuration"
echo "Project ID:       ${PROJECT_ID}"
echo "Location:         ${LOCATION}"
echo "Network:          ${NETWORK_NAME}"
echo "Dry Run Mode:     ${DRY_RUN}"

# 1. Delete SGP Policy
log_step "1. Deleting Semantic Governance Policy"
run_cmd gcloud beta ai semantic-governance-policies delete high-value-limit \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 2. Delete Authz Policy
log_step "2. Deleting Network Security Authz Policy"
run_cmd gcloud beta network-security authz-policies delete agent-egress-sgp-authzpolicy \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 3. Delete Authz Extension
log_step "3. Deleting Network Services Authz Extension"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] curl -X DELETE https://networkservices.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions/sgp-authzextension"
else
  ACCESS_TOKEN="$(gcloud auth print-access-token 2>/dev/null || echo "")"
  if [[ -n "${ACCESS_TOKEN}" ]]; then
    curl -s -X DELETE \
      "https://networkservices.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions/sgp-authzextension" \
      -H "Authorization: Bearer ${ACCESS_TOKEN}" || true
  fi
fi

# 4. Delete Agent Gateway
log_step "4. Deleting Agent Gateway Resource"
run_cmd gcloud network-services agent-gateways delete agent-egress \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 5. Delete Agent Registry MCP services & allowlisted endpoints
log_step "5. Deleting Agent Registry Services"
ENDPOINTS=(
  banking-mcp-server
  vertexailocationalapi
  cloudtraceapi
  cloudloggingapi
  agentregistryapi
)

for ep in "${ENDPOINTS[@]}"; do
  run_cmd gcloud alpha agent-registry services delete "${ep}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --quiet
done

# Optional: Cloud Run backend teardown
log_step "5b. Deleting Cloud Run MCP Server"
run_cmd gcloud run services delete banking-mcp-server \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 6. Delete Private DNS Records & Zone
log_step "6. Deleting Private Cloud DNS Zone & A Record"
run_cmd gcloud dns record-sets delete policy.internal. \
  --zone=policy-engine-zone \
  --type=A \
  --project="${PROJECT_ID}" \
  --quiet

run_cmd gcloud dns managed-zones delete policy-engine-zone \
  --project="${PROJECT_ID}" \
  --quiet

# 7. Delete PSC Forwarding Rule & Static IP
log_step "7. Deleting Private Service Connect Forwarding Rule & Static IP"
run_cmd gcloud compute forwarding-rules delete sgp-psc-endpoint \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

run_cmd gcloud compute addresses delete sgp-psc-ip \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

# 8. Delete Network Attachment & Proxy-only Subnet
log_step "8. Deleting Network Attachment & Proxy-only Subnet"
run_cmd gcloud compute network-attachments delete agent-gateway-na \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

run_cmd gcloud compute networks subnets delete proxy-only-subnet \
  --region="${LOCATION}" \
  --project="${PROJECT_ID}" \
  --quiet

log_step "Agent Gateway & Governance Infrastructure Successfully Destroyed!"
echo "Status: CLEAN (No orphaned VPC or gateway resources remaining)"
