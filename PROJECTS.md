# MindForge AgentLab — project catalog

**Portfolio:** MindForge AgentLab AI Portfolio  
**Folder:** `mindforge-agentlab-ai-portfolio` (replaces `set-of-designed-projects`)

Each **Name** is the canonical single product id. Package folder paths with `&` / `(tags)` stay as path aliases.

## Packages in this portfolio

| Name | Folder / package path | Stack (one line) |
|------|----------------------|------------------|
| **ResonanceResearch** | `1…/resonance-ai-research-assistant` | Research assistant agent |
| **ResonanceTriage** | `1…/resonance-ai-ticket-triage-agent` | Ticket triage agent |
| **AetherRAG** | `2.agentic-rag-chatbot` | LangChain + ChromaDB + n8n |
| **KnowledgeForge** | `4.enterprise-ai-knowledge-platform` | RAG + GraphRAG + HITL |
| **RoboForge** | `5…/roboforge-ai` | Robots & Pencils agent platform |
| **RPFabric** | `5…/rp-agentic-fabric` | Agentic fabric / orchestration |
| **WAIP** | `6…/waip` | Walmart AI intake / planning |
| **WIDRA** | `6…/widra` | Walmart document / retrieval agent |
| **WOKA** | `6…/woka` | Walmart ops / knowledge agent |
| **CarePath** | [`healthtech-intelligence-suite/carepath-ai`](healthtech-intelligence-suite/carepath-ai/) | Healthcare pathway / clinical CDS agent |
| **HEDIP** | [`healthtech-intelligence-suite/hedip`](healthtech-intelligence-suite/hedip/) | HEDI quality / decision intelligence platform |
| **RAIP** | [`healthtech-intelligence-suite/raip`](healthtech-intelligence-suite/raip/) | Risk adjustment / evidence-first authoring engine |
| **AgentForge** | `8…/agentforge` | LangGraph 1.x agent framework |
| **LocalLLMAgents** | `8…/local-llm-agents` | Local LLM agent demos |
| **AdviseGuard** | `10…/adviseguard-ai` | Fintech advisory guardrails |
| **BankShield** | `10…/bankshield-ai` | Banking risk / shield agents |

Parent `#` folders are group containers, not product names. Missing slots here: `#3`, `#9`, `#11–#14`.

## Sibling portfolio — DataForge FlowLab

Folder: [`../dataforge-flowlab-pipeline-portfolio/`](../dataforge-flowlab-pipeline-portfolio/) · catalog: [`../dataforge-flowlab-pipeline-portfolio/PROJECTS.md`](../dataforge-flowlab-pipeline-portfolio/PROJECTS.md)

| Name | Folder | Stack |
|------|--------|-------|
| **DemandCast** | `astro-salesforecast` | Astro/Airflow 3, MLflow, Streamlit/FastAPI |
| **RUSP** | `e2e-data-engineering` | Airflow → Kafka KRaft → Spark → Cassandra |
| **Aurelia** | `modern-data-eng-dbt-databricks-azure` | Azure medallion + dbt |
| **ReviewStream** | `realtime-streaming-engineering` | Sentiment streaming → Kafka → ES |
| **KarmaLake** | `reddit-data-engineering` | Reddit → Airflow → S3 |
| **HealFlow** | `self-healing-pipeline` | Airflow 3 + healing + Ollama |
| **CorridorPulse** | `smart-city` | Redpanda → Spark → lakehouse |
| **LedgerForge** | `…/ledgerforge` | Kafka → Flink/Spark → ClickHouse |
| **PolyStream** | `unstructural-data` | Polyglot → Spark lakehouse |
| **TubePulse** | `youtube-analytics` | YouTube → Kafka → ksqlDB → Telegram |

## Naming rules

1. One **Name** per shippable package.
2. Portfolio folder names are representative umbrellas: **MindForge** (agents/AI) · **DataForge** (pipelines/DE).
3. Do not rename package parents containing `&` / `(tags)` without an explicit migration pass.
