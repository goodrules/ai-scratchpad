# Software Bug Assistant - Apex Bank (Local Setup)

This workspace contains a localized version of the Software Bug Assistant, pivoted to the banking domain (Apex Bank). It is configured to run entirely on local infrastructure using native PostgreSQL and local tools.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation) (Dependency manager)
- Native PostgreSQL (installed locally, e.g., via Homebrew or installer)

---

## Setup and Installation

### 1. Synchronize Dependencies
Run this command from the project root to install Python dependencies:
```bash
uv sync
```

### 2. Configure Environment
Create a `.env` file in the project root:
```bash
touch .env
```
Add the following variables (replace placeholders with your keys):
```env
# Gemini API Configuration
GEMINI_API_KEY="your-api-key-here"

# GitHub Configuration for external ticket search (Optional but recommended)
GITHUB_PERSONAL_ACCESS_TOKEN="your-github-pat-here"

# Local MCP Toolbox URL
MCP_TOOLBOX_URL="http://localhost:5000"
```

---

## Database Initialization

Create a database named `ticketsdb` and seed it using standard SQL.

### 1. Create Database
```bash
createdb ticketsdb
```

### 2. Create Table
Run `psql ticketsdb` and execute:
```sql
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    assignee TEXT,
    priority TEXT,
    status TEXT,
    creation_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Seed Sample Banking Data
While in `psql ticketsdb`, run:
```sql
INSERT INTO tickets (title, description, assignee, priority, status, creation_time, updated_time) VALUES
('Retail Banking Mobile App Login Freezes After MFA', 'Retail customers are reporting that after entering the MFA code on the mobile app, the login screen freezes. No error message is shown, requiring a force close of the app.', 'samuel.green@apexbank.com', 'P0 - Critical', 'Open', '2026-03-24 08:30:00-05', '2026-03-24 09:00:00-05'),
('Corporate SWIFT Transfer Dashboard Slow Loading', 'The "Ancillary Transfers Overview" widget on the Corp Strategy dashboard intermittently shows a loading spinner but no real-time transfer state data. Primarily affects Edge browser users.', 'maria.rodriguez@apexbank.com', 'P1 - High', 'In Progress', '2026-03-20 14:22:00-05', '2026-03-21 10:00:00-05'),
('Broken Link in ApexBank.com Footer - Terms of Service', 'The "Terms and Conditions" hyperlink located in the website footer leads to a 404 "Page Not Found" error on the main production site.', 'maria.rodriguez@apexbank.com', 'P3 - Low', 'Resolved', '2026-02-28 11:00:00-05', '2026-03-05 16:45:00-05'),
('Mortgage Application UI Misalignment for iOS', 'On specific iOS devices (e.g., iPhone 14 models), the signature block on the digital mortgage application shifts downwards when viewed in landscape orientation, making it difficult to sign.', 'maria.rodriguez@apexbank.com', 'P2 - Medium', 'In Progress', '2026-03-10 09:15:00-05', '2026-03-18 11:20:00-05'),
('Critical XZ Utils Backdoor Detected in Core Settlement Nodes (CVE-2024-3094)', 'Urgent: A sophisticated supply chain compromise (CVE-2024-3094) has been identified in XZ Utils. Immediate investigation and patching required for affected Linux/Unix systems hosting the settlement tracking DBs to prevent unauthorized remote SSH access.', 'frank.white@apexbank.com', 'P0 - Critical', 'Open', '2026-03-25 02:00:00-05', '2026-03-25 08:00:00-05'),
('Fraud Detection DB Connection Timeouts During Peak Usage', 'The fraud scoring system (FSS) is experiencing frequent database connection timeouts, particularly during peak transaction hours (10 AM - 12 PM EDT), affecting real-time fraud checks and causing transaction delays.', 'frank.white@apexbank.com', 'P1 - High', 'Open', '2026-03-14 10:05:00-05', '2026-03-15 09:00:00-05'),
('Export to PDF Truncates Credit Assessment Reports', 'When generating PDF exports of credit history and risk profiles containing extensive notes, the text is abruptly cut off at the end of the page instead of wrapping.', 'samuel.green@apexbank.com', 'P1 - High', 'Open', '2026-03-05 13:40:00-05', '2026-03-08 14:10:00-05'),
('Commercial Banking Portal "Date Range" Filter Not Applying', 'The "Date Range" filter in the commercial banking portal does not filter transactions accurately; items outside the specified date range are still being displayed in the audit view.', 'samuel.green@apexbank.com', 'P2 - Medium', 'Resolved', '2026-03-12 16:30:00-05', '2026-03-14 10:00:00-05'),
('Typo in ATM Error Message: "Unathorized Account"', 'The error message displayed when a customer attempts an unauthorized action on local ATMs reads "Unathorized Account" instead of "Unauthorized Account."', 'maria.rodriguez@apexbank.com', 'P3 - Low', 'Resolved', '2026-02-28 08:00:00-05', '2026-03-02 09:00:00-05'),
('Intermittent Sync Failures for Relationship Manager Tablets', 'Bank managers are intermittently reporting that tablet syncs for customer profiles fail without a clear error message over cellular connections, especially for payload files exceeding 10MB.', 'frank.white@apexbank.com', 'P1 - High', 'Open', '2026-03-22 18:45:00-05', '2026-03-23 09:15:00-05'),
('OOMKilled (Exit Code 137) on Trading API Microservice', 'The Kubernetes pods handling high-frequency trading queries are repeatedly crashing with "OOMKilled" and Exit Code 137 during market open. Need to review memory limits and check for leaks in the Node.js app.', 'david.chen@apexbank.com', 'P1 - High', 'Open', '2026-03-23 07:15:00-05', '2026-03-23 08:30:00-05'),
('Core Banking DB Error: FATAL: remaining connection slots are reserved', 'Branch terminals cannot query user accounts. The PostgreSQL database is throwing "FATAL: remaining connection slots are reserved for non-replication superuser connections". Looks like connection pooling via PgBouncer is failing.', 'samuel.green@apexbank.com', 'P0 - Critical', 'Open', '2026-03-24 14:00:00-05', '2026-03-24 14:15:00-05');
```

---

## Running Locally

You need to run the MCP Toolbox server, the Python backend, and the Next.js frontend concurrently.

### 1. Run MCP Toolbox
Navigate to `deployment/mcp-toolbox` and run:
```bash
./toolbox --config "tools.yaml"
```

### 2. Run Python Backend
In a new terminal, from the project root run:
```bash
uv run python ui/server.py
```

### 3. Run Custom UI Frontend
In a new terminal, run:
```bash
cd ui/frontend
npm run dev
```

Access the UI at **`http://localhost:3000`**.
