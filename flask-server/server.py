from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, urllib.parse
import nlp

app = Flask(__name__)
CORS(app)

API_KEY = "531966d5c37d4c18829cfa3f18d2f3d9"

@app.route("/news")
def get_news():
    category = request.args.get("category", "general")
    safe_category = urllib.parse.quote_plus(category)

    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"category={safe_category}&country=us&apiKey={API_KEY}"
    )

    response = requests.get(url)
    if response.status_code != 200:
        return jsonify({"error": f"Failed to fetch news ({response.status_code})"}), response.status_code

    data = response.json()
    articles = data.get("articles", [])

    # 🧠 Run sentiment analysis
    articles = nlp.analyze_sentiment_batch(articles)

    # 🧩 Aggregate sentiment for this category
    summary = nlp.aggregate_by_category(articles, category)

    return jsonify({
        "category": category,
        "summary": summary,
        "articles": articles
    })

if __name__ == "__main__":
    app.run(debug=True)
