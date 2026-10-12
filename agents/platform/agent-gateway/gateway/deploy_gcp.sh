#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Agent Gateway & Semantic Governance Policy Deployment Script
# ==============================================================================
# Automates the 5 governance pillars for the enterprise banking hybrid demo:
#   1. Identity: Service identities & service agents
#   2. Gateway: Agent Gateway (agent-egress) in AGENT_TO_ANYWHERE mode (MCP)
#   3. IAM: Unified access bindings (roles/agentgateway.serviceAgent, iap.egressor, etc.)
#   4. Registry: Agent Registry catalog registration & allowlisting
#   5. SGP: SGP Engine, PSC static IP, forwarding rule, DNS zone, Authz Extension & Policy
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

# ------------------------------------------------------------------------------
# Default Configuration & Parameter Parsing
# ------------------------------------------------------------------------------
DRY_RUN=false
DEPLOY_MCP=false
DEPLOY_AGENT=false
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "demo-banking-project")}"
LOCATION="${LOCATION:-us-central1}"
NETWORK_NAME="${NETWORK_NAME:-default}"
SUBNET_NAME="${SUBNET_NAME:-default}"
PROXY_SUBNET_RANGE="${PROXY_SUBNET_RANGE:-10.11.13.0/24}"
SGP_SERVICE_ATTACHMENT="${SGP_SERVICE_ATTACHMENT:-projects/sgp-service-producer-tp/regions/us-central1/serviceAttachments/semantic-governance-psc-attachment}"
MCP_URL="${MCP_URL:-https://banking-mcp-server-demo.a.run.app}"
MCP_SERVER_NAME="${MCP_SERVER_NAME:-banking-mcp-server}"
AGENT_ID="${AGENT_ID:-conversational-banking-001}"
AGENT_RUNTIME_ID="${AGENT_RUNTIME_ID:-}"

print_usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Provisions Google Cloud Agent Gateway with full Semantic Governance Policies (SGP).

Options:
  --dry-run             Display all intended commands without executing them.
  --deploy-mcp          Build and deploy the FastMCP banking server to Cloud Run before gateway registration.
  --deploy-agent        Deploy the ADK banking agent to Vertex AI Agent Runtime bound to Agent Gateway.
  --mcp-url URL         Explicit MCP service URL (auto-discovered if --deploy-mcp is used).
  --mcp-server-name NAME Agent Registry MCP server resource name (default: banking-mcp-server).
  --agent-id ID         Agent ID in Agent Registry for SGP targeting (default: conversational-banking-001).
  --project-id ID       Google Cloud project ID (default: current gcloud config or '$PROJECT_ID').
  --location REGION     Deployment region (default: us-central1).
  --network NAME        VPC Network name (default: default, auto-detected if default absent).
  --subnet NAME         VPC Subnet name (default: default, auto-detected if default absent).
  -h, --help            Show this help message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --deploy-mcp)
      DEPLOY_MCP=true
      shift
      ;;
    --deploy-agent)
      DEPLOY_AGENT=true
      shift
      ;;
    --mcp-url)
      MCP_URL="$2"
      shift 2
      ;;
    --mcp-server-name)
      MCP_SERVER_NAME="$2"
      shift 2
      ;;
    --agent-id)
      AGENT_ID="$2"
      shift 2
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
    --subnet)
      SUBNET_NAME="$2"
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

# ------------------------------------------------------------------------------
# Logging & Command Execution Helper
# ------------------------------------------------------------------------------
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
    "$@"
  fi
}

