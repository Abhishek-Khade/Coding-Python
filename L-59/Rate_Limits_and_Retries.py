"""
=====================================================================
RATE LIMITS AND RETRIES - Exponential Backoff, Jitter, and
tenacity/backoff - Complete Notes with Executable Examples
=====================================================================

Any code that talks to an external API, database, or queue over a
network WILL occasionally see a request fail for a TRANSIENT reason:
a connection timeout, a temporary 503 from an overloaded service, or
a 429 "Too Many Requests" because you tripped a rate limit. The naive
reaction - "just try again immediately" - is usually the WRONG move.
If the failure was caused by the remote service being overloaded or
rate-limiting you, retrying instantly (especially in a tight loop,
and especially across many client processes at once) just adds MORE
load at the worst possible moment. This is called a RETRY STORM, and
it can turn a brief hiccup into a full outage.

The fix data engineers reach for constantly - anywhere a pipeline
calls a REST API, a warehouse, or a queue - is EXPONENTIAL BACKOFF:
each retry waits longer than the last (delay doubling each attempt),
giving the remote service room to recover, combined with a MAX RETRY
COUNT so a genuinely broken call fails loudly instead of hanging
forever. Adding random JITTER to that delay avoids many clients all
retrying in lockstep (the "thundering herd" problem). And a well-
behaved client should also respect the server's OWN guidance when it
provides one - an HTTP `Retry-After` header on a 429/503 response -
rather than guessing.

This file builds that up in three layers: hand-rolling a retry
decorator from scratch (the same `functools.wraps`-based pattern from
the Decorators file, now applied to backoff), then doing the exact
same thing declaratively with the `tenacity` and `backoff` libraries,
and finally distinguishing which failures are even worth retrying in
the first place - retrying a permanent error (bad request, 404, bad
auth) never helps; it just wastes time and can mask a real bug.
=====================================================================
"""

import time
import random
import functools

print("--- Overview ---")
print("Naive immediate retries in a tight loop can worsen an outage.")
print("The fix: exponential backoff + jitter, respect Retry-After,")
print("cap attempts, and only retry TRANSIENT failures.")


"""
---------------------------------------------------------------------
1. WHY NAIVE IMMEDIATE RETRY IS DANGEROUS (THE "RETRY STORM")  ⭐⭐⭐
---------------------------------------------------------------------
If a call fails because the remote service is overloaded (a 503) or
because YOU are being rate-limited (a 429), retrying instantly in a
tight `while True` loop does two bad things at once: it keeps hitting
a service that just told you it's struggling, and - if many client
processes/threads are all doing this at the same time - all of them
pile back on at once in a synchronized burst the moment the service
shows the first sign of life, which can knock it back over. This
compounding effect is exactly what backoff (spacing retries out) and
jitter (de-synchronizing clients) are designed to prevent.
---------------------------------------------------------------------
"""

print("\n--- Why Naive Immediate Retry Is Dangerous ---")

call_attempts = {"count": 0}

def flaky_service_call():
    """Simulates a service that is currently overloaded/rate-limited."""
    call_attempts["count"] += 1
    raise ConnectionError("503 Service Unavailable (simulated)")

print("naive approach: retry immediately in a tight loop, no delay -")
print("this just hammers the struggling service as fast as possible:")
naive_attempts = 0
try:
    for _ in range(4):
        naive_attempts += 1
        flaky_service_call()          # fails every time in this demo
except ConnectionError as e:
    print(f"  after {naive_attempts} back-to-back attempts with ZERO delay: {e}")
print("  4 attempts fired in essentially 0 seconds - if this were a")
print("  real rate limit, we just made it worse, and if 100 other")
print("  client processes are doing the exact same thing, the")
print("  service may never recover. This is the 'retry storm'.")


