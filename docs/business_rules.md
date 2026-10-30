# ResolveIQ — Business Rules

**Document version:** 1.0
**Status:** Draft for implementation
**Project:** ResolveIQ — AI-Assisted Complaint Intelligence & Resolution System

This document defines the deterministic business rules used to classify, prioritize, assign, monitor, and resolve complaints. These are demonstration policies created for this project; they are not claimed to be official YottaFlex policies.

## 1. Design principles

1. Decisions must be explainable and reproducible.
2. Safety-related complaints take precedence over commercial value, sentiment, or workload.
3. Source records and event history must be preserved. State changes are appended as events rather than silently overwriting history.
4. Derived values must be calculated from source records and documented rules.
5. The same input data, configuration, and random seed must produce the same output.
6. Rules and SLA targets must be configurable; avoid embedding policy thresholds throughout application code.
7. Validation reports problems but does not silently repair data.

## 2. Complaint categories

Seed these ten categories:

| Code | Category | Default owning team |
|---|---|---|
| CAT-001 | PRODUCT_SAFETY | SAFETY_RESPONSE |
| CAT-002 | PRODUCT_QUALITY | PRODUCT_SUPPORT |
| CAT-003 | DELIVERY_DELAY | DELIVERY_OPERATIONS |
| CAT-004 | DAMAGED_DELIVERY | DELIVERY_OPERATIONS |
| CAT-005 | PAYMENT_ISSUE | BILLING |
| CAT-006 | REFUND_REQUEST | BILLING |
| CAT-007 | ORDER_CANCELLATION | ORDER_SUPPORT |
| CAT-008 | ACCOUNT_ACCESS | DIGITAL_SUPPORT |
| CAT-009 | CUSTOMER_SERVICE | CUSTOMER_CARE |
| CAT-010 | GENERAL_ENQUIRY | CUSTOMER_CARE |

The category-to-team mapping is configurable. The default mapping is a deterministic routing rule, not a machine-learning prediction.

## 3. Classification

