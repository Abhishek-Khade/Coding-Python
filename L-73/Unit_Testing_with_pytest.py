"""
=====================================================================
UNIT TESTING WITH PYTEST - Complete Notes with Executable Examples
=====================================================================

pytest is the de-facto standard testing framework in the Python data
world. It is NOT part of the standard library (you `pip install
pytest`), but it has effectively replaced the builtin `unittest`
module as the default choice almost everywhere, because it lets you
write tests as PLAIN FUNCTIONS with PLAIN `assert` statements instead
of a class hierarchy full of `self.assertEqual(...)`-style methods.

The normal way to use pytest is: you write one or more files named
`test_*.py` (or `*_test.py`), each containing plain `def test_xxx():`
functions, and you run the `pytest` command from your shell in that
directory. pytest auto-discovers those files, auto-discovers those
functions, runs each one, and reports a pass/fail summary - none of
that requires an `if __name__ == "__main__":` block or any code that
calls itself.

This repo's notes files, however, are all a single, self-contained
`python3 thisfile.py` script by house style - so this file does
something slightly unusual for a pytest lesson: it defines a real,
idiomatic pytest test suite (real fixtures, real `assert`, real
`pytest.raises`, real `@pytest.mark.parametrize`, real mocking) right
here in this module, and then, at the bottom, calls pytest's own
programmatic entry point - `pytest.main()` - ON ITSELF, so running
`python3 Unit_Testing_with_pytest.py` produces genuine pytest output
(the same "collecting... PASSED/FAILED" report you'd see from the
`pytest` CLI) without needing a separate shell invocation. Everything
about the tests themselves is 100% ordinary, transferable pytest -
only the "run it" step at the very end is non-standard.
=====================================================================
"""

import sys
import sqlite3
import unittest
from unittest.mock import patch

import requests
import pytest


print("--- Overview ---")
print("pytest = write plain `test_` functions with plain `assert` -")
print("no special assertion methods, no boilerplate class required.")
print("This file both DEFINES a real pytest suite and RUNS it for")
print("real, via pytest.main(), at the very bottom of the script.")


# =====================================================================
# THE "LIBRARY" UNDER TEST
#
# Everything below this comment and above SECTION 1 is ordinary
# production-style code - NOT test code. It's the small ETL-flavored
# library that the rest of this file will actually unit test.
# =====================================================================

def clean_price(raw_price):
    """
    Clean a messy, human/export-formatted price string into a float.

    Real ETL price columns show up looking like "$1,234.56", " 19.99 ",
    or "(12.00)" (accounting notation for a negative number) - and
    sometimes outright garbage from a bad export. This function is a
    perfect unit-testing target because it's PURE: no I/O, no shared
    state, no side effects - same input always produces the same
    output (or the same exception), which is exactly what makes a
    function cheap and reliable to unit test in isolation.
    """
    if raw_price is None:
        raise ValueError("cannot clean a None price")

    text = str(raw_price).strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):   # accounting negative
        negative = True
        text = text[1:-1]
    text = text.replace("$", "").replace(",", "").strip()

    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"could not parse a price from {raw_price!r}") from None

    return -value if negative else value


class Deduplicator:
    """
    Deduplicates a stream of records by a caller-supplied KEY function,
    preserving first-seen order - the same "dedupe while preserving
    order" logic that comes up constantly when merging incremental ETL
    batches that may reprocess the same source rows more than once.
    """

    def __init__(self, key_func):
        self._key_func = key_func
        self._seen_keys = set()
        self.duplicate_count = 0

    def add(self, record):
        """Return True if `record` is new (kept); False if it was a duplicate."""
        key = self._key_func(record)
        if key in self._seen_keys:
            self.duplicate_count += 1
            return False
        self._seen_keys.add(key)
        return True

    def dedupe(self, records):
        return [r for r in records if self.add(r)]


def get_total_spent(conn, customer_id):
    """
    Sum the `amount` column of an `orders` table for one customer,
    given an ALREADY-OPEN DB-API connection.

    That one design choice - accepting a connection as an argument
    instead of opening a hardcoded connection to a specific database
    inside the function - is what makes this function testable at
    all. It's the same "dependency injection" idea data engineers rely
    on constantly: the function doesn't care whether `conn` points at
    production Postgres or a throwaway in-memory sqlite3 database, as
    long as it speaks the DB-API 2.0 cursor/execute contract.
    """
    cursor = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE customer_id = ?",
        (customer_id,),
    )
    (total,) = cursor.fetchone()
    return total


