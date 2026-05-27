# Bilingual Frankfurt / Rhein-Main Lunch Survey

Small Flask web app for an anonymous lunch habits survey among working people in Frankfurt and nearby Rhein-Main work areas such as Offenbach and Eschborn.

The survey is part of a seminar project at the University of Marburg:

```text
Eine Seminararbeit an der Uni Marburg
```

## Bilingual Format

All visible survey text uses one combined format:

```text
German text || English text
```

There are no separate German and English pages. The database stores normalized values such as `canteen`, `banking_district`, or `rather_yes`, not the full bilingual labels.

## Privacy

The app does not store names, email addresses, IP addresses, Reddit usernames, user agents, or device IDs. It only stores selected survey answers, optional comments, timestamps, and the optional `source` URL parameter.

Do not add third-party analytics or tracking scripts without a proper privacy review.

This is a student seminar prototype. Before large-scale public deployment, get proper GDPR/legal review for hosting, retention, consent language, data access, and deletion procedures.

## Local Setup With SQLite

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the local survey page:

```text
http://127.0.0.1:5000/
```

When `APP_ENV=development` and `DATABASE_URL` is not set, the app uses SQLite and creates:

```text
data/survey.db
```

Existing SQLite databases are updated safely by adding missing columns when the app starts.

## Environment Variables

Local `.env` example:

```text
APP_ENV=development
FLASK_DEBUG=1
ADMIN_PASSWORD=change-this-to-a-strong-password
SECRET_KEY=change-this-to-a-long-random-secret-key
# DATABASE_URL=postgresql://username:password@host:5432/database_name
```

Production must set:

```text
APP_ENV=production
DATABASE_URL=postgresql://username:password@host:5432/database_name
ADMIN_PASSWORD=your-initial-strong-admin-password
SECRET_KEY=your-long-random-secret-key
```

In production, the app refuses to start if `DATABASE_URL`, `SECRET_KEY`, and either `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH` are missing.

Recommended admin password:

- at least 16 characters
- uppercase and lowercase letters
- numbers
- special characters
- unique to this app

Do not commit `.env` to Git. In production, prefer environment variables or a deployment secret manager. Do not store production passwords in committed plaintext files.

## Admin Password

On first start, the app initializes an admin password hash in the database from `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH`. The plaintext password is not stored in the database.

After logging in, the admin dashboard includes a password-change form. New admin passwords must be at least 16 characters.

If `ADMIN_PASSWORD` is missing in local development, the app allows the fallback password `admin123` and prints a console warning. This fallback is blocked in production by the required environment checks.

## PostgreSQL Production Option

For public Reddit sharing, use PostgreSQL rather than SQLite:

```text
DATABASE_URL=postgresql://username:password@host:5432/database_name
```

The app also accepts old `postgres://` URLs and converts them to `postgresql://`.

You usually do not need local pgAdmin for deployment. On platforms such as Render or Railway, create a managed PostgreSQL database, copy its connection string, and set it as `DATABASE_URL` for the web service.

## Production Start Command

The project includes:

```text
Procfile
runtime.txt
```

Production start command:

```text
gunicorn app:app
```

Local development can still use:

```powershell
python app.py
```

## Admin Pages

Login:

```text
http://127.0.0.1:5000/admin
```

After login, the dashboard is:

```text
http://127.0.0.1:5000/admin/export
```

The dashboard includes filters, charts, latest filtered responses, CSV export links, report link, logout, and admin password change.

The clear-data button is available only outside production. In `APP_ENV=production`, both the button and the clearing route are disabled.

Readable seminar report:

```text
http://127.0.0.1:5000/admin/report
```

## CSV Export

The raw response CSV preserves active filters:

```text
http://127.0.0.1:5000/admin/export.csv
```

The statistics CSV also preserves active filters:

```text
http://127.0.0.1:5000/admin/export-stats.csv
```

Example filtered export:

```text
http://127.0.0.1:5000/admin/export.csv?source_platform=reddit_frankfurt&q_area=banking_district
```

## Reddit Source Tracking

Use this link pattern for Reddit Frankfurt:

```text
https://your-domain.com/?source=reddit_frankfurt
```

Other examples:

```text
https://your-domain.com/?source=linkedin
https://your-domain.com/?source=offline_tablet
https://your-domain.com/?source=whatsapp
https://your-domain.com/?source=qr_code
```

Only the source string is stored in `source_platform`. No Reddit usernames are stored.

## Duplicate Submission Prevention

The app uses browser `localStorage` as a soft duplicate prevention:

```text
lunch_survey_submitted=true
```

After a successful submission, the same browser sees:

```text
Sie haben bereits teilgenommen. || You have already participated.
```

Users can still click:

```text
Trotzdem erneut teilnehmen || Participate again anyway
```

This is not IP-based tracking and does not permanently block anyone.

## Git Hygiene

The `.gitignore` excludes local secrets, local databases, virtual environments, IDE settings, and Python cache files. Do not commit:

```text
.env
data/survey.db
.venv/
```
