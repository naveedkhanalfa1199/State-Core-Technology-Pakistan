"""Sample content, inserted once when the database is empty. Everything here is editable from /admin."""


def seed(db, Page, Section, Box, Setting):
    def page(slug, title, order, desc, nav=True):
        p = Page(slug=slug, title=title, sort_order=order, meta_description=desc, show_in_nav=nav)
        db.session.add(p)
        return p

    def sec(p, type, style="light", **kw):
        s = Section(page=p, type=type, style=style, sort_order=len(p.sections), **kw)
        db.session.add(s)
        return s

    def box(s, **kw):
        db.session.add(Box(section=s, sort_order=len(s.boxes), **kw))

    home = page("home", "Home", 0, "Fast, clear websites and web apps, built and hosted for growing businesses.")
    about = page("about", "About", 1, "Who we are and how we work.")
    services = page("services", "Services", 2, "Web design, development, hosting and care plans.")
    work = page("portfolio", "Portfolio", 3, "Selected projects.")
    contact = page("contact", "Contact", 4, "Tell us about your project.")

    # ---- Home
    s = sec(home, "hero", heading="Websites that load fast, read clearly and are easy to run.",
            subheading="We design, build and host websites and web apps for small businesses and startups. You get a site you can edit yourself, without calling a developer for every change.",
            button_text="See our work", button_url="/portfolio", button2_text="Talk to us", button2_url="/contact",
            image_url="https://picsum.photos/seed/statecore-hero/1200/860")
    for t in ["Python", "Flask", "PostgreSQL", "Supabase", "Render", "HTML + CSS"]:
        box(s, title=t)
    s = sec(home, "stats", "dark")
    for n, l in [("40+", "Projects delivered"), ("12", "Industries served"), ("98%", "Clients who come back"), ("2 weeks", "Typical time to first launch")]:
        box(s, title=n, text=l)
    s = sec(home, "cards", heading="What we do", subheading="Everything you need to get a business online and keep it running.")
    for ic, t, x in [
        ("design", "Web design", "Layouts built around your content and your customers, not around a template."),
        ("code", "Web development", "Hand-written, tested code that stays fast as your site grows."),
        ("database", "Web apps and dashboards", "Logins, databases and admin panels for the tools your team uses every day."),
        ("cart", "Online stores", "Product pages, carts and payments that are simple to manage."),
        ("search", "SEO basics", "Clean structure, fast pages and proper metadata so people can find you."),
        ("shield", "Hosting and care plans", "Secure hosting, backups and updates, with a person to call when something breaks."),
    ]:
        box(s, icon=ic, title=t, text=x, link_text="Details", link_url="/services")
    s = sec(home, "portfolio", "tint", heading="Recent work", subheading="A few projects we are proud of.", button_text="View all projects", button_url="/portfolio")
    for t, tag, x, seed in [
        ("Harbor Coffee Roasters", "Online store", "A subscription store that doubled repeat orders in three months.", "statecore-proj-1"),
        ("Northline Physio", "Booking website", "Online appointments and a clear services page for a local clinic.", "statecore-proj-2"),
        ("Atlas Freight Portal", "Web app", "A customer portal for tracking shipments and downloading invoices.", "statecore-proj-3"),
    ]:
        box(s, title=t, tag=tag, text=x, image_url=f"https://picsum.photos/seed/{seed}/900/560")
    s = sec(home, "process", heading="How a project runs", subheading="Four steps, with a review after each one.")
    for t, x in [("Discover", "We learn about your business, your customers and what the site must do."),
                 ("Design", "You see real screens, not descriptions, and give feedback."),
                 ("Build", "We build, test on phones and laptops, and load in your content."),
                 ("Launch and support", "We go live, train you on the admin panel and stay on call.")]:
        box(s, title=t, text=x)
    s = sec(home, "testimonials", "tint", heading="What clients say")
    for q, n, r in [
        ("They explained every step in plain language and shipped two days early. Updating the site ourselves is genuinely easy.", "Amira Khan", "Owner, Harbor Coffee"),
        ("Our old site took eight seconds to load. The new one feels instant, and bookings went up the same month.", "Daniel Ross", "Director, Northline Physio"),
        ("The portal saved our support team hours every week. We only had to ask once for changes.", "Sara Malik", "Operations lead, Atlas Freight"),
    ]:
        box(s, text=q, title=n, tag=r)
    sec(home, "cta", "light", heading="Have a project in mind?", subheading="Tell us what you need. We reply within one working day.", button_text="Start a project", button_url="/contact")

    # ---- About
    sec(about, "text", "light", heading="A small studio that stays close to your project",
        subheading="Built by developers who also answer your emails.",
        body="FuTuRe FLoW started as a side project and grew into a studio that builds websites and web apps for people who would rather run their business than manage a website.\n\nEvery project has one person you can talk to from the first call to launch day and beyond. No hand-offs, no ticket queues.",
        image_url="https://picsum.photos/seed/statecore-about/1000/1250")
    s = sec(about, "cards", "tint", heading="How we work")
    for ic, t, x in [("speed", "Fast by default", "Small pages, sensible images and no unused code. Speed is part of the design."),
                     ("shield", "Secure by default", "Encrypted logins, backups and regular updates are included, not add-ons."),
                     ("globe", "Yours to control", "You get an admin panel to edit text, pages and images. You never depend on us for a typo.")]:
        box(s, icon=ic, title=t, text=x)
    sec(about, "cta", "light", heading="Let's talk about your site", button_text="Contact us", button_url="/contact")

    # ---- Services
    sec(services, "text", "light", heading="Services", subheading="Pick one service or combine them.",
        body="Every project starts with a short call and a written quote. Prices below are starting points for a typical small-business project.",
        image_url="https://picsum.photos/seed/statecore-services/1000/1250")
    s = sec(services, "cards", "tint")
    for ic, t, x, tag in [
        ("design", "Website design", "Custom layouts, brand-matched colors and typography, mobile-first.", "From $600"),
        ("code", "Website development", "A fast, editable site with pages, forms and an admin panel.", "From $1,200"),
        ("database", "Web apps", "Customer portals, dashboards and internal tools with secure logins.", "From $3,000"),
        ("cart", "Online stores", "Catalog, cart and payments, plus training for your team.", "From $2,000"),
        ("chart", "SEO and analytics", "Technical SEO, speed tuning and simple monthly reports.", "From $250 / month"),
        ("shield", "Hosting and care", "Hosting, backups, updates and support within one working day.", "From $40 / month"),
    ]:
        box(s, icon=ic, title=t, text=x + " " + tag, link_text="Ask about this", link_url="/contact")
    s = sec(services, "faq", "light", heading="Common questions")
    for q, a in [("How long does a website take?", "Most small-business sites launch in two to four weeks once we have your content."),
                 ("Can I edit the site myself?", "Yes. Every site comes with an admin panel for text, pages and images. We train you on it at launch."),
                 ("Who owns the website?", "You do. The code and content are yours, and you can move them to any host."),
                 ("Do you offer ongoing support?", "Yes. Care plans cover hosting, backups, security updates and small changes each month.")]:
        box(s, title=q, text=a)
    sec(services, "cta", "light", heading="Not sure what you need?", subheading="Describe your idea and we will suggest the simplest way to build it.", button_text="Ask us", button_url="/contact")

    # ---- Portfolio
    s = sec(work, "portfolio", "light", heading="Selected projects", subheading="A mix of stores, service websites and web apps.")
    for t, tag, x, seed in [
        ("Harbor Coffee Roasters", "Online store", "Subscription store with a simple admin for the roastery team.", "statecore-proj-1"),
        ("Northline Physio", "Booking website", "Clear service pages and online appointment requests.", "statecore-proj-2"),
        ("Atlas Freight Portal", "Web app", "Shipment tracking and invoice downloads for customers.", "statecore-proj-3"),
        ("Green Table Catering", "Website", "Menu pages, event enquiries and a photo gallery.", "statecore-proj-4"),
        ("Brightpath Tutors", "Web app", "Student sign-ups, class schedules and a parent dashboard.", "statecore-proj-5"),
        ("Kite & Co Studio", "Portfolio", "A fast portfolio for a photography studio.", "statecore-proj-6"),
    ]:
        box(s, title=t, tag=tag, text=x, image_url=f"https://picsum.photos/seed/{seed}/900/560")
    sec(work, "cta", "tint", heading="Want to be on this page?", button_text="Start a project", button_url="/contact")

    # ---- Contact
    sec(contact, "contact", "light", heading="Tell us about your project",
        subheading="Share a few details and we will reply within one working day.",
        body="Prefer email or a call? Use the details here.")

    defaults = {}
    for k, v in defaults.items():
        db.session.add(Setting(key=k, value=v))
    db.session.commit()
