"""Validate search metadata and discovery files in a built Jekyll site."""

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titles = []
        self.descriptions = []
        self.canonicals = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.titles.append("")
            self.in_title = True
        elif tag == "meta" and attrs.get("name") == "description":
            self.descriptions.append(attrs.get("content", ""))
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def validate(folder, site):
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls = [node.text for node in ET.parse(folder / "sitemap.xml").getroot().iter(namespace + "loc")]
    if not urls or len(urls) != len(set(urls)):
        raise ValueError("Sitemap must list unique canonical URLs")
    if f"Sitemap: {site.rstrip('/')}/sitemap.xml" not in (folder / "robots.txt").read_text():
        raise ValueError("robots.txt must declare the canonical sitemap")
    titles, descriptions = [], []
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != urlsplit(site).netloc or parts.query or parts.fragment:
            raise ValueError(f"Non-canonical sitemap URL: {url}")
        path = folder / unquote(parts.path).lstrip("/")
        if path.is_dir():
            path /= "index.html"
        if not path.resolve().is_relative_to(folder.resolve()) or path.suffix != ".html":
            raise ValueError(f"Sitemap URL does not point to an HTML page: {url}")
        page = Metadata()
        page.feed(path.read_text())
        if len(page.titles) != 1 or len(page.descriptions) != 1 or page.canonicals != [url]:
            raise ValueError(f"Expected one title, description and matching canonical URL: {url}")
        title, description = page.titles[0], page.descriptions[0]
        if not 15 <= len(title) <= 80:
            raise ValueError(f"Title needs more context or is too long ({len(title)} characters): {url}")
        if not 60 <= len(description) <= 150:
            raise ValueError(f"Description needs more context or is too long ({len(description)} characters): {url}")
        titles.append(title)
        descriptions.append(description)
    for name, values in (("titles", titles), ("descriptions", descriptions)):
        repeated = [text for text, count in Counter(values).items() if count > 1]
        if repeated:
            raise ValueError(f"Duplicate {name}: {repeated}")
    print(f"Validated {len(urls)} indexable HTML pages: unique titles/descriptions, canonical URLs and sitemap discovery")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--site", required=True)
    args = parser.parse_args()
    validate(args.site_dir, args.site)
