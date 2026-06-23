type SkeletonBlockProps = {
  width?: string;
  height?: string;
};

export function SkeletonBlock({ width = "100%", height = "14px" }: SkeletonBlockProps) {
  return <span className="hub-skeleton" style={{ width, height }} />;
}
