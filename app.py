
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from db import get_db_connection
from datetime import date
from decimal import Decimal, InvalidOperation
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


# -------------------------------
# Login Required Decorator
# -------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# -------------------------------
# Registration
# -------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        connection = get_db_connection()

        if connection is None:
            return "Database connection failed!"

        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:
                flash("This email is already registered.", "error")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (name, email, hashed_password)
            )

            connection.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            connection.rollback()
            print("Registration error:", e)
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for("register"))

        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")


# -------------------------------
# Login
# -------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "error")
            return redirect(url_for("login"))

        connection = get_db_connection()

        if connection is None:
            return "Database connection failed!"

        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )

            user = cursor.fetchone()

        except Exception as e:
            print("Login database error:", e)
            flash("Unable to access the database.", "error")
            return redirect(url_for("login"))

        finally:
            cursor.close()
            connection.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            flash("Welcome back, " + user["name"] + "!", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    if "user_id" in session:
        return redirect(url_for("index"))

    return render_template("login.html")


# -------------------------------
# Logout
# -------------------------------

@app.route("/logout")
@login_required
def logout():

    session.clear()
    flash("You have logged out successfully.", "success")

    return redirect(url_for("login"))


# -------------------------------
# Dashboard
# -------------------------------

@app.route("/")
@login_required
def index():

    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    cursor = connection.cursor(dictionary=True)

    try:
        today = date.today()
        user_id = session["user_id"]

        # Daily calorie and food summary
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(calories), 0) AS total_calories,
                COUNT(*) AS total_entries
            FROM food_entries
            WHERE food_date = %s AND user_id = %s
            """,
            (today, user_id)
        )

        summary = cursor.fetchone()

        # Daily nutrition summary
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(protein), 0) AS total_protein,
                COALESCE(SUM(carbs), 0) AS total_carbs,
                COALESCE(SUM(fats), 0) AS total_fats
            FROM food_entries
            WHERE food_date = %s AND user_id = %s
            """,
            (today, user_id)
        )

        nutrition_summary = cursor.fetchone()

        # Today's food records
        cursor.execute(
            """
            SELECT *
            FROM food_entries
            WHERE food_date = %s AND user_id = %s
            ORDER BY id DESC
            """,
            (today, user_id)
        )

        foods = cursor.fetchall()

        # Meal-wise calorie summary
        cursor.execute(
            """
            SELECT meal_type, SUM(calories) AS total
            FROM food_entries
            WHERE food_date = %s AND user_id = %s
            GROUP BY meal_type
            """,
            (today, user_id)
        )

        meal_summary = cursor.fetchall()

        # Daily water summary
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount_ml), 0) AS water_consumed
            FROM water_entries
            WHERE water_date = %s AND user_id = %s
            """,
            (today, user_id)
        )

        water_summary = cursor.fetchone()

        water_goal = 2000
        water_consumed = water_summary["water_consumed"]
        water_remaining = max(water_goal - water_consumed, 0)
        water_percentage = min(
            (water_consumed / water_goal) * 100, 100
        )

        return render_template(
            "index.html",
            summary=summary,
            nutrition_summary=nutrition_summary,
            foods=foods,
            meal_summary=meal_summary,
            water_consumed=water_consumed,
            water_goal=water_goal,
            water_remaining=water_remaining,
            water_percentage=water_percentage,
            today=today,
            user_name=session.get("user_name")
        )

    except Exception as e:
        print("Dashboard error:", e)
        return "Dashboard loading failed. Check the VS Code terminal."

    finally:
        cursor.close()
        connection.close()


# -------------------------------
# Add Food
# -------------------------------

@app.route("/add-food", methods=["GET", "POST"])
@login_required
def add_food():

    if request.method == "POST":

        food_name = request.form.get("food_name", "").strip()
        meal_type = request.form.get("meal_type", "")
        calories = request.form.get("calories", "")
        protein = request.form.get("protein", "")
        carbs = request.form.get("carbs", "")
        fats = request.form.get("fats", "")
        food_date = request.form.get("food_date", "")

        if not all([
            food_name, meal_type, calories,
            protein, carbs, fats, food_date
        ]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("add_food"))

        try:
            calories = int(calories)
            protein = Decimal(protein)
            carbs = Decimal(carbs)
            fats = Decimal(fats)

            if calories <= 0:
                raise ValueError

            if not all(
                value.is_finite() and value >= 0
                for value in [protein, carbs, fats]
            ):
                raise ValueError

        except (ValueError, InvalidOperation):
            flash("Please enter valid nutrition values.", "error")
            return redirect(url_for("add_food"))

        connection = get_db_connection()

        if connection is None:
            return "Database connection failed!"

        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO food_entries
                (
                    user_id, food_name, meal_type, calories,
                    protein, carbs, fats, food_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    food_name,
                    meal_type,
                    calories,
                    protein,
                    carbs,
                    fats,
                    food_date
                )
            )

            connection.commit()

            flash("Food record added successfully!", "success")
            return redirect(url_for("index"))

        except Exception as e:
            connection.rollback()
            print("Add food error:", e)
            flash("Unable to add food record.", "error")
            return redirect(url_for("add_food"))

        finally:
            cursor.close()
            connection.close()

    return render_template(
        "add_food.html",
        today=date.today()
    )


# -------------------------------
# Add Water
# -------------------------------

@app.route("/add-water", methods=["POST"])
@login_required
def add_water():

    amount_ml = request.form.get("amount_ml", "")

    try:
        amount_ml = int(amount_ml)

        if amount_ml not in [150, 250, 500]:
            flash("Please select a valid water quantity.", "error")
            return redirect(url_for("index"))

    except ValueError:
        flash("Invalid water quantity.", "error")
        return redirect(url_for("index"))

    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO water_entries
            (user_id, amount_ml, water_date)
            VALUES (%s, %s, %s)
            """,
            (session["user_id"], amount_ml, date.today())
        )

        connection.commit()
        flash("Water intake added successfully!", "success")

    except Exception as e:
        connection.rollback()
        print("Water tracking error:", e)
        flash("Unable to save water intake.", "error")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("index"))


# -------------------------------
# Food History
# -------------------------------

@app.route("/history")
@login_required
def history():

    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM food_entries
            WHERE user_id = %s
            ORDER BY food_date DESC, id DESC
            """,
            (session["user_id"],)
        )

        foods = cursor.fetchall()

        return render_template(
            "history.html",
            foods=foods
        )

    except Exception as e:
        print("History error:", e)
        return "Unable to load food history."

    finally:
        cursor.close()
        connection.close()


# -------------------------------
# Delete Food
# -------------------------------

@app.route("/delete/<int:food_id>", methods=["POST"])
@login_required
def delete_food(food_id):

    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM food_entries
            WHERE id = %s AND user_id = %s
            """,
            (food_id, session["user_id"])
        )

        connection.commit()

        if cursor.rowcount == 0:
            flash("Food record not found.", "error")
        else:
            flash("Food record deleted successfully!", "success")

        return redirect(request.referrer or url_for("history"))

    except Exception as e:
        connection.rollback()
        print("Delete error:", e)
        flash("Unable to delete food record.", "error")
        return redirect(url_for("history"))

    finally:
        cursor.close()
        connection.close()


# -------------------------------
# Run Application
# -------------------------------

if __name__ == "__main__":
    app.run(debug=True)
