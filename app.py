"""FuTuRe FLoW - admin-controlled website (Flask + SQLAlchemy + Postgres/Supabase)."""
import os
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup, escape
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
db_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
if db_url.startswith("postgres://"):
    db_url = "postgresql://" + db_url[len("postgres://"):]
ON_RENDER = bool(os.environ.get("RENDER"))
app.config.update(
    SQLALCHEMY_DATABASE_URI=db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=ON_RENDER,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=1024 * 1024,
)
db = SQLAlchemy(app)

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)


class Page(db.Model):
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    meta_description = db.Column(db.String(300), default="")
    show_in_nav = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    sections = db.relationship("Section", backref="page", cascade="all, delete-orphan",
                               order_by="Section.sort_order")


class Section(db.Model):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("pages.id"), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    style = db.Column(db.String(10), default="light")
    heading = db.Column(db.String(300), default="")
    subheading = db.Column(db.String(300), default="")
    body = db.Column(db.Text, default="")
    button_text = db.Column(db.String(300), default="")
    button_url = db.Column(db.String(300), default="")
    button2_text = db.Column(db.String(300), default="")
    button2_url = db.Column(db.String(300), default="")
    image_url = db.Column(db.String(300), default="")
    image_width = db.Column(db.String(4), default="100")
    font_size = db.Column(db.String(4), default="")
    font_color = db.Column(db.String(20), default="")
    font_family = db.Column(db.String(20), default="")
    text_align = db.Column(db.String(10), default="")
    is_visible = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    boxes = db.relationship("Box", backref="section", cascade="all, delete-orphan",
                            order_by="Box.sort_order")


class Box(db.Model):
    __tablename__ = "boxes"
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    icon = db.Column(db.String(300), default="")
    title = db.Column(db.String(300), default="")
    text = db.Column(db.Text, default="")
    image_url = db.Column(db.String(300), default="")
    image_width = db.Column(db.String(4), default="100")
    tag = db.Column(db.String(300), default="")
    link_text = db.Column(db.String(300), default="")
    link_url = db.Column(db.String(300), default="")
    font_size = db.Column(db.String(4), default="")
    font_color = db.Column(db.String(20), default="")
    font_family = db.Column(db.String(20), default="")
    text_align = db.Column(db.String(10), default="")
    is_visible = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, default="")


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(200))
    subject = db.Column(db.String(200), default="")
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


# --------------------------------------------------------------------------
# Configuration of what the admin can build
# --------------------------------------------------------------------------

ICONS = {
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "design": '<path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.6 7.6"/><circle cx="11" cy="11" r="2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.7-4 3-9 3s-9-1.3-9-3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/>',
    "speed": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "mobile": '<rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "cart": '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
    "mail": '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
}

FIELD_LABELS = {
    "heading": "Heading", "subheading": "Sub-heading", "body": "Body text",
    "button_text": "Button text", "button_url": "Button link",
    "button2_text": "Second button text", "button2_url": "Second button link",
    "image_url": "Image link",
}

