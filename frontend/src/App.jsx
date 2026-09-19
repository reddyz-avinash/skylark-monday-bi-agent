import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

/* =========================================================
   API CONFIGURATION
========================================================= */

const API =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";


/* =========================================================
   SUGGESTED QUESTIONS
========================================================= */

const examples = [
  "How is our Mining pipeline looking?",
  "Which sectors have the highest open pipeline?",
  "How many work orders are ongoing?",
  "What is the total billed amount, collected amount, and receivable?",
  "Compare Mining and Renewables across sales and operations",
  "Prepare a leadership update",
];


/* =========================================================
   FORMATTING HELPERS
========================================================= */

function formatMoney(value) {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "N/A";
  }

  if (Math.abs(n) >= 10000000) {
    return `₹${(n / 10000000).toFixed(2)} Cr`;
  }

  if (Math.abs(n) >= 100000) {
    return `₹${(n / 100000).toFixed(2)} L`;
  }

  return `₹${n.toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;
}


function formatNumber(value) {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "N/A";
  }

  return n.toLocaleString("en-IN");
}


function formatIntent(intent) {
  if (!intent) {
    return "";
  }

  return String(intent)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}


function formatSectorName(sector) {
  if (
    sector === null ||
    sector === undefined ||
    String(sector).trim() === ""
  ) {
    return "Unknown";
  }

  return String(sector)
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}


/* =========================================================
   SAFE NUMBER
========================================================= */

function safeNumber(value, fallback = 0) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return fallback;
  }

  return number;
}


/* =========================================================
   SIMPLE MARKDOWN RENDERER
========================================================= */

function renderInline(text) {
  if (!text) {
    return null;
  }

  const parts = String(text).split(
    /(\*\*.*?\*\*)/g
  );

  return parts.map((part, index) => {
    if (
      part.startsWith("**") &&
      part.endsWith("**")
    ) {
      return (
        <strong key={index}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    return (
      <React.Fragment key={index}>
        {part}
      </React.Fragment>
    );
  });
}


function AnswerText({ text }) {
  if (!text) {
    return null;
  }

  const lines = String(text).split("\n");

  return (
    <div className="answer-text">
      {lines.map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return (
            <div
              className="answer-space"
              key={index}
            />
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h3
              className="answer-heading"
              key={index}
            >
              {renderInline(
                trimmed.replace("## ", "")
              )}
            </h3>
          );
        }

        if (trimmed.startsWith("- ")) {
          return (
            <div
              className="answer-bullet"
              key={index}
            >
              <span>•</span>

              <span>
                {renderInline(
                  trimmed.slice(2)
                )}
              </span>
            </div>
          );
        }

        return (
          <div
            className="answer-line"
            key={index}
          >
            {renderInline(line)}
          </div>
        );
      })}
    </div>
  );
}


/* =========================================================
   KPI CARD
========================================================= */

function KpiCard({
  label,
  value,
  description,
  icon,
}) {
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <span className="kpi-label">
          {label}
        </span>

        <span className="kpi-icon">
          {icon}
        </span>
      </div>

      <div className="kpi-value">
        {value}
      </div>

      {description && (
        <div className="kpi-description">
          {description}
        </div>
      )}
    </div>
  );
}


/* =========================================================
   PIPELINE VIEW
========================================================= */

function PipelineView({ metrics }) {
  return (
    <div className="metrics-section">
      <div className="section-title">
        Pipeline snapshot
      </div>

      <div className="kpi-grid">

        <KpiCard
          label="Open Deals"
          value={formatNumber(
            metrics.open_deals ?? 0
          )}
          description={`${formatNumber(
            metrics.valued_open_deals ?? 0
          )} with usable values`}
          icon="◉"
        />

        <KpiCard
          label="Open Pipeline"
          value={formatMoney(
            metrics.open_pipeline
          )}
          description="Available valued pipeline"
          icon="₹"
        />

        <KpiCard
          label="Missing Values"
          value={formatNumber(
            metrics.missing_open_values ?? 0
          )}
          description="Excluded from pipeline total"
          icon="!"
        />

      </div>
    </div>
  );
}


/* =========================================================
   OPERATIONS VIEW
========================================================= */

function OperationsView({ metrics }) {
  return (
    <div className="metrics-section">

      <div className="section-title">
        Operations snapshot
      </div>

      <div className="kpi-grid four">

        <KpiCard
          label="Work Orders"
          value={formatNumber(
            metrics.work_orders ?? 0
          )}
          icon="▦"
        />

        <KpiCard
          label="Ongoing"
          value={formatNumber(
            metrics.ongoing ?? 0
          )}
          icon="▶"
        />

        <KpiCard
          label="Completed"
          value={formatNumber(
            metrics.completed ?? 0
          )}
          icon="✓"
        />

        <KpiCard
          label="Not Started"
          value={formatNumber(
            metrics.not_started ?? 0
          )}
          icon="○"
        />

      </div>
    </div>
  );
}


/* =========================================================
   BILLING VIEW
========================================================= */

function BillingView({ metrics }) {
  return (
    <div className="metrics-section">

      <div className="section-title">
        Billing & collections
      </div>

      <div className="kpi-grid">

        <KpiCard
          label="Billed"
          value={formatMoney(
            metrics.billed_total
          )}
          description={`${formatNumber(
            metrics.billed_available ?? 0
          )} records with data`}
          icon="₹"
        />

        <KpiCard
          label="Collected"
          value={formatMoney(
            metrics.collected_total
          )}
          description={`${formatNumber(
            metrics.collected_available ?? 0
          )} records with data`}
          icon="✓"
        />

        <KpiCard
          label="Receivable"
          value={formatMoney(
            metrics.receivable_total
          )}
          description={`${formatNumber(
            metrics.receivable_available ?? 0
          )} records with data`}
          icon="!"
        />

      </div>
    </div>
  );
}


/* =========================================================
   PIPELINE BY SECTOR
========================================================= */

function PipelineBySectorView({ metrics }) {
  const rows = Array.isArray(metrics.sectors)
    ? metrics.sectors
    : [];

  if (!rows.length) {
    return null;
  }

  const maxPipeline = Math.max(
    ...rows.map((row) =>
      safeNumber(row?.pipeline)
    ),
    0
  );

  return (
    <div className="metrics-section">

      <div className="section-title">
        Open pipeline by sector
      </div>

      <div className="sector-table">

        <div className="sector-header">
          <span>Sector</span>
          <span>Open Deals</span>
          <span>Pipeline</span>
        </div>

        {rows.map((row, index) => {

          const pipeline = safeNumber(
            row?.pipeline
          );

          const openDeals = safeNumber(
            row?.open_deals
          );

          const percentage =
            maxPipeline > 0
              ? (pipeline / maxPipeline) * 100
              : 0;

          return (
            <div
              className="sector-row"
              key={`${row?.sector || "unknown"}-${index}`}
            >

              <div className="sector-name">

                <span className="rank">
                  {index + 1}
                </span>

                <div>

                  <strong>
                    {formatSectorName(
                      row?.sector
                    )}
                  </strong>

                  <div className="bar">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${percentage}%`,
                      }}
                    />
                  </div>

                </div>
              </div>

              <span className="sector-deals">
                {formatNumber(openDeals)}
              </span>

              <strong className="sector-money">
                {formatMoney(pipeline)}
              </strong>

            </div>
          );
        })}

      </div>
    </div>
  );
}


