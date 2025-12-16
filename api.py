from time import time
from flask import Blueprint, request, jsonify, current_app
from datetime import date, datetime, timedelta
from db import get_db
from functools import wraps
import jwt
from werkzeug.security import check_password_hash

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ------------------------------------------------------------------
# Auth utilities
# ------------------------------------------------------------------
def get_user_id_by_username(username: str):
    if not username:
        return None
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return row["id"] if row else None


def _decode_token(token: str, verify_exp=True):
    """Decodifica y valida un JWT token"""
    secret = current_app.config.get("SECRET_KEY", None)
    if not secret:
        raise RuntimeError("SECRET_KEY no está configurada en app.config")
    
    options = {"verify_exp": verify_exp}
    payload = jwt.decode(token, secret, algorithms=["HS256"], options=options)
    return payload


def _generate_token(user_id: int, username: str, expires_in_hours=24):
    """Genera un nuevo JWT token"""
    now_ts = int(time())
    exp_ts = now_ts + (expires_in_hours * 3600)
    
    payload = {
        "sub": str(user_id),  # JWT requiere que 'sub' sea string
        "username": username,
        "iat": now_ts,
        "exp": exp_ts,
    }
    
    secret = current_app.config.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY no está configurada")
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, exp_ts


def get_user_id_from_request():
    """Obtiene user_id desde Authorization header o parámetros (legacy)"""
    auth = request.headers.get("Authorization", "")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            try:
                payload = _decode_token(token)
                user_id_str = payload.get("sub")
                # Convertir de string a int
                return int(user_id_str) if user_id_str else None
            except jwt.ExpiredSignatureError:
                return None
            except jwt.InvalidTokenError:
                return None
            except (ValueError, TypeError):
                return None
   
    # Fallback para compatibilidad con requests sin token
    username = request.args.get("username") or (request.json and request.json.get("username"))
    return get_user_id_by_username(username)


