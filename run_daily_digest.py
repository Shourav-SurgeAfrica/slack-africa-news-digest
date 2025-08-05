import os
import feedparser
from slack_sdk import WebClient
from datetime import datetime
import openai

# Load environment variables
slack_token = os.environ.get("SLACK_BOT_TOKEN")
channel = os.environ.get("SLACK_CHANNEL")
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI client (latest SDK)
client = openai.OpenAI(api_key=openai_api_key)

# RSS feeds to monitor
RSS_FEEDS = [
    "https://techcabal.com/feed/",
    "https://qz.com/africa/feed",
    "https://disrupt-africa.com/feed/",
    "https://weetracker.com/feed/",
    "https://www.theafricareport.com/feed/"
]

# Keywords to filter relevant stories
KEYWORDS = [
    "fintech", "payments", "investment", "vc", "remittance",
    "startups", "wallet", "funding", "cross-border", "digital money"
]

def fetch_articles():
    entries = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if any(k in entry.title.lower() or k in entry.summary.lower() for k in KEYWORDS):
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.summary
                })
    return entries

def summarize_articles(articles):
    summaries = []
    for article in articles[:5]:  # Limit to top 5
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
        except Exception as e:
            summary = f"❌ Failed to summarize:\n{e}"
        summaries.append(f"*{article['title']}*\n{summary}\n🔗 {article['link']}\n")
    return summaries

def post_to_slack(digest):
    client = WebClient(token=slack_token)
    date = datetime.utcnow().strftime('%A, %d %B %Y')
    header = f":newspaper: *Your Africa Fintech Digest – {date}*\n"
    message = header + "\n\n".join(digest)
    client.chat_postMessage(channel=channel, text=message)

def main():
    articles = fetch_articles()
    summaries = summarize_articles(articles)
    post_to_slack(summaries)

if __name__ == "__main__":
    main()
