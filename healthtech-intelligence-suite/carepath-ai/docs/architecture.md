# Architecture

Canonical HLA/LLA for CarePath AI. Narrative design: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

**Port:** Clinician console FastAPI **8007**.

## High-Level Architecture (HLA)

Extracted from [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) §3:

```mermaid
flowchart LR
  subgraph clients [Clients]
    WebUI[ClinicianConsole]
  end
  subgraph runtime [AgentRuntime]
    FastAPI[FastAPI_8007]
    LG[LangGraph_Supervisor]
  end
  subgraph knowledge [KnowledgePlane]
    Vec[Hybrid_RAG]
    Neo[Neo4j_KG]
    Mem[Three_Memory_Layers]
  end
  subgraph models [ModelPlane]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
  end
  WebUI --> FastAPI --> LG
  LG --> Vec
  LG --> Neo
  LG --> Mem
  LG --> Bedrock
  LG --> Vertex
```

Agents: firewall → supervisor ↔ (patient_data_extractor, medication_interaction_checker, treatment_plan_generator, patient_preference_agent, treatment_plan_evaluator) → HITL → plan_publish.

## Low-Level Architecture (LLA)

Clinical HITL happy path: generate plan for complex chronic patient → clinician approve → mock EHR publish.

```mermaid
sequenceDiagram
  participant Clinician
  participant API as FastAPI_8007
  participant FW as Firewall
  participant Sup as Supervisor
  participant Ext as PatientExtractor
  participant Med as MedInteractionChecker
  participant Gen as PlanGenerator
  participant Pref as PreferenceAgent
  participant Eval as PlanEvaluator
  participant HITL as HITL
  participant Pub as PlanPublish

  Clinician->>API: generate plan patient_P001
  API->>FW: scan input
  FW-->>API: allow
  API->>Sup: start TreatmentPlanState
  Sup->>Ext: structure EHR + notes + KG
  Ext-->>Sup: patient_profile
  Sup->>Med: check interactions
  Med-->>Sup: interaction_flags
  Sup->>Gen: draft goals interventions monitoring
  Gen-->>Sup: draft_plan
  Sup->>Pref: adapt to preferences
  Pref-->>Sup: adapted_plan
  Sup->>Eval: safety + guidelines + citations
  Eval-->>Sup: judge pass
  Sup->>HITL: interrupt clinical approval
  HITL-->>API: pending card
  Clinician->>API: approve or edit
  API->>HITL: resume
  HITL-->>Sup: approval
  Sup->>Pub: audit log + mock EHR
  Pub-->>Sup: published
  Sup-->>API: final plan
  API-->>Clinician: published treatment plan
```
