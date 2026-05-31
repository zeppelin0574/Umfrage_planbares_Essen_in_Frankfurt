import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv()

db = SQLAlchemy()

DEV_ADMIN_PASSWORD = "admin123"
DEV_SECRET_KEY = "local-dev-secret-change-me"


Q1_OPTIONS = [
    ("bring_from_home", "Ich bringe etwas mit || I bring something from home"),
    ("supermarket_bakery", "Supermarkt / Bäckerei || Supermarket / bakery"),
    ("fast_food", "Döner / Fast Food || Kebab / fast food"),
    ("restaurant", "Restaurant || Restaurant"),
    ("canteen", "Kantine || Canteen"),
    ("delivery", "Lieferdienst || Delivery service"),
    ("varies", "Unterschiedlich || It varies"),
    ("other", "Sonstiges || Other"),
]

Q2_OPTIONS = [
    ("too_expensive", "Zu teuer || Too expensive"),
    ("long_waiting_time", "Zu lange Wartezeit || Waiting time too long"),
    ("few_healthy_options", "Zu wenig gesunde Optionen || Too few healthy options"),
    ("inconsistent_quality", "Qualität schwankt || Quality is inconsistent"),
    (
        "too_many_choices",
        "Zu viel Auswahl / Entscheidung dauert zu lange || Too many choices / decision takes too long",
    ),
    ("other", "Sonstiges || Other"),
]

Q3_OPTIONS = [
    ("under_8", "Unter 8 € || Under €8"),
    ("8_9", "8–9 € || €8–9"),
    ("9_10", "9–10 € || €9–10"),
    ("10_11", "10–11 € || €10–11"),
    ("over_11_quality", "Über 11 €, wenn die Qualität stimmt || Over €11 if the quality is good"),
]

Q4_OPTIONS = [
    ("yes_definitely", "Ja, auf jeden Fall || Yes, definitely"),
    ("rather_yes", "Eher ja || Rather yes"),
    ("maybe", "Vielleicht || Maybe"),
    ("rather_no", "Eher nein || Rather no"),
    ("no", "Nein || No"),
]

Q5_OPTIONS = [
    ("do_not_want_preorder", "Ich möchte nicht vorbestellen || I do not want to pre-order"),
    ("prefer_delivery", "Ich möchte lieber Lieferung || I prefer delivery"),
    ("do_not_trust_quality", "Ich vertraue der Qualität nicht || I do not trust the quality"),
    ("want_customization", "Ich möchte Gerichte individuell ändern können || I want to customize my meals"),
    ("price_too_high", "Der Preis wäre zu hoch || The price would be too high"),
    ("pickup_too_far", "Der Abholort wäre zu weit weg || The pickup location would be too far away"),
    ("other", "Sonstiges || Other"),
]

LUNCH_TIME_OPTIONS = [
    ("before_12", "Vor 12:00 || Before 12:00"),
    ("12_1230", "12:00–12:30 || 12:00–12:30"),
    ("1230_13", "12:30–13:00 || 12:30–13:00"),
    ("13_1330", "13:00–13:30 || 13:00–13:30"),
    ("after_1330", "Nach 13:30 || After 13:30"),
    ("varies", "Unterschiedlich || It varies"),
]

AREA_OPTIONS = [
    ("frankfurt_city_center", "Frankfurt Innenstadt / Hauptwache / Zeil || Frankfurt city center / Hauptwache / Zeil"),
    ("banking_district", "Bankenviertel || Banking district"),
    ("messe_gallus", "Messe / Gallus || Trade fair area / Gallus"),
    ("central_station_area", "Hauptbahnhofviertel || Main station area"),
    ("sachsenhausen", "Sachsenhausen || Sachsenhausen"),
    ("bockenheim_westend", "Bockenheim / Westend || Bockenheim / Westend"),
    ("ostend_ecb", "Ostend / EZB || Ostend / ECB area"),
    ("eschborn", "Eschborn || Eschborn"),
    ("offenbach", "Offenbach || Offenbach"),
    ("frankfurt_airport", "Frankfurt Flughafen || Frankfurt Airport"),
    ("other_rhein_main", "Anderer Bereich in Frankfurt/Rhein-Main || Other area in Frankfurt/Rhein-Main"),
    (
        "not_rhein_main",
        "Ich arbeite/esse normalerweise nicht in Frankfurt/Rhein-Main || I do not usually work/eat in Frankfurt/Rhein-Main",
    ),
]

