export default function Sources({ sources }) {
  return (
    <section className="card card--sm">
      <h3 className="card__heading">Sources</h3>
      <ul className="list list--plain">
        {sources.map((s) => (
          <li key={s.name} className="source">
            <span>{s.name}</span><small>{s.time}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}