SECTION_TYPES = {
    "hero": {"label": "Hero (top banner)",
             "fields": ["heading", "subheading", "button_text", "button_url", "button2_text", "button2_url", "image_url"],
             "box_fields": ["title"], "box_name": "tech chip", "labels": {"title": "Name"},
             "defaults": {"heading": "Your headline goes here", "subheading": "One or two sentences about what you do.", "style": "light"}},
    "cards": {"label": "Cards (services, features)",
              "fields": ["heading", "subheading"],
              "box_fields": ["icon", "title", "text", "link_text", "link_url"], "box_name": "card", "labels": {},
              "defaults": {"heading": "What we do", "style": "light"}},
    "text": {"label": "Text and image",
             "fields": ["heading", "subheading", "body", "image_url", "button_text", "button_url"],
             "box_fields": [], "box_name": "", "labels": {},
             "defaults": {"heading": "About us", "body": "Write your text here.", "style": "tint"}},
    "stats": {"label": "Numbers strip",
              "fields": ["heading"], "box_fields": ["title", "text"], "box_name": "number",
              "labels": {"title": "Number (e.g. 40+)", "text": "Label"},
              "defaults": {"style": "dark"}},
    "process": {"label": "Steps (a process in order)",
                "fields": ["heading", "subheading"], "box_fields": ["title", "text"], "box_name": "step", "labels": {},
                "defaults": {"heading": "How a project runs", "style": "light"}},
    "portfolio": {"label": "Portfolio / projects",
                  "fields": ["heading", "subheading", "button_text", "button_url"],
                  "box_fields": ["image_url", "title", "text", "tag", "link_text", "link_url"], "box_name": "project",
                  "labels": {"tag": "Category label"},
                  "defaults": {"heading": "Recent work", "style": "tint"}},
    "testimonials": {"label": "Testimonials",
                     "fields": ["heading"], "box_fields": ["text", "title", "tag"], "box_name": "testimonial",
                     "labels": {"text": "Quote", "title": "Person's name", "tag": "Role / company"},
                     "defaults": {"heading": "What clients say", "style": "light"}},
    "faq": {"label": "FAQ",
            "fields": ["heading", "subheading"], "box_fields": ["title", "text"], "box_name": "question",
            "labels": {"title": "Question", "text": "Answer"},
            "defaults": {"heading": "Common questions", "style": "light"}},
    "cta": {"label": "Call to action banner",
            "fields": ["heading", "subheading", "button_text", "button_url"],
            "box_fields": [], "box_name": "", "labels": {},
            "defaults": {"heading": "Ready to start?", "button_text": "Get in touch", "button_url": "/contact", "style": "light"}},
    "contact": {"label": "Contact form",
                "fields": ["heading", "subheading", "body"], "box_fields": [], "box_name": "", "labels": {"body": "Text next to the form"},
                "defaults": {"heading": "Tell us about your project", "style": "light"}},
}
BOX_LABELS = {"icon": "Icon", "title": "Title", "text": "Text", "image_url": "Image link",
              "tag": "Label", "link_text": "Link text", "link_url": "Link address"}
LONG_FIELDS = {"body", "text"}

# On-page editor: text style and image-width choices
TEXT_SIZES = {"sm": "0.9rem", "md": "", "lg": "1.3rem", "xl": "1.8rem"}
FONT_STACKS = {
    "": "", "display": "'Bricolage Grotesque', system-ui, sans-serif",
    "body": "'Instrument Sans', system-ui, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif", "mono": "'Courier New', monospace",
}
SIZE_CHOICES = {"sm": "Small", "md": "Normal", "lg": "Large", "xl": "Extra large"}
FONT_CHOICES = {"": "Default", "display": "Heading style", "body": "Body style", "serif": "Serif", "mono": "Monospace"}
ALIGN_CHOICES = {"left": "Left", "center": "Center", "right": "Right"}
WIDTH_CHOICES = ("25", "50", "75", "100")

