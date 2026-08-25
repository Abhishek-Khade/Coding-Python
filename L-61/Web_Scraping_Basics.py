"""
=====================================================================
WEB SCRAPING BASICS WITH BEAUTIFULSOUP - Complete Notes with
Executable Examples
=====================================================================

IMPORTANT FRAMING - READ THIS FIRST: scraping is a LAST RESORT, not
a default tool. If a site or service exposes a real/official API,
ALWAYS prefer that API over scraping its HTML:
    - an API is a STABLE, VERSIONED CONTRACT - a scraper is coupled
      to whatever HTML markup a front-end team happens to ship today
    - an API is EXPLICITLY PERMITTED and documented - scraping a site
      that doesn't want to be scraped can violate its Terms of
      Service and get your IP/account blocked
    - an API returns STRUCTURED data (JSON) - HTML has to be parsed
      and cleaned by hand, and is far more fragile
Only reach for scraping when NO API exists for the data you need,
and even then, always check and respect the site's robots.txt and
Terms of Service before scraping anything in production.

That said, BeautifulSoup is a small, well-known HTML/XML PARSING
library, and interviewers occasionally ask a shallow "can you find
an element in this HTML" question to see if you've touched it at
all. This file covers exactly that: loading a string of HTML into a
BeautifulSoup "soup" object, searching it by tag/class/id, walking
the parse tree, pulling out text and attributes safely, and using
CSS selectors - then tying it into the same ETL shape (list of dicts
-> pandas DataFrame) used elsewhere in this repo for API/CSV data.

To keep this file self-contained, reproducible, and policy-safe, all
examples parse a small HTML string that WE construct in code below -
nothing here makes a real network request to a real website.
=====================================================================
"""

from bs4 import BeautifulSoup
import pandas as pd

print("--- Overview ---")
print("BeautifulSoup parses HTML into a searchable tree of tags.")
print("Prefer a real API when one exists - scrape only as a last resort,")
print("and only while respecting robots.txt and the site's Terms of Service.")


"""
---------------------------------------------------------------------
1. PARSING AN HTML STRING WITH BeautifulSoup(html, "html.parser")  ⭐⭐
---------------------------------------------------------------------
`BeautifulSoup(markup, parser_name)` takes raw HTML (a str, or bytes)
and builds a navigable tree out of it. "html.parser" is Python's
built-in parser - no extra dependency required - and is fine for
well-formed HTML like this. (Real-world messy HTML sometimes parses
more forgivingly with the third-party "lxml" or "html5lib" parsers,
but the API is identical either way.)
---------------------------------------------------------------------
"""

print("\n--- Parsing an HTML String ---")

# A tiny, hand-built page - stands in for whatever HTML a real
# (permitted) scrape target would return as response.text
sample_html = """
<html>
  <body>
    <h1 id="page-title">Today's Deals</h1>
    <div class="product" data-sku="A100">
      <span class="name">Wireless Mouse</span>
      <span class="price">$19.99</span>
      <span class="rating">4.5</span>
      <a class="detail-link" href="/items/a100">details</a>
    </div>
    <div class="product" data-sku="A101">
      <span class="name">USB-C Hub</span>
      <span class="price">$34.50</span>
      <span class="rating">4.2</span>
      <a class="detail-link" href="/items/a101">details</a>
    </div>
    <div class="product" data-sku="A102">
      <span class="name">Laptop Stand</span>
      <span class="price">$28.00</span>
      <span class="rating">4.8</span>
      <!-- no link on this one - real HTML is often inconsistent! -->
    </div>
  </body>
</html>
"""

soup = BeautifulSoup(sample_html, "html.parser")
print("parsed object type:", type(soup))
print("soup.title would be None here (no <title> tag) ->", soup.title)
print("first <h1> tag object:", soup.h1)


"""
---------------------------------------------------------------------
2. FINDING ELEMENTS: .find() / .find_all() BY TAG, class_=, id=  ⭐⭐⭐
---------------------------------------------------------------------
`.find(tag, **kwargs)` returns the FIRST matching Tag (or None if
nothing matches). `.find_all(tag, **kwargs)` returns a list of ALL
matches (empty list if none). Because `class` is a reserved Python
keyword, BeautifulSoup uses `class_=` to filter by CSS class, and
`id=` to filter by the id attribute.
---------------------------------------------------------------------
"""

