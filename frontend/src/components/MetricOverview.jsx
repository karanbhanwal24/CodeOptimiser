import React from "react";

const formatNumber = (value, digits = 2) =>
  typeof value === "number" ? value.toFixed(digits) : "--";

function MetricCard({ label, value, detail, accent }) {
  return (
    <article className={`metric-card metric-card--${accent}`}>
      <span className="metric-card__label">{label}</span>
      <strong className="metric-card__value">{value}</strong>
      <span className="metric-card__detail">{detail}</span>
    </article>
  );
}

function MetricOverview({ result }) {
  const { original_metrics: originalMetrics, best_variant: bestVariant, comparison, benchmark, variants } = result;

  return (
    <section className="metrics-row">
      <MetricCard
        label="Best Strategy"
        value={bestVariant?.title || "No variant"}
        detail={`${variants?.length ?? 0} generated variants`}
        accent="teal"
      />
      <MetricCard
        label="Execution Gain"
        value={`${formatNumber(comparison?.time_gain_percent, 2)}%`}
        detail={`Average over ${benchmark?.runs ?? "--"} runs`}
        accent="sand"
      />
      <MetricCard
        label="Memory Gain"
        value={`${formatNumber(comparison?.memory_gain_percent, 2)}%`}
        detail={`Timeout ${benchmark?.timeout_seconds ?? "--"}s`}
        accent="emerald"
      />
      <MetricCard
        label="Original Complexity"
        value={originalMetrics?.complexity || "--"}
        detail={`Loops ${originalMetrics?.loops ?? "--"} · calls ${originalMetrics?.function_calls ?? "--"}`}
        accent="rose"
      />
    </section>
  );
}

export default MetricOverview;
