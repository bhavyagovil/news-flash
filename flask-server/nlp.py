
from transformers import pipeline

import json
from datetime import datetime, timedelta,UTC
import os
import re
from newsapi import NewsApiClient

newsapi = NewsApiClient(api_key='531966d5c37d4c18829cfa3f18d2f3d9')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, 'sentiment_cache.json')
CACHE_TTL = 600

nlp_pipeline = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment"
)
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'http\S+|www\S+', '', text)
    
    text = re.sub(r'[^A-Za-z0-9\s]+', '', text)
    return text.lower().strip()
    
def analyze_sentiment_batch(articles):
    texts = []
    for article in articles:
        text = f"{article['title']} {article.get('description', '')}"
        cleaned = clean_text(text)
        texts.append(cleaned if cleaned else "neutral")

    sentiments = nlp_pipeline(texts, batch_size=8)

    label_map = {"LABEL_0": "NEGATIVE", "LABEL_1": "NEUTRAL", "LABEL_2": "POSITIVE"}

    for article, sentiment in zip(articles, sentiments):
        label = label_map.get(sentiment['label'], sentiment['label'])
        article['sentiment'] = label
        article['score'] = sentiment['score']

        if label == 'POSITIVE':
            article['sentiment_score'] = sentiment['score']
        elif label == 'NEGATIVE':
            article['sentiment_score'] = -sentiment['score']
        else:
            article['sentiment_score'] = 0.0

    return articles




def aggregate_by_category(articles, category):
    category = category.lower()
    positive_count = sum(1 for a in articles if a['sentiment'] == 'POSITIVE')
    negative_count = sum(1 for a in articles if a['sentiment'] == 'NEGATIVE')
    avg_sentiment = sum(a['sentiment_score'] for a in articles) / len(articles) if articles else 0

    summary = {
        "category": category,
        "average_sentiment": avg_sentiment,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "overall_label": "Positive" if avg_sentiment > 0 else "Negative" if avg_sentiment < 0 else "Neutral"
    }
    return summary




def save_to_history(cache, cache_key, articles, aggregagted_data):
    if cache_key not in cache:
        cache[cache_key] = {
            'current': {},
            'history': [],
        }

    snapshot = {
            'timestamp': datetime.now(UTC).isoformat(),
            'arcticle_count' : len(articles),
            'aggregated': aggregagted_data,
            }

    cache[cache_key]['history'].append(snapshot)
    cache[cache_key]['current'] = snapshot

    if len(cache[cache_key]['history']) > 10:
            cache[cache_key]['history'] = cache[cache_key]['history'][-10:]

    return cache
    
def calculate_deltas(cache, cache_key):
    if not cache_key or cache_key not in cache or 'history' not in cache[cache_key]:
        return None

    history = cache[cache_key]['history']
    if len(history) < 2:
        return {
            'status': 'insufficient_data',
        }
    
    current = history[-1]
    previous = history[-2]

    current_time = datetime.fromisoformat(current['timestamp'])
    previous_time = datetime.fromisoformat(previous['timestamp'])
    time_diff = (current_time - previous_time).total_seconds() / 60.0

    overall_change = (current['arcticle_count'] - previous['arcticle_count'])
    overall_rate = overall_change / time_diff if time_diff > 0 else 0

    topic_deltas = {}
    for topic in current['aggregated'].keys():
        if topic in previous['aggregated']:
            curr_agg = current['aggregated'][topic]
            prev_agg = previous['aggregated'][topic]

            topic_change = curr_agg['article_count'] - prev_agg['article_count']
            topic_rate = topic_change / time_diff if time_diff > 0 else 0

            topic_deltas[topic] = {
                'article_count_change': topic_change,
                'article_count_rate_per_min': topic_rate,
                'average_sentiment_change': curr_agg['average_sentiment'] - prev_agg['average_sentiment'],
            }

    deltas = {
        'article_count_delta': current['arcticle_count'] - previous['arcticle_count'],
        'aggregated_deltas': {},
    }

    return { 
        'status': 'ok',
        'time_diff_minutes': time_diff,
        'overall':{
            'article_count_change': overall_change,
            'article_count_rate_per_min': overall_rate,
            'current_article_count': current['arcticle_count'],
            'previous_article_count': previous['arcticle_count'],
        },
        'topics': topic_deltas,
        'snapshosts_available': len(history),


    }
         
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                return cache if cache else {}
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def is_cache_valid(cache_entry):
    if not cache_entry or 'timestamp' not in cache_entry:
        return False
    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
    return datetime.now(UTC) - cache_time < timedelta(seconds=CACHE_TTL)

def request(input):
    topics = input.split(',')
    topics = [topic.strip().lower() for topic in input.split(',')]
    boolstr = ' OR '.join(topics)
    cache_key = boolstr.lower()
    cache = load_cache()

    
    if  cache_key in cache and is_cache_valid(cache[cache_key]):
        print("Using cached data")
        return cache[cache_key]['data']
    else:
        req = newsapi.get_everything(q=boolstr, language='en', sort_by='relevancy')
    articles = req["articles"]
    articles = analyze_sentiment_batch(articles)
    aggregated_data = aggregate_by_topics(articles, topics)
    result = {
        'articles': articles,
        'aggregated': aggregated_data,
    }
    cache = save_to_history(cache, cache_key, articles, aggregated_data)
    save_cache(cache)
    
    return result


if __name__ == "__main__":
    topics_input = input("Enter topics separated by commas: ")
    articles = request(topics_input)
    print(json.dumps(articles, indent=2))
    
    cache = load_cache()
    if not cache: 
        cache = {}
    cache_key = ' OR '.join([t.strip().lower() for t in topics_input.split(',')]).lower()
    deltas = calculate_deltas(cache, cache_key)
    
    if deltas:
        print("\n=== DELTAS (Changes from last run) ===")
        print(json.dumps(deltas, indent=2))
    else:
        print("\n(No previous data to compare)")