SETTING_DEFAULTS = {
    "site_name": "FuTuRe FLoW", "tagline": "Web development studio", "logo_url": "",
    "meta_description": "We design, build and host fast websites and web apps for growing businesses.",
    "email": "hello@example.com", "phone": "+00 000 0000000", "address": "Your city, Country",
    "github": "", "linkedin": "", "instagram": "", "x_twitter": "",
    "header_cta_text": "Start a project", "header_cta_url": "/contact",
    "footer_text": "© {year} FuTuRe FLoW. All rights reserved.",
    "brand_color": "#4B3BFF", "accent_color": "#FFCE3A",
}
RESERVED_SLUGS = {"admin", "static", "contact-submit"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# --------------------------------------------------------------------------
# Helpers, filters, security
# --------------------------------------------------------------------------


def get_settings():
    data = dict(SETTING_DEFAULTS)
    for s in Setting.query.all():
        data[s.key] = s.value or ""
    return data


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        if request.is_json:
            sent = (request.get_json(silent=True) or {}).get("csrf_token", "")
        else:
            sent = request.form.get("csrf_token", "")
        if not session.get("_csrf") or not secrets.compare_digest(session["_csrf"], sent):
            abort(400)


@app.after_request
def security_headers(resp):
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/admin"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(400)
def bad_request(_e):
    return "Your session expired. Go back, refresh the page and try again.", 400


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.template_filter("paragraphs")
def paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return Markup("".join("<p>%s</p>" % str(escape(p)).replace("\n", "<br>") for p in parts))


@app.template_filter("safe_url")
def safe_url(url):
    url = (url or "").strip()
    if url and not url.startswith("//") and re.match(r"^(https?://|mailto:|tel:|/|#)", url, re.I):
        return url
    return "#"


@app.template_filter("icon")
def icon(name):
    name = (name or "").strip()
    if name in ICONS:
        return Markup('<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
                      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % ICONS[name])
    return escape(name[:4])


@app.template_filter("hue")
def hue(text):
    return sum(ord(c) for c in (text or "x")) % 360


def style_attr(obj):
    parts = []
    if getattr(obj, "font_size", "") in TEXT_SIZES and TEXT_SIZES.get(obj.font_size):
        parts.append("font-size:%s" % TEXT_SIZES[obj.font_size])
    if FONT_STACKS.get(getattr(obj, "font_family", "")):
        parts.append("font-family:%s" % FONT_STACKS[obj.font_family])
    if getattr(obj, "font_color", ""):
        parts.append("color:%s" % obj.font_color)
    if getattr(obj, "text_align", ""):
        parts.append("text-align:%s" % obj.text_align)
    return "; ".join(parts)


@app.template_filter("stylevars")
def stylevars(obj):
    return style_attr(obj)


@app.context_processor
def inject():
    try:
        site = get_settings()
        nav = Page.query.filter_by(is_published=True, show_in_nav=True).order_by(Page.sort_order).all()
        unread = Message.query.filter_by(is_read=False).count() if session.get("admin_id") else 0
    except Exception:  # database not reachable yet
        site, nav, unread = dict(SETTING_DEFAULTS), [], 0
    admin_on = bool(session.get("admin_id"))
    return dict(site=site, nav_pages=nav, unread=unread, csrf_token=csrf_token,
                year=datetime.utcnow().year, ICON_NAMES=list(ICONS), SECTION_TYPES=SECTION_TYPES,
                FIELD_LABELS=FIELD_LABELS, BOX_LABELS=BOX_LABELS, LONG_FIELDS=LONG_FIELDS,
                is_admin=admin_on, edit_mode=admin_on and bool(session.get("edit_mode")),
                SIZE_CHOICES=SIZE_CHOICES, FONT_CHOICES=FONT_CHOICES, ALIGN_CHOICES=ALIGN_CHOICES,
                WIDTH_CHOICES=WIDTH_CHOICES)


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return fn(*a, **kw)
    return wrapper


def admin_json_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("admin_id"):
            return jsonify(ok=False, error="Not logged in."), 401
        return fn(*a, **kw)
    return wrapper


def clean_slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60]


def set_fields(obj, names):
    for n in names:
        limit = 5000 if n in LONG_FIELDS else 300
        setattr(obj, n, (request.form.get(n) or "").strip()[:limit])


def next_order(model, **flt):
    m = db.session.query(db.func.max(model.sort_order)).filter_by(**flt).scalar()
    return 0 if m is None else m + 1


def move(items, obj, direction):
    items = sorted(items, key=lambda x: x.sort_order or 0)
    for i, it in enumerate(items):
        it.sort_order = i
    i = items.index(obj)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(items):
        items[i].sort_order, items[j].sort_order = items[j].sort_order, items[i].sort_order
    db.session.commit()

# --------------------------------------------------------------------------
# Public site
# --------------------------------------------------------------------------


def render_page(page):
    if not page or (not page.is_published and not session.get("admin_id")):
        abort(404)
    edit_on = session.get("admin_id") and session.get("edit_mode")
    sections = list(page.sections) if edit_on else [s for s in page.sections if s.is_visible]
    return render_template("page.html", page=page, sections=sections)


@app.route("/")
def home():
    page = (Page.query.filter_by(slug="home").first()
            or Page.query.filter_by(is_published=True).order_by(Page.sort_order).first())
    return render_page(page)


@app.route("/<slug>")
def page_view(slug):
    if slug == "home":
        return redirect("/")
    return render_page(Page.query.filter_by(slug=slug).first())


