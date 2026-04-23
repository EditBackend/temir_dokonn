import requests
from django.utils import timezone
from django.db.models import Sum
from .models import Sale, Payment

BOT_TOKEN = "8289664382:AAEopZRtaLDyQlHphfNozu-c25koBd9SMwI"
CHAT_ID = "8235903420"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    requests.post(url, data=data)




def update_customer_score(customer):
    sales = Sale.objects.filter(customer=customer, payment_type='Nasiya')
    score = 10
    for sale in sales:
        if sale.due_date:
            if timezone.now() > sale.due_date:
                paid = sum(p.amount for p in sale.payments.all())
                if paid < sale.total_price:
                    score -= 1

    if score < 0:
        score = 0

    customer.score = score
    customer.save()


def calculate_credit_limit(customer):
    payments = Payment.objects.filter(customer=customer)

    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0

    limit = total_paid * 5

    if customer.score <= 3:
        limit = limit * 0.3
    elif customer.score <= 5:
        limit = limit * 0.5

    return limit