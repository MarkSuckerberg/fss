from dotenv import dotenv_values
from faapi import FAAPI, Submission as FAAPISubmission
from faapi.exceptions import NotFound, DisabledAccount
from feedgen.feed import FeedGenerator
from feedgen.ext.dc import DcEntryExtension
from flask import Flask, redirect
from pickle import dump, load
from requests.cookies import RequestsCookieJar
from threading import Lock

from submissiondata import SubmissionData
from fafeed import FAFeed
from i_love_libraries import ErrorFixEntryExtension

import lzma

app = Flask(__name__)

env = dotenv_values(".env")

cookies = RequestsCookieJar()
cookies.set("a", env["FA_A"])
cookies.set("b", env["FA_B"])

faapi = FAAPI(cookies)


submission_cache: dict[str, SubmissionData] = {}
submission_cache_lock = Lock()


try:
    with lzma.open("submission_cache.pkl.xz", "rb") as f:
        submission_cache = load(f)
except FileNotFoundError:
    pass


@app.route("/")
def index():
    return redirect("https://github.com/MarkSuckerberg/fss")


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
    feed.description(user.title or user.name)

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

        file_type = submission.file_url.split(".")[-1]
        types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "pdf": "application/pdf",
        }

        fix: ErrorFixEntryExtension = entry.errorfix
        fix.add_atom_link(
            submission.file_url,
            rel="enclosure",
            type=types.get(file_type, "application/octet-stream"),
        )

        entry.enclosure(
            url=submission.file_url,
            type=types.get(file_type, "application/octet-stream"),
        )

        entry.description(
            f"""
            <a href="{submission.url}">
                <img src="{submission.thumbnail_url}" alt="{submission.title}">
            </a>
            <hr />
            {submission.description}
            """
        )

        entry.author(name=username)

        date = submission.date

        entry.published(date)
        entry.updated(date)

    # Save the cache if we have new submissions
    if save:
        with submission_cache_lock:
            with lzma.open("submission_cache.pkl.xz", "wb") as f:
                dump(submission_cache, f)

    return feed


def get_submission(submission_id: int) -> tuple[SubmissionData, bool]:
    with submission_cache_lock:
        if submission_id in submission_cache:
            return submission_cache[submission_id], True

        submission = SubmissionData(faapi.submission(submission_id)[0])

        submission_cache[submission_id] = submission

        return submission, False


if __name__ == "__main__":
    app.run()
