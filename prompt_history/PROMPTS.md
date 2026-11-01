# ResolveIQ — AI Prompt History
## Prompt Record

| No. | Development Phase | Prompt / Assistance Summary |
|---:|---|---|
| 1 | Project planning | Help define a practical complaint intelligence and resolution system suitable for a 72-hour technical challenge. |
| 2 | Architecture | Design the system architecture, identify entities, relationships, primary keys and foreign keys. |
| 3 | Business rules | Define configurable complaint priority, routing, SLA, repeat complaint and approval rules. |
| 4 | Database | Help implement a normalized SQLite schema with appropriate constraints and relationships. |
| 5 | Database validation | Design tests for primary-key uniqueness, foreign keys, check constraints and duplicate records. |
| 6 | Master data | Implement deterministic generation of categories, teams, roles, agents, products and priority rules. |
| 7 | Customer generation | Generate reproducible customer records with deterministic identifiers and realistic attributes. |
| 8 | Order generation | Generate customer orders and order items with consistent quantities, prices and totals. |
| 9 | Complaint generation | Generate complaints with valid customer, order and product relationships, including repeat complaints. |
| 10 | Priority engine | Implement priority classification using safety, severity, sentiment, order value, vulnerability and recurrence. |
| 11 | Priority testing | Design tests and validation checks to verify priority decisions and rule references. |
| 12 | Assignment engine | Implement category-based team routing and lowest-active-workload agent assignment. |
| 13 | SLA engine | Implement first-response and resolution deadlines based on complaint priority. |
| 14 | SLA events | Implement SLA pause, resume and accumulated paused-time calculations. |
| 15 | Complaint lifecycle | Implement allowed complaint status transitions, timestamp validation and status-event history. |
| 16 | Resolution workflow | Implement resolution proposals, approval requirements, rejection and completion. |
| 17 | Transaction handling | Debug database transaction ownership and SQLite temporary database cleanup issues. |
| 18 | Message service | Implement complaint message validation, chronological checks and deterministic message identifiers. |
| 19 | Message generation | Generate three messages per complaint and validate the expected message count. |
| 20 | Anomaly injection | Design controlled anomaly injection while preserving a separate clean database and ground-truth labels. |
| 21 | Anomaly detection | Implement checks for incorrect order totals, item prices, customer-order relationships, SLA deadlines and team assignments. |
| 22 | Anomaly evaluation | Calculate true positives, false positives, false negatives, precision, recall and F1 score. |
| 23 | Robustness | Investigate overlapping anomalies, malformed SLA values, database integrity and reproducibility. |
| 24 | Final validation | Review validation output, syntax checks, Git commits and project documentation. |


