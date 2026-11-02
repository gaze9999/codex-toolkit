# AI agent terminology and responsibility boundaries

Read for agent architecture terminology, responsibility routing, bilingual documentation or terminology-profile maintenance. Select the relevant section.

## Wording scope

Use the Taiwan Chinese labels below as this Toolkit's engineering recommendations, with the English term on first use when ambiguity matters. Preserve product terminology, formal names, API Symbols, specifications and quotations. `AI 代理程式`, `AI 代理人` and the concise `AI 代理` can describe the same English concept; choose one for authored project prose without rewriting an authoritative source.

Use `工作規範` for Agent Instructions, `設定管理` for source/version/options and `權限管理` for access/authorization. Retain `AI 代理治理` when the subject is policy, accountability, identity, risk, lifecycle or organizational controls.

## Responsibility routing

| Concern | Engineering label | Maintained owner and evidence |
| --- | --- | --- |
| Policies, accountability, identity and risk | AI 代理治理 (Agent Governance) | Applicable policy and permission owners, with access controls enforced at runtime |
| Routing, delegation, ordering and result integration | 代理編排 (Agent Orchestration) | Selected workflow and runtime, with dispatch based on current task authorization |
| Model/tool/context loop and recovery control | 代理執行控制框架 (Agent Harness) | Actual client/framework; distinguish it from sandbox compute |
| Information supplied at each model step | 上下文工程 (Context Engineering) | Context selection, sources and limits; retrieval is one possible input |
| Observed execution and operational signals | 代理可觀測性 (Agent Observability) | Instrumentation and authorized traces/metrics/logs |
| Judging behavior/results against criteria | 代理評估 (Agent Evaluation) | Task-specific criteria, test/evaluation owner and actual outcomes |

These responsibilities can share components. Keep business decisions with the project, portable methods with the relevant Skill, distribution with the Plugin and protocol/authentication/data access with the integration owner.

## Concepts and architecture

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| AI 代理程式 | AI Agent | A task-performing system that can select actions/tools toward a goal; autonomy remains bounded by authorization |
| 代理式 AI | Agentic AI | A capability/design approach involving goal-directed planning and action |
| 代理式 AI 系統 | Agentic System | The overall arrangement of models, tools, execution and state that provides agentic behavior |
| 代理式工作流程 | Agentic Workflow | An LLM/tool process; state whether steps are predefined or dynamically selected |
| 自主代理程式 | Autonomous Agent | An agent that selects subsequent actions within its allowed scope |
| 單一代理系統 | Single-Agent System | One agent owns task execution and can use multiple tools |
| 多代理系統 | Multi-Agent System (MAS) | Multiple agents coordinate bounded responsibilities through sequential or parallel execution |
| 代理系統架構 | Agent Architecture | The system's model, tool, state, execution and interaction boundaries |
| 代理程式框架 | Agent Framework | Reusable facilities for constructing and running agents |

## Collaboration and control flow

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| 主代理程式 | Main Agent | The primary task/integration owner in the selected workflow |
| 子代理程式 | Subagent | An agent assigned a bounded subtask within the caller's authorized scope |
| 監督代理程式 | Supervisor Agent | A role directing or selecting other agents' work |
| 執行代理程式 | Worker Agent | A role performing assigned work and returning its evidence/results |
| 代理編排 | Agent Orchestration | Routing, sequencing, coordination and integration of agent work |
| 任務委派 | Task Delegation | Assigning work; control can remain with the caller, depending on the mechanism |
| 任務路由 | Task Routing | Selecting the handler or workflow for a task |
| 代理交接 | Agent Handoff | Transferring active handling/control to another agent in the selected runtime |
| 代理協作 | Agent Collaboration | Exchanging information/results to complete shared work |
| 平行執行 | Parallel Execution | Overlapping independent execution with verified resource isolation |
| 編排器與執行代理模式 | Orchestrator-Workers | Dynamic task decomposition, delegation and result synthesis |
| 評估與改良模式 | Evaluator-Optimizer | Generation, evaluation and revision in a feedback loop; preserve formal optimizer names |

Delegation is the broader assignment relationship; a handoff can be a delegation mechanism. In OpenAI Agents SDK, a handoff transfers control, while an agent used as a tool can return a result to its caller. Inspect the selected API instead of inferring control ownership from a role name. A conversation handoff document records continuation context, while a runtime handoff transfers active control.

