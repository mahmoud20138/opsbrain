/**
 * OpsBrain Enterprise Graph Visualization Engine.
 *
 * Implements SVG-based interactive canvas rendering with:
 * - 4 Layout Algorithms: Hierarchical (Top-Down), Flow (Left-Right), Force-Directed, Concentric Radar
 * - Distinct Edge Types: Structural Hierarchy (solid), Data Flow (animated dashed), SLA Escalation (dotted), Governance (dash-dot)
 * - Multi-Touch / Mouse Pan, Zoom, Fit-to-View, Minimap
 * - Node Hover & Dependency Highlighting
 */

export class OrgGraphEngine {
  constructor(svgElement, options = {}) {
    this.svg = svgElement;
    this.options = Object.assign({
      nodeWidth: 260,
      nodeHeight: 130,
      onNodeSelect: () => {},
      onNodeHover: () => {},
    }, options);

    // Viewport state
    this.scale = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;

    // Graph Data & State
    this.nodes = [];
    this.edges = [];
    this.selectedNodeId = null;
    this.hoveredNodeId = null;
    this.activeFramework = "ALL";
    this.searchQuery = "";
    this.currentLayout = "hierarchical"; // hierarchical, flow, force, concentric

    // Initialize SVG DOM layers
    this.initLayers();
    this.bindEvents();
  }

