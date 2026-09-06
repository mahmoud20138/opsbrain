/**
 * Analytical Framework Matrix and Mapping Engine for OpsBrain Enterprise UI.
 *
 * Defines industry-standard analytical frameworks:
 * - DORA (DevOps Research and Assessment)
 * - SCOR (Supply Chain Operations Reference)
 * - DMAIC (Six Sigma Process Improvement)
 * - COSO (Enterprise Risk Management)
 * - ITIL 4 (Service Management & Reliability)
 */

export const FRAMEWORKS = {
  DORA: {
    id: "DORA",
    name: "DORA Metrics Framework",
    badge: "DORA",
    tagline: "Software Delivery & Reliability Performance",
    color: "#06B6D4", // Cyan
    bgLight: "rgba(6, 182, 212, 0.12)",
    description: "Industry-standard benchmarks established by Google Cloud DevOps Research and Assessment to measure software delivery velocity and stability.",
    pillars: [
      { code: "DF", name: "Deployment Frequency", description: "How often an organization successfully releases to production" },
      { code: "LT", name: "Lead Time for Changes", description: "Time from commit to code running successfully in production" },
      { code: "CFR", name: "Change Failure Rate", description: "Percentage of deployments causing production degradation or requiring rollbacks" },
      { code: "MTTR", name: "Time to Restore Service", description: "How long it takes an organization to recover from a production outage" }
    ],
    agentMapping: {
      DF: "monitor",
      LT: "evaluator",
      CFR: "rca",
      MTTR: "solver"
    }
  },

  SCOR: {
    id: "SCOR",
    name: "SCOR Supply Chain Model",
    badge: "SCOR",
    tagline: "Supply Chain Operations Reference",
    color: "#3B82F6", // Blue
    bgLight: "rgba(59, 130, 246, 0.12)",
    description: "The global reference model endorsed by the Association for Supply Chain Management (ASCM) covering business activities from demand to fulfillment.",
    pillars: [
      { code: "PLAN", name: "Plan", description: "Balancing resources with demand requirements and establishing execution rules" },
      { code: "SOURCE", name: "Source", description: "Procuring goods and raw materials to meet planned or actual demand" },
      { code: "MAKE", name: "Make", description: "Transforming materials into completed products or converting raw inputs" },
      { code: "DELIVER", name: "Deliver", description: "Order management, warehousing, transportation, and customer handoff" },
      { code: "RETURN", name: "Return", description: "Reverse logistics, warranty management, refurbishment, and defect analysis" }
    ],
    agentMapping: {
      PLAN: "coordinator",
      SOURCE: "monitor",
      MAKE: "solver",
      DELIVER: "rca",
      RETURN: "evaluator"
    }
  },

  DMAIC: {
    id: "DMAIC",
    name: "Six Sigma DMAIC",
    badge: "DMAIC",
    tagline: "Data-Driven Process Optimization & Quality",
    color: "#10B981", // Emerald
    bgLight: "rgba(16, 185, 129, 0.12)",
    description: "A closed-loop quality control and process capability methodology aimed at eliminating operational variance, defects, and SLA friction.",
    pillars: [
      { code: "D", name: "Define", description: "Define customer requirements, process boundaries, and business objectives" },
      { code: "M", name: "Measure", description: "Establish baseline process performance metrics and data collection plans" },
      { code: "A", name: "Analyze", description: "Identify root causes of defects, bottlenecks, and performance variance" },
      { code: "I", name: "Improve", description: "Design, test, and implement targeted remediation solutions" },
      { code: "C", name: "Control", description: "Institutionalize automated monitoring and governance guardrails" }
    ],
    agentMapping: {
      D: "coordinator",
      M: "monitor",
      A: "rca",
      I: "solver",
      C: "evaluator"
    }
  },

  COSO: {
    id: "COSO",
    name: "COSO Enterprise Risk Management",
    badge: "COSO",
    tagline: "Governance, Risk & Internal Controls",
    color: "#F59E0B", // Amber
    bgLight: "rgba(245, 158, 11, 0.12)",
    description: "Framework created by the Committee of Sponsoring Organizations to integrate risk assessment with strategic business execution.",
    pillars: [
      { code: "GOV", name: "Governance & Culture", description: "Tone at the top, executive oversight, and organizational culture" },
      { code: "STRAT", name: "Strategy & Objective-Setting", description: "Risk appetite alignment with business portfolio growth" },
      { code: "PERF", name: "Performance Risk Assessment", description: "Identifying, prioritizing, and responding to operational risks" },
      { code: "REV", name: "Review & Revision", description: "Auditing internal controls against evolving systemic disruptions" },
      { code: "INFO", name: "Information & Communication", description: "Leveraging structured telemetry for real-time compliance reporting" }
    ],
    agentMapping: {
      GOV: "coordinator",
      STRAT: "evaluator",
      PERF: "monitor",
      REV: "rca",
      INFO: "solver"
    }
  },

  ITIL: {
    id: "ITIL",
    name: "ITIL 4 Service Value System",
    badge: "ITIL 4",
    tagline: "Service Management & Operational Excellence",
    color: "#8B5CF6", // Violet
    bgLight: "rgba(139, 92, 246, 0.12)",
    description: "A framework for managing digital services end-to-end, governing incident response, service level agreements (SLAs), and change enablement.",
    pillars: [
      { code: "INC", name: "Incident Management", description: "Minimizing negative impact by restoring normal service operation rapidly" },
      { code: "PRB", name: "Problem Management", description: "Reducing likelihood and impact of incidents by identifying actual root causes" },
      { code: "CHG", name: "Change Enablement", description: "Maximizing successful service changes through automated risk assessment" },
      { code: "SLA", name: "Service Level Management", description: "Defining, monitoring, and enforcing performance commitments with consumers" }
    ],
    agentMapping: {
      INC: "monitor",
      PRB: "rca",
      CHG: "solver",
      SLA: "coordinator"
    }
  }
};

/**
 * Filter departments by active framework.
 * Returns map of departmentId -> active framework touchpoints count.
 */
export function evaluateDepartmentFrameworks(departments, frameworkId) {
  const result = new Map();
  if (!frameworkId || frameworkId === "ALL") {
    departments.forEach(d => result.set(d.id, d.touchpoints ? d.touchpoints.length : 0));
    return result;
  }

  departments.forEach(d => {
    const matching = (d.touchpoints || []).filter(t => t.framework === frameworkId);
    result.set(d.id, matching.length);
  });
  return result;
}