def fetch_current_usd_to_eur_rate():
    """
    Call a REAL external exchange-rate API and return the USD->EUR
    rate. This stands in for any external dependency at all - a REST
    API, a third-party SDK call, an S3 read - that a unit test must
    NEVER actually reach out to over the network: real calls are slow,
    can fail for reasons unrelated to your code (rate limits, outages,
    DNS), and can return a DIFFERENT result each time they run, which
    makes a "unit" test non-deterministic - the opposite of the point.
    """
    response = requests.get("https://api.example.com/rates/USD_EUR", timeout=5)
    response.raise_for_status()
    return response.json()["rate"]


# =====================================================================
# PYTEST FIXTURES
#
# Fixtures are plain functions decorated with @pytest.fixture. Any
# test function that wants one simply names it as a PARAMETER - pytest
# matches the name, calls the fixture function, and hands the test
# whatever it returns (or yields).
# =====================================================================

@pytest.fixture
def orders_db():
    """
    Provide a fresh, fast, fully isolated in-memory sqlite3 connection,
    pre-seeded with an `orders` table, to every test that asks for it
    by name.

    THIS is the concrete answer to the syllabus's question "how do you
    unit test a function that reads from a database?": you do NOT
    point the test at the real production database (slow, shared
    across the whole team, and one bad test run could leave garbage
    rows behind). Instead you point it at a tiny, throwaway,
    in-memory database that satisfies the exact same DB-API contract
    (`conn.execute(...)`, `cursor.fetchone()`) and is seeded with
    exactly the rows a given test needs - fast, deterministic, and
    impossible to pollute anything real.

    # In production, get_total_spent() would instead be handed a real
    # connection, e.g.:
    #     conn = psycopg2.connect(host="warehouse.internal", dbname="orders")
    # The function itself never changes between the two - only what
    # you inject into it during a test differs.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL)"
    )
    conn.executemany(
        "INSERT INTO orders (customer_id, amount) VALUES (?, ?)",
        [(1, 19.99), (1, 5.00), (2, 100.00)],
    )
    conn.commit()
    print("  [orders_db fixture] seeded in-memory sqlite3 db with 3 rows")

    yield conn                     # <- the test itself runs right here

    print("  [orders_db fixture] tearing down: closing connection")
    conn.close()                    # <- teardown: always runs, even if the test failed


# =====================================================================
# THE ACTUAL TEST FUNCTIONS
#
# pytest discovers any function in this module named `test_*` - note
# there is nothing special about how these are defined; they are
# ordinary module-level functions, discoverable regardless of HOW this
# module gets imported (directly as a script, or by pytest itself).
# =====================================================================

def test_clean_price_strips_dollar_sign_and_commas():
    assert clean_price("$1,234.56") == 1234.56


def test_clean_price_handles_plain_number_with_whitespace():
    assert clean_price(" 19.99 ") == 19.99


def test_clean_price_handles_accounting_negative_notation():
    assert clean_price("(12.00)") == -12.00


def test_clean_price_raises_valueerror_on_garbage():
    with pytest.raises(ValueError):
        clean_price("garbage")


def test_clean_price_raises_valueerror_on_none():
    with pytest.raises(ValueError):
        clean_price(None)


@pytest.mark.parametrize(
    "raw_price, expected",
    [
        ("$1,234.56", 1234.56),
        (" 19.99 ", 19.99),
        ("(12.00)", -12.00),
        ("$0.00", 0.0),
        ("2,000", 2000.0),
    ],
)
def test_clean_price_parametrized(raw_price, expected):
    assert clean_price(raw_price) == expected


def test_deduplicator_removes_duplicates_preserving_order():
    dedup = Deduplicator(key_func=lambda record: record["id"])
    records = [{"id": 1}, {"id": 2}, {"id": 1}, {"id": 3}, {"id": 2}]
    assert dedup.dedupe(records) == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_deduplicator_tracks_duplicate_count():
    dedup = Deduplicator(key_func=lambda record: record)
    for item in ["a", "b", "a", "a", "c"]:
        dedup.add(item)
    assert dedup.duplicate_count == 2


def test_get_total_spent_uses_orders_db_fixture(orders_db):
    print("  [test] running against the seeded in-memory fixture db")
    assert get_total_spent(orders_db, customer_id=1) == pytest.approx(24.99)
    assert get_total_spent(orders_db, customer_id=2) == pytest.approx(100.00)


def test_get_total_spent_returns_zero_for_unknown_customer(orders_db):
    assert get_total_spent(orders_db, customer_id=999) == 0


def test_fetch_rate_with_unittest_mock_patch():
    """Replace requests.get itself so no real network call is ever made."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"rate": 0.92}
        mock_get.return_value.raise_for_status.return_value = None
        rate = fetch_current_usd_to_eur_rate()
    assert rate == 0.92
    mock_get.assert_called_once()


