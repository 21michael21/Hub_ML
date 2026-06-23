import type { ReactNode } from "react";
import { BottomStatusBar } from "./BottomStatusBar";
import { TopIdeBar } from "./TopIdeBar";

type AppShellProps = {
  children: ReactNode;
  breadcrumb?: string[];
  commandLabel?: string;
  isReloading?: boolean;
  onReload?: () => void;
  statusLeft?: string[];
  statusRight?: string[];
};

export function AppShell({
  children,
  breadcrumb = ["Task Command", "Home"],
  commandLabel,
  isReloading = false,
  onReload,
  statusLeft = ["local · online", "trello connected", "calendar connected"],
  statusRight = ["main", "⌘K"],
}: AppShellProps) {
  return (
    <div className="hub-shell">
      <TopIdeBar breadcrumb={breadcrumb} commandLabel={commandLabel} isReloading={isReloading} onReload={onReload} />
      <main className="hub-main">{children}</main>
      <BottomStatusBar left={statusLeft} right={statusRight} />
    </div>
  );
}
