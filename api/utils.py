import requests

BOT_TOKEN = "8289664382:AAEopZRtaLDyQlHphfNozu-c25koBd9SMwI"
CHAT_ID = "8235903420"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    requests.post(url, data=data)