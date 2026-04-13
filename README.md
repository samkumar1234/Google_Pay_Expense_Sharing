# Expense Sharing App

A Python program to track shared expenses among friends, calculate who owes whom, and suggest payments to settle all debts.

## Dependencies

```
pip install numpy prettytable
```

sqlite3, json, and datetime are built into Python. No extra install needed.

## How to Run

```
python expense_sharing.py
```

## Features

- Add and remove friends
- Add expenses with descriptions
- Equal split and custom split support
- Transaction history for all users and per user
- Calculates final settlement balances
- Suggests minimum transactions to clear all debts
- SQLite database for data persistence

## Usage

```python
add_friend("Alice")

add_expense("Alice", ["Alice", "Bob", "Carol"], 1200, "Hotel stay")

add_expense("Bob", ["Alice", "Bob"], 500, "Fuel",
            split_type="custom",
            custom_amounts={"Alice": 200, "Bob": 300})

show_history()
show_user_history("Bob")
display_settlements()
suggest_payments()
```

## Database

A file called expenses.db is automatically created on first run. It stores all friends and expense records across sessions.

## Project Structure

```
expense_sharing.py   - main application
expenses.db          - auto-generated database
README.md            - this file
```