"""
---------------------------------------------------------------------
2. HAND-ROLLING A RETRY DECORATOR WITH EXPONENTIAL BACKOFF  ⭐⭐⭐
---------------------------------------------------------------------
This directly answers the classic interview question: "write a
decorator that retries a function on failure with exponential
backoff." It reuses the exact `functools.wraps` pattern from the
Decorators file - `wraps` copies over `__name__`/`__doc__` from the
wrapped function so introspection and debugging still show the real
function's identity instead of the generic `wrapper`.

The core formula: delay = base * (2 ** attempt) - each failed
attempt DOUBLES the wait relative to the previous one, and a
`max_attempts` cap ensures we eventually give up and raise instead of
retrying forever.
---------------------------------------------------------------------
"""

print("\n--- Hand-Rolled Retry Decorator (Exponential Backoff) ---")

def retry_with_backoff(max_attempts=5, base_delay=0.05):
    """Decorator factory: retries the wrapped function on ANY Exception,
    waiting base_delay * (2 ** attempt) seconds between attempts."""
    def decorator(func):
        @functools.wraps(func)          # preserves func.__name__/__doc__ on wrapper
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"  [{func.__name__}] attempt {attempt + 1} failed "
                              f"({e}) - out of retries, giving up")
                        raise
                    delay = base_delay * (2 ** attempt)   # the core backoff formula
                    print(f"  [{func.__name__}] attempt {attempt + 1} failed "
                          f"({e}) - retrying in {delay:.3f}s")
                    time.sleep(delay)
        return wrapper
    return decorator

# A deterministic "flaky" function: fails a fixed number of times, then
# succeeds, using a mutable counter closed over the function - reproducible
# every run, unlike a real network call.
fail_schedule = {"remaining_failures": 3}

@retry_with_backoff(max_attempts=5, base_delay=0.05)
def fetch_from_flaky_api():
    if fail_schedule["remaining_failures"] > 0:
        fail_schedule["remaining_failures"] -= 1
        raise TimeoutError("simulated network timeout")
    return {"status": "ok", "data": [1, 2, 3]}

print("calling fetch_from_flaky_api() (fails 3 times, then succeeds):")
result = fetch_from_flaky_api()
print("  final result:", result)
print(f"  preserved via functools.wraps -> fetch_from_flaky_api.__name__ =",
      fetch_from_flaky_api.__name__)

# Also show the "out of retries" path explicitly, to prove the cap works.
@retry_with_backoff(max_attempts=3, base_delay=0.05)
def always_fails():
    raise ConnectionError("simulated permanent outage")

print("\ncalling always_fails() (never succeeds, max_attempts=3):")
try:
    always_fails()
except ConnectionError as e:
    print(f"  correctly raised after exhausting retries: {e}")


"""
---------------------------------------------------------------------
3. ADDING JITTER: AVOIDING THE "THUNDERING HERD"  ⭐⭐⭐
---------------------------------------------------------------------
Pure exponential backoff has a subtle problem: if MANY clients all
fail at the same moment (e.g. a shared service blips), they will all
compute the EXACT SAME delay sequence and all retry at the EXACT SAME
synchronized moments - just spaced out in bursts instead of one
continuous hammering. This is the "thundering herd" problem. JITTER
fixes it by randomizing each delay slightly, so retries from
different clients spread out instead of arriving in lockstep.
---------------------------------------------------------------------
"""

print("\n--- Adding Jitter to Backoff ---")