def test_fetch_rate_with_monkeypatch(monkeypatch):
    """monkeypatch is pytest's OWN built-in fixture for exactly this job."""
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rate": 0.87}

    def fake_get(url, timeout=5):
        return FakeResponse()

    monkeypatch.setattr("requests.get", fake_get)
    assert fetch_current_usd_to_eur_rate() == 0.87


class LegacyStyleDeduplicatorTests(unittest.TestCase):
    """
    The OLDER `unittest.TestCase`-based style, shown briefly for
    contrast. pytest can discover and run these too (it has native
    unittest support), but modern, idiomatic pytest code almost always
    prefers plain functions + bare `assert` - less boilerplate, no
    self.assertX(...) zoo of methods to remember, and pytest's
    assertion-rewriting gives introspection at least as good.
    """

    def test_add_returns_true_only_for_a_new_key(self):
        dedup = Deduplicator(key_func=lambda r: r)
        self.assertTrue(dedup.add("a"))
        self.assertFalse(dedup.add("a"))


def _narrative_demo():
    """
    Walks through the concepts above with live, printed output. Kept
    in its own function (rather than flat module-level code) and
    called exactly once, from the `if __name__ == "__main__":` guard
    at the bottom - see SECTION 8 for why that matters here.
    """

    """
    ---------------------------------------------------------------------
    1. TEST ORGANIZATION CONVENTIONS  ⭐
    ---------------------------------------------------------------------
    pytest's default auto-discovery rules:
        - FILES named `test_*.py` or `*_test.py`
        - FUNCTIONS named `test_*` inside those files
        - CLASSES named `Test*` (plain classes) - OR any subclass of
          `unittest.TestCase`, regardless of its name
    Two competing styles exist:
        - modern pytest style: plain functions, bare `assert`
        - older `unittest.TestCase` style: a class per test suite,
          methods named `test_*`, and `self.assertEqual(...)` /
          `self.assertTrue(...)` / etc. instead of bare `assert`
    pytest happily runs BOTH styles in the same run (see
    `LegacyStyleDeduplicatorTests` above), which is one reason it
    became the standard: it's a strict superset of `unittest`.
    ---------------------------------------------------------------------
    """
    print("\n--- Test Organization Conventions ---")
    print("File naming:      test_*.py  or  *_test.py")
    print("Function naming:  def test_*():")
    print("Class naming:     class Test*  (or any unittest.TestCase subclass)")
    print("This file intentionally violates the FILE naming rule - see")
    print("section 8 below for how we tell pytest to collect it anyway.")

    """
    ---------------------------------------------------------------------
    2. THE LIBRARY UNDER TEST, EXERCISED DIRECTLY  ⭐
    ---------------------------------------------------------------------
    Before writing tests FOR something, it helps to see it working
    correctly in the first place. None of the calls below are pytest
    tests - they're just this script proving the library behaves as
    the tests (defined above, and run for real in section 8) assert.
    ---------------------------------------------------------------------
    """
    print("\n--- The Library Under Test ---")
    print("clean_price('$1,234.56') ->", clean_price("$1,234.56"))
    print("clean_price('(12.00)')   ->", clean_price("(12.00)"))

    dedup = Deduplicator(key_func=lambda r: r["id"])
    sample = [{"id": 1}, {"id": 2}, {"id": 1}]
    print("Deduplicator.dedupe(...) ->", dedup.dedupe(sample))
    print("duplicate_count          ->", dedup.duplicate_count)

    demo_conn = sqlite3.connect(":memory:")
    demo_conn.execute("CREATE TABLE orders (id INTEGER, customer_id INTEGER, amount REAL)")
    demo_conn.execute("INSERT INTO orders VALUES (1, 7, 42.50)")
    print("get_total_spent(demo db, customer 7) ->", get_total_spent(demo_conn, 7))
    demo_conn.close()

    """
    ---------------------------------------------------------------------
    3. PLAIN assert IS ENOUGH: pytest'S ASSERTION REWRITING  ⭐⭐⭐
    ---------------------------------------------------------------------
    Older frameworks (including unittest) need special assertion
    methods - `self.assertEqual(a, b)`, `self.assertIn(a, b)`,
    `self.assertTrue(x)` - specifically so the failure message can show
    WHAT was compared. pytest does not need any of that: it rewrites
    the bytecode of every `assert` statement inside a test module at
    IMPORT time, so a plain `assert a == b` can still print a full,
    detailed diff of `a` and `b` on failure. This is a genuine design
    advantage of pytest, not just a style preference - you get the
    SAME rich failure output with far less code to write and remember.
    ---------------------------------------------------------------------
    """
    print("\n--- Plain assert Is Enough (pytest's Assertion Rewriting) ---")
    print("unittest style: self.assertEqual(clean_price('$5'), 5.0)")
    print("pytest style:                assert clean_price('$5') == 5.0")
    print("Both work - but pytest rewrites plain `assert` at import time")
    print("so a FAILING `assert clean_price('$5') == 6.0` would still")
    print("print something like:  assert 5.0 == 6.0  (full value diff),")
    print("with no special assertion method required at all.")

    """
    ---------------------------------------------------------------------
    4. pytest.raises: ASSERTING THAT CODE RAISES  ⭐⭐⭐
    ---------------------------------------------------------------------
    `with pytest.raises(SomeException):` is how you assert that a
    block of code raises a specific exception - and, critically, the
    test FAILS if the block does NOT raise. Compare that to a naive,
    hand-rolled try/except "test", which is a classic, easy-to-write
    bug: if you forget the explicit `assert False` in the "no exception
    happened" path, the test can NEVER fail, no matter what the code
    under test actually does.
    ---------------------------------------------------------------------
    """
    print("\n--- pytest.raises: Asserting That Code Raises ---")

    def naive_and_buggy_exception_check(raw_price):
        # BUGGY: if clean_price(...) does NOT raise, execution simply
        # falls through here with NOTHING asserted at all - this
        # "test" can pass even when the function is completely broken.
        try:
            clean_price(raw_price)
        except ValueError:
            print("  naive check: got ValueError, as expected")

    print("calling the buggy checker with input that should raise:")
    naive_and_buggy_exception_check("garbage")
    print("calling the buggy checker with input that should NOT raise:")
    naive_and_buggy_exception_check("19.99")   # no exception, no error printed,
    print("  ^ nothing printed above and nothing failed - the bug in")
    print("    naive_and_buggy_exception_check() silently 'passed' even")
    print("    though it asserted absolutely nothing that time.")

    print("\nthe FIXED, idiomatic version (this is a REAL pytest test,")
    print("test_clean_price_raises_valueerror_on_garbage, defined above):")
    with pytest.raises(ValueError) as exc_info:
        clean_price("garbage")
    print("  pytest.raises caught:", exc_info.value)
    print("  and if clean_price('garbage') had NOT raised, pytest.raises")
    print("  itself would have failed the test with a clear message -")
    print("  no `assert False` to forget.")

    """
    ---------------------------------------------------------------------
    5. @pytest.fixture: SHARED SETUP/TEARDOWN - TESTING DB CODE  ⭐⭐⭐
    ---------------------------------------------------------------------
    This directly answers the syllabus question: "how do you unit test
    a function that reads from a database?" You do not run it against
    the real database. You give it a REAL, but disposable, database
    connection that satisfies the same interface - here, an in-memory
    sqlite3 connection built and torn down by the `orders_db` fixture
    (defined above `@pytest.fixture`). Any test that names `orders_db`
    as a parameter gets its OWN fresh, seeded connection; the `yield`
    inside the fixture is what splits "setup" (before yield) from
    "teardown" (after yield) - teardown runs after the test finishes,
    pass OR fail.
    ---------------------------------------------------------------------
    """
    print("\n--- @pytest.fixture: Testing DB-Reading Code ---")
    print("orders_db fixture setup  -> CREATE TABLE + seed 3 rows")
    print("                             (yield hands the connection to the test)")
    print("orders_db fixture teardown -> conn.close() runs AFTER the test")
    print("See test_get_total_spent_uses_orders_db_fixture() for the real")
    print("test using it - it will run for real, with its print output")
    print("visible, in section 8's pytest run below.")

    """
    ---------------------------------------------------------------------
    6. @pytest.mark.parametrize: ONE TEST BODY, MANY CASES  ⭐⭐⭐
    ---------------------------------------------------------------------
    Without parametrize, testing 5 messy price strings means writing 5
    near-identical test functions (or one giant test that loses which
    specific case failed). @pytest.mark.parametrize runs the SAME test
    body once per (input, expected) pair, and reports each one as its
    OWN pass/fail line - no duplicated test code, and a failure tells
    you exactly which input broke.
    ---------------------------------------------------------------------
    """
    print("\n--- @pytest.mark.parametrize: One Test, Many Cases ---")
    cases = [
        ("$1,234.56", 1234.56),
        (" 19.99 ", 19.99),
        ("(12.00)", -12.00),
        ("$0.00", 0.0),
        ("2,000", 2000.0),
    ]
    for raw_price, expected in cases:
        print(f"  clean_price({raw_price!r}) == {expected} ->", clean_price(raw_price) == expected)
    print("test_clean_price_parametrized() above runs exactly this table")
    print("as 5 separate, individually-reported pytest test cases.")

    """
    ---------------------------------------------------------------------
    7. MOCKING EXTERNAL DEPENDENCIES: patch AND monkeypatch  ⭐⭐⭐
    ---------------------------------------------------------------------
    A "unit" test must not depend on a real external system - a live
    API, in this case. `unittest.mock.patch` and pytest's own built-in
    `monkeypatch` fixture both let you swap out a real function
    (`requests.get` here) for a fake, controlled stand-in for the
    duration of one test, so the test is fast, deterministic, and works
    with no network at all.
    ---------------------------------------------------------------------
    """
    print("\n--- Mocking External Dependencies ---")
    print("unittest.mock.patch('requests.get') and pytest's monkeypatch")
    print("fixture both swap out requests.get for a fake before the call")
    print("- neither ever touches the real network. Demonstrating live:")
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"rate": 0.92}
        mock_get.return_value.raise_for_status.return_value = None
        print("  fetch_current_usd_to_eur_rate() (patched) ->", fetch_current_usd_to_eur_rate())

    print("\nWithout mocking, calling this function for real would look")
    print("like the code below - shown here, but deliberately never")
    print("actually executed unmocked in this file (that's the whole point):")
    print('    response = requests.get("https://api.example.com/rates/USD_EUR")')
    print('    return response.json()["rate"]')
    print("See test_fetch_rate_with_unittest_mock_patch() and")
    print("test_fetch_rate_with_monkeypatch() above for the two real,")
    print("equivalent, idiomatic versions of this test.")


