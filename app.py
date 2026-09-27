"""State Core Technology - admin-controlled website (Flask + SQLAlchemy + Postgres/Supabase).

ARCHITECTURE (rewritten):
  Every page (home, about, services, portfolio, contact, and any new page added later)
  has its OWN template file with its OWN complete, hardcoded HTML/CSS/layout -
  box sizes, positions, number of boxes, everything. Nothing about the LAYOUT of a
  page comes from the database anymore.

  The ONLY thing the database controls is TEXT and IMAGES, through one generic model:
  ContentBlock. Every editable spot on every page - a heading, a paragraph, a card's
  caption, an image inside a box - is one ContentBlock row, looked up by a
  (page, key) pair that the page's own template chooses (e.g. page="home",
  key="hero_heading"). The template calls the `block()` helper (added to every
  template's context below) to read it, and renders its own edit controls (text
  editing, font size/color/family/alignment, image upload, a per-box "Save changes"
  button) around it when `edit_mode` is on. Saving is done through the small generic
  JSON/upload API at the bottom of the admin section: /admin/api/block/save and
  /admin/api/block/image.

  The footer (and header/nav) stay shared, in templates/base.html, since they are the
  same on every page.

  Page objects (Page model) still exist, but only to drive routing, the nav menu and
  publish/hide status - not content or layout.
"""
import os
import re
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from jinja2 import TemplateNotFound
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
    # Raised from 1 MB so an uploaded photo (up to MAX_IMAGE_BYTES below) fits in the request.
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
)
db = SQLAlchemy(app)

# --------------------------------------------------------------------------
# Supabase Storage (image uploads) - same Supabase project the database is on.
# Create a PUBLIC bucket in Supabase (Storage -> New bucket) and set these on Render:
#   SUPABASE_URL            e.g. https://xxxxx.supabase.co
#   SUPABASE_SERVICE_KEY    Settings -> API -> service_role secret (server-side only, never expose it)
#   SUPABASE_BUCKET         bucket name, defaults to "uploads"
# --------------------------------------------------------------------------
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "uploads")
ALLOWED_IMAGE_EXT = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                      "webp": "image/webp", "gif": "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def upload_image_to_supabase(file_storage):
    """Uploads an image file to Supabase Storage. Returns (public_url, None) or (None, error_message)."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        return None, "Image storage isn't configured yet. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."
    name = (file_storage.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXT:
        return None, "Please upload a JPG, PNG, WEBP or GIF image."
    data = file_storage.read()
    if not data:
        return None, "That file is empty."
    if len(data) > MAX_IMAGE_BYTES:
        return None, "Image is too large (max 5 MB)."
    path = "%s.%s" % (uuid.uuid4().hex, ext)
    upload_url = "%s/storage/v1/object/%s/%s" % (SUPABASE_URL, SUPABASE_BUCKET, path)
    req = urllib.request.Request(upload_url, data=data, method="POST", headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": "Bearer " + SUPABASE_SERVICE_KEY,
        "Content-Type": ALLOWED_IMAGE_EXT[ext],
        "x-upsert": "true",
    })
    try:
        urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        return None, "Upload failed: %s" % e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return None, "Upload failed: %s" % str(e)[:200]
    return "%s/storage/v1/object/public/%s/%s" % (SUPABASE_URL, SUPABASE_BUCKET, path), None

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
    """A page in the site's navigation. Only routing/menu/publish metadata lives here -
    the page's actual content and design live entirely in its own template file
    (e.g. templates/home.html), plus whatever ContentBlock rows that template reads."""
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    meta_description = db.Column(db.String(300), default="")
    show_in_nav = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class ContentBlock(db.Model):
    """One admin-editable spot of text and/or image on one page. Identified by
    (page, key) - the page's own template picks the key, e.g. key="hero_heading" or
    key="service_box_1". This is the ONLY thing about a page's content that the
    database controls; box size/position/how-many-boxes is fixed in the page's HTML."""
    __tablename__ = "content_blocks"
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(60), nullable=False, index=True)
    key = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, default="")
    font_size = db.Column(db.String(4), default="")
    font_color = db.Column(db.String(20), default="")
    font_family = db.Column(db.String(20), default="")
    text_align = db.Column(db.String(10), default="")
    image_url = db.Column(db.String(300), default="")
    __table_args__ = (db.UniqueConstraint("page", "key", name="uq_content_block_page_key"),)


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
# Configuration shared by every hardcoded page template
# --------------------------------------------------------------------------

# A small library of inline-SVG icons a page template can drop into its own hardcoded
# markup with {{ 'code'|icon }}. Which icon a box uses is a design choice baked into
# that page's HTML now, not an admin-editable setting.
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

