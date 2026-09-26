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

    home = page("home", "Home", 0, "State Core Technology builds fast, reliable web, mobile and cloud products for businesses across Pakistan and abroad.")
    about = page("about", "About", 1, "Who State Core Technology is, how the team works, and why clients stay with us.")
    services = page("services", "Services", 2, "Web development, mobile apps, cloud engineering, product design and ongoing support.")
    work = page("portfolio", "Portfolio", 3, "Selected products we have designed, built and shipped.")
    contact = page("contact", "Contact", 4, "Tell us about your project and get a reply within one working day.")

    # ---- Home
    s = sec(home, "hero", heading="Software that scales, ships fast and never gets in your way.",
            subheading="State Core Technology designs and engineers web platforms, mobile apps and cloud systems for startups and enterprises. One senior team, clear timelines, and code you actually own.",
            button_text="See our work", button_url="/portfolio", button2_text="Book a call", button2_url="/contact",
            image_url="https://picsum.photos/seed/sct-hero-2026/1200/840")
    for t in ["React", "Next.js", "Node.js", "Python", "Flutter", "AWS", "PostgreSQL", "Docker"]:
        box(s, title=t)
    s = sec(home, "stats", "dark")
    for n, l in [("120+", "Products shipped"), ("18", "Industries served"), ("96%", "Clients who return"), ("24/7", "Production monitoring")]:
        box(s, title=n, text=l)
    s = sec(home, "cards", "light", heading="What we build", subheading="A senior engineering team covering the full product lifecycle, from first sketch to production support.")
    for ic, t, x in [
        ("code", "Web development", "Custom web platforms and dashboards built on modern, well-tested frameworks that stay fast as you grow."),
        ("mobile", "Mobile app development", "Native-feel iOS and Android apps from a single Flutter codebase, or fully native when you need it."),
        ("database", "Cloud & DevOps", "AWS and container-based infrastructure, CI/CD pipelines and monitoring so releases are boring, in a good way."),
        ("design", "Product design (UI/UX)", "Research-backed interfaces that are fast to use and easy for your team to maintain and extend."),
        ("shield", "Custom software & ERP", "Internal tools, inventory, HR and finance systems built around how your business actually runs."),
        ("search", "QA, security & support", "Automated testing, security reviews and a support desk that responds within one working day."),
    ]:
        box(s, icon=ic, title=t, text=x, link_text="Learn more", link_url="/services")
    s = sec(home, "portfolio", "dark", heading="Recent work", subheading="A sample of platforms and apps our team has shipped to production.", button_text="View all projects", button_url="/portfolio")
    for t, tag, x, seedimg in [
        ("Kashan Retail Cloud", "E-commerce platform", "A multi-vendor storefront and seller dashboard handling thousands of orders a day.", "sct-proj-1"),
        ("Meridian Pay", "Fintech dashboard", "Real-time transaction monitoring and reconciliation for a regional payments provider.", "sct-proj-2"),
        ("Freightline Tracker", "Logistics web app", "Live shipment tracking, route planning and customer-facing delivery status pages.", "sct-proj-3"),
        ("CareLoop Clinics", "Healthcare booking system", "Appointment scheduling and patient records for a network of outpatient clinics.", "sct-proj-4"),
        ("Estatehub Pakistan", "Real estate portal", "Property listings, verified agent profiles and mortgage calculators for a nationwide marketplace.", "sct-proj-5"),
        ("Bazaar POS", "Point-of-sale system", "Offline-first checkout, inventory sync and reporting for multi-branch retail chains.", "sct-proj-6"),
    ]:
        box(s, title=t, tag=tag, text=x, image_url=f"https://picsum.photos/seed/{seedimg}/900/560")
    s = sec(home, "process", "light", heading="How a project runs", subheading="Four stages, with a working review at the end of each one.")
    for t, x in [("Discovery", "We map your goals, users and technical constraints before a single line of code is written."),
                 ("Design", "You review real, clickable screens and give feedback early, not after the build is finished."),
                 ("Development & QA", "Two-week sprints, automated tests and a staging link you can check at any time."),
                 ("Launch & support", "We deploy, monitor and stay on call, with a care plan for updates and scaling.")]:
        box(s, title=t, text=x)
    s = sec(home, "testimonials", "dark", heading="What clients say")
    for q, n, r in [
        ("They understood our business before they touched the codebase. Six months in, the platform still hasn't had a single hour of unplanned downtime.", "Bilal Ahmed", "CEO, Kashan Retail"),
        ("Our previous vendor took a year and never finished. State Core rebuilt the core product in eleven weeks and it has been rock solid since.", "Sana Riaz", "Product Lead, Meridian Pay"),
        ("Clear sprint updates every week, no surprises at invoice time, and a support team that actually answers the phone.", "David Chen", "COO, Freightline Logistics"),
    ]:
        box(s, text=q, title=n, tag=r)
    sec(home, "cta", "light", heading="Have a product in mind?", subheading="Tell us what you're building. We reply within one working day with a clear next step.", button_text="Start a project", button_url="/contact")

    # ---- About
    sec(about, "text", "dark", heading="An engineering-led team that stays close to your product",
        subheading="Built by developers who also join your stand-ups.",
        body="State Core Technology started as a small team of engineers who were frustrated by agencies that hand off a PDF and disappear. We build differently: one accountable team, from the first architecture decision to the day your product is running at scale.\n\nEvery client gets a named lead engineer and a project manager who can be reached directly, not a rotating cast of account managers. We work in fixed sprints with visible progress, so you always know exactly what shipped and what's next.",
        image_url="https://picsum.photos/seed/sct-about-2026/1000/1250")
    s = sec(about, "cards", "tint", heading="How we work")
    for ic, t, x in [("speed", "Fast, without cutting corners", "Small, well-tested releases every sprint. You see working software in weeks, not months."),
                     ("shield", "Secure by default", "Code review, dependency scanning and access controls are part of every build, not an add-on."),
                     ("globe", "Built for handover", "Documented code, clean architecture and admin panels so you are never locked into us.")]:
        box(s, icon=ic, title=t, text=x)
    s = sec(about, "stats", "dark")
    for n, l in [("9", "Years building software"), ("35+", "Engineers, designers & QA"), ("6", "Countries we ship to"), ("40+", "Long-term retained clients")]:
        box(s, title=n, text=l)
    sec(about, "cta", "light", heading="Want to talk to the team that would build it?", button_text="Contact us", button_url="/contact")

    # ---- Services
    sec(services, "text", "dark", heading="Services", subheading="Pick one service or combine several into a single roadmap.",
        body="Every engagement starts with a short discovery call and a written proposal with fixed milestones. The starting prices below cover a typical project; final scope is quoted after discovery.",
        image_url="https://picsum.photos/seed/sct-services-2026/1000/1250")
    s = sec(services, "cards", "tint")
    for ic, t, x, tag in [
        ("design", "Product design (UI/UX)", "Research, wireframes and a polished, developer-ready design system.", "From $800"),
        ("code", "Web development", "A fast, secure, fully custom web platform with an admin panel your team can run.", "From $2,500"),
        ("mobile", "Mobile app development", "Cross-platform Flutter apps, or native iOS and Android when you need it.", "From $4,000"),
        ("database", "Custom software & ERP", "Internal tools, inventory, HR and finance systems built around your workflow.", "From $5,000"),
        ("chart", "Cloud & DevOps", "AWS setup, CI/CD pipelines, containers and monitoring for reliable releases.", "From $600 / month"),
        ("shield", "QA, security & support", "Test automation, security audits and a support desk within one working day.", "From $350 / month"),
    ]:
        box(s, icon=ic, title=t, text=x + " " + tag, link_text="Ask about this", link_url="/contact")
    s = sec(services, "faq", "light", heading="Common questions")
    for q, a in [("How long does a typical project take?", "A focused web platform usually launches in six to ten weeks. Larger products with mobile apps or ERP integrations run three to six months, delivered in shippable stages."),
                 ("Do you work with clients outside Pakistan?", "Yes. About half of our current clients are based in the US, UK and the Gulf. We run sprints on overlapping hours and communicate over Slack, email and weekly video calls."),
                 ("Who owns the code and the data?", "You do, fully. Source code, infrastructure access and content are handed over at every milestone, not just at the end."),
                 ("What happens after launch?", "Every project includes a warranty period, and most clients move onto a monthly care plan covering hosting, monitoring, security updates and a support-response window."),
                 ("How do you price a project?", "Fixed price for well-defined scopes, or monthly retainer for ongoing product work. You get a written quote before anything starts, no surprise invoices.")]:
        box(s, title=q, text=a)
    sec(services, "cta", "light", heading="Not sure which service you need?", subheading="Describe what you're trying to build and we'll suggest the simplest, most cost-effective way to do it.", button_text="Ask us", button_url="/contact")

    # ---- Portfolio
    s = sec(work, "portfolio", "dark", heading="Selected projects", subheading="A mix of platforms, mobile apps and internal systems shipped to production.")
    for t, tag, x, seedimg in [
        ("Kashan Retail Cloud", "E-commerce platform", "Multi-vendor storefront, seller dashboard and automated payouts.", "sct-proj-1"),
        ("Meridian Pay", "Fintech dashboard", "Real-time transaction monitoring and reconciliation tooling.", "sct-proj-2"),
        ("Freightline Tracker", "Logistics web app", "Live shipment tracking and customer delivery status pages.", "sct-proj-3"),
        ("CareLoop Clinics", "Healthcare booking system", "Appointment scheduling and records for outpatient clinics.", "sct-proj-4"),
        ("Estatehub Pakistan", "Real estate portal", "Property listings, agent profiles and mortgage calculators.", "sct-proj-5"),
        ("Bazaar POS", "Point-of-sale system", "Offline-first checkout and inventory sync for retail chains.", "sct-proj-6"),
        ("Horizon Freight Mobile", "Mobile app", "Driver-facing Flutter app for pickups, proof of delivery and routing.", "sct-proj-7"),
        ("Almas HR Suite", "Internal ERP", "Payroll, leave management and performance reviews for a 500-person company.", "sct-proj-8"),
        ("Northwind Analytics", "Data dashboard", "A self-serve reporting layer built on top of a client's existing warehouse.", "sct-proj-9"),
    ]:
        box(s, title=t, tag=tag, text=x, image_url=f"https://picsum.photos/seed/{seedimg}/900/560")
    sec(work, "cta", "light", heading="Want your product on this page next?", button_text="Start a project", button_url="/contact")

    # ---- Contact
    sec(contact, "contact", "light", heading="Tell us about your project",
        subheading="Share a few details and a lead engineer will reply within one working day.",
        body="Prefer a call first? Use the details here, or send a message and we'll set up a time that works across time zones.")

    defaults = {}
    for k, v in defaults.items():
        db.session.add(Setting(key=k, value=v))
    db.session.commit()
