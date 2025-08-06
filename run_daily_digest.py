import feedparser
import openai
import os
import time
import psutil
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime, timedelta
from more_itertools import chunked

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KEYWORDS = [
    "africa", "fintech", "china", "international payments", "MENA", "AI",
    "B2B payments", "payments", "venture capital", "vc", "startup",
    "stablecoin", "blockchain", "cross-border",
]

NEWS_SOURCES = [
    "https://techcrunch.com/tag/africa/feed/",
    "https://techcrunch.com/feed/",
    "https://news.google.com/rss/search?q=site:bloomberg.com+africa",
    "https://feeds.reuters.com/Reuters/africaNews",
    "https://restofworld.org/feed",
    "https://techcabal.com/feed/",
    "https://disrupt-africa.com/feed/",
    "https://www.cnbcafrica.com/feed/",
]

openai.api_key = OPENAI_API_KEY

client = WebClient(token=SLACK_TOKEN)

BATCH_SIZE = 3  # Reduced for memory efficiency


def fetch_articles():
    all_entries = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=15)

    for url in NEWS_SOURCES:
        print(f"\n[INFO] Fetching: {url}")
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"[WARNING] Failed to parse feed: {url} — Reason: {feed.bozo_exception}")
            continue

        print(f"[INFO] Entries found in feed: {len(feed.entries)}")

        for entry in feed.entries:
            try:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if not published:
                    continue

                published_dt = datetime.fromtimestamp(time.mktime(published))
                if published_dt < cutoff:
                    continue

                summary = entry.get("summary") or entry.get("description") or ""
                title = entry.get("title", "")

                if any(k in title.lower() or k in summary.lower() for k in KEYWORDS):
                    all_entries.append({
                        "title": title,
                        "link": entry.link,
                        "published": published_dt.strftime("%Y-%m-%d"),
                        "summary": summary,
                        "source": url
                    })

            except Exception as e:
                print(f"[ERROR] Parsing entry from {url} — {e}")

    print(f"\n🔍 Total relevant articles found: {len(all_entries)}")
    return all_entries



def log_memory(label):
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"[MEMORY] {label}: {mem_mb:.2f} MB")


def summarize_articles(articles):
    log_memory("Start of summarize_articles")
    summarized_articles = []
    for i, article in enumerate(articles):
        log_memory(f"Before Article {i+1}")
        try:
            prompt = f"Summarize this article in 2 short bullet points.\n\nTitle: {article['title']}\n\nSummary: {article['summary']}"
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tech news assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            summary_text = response.choices[0].message.content.strip()
            summarized_articles.append({
                "title": article['title'],
                "link": article['link'],
                "summary": summary_text
            })
        except Exception as e:
            print(f"[ERROR] Article {i+1} failed: {e}")
            summarized_articles.append({
                "title": article['title'],
                "link": article['link'],
                "summary": "⚠️ Failed to summarize this article."
            })
        log_memory(f"After Article {i+1}")
    return summarized_articles

def send_to_slack(summarized_articles):
    text_lines = [
        "*Africa Tech & VC Digest — Past 5 Days*",
        f"_Scanned {len(summarized_articles)} relevant articles_\n"
    ]

    for article in summarized_articles:
        text_lines.append(f"*<{article['link']}|{article['title']}>*")
        text_lines.append(f"{article['summary']}\n")

    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text="\n".join(text_lines)
        )
    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")



def main():
    articles = fetch_articles()
    if not articles:
        send_to_slack(["No relevant articles found in the past 5 days."])
        return
    summaries = summarize_articles(articles)
    send_to_slack(summaries)


if __name__ == "__main__":
    main()