Each complaint receives:
- `category_id`: one of the seeded categories;
- `sentiment`: `POSITIVE`, `NEUTRAL`, or `NEGATIVE`;
- `severity`: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`;
- `priority`: `P1`, `P2`, `P3`, or `P4`.

For this synthetic dataset, classification labels are generated from explicit scenario attributes and documented rules. Do not generate an arbitrary label independently of the complaint content or scenario.

### 3.1 Severity guidance

| Severity | Meaning | Example |
|---|---|---|
| LOW | Minor inconvenience, no material impact | General product question |
| MEDIUM | Service failure requiring follow-up | Delayed delivery |
| HIGH | Significant customer or financial impact | Expensive order failure |
| CRITICAL | Potential injury, fire, electrical hazard, or other safety risk | Product overheating |

A product safety issue must be classified as `CRITICAL`, unless a documented test case intentionally injects an incorrect value as an anomaly.

### 3.2 Sentiment guidance

Sentiment is a synthetic, rule-driven label. Use scenario attributes such as explicit positive/neutral/negative wording classes. Do not claim that a language model has inferred sentiment unless an actual model is implemented and evaluated.

## 4. Priority calculation

Priority is assigned in this order. The first matching rule wins.

| Rule order | Condition | Priority | Explanation |
|---|---|---|---|
| 1 | Product safety risk or `severity = CRITICAL` | P1 | Safety override |
| 2 | `severity = HIGH` | P2 | Significant impact |
| 3 | Repeat complaint with negative sentiment | Escalate one level from the base priority, but never above P1 | Recurrence escalation |
| 4 | High-value order and negative sentiment | At least P2 | Financial impact |
| 5 | Vulnerable-customer flag and negative sentiment | At least P2 | Additional care |
| 6 | Otherwise `severity = MEDIUM` | P3 | Standard handling |
| 7 | Otherwise `severity = LOW` | P4 | Routine handling |

### 4.1 Priority order

`P1` is highest urgency, followed by `P2`, `P3`, and `P4`.

For escalation, move one level toward P1:
- P4 becomes P3;
- P3 becomes P2;
- P2 becomes P1;
- P1 remains P1.

The high-value threshold is **₹50,000 (5,000,000 paise)** for the demonstration dataset. The vulnerable-customer flag is synthetic and must not represent a real person's sensitive attribute.

### 4.2 Explainability

For every triaged complaint, store or produce:
- the selected priority rule ID and version;
- the input conditions that matched;
- the resulting priority;
- a short human-readable decision reason.

A safety override reason should be explicit, e.g. `P1: product safety risk overrides all other factors`.

## 5. Assignment

### 5.1 Team routing

Route by complaint category using the category-to-team mapping in configuration. Safety complaints always route to `SAFETY_RESPONSE`.

### 5.2 Agent selection

Within the owning team:
1. Consider active agents only.
2. Calculate each agent's active workload as the count of currently assigned complaints in statuses `ASSIGNED`, `IN_PROGRESS`, `PENDING_CUSTOMER`, or `PENDING_APPROVAL`.
3. Select the agent with the lowest active workload.
4. Break ties by ascending immutable `agent_id`.

This produces deterministic assignment. It is a simple workload-count policy, not an optimized workforce scheduler.

### 5.3 Assignment history

- Every assignment or reassignment creates a new `Assignment` record.
- When an assignment is replaced, set the previous record's `unassigned_at` and `is_current = 0`; do not delete it.
- At most one current assignment may exist per complaint.
- An assignment may be team-only (`agent_id = NULL`) if no eligible agent is available.
- Record the reason for assignment or reassignment.

## 6. Service-level agreements (SLAs)

### 6.1 Clock model

Each complaint can have two independent clocks:
- `FIRST_RESPONSE`
- `RESOLUTION`

SLA calculations use **24/7 elapsed time**:
- nights and weekends count;
- public holidays count;
- no business-hours calendar is applied in version 1.

All timestamps are stored as ISO 8601 UTC timestamps. The generated reference timestamp is fixed by configuration so repeated runs are reproducible.

### 6.2 Target durations

| Priority | First-response target | Resolution target |
|---|---:|---:|
| P1 | 15 minutes | 4 hours |
| P2 | 1 hour | 8 hours |
| P3 | 4 hours | 24 hours |
| P4 | 8 hours | 72 hours |

These are illustrative project policy values and must be configurable.

### 6.3 Starting and stopping clocks

- Start both clocks when the complaint is triaged and enters the managed workflow.
- The first-response clock is met by the first qualifying outbound response from an agent to the customer.
- Stop the resolution clock when a resolution is marked `COMPLETED` and the complaint transitions to `RESOLVED`.
- A complaint closure after resolution does not rewrite the original resolution timestamp.

### 6.4 Pause and resume

For version 1, pause both active clocks only while the complaint is in `PENDING_CUSTOMER` or `PENDING_APPROVAL`. A pause and resume must each create an `SLAEvent` with timestamp, event type, reason, and optional actor.

- `PAUSE` is valid only when the clock is `RUNNING`.
- `RESUME` is valid only when the clock is `PAUSED`.
- `STOP` is valid only when the clock is `RUNNING` or `PAUSED`.
- Do not allow negative pause durations or overlapping pause intervals.
- The clock's accumulated paused minutes must reconcile with its pause/resume events.

The first-response clock should normally already be stopped when a complaint is waiting for the customer. If it is paused before the first response, that must be explainable by an explicit workflow event.

### 6.5 SLA outcome

At evaluation time:
- `MET`: qualifying event occurred on or before the adjusted deadline;
- `BREACHED`: adjusted deadline passed before the qualifying event;
- `RUNNING`: target has not yet been met and the adjusted deadline has not passed;
- `PAUSED`: currently paused;
- `STOPPED`: stopped for a documented reason without an SLA success/failure conclusion.

The adjusted deadline equals the original deadline plus accumulated paused time. Store the original target and event history so the result can be recomputed.

## 7. Complaint lifecycle

Allowed statuses:

`NEW`, `TRIAGED`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_CUSTOMER`, `PENDING_APPROVAL`, `RESOLVED`, `REOPENED`, `CLOSED`.

Allowed transitions:

| From | Allowed next status |
|---|---|
| NEW | TRIAGED |
| TRIAGED | ASSIGNED |
| ASSIGNED | IN_PROGRESS, PENDING_CUSTOMER, PENDING_APPROVAL |
| IN_PROGRESS | PENDING_CUSTOMER, PENDING_APPROVAL, RESOLVED |
| PENDING_CUSTOMER | IN_PROGRESS, RESOLVED |
| PENDING_APPROVAL | IN_PROGRESS, RESOLVED |
| RESOLVED | CLOSED, REOPENED |
| REOPENED | TRIAGED |
| CLOSED | No transition in version 1 |

Every transition creates a `ComplaintStatusEvent` containing the previous status, new status, timestamp, actor if applicable, and reason.

