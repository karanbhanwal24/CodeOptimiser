import React from "react";

function CodePanel({ title, code, tone = "default" }) {
  return (
    <article className={`code-panel code-panel--${tone}`}>
      <div className="code-panel__header">
        <h3>{title}</h3>
      </div>
      <pre>{code || "No code available."}</pre>
    </article>
  );
}

function CodeResultsPanel({ originalCode, selectedVariant }) {
  return (
    <section className="code-grid">
      <CodePanel title="Original Code" code={originalCode} />
      <CodePanel
        title={selectedVariant ? `${selectedVariant.title} Output` : "Optimized Code"}
        code={selectedVariant?.code}
        tone="highlight"
      />
    </section>
  );
}

export default CodeResultsPanel;