print("\n--- Finding Elements by Tag, class_=, and id= ---")

# by id - unique elements are usually looked up with .find() + id=
title_tag = soup.find(id="page-title")
print("title by id='page-title':", title_tag.get_text())

# by tag name alone
first_span = soup.find("span")
print("first <span> found anywhere:", first_span.get_text())

# by tag name + class_= - the single most common scraping pattern:
# "grab every repeating card/row on the page"
product_divs = soup.find_all("div", class_="product")
print(f"found {len(product_divs)} <div class='product'> blocks")
for div in product_divs:
    print(" -", div.find("span", class_="name").get_text())

# .find_all() also accepts a LIST of tag names, or a `limit=`
first_two_names = soup.find_all("span", class_="name", limit=2)
print("first two names only (limit=2):", [t.get_text() for t in first_two_names])

# a search with no match returns None (find) or [] (find_all) - NOT
# an exception - this is a common "what does this return" question
missing = soup.find("div", class_="does-not-exist")
print("searching for a class that doesn't exist ->", missing)


"""
---------------------------------------------------------------------
3. NAVIGATING THE TREE: .parent, .children, .next_sibling  ⭐
---------------------------------------------------------------------
Every Tag also knows its position in the document: `.parent` walks
UP to the enclosing tag, `.children` iterates its DIRECT child nodes
(an iterator, so wrap it in list() to inspect), and `.next_sibling`
moves to the next node at the SAME level (which can be a stray
whitespace/newline text node in real HTML, not just another tag -
`.find_next_sibling()` skips those and returns the next actual TAG).
---------------------------------------------------------------------
"""

print("\n--- Navigating the Tree ---")

first_product = product_divs[0]
name_tag = first_product.find("span", class_="name")

print("name_tag.parent is the enclosing <div>:", name_tag.parent.get("data-sku"))
print("direct children of first_product (tags only):")
for child in first_product.children:
    if child.name:                     # skip stray text/newline nodes
        print("  <%s>" % child.name, child.get_text(strip=True))

# .next_sibling can land on a blank text node (newline) between tags;
# .find_next_sibling() is the robust way to get the next real TAG
raw_next = name_tag.next_sibling
real_next = name_tag.find_next_sibling()
print("\nname_tag.next_sibling (raw, often just whitespace):", repr(raw_next))
print("name_tag.find_next_sibling() (skips whitespace):", real_next.get_text())


"""
---------------------------------------------------------------------
4. EXTRACTING TEXT AND ATTRIBUTES: .get_text() AND tag.get()  ⭐⭐⭐
---------------------------------------------------------------------
`.get_text()` returns all the text INSIDE a tag (and its descendants),
with tags stripped away. Attributes are read like dict keys:
`tag['href']` - but that raises KeyError if the attribute isn't
present on that tag. `tag.get('href')` is the SAFER equivalent to
`dict.get()` - it returns None (or a default you supply) instead of
raising, which matters a lot when scraping real pages where not
every element has every attribute (see the third product above,
which has no <a> tag at all).
---------------------------------------------------------------------
"""

print("\n--- Extracting Text and Attributes Safely ---")

link_tag = product_divs[0].find("a", class_="detail-link")
print("link_tag.get_text():", link_tag.get_text())
print("link_tag['href'] (dict-style access):", link_tag["href"])

# BUGGY: the third product has NO <a> tag, so .find() returns None,
# and indexing None (or a missing attribute on a real tag) blows up
missing_link_tag = product_divs[2].find("a", class_="detail-link")
try:
    href = missing_link_tag["href"]        # missing_link_tag is None here
except TypeError as e:
    print("\nError indexing a missing element with ['href']:", e)

# also demonstrate the attribute-missing case directly on a REAL tag
name_only_tag = product_divs[2].find("span", class_="name")
try:
    href = name_only_tag["href"]           # real tag, but no href attribute
except KeyError as e:
    print("Error with tag['href'] when the attribute doesn't exist:", e)

# FIXED: .get() never raises - always prefer it for optional attributes
safe_href = None
if missing_link_tag is not None:
    safe_href = missing_link_tag.get("href")
print("\nsafe lookup with .get() on a missing tag ->", safe_href)
print("safe lookup with .get() on an existing attribute:",
      product_divs[0].find("a").get("href"))
