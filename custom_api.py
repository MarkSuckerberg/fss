from bs4 import BeautifulSoup, Tag, ResultSet
import requests
from requests.cookies import RequestsCookieJar
from datetime import date, timedelta
import sqlite3


class PostInfo:
    id: int
    url: str
    title: str
    thumbnail: str
    rating: str
    mediaType: str


def get_posts(
    cookies: RequestsCookieJar, username: str, page: int, sfw=True
) -> tuple[list[PostInfo], str]:
    start_date = (date.today() - timedelta(days=60 * page)).strftime("%Y-%m-%d")
    end_date = (date.today() - timedelta(days=60 * (page - 1))).strftime("%Y-%m-%d")

    response = requests.post(
        "https://www.furaffinity.net/search/",
        cookies=cookies,
        data={
            "q": f"@lower+{username}",
            "page": 1,
            "range": "manual",
            "range_to": end_date,
            "range_from": start_date,
            "order_by": "date",
            "mode": "extended",
            "rating-general": "1",
            "rating-mature": "0" if sfw else "1",
            "rating-adult": "0" if sfw else "1",
        },
        headers={
            "User-Agent": "FA RSS Proxy",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    soup = BeautifulSoup(response.text, "html.parser")

    gallery: Tag = soup.find_all("section", class_="gallery")[0]
    posts: ResultSet[Tag] = gallery.find_all("figure")

    post_data: list[PostInfo] = []

    author_name = ""

    for post in posts:
        links: ResultSet[Tag] = post.find_all("a")

        data = PostInfo()

        data.url = "https://furaffinity.net" + links[0]["href"]
        data.title = links[1].text
        data.id = int(data.url.split("/")[-2])

        author_tag = links[2]
        author_name = author_tag.text

        data.thumbnail = "https:" + post.find("img")["src"]

        size_index = data.thumbnail.find("@")
        data.thumbnail = (
            data.thumbnail[:size_index] + "@600" + data.thumbnail[size_index + 4 :]
        )

        data.rating = post.attrs["class"][0].split("-")[1]
        data.mediaType = post.attrs["class"][1].split("-")[1]

        post_data.append(data)

    return (post_data, author_name)


def FullSubmissionInfo(cookies: RequestsCookieJar, id: int) -> PostInfo:
    response = requests.get(
        f"https://furaffinity.net/view/{id}/",
        cookies=cookies,
        headers={"User-Agent": "FA RSS Proxy"},
    )
