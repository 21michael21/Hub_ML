import { StatusChip, type StatusChipVariant } from "./StatusChip";

type SectionHeaderProps = {
  eyebrow: string;
  title: string;
  description?: string;
  status?: StatusChipVariant;
};

export function SectionHeader({ eyebrow, title, description, status }: SectionHeaderProps) {
  return (
    <section className="hub-section-header">
      <div className="hub-eyebrow">{eyebrow}</div>
      <div className="hub-section-title-row">
        <h2>{title}</h2>
        {status && <StatusChip label={status} />}
      </div>
      {description && <p>{description}</p>}
    </section>
  );
}
