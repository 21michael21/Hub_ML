import type { ReactNode } from "react";
import { StatusChip, type StatusChipVariant } from "./StatusChip";

type ClickableCardProps = {
  title: string;
  meta: string;
  action: string;
  status?: StatusChipVariant;
  href?: string;
  fail?: boolean;
  children?: ReactNode;
};

export function ClickableCard({ title, meta, action, status, href = "#", fail = false, children }: ClickableCardProps) {
  return (
    <a className={fail ? "hub-clickable-card hub-clickable-card-fail" : "hub-clickable-card"} href={href}>
      <span className="hub-clickable-body">
        <span className="hub-clickable-title">
          {title}
          {status && <StatusChip label={status} size="sm" live={status === "IN PROGRESS"} />}
        </span>
        <span className={fail ? "hub-clickable-meta hub-clickable-meta-fail" : "hub-clickable-meta"}>{meta}</span>
        {children}
      </span>
      <span className="hub-clickable-arrow">→ {action}</span>
    </a>
  );
}