print(
    "\n--- Sections 1-7: Library, Assertions, Raises, Fixtures, "
    "Parametrize, Mocking ---"
)


"""
---------------------------------------------------------------------
8. RUNNING THE SUITE FOR REAL: pytest.main() FROM CODE  ⭐⭐
---------------------------------------------------------------------
The normal way to run this suite is from a shell:
    $ pytest Unit_Testing_with_pytest.py -v
`pytest.main(args)` is the REAL, documented, programmatic equivalent -
the same entry point tools like tox, CI runners, and IDE test panels
call under the hood - so calling it here makes `python3 thisfile.py`
produce genuine pytest collection and genuine pytest pass/fail output,
with no separate CLI invocation required.

Two things are worth understanding about doing this from INSIDE the
very file being tested:

  1. This filename doesn't match pytest's default `test_*.py` /
     `*_test.py` discovery pattern (it can't - the repo's style guide
     requires one plain, descriptively-named `python3`-runnable
     file). `-o python_files=*.py` tells pytest, just for this run,
     "collect this file regardless of its name" - everything else
     about collection stays genuine default pytest behavior.

  2. `pytest.main([__file__, ...])` makes pytest IMPORT this file
     again, as a fresh module, purely to discover its `test_*`
     functions - that's a real, separate import, distinct from this
     module's `__main__` run. The `if __name__ == "__main__":` guard
     below is what stops THAT reimport from also re-triggering this
     exact `pytest.main()` call and recursing forever: on the
     reimport, `__name__` is the module's real name, not
     `"__main__"`, so this entire block is simply skipped - only the
     library code, fixtures, and test functions above (all needed for
     collection) get redefined, silently, with no printed output.
---------------------------------------------------------------------
"""