ALL_OPTION_SETS = {
    "q1_lunch_type": Q1_OPTIONS,
    "q2_problems": Q2_OPTIONS,
    "q3_price": Q3_OPTIONS,
    "q4_preorder": Q4_OPTIONS,
    "q5_reason_not_use": Q5_OPTIONS,
    "q_lunch_time": LUNCH_TIME_OPTIONS,
    "q_area": AREA_OPTIONS,
}

STAT_SECTIONS = [
    ("q1", "Q1 lunch type", "Frage 1: Mittagessen (Mehrfachauswahl)"),
    ("q2", "Q2 lunch problems", "Frage 2: Probleme beim Mittagessen"),
    ("q3", "Q3 fair price", "Frage 3: Fairer Preis"),
    ("q4", "Q4 preorder willingness", "Frage 4: Vorbestellen"),
    ("q5", "Q5 reason not to use", "Frage 5: Gründe gegen Nutzung"),
    ("q_lunch_time", "Q6 lunch time", "Frage 6: Mittagszeit"),
    ("q_area", "Q7 area", "Frage 7: Arbeits-/Essbereich"),
    ("sources", "Source platform", "Quelle"),
]

FILTER_FIELDS = ["source_platform", "q_area", "q_lunch_time", "q3_price", "q4_preorder"]


class ResponseEntry(db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.Text, nullable=False)
    source_platform = db.Column(db.Text)
    q1_lunch_type = db.Column(db.Text)
    q1_other = db.Column(db.Text)
    q2_problems = db.Column(Text)
    q2_other = db.Column(db.Text)
    q3_price = db.Column(db.Text)
    q4_preorder = db.Column(db.Text)
    q5_reason_not_use = db.Column(db.Text)
    q5_other = db.Column(db.Text)
    q_lunch_time = db.Column(db.Text)
    q_area = db.Column(db.Text)
    comments = db.Column(Text)


class AdminSetting(db.Model):
    __tablename__ = "admin_settings"

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(Text, nullable=False)


def create_app():
    app = Flask(__name__)
    validate_production_config()
    app.config["SECRET_KEY"] = get_secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = is_production()

    db.init_app(app)

    with app.app_context():
        initialize_database()

    register_routes(app)
    return app


def get_database_uri():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return normalize_database_url(database_url)

    data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    return "sqlite:///" + os.path.join(data_dir, "survey.db")


def normalize_database_url(database_url):
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def is_production():
    if os.getenv("LOCAL_DEV", "").lower() in {"1", "true", "yes"}:
        return False
    return os.getenv("APP_ENV", "development").lower() == "production"


def validate_production_config():
    if not is_production():
        return

    missing = []
    if not os.getenv("DATABASE_URL"):
        missing.append("DATABASE_URL")
    elif os.getenv("DATABASE_URL", "").startswith("sqlite"):
        missing.append("non-SQLite DATABASE_URL")
    if not os.getenv("SECRET_KEY"):
        missing.append("SECRET_KEY")
    if not os.getenv("ADMIN_PASSWORD") and not os.getenv("ADMIN_PASSWORD_HASH"):
        missing.append("ADMIN_PASSWORD or ADMIN_PASSWORD_HASH")
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Production configuration missing required environment variable(s): {joined}")


def get_secret_key():
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        return secret_key
    print("WARNING: SECRET_KEY is not set. Using local development fallback only.")
    return DEV_SECRET_KEY


def get_admin_password():
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_password:
        return admin_password
    print("WARNING: ADMIN_PASSWORD is not set. Using local development fallback password only.")
    return DEV_ADMIN_PASSWORD


def initialize_database():
    db.create_all()
    ensure_response_columns()
    initialize_admin_password_hash()


def initialize_admin_password_hash():
    existing = db.session.get(AdminSetting, "admin_password_hash")
    if existing:
        return

    env_hash = os.getenv("ADMIN_PASSWORD_HASH")
    if env_hash:
        password_hash = env_hash
    else:
        password_hash = generate_password_hash(get_admin_password())

    db.session.add(AdminSetting(key="admin_password_hash", value=password_hash))
    db.session.commit()


def ensure_response_columns():
    required_columns = {
        "source_platform": "TEXT",
        "q_lunch_time": "TEXT",
        "q_area": "TEXT",
    }
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns("responses")}
    missing_columns = {
        name: column_type
        for name, column_type in required_columns.items()
        if name not in existing_columns
    }
    if not missing_columns:
        return

    dialect = db.engine.dialect.name
    with db.engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            if dialect == "postgresql":
                connection.execute(text(f"ALTER TABLE responses ADD COLUMN IF NOT EXISTS {column_name} {column_type}"))
            else:
                connection.execute(text(f"ALTER TABLE responses ADD COLUMN {column_name} {column_type}"))


