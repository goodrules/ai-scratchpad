/**
 * Google Cloud Agent Gateway — Enterprise Dashboard Frontend Logic
 * Vanilla ES6+ JavaScript, Zero Build Step, Production Quality
 */

// Global Application State
const state = {
  customers: [],
  activeCustomerId: "CUST001",
  activeCustomer: null,
  executionMode: "simulated", // "simulated" | "local_adk" | "agent_runtime"
  agentRuntimeId: "",
  traceSpans: [],
  activeJsonTab: "response", // "response" | "request" | "traces"
  currentGatewayData: null,
  auditPollingInterval: null,
  isSendingChat: false,
};

// ==============================================================================
// DOM Element Selectors
// ==============================================================================

const elements = {
  // Metric Counters
  metricTotal: document.getElementById("metric-total-requests"),
  metricPermitted: document.getElementById("metric-permitted-count"),
  metricBlocked: document.getElementById("metric-blocked-count"),
  metricLatency: document.getElementById("metric-avg-latency"),

  // Header & Execution Mode Controls
  headerModeText: document.getElementById("header-mode-text"),
  headerAdcStatus: document.getElementById("header-adc-status"),
  execModePill: document.getElementById("execution-mode-pill"),
  runtimeConfigBar: document.getElementById("agent-runtime-config-bar"),
  inputRuntimeId: document.getElementById("input-agent-runtime-id"),
  btnApplyRuntimeId: document.getElementById("btn-apply-runtime-id"),
  btnDiscoverRuntimes: document.getElementById("btn-discover-runtimes"),
  selectDiscoveredRuntime: document.getElementById("select-discovered-runtime"),

  // Customer Selector & Profile
  customerSelect: document.getElementById("customer-select"),
  custName: document.getElementById("cust-preview-name"),
  custTier: document.getElementById("cust-preview-tier"),
  custPhone: document.getElementById("cust-preview-phone"),
  custBalance: document.getElementById("cust-preview-balance"),
  custDailyLimit: document.getElementById("cust-preview-daily-limit"),
  custRiskScore: document.getElementById("cust-preview-risk"),

  // Chat
  chatMessages: document.getElementById("chat-messages"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  btnChatClear: document.getElementById("btn-chat-clear"),

  // Waterfall Banner & Steps
  waterfallToolTag: document.getElementById("waterfall-tool-tag"),
  waterfallVerdictBadge: document.getElementById("waterfall-verdict-badge"),
  waterfallReqId: document.getElementById("waterfall-req-id"),
  waterfallLatency: document.getElementById("waterfall-latency"),
  waterfallTimestamp: document.getElementById("waterfall-timestamp"),
  step1: document.getElementById("waterfall-step-1"),
  step2: document.getElementById("waterfall-step-2"),
  step3: document.getElementById("waterfall-step-3"),
  step4: document.getElementById("waterfall-step-4"),
  step5: document.getElementById("waterfall-step-5"),

  // Inspection Drawer
  drawerToggle: document.getElementById("drawer-toggle"),
  drawerBody: document.getElementById("drawer-body"),
  tabReq: document.getElementById("tab-view-request"),
  tabResp: document.getElementById("tab-view-response"),
  tabTraces: document.getElementById("tab-view-traces"),
  btnSyncTraces: document.getElementById("btn-sync-traces"),
  jsonCode: document.getElementById("json-viewer-content"),
  btnCopyJson: document.getElementById("btn-copy-json"),

  // Policy Toggles & Sliders
  toggleIdentity: document.getElementById("toggle-identity"),
  toggleRegistry: document.getElementById("toggle-registry"),
  toggleModelArmor: document.getElementById("toggle-model-armor"),
  toggleIam: document.getElementById("toggle-iam"),
  toggleSgp: document.getElementById("toggle-sgp"),
  sliderAmlLimit: document.getElementById("slider-aml-limit"),
  displayAmlLimit: document.getElementById("display-aml-limit"),
  sliderDailyLimit: document.getElementById("slider-daily-limit"),
  displayDailyLimit: document.getElementById("display-daily-limit"),
  sliderRiskScore: document.getElementById("slider-risk-score"),
  displayRiskScore: document.getElementById("display-risk-score"),

  // Audit Logs & Reset
  auditFeed: document.getElementById("audit-log-feed"),
  btnHeaderReset: document.getElementById("btn-header-reset"),
  btnCardReset: document.getElementById("btn-card-reset"),
  toastContainer: document.getElementById("toast-container"),
};

// ==============================================================================
// Utility Functions
// ==============================================================================

function formatCurrency(val) {
  const num = typeof val === "number" ? val : parseFloat(val || 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(num);
}

function updateSliderFill(sliderEl) {
  if (!sliderEl) return;
  const min = parseFloat(sliderEl.min || 0);
  const max = parseFloat(sliderEl.max || 100);
  const val = parseFloat(sliderEl.value || 0);
  const pct = Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100));
  sliderEl.style.setProperty("--slider-pct", `${pct}%`);
}

