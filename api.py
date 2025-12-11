from flask import Blueprint, request, jsonify
from datetime import date
from db import get_db

api_bp = Blueprint("api", __name__, url_prefix="/api")

def get_user_id_by_username(username: str):
    if not username:
        return None
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return row["id"] if row else None




@api_bp.route("/api/categories")
def api_categories():
    username = request.args.get("username")
    user_id = get_user_id_by_username(username)

    if not user_id:
        return jsonify({"error": "Usuario inválido"}), 400

    db = get_db()
    rows = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    categories = [
        {"id": r["id"], "name": r["name"]}
        for r in rows
    ]

    return jsonify({"categories": categories})



@api_bp.route("/summary")
def api_summary():
    username = request.args.get("username")
    user_id = get_user_id_by_username(username)

    if not user_id:
        return jsonify({"error": "Usuario inválido"}), 400

    db = get_db()

    rows = db.execute(
        """
        SELECT t.id,
               t.amount,
               t.type,
               t.description,
               t.date,
               c.name AS category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC, t.id DESC
        LIMIT 100
        """,
        (user_id,),
    ).fetchall()

    income = sum(r["amount"] for r in rows if r["type"] == "income")
    expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    balance = income - expense

    transactions = [
        {
            "id": r["id"],
            "amount": r["amount"],
            "type": r["type"],
            "description": r["description"],
            "category": r["category"],
            "date": r["date"],
        }
        for r in rows
    ]

    return jsonify(
        {
            "username": username,
            "total_income": income,
            "total_expense": expense,
            "balance": balance,
            "transactions": transactions,
        }
    )


@api_bp.route("/analytics")
def api_analytics():
    username = request.args.get("username")
    range_ = request.args.get("range", "month")  # month | year | all

    user_id = get_user_id_by_username(username)
    if not user_id:
        return jsonify({"error": "Usuario inválido"}), 400

    today = date.today()

    if range_ == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif range_ == "year":
        start_date = date(today.year, 1, 1)
        end_date = today
    else: 
        start_date = date(1970, 1, 1)
        end_date = date(2100, 12, 31)

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    db = get_db()

    # totales generales
    income_row = db.execute(
        """
        SELECT SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
          AND type = 'income'
          AND date BETWEEN ? AND ?
        """,
        (user_id, start_str, end_str),
    ).fetchone()

    expense_row = db.execute(
        """
        SELECT SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
          AND type = 'expense'
          AND date BETWEEN ? AND ?
        """,
        (user_id, start_str, end_str),
    ).fetchone()

    income_total = income_row["total"] or 0
    expense_total = expense_row["total"] or 0
    balance = income_total - expense_total

    # egresos por categoría
    expense_cat_rows = db.execute(
        """
        SELECT c.name AS category, SUM(t.amount) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
          AND t.type = 'expense'
          AND t.date BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, start_str, end_str),
    ).fetchall()

    expenses_by_category = [
        {"category": r["category"], "total": r["total"] or 0}
        for r in expense_cat_rows
    ]

    # ingresos por categoría
    income_cat_rows = db.execute(
        """
        SELECT c.name AS category, SUM(t.amount) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
          AND t.type = 'income'
          AND t.date BETWEEN ? AND ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, start_str, end_str),
    ).fetchall()

    incomes_by_category = [
        {"category": r["category"], "total": r["total"] or 0}
        for r in income_cat_rows
    ]

    return jsonify(
        {
            "range": range_,
            "start_date": start_str,
            "end_date": end_str,
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": balance,
            "expenses_by_category": expenses_by_category,
            "incomes_by_category": incomes_by_category,
        }
    )
@api_bp.route("/api/transactions", methods=["POST"])
def api_create_transaction():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    amount = data.get("amount")
    type_ = data.get("type")
    description = data.get("description") or ""
    category_name = (data.get("category") or "").strip()
    date_str = data.get("date") or date.today().isoformat()

    user_id = get_user_id_by_username(username)
    if not user_id:
        return jsonify({"error": "Usuario inválido"}), 400

    # validaciones básicas
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Monto inválido"}), 400

    if type_ not in ("income", "expense"):
        return jsonify({"error": "Tipo inválido"}), 400

    if not category_name:
        return jsonify({"error": "Categoría requerida"}), 400

    db = get_db()

    # buscar o crear categoría
    cat = db.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ?",
        (user_id, category_name),
    ).fetchone()

    if cat:
        category_id = cat["id"]
    else:
        db.execute(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            (user_id, category_name),
        )
        db.commit()
        category_id = db.execute(
            "SELECT id FROM categories WHERE user_id = ? AND name = ?",
            (user_id, category_name),
        ).fetchone()["id"]

    db.execute(
        """
        INSERT INTO transactions (user_id, category_id, amount, type, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, category_id, amount, type_, description, date_str),
    )
    db.commit()

    return jsonify({"status": "ok"}), 201


