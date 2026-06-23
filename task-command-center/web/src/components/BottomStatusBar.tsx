type BottomStatusBarProps = {
  left: string[];
  right: string[];
};

export function BottomStatusBar({ left, right }: BottomStatusBarProps) {
  return (
    <footer className="hub-statusbar">
      <div className="hub-statusbar-group">
        <span className="hub-status-online">
          <span />
          {left[0]}
        </span>
        {left.slice(1).map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      <div className="hub-statusbar-group">
        {right.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
    </footer>
  );
}
