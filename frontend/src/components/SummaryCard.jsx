export default function SummaryCard({ text }) {
  return (
    <article className="card">
      <h2 className="card__heading">Summary</h2>
      <p className="card__text">{text}</p>
    </article>
  );
}