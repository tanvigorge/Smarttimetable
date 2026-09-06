import os
import smtplib
from email.message import EmailMessage


def build_reminders(assignments, exams, today, days_before=3):
    reminders = []
    for item in assignments:
        if item.get("completed"):
            continue
        days_left = (item["due_date"] - today).days
        if 0 <= days_left <= days_before:
            reminders.append(
                {
                    "title": f"Assignment due: {item['title']}",
                    "subject": item.get("subject", "General"),
                    "date": item["due_date"].isoformat(),
                    "days_left": days_left,
                    "priority": item.get("priority", "Medium"),
                }
            )
    for item in exams:
        days_left = (item["exam_date"] - today).days
        if 0 <= days_left <= days_before:
            reminders.append(
                {
                    "title": f"Exam coming up: {item['subject']}",
                    "subject": item["subject"],
                    "date": item["exam_date"].isoformat(),
                    "days_left": days_left,
                    "priority": "Critical",
                }
            )
    return sorted(reminders, key=lambda item: (item["days_left"], item["priority"]))


def send_email_reminder(reminders, recipient, smtp_host, smtp_port, smtp_user, smtp_password, sender=None):
    if not reminders:
        raise ValueError("There are no reminders to send.")
    if not recipient.strip():
        raise ValueError("A recipient email address is required.")
    if not smtp_host.strip() or not smtp_user.strip() or not smtp_password:
        raise ValueError("SMTP host, username, and password are required.")

    message = EmailMessage()
    message["Subject"] = "Smart Timetable reminders"
    message["From"] = sender or smtp_user
    message["To"] = recipient.strip()
    message.set_content(
        "Upcoming academic items:\n\n"
        + "\n".join(
            f"- {item['title']} ({item['date']}, {item['days_left']} days left)"
            for item in reminders
        )
    )
    with smtplib.SMTP(smtp_host.strip(), int(smtp_port), timeout=15) as server:
        server.starttls()
        server.login(smtp_user.strip(), smtp_password)
        server.send_message(message)


def smtp_defaults():
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
    }
