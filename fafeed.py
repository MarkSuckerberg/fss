from feedgen.feed import FeedGenerator
from error_fix_extension import ErrorFixExtension, ErrorFixEntryExtension


class FAFeed(FeedGenerator):
    def __init__(self):
        super().__init__()
        self.load_extension("dc")
        self.register_extension("errorfix", ErrorFixExtension, ErrorFixEntryExtension)

        self.generator("FA RSS Proxy")
        self.webMaster("fss@stellers.gay")
        self.link(href="https://www.furaffinity.net/favicon.ico", rel="icon")
        self.language("en")
