import datetime
from faapi import Submission as FAAPISubmission
from datetime import timezone, timedelta

# FA returns EST for some reason
FA_TIMEZONE = timezone(-timedelta(hours=5))


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
        # FAAPI returns a broken thumbnail URL
        self.thumbnail_url = fa_submission.thumbnail_url.replace("%40", "@")
        self.date = fa_submission.date.replace(tzinfo=FA_TIMEZONE).astimezone(
            timezone.utc
        )