function updateAllSliderFills() {
  [elements.sliderAmlLimit, elements.sliderDailyLimit, elements.sliderRiskScore].forEach(updateSliderFill);
}

function showToast(message, type = "info") {
  if (!elements.toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ==============================================================================
// Customer Profile Management
// ==============================================================================

async function loadCustomers() {
  try {
    const res = await fetch("/api/customers");
    if (!res.ok) throw new Error("Failed to fetch customers");
    const data = await res.json();
    state.customers = data.customers || [];
    renderCustomerDropdown();
    updateActiveCustomer(state.activeCustomerId);
  } catch (err) {
    console.error("Error loading customers:", err);
  }
}

function renderCustomerDropdown() {
  if (!elements.customerSelect) return;
  elements.customerSelect.innerHTML = "";
  state.customers.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.customer_id;
    opt.textContent = `${c.name} (${c.customer_id}) — ${c.tier} [${formatCurrency(c.balance)}]`;
    elements.customerSelect.appendChild(opt);
  });
  elements.customerSelect.value = state.activeCustomerId;
}

function updateActiveCustomer(customerId) {
  state.activeCustomerId = customerId;
  const cust = state.customers.find((c) => c.customer_id === customerId);
  if (!cust) return;
  state.activeCustomer = cust;

  if (elements.custName) elements.custName.textContent = cust.name;
  if (elements.custPhone) elements.custPhone.textContent = `Phone: ${cust.phone}`;
  if (elements.custBalance) elements.custBalance.textContent = formatCurrency(cust.balance);
  if (elements.custDailyLimit) elements.custDailyLimit.textContent = formatCurrency(cust.daily_limit);

  // Tier badge styling
  if (elements.custTier) {
    elements.custTier.textContent = cust.tier;
    elements.custTier.className = "cust-badge-tier " + (
      cust.tier === "PREMIUM_VIP" ? "tier-vip" :
      cust.tier === "CORPORATE_TREASURY" ? "tier-corporate" : "tier-standard"
    );
  }

  // Risk score styling
  if (elements.custRiskScore) {
    const risk = cust.risk_score || 0;
    elements.custRiskScore.textContent = `${risk} / 100`;
    elements.custRiskScore.className = "cust-stat-val " + (
      risk > 50 ? "risk-high" : risk > 25 ? "risk-warning" : "risk-safe"
    );
  }
}

// ==============================================================================
// Conversational Banking Assistant (Panel 1)
// ==============================================================================

