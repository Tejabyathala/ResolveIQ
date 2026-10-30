# ResolveIQ — Database Architecture

**Document version:** 1.0  
**Project:** ResolveIQ — Explainable Complaint Intelligence & Resolution System  
**Database:** SQLite  
**Primary design goals:** relational integrity, traceability, explainable business decisions, reproducible synthetic data, and explicit anomaly detection.

---

## 1. Purpose and scope

ResolveIQ models a customer-support complaint workflow from purchase history through complaint intake, classification, prioritisation, assignment, SLA tracking, communication, resolution, and customer feedback.

The database is designed to:

- Preserve relationships between customers, orders, products, and complaints.
- Keep important changes as append-only history records instead of overwriting history.
- Make classification, priority, assignment, and SLA decisions explainable.
- Support clean baseline data and a separate dataset containing deliberately injected anomalies.
- Support reporting and reconciliation through SQL and Python.

This document describes the proposed logical schema. Physical SQLite DDL will be implemented after the schema and data dictionary are reviewed.

## 2. Design principles

1. **Stable business identifiers:** use readable IDs such as `CUS-000001` and `CMP-2026-000001` as primary keys.
2. **Referential integrity:** use foreign keys for relationships and enable `PRAGMA foreign_keys = ON` on every normal SQLite connection.
3. **History is append-only:** assignments, messages, status transitions, SLA events, and resolution attempts are separate records.
4. **Derived values have a source:** totals, paid/remaining amounts (if later added), SLA deadlines, and metrics must be calculated from source records or documented rules.
5. **Exceptions are explicit:** clean data is generated first. Anomalies are injected into a copy and recorded separately in ground truth.
6. **Time is reproducible:** generated timestamps use a configured fixed reference date and deterministic seed, not the machine's current clock.
7. **Rules are versioned:** priority rules have effective dates and a version so a historical decision can be explained.
8. **No hidden labels:** anomaly labels are kept in a separate ground-truth file/table, not mixed into ordinary input features.

## 3. Entity inventory

| Group | Entity | Purpose |
|---|---|---|
| Master data | Customer | Customer profile and synthetic vulnerability indicator |
| Master data | Product | Product catalogue and safety-related attributes |
| Master data | Category | Complaint categories |
| Master data | Team | Operational support teams |
| Master data | Agent | Agents who handle complaints |
| Governance | Role | Business roles for actors |
| Transactions | CustomerOrder | A customer's purchase/order header |
| Transactions | OrderItem | Products and quantities within an order; resolves the order-product many-to-many relationship |
| Transactions | Complaint | Main complaint record |
| Rules | PriorityRule | Effective-dated, explainable priority policy |
| Operations | Assignment | Assignment history for teams and agents |
| Operations | ComplaintMessage | Customer/business communication history |
| Operations | SLAClock | SLA clock configuration and current calculated state |
| Operations | SLAEvent | Append-only pause/resume/stop events |
| Operations | ComplaintStatusEvent | Append-only complaint lifecycle transitions |
| Outcomes | Resolution | One record for each resolution attempt |
| Outcomes | Survey | Customer feedback associated with a resolution |

**Naming note:** the physical table for an order is called `customer_order` to avoid using the SQL keyword `ORDER`.

## 4. Entity relationships and cardinalities

