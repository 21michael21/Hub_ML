export type StatusChipVariant = "PASS" | "FAIL" | "ERROR" | "IN PROGRESS" | "READY" | "DONE" | "BLOCKED" | "P1" | "P2" | "P3";

type StatusChipProps = {
  label: StatusChipVariant;
  size?: "sm" | "md" | "lg";
  live?: boolean;
};

export function StatusChip({ label, size = "md", live = false }: StatusChipProps) {
  return (
    <span className={`hub-status-chip hub-status-${label.toLowerCase().replaceAll(" ", "-")} hub-status-${size}`}>
      <span className={live ? "hub-status-dot hub-status-dot-live" : "hub-status-dot"} />
      {label}
    </span>
  );
}