def token_required(f):
    """Decorator que requiere un token JWT válido"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth:
            return jsonify({"error": "Authorization header requerido"}), 401
        
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Formato de Authorization header inválido. Use: Bearer <token>"}), 401
        
        token = parts[1]
        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Token inválido: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"error": f"Error al validar token: {str(e)}"}), 500
        
        # Agregar info del usuario al request
        request.user_id = int(payload.get("sub"))  # Convertir a int
        request.username = payload.get("username")
        return f(*args, **kwargs)
    
    return decorated


# ------------------------------------------------------------------
# Auth endpoints
# ------------------------------------------------------------------
@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """Login endpoint - retorna JWT token"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username y password son requeridos"}), 400

    db = get_db()
    row = db.execute(
        "SELECT id, hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if not row:
        return jsonify({"error": "Credenciales inválidas"}), 401

    if not check_password_hash(row["hash"], password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    user_id = row["id"]
    
    try:
        # Token válido por 24 horas (puedes ajustar este valor)
        token, exp_ts = _generate_token(user_id, username, expires_in_hours=24)
        
        return jsonify({
            "token": token,
            "expires_at": datetime.fromtimestamp(exp_ts).isoformat(),
            "expires_in": exp_ts - int(time()),  # segundos hasta expiración
            "user": {
                "id": user_id,
                "username": username
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al generar token: {str(e)}"}), 500


@api_bp.route("/auth/refresh", methods=["POST"])
@token_required
def api_refresh_token():
    """Refresh token - genera un nuevo token antes de que expire el actual"""
    try:
        # Usar la info del request (agregada por @token_required)
        user_id = request.user_id
        username = request.username
        
        # Generar nuevo token
        token, exp_ts = _generate_token(user_id, username, expires_in_hours=24)
        
        return jsonify({
            "token": token,
            "expires_at": datetime.fromtimestamp(exp_ts).isoformat(),
            "expires_in": exp_ts - int(time()),
            "user": {
                "id": user_id,
                "username": username
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al refrescar token: {str(e)}"}), 500


@api_bp.route("/auth/validate", methods=["POST"])
def api_validate_token():
    """Valida un token JWT sin requerir autenticación"""
    data = request.get_json(silent=True) or {}
    
    # Intentar obtener el token de varias fuentes
    token = None
    auth = request.headers.get("Authorization", "")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    
    if not token:
        token = data.get("token") or request.args.get("token")

    if not token:
        return jsonify({
            "valid": False,
            "error": "Token requerido"
        }), 400

    try:
        payload = _decode_token(token)
        
        exp = payload.get("exp")
        expires_at = None
        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp).isoformat()
        
        # Verificar si el usuario aún existe
        db = get_db()
        user_id = int(payload.get("sub"))  # Convertir a int
        user_exists = db.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        
        if not user_exists:
            return jsonify({
                "valid": False,
                "error": "Usuario no existe"
            }), 401

        return jsonify({
            "valid": True,
            "user_id": user_id,
            "username": payload.get("username"),
            "expires_at": expires_at,
            "issued_at": datetime.fromtimestamp(payload.get("iat")).isoformat() if payload.get("iat") else None,
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({
            "valid": False,
            "error": "Token expirado"
        }), 401
    except jwt.InvalidTokenError as e:
        return jsonify({
            "valid": False,
            "error": f"Token inválido: {str(e)}"
        }), 401
    except Exception as e:
        return jsonify({
            "valid": False,
            "error": f"Error al validar token: {str(e)}"
        }), 500


@api_bp.route("/auth/logout", methods=["POST"])
@token_required
def api_logout():
    """
    Logout endpoint - en JWT stateless no hay mucho que hacer server-side.
    El cliente debe eliminar el token.
    Si quieres invalidar tokens, necesitarías una blacklist en DB.
    """
    return jsonify({
        "status": "ok",
        "message": "Sesión cerrada. Elimine el token del cliente."
    }), 200


# ------------------------------------------------------------------
# Protected API endpoints
# ------------------------------------------------------------------
@api_bp.route("/categories")
def api_categories():
    """Lista categorías del usuario - soporta token y username (legacy)"""
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Autenticación requerida"}), 401

    db = get_db()
    rows = db.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    categories = [{"id": r["id"], "name": r["name"]} for r in rows]
    return jsonify({"categories": categories})


@api_bp.route("/summary")
def api_summary():
    """Resumen de transacciones del usuario"""
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Autenticación requerida"}), 401

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

    return jsonify({
        "total_income": income,
        "total_expense": expense,
        "balance": balance,
        "transactions": transactions,
    })


@api_bp.route("/analytics")
def api_analytics():
    """Analytics con filtros por rango de fechas"""
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Autenticación requerida"}), 401

    range_ = request.args.get("range", "month")  # month | year | all
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

    # Totales generales
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

    # Egresos por categoría
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

    # Ingresos por categoría
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

    return jsonify({
        "range": range_,
        "start_date": start_str,
        "end_date": end_str,
        "income_total": income_total,
        "expense_total": expense_total,
        "balance": balance,
        "expenses_by_category": expenses_by_category,
        "incomes_by_category": incomes_by_category,
    })


@api_bp.route("/transactions", methods=["POST"])
def api_create_transaction():
    """Crea una nueva transacción"""
    data = request.get_json(silent=True) or {}

    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Autenticación requerida"}), 401

    amount = data.get("amount")
    type_ = data.get("type")
    description = data.get("description") or ""
    category_name = (data.get("category") or "").strip()
    date_str = data.get("date") or date.today().isoformat()

    # Validaciones
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Monto inválido: {str(e)}"}), 400

    if type_ not in ("income", "expense"):
        return jsonify({"error": "Tipo debe ser 'income' o 'expense'"}), 400

    if not category_name:
        return jsonify({"error": "Categoría requerida"}), 400

    db = get_db()

    # Buscar o crear categoría
    cat = db.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ?",
        (user_id, category_name),
    ).fetchone()

    if cat:
        category_id = cat["id"]
    else:
        cursor = db.execute(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            (user_id, category_name)
        )
        db.commit()
        category_id = cursor.lastrowid

    # Crear transacción
    cursor = db.execute(
        """
        INSERT INTO transactions (user_id, category_id, amount, type, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, category_id, amount, type_, description, date_str),
    )
    db.commit()

    return jsonify({
        "status": "ok",
        "transaction_id": cursor.lastrowid
    }), 201