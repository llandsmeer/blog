AUTHOR = 'Lennart Landsmeer'
SITENAME = 'The Weekend Writeup'
SITESUBTITLE = 'Lennart Landsmeer\'s Personal Blog'
SITEURL = ''

THEME='./theme'

PATH = "content"

TIMEZONE = 'Europe/Amsterdam'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ATOM = ('atom.xml')
CATEGORY_FEED_ATOM = None
FEED_DOMAIN = SITEURL
TRANSLATION_FEED = None
SUMMARY_MAX_LENGTH = 100

DEFAULT_CATEGORY = 'tech'
DISPLAY_CATEGORIES_ON_MENU = False
WITH_FUTURE_DATES = False

SLUGIFY_SOURCE = 'basename'
SLUG_REGEX_SUBSTITUTIONS = [
    # (r'[^\\w\\s-]', ''),  # remove non-alphabetical/whitespace/'-' chars
    # (r'(?u)\\A\\s*', ''),  # strip leading whitespace
    # (r'(?u)\\s*\\Z', ''),  # strip trailing whitespace
    # (r'[-\\s]+', '-'),  # reduce multiple whitespace or '-' to single '-'
    (r'^\d{4}-\d{2}-\d{2}-', '') # remove date
]
ARTICLE_URL = '{category}/{date:%Y}/{date:%m}/{date:%d}/{slug}.html'
ARTICLE_SAVE_AS = '{category}/{date:%Y}/{date:%m}/{date:%d}/{slug}.html'

# Blogroll
LINKS = []
# (
#     ("Github", "https://github.com/llandsmeer"),
#     ("Python.org", "https://www.python.org/"),
#     ("Jinja2", "https://palletsprojects.com/p/jinja/"),
#     ("You can modify those links in your config file", "#"),
# )

# Social widget
SOCIAL = []
# (
#     ("You can add links in your config file", "#"),
#     ("Another social link", "#"),
# )
# 
DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True
