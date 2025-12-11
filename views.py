from flask import Blueprint, render_template, request, redirect, session,url_for
from datetime import datetime
from db import get_db

views_bp = Blueprint("views", __name__)



@views_bp.route("/")
def index():
    db = get_db()
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    from datetime import datetime
    today = datetime.today()
    year = int(request.args.get("year") or today.year)
    month = int(request.args.get("month") or today.month)

    rows = db.execute(
    """
    SELECT
        t.id,
        t.amount,
        t.type,
        t.description,
        t.date,
        c.name AS category
    FROM transactions t
    JOIN categories c
      ON t.category_id = c.id
    WHERE t.user_id = ?
      AND strftime('%Y', t.date) = ?
      AND strftime('%m', t.date) = ?
    ORDER BY t.date DESC, t.id DESC
    """,
    (user_id, f"{year:04d}", f"{month:02d}"),
).fetchall()


    total_income = sum(r["amount"] for r in rows if r["type"] == "income")
    total_expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    balance = total_income - total_expense

    return render_template(
        "index.html",
        rows=rows,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        year=year,
        month=month,
    )

@views_bp.route("/add", methods=["GET", "POST"])
def add():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        type_ = request.form.get("type")         
        amount_raw = request.form.get("amount")
        description = request.form.get("description") or ""
        date_str = request.form.get("date")
        category_id = request.form.get("category_id")

         
        if type_ not in ("income", "expense"):
            return "Tipo inválido", 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return "Monto inválido", 400

        if not date_str:
            return "Fecha requerida", 400

        if not category_id:
            return "Categoría requerida", 400

        
        cat = db.execute(
            "SELECT id FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id),
        ).fetchone()
        if not cat:
            return "Categoría inválida", 400

        db.execute(
            """
            INSERT INTO transactions (user_id, category_id, amount, type, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, category_id, amount, type_, description, date_str),
        )
        db.commit()

        return redirect("/")

    
    categories = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    if not categories:
       
        return redirect("/categories")

    return render_template("add.html", categories=categories)


@views_bp.route("/transactions/<int:tx_id>/delete", methods=["POST"])
def delete_transaction(tx_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    db = get_db()

    # me aseguro de que la transacción es del usuario logueado
    tx = db.execute(
        "SELECT id FROM transactions WHERE id = ? AND user_id = ?",
        (tx_id, user_id),
    ).fetchone()

    if not tx:
        return redirect(url_for("views.index"))

    db.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (tx_id, user_id),
    )
    db.commit()

    return redirect(url_for("views.index"))


@views_bp.route("/transactions/<int:tx_id>/edit", methods=["GET", "POST"])
def edit_transaction(tx_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    db = get_db()

    # traigo la transaccion, verifico que sea del usuario
    tx = db.execute(
        """
        SELECT id, user_id, category_id, amount, type, description, date
        FROM transactions
        WHERE id = ? AND user_id = ?
        """,
        (tx_id, user_id),
    ).fetchone()

    if not tx:
        # no existe o no es del user
        return redirect(url_for("views.index"))

    
    categories = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        type_ = request.form.get("type")
        amount_raw = request.form.get("amount")
        description = request.form.get("description") or ""
        date_str = request.form.get("date")
        category_id = request.form.get("category_id")

        if type_ not in ("income", "expense"):
            return "Tipo inválido", 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return "Monto inválido", 400

        if not date_str:
            return "Fecha requerida", 400

        if not category_id:
            return "Categoría requerida", 400

        # chequear que la categoría sea del usuario
        cat = db.execute(
            "SELECT id FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id),
        ).fetchone()
        if not cat:
            return "Categoría inválida", 400

        db.execute(
            """
            UPDATE transactions
            SET category_id = ?, amount = ?, type = ?, description = ?, date = ?
            WHERE id = ? AND user_id = ?
            """,
            (category_id, amount, type_, description, date_str, tx_id, user_id),
        )
        db.commit()

        return redirect(url_for("views.index"))

    
    return render_template("edit.html", tx=tx, categories=categories)

@views_bp.route("/categories", methods=["GET", "POST"])
def categories():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        # agregar categoría
        if action == "add":
            name = (request.form.get("name") or "").strip()
            if not name:
                return "Nombre de categoría requerido", 400

            # evitar duplicados por usuario
            existing = db.execute(
                "SELECT id FROM categories WHERE user_id = ? AND name = ?",
                (user_id, name),
            ).fetchone()
            if existing:
                return "La categoría ya existe", 400

            db.execute(
                "INSERT INTO categories (user_id, name) VALUES (?, ?)",
                (user_id, name),
            )
            db.commit()
            return redirect("/categories")

        # eliminar categoría
        if action == "delete":
            cat_id = request.form.get("category_id")
            if not cat_id:
                return "ID de categoría requerido", 400

            db.execute(
                "DELETE FROM categories WHERE id = ? AND user_id = ?",
                (cat_id, user_id),
            )
            db.commit()
            return redirect("/categories")

    # GET: listar categorias
    rows = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    return render_template("categories.html", categories=rows)

@views_bp.route("/history")
def summary():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()

    income = db.execute(
        """
        SELECT SUM(amount) as total_income
        FROM transactions
        WHERE user_id = ? AND type = 'income'
        """,
        (user_id,),
    ).fetchone()["total_income"] or 0

    expense = db.execute(
        """
        SELECT SUM(amount) as total_expense
        FROM transactions
        WHERE user_id = ? AND type = 'expense'
        """,
        (user_id,),
    ).fetchone()["total_expense"] or 0

    balance = income - expense

    return render_template(
        "summary.html", 
        income=income,
        expense=expense,
        balance=balance,
    )
