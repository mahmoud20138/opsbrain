/**
 * OpsBrain Enterprise Organizational Hierarchy & Frameworks UI Application.
 *
 * Coordinates graph engine, inspector, industry blueprints, frameworks,
 * live telemetry simulation, and model export.
 */

import { INDUSTRY_PRESETS } from "./data/models.js";
import { FRAMEWORKS } from "./components/frameworks.js";
import { OrgGraphEngine } from "./graph/engine.js";
import { DepartmentInspector } from "./components/inspector.js";

class OpsBrainApp {
  constructor() {
    this.currentIndustryKey = "tech_saas";
    this.currentData = JSON.parse(JSON.stringify(INDUSTRY_PRESETS[this.currentIndustryKey]));
    this.simulationActive = true;
    this.simulationTimer = null;

    this.initElements();
    this.initGraphEngine();
    this.initInspector();
    this.populateFrameworkDropdown();
    this.populateIndustryDropdown();
    this.bindEvents();
    this.loadIndustry(this.currentIndustryKey);
    this.startLiveSimulation();
  }

  initElements() {
    this.svgEl = document.getElementById("graph-svg");
    this.inspectorEl = document.getElementById("department-inspector");
    this.industrySelect = document.getElementById("industry-select");
    this.layoutSelect = document.getElementById("layout-select");
    this.frameworkSelect = document.getElementById("framework-select");
    this.searchInput = document.getElementById("search-input");
    this.statsDepartments = document.getElementById("stat-departments");
    this.statsHeadcount = document.getElementById("stat-headcount");
    this.statsTouchpoints = document.getElementById("stat-touchpoints");
    this.statsStatus = document.getElementById("stat-health");
    this.blueprintTitle = document.getElementById("blueprint-title");
    this.blueprintDesc = document.getElementById("blueprint-desc");
  }

  initGraphEngine() {
    this.graphEngine = new OrgGraphEngine(this.svgEl, {
      onNodeSelect: (node) => {
        if (node) {
          this.inspector.show(node, this.graphEngine.nodes);
        } else {
          this.inspector.hide();
        }
      },
      onNodeHover: (node) => {
        const tooltip = document.getElementById("graph-tooltip");
        if (!tooltip) return;
        if (node) {
          tooltip.innerHTML = `
            <strong>${node.name}</strong> (${node.code})<br/>
            Division: ${node.division} | Staff: ${node.headcount}<br/>
            Touchpoints: ${(node.touchpoints || []).length} active
          `;
          tooltip.style.display = "block";
        } else {
          tooltip.style.display = "none";
        }
      }
    });
  }

  initInspector() {
    this.inspector = new DepartmentInspector(this.inspectorEl, {
      onDepartmentSelect: (departmentId) => {
        this.graphEngine.selectNode(departmentId);
      }
    });
  }

  populateIndustryDropdown() {
    this.industrySelect.innerHTML = "";
    Object.values(INDUSTRY_PRESETS).forEach(ind => {
      const opt = document.createElement("option");
      opt.value = ind.id;
      opt.textContent = ind.name;
      this.industrySelect.appendChild(opt);
    });

    const customOpt = document.createElement("option");
    customOpt.value = "custom";
    customOpt.textContent = "+ Custom Architecture...";
    this.industrySelect.appendChild(customOpt);
  }

  populateFrameworkDropdown() {
    this.frameworkSelect.innerHTML = `<option value="ALL">All Frameworks (Overview)</option>`;
    Object.values(FRAMEWORKS).forEach(fw => {
      const opt = document.createElement("option");
      opt.value = fw.id;
      opt.textContent = `${fw.badge} - ${fw.name}`;
      this.frameworkSelect.appendChild(opt);
    });
  }