def retry_with_jitter(max_attempts=5, base_delay=0.05):
    """Same as retry_with_backoff, but adds random jitter to each delay
    so concurrent callers don't all retry at the exact same instant."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    raw_delay = base_delay * (2 ** attempt)
                    # "full jitter": pick a random value between 0 and the
                    # raw delay, rather than using the raw delay exactly -
                    # a strategy used in AWS's own backoff guidance.
                    jittered_delay = random.uniform(0, raw_delay)
                    print(f"  [{func.__name__}] attempt {attempt + 1} failed "
                          f"({e}) - raw delay {raw_delay:.3f}s, "
                          f"jittered to {jittered_delay:.3f}s")
                    time.sleep(jittered_delay)
        return wrapper
    return decorator

jitter_schedule = {"remaining_failures": 2}

@retry_with_jitter(max_attempts=5, base_delay=0.05)
def fetch_with_jittered_retry():
    if jitter_schedule["remaining_failures"] > 0:
        jitter_schedule["remaining_failures"] -= 1
        raise TimeoutError("simulated timeout")
    return "success"

print("calling fetch_with_jittered_retry() (fails 2 times, then succeeds):")
print("  result:", fetch_with_jittered_retry())
print("\nWithout jitter, 1000 clients that all failed at the same instant")
print("would all sleep exactly 0.05s, 0.10s, 0.20s... and all retry in")
print("the same synchronized bursts. Jitter spreads those retries out.")


"""
---------------------------------------------------------------------
4. RESPECTING A SERVER'S Retry-After HEADER  ⭐⭐⭐
---------------------------------------------------------------------
Many real APIs return a `Retry-After` header on a 429 (rate limited)
or 503 (unavailable) response, telling you EXACTLY how long to wait
before trying again - either as a number of seconds or an HTTP-date.
When a server gives you this, HONOR IT instead of blindly computing
your own exponential delay - the server knows its own recovery time
(e.g. "your rate-limit window resets in 2 seconds") far better than
a client-side guess does. Good retry logic checks for this header
FIRST and only falls back to exponential backoff when it's absent.
---------------------------------------------------------------------
"""

print("\n--- Respecting a Retry-After Header ---")

class MockRateLimitedResponse:
    """Stands in for a `requests.Response` from a real HTTP client."""
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}

# A fixed schedule of mocked responses this "API" will return, so the
# demo is fully deterministic: 429 with guidance, then 429 with
# guidance, then a real success - no live network call involved.
mock_response_schedule = [
    MockRateLimitedResponse(429, headers={"Retry-After": "0.06"}),
    MockRateLimitedResponse(429, headers={"Retry-After": "0.03"}),
    MockRateLimitedResponse(200),
]
mock_call_index = {"i": 0}

def call_mocked_api():
    """Returns the next canned response in mock_response_schedule."""
    response = mock_response_schedule[mock_call_index["i"]]
    mock_call_index["i"] += 1
    return response

def fetch_respecting_retry_after(max_attempts=5, default_base_delay=0.05):
    for attempt in range(max_attempts):
        response = call_mocked_api()
        if response.status_code == 200:
            print(f"  attempt {attempt + 1}: 200 OK")
            return "success"
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                # server told us exactly how long to wait - honor it
                # rather than computing our own exponential guess.
                delay = float(retry_after)
                print(f"  attempt {attempt + 1}: 429 with Retry-After="
                      f"{retry_after} -> honoring server's guidance, "
                      f"sleeping {delay:.3f}s")
            else:
                # no guidance given - fall back to our own backoff
                delay = default_base_delay * (2 ** attempt)
                print(f"  attempt {attempt + 1}: 429 with no Retry-After "
                      f"-> falling back to exponential backoff {delay:.3f}s")
            time.sleep(delay)
    raise RuntimeError("exhausted retries respecting Retry-After")

print("calling fetch_respecting_retry_after() against a mocked 429/429/200 schedule:")
print("  result:", fetch_respecting_retry_after())


"""
---------------------------------------------------------------------
5. THE SAME LOGIC, DECLARATIVELY, WITH `tenacity`  ⭐⭐⭐
---------------------------------------------------------------------
Everything in sections 2-3 is exactly what the `tenacity` library
gives you out of the box, with far less boilerplate: `stop_after_
attempt(n)` caps retries, `wait_exponential(multiplier=..., min=...,
max=...)` implements exponential backoff (and can add jitter too),
and `retry_if_exception_type(...)` restricts WHICH exceptions trigger
a retry. This is the library you'll actually reach for in real
pipeline code instead of hand-rolling the decorator every time.
---------------------------------------------------------------------
"""

print("\n--- The Same Logic, Declaratively, with tenacity ---")

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logging.basicConfig(level=logging.INFO, format="  %(message)s")
logger = logging.getLogger("tenacity_demo")

tenacity_schedule = {"remaining_failures": 3}

@retry(
    stop=stop_after_attempt(5),                         # give up after 5 tries
    wait=wait_exponential(multiplier=0.05, min=0.01, max=1),  # backoff (jitter built into some strategies too)
    retry=retry_if_exception_type(TimeoutError),         # only retry on TimeoutError
    before_sleep=before_sleep_log(logger, logging.INFO),  # logs each wait, for visibility
    reraise=True,                                        # re-raise the real exception if all attempts fail
)
def fetch_with_tenacity():
    if tenacity_schedule["remaining_failures"] > 0:
        tenacity_schedule["remaining_failures"] -= 1
        raise TimeoutError("simulated timeout")
    return "tenacity success"

print("calling fetch_with_tenacity() (fails 3 times, then succeeds):")
print("  result:", fetch_with_tenacity())
print("\nCompare this ~8-line declarative config to the ~15-line hand-")
print("rolled decorator in section 2 - same behavior, far less")
print("boilerplate, and battle-tested edge cases (jitter strategies,")
print("timeouts, async support) handled for you.")


"""
---------------------------------------------------------------------
6. AN ALTERNATIVE: THE `backoff` LIBRARY  ⭐⭐
---------------------------------------------------------------------
`backoff` is a smaller, more minimal alternative to `tenacity` with a
more function-decorator-first API: `@backoff.on_exception(backoff.
expo, ExceptionType, max_tries=...)` gets you exponential backoff
(with jitter ON by default) in one line. Good to know both exist -
some codebases standardize on one or the other.
---------------------------------------------------------------------
"""

print("\n--- An Alternative: the backoff Library ---")

import backoff

backoff_schedule = {"remaining_failures": 2}

def log_backoff_attempt(details):
    print(f"  backing off {details['wait']:.3f}s after "
          f"{details['tries']} tries calling {details['target'].__name__}")

@backoff.on_exception(
    backoff.expo,             # exponential backoff strategy (jitter included by default)
    TimeoutError,              # only retry on this exception type
    max_tries=5,
    base=2,
    factor=0.05,
    on_backoff=log_backoff_attempt,
)
def fetch_with_backoff_lib():
    if backoff_schedule["remaining_failures"] > 0:
        backoff_schedule["remaining_failures"] -= 1
        raise TimeoutError("simulated timeout")
    return "backoff-lib success"

print("calling fetch_with_backoff_lib() (fails 2 times, then succeeds):")
print("  result:", fetch_with_backoff_lib())


"""
---------------------------------------------------------------------
7. RETRY THE RIGHT FAILURES: TRANSIENT vs PERMANENT ERRORS  ⭐⭐⭐
---------------------------------------------------------------------
Not every failure deserves a retry. TRANSIENT errors are ones that
might succeed if you just wait and try again: network timeouts, HTTP
429 (rate limited), HTTP 503 (temporarily unavailable), connection
resets. PERMANENT errors will NEVER succeed no matter how many times
you retry: HTTP 400 (bad request - your payload is malformed), HTTP
404 (not found - the resource doesn't exist), HTTP 401/403 (bad
auth). Retrying a permanent error wastes time, delays surfacing a
real bug to a human, and in the worst case can mask a genuine defect
behind a wall of pointless retry logging. Good retry logic explicitly
distinguishes these cases instead of retrying on bare `Exception`.
---------------------------------------------------------------------
"""

print("\n--- Retry the RIGHT Failures: Transient vs Permanent ---")

class TransientAPIError(Exception):
    """429 / 503 / timeout - worth retrying."""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code

class PermanentAPIError(Exception):
    """400 / 404 / 401 - retrying can never help."""
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code

TRANSIENT_STATUS_CODES = {429, 503, 504}
PERMANENT_STATUS_CODES = {400, 401, 403, 404}

def call_api_with_status(status_code):
    """Raises the right exception TYPE based on the simulated status code -
    mirrors how a real HTTP client wrapper should classify errors."""
    if status_code in TRANSIENT_STATUS_CODES:
        raise TransientAPIError(f"HTTP {status_code}", status_code)
    if status_code in PERMANENT_STATUS_CODES:
        raise PermanentAPIError(f"HTTP {status_code}", status_code)
    return "ok"

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.03, min=0.01, max=0.5),
    retry=retry_if_exception_type(TransientAPIError),   # ONLY retries transient errors
    reraise=True,
)
def fetch_page(status_code):
    return call_api_with_status(status_code)

print("simulating a 503 (transient) - tenacity WILL retry it:")
permanent_status_schedule = {"calls": 0}

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.03, min=0.01, max=0.5),
    retry=retry_if_exception_type(TransientAPIError),
    reraise=True,
)
def fetch_that_eventually_succeeds():
    permanent_status_schedule["calls"] += 1
    if permanent_status_schedule["calls"] < 3:
        return call_api_with_status(503)   # transient - retried
    return call_api_with_status(200)       # succeeds on 3rd call

print("  result:", fetch_that_eventually_succeeds())

print("\nsimulating a 404 (permanent) - retry_if_exception_type means")
print("tenacity does NOT catch PermanentAPIError at all, so it fails fast:")
try:
    fetch_page(404)
except PermanentAPIError as e:
    print(f"  failed immediately, no wasted retries: {e} "
          f"(status_code={e.status_code})")
print("  Note: this raised on the FIRST call - a bare `except Exception`")
print("  retry policy would have wasted 3 attempts and several seconds")
print("  retrying a URL that will 404 forever, delaying the real signal")
print("  that the request itself (URL, payload, auth) is broken.")


"""
---------------------------------------------------------------------
8. PUTTING IT TOGETHER: A REALISTIC ETL "FETCH PAGE" CLIENT  ⭐⭐⭐
---------------------------------------------------------------------
A realistic ETL extract step: pull paginated results from a flaky
upstream API. The mocked `fetch_page_from_source` fails with
transient errors a fixed number of times (simulating rate limiting)
before succeeding, all wrapped in a tenacity retry+backoff policy
that only targets transient failures and stays within a retry
"budget" (`stop_after_attempt`) so a truly dead upstream still fails
the pipeline run instead of hanging forever.
---------------------------------------------------------------------
"""

print("\n--- Realistic ETL Example: Fetching Paginated API Data ---")

# Deterministic failure schedule per "page": page 1 fails twice then
# succeeds, page 2 succeeds immediately - reproducible, no real network.
page_failure_schedule = {1: 2, 2: 0}
page_call_counts = {1: 0, 2: 0}

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.02, min=0.01, max=0.3),
    retry=retry_if_exception_type(TransientAPIError),
    reraise=True,
)
def fetch_page_from_source(page_number):
    page_call_counts[page_number] += 1
    remaining = page_failure_schedule[page_number]
    if remaining > 0:
        page_failure_schedule[page_number] -= 1
        raise TransientAPIError(f"HTTP 429 rate limited on page {page_number}", 429)
    # simulated page of extracted records
    return [{"id": page_number * 10 + i, "page": page_number} for i in range(3)]

def extract_all_pages(page_numbers):
    """ETL extract step: pulls each page, letting tenacity handle
    transient retries transparently underneath fetch_page_from_source."""
    all_records = []
    for page_number in page_numbers:
        print(f"  extracting page {page_number}...")
        records = fetch_page_from_source(page_number)
        print(f"    got {len(records)} records after "
              f"{page_call_counts[page_number]} call(s)")
        all_records.extend(records)
    return all_records

extracted = extract_all_pages([1, 2])
print(f"\nfull extract complete: {len(extracted)} total records")
print("sample record:", extracted[0])
print("\nThis is the shape of a real ETL 'extract' step: retry/backoff")
print("logic lives in a decorator on the low-level fetch function, so")
print("the higher-level pipeline code (extract_all_pages) stays clean")
print("and doesn't need to know anything about retries at all.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Naive immediate retry in a loop  -> can worsen an outage ("retry storm")
Exponential backoff formula      -> delay = base * (2 ** attempt)
Max attempts                     -> always cap retries, then raise/give up
Jitter                           -> randomize delay to avoid "thundering
                                     herd" (many clients retrying in sync)
Retry-After header               -> HONOR it when present; server knows
                                     its own recovery time better than you
Hand-rolled decorator            -> functools.wraps + for-loop + try/except
                                     + time.sleep(base * 2**attempt)

tenacity:
    @retry(stop=stop_after_attempt(n),
           wait=wait_exponential(multiplier=..., min=..., max=...),
           retry=retry_if_exception_type(SomeTransientError),
           reraise=True)

backoff:
    @backoff.on_exception(backoff.expo, SomeTransientError,
                          max_tries=n, base=2, factor=...)

Retry these (TRANSIENT)          -> timeouts, HTTP 429, 503, 504,
                                     connection reset
Do NOT retry these (PERMANENT)   -> HTTP 400, 401, 403, 404 - retrying
                                     wastes time and can mask a real bug

ETL pattern -> put retry/backoff on the low-level fetch function;
               keep higher-level pipeline code retry-agnostic.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - RATE LIMITS AND RETRIES
=====================================================================

1. Write a decorator that retries a function on failure with
   exponential backoff, from scratch, without using any third-party
   library.

2. What is a "retry storm," and why can naive immediate retries in a
   tight loop actually make an outage worse instead of better?

3. Given `delay = base_delay * (2 ** attempt)`, walk through the
   actual delay values produced for `base_delay=0.05` across 4
   attempts (attempt 0, 1, 2, 3).

4. Why does the hand-rolled `retry_with_backoff` decorator in this
   file use `@functools.wraps(func)`? What would break (or become
   harder to debug) if it were omitted?

5. What is "jitter" in the context of retry/backoff logic, and what
   specific problem ("thundering herd") does it solve that plain
   exponential backoff does not?

6. What is the `Retry-After` HTTP header, and why should a
   well-behaved client prefer it over its own computed exponential
   backoff delay when the server provides it?

7. How would you rewrite the hand-rolled `retry_with_jitter` decorator
   from this file using the `tenacity` library instead? Which
   `tenacity` arguments correspond to `max_attempts` and `base_delay`?

8. What does `stop_after_attempt(5)` do in `tenacity`, and what
   happens to the underlying exception when all 5 attempts are
   exhausted (see the `reraise=True` argument used in this file)?

9. Compare the `tenacity` and `backoff` libraries' APIs for expressing
   "retry this function up to 5 times with exponential backoff."
   What are the main differences in how you configure each?

10. Why should you NOT retry an HTTP 400 (bad request) or 404 (not
    found) response the same way you'd retry a 429 or 503? What harm
    can blindly retrying on `except Exception` cause in production?

11. In this file's `fetch_page` example, how does
    `retry_if_exception_type(TransientAPIError)` ensure a
    `PermanentAPIError` is never retried, and what does the call site
    see happen instead?

12. In the `extract_all_pages` ETL example, why is it good design to
    put the `@retry` decorator on `fetch_page_from_source` rather
    than wrapping the whole `extract_all_pages` loop in a try/except
    retry block?

13. How would you design a rate-limit-aware API client that checks
    for a `Retry-After` header on a 429 response, but falls back to
    its own exponential backoff with jitter when that header is
    absent?

14. What's the difference between capping retries with a fixed
    `max_attempts` count versus capping total elapsed wall-clock time
    (e.g. "keep retrying for up to 30 seconds")? When might you want
    the latter in a real pipeline?

15. How would you implement exponential backoff for API retries in
    an `asyncio`-based pipeline, where you can't use a blocking
    `time.sleep()` inside the retry loop?
=====================================================================
"""
