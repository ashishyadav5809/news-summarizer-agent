export default function TopicHeader({ topic }) {
  return (
    <div className="topic">
      <span className="topic__label">Topic</span>
      <h1 className="topic__title">{topic}</h1>
    </div>
  );
}