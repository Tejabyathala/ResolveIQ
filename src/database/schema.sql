
-- ResolveIQ Database Schema
-- Phase 1: Master Data Tables

PRAGMA foreign_keys = ON;

-- 1. Customer
CREATE TABLE IF NOT EXISTS customer (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    phone TEXT NOT NULL UNIQUE,
    is_vulnerable INTEGER NOT NULL DEFAULT 0
        CHECK (is_vulnerable IN (0, 1)),
    created_at TEXT NOT NULL
);

-- 2. Product
CREATE TABLE IF NOT EXISTS product (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL,
    unit_price_paise INTEGER NOT NULL
        CHECK (unit_price_paise >= 0),
    is_safety_critical INTEGER NOT NULL DEFAULT 0
        CHECK (is_safety_critical IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL
);

-- 3. Category
CREATE TABLE IF NOT EXISTS category (
    category_id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1))
);

-- 4. Team
CREATE TABLE IF NOT EXISTS team (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1))
);

-- 5. Role
CREATE TABLE IF NOT EXISTS role (
    role_id TEXT PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- 6. Agent
CREATE TABLE IF NOT EXISTS agent (
    agent_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    capacity_weight INTEGER NOT NULL DEFAULT 1
        CHECK (capacity_weight > 0),

    FOREIGN KEY (team_id)
        REFERENCES team(team_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (role_id)
        REFERENCES role(role_id)
        ON DELETE RESTRICT
);

-- 7. Priority Rule
CREATE TABLE IF NOT EXISTS priority_rule (
    priority_rule_id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_version INTEGER NOT NULL
        CHECK (rule_version > 0),
    priority TEXT NOT NULL
        CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),
    conditions_json TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),

    UNIQUE (rule_name, rule_version),

    CHECK (
        effective_to IS NULL
        OR effective_to >= effective_from
    )
);


-- Phase 2: Transaction Tables

-- 8. Customer Order
CREATE TABLE IF NOT EXISTS customer_order (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    order_status TEXT NOT NULL
        CHECK (order_status IN (
            'PLACED', 'SHIPPED', 'DELIVERED',
            'CANCELLED', 'RETURNED'
        )),
    currency_code TEXT NOT NULL DEFAULT 'INR'
        CHECK (currency_code = 'INR'),
    order_total_paise INTEGER NOT NULL DEFAULT 0
        CHECK (order_total_paise >= 0),
    created_at TEXT NOT NULL,

    FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE RESTRICT
);