# On-page text editor: every editable text on every page gets the same style choices.
TEXT_SIZES = {"sm": "0.9rem", "md": "", "lg": "1.3rem", "xl": "1.8rem"}
FONT_STACKS = {
    "": "", "display": "'Space Grotesk', system-ui, sans-serif",
    "body": "'Inter', system-ui, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif", "mono": "'Courier New', monospace",
}
SIZE_CHOICES = {"sm": "Small", "md": "Normal", "lg": "Large", "xl": "Extra large"}
FONT_CHOICES = {"": "Default", "display": "Heading style", "body": "Body style", "serif": "Serif", "mono": "Monospace"}
ALIGN_CHOICES = {"left": "Left", "center": "Center", "right": "Right"}

SETTING_DEFAULTS = {
    "site_name": "State Core Technology", "tagline": "Software house, Pakistan", "logo_url": "",
    "meta_description": "State Core Technology designs and builds fast, reliable websites, web apps and digital products for growing businesses.",
    "email": "hello@statecoretechnology.com", "phone": "+92 300 0000000", "address": "Lahore, Pakistan",
    "github": "", "linkedin": "", "instagram": "", "x_twitter": "",
    "header_cta_text": "Start a project", "header_cta_url": "/contact",
    "footer_text": "© {year} State Core Technology. All rights reserved.",
    "brand_color": "#6D5BFF", "accent_color": "#1FE0C4",
}
RESERVED_SLUGS = {"admin", "static", "contact-submit"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# page slugs and content-block keys: lowercase letters/numbers/underscore/hyphen only.
SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,79}$")

# Every known page and the template file that renders it. New pages added later just
# get a new entry here (or, for a slug with no entry, the code below falls back to
# "<slug>.html" automatically) plus their own template file.
PAGE_TEMPLATES = {
    "home": "home.html",
    "about": "about.html",
    "services": "services.html",
    "portfolio": "portfolio.html",
    "contact": "contact.html",
}

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
    """Inline CSS for one ContentBlock's text style choices. Used as {{ blk|stylevars }}."""
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


def get_block(page_slug, key, default_text="", default_image=""):
    """Read one editable text+image block for a hardcoded page. Every page template
    calls this for each spot the admin should be able to edit, e.g.:
        {% set b = block('home', 'hero_heading') %}
        <h1 style="{{ b|stylevars }}">{{ b.text or 'Default headline' }}</h1>
    Reading never writes to the database - only a real Save-changes click
    (/admin/api/block/save or /admin/api/block/image) creates or updates a row, so an
    unsaved block simply falls back to the defaults the template passed in."""
    row = ContentBlock.query.filter_by(page=page_slug, key=key).first()
    if row:
        return row
    return ContentBlock(page=page_slug, key=key, text=default_text, image_url=default_image)


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
                year=datetime.utcnow().year, block=get_block,
                SIZE_CHOICES=SIZE_CHOICES, FONT_CHOICES=FONT_CHOICES, ALIGN_CHOICES=ALIGN_CHOICES,
                is_admin=admin_on, edit_mode=admin_on and bool(session.get("edit_mode")))


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
    template = PAGE_TEMPLATES.get(page.slug, page.slug + ".html")
    try:
        return render_template(template, page=page)
    except TemplateNotFound:
        # The page exists in the database (nav/admin) but its own HTML file hasn't
        # been created yet. Expected while pages are being rebuilt one at a time.
        abort(404)


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
# Admin: dashboard and page list/metadata (title, web address, nav, publish status)
# --------------------------------------------------------------------------


@app.route("/admin")
@login_required
def admin_dashboard():
    counts = dict(pages=Page.query.count(), blocks=ContentBlock.query.count())
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
            flash("Page saved. Its design/content will use a matching template file "
                  "(e.g. templates/%s.html) once that's created." % page.slug, "ok")
            return redirect(url_for("admin_page", pid=page.id))
    return render_template("admin/page_edit.html", page=page)


@app.post("/admin/pages/<int:pid>/delete")
@login_required
def admin_page_delete(pid):
    page = db.get_or_404(Page, pid)
    if page.slug == "home":
        flash("The home page can't be deleted.", "error")
        return redirect(url_for("admin_pages"))
    db.session.delete(page)
    db.session.commit()
    flash("Page deleted.", "ok")
    return redirect(url_for("admin_pages"))


@app.post("/admin/pages/<int:pid>/move/<direction>")
@login_required
def admin_page_move(pid, direction):
    move(Page.query.all(), db.get_or_404(Page, pid), direction)
    return redirect(url_for("admin_pages"))


@app.get("/admin/api/pages")
@admin_json_required
def api_pages_list():
    pages = Page.query.order_by(Page.sort_order).all()
    return jsonify(ok=True, pages=[{
        "id": p.id, "title": p.title, "slug": p.slug,
        "is_published": p.is_published, "show_in_nav": p.show_in_nav,
    } for p in pages])


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


