import { latestHeadlines } from "../data/dummySummary";

export default function LatestHeadlines() {
  return (
    <section className="headlines">
      <h3 className="headlines__title">Latest Headlines</h3>
      <div className="headlines__grid">
        {latestHeadlines.map((h) => (
          <div className="card card--sm" key={h.title}>
            <small className="tag">{h.tag}</small>
            <p className="card__text">{h.title}</p>
          </div>
        ))}
      </div>
    </section>
  );
}