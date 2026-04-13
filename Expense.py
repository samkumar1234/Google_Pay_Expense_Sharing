import numpy as np
import sqlite3
import json
from datetime import datetime
from prettytable import PrettyTable

def init_db(db_name="expenses.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            payer         TEXT NOT NULL,
            beneficiaries TEXT NOT NULL,   -- JSON list
            amounts       TEXT NOT NULL,   -- JSON dict {name: share}
            total_amount  REAL NOT NULL,
            description   TEXT,
            split_type    TEXT NOT NULL,   -- 'equal' or 'custom'
            timestamp     TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_friends(db_name="expenses.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM friends ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_friend(name, db_name="expenses.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO friends (name) VALUES (?)", (name,))
        conn.commit()
        print(f"'{name}' added to the group.")
    except sqlite3.IntegrityError:
        print(f"'{name}' already exists.")
    conn.close()


def remove_friend(name, db_name="expenses.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM friends WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    print(f"'{name}' removed from the group.")
  

def add_expense(payer, beneficiaries, total_amount,
                description="", split_type="equal",
                custom_amounts=None, db_name="expenses.db"):
    friends = get_friends(db_name)

    if payer not in friends:
        print(f"Payer '{payer}' not in group.")
        return
    for b in beneficiaries:
        if b not in friends:
            print(f"Beneficiary '{b}' not in group.")
            return

    if split_type == "equal":
        share = round(total_amount / len(beneficiaries), 2)
        amounts = {b: share for b in beneficiaries}

    elif split_type == "custom":
        if custom_amounts is None:
            print("Provide custom_amounts dict for custom split.")
            return
        if round(sum(custom_amounts.values()), 2) != round(total_amount, 2):
            print(f"Custom amounts {sum(custom_amounts.values())} "
                  f"don't add up to total {total_amount}.")
            return
        amounts = custom_amounts

    else:
        print("split_type must be 'equal' or 'custom'.")
        return
      
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses
            (payer, beneficiaries, amounts, total_amount,
             description, split_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        payer,
        json.dumps(beneficiaries),
        json.dumps(amounts),
        total_amount,
        description,
        split_type,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    print(f"Expense recorded: '{description}' | ₹{total_amount} paid by {payer}")

def build_expense_matrix(db_name="expenses.db"):
    """Build the NumPy expense matrix from DB records."""
    friends = get_friends(db_name)
    n = len(friends)
    matrix = np.zeros((n, n))

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT payer, amounts FROM expenses")
    rows = cursor.fetchall()
    conn.close()

    for payer, amounts_json in rows:
        amounts = json.loads(amounts_json)
        payer_idx = friends.index(payer)
        for beneficiary, share in amounts.items():
            if beneficiary in friends:
                ben_idx = friends.index(beneficiary)
                matrix[payer_idx][ben_idx] += share

    return matrix, friends


def calculate_settlements(db_name="expenses.db"):
    matrix, friends = build_expense_matrix(db_name)
    total_paid = np.sum(matrix, axis=1)   # Row sum: what you paid out
    total_owed = np.sum(matrix, axis=0)   # Col sum: what others paid for you
    net_balance = total_paid - total_owed  # Positive = should receive
    return net_balance, friends


def display_settlements(db_name="expenses.db"):
    net_balance, friends = calculate_settlements(db_name)

    table = PrettyTable()
    table.field_names = ["Friend", "Settlement"]

    for i, friend in enumerate(friends):
        if net_balance[i] > 0.01:
            table.add_row([friend, f"Should Receive ₹{net_balance[i]:.2f}"])
        elif net_balance[i] < -0.01:
            table.add_row([friend, f"Owes ₹{-net_balance[i]:.2f}"])
        else:
            table.add_row([friend, "Is Settled"])

    print("\nFinal Settlements:")
    print(table)


def suggest_payments(db_name="expenses.db"):
    net_balance, friends = calculate_settlements(db_name)

    creditors = sorted(
        [(friends[i], round(amt, 2)) for i, amt in enumerate(net_balance) if amt > 0.01],
        key=lambda x: -x[1]
    )
    debtors = sorted(
        [(friends[i], round(-amt, 2)) for i, amt in enumerate(net_balance) if amt < -0.01],
        key=lambda x: -x[1]
    )

    transactions = []

    while debtors and creditors:
        debtor,   debt_amount   = debtors.pop(0)
        creditor, credit_amount = creditors.pop(0)

        payment = round(min(debt_amount, credit_amount), 2)
        transactions.append((debtor, creditor, payment))

        debt_amount   = round(debt_amount   - payment, 2)
        credit_amount = round(credit_amount - payment, 2)

        if debt_amount > 0.01:
            debtors.insert(0, (debtor, debt_amount))
        if credit_amount > 0.01:
            creditors.insert(0, (creditor, credit_amount))

    print("\nSuggested Transactions:")
    if transactions:
        for debtor, creditor, amount in transactions:
            print(f"   {debtor} should pay ₹{amount:.2f} to {creditor}")
    else:
        print("   No transactions needed. Everyone is settled!")

    return transactions

def show_history(db_name="expenses.db"):
    """Show full expense history."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, payer, beneficiaries, amounts,
               total_amount, description, split_type, timestamp
        FROM expenses ORDER BY timestamp
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No expenses recorded yet.")
        return

    table = PrettyTable()
    table.field_names = ["#", "Payer", "Amount", "Description", "Split", "Date"]
    table.max_width = 30

    for row in rows:
        eid, payer, _, _, total, desc, split_type, ts = row
        table.add_row([eid, payer, f"₹{total:.2f}",
                       desc or "-", split_type, ts[:10]])

    print("\n📋 Expense History:")
    print(table)


def show_user_history(name, db_name="expenses.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT payer, beneficiaries, amounts, total_amount,
               description, split_type, timestamp
        FROM expenses ORDER BY timestamp
    """)
    rows = cursor.fetchall()
    conn.close()

    print(f"\n📋 History for {name}:")
    table = PrettyTable()
    table.field_names = ["Role", "With", "Your Share", "Description", "Date"]

    found = False
    for payer, bens_json, amounts_json, total, desc, split_type, ts in rows:
        bens    = json.loads(bens_json)
        amounts = json.loads(amounts_json)

        if payer == name:
            others = [b for b in bens if b != name]
            table.add_row([
                "Paid",
                ", ".join(others) or "-",
                f"₹{total:.2f} (total)",
                desc or "-",
                ts[:10]
            ])
            found = True

        elif name in bens:
            share = amounts.get(name, 0)
            table.add_row([
                f"Owes → {payer}",
                payer,
                f"₹{share:.2f}",
                desc or "-",
                ts[:10]
            ])
            found = True

    if found:
        print(table)
    else:
        print(f"  No transactions found for '{name}'.")
      
if __name__ == "__main__":
    DB = "expenses.db"
    init_db(DB)
    print("=" * 50)
    print("  GooglePay Expense Sharing App")
    print("=" * 50)

    for name in ["Alice", "Bob", "Carol", "David"]:
        add_friend(name, DB)

    add_expense("Alice", ["Alice", "Bob", "Carol"],
                1250, "Hotel accommodation", db_name=DB)

    add_expense("Bob",   ["Bob", "Carol"],
                800,  "Dinner at restaurant", db_name=DB)

    add_expense("Carol", ["Alice", "Bob", "Carol", "David"],
                1785, "Sightseeing bus tickets", db_name=DB)

    add_expense(
        payer="David",
        beneficiaries=["Alice", "Bob", "Carol", "David"],
        total_amount=1000,
        description="Groceries (custom split)",
        split_type="custom",
        custom_amounts={"Alice": 400, "Bob": 200, "Carol": 200, "David": 200},
        db_name=DB
    )

    show_history(DB)
    show_user_history("Bob", DB)
    display_settlements(DB)
    suggest_payments(DB)
