from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tasks.db"

VALID_STATUSES = {"pending", "in_progress", "done"}

app = Flask(__name__)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                scheduled_for TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

        # Migrate old schema: is_done (0/1) -> status (pending/done)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        if "is_done" in cols and "status" not in cols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'"
            )
            conn.execute("UPDATE tasks SET status = 'done' WHERE is_done = 1")
            conn.commit()

        if "start_date" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN start_date TEXT")
            conn.commit()

        if "end_date" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN end_date TEXT")
            conn.commit()


init_db()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/image/<path:filename>")
def image_file(filename: str):
    return send_from_directory(BASE_DIR / "Image", filename)


@app.route("/api/tasks", methods=["GET"])
def list_tasks() -> Any:
    status_filter = request.args.get("status", "all").strip()
    if status_filter not in ("all", *VALID_STATUSES):
        return jsonify({"error": "Invalid status filter."}), 400

    order = """
        ORDER BY
            CASE WHEN end_date IS NULL OR end_date = '' THEN 1 ELSE 0 END,
            end_date ASC,
            created_at DESC
    """

    with get_db_connection() as conn:
        if status_filter == "all":
            rows = conn.execute(
                f"SELECT id, title, message, start_date, end_date, scheduled_for, status, created_at FROM tasks {order}"
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, title, message, start_date, end_date, scheduled_for, status, created_at FROM tasks WHERE status = ? {order}",
                (status_filter,),
            ).fetchall()

    tasks = [dict(row) for row in rows]
    for task in tasks:
        task["note"] = task.get("message", "")
        task["task_name"] = task.get("title", "")
        task["details"] = task.get("message", "")
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task() -> Any:
    data = request.get_json(silent=True) or {}
    task_name = str(data.get("task_name", "")).strip()
    details = str(data.get("details", "")).strip()
    start_date = str(data.get("start_date", "")).strip()
    end_date = str(data.get("end_date", "")).strip()
    note = str(data.get("note", "")).strip()
    title = str(data.get("title", "")).strip()
    message = str(data.get("message", "")).strip()
    scheduled_for = str(data.get("scheduled_for", "")).strip()
    status = str(data.get("status", "pending")).strip()

    if task_name:
        title = task_name
    if details:
        message = details
    if note:
        message = note

    if not title and message:
        title = message[:80]

    if not title or not message:
        return jsonify({"error": "Task name and details are required."}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status."}), 400

    if bool(start_date) != bool(end_date):
        return jsonify({"error": "Both from and to dates are required together."}), 400

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end < start:
                return jsonify({"error": "To date cannot be earlier than from date."}), 400
        except ValueError:
            return jsonify({"error": "Invalid from/to date format."}), 400

    if scheduled_for:
        try:
            parsed = datetime.fromisoformat(scheduled_for)
            scheduled_for = parsed.strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify({"error": "Invalid schedule format."}), 400

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, message, start_date, end_date, scheduled_for, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, message, start_date, end_date, scheduled_for, status,
             datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
        task_id = cursor.lastrowid

        row = conn.execute(
            "SELECT id, title, message, start_date, end_date, scheduled_for, status, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    task = dict(row)
    task["note"] = task.get("message", "")
    task["task_name"] = task.get("title", "")
    task["details"] = task.get("message", "")
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id: int) -> Any:
    data = request.get_json(silent=True) or {}
    updates: list[str] = []
    values: list[Any] = []

    if "note" in data:
        note = str(data["note"]).strip()
        if not note:
            return jsonify({"error": "Note cannot be empty."}), 400
        updates.append("title = ?")
        values.append(note)
        updates.append("message = ?")
        values.append(note)

    if "title" in data:
        title = str(data["title"]).strip()
        if not title:
            return jsonify({"error": "Title cannot be empty."}), 400
        updates.append("title = ?")
        values.append(title)

    if "task_name" in data:
        task_name = str(data["task_name"]).strip()
        if not task_name:
            return jsonify({"error": "Task name cannot be empty."}), 400
        updates.append("title = ?")
        values.append(task_name)

    if "message" in data:
        message = str(data["message"]).strip()
        if not message:
            return jsonify({"error": "Message cannot be empty."}), 400
        updates.append("message = ?")
        values.append(message)

    if "details" in data:
        details = str(data["details"]).strip()
        if not details:
            return jsonify({"error": "Details cannot be empty."}), 400
        updates.append("message = ?")
        values.append(details)

    if "start_date" in data:
        start_date = str(data["start_date"]).strip()
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid from date format."}), 400
        updates.append("start_date = ?")
        values.append(start_date)

    if "end_date" in data:
        end_date = str(data["end_date"]).strip()
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid to date format."}), 400
        updates.append("end_date = ?")
        values.append(end_date)

    if "status" in data:
        status = str(data["status"]).strip()
        if status not in VALID_STATUSES:
            return jsonify({"error": f"Status must be one of: {', '.join(VALID_STATUSES)}."}), 400
        updates.append("status = ?")
        values.append(status)

    if not updates:
        return jsonify({"error": "Nothing to update."}), 400

    values.append(task_id)
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, title, message, start_date, end_date, scheduled_for, status, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        return jsonify({"error": "Task not found."}), 404

    task = dict(row)
    task["note"] = task.get("message", "")
    task["task_name"] = task.get("title", "")
    task["details"] = task.get("message", "")
    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> Any:
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found."}), 404

    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
