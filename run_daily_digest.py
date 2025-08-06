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

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KEYWORDS = [
    "africa", "fintech", "remittance", "payments", "venture capital", "vc", "startup",
    "flutterwave", "chipper", "mfs africa", "yellow card", "mtn", "airtel", "crypto",
    "stablecoin", "blockchain", "cross-border", "central bank", "regulation", "african tech"
]

NEWS_SOURCES = [
    "https://techcrunch.com/tag/africa/feed/",
    "https://techcabal.com/feed/",
    "https://disrupt-africa.com/feed/",
    "https://www.balancingact-africa.com/news/feed",
    "https://africa.techdigest.ng/feed/",
    "https://www.cnbcafrica.com/feed/",
    "https://rss.app/feeds/xRssLYcsP9MyFC2C.xml",  # Google News - Fintech Africa
    "https://rss.app/feeds/kqQx6ydQ7vrcztCg.xml",  # Google News - African Remittance
    "https://rss.app/feeds/4R5ErfnYTbFy4sHi.xml",  # Google News - VC Africa
]

openai.api_key = OPENAI_API_KEY

client = WebClient(token=SLACK_TOKEN)

BATCH_SIZE = 3  # Reduced for memory efficiency


def fetch_articles():
    all_entries = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=5)

    for url in NEWS_SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if not published:
                    continue
                published_dt = datetime.fromtimestamp(time.mktime(published))
                if published_dt < cutoff:
                    continue

                summary = entry.get("summary") or entry.get("description") or ""
                if any(k in entry.title.lower() or k in summary.lower() for k in KEYWORDS):
                    all_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": published_dt.strftime("%Y-%m-%d"),
                        "summary": summary,
                    })
            except Exception as e:
                print(f"Error parsing entry: {e}")

    print(f"\U0001F50D Found {len(all_entries)} relevant articles.")
    return all_entries


def log_memory(label):
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"[MEMORY] {label}: {mem_mb:.2f} MB")


def summarize_articles(articles):
    log_memory("Start of summarize_articles")
    summaries = []
    for i, batch in enumerate(chunked(articles, BATCH_SIZE)):
        log_memory(f"Before Batch {i+1}")
        try:
            content = "\n\n".join(f"{item['title']}\n{item['summary']}" for item in batch)
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tech news assistant."},
                    {"role": "user", "content": f"Summarize the following tech news articles in 5 bullet points.\n\n{content}"},
                ]
            )
            summary_text = response.choices[0].message.content
            summaries.append(summary_text)
        except Exception as e:
            print(f"[ERROR] Batch {i+1} failed: {e}")
            summaries.append(f"⚠️ Skipped one batch due to error.")
        log_memory(f"After Batch {i+1}")

    if not summaries:
        summaries.append("⚠️ Digest failed due to memory or processing issues.")

    return summaries


def send_to_slack(summaries):
    text = "*Africa Tech & VC Digest — Past 5 Days*\n\n" + "\n\n".join(summaries)
    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=text
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