function appendChatMessage(sender, text, isBlocked = false) {
  if (!elements.chatMessages) return;

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender} ${isBlocked ? "blocked" : ""}`;

  const senderTag = document.createElement("div");
  senderTag.className = "chat-sender-tag";
  senderTag.textContent = sender === "user" ? "You (Client)" : "Governed Banking Assistant";
  bubble.appendChild(senderTag);

  const textNode = document.createElement("div");
  // Simple markdown formatting (bold, backticks, line breaks)
  let formatted = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
  textNode.innerHTML = formatted;
  bubble.appendChild(textNode);

  elements.chatMessages.appendChild(bubble);
  if (elements.chatMessages.children.length > 1) {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  } else {
    elements.chatMessages.scrollTop = 0;
  }
}

async function sendChatTurn(messageText, scenario = null) {
  if (state.isSendingChat) return;
  state.isSendingChat = true;

  appendChatMessage("user", messageText);

  try {
    const runtimeOverride = elements.inputRuntimeId ? elements.inputRuntimeId.value.trim() : "";
    const stdLimit = elements.sliderAmlLimit ? parseFloat(elements.sliderAmlLimit.value) : undefined;
    const dailyLimit = elements.sliderDailyLimit ? parseFloat(elements.sliderDailyLimit.value) : undefined;
    const payload = {
      message: messageText,
      customer_id: state.activeCustomerId,
      scenario: scenario,
      execution_mode: state.executionMode || "simulated",
      agent_runtime_id: runtimeOverride || state.agentRuntimeId || undefined,
      standard_transfer_limit: stdLimit,
      daily_velocity_limit: dailyLimit !== undefined && stdLimit !== undefined ? Math.max(dailyLimit, stdLimit) : dailyLimit,
      max_allowed_risk_score: elements.sliderRiskScore ? parseInt(elements.sliderRiskScore.value, 10) : undefined,
    };

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const isBlocked = data.tool_invocation?.gateway_response?.outcome === "BLOCKED";
    appendChatMessage("assistant", data.reply, isBlocked);

    if (Array.isArray(data.trace_spans) && data.trace_spans.length > 0) {
      state.traceSpans = data.trace_spans;
    } else if (Array.isArray(data.tool_invocation?.trace_spans)) {
      state.traceSpans = data.tool_invocation.trace_spans;
    }

    // Update real-time waterfall if tool was invoked
    if (data.tool_invocation) {
      renderWaterfall(data.tool_invocation);
    } else {
      updateJsonViewer();
    }

    // Refresh customers and audit logs
    await loadCustomers();
    await loadAuditFeed();
  } catch (err) {
    appendChatMessage("assistant", `⚠️ Error processing request: ${err.message}`, true);
  } finally {
    state.isSendingChat = false;
  }
}

// ==============================================================================
// Real-Time 5-Pillar Governance Waterfall (Panel 2)
// ==============================================================================

function renderWaterfall(toolInvocation) {
  state.currentGatewayData = toolInvocation;
  if (Array.isArray(toolInvocation.trace_spans) && toolInvocation.trace_spans.length > 0) {
    state.traceSpans = toolInvocation.trace_spans;
  }
  const gwReq = toolInvocation.gateway_request || {};
  const gwResp = toolInvocation.gateway_response || {};
  const decisions = gwResp.step_decisions || [];

  // Update Overview Banner
  if (elements.waterfallToolTag) {
    elements.waterfallToolTag.textContent = `Tool: ${toolInvocation.tool_name || gwReq.tool_name || "N/A"}`;
  }

  const isPermitted = gwResp.outcome === "PERMITTED";
  if (elements.waterfallVerdictBadge) {
    elements.waterfallVerdictBadge.textContent = isPermitted ? "PERMITTED (200 OK)" : `BLOCKED (${gwResp.status_code || 403})`;
    elements.waterfallVerdictBadge.className = `verdict-badge ${isPermitted ? "permitted" : "blocked"}`;
  }

  if (elements.waterfallReqId) {
    elements.waterfallReqId.textContent = gwResp.request_id || "req-00000";
  }
  if (elements.waterfallLatency) {
    elements.waterfallLatency.textContent = `${(gwResp.latency_ms || 0).toFixed(2)} ms`;
  }
  if (elements.waterfallTimestamp) {
    const d = new Date(gwResp.timestamp || Date.now());
    elements.waterfallTimestamp.textContent = d.toLocaleTimeString();
  }

  // Map step decisions to the 5 visual cards
  const stepMap = {
    step_1_identity: elements.step1,
    step_2_registry: elements.step2,
    step_3_model_armor: elements.step3,
    step_4_iam: elements.step4,
    step_5_sgp: elements.step5,
  };

  // Reset all steps to skipped initially
  Object.values(stepMap).forEach((card) => {
    if (!card) return;
    card.className = "step-card skipped";
    const pill = card.querySelector(".step-status-pill");
    const lat = card.querySelector(".step-latency");
    const det = card.querySelector(".step-details");
    if (pill) { pill.textContent = "SKIPPED"; pill.className = "step-status-pill skipped"; }
    if (lat) lat.textContent = "-";
    if (det) det.textContent = "Step not evaluated (prior step halted execution).";
  });

  // Populate evaluated decisions
  decisions.forEach((dec) => {
    const card = stepMap[dec.step];
    if (!card) return;

    const statusLower = dec.status.toLowerCase();
    card.className = `step-card ${statusLower}`;

    const pill = card.querySelector(".step-status-pill");
    if (pill) {
      pill.textContent = dec.status;
      pill.className = `step-status-pill ${statusLower}`;
    }

    const lat = card.querySelector(".step-latency");
    if (lat) {
      lat.textContent = `${(dec.latency_ms || 0).toFixed(2)} ms`;
    }

    const det = card.querySelector(".step-details");
    if (det) {
      let detailHtml = "";
      if (dec.rule_id) {
        detailHtml += `<span class="step-rule-tag">${dec.rule_id}</span> `;
      }
      detailHtml += dec.details || "";
      det.innerHTML = detailHtml;
    }
  });

  // Update inspection drawer JSON view
  updateJsonViewer();
}

function updateJsonViewer() {
  if (!elements.jsonCode) return;
  if (state.activeJsonTab === "traces") {
    const tracePayload = {
      execution_mode: state.executionMode,
      agent_runtime_id: state.agentRuntimeId || null,
      span_count: state.traceSpans.length,
      spans: state.traceSpans,
    };
    elements.jsonCode.textContent = JSON.stringify(tracePayload, null, 2);
    return;
  }
  if (!state.currentGatewayData) return;
  const content = state.activeJsonTab === "request"
    ? state.currentGatewayData.gateway_request
    : state.currentGatewayData.gateway_response;
  elements.jsonCode.textContent = JSON.stringify(content, null, 2);
}

// ==============================================================================
// Policy Controls & Live Audit Log Feed (Panel 3)
// ==============================================================================

async function loadPolicies() {
  try {
    const res = await fetch("/api/policies");
    if (!res.ok) return;
    const data = await res.json();
    const p = data.active_policies || {};

    if (elements.toggleIdentity) elements.toggleIdentity.checked = !!p.identity_check;
    if (elements.toggleRegistry) elements.toggleRegistry.checked = !!p.registry_check;
    if (elements.toggleModelArmor) elements.toggleModelArmor.checked = !!p.model_armor;
    if (elements.toggleIam) elements.toggleIam.checked = !!p.iam_check;
    if (elements.toggleSgp) elements.toggleSgp.checked = !!p.semantic_governance;

    if (elements.sliderAmlLimit && p.standard_transfer_limit) {
      elements.sliderAmlLimit.value = p.standard_transfer_limit;
      if (elements.displayAmlLimit) {
        elements.displayAmlLimit.textContent = formatCurrency(p.standard_transfer_limit);
      }
    }

    if (elements.sliderDailyLimit && p.daily_velocity_limit) {
      elements.sliderDailyLimit.value = p.daily_velocity_limit;
      if (elements.displayDailyLimit) {
        elements.displayDailyLimit.textContent = formatCurrency(p.daily_velocity_limit);
      }
    }

    if (elements.sliderRiskScore && p.max_allowed_risk_score) {
      elements.sliderRiskScore.value = p.max_allowed_risk_score;
      if (elements.displayRiskScore) {
        elements.displayRiskScore.textContent = p.max_allowed_risk_score;
      }
    }
    updateAllSliderFills();
  } catch (err) {
    console.error("Error loading policies:", err);
  }
}

async function updatePolicyToggle(key, value) {
  try {
    const payload = { [key]: value };
    const res = await fetch("/api/policies/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Toggle update failed");
    const data = await res.json();
    const p = data.active_policies || {};
    if (elements.sliderDailyLimit && p.daily_velocity_limit) {
      elements.sliderDailyLimit.value = p.daily_velocity_limit;
      if (elements.displayDailyLimit) {
        elements.displayDailyLimit.textContent = formatCurrency(p.daily_velocity_limit);
      }
    }
    if (key === "standard_transfer_limit" || key === "daily_velocity_limit") {
      await loadCustomers();
    }
    showToast(`Policy updated: ${key} = ${value}`, "success");
  } catch (err) {
    showToast(`Error updating policy: ${err.message}`, "error");
  }
}

async function loadAuditFeed() {
  try {
    const res = await fetch("/api/audit?limit=25");
    if (!res.ok) return;
    const data = await res.json();

    // Update Metric Ribbon Counters
    const stats = data.stats || {};
    if (elements.metricTotal) elements.metricTotal.textContent = stats.total_requests || 0;
    if (elements.metricPermitted) elements.metricPermitted.textContent = stats.permitted || 0;
    if (elements.metricBlocked) elements.metricBlocked.textContent = stats.blocked || 0;
    if (elements.metricLatency) {
      elements.metricLatency.textContent = `${(stats.average_latency_ms || 0).toFixed(2)} ms`;
    }

    // Render Audit Cards
    if (!elements.auditFeed) return;
    elements.auditFeed.innerHTML = "";
    const entries = data.entries || [];

    if (entries.length === 0) {
      elements.auditFeed.innerHTML = '<div class="audit-empty-state">No audit events yet. Try a 1-click scenario!</div>';
      return;
    }

    // Show newest first
    [...entries].reverse().forEach((entry) => {
      const card = document.createElement("div");
      const isPermitted = entry.outcome === "PERMITTED";
      card.className = `audit-card ${isPermitted ? "permitted" : "blocked"}`;
      const timeStr = new Date(entry.timestamp).toLocaleTimeString();

      let citationHtml = "";
      if (!isPermitted && entry.error_code) {
        citationHtml = `<div class="audit-citation">Blocked by ${entry.error_code}</div>`;
      }

      card.innerHTML = `
        <div class="audit-card-top audit-cell-tool">
          <span class="audit-tool-name">${entry.tool_name}</span>
          ${citationHtml}
        </div>
        <div class="audit-cell-verdict">
          <span class="audit-outcome-badge ${isPermitted ? "permitted" : "blocked"}">${entry.outcome}</span>
        </div>
        <div class="audit-card-meta audit-cell-meta">
          <span class="audit-time">${timeStr}</span>
          <span class="audit-lat">${entry.latency_ms.toFixed(2)} ms</span>
        </div>
      `;

      // Clicking an audit entry reconstructs its waterfall inspection!
      card.addEventListener("click", () => {
        renderWaterfall({
          tool_name: entry.tool_name,
          gateway_request: {
            request_id: entry.request_id,
            tool_name: entry.tool_name,
            tool_args: entry.tool_args,
            caller_identity: entry.caller_identity,
            timestamp: entry.timestamp,
          },
          gateway_response: {
            request_id: entry.request_id,
            status_code: entry.status_code,
            outcome: entry.outcome,
            error_code: entry.error_code,
            message: entry.message,
            latency_ms: entry.latency_ms,
            timestamp: entry.timestamp,
            step_decisions: entry.step_decisions,
            tool_result: entry.tool_result_preview ? { preview: entry.tool_result_preview } : null,
          },
        });
        showToast(`Inspecting event ${entry.request_id}`, "info");
      });

      elements.auditFeed.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading audit logs:", err);
  }
}

async function resetAllState() {
  if (!confirm("Reset database state and clear all audit logs?")) return;
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) throw new Error("Reset failed");
    showToast("Database restored and audit records cleared", "success");

    // Reset Chat messages
    if (elements.chatMessages) {
      elements.chatMessages.innerHTML = "";
    }
    appendChatMessage(
      "assistant",
      "Hello! Welcome to Enterprise Banking. Synthetic ledger balances have been restored to baseline.\n\n" +
      "What would you like to do?\n1. Check balance\n2. Transfer funds\n3. Bill payment\n4. Transaction history"
    );

    await loadPolicies();
    await loadCustomers();
    await loadAuditFeed();
  } catch (err) {
    showToast(`Reset error: ${err.message}`, "error");
  }
}

// ==============================================================================
// Event Listeners Initialization
// ==============================================================================

function setupEventListeners() {
  // Customer selection change
  if (elements.customerSelect) {
    elements.customerSelect.addEventListener("change", (e) => {
      updateActiveCustomer(e.target.value);
      sendChatTurn("Safe Balance & Menu", "safe_balance");
    });
  }

  // 1-Click Scenario Buttons
  document.querySelectorAll("[data-scenario]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const scenario = btn.getAttribute("data-scenario");
      const label = btn.querySelector(".scenario-name")?.textContent.trim() || scenario;

      // Handle special scenario setup (e.g. CUST008 for watchlist)
      if (scenario === "sgp_aml_watchlist") {
        if (elements.customerSelect) {
          elements.customerSelect.value = "CUST008";
        }
        updateActiveCustomer("CUST008");
      }

      sendChatTurn(label, scenario);
    });
  });

  // Chat form submit
  if (elements.chatForm) {
    elements.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const txt = (elements.chatInput.value || "").trim();
      if (!txt) return;
      elements.chatInput.value = "";
      sendChatTurn(txt);
    });
  }

  // Clear chat button
  if (elements.btnChatClear) {
    elements.btnChatClear.addEventListener("click", () => {
      if (elements.chatMessages) elements.chatMessages.innerHTML = "";
      appendChatMessage(
        "assistant",
        "Chat history cleared. How may I assist you today?\n\n1. Check balance\n2. Transfer funds\n3. Bill payment\n4. Transaction history"
      );
    });
  }

  // Drawer Toggle
  if (elements.drawerToggle && elements.drawerBody) {
    elements.drawerToggle.addEventListener("click", () => {
      const isHidden = elements.drawerBody.style.display === "none";
      elements.drawerBody.style.display = isHidden ? "block" : "none";
    });
  }

  // Inspection Drawer Tabs
  const activateDrawerTab = (tabName) => {
    state.activeJsonTab = tabName;
    if (elements.tabResp) elements.tabResp.classList.toggle("active", tabName === "response");
    if (elements.tabReq) elements.tabReq.classList.toggle("active", tabName === "request");
    if (elements.tabTraces) elements.tabTraces.classList.toggle("active", tabName === "traces");
    updateJsonViewer();
  };
  if (elements.tabResp) elements.tabResp.addEventListener("click", () => activateDrawerTab("response"));
  if (elements.tabReq) elements.tabReq.addEventListener("click", () => activateDrawerTab("request"));
  if (elements.tabTraces) elements.tabTraces.addEventListener("click", () => activateDrawerTab("traces"));

  // Sync GCP Cloud Trace & SGP Spans button
  if (elements.btnSyncTraces) {
    elements.btnSyncTraces.addEventListener("click", async () => {
      await syncGcpTraces(true);
      activateDrawerTab("traces");
    });
  }

  // 3-Mode Execution Selector Buttons
  document.querySelectorAll("[data-exec-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-exec-mode") || "simulated";
      setExecutionMode(mode);
    });
  });

  // Agent Runtime Discover & Set buttons
  if (elements.btnDiscoverRuntimes) {
    elements.btnDiscoverRuntimes.addEventListener("click", () => discoverRuntimes(true));
  }
  if (elements.btnApplyRuntimeId) {
    elements.btnApplyRuntimeId.addEventListener("click", () => {
      const val = elements.inputRuntimeId ? elements.inputRuntimeId.value.trim() : "";
      if (val) applyRuntimeId(val);
    });
  }
  if (elements.selectDiscoveredRuntime) {
    elements.selectDiscoveredRuntime.addEventListener("change", (e) => {
      const val = e.target.value;
      if (val) {
        if (elements.inputRuntimeId) elements.inputRuntimeId.value = val;
        applyRuntimeId(val);
      }
    });
  }

  // Copy JSON
  if (elements.btnCopyJson && elements.jsonCode) {
    elements.btnCopyJson.addEventListener("click", () => {
      navigator.clipboard.writeText(elements.jsonCode.textContent || "");
      showToast("JSON copied to clipboard", "success");
    });
  }

  // Policy Toggles
  if (elements.toggleIdentity) {
    elements.toggleIdentity.addEventListener("change", (e) => updatePolicyToggle("enable_identity_check", e.target.checked));
  }
  if (elements.toggleRegistry) {
    elements.toggleRegistry.addEventListener("change", (e) => updatePolicyToggle("enable_registry_check", e.target.checked));
  }
  if (elements.toggleModelArmor) {
    elements.toggleModelArmor.addEventListener("change", (e) => updatePolicyToggle("enable_model_armor", e.target.checked));
  }
  if (elements.toggleIam) {
    elements.toggleIam.addEventListener("change", (e) => updatePolicyToggle("enable_iam_check", e.target.checked));
  }
  if (elements.toggleSgp) {
    elements.toggleSgp.addEventListener("change", (e) => updatePolicyToggle("enable_sgp", e.target.checked));
  }

  // AML Limit Slider (SGP-01)
  let amlDebounceTimer = null;
  if (elements.sliderAmlLimit) {
    elements.sliderAmlLimit.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      if (elements.displayAmlLimit) elements.displayAmlLimit.textContent = formatCurrency(val);
      if (elements.sliderDailyLimit && parseFloat(elements.sliderDailyLimit.value) < val) {
        elements.sliderDailyLimit.value = val;
        if (elements.displayDailyLimit) elements.displayDailyLimit.textContent = formatCurrency(val);
      }
      updateAllSliderFills();
      clearTimeout(amlDebounceTimer);
      amlDebounceTimer = setTimeout(() => {
        updatePolicyToggle("standard_transfer_limit", val);
      }, 150);
    });
    elements.sliderAmlLimit.addEventListener("change", (e) => {
      clearTimeout(amlDebounceTimer);
      updateAllSliderFills();
      updatePolicyToggle("standard_transfer_limit", parseFloat(e.target.value));
    });
  }

  // 24h Daily Velocity Limit Slider (SGP-02)
  let dailyDebounceTimer = null;
  if (elements.sliderDailyLimit) {
    elements.sliderDailyLimit.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      if (elements.displayDailyLimit) elements.displayDailyLimit.textContent = formatCurrency(val);
      updateAllSliderFills();
      clearTimeout(dailyDebounceTimer);
      dailyDebounceTimer = setTimeout(() => {
        updatePolicyToggle("daily_velocity_limit", val);
      }, 150);
    });
    elements.sliderDailyLimit.addEventListener("change", (e) => {
      clearTimeout(dailyDebounceTimer);
      updateAllSliderFills();
      updatePolicyToggle("daily_velocity_limit", parseFloat(e.target.value));
    });
  }

  // Risk Score Slider
  let riskDebounceTimer = null;
  if (elements.sliderRiskScore) {
    elements.sliderRiskScore.addEventListener("input", (e) => {
      const val = parseInt(e.target.value, 10);
      if (elements.displayRiskScore) elements.displayRiskScore.textContent = val;
      updateAllSliderFills();
      clearTimeout(riskDebounceTimer);
      riskDebounceTimer = setTimeout(() => {
        updatePolicyToggle("max_allowed_risk_score", val);
      }, 150);
    });
    elements.sliderRiskScore.addEventListener("change", (e) => {
      clearTimeout(riskDebounceTimer);
      updateAllSliderFills();
      updatePolicyToggle("max_allowed_risk_score", parseInt(e.target.value, 10));
    });
  }

  // Reset buttons
  if (elements.btnHeaderReset) elements.btnHeaderReset.addEventListener("click", resetAllState);
  if (elements.btnCardReset) elements.btnCardReset.addEventListener("click", resetAllState);
}

// ==============================================================================
// Execution Mode, Agent Runtime Discovery & Live Telemetry Sync
// ==============================================================================

function setExecutionMode(mode) {
  state.executionMode = mode;
  document.querySelectorAll("[data-exec-mode]").forEach((btn) => {
    const isTarget = btn.getAttribute("data-exec-mode") === mode;
    btn.classList.toggle("active", isTarget);
  });

  const modeLabels = {
    simulated: { pill: "Simulated (0ms)", header: "Hybrid Local Simulator (In-Process PSC)" },
    local_adk: { pill: "Local ADK Agent", header: "Local ADK Agent (In-Process Runner + Gateway)" },
    agent_runtime: { pill: "Vertex AI Agent Runtime", header: "Vertex AI Agent Runtime (Cloud Trace + SGP)" },
  };
  const info = modeLabels[mode] || modeLabels.simulated;
  if (elements.execModePill) elements.execModePill.textContent = info.pill;
  if (elements.headerModeText) elements.headerModeText.textContent = info.header;

  if (elements.runtimeConfigBar) {
    elements.runtimeConfigBar.style.display = mode === "agent_runtime" ? "block" : "none";
  }
  if (mode === "agent_runtime") {
    discoverRuntimes(false);
  }
  updateJsonViewer();
  showToast(`Execution mode switched to: ${info.pill}`, "info");
}

async function discoverRuntimes(refresh = false) {
  try {
    const res = await fetch(`/api/runtimes?refresh=${refresh ? "true" : "false"}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.active_runtime_id) {
      state.agentRuntimeId = data.active_runtime_id;
      if (elements.inputRuntimeId && !elements.inputRuntimeId.value) {
        elements.inputRuntimeId.value = data.active_runtime_id;
      }
    }
    const list = data.runtimes || [];
    if (elements.selectDiscoveredRuntime) {
      if (list.length > 0) {
        elements.selectDiscoveredRuntime.style.display = "block";
        elements.selectDiscoveredRuntime.innerHTML = "";
        list.forEach((rt) => {
          const opt = document.createElement("option");
          opt.value = rt.resource_name;
          opt.textContent = `${rt.display_name} (${rt.engine_id}) [${rt.source}]`;
          elements.selectDiscoveredRuntime.appendChild(opt);
        });
        if (state.agentRuntimeId) {
          elements.selectDiscoveredRuntime.value = state.agentRuntimeId;
        }
      } else {
        elements.selectDiscoveredRuntime.style.display = "none";
      }
    }
    if (refresh) {
      showToast(`Discovered ${list.length} Agent Runtime(s)`, "success");
    }
  } catch (err) {
    console.warn("Failed to discover runtimes:", err);
  }
}

