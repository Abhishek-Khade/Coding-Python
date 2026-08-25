"""
=====================================================================
THE requests LIBRARY - GET/POST, HEADERS, AUTH & PAGINATION
=====================================================================

`requests` is the de-facto standard HTTP client for Python. In data
engineering it is almost always how you EXTRACT data from a REST API
as the first step of a pipeline: pull orders from an e-commerce
platform, pull metrics from a SaaS tool, push transformed rows to a
downstream service, etc.

The core mental model is simple: you call `requests.get(...)` or
`requests.post(...)`, which sends an HTTP request and blocks until it
gets back a `Response` object. That `Response` carries everything
you need: `.status_code` (200, 404, 500...), `.headers` (a dict-like
of response headers), `.text` (the raw response body as a string),
and `.json()` (the body parsed into a Python dict/list, when the
server sent JSON).

The parts that separate "toy script" from "production-grade extract
step" are: ALWAYS setting a `timeout=`, checking `.status_code` (or
calling `.raise_for_status()`) instead of assuming success, sending
the right AUTH (API key, bearer token, or HTTP Basic), reusing a
`requests.Session()` instead of paying connection setup cost on every
call, and correctly PAGINATING through multi-page result sets instead
of only grabbing page 1. This file covers all of it with real,
runnable `requests` code.

This sandbox has no reliable outbound internet access, so every
example below MOCKS the network boundary by patching `requests.get`
/ `requests.post` with `unittest.mock.patch` and a small hand-rolled
`FakeResponse` class shaped like a real `requests.Response`. The
CODE you see calling `requests.get(...)` / `requests.post(...)` is
the real, correct API - only the actual socket I/O is swapped out.
=====================================================================
"""

import base64
import json
from unittest.mock import patch

import pandas as pd
import requests

print("--- Overview ---")
print("requests.get()/post() send an HTTP request and return a Response")
print("with .status_code, .headers, .text, and .json(). Production code")
print("adds timeout=, error handling, auth, sessions, and pagination.")


"""
---------------------------------------------------------------------
1. FakeResponse - A MINIMAL STAND-IN FOR requests.Response  ⭐
---------------------------------------------------------------------
To demonstrate REAL requests.get()/post() calls without a real
network, we patch requests.get/requests.post so they return this
object instead of making a socket connection. It only implements the
handful of Response attributes/methods this file actually uses.
---------------------------------------------------------------------
"""

print("\n--- FakeResponse: a Response-shaped stand-in for testing ---")


class FakeResponse:
    """Mimics the small slice of requests.Response used in this file:
    .status_code, .headers, .text, .json(), .raise_for_status()."""

    def __init__(self, status_code, json_data=None, headers=None, reason=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.headers = headers or {"Content-Type": "application/json"}
        self.reason = reason or ("OK" if status_code < 400 else "Error")
        self.text = json.dumps(self._json_data)

    def json(self):
        return self._json_data

    def raise_for_status(self):
        # Mirrors the REAL requests.Response.raise_for_status(): it is a
        # no-op on success, and raises HTTPError on any 4xx/5xx status.
        if 400 <= self.status_code < 600:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Error: {self.reason}", response=self
            )


print("FakeResponse implements .status_code/.headers/.text/.json()/")
print("raise_for_status() - just enough surface area to stand in for")
print("a real requests.Response in every example below.")


"""
---------------------------------------------------------------------
2. GET REQUESTS: params=, .status_code, .json(), .text, .headers  ⭐⭐⭐
---------------------------------------------------------------------
requests.get(url, params=...) builds the query string for you (URL-
encoding values, joining with '&') instead of you concatenating
strings by hand - always prefer params= over manual string building.
---------------------------------------------------------------------
"""

print("\n--- GET Requests: params, status_code, json(), text, headers ---")


