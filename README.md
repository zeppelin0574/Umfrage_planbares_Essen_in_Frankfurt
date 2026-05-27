# Bilingual Frankfurt / Rhein-Main Lunch Survey

Small Flask web app for an anonymous student seminar survey about lunch habits of working people in Frankfurt and nearby Rhein-Main work areas such as Offenbach and Eschborn.

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

Open the survey page:

```text
http://127.0.0.1:5000/
```

When `DATABASE_URL` is not set, the app uses SQLite and creates:

```text
data/survey.db
```

Existing SQLite databases are updated safely by adding missing columns when the app starts.

## PostgreSQL Production Option

Set `DATABASE_URL` for PostgreSQL:

```powershell
$env:DATABASE_URL="postgresql://username:password@host:5432/database_name"
python app.py
```

The app also accepts old `postgres://` URLs and converts them to `postgresql://`.

## Admin Password And Secret Key

Set both values before deployment:

```powershell
$env:ADMIN_PASSWORD="your-strong-password"
$env:SECRET_KEY="your-long-random-secret-key"
```

Recommended admin password:

- at least 16 characters
- uppercase and lowercase letters
- numbers
- special characters
- unique to this app

Do not commit `.env` to Git. In production, prefer environment variables or a deployment secret manager. Do not store production passwords in committed plaintext files.

If `ADMIN_PASSWORD` is missing, the app allows a local development fallback password `admin123` and prints a console warning. If `SECRET_KEY` is missing, the app also uses a local development fallback and prints a warning. These fallbacks are only for local testing.

`.env.example` shows the expected variables.

## Admin Pages

Login:

```text
http://127.0.0.1:5000/admin
```

After login, the dashboard is:

```text
http://127.0.0.1:5000/admin/export
```

The dashboard includes filters, charts, latest filtered responses, CSV export links, a report link, logout, and a clear-data button for testing.

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

## Source Tracking

Share source-specific links without collecting personal identifiers:

```text
http://your-domain.com/?source=reddit_frankfurt
http://your-domain.com/?source=linkedin
http://your-domain.com/?source=offline_tablet
http://your-domain.com/?source=whatsapp
http://your-domain.com/?source=qr_code
```

Only the source string is stored in `source_platform`.

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
