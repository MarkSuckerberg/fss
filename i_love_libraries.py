from feedgen.ext.base import BaseExtension, BaseEntryExtension
from feedgen.util import xml_elem
from lxml.etree import Element

ERROR_NS = "https://github.com/lkiesow/python-feedgen/issues/135"


class ErrorFixExtension(BaseExtension):
    """It's broken, and I want to use enclosures on ATOM."""

    def extend_ns(self):
        return {"errorfix": ERROR_NS}


class ErrorFixEntryExtension(BaseEntryExtension):
    atom_links = []

    def __init__(self):
        self.atom_links = []

    def extend_atom(self, entry: Element):
        for link in self.atom_links or []:
            element = xml_elem("link", entry, href=link["href"])
            if link.get("rel"):
                element.attrib["rel"] = link["rel"]
            if link.get("type"):
                element.attrib["type"] = link["type"]
            if link.get("hreflang"):
                element.attrib["hreflang"] = link["hreflang"]
            if link.get("title"):
                element.attrib["title"] = link["title"]
            if link.get("length"):
                element.attrib["length"] = link["length"]

        return entry

    def add_atom_link(
        self, href, rel=None, type=None, hreflang=None, title=None, length=None
    ):
        self.atom_links.append(
            {
                "href": href,
                "rel": rel,
                "type": type,
                "hreflang": hreflang,
                "title": title,
                "length": length,
            }
        )
