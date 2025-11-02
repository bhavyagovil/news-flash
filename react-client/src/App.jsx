import React, { useEffect, useState } from "react";
import "./app.css";

function App() {
  const [articles, setArticles] = useState([]);
  const [summary, setSummary] = useState(null);
  const [category, setCategory] = useState("general");
  const [loading, setLoading] = useState(false);

  const fetchNews = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:5000/news?category=${category}`);
      const data = await res.json();

      setArticles(data.articles || []);
      setSummary(data.summary || null);
    } catch (err) {
      console.error("Error fetching news:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 6000000);
    return () => clearInterval(interval);
  }, [category]);

  return (
    <div className="app">
      <h1>NEWS FLASH!</h1>

      <label className="category-label">
        Category:{" "}
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="business">Business</option>
          <option value="entertainment">Entertainment</option>
          <option value="general">General</option>
          <option value="health">Health</option>
          <option value="science">Science</option>
          <option value="sports">Sports</option>
          <option value="technology">Technology</option>
        </select>
      </label>

      <p className="refresh-note">Auto-refreshing every 10 minutes</p>

      {summary && (
        <div className="summary-card">
          <h2>
            {summary.category.toUpperCase()}:{" "}
            {summary.overall_label === "Positive" ? (
              <span style={{ color: "green" }}>Positive</span>
            ) : summary.overall_label === "Negative" ? (
              <span style={{ color: "darkred" }}>Negative</span>
            ) : (
              <span style={{ color: "gray" }}>Neutral</span>
            )}
          </h2>
          <p>
            Avg Sentiment: {summary.average_sentiment.toFixed(4)}
          </p>
        </div>
      )}

      {loading && <p className="loading">Loading latest headlines...</p>}

      <ul className="article-list">
        {articles.map((a, i) => (
          <li key={i} className="article-item">
            {a.urlToImage && (
              <img src={a.urlToImage} alt="" className="article-thumb" />
            )}
            <div className="article-text">
              <a href={a.url} target="_blank" rel="noreferrer">
                {a.title}
              </a>
              {a.sentiment && (
                <p className="sentiment-line">
                  Sentiment:{" "}
                  <span
                    style={{
                      color:
                        a.sentiment === "POSITIVE"
                          ? "green"
                          : a.sentiment === "NEGATIVE"
                          ? "darkred"
                          : "gray",
                      fontWeight: "bold",
                    }}
                  >
                    {a.sentiment}
                  </span>{" "}
                  ({(a.score * 100).toFixed(1)}%)
                </p>
              )}
              {a.source?.name && (
                <span className="source"> — {a.source.name}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
