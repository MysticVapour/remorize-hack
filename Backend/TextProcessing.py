import sqlite3
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from openai import OpenAI
import json
from dotenv import load_dotenv
import os
from pineconefuncs import index_markdown_note

load_dotenv()


client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

DB_PATH = "app.db"


def check_and_process_texts():
    """Check for texts that are an hour past their timestamp and process them"""
    current_time = datetime.datetime.now()
    one_hour_ago = current_time - datetime.timedelta(minutes=1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Select texts where the datetime is more than one hour ago
    cursor.execute(
        "SELECT id, raw_text FROM texts WHERE datetime <= ?",
        (one_hour_ago.strftime("%Y%m%d%H%M"),),
    )
    rows = cursor.fetchall()

    for row in rows:
        text_id, raw_text = row
        notes = process_text_to_notes(raw_text)

        index_markdown_note(notes)

        cursor.execute("UPDATE texts SET notes_text = ? WHERE id = ?", (notes, text_id))

    cursor.execute(
        "SELECT id, raw_text FROM texts WHERE datetime <= ?",
        (one_hour_ago.strftime("%Y%m%d%H%M"),),
    )
    rows = cursor.fetchall()

    for row in rows:
        text_id, raw_text = row
        action_items = extract_action_items(raw_text)
        cursor.execute(
            "UPDATE texts SET action_items_text = ? WHERE id = ?",
            (json.dumps(action_items), text_id),
        )

    conn.commit()
    conn.close()


def process_text_to_notes(raw_text):
    """Placeholder function to simulate text processing"""
    # This should ideally call an AI model to process the text into notes
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Convert the following text into structured notes in markdown format, that is # for headings, ** for bold texts, > for blockquotes, - for lists and --- for horizontal rule without adding any introductory text.",
            },
            {"role": "user", "content": raw_text},
        ],
    )
    notes = response.choices[0].message.content
    return notes


def extract_action_items(raw_text):
    current_time = datetime.datetime.now()
    """Use GPT to extract action items, calendar events, and email drafts from text."""
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """You are an assistant skilled in extracting structured information. 
                Convert the following text into a structured JSON containing task lists, calendar events, and email drafts. 
                You may ignore content if it does not require to be made into a task, event or email. Here's the format for the JSON:
                            {
                “Task List”: [a, b, c, d, e …],
                “Calendar Events” : [{
                        'summary': summary,
                        'location': location,
                        'description': description,
                        'start': {
                            'dateTime': 2015-05-28T09:00:00-07:00 in this format but use the actual date and time from the text, or schedule it a few days after ${current_time}
                                'timeZone': 'America/New_York',
                        },
                        'end': {
                                'dateTime': 2015-05-28T17:00:00-07:00 in this format but the end time is an hour after the start time,
                                'timeZone': 'America/New_York',
                        }
                    }, b, c, d, e …]	“Email Draft”: [
                    { “Subject”: “…”, “Content”: “…”}, b, c, d, e …
                ]
            }
                """,
            },
            {"role": "user", "content": raw_text},
        ],
    )
    # Assume that the model's response is well-structured JSON
    structured_data = json.loads(response.choices[0].message.content)
    return structured_data


def schedule_action_items():
    """Check for texts that are an hour past their timestamp and extract action items."""
    current_time = datetime.datetime.now()
    one_hour_ago = current_time - datetime.timedelta(minutes=1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, raw_text FROM texts WHERE datetime <= ? AND action_items_text = ''",
        (one_hour_ago.strftime("%Y%m%d%H%M"),),
    )
    rows = cursor.fetchall()

    for row in rows:
        text_id, raw_text = row
        action_items = extract_action_items(raw_text)
        cursor.execute(
            "UPDATE texts SET action_items_text = ? WHERE id = ?",
            (json.dumps(action_items), text_id),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(check_and_process_texts, "interval", minutes=1)
    print("Scheduler started, checking for texts to process every minute...")
    scheduler.start()
