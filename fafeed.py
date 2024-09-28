from feedgen.feed import FeedGenerator
from i_love_libraries import ErrorFixExtension, ErrorFixEntryExtension


class FAFeed(FeedGenerator):
    def __init__(self):
        super().__init__()
        self.load_extension("dc")
        self.register_extension("errorfix", ErrorFixExtension, ErrorFixEntryExtension)

        self.generator("FA RSS Proxy")
        self.webMaster("fss@stellers.gay")
        self.link(href="https://www.furaffinity.net/favicon.ico", rel="icon")
        self.language("en")
