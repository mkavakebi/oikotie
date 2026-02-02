import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    """Sends a message to the configured Telegram channel."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def format_summary(analytics_data):
    """Formats the analytics data into a readable Telegram message."""
    total = analytics_data.get('total_listings', 0)
    drops = analytics_data.get('listings_with_price_drops', 0)
    changes = analytics_data.get('total_price_changes', 0)
    avg_drop = analytics_data.get('average_price_drop', '0 €')
    
    msg = [
        "<b>🏠 Oikotie Daily Refresh Summary</b>",
        f"📅 Date: {os.popen('date +%Y-%m-%d').read().strip()}",
        "",
        f"📊 <b>Stats:</b>",
        f"• Total Listings: {total}",
        f"• Price Drops Today: {drops}",
        f"• Total Price Changes: {changes}",
        f"• Average Drop: {avg_drop}",
        ""
    ]
    
    biggest_drops = analytics_data.get('biggest_drops', [])
    if biggest_drops:
        msg.append("📉 <b>Top Price Drops:</b>")
        for drop in biggest_drops[:3]:
            addr = drop.get('address', 'Unknown')
            diff = drop.get('difference', 'N/A')
            diff_pct = drop.get('difference_pct', 'N/A')
            url = drop.get('url', '#')
            msg.append(f"• <a href='{url}'>{addr}</a>: <b>-{diff}</b> ({diff_pct})")
    
    msg.append("")
    msg.append("🔗 <a href='http://localhost:5000'>View Dashboard</a>")
    
    return "\n".join(msg)

if __name__ == "__main__":
    # Test or run from CLI
    analytics_path = 'data/price_analytics.json'
    if os.path.exists(analytics_path):
        with open(analytics_path, 'r') as f:
            data = json.load(f)
        summary = format_summary(data)
        if send_telegram_message(summary):
            print("Telegram summary sent successfully!")
        else:
            print("Failed to send Telegram summary.")
    else:
        print(f"Analytics file not found at {analytics_path}")
