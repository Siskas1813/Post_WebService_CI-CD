from pathlib import Path

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_from_directory, session, url_for

from webmail.security import normalize_attachment, save_attachment_file
from webmail.services.mail_service import MailService

mailbox_bp = Blueprint("mailbox", __name__)


def _service() -> MailService:
    return MailService(current_app.config["DB_PATH"])


def _require_login():
    if "username" not in session:
        return redirect(url_for("auth.login_page", next=request.path))
    return None


@mailbox_bp.app_context_processor
def inject_nav_stats():
    if "username" not in session:
        return {}
    return {"nav_stats": _service().mailbox_stats(session["username"])}


@mailbox_bp.route("/dashboard")
def dashboard():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    folder = request.args.get("folder", "inbox")
    mails = _service().list_mailbox(session["username"], folder)
    stats = _service().mailbox_stats(session["username"])
    profile = _service().profile(session["username"])
    return render_template("dashboard.html", mails=mails, folder=folder, stats=stats, profile=profile, user=session)


@mailbox_bp.route("/search")
def search():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    query = request.args.get("q", "")
    results = _service().search(session["username"], query)
    return render_template("search_results.html", results=results, query=query)


@mailbox_bp.route("/mail/<mail_id>")
def mail_detail(mail_id):
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    mail, attachments = _service().get_mail(mail_id, session["username"], session.get("role", "user"))
    if not mail:
        abort(404)
    return render_template("mail_detail.html", mail=mail, attachments=attachments)


@mailbox_bp.route("/mail/<mail_id>/star")
def star_mail(mail_id):
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    _service().toggle_star(mail_id, session["username"], session.get("role", "user"))
    return redirect(url_for("mailbox.dashboard"))


@mailbox_bp.route("/mail/<mail_id>/move/<folder>")
def move_mail(mail_id, folder):
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    _service().move_mail(mail_id, folder, session["username"], session.get("role", "user"))
    return redirect(url_for("mailbox.dashboard", folder=folder))


@mailbox_bp.route("/compose", methods=["GET", "POST"])
def compose():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    service = _service()
    if request.method == "POST":
        sender = session["username"]
        recipient = request.form.get("recipient", "")
        cc = request.form.get("cc", "")
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        priority = request.form.get("priority", "normal")
        classification = request.form.get("classification", "internal")
        label = request.form.get("label", "")

        service.compose(sender, recipient, cc, subject, body, priority, classification, label)
        service.save_audit(sender, "compose", f"Compose to={recipient}, subject={subject}")
        return redirect(url_for("mailbox.dashboard", folder="sent"))

    return render_template("compose.html", contacts=service.contacts(session["username"]))


@mailbox_bp.route("/contacts", methods=["GET", "POST"])
def contacts():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    service = _service()
    if request.method == "POST":
        service.add_contact(
            session["username"],
            request.form.get("display_name", ""),
            request.form.get("email", ""),
            request.form.get("department", ""),
            request.form.get("trust_level", "external"),
            request.form.get("notes", ""),
        )
        service.save_audit(session["username"], "contact_create", request.form.get("email", ""))
        return redirect(url_for("mailbox.contacts"))

    return render_template("contacts.html", contacts=service.contacts(session["username"]))


@mailbox_bp.route("/rules", methods=["GET", "POST"])
def rules():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    service = _service()
    if request.method == "POST":
        service.add_rule(
            session["username"],
            request.form.get("name", ""),
            request.form.get("expression", ""),
            request.form.get("target_folder", "inbox"),
            request.form.get("enabled", "1"),
        )
        service.save_audit(session["username"], "rule_create", request.form.get("name", ""))
        return redirect(url_for("mailbox.rules"))

    return render_template("rules.html", rules=service.rules(session["username"]))


@mailbox_bp.route("/profile", methods=["GET", "POST"])
def profile():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    service = _service()
    if request.method == "POST":
        service.update_profile(
            session["username"],
            request.form.get("full_name", ""),
            request.form.get("title", ""),
            request.form.get("phone", ""),
            request.form.get("signature", ""),
        )
        session["full_name"] = request.form.get("full_name", "")
        session["title"] = request.form.get("title", "")
        service.save_audit(session["username"], "profile_update", request.form.get("full_name", ""))
        return redirect(url_for("mailbox.profile"))

    return render_template("profile.html", profile=service.profile(session["username"]))


@mailbox_bp.route("/attachments", methods=["GET", "POST"])
def attachments_center():
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    service = _service()
    if request.method == "POST":
        upload = request.files.get("attachment")
        mail_id_raw = request.form.get("mail_id", "1")
        if not upload:
            return "File is required", 400

        try:
            mail_id = int(mail_id_raw)
        except ValueError:
            return "Invalid mail id", 400

        mail, _ = service.get_mail(str(mail_id), session["username"], session.get("role", "user"))
        if not mail:
            abort(403)

        normalized, error = normalize_attachment(upload)
        if error:
            return error, 400

        filename, storage_name, content_type = normalized
        storage_name, size_bytes = save_attachment_file(upload, storage_name)
        service.add_attachment(mail_id, filename, storage_name, session["username"], content_type, size_bytes)

    items = service.attachments_for_user(session["username"], session.get("role", "user"))
    return render_template("attachments_center.html", items=items)


@mailbox_bp.route("/download/<int:attachment_id>")
def download(attachment_id):
    redirect_response = _require_login()
    if redirect_response:
        return redirect_response

    attachment = _service().get_attachment_for_user(attachment_id, session["username"], session.get("role", "user"))
    if not attachment:
        abort(404)

    upload_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    return send_from_directory(upload_dir, attachment["storage_path"], as_attachment=True, download_name=attachment["filename"])