| Parent | Child | Cardinality | Relationship rule |
|---|---|---|---|
| Customer | CustomerOrder | 1:N | One customer can place many orders; each order belongs to one customer |
| CustomerOrder | OrderItem | 1:N | One order contains one or more order items |
| Product | OrderItem | 1:N | One product can appear in many order items |
| Customer | Complaint | 1:N, optional at complaint side | A customer can raise many complaints; `customer_id` is nullable only to support the missing-customer exception |
| CustomerOrder | Complaint | 1:N, optional at complaint side | A complaint may refer to an order; order may be unknown or unavailable |
| Product | Complaint | 1:N, optional at complaint side | A complaint may refer to a specific product |
| Category | Complaint | 1:N | Each classified complaint has one category; classification may be pending at intake if the implementation allows a nullable category |
| PriorityRule | Complaint | 1:N | A complaint records the rule/version used for its priority decision |
| Team | Agent | 1:N | An agent belongs to one primary team in the initial model |
| Role | Agent | 1:N | Each agent has one primary role in the initial model |
| Complaint | Assignment | 1:N | A complaint can be assigned or reassigned many times |
| Team | Assignment | 1:N | A team can receive many assignment records |
| Agent | Assignment | 1:N, optional | An assignment may be team-only while awaiting an individual agent |
| Complaint | ComplaintMessage | 1:N | A complaint has many messages |
| Complaint | SLAClock | 1:N | A complaint can have separate first-response and resolution clocks |
| SLAClock | SLAEvent | 1:N | A clock has many pause, resume, and stop events |
| Complaint | ComplaintStatusEvent | 1:N | Every status transition is recorded |
| Complaint | Resolution | 1:N | A complaint can be resolved, reopened, and resolved again |
| Resolution | Survey | 1:N, optional | A resolution may receive zero or more survey responses |

### 4.1 Why OrderItem is necessary

An order can contain multiple products, and the same product can appear in many orders. This is a many-to-many relationship. `OrderItem` is the bridge table and stores relationship-specific attributes such as quantity and unit price at the time of purchase.

### 4.2 Why history tables are necessary

Do not store only the latest assigned agent or latest complaint status. Keep each assignment and status transition as a separate record. A current state can be obtained from the latest valid event, while the full history remains auditable.

### 4.3 Optional relationships

- `Complaint.customer_id` is nullable to represent the required missing-customer exception.
- `Complaint.order_id` can be nullable for complaints where the customer cannot provide an order reference.
- `Complaint.product_id` can be nullable where the complaint is not product-specific or the product is unknown.
- `Assignment.agent_id` can be nullable when a team owns the case before an individual agent is selected.
- `ComplaintStatusEvent.actor_agent_id` can be nullable for automated system events.
- `Survey` is optional because customers may not respond.
- `Complaint.category_id` and `Complaint.priority_rule_id` may be nullable only while a complaint is awaiting classification. Once triaged, they should be populated.

The anomaly scenario “complaint without customer” should be represented explicitly. A `NULL` customer reference is a valid representation of a missing relationship when the business rule permits it; a dangling ID such as `CUS-999999` is a separate referential-integrity violation. Keep these as distinct anomaly types if both are included.

## 5. Proposed entity fields

The detailed field-level data dictionary will be maintained in `data_dictionary.md`. The following is the logical field outline.

### 5.1 Customer

- `customer_id` — PK; format `CUS-000001`
- `full_name`
- `email`
- `phone`
- `created_at`
- `is_vulnerable` — synthetic business flag; not a real-world sensitive classification

### 5.2 Product

- `product_id` — PK; format `PRD-000001`
- `product_name`
- `product_category`
- `unit_price`
- `is_safety_critical`
- `is_active`

### 5.3 CustomerOrder

- `order_id` — PK; format `ORD-2026-000001`
- `customer_id` — FK to Customer
- `order_date`
- `order_status`
- `order_total` — derived from order items
- `currency_code`

### 5.4 OrderItem

- `order_item_id` — PK; format `OIT-000001`
- `order_id` — FK to CustomerOrder
- `product_id` — FK to Product
- `quantity`
- `unit_price`
- `line_total` — derived as quantity multiplied by unit price

### 5.5 Complaint

