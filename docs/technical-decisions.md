# Technical Decision Record: Autonomous AI Task Worker

This document outlines the rationale behind the key architectural and engineering decisions in the project.

---

### 1. Why LangGraph?
* **Problem**: Traditional ReAct loops or monolithic agent functions often become unbounded, unpredictable black boxes that fail to pause cleanly for human intervention or handle complex retries.
* **Decision**: We implemented the core agent workflow using **LangGraph**.
* **Rationale**:
  - LangGraph allows modeling the agent as an explicit **directed state graph** with typed state (`AgentState`).
  - State transitions, conditional branching (e.g. failure recovery vs. advancement), and checkpointing are transparent and testable in isolation.
  - Pausing the graph for **Human-in-the-Loop (HIL) approval** is natural: the agent sets its status to `AWAITING_APPROVAL`, saves its checkpoint to the database, and halts cleanly until resumed by an API call.

---

### 2. Why Playwright for Python?
* **Problem**: Many AI demos merely simulate tool calls via mocked JSON payloads (`call_fake_api(...)`) without actually interacting with realistic web interfaces.
* **Decision**: We utilized **Playwright Python** for end-to-end browser automation.
* **Rationale**:
  - Playwright provides native async execution, resilient selector auto-waiting, network idle synchronization, and full-page screenshot capture.
  - It exposes a clean abstraction (`BrowserManager`, `InvoiceTools`, `BillingTools`) ensuring the agent never interacts directly with low-level browser internals.
  - Seamlessly supports both headless mode (for CI, Docker, Render) and headed mode (for visual debugging).

---

### 3. Why Controlled Sandbox Applications?
* **Problem**: Executing tests or demos against third-party production websites introduces credential leakage risks, rate limits, UI flakiness, and legal liability.
* **Decision**: We created two simulated enterprise web applications (`Invoice Portal` and `Internal Billing System`).
* **Rationale**:
  - Provides a self-contained, 100% reproducible testing ground.
  - Features real DOM tables, input forms, and dynamic date sorting.
  - Integrates a controllable intermittent failure mode (`?fail_once=true`) to demonstrate genuine failure recovery and duplicate prevention.

---

### 4. Why PostgreSQL with SQLite Development Fallback?
* **Problem**: In-memory storage loses all audit logs when a process restarts; conversely, requiring a dedicated PostgreSQL server for local development or fast CI can hinder developer velocity.
* **Decision**: We implemented SQLAlchemy with Alembic migrations, defaulting to local SQLite for instant setup while fully supporting PostgreSQL for production (Render / Docker Compose).
* **Rationale**:
  - Full relational modeling of `tasks`, `execution_steps`, `approvals`, and `evidence`.
  - Zero-configuration local startup with zero database setup overhead.
  - Seamless migration to managed PostgreSQL on Render or Docker with one environment variable change (`DATABASE_URL`).

---

### 5. Why Structured LLM Outputs?
* **Problem**: Unstructured LLM text outputs frequently hallucinate arguments or invent non-existent tool names.
* **Decision**: We enforced structured outputs with Pydantic schemas (`StructuredPlan`, `PlanStep`) and validated actions against a strict set of `REGISTERED_ACTIONS`.
* **Rationale**:
  - Guarantees valid JSON format.
  - Prevents prompt injection or arbitrary code execution from model outputs.
  - Backed by a deterministic parser fallback ensuring tests can run offline or in air-gapped CI environments.

---

### 6. Why Independent Post-Execution Verification?
* **Problem**: A successful click or HTTP 200 toast does not prove that a database transaction committed correctly.
* **Decision**: The agent performs independent post-execution verification before marking the task `COMPLETED`.
* **Rationale**:
  - The agent opens the billing records ledger, queries by `invoice_id`, and verifies that `company`, `amount`, and `due_date` match the source invoice.
  - If any field mismatches or the record is missing, the task is marked as `FAILED`.
  - Captures dedicated verification screenshot evidence.

---

### 7. Why Bounded Retries with Pre-Retry Duplicate Checks?
* **Problem**: Naive retry loops can create infinite loops or, worse, duplicate billing records and transactions.
* **Decision**: We implemented a strict bounded retry policy (`MAX_RETRIES = 2`) combined with a ledger duplicate check before retrying.
* **Rationale**:
  - If a save operation fails with a 500 error, the agent first queries the ledger to check whether the record was committed despite the timeout signal.
  - Only if the record does not exist will it proceed with a retry.
  - Once max retries are reached, the agent terminates safely without looping infinitely.
