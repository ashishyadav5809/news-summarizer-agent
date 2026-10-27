export default function QueryForm({ query, setQuery, onGenerate, loading }) {
  const submit = (e) => {
    e.preventDefault();
    if (query.trim()) onGenerate();
  };
  return (
    <form className="query" onSubmit={submit}>
      <input
        className="query__input"
        type="text"
        placeholder="Enter a topic, e.g. global markets, climate summit…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button className="btn btn--solid" type="submit" disabled={loading}>
        {loading ? "Generating…" : "Generate"}
      </button>
    </form>
  );
}