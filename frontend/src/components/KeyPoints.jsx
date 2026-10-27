export default function KeyPoints({ points }) {
  return (
    <section className="card card--sm">
      <h3 className="card__heading">Key Points</h3>
      <ul className="list">
        {points.map((p, i) => <li key={i}>{p}</li>)}
      </ul>
    </section>
  );
}