import os
import feedparser
import time
from slack_sdk import WebClient
from datetime import datetime, timedelta
import openai
from more_itertools import chunked

# Load environment variables
slack_token = os.environ.get("SLACK_BOT_TOKEN")
channel = os.environ.get("SLACK_CHANNEL")
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI client (latest SDK)
client = openai.OpenAI(api_key=openai_api_key)

# RSS feeds
RSS_FEEDS = [
    # 🌍 Pan-African & Regional Tech/Fintech News
    "https://techcabal.com/feed/",
    "https://disrupt-africa.com/feed/",
    "https://weetracker.com/feed/",
    "https://www.technext.ng/feed/",
    "https://www.benjamindada.com/rss/",
    "https://techmoran.com/feed/",
    "https://techpoint.africa/feed/",
    # 💸 Finance, VC & Remittance-Focused
    "https://www.theafricareport.com/feed/",
    "https://africa.businessinsider.com/rss",
    "https://www.pymnts.com/feed/",
    "https://www.finextra.com/rss/news.aspx",
    "https://techinafrica.com/feed/",
    "https://qz.com/africa/feed",
    # 🧠 Analytical / Long-form / Reports
    "https://fincra.com/blog/feed/",
    "https://mfsafrica.com/blog/rss.xml",
    "https://blog.chipper.cash/feed/",
    # 📣 Global Media
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://finance.yahoo.com/news/rssindex",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

KEYWORDS = [
    "fintech", "payments", "remittance", "wallet", "mobile money", "digital money", "international payments",
    "international supplier payments", "money transfer", "cross-border", "p2p", "fx", "foreign exchange", "forex",
    "funding", "seed", "series a", "series b", "venture capital", "vc", "angel investment", "raising capital",
    "startups", "scaleups", "founder", "entrepreneur", "pitch", "accelerator", "incubator",
    "blockchain", "crypto", "decentralized", "web3", "neobank", "banking as a service", "api",
    "financial inclusion", "regulation", "compliance", "aml", "kyc", "unbanked", "underserved",
    "mpesa", "flutterwave", "chipper", "opal", "yellow card", "paystack", "mtn", "airtel", "wave"
]

def fetch_articles():
    entries = []
    cutoff_date = datetime.utcnow() - timedelta(days=5)

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            try:
                published_time = (
                    datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if hasattr(entry, "published_parsed")
                    else None
                )
            except Exception:
                published_time = None

            if not published_time or published_time < cutoff_date:
                continue

            content = entry.get("summary", entry.get("description", "")).lower()
            if any(k in entry.title.lower() or k in content for k in KEYWORDS):
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", entry.get("description", "")),
                    "published": published_time.strftime('%Y-%m-%d')
                })

    print(f"🔍 Found {len(entries)} relevant articles.")
    return entries[:30]  # Limit to 30 articles for now to avoid overload

import os
import psutil
from openai import OpenAIError

def summarize_articles(articles):
    summaries = []
    batch_size = 5
    batch_failures = 0

    def log_memory_usage(batch_num):
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024  # in MB
        print(f"📊 Batch {batch_num}: Current memory usage: {mem:.2f} MB")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        batch_num = i // batch_size + 1

        try:
            log_memory_usage(batch_num)

            user_content = "\n\n".join(
                [f"Title: {article['title']}\nContent: {article['summary']}" for article in batch]
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a summarizer bot for a Slack digest. "
                            "Summarize each article below in 2–3 bullet points. "
                            "Respond in Markdown with emojis where appropriate."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )

            summaries.append(response.choices[0].message.content)

        except OpenAIError as e:
            print(f"❌ OpenAI error on batch {batch_num}: {e}")
            summaries.append(f"⚠️ Failed to summarize batch {batch_num} due to OpenAI error.")
            batch_failures += 1

        except Exception as e:
            print(f"❌ General error on batch {batch_num}: {e}")
            summaries.append(f"⚠️ Unexpected error in batch {batch_num}.")
            batch_failures += 1

    # Fallback: All batches failed
    if batch_failures == len(articles) // batch_size + (1 if len(articles) % batch_size != 0 else 0):
        return [
            "⚠️ All summarization batches failed. Please check API key, memory limits, or article formatting."
        ]

    return summaries


def post_to_slack(digest):
    slack_client = WebClient(token=slack_token)
    date = datetime.utcnow().strftime('%A, %d %B %Y')
    header = f":newspaper: *Your Africa Fintech Digest – {date}*\n"
    message = header + "\n\n".join(digest)

    slack_client.chat_postMessage(channel=channel, text=message)

def main():
    articles = fetch_articles()

    if not articles:
        no_content_msg = f":newspaper: *Your Africa Fintech Digest – {datetime.utcnow().strftime('%A, %d %B %Y')}*\n\n_No relevant articles found in the past 5 days._"
        post_to_slack([no_content_msg])
        return

    summaries = summarize_articles(articles)
    post_to_slack(summaries)

if __name__ == "__main__":
    main()