@app.post("/contact-submit")
def contact_submit():
    f = request.form
    slug = clean_slug(f.get("slug")) or "home"
    back = "/" if slug == "home" else "/" + slug
    if f.get("website"):  # honeypot for bots
        return redirect(back)
    name, email = (f.get("name") or "").strip()[:120], (f.get("email") or "").strip()[:200]
    subject, body = (f.get("subject") or "").strip()[:200], (f.get("message") or "").strip()[:5000]
    last = session.get("last_msg", 0)
    now = datetime.utcnow().timestamp()
    if not (name and EMAIL_RE.match(email) and body):
        flash("Please enter your name, a valid email address and a message.", "error")
    elif now - last < 20:
        flash("Please wait a few seconds before sending another message.", "error")
    else:
        db.session.add(Message(name=name, email=email, subject=subject, body=body))
        db.session.commit()
        session["last_msg"] = now
        flash("Thanks. We received your message and will reply by email.", "ok")
    return redirect(back + "#contact")

# --------------------------------------------------------------------------
# Admin: auth
# --------------------------------------------------------------------------


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        user = AdminUser.query.filter_by(username=(request.form.get("username") or "").strip()).first()
        now = datetime.utcnow()
        if user and user.locked_until and user.locked_until > now:
            flash("Too many failed attempts. Try again in 15 minutes.", "error")
        elif user and check_password_hash(user.password_hash, request.form.get("password") or ""):
            user.failed_attempts, user.locked_until = 0, None
            db.session.commit()
            session.clear()
            session["admin_id"] = user.id
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        else:
            if user:
                user.failed_attempts = (user.failed_attempts or 0) + 1
                if user.failed_attempts >= 5:
                    user.locked_until, user.failed_attempts = now + timedelta(minutes=15), 0
                db.session.commit()
            flash("Wrong username or password.", "error")
    return render_template("admin/login.html")


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/password", methods=["GET", "POST"])
@login_required
def admin_password():
    user = db.session.get(AdminUser, session["admin_id"])
    if request.method == "POST":
        new = request.form.get("new_password") or ""
        if not check_password_hash(user.password_hash, request.form.get("current_password") or ""):
            flash("Current password is wrong.", "error")
        elif len(new) < 10:
            flash("New password must be at least 10 characters.", "error")
        elif new != request.form.get("confirm_password"):
            flash("The two new passwords do not match.", "error")
        else:
            user.password_hash = generate_password_hash(new)
            db.session.commit()
            flash("Password changed.", "ok")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/password.html")

# --------------------------------------------------------------------------
# Admin: dashboard, pages, sections, boxes
# --------------------------------------------------------------------------


@app.route("/admin")
@login_required
def admin_dashboard():
    counts = dict(pages=Page.query.count(), sections=Section.query.count(), boxes=Box.query.count())
    return render_template("admin/dashboard.html", counts=counts)


@app.route("/admin/pages")
@login_required
def admin_pages():
    return render_template("admin/pages.html", pages=Page.query.order_by(Page.sort_order).all())


@app.route("/admin/pages/new", methods=["GET", "POST"])
@app.route("/admin/pages/<int:pid>", methods=["GET", "POST"])
@login_required
def admin_page(pid=None):
    page = db.get_or_404(Page, pid) if pid else None
    if request.method == "POST":
        slug = clean_slug(request.form.get("slug") or request.form.get("title"))
        title = (request.form.get("title") or "").strip()[:120]
        clash = Page.query.filter_by(slug=slug).first()
        if not title or not slug:
            flash("A page needs a title and a web address.", "error")
        elif slug in RESERVED_SLUGS:
            flash("That web address is reserved. Pick another.", "error")
        elif clash and (not page or clash.id != page.id):
            flash("Another page already uses that web address.", "error")
        else:
            if not page:
                page = Page(sort_order=next_order(Page))
                db.session.add(page)
            page.title, page.slug = title, slug
            page.meta_description = (request.form.get("meta_description") or "").strip()[:300]
            page.show_in_nav = request.form.get("show_in_nav") == "on"
            page.is_published = request.form.get("is_published") == "on"
            db.session.commit()
            flash("Page saved.", "ok")
            return redirect(url_for("admin_page", pid=page.id))
    return render_template("admin/page_edit.html", page=page)


@app.post("/admin/pages/<int:pid>/delete")
@login_required
def admin_page_delete(pid):
    db.session.delete(db.get_or_404(Page, pid))
    db.session.commit()
    flash("Page deleted.", "ok")
    return redirect(url_for("admin_pages"))