async function applyRuntimeId(runtimeId) {
  try {
    const res = await fetch("/api/runtimes/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_runtime_id: runtimeId }),
    });
    if (!res.ok) throw new Error("Invalid Agent Runtime ID");
    const data = await res.json();
    state.agentRuntimeId = data.active_runtime_id;
    if (elements.inputRuntimeId) elements.inputRuntimeId.value = data.active_runtime_id;
    updateJsonViewer();
    showToast(`Active Agent Runtime set to: ${data.engine_id}`, "success");
  } catch (err) {
    showToast(`Runtime selection failed: ${err.message}`, "error");
  }
}

async function syncGcpTraces(syncGcp = false) {
  try {
    const res = await fetch(`/api/telemetry/traces?limit=50&sync_gcp=${syncGcp ? "true" : "false"}`);
    if (!res.ok) return;
    const data = await res.json();
    state.traceSpans = data.spans || [];
    if (data.auth && elements.headerAdcStatus) {
      elements.headerAdcStatus.textContent = data.auth.authenticated
        ? `ADC (${data.auth.project_id})`
        : "Local OTel Fallback";
    }
    updateJsonViewer();
    if (syncGcp) {
      showToast(`Synced ${state.traceSpans.length} Cloud Trace / SGP spans (${data.auth?.auth_mode || "local"})`, "success");
    }
  } catch (err) {
    console.warn("Error syncing traces:", err);
  }
}

