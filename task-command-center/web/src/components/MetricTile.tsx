type MetricTileProps = {
  label: string;
  value: string;
  total?: string;
  meta?: string;
  progress?: number;
};

export function MetricTile({ label, value, total, meta, progress }: MetricTileProps) {
  const hasProgress = typeof progress === "number";
  const clamped = Math.max(0, Math.min(100, progress ?? 0));

  return (
    <div className="hub-metric-tile">
      <div className="hub-metric-label">{label}</div>
      <div className="hub-metric-value">
        {value}
        {total && <span>/{total}</span>}
      </div>
      {meta && <div className="hub-metric-meta">{meta}</div>}
      {hasProgress && (
        <div className="hub-progress">
          <i style={{ width: `${clamped}%` }} />
        </div>
      )}
    </div>
  );
}