- `complaint_id` — PK; format `CMP-2026-000001`
- `customer_id` — nullable FK to Customer
- `order_id` — nullable FK to CustomerOrder
- `product_id` — nullable FK to Product
- `category_id` — nullable during intake; FK to Category
- `priority_rule_id` — nullable until triage; FK to PriorityRule
- `channel` — e.g. EMAIL, PHONE, WEB, CHAT, SOCIAL
- `subject`
- `description`
- `sentiment` — e.g. POSITIVE, NEUTRAL, NEGATIVE
- `severity` — e.g. LOW, MEDIUM, HIGH, CRITICAL
- `priority` — P1, P2, P3, P4
- `is_repeat` — derived/validated from prior related complaints
- `repeat_of_complaint_id` — nullable self-FK to Complaint
- `created_at`
- `current_status` — convenient current-state projection; must agree with the latest status event
- `closed_at` — nullable; populated when the complaint is closed

### 5.6 Category

- `category_id` — PK; format `CAT-001`
- `category_name` — unique
- `description`
- `is_active`

### 5.7 PriorityRule

- `priority_rule_id` — PK; format `PR-001`
- `rule_name`
- `rule_version`
- `priority`
- `conditions_json` — structured rule conditions
- `effective_from`
- `effective_to` — nullable for currently effective rule
- `is_active`

### 5.8 Team

- `team_id` — PK; format `TEAM-001`
- `team_name` — unique
- `description`
- `is_active`

### 5.9 Agent

- `agent_id` — PK; format `AGT-000001`
- `team_id` — FK to Team
- `role_id` — FK to Role
- `display_name`
- `email` — unique synthetic email
- `is_active`
- `capacity_weight` — positive workload/capacity factor used by deterministic assignment logic

### 5.10 Role

- `role_id` — PK; format `ROLE-001`
- `role_name` — unique
- `description`

Seed roles should cover the business actors in the problem statement: BUSINESS_REQUESTER, PROCESS_OWNER, APPROVER, OPERATIONS_ANALYST, SYSTEM_ADMINISTRATOR. Customer/requester identity can be represented by Customer, while staff actors are represented by Agent with a Role. Automated system actions should use a distinct actor type or a nullable agent reference with an explicit system actor label.

### 5.11 Assignment

- `assignment_id` — PK; format `ASN-<complaint-id>-001`
- `complaint_id` — FK to Complaint
- `team_id` — FK to Team
- `agent_id` — nullable FK to Agent
- `assigned_at`
- `unassigned_at` — nullable
- `assigned_by_agent_id` — nullable FK to Agent
- `assignment_reason`
- `is_current`

Only one assignment per complaint should be current at a time. Historical assignment rows remain unchanged after they end.

### 5.12 ComplaintMessage

- `message_id` — PK; format `MSG-<complaint-id>-001`
- `complaint_id` — FK to Complaint
- `sender_type` — CUSTOMER, AGENT, SYSTEM
- `sender_agent_id` — nullable FK to Agent
- `channel`
- `message_direction` — INBOUND or OUTBOUND
- `message_text`
- `sent_at`

### 5.13 SLAClock

- `sla_clock_id` — PK; format `SLA-<complaint-id>-<clock-type>`
- `complaint_id` — FK to Complaint
- `clock_type` — FIRST_RESPONSE or RESOLUTION
- `started_at`
- `target_minutes`
- `deadline_at` — calculated from start, target, and pause policy
- `stopped_at` — nullable
- `clock_status` — RUNNING, PAUSED, STOPPED, BREACHED, MET
- `total_paused_minutes` — derived from SLA events

Use a uniqueness constraint on (`complaint_id`, `clock_type`) for the initial design, so one complaint has at most one first-response clock and one resolution clock.

### 5.14 SLAEvent

- `sla_event_id` — PK; format `SLEV-000001`
- `sla_clock_id` — FK to SLAClock
- `event_type` — PAUSE, RESUME, STOP
- `event_at`
- `reason`
- `actor_agent_id` — nullable FK to Agent

Events are append-only. Pause and resume pairs must be chronologically valid. Paused duration and adjusted deadline must reconcile with the event history.

### 5.15 ComplaintStatusEvent

- `status_event_id` — PK; format `CSE-000001`
- `complaint_id` — FK to Complaint
- `from_status` — nullable for the initial event
- `to_status`
- `changed_at`
- `actor_agent_id` — nullable FK to Agent
- `reason`