// ==============================================================================
// Bootstrap
// ==============================================================================

async function loadConfig() {
  try {
    const resp = await fetch("/api/health");
    if (!resp.ok) return;
    const data = await resp.json();
    const projEl = document.getElementById("header-project-id");
    if (projEl && data.project_id) projEl.textContent = data.project_id;
    const locEl = document.getElementById("header-location");
    if (locEl && data.location) locEl.textContent = data.location;
    const modeEl = document.getElementById("header-mode-text");
    if (modeEl && data.backend_mode) modeEl.textContent = data.backend_mode;
    if (data.active_runtime_id) {
      state.agentRuntimeId = data.active_runtime_id;
      if (elements.inputRuntimeId) elements.inputRuntimeId.value = data.active_runtime_id;
    }
    if (data.telemetry_auth && elements.headerAdcStatus) {
      elements.headerAdcStatus.textContent = data.telemetry_auth.authenticated
        ? `ADC Active (${data.telemetry_auth.auth_mode.toUpperCase()})`
        : "Local OTel Fallback";
    }
  } catch (err) {
    console.warn("Failed to load /api/health config:", err);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadConfig();
  await loadCustomers();
  await loadPolicies();
  await loadAuditFeed();
  await syncGcpTraces(false);

  // Initial welcome message
  appendChatMessage(
    "assistant",
    "Hello **Alice Smith**! Welcome to Enterprise Banking.\n" +
    "• **Tier**: STANDARD | **Balance**: `$4,850.00` | **Limit**: `$2,500.00`\n" +
    "• **AML Risk**: `15/100` (Safe) — Select a scenario above or type a request below."
  );

  // Real-time audit log streaming via Server-Sent Events (SSE) with fallback to polling
  startAuditStream();
});

