import React, { useMemo, useState } from "react";
import axios from "axios";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const SAMPLE_SNIPPETS = [
  {
    label: "Nested Loops",
    code: `items = [1, 2, 3, 4]
other = [2, 4]
matches = []
for item in items:
    for candidate in other:
        if item == candidate:
            matches.append(item)
print(matches)
`
  },
  {
    label: "Fibonacci",
    code: `def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(10))
`
  },
  {
    label: "String Concat",
    code: `parts = ["alpha", "beta", "gamma"]
result = ""
for part in parts:
    result += part.upper()
print(result)
`
  },
  {
    label: "Dead Code",
    code: `def transform(values):
    unused_total = 0
    result = []
    for value in values:
        result.append(value * 2)
    return result
`
  },
  {
    label: "Bubble Sort",
    code: `def bubble_sort(values):
    values = values.copy()
    for i in range(len(values)):
        for j in range(0, len(values) - i - 1):
            if values[j] > values[j + 1]:
                values[j], values[j + 1] = values[j + 1], values[j]
    return values

print(bubble_sort([4, 1, 3, 2]))
`
  }
];

const TABS = ["Output", "Issues", "Metrics", "Explains", "History"];
const API_BASE_URL = import.meta.env.DEV ? "" : import.meta.env.VITE_API_BASE_URL || "/api";
const api = axios.create({
  baseURL: API_BASE_URL
});

const styles = {
  app: {
    minHeight: "100vh",
    background: "radial-gradient(circle at top left, #e9f3ff 0%, #f7f3ea 45%, #f3efe6 100%)",
    color: "var(--color-text-primary)",
    fontFamily: '"Segoe UI", "Helvetica Neue", sans-serif',
    padding: "24px"
  },
  shell: {
    maxWidth: "1440px",
    margin: "0 auto"
  },
  banner: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#ffe1df",
    color: "#8a1f17",
    border: "1px solid #efb0ab",
    borderRadius: "14px",
    padding: "12px 16px",
    marginBottom: "16px"
  },
  hero: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    flexWrap: "wrap",
    marginBottom: "18px"
  },
  heroCard: {
    flex: "1 1 420px",
    background: "rgba(255, 255, 255, 0.82)",
    border: "1px solid rgba(20, 44, 72, 0.08)",
    borderRadius: "24px",
    padding: "24px",
    boxShadow: "0 18px 50px rgba(19, 41, 61, 0.08)"
  },
  workspace: {
    display: "flex",
    gap: "18px",
    flexWrap: "wrap",
    alignItems: "stretch"
  },
  panel: {
    background: "rgba(255, 255, 255, 0.86)",
    border: "1px solid rgba(20, 44, 72, 0.08)",
    borderRadius: "24px",
    boxShadow: "0 18px 50px rgba(19, 41, 61, 0.08)"
  },
  leftPane: {
    flex: "1 1 560px",
    minWidth: "320px",
    padding: "20px"
  },
  rightPane: {
    flex: "1 1 520px",
    minWidth: "320px",
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "16px"
  },
  textarea: {
    width: "100%",
    minHeight: "460px",
    resize: "vertical",
    borderRadius: "18px",
    border: "1px solid #c7d7e6",
    padding: "16px",
    background: "#0f1723",
    color: "#edf5ff",
    fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", monospace',
    fontSize: "14px",
    lineHeight: 1.55,
    outline: "none",
    boxSizing: "border-box"
  },
  chipRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginBottom: "16px"
  },
  chip: {
    borderRadius: "999px",
    border: "1px solid #d5dfeb",
    background: "#f8fbff",
    color: "#24415c",
    padding: "8px 12px",
    cursor: "pointer",
    fontSize: "13px"
  },
  buttonRow: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
    marginTop: "16px"
  },
  button: {
    border: "none",
    borderRadius: "14px",
    padding: "12px 18px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: 600
  },
  primaryButton: {
    background: "#123d66",
    color: "#ffffff"
  },
  secondaryButton: {
    background: "#e7eef5",
    color: "#17324b"
  },
  tabRow: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap"
  },
  tab: {
    borderRadius: "999px",
    padding: "8px 14px",
    border: "1px solid #d3dce8",
    cursor: "pointer",
    background: "#f5f8fb",
    color: "#34506b",
    fontSize: "13px",
    fontWeight: 600
  },
  activeTab: {
    background: "#143a5d",
    color: "#ffffff",
    borderColor: "#143a5d"
  },
  pre: {
    background: "#101823",
    color: "#edf5ff",
    borderRadius: "18px",
    padding: "16px",
    overflowX: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", monospace',
    fontSize: "13px",
    lineHeight: 1.6
  },
  issueGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "10px"
  },
  issueItem: {
    display: "flex",
    gap: "12px",
    alignItems: "flex-start",
    padding: "12px 14px",
    borderRadius: "16px",
    background: "#f9fbfd",
    border: "1px solid #e2eaf2"
  },
  severityDot: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    marginTop: "6px",
    flexShrink: 0
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: "12px"
  },
  metricCard: {
    borderRadius: "18px",
    padding: "16px",
    background: "#f8fbff",
    border: "1px solid #dde7f1"
  },
  chartCard: {
    height: "250px",
    borderRadius: "18px",
    padding: "12px",
    background: "#f8fbff",
    border: "1px solid #dde7f1"
  },
  historyHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap"
  },
  historyList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  historyItem: {
    borderRadius: "18px",
    padding: "16px",
    background: "#f8fbff",
    border: "1px solid #dde7f1",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  historyMeta: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    color: "var(--color-text-secondary)",
    fontSize: "13px"
  },
  historyActions: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap"
  },
  codePreview: {
    margin: 0,
    padding: "12px 14px",
    borderRadius: "14px",
    background: "#eef5fb",
    color: "#17324b",
    fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", monospace',
    fontSize: "12px",
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word"
  }
};