Possible lifecycle states: NEW, TRIAGED, ASSIGNED, IN_PROGRESS, PENDING_CUSTOMER, PENDING_APPROVAL, RESOLVED, REOPENED, CLOSED. Allowed transitions will be defined in `business_rules.md`.

### 5.16 Resolution

- `resolution_id` — PK; format `RES-<complaint-id>-001`
- `complaint_id` — FK to Complaint
- `resolution_type` — e.g. REFUND, REPLACEMENT, REPAIR, INFORMATION, REJECTED
- `resolution_notes`
- `resolved_at`
- `approved_by_agent_id` — nullable FK to Agent
- `resolution_status` — PROPOSED, APPROVED, COMPLETED, REJECTED

A reopened complaint may have a later resolution record. Do not overwrite an earlier resolution.

### 5.17 Survey

- `survey_id` — PK; format `SUR-000001`
- `resolution_id` — FK to Resolution
- `customer_id` — nullable FK to Customer for exceptional/missing-customer cases
- `rating` — integer 1–5
- `feedback` — nullable
- `submitted_at`

A survey must not be submitted before its associated resolution is completed. For a straightforward evaluation dataset, permit at most one survey per resolution; this can be relaxed later if multiple survey channels are required.

## 6. Keys, uniqueness, and validation constraints

At minimum, implement these constraints in SQLite and/or application validation:

- Every primary key is non-null and unique.
- Business identifiers follow their documented formats and are immutable after creation.
- `CustomerOrder.customer_id` must reference an existing customer.
- `OrderItem.order_id` and `OrderItem.product_id` must reference existing records.
- `quantity > 0`, `unit_price >= 0`, and `line_total = quantity * unit_price`.
- `order_total` must equal the sum of its order-item line totals.
- Complaint priority must be one of P1, P2, P3, P4.
- Complaint severity must be one of LOW, MEDIUM, HIGH, CRITICAL.
- `repeat_of_complaint_id`, if present, must reference an earlier complaint and must not reference itself.
- Assignment end time cannot precede assignment start time.
- At most one current assignment exists per complaint.
- Message and event timestamps must be valid and must not precede complaint creation.
- SLA target minutes must be positive.
- SLA pause/resume events must form valid chronological pairs.
- Resolution cannot precede complaint creation.
- Survey cannot precede completion of its resolution.
- Status changes must follow the allowed lifecycle transition map.
- Current-state fields must reconcile with the latest history event.

SQLite `CHECK` constraints should enforce row-local rules. Cross-row and chronological rules should be checked by the application validator and tests.

## 7. Complaint lifecycle

The proposed lifecycle is:

```text
NEW
  -> TRIAGED
  -> ASSIGNED
  -> IN_PROGRESS
  -> PENDING_CUSTOMER / PENDING_APPROVAL (when required)
  -> IN_PROGRESS
  -> RESOLVED
  -> CLOSED

RESOLVED -> REOPENED -> TRIAGED / ASSIGNED -> ... -> RESOLVED
```

This is an illustrative transition map. The authoritative allowed transitions, including actor permissions and exceptional paths, will be defined in `business_rules.md`.

Every transition must create a `ComplaintStatusEvent`. Updating `Complaint.current_status` is allowed as a current-state projection, but it must be updated in the same transaction as the event and validated against the event history.

## 8. SQLite implementation notes

- Use SQLite for the local relational store.
- Enable foreign keys on every normal connection using `PRAGMA foreign_keys = ON`.
- Use transactions for multi-table operations.
- Store monetary values as integer minor units (for example, paise) or as carefully validated decimal strings; do not use binary floating-point for financial arithmetic. The final physical schema will choose one consistent representation.
- Store timestamps in a consistent ISO 8601 format and document the timezone convention. Prefer UTC timestamps for event storage, with generated data based on a fixed reference date.
- Create indexes on foreign keys and frequently filtered columns such as complaint status, priority, created date, customer ID, and order ID.
- Use deterministic seed data and stable ordering for reproducible exports.
- Do not disable foreign-key enforcement during ordinary generation. If an anomaly requires a dangling foreign key, create it only in the separate anomaly dataset using a controlled injection procedure, then run explicit integrity checks.