function startAuditStream() {
  if (!window.EventSource) {
    state.auditPollingInterval = setInterval(loadAuditFeed, 3500);
    return;
  }

  try {
    const sse = new EventSource("/api/audit/stream");
    sse.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.telemetry_auth && elements.headerAdcStatus) {
          elements.headerAdcStatus.textContent = payload.telemetry_auth.authenticated
            ? `ADC Active (${payload.telemetry_auth.auth_mode.toUpperCase()})`
            : "Local OTel Fallback";
        }
        if (Array.isArray(payload.trace_spans) && payload.trace_spans.length > 0) {
          state.traceSpans = payload.trace_spans;
          if (state.activeJsonTab === "traces") updateJsonViewer();
        }
        if (payload.stats) {
          const stats = payload.stats;
          if (elements.metricTotal) elements.metricTotal.textContent = stats.total_requests || 0;
          if (elements.metricPermitted) elements.metricPermitted.textContent = stats.permitted || 0;
          if (elements.metricBlocked) elements.metricBlocked.textContent = stats.blocked || 0;
          if (elements.metricLatency) {
            elements.metricLatency.textContent = `${(stats.average_latency_ms || 0).toFixed(2)} ms`;
          }
        }
        loadAuditFeed();
      } catch (e) {
        console.error("SSE parsing error", e);
      }
    };
    sse.onerror = () => {
      sse.close();
      if (!state.auditPollingInterval) {
        state.auditPollingInterval = setInterval(loadAuditFeed, 3500);
      }
    };
  } catch (err) {
    state.auditPollingInterval = setInterval(loadAuditFeed, 3500);
  }
}
