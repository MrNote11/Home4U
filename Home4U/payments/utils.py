import requests
import os
from django.conf import settings

FLW_SECRET_KEY = settings.FLW_SECRET_KEY

def get_bank_code(country, account_bank):
    """Fetch bank details from Flutterwave"""
    url = f"https://api.flutterwave.com/v3/banks/{country}"
    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch bank list: {response.text}")

    banks = response.json().get("data", [])
    selected_bank = next((bank for bank in banks if bank['code'] == account_bank), None)
    if not selected_bank:
        raise Exception(f"Bank not found for code: {account_bank}")

    return selected_bank

def resolve_account(account_number, account_bank):
    """Resolve bank account details"""
    url = "https://api.flutterwave.com/v3/accounts/resolve"
    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "account_number": account_number,
        "account_bank": account_bank
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Failed to resolve account: {response.text}")

    return response.json().get("data")