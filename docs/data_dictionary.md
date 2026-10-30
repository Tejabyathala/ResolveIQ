# ResolveIQ — Data Dictionary

**Document version:** 1.0  
**Related document:** `architecture.md`  
**Database:** SQLite  
**Money representation:** Integer minor units (paise for INR)  
**Timestamp representation:** ISO 8601 UTC strings, for example `2026-10-30T04:00:00Z`

This document defines the fields, types, nullability, allowed values, uniqueness rules, and validation expectations for the ResolveIQ logical schema.

## 1. Conventions

### 1.1 SQLite type conventions

| Logical type | SQLite storage | Meaning |
|---|---|---|
| Identifier | `TEXT` | Stable business ID |
| Short text | `TEXT` | Bounded string validated by application |
| Long text | `TEXT` | Description, notes, or message body |
| Integer | `INTEGER` | Whole number |
| Money | `INTEGER` | Amount in minor currency units; INR values are paise |
| Boolean | `INTEGER` | `0` = false, `1` = true |
| Date | `TEXT` | ISO `YYYY-MM-DD` |
| Timestamp | `TEXT` | ISO 8601 UTC timestamp |
| JSON | `TEXT` | Valid JSON document, checked by application or SQLite JSON functions |

`Required = Yes` means `NOT NULL`, unless the field is a generated value populated before insertion. `Unique = Yes` means a unique constraint or unique index is required.

### 1.2 Identifier formats

| Entity | Format | Example |
|---|---|---|
| Customer | `CUS-` + 6 digits | `CUS-000001` |
| Product | `PRD-` + 6 digits | `PRD-000001` |
| CustomerOrder | `ORD-YYYY-` + 6 digits | `ORD-2026-000001` |
| OrderItem | `OIT-` + 6 digits | `OIT-000001` |
| Complaint | `CMP-YYYY-` + 6 digits | `CMP-2026-000001` |
| Category | `CAT-` + 3 digits | `CAT-001` |
| PriorityRule | `PR-` + 3 digits + version suffix if needed | `PR-001` |
| Team | `TEAM-` + 3 digits | `TEAM-001` |
| Agent | `AGT-` + 6 digits | `AGT-000001` |
| Role | `ROLE-` + 3 digits | `ROLE-001` |
| Assignment | `ASN-<complaint-id>-` + 3 digits | `ASN-CMP-2026-000001-001` |
| ComplaintMessage | `MSG-<complaint-id>-` + 3 digits | `MSG-CMP-2026-000001-001` |
| SLAClock | `SLA-<complaint-id>-<clock-type>` | `SLA-CMP-2026-000001-FIRST_RESPONSE` |
| SLAEvent | `SLEV-` + 6 digits | `SLEV-000001` |
| ComplaintStatusEvent | `CSE-` + 6 digits | `CSE-000001` |
| Resolution | `RES-<complaint-id>-` + 3 digits | `RES-CMP-2026-000001-001` |
| Survey | `SUR-` + 6 digits | `SUR-000001` |

IDs are immutable after creation. The year component comes from the configured generation reference date, not the machine clock.

## 2. Master data entities

### 2.1 Customer

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `customer_id` | TEXT | Yes | PK | `CUS-` plus six digits; immutable |
| `full_name` | TEXT | Yes | — | 2–100 characters after trimming |
| `email` | TEXT | Yes | Unique | Valid synthetic email; normalize case before uniqueness check |
| `phone` | TEXT | Yes | Unique | Synthetic phone in documented format; store as text to preserve leading zeros and `+` |
| `created_at` | TEXT | Yes | — | Valid ISO 8601 UTC timestamp |

**Generation note:** Customer vulnerability is better represented as a synthetic operational flag only if the business scenario needs it. It must not represent or infer a real person's protected or sensitive trait.

