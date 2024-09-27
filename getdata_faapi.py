from feedgen.feed import FeedGenerator
from feedgen.ext.dc import DcEntryExtension
from faapi import FAAPI, Submission as FAAPISubmission
from faapi.exceptions import NotFound, DisabledAccount
from requests.cookies import RequestsCookieJar
from dotenv import dotenv_values
from datetime import timezone, timedelta, datetime
from flask import Flask, redirect
from pickle import dump, load
from threading import Lock
import lzma

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


class SubmissionData:
    id: str
    title: str
    description: str
    url: str
    file_url: str
    thumbnail_url: str
    date: datetime

    def __init__(self, fa_submission: FAAPISubmission):
        self.id = fa_submission.id
        self.title = fa_submission.title
        self.description = fa_submission.description
        self.url = fa_submission.url
        self.file_url = fa_submission.file_url
        self.thumbnail_url = fa_submission.thumbnail_url
        self.date = fa_submission.date


class FAFeed(FeedGenerator):
    def __init__(self):
        super().__init__()
        self.load_extension("dc")
        self.generator("FA RSS Proxy")
        self.link(href="https://www.furaffinity.net/favicon.ico", rel="icon")
        self.language("en")


try:
    with lzma.open("submission_cache.pkl.xz", "rb") as f:
        submission_cache = load(f)
except FileNotFoundError:
    pass


@app.route("/favicon.ico")
def favicon():
    return redirect("https://www.furaffinity.net/favicon.ico")


@app.route("/gallery/<username>")
@app.route("/gallery/<username>/<int:page>")
def gallery_atom(username, page=1):
    try:
        feed = gallery_feed(username, page)
    except NotFound as e:
        return str(e), 404

    return (
        feed.atom_str(pretty=True),
        200,
        {"Content-Type": "application/atom+xml"},
    )


@app.route("/gallery/<username>/rss")
@app.route("/gallery/<username>/rss/<int:page>")
def gallery_rss(username, page=1):
    try:
        feed = gallery_feed(username, page)
    except NotFound as e:
        return str(e), 404

    return (
        feed.rss_str(pretty=True),
        200,
        {"Content-Type": "application/rss+xml"},
    )


def gallery_feed(username, page=1) -> FeedGenerator:
    feed = FAFeed()

    feed.id(f"https://furaffinity.net/gallery/{username}")
    feed.link(href=f"https://furaffinity.net/gallery/{username}", rel="alternate")

    try:
        gallery, nextPage = faapi.gallery(username, page)
    except DisabledAccount as e:
        feed.title(f"FA Gallery feed of {username}")
        feed.description(str(e))
        return feed
    except NotFound as e:
        raise e

    if page > 1:
        feed.link(href=f"/{username}/gallery", rel="first")
        feed.link(href=f"/{username}/gallery/{page-1}", rel="prev")

    if nextPage:
        feed.link(href=f"/{username}/gallery/{page+1}", rel="next")

    if len(gallery) == 0:
        feed.title(f"FA Gallery feed of {username}")
        feed.description("No submissions found, but the user exists.")
        return feed

    user = gallery[0].author

    feed.title(f"FA Gallery feed of {user.name}")
    feed.description(user.title)

    # Check if anything fetched is new
    save = False

    for submission in gallery[:10]:
        submission, cached = get_submission(submission.id)

        save = save or not cached

        entry = feed.add_entry()

        dc: DcEntryExtension = entry.dc
        dc.dc_creator(username)

        entry.title(submission.title)
        entry.link(href=submission.url, rel="alternate")
        entry.id(submission.url)

        entry.enclosure(url=submission.thumbnail_url, type="image/jpeg")
        entry.enclosure(url=submission.file_url, type="image/jpeg")

        entry.description(
            f"""
            <a href="{submission.url}">
                <picture>
                    <source srcset="{submission.file_url}" media="(min-width: 10000px, min-height: 800px)">
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
            with lzma.open("submission_cache.pkl.xz", "wb") as f:
                dump(submission_cache, f)

    return feed


def get_submission(submission_id) -> tuple[SubmissionData, bool]:
    with submission_cache_lock:
        if submission_id in submission_cache:
            return submission_cache[submission_id], True

        submission = SubmissionData(faapi.submission(submission_id)[0])

        submission_cache[submission_id] = submission

        return submission, False


if __name__ == "__main__":
    app.run()