@app.post("/admin/pages/<int:pid>/move/<direction>")
@login_required
def admin_page_move(pid, direction):
    move(Page.query.all(), db.get_or_404(Page, pid), direction)
    return redirect(url_for("admin_pages"))


@app.post("/admin/pages/<int:pid>/sections/add")
@login_required
def admin_section_add(pid):
    page = db.get_or_404(Page, pid)
    stype = request.form.get("type")
    if stype not in SECTION_TYPES:
        abort(400)
    d = SECTION_TYPES[stype]["defaults"]
    sec = Section(page_id=page.id, type=stype, sort_order=next_order(Section, page_id=page.id),
                  **{k: v for k, v in d.items()})
    db.session.add(sec)
    db.session.commit()
    flash("Section added. Fill it in below.", "ok")
    return redirect(url_for("admin_section", sid=sec.id))


@app.route("/admin/sections/<int:sid>", methods=["GET", "POST"])
@login_required
def admin_section(sid):
    sec = db.get_or_404(Section, sid)
    cfg = SECTION_TYPES[sec.type]
    if request.method == "POST":
        set_fields(sec, cfg["fields"])
        style = request.form.get("style")
        sec.style = style if style in ("light", "tint", "dark") else "light"
        sec.is_visible = request.form.get("is_visible") == "on"
        db.session.commit()
        flash("Section saved.", "ok")
        return redirect(url_for("admin_section", sid=sec.id))
    return render_template("admin/section_edit.html", sec=sec, cfg=cfg)


@app.post("/admin/sections/<int:sid>/delete")
@login_required
def admin_section_delete(sid):
    sec = db.get_or_404(Section, sid)
    pid = sec.page_id
    db.session.delete(sec)
    db.session.commit()
    flash("Section deleted.", "ok")
    return redirect(url_for("admin_page", pid=pid))


@app.post("/admin/sections/<int:sid>/move/<direction>")
@login_required
def admin_section_move(sid, direction):
    sec = db.get_or_404(Section, sid)
    move(list(sec.page.sections), sec, direction)
    return redirect(url_for("admin_page", pid=sec.page_id))


@app.post("/admin/sections/<int:sid>/toggle")
@login_required
def admin_section_toggle(sid):
    sec = db.get_or_404(Section, sid)
    sec.is_visible = not sec.is_visible
    db.session.commit()
    return redirect(url_for("admin_page", pid=sec.page_id))


@app.route("/admin/sections/<int:sid>/boxes/new", methods=["GET", "POST"])
@app.route("/admin/boxes/<int:bid>", methods=["GET", "POST"])
@login_required
def admin_box(sid=None, bid=None):
    box = db.get_or_404(Box, bid) if bid else None
    sec = box.section if box else db.get_or_404(Section, sid)
    cfg = SECTION_TYPES[sec.type]
    if not cfg["box_fields"]:
        abort(404)
    if request.method == "POST":
        if not box:
            box = Box(section_id=sec.id, sort_order=next_order(Box, section_id=sec.id))
            db.session.add(box)
        set_fields(box, cfg["box_fields"])
        box.is_visible = request.form.get("is_visible") == "on"
        db.session.commit()
        flash("Saved.", "ok")
        return redirect(url_for("admin_section", sid=sec.id))
    return render_template("admin/box_edit.html", box=box, sec=sec, cfg=cfg)


@app.post("/admin/boxes/<int:bid>/delete")
@login_required
def admin_box_delete(bid):
    box = db.get_or_404(Box, bid)
    sid = box.section_id
    db.session.delete(box)
    db.session.commit()
    flash("Deleted.", "ok")
    return redirect(url_for("admin_section", sid=sid))


@app.post("/admin/boxes/<int:bid>/move/<direction>")
@login_required
def admin_box_move(bid, direction):
    box = db.get_or_404(Box, bid)
    move(list(box.section.boxes), box, direction)
    return redirect(url_for("admin_section", sid=box.section_id))


@app.post("/admin/boxes/<int:bid>/toggle")
@login_required
def admin_box_toggle(bid):
    box = db.get_or_404(Box, bid)
    box.is_visible = not box.is_visible
    db.session.commit()
    return redirect(url_for("admin_section", sid=box.section_id))