### 2.2 Product

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `product_id` | TEXT | Yes | PK | `PRD-` plus six digits |
| `product_name` | TEXT | Yes | — | 2–120 characters |
| `product_category` | TEXT | Yes | — | Controlled product category from configuration |
| `unit_price_paise` | INTEGER | Yes | — | Integer; `>= 0` |
| `is_safety_critical` | INTEGER | Yes | — | Boolean: `0` or `1` |
| `is_active` | INTEGER | Yes | — | Boolean: `0` or `1` |

### 2.3 Category

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `category_id` | TEXT | Yes | PK | `CAT-` plus three digits |
| `category_name` | TEXT | Yes | Unique | 2–60 characters |
| `description` | TEXT | No | — | Up to 500 characters |
| `is_active` | INTEGER | Yes | — | Boolean: `0` or `1` |

**Initial category set (10):** PRODUCT_DAMAGE, LATE_DELIVERY, WRONG_ITEM, MISSING_ITEM, REFUND_REQUEST, PAYMENT_ISSUE, PRODUCT_DEFECT, ORDER_CANCELLATION, ACCOUNT_ISSUE, OTHER. These are configurable seed values, not hard-coded assumptions in validation logic.

### 2.4 Team

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `team_id` | TEXT | Yes | PK | `TEAM-` plus three digits |
| `team_name` | TEXT | Yes | Unique | 2–80 characters |
| `description` | TEXT | No | — | Up to 500 characters |
| `is_active` | INTEGER | Yes | — | Boolean: `0` or `1` |

### 2.5 Role

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `role_id` | TEXT | Yes | PK | `ROLE-` plus three digits |
| `role_name` | TEXT | Yes | Unique | BUSINESS_REQUESTER, PROCESS_OWNER, APPROVER, OPERATIONS_ANALYST, SYSTEM_ADMINISTRATOR |
| `description` | TEXT | No | — | Up to 500 characters |

The customer is the business requester in the initial model. Staff actors are represented by Agent and their primary Role. Automated events use an explicit system actor value rather than inventing a staff agent.

### 2.6 Agent

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `agent_id` | TEXT | Yes | PK | `AGT-` plus six digits |
| `team_id` | TEXT | Yes | FK → Team | Must reference an existing team |
| `role_id` | TEXT | Yes | FK → Role | Must reference an existing role |
| `display_name` | TEXT | Yes | — | 2–100 characters |
| `email` | TEXT | Yes | Unique | Valid synthetic email; normalized |
| `is_active` | INTEGER | Yes | — | Boolean: `0` or `1` |
| `capacity_weight` | INTEGER | Yes | — | Positive integer; default `1`; used by deterministic workload balancing |

## 3. Transaction entities

### 3.1 CustomerOrder

Physical table name: `customer_order`.

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `order_id` | TEXT | Yes | PK | `ORD-YYYY-` plus six digits |
| `customer_id` | TEXT | Yes | FK → Customer | Must reference an existing customer |
| `order_date` | TEXT | Yes | — | ISO date; not after configured reference date |
| `order_status` | TEXT | Yes | — | PLACED, PROCESSING, SHIPPED, DELIVERED, CANCELLED, RETURNED |
| `order_total_paise` | INTEGER | Yes | — | `>= 0`; equals sum of its order-item line totals |
| `currency_code` | TEXT | Yes | — | ISO 4217 code; initial dataset uses `INR` |

### 3.2 OrderItem

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `order_item_id` | TEXT | Yes | PK | `OIT-` plus six digits |
| `order_id` | TEXT | Yes | FK → CustomerOrder | Must reference an existing order |
| `product_id` | TEXT | Yes | FK → Product | Must reference an existing product |
| `quantity` | INTEGER | Yes | — | Integer `> 0` |
| `unit_price_paise` | INTEGER | Yes | — | Integer `>= 0`; snapshot price at purchase time |
| `line_total_paise` | INTEGER | Yes | — | Must equal `quantity * unit_price_paise` |

Recommended uniqueness: (`order_id`, `product_id`) if duplicate product lines are not required. If separate lines for the same product are meaningful, omit this constraint and retain the distinct `order_item_id`.