/* =========================================================
   CROSS-BOARD COMPARISON
========================================================= */

/*
  IMPORTANT FIX

  Backend returns objects like:

  {
    sector: "Mining",
    pipeline: {
      open_pipeline: 29100000,
      open_deals: 9
    },
    operations: {
      work_orders: 100,
      ongoing: 6,
      completed: 73
    }
  }

  Older frontend code expected:

  row[0]
  row[1]
  row[2]

  That caused:

  Unknown
  ₹0
  0 work orders

  This version supports BOTH formats.
*/

function normalizeComparisonRow(row) {

  /* -----------------------------------------
     Format 1:
     Object format
  ----------------------------------------- */

  if (
    row &&
    typeof row === "object" &&
    !Array.isArray(row)
  ) {

    return {
      sector:
        row.sector ??
        row.name ??
        row.label ??
        "Unknown",

      pipeline:
        row.pipeline ??
        row.sales ??
        {},

      operations:
        row.operations ??
        row.ops ??
        {},
    };
  }


  /* -----------------------------------------
     Format 2:
     Array format
  ----------------------------------------- */

  if (Array.isArray(row)) {

    return {
      sector:
        row[0] ??
        "Unknown",

      pipeline:
        row[1] ??
        {},

      operations:
        row[2] ??
        {},
    };
  }


  /* -----------------------------------------
     Unknown format
  ----------------------------------------- */

  return {
    sector: "Unknown",
    pipeline: {},
    operations: {},
  };
}


