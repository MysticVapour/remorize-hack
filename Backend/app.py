from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
import datetime
from pineconefuncs import find_relevant_notes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar"]

app = Flask(__name__)
CORS(app)

DB_PATH = "app.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
        uuid TEXT PRIMARY KEY,
        email_id TEXT UNIQUE,
        token TEXT
    )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT,
        datetime TEXT,
        raw_text TEXT,
        notes_text TEXT DEFAULT '',
        action_items_text TEXT DEFAULT '',
        FOREIGN KEY (user_uuid) REFERENCES users(uuid)
    )"""
    )
    conn.commit()
    conn.close()


@app.route("/register_user", methods=["POST"])
def register_user():
    data = request.json
    email = data["email"]
    token = data.get("token", "")  # Optional field

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Check if the email already exists and fetch the UUID
        cursor.execute("SELECT uuid FROM users WHERE email_id = ?", (email,))
        result = cursor.fetchone()

        if result:
            # If the email is already registered, return the existing UUID
            user_uuid = result[0]
            return jsonify(success=True, uuid=user_uuid, message="Login successful")
        else:
            # If the email is not registered, create a new user
            user_uuid = str(uuid.uuid4())  # Generate a new UUID for each new user
            cursor.execute(
                "INSERT INTO users (uuid, email_id, token) VALUES (?, ?, ?)",
                (user_uuid, email, token),
            )
            conn.commit()
            return jsonify(
                success=True, uuid=user_uuid, message="Registration successful"
            )

    return jsonify(success=False, message="An error occurred"), 500


@app.route("/receive_text", methods=["POST"])
def receive_text():
    data = request.json
    user_uuid = data["uuid"]
    datetime = data["dateTime"]
    text = data["text"]

    print(f"Received text from user {user_uuid} at {datetime}: {text}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT raw_text FROM texts WHERE user_uuid = ? AND datetime = ?",
            (user_uuid, datetime),
        )
        result = cursor.fetchone()

        if result:
            new_text = result[0] + " " + text
            cursor.execute(
                "UPDATE texts SET raw_text = ? WHERE user_uuid = ? AND datetime = ?",
                (new_text, user_uuid, datetime),
            )
        else:
            cursor.execute(
                "INSERT INTO texts (user_uuid, datetime, raw_text) VALUES (?, ?, ?)",
                (user_uuid, datetime, text),
            )
        conn.commit()
    return jsonify(success=True)


@app.route("/get_relevant_notes", methods=["POST"])
def get_relevant_notes_endpoint():
    data = request.get_json()
    try:
        return jsonify(success=True, data=find_relevant_notes(data.get("query")))
    except Exception as e:
        print(e)


@app.route("/get_texts_by_email", methods=["POST"])
def get_texts_by_email():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify(success=False, message="Email parameter is required"), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT uuid FROM users WHERE email_id = ?", (email,))
        result = cursor.fetchone()

        if not result:
            return jsonify(success=False, message="Email not found"), 404

        user_uuid = result[0]

        cursor.execute(
            "SELECT id, datetime, raw_text, notes_text, action_items_text FROM texts WHERE user_uuid = ?",
            (user_uuid,),
        )
        texts = cursor.fetchall()

        texts_data = [
            {
                "id": text[0],
                "dateTime": text[1],
                "rawText": text[2],
                "notesText": text[3],
                "actionItemsText": text[4],
            }
            for text in texts
        ]

        return jsonify(success=True, texts=texts_data)

    return jsonify(success=False, message="An error occurred"), 500


def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    service = build("calendar", "v3", credentials=creds)
    return service


@app.route("/add_event", methods=["POST"])
def add_event():
    events_data = request.json
    now = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        service = get_calendar_service()
        for event_data in events_data:
            event = (
                service.events().insert(calendarId="primary", body=event_data).execute()
            )
        print("Event created: %s" % (event.get("htmlLink")))
        return jsonify({"status": "success", "event_id": event.get("id")}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
