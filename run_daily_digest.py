import os
import gc
import psutil
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from more_itertools import batched
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
KEYWORDS = ["fintech", "payments", "remittance", "startup", "africa"]
BATCH_SIZE = 3

FEED_URLS = [
    # Pan-African & Regional
    "https://techcabal.com/feed/",
    "https://disrupt-africa.com/feed/",
    "https://weetracker.com/feed/",
    "https://technext24.com/feed/",
    "https://techmoran.com/feed/",
    "https://techpoint.africa/feed/",

    # Finance, VC & Remittance
    "https://www.pymnts.com/feed/",
    "https://www.finextra.com/rss.xml",
    "https://techinafrica.com/feed/",

    # Global w/ filters
    "https://techcrunch.com/feed/",
    "https://finance.yahoo.com/news/rssindex",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

def log_memory(context=""):
    process = psutil.Process()
    mem = process.memory_info().rss / (1024 * 1024)
    print(f"[MEMORY] {context}: {mem:.2f} MB")

def fetch_articles():
    all_articles = []
    for url in FEED_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                if any(k in entry.title.lower() or k in entry.summary.lower() for k in KEYWORDS):
                    all_articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary if hasattr(entry, 'summary') else ""
                    })
            except Exception as e:
                print(f"Error parsing entry: {e}")
    print(f"\U0001F50D Found {len(all_articles)} relevant articles.")
    return all_articles[:15]  # temporary limit for testing

def summarize_articles(articles):
    summaries = []
    success = False

    log_memory("Start of summarize_articles")

    for idx, batch in enumerate(batched(articles, BATCH_SIZE), 1):
        batch_summaries = []

        log_memory(f"Before Batch {idx}")

        for article in batch:
            prompt = f"Summarize the following article in 2 bullet points:\n\nTitle: {article['title']}\n\nSummary: {article['summary']}"
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a summarizer for African fintech news."},
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = response.choices[0].message.content.strip()
                success = True
            except Exception as e:
                print(f"[ERROR] GPT-4 failed on Batch {idx}: {e}\nTrying GPT-3.5 fallback...")
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You're a summarizer for African fintech news."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    summary = response.choices[0].message.content.strip()
                    success = True
                except Exception as fallback_error:
                    print(f"[FATAL] GPT-3.5 fallback also failed: {fallback_error}")
                    summary = f"❌ Failed to summarize:\n{article['title']}"

            batch_summaries.append(f"*{article['title']}*\n{summary}\n🔗 {article['link']}\n")

        summaries.extend(batch_summaries)
        del batch_summaries
        gc.collect()
        log_memory(f"After Batch {idx}")

    if not success:
        summaries.append("❌ All AI summarization attempts failed. Please check your OpenAI quota or API status.")

    log_memory("End of summarize_articles")
    return summaries

def post_to_slack(message):
    try:
        slack_client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=message)
    except SlackApiError as e:
        print(f"[SLACK ERROR] {e.response['error']}")

def main():
    articles = fetch_articles()
    summaries = summarize_articles(articles)
    message = "\n\n".join(summaries)
    post_to_slack(message)

if __name__ == "__main__":
    main()