if __name__ == "__main__":
    _narrative_demo()

    print("\n--- Running the Real pytest Suite (pytest.main(), live) ---")
    exit_code = pytest.main([__file__, "-v", "-s", "-o", "python_files=*.py"])

    print(f"\npytest.main() returned exit code: {int(exit_code)}")
    if int(exit_code) == 0:
        print("ALL TESTS PASSED.")
    else:
        print("SOME TESTS FAILED - see the -v output above for details.")

    """
    =====================================================================
    QUICK REFERENCE
    =====================================================================
    File naming     -> test_*.py or *_test.py     (auto-discovered)
    Function naming -> def test_*():                (auto-discovered)
    Class naming    -> class Test*  /  any unittest.TestCase subclass

    assert a == b                  -> plain assert; pytest rewrites it
                                       for a full diff on failure - no
                                       self.assertEqual(...) needed
    with pytest.raises(ValueError): -> asserts a block RAISES; the test
        risky_call()                   fails if it does NOT raise

    @pytest.fixture                -> shared setup/teardown; use `yield`
    def thing():                       to split setup (before) from
        ...                             teardown (after) the test
        yield value
        ...teardown...

    @pytest.mark.parametrize(       -> run ONE test body once per
        "a,b", [(1, 2), (3, 4)])       (a, b) pair - no duplicated code
    def test_x(a, b): ...

    unittest.mock.patch("mod.fn")  -> swap out a real dependency for a
    monkeypatch.setattr(...)          fake for the life of one test -
                                       never touch a real DB/API in a
                                       unit test

    "How do you unit test a function that reads from a database?"
        -> inject the connection (don't hardcode it), and test against
           a fast, disposable, in-memory database (sqlite3 here) that
           satisfies the same interface as the real one.
    =====================================================================
    """
    print("\n--- Quick Reference (see comment block above) ---")

    sys.exit(int(exit_code))