### 3.3 Complaint

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `complaint_id` | TEXT | Yes | PK | `CMP-YYYY-` plus six digits |
| `customer_id` | TEXT | No | FK → Customer | Nullable for documented missing-customer exception; otherwise valid customer |
| `order_id` | TEXT | No | FK → CustomerOrder | Nullable if order is unknown or not applicable |
| `product_id` | TEXT | No | FK → Product | Nullable if product is unknown or complaint is not product-specific |
| `category_id` | TEXT | No | FK → Category | Nullable only while awaiting classification |
| `priority_rule_id` | TEXT | No | FK → PriorityRule | Nullable only while awaiting triage |
| `channel` | TEXT | Yes | — | EMAIL, PHONE, WEB, CHAT, SOCIAL |
| `subject` | TEXT | Yes | — | 3–160 characters |
| `description` | TEXT | Yes | — | 1–5,000 characters |
| `sentiment` | TEXT | Yes | — | POSITIVE, NEUTRAL, NEGATIVE |
| `severity` | TEXT | Yes | — | LOW, MEDIUM, HIGH, CRITICAL |
| `priority` | TEXT | Yes | — | P1, P2, P3, P4 |
| `is_repeat` | INTEGER | Yes | — | Boolean: `0` or `1`; reconcile with prior complaints |
| `repeat_of_complaint_id` | TEXT | No | Self-FK → Complaint | Must reference an earlier complaint; cannot reference itself |
| `created_at` | TEXT | Yes | — | ISO 8601 UTC timestamp |
| `current_status` | TEXT | Yes | — | NEW, TRIAGED, ASSIGNED, IN_PROGRESS, PENDING_CUSTOMER, PENDING_APPROVAL, RESOLVED, REOPENED, CLOSED |
| `closed_at` | TEXT | No | — | ISO timestamp; cannot precede creation; set only when closed |

**Cross-field validation:**
- If `is_repeat = 0`, `repeat_of_complaint_id` should be NULL.
- If `is_repeat = 1`, a valid earlier related complaint should be identified.
- If both customer and order are present, the order's customer must match the complaint's customer.
- If product and order are present, the product should appear in one of that order's OrderItem rows unless a documented exception applies.
- `current_status` must agree with the latest ComplaintStatusEvent.

## 4. Business rules entity

### 4.1 PriorityRule

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `priority_rule_id` | TEXT | Yes | PK | `PR-` plus three digits for the initial version set |
| `rule_name` | TEXT | Yes | — | 3–100 characters |
| `rule_version` | INTEGER | Yes | — | Integer `>= 1` |
| `priority` | TEXT | Yes | — | P1, P2, P3, P4 |
| `conditions_json` | TEXT | Yes | — | Valid JSON describing the rule conditions |
| `effective_from` | TEXT | Yes | — | ISO 8601 UTC timestamp |
| `effective_to` | TEXT | No | — | Must be later than `effective_from` |
| `is_active` | INTEGER | Yes | — | Boolean: `0` or `1` |

Recommended uniqueness: (`rule_name`, `rule_version`). Effective periods for versions of the same rule should not overlap unless precedence is explicitly defined.

## 5. Operations and history entities

### 5.1 Assignment

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `assignment_id` | TEXT | Yes | PK | `ASN-<complaint-id>-NNN` |
| `complaint_id` | TEXT | Yes | FK → Complaint | Must reference an existing complaint |
| `team_id` | TEXT | Yes | FK → Team | Must reference an existing team |
| `agent_id` | TEXT | No | FK → Agent | Nullable while team owns case without an individual agent |
| `assigned_at` | TEXT | Yes | — | ISO timestamp; not before complaint creation |
| `unassigned_at` | TEXT | No | — | If present, must be >= `assigned_at` |
| `assigned_by_agent_id` | TEXT | No | FK → Agent | Nullable for system-generated assignment |
| `assignment_reason` | TEXT | Yes | — | 3–500 characters |
| `is_current` | INTEGER | Yes | — | Boolean: `0` or `1` |