# --------------------------------------------------------------------------
# On-page editor ("edit mode"): toggle, and small JSON API used by edit.js
# --------------------------------------------------------------------------


@app.post("/admin/edit-mode/<state>")
@login_required
def admin_edit_mode(state):
    session["edit_mode"] = (state == "on")
    return redirect(request.form.get("next") or url_for("home"))


def _kind_obj(kind, obj_id):
    model = {"section": Section, "box": Box}.get(kind)
    if not model:
        abort(400)
    return model, db.get_or_404(model, obj_id)


@app.post("/admin/api/text")
@admin_json_required
def api_text():
    data = request.get_json(silent=True) or {}
    _model, obj = _kind_obj(data.get("kind"), data.get("id"))
    cfg = SECTION_TYPES[obj.type if data.get("kind") == "section" else obj.section.type]
    allowed = cfg["fields"] if data.get("kind") == "section" else cfg["box_fields"]
    field = data.get("field")
    if field not in allowed:
        return jsonify(ok=False, error="That field can't be edited."), 400
    limit = 5000 if field in LONG_FIELDS else 300
    setattr(obj, field, (data.get("value") or "").strip()[:limit])
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/style")
@admin_json_required
def api_style():
    data = request.get_json(silent=True) or {}
    _model, obj = _kind_obj(data.get("kind"), data.get("id"))
    obj.font_size = data.get("font_size") if data.get("font_size") in TEXT_SIZES else ""
    obj.font_family = data.get("font_family") if data.get("font_family") in FONT_STACKS else ""
    obj.text_align = data.get("text_align") if data.get("text_align") in ALIGN_CHOICES else ""
    color = (data.get("font_color") or "").strip()
    obj.font_color = color if HEX_RE.match(color) else ""
    db.session.commit()
    return jsonify(ok=True, style=style_attr(obj))


@app.post("/admin/api/image")
@admin_json_required
def api_image():
    data = request.get_json(silent=True) or {}
    _model, obj = _kind_obj(data.get("kind"), data.get("id"))
    obj.image_url = (data.get("url") or "").strip()[:300]
    width = str(data.get("width") or "100")
    obj.image_width = width if width in WIDTH_CHOICES else "100"
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/visibility")
@admin_json_required
def api_visibility():
    data = request.get_json(silent=True) or {}
    _model, obj = _kind_obj(data.get("kind"), data.get("id"))
    obj.is_visible = bool(data.get("visible"))
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/reorder")
@admin_json_required
def api_reorder():
    data = request.get_json(silent=True) or {}
    model, ids = {"section": Section, "box": Box}.get(data.get("kind")), data.get("ids") or []
    if not model or not isinstance(ids, list) or not ids:
        abort(400)
    objs = {o.id: o for o in model.query.filter(model.id.in_(ids)).all()}
    parent_attr = "page_id" if model is Section else "section_id"
    if len(objs) != len(ids) or len({getattr(o, parent_attr) for o in objs.values()}) != 1:
        abort(400)
    for i, oid in enumerate(ids):
        objs[oid].sort_order = i
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/section/add")
@admin_json_required
def api_section_add():
    data = request.get_json(silent=True) or {}
    page = db.get_or_404(Page, data.get("page_id"))
    stype = data.get("type")
    if stype not in SECTION_TYPES:
        abort(400)
    sec = Section(page_id=page.id, type=stype, sort_order=next_order(Section, page_id=page.id),
                  **SECTION_TYPES[stype]["defaults"])
    db.session.add(sec)
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/section/<int:sid>/delete")
@admin_json_required
def api_section_delete(sid):
    db.session.delete(db.get_or_404(Section, sid))
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/box/add")
@admin_json_required
def api_box_add():
    data = request.get_json(silent=True) or {}
    sec = db.get_or_404(Section, data.get("section_id"))
    if not SECTION_TYPES[sec.type]["box_fields"]:
        abort(400)
    db.session.add(Box(section_id=sec.id, sort_order=next_order(Box, section_id=sec.id)))
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/box/<int:bid>/delete")
@admin_json_required
def api_box_delete(bid):
    db.session.delete(db.get_or_404(Box, bid))
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/page/add")
@admin_json_required
def api_page_add():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:120]
    slug = clean_slug(title)
    if not title or not slug:
        return jsonify(ok=False, error="Page needs a title."), 400
    if slug in RESERVED_SLUGS or Page.query.filter_by(slug=slug).first():
        return jsonify(ok=False, error="That page name is already used. Try a different title."), 400
    page = Page(title=title, slug=slug, sort_order=next_order(Page))
    db.session.add(page)
    db.session.commit()
    session["edit_mode"] = True
    return jsonify(ok=True, url=("/" if slug == "home" else "/" + slug))

