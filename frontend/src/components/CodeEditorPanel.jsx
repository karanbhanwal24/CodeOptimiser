import React from "react";

const SAMPLE_CODE = `numbers = [1, 2, 3, 4, 5]
results = []

for index in range(0, len(numbers)):
    if numbers[index] in [1, 2, 3, 4, 5]:
        results.append(numbers[index] * 2)

print(results)
`;

function CodeEditorPanel({ code, setCode, onOptimize, loading, error }) {
  return (
    <section className="panel composer">
      <div className="section-heading">
        <h3>Code Input Editor</h3>
        <span>Python source only for the current AST optimizer</span>
      </div>

      <textarea
        className="editor"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        spellCheck="false"
      />

      <div className="composer__actions">
        <button className="button button--ghost" onClick={() => setCode(SAMPLE_CODE)} type="button">
          Load sample
        </button>
        <button className="button button--primary" onClick={onOptimize} disabled={loading} type="button">
          {loading ? "Optimizing..." : "Optimize"}
        </button>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}
    </section>
  );
}

export default CodeEditorPanel;
