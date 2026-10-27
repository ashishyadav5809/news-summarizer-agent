import { useState } from "react";
import Navbar from "./components/Navbar";
import NoirSpider from "./components/NoirSpider";
import QueryForm from "./components/QueryForm";
import TopicHeader from "./components/TopicHeader";
import SummaryCard from "./components/SummaryCard";
import KeyPoints from "./components/KeyPoints";
import Sources from "./components/Sources";
import LatestHeadlines from "./components/LatestHeadlines";
import { dummySummary } from "./data/dummySummary";

export default function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const generate = () => {
    setLoading(true);
    setTimeout(() => {
      setResult(dummySummary(query.trim()));
      setLoading(false);
    }, 900);
  };

  return (
    <>
      <Navbar />
      <NoirSpider />
      <main className="main">
        {!result && (
          <div className="hero">
            <h1 className="hero__title">The news, <em>distilled.</em></h1>
            <p className="hero__sub">Ask for any topic. Receive a considered summary.</p>
          </div>
        )}

        <QueryForm query={query} setQuery={setQuery} onGenerate={generate} loading={loading} />

        {result ? (
          <section className="result">
            <TopicHeader topic={result.topic} />
            <SummaryCard text={result.summary} />
            <div className="result__grid">
              <KeyPoints points={result.points} />
              <Sources sources={result.sources} />
            </div>
          </section>
        ) : (
          <LatestHeadlines />
        )}
      </main>
    </>
  );
}