# --------------------------------------------------------------------------
# Admin: settings and messages
# --------------------------------------------------------------------------


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    is_ajax = request.headers.get("X-Requested-With") == "fetch"
    if request.method == "POST":
        for key, default in SETTING_DEFAULTS.items():
            val = (request.form.get(key) or "").strip()[:300]
            if key in ("brand_color", "accent_color") and not HEX_RE.match(val):
                val = default
            row = db.session.get(Setting, key) or Setting(key=key)
            row.value = val
            db.session.add(row)
        db.session.commit()
        if is_ajax:
            return jsonify(ok=True)
        flash("Settings saved.", "ok")
        return redirect(url_for("admin_settings"))
    if is_ajax:
        return render_template("admin/_settings_fields.html", values=get_settings())
    return render_template("admin/settings.html", values=get_settings())


@app.route("/admin/messages")
@login_required
def admin_messages():
    return render_template("admin/messages.html", messages=Message.query.order_by(Message.created_at.desc()).all())


@app.post("/admin/messages/<int:mid>/<action>")
@login_required
def admin_message_action(mid, action):
    msg = db.get_or_404(Message, mid)
    if action == "delete":
        db.session.delete(msg)
    elif action == "read":
        msg.is_read = True
    else:
        abort(400)
    db.session.commit()
    return redirect(url_for("admin_messages"))

# --------------------------------------------------------------------------
# First-run setup: tables, first admin, sample content
# --------------------------------------------------------------------------


def ensure_admin():
    if AdminUser.query.count():
        return
    user, pw = os.environ.get("ADMIN_USERNAME"), os.environ.get("ADMIN_PASSWORD")
    if user and pw:
        db.session.add(AdminUser(username=user, password_hash=generate_password_hash(pw)))
    elif not ON_RENDER:
        db.session.add(AdminUser(username="admin", password_hash=generate_password_hash("change-me-now")))
        print("Local dev admin created: admin / change-me-now")
    else:
        print("WARNING: set ADMIN_USERNAME and ADMIN_PASSWORD env vars to create the first admin.")
    db.session.commit()


NEW_COLUMNS = {
    "sections": [("image_width", "VARCHAR(4) DEFAULT '100'"), ("font_size", "VARCHAR(4) DEFAULT ''"),
                 ("font_color", "VARCHAR(20) DEFAULT ''"), ("font_family", "VARCHAR(20) DEFAULT ''"),
                 ("text_align", "VARCHAR(10) DEFAULT ''")],
    "boxes": [("image_width", "VARCHAR(4) DEFAULT '100'"), ("font_size", "VARCHAR(4) DEFAULT ''"),
              ("font_color", "VARCHAR(20) DEFAULT ''"), ("font_family", "VARCHAR(20) DEFAULT ''"),
              ("text_align", "VARCHAR(10) DEFAULT ''")],
}


def ensure_columns():
    """db.create_all() only creates missing TABLES, never new columns on tables that
    already exist. This adds any columns a newer version of the app introduced, so an
    already-deployed database (e.g. on Supabase) stays in sync without losing data."""
    insp = inspect(db.engine)
    for table, columns in NEW_COLUMNS.items():
        if table not in insp.get_table_names():
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in columns:
            if name not in existing:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        ensure_columns()
        ensure_admin()
        if Page.query.count() == 0:
            from seed_data import seed
            seed(db, Page, Section, Box, Setting)


try:
    init_db()
except Exception as exc:  # keep the app importable so the error is visible in logs
    print("DATABASE SETUP FAILED:", exc)

if __name__ == "__main__":
    app.run(debug=True)
