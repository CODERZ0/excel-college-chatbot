
import os
from uuid import uuid4

from flask import Flask, render_template, request, session
from chatbot import chatbot
import mysql.connector

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-development-secret-change-before-deployment"
)

app.static_folder = "static"


@app.route("/")
def home():
    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid4())
    return render_template("index.html")


@app.route("/get")
def get_bot_response():
    user_text = request.args.get("msg", "").strip()

    if not user_text:
        return "Please type a question about Excel Engineering College."

    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid4())

    return chatbot.get_response(
        user_text,
        session_id=session["chat_session_id"]
    )


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/result", methods=["POST", "GET"])
def result():
    if request.method != "POST":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    mydb = None
    mycursor = None

    try:
        mydb = mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "chatbot"),
            port=int(os.environ.get("DB_PORT", "3306"))
        )

        mycursor = mydb.cursor()

        mycursor.execute(
            "SELECT * FROM reg WHERE Username = %s AND Password = %s",
            (username, password)
        )

        if mycursor.fetchone():
            if "chat_session_id" not in session:
                session["chat_session_id"] = str(uuid4())

            return render_template("index.html")

        return render_template("login.html")

    except mysql.connector.Error:
        app.logger.exception("Login database connection failed")
        return "Login database is unavailable. Please try again later.", 503

    finally:
        if mycursor:
            mycursor.close()

        if mydb and mydb.is_connected():
            mydb.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