## 9. Clean and anomaly dataset strategy

### Clean baseline

1. Generate master data first.
2. Generate dependent orders and order items.
3. Generate complaints and their related events.
4. Apply documented classification, priority, assignment, and SLA rules.
5. Run all validators.
6. Expected result: zero unexpected validation violations.

### Anomaly dataset

1. Copy the clean dataset.
2. Inject only documented anomalies into selected records.
3. Write expected labels to a separate ground-truth file/table.
4. Run validators without silently repairing records.
5. Compare detected anomalies with ground truth.

Candidate anomaly types:

| Anomaly type | Example |
|---|---|
| Missing customer | Complaint has no customer reference |
| Dangling customer FK | Complaint references `CUS-999999` |
| Resolution before complaint | Resolution timestamp precedes complaint creation |
| Incorrect SLA pause | Pause/resume history does not reconcile with deadline |
| Unlinked repeat complaint | Repeat case has no valid link to its earlier case |
| Unsafe low-priority assignment | Safety-critical case assigned to an inappropriate low-priority queue |
| Survey before closure | Survey submitted before its resolution is completed |

A nullable customer relationship and a dangling customer ID are different cases: the first may be permitted as an exception; the second violates referential integrity. Document expected validator behavior for each.

Ground-truth columns should include at least:

- `entity`
- `record_id`
- `issue_type`
- `expected_decision`

Do not add an `is_anomaly` label to normal source feature tables.

## 10. Initial scale targets

| Entity | Full-scale target |
|---|---:|
| Customer | 5,000 |
| Product | Configurable; initial target 500 |
| CustomerOrder | 8,000 |
| OrderItem | Derived; multiple items per order |
| Complaint | 2,000 |
| ComplaintMessage | 6,000 |
| Category | 10 |
| Team | Configurable; initial target 5 |
| Agent | Configurable; initial target 50 |
| PriorityRule | Configurable, versioned rule set |
| Assignment | At least one per triaged complaint, plus reassignment history |
| SLAClock | Up to 2 per complaint |
| SLAEvent | Derived from pause/resume scenarios |
| ComplaintStatusEvent | Multiple per complaint |
| Resolution | At least one for resolved complaints; more for reopened cases |
| Survey | Optional; subset of completed resolutions |
| Role | 5 core roles |

All counts must be configurable. A smaller starter scale should use the same generator and business rules as full scale.

## 11. Open decisions to finalize before DDL

The following are implementation choices to settle in the data dictionary and business-rules document:

1. Whether monetary values are stored as integer paise or decimal strings. Recommendation: integer paise for exact arithmetic.
2. The exact ten complaint categories.
3. Priority thresholds and safety override behavior.
4. First-response and resolution SLA durations for each priority.
5. Exact status transition permissions.
6. Whether the initial data model needs multiple roles per agent. Recommendation: one primary role initially; extend with a bridge table only if required.
7. Whether survey is one-per-resolution or supports multiple responses. Recommendation: one-per-resolution for the initial challenge.

## 12. Definition of done for database design

The database design phase is ready for implementation when:

- Every entity has a documented purpose and primary key.
- Every foreign key and cardinality is documented.
- Optional relationships and exception semantics are explicit.
- The data dictionary defines type, required status, allowed values, uniqueness, units, and validation.
- Lifecycle transitions and event-history behavior are documented.
- Clean-data and anomaly-data expectations are documented.
- The schema can be implemented without ambiguous relationships.

---

**Status:** Logical architecture draft. This document is a design artifact, not yet the executable SQLite schema. The next step is to complete `data_dictionary.md`, finalize the business-rule assumptions, and then implement and test `schema.sql`.
