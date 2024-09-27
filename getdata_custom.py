from feedgen.feed import FeedGenerator
from faapi import FAAPI
from requests.cookies import RequestsCookieJar
from dotenv import dotenv_values
from datetime import timezone, timedelta
import sqlite3

from flask import Flask

from custom_api import get_posts

app = Flask(__name__)

env = dotenv_values(".env")

cookies = RequestsCookieJar()
cookies.set("a", env["FA_A"])
cookies.set("b", env["FA_B"])

faapi = FAAPI(cookies)

EST_TIMEZONE = timezone(-timedelta(hours=5))


with sqlite3.connect("posts.db") as conn:
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, url TEXT, thumbnail TEXT, rating TEXT, mediaType TEXT, author TEXT);"
    )


@app.route("/<username>/gallery")
@app.route("/<username>/gallery/<int:page>")
def gallery_atom(username, page=1):
    return (
        gallery_feed(username, page).atom_str(pretty=True),
        200,
        {"Content-Type": "application/atom+xml"},
    )


@app.route("/<username>/gallery/rss")
@app.route("/<username>/gallery/rss/<int:page>")
def gallery_rss(username, page=1):
    return (
        gallery_feed(username, page).rss_str(pretty=True),
        200,
        {"Content-Type": "application/rss+xml"},
    )


def gallery_feed(username, page=1) -> FeedGenerator:
    feed = FeedGenerator()
    feed.generator("FA RSS Proxy")

    gallery, author_name = get_posts(cookies, username, page)

    if page > 1:
        feed.link(href=f"/{username}/gallery", rel="first")
        feed.link(href=f"/{username}/gallery/{page-1}", rel="prev")

    feed.title(f"FA Gallery feed of {author_name}")
    # feed.description(user.profile)
    feed.id(f"https://furaffinity.net/gallery/{username}")
    feed.link(href=f"https://furaffinity.net/gallery/{username}", rel="alternate")
    feed.language("en")

    for submission in gallery:
        entry = feed.add_entry()
        entry.title(submission.title)
        entry.link(href=submission.url, rel="alternate")
        entry.id(submission.url)
        entry.enclosure(submission.thumbnail, 0, "image/jpeg")
        entry.description(
            f'<a href={submission.url}><img src="{submission.thumbnail}" alt="{submission.title}"></a>'
        )
        entry.author(name=username)

        # entry.published(submission.date.replace(tzinfo=EST_TIMEZONE))

    return feed


app.run()