def fake_get_users(url, params=None, headers=None, timeout=None, **kwargs):
    # Stands in for a real server at GET /users?active=true
    all_users = [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
        {"id": 3, "name": "Carla", "active": True},
    ]
    want_active_only = (params or {}).get("active") == "true"
    data = [u for u in all_users if u["active"]] if want_active_only else all_users
    return FakeResponse(
        200,
        json_data={"users": data},
        headers={"Content-Type": "application/json", "X-RateLimit-Remaining": "99"},
    )


with patch("requests.get", side_effect=fake_get_users):
    response = requests.get(
        "https://api.example.com/users", params={"active": "true"}, timeout=5
    )
    print("status_code:", response.status_code)
    print("headers:", dict(response.headers))
    print("json():", response.json())
    print("text (raw body string):", response.text)

print("\n(optional bonus) attempting ONE real network call - this is")
print("expected to fail in a sandboxed environment with no outbound")
print("internet, and that is fine: nothing above depends on it.")
try:
    real_response = requests.get(
        "https://httpbin.org/get", params={"demo": "1"}, timeout=3
    )
    real_response.raise_for_status()
    print("real call succeeded, status:", real_response.status_code)
except requests.exceptions.RequestException as e:
    print(f"real call failed as expected here ({type(e).__name__}): {e}")


"""
---------------------------------------------------------------------
3. POST REQUESTS: json= FOR THE REQUEST BODY  ⭐⭐⭐
---------------------------------------------------------------------
requests.post(url, json=payload) serializes `payload` to a JSON
string AND sets the "Content-Type: application/json" header for you.
(The older `data=` sends a raw/form-encoded body and does NOT set
that header automatically - a classic source of "why is my API
rejecting this?" bugs.)
---------------------------------------------------------------------
"""

print("\n--- POST Requests: json= for the request body ---")


def fake_post_orders(url, json=None, headers=None, timeout=None, **kwargs):
    order_id = 1001
    return FakeResponse(
        201,
        json_data={"order_id": order_id, "status": "created", **(json or {})},
        headers={"Content-Type": "application/json", "Location": f"/orders/{order_id}"},
    )


with patch("requests.post", side_effect=fake_post_orders):
    payload = {"sku": "WIDGET-42", "qty": 3}
    response = requests.post(
        "https://api.example.com/orders", json=payload, timeout=5
    )
    print("status_code:", response.status_code)
    print("created order:", response.json())
    print("Location header:", response.headers["Location"])


"""
---------------------------------------------------------------------
4. ERROR HANDLING: raise_for_status() AND CATCHING HTTPError,
   ConnectionError, Timeout  ⭐⭐⭐
---------------------------------------------------------------------
requests does NOT raise an exception on a 404 or 500 by default - a
bad status is just a Response with response.status_code == 404. You
must EXPLICITLY call response.raise_for_status() to turn it into an
exception, or check response.status_code yourself. Separately,
network-level failures (DNS lookup fails, connection refused, no
response in time) raise their OWN exception types before you even get
a Response object back.
---------------------------------------------------------------------
"""

print("\n--- Error Handling: raise_for_status(), HTTPError, ConnectionError, Timeout ---")


def fake_get_not_found(url, timeout=None, **kwargs):
    return FakeResponse(404, json_data={"error": "not found"}, reason="Not Found")


with patch("requests.get", side_effect=fake_get_not_found):
    response = requests.get("https://api.example.com/users/9999", timeout=5)
    print("status_code (no exception yet - requests never raises on its own):", response.status_code)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("caught HTTPError:", e)


def fake_get_connection_error(url, timeout=None, **kwargs):
    # Simulates DNS failure / refused connection - happens BEFORE any
    # Response object exists, so there is nothing to call .json() on.
    raise requests.exceptions.ConnectionError(
        "Failed to establish a new connection: [Errno -2] Name or service not known"
    )


with patch("requests.get", side_effect=fake_get_connection_error):
    try:
        requests.get("https://this-host-does-not-exist.invalid/data", timeout=5)
    except requests.exceptions.ConnectionError as e:
        print("caught ConnectionError:", e)


