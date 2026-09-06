# Smart Timetable Assistant

A Track A Streamlit academic schedule manager with recurring class conflict detection, semester templates, assignment and exam tracking, study-time recommendations, Indian academic calendar dates, analytics, natural-language scheduling requests, email reminders, workflows, and optional Google Calendar synchronization.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   streamlit run app.py
   ```

Google Calendar is optional. The class planner, academic planner, study queue, analytics, scheduling assistant, and local reminders work without OAuth credentials.

## Google Calendar setup

1. In Google Cloud Console, create a project and enable the Google Calendar API.
2. Create an OAuth client for a desktop application.
3. Copy `.env.example` to `.env` and set `GOOGLE_CLIENT_ID` from Google Cloud Console.
4. Ensure `http://localhost:8501` is listed under **Authorized JavaScript origins** for the Web application client.
5. Click **Connect to Google Calendar** in the app and complete the browser popup authorization flow.

Calendar API failures are shown in the UI and do not prevent local academic planning.

## Features

- Semester and term templates with start and end validation.
- Recurring lectures, labs, tutorials, and seminars with overlap detection.
- Assignment deadlines with Low, Medium, High, and Critical priority levels.
- Exam records and an urgency-weighted study recommendation queue.
- Weekly class-hour, outstanding study-hour, completion-rate, and exam-count analytics.
- Common Indian national holidays and academic breaks as editable reference data.
- Google Calendar event creation and upcoming-event retrieval.
- Local scheduling requests such as `schedule Physics on Monday 14:00 to 15:00` and `find free time tomorrow`.
- Optional SMTP email reminders for assignments and exams due within three days. Set `SMTP_HOST`, `SMTP_PORT`, and `SMTP_USER` as environment defaults, then use an email/app password in the UI.
- Workflow API in `workflow_api.py` with health, list, create, complete, and submit endpoints.

## Local data and privacy

The app stores local planner data in `schedule.json`, `academic_data.json`, and `workflows.json`. The browser OAuth access token stays in Streamlit session memory and is never written to disk. The client ID is loaded from the ignored `.env` file; no client secret, credential file, or service account is used.

## Deployment

For Streamlit Community Cloud, deploy `app.py` and add Google OAuth files through the platform's secret/file configuration. Local JSON persistence is suitable for demos; production deployments should move planner data to an authenticated database.

SMTP defaults can be provided as deployment environment variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=student@example.com
```

Use a provider app password rather than a personal email password. SMTP and Calendar failures are shown in the UI and do not prevent local academic planning.
