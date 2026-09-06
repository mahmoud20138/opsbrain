/**
 * OpsBrain Deep-Dive Department & Analytical Touchpoint Inspector.
 *
 * Renders the right-hand slide-over drawer detailing:
 * - Department Overview & Governance
 * - Core Functions & Capabilities
 * - Upstream Inputs & Downstream Outputs
 * - Cross-Team Structural Relationships (with quick-select navigation)
 * - Key Analysis Touchpoints & Live Telemetry
 * - Interactive OpsBrain Agent Trigger Simulation
 */

import { FRAMEWORKS } from "./frameworks.js";

export class DepartmentInspector {
  constructor(containerEl, options = {}) {
    this.container = containerEl;
    this.options = Object.assign({
      onDepartmentSelect: () => {},
      onAgentTrigger: () => {}
    }, options);
    this.currentNode = null;
  }

  show(node, allNodes = []) {
    this.currentNode = node;
    this.container.classList.add("open");
    this.render(node, allNodes);
  }

  hide() {
    this.container.classList.remove("open");
    this.currentNode = null;
  }

  render(node, allNodes = []) {
    if (!node) {
      this.hide();
      return;
    }

    const nodeMap = new Map(allNodes.map(n => [n.id, n]));

    const statusBadge = {
      healthy: `<span class="badge badge-healthy"><span class="pulse-dot green"></span> Healthy</span>`,
      warning: `<span class="badge badge-warning"><span class="pulse-dot yellow"></span> Warning</span>`,
      critical: `<span class="badge badge-critical"><span class="pulse-dot red"></span> Critical Alert</span>`
    }[node.status || "healthy"];

    // Inbound relationships
    const inboundRels = [];
    allNodes.forEach(other => {
      (other.relationships || []).forEach(rel => {
        if (rel.targetId === node.id) {
          inboundRels.push({
            source: other,
            type: rel.type,
            description: rel.description
          });
        }
      });
    });

    const html = `
      <div class="inspector-header">
        <div class="inspector-title-row">
          <div class="inspector-code-pill">${node.code || "OPS"}</div>
          ${statusBadge}
          <button class="inspector-close-btn" id="inspector-close-btn" aria-label="Close Inspector">&times;</button>
        </div>
        <h2 class="inspector-title">${node.name}</h2>
        <div class="inspector-meta-row">
          <span><strong>Division:</strong> ${node.division || "Operations"}</span>
          <span><strong>Head:</strong> ${node.head || "Unassigned"}</span>
          <span><strong>Staff:</strong> ${node.headcount || 0}</span>
          <span><strong>Budget:</strong> ${node.budget || "N/A"}</span>
        </div>
      </div>

      <div class="inspector-body">
        <!-- Section 1: Department Functions -->
        <div class="inspector-section">
          <h3 class="section-heading">Core Functions & Capabilities</h3>
          <ul class="functions-list">
            ${(node.functions || []).map(fn => `<li>${fn}</li>`).join("")}
          </ul>
        </div>

        <!-- Section 2: Inputs & Outputs -->
        <div class="inspector-section">
          <h3 class="section-heading">Operational Hand-offs</h3>
          <div class="io-grid">
            <div class="io-col">
              <span class="io-label">Upstream Inputs</span>
              <ul class="io-list">
                ${(node.inputs || []).map(inp => `<li>${inp}</li>`).join("")}
              </ul>
            </div>
            <div class="io-col">
              <span class="io-label">Downstream Outputs</span>
              <ul class="io-list">
                ${(node.outputs || []).map(out => `<li>${out}</li>`).join("")}
              </ul>
            </div>
          </div>
        </div>

        <!-- Section 3: KPIs -->
        <div class="inspector-section">
          <h3 class="section-heading">Department KPIs</h3>
          <div class="kpi-grid">
            ${(node.kpis || []).map(kpi => `
              <div class="kpi-card">
                <span class="kpi-name">${kpi.name}</span>
                <div class="kpi-values">
                  <span class="kpi-current">${kpi.current}</span>
                  <span class="kpi-target">Target: ${kpi.target}</span>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- Section 4: Cross-Team Relationships -->
        <div class="inspector-section">
          <h3 class="section-heading">Cross-Team Structural Links</h3>
          <div class="relationships-list">
            ${(node.relationships || []).map(rel => {
              const target = nodeMap.get(rel.targetId);
              const targetName = target ? target.name : rel.targetId;
              const typeClass = `rel-badge-${rel.type || 'reports_to'}`;
              return `
                <div class="rel-item" data-target-id="${rel.targetId}">
                  <div class="rel-header">
                    <span class="rel-badge ${typeClass}">${(rel.type || '').replace('_', ' ').toUpperCase()}</span>
                    <span class="rel-arrow">&rarr;</span>
                    <span class="rel-target-link" data-id="${rel.targetId}">${targetName}</span>
                  </div>
                  <div class="rel-desc">${rel.description || "Operational relationship"}</div>
                </div>
              `;
            }).join("")}

            ${inboundRels.length > 0 ? `
              <div class="inbound-divider">Inbound Dependencies</div>
              ${inboundRels.map(ib => `
                <div class="rel-item" data-target-id="${ib.source.id}">
                  <div class="rel-header">
                    <span class="rel-target-link" data-id="${ib.source.id}">${ib.source.name}</span>
                    <span class="rel-arrow">&rarr;</span>
                    <span class="rel-badge rel-badge-${ib.type}">${(ib.type || '').replace('_', ' ').toUpperCase()}</span>
                  </div>
                  <div class="rel-desc">${ib.description || "Inbound dependency"}</div>
                </div>
              `).join("")}
            ` : ""}
          </div>
        </div>

        <!-- Section 5: Analytical Framework Touchpoints -->
        <div class="inspector-section">
          <h3 class="section-heading">Analytical Framework Touchpoints</h3>
          <div class="touchpoints-container">
            ${(node.touchpoints || []).map(tp => {
              const fw = FRAMEWORKS[tp.framework] || { name: tp.framework, color: "#38BDF8" };
              const tpStatus = tp.status || "healthy";
              return `
                <div class="touchpoint-card touchpoint-${tpStatus}">
                  <div class="tp-header">
                    <span class="tp-framework-pill" style="border-color: ${fw.color}; color: ${fw.color}">
                      ${tp.framework}
                    </span>
                    <span class="tp-agent-pill">Agent: ${tp.agent || 'monitor'}</span>
                    <span class="tp-status-pill tp-status-${tpStatus}">${tpStatus.toUpperCase()}</span>
                  </div>
                  <div class="tp-name">${tp.name}</div>
                  <div class="tp-metric-row">
                    <span class="tp-metric-code">${tp.metric}</span>
                    <div class="tp-metric-reading">
                      <span class="tp-val">${tp.value}</span>
                      <span class="tp-thresh">(Threshold: ${tp.threshold})</span>
                    </div>
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        </div>

        <!-- Section 6: Live OpsBrain Simulation Action -->
        <div class="inspector-section simulation-box">
          <h3 class="section-heading">OpsBrain Multi-Agent Diagnostic Probe</h3>
          <p class="sim-explainer">Trigger OpsBrain's agent harness to simulate an operational anomaly, run automated root cause analysis, and draft cross-team remediation.</p>
          <button class="sim-trigger-btn" id="btn-trigger-agent-probe" data-node-id="${node.id}">
            <span class="sim-btn-icon">[*]</span> Run Multi-Agent Triage on ${node.code}
          </button>
          <div class="agent-probe-output" id="agent-probe-output" style="display: none;">
            <div class="probe-spinner" id="probe-spinner">Analyzing operational telemetry...</div>
            <div class="probe-content" id="probe-content"></div>
          </div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;

    // Attach listeners
    this.container.querySelector("#inspector-close-btn")?.addEventListener("click", () => this.hide());

    // Click on related department link
    this.container.querySelectorAll(".rel-target-link").forEach(link => {
      link.addEventListener("click", (e) => {
        const targetId = e.currentTarget.getAttribute("data-id");
        if (targetId) this.options.onDepartmentSelect(targetId);
      });
    });

    // OpsBrain agent trigger button
    const triggerBtn = this.container.querySelector("#btn-trigger-agent-probe");
    if (triggerBtn) {
      triggerBtn.addEventListener("click", () => this.executeAgentSimulation(node));
    }
  }

  async executeAgentSimulation(node) {
    const outputBox = this.container.querySelector("#agent-probe-output");
    const spinner = this.container.querySelector("#probe-spinner");
    const content = this.container.querySelector("#probe-content");

    if (!outputBox || !spinner || !content) return;

    outputBox.style.display = "block";
    spinner.style.display = "block";
    content.innerHTML = "";

    // Simulated 3-stage agent diagnostics
    const steps = [
      { agent: "MonitorAgent", text: `Scanning telemetry metrics for ${node.name} (${node.code})...` },
      { agent: "RCAAgent", text: `Isolating cross-team bottlenecks across ${node.relationships ? node.relationships.length : 0} structural connections...` },
      { agent: "SolverAgent", text: `Evaluating remediation options against ${node.touchpoints ? node.touchpoints.length : 0} analytical framework touchpoints...` },
      { agent: "CoordinatorAgent", text: `Drafting resolution plan and cross-team communication.` }
    ];

    let stepIdx = 0;
    const interval = setInterval(() => {
      if (stepIdx < steps.length) {
        const step = steps[stepIdx];
        const stepDiv = document.createElement("div");
        stepDiv.className = "probe-step-log";
        stepDiv.innerHTML = `<span class="probe-agent-badge">${step.agent}</span> ${step.text}`;
        content.appendChild(stepDiv);
        stepIdx++;
      } else {
        clearInterval(interval);
        spinner.style.display = "none";
        
        // Final resolution report card
        const reportDiv = document.createElement("div");
        reportDiv.className = "probe-final-report";
        const primaryIssue = (node.touchpoints || []).find(t => t.status === "critical" || t.status === "warning") || 
          { name: "Operational Latency", value: "Degraded", framework: "ITIL" };

        reportDiv.innerHTML = `
          <div class="report-heading">[+] OpsBrain Automated Diagnostic Summary</div>
          <div class="report-line"><strong>Primary Root Cause:</strong> Variance in ${primaryIssue.name} (${primaryIssue.value}) exceeding ${primaryIssue.framework} governance baseline.</div>
          <div class="report-line"><strong>Recommended Action:</strong> Auto-rebalance workload across upstream dependencies and activate secondary SLA routing.</div>
          <div class="report-line"><strong>Status:</strong> <span style="color:#10B981">Remediation Plan Generated (Confidence: 96.4%)</span></div>
        `;
        content.appendChild(reportDiv);
      }
    }, 450);
  }
}
