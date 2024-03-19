AUTHOR = 'Lennart Landsmeer'
SITENAME = 'Lennart Landsmeer'
SITEURL = "https://blog.llandsmeer.com"

PATH = "content"

TIMEZONE = 'Europe/Amsterdam'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ATOM = ('atom.xml')
CATEGORY_FEED_ATOM = None
FEED_DOMAIN = SITEURL
TRANSLATION_FEED = None

ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = '{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'

# Blogroll
LINKS = (
    ("Github", "https://github.com/llandsmeer"),
    ("Python.org", "https://www.python.org/"),
    ("Jinja2", "https://palletsprojects.com/p/jinja/"),
    ("You can modify those links in your config file", "#"),
)

# Social widget
SOCIAL = (
    ("You can add links in your config file", "#"),
    ("Another social link", "#"),
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True