@app.post("/admin/api/page/<int:pid>/update")
@admin_json_required
def api_page_update(pid):
    page = db.get_or_404(Page, pid)
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:120]
    slug = clean_slug(data.get("slug") or title)
    if not title or not slug:
        return jsonify(ok=False, error="A page needs a title and a web address."), 400
    if slug in RESERVED_SLUGS:
        return jsonify(ok=False, error="That web address is reserved. Pick another."), 400
    clash = Page.query.filter_by(slug=slug).first()
    if clash and clash.id != page.id:
        return jsonify(ok=False, error="Another page already uses that web address."), 400
    page.title, page.slug = title, slug
    page.meta_description = (data.get("meta_description") or "").strip()[:300]
    page.show_in_nav = bool(data.get("show_in_nav"))
    page.is_published = bool(data.get("is_published"))
    db.session.commit()
    return jsonify(ok=True)


@app.post("/admin/api/page/<int:pid>/delete")
@admin_json_required
def api_page_delete_json(pid):
    page = db.get_or_404(Page, pid)
    if page.slug == "home":
        return jsonify(ok=False, error="The home page can't be deleted."), 400
    db.session.delete(page)
    db.session.commit()
    return jsonify(ok=True)

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
# On-page editor ("edit mode"): toggle
# --------------------------------------------------------------------------


@app.post("/admin/edit-mode/<state>")
@login_required
def admin_edit_mode(state):
    session["edit_mode"] = (state == "on")
    return redirect(request.form.get("next") or url_for("home"))

# --------------------------------------------------------------------------
# Generic content-block API: every editable text/image on every hardcoded page goes
# through these three endpoints, identified by (page, key). One box's "Save changes"
# button fires /block/save (text + style) and, if the image was changed, /block/image
# (multipart upload) together - both from the one click.
# --------------------------------------------------------------------------


def _valid_page_key(page_slug, key):
    return bool(SAFE_KEY_RE.match(page_slug or "") and SAFE_KEY_RE.match(key or ""))


def _get_or_create_block(page_slug, key):
    row = ContentBlock.query.filter_by(page=page_slug, key=key).first()
    if not row:
        row = ContentBlock(page=page_slug, key=key)
        db.session.add(row)
    return row


@app.post("/admin/api/block/save")
@admin_json_required
def api_block_save():
    """Save a block's text and text style (size, color, font, alignment) in one go."""
    data = request.get_json(silent=True) or {}
    page_slug, key = (data.get("page") or "").strip().lower(), (data.get("key") or "").strip().lower()
    if not _valid_page_key(page_slug, key):
        return jsonify(ok=False, error="Invalid page or key."), 400
    row = _get_or_create_block(page_slug, key)
    row.text = (data.get("text") or "").strip()[:5000]
    row.font_size = data.get("font_size") if data.get("font_size") in TEXT_SIZES else ""
    row.font_family = data.get("font_family") if data.get("font_family") in FONT_STACKS else ""
    row.text_align = data.get("text_align") if data.get("text_align") in ALIGN_CHOICES else ""
    color = (data.get("font_color") or "").strip()
    row.font_color = color if HEX_RE.match(color) else ""
    db.session.commit()
    return jsonify(ok=True, style=style_attr(row))


@app.post("/admin/api/block/image")
@admin_json_required
def api_block_image_upload():
    """Upload/replace a block's image straight from the admin's device.
    multipart/form-data fields: page, key, file."""
    page_slug = (request.form.get("page") or "").strip().lower()
    key = (request.form.get("key") or "").strip().lower()
    if not _valid_page_key(page_slug, key):
        return jsonify(ok=False, error="Invalid page or key."), 400
    file = request.files.get("file")
    if not file:
        return jsonify(ok=False, error="No file received."), 400
    url, err = upload_image_to_supabase(file)
    if err:
        return jsonify(ok=False, error=err), 400
    row = _get_or_create_block(page_slug, key)
    row.image_url = url
    db.session.commit()
    return jsonify(ok=True, url=url)


@app.post("/admin/api/block/image/delete")
@admin_json_required
def api_block_image_delete():
    data = request.get_json(silent=True) or {}
    page_slug, key = (data.get("page") or "").strip().lower(), (data.get("key") or "").strip().lower()
    if not _valid_page_key(page_slug, key):
        return jsonify(ok=False, error="Invalid page or key."), 400
    row = ContentBlock.query.filter_by(page=page_slug, key=key).first()
    if row:
        row.image_url = ""
        db.session.commit()
    return jsonify(ok=True)

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


# Columns to add, non-destructively, to a table that already exists in an already
# deployed database but is missing a column a newer version of the app introduced.
# Empty for now since content_blocks is a brand-new table (created fresh by
# db.create_all()) - add entries here later the same way if new columns are needed.
NEW_COLUMNS = {}


def ensure_columns():
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
            seed(db, Page, Setting)


try:
    init_db()
except Exception as exc:  # keep the app importable so the error is visible in logs
    print("DATABASE SETUP FAILED:", exc)

if __name__ == "__main__":
    app.run(debug=True)
