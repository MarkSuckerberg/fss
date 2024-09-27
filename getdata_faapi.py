from feedgen.feed import FeedGenerator
from feedgen.ext.dc import DcExtension
from faapi import FAAPI, Submission
from requests.cookies import RequestsCookieJar
from requests.exceptions import HTTPError
from dotenv import dotenv_values
from datetime import timezone, timedelta
from flask import Flask
from pickle import dump, load
from threading import Lock

app = Flask(__name__)

env = dotenv_values(".env")

cookies = RequestsCookieJar()
cookies.set("a", env["FA_A"])
cookies.set("b", env["FA_B"])

faapi = FAAPI(cookies)

# FA returns EST for some reason
FA_TIMEZONE = timezone(-timedelta(hours=5))

submission_cache = {}
submission_cache_lock = Lock()


class FAFeed(FeedGenerator):
    def __init__(self):
        super().__init__()
        self.load_extension("dc")
        self.generator("FA RSS Proxy")


try:
    submission_cache = load(open("submission_cache.pkl", "rb"))
except FileNotFoundError:
    pass


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
    feed = FeedGenerator()
    feed.load_extension("dc")
    feed.generator("FA RSS Proxy")

    try:
        gallery, nextPage = faapi.gallery(username, page)
    except HTTPError as e:
        return str(e), 404

    if page > 1:
        feed.link(href=f"/{username}/gallery", rel="first")
        feed.link(href=f"/{username}/gallery/{page-1}", rel="prev")

    if nextPage:
        feed.link(href=f"/{username}/gallery/{page+1}", rel="next")

    user = gallery[0].author

    feed.title(f"FA Gallery feed of {user.name}")
    feed.description(user.title)

    feed.id(f"https://furaffinity.net/gallery/{username}")
    feed.link(href=f"https://furaffinity.net/gallery/{username}", rel="alternate")
    feed.language("en")

    # Check if anything fetched is new
    save = False

    for submission in gallery[:10]:
        submission, cached = get_submission(submission.id)

        save = save or cached

        entry = feed.add_entry()

        dc: DcExtension = entry.dc
        dc.dc_creator(username)

        entry.title(submission.title)
        entry.link(href=submission.url, rel="alternate")
        entry.id(submission.url)

        entry.enclosure(submission.thumbnail_url, 0, "image/jpeg")
        entry.enclosure(submission.file_url, 0, "image/jpeg")

        entry.description(
            f"""
            <a href="{submission.url}">
                <picture>
                    <source srcset="{submission.file_url}" media="(min-width: 800px, min-height: 800px)">
                    <img src="{submission.thumbnail_url}" alt="{submission.title}">
                </picture>      
            </a>
            <hr />
            {submission.description}
            """
        )

        entry.author(name=username)

        date = submission.date.replace(tzinfo=FA_TIMEZONE)

        entry.published(date)
        entry.updated(date)

    # Save the cache if we have new submissions
    if save:
        with submission_cache_lock:
            dump(submission_cache, open("submission_cache.pkl", "wb"))

    return feed


def get_submission(submission_id) -> tuple[Submission, bool]:
    with submission_cache_lock:
        if submission_id in submission_cache:
            return submission_cache[submission_id], True

        submission = faapi.submission(submission_id)[0]

        submission_cache[submission_id] = submission

        return submission, False


if __name__ == "__main__":
    app.run()
