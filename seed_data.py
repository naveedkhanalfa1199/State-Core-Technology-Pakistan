"""First-run setup: creates the site's page list (used for routing and the nav menu).

Content and design now live entirely in each page's own template file
(templates/home.html, templates/services.html, ...) plus whatever ContentBlock rows
that template's editable spots use - there is nothing to seed for those, since a
ContentBlock is only created once the admin actually edits and saves that spot (until
then the page template just shows its own built-in default text/image)."""


def seed(db, Page, Setting):
    def page(slug, title, order, desc, nav=True):
        db.session.add(Page(slug=slug, title=title, sort_order=order, meta_description=desc, show_in_nav=nav))

    page("home", "Home", 0, "State Core Technology builds fast, reliable web, mobile and cloud products for businesses across Pakistan and abroad.")
    page("about", "About", 1, "Who State Core Technology is, how the team works, and why clients stay with us.")
    page("services", "Services", 2, "Web development, mobile apps, cloud engineering, product design and ongoing support.")
    page("portfolio", "Portfolio", 3, "Selected products we have designed, built and shipped.")
    page("contact", "Contact", 4, "Tell us about your project and get a reply within one working day.")

    defaults = {}
    for k, v in defaults.items():
        db.session.add(Setting(key=k, value=v))
    db.session.commit()