## Tools, protocols and distribution

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| 工具呼叫 | Tool Calling | Selecting/invoking a tool through its actual schema and authorization |
| 函式呼叫 | Function Calling | Producing structured function arguments; a requested call is distinct from successful execution |
| 工具串接 | Tool Integration | Connecting tool/API/data capabilities to the application |
| 模型情境協定 | Model Context Protocol (MCP) | A standard connection model for AI applications, tools, resources and prompts; preserve product-specific translations |
| 代理對代理協定 | Agent2Agent (A2A) | Interoperation and work exchange between agent systems |
| 代理對使用者介面規格 | Agent-to-User Interface (A2UI) | Declarative UI structure/data interpreted by a renderer; check the selected specification/catalog/version |
| 代理與使用者互動協定 | Agent-User Interaction (AG-UI) | Bidirectional agent/frontend events, state and interactions; transport and renderer are separate choices |
| 檢索增強生成 | Retrieval-Augmented Generation (RAG) | Supplying retrieved information for generation, with source authority and answer correctness evaluated separately |
| 代理技能模組 | Agent Skills | Reusable instructions with optional references/scripts/assets, loaded within the authorized task scope |
| 外掛 | Plugin | A host-supported distribution/integration unit that can package Skills and other capabilities; installation, loading and invocation are separate |
| 代理工作規範 | Agent Instructions | Applicable instructions such as AGENTS.md; distinguish text guidance from enforced configuration/permissions |

MCP, A2A, A2UI and AG-UI name different primary boundaries and can be composed. A2UI describes declarative UI structure/data; AG-UI specifies bidirectional events, state and interactions across supported transports. Verify current extensions and framework/renderer support before implementation.

## Execution, context and recovery

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| 代理執行環境 | Agent Runtime | Facilities that run the agent and its execution lifecycle |
| 代理執行控制框架 | Agent Harness | Control around model calls, tools, context, approvals and recovery; separate from compute isolation |
| 代理執行迴圈 | Agent Loop | Repeated observation, model/action selection, execution and result handling |
| 沙箱 / 隔離執行環境 | Sandbox | A bounded compute/filesystem/process environment with its own actual isolation guarantees |
| 上下文工程 | Context Engineering | Selecting/structuring information available to the model at each step, retaining established 情境工程 wording in sources |
| 上下文視窗 | Context Window | The model's context capacity under its actual token/account/runtime limits |
| 上下文壓縮 | Context Compaction | Reducing retained prompt history |
| 代理記憶 | Agent Memory | Information retained/retrieved across steps or sessions according to the actual implementation |
| 檢查點 | Checkpoint | A captured execution state from which a supported recovery mechanism can resume |
| 狀態持久保存 | State Persistence | Keeping selected state in durable storage beyond a process/session |
| 可復原執行 | Durable Execution | Resuming interrupted work with defined recovery/replay semantics; external effects still need outcome checks and idempotency |

Memory can be implemented through checkpoints or separate stores. Distinguish an instruction/progress record, prompt compaction, retained memory, a code snapshot and an executable checkpoint. Before replaying an interrupted external write, check its receipt, destination state and idempotency requirements.

## Governance, safety and permissions

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| AI 代理治理 | Agent Governance | Policies/accountability for agent identity, ownership, risk, access, lifecycle and oversight |
| 代理生命週期管理 | Agent Lifecycle Management | Creation, deployment, updating, retirement and ownership transitions |
| 控制平面 | Control Plane | Policy/configuration/identity and coordination controls; its scope depends on the system |
| 代理身分識別 | Agent Identity | The identity and accountable owner associated with an agent |
| 政策強制執行 | Policy Enforcement | Applying controls at the actual execution boundary rather than only describing them |
| 最小權限原則 | Least Privilege | Granting only permissions needed for the authorized work |
| 信任邊界 | Trust Boundary | A boundary across which identity, data or authorization assumptions change |
| 防護機制 | Guardrails | Checks/controls constraining behavior; inspect which layer actually enforces them |
| 人員參與機制 | Human-in-the-Loop (HITL) | Human input/approval at selected workflow steps |
| 人員監督機制 | Human-on-the-Loop (HOTL) | Oversight with intervention capability during automated execution |
| 核准關卡 | Approval Gate | A policy-defined approval prerequisite for a scoped operation |
| 稽核軌跡 | Audit Trail | Evidence linking actions and relevant decisions to their accountable source |
| 提示詞注入 | Prompt Injection | Untrusted content attempting to redirect instruction-following across a trust boundary |

## Operations and quality