def register_routes(app):
    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            errors = validate_submission(request.form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_survey(form=request.form, status_code=400)

            save_response(request.form)
            return redirect(url_for("thanks"))

        return render_survey(form={}, source_platform=safe_source(request.args.get("source")))

    @app.route("/thanks")
    def thanks():
        return render_template("thanks.html")

    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if session.get("admin_logged_in"):
            return redirect(url_for("admin_export", **request.args))

        if request.method == "POST":
            password = request.form.get("password", "")
            if verify_admin_password(password):
                session["admin_logged_in"] = True
                return redirect(url_for("admin_export"))
            flash("Falsches Passwort.", "error")

        return render_template("admin.html", admin_logged_in=False)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        return redirect(url_for("admin"))

    @app.route("/admin/logout", methods=["POST"])
    @admin_required
    def admin_logout():
        session.pop("admin_logged_in", None)
        return redirect(url_for("admin"))

    @app.route("/admin/export")
    @admin_required
    def admin_export():
        filters = get_filters_from_request()
        rows = query_responses(filters).order_by(ResponseEntry.id.asc()).all()
        latest_responses = list(reversed(rows))[:20]
        stats = load_statistics(rows)
        return render_template(
            "admin.html",
            admin_logged_in=True,
            stats=stats,
            stat_sections=STAT_SECTIONS,
            latest_responses=latest_responses,
            filters=filters,
            filter_options=load_filter_options(),
            export_query=request.query_string.decode("utf-8"),
            allow_clear_data=not is_production(),
        )

    @app.route("/admin/report")
    @admin_required
    def admin_report():
        filters = get_filters_from_request()
        rows = query_responses(filters).order_by(ResponseEntry.id.asc()).all()
        all_total = ResponseEntry.query.count()
        stats = load_statistics(rows)
        report = build_report(rows, stats, all_total, filters)
        return render_template(
            "report.html",
            report=report,
            filters=filters,
            filter_options=load_filter_options(),
            export_query=request.query_string.decode("utf-8"),
        )

    @app.route("/admin/export.csv")
    @admin_required
    def export_csv():
        filters = get_filters_from_request()
        rows = query_responses(filters).order_by(ResponseEntry.id.asc()).all()
        return export_responses_csv(rows)

    @app.route("/admin/export-stats.csv")
    @admin_required
    def export_stats_csv():
        filters = get_filters_from_request()
        rows = query_responses(filters).order_by(ResponseEntry.id.asc()).all()
        return export_statistics_csv(load_statistics(rows))

    @app.route("/admin/change-password", methods=["POST"])
    @admin_required
    def change_admin_password():
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not verify_admin_password(current_password):
            flash("Aktuelles Passwort ist falsch.", "error")
            return redirect(url_for("admin_export"))
        if new_password != confirm_password:
            flash("Neue Passwörter stimmen nicht überein.", "error")
            return redirect(url_for("admin_export"))
        if not is_valid_admin_password(new_password):
            flash("Das neue Passwort muss mindestens 8 Zeichen haben und Buchstaben sowie Zahlen enthalten.", "error")
            return redirect(url_for("admin_export"))

        setting = db.session.get(AdminSetting, "admin_password_hash")
        setting.value = generate_password_hash(new_password)
        db.session.commit()
        flash("Admin-Passwort wurde aktualisiert.", "success")
        return redirect(url_for("admin_export"))

    @app.route("/admin/clear-data", methods=["POST"])
    @admin_required
    def clear_data():
        if is_production():
            flash("Daten löschen ist in Produktion deaktiviert.", "error")
            return redirect(url_for("admin_export"))
        confirmation = request.form.get("confirm_clear")
        if confirmation == "yes":
            db.session.query(ResponseEntry).delete()
            db.session.commit()
            flash("Alle Testdaten wurden gelöscht.", "success")
        else:
            flash("Löschen wurde nicht bestätigt.", "error")
        return redirect(url_for("admin_export"))

    @app.route("/health")
    def health():
        return {"status": "ok"}


def render_survey(form, source_platform=None, status_code=200):
    rendered = render_template(
        "index.html",
        options=ALL_OPTION_SETS,
        form=form,
        source_platform=source_platform if source_platform is not None else safe_source(form.get("source_platform")),
    )
    return rendered, status_code


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin"))
        return view_func(*args, **kwargs)

    return wrapped


def verify_admin_password(password):
    setting = db.session.get(AdminSetting, "admin_password_hash")
    if not setting:
        return password == get_admin_password()
    return check_password_hash(setting.value, password)


def is_valid_admin_password(password):
    if len(password) < 8:
        return False
    has_letter = any(character.isalpha() for character in password)
    has_digit = any(character.isdigit() for character in password)
    return has_letter and has_digit


def validate_submission(form):
    errors = []
    required_fields = {
        "q3_price": Q3_OPTIONS,
        "q4_preorder": Q4_OPTIONS,
        "q5_reason_not_use": Q5_OPTIONS,
    }

    for field_name, options in required_fields.items():
        allowed_values = option_values(options)
        value = form.get(field_name)
        if not value:
            errors.append("Bitte beantworten Sie alle Pflichtfragen. || Please answer all required questions.")
        elif value not in allowed_values:
            errors.append("Ungültige Antwort erkannt. || Invalid answer detected.")

    q1_values = form.getlist("q1_lunch_type")
    allowed_q1_values = option_values(Q1_OPTIONS)
    if not q1_values:
        errors.append("Bitte wählen Sie bei Frage 1 mindestens eine Antwort aus. || Please select at least one answer for question 1.")
    elif any(value not in allowed_q1_values for value in q1_values):
        errors.append("Ungültige Mehrfachauswahl bei Frage 1 erkannt. || Invalid multiple-choice selection detected for question 1.")

    optional_fields = {
        "q_lunch_time": LUNCH_TIME_OPTIONS,
        "q_area": AREA_OPTIONS,
    }
    for field_name, options in optional_fields.items():
        value = form.get(field_name)
        if value and value not in option_values(options):
            errors.append("Ungültige optionale Antwort erkannt. || Invalid optional answer detected.")

    q2_values = form.getlist("q2_problems")
    allowed_q2_values = option_values(Q2_OPTIONS)
    if any(value not in allowed_q2_values for value in q2_values):
        errors.append("Ungültige Mehrfachauswahl erkannt. || Invalid multiple-choice selection detected.")

    return errors


def save_response(form):
    entry = ResponseEntry(
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_platform=safe_source(form.get("source_platform")),
        q1_lunch_type=json.dumps(form.getlist("q1_lunch_type")),
        q1_other=safe_trim(form.get("q1_other")),
        q2_problems=json.dumps(form.getlist("q2_problems")),
        q2_other=safe_trim(form.get("q2_other")),
        q3_price=form.get("q3_price"),
        q4_preorder=form.get("q4_preorder"),
        q5_reason_not_use=form.get("q5_reason_not_use"),
        q5_other=safe_trim(form.get("q5_other")),
        q_lunch_time=empty_to_none(form.get("q_lunch_time")),
        q_area=empty_to_none(form.get("q_area")),
        comments=safe_trim(form.get("comments")),
    )
    db.session.add(entry)
    db.session.commit()


def get_filters_from_request():
    filters = {}
    allowed_values = {
        "q_area": option_values(AREA_OPTIONS),
        "q_lunch_time": option_values(LUNCH_TIME_OPTIONS),
        "q3_price": option_values(Q3_OPTIONS),
        "q4_preorder": option_values(Q4_OPTIONS),
    }
    for field in FILTER_FIELDS:
        value = safe_trim(request.args.get(field), max_length=80)
        if not value:
            continue
        if field in allowed_values and value not in allowed_values[field]:
            continue
        filters[field] = value
    return filters


def query_responses(filters):
    query = ResponseEntry.query
    for field, value in filters.items():
        query = query.filter(getattr(ResponseEntry, field) == value)
    return query


def load_filter_options():
    return {
        "source_platform": distinct_filter_options("source_platform"),
        "q_area": german_options(AREA_OPTIONS),
        "q_lunch_time": german_options(LUNCH_TIME_OPTIONS),
        "q3_price": german_options(Q3_OPTIONS),
        "q4_preorder": german_options(Q4_OPTIONS),
    }


def distinct_filter_options(field_name):
    values = (
        db.session.query(getattr(ResponseEntry, field_name))
        .filter(getattr(ResponseEntry, field_name).isnot(None))
        .distinct()
        .order_by(getattr(ResponseEntry, field_name).asc())
        .all()
    )
    return [(value[0], value[0]) for value in values if value[0]]


def load_statistics(responses):
    total = len(responses)
    stats = {"total": total}
    stats["q1"] = count_multiple_choice(responses, "q1_lunch_type", Q1_OPTIONS, allow_legacy_scalar=True)
    stats["q2"] = count_multiple_choice(responses, "q2_problems", Q2_OPTIONS)
    stats["q3"] = count_single_choice(responses, "q3_price", Q3_OPTIONS)
    stats["q4"] = count_single_choice(responses, "q4_preorder", Q4_OPTIONS)
    stats["q5"] = count_single_choice(responses, "q5_reason_not_use", Q5_OPTIONS)
    stats["q_lunch_time"] = count_single_choice(responses, "q_lunch_time", LUNCH_TIME_OPTIONS)
    stats["q_area"] = count_single_choice(responses, "q_area", AREA_OPTIONS)
    stats["sources"] = count_dynamic_values(responses, "source_platform")
    return stats


def count_single_choice(responses, field_name, options):
    counts = {value: 0 for value, _label in options}
    for response in responses:
        value = getattr(response, field_name, None)
        if value in counts:
            counts[value] += 1
    return format_counts(counts, options, len(responses))


def count_multiple_choice(responses, field_name, options, allow_legacy_scalar=False):
    counts = {value: 0 for value, _label in options}
    for response in responses:
        raw_value = getattr(response, field_name, None)
        try:
            selected_values = json.loads(raw_value or "[]")
        except json.JSONDecodeError:
            selected_values = [raw_value] if allow_legacy_scalar and raw_value else []
        if isinstance(selected_values, str) and allow_legacy_scalar:
            selected_values = [selected_values]
        if not isinstance(selected_values, list):
            selected_values = []
        for value in selected_values:
            if value in counts:
                counts[value] += 1
    return format_counts(counts, options, len(responses))


def count_dynamic_values(responses, field_name):
    counts = {}
    for response in responses:
        value = getattr(response, field_name, None)
        if value:
            counts[value] = counts.get(value, 0) + 1
    total = len(responses)
    return [
        {"label": value, "value": value, "count": count, "percentage": percentage(count, total)}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def format_counts(counts, options, total):
    return [
        {
            "value": value,
            "label": german_label(label),
            "count": counts.get(value, 0),
            "percentage": percentage(counts.get(value, 0), total),
        }
        for value, label in options
    ]


def german_options(options):
    return [(value, german_label(label)) for value, label in options]


def german_label(label):
    return label.split(" || ", 1)[0]


def build_report(rows, stats, all_total, filters):
    positive_count = sum(1 for row in rows if row.q4_preorder in {"yes_definitely", "rather_yes"})
    latest_comments = [row.comments for row in reversed(rows) if row.comments][:10]
    return {
        "all_total": all_total,
        "filtered_total": len(rows),
        "filters_active": bool(filters),
        "top_lunch_types": top_rows(stats["q1"], 3),
        "top_lunch_problems": top_rows(stats["q2"], 3),
        "most_common_price": top_rows(stats["q3"], 1),
        "positive_preorder_percentage": percentage(positive_count, len(rows)),
        "most_common_lunch_time": top_rows(stats["q_lunch_time"], 1),
        "most_common_area": top_rows(stats["q_area"], 1),
        "top_reasons": top_rows(stats["q5"], 3),
        "sources": stats["sources"],
        "latest_comments": latest_comments,
    }


def top_rows(rows, limit):
    return [row for row in sorted(rows, key=lambda item: (-item["count"], item["label"])) if row["count"] > 0][:limit]


def percentage(count, total):
    if total == 0:
        return 0
    return round((count / total) * 100, 1)


def export_responses_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "id",
        "created_at",
        "source_platform",
        "q1_lunch_type",
        "q1_other",
        "q2_problems",
        "q2_other",
        "q3_price",
        "q4_preorder",
        "q5_reason_not_use",
        "q5_other",
        "q_lunch_time",
        "q_area",
        "comments",
    ]
    writer.writerow(headers)
    for row in rows:
        writer.writerow([getattr(row, header, None) for header in headers])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=survey_responses.csv"},
    )


def export_statistics_csv(stats):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "value", "label", "count", "percentage"])
    writer.writerow(["total", "responses", "Total responses", stats["total"], "100" if stats["total"] else "0"])

    for key, section_label, _title in STAT_SECTIONS:
        for row in stats.get(key, []):
            writer.writerow([section_label, row["value"], row["label"], row["count"], row["percentage"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=survey_statistics.csv"},
    )


def option_values(options):
    return {value for value, _label in options}


def safe_source(value):
    value = safe_trim(value, max_length=80)
    if not value:
        return None
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)


def safe_trim(value, max_length=1000):
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return trimmed[:max_length]


def empty_to_none(value):
    return safe_trim(value, max_length=80)


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