  initLayers() {
    this.svg.innerHTML = "";
    
    // Defs for markers & filters
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
      <!-- Arrowhead Markers -->
      <marker id="arrow-hierarchy" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748B" />
      </marker>
      <marker id="arrow-dataflow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#06B6D4" />
      </marker>
      <marker id="arrow-escalation" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#F43F5E" />
      </marker>
      <marker id="arrow-governance" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#8B5CF6" />
      </marker>

      <!-- Glow Filters -->
      <filter id="glow-critical" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#F43F5E" flood-opacity="0.6"/>
      </filter>
      <filter id="glow-warning" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#F59E0B" flood-opacity="0.5"/>
      </filter>
      <filter id="glow-selected" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#38BDF8" flood-opacity="0.7"/>
      </filter>
    `;
    this.svg.appendChild(defs);

    // Grid Background layer
    this.gridLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.gridLayer.setAttribute("class", "graph-grid-layer");
    this.svg.appendChild(this.gridLayer);

    // Root Transform Layer (scaled & panned)
    this.worldLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.worldLayer.setAttribute("class", "graph-world-layer");
    this.svg.appendChild(this.worldLayer);

    // Edge Sub-layer
    this.edgesLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.edgesLayer.setAttribute("class", "graph-edges-layer");
    this.worldLayer.appendChild(this.edgesLayer);

    // Nodes Sub-layer
    this.nodesLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.nodesLayer.setAttribute("class", "graph-nodes-layer");
    this.worldLayer.appendChild(this.nodesLayer);
  }

  bindEvents() {
    this.svg.addEventListener("mousedown", (e) => this.onMouseDown(e));
    window.addEventListener("mousemove", (e) => this.onMouseMove(e));
    window.addEventListener("mouseup", () => this.onMouseUp());
    this.svg.addEventListener("wheel", (e) => this.onWheel(e), { passive: false });

    // Touch support for tablets/mobile
    let lastTouchDist = null;
    this.svg.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.dragStartX = e.touches[0].clientX - this.panX;
        this.dragStartY = e.touches[0].clientY - this.panY;
      } else if (e.touches.length === 2) {
        lastTouchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    });

    this.svg.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1 && this.isDragging) {
        this.panX = e.touches[0].clientX - this.dragStartX;
        this.panY = e.touches[0].clientY - this.dragStartY;
        this.updateTransform();
      } else if (e.touches.length === 2 && lastTouchDist) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / lastTouchDist;
        this.zoomAt(factor, (e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2);
        lastTouchDist = dist;
      }
    }, { passive: false });

    this.svg.addEventListener("touchend", () => {
      this.isDragging = false;
      lastTouchDist = null;
    });
  }

  onMouseDown(e) {
    // If clicking on background, initiate pan
    if (e.target === this.svg || e.target.classList.contains("graph-grid-layer") || e.target.tagName === "svg") {
      this.isDragging = true;
      this.dragStartX = e.clientX - this.panX;
      this.dragStartY = e.clientY - this.panY;
      this.svg.style.cursor = "grabbing";
    }
  }

  onMouseMove(e) {
    if (!this.isDragging) return;
    this.panX = e.clientX - this.dragStartX;
    this.panY = e.clientY - this.dragStartY;
    this.updateTransform();
  }

  onMouseUp() {
    this.isDragging = false;
    this.svg.style.cursor = "grab";
  }

  onWheel(e) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    const rect = this.svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    this.zoomAt(zoomFactor, mouseX, mouseY);
  }

  zoomAt(factor, focalX, focalY) {
    const prevScale = this.scale;
    let newScale = prevScale * factor;
    newScale = Math.max(0.2, Math.min(newScale, 3.0));

    this.panX = focalX - (focalX - this.panX) * (newScale / prevScale);
    this.panY = focalY - (focalY - this.panY) * (newScale / prevScale);
    this.scale = newScale;
    this.updateTransform();
  }

  updateTransform() {
    this.worldLayer.setAttribute("transform", `translate(${this.panX}, ${this.panY}) scale(${this.scale})`);
    this.updateMinimap();
  }

  // =========================================================================
  // Graph Loading & Layout Computing
  // =========================================================================

  setData(departments, layoutType = null) {
    if (layoutType) this.currentLayout = layoutType;
    this.departments = departments || [];

    // Parse Nodes
    this.nodes = this.departments.map(d => ({
      ...d,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      width: this.options.nodeWidth,
      height: this.options.nodeHeight
    }));

    // Parse Edges
    this.edges = [];
    const nodeMap = new Map(this.nodes.map(n => [n.id, n]));

    this.nodes.forEach(sourceNode => {
      (sourceNode.relationships || []).forEach(rel => {
        if (nodeMap.has(rel.targetId)) {
          this.edges.push({
            id: `${sourceNode.id}->${rel.targetId}:${rel.type}`,
            sourceId: sourceNode.id,
            targetId: rel.targetId,
            type: rel.type || "reports_to",
            description: rel.description || "",
            source: sourceNode,
            target: nodeMap.get(rel.targetId)
          });
        }
      });
    });

    this.computeLayout();
    this.render();
    this.fitToView();
  }

  computeLayout() {
    switch (this.currentLayout) {
      case "flow":
        this.computeFlowLayout();
        break;
      case "force":
        this.computeForceLayout();
        break;
      case "concentric":
        this.computeConcentricLayout();
        break;
      case "hierarchical":
      default:
        this.computeHierarchicalLayout();
        break;
    }
  }

  computeHierarchicalLayout() {
    // Group by Level (1 = Executive, 2 = VP/Divisional, 3 = Core/Operational)
    const levels = new Map();
    this.nodes.forEach(node => {
      const lvl = node.level || 2;
      if (!levels.has(lvl)) levels.set(lvl, []);
      levels.get(lvl).push(node);
    });

    const sortedLevels = Array.from(levels.keys()).sort((a, b) => a - b);
    const ySpacing = 240;
    const xSpacing = 320;

    sortedLevels.forEach((lvl, rowIdx) => {
      const rowNodes = levels.get(lvl);
      const totalRowWidth = (rowNodes.length - 1) * xSpacing;
      const startX = -totalRowWidth / 2;

      rowNodes.forEach((node, colIdx) => {
        node.x = startX + colIdx * xSpacing;
        node.y = rowIdx * ySpacing + 60;
      });
    });
  }

  computeFlowLayout() {
    // Horizontal Left-to-Right pipeline
    const divisionColumns = {
      "Executive": 0,
      "Product": 1,
      "Engineering": 2,
      "Security": 2,
      "Operations": 3,
      "Supply Chain": 2,
      "Quality": 3,
      "Clinical": 2,
      "Trading": 2,
      "Compliance": 3,
      "Revenue": 4,
      "Technology": 2
    };

    const columns = new Map();
    this.nodes.forEach(node => {
      const col = divisionColumns[node.division] !== undefined ? divisionColumns[node.division] : 2;
      if (!columns.has(col)) columns.set(col, []);
      columns.get(col).push(node);
    });

    const xSpacing = 360;
    const ySpacing = 200;

    Array.from(columns.keys()).sort((a, b) => a - b).forEach((colIdx) => {
      const colNodes = columns.get(colIdx);
      const totalColHeight = (colNodes.length - 1) * ySpacing;
      const startY = -totalColHeight / 2;

      colNodes.forEach((node, rowIdx) => {
        node.x = (colIdx - 2) * xSpacing;
        node.y = startY + rowIdx * ySpacing;
      });
    });
  }

  computeForceLayout() {
    // Simple 80-iteration physics relaxation
    const width = 1000;
    const height = 700;

    // Initial circle distribution
    this.nodes.forEach((node, idx) => {
      const angle = (idx / this.nodes.length) * Math.PI * 2;
      node.x = Math.cos(angle) * 350;
      node.y = Math.sin(angle) * 280;
    });

    for (let iter = 0; iter < 90; iter++) {
      // Repulsion between all node pairs
      for (let i = 0; i < this.nodes.length; i++) {
        for (let j = i + 1; j < this.nodes.length; j++) {
          const n1 = this.nodes[i];
          const n2 = this.nodes[j];
          const dx = n2.x - n1.x || 1;
          const dy = n2.y - n1.y || 1;
          const dist = Math.hypot(dx, dy) || 1;
          const minDist = 320;
          if (dist < minDist) {
            const force = (minDist - dist) / dist * 0.45;
            n1.x -= dx * force;
            n1.y -= dy * force;
            n2.x += dx * force;
            n2.y += dy * force;
          }
        }
      }

      // Spring attraction along relationships
      this.edges.forEach(edge => {
        const dx = edge.target.x - edge.source.x;
        const dy = edge.target.y - edge.source.y;
        const dist = Math.hypot(dx, dy) || 1;
        const targetDist = 260;
        const springForce = (dist - targetDist) * 0.05;
        const fx = (dx / dist) * springForce;
        const fy = (dy / dist) * springForce;

        edge.source.x += fx;
        edge.source.y += fy;
        edge.target.x -= fx;
        edge.target.y -= fy;
      });

      // Weak center gravity
      this.nodes.forEach(node => {
        node.x *= 0.96;
        node.y *= 0.96;
      });
    }
  }

  computeConcentricLayout() {
    const centerNode = this.nodes.find(n => n.level === 1) || this.nodes[0];
    const ring1 = this.nodes.filter(n => n.level === 2 && n !== centerNode);
    const ring2 = this.nodes.filter(n => n.level >= 3 && n !== centerNode);

    if (centerNode) {
      centerNode.x = 0;
      centerNode.y = 0;
    }

    const radius1 = 340;
    ring1.forEach((node, i) => {
      const angle = (i / ring1.length) * Math.PI * 2 - Math.PI / 2;
      node.x = Math.cos(angle) * radius1;
      node.y = Math.sin(angle) * radius1;
    });

    const radius2 = 620;
    ring2.forEach((node, i) => {
      const angle = (i / ring2.length) * Math.PI * 2 - Math.PI / 2;
      node.x = Math.cos(angle) * radius2;
      node.y = Math.sin(angle) * radius2;
    });
  }

  // =========================================================================
  // Rendering
  // =========================================================================

  render() {
    this.renderEdges();
    this.renderNodes();
    this.applyFiltering();
  }

  renderEdges() {
    this.edgesLayer.innerHTML = "";

    this.edges.forEach(edge => {
      const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pathEl.setAttribute("id", `edge-${edge.id}`);
      pathEl.setAttribute("class", `graph-edge edge-type-${edge.type}`);

      // Compute Bezier Curve points
      const d = this.calculateEdgePath(edge.source, edge.target, edge.type);
      pathEl.setAttribute("d", d);

      // Marker according to edge type
      let markerId = "arrow-hierarchy";
      if (edge.type === "data_flow") markerId = "arrow-dataflow";
      else if (edge.type === "sla_escalation") markerId = "arrow-escalation";
      else if (edge.type === "governance") markerId = "arrow-governance";

      pathEl.setAttribute("marker-end", `url(#${markerId})`);

      // Tooltip description
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${edge.type.toUpperCase()}: ${edge.description || "Relationship"}`;
      pathEl.appendChild(title);

      this.edgesLayer.appendChild(pathEl);
    });
  }

  calculateEdgePath(source, target, type) {
    const sx = source.x;
    const sy = source.y;
    const tx = target.x;
    const ty = target.y;

    const dx = tx - sx;
    const dy = ty - sy;

    // Determine connection ports
    let startX = sx;
    let startY = sy;
    let endX = tx;
    let endY = ty;

    if (Math.abs(dy) > Math.abs(dx)) {
      // Vertical flow
      startY = dy > 0 ? sy + source.height / 2 : sy - source.height / 2;
      endY = dy > 0 ? ty - target.height / 2 : ty + target.height / 2;
      const c1y = startY + dy * 0.45;
      const c2y = endY - dy * 0.45;
      return `M ${startX} ${startY} C ${startX} ${c1y}, ${endX} ${c2y}, ${endX} ${endY}`;
    } else {
      // Horizontal flow
      startX = dx > 0 ? sx + source.width / 2 : sx - source.width / 2;
      endX = dx > 0 ? tx - target.width / 2 : tx + target.width / 2;
      const c1x = startX + dx * 0.45;
      const c2x = endX - dx * 0.45;
      return `M ${startX} ${startY} C ${c1x} ${startY}, ${c2x} ${endY}, ${endX} ${endY}`;
    }
  }

  renderNodes() {
    this.nodesLayer.innerHTML = "";

    this.nodes.forEach(node => {
      const nodeGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      nodeGroup.setAttribute("class", `graph-node status-${node.status || "healthy"}`);
      nodeGroup.setAttribute("id", `node-${node.id}`);
      nodeGroup.setAttribute("transform", `translate(${node.x - node.width / 2}, ${node.y - node.height / 2})`);

      // Division Color Accent
      const divisionColors = {
        "Executive": "#8B5CF6", // Violet
        "Engineering": "#06B6D4", // Cyan
        "Operations": "#10B981", // Emerald
        "Security": "#EC4899", // Pink
        "Product": "#F59E0B", // Amber
        "Supply Chain": "#3B82F6", // Blue
        "Quality": "#14B8A6", // Teal
        "Clinical": "#EF4444", // Red
        "Trading": "#6366F1", // Indigo
        "Compliance": "#D97706", // Ochre
        "Technology": "#0EA5E9" // Sky
      };
      const accentColor = divisionColors[node.division] || "#3B82F6";

      // Card Background with border
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("width", node.width);
      rect.setAttribute("height", node.height);
      rect.setAttribute("rx", "12");
      rect.setAttribute("class", "node-card-bg");

      // Division Tag Pill Header
      const tagRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      tagRect.setAttribute("x", "14");
      tagRect.setAttribute("y", "12");
      tagRect.setAttribute("width", "72");
      tagRect.setAttribute("height", "18");
      tagRect.setAttribute("rx", "4");
      tagRect.setAttribute("fill", accentColor);
      tagRect.setAttribute("fill-opacity", "0.18");

      const tagText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      tagText.setAttribute("x", "50");
      tagText.setAttribute("y", "24");
      tagText.setAttribute("class", "node-tag-text");
      tagText.setAttribute("text-anchor", "middle");
      tagText.setAttribute("fill", accentColor);
      tagText.textContent = (node.division || "TEAM").toUpperCase();

      // Status Indicator Dot
      const statusColors = {
        healthy: "#10B981",
        warning: "#F59E0B",
        critical: "#F43F5E"
      };
      const statusColor = statusColors[node.status] || "#10B981";

      const statusDot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      statusDot.setAttribute("cx", node.width - 24);
      statusDot.setAttribute("cy", "21");
      statusDot.setAttribute("r", "5");
      statusDot.setAttribute("fill", statusColor);
      statusDot.setAttribute("class", `status-dot status-dot-${node.status}`);

      // Department Name
      const nameText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      nameText.setAttribute("x", "14");
      nameText.setAttribute("y", "54");
      nameText.setAttribute("class", "node-title-text");
      nameText.textContent = this.truncate(node.name, 26);

      // Department Head / Leader
      const leaderText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      leaderText.setAttribute("x", "14");
      leaderText.setAttribute("y", "74");
      leaderText.setAttribute("class", "node-subtitle-text");
      leaderText.textContent = `Head: ${node.head || "Unassigned"}`;

      // Bottom Meta Strip: Headcount & Touchpoints count
      const metaText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      metaText.setAttribute("x", "14");
      metaText.setAttribute("y", "106");
      metaText.setAttribute("class", "node-meta-text");
      const touchpointsCount = (node.touchpoints || []).length;
      metaText.textContent = `${node.headcount || 0} staff  |  ${touchpointsCount} touchpoint${touchpointsCount === 1 ? '' : 's'}`;

      // Touchpoint Chip Badge
      const badgeRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      badgeRect.setAttribute("x", node.width - 92);
      badgeRect.setAttribute("y", node.height - 34);
      badgeRect.setAttribute("width", "78");
      badgeRect.setAttribute("height", "22");
      badgeRect.setAttribute("rx", "11");
      badgeRect.setAttribute("class", "node-badge-bg");

      const badgeText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      badgeText.setAttribute("x", node.width - 53);
      badgeText.setAttribute("y", node.height - 19);
      badgeText.setAttribute("class", "node-badge-text");
      badgeText.setAttribute("text-anchor", "middle");
      badgeText.textContent = node.code || "OPS";

      // Assemble Group
      nodeGroup.appendChild(rect);
      nodeGroup.appendChild(tagRect);
      nodeGroup.appendChild(tagText);
      nodeGroup.appendChild(statusDot);
      nodeGroup.appendChild(nameText);
      nodeGroup.appendChild(leaderText);
      nodeGroup.appendChild(metaText);
      nodeGroup.appendChild(badgeRect);
      nodeGroup.appendChild(badgeText);

      // Event Handlers
      nodeGroup.addEventListener("click", (e) => {
        e.stopPropagation();
        this.selectNode(node.id);
      });

      nodeGroup.addEventListener("mouseenter", () => {
        this.setHoveredNode(node.id);
      });

      nodeGroup.addEventListener("mouseleave", () => {
        this.setHoveredNode(null);
      });

      this.nodesLayer.appendChild(nodeGroup);
    });
  }

  // =========================================================================
  // Interactivity & Highlighting
  // =========================================================================

  selectNode(nodeId) {
    this.selectedNodeId = nodeId;
    const node = this.nodes.find(n => n.id === nodeId);
    this.updateHighlighting();
    this.options.onNodeSelect(node);
  }

  setHoveredNode(nodeId) {
    this.hoveredNodeId = nodeId;
    this.updateHighlighting();
    const node = this.nodes.find(n => n.id === nodeId);
    this.options.onNodeHover(node);
  }

  updateHighlighting() {
    const activeId = this.hoveredNodeId || this.selectedNodeId;

    if (!activeId) {
      // Clear dimming
      this.nodesLayer.querySelectorAll(".graph-node").forEach(el => {
        el.classList.remove("node-dimmed", "node-highlighted", "node-selected");
      });
      this.edgesLayer.querySelectorAll(".graph-edge").forEach(el => {
        el.classList.remove("edge-dimmed", "edge-highlighted");
      });
      return;
    }

    // Find all directly connected neighbors
    const connectedNodeIds = new Set([activeId]);
    const activeEdgeIds = new Set();

    this.edges.forEach(edge => {
      if (edge.sourceId === activeId || edge.targetId === activeId) {
        connectedNodeIds.add(edge.sourceId);
        connectedNodeIds.add(edge.targetId);
        activeEdgeIds.add(`edge-${edge.id}`);
      }
    });

    // Apply Node classes
    this.nodes.forEach(node => {
      const el = document.getElementById(`node-${node.id}`);
      if (!el) return;

      if (node.id === this.selectedNodeId) {
        el.classList.add("node-selected");
      } else {
        el.classList.remove("node-selected");
      }

      if (connectedNodeIds.has(node.id)) {
        el.classList.remove("node-dimmed");
        el.classList.add("node-highlighted");
      } else {
        el.classList.add("node-dimmed");
        el.classList.remove("node-highlighted");
      }
    });

    // Apply Edge classes
    this.edgesLayer.querySelectorAll(".graph-edge").forEach(el => {
      if (activeEdgeIds.has(el.id)) {
        el.classList.add("edge-highlighted");
        el.classList.remove("edge-dimmed");
      } else {
        el.classList.add("edge-dimmed");
        el.classList.remove("edge-highlighted");
      }
    });
  }

  // =========================================================================
  // Filtering & Search
  // =========================================================================

  setFrameworkFilter(frameworkId) {
    this.activeFramework = frameworkId;
    this.applyFiltering();
  }

  setSearchQuery(query) {
    this.searchQuery = (query || "").trim().toLowerCase();
    this.applyFiltering();
  }

  applyFiltering() {
    this.nodes.forEach(node => {
      const el = document.getElementById(`node-${node.id}`);
      if (!el) return;

      let matchesFramework = true;
      if (this.activeFramework && this.activeFramework !== "ALL") {
        matchesFramework = (node.touchpoints || []).some(t => t.framework === this.activeFramework);
      }

      let matchesSearch = true;
      if (this.searchQuery) {
        const textToSearch = `${node.name} ${node.code} ${node.division} ${node.head} ${(node.functions || []).join(' ')}`.toLowerCase();
        matchesSearch = textToSearch.includes(this.searchQuery);
      }

      if (matchesFramework && matchesSearch) {
        el.style.opacity = "1.0";
        el.style.pointerEvents = "all";
      } else {
        el.style.opacity = "0.15";
        el.style.pointerEvents = "none";
      }
    });
  }

  // =========================================================================
  // Viewport Helpers & Minimap
  // =========================================================================

  fitToView() {
    if (this.nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    this.nodes.forEach(node => {
      minX = Math.min(minX, node.x - node.width / 2);
      maxX = Math.max(maxX, node.x + node.width / 2);
      minY = Math.min(minY, node.y - node.height / 2);
      maxY = Math.max(maxY, node.y + node.height / 2);
    });

    const padding = 80;
    const graphWidth = maxX - minX + padding * 2;
    const graphHeight = maxY - minY + padding * 2;

    const rect = this.svg.getBoundingClientRect();
    const svgWidth = rect.width || 1200;
    const svgHeight = rect.height || 800;

    const scaleX = svgWidth / graphWidth;
    const scaleY = svgHeight / graphHeight;
    this.scale = Math.min(scaleX, scaleY, 1.2);
    this.scale = Math.max(this.scale, 0.35);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    this.panX = svgWidth / 2 - centerX * this.scale;
    this.panY = svgHeight / 2 - centerY * this.scale;

    this.updateTransform();
  }

  resetZoom() {
    this.scale = 1.0;
    const rect = this.svg.getBoundingClientRect();
    this.panX = rect.width / 2;
    this.panY = rect.height / 2;
    this.updateTransform();
  }

  zoomIn() {
    const rect = this.svg.getBoundingClientRect();
    this.zoomAt(1.25, rect.width / 2, rect.height / 2);
  }

  zoomOut() {
    const rect = this.svg.getBoundingClientRect();
    this.zoomAt(0.8, rect.width / 2, rect.height / 2);
  }

  updateMinimap() {
    const minimapCanvas = document.getElementById("minimap-canvas");
    if (!minimapCanvas) return;

    const ctx = minimapCanvas.getContext("2d");
    const mw = minimapCanvas.width;
    const mh = minimapCanvas.height;
    ctx.clearRect(0, 0, mw, mh);

    // Compute bounding box
    let minX = -1200, maxX = 1200, minY = -800, maxY = 800;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.x - 200);
      maxX = Math.max(maxX, n.x + 200);
      minY = Math.min(minY, n.y - 150);
      maxY = Math.max(maxY, n.y + 150);
    });

    const mapScale = Math.min(mw / (maxX - minX), mh / (maxY - minY));

    // Draw Nodes on minimap
    this.nodes.forEach(n => {
      const mx = (n.x - minX) * mapScale;
      const my = (n.y - minY) * mapScale;
      ctx.fillStyle = n.id === this.selectedNodeId ? "#38BDF8" : (n.status === "critical" ? "#F43F5E" : "#64748B");
      ctx.fillRect(mx - 4, my - 2, 8, 5);
    });

    // Draw viewport rectangle on minimap
    const rect = this.svg.getBoundingClientRect();
    const vx = (-this.panX / this.scale - minX) * mapScale;
    const vy = (-this.panY / this.scale - minY) * mapScale;
    const vw = (rect.width / this.scale) * mapScale;
    const vh = (rect.height / this.scale) * mapScale;

    ctx.strokeStyle = "rgba(56, 189, 248, 0.75)";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(vx, vy, vw, vh);
  }

  truncate(str, max) {
    if (!str) return "";
    return str.length > max ? str.substring(0, max - 1) + "…" : str;
  }
}