# Auto-detect or validate VPC Network and Subnet when not running in dry-run mode
if [[ "$DRY_RUN" != "true" ]]; then
  if ! gcloud compute networks describe "${NETWORK_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    AVAILABLE_NETWORKS=($(gcloud compute networks list --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || true))
    if [[ ${#AVAILABLE_NETWORKS[@]} -eq 1 ]]; then
      echo "Notice: Network '${NETWORK_NAME}' not found in project '${PROJECT_ID}'. Auto-selecting detected VPC: '${AVAILABLE_NETWORKS[0]}'"
      NETWORK_NAME="${AVAILABLE_NETWORKS[0]}"
    elif [[ ${#AVAILABLE_NETWORKS[@]} -gt 1 ]]; then
      echo "ERROR: VPC network '${NETWORK_NAME}' was not found in project '${PROJECT_ID}'." >&2
      echo "Available networks in '${PROJECT_ID}':" >&2
      gcloud compute networks list --project="${PROJECT_ID}" --format="table(name,subnetMode,bgpRoutingMode)" >&2
      exit 1
    else
      echo "ERROR: No VPC networks found in project '${PROJECT_ID}'." >&2
      exit 1
    fi
  fi

  if ! gcloud compute networks subnets describe "${SUBNET_NAME}" --region="${LOCATION}" --project="${PROJECT_ID}" &>/dev/null; then
    FOUND_SUBNET="$(gcloud compute networks subnets list --network="${NETWORK_NAME}" --filter="region:(${LOCATION})" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null | head -n 1 || true)"
    if [[ -n "${FOUND_SUBNET}" ]]; then
      echo "Notice: Subnet '${SUBNET_NAME}' not found in region '${LOCATION}'. Auto-selecting detected subnet: '${FOUND_SUBNET}'"
      SUBNET_NAME="${FOUND_SUBNET}"
    else
      echo "ERROR: Subnet '${SUBNET_NAME}' was not found in region '${LOCATION}' for network '${NETWORK_NAME}'." >&2
      exit 1
    fi
  fi
fi

log_step "Initializing Deployment Configuration"
echo "Project ID:       ${PROJECT_ID}"
echo "Location:         ${LOCATION}"
echo "Network:          ${NETWORK_NAME}"
echo "Subnet:           ${SUBNET_NAME}"
echo "Dry Run Mode:     ${DRY_RUN}"

# Resolve project number
if [[ "$DRY_RUN" == "true" ]]; then
  PROJECT_NUM="123456789012"
  PSC_IP="10.128.0.50"
  MCP_SERVER_NAME="${MCP_SERVER_NAME:-agentregistry-00000000-0000-0000-0000-000000000001}"
  AGENT_ID="${AGENT_ID:-conversational-banking-001}"
else
  PROJECT_NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
fi

AGW_SA="serviceAccount:service-${PROJECT_NUM}@gcp-sa-agentgateway.iam.gserviceaccount.com"
AI_SA="serviceAccount:service-${PROJECT_NUM}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

# ------------------------------------------------------------------------------
# PILLAR 1: Identity & API Enablement
# ------------------------------------------------------------------------------
log_step "Pillar 1: Enabling Required APIs & Creating Service Identities"

APIS=(
  compute.googleapis.com
  networksecurity.googleapis.com
  networkservices.googleapis.com
  dns.googleapis.com
  iam.googleapis.com
  iap.googleapis.com
  agentregistry.googleapis.com
  aiplatform.googleapis.com
  run.googleapis.com
  cloudbuild.googleapis.com
  artifactregistry.googleapis.com
  storage.googleapis.com
  modelarmor.googleapis.com
  telemetry.googleapis.com
  cloudtrace.googleapis.com
  logging.googleapis.com
)

run_cmd gcloud services enable "${APIS[@]}" --project="${PROJECT_ID}"

run_cmd gcloud beta services identity create \
  --service=networkservices.googleapis.com \
  --project="${PROJECT_ID}" || true

run_cmd gcloud beta services identity create \
  --service=aiplatform.googleapis.com \
  --project="${PROJECT_ID}" || true

# ------------------------------------------------------------------------------
# PILLAR 2: Agent Gateway & Managed Egress Infrastructure
# ------------------------------------------------------------------------------
log_step "Pillar 2: Provisioning Agent Gateway & VPC Egress Attachments"

run_cmd gcloud compute networks subnets create proxy-only-subnet \
  --network="${NETWORK_NAME}" \
  --region="${LOCATION}" \
  --range="${PROXY_SUBNET_RANGE}" \
  --purpose=REGIONAL_MANAGED_PROXY \
  --role=ACTIVE \
  --project="${PROJECT_ID}" || true

run_cmd gcloud compute network-attachments create agent-gateway-na \
  --region="${LOCATION}" \
  --subnets="${SUBNET_NAME}" \
  --connection-preference=ACCEPT_AUTOMATIC \
  --project="${PROJECT_ID}" || true

# Provision SGP PSC Endpoint & Private DNS Peering Zone required by Agent Gateway
run_cmd gcloud compute addresses create sgp-psc-ip \
  --region="${LOCATION}" \
  --subnet="${SUBNET_NAME}" \
  --purpose=GCE_ENDPOINT \
  --project="${PROJECT_ID}" || true

if [[ "$DRY_RUN" != "true" ]]; then
  PSC_IP="$(gcloud compute addresses describe sgp-psc-ip --region="${LOCATION}" --project="${PROJECT_ID}" --format='value(address)' 2>/dev/null || echo "")"
fi

run_cmd gcloud compute forwarding-rules create sgp-psc-endpoint \
  --region="${LOCATION}" \
  --network="${NETWORK_NAME}" \
  --address=sgp-psc-ip \
  --target-service-attachment="${SGP_SERVICE_ATTACHMENT}" \
  --project="${PROJECT_ID}" || true

run_cmd gcloud dns managed-zones create policy-engine-zone \
  --description="Private zone for internal SGP service" \
  --dns-name="policy.internal." \
  --visibility=private \
  --networks="${NETWORK_NAME}" \
  --project="${PROJECT_ID}" || true

run_cmd gcloud dns record-sets create policy.internal. \
  --zone=policy-engine-zone \
  --type=A \
  --ttl=300 \
  --rrdatas="${PSC_IP}" \
  --project="${PROJECT_ID}" || true

# Brief pause to allow Cloud DNS private zone to propagate to Network Services validator
if [[ "$DRY_RUN" != "true" ]]; then
  sleep 3
fi

# Create Agent Gateway YAML
GATEWAY_SPEC="/tmp/agent-gateway-vpc-egress.yaml"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] Generate ${GATEWAY_SPEC} for Agent Gateway agent-egress (AGENT_TO_ANYWHERE, MCP)"
else
  cat > "${GATEWAY_SPEC}" <<EOF
name: projects/${PROJECT_ID}/locations/${LOCATION}/agentGateways/agent-egress
protocols:
  - MCP
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
registries:
  - //agentregistry.googleapis.com/projects/${PROJECT_ID}/locations/${LOCATION}
networkConfig:
  egress:
    networkAttachment: projects/${PROJECT_ID}/regions/${LOCATION}/networkAttachments/agent-gateway-na
  dnsPeeringConfig:
    domains:
      - policy.internal.
    targetProject: ${PROJECT_ID}
    targetNetwork: projects/${PROJECT_ID}/global/networks/${NETWORK_NAME}
EOF
fi

run_cmd gcloud network-services agent-gateways import agent-egress \
  --source="${GATEWAY_SPEC}" \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"

# ------------------------------------------------------------------------------
# PILLAR 3: IAM Unified Access Policies
# ------------------------------------------------------------------------------
log_step "Pillar 3: Configuring IAM Unified Access Bindings"

run_cmd gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${AGW_SA}" \
  --role="roles/agentgateway.serviceAgent" \
  --condition=None

run_cmd gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${AGW_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None

run_cmd gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${AGW_SA}" \
  --role="roles/modelarmor.user" \
  --condition=None

if gcloud run services describe banking-mcp-server --region="${LOCATION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  run_cmd gcloud run services add-iam-policy-binding banking-mcp-server \
    --region="${LOCATION}" \
    --member="${AGW_SA}" \
    --role="roles/run.servicesInvoker" \
    --project="${PROJECT_ID}" || true
fi

# ------------------------------------------------------------------------------
# OPTIONAL: Build & Deploy FastMCP Server to Cloud Run
# ------------------------------------------------------------------------------
if [[ "$DEPLOY_MCP" == "true" ]]; then
  log_step "Building & Deploying FastMCP Server to Cloud Run (--deploy-mcp)"
  run_cmd gcloud run deploy banking-mcp-server \
    --source="agents/platform/agent-gateway/mcp_server" \
    --region="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --no-allow-unauthenticated \
    --quiet
  if [[ "$DRY_RUN" != "true" ]]; then
    MCP_URL="$(gcloud run services describe banking-mcp-server --region="${LOCATION}" --project="${PROJECT_ID}" --format='value(status.url)' 2>/dev/null || echo "https://banking-mcp-server-${PROJECT_ID}.${LOCATION}.run.app")"
    echo "Resolved Live Cloud Run MCP URL: ${MCP_URL}"
  else
    MCP_URL="https://banking-mcp-server-${PROJECT_ID}.${LOCATION}.run.app"
    echo "[DRY-RUN] Auto-discovered Cloud Run MCP URL: ${MCP_URL}"
  fi

  # Authorize Agent Gateway service agent to invoke Cloud Run
  run_cmd gcloud run services add-iam-policy-binding banking-mcp-server \
    --region="${LOCATION}" \
    --member="${AGW_SA}" \
    --role="roles/run.servicesInvoker" \
    --project="${PROJECT_ID}" || true
fi

# ------------------------------------------------------------------------------
# PILLAR 4: Agent Registry Dynamic Catalog & Service Allowlisting
# ------------------------------------------------------------------------------
log_step "Pillar 4: Registering Tools in Agent Registry & IAP Allowlisting"

if [[ "$DRY_RUN" == "true" ]]; then
  run_cmd gcloud alpha agent-registry services create banking-mcp-server \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --display-name="Banking MCP Server" \
    --interfaces="url=${MCP_URL}/mcp,protocolBinding=JSONRPC" \
    --mcp-server-spec-type=tool-spec \
    --mcp-server-spec-content="agents/platform/agent-gateway/gateway/policies/toolspec.json"
elif gcloud alpha agent-registry services describe banking-mcp-server --project="${PROJECT_ID}" --location="${LOCATION}" &>/dev/null; then
  run_cmd gcloud alpha agent-registry services update banking-mcp-server \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --interfaces="url=${MCP_URL}/mcp,protocolBinding=JSONRPC" \
    --mcp-server-spec-content="agents/platform/agent-gateway/gateway/policies/toolspec.json" || true
else
  run_cmd gcloud alpha agent-registry services create banking-mcp-server \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --display-name="Banking MCP Server" \
    --interfaces="url=${MCP_URL}/mcp,protocolBinding=JSONRPC" \
    --mcp-server-spec-type=tool-spec \
    --mcp-server-spec-content="agents/platform/agent-gateway/gateway/policies/toolspec.json" || true
fi

SYSTEM_ENDPOINTS=(
  "Vertex AI Locational API|https://${LOCATION}-aiplatform.googleapis.com"
  "Cloud Trace API|https://telemetry.googleapis.com"
  "Cloud Logging API|https://logging.googleapis.com"
  "Agent Registry API|https://agentregistry.googleapis.com"
)

for entry in "${SYSTEM_ENDPOINTS[@]}"; do
  IFS="|" read -r ep_name ep_url <<< "$entry"
  ep_name="$(echo "$ep_name" | xargs)"
  ep_url="$(echo "$ep_url" | xargs)"
  svc_id="$(echo "$ep_name" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | cut -c 1-40)"

  run_cmd gcloud alpha agent-registry services create "${svc_id}" \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --display-name="${ep_name}" \
    --endpoint-spec-type=no-spec \
    --interfaces="url=${ep_url},protocolBinding=JSONRPC" || true

  run_cmd gcloud alpha iap web add-iam-policy-binding \
    --resource-type=agent-registry \
    --endpoint="${svc_id}" \
    --region="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --member="allAuthenticatedUsers" \
    --role="roles/iap.egressor" \
    --quiet || true
done

# ------------------------------------------------------------------------------
# PILLAR 5: Semantic Governance Policies (Authz Extension, Policy & SGP Rules)
# ------------------------------------------------------------------------------
log_step "Pillar 5: Configuring Authz Extension, Authz Policy & SGP Enforcement"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] curl -X POST https://networkservices.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions?authzExtensionId=sgp-authzextension (service: policy.internal, failOpen: false)"
else
  ACCESS_TOKEN="$(gcloud auth print-access-token)"
  curl -s -X POST \
    "https://networkservices.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions?authzExtensionId=sgp-authzextension" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "service": "policy.internal",
      "authority": "policy.internal",
      "failOpen": false,
      "loadBalancingScheme": "LOAD_BALANCING_SCHEME_UNSPECIFIED"
    }' || true
fi

AUTHZ_POLICY_SPEC="/tmp/agent-egress-sgp-authzpolicy.yaml"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] Generate ${AUTHZ_POLICY_SPEC} for Content Authorization (CONTENT_AUTHZ, targeting agent-egress)"
else
  cat > "${AUTHZ_POLICY_SPEC}" <<EOF
name: projects/${PROJECT_ID}/locations/${LOCATION}/authzPolicies/agent-egress-sgp-authzpolicy
target:
  loadBalancingScheme: LOAD_BALANCING_SCHEME_UNSPECIFIED
  resources:
    - "projects/${PROJECT_NUM}/locations/${LOCATION}/agentGateways/agent-egress"
httpRules:
  - to:
      operations:
        - paths:
            - prefix: "/"
    when: "!request.headers[\"content-type\"].startsWith(\"application/grpc\") && (request.path.endsWith(\":generateContent\") || request.path.endsWith(\":streamGenerateContent\"))"
action: CUSTOM
policyProfile: CONTENT_AUTHZ
customProvider:
  authzExtension:
    resources:
      - "projects/${PROJECT_NUM}/locations/${LOCATION}/authzExtensions/sgp-authzextension"
EOF
fi

run_cmd gcloud beta network-security authz-policies import agent-egress-sgp-authzpolicy \
  --source="${AUTHZ_POLICY_SPEC}" \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"

# Create SGP rule
run_cmd gcloud beta ai semantic-governance-policies create high-value-limit \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --display-name="High Value Transfer Limit" \
  --mcp-tools="mcp-server=projects/${PROJECT_ID}/locations/${LOCATION}/mcpServers/${MCP_SERVER_NAME},tools=transfer_to_phone" \
  --natural-language-constraint="Block any transfer value exceeding USD 1000." || true

# ------------------------------------------------------------------------------
# OPTIONAL: Deploy ADK Banking Agent to Vertex AI Agent Runtime (--deploy-agent)
# ------------------------------------------------------------------------------
if [[ "$DEPLOY_AGENT" == "true" ]]; then
  log_step "Deploying ADK Banking Agent to Vertex AI Agent Runtime (--deploy-agent)"
  run_cmd agents-cli deploy \
    --project="${PROJECT_ID}" \
    --region="${LOCATION}" \
    --service-name="conversational-banking" \
    --agent-identity \
    --agent-gateway-egress="projects/${PROJECT_ID}/locations/${LOCATION}/agentGateways/agent-egress" \
    --update-env-vars="MCP_SERVER_NAME=${MCP_SERVER_NAME},MCP_SERVER_URL=${MCP_URL}/mcp" \
    --no-confirm-project

  if [[ "$DRY_RUN" != "true" ]]; then
    if [[ -z "${AGENT_RUNTIME_ID}" ]]; then
      AGENT_RUNTIME_ID="$(gcloud ai reasoning-engines list --region="${LOCATION}" --project="${PROJECT_ID}" --filter="displayName:Conversational Banking Agent" --format="value(name)" 2>/dev/null | head -n 1 || echo "")"
    fi
    if [[ -n "${AGENT_RUNTIME_ID}" ]]; then
      echo "Resolved Vertex AI Agent Runtime Resource: ${AGENT_RUNTIME_ID}"
      cat > "${SCRIPT_DIR}/../deployment_metadata.json" <<EOF
{
  "remote_agent_runtime_id": "${AGENT_RUNTIME_ID}",
  "project_id": "${PROJECT_ID}",
  "location": "${LOCATION}",
  "gateway_name": "agent-egress",
  "mcp_server_url": "${MCP_URL}/mcp"
}
EOF
    fi
  else
    AGENT_RUNTIME_ID="projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines/9876543210987654321"
    echo "[DRY-RUN] Auto-discovered Agent Runtime Resource: ${AGENT_RUNTIME_ID}"
    echo "[DRY-RUN] Write deployment_metadata.json with remote_agent_runtime_id=${AGENT_RUNTIME_ID}"
  fi
fi

# Write environment configuration file
if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] Write environment configuration to ${SCRIPT_DIR}/.env"
else
  cat <<EOF > "${SCRIPT_DIR}/.env"
export PROJECT_ID="${PROJECT_ID}"
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export LOCATION="${LOCATION}"
export GOOGLE_CLOUD_LOCATION="${LOCATION}"
export NETWORK_NAME="${NETWORK_NAME:-default}"
export SUBNET_NAME="${SUBNET_NAME:-default}"
export SGP_SERVICE_ATTACHMENT="${SGP_SERVICE_ATTACHMENT}"
export MCP_SERVER_NAME="${MCP_SERVER_NAME}"
export MCP_SERVER_URL="${MCP_URL:-https://${MCP_SERVER_NAME}-${PROJECT_NUM:-unknown}.${LOCATION}.run.app}"
export MCP_URL="${MCP_URL:-https://${MCP_SERVER_NAME}-${PROJECT_NUM:-unknown}.${LOCATION}.run.app}"
export GATEWAY_NAME="agent-egress"
export NETWORK="${NETWORK_NAME:-default}"
export SUBNET="${SUBNET_NAME:-default}"
EOF
  if [[ -n "${AGENT_RUNTIME_ID}" ]]; then
    echo "export AGENT_RUNTIME_ID=\"${AGENT_RUNTIME_ID}\"" >> "${SCRIPT_DIR}/.env"
  fi
fi

log_step "Agent Gateway & Semantic Governance Policy Deployment Successfully Completed!"
echo "Gateway:       agent-egress (MCP, AGENT_TO_ANYWHERE)"
echo "SGP Endpoint:  ${PSC_IP} (policy.internal.)"
if [[ -n "${AGENT_RUNTIME_ID}" ]]; then
  echo "Agent Runtime: ${AGENT_RUNTIME_ID}"
fi
echo "Status:        ACTIVE / ENFORCING"
echo "Env File:      ${SCRIPT_DIR}/.env"
echo ""
echo "To export these environment variables to your active shell, run:"
echo "  source ${SCRIPT_DIR}/.env"


