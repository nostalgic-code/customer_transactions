from flask import Flask, jsonify
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

app = Flask(__name__)

# Your credentials & base URL
USERNAME = "d5900938-be95-4412-95b3-50b11983e13e"
PASSWORD = "90fa0de5-250a-4e99-bd65-85b1854d9c82"
BASE_URL = "http://102.33.60.228:9183/getResources/customer_transactions?max=100"

def fetch_transactions():
    try:
        response = requests.get(BASE_URL, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response.raise_for_status()
        data = response.json()
        return data.get('customer_transactions', [])
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%m-%d-%Y")
    except:
        return None

def aggregate_spend_by_year(transactions):
    spend = {}
    for tx in transactions:
        amount_str = tx.get('amount', '0').strip()
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
        if customer is None:
            continue

        # Only consider invoice transactions (INV)
        if tx.get('transaction_type') != 'INV':
            continue

        if customer not in spend:
            spend[customer] = {}

        if year not in spend[customer]:
            spend[customer][year] = 0

        spend[customer][year] += amount

    return spend

@app.route('/top_customers_comparison', methods=['GET'])
def top_customers_comparison():
    transactions = fetch_transactions()
    spend = aggregate_spend_by_year(transactions)

    current_year = datetime.now().year
    last_year = current_year - 1

    customers_current_year = []
    for customer, yearly_data in spend.items():
        amt = yearly_data.get(current_year, 0)
        if amt > 0:
            customers_current_year.append((customer, amt))

    customers_current_year.sort(key=lambda x: x[1], reverse=True)
    top_10 = customers_current_year[:10]

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

    return jsonify({'top_customers_comparison': result})

if __name__ == '__main__':
    app.run(debug=True)
