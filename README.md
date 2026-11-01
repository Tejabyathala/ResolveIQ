# ResolveIQ – Complaint Intelligence and Resolution System

## About the Project

ResolveIQ is a Python-based project that helps businesses manage customer complaints.

The system stores customer, order and complaint information. It assigns priorities to complaints, assigns them to suitable teams and agents, tracks response and resolution deadlines, and manages the resolution process.

I built this project as part of a technical recruitment challenge. My main goal was to understand how a real business complaint management system works and implement its important features.

## Technologies Used

- Python 3.14
- SQLite
- SQL
- YAML
- PyYAML
- Git

## Main Features

**1. Database Management**
- Created a database with 17 related tables.
- Added primary keys, foreign keys and database constraints.
- Maintained relationships between customers, orders, complaints and other records.

**2. Data Generation**
- Generated 5,000 customers.
- Generated 8,000 orders.
- Generated 2,000 complaints.
- Generated 6,000 complaint messages.
- Used a fixed random seed to make data generation repeatable.

**3. Complaint Priority**
- Implemented priority levels P1, P2, P3 and P4.
- Used complaint severity, customer information and business rules to determine priority.
- Kept the business rules in a YAML configuration file.

**4. Agent Assignment**
- Assigned complaints to teams based on their categories.
- Selected agents based on their current workload.
- Checked that every complaint had a valid assignment.

**5. SLA Management**
- Created first-response and resolution deadlines.
- Implemented pause and resume functionality.
- Tracked SLA events and complaint status changes.

**6. Resolution and Approval**
- Added a resolution proposal process.
- Implemented approval and rejection workflows.
- Added additional approval checks for certain refunds and safety-related complaints.

**7. Complaint Messages**
- Stored customer, agent and system messages.
- Added validation for message details and timestamps.

**8. Anomaly Detection**
- Created a separate database containing intentionally introduced data problems.
- Implemented checks to detect incorrect order totals, item prices, customer-order relationships, SLA deadlines and team assignments.
- Compared detection results against a separate ground-truth CSV file.

## Project Structure

```text
ResolveIQ/
│
├── config/
│   └── business_rules.yaml
│
├── docs/
│   ├── architecture.md
│   ├── business_rules.md
│   └── data_dictionary.md
│
├── output/
│   ├── clean/
│   ├── ground_truth/
│   └── with_anomalies/
│
├── prompt_history/
│   └── PROMPTS.md
│
├── scripts/
├── src/
│   ├── database/
│   ├── engine/
│   └── generator/
│
├── tests/
├── main.py
└── requirements.txt
```

## How to Run

### 1. Clone the repository

```powershell
git clone <your-github-repository-url>
cd ResolveIQ
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Initialize the database

```powershell
python -m src.database.initialize
```

### 5. Apply the resolution workflow migration

```powershell
python -c "import runpy; runpy.run_path('src/database/migrations/001_resolution_workflow.py', run_name='__main__')"
```

### 6. Generate the project data

Run these commands in order:

```powershell
python -m src.database.seed_master_data
python -m src.generator.customer_service
python -m src.generator.order_service
python -m src.generator.complaint_service
python -m src.engine.priority_service
python -m src.engine.assignment_service
python -m src.engine.sla_service
python -m src.generator.message_generation_service
```

### 7. Generate test anomalies

```powershell
python -m src.engine.anomaly_generator
```

### 8. Run the validation pipeline

```powershell
python main.py
```

The validation pipeline checks the existing database, priority results, assignments, SLA records, messages and anomaly detection results.

**Note:** The `output/` directory is excluded from Git. The database and generated files need to be created by running the steps above. The migration is intended for a newly initialized database and should not be run again on an already migrated database.

## Validation Results

The project was tested using generated data and intentionally introduced anomalies.

| Check | Result |
|---|---:|
| Database tables | 17 |
| Customers | 5,000 |
| Orders | 8,000 |
| Complaints | 2,000 |
| Messages | 6,000 |
| Injected anomalies | 100 |
| Detected anomalies | 100 |
| False positives | 0 |
| False negatives | 0 |

### Anomaly Detection Evaluation

| Metric | Result |
|---|---:|
| Precision | 1.00 |
| Recall | 1.00 |
| F1 Score | 1.00 |

These results are from the controlled synthetic dataset used in this project. They do not represent performance on real-world customer data.

## What I Learned

While working on ResolveIQ, I gained practical experience with:

- Designing relational databases.
- Writing SQL queries and working with SQLite.
- Structuring a Python project into separate modules.
- Implementing business rules and validation.
- Handling transactions and database relationships.
- Writing test cases and debugging errors.
- Using Git for version control.
- Understanding anomaly detection and evaluation metrics.

## AI Assistance

I used ChatGPT as a development assistant for understanding concepts, planning the project, debugging errors, reviewing implementation ideas and preparing tests and documentation.

I implemented and tested the project locally and reviewed the suggested changes. ChatGPT is not used as a runtime component of ResolveIQ.

A summary of the AI-assisted development prompts is available in `prompt_history/PROMPTS.md`.
