import { StatusChip } from "./StatusChip";

type QualityGateCardProps = {
  percent: number;
  label: string;
  status: "READY" | "PASS" | "IN PROGRESS";
  caption: string;
  details?: string[];
};

export function QualityGateCard({ percent, label, status, caption, details = [] }: QualityGateCardProps) {
  const clamped = Math.max(0, Math.min(100, percent));

  return (
    <section className="hub-quality-card">
      <svg className="hub-quality-ring" width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
        <circle cx="48" cy="48" r="34" fill="none" stroke="var(--hub-raised)" strokeWidth="8" />
        <circle
          cx="48"
          cy="48"
          r="34"
          fill="none"
          stroke="var(--hub-pass)"
          strokeDasharray="213.6"
          strokeDashoffset={213.6 - (213.6 * clamped) / 100}
          strokeLinecap="round"
          strokeWidth="8"
        />
      </svg>
      <div className="hub-quality-percent">{clamped}%</div>
      <div>
        <div className="hub-quality-label">{label}</div>
        <StatusChip label={status === "IN PROGRESS" ? "IN PROGRESS" : status} live={status === "IN PROGRESS"} />
        <p>{caption}</p>
        {details.length > 0 && (
          <div className="hub-quality-details">
            {details.map((detail) => (
              <span key={detail}>{detail}</span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
