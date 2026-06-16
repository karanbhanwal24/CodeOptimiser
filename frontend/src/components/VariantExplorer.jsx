import React from "react";

const formatNumber = (value, digits = 4) =>
  typeof value === "number" ? value.toFixed(digits) : "--";

function VariantExplorer({ variants = [], bestVariantId, selectedVariantId, setSelectedVariantId }) {
  const selectedVariant =
    variants.find((variant) => variant.id === selectedVariantId) ||
    variants.find((variant) => variant.id === bestVariantId) ||
    variants[0];

  if (!variants.length) {
    return (
      <section className="panel">
        <div className="section-heading">
          <h3>Optimization Variants</h3>
          <span>No alternate strategies were generated for this input</span>
        </div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Optimization Variants</h3>
        <span>Switch between generated strategies and inspect their metrics</span>
      </div>

      <div className="variant-tabs">
        {variants.map((variant) => (
          <button
            key={variant.id}
            type="button"
            className={`variant-tab ${selectedVariant?.id === variant.id ? "variant-tab--active" : ""}`}
            onClick={() => setSelectedVariantId(variant.id)}
          >
            <span>{variant.id}</span>
            <strong>{variant.title}</strong>
            {variant.id === bestVariantId ? <small>Best</small> : <small>{variant.strategy}</small>}
          </button>
        ))}
      </div>

      {selectedVariant ? (
        <div className="variant-detail-grid">
          <article className="insight-card">
            <span className={`pill pill--${selectedVariant.id === bestVariantId ? "high" : "medium"}`}>
              {selectedVariant.id === bestVariantId ? "best variant" : selectedVariant.strategy}
            </span>
            <h4>{selectedVariant.title}</h4>
            <p>{selectedVariant.explanation}</p>
            <small>{selectedVariant.why_better}</small>
          </article>

          <article className="insight-card insight-card--outline">
            <span className="pill pill--neutral">metrics</span>
            <h4>{`${formatNumber(selectedVariant.metrics?.execution_time)} ms`}</h4>
            <p>
              {`Memory ${formatNumber(selectedVariant.metrics?.memory_usage, 2)} KB · Complexity ${selectedVariant.metrics?.complexity || "--"}`}
            </p>
            <small>
              {`Time gain ${formatNumber(selectedVariant.gain?.time_gain_percent, 2)}% · Memory gain ${formatNumber(selectedVariant.gain?.memory_gain_percent, 2)}%`}
            </small>
          </article>

          <article className="insight-card insight-card--outline">
            <span className="pill pill--neutral">techniques</span>
            <h4>{selectedVariant.applied_techniques?.length || 0} applied</h4>
            <p>
              {(selectedVariant.applied_techniques || [])
                .map((technique) => technique.title)
                .join(", ") || "No concrete transform metadata available."}
            </p>
          </article>
        </div>
      ) : null}
    </section>
  );
}

export default VariantExplorer;