function ComparisonCard({
  row,
  index,
}) {

  const sector =
    formatSectorName(row.sector);

  const pipeline =
    row.pipeline || {};

  const operations =
    row.operations || {};


  const openPipeline =
    safeNumber(
      pipeline.open_pipeline ??
      pipeline.pipeline ??
      pipeline.value
    );

  const openDeals =
    safeNumber(
      pipeline.open_deals ??
      pipeline.deals
    );

  const workOrders =
    safeNumber(
      operations.work_orders ??
      operations.total ??
      operations.work_orders_count
    );

  const ongoing =
    safeNumber(
      operations.ongoing ??
      operations.ongoing_work_orders
    );

  const completed =
    safeNumber(
      operations.completed ??
      operations.completed_work_orders
    );

  const notStarted =
    safeNumber(
      operations.not_started ??
      operations.notStarted
    );

  const paused =
    safeNumber(
      operations.paused ??
      operations.paused_struck ??
      operations.paused_work_orders
    );


  return (
    <div
      className="comparison-card"
      key={`${sector}-${index}`}
    >

      <div className="comparison-title">
        {sector}
      </div>


      <div className="comparison-item">

        <span>
          Open pipeline
        </span>

        <strong>
          {formatMoney(openPipeline)}
        </strong>

      </div>


      <div className="comparison-item">

        <span>
          Open deals
        </span>

        <strong>
          {formatNumber(openDeals)}
        </strong>

      </div>


      <div className="comparison-item">

        <span>
          Work orders
        </span>

        <strong>
          {formatNumber(workOrders)}
        </strong>

      </div>


      <div className="comparison-item">

        <span>
          Ongoing
        </span>

        <strong>
          {formatNumber(ongoing)}
        </strong>

      </div>


      <div className="comparison-item">

        <span>
          Completed
        </span>

        <strong>
          {formatNumber(completed)}
        </strong>

      </div>


      {notStarted > 0 && (
        <div className="comparison-item">

          <span>
            Not started
          </span>

          <strong>
            {formatNumber(notStarted)}
          </strong>

        </div>
      )}


      {paused > 0 && (
        <div className="comparison-item">

          <span>
            Paused / struck
          </span>

          <strong>
            {formatNumber(paused)}
          </strong>

        </div>
      )}

    </div>
  );
}


function SectorComparisonView({ metrics }) {

  /*
    Support all possible backend keys.
  */

  const rawRows =
    Array.isArray(metrics?.comparison)
      ? metrics.comparison
      : Array.isArray(metrics?.comparison_rows)
        ? metrics.comparison_rows
        : Array.isArray(metrics?.rows)
          ? metrics.rows
          : [];


  if (!rawRows.length) {
    return null;
  }


  const rows = rawRows.map(
    normalizeComparisonRow
  );


  return (
    <div className="metrics-section">

      <div className="section-title">
        Sales & operations comparison
      </div>

      <div className="comparison-grid">

        {rows.map((row, index) => (
          <ComparisonCard
            row={row}
            index={index}
            key={`${row.sector}-${index}`}
          />
        ))}

      </div>
    </div>
  );
}


/* =========================================================
   LEADERSHIP UPDATE
========================================================= */

function LeadershipView({ metrics }) {

  const pipeline =
    metrics?.pipeline || {};

  const operations =
    metrics?.operations || {};

  const billing =
    metrics?.billing || {};


  return (
    <div className="metrics-section">

      <div className="section-title">
        Executive snapshot
      </div>

      <div className="kpi-grid">

        <KpiCard
          label="Open Pipeline"
          value={formatMoney(
            pipeline.open_pipeline
          )}
          description={`${formatNumber(
            pipeline.open_deals ?? 0
          )} open deals`}
          icon="₹"
        />

        <KpiCard
          label="Work Orders"
          value={formatNumber(
            operations.work_orders ?? 0
          )}
          description={`${formatNumber(
            operations.ongoing ?? 0
          )} ongoing`}
          icon="▦"
        />

        <KpiCard
          label="Receivable"
          value={formatMoney(
            billing.receivable_total
          )}
          description="Based on populated fields"
          icon="!"
        />

      </div>
    </div>
  );
}


/* =========================================================
   METRICS ROUTER
========================================================= */

function MetricsView({
  intent,
  metrics,
}) {

  if (
    !metrics ||
    typeof metrics !== "object" ||
    Object.keys(metrics).length === 0
  ) {
    return null;
  }


  switch (intent) {

    case "pipeline":
      return (
        <PipelineView
          metrics={metrics}
        />
      );


    case "operations":
      return (
        <OperationsView
          metrics={metrics}
        />
      );


    case "billing":
      return (
        <BillingView
          metrics={metrics}
        />
      );


    case "pipeline_by_sector":
      return (
        <PipelineBySectorView
          metrics={metrics}
        />
      );


    case "sector_comparison":
      return (
        <SectorComparisonView
          metrics={metrics}
        />
      );


    case "leadership_update":
      return (
        <LeadershipView
          metrics={metrics}
        />
      );


    default:
      return null;
  }
}