def fake_get_timeout(url, timeout=None, **kwargs):
    raise requests.exceptions.Timeout(f"Request timed out after {timeout}s")


with patch("requests.get", side_effect=fake_get_timeout):
    try:
        requests.get("https://slow-api.example.com/data", timeout=3)
    except requests.exceptions.Timeout as e:
        print("caught Timeout:", e)

print("\nAll three (HTTPError, ConnectionError, Timeout) are subclasses of")
print("requests.exceptions.RequestException - catch that base class when")
print("you just want 'any request-related failure' in one except block.")


"""
---------------------------------------------------------------------
5. WHY YOU MUST ALWAYS PASS timeout=  ⭐⭐⭐
---------------------------------------------------------------------
requests has NO default timeout. If the server accepts the TCP
connection but then never sends a response (a hung backend, a stalled
load balancer, a black-holed connection), requests.get() WITHOUT
timeout= will wait FOREVER. In a real pipeline that means a worker
thread/process is stuck indefinitely - it never fails, never retries,
never frees resources - it just silently hangs the job. This is one
of the most common real production bugs with `requests`.

We cannot actually demonstrate an infinite hang here (it would freeze
this script), so the mock below raises a clearly-labeled simulated
error in place of "hangs forever" when timeout is omitted, and
behaves normally when a real timeout is supplied.
---------------------------------------------------------------------
"""

print("\n--- Why You Must ALWAYS Pass timeout= ---")


def fake_get_maybe_hangs(url, timeout=None, **kwargs):
    if timeout is None:
        raise RuntimeError(
            "SIMULATED HANG: in REAL requests, this call would block "
            "forever waiting on the socket - there is no default timeout"
        )
    return FakeResponse(200, json_data={"ok": True})


# BUGGY: no timeout= at all
with patch("requests.get", side_effect=fake_get_maybe_hangs):
    try:
        requests.get("https://flaky-api.example.com/data")  # NO timeout - dangerous!
    except RuntimeError as e:
        print("without timeout=:", e)

# FIXED: always pass timeout=. A tuple is (connect_timeout, read_timeout)
# in seconds - connect_timeout bounds the TCP handshake, read_timeout
# bounds how long to wait for data once connected.
with patch("requests.get", side_effect=fake_get_maybe_hangs):
    response = requests.get(
        "https://flaky-api.example.com/data", timeout=(3.05, 10)
    )
    print("with timeout=(connect, read):", response.status_code)

print("\nRule of thumb: EVERY requests call in production code gets a")
print("timeout=, no exceptions - pair it with retry logic (e.g. `tenacity`")
print("or `backoff`) for the Timeout that eventually gets raised.")


"""
---------------------------------------------------------------------
6. CUSTOM HEADERS: Authorization BEARER TOKEN, Content-Type  ⭐⭐
---------------------------------------------------------------------
headers=... is a plain dict merged into the request. The most common
data-engineering use is an "Authorization: Bearer <token>" header for
OAuth2/JWT-style APIs, and "Content-Type"/"Accept" to declare what
format you're sending/expecting.
---------------------------------------------------------------------
"""

print("\n--- Custom Headers: Authorization Bearer Token, Content-Type ---")


def fake_get_profile(url, headers=None, timeout=None, **kwargs):
    auth_header = (headers or {}).get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return FakeResponse(
            401, json_data={"error": "missing or malformed bearer token"}, reason="Unauthorized"
        )
    token = auth_header.removeprefix("Bearer ")
    return FakeResponse(200, json_data={"user": "svc-account", "token_used": token})