"""
=====================================================================
INTERVIEW QUESTIONS - UNIT TESTING WITH PYTEST
=====================================================================

1. How do you unit test a function that reads from a database?

2. What's the benefit of type hints in large data pipelines? (Related
   testing angle: how do type hints and unit tests complement each
   other in catching bugs?)

3. How would you mock an API call in a test?

4. Why doesn't pytest require special assertion methods like
   `self.assertEqual()`, the way `unittest.TestCase` does? What
   mechanism lets a plain `assert a == b` still produce a detailed
   failure message?

5. Walk through what `pytest.raises(ValueError)` actually asserts.
   What happens if the code inside the `with` block does NOT raise
   at all?

6. What's wrong with `naive_and_buggy_exception_check()` in this file
   - specifically, what happens when you call it with input that does
   NOT raise an exception, and why is that a dangerous kind of test
   bug?

7. What is a pytest fixture, and what problem does `@pytest.fixture`
   solve that copy-pasting the same setup code into every test
   function does not?

8. In the `orders_db` fixture, what is the purpose of `yield` instead
   of `return`? What runs before the `yield` versus after it, and
   when does the "after" part actually execute?

9. Why is it safe (and preferable) to test `get_total_spent()` against
   an in-memory sqlite3 database instead of the real production
   database? What design choice in `get_total_spent()` itself makes
   that possible?

10. What does `@pytest.mark.parametrize` do, and why is it better than
    writing five near-identical `test_clean_price_case1()`,
    `test_clean_price_case2()`, ... functions?

11. What's the difference between using `unittest.mock.patch` and
    pytest's `monkeypatch` fixture to replace `requests.get` in a
    test? When might you prefer one over the other?

12. Why must a genuine UNIT test never make a real network call or hit
    a real database? What kinds of failures does that protect you
    from?

13. `LegacyStyleDeduplicatorTests` in this file is a `unittest.TestCase`
    subclass, not a plain function - will pytest actually discover and
    run it? Why or why not, given that its class name doesn't start
    with "Test" the way a plain pytest test class would need to?

14. What naming conventions does pytest use, by default, to
    auto-discover test files, test functions, and test classes?

15. If `test_clean_price_parametrized` has 5 parametrized cases and one
    of them fails, what does pytest's output tell you about WHICH
    input failed, versus a single test function that loops over all 5
    inputs internally?
=====================================================================
"""