| Preferred Chinese label | English term | Meaning and boundary |
| --- | --- | --- |
| AI 代理維運 | AgentOps | Deployment, operation, monitoring and improvement practices for agent systems |
| 代理可觀測性 | Agent Observability | Inferring operational state/behavior from authorized signals |
| 執行追蹤 | Tracing | Correlating an execution's operations/events; capture/export permissions remain separate |
| 追蹤區段 | Span | A trace's individual operation with its timing/context |
| 事件記錄 | Logging | Recording execution events, with 記錄檔 naming the resulting log file |
| 代理評估 | Agent Evaluation (Evals) | Judging behavior/results against explicit task-specific criteria |
| 回歸測試 | Regression Testing | Checking that a change preserves required existing behavior |
| 任務成功率 | Task Success Rate | Accepted successful tasks divided by an explicitly defined evaluated task set |
| 品質關卡 | Quality Gate | Required quality criteria before an authorized stage transition |
| 單任務成本 | Cost per Task | End-to-end task cost, including retries, review and repair under comparable conditions |
| 失敗復原 | Failure Recovery | Restoring a valid execution state after failure, preserving unresolved outcomes |

Observability describes evidence about execution; evaluation applies acceptance criteria. Distinguish tasks, cases, assertions, logical calls and retries when reporting counts/costs.

## Document names by responsibility

| Document label | English name | Use |
| --- | --- | --- |
| AI 代理治理政策 | Agent Governance Policy | Policy, accountability and organizational controls |
| 多代理協作與編排設計 | Multi-Agent Orchestration Design | Task/control/state/resource ownership |
| 代理執行控制框架設計 | Agent Harness Design | Runtime loop, tools, context and recovery |
| 代理工作規範 | Agent Instructions | Task/project instructions |
| 代理技能模組 | Agent Skills | Reusable task capability |
| 模型選擇與路由策略 | Model Selection and Routing Policy | Eligible model selection and routing conditions |
| 代理工具設定與權限管理 | Agent Tool Configuration and Permission Management | Source/version/options and separately enforced access |
| 上下文與記憶管理 | Context and Memory Management | Information selection, retention and recovery boundaries |
| 任務委派與交接規範 | Task Delegation and Handoff Policy | Assignment, active control and result ownership |
| 代理可觀測性與評估 | Agent Observability and Evaluation | Operational signals and separate acceptance criteria |

Choose a name from the actual responsibility; do not rename stable IDs, APIs or existing files merely to match this table.

## Sources and adoption status

Sources checked 2026-11-02. The glossary summarizes the sources below and provides Chinese labels for Toolkit/project use. Retain source publication/version dates separately from this check date.

| Source | Checked contribution |
| --- | --- |
| [Microsoft AI agent governance](https://learn.microsoft.com/zh-tw/azure/cloud-adoption-framework/ai-agents/governance-security-across-organization) | Governance includes identity, ownership, lifecycle, observability, data and security; its translated labels vary |
| [AWS Agentic AI](https://aws.amazon.com/tw/what-is/agentic-ai/) | Agentic AI and Taiwan-facing product terminology |
| [Anthropic Building effective agents](https://www.anthropic.com/research/building-effective-agents) | Predetermined workflows versus dynamic agents, orchestrator-workers and evaluator-optimizer patterns; article originally published 2024-12-19 |
| [OpenAI sandbox agents](https://developers.openai.com/api/docs/guides/agents/sandboxes) | Harness/control versus sandbox/compute responsibilities |
| [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/) and [agents as tools](https://openai.github.io/openai-agents-python/tools/#agents-as-tools) | Handoffs transfer control; an agent used as a tool can return to its caller |
| [OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/) | Traces/spans and recorded event types, with separate sensitive-data/export choices |
| [Google agent protocol guide](https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/) | Primary MCP/A2A/A2UI/AG-UI boundaries and renderer examples; published 2026-03-18 |
| [MCP introduction, 2026-07-28 documentation](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro) | Connection to external tools, data and workflows |
| [AG-UI introduction](https://docs.ag-ui.com/introduction) | Bidirectional events/state/interaction; distinct from declarative UI descriptions |
| [Agent Skills specification](https://agentskills.io/specification) | SKILL.md with optional scripts, references and assets |
| [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/) | Traces and spans as operational signals |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpointers versus stores and the limits of in-memory persistence |

For terminology automation, keep only reliable narrow patterns in the selected profile. Context-sensitive aliases receive manual advice without automatic replacement. Preserve accepted alternatives, quotations, code, URLs, formal names and authoritative UI/specification copy. See the [proofreading workflow](https://github.com/gaze9999/codex-toolkit/blob/main/docs/tools/proofreading.md) for engine/configuration ownership.
