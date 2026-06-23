type EmptyStateProps = {
  title: string;
  body: string;
  action: string;
};

export function EmptyState({ title, body, action }: EmptyStateProps) {
  return (
    <section className="hub-empty-state">
      <div className="hub-empty-icon">∅</div>
      <h3>{title}</h3>
      <p>{body}</p>
      <a href="#">{action}</a>
    </section>
  );
}
