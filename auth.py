from werkzeug.security import check_password_hash, generate_password_hash
from flask import render_template, request, redirect, session, Blueprint, request,url_for

from db import get_db

auth_bp = Blueprint("auth", __name__,)



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or password != confirmation:
            return "Error en datos", 400

        hash_ = generate_password_hash(password)

        db = get_db()

        
        row = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is not None:
            return "Usuario ya existe", 400

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, hash_),
        )
        db.commit()

        return redirect("/login")

    return render_template("register.html")




@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Faltan datos", 400

        db = get_db()
        row = db.execute(
            "SELECT id, hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if row is None or not check_password_hash(row["hash"], password):
            return "Usuario o contraseña incorrectos", 400

        session["user_id"] = row["id"]

        return redirect(url_for("views.index"))

    return render_template("login.html")




@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")