print("safe lookup with .get() + a default value:",
      name_only_tag.get("href", "NO LINK PROVIDED"))


"""
---------------------------------------------------------------------
5. CSS SELECTORS VIA .select() - MORE POWERFUL FOR COMPLEX QUERIES  ⭐⭐
---------------------------------------------------------------------
`.select(css_selector)` runs a real CSS selector against the tree and
always returns a list (use `.select_one()` for just the first match).
For simple "one tag, one class" lookups, `.find_all()` is just as
good - but for anything more structural (descendant combinators,
nth-child, multiple classes, attribute selectors) a CSS selector is
far more concise than nesting several `.find()`/`.find_all()` calls.
---------------------------------------------------------------------
"""

print("\n--- CSS Selectors via .select() ---")

# equivalent to find_all("div", class_="product") but as a selector
print("div.product count:", len(soup.select("div.product")))

# descendant combinator: only <span class="price"> INSIDE a product div
prices = soup.select("div.product span.price")
print("prices via 'div.product span.price':", [p.get_text() for p in prices])

# attribute selector: products carrying a data-sku attribute
skus = [d["data-sku"] for d in soup.select("div.product[data-sku]")]
print("skus via 'div.product[data-sku]':", skus)

# select_one() = first match, or None - like find() but with CSS syntax
top_result = soup.select_one("div.product .rating")
print("select_one('div.product .rating') ->", top_result.get_text())


"""
---------------------------------------------------------------------
6. DATA ENGINEERING USE CASE: SCRAPED HTML -> LIST OF DICTS ->
   pandas.DataFrame  ⭐⭐⭐
---------------------------------------------------------------------
Whatever the SOURCE of raw records - a scraped page, a paginated
API response, a CSV file - the goal in an ETL pipeline is the same:
land it as a clean, uniform list of dicts, then hand that to pandas
for the actual transform/load. This makes scraping "just another
extractor" that plugs into the same downstream shape as everything
else in this repo.
---------------------------------------------------------------------
"""

print("\n--- Use Case: Scraped Product Listing -> DataFrame ---")

def parse_product_card(card):
    """Turn one <div class="product"> tag into a clean dict record.

    Uses .get()/defensive None-checks throughout, since scraped HTML
    is never guaranteed to be as uniform as a versioned API schema.
    """
    name_el = card.find("span", class_="name")
    price_el = card.find("span", class_="price")
    rating_el = card.find("span", class_="rating")
    link_el = card.find("a", class_="detail-link")

    price_text = price_el.get_text(strip=True) if price_el else None
    return {
        "sku": card.get("data-sku"),
        "name": name_el.get_text(strip=True) if name_el else None,
        # strip the leading "$" and convert to float for real analysis -
        # wrapped in try/except since scraped text is never guaranteed
        # to be clean, well-formed numeric data
        "price": float(price_text.lstrip("$")) if price_text else None,
        "rating": float(rating_el.get_text(strip=True)) if rating_el else None,
        "detail_url": link_el.get("href") if link_el else None,   # None, not KeyError
    }

records = [parse_product_card(card) for card in soup.select("div.product")]
print("parsed records (list of dicts):")
for r in records:
    print(" ", r)

products_df = pd.DataFrame(records)
print("\nas a pandas DataFrame:")
print(products_df)
print("\naverage price across scraped products: $%.2f" % products_df["price"].mean())
print("products missing a detail_url (defensive check paid off):")
print(products_df[products_df["detail_url"].isna()]["name"].tolist())


"""
---------------------------------------------------------------------
7. ROBUSTNESS NOTES: WHY SCRAPING IS FRAGILE (AND APIS ARE PREFERRED)  ⭐⭐
---------------------------------------------------------------------
An API has a versioned CONTRACT - if a field is renamed, that's a
breaking change the provider has to announce. HTML has NO such
contract: a front-end team can rename a CSS class, restructure a
<div>, or A/B test new markup at any time, with zero notice, and a
brittle selector like `soup.find("div", class_="product")` will
either silently return [] or start returning the WRONG data instead
of raising a clear error. That's why scraping code needs MORE
defensive `None`-checking than API-parsing code (as in Section 6
above), and why it's a fragile long-term choice compared to an
official, versioned API - use scraping only when no API is
available, and only within the target site's robots.txt / ToS.
---------------------------------------------------------------------
"""

