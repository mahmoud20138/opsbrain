/**
 * OpsBrain Enterprise Organizational Data Models & Industry Presets.
 *
 * Provides comprehensive organizational blueprints across 5 industries:
 * 1. Tech & Cloud SaaS
 * 2. Manufacturing & Global Supply Chain
 * 3. Healthcare & Life Sciences
 * 4. Financial Services & FinTech
 * 5. Omnichannel Retail & E-Commerce
 *
 * Each blueprint models:
 * - Structural hierarchies (divisions, reporting tiers)
 * - Individual departmental functions & core capabilities
 * - Cross-team relationships (Reporting, Data Flow, SLA Escalation, Governance)
 * - Analytical framework touchpoints (DORA, SCOR, DMAIC, COSO, ITIL)
 */

export const INDUSTRY_PRESETS = {
  // =========================================================================
  // 1. TECH & CLOUD SAAS
  // =========================================================================
  tech_saas: {
    id: "tech_saas",
    name: "Enterprise Cloud & SaaS",
    description: "Multi-region cloud infrastructure, microservices, DevSecOps, product engineering, and revenue operations.",
    frameworks: ["DORA", "ITIL", "COSO"],
    departments: [
      {
        id: "exec_cto",
        name: "Executive Technology Office",
        code: "CTO-01",
        division: "Executive",
        level: 1,
        head: "Chief Technology Officer",
        headcount: 8,
        budget: "$42M",
        status: "healthy",
        functions: [
          "Enterprise Technology Strategy & R&D",
          "Capital Allocation & Cloud Architecture Governance",
          "Cross-Functional Engineering Alignment"
        ],
        kpis: [
          { name: "R&D Spend to ARR Ratio", target: "18%", current: "17.4%" },
          { name: "Executive SLA Adherence", target: "99.9%", current: "99.85%" }
        ],
        inputs: ["Market trends", "Departmental performance reports", "Board directives"],
        outputs: ["Tech roadmap", "Architecture standards", "Annual tech budget"],
        relationships: [
          { targetId: "plat_eng", type: "reports_to", description: "Direct engineering leadership" },
          { targetId: "prod_mgmt", type: "reports_to", description: "Product strategy alignment" },
          { targetId: "info_sec", type: "governance", description: "Security posture oversight" }
        ],
        touchpoints: [
          { name: "Tech Debt Ratio", metric: "tech_debt_ratio", framework: "ITIL", value: "14%", threshold: "20%", status: "healthy", agent: "evaluator" },
          { name: "Innovation CapEx ROI", metric: "capex_roi", framework: "COSO", value: "3.2x", threshold: "2.5x", status: "healthy", agent: "coordinator" }
        ]
      },
      {
        id: "plat_eng",
        name: "Platform & Cloud Engineering",
        code: "ENG-PLT",
        division: "Engineering",
        level: 2,
        head: "VP of Cloud Platform",
        headcount: 45,
        budget: "$14M",
        status: "warning",
        functions: [
          "Multi-Cloud Kubernetes Infrastructure (AWS/GCP)",
          "Developer Platform Tooling & CI/CD Pipelines",
          "Database Clustering & Storage Infrastructure",
          "FinOps Cloud Spend Optimization"
        ],
        kpis: [
          { name: "Cluster Availability (99.99%)", target: "99.99%", current: "99.95%" },
          { name: "CI/CD Build Duration", target: "< 12 min", current: "11.2 min" }
        ],
        inputs: ["Product code repositories", "Cloud telemetry", "Infrastructure cost reports"],
        outputs: ["Standardized deployment environments", "Automated pipelines", "Cluster telemetry"],
        relationships: [
          { targetId: "sre_ops", type: "data_flow", description: "Telemetry metrics streaming to SRE observability pool" },
          { targetId: "app_eng", type: "data_flow", description: "Shared runtime environments and build systems" },
          { targetId: "fin_ops", type: "governance", description: "Cloud resource utilization reporting" }
        ],
        touchpoints: [
          { name: "Deployment Frequency", metric: "deploy_frequency_daily", framework: "DORA", value: "18/day", threshold: "10/day", status: "healthy", agent: "monitor" },
          { name: "Kubernetes CPU Node Pressure", metric: "k8s_node_cpu_pct", framework: "ITIL", value: "84.2%", threshold: "80.0%", status: "warning", agent: "monitor" },
          { name: "Cloud Cost Pacing Variance", metric: "cloud_cost_variance_pct", framework: "COSO", value: "+8.4%", threshold: "+5.0%", status: "warning", agent: "solver" }
        ]
      },
      {
        id: "app_eng",
        name: "Core Application Engineering",
        code: "ENG-APP",
        division: "Engineering",
        level: 3,
        head: "Director of Product Engineering",
        headcount: 85,
        budget: "$18M",
        status: "healthy",
        functions: [
          "Core Microservices Architecture (Go/Python)",
          "Customer-Facing Frontend Application",
          "Public & Partner REST/GraphQL APIs",
          "Feature Flag Automation & Rollout"
        ],
        kpis: [
          { name: "Lead Time for Changes", target: "< 48 hrs", current: "36 hrs" },
          { name: "Change Failure Rate", target: "< 5%", current: "3.8%" }
        ],
        inputs: ["Product PRDs", "API contracts", "QA test fixtures"],
        outputs: ["Release artifacts", "Changelogs", "API documentation"],
        relationships: [
          { targetId: "sre_ops", type: "sla_escalation", description: "Level-3 engineering escalation on P1 production incidents" },
          { targetId: "prod_mgmt", type: "reports_to", description: "Bi-weekly sprint deliverables and backlog reviews" },
          { targetId: "qa_automation", type: "data_flow", description: "Automated regression test triggers on pull requests" }
        ],
        touchpoints: [
          { name: "Lead Time for Changes", metric: "lead_time_hrs", framework: "DORA", value: "36 hrs", threshold: "48 hrs", status: "healthy", agent: "evaluator" },
          { name: "Change Failure Rate", metric: "change_fail_pct", framework: "DORA", value: "3.8%", threshold: "5.0%", status: "healthy", agent: "rca" }
        ]
      },
      {
        id: "sre_ops",
        name: "Site Reliability & Operations (SRE)",
        code: "OPS-SRE",
        division: "Operations",
        level: 3,
        head: "Head of SRE",
        headcount: 24,
        budget: "$6.5M",
        status: "critical",
        functions: [
          "24/7 Global On-Call Triage & Incident Command",
          "SLO/SLI Definition & Error Budget Governance",
          "Chaos Engineering & Disaster Recovery Runbooks",
          "Observability Stack Maintenance (Prometheus/Grafana)"
        ],
        kpis: [
          { name: "MTTR (Mean Time to Restore)", target: "< 30 min", current: "48 min" },
          { name: "P1 Incident MTTA", target: "< 3 min", current: "2.4 min" }
        ],
        inputs: ["Prometheus/Datadog alerts", "Incident tickets", "Deployment webhooks"],
        outputs: ["Post-incident RCA reports", "SLO dashboards", "Automated remediation runs"],
        relationships: [
          { targetId: "cust_support", type: "sla_escalation", description: "Customer status page syndication & executive escalation" },
          { targetId: "app_eng", type: "sla_escalation", description: "Root-cause bug backlogs for engineering fixes" }
        ],
        touchpoints: [
          { name: "Mean Time to Restore (MTTR)", metric: "mttr_minutes", framework: "DORA", value: "48 min", threshold: "30 min", status: "critical", agent: "rca" },
          { name: "Error Budget Depletion Rate", metric: "error_budget_burn_rate", framework: "ITIL", value: "4.2x", threshold: "2.0x", status: "critical", agent: "monitor" },
          { name: "Synthetic API Probe Latency", metric: "p99_synthetic_latency_ms", framework: "ITIL", value: "1850ms", threshold: "800ms", status: "critical", agent: "solver" }
        ]
      },
      {
        id: "info_sec",
        name: "Cloud Security & SecOps",
        code: "SEC-OPS",
        division: "Security",
        level: 2,
        head: "Chief Information Security Officer (CISO)",
        headcount: 20,
        budget: "$7.2M",
        status: "healthy",
        functions: [
          "Cloud Identity, RBAC & IAM Policy Enforcement",
          "Vulnerability Management & Pen Testing",
          "SOC 2 / ISO 27001 / HIPAA Compliance",
          "Security Incident & Event Management (SIEM)"
        ],
        kpis: [
          { name: "Critical Vulnerability Patch Window", target: "< 7 days", current: "4.2 days" },
          { name: "False Positive Alert Ratio", target: "< 15%", current: "11%" }
        ],
        inputs: ["Container scan CVEs", "Audit logs", "Access requests"],
        outputs: ["Compliance attestations", "Blocked attack telemetry", "Security runbooks"],
        relationships: [
          { targetId: "plat_eng", type: "governance", description: "Mandated automated image scanning in CI/CD" },
          { targetId: "sre_ops", type: "data_flow", description: "SIEM anomaly feed correlated with production alerts" }
        ],
        touchpoints: [
          { name: "Mean Time to Remediate CVEs", metric: "cve_mttr_days", framework: "COSO", value: "4.2 days", threshold: "7.0 days", status: "healthy", agent: "evaluator" },
          { name: "Unauthorized Access Attempts", metric: "unauth_access_rate", framework: "COSO", value: "0.01%", threshold: "0.05%", status: "healthy", agent: "monitor" }
        ]
      },
      {
        id: "prod_mgmt",
        name: "Product Management & UX",
        code: "PRD-MGT",
        division: "Product",
        level: 2,
        head: "Chief Product Officer",
        headcount: 35,
        budget: "$9M",
        status: "healthy",
        functions: [
          "Product Vision, Roadmapping & Spec Writing",
          "User Research & Quantitative Analytics",
          "Customer Feature Prioritization Matrix"
        ],
        kpis: [
          { name: "Feature Adoption Rate", target: "> 40%", current: "44%" },
          { name: "Customer Net Promoter Score (NPS)", target: "> 55", current: "58" }
        ],
        inputs: ["Customer feedback", "Sales loss analysis", "Telemetry telemetry"],
        outputs: ["PRD specifications", "Release roadmap", "Sprint goals"],
        relationships: [
          { targetId: "app_eng", type: "reports_to", description: "Feature requirements and user story handoffs" },
          { targetId: "cust_success", type: "data_flow", description: "Beta customer cohorts and onboarding feedback" }
        ],
        touchpoints: [
          { name: "Feature Time to Market", metric: "feature_ttm_weeks", framework: "ITIL", value: "6.2 weeks", threshold: "8.0 weeks", status: "healthy", agent: "coordinator" }
        ]
      },
      {
        id: "cust_success",
        name: "Customer Success & Enterprise Support",
        code: "CS-OPS",
        division: "Revenue",
        level: 3,
        head: "VP of Customer Experience",
        headcount: 60,
        budget: "$8.5M",
        status: "warning",
        functions: [
          "Enterprise Account Health Monitoring",
          "Tier-1 / Tier-2 Customer Helpdesk Tickets",
          "Customer Onboarding & Renewal Enablement"
        ],
        kpis: [
          { name: "Gross Revenue Retention (GRR)", target: "> 92%", current: "93.4%" },
          { name: "Ticket First Response Time", target: "< 15 min", current: "22 min" }
        ],
        inputs: ["Customer incident tickets", "CSAT surveys", "Product telemetry"],
        outputs: ["Escalated bug tickets", "Renewal forecasts", "Churn risk scores"],
        relationships: [
          { targetId: "sre_ops", type: "sla_escalation", description: "Escalation of customer-impacting outages" },
          { targetId: "prod_mgmt", type: "data_flow", description: "Feature request frequency statistics" }
        ],
        touchpoints: [
          { name: "Customer SLA Breach Rate", metric: "customer_sla_breach_pct", framework: "ITIL", value: "3.4%", threshold: "2.0%", status: "warning", agent: "coordinator" }
        ]
      }
    ]
  },

  // =========================================================================
  // 2. MANUFACTURING & GLOBAL SUPPLY CHAIN
  // =========================================================================
  manufacturing_supply_chain: {
    id: "manufacturing_supply_chain",
    name: "Advanced Manufacturing & Logistics",
    description: "Automated production facilities, just-in-time component sourcing, warehouse robotics, and multimodal freight operations.",
    frameworks: ["SCOR", "DMAIC", "COSO"],
    departments: [
      {
        id: "exec_coo",
        name: "Global Operations Executive",
        code: "COO-01",
        division: "Executive",
        level: 1,
        head: "Chief Operating Officer",
        headcount: 12,
        budget: "$180M",
        status: "healthy",
        functions: [
          "Global Manufacturing Strategy & Footprint Optimization",
          "CapEx Investment in Industry 4.0 Robotics",
          "Supply Chain Resilience & Risk Governance"
        ],
        kpis: [
          { name: "Overall Equipment Effectiveness (OEE)", target: "> 85%", current: "82.4%" },
          { name: "On-Time In-Full Delivery (OTIF)", target: "> 96%", current: "91.8%" }
        ],
        inputs: ["ERP demand forecasts", "Commodity index prices", "Plant telemetry"],
        outputs: ["Annual capacity plan", "CapEx allocations", "Plant safety policies"],
        relationships: [
          { targetId: "plant_ops", type: "reports_to", description: "Direct operational oversight" },
          { targetId: "procure_dept", type: "reports_to", description: "Strategic sourcing directives" },
          { targetId: "logistics_dist", type: "reports_to", description: "Global fulfillment targets" }
        ],
        touchpoints: [
          { name: "OEE Global Benchmark", metric: "oee_global_pct", framework: "SCOR", value: "82.4%", threshold: "85.0%", status: "warning", agent: "evaluator" },
          { name: "Supply Disruption Exposure", metric: "supply_disruption_index", framework: "COSO", value: "6.8/10", threshold: "5.0/10", status: "warning", agent: "solver" }
        ]
      },
      {
        id: "plant_ops",
        name: "Factory Automation & Assembly",
        code: "MFG-PLT",
        division: "Operations",
        level: 2,
        head: "VP of Manufacturing Operations",
        headcount: 320,
        budget: "$85M",
        status: "warning",
        functions: [
          "Robotic Line Assembly & SMT Electronics Placement",
          "Predictive CNC Maintenance & Vibration Monitoring",
          "Factory Floor Shift Scheduling & Worker Safety"
        ],
        kpis: [
          { name: "Line Stoppage Downtime", target: "< 1.5%", current: "3.4%" },
          { name: "Assembly Cycle Time", target: "42 sec", current: "41.8 sec" }
        ],
        inputs: ["Raw materials inventory", "Engineering CAD/CAM files", "PLC sensor data"],
        outputs: ["Finished product batches", "Scrap rate logs", "Maintenance tickets"],
        relationships: [
          { targetId: "quality_ctrl", type: "data_flow", description: "Real-time automated vision inspection telemetry" },
          { targetId: "logistics_dist", type: "data_flow", description: "Pallet staging for outbound freight transfer" }
        ],
        touchpoints: [
          { name: "Unscheduled Machine Downtime", metric: "mfg_downtime_pct", framework: "DMAIC", value: "3.4%", threshold: "1.5%", status: "warning", agent: "rca" },
          { name: "First Pass Yield (FPY)", metric: "first_pass_yield_pct", framework: "DMAIC", value: "96.2%", threshold: "98.5%", status: "warning", agent: "solver" }
        ]
      },
      {
        id: "procure_dept",
        name: "Procurement & Raw Material Sourcing",
        code: "SCM-PRO",
        division: "Supply Chain",
        level: 2,
        head: "Chief Procurement Officer",
        headcount: 48,
        budget: "$120M",
        status: "critical",
        functions: [
          "Supplier Relationship Management (Tier-1/Tier-2)",
          "Long-term Commodity Sourcing Contracts",
          "Dual-Sourcing Strategic Buffer Governance"
        ],
        kpis: [
          { name: "Supplier On-Time Delivery", target: "> 95%", current: "81.2%" },
          { name: "Purchase Price Variance (PPV)", target: "< +2%", current: "+7.4%" }
        ],
        inputs: ["MRP production requirements", "Supplier capacity alerts", "Port delays"],
        outputs: ["Purchase orders", "Vendor quality scorecards", "Inventory safety stock targets"],
        relationships: [
          { targetId: "plant_ops", type: "data_flow", description: "Raw material ETA schedules for production line buffers" },
          { targetId: "logistics_dist", type: "sla_escalation", description: "Emergency freight escalation on delayed silicon wafers" }
        ],
        touchpoints: [
          { name: "Critical Component Stockout Days", metric: "component_stockout_days", framework: "SCOR", value: "4.5 days", threshold: "1.0 days", status: "critical", agent: "monitor" },
          { name: "Supplier Defect Rate (PPM)", metric: "supplier_defect_ppm", framework: "DMAIC", value: "450 PPM", threshold: "100 PPM", status: "critical", agent: "rca" }
        ]
      },
      {
        id: "logistics_dist",
        name: "Global Freight & Distribution Centers",
        code: "LOG-DIST",
        division: "Supply Chain",
        level: 2,
        head: "VP of Global Logistics",
        headcount: 140,
        budget: "$64M",
        status: "critical",
        functions: [
          "Multimodal Ocean / Air / Intermodal Rail Freight",
          "Automated Guided Vehicle (AGV) Warehousing",
          "Customs Clearance & International Trade Compliance"
        ],
        kpis: [
          { name: "Port Dwell Time", target: "< 3.0 days", current: "14.2 days" },
          { name: "Freight Expedited Cost", target: "< $500K/mo", current: "$2.1M/mo" }
        ],
        inputs: ["Finished goods inventory", "Ocean carrier telematics", "Customs declarations"],
        outputs: ["Customer shipments", "In-transit tracking events", "Bill of lading"],
        relationships: [
          { targetId: "exec_coo", type: "sla_escalation", description: "P1 port bottleneck notification and contingency routing" },
          { targetId: "procure_dept", type: "data_flow", description: "Inbound container tracking timestamps" }
        ],
        touchpoints: [
          { name: "Port Dwell Time Spike", metric: "port_dwell_days", framework: "SCOR", value: "14.2 days", threshold: "4.0 days", status: "critical", agent: "monitor" },
          { name: "Expedited Freight Spend Variance", metric: "freight_expedite_spend_pct", framework: "COSO", value: "+320%", threshold: "+25%", status: "critical", agent: "solver" }
        ]
      },
      {
        id: "quality_ctrl",
        name: "Quality Assurance & Six Sigma Engineering",
        code: "QA-ENG",
        division: "Quality",
        level: 3,
        head: "Director of Quality Assurance",
        headcount: 36,
        budget: "$11M",
        status: "healthy",
        functions: [
          "Statistical Process Control (SPC) Monitoring",
          "ISO 9001 / IATF 16949 Audits & Root Cause DMAIC",
          "Automated Optical Inspection (AOI) Calibration"
        ],
        kpis: [
          { name: "Defect Rate (DPMO)", target: "< 3.4 DPMO", current: "4.8 DPMO" },
          { name: "Customer RMA Warranty Rate", target: "< 0.4%", current: "0.32%" }
        ],
        inputs: ["Inspection camera imagery", "Warranty returns", "Calibration logs"],
        outputs: ["Corrective Action Reports (CAPA)", "SPC deviation alerts", "Batch approvals"],
        relationships: [
          { targetId: "plant_ops", type: "governance", description: "Line hold authority on quality metric variance" }
        ],
        touchpoints: [
          { name: "Defects Per Million Opportunities", metric: "six_sigma_dpmo", framework: "DMAIC", value: "4.8 DPMO", threshold: "3.4 DPMO", status: "healthy", agent: "evaluator" }
        ]
      }
    ]
  },

  // =========================================================================
  // 3. HEALTHCARE & HOSPITAL NETWORKS
  // =========================================================================
  healthcare_networks: {
    id: "healthcare_networks",
    name: "Healthcare & Academic Hospital Network",
    description: "Acute emergency care, surgical suites, pharmacy logistics, electronic health record (EHR) integration, and patient billing compliance.",
    frameworks: ["DMAIC", "COSO", "ITIL"],
    departments: [
      {
        id: "exec_cmo",
        name: "Chief Medical & Clinical Operations Office",
        code: "CMO-01",
        division: "Executive",
        level: 1,
        head: "Chief Medical Officer",
        headcount: 14,
        budget: "$240M",
        status: "healthy",
        functions: [
          "Clinical Care Standards & Patient Safety Oversight",
          "Joint Commission (JCAHO) Regulatory Accreditation",
          "Interdisciplinary Clinical Pathway Innovation"
        ],
        kpis: [
          { name: "Patient Safety Score Index", target: "> 98%", current: "97.6%" },
          { name: "Hospital-Acquired Infection Rate", target: "< 0.15%", current: "0.12%" }
        ],
        inputs: ["Clinical morbidity reports", "Regulatory inspections", "Hospital census"],
        outputs: ["Clinical guidelines", "Privileging approvals", "Patient safety directives"],
        relationships: [
          { targetId: "emerg_dept", type: "reports_to", description: "Emergency clinical protocol oversight" },
          { targetId: "pharm_thera", type: "governance", description: "Formulary medication safety approval" },
          { targetId: "health_it", type: "governance", description: "Clinical decision support EHR compliance" }
        ],
        touchpoints: [
          { name: "Patient Safety Incident Ratio", metric: "patient_safety_index", framework: "DMAIC", value: "97.6%", threshold: "98.0%", status: "healthy", agent: "evaluator" }
        ]
      },
      {
        id: "emerg_dept",
        name: "Emergency Services & Trauma Center",
        code: "CLIN-ER",
        division: "Clinical",
        level: 2,
        head: "Chair of Emergency Medicine",
        headcount: 180,
        budget: "$52M",
        status: "critical",
        functions: [
          "Triage & Resuscitation Operations",
          "Acute Stroke, STEMI & Trauma Protocol Activation",
          "Bedside Point-of-Care Diagnostic Testing"
        ],
        kpis: [
          { name: "Door-to-Doctor Time", target: "< 25 min", current: "68 min" },
          { name: "ED Left-Without-Being-Seen (LWBS)", target: "< 2%", current: "5.8%" }
        ],
        inputs: ["EMS ambulance dispatches", "Walk-in patient check-ins", "Telemetry monitors"],
        outputs: ["Inpatient admission orders", "Discharge summaries", "Emergency lab orders"],
        relationships: [
          { targetId: "inpatient_nurs", type: "sla_escalation", description: "Hospital bed management transfer bottleneck" },
          { targetId: "pharm_thera", type: "data_flow", description: "Stat medication orders for critical resuscitations" }
        ],
        touchpoints: [
          { name: "Emergency Door-to-Doctor Delay", metric: "ed_door_to_doc_min", framework: "DMAIC", value: "68 min", threshold: "25 min", status: "critical", agent: "monitor" },
          { name: "Bed Placement Transfer Wait Time", metric: "bed_transfer_wait_min", framework: "DMAIC", value: "142 min", threshold: "45 min", status: "critical", agent: "rca" }
        ]
      },
      {
        id: "inpatient_nurs",
        name: "Inpatient Bed Management & Nursing",
        code: "NURS-OPS",
        division: "Clinical",
        level: 2,
        head: "Chief Nursing Officer (CNO)",
        headcount: 540,
        budget: "$98M",
        status: "warning",
        functions: [
          "Nurse-to-Patient Ratio Staffing Schedules",
          "Inpatient Bed Turnover & Environmental Sanitization",
          "Clinical Medication Administration Records (eMAR)"
        ],
        kpis: [
          { name: "Bed Turnover Turnaround Time", target: "< 45 min", current: "74 min" },
          { name: "Medication Reconciliation Accuracy", target: "> 99.5%", current: "99.1%" }
        ],
        inputs: ["ED admission requests", "Surgical post-op bed orders", "Discharge authorizations"],
        outputs: ["Available bed census", "Staffing shift schedules", "Patient vital trend logs"],
        relationships: [
          { targetId: "emerg_dept", type: "data_flow", description: "Real-time bed availability updates to ED triage" },
          { targetId: "health_it", type: "data_flow", description: "Smart bedside telemetry pump data streaming" }
        ],
        touchpoints: [
          { name: "Bed Turnover Turnaround Latency", metric: "bed_turnover_min", framework: "DMAIC", value: "74 min", threshold: "45 min", status: "warning", agent: "solver" }
        ]
      },
      {
        id: "pharm_thera",
        name: "Pharmacy Logistics & Therapeutics",
        code: "PHARM-RX",
        division: "Clinical",
        level: 3,
        head: "Director of Pharmacy",
        headcount: 65,
        budget: "$44M",
        status: "healthy",
        functions: [
          "Automated Pyxis Dispensing Machine Replenishment",
          "Chemotherapy & Sterile IV Compounding",
          "Adverse Drug Event (ADE) Clinical Surveillance"
        ],
        kpis: [
          { name: "Stat Medication Dispense Time", target: "< 15 min", current: "11 min" },
          { name: "Automated Dispenser Out-of-Stock", target: "< 0.5%", current: "0.28%" }
        ],
        inputs: ["Physician e-prescriptions", "Medication wholesaler shipments", "Pyxis sensor alerts"],
        outputs: ["Barcoded medication packs", "Pharmacokinetic dosing consultations"],
        relationships: [
          { targetId: "inpatient_nurs", type: "data_flow", description: "Electronic Medication Administration validation" }
        ],
        touchpoints: [
          { name: "Stat Medication Delivery Latency", metric: "rx_stat_delivery_min", framework: "ITIL", value: "11 min", threshold: "15 min", status: "healthy", agent: "monitor" }
        ]
      },
      {
        id: "health_it",
        name: "Health Informatics & EHR Systems",
        code: "HIT-EHR",
        division: "Technology",
        level: 2,
        head: "Chief Information Officer (CIO)",
        headcount: 75,
        budget: "$38M",
        status: "healthy",
        functions: [
          "Epic/Cerner EHR System High-Availability",
          "DICOM PACS Medical Imaging Network Streaming",
          "HIPAA Security Rule Audits & Encrypted Telemetry"
        ],
        kpis: [
          { name: "EHR Clinical Core Uptime", target: "99.99%", current: "99.995%" },
          { name: "PACS Image Loading Latency", target: "< 1.2 sec", current: "0.85 sec" }
        ],
        inputs: ["Biomedical device feeds", "Physician dictations", "Lab analyzer HL7 interfaces"],
        outputs: ["Unified patient health records", "EHR billing audit logs", "Clinical alert triggers"],
        relationships: [
          { targetId: "exec_cmo", type: "data_flow", description: "Clinical quality metric aggregations" }
        ],
        touchpoints: [
          { name: "EHR Core Availability", metric: "ehr_uptime_pct", framework: "ITIL", value: "99.995%", threshold: "99.990%", status: "healthy", agent: "monitor" }
        ]
      }
    ]
  },

  // =========================================================================
  // 4. FINANCIAL SERVICES & FINTECH
  // =========================================================================
  financial_services: {
    id: "financial_services",
    name: "Capital Markets & FinTech Banking",
    description: "Algorithmic trading engines, payment clearing rails, quantitative risk models, AML/KYC regulatory reporting, and core banking.",
    frameworks: ["COSO", "ITIL", "DMAIC"],
    departments: [
      {
        id: "exec_cro",
        name: "Enterprise Risk & Executive Office",
        code: "CRO-01",
        division: "Executive",
        level: 1,
        head: "Chief Risk Officer",
        headcount: 15,
        budget: "$60M",
        status: "healthy",
        functions: [
          "Value at Risk (VaR) & Capital Adequacy Oversight",
          "Federal Reserve / SEC Regulatory Stress Testing (CCAR)",
          "Enterprise Counterparty Credit Risk Governance"
        ],
        kpis: [
          { name: "Tier 1 Common Capital Ratio (CET1)", target: "> 12.5%", current: "14.2%" },
          { name: "Enterprise VaR Model Variance", target: "< 5%", current: "2.8%" }
        ],
        inputs: ["Trading book exposures", "Interest rate swap curves", "Macroeconomic forecasts"],
        outputs: ["Daily Risk Capital Allocations", "Regulatory filings", "Limit breach alerts"],
        relationships: [
          { targetId: "quant_trade", type: "governance", description: "Intraday position limit enforcement" },
          { targetId: "aml_comp", type: "reports_to", description: "BSA/AML compliance escalation" },
          { targetId: "core_bank", type: "reports_to", description: "Liquidity reserve ratio governance" }
        ],
        touchpoints: [
          { name: "Daily Value at Risk (VaR)", metric: "daily_var_usd", framework: "COSO", value: "$4.2M", threshold: "$6.0M", status: "healthy", agent: "evaluator" },
          { name: "Counterparty Credit Breach Count", metric: "counterparty_breach_count", framework: "COSO", value: "0", threshold: "2", status: "healthy", agent: "monitor" }
        ]
      },
      {
        id: "quant_trade",
        name: "Algorithmic Execution & Trading Systems",
        code: "TRD-QNT",
        division: "Trading",
        level: 2,
        head: "Head of Electronic Trading",
        headcount: 55,
        budget: "$42M",
        status: "critical",
        functions: [
          "Ultra-Low Latency Order Matching & Market Making",
          "FIX Protocol Gateway Direct Market Access (DMA)",
          "FPGA Hardware Acceleration & Kernel Bypass Networking"
        ],
        kpis: [
          { name: "Order-to-Tick Latency (p99)", target: "< 5.0 µs", current: "24.5 µs" },
          { name: "Market Fill Slippage Rate", target: "< 0.02%", current: "0.07%" }
        ],
        inputs: ["Direct market data feeds (ITCH/OUCH)", "Order flow signals", "Risk limits"],
        outputs: ["Executed trades", "Drop copy execution reports", "Tick audit logs"],
        relationships: [
          { targetId: "clearing_settle", type: "data_flow", description: "Real-time executed trade batches for DTCC/Fedwire settlement" },
          { targetId: "exec_cro", type: "sla_escalation", description: "Trading circuit breaker breach alerts" }
        ],
        touchpoints: [
          { name: "Matching Engine Tick Latency (p99)", metric: "tick_latency_us", framework: "ITIL", value: "24.5 µs", threshold: "8.0 µs", status: "critical", agent: "rca" },
          { name: "Unhedged Position Delta", metric: "unhedged_delta_usd", framework: "COSO", value: "$1.85M", threshold: "$750K", status: "critical", agent: "solver" }
        ]
      },
      {
        id: "clearing_settle",
        name: "Clearing, Treasury & Payment Rails",
        code: "OPS-CLR",
        division: "Operations",
        level: 2,
        head: "Head of Clearing & Settlement",
        headcount: 70,
        budget: "$32M",
        status: "warning",
        functions: [
          "FedNow / SWIFT / ACH Batch Processing & Reconciliations",
          "Intraday Liquidity Forecasting & Central Bank Settlement",
          "Failed Trade T+1 Resolution & Fails-to-Deliver Minimization"
        ],
        kpis: [
          { name: "STP (Straight-Through-Processing) Rate", target: "> 99.2%", current: "96.4%" },
          { name: "Payment Rail Processing Time", target: "< 1.5 sec", current: "3.2 sec" }
        ],
        inputs: ["Trade confirmations", "SWIFT MT/ISO 20022 wire messages", "Bank balances"],
        outputs: ["Ledger journal entries", "Fedwire debit/credit files", "Failed trade tickets"],
        relationships: [
          { targetId: "core_bank", type: "data_flow", description: "Balance adjustments to customer demand deposit accounts" }
        ],
        touchpoints: [
          { name: "Payment Straight-Through-Processing (STP)", metric: "payment_stp_pct", framework: "DMAIC", value: "96.4%", threshold: "99.0%", status: "warning", agent: "monitor" },
          { name: "Failed Settlement Exposure", metric: "failed_settlement_usd", framework: "COSO", value: "$4.8M", threshold: "$2.0M", status: "warning", agent: "coordinator" }
        ]
      },
      {
        id: "aml_comp",
        name: "Financial Crime, AML & Sanctions Compliance",
        code: "CMP-AML",
        division: "Compliance",
        level: 3,
        head: "Chief Compliance Officer",
        headcount: 85,
        budget: "$28M",
        status: "healthy",
        functions: [
          "Real-Time OFAC / PEP Sanctions Screening",
          "Suspicious Activity Report (SAR) Automated Filing",
          "Know Your Customer (KYC) Identity Document Verification"
        ],
        kpis: [
          { name: "Sanctions False Positive Rate", target: "< 10%", current: "7.8%" },
          { name: "SAR Regulatory Filing Window", target: "< 30 days", current: "18 days" }
        ],
        inputs: ["Wire transaction logs", "Global watchlist updates", "KYC onboarding data"],
        outputs: ["Automated wire hold decisions", "SAR filings to FinCEN", "Compliance audit trail"],
        relationships: [
          { targetId: "clearing_settle", type: "governance", description: "Real-time payment screening hold authorization" }
        ],
        touchpoints: [
          { name: "Sanctions Screening Queue Backlog", metric: "aml_screening_backlog", framework: "COSO", value: "14 items", threshold: "50 items", status: "healthy", agent: "monitor" }
        ]
      },
      {
        id: "core_bank",
        name: "Core Banking Ledger & Accounts",
        code: "BNK-COR",
        division: "Technology",
        level: 3,
        head: "VP of Core Banking Infrastructure",
        headcount: 60,
        budget: "$35M",
        status: "healthy",
        functions: [
          "Double-Entry Immutable Transaction Ledger",
          "Interest Calculation & Accrual Batch Jobs",
          "Customer Account Management & Overdraft Protection"
        ],
        kpis: [
          { name: "Ledger Transaction Throughput (TPS)", target: "> 5,000 TPS", current: "6,200 TPS" },
          { name: "Nightly Batch Reconciliation SLA", target: "< 3.0 hrs", current: "2.1 hrs" }
        ],
        inputs: ["Debit card swipes", "Mobile app transfers", "Direct deposits"],
        outputs: ["Monthly account statements", "Ledger balance state", "Overdraft notifications"],
        relationships: [
          { targetId: "exec_cro", type: "data_flow", description: "Nightly balance and reserve telemetry" }
        ],
        touchpoints: [
          { name: "Ledger Nightly Batch Duration", metric: "ledger_batch_duration_hrs", framework: "ITIL", value: "2.1 hrs", threshold: "3.0 hrs", status: "healthy", agent: "evaluator" }
        ]
      }
    ]
  },

  // =========================================================================
  // 5. OMNICHANNEL RETAIL & E-COMMERCE
  // =========================================================================
  retail_ecommerce: {
    id: "retail_ecommerce",
    name: "Global Omnichannel Retail & E-Commerce",
    description: "High-traffic storefronts, automated fulfillment micro-warehouses, demand forecasting algorithms, and customer loyalty retention.",
    frameworks: ["SCOR", "DORA", "DMAIC"],
    departments: [
      {
        id: "exec_retail",
        name: "Retail Executive Strategy & Commerce",
        code: "RET-01",
        division: "Executive",
        level: 1,
        head: "Chief Commercial Officer",
        headcount: 10,
        budget: "$110M",
        status: "healthy",
        functions: [
          "Omnichannel Merchandising & Margin Strategy",
          "Unified Commerce Technology Modernization",
          "Customer Lifetime Value (LTV) Optimization"
        ],
        kpis: [
          { name: "Gross Margin Return on Investment (GMROI)", target: "> 3.2", current: "3.4" },
          { name: "Same-Store Sales Growth", target: "> 4.5%", current: "4.8%" }
        ],
        inputs: ["POS transaction streams", "Competitive price scrapers", "Foot traffic analytics"],
        outputs: ["Quarterly markdown plans", "Assortment guidelines", "Store expansion budget"],
        relationships: [
          { targetId: "ecom_plat", type: "reports_to", description: "Digital revenue and conversion targets" },
          { targetId: "fulfill_hub", type: "reports_to", description: "Same-day delivery service standards" },
          { targetId: "demand_plan", type: "reports_to", description: "Seasonal inventory stocking directives" }
        ],
        touchpoints: [
          { name: "E-Commerce Gross Margin (GMROI)", metric: "gmroi_index", framework: "SCOR", value: "3.4", threshold: "3.2", status: "healthy", agent: "evaluator" }
        ]
      },
      {
        id: "ecom_plat",
        name: "Digital Storefront & Mobile App Platform",
        code: "RET-ECM",
        division: "Technology",
        level: 2,
        head: "VP of E-Commerce Technology",
        headcount: 65,
        budget: "$26M",
        status: "critical",
        functions: [
          "Headless E-Commerce Architecture (Next.js/GraphQL)",
          "Real-Time Product Search, Recommendations & Personalization",
          "Checkout & Payment Gateway Integration (Apple Pay/Stripe)"
        ],
        kpis: [
          { name: "Cart Checkout Conversion Rate", target: "> 3.5%", current: "1.8%" },
          { name: "Page Load Time (Largest Contentful Paint)", target: "< 1.8 sec", current: "3.9 sec" }
        ],
        inputs: ["Customer web/app traffic", "Catalog pricing databases", "Inventory feeds"],
        outputs: ["Completed orders", "Shopping cart abandon telemetry", "A/B testing readouts"],
        relationships: [
          { targetId: "fulfill_hub", type: "data_flow", description: "Live order stream pushed to fulfillment robotics" },
          { targetId: "demand_plan", type: "data_flow", description: "Search query frequency and out-of-stock search tracking" }
        ],
        touchpoints: [
          { name: "Cart Checkout 504 Gateway Timeouts", metric: "checkout_timeout_rate_pct", framework: "DORA", value: "8.4%", threshold: "0.5%", status: "critical", agent: "monitor" },
          { name: "E-Commerce Core Web Vitals (LCP)", metric: "cwv_lcp_seconds", framework: "DORA", value: "3.9 sec", threshold: "2.5 sec", status: "critical", agent: "rca" }
        ]
      },
      {
        id: "fulfill_hub",
        name: "Robotic Fulfillment Centers & Logistics",
        code: "FUL-OPS",
        division: "Operations",
        level: 2,
        head: "VP of Fulfillment & Last-Mile Delivery",
        headcount: 220,
        budget: "$48M",
        status: "warning",
        functions: [
          "Automated Pick-Pack-Ship Conveyor & Kiva Robotics",
          "Same-Day / Next-Day Regional Courier Dispatch",
          "Returns Processing & Reverse Logistics Refurbishment"
        ],
        kpis: [
          { name: "Order Pick-to-Ship Cycle Time", target: "< 90 min", current: "145 min" },
          { name: "Last-Mile Delivery On-Time Rate", target: "> 98%", current: "94.2%" }
        ],
        inputs: ["E-commerce orders", "Inbound vendor restock pallets", "Courier tracking"],
        outputs: ["Dispatched parcel packages", "Shipping label manifests", "Returned inventory"],
        relationships: [
          { targetId: "store_ops", type: "data_flow", description: "BOPIS (Buy Online, Pick Up in Store) staged orders" }
        ],
        touchpoints: [
          { name: "Order Pick-to-Ship Turnaround", metric: "pick_to_ship_min", framework: "SCOR", value: "145 min", threshold: "90 min", status: "warning", agent: "solver" }
        ]
      },
      {
        id: "demand_plan",
        name: "Inventory Demand Forecasting & Replenishment",
        code: "SCM-DMD",
        division: "Supply Chain",
        level: 3,
        head: "Director of Supply Chain Analytics",
        headcount: 30,
        budget: "$14M",
        status: "healthy",
        functions: [
          "Machine Learning Demand Forecasting Models",
          "Dynamic Pricing & Markdown Optimization Engine",
          "Safety Stock Reorder Point Calculation"
        ],
        kpis: [
          { name: "Forecast Accuracy (WAPE)", target: "> 88%", current: "91.2%" },
          { name: "Out-of-Stock SKUs During Promotions", target: "< 2%", current: "1.4%" }
        ],
        inputs: ["Historical sales velocity", "Weather forecasts", "Supplier lead times"],
        outputs: ["Automated purchase orders", "Dynamic markdown schedules", "Store replenishment allocations"],
        relationships: [
          { targetId: "fulfill_hub", type: "governance", description: "Warehouse slotting and reorder parameters" }
        ],
        touchpoints: [
          { name: "Demand Forecast Error (WAPE)", metric: "forecast_wape_pct", framework: "DMAIC", value: "8.8%", threshold: "12.0%", status: "healthy", agent: "evaluator" }
        ]
      },
      {
        id: "store_ops",
        name: "Retail Store Network & POS Systems",
        code: "RET-STR",
        division: "Operations",
        level: 3,
        head: "VP of Retail Store Operations",
        headcount: 450,
        budget: "$72M",
        status: "healthy",
        functions: [
          "Brick-and-Mortar Store Operations & Merchandising",
          "Point-of-Sale (POS) Terminal Hardware & Edge Networks",
          "Customer Curbside Pickup & In-Store Inventory Cycle Counting"
        ],
        kpis: [
          { name: "POS Terminal Uptime", target: "99.99%", current: "99.99%" },
          { name: "Inventory BOH (Balance On Hand) Accuracy", target: "> 97%", current: "98.2%" }
        ],
        inputs: ["Store inventory shipments", "Store associate staffing", "Shopper traffic"],
        outputs: ["POS transaction receipts", "Store cash deposits", "Shrinkage discrepancy logs"],
        relationships: [
          { targetId: "exec_retail", type: "data_flow", description: "Daily comparable store sales telemetry" }
        ],
        touchpoints: [
          { name: "Store POS Edge Terminal Latency", metric: "pos_edge_latency_ms", framework: "ITIL", value: "85ms", threshold: "250ms", status: "healthy", agent: "monitor" }
        ]
      }
    ]
  }
};
