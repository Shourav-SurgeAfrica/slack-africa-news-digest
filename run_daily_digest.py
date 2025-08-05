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
    # 🌍 Pan-African & Regional Tech/Fintech News
    "https://techcabal.com/feed/",                          # ✔ TechCabal
    "https://disrupt-africa.com/feed/",                     # Disrupt Africa
    "https://weetracker.com/feed/",                         # WeeTracker
    "https://www.technext.ng/feed/",                        # TechNext Nigeria
    "https://www.benjamindada.com/rss/",                    # Benjamin Dada (converted via Kill the Newsletter)
    "https://techmoran.com/feed/",                          # Tech Moran (Kenya)
    "https://techpoint.africa/feed/",                       # TechPoint Africa

    # 💸 Finance, VC & Remittance-Focused
    "https://www.theafricareport.com/feed/",                # The Africa Report
    "https://africa.businessinsider.com/rss",               # Business Insider Africa
    "https://www.pymnts.com/feed/",                         # PYMNTS (Global, use filters)
    "https://www.finextra.com/rss/news.aspx",              # Finextra
    "https://techinafrica.com/feed/",                       # Tech in Africa
    "https://qz.com/africa/feed",                           # Quartz Africa

    # 🧠 Analytical / Long-form / Reports
    "https://fincra.com/blog/feed/",                        # Fincra Blog
    "https://mfsafrica.com/blog/rss.xml",                  # MFS Africa Blog
    "https://blog.chipper.cash/feed/",                      # Chipper Cash Blog

    # 📣 Global Media (use with filters in code)
    "https://techcrunch.com/feed/",                         # TechCrunch (Filter for Africa)
    "https://www.theverge.com/rss/index.xml",              # The Verge (Use only when mapping trends)
    "https://www.wired.com/feed/rss",                       # Wired (Use with caution)
    "https://finance.yahoo.com/news/rssindex",             # Yahoo Finance
    "https://www.coindesk.com/arc/outboundfeeds/rss/",     # CoinDesk (filter for African crypto)
]

# Keywords to filter relevant stories
KEYWORDS = [
   "fintech", "payments", "remittance", "wallet", "mobile money", "digital money","internatonal payments", "international supplier payments",
    "money transfer", "cross-border", "p2p", "fx", "foreign exchange", "forex",
    "funding", "seed", "series a", "series b", "venture capital", "vc", "angel investment", "raising capital",
    "startups", "scaleups", "founder", "entrepreneur", "pitch", "accelerator", "incubator",
    "blockchain", "crypto", "decentralized", "web3", "neobank", "banking as a service", "api",
    "financial inclusion", "regulation", "compliance", "aml", "kyc", "unbanked", "underserved",
    "mpesa", "flutterwave", "chipper", "opal", "yellow card", "paystack", "mtn", "airtel", "wave"
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