print("\n--- Robustness: Why HTML Structure Changes Break Scrapers ---")

# simulate the site silently renaming "product" -> "product-card"
changed_html = sample_html.replace('class="product"', 'class="product-card"')
changed_soup = BeautifulSoup(changed_html, "html.parser")

old_selector_results = changed_soup.select("div.product")   # our old selector
print("old selector 'div.product' after a silent markup change:", old_selector_results)
print("-> returns an EMPTY list, not an error - a pipeline built on this")
print("   would silently produce ZERO records with no exception raised!")

# an API contract change, by contrast, is typically an explicit,
# versioned break (e.g. HTTP 410/404 on a deprecated endpoint, or a
# documented field rename) rather than a silent, invisible one.
new_selector_results = changed_soup.select("div.product-card")
print("\nfixed selector after noticing the change:",
      [c.get("data-sku") for c in new_selector_results])


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Prefer a real API over scraping whenever one exists:
    stable contract, explicitly permitted, structured (JSON) data
Scrape only as a LAST RESORT - and always respect robots.txt / ToS.

Parse HTML:
    BeautifulSoup(html_string, "html.parser")   -> a "soup" tree

Find elements:
    soup.find(tag)                    -> first match, or None
    soup.find_all(tag)                -> list of ALL matches (or [])
    soup.find(tag, class_="x")        -> filter by CSS class
    soup.find(id="x")                 -> filter by id attribute

Navigate the tree:
    tag.parent            -> enclosing tag
    tag.children           -> iterator of direct child nodes
    tag.next_sibling         -> next node at same level (may be whitespace)
    tag.find_next_sibling()   -> next real TAG at same level

Extract data:
    tag.get_text()          -> text content, tags stripped
    tag['href']               -> KeyError if attribute missing
    tag.get('href')             -> None (or a default) if missing - SAFER

CSS selectors (more powerful for complex queries):
    soup.select("div.product span.price")   -> list of matches
    soup.select_one("div.product")            -> first match, or None

ETL shape:      scraped cards -> list of dicts -> pandas.DataFrame
                (same downstream shape as API/CSV extractors)

Fragility:      HTML markup changes SILENTLY break selectors ->
                more defensive None-checking needed than for a
                versioned API contract.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - WEB SCRAPING BASICS WITH BEAUTIFULSOUP
=====================================================================

1. When should you scrape a website with BeautifulSoup instead of
   using that site's official API - and why is an API generally the
   better choice when one is available?

2. Before scraping a site in production, what should you check
   regarding that site's robots.txt and Terms of Service, and why?

3. What does `BeautifulSoup(html, "html.parser")` actually do, and
   what's returned?

4. What's the difference between `.find()` and `.find_all()` in
   terms of what they return when there IS a match, and when there
   ISN'T one?

5. Why does BeautifulSoup use `class_=` instead of `class=` when
   filtering by CSS class?

6. Given `product_divs = soup.find_all("div", class_="product")` from
   this file, how would you pull out just the `name` span's text from
   each one?

7. What's the difference between `tag['href']` and `tag.get('href')`
   when the tag doesn't have an `href` attribute? Which is safer to
   use when scraping, and why?

8. In this file's `parse_product_card()` function, why does the code
   check `if link_el else None` instead of just calling
   `link_el.get("href")` directly?

9. What does `.get_text()` do, and how is it different from just
   printing the tag itself (`str(tag)`)?

10. When would you prefer CSS selectors via `.select()` over chaining
    multiple `.find()`/`.find_all()` calls?

11. What's the difference between `tag.next_sibling` and
    `tag.find_next_sibling()`, and why might the raw `.next_sibling`
    surprise you on real-world HTML?

12. In Section 7, a class name silently changes from "product" to
    "product-card" and the old `.select("div.product")` call returns
    an empty list instead of raising an error. Why is this kind of
    silent failure specifically more dangerous in a scraping pipeline
    than in one built against a versioned API?

13. How would you turn a list of scraped product dicts into a
    pandas DataFrame, and why is that a useful intermediate shape in
    an ETL pipeline?

14. If you were scraping a real (permitted) site at scale, what
    would you add around your requests to be a "good citizen" (e.g.
    rate limiting, retries, a descriptive User-Agent)?
=====================================================================
"""
