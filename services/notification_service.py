from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


def create_notification(
    conn: sqlite3.Connection,
    user_id: int,
    farm_id: int,
    title: str,
    message: str,
    notification_type: str = "SYSTEM",
    link_url: Optional[str] = None,
) -> int:
    """Inserts a persistent in-app notification if a similar unread notification does not already exist."""
    # Prevent duplicate unread notifications
    existing = conn.execute(
        """
        SELECT id FROM notifications
        WHERE user_id = ? AND title = ? AND is_read = 0
        """,
        (user_id, title),
    ).fetchone()
    if existing:
        return existing[0]

    cur = conn.execute(
        """
        INSERT INTO notifications (user_id, farm_id, title, message, notification_type, is_read, link_url, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
        """,
        (user_id, farm_id, title, message, notification_type, link_url),
    )
    conn.commit()
    return cur.lastrowid


def get_user_notifications(conn_or_user: Any, user_or_conn: Any, limit: int = 15) -> List[Dict[str, Any]]:
    if isinstance(conn_or_user, sqlite3.Connection):
        conn = conn_or_user
        uid = user_or_conn
    else:
        uid = conn_or_user
        conn = user_or_conn

    rows = conn.execute(
        """
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY is_read ASC, id DESC
        LIMIT ?
        """,
        (uid, limit),
    ).fetchall()
    return [dict(r) for r in rows]



def get_unread_count(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
    ).fetchone()
    return row[0] if row else 0


def mark_notification_read(conn_or_id: Any, notification_id_or_conn: Any = None, user_id: Optional[int] = None) -> bool:
    if isinstance(conn_or_id, sqlite3.Connection):
        conn = conn_or_id
        notif_id = notification_id_or_conn
    else:
        notif_id = conn_or_id
        conn = notification_id_or_conn

    if user_id is not None:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user_id))
    else:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    return True


def mark_all_read(conn_or_user: Any, user_or_conn: Any = None) -> bool:
    if isinstance(conn_or_user, sqlite3.Connection):
        conn = conn_or_user
        uid = user_or_conn
    else:
        uid = conn_or_user
        conn = user_or_conn

    if uid:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (uid,))
    else:
        conn.execute("UPDATE notifications SET is_read = 1")
    conn.commit()
    return True


mark_notification_as_read = mark_notification_read
mark_all_notifications_as_read = mark_all_read



def sync_farm_notifications(
    conn: sqlite3.Connection,
    user_id: int,
    farm_id: int,
    activities: List[Dict[str, Any]],
    weather: Dict[str, Any],
) -> int:
    """Auto-generates timely in-app notifications from activities and live weather."""
    count = 0
    today_str = date.today().isoformat()

    # 1. Activities due today or overdue
    for act in activities:
        st = str(act.get("status", "")).upper()
        due = str(act.get("due_date", ""))
        title = act.get("title", "Farm Task")

        if st == "PENDING" and due == today_str:
            create_notification(
                conn, user_id, farm_id,
                title=f"Task Due Today: {title}",
                message=f"Scheduled operation '{title}' is due for execution today.",
                notification_type="DUE_TODAY",
                link_url="/activities",
            )
            count += 1
        elif st == "PENDING" and due < today_str and due != "":
            create_notification(
                conn, user_id, farm_id,
                title=f"Overdue Task: {title}",
                message=f"Farm activity '{title}' was due on {due} and requires immediate action.",
                notification_type="OVERDUE",
                link_url="/activities",
            )
            count += 1

    # 2. Weather alerts
    curr = weather.get("current", {})
    if float(curr.get("wind_speed", 0.0) or 0.0) > 25.0:
        create_notification(
            conn, user_id, farm_id,
            title="High Wind Alert",
            message=f"Current wind speed is {curr.get('wind_speed')} km/h. Avoid pesticide spraying.",
            notification_type="WEATHER",
            link_url="/weather",
        )
        count += 1

    rain_prob = float(curr.get("rain_probability", 0.0) or 0.0)
    if rain_prob > 75.0:
        create_notification(
            conn, user_id, farm_id,
            title="Incoming Rain Alert",
            message=f"High precipitation probability ({rain_prob:.0f}%). Delay planned irrigation.",
            notification_type="WEATHER",
            link_url="/weather",
        )
        count += 1

    return count