Cross-row rule: at most one assignment per complaint may have `is_current = 1`. If `agent_id` is present, its team should match `team_id` at assignment time.

### 5.2 ComplaintMessage

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `message_id` | TEXT | Yes | PK | `MSG-<complaint-id>-NNN` |
| `complaint_id` | TEXT | Yes | FK → Complaint | Must reference an existing complaint |
| `sender_type` | TEXT | Yes | — | CUSTOMER, AGENT, SYSTEM |
| `sender_agent_id` | TEXT | No | FK → Agent | Required when sender type is AGENT; NULL for CUSTOMER or SYSTEM |
| `channel` | TEXT | Yes | — | EMAIL, PHONE, WEB, CHAT, SOCIAL |
| `message_direction` | TEXT | Yes | — | INBOUND, OUTBOUND |
| `message_text` | TEXT | Yes | — | 1–5,000 characters |
| `sent_at` | TEXT | Yes | — | ISO timestamp; not before complaint creation |

### 5.3 SLAClock

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `sla_clock_id` | TEXT | Yes | PK | `SLA-<complaint-id>-<clock-type>` |
| `complaint_id` | TEXT | Yes | FK → Complaint | Must reference an existing complaint |
| `clock_type` | TEXT | Yes | — | FIRST_RESPONSE, RESOLUTION |
| `started_at` | TEXT | Yes | — | ISO timestamp |
| `target_minutes` | INTEGER | Yes | — | Integer `> 0` |
| `deadline_at` | TEXT | Yes | — | Calculated deadline after applying documented pause policy |
| `stopped_at` | TEXT | No | — | If present, must be >= `started_at` |
| `clock_status` | TEXT | Yes | — | RUNNING, PAUSED, STOPPED, BREACHED, MET |
| `total_paused_minutes` | INTEGER | Yes | — | Integer `>= 0`; reconciles with SLAEvent history |

Recommended uniqueness: (`complaint_id`, `clock_type`).

### 5.4 SLAEvent

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `sla_event_id` | TEXT | Yes | PK | `SLEV-` plus six digits |
| `sla_clock_id` | TEXT | Yes | FK → SLAClock | Must reference an existing SLA clock |
| `event_type` | TEXT | Yes | — | PAUSE, RESUME, STOP |
| `event_at` | TEXT | Yes | — | ISO timestamp; within clock lifecycle |
| `reason` | TEXT | Yes | — | 3–300 characters |
| `actor_agent_id` | TEXT | No | FK → Agent | NULL for system events |

Chronology rule: PAUSE must occur while running; RESUME must follow a PAUSE; STOP must occur while running or paused according to the documented policy. No duplicate consecutive PAUSE or RESUME events.

### 5.5 ComplaintStatusEvent

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `status_event_id` | TEXT | Yes | PK | `CSE-` plus six digits |
| `complaint_id` | TEXT | Yes | FK → Complaint | Must reference an existing complaint |
| `from_status` | TEXT | No | — | NULL only for initial event; otherwise valid lifecycle state |
| `to_status` | TEXT | Yes | — | NEW, TRIAGED, ASSIGNED, IN_PROGRESS, PENDING_CUSTOMER, PENDING_APPROVAL, RESOLVED, REOPENED, CLOSED |
| `changed_at` | TEXT | Yes | — | ISO timestamp; not before complaint creation |
| `actor_agent_id` | TEXT | No | FK → Agent | NULL for automated system events |
| `reason` | TEXT | Yes | — | 3–500 characters |

Cross-row rules: event timestamps must be ordered for each complaint; each event's `from_status` must match the preceding event's `to_status`; the transition must be permitted by the lifecycle map.

## 6. Outcome entities

