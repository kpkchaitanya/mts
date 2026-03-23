# Trace Log

**Run ID:**
**Feature:** math_worksheet_generation_from_source
**Date:**

---

## Step-by-Step Execution

### Step 1 — Intake Agent
- **Input:** raw request
- **Output:** request.json
- **Status:** ✅ / ❌
- **Notes:**

### Step 2 — Source Extractor Agent
- **Input:** request.json + source document
- **Output:** source-extract.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 3 — Concept Mapper Agent
- **Input:** source-extract.md
- **Output:** concept-map.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 4 — Worksheet Planner Agent
- **Input:** concept-map.md + request.json
- **Output:** plan.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 5 — Question Generator Agent
- **Input:** plan.md
- **Output:** worksheet-draft.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 6 — Answer Key Agent
- **Input:** worksheet-draft.md
- **Output:** answer-key-draft.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 7 — QA Agent
- **Input:** worksheet-draft.md + answer-key-draft.md
- **Output:** qa-report.md
- **Status:** ✅ / ❌
- **Notes:**

### Step 8 — Formatter Agent
- **Input:** worksheet-draft.md (approved)
- **Output:** worksheet-final.md
- **Status:** ✅ / ❌
- **Notes:**

---

## Revision Loops

| Loop # | Reason | Sent Back To | Result |
|--------|--------|-------------|--------|
| | | | |

---

## Total Time

**Start:**
**End:**
**Duration:**