function formatNumber(value, suffix = "") {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${Number(value).toFixed(3)}${suffix}`;
}

function groupIssues(issues) {
  return issues.reduce((groups, issue) => {
    const key = issue.category || "general";
    groups[key] = groups[key] || [];
    groups[key].push(issue);
    return groups;
  }, {});
}

function formatTimestamp(value) {
  if (!value) {
    return "unknown";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function previewCode(code, maxLength = 180) {
  if (!code) {
    return "No code saved.";
  }

  const normalized = code.trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}...`;
}

function App() {
  const [code, setCode] = useState(SAMPLE_SNIPPETS[0].code);
  const [optimizedCode, setOptimizedCode] = useState("");
  const [issues, setIssues] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [explanation, setExplanation] = useState({ text: "", improvements: [] });
  const [historyRecords, setHistoryRecords] = useState([]);
  const [loading, setLoading] = useState("");
  const [activeTab, setActiveTab] = useState("Output");
  const [error, setError] = useState("");

  const groupedIssues = useMemo(() => groupIssues(issues), [issues]);

  async function withLoading(action, request) {
    try {
      setLoading(action);
      setError("");
      await request();
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || err.message || "Request failed");
    } finally {
      setLoading("");
    }
  }


  function populateFromMetrics(data) {
    setMetrics(data);
    if (data.optimized_code) {
      setOptimizedCode(data.optimized_code);
    }
  }

  async function runOptimizer() {
    await withLoading("optimize", async () => {
      const response = await api.post("/optimize", { code });
      const data = response.data;
      setOptimizedCode(data.optimized_code || "");
      setIssues(data.analysis?.issues || []);
      setMetrics(data);
      setExplanation({
        text: data.explanation || "Optimization completed.",
        improvements: data.improvements || []
      });
      setHistoryRecords((current) => {
        const nextRecord = {
          id: data.record_id,
          original_code: code,
          optimized_code: data.optimized_code || "",
          explanation: data.explanation || "Optimization completed.",
          original_time_ms: data.original_time_ms,
          optimized_time_ms: data.optimized_time_ms,
          original_memory_mb: data.original_memory_mb,
          optimized_memory_mb: data.optimized_memory_mb,
          time_improvement_pct: data.time_improvement_pct,
          memory_improvement_pct: data.memory_improvement_pct,
          lines_of_code_before: data.lines_of_code_before,
          lines_of_code_after: data.lines_of_code_after,
          cyclomatic_complexity_before: data.cyclomatic_complexity_before,
          cyclomatic_complexity_after: data.cyclomatic_complexity_after,
          improvements: data.improvements || [],
          variants: data.variants || [],
          analysis: data.analysis || {},
          created_at: new Date().toISOString()
        };
        return [nextRecord, ...current.filter((item) => item.id !== nextRecord.id)];
      });
      setActiveTab("Output");
    });
  }

  async function runAnalysis() {
    await withLoading("analysis", async () => {
      const response = await api.post("/analysis", { code });
      setIssues(response.data.issues || []);
      setActiveTab("Issues");
    });
  }

  async function runMetrics() {
    await withLoading("metrics", async () => {
      const payload = { original_code: code };
      if (optimizedCode) {
        payload.variants = [
          {
            name: "current-optimized",
            code: optimizedCode,
            description: "Current optimized code from the output panel.",
            technique: "User-selected optimized code",
            category: "performance"
          }
        ];
      }
      const response = await api.post("/metrics", payload);
      populateFromMetrics(response.data);
      setExplanation((current) => ({
        text: response.data.explanation || current.text,
        improvements: response.data.improvements || current.improvements
      }));
      setActiveTab("Metrics");
    });
  }

  function applyHistoryRecord(record) {
    setCode(record.original_code || "");
    setOptimizedCode(record.optimized_code || "");
    setIssues(record.analysis?.issues || []);
    setMetrics({
      optimized_code: record.optimized_code,
      original_time_ms: record.original_time_ms,
      optimized_time_ms: record.optimized_time_ms,
      original_memory_mb: record.original_memory_mb,
      optimized_memory_mb: record.optimized_memory_mb,
      time_improvement_pct: record.time_improvement_pct,
      memory_improvement_pct: record.memory_improvement_pct,
      lines_of_code_before: record.lines_of_code_before,
      lines_of_code_after: record.lines_of_code_after,
      cyclomatic_complexity_before: record.cyclomatic_complexity_before,
      cyclomatic_complexity_after: record.cyclomatic_complexity_after,
      variants: record.variants || [],
      analysis: record.analysis || {}
    });
    setExplanation({
      text: record.explanation || "Loaded from history.",
      improvements: record.improvements || []
    });
    setActiveTab("Output");
  }

  async function loadHistory({ force = false } = {}) {
    if (!force && historyRecords.length) {
      setActiveTab("History");
      return;
    }

    await withLoading("history", async () => {
      const response = await api.get("/optimizations");
      setHistoryRecords(response.data.items || []);
      setActiveTab("History");
    });
  }

  // no auth functions — authentication removed

  function onEditorKeyDown(event) {
    if (event.key !== "Tab") {
      return;
    }
    event.preventDefault();
    const { selectionStart, selectionEnd, value } = event.currentTarget;
    const nextValue = `${value.slice(0, selectionStart)}  ${value.slice(selectionEnd)}`;
    setCode(nextValue);
    requestAnimationFrame(() => {
      event.currentTarget.selectionStart = selectionStart + 2;
      event.currentTarget.selectionEnd = selectionStart + 2;
    });
  }

  const timeChartData = [
    { name: "Original", value: metrics?.original_time_ms ?? 0 },
    { name: "Optimized", value: metrics?.optimized_time_ms ?? 0 }
  ];

  const memoryChartData = [
    { name: "Original", value: metrics?.original_memory_mb ?? 0 },
    { name: "Optimized", value: metrics?.optimized_memory_mb ?? 0 }
  ];

  return (
    <div
      style={{
        ...styles.app,
        "--color-text-primary": "#132a3b",
        "--color-text-secondary": "#4e6478",
        "--color-accent": "#123d66",
        "--color-surface": "#ffffff"
      }}
    >
      <div style={styles.shell}>
        {error ? (
          <div style={styles.banner}>
            <span>{error}</span>
            <button style={{ ...styles.button, ...styles.secondaryButton, padding: "8px 12px" }} onClick={() => setError("")}>
              Dismiss
            </button>
          </div>
        ) : null}

        <div style={styles.hero}>
          <section style={styles.heroCard}>
            <div style={{ fontSize: "12px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-text-secondary)", marginBottom: "12px" }}>
              3-Tier Code Optimizer
            </div>
            <h1 style={{ margin: "0 0 10px", fontSize: "clamp(2rem, 3vw, 3rem)", lineHeight: 1.05 }}>
              Analyze Python code, generate AST-safe rewrites, and compare the runtime tradeoffs.
            </h1>
            <p style={{ margin: 0, color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              The optimizer produces independent variants plus a combined rewrite, reports timing and memory,
              and surfaces analysis issues before you accept a suggestion.
            </p>
          </section>

          <section style={{ ...styles.heroCard, flex: "0 1 280px" }}>
            <div style={{ color: "var(--color-text-secondary)", fontSize: "13px", marginBottom: "6px" }}>Current best time improvement</div>
            <div style={{ fontSize: "2.4rem", fontWeight: 700, color: "var(--color-accent)" }}>
              {formatNumber(metrics?.time_improvement_pct, "%")}
            </div>
            <div style={{ color: "var(--color-text-secondary)", marginTop: "10px", lineHeight: 1.5 }}>
              {metrics?.variants?.find((variant) => variant.code === optimizedCode)?.name || "Run the optimizer to benchmark variants."}
            </div>
          </section>
          {/* Account panel removed to keep UI compact and auth-free */}
        </div>

        <div style={styles.workspace}>
          <section style={{ ...styles.panel, ...styles.leftPane }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-text-secondary)" }}>Code Editor</div>
                <div style={{ fontSize: "24px", fontWeight: 700 }}>Source Input</div>
              </div>
            </div>

            <div style={styles.chipRow}>
              {SAMPLE_SNIPPETS.map((sample) => (
                <button key={sample.label} style={styles.chip} onClick={() => setCode(sample.code)}>
                  {sample.label}
                </button>
              ))}
            </div>

            <textarea
              value={code}
              onChange={(event) => setCode(event.target.value)}
              onKeyDown={onEditorKeyDown}
              spellCheck={false}
              style={styles.textarea}
            />

            <div style={styles.buttonRow}>
              <button style={{ ...styles.button, ...styles.primaryButton }} onClick={runOptimizer} disabled={Boolean(loading)}>
                {loading === "optimize" ? "Running..." : "Run Optimizer"}
              </button>
              <button style={{ ...styles.button, ...styles.secondaryButton }} onClick={runAnalysis} disabled={Boolean(loading)}>
                {loading === "analysis" ? "Analyzing..." : "Analyze"}
              </button>
              <button style={{ ...styles.button, ...styles.secondaryButton }} onClick={runMetrics} disabled={Boolean(loading)}>
                {loading === "metrics" ? "Measuring..." : "Metrics"}
              </button>
              <button style={{ ...styles.button, ...styles.secondaryButton }} onClick={() => loadHistory({ force: true })} disabled={Boolean(loading)}>
                {loading === "history" ? "Loading..." : "View History"}
              </button>
            </div>
          </section>

          <section style={{ ...styles.panel, ...styles.rightPane }}>
            <div style={styles.tabRow}>
              {TABS.map((tab) => (
                <button
                  key={tab}
                  style={{ ...styles.tab, ...(activeTab === tab ? styles.activeTab : null) }}
                  onClick={() => {
                    if (tab === "History") {
                      loadHistory();
                      return;
                    }
                    setActiveTab(tab);
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === "Output" ? (
              <div>
                <div style={{ fontSize: "13px", color: "var(--color-text-secondary)", marginBottom: "10px" }}>Optimized code</div>
                <pre style={styles.pre}>{optimizedCode || "Run the optimizer to see rewritten code."}</pre>
              </div>
            ) : null}

            {activeTab === "Issues" ? (
              <div style={styles.issueGroup}>
                {Object.keys(groupedIssues).length ? Object.entries(groupedIssues).map(([category, categoryIssues]) => (
                  <div key={category}>
                    <div style={{ fontWeight: 700, textTransform: "capitalize", marginBottom: "10px" }}>{category}</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      {categoryIssues.map((issue, index) => {
                        const color = issue.severity === "high" ? "#d8443f" : issue.severity === "medium" ? "#d29a19" : "#3f8f57";
                        return (
                          <div key={`${category}-${index}`} style={styles.issueItem}>
                            <span style={{ ...styles.severityDot, background: color }} />
                            <div>
                              <div style={{ fontWeight: 600 }}>{issue.description}</div>
                              <div style={{ color: "var(--color-text-secondary)", fontSize: "13px", marginTop: "4px" }}>
                                Line {issue.line} • severity {issue.severity} • fix {String(issue.fix_available)} • effort {issue.effort} • impact {issue.impact}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )) : <div style={{ color: "var(--color-text-secondary)" }}>Run analysis to see detected issues.</div>}
              </div>
            ) : null}

            {activeTab === "Metrics" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={styles.metricsGrid}>
                  <div style={styles.metricCard}>
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>Original Time</div>
                    <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{formatNumber(metrics?.original_time_ms, " ms")}</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>Optimized Time</div>
                    <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{formatNumber(metrics?.optimized_time_ms, " ms")}</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>Original Memory</div>
                    <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{formatNumber(metrics?.original_memory_mb, " MB")}</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>Optimized Memory</div>
                    <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{formatNumber(metrics?.optimized_memory_mb, " MB")}</div>
                  </div>
                </div>

                <div style={styles.chartCard}>
                  <div style={{ fontWeight: 700, marginBottom: "10px" }}>Time Comparison</div>
                  <ResponsiveContainer width="100%" height="88%">
                    <BarChart data={timeChartData} layout="vertical" margin={{ top: 0, right: 12, left: 12, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="name" type="category" width={72} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#143a5d" radius={[0, 8, 8, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div style={styles.chartCard}>
                  <div style={{ fontWeight: 700, marginBottom: "10px" }}>Memory Comparison</div>
                  <ResponsiveContainer width="100%" height="88%">
                    <BarChart data={memoryChartData} layout="vertical" margin={{ top: 0, right: 12, left: 12, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="name" type="category" width={72} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#d08b1f" radius={[0, 8, 8, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {metrics?.cyclomatic_complexity_before !== undefined ? (
                  <div style={{ ...styles.metricCard, display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                    <span>Complexity before: {metrics.cyclomatic_complexity_before}</span>
                    <span>Complexity after: {metrics.cyclomatic_complexity_after}</span>
                    <span>Lines before: {metrics.lines_of_code_before}</span>
                    <span>Lines after: {metrics.lines_of_code_after}</span>
                  </div>
                ) : null}
              </div>
            ) : null}

            {activeTab === "Explains" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ ...styles.metricCard, lineHeight: 1.6 }}>
                  {explanation.text || "Run the optimizer to generate a summary."}
                </div>
                <div style={{ ...styles.metricCard, paddingBottom: "8px" }}>
                  <div style={{ fontWeight: 700, marginBottom: "10px" }}>Improvements</div>
                  {(explanation.improvements || []).length ? (
                    <ul style={{ margin: 0, paddingLeft: "18px", lineHeight: 1.7 }}>
                      {explanation.improvements.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                    </ul>
                  ) : (
                    <div style={{ color: "var(--color-text-secondary)" }}>No optimization details available yet.</div>
                  )}
                </div>
              </div>
            ) : null}

            {activeTab === "History" ? (
              <div style={styles.historyList}>
                <div style={styles.historyHeader}>
                  <div>
                    <div style={{ fontWeight: 700 }}>Optimization History</div>
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "13px", marginTop: "4px" }}>
                      Saved optimization runs from PostgreSQL.
                    </div>
                  </div>
                  <button
                    style={{ ...styles.button, ...styles.secondaryButton, padding: "10px 14px" }}
                    onClick={() => loadHistory({ force: true })}
                    disabled={Boolean(loading)}
                  >
                    {loading === "history" ? "Refreshing..." : "Refresh"}
                  </button>
                </div>

                {historyRecords.length ? historyRecords.map((record) => (
                  <div key={record.id} style={styles.historyItem}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                      <div style={{ fontWeight: 700 }}>Run #{record.id}</div>
                      <div style={styles.historyMeta}>
                        <span>{formatTimestamp(record.created_at)}</span>
                        <span>Time gain {formatNumber(record.time_improvement_pct, "%")}</span>
                        <span>Memory gain {formatNumber(record.memory_improvement_pct, "%")}</span>
                      </div>
                    </div>

                    <pre style={styles.codePreview}>{previewCode(record.original_code)}</pre>

                    <div style={styles.historyActions}>
                      <button
                        style={{ ...styles.button, ...styles.primaryButton, padding: "10px 14px" }}
                        onClick={() => applyHistoryRecord(record)}
                      >
                        Load Run
                      </button>
                      <button
                        style={{ ...styles.button, ...styles.secondaryButton, padding: "10px 14px" }}
                        onClick={() => {
                          setCode(record.original_code || "");
                          setActiveTab("Output");
                        }}
                      >
                        Load Source Only
                      </button>
                    </div>
                  </div>
                )) : (
                  <div style={{ ...styles.metricCard, color: "var(--color-text-secondary)" }}>
                    No optimization history yet. Run the optimizer once to create a saved record.
                  </div>
                )}
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
