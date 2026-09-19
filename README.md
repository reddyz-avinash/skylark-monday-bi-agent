# Skylark Drones — Monday.com Business Intelligence Agent

Founder-facing conversational BI agent for the Skylark Full Stack assignment.

## Core flow

React UI -> FastAPI -> Query Planner -> Monday.com GraphQL API -> Normalization -> Deterministic BI -> Answer + Caveats

The Excel files are used to populate the two Monday.com boards. They are **not** used at runtime. This satisfies the assignment requirement that the agent query Monday.com dynamically.

## Features

- Read-only Monday.com integration for Deals and Work Orders.
- Natural-language conversational interface.
- Pipeline, deal-stage, sector, operations, billing and receivable analysis.
- Cross-board sector comparisons.
- Leadership-update generation.
- Missing/null/date/text normalization.
- Explicit data-quality caveats.
- Clarifying responses for vague questions.
- Graceful Monday API failure handling.
- Optional LLM polishing without allowing the LLM to invent business numbers.

## Structure

```text
skylark-bi-agent/
├── backend/app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── monday.py
│   ├── normalize.py
│   ├── analytics.py
│   ├── planner.py
│   └── llm.py
├── frontend/src/
│   ├── App.jsx
│   ├── main.jsx
│   └── styles.css
├── docs/
│   ├── monday-board-setup.md
│   └── decision-log.md
├── .env.example
├── render.yaml
└── README.md
```

## Backend setup

Python 3.11+ recommended.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Put these variables in a `.env` file at the project root:

```env
MONDAY_API_TOKEN=your_read_only_token
MONDAY_DEALS_BOARD_ID=123456789
MONDAY_WORK_ORDERS_BOARD_ID=987654321
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

For a deployed backend:

```env
VITE_API_URL=https://your-backend.example.com
```

## Example questions

- How is our Mining pipeline looking?
- How many open deals do we have?
- Show pipeline by sector.
- Where are our deals getting stuck?
- How many work orders are ongoing?
- How much is still to be billed?
- Which sectors have the highest receivables?
- Compare Mining and Renewables across sales and operations.
- Prepare a leadership update.

## Important data-resilience behavior

The supplied data is intentionally messy. Missing values are not silently converted to zero. Answers report available populations and caveats, e.g.:

> Open pipeline is ₹X across 47 valued open deals. 2 additional open deals do not have a usable deal value and are excluded from the amount calculation.

## Deployment

`render.yaml` contains a backend service and static frontend service. Add the Monday and optional LLM secrets in the hosting dashboard.

## Security

Never commit `.env`, Monday tokens, or LLM API keys.
