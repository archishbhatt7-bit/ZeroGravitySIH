export function GlobeLegend() {
  const items = [
    { color: "#00f0ff", label: "Active" },
    { color: "#999999", label: "Debris" },
    { color: "#eab308", label: "Rocket" },
    { color: "#ef4444", label: "HIGH Risk" },
    { color: "#f97316", label: "MED Risk" },
    { color: "#3b82f6", label: "LOW Risk" },
  ];

  return (
    <div className="globe-legend">
      {items.map((item) => (
        <div key={item.label} className="globe-legend-item">
          <span className="globe-legend-dot" style={{ background: item.color }} />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