with patch("requests.get", side_effect=fake_get_profile):
    good_headers = {
        "Authorization": "Bearer abc123.def456.ghi789",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    response = requests.get("https://api.example.com/me", headers=good_headers, timeout=5)
    print("valid bearer token ->", response.status_code, response.json())

    # BUGGY: forgetting the required "Bearer " prefix is a very common mistake
    bad_headers = {"Authorization": "abc123.def456.ghi789"}
    response = requests.get("https://api.example.com/me", headers=bad_headers, timeout=5)
    print("missing 'Bearer ' prefix ->", response.status_code, response.json())


"""
---------------------------------------------------------------------
7. AUTH PATTERNS: API KEY IN HEADER vs QUERY PARAM vs auth=(user, pw)  ⭐⭐⭐
---------------------------------------------------------------------
Three patterns cover almost every REST API you'll hit as a data
engineer. Interviewers commonly ask you to name/compare all three.
---------------------------------------------------------------------
"""

print("\n--- Auth Patterns: Header API Key vs Query-Param API Key vs Basic Auth ---")

VALID_KEY = "sk_live_12345"


# Pattern 1: API key in a custom header (most common, most secure of the two API-key styles)
def fake_get_apikey_header(url, headers=None, timeout=None, **kwargs):
    key = (headers or {}).get("X-API-Key")
    return FakeResponse(200 if key == VALID_KEY else 403, json_data={"authenticated": key == VALID_KEY})


with patch("requests.get", side_effect=fake_get_apikey_header):
    response = requests.get(
        "https://api.example.com/data", headers={"X-API-Key": VALID_KEY}, timeout=5
    )
    print("API key in header:      ", response.status_code, response.json())


# Pattern 2: API key as a query parameter (simple, but leaks into server
# access logs, browser history, and proxy logs - avoid when a header option exists)
def fake_get_apikey_param(url, params=None, timeout=None, **kwargs):
    key = (params or {}).get("api_key")
    return FakeResponse(200 if key == VALID_KEY else 403, json_data={"authenticated": key == VALID_KEY})


with patch("requests.get", side_effect=fake_get_apikey_param):
    response = requests.get(
        "https://api.example.com/data", params={"api_key": VALID_KEY}, timeout=5
    )
    print("API key in query param: ", response.status_code, response.json())


# Pattern 3: requests' built-in HTTP Basic Auth via auth=(user, pass) -
# requests builds "Authorization: Basic base64(user:pass)" internally.
def fake_get_basic_auth(url, auth=None, timeout=None, **kwargs):
    if auth is None:
        return FakeResponse(401, json_data={"error": "unauthorized"}, reason="Unauthorized")
    user, pw = auth
    expected_header_value = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return FakeResponse(
        200,
        json_data={"authenticated": True, "authorization_header_would_be": f"Basic {expected_header_value}"},
    )


with patch("requests.get", side_effect=fake_get_basic_auth):
    response = requests.get(
        "https://api.example.com/secure", auth=("svc_user", "s3cr3t-pw"), timeout=5
    )
    print("HTTP Basic auth (auth=):", response.status_code, response.json())

print("\nheader API key -> not logged in URLs, works with any client")
print("query-param key -> simplest, but shows up in logs/history - avoid for secrets")
print("auth=(user, pw) -> requests base64-encodes it into a standard")
print("                   Authorization: Basic header for you")


"""
---------------------------------------------------------------------
8. PAGINATION, STYLE 1: PAGE-NUMBER BASED  ⭐⭐⭐
---------------------------------------------------------------------
The single most common REST API interview question in this module:
"how do you handle pagination pulling data from a REST API?" The
page-number style increments a `?page=N` parameter until the server
returns an EMPTY results list, meaning there's nothing left to fetch.
A generator is the right tool here - it yields records lazily, one
page's worth at a time, instead of forcing every page into memory
before the caller can start processing.
---------------------------------------------------------------------
"""

print("\n--- Pagination Style 1: Page-Number Based (?page=1, ?page=2, ...) ---")

_ORDERS_DB = [{"order_id": i, "amount": round(10 + i * 1.5, 2)} for i in range(1, 24)]  # 23 fake orders
_PAGE_SIZE = 10


def fake_get_orders_page_based(url, params=None, timeout=None, **kwargs):
    page = (params or {}).get("page", 1)
    start = (page - 1) * _PAGE_SIZE
    chunk = _ORDERS_DB[start:start + _PAGE_SIZE]
    return FakeResponse(200, json_data={"results": chunk, "page": page})


def fetch_all_orders_page_based(base_url):
    """Generator: pages through a page-number-based API, yielding every
    record lazily, until a page comes back with an empty 'results' list."""
    page = 1
    while True:
        response = requests.get(base_url, params={"page": page}, timeout=5)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            break                      # empty page = no more data, stop
        yield from results
        page += 1


with patch("requests.get", side_effect=fake_get_orders_page_based):
    all_orders_p1 = list(fetch_all_orders_page_based("https://api.example.com/orders"))

print(f"page-based pagination pulled {len(all_orders_p1)} orders across {-(-len(all_orders_p1)//_PAGE_SIZE)} pages")
print("first:", all_orders_p1[0], "  last:", all_orders_p1[-1])


"""
---------------------------------------------------------------------
9. PAGINATION, STYLE 2: CURSOR / next-TOKEN BASED  ⭐⭐⭐
---------------------------------------------------------------------
The other extremely common style: instead of a page NUMBER, the
server returns an opaque "next" cursor/token in the response body.
You keep calling with `?cursor=<that token>` until the server returns
next=None (or omits the field), meaning you've reached the last page.
This style is common in APIs that need STABLE pagination even while
the underlying dataset is being written to concurrently.
---------------------------------------------------------------------
"""

print("\n--- Pagination Style 2: Cursor / next-Token Based ---")

_EVENTS_DB = [{"event_id": f"evt_{i}", "type": "click"} for i in range(1, 27)]  # 26 fake events
_CURSOR_PAGE_SIZE = 12


def fake_get_events_cursor_based(url, params=None, timeout=None, **kwargs):
    cursor = (params or {}).get("cursor")
    start = int(cursor) if cursor else 0
    chunk = _EVENTS_DB[start:start + _CURSOR_PAGE_SIZE]
    end = start + len(chunk)
    next_cursor = str(end) if end < len(_EVENTS_DB) else None   # None -> last page
    return FakeResponse(200, json_data={"data": chunk, "next": next_cursor})


def fetch_all_events_cursor_based(base_url):
    """Generator: follows an opaque 'next' cursor token, yielding every
    record lazily, until the server signals next=None."""
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        body = response.json()
        yield from body.get("data", [])
        cursor = body.get("next")
        if cursor is None:
            break                      # server says there is no next page


with patch("requests.get", side_effect=fake_get_events_cursor_based):
    all_events = list(fetch_all_events_cursor_based("https://api.example.com/events"))

print(f"cursor-based pagination pulled {len(all_events)} events lazily via `next`")
print("first:", all_events[0], "  last:", all_events[-1])

print("\nBoth generators are LAZY: `for event in fetch_all_events_cursor_based(url):`")
print("would start processing the first page's records before page 2 is")
print("even requested - critical for memory-efficient streaming of huge result sets.")


"""
---------------------------------------------------------------------
10. requests.Session() FOR CONNECTION REUSE & SHARED HEADERS  ⭐⭐
---------------------------------------------------------------------
Calling requests.get() at module level opens a NEW underlying TCP
connection (and, for HTTPS, redoes the TLS handshake) for every call.
A requests.Session() reuses an underlying connection pool (same idea
as the CONNECTION POOLING file, applied to HTTP instead of a
database) - repeated calls to the SAME host reuse an already-open
connection instead of paying handshake cost every time. A Session
also lets you set headers/auth ONCE and have them apply to every
request made through it.
---------------------------------------------------------------------
"""

print("\n--- requests.Session() for Connection Reuse & Shared Headers ---")

with patch.object(requests.Session, "get", side_effect=fake_get_orders_page_based) as mocked_get:
    with requests.Session() as session:
        # set once, applied automatically to every request this session makes
        session.headers.update({
            "Authorization": "Bearer session-token-xyz",
            "User-Agent": "pattern-etl/1.0",
        })
        page_1 = session.get("https://api.example.com/orders", params={"page": 1}, timeout=5)
        page_2 = session.get("https://api.example.com/orders", params={"page": 2}, timeout=5)

    print("session.headers applied to both calls:", dict(session.headers))
    print("number of session.get() calls made:", mocked_get.call_count)
    print("page 1 count:", len(page_1.json()["results"]), " page 2 count:", len(page_2.json()["results"]))

print("\nUnder the hood, requests.Session keeps a urllib3 connection pool per")
print("host - exactly the connection-pooling concept from that other file,")
print("just for HTTP instead of a database. Use a Session whenever you're")
print("making MULTIPLE calls to the same API in one process (e.g. paginating).")


"""
---------------------------------------------------------------------
11. DATA ENGINEERING USE CASE: ETL EXTRACT WITH A TRANSIENT FAILURE  ⭐⭐⭐
---------------------------------------------------------------------
Real APIs occasionally return a transient 500/502/503 on one page for
no good reason (a backend blip, a load balancer hiccup) even though
every other page succeeds. Exactly like the "one bad file shouldn't
kill the whole job" principle for file-based ingestion, a single bad
PAGE should not abort the entire extract - retry it a bounded number
of times, log clearly, and only give up on that one page if retries
are exhausted, while the rest of the pages still get processed.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: ETL Extract Tolerating a Transient 500 ---")

_RAW_ORDER_PAGES = {
    1: [{"order_id": 1, "customer": "Acme", "amount": 120.50},
        {"order_id": 2, "customer": "Globex", "amount": 75.00}],
    2: [{"order_id": 3, "customer": "Initech", "amount": 300.00}],
    3: [],  # empty results -> natural end of pagination
}
_page_2_attempts = {"count": 0}


def fake_get_orders_etl(url, params=None, timeout=None, **kwargs):
    page = (params or {}).get("page", 1)
    if page == 2:
        _page_2_attempts["count"] += 1
        if _page_2_attempts["count"] == 1:
            # simulate a TRANSIENT failure - the backend is healthy again
            # by the very next attempt, which is the common real-world case
            return FakeResponse(500, json_data={"error": "internal server error"}, reason="Internal Server Error")
    return FakeResponse(200, json_data={"results": _RAW_ORDER_PAGES.get(page, [])})


def extract_all_orders(base_url, max_retries=3):
    """ETL 'extract' step with per-page retry: a page that fails with an
    HTTPError is retried up to max_retries times before being logged and
    skipped - so one flaky page degrades the job instead of crashing it."""
    page = 1
    collected = []
    while True:
        results = None
        for attempt in range(1, max_retries + 1):
            response = requests.get(base_url, params={"page": page}, timeout=5)
            try:
                response.raise_for_status()
                results = response.json().get("results", [])
                break                     # success - stop retrying this page
            except requests.exceptions.HTTPError as e:
                print(f"  page {page} attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    print(f"  WARNING: page {page} still failing after {max_retries} attempts - "
                          f"skipping it and continuing the job")
        if results is None:
            page += 1          # gave up on this page - move on, don't crash the job
            if page > 10:       # safety valve against a permanently broken feed
                break
            continue
        if not results:
            break               # empty page = end of pagination
        collected.extend(results)
        page += 1
    return collected


with patch("requests.get", side_effect=fake_get_orders_etl):
    orders = extract_all_orders("https://api.example.com/orders")

print(f"\nextracted {len(orders)} orders total (page 2's transient 500 was")
print(f"retried and recovered - job never crashed)")

orders_df = pd.DataFrame(orders)
print("\ncombined into one DataFrame for downstream loading:")
print(orders_df)
print("\ntotal revenue across all extracted orders:", orders_df["amount"].sum())


"""
=====================================================================
QUICK REFERENCE
=====================================================================
GET (read)         -> requests.get(url, params={...}, timeout=5)
POST (write)        -> requests.post(url, json={...}, timeout=5)
Inspect a response  -> .status_code, .headers, .text, .json()
Raise on 4xx/5xx     -> response.raise_for_status() -> HTTPError
Network failures     -> requests.exceptions.ConnectionError, Timeout
                        (base class: requests.exceptions.RequestException)
ALWAYS pass          -> timeout=5  or  timeout=(connect, read)
                        (no timeout = can hang forever - real prod bug)

Headers   -> headers={"Authorization": "Bearer <token>",
                       "Content-Type": "application/json"}

Auth patterns:
  API key in header    -> headers={"X-API-Key": "..."}         (preferred)
  API key in query      -> params={"api_key": "..."}            (leaks to logs)
  HTTP Basic Auth        -> auth=("user", "password")            (requests
                                                                   base64-encodes it)

Pagination, page-number:
    page = 1
    while True:
        r = requests.get(url, params={"page": page}, timeout=5)
        results = r.json()["results"]
        if not results: break
        yield from results
        page += 1

Pagination, cursor/next-token:
    cursor = None
    while True:
        r = requests.get(url, params={"cursor": cursor} if cursor else {}, timeout=5)
        body = r.json()
        yield from body["data"]
        cursor = body.get("next")
        if cursor is None: break

Session reuse -> with requests.Session() as s:
                     s.headers.update({...})   # set once
                     s.get(url1); s.get(url2)   # pooled connections

Resilient ETL page -> retry N times on HTTPError, log + skip that
                       page on exhaustion, keep processing the rest -
                       one bad page must not kill the whole job.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - THE requests LIBRARY
=====================================================================

1. How do you handle pagination when pulling data from a REST API?
   Describe both the page-number style and the cursor/next-token
   style used by `fetch_all_orders_page_based` and
   `fetch_all_events_cursor_based` in this file.

2. Why is `fetch_all_orders_page_based` written as a GENERATOR
   (using `yield from`) instead of building and returning one big
   list? What breaks if the API has millions of records?

3. What is the difference between `requests.get(url, params=...)`
   and `requests.post(url, json=...)`? What does passing `json=`
   do for you automatically that `data=` does not?

4. `response.raise_for_status()` - what does it do on a 200, and
   what does it do on a 404 or 500? What exception type does it
   raise, and what is that exception's parent class?

5. Why does requests have NO default timeout, and what actually
   happens to your program if you call `requests.get(url)` against
   a server that accepts the connection but never responds?

6. What is the difference between `requests.exceptions.ConnectionError`
   and `requests.exceptions.Timeout`? At what point in the request
   lifecycle does each one get raised?

7. Name three ways to authenticate against a REST API with
   `requests`. What is the security downside of putting an API key
   in the query string versus a header?

8. What does `auth=("user", "password")` actually send on the wire?
   How would you construct that same header value by hand (hint:
   `base64`)?

9. In `extract_all_orders`, why does a failed page get RETRIED up
   to `max_retries` times before being skipped, rather than either
   (a) crashing the whole job immediately, or (b) retrying forever?

10. How does this file's "retry then skip" pattern for one bad API
    page relate to handling "one bad file" in a multi-file batch
    ingestion job? Why should neither one bring down the entire job?

11. What performance/connection-reuse benefit does `requests.Session()`
    give you over calling `requests.get()` at module level for every
    request, especially against the same host?

12. If you set `session.headers.update({"Authorization": ...})` on a
    `requests.Session`, does every subsequent `session.get()` call
    automatically include that header? Why is that useful for an API
    that requires an auth token on every call?

13. How would you design a Python script to incrementally pull only
    *new* data from an API each day (e.g. using a `since=<timestamp>`
    or cursor parameter), rather than re-pulling everything?

14. What's the difference between `response.text` and `response.json()`?
    What happens if you call `.json()` on a response whose body isn't
    valid JSON?

15. How would you implement exponential backoff on top of the retry
    loop in `extract_all_orders`, and which libraries in this
    sandbox (`tenacity`, `backoff`) are commonly used for that
    instead of hand-rolling it?
=====================================================================
"""
