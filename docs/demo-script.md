# Autonomous AI Task Worker: Video Demonstration Script

**Target Duration**: 3 – 5 minutes  
**Format**: Live screen recording with voiceover

---

### [0:00 – 0:30] Introduction & The Problem
* **Visual**: Project title screen on the React dashboard (`http://localhost:5173`).
* **Speaker**:
  > *"Welcome! Today we are demonstrating the Autonomous AI Task Worker. In enterprise environments, invoice processing often relies either on rigid scripts that break whenever web layouts change, or simple chatbots that can only simulate actions with fake APIs.*
  > *In contrast, our system is an agentic AI worker: given a natural language goal, it autonomously plans the work, navigates real browser sessions using Playwright, recovers from transient failures, respects human approval before committing financial data, independently verifies the ledger, and collates visual evidence."*

---

### [0:30 – 1:00] Architecture & Key Principles
* **Visual**: Quick switch to the Mermaid diagram in `docs/architecture.md` or README.
* **Speaker**:
  > *"Under the hood, the system uses FastAPI and LangGraph to manage an explicit state machine. Instead of letting an LLM execute arbitrary scripts, all browser operations flow through registered Playwright tools. The backend persists tasks and execution steps into a database, while pausing cleanly at checkpoint nodes for Human-in-the-Loop approval."*

---

### [1:00 – 2:30] Live Execution: The Main Objective
* **Visual**: Dashboard task input. Click the preset:
  `"Find the latest invoice from Acme, extract the invoice amount and due date, enter the information into our internal billing system, and tell me once it is completed."`
  Toggle on: **"Simulate Intermittent Billing Save Error"** to showcase failure recovery. Click **Start Autonomous Task**.
* **Speaker**:
  > *"Let's submit our task. Notice how the agent immediately decomposes the prompt:*
  > *1. It discovers the target company 'Acme' without hardcoding.*
  > *2. It generates a 7-step execution plan.*
  > *3. Playwright launches in the background, opens the Invoice Portal, searches 'Acme', compares dates across three invoices, and dynamically identifies INV-1024 (dated 2026-10-02) with amount ₹48,500 and due date 2026-10-15.*
  > *4. It then navigates to our Internal Billing System and populates the form."*

---

### [2:30 – 3:30] Human Approval & Resilient Failure Recovery
* **Visual**: The **Approval Required** banner appears on the dashboard with extracted fields: Company: Acme, Invoice: INV-1024, Amount: ₹48,500, Due Date: 2026-10-15.
* **Speaker**:
  > *"Notice that before submitting a permanent financial record, the agent pauses execution. It presents the extracted details for human review. I'll click **Approve & Write to Ledger**.*
  > *Now, because we simulated an intermittent database lock timeout, the first save attempt fails with a 500 error banner.*
  > *Instead of blindly re-saving—which could cause duplicate charges—the agent executes our duplicate recovery logic: it first checks the ledger to verify whether the record was created. Seeing that it wasn't, it increments its bounded retry counter and retries the save, which succeeds with record ID BILL-7842."*

---

### [3:30 – 4:15] Independent Verification & Evidence Gallery
* **Visual**: Agent automatically executes the verification step, searches the ledger by `INV-1024`, and confirms all fields match. Green badge appears: **Verification: PASSED**.
* **Speaker**:
  > *"Notice the agent does not consider 'clicking save' to mean success. It navigates to the records search page, queries INV-1024, and confirms that the company, amount, and due date match the source invoice.*
  > *Below the timeline, the Evidence Gallery displays full-page screenshots captured at each milestone: invoice discovery, form filling, and the verified ledger entry."*

---

### [4:15 – 5:00] Generalization, Limitations & Conclusion
* **Visual**: Quick demo of entering "Find the latest invoice from Globex...". Shows that it seamlessly handles other companies without any code changes.
* **Speaker**:
  > *"The agent generalizes cleanly: changing the target company to Globex automatically searches Globex invoices and processes them with the exact same workflow.*
  > *While current browser support is targeted at our sandboxed enterprise environments, the LangGraph architecture can easily scale to additional tools, multi-tenant auth, and vision-based browser models.*
  > *Thank you for watching!"*