-- 9. Order Item
CREATE TABLE IF NOT EXISTS order_item (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_paise INTEGER NOT NULL
        CHECK (unit_price_paise >= 0),
    line_total_paise INTEGER NOT NULL
        CHECK (line_total_paise >= 0),

    UNIQUE (order_id, product_id),

    FOREIGN KEY (order_id)
        REFERENCES customer_order(order_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE RESTRICT,

    CHECK (line_total_paise = quantity * unit_price_paise)
);

-- 10. Complaint
CREATE TABLE IF NOT EXISTS complaint (
    complaint_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_id TEXT,
    product_id TEXT,
    category_id TEXT,
    priority_rule_id TEXT,

    subject TEXT NOT NULL,
    description TEXT NOT NULL,

    channel TEXT NOT NULL
        CHECK (channel IN (
            'EMAIL', 'PHONE', 'WEB', 'CHAT', 'SOCIAL'
        )),

    sentiment TEXT
        CHECK (sentiment IN (
            'POSITIVE', 'NEUTRAL', 'NEGATIVE'
        )),

    severity TEXT
        CHECK (severity IN (
            'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        )),

    priority TEXT
        CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),

    is_repeat INTEGER NOT NULL DEFAULT 0
        CHECK (is_repeat IN (0, 1)),

    repeat_of_complaint_id TEXT,

    current_status TEXT NOT NULL DEFAULT 'NEW'
        CHECK (current_status IN (
            'NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS',
            'PENDING_CUSTOMER', 'PENDING_APPROVAL',
            'RESOLVED', 'REOPENED', 'CLOSED'
        )),

    created_at TEXT NOT NULL,
    closed_at TEXT,

    FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (order_id)
        REFERENCES customer_order(order_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (category_id)
        REFERENCES category(category_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (priority_rule_id)
        REFERENCES priority_rule(priority_rule_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (repeat_of_complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT,

    CHECK (
        (is_repeat = 1 AND repeat_of_complaint_id IS NOT NULL)
        OR
        (is_repeat = 0 AND repeat_of_complaint_id IS NULL)
    )
);

-- 11. Assignment
CREATE TABLE IF NOT EXISTS assignment (
    assignment_id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    agent_id TEXT,
    assigned_at TEXT NOT NULL,
    unassigned_at TEXT,
    assigned_by_agent_id TEXT,
    assignment_reason TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1
        CHECK (is_current IN (0, 1)),

    FOREIGN KEY (complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (team_id)
        REFERENCES team(team_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (assigned_by_agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT,

    CHECK (
        (is_current = 1 AND unassigned_at IS NULL)
        OR
        (is_current = 0 AND unassigned_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_one_current_assignment_per_complaint
ON assignment(complaint_id)
WHERE is_current = 1;

-- 12. Complaint Message
CREATE TABLE IF NOT EXISTS complaint_message (
    message_id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    sender_type TEXT NOT NULL
        CHECK (sender_type IN ('CUSTOMER', 'AGENT', 'SYSTEM')),
    sender_agent_id TEXT,
    channel TEXT NOT NULL
        CHECK (channel IN (
            'EMAIL', 'PHONE', 'WEB', 'CHAT', 'SOCIAL'
        )),
    message_direction TEXT NOT NULL
        CHECK (message_direction IN ('INBOUND', 'OUTBOUND')),
    message_text TEXT NOT NULL,
    sent_at TEXT NOT NULL,

    FOREIGN KEY (complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (sender_agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT,

    CHECK (
        (sender_type = 'AGENT' AND sender_agent_id IS NOT NULL)
        OR
        (sender_type IN ('CUSTOMER', 'SYSTEM')
            AND sender_agent_id IS NULL)
    )
);

-- Phase 3: Tracking and Outcome Tables

-- 13. SLA Clock
CREATE TABLE IF NOT EXISTS sla_clock (
    sla_clock_id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    clock_type TEXT NOT NULL
        CHECK (clock_type IN ('FIRST_RESPONSE', 'RESOLUTION')),
    started_at TEXT NOT NULL,
    target_minutes INTEGER NOT NULL CHECK (target_minutes > 0),
    deadline_at TEXT NOT NULL,
    stopped_at TEXT,
    clock_status TEXT NOT NULL
        CHECK (clock_status IN (
            'RUNNING', 'PAUSED', 'STOPPED', 'BREACHED', 'MET'
        )),
    total_paused_minutes INTEGER NOT NULL DEFAULT 0
        CHECK (total_paused_minutes >= 0),

    UNIQUE (complaint_id, clock_type),

    FOREIGN KEY (complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT
);

-- 14. SLA Event
CREATE TABLE IF NOT EXISTS sla_event (
    sla_event_id TEXT PRIMARY KEY,
    sla_clock_id TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN ('PAUSE', 'RESUME', 'STOP')),
    event_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    actor_agent_id TEXT,

    FOREIGN KEY (sla_clock_id)
        REFERENCES sla_clock(sla_clock_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (actor_agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT
);

-- 15. Complaint Status Event
CREATE TABLE IF NOT EXISTS complaint_status_event (
    status_event_id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    actor_agent_id TEXT,
    reason TEXT NOT NULL,

    FOREIGN KEY (complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (actor_agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT
);

-- 16. Resolution
CREATE TABLE IF NOT EXISTS resolution (
    resolution_id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    resolution_type TEXT NOT NULL
        CHECK (resolution_type IN (
            'REFUND', 'REPLACEMENT', 'REPAIR',
            'INFORMATION', 'REJECTED'
        )),
    resolution_notes TEXT NOT NULL,
    resolved_at TEXT NOT NULL,
    approved_by_agent_id TEXT,
    resolution_status TEXT NOT NULL
        CHECK (resolution_status IN (
            'PROPOSED', 'APPROVED', 'COMPLETED', 'REJECTED'
        )),

    FOREIGN KEY (complaint_id)
        REFERENCES complaint(complaint_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (approved_by_agent_id)
        REFERENCES agent(agent_id)
        ON DELETE RESTRICT
);

-- 17. Survey
CREATE TABLE IF NOT EXISTS survey (
    survey_id TEXT PRIMARY KEY,
    resolution_id TEXT NOT NULL UNIQUE,
    customer_id TEXT,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    submitted_at TEXT NOT NULL,

    FOREIGN KEY (resolution_id)
        REFERENCES resolution(resolution_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (customer_id)
        REFERENCES customer(customer_id)
        ON DELETE RESTRICT
);
