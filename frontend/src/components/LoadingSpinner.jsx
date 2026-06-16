import React from "react";

function LoadingSpinner() {
  return (
    <section className="panel loading-panel">
      <div className="spinner" />
      <div>
        <h3>Processing</h3>
        <p>Analyzing AST, generating candidate optimization, and running benchmark comparisons.</p>
      </div>
    </section>
  );
}

export default LoadingSpinner;
