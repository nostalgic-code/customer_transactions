from flask import Flask, jsonify
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

app = Flask(__name__)

# Your credentials & base URL
USERNAME = "d5900938-be95-4412-95b3-50b11983e13e"
PASSWORD = "90fa0de5-250a-4e99-bd65-85b1854d9c82"
BASE_URL = "http://102.33.60.228:9183/getResources/customer_transactions?max=100"

# --- Fetch from external API ---
def fetch_transactions():
    try:
        response = requests.get(BASE_URL, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response.raise_for_status()
        data = response.json()
        print("🔄 RAW RESPONSE:", data)  # DEBUG
        return data.get('customer_transactions', [])
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return []

# --- Parse transaction date safely ---
def parse_date(date_str):
    for fmt in ("%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    print(f"⚠️ Unrecognized date format: {date_str}")
    return None

# --- Aggregate spend per customer per year ---
def aggregate_spend_by_year(transactions):
    spend = {}
    for tx in transactions:
        if tx.get('transaction_type') != 'INV':
            continue

        amount_str = tx.get('amount', '').strip()
        if not amount_str:
            continue

        try:
            amount = float(amount_str)
        except:
            continue

        date_str = tx.get('transaction_date')
        dt = parse_date(date_str)
        if dt is None:
            continue

        year = dt.year
        customer = tx.get('customer_account_number')
        if not customer:
            continue

        spend.setdefault(customer, {}).setdefault(year, 0)
        spend[customer][year] += amount

    print("📊 AGGREGATED SPEND:", spend)  # DEBUG
    return spend

# --- Endpoint for top customer comparison ---
@app.route('/top_customers_comparison', methods=['GET'])
def top_customers_comparison():
    transactions = fetch_transactions()
    spend = aggregate_spend_by_year(transactions)

    current_year = datetime.now().year
    last_year = current_year - 1

    # Build top 10 customers list
    customers_current_year = [
        (customer, yearly.get(current_year, 0))
        for customer, yearly in spend.items()
        if yearly.get(current_year, 0) > 0
    ]
    customers_current_year.sort(key=lambda x: x[1], reverse=True)
    top_10 = customers_current_year[:10]

    # Final response formatting
    result = []
    for customer, current_amt in top_10:
        last_amt = spend.get(customer, {}).get(last_year, 0)
        diff = current_amt - last_amt
        pct_change = ((diff / last_amt) * 100) if last_amt != 0 else None

        result.append({
            'customer_account_number': customer,
            'this_year_spend': round(current_amt, 2),
            'last_year_spend': round(last_amt, 2),
            'difference': round(diff, 2),
            'percentage_change': round(pct_change, 2) if pct_change is not None else None,
        })

    print("✅ FINAL TOP 10:", result)  # DEBUG

    return jsonify({
        'count': len(result),
        'raw_top_10': result
    })

if __name__ == '__main__':
    app.run(debug=True)