`Complaint.current_status` is a current-state projection. It must equal the latest status event's `to_status`. It does not replace the event history.

## 8. Repeat complaints

A complaint is a repeat when it is linked to an earlier complaint for the same customer and the same category within the configured **30-day** lookback window.

- Set `repeat_of_complaint_id` to the earlier complaint.
- Set `is_repeat = 1`.
- The earlier complaint must have an earlier `created_at`.
- Prefer the most recent matching earlier complaint as the parent.
- If no matching earlier complaint exists, `is_repeat = 0` and `repeat_of_complaint_id = NULL`.

A deliberately unlinked repeat complaint may be inserted only in the anomaly dataset and must have a matching ground-truth label.

## 9. Resolution and approval

Supported resolution types:

`REFUND`, `REPLACEMENT`, `REPAIR`, `INFORMATION`, `REJECTED`.

Resolution statuses:

`PROPOSED`, `APPROVED`, `COMPLETED`, `REJECTED`.

Rules:
- A resolution is a separate record; do not overwrite an earlier resolution when a complaint is reopened.
- A complaint may have multiple resolution records over its lifecycle.
- Refunds of **₹10,000 (1,000,000 paise) or more** require an approver.
- Safety-related resolutions involving a refund, replacement, or repair require approval before completion.
- Approval must be recorded with the approving agent and event time.
- A resolution marked `COMPLETED` must have a completion timestamp.
- A complaint may transition to `RESOLVED` only when a resolution is `COMPLETED`.

The refund threshold is a demonstration assumption and is configurable.

## 10. Customer messages and surveys

### 10.1 Messages

- Every message belongs to one complaint.
- `sender_type` is `CUSTOMER`, `AGENT`, or `SYSTEM`.
- Agent messages must reference a valid agent.
- Customer and system messages do not require an agent ID.
- An outbound agent response can satisfy the first-response SLA; inbound customer messages cannot.
- Message records are append-only.

### 10.2 Surveys

- A survey belongs to a resolution and may optionally reference the customer.
- Rating must be an integer from 1 through 5.
- A survey may be submitted only after its linked resolution is completed.
- Version 1 permits at most one survey per resolution.
- Survey absence is valid; do not invent a response for every resolution.

## 11. Data integrity and exception handling

The clean baseline dataset must pass all integrity checks with zero violations.

The anomaly dataset is created by copying the clean baseline and applying explicitly labelled, controlled mutations. Examples:
- complaint with a missing customer relationship (`customer_id = NULL`);
- complaint with a dangling customer ID;
- resolution timestamp before complaint creation;
- safety complaint assigned to a non-safety team or low priority;
- repeat complaint missing its repeat link;
- invalid SLA pause/resume sequence;
- survey submitted before resolution completion.

Anomalies must not be introduced by random corruption of unrelated fields. Each injected anomaly must have a ground-truth entry with:
- entity;
- record ID;
- issue type;
- expected decision.

The validator must report violations; it must not silently repair source data.

## 12. Determinism and reproducibility

- Use one configured master seed: `20261022`.
- Use a fixed reference date/time from configuration, not the machine's current clock.
- Use deterministic ID generation and deterministic tie-breaking.
- Avoid unseeded random generators.
- Run the generator twice with the same configuration and seed; compare row counts and file checksums.
- A scale setting may change record volumes, but it must not change the rules.

## 13. Configuration values

The following values belong in `config/business_rules.yaml`, not scattered across Python modules:

| Setting | Initial value |
|---|---|
| Repeat lookback | 30 days |
| High-value order threshold | 5,000,000 paise |
| Refund approval threshold | 1,000,000 paise |
| SLA calendar | 24/7 elapsed time |
| P1 first response / resolution | 15 / 240 minutes |
| P2 first response / resolution | 60 / 480 minutes |
| P3 first response / resolution | 240 / 1,440 minutes |
| P4 first response / resolution | 480 / 4,320 minutes |
| Master seed | 20261022 |

## 14. Known limitations and future enhancements

Version 1 uses deterministic, rule-based classification and assignment. It does not claim to use a trained AI/ML model. Potential future enhancements include:
- business-hours and holiday calendars;
- natural-language classification and sentiment models;
- capacity-weighted assignment and skills-based routing;
- configurable approval matrices;
- multi-currency support;
- a user interface and role-based authentication.

Any enhancement must preserve reproducibility, decision traceability, and validation coverage.