### 6.1 Resolution

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `resolution_id` | TEXT | Yes | PK | `RES-<complaint-id>-NNN` |
| `complaint_id` | TEXT | Yes | FK → Complaint | Must reference an existing complaint |
| `resolution_type` | TEXT | Yes | — | REFUND, REPLACEMENT, REPAIR, INFORMATION, REJECTED |
| `resolution_notes` | TEXT | Yes | — | 3–2,000 characters |
| `resolved_at` | TEXT | Yes | — | ISO timestamp; not before complaint creation |
| `approved_by_agent_id` | TEXT | No | FK → Agent | Nullable when approval is not required |
| `resolution_status` | TEXT | Yes | — | PROPOSED, APPROVED, COMPLETED, REJECTED |

A complaint may have multiple resolution records if it is reopened and resolved again. A completed resolution must have a corresponding valid status transition.

### 6.2 Survey

| Field | SQLite type | Required | Key / unique | Allowed values / validation |
|---|---|---:|---|---|
| `survey_id` | TEXT | Yes | PK | `SUR-` plus six digits |
| `resolution_id` | TEXT | Yes | FK → Resolution | Must reference an existing resolution |
| `customer_id` | TEXT | No | FK → Customer | Nullable only for documented missing-customer cases |
| `rating` | INTEGER | Yes | — | Integer from 1 through 5 |
| `feedback` | TEXT | No | — | Up to 2,000 characters |
| `submitted_at` | TEXT | Yes | — | ISO timestamp; must not precede resolution completion |

Recommended uniqueness: `resolution_id` for one survey per resolution in the initial implementation.

## 7. Cross-entity validation matrix

| Validation | Tables involved | Expected behavior |
|---|---|---|
| Primary key uniqueness | All | No duplicate IDs |
| Customer-order relationship | Customer, CustomerOrder | Every order has an existing customer |
| Order item references | CustomerOrder, OrderItem, Product | Every item references an existing order and product |
| Order total reconciliation | CustomerOrder, OrderItem | Header total equals sum of line totals |
| Complaint customer/order consistency | Complaint, CustomerOrder | If both exist, order belongs to the same customer |
| Complaint product/order consistency | Complaint, OrderItem | Product should belong to referenced order |
| Repeat complaint linkage | Complaint | Repeat flag and predecessor reference agree |
| Assignment history | Complaint, Assignment, Team, Agent | Valid references, time ranges, and at most one current assignment |
| Message chronology | Complaint, ComplaintMessage | Messages do not predate complaint creation |
| Status lifecycle | Complaint, ComplaintStatusEvent | Valid transitions and current-state reconciliation |
| SLA reconciliation | SLAClock, SLAEvent | Pause/resume history reconciles with paused duration and deadline |
| Resolution chronology | Complaint, Resolution | Resolution does not predate complaint |
| Survey chronology | Resolution, Survey | Survey does not predate completed resolution |
| Rule effectiveness | PriorityRule, Complaint | Rule used was effective at decision time |

## 8. Data-generation and validation notes

- Use one configured seed, initially `20261022`, and pass it to all random generators.
- Use a fixed `reference_datetime` in configuration for generated dates and IDs.
- Generate master records before dependent records.
- Generate `CustomerOrder` totals from `OrderItem` rows; never generate both independently.
- Store INR values as integer paise. For display, format paise as rupees by dividing by 100 only at the presentation/reporting boundary.
- Keep ground-truth labels outside ordinary business records.
- Do not silently repair invalid rows during validation.
- Record validation findings with entity, record ID, issue type, severity, and explanation.
- Use the same schema and business rules for starter and full scale.

## 9. Decisions to carry into business_rules.md

The following are policy choices, not facts supplied by the challenge. They must be documented as configurable assumptions:

1. Exact priority scoring and safety override.
2. First-response and resolution SLA targets for each priority.
3. Which statuses pause which SLA clocks.
4. Which roles may approve refunds or other resolutions.
5. Allowed status transitions and reopening conditions.
6. Assignment balancing and team-routing rules.
7. Which complaint categories are considered safety-related.
8. Repeat-complaint matching window and matching criteria.

---

**Status:** Field-level data dictionary draft. Review against `architecture.md` before creating the executable SQLite schema in `src/database/schema.sql`.
