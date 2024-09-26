from feedgen.feed import FeedGenerator
from faapi import FAAPI
from requests.cookies import RequestsCookieJar
from requests.exceptions import HTTPError
from dotenv import dotenv_values
from datetime import timezone, timedelta
from flask import Flask

app = Flask(__name__)

env = dotenv_values(".env")

cookies = RequestsCookieJar()
cookies.set("a", env["FA_A"])
cookies.set("b", env["FA_B"])

faapi = FAAPI(cookies)

EST_TIMEZONE = timezone(-timedelta(hours=5))


@app.route("/gallery/<username>")
@app.route("/gallery/<username>/<int:page>")
def gallery_atom(username, page=1):
    return (
        gallery_feed(username, page).atom_str(pretty=True),
        200,
        {"Content-Type": "application/atom+xml"},
    )


@app.route("/gallery/<username>/rss")
@app.route("/gallery/<username>/rss/<int:page>")
def gallery_rss(username, page=1):
    return (
        gallery_feed(username, page).rss_str(pretty=True),
        200,
        {"Content-Type": "application/rss+xml"},
    )


def gallery_feed(username, page=1) -> FeedGenerator:
    try:
        user = faapi.user(username)
    except HTTPError as e:
        return str(e), 404

    feed = FeedGenerator()
    feed.generator("FA RSS Proxy")

    gallery, nextPage = faapi.gallery(username, page)

    if page > 1:
        feed.link(href=f"/{username}/gallery", rel="first")
        feed.link(href=f"/{username}/gallery/{page-1}", rel="prev")

    if nextPage:
        feed.link(href=f"/{username}/gallery/{page+1}", rel="next")

    feed.title(f"FA Gallery feed of {user.name}")
    feed.description(user.title)
    feed.id(f"https://furaffinity.net/gallery/{username}")
    feed.link(href=f"https://furaffinity.net/gallery/{username}", rel="alternate")
    feed.language("en")

    for submission in gallery[:10]:
        submission = faapi.submission(submission.id)[0]

        entry = feed.add_entry()
        entry.title(submission.title)
        entry.link(href=submission.url, rel="alternate")
        entry.id(submission.url)
        entry.enclosure(submission.file_url, 0, "image/jpeg")
        entry.description(
            f'<a href={submission.url}><img src="{submission.file_url}" alt="{submission.title}"></a>{submission.description}'
        )
        entry.author(name=username)

        entry.published(submission.date.replace(tzinfo=EST_TIMEZONE))

    return feed


app.run()