/* =========================================================
   DATA QUALITY
========================================================= */

function DataQuality({
  caveats,
}) {

  if (
    !Array.isArray(caveats) ||
    caveats.length === 0
  ) {
    return null;
  }


  return (
    <div className="data-quality">

      <div className="data-quality-title">

        <span>
          ⚠
        </span>

        Data quality

      </div>


      <div className="data-quality-subtitle">

        Missing fields are not silently
        treated as zero.

      </div>


      <div className="quality-list">

        {caveats
          .slice(0, 5)
          .map((item, index) => (

            <div
              key={index}
              className="quality-item"
            >

              <span>
                •
              </span>

              {item}

            </div>

          ))}

      </div>

    </div>
  );
}


/* =========================================================
   API ERROR HELPER
========================================================= */

async function getApiError(response) {

  try {

    const data =
      await response.json();

    return (
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`
    );

  } catch {

    return `Request failed with status ${response.status}`;

  }
}


/* =========================================================
   MAIN APP
========================================================= */

function App() {

  const [
    messages,
    setMessages,
  ] = useState([]);


  const [
    input,
    setInput,
  ] = useState("");


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    intent,
    setIntent,
  ] = useState("");


  /* =======================================================
     SEND QUESTION
  ======================================================= */

  async function send(
    text = input
  ) {

    const question =
      String(text || "").trim();


    if (
      !question ||
      loading
    ) {
      return;
    }


    /* -----------------------------------------------
       Add user message immediately
    ----------------------------------------------- */

    setMessages(
      (previous) => [
        ...previous,

        {
          role: "user",
          text: question,
        },
      ]
    );


    setInput("");
    setLoading(true);


    try {

      /* ---------------------------------------------
         API request
      --------------------------------------------- */

      const response =
        await fetch(
          `${API}/api/chat`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              message: question,
            }),
          }
        );


      /* ---------------------------------------------
         Handle HTTP errors
      --------------------------------------------- */

      if (!response.ok) {

        const errorMessage =
          await getApiError(
            response
          );

        throw new Error(
          errorMessage
        );
      }


      /* ---------------------------------------------
         Parse JSON
      --------------------------------------------- */

      const data =
        await response.json();


      /* ---------------------------------------------
         Extract response safely
      --------------------------------------------- */

      const answer =
        data?.answer ||
        "No answer was returned.";


      const responseIntent =
        data?.intent ||
        "";


      const caveats =
        Array.isArray(data?.caveats)
          ? data.caveats
          : [];


      const responseMetrics =
        data?.metrics &&
        typeof data.metrics === "object"
          ? data.metrics
          : {};


      /* ---------------------------------------------
         Add assistant message
      --------------------------------------------- */

      setMessages(
        (previous) => [
          ...previous,

          {
            role: "assistant",

            text: answer,

            caveats,

            metrics: responseMetrics,

            intent: responseIntent,
          },
        ]
      );


      /* ---------------------------------------------
         Update sidebar intent
      --------------------------------------------- */

      setIntent(
        responseIntent ||
        "business_analysis"
      );

    } catch (error) {

      console.error(
        "Chat request failed:",
        error
      );


      setMessages(
        (previous) => [
          ...previous,

          {
            role: "assistant",

            text:
              "I couldn't complete that request.\n\n" +
              `${error?.message || "Unexpected error."}`,

            caveats: [],

            metrics: {},

            intent: "error",
          },
        ]
      );


      setIntent("error");

    } finally {

      setLoading(false);

    }
  }


  /* =======================================================
     RENDER
  ======================================================= */

  return (

    <div className="app">


      {/* =================================================
          HEADER
      ================================================= */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-name">
            SKYLARK DRONES
          </div>


          <h1>
            Business Intelligence Agent
          </h1>


          <p>
            Founder-level answers across
            Deals and Work Orders.
          </p>

        </div>


        <div className="connection-status">

          <span className="status-dot" />

          Monday.com connected

        </div>

      </header>


      {/* =================================================
          MAIN DASHBOARD
      ================================================= */}

      <main className="dashboard">


        {/* ===============================================
            CHAT PANEL
        =============================================== */}

        <section className="chat-panel">

          <div className="messages">


            {/* -------------------------------------------
                WELCOME SCREEN
            ------------------------------------------- */}

            {!messages.length && (

              <div className="welcome">

                <div className="welcome-icon">
                  ✦
                </div>


                <h2>
                  What would you like to know?
                </h2>


                <p>
                  Ask about pipeline,
                  sectors, operations,
                  billing, or leadership
                  updates.
                </p>


                <div className="welcome-tags">

                  <span>
                    Deals
                  </span>

                  <span>
                    Work Orders
                  </span>

                  <span>
                    Revenue
                  </span>

                  <span>
                    Operations
                  </span>

                </div>

              </div>

            )}


            {/* -------------------------------------------
                CONVERSATION
            ------------------------------------------- */}

            {messages.map(
              (message, index) => (

                <div
                  className={`message ${message.role}`}
                  key={index}
                >


                  {/* Assistant icon */}

                  {message.role ===
                    "assistant" && (

                    <div className="assistant-avatar">
                      ✦
                    </div>

                  )}


                  <div className="message-content">


                    {/* USER MESSAGE */}

                    {message.role ===
                    "user" ? (

                      <div className="user-bubble">
                        {message.text}
                      </div>

                    ) : (


                      /* ASSISTANT MESSAGE */

                      <div className="assistant-bubble">


                        {/* Answer */}

                        <AnswerText
                          text={
                            message.text
                          }
                        />


                        {/* Metrics */}

                        <MetricsView
                          intent={
                            message.intent
                          }
                          metrics={
                            message.metrics
                          }
                        />


                        {/* Data quality */}

                        <DataQuality
                          caveats={
                            message.caveats
                          }
                        />


                      </div>

                    )}

                  </div>

                </div>

              )
            )}


            {/* -------------------------------------------
                LOADING
            ------------------------------------------- */}

            {loading && (

              <div className="message assistant">

                <div className="assistant-avatar">
                  ✦
                </div>


                <div className="message-content">

                  <div className="assistant-bubble loading-bubble">

                    <span className="typing-dot" />

                    <span className="typing-dot" />

                    <span className="typing-dot" />


                    <span className="loading-text">
                      Analyzing live
                      Monday.com data…
                    </span>

                  </div>

                </div>

              </div>

            )}

          </div>


          {/* =================================================
              COMPOSER
          ================================================= */}

          <div className="composer">

            <input

              value={input}

              onChange={(event) =>
                setInput(
                  event.target.value
                )
              }


              onKeyDown={(event) => {

                if (
                  event.key === "Enter"
                ) {

                  event.preventDefault();

                  send();

                }

              }}


              placeholder="Ask a business question..."

              disabled={loading}

            />


            <button

              className="ask-button"

              disabled={
                loading ||
                !input.trim()
              }

              onClick={() =>
                send()
              }

            >

              {loading
                ? "..."
                : "Ask"}

            </button>

          </div>

        </section>


        {/* =================================================
            SIDEBAR
        ================================================= */}

        <aside className="sidebar">


          {/* -----------------------------------------------
              SUGGESTED QUESTIONS
          ----------------------------------------------- */}

          <div className="sidebar-section">

            <h3>
              Suggested questions
            </h3>


            {examples.map(
              (example, index) => (

                <button

                  className="suggestion"

                  key={index}

                  onClick={() =>
                    send(example)
                  }

                  disabled={loading}

                >

                  <span>
                    {example}
                  </span>


                  <span className="suggestion-arrow">
                    →
                  </span>

                </button>

              )
            )}

          </div>


          {/* -----------------------------------------------
              AGENT PRINCIPLES
          ----------------------------------------------- */}

          <div className="sidebar-section principles">

            <h3>
              Agent principles
            </h3>


            <div className="principle">

              <span>
                ✓
              </span>

              Live Monday.com reads

            </div>


            <div className="principle">

              <span>
                ✓
              </span>

              Missing data is disclosed

            </div>


            <div className="principle">

              <span>
                ✓
              </span>

              Deterministic calculations

            </div>


            <div className="principle">

              <span>
                ✓
              </span>

              Cross-board analysis

            </div>


            <div className="principle">

              <span>
                ✓
              </span>

              Graceful API failures

            </div>

          </div>


          {/* -----------------------------------------------
              CURRENT INTENT
          ----------------------------------------------- */}

          {intent && (

            <div className="intent-card">

              <span>
                Current intent
              </span>


              <strong>
                {formatIntent(intent)}
              </strong>

            </div>

          )}

        </aside>

      </main>

    </div>

  );
}


/* =========================================================
   REACT MOUNT
========================================================= */

createRoot(
  document.getElementById("root")
).render(
  <App />
);


export default App;