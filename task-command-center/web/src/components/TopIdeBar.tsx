type TopIdeBarProps = {
  breadcrumb: string[];
  commandLabel?: string;
  isReloading?: boolean;
  onReload?: () => void;
};

export function TopIdeBar({ breadcrumb, commandLabel = "⌘K command palette", isReloading = false, onReload }: TopIdeBarProps) {
  return (
    <header className="hub-topbar">
      <div className="hub-topbar-left">
        <span className="hub-accent-marker" />
        {breadcrumb.map((item, index) => (
          <span className="hub-crumb" key={`${item}-${index}`}>
            {index > 0 && <span className="hub-crumb-sep">/</span>}
            <span>{item}</span>
          </span>
        ))}
      </div>
      <div className="hub-topbar-right">
        <button className="hub-button hub-button-compact" disabled={isReloading} onClick={onReload} type="button">
          <span className={isReloading ? "hub-spin-glyph" : undefined}>↻</span>
          {isReloading ? "loading" : "reload"}
        </button>
        <div aria-disabled="true" className="hub-command-pill">
          {commandLabel}
        </div>
      </div>
    </header>
  );
}
