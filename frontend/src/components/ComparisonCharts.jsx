import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function ComparisonCharts({ result }) {
  const bestVariantId = result.best_variant?.id;
  const variantData = [
    {
      name: "Original",
      executionTime: result.original_metrics?.execution_time ?? 0,
      memoryUsage: result.original_metrics?.memory_usage ?? 0,
      fill: "#a54f5c",
    },
    ...(result.variants || []).map((variant) => ({
      name: variant.id,
      label: variant.title,
      executionTime: variant.metrics?.execution_time ?? 0,
      memoryUsage: variant.metrics?.memory_usage ?? 0,
      fill: variant.id === bestVariantId ? "#2f7d58" : "#1d6b63",
    })),
  ];

  return (
    <section className="visual-grid">
      <div className="chart-card">
        <div className="section-heading">
          <h3>Execution Time Comparison</h3>
          <span>Original baseline versus all generated variants</span>
        </div>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={variantData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(24, 26, 22, 0.08)" />
              <XAxis dataKey="name" stroke="#66685f" />
              <YAxis stroke="#66685f" />
              <Tooltip />
              <Legend />
              <Bar dataKey="executionTime" name="Execution Time (ms)" radius={[8, 8, 0, 0]}>
                {variantData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-card">
        <div className="section-heading">
          <h3>Memory Usage Comparison</h3>
          <span>Peak memory across the original code and all variants</span>
        </div>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={variantData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(24, 26, 22, 0.08)" />
              <XAxis dataKey="name" stroke="#66685f" />
              <YAxis stroke="#66685f" />
              <Tooltip />
              <Legend />
              <Bar dataKey="memoryUsage" name="Memory Usage (KB)" radius={[8, 8, 0, 0]}>
                {variantData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

export default ComparisonCharts;
