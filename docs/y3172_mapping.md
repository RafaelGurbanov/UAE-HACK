# ITU-T Y.3172 mapping — smart pen use case

Y.3172 describes an ML pipeline of SRC → C → PP → M → P → D → SINK nodes. The **legal basis column is filled only from retrieved KB passages** (Phase 3+). Nothing below is a legal claim.

| Node | Smart-pen component | Data handled | Main governance concerns | Lead agent(s) | Readiness dimension(s) |
|---|---|---|---|---|---|
| **SRC** | Smart pen + writing board | Stroke pressure, speed, pauses, letter formation (raw, per child) | Collection from minors, notice, parental consent, data minimisation | Data Protection, Education | Human interaction & supervision; AI for social inclusion |
| **C** | School edge compute platform | Raw + session data inside the school | Security, access control, on-premise retention | Education, Data Protection | Digital infrastructure & energy |
| **PP** | Pre-processing / harmonisation (device or edge) | Features; pseudonymisation / de-identification | De-identification standard, purpose limitation | Data Protection | Open data & open-source management |
| **M** | Anomaly detection, handwriting analysis models | Features → risk flags (inferred disability signals) | Accuracy, bias across scripts (Arabic/English handwriting), false positives, **inferred sensitive data** | AI Ethics, Data Protection | Contextualisation & regional development; AI integration in domains |
| **P** | Policy / human review | Flags + model explanation → counsellor decision | Mandatory counsellor review, override conditions, appeal, no automated decision about the child | Education, AI Ethics | Human interaction & supervision; AI policy & implementation |
| **D** | Provider cloud analytics | Aggregates, model updates, possibly identifiable data | Cross-border transfer, secondary use (advertising), retention | Data Protection, Consumer Protection | Digital infrastructure & energy; AI policy & implementation |
| **SINK** | Parent / teacher mobile app | Counsellor-approved outcomes, in-app commerce | Stigmatising language, in-app purchases, dark patterns, ads to minors | Consumer Protection, Education | AI for social inclusion; Generative AI content ecosystem |

## Hard rules enforced by the platform
1. Nothing goes from **M** to **SINK** without passing **P** (counsellor approval). Scenario checks flag any bypass.
2. Outputs of **M** (inferred learning-difficulty signals) must not flow into **D** for advertising or any secondary purpose. This is the judges' escalation step.
3. Any recommendation affecting a child sets `requires_human_decision = true`.

## Readiness framework cross-reference (to confirm with organisers)
Our brief lists 8 dimensions. The reference repo's `dimensions.json` (Readiness Framework Report 2.0, Jan 2026) uses different names. The cross-walk table will be added once we confirm which list judges score against.
