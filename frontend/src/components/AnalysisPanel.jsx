import React from "react";

function AnalysisPanel({ result }) {
  const issues = Array.isArray(result.issues) ? result.issues : [];
  const bestVariant = result.best_variant;
  const originalMetrics = result.original_metrics || {};

  return (
    <section className="detail-grid">
      <div className="panel">
        <div className="section-heading">
          <h3>Issues Detected</h3>
          <span>Static AST findings before optimization</span>
        </div>
        <div className="chip-row">
          {issues.length ? (
            issues.map((issue) => (
              <article className="insight-card insight-card--outline" key={issue.id}>
                <span className={`pill pill--${issue.severity}`}>{issue.severity}</span>
                <h4>{issue.title}</h4>
                <p>{issue.description}</p>
                <small>{issue.suggestion}</small>
              </article>
            ))
          ) : (
            <article className="insight-card insight-card--muted">
              <span className="pill pill--neutral">clean</span>
              <h4>No issues detected</h4>
              <p>The analyzer did not find rule-based improvement opportunities in the current code.</p>
            </article>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="section-heading">
          <h3>Best Variant Reasoning</h3>
          <span>Why the selected optimization outperformed the others</span>
        </div>
        <div className="chip-row">
          {bestVariant ? (
            <>
              <article className="insight-card">
                <span className="pill pill--high">best variant</span>
                <h4>{bestVariant.title}</h4>
                <p>{bestVariant.reason}</p>
                <small>{bestVariant.explanation}</small>
              </article>
              <article className="insight-card insight-card--outline">
                <span className="pill pill--neutral">original profile</span>
                <h4>{originalMetrics.complexity || "Unknown complexity"}</h4>
                <p>
                  {`Loops: ${originalMetrics.loops ?? "--"} · Nested depth: ${originalMetrics.nested_depth ?? "--"} · Calls: ${originalMetrics.function_calls ?? "--"}`}
                </p>
                <small>{`Approx operations: ${originalMetrics.operation_count ?? "--"}`}</small>
              </article>
            </>
          ) : (
            <article className="insight-card insight-card--muted">
              <span className="pill pill--neutral">{issues.length ? "manual review" : "no-op"}</span>
              <h4>{issues.length ? "Optimization opportunity detected" : "No variants generated"}</h4>
              <p>
                {issues.length
                  ? "The analyzer found inefficient structure, but no strategy produced a valid alternate implementation."
                  : "The optimizer did not find a safe variant for the current code."}
              </p>
            </article>
          )}
      </div>
      </div>
    </section>
  );
}

export default AnalysisPanel;