  bindEvents() {
    // Industry selection
    this.industrySelect.addEventListener("change", (e) => {
      if (e.target.value === "custom") {
        this.openCustomModelModal();
      } else {
        this.loadIndustry(e.target.value);
      }
    });

    // Layout selection
    this.layoutSelect.addEventListener("change", (e) => {
      this.graphEngine.setData(this.currentData.departments, e.target.value);
    });

    // Framework filtering
    this.frameworkSelect.addEventListener("change", (e) => {
      this.graphEngine.setFrameworkFilter(e.target.value);
    });

    // Search bar with debouncing
    let debounceTimer;
    this.searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        this.graphEngine.setSearchQuery(e.target.value);
      }, 150);
    });

    // Viewport control buttons
    document.getElementById("btn-zoom-in")?.addEventListener("click", () => this.graphEngine.zoomIn());
    document.getElementById("btn-zoom-out")?.addEventListener("click", () => this.graphEngine.zoomOut());
    document.getElementById("btn-fit-view")?.addEventListener("click", () => this.graphEngine.fitToView());
    document.getElementById("btn-reset-zoom")?.addEventListener("click", () => this.graphEngine.resetZoom());

    // Live Simulation toggle
    const simToggleBtn = document.getElementById("btn-toggle-sim");
    if (simToggleBtn) {
      simToggleBtn.addEventListener("click", () => {
        this.simulationActive = !this.simulationActive;
        simToggleBtn.classList.toggle("active", this.simulationActive);
        simToggleBtn.innerHTML = this.simulationActive 
          ? `<span class="sim-pulse-dot"></span> Live Telemetry: ON` 
          : `<span class="sim-pulse-dot paused"></span> Live Telemetry: PAUSED`;
      });
    }

    // Export Dropdown & actions
    document.getElementById("btn-export-json")?.addEventListener("click", () => this.exportModelJSON());
    document.getElementById("btn-export-svg")?.addEventListener("click", () => this.exportModelSVG());

    // Window Resize -> re-center
    window.addEventListener("resize", () => {
      this.graphEngine.updateMinimap();
    });

    // Tooltip position tracking
    this.svgEl.addEventListener("mousemove", (e) => {
      const tooltip = document.getElementById("graph-tooltip");
      if (tooltip && tooltip.style.display === "block") {
        tooltip.style.left = `${e.clientX + 16}px`;
        tooltip.style.top = `${e.clientY + 16}px`;
      }
    });
  }

  loadIndustry(industryKey) {
    if (!INDUSTRY_PRESETS[industryKey]) return;
    this.currentIndustryKey = industryKey;
    this.currentData = JSON.parse(JSON.stringify(INDUSTRY_PRESETS[industryKey]));

    // Update Header
    if (this.blueprintTitle) this.blueprintTitle.textContent = this.currentData.name;
    if (this.blueprintDesc) this.blueprintDesc.textContent = this.currentData.description;

    // Update Top Stats
    this.updateStats();

    // Close open drawer
    this.inspector.hide();

    // Pass data into graph engine
    this.graphEngine.setData(this.currentData.departments, this.layoutSelect.value);
  }

  updateStats() {
    const depts = this.currentData.departments || [];
    const totalHeadcount = depts.reduce((acc, d) => acc + (d.headcount || 0), 0);
    const totalTouchpoints = depts.reduce((acc, d) => acc + (d.touchpoints ? d.touchpoints.length : 0), 0);
    const criticalCount = depts.filter(d => d.status === "critical").length;
    const warningCount = depts.filter(d => d.status === "warning").length;

    if (this.statsDepartments) this.statsDepartments.textContent = depts.length;
    if (this.statsHeadcount) this.statsHeadcount.textContent = totalHeadcount.toLocaleString();
    if (this.statsTouchpoints) this.statsTouchpoints.textContent = totalTouchpoints;

    if (this.statsStatus) {
      if (criticalCount > 0) {
        this.statsStatus.innerHTML = `<span style="color:#F43F5E">${criticalCount} Critical</span>`;
      } else if (warningCount > 0) {
        this.statsStatus.innerHTML = `<span style="color:#F59E0B">${warningCount} Warning</span>`;
      } else {
        this.statsStatus.innerHTML = `<span style="color:#10B981">Optimal</span>`;
      }
    }
  }

  // =========================================================================
  // Live Telemetry Simulation
  // =========================================================================

  startLiveSimulation() {
    if (this.simulationTimer) clearInterval(this.simulationTimer);

    this.simulationTimer = setInterval(() => {
      if (!this.simulationActive) return;

      // Randomly tweak 1-2 metrics in the active dataset to simulate live telemetry
      const depts = this.currentData.departments || [];
      if (depts.length === 0) return;

      const randomDept = depts[Math.floor(Math.random() * depts.length)];
      if (randomDept && randomDept.touchpoints && randomDept.touchpoints.length > 0) {
        const tp = randomDept.touchpoints[Math.floor(Math.random() * randomDept.touchpoints.length)];
        
        // Slightly vary numeric metric if applicable
        const numMatch = String(tp.value).match(/([\d.]+)/);
        if (numMatch) {
          const baseVal = parseFloat(numMatch[1]);
          const variance = (Math.random() - 0.5) * (baseVal * 0.08);
          const newVal = Math.max(0.1, baseVal + variance);
          tp.value = tp.value.replace(numMatch[1], newVal.toFixed(1));

          // If inspector is open on this department, refresh
          if (this.inspector.currentNode && this.inspector.currentNode.id === randomDept.id) {
            this.inspector.render(randomDept, this.graphEngine.nodes);
          }
        }
      }
    }, 3200);
  }

  // =========================================================================
  // Model Export & Customizer
  // =========================================================================

  exportModelJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.currentData, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `${this.currentIndustryKey}_org_architecture.json`);
    dlAnchor.click();
  }

  exportModelSVG() {
    const svgClone = this.svgEl.cloneNode(true);
    const svgData = new XMLSerializer().serializeToString(svgClone);
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", url);
    dlAnchor.setAttribute("download", `${this.currentIndustryKey}_org_hierarchy.svg`);
    dlAnchor.click();
  }

  openCustomModelModal() {
    const modal = document.getElementById("custom-modal");
    const jsonArea = document.getElementById("custom-json-input");
    if (!modal || !jsonArea) return;

    jsonArea.value = JSON.stringify(this.currentData, null, 2);
    modal.style.display = "flex";

    document.getElementById("btn-modal-close")?.addEventListener("click", () => {
      modal.style.display = "none";
    });

    document.getElementById("btn-modal-apply")?.addEventListener("click", () => {
      try {
        const parsed = JSON.parse(jsonArea.value);
        if (!parsed.departments || !Array.isArray(parsed.departments)) {
          alert("Invalid schema: 'departments' array is required.");
          return;
        }
        this.currentData = parsed;
        this.currentIndustryKey = "custom";
        if (this.blueprintTitle) this.blueprintTitle.textContent = parsed.name || "Custom Enterprise Model";
        if (this.blueprintDesc) this.blueprintDesc.textContent = parsed.description || "User-defined custom hierarchy.";
        this.updateStats();
        this.graphEngine.setData(parsed.departments, this.layoutSelect.value);
        modal.style.display = "none";
      } catch (err) {
        alert(`JSON Parse Error: ${err.message}`);
      }
    });
  }
}

// Bootstrap on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.opsBrainApp = new OpsBrainApp();
});
