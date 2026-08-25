"""
=====================================================================
MOCKING WITH unittest.mock - Mock, MagicMock, patch, and Testing
DB/API-Dependent Code in Isolation - Complete Notes with Executable
Examples
=====================================================================

MOCKING means replacing a real dependency (a network call, a database
connection, a paid third-party API) with a fake stand-in object that
you fully control, for the duration of a single test. The function or
class you're actually testing - the "unit under test" - never knows
the difference; it calls what it thinks is `requests` or a DB
connection, and gets back exactly the response YOU scripted.

An earlier file in this repo already covers `pytest` fixtures,
`@pytest.mark.parametrize`, and basic mocking via pytest's built-in
`monkeypatch` fixture at an introductory level - if you just need to
swap out a single attribute or environment variable for one test,
`monkeypatch` is often the simplest tool for the job. This file goes
DEEPER into the general-purpose `unittest.mock` TOOLKIT itself -
`Mock`, `MagicMock`, `patch()`, `side_effect`, and call assertions -
which is what you reach for once a dependency is more complex than a
single attribute: an object with several methods, a class you need to
stand in for entirely, or a dependency imported and used the way real
production code actually imports and uses it (`import requests` then
`requests.get(...)`, or a DB connection object with `.execute()` /
`.commit()` / context-manager behavior).

WHY mock at all? Because a "unit test" is supposed to test ONE unit of
your own logic in isolation. If that logic calls a real API or a real
database, your test is no longer testing just your logic - it is also
testing the network, the remote server's uptime, and the DB's current
state, all at once. That makes tests:
    - SLOW      (a real HTTP round-trip vs. a microsecond-fast mock)
    - FLAKY     (the network hiccups, the API rate-limits you, the
                 test suite fails for reasons that have nothing to do
                 with a bug in your code)
    - COSTLY    (many APIs charge per call, or have call quotas)
    - UNAVAILABLE in CI  (no test runner should need live prod
                 credentials or an open path to a production DB just
                 to run the test suite)
Mocking swaps the real dependency for a controllable fake, so the
test only ever exercises YOUR code's logic - fast, deterministic, and
runnable anywhere with zero live infrastructure.
=====================================================================
"""

import sys
import time
import types
import sqlite3
import contextlib
from unittest.mock import Mock, MagicMock, patch, call

print("--- Overview ---")
print("Mocking = swap a slow/flaky/costly/unavailable real dependency")
print("(network call, DB, paid API) for a controllable fake object,")
print("so tests exercise ONLY your own code's logic - fast and stable.")


"""
---------------------------------------------------------------------
1. WHY MOCK? ISOLATING THE UNIT UNDER TEST (BEFORE vs AFTER)  ⭐⭐⭐
---------------------------------------------------------------------
"Before" mocking: a test that calls the REAL dependency pays its real
cost every single run - here simulated with `time.sleep` standing in
for real network latency (a real flaky DB/API call would ALSO risk
raising a transient error, unrelated to any bug in your own code).
"After" mocking: the exact same calling code runs against a `Mock`
that returns instantly and ALWAYS returns the same thing - proving
both the speed and the determinism gain.
---------------------------------------------------------------------
"""

print("\n--- Why Mock: Before vs After, Concretely Timed ---")

def real_flaky_db_query(user_id):
    """Stands in for a REAL query hitting a real, possibly slow/flaky DB."""
    time.sleep(0.3)          # simulated real network/DB round-trip latency
    # a genuine version of this could ALSO randomly raise a timeout or
    # connection error here, depending on network conditions that day
    return {"id": user_id, "name": "Alice"}

def get_user_display_name(query_fn, user_id):
    """The actual UNIT UNDER TEST: pure logic, just needs SOME query function."""
    row = query_fn(user_id)
    return row["name"].upper()

print("BEFORE (against the real/slow dependency):")
start = time.perf_counter()
result_before = get_user_display_name(real_flaky_db_query, 7)
elapsed_before = time.perf_counter() - start
print(f"  result: {result_before!r}  (took {elapsed_before:.3f}s)")

print("\nAFTER (against a Mock standing in for the same dependency):")
mock_query_fn = Mock(return_value={"id": 7, "name": "Alice"})   # instant, fixed
start = time.perf_counter()
result_after = get_user_display_name(mock_query_fn, 7)
elapsed_after = time.perf_counter() - start
print(f"  result: {result_after!r}  (took {elapsed_after:.6f}s)")
print(f"\nsame correct result, but ~{elapsed_before / max(elapsed_after, 1e-9):.0f}x")
print("faster, and 100% deterministic - no real DB/network involved.")


"""
---------------------------------------------------------------------
2. Mock() vs MagicMock(): THE CORE DIFFERENCE  ⭐⭐⭐
---------------------------------------------------------------------
Both `Mock` and `MagicMock` let you stub out arbitrary attributes and
method calls. The difference is DUNDER (magic) method support (see
the earlier Magic/Dunder Methods file for what these hooks mean):
`MagicMock` comes with working default implementations of most magic
methods (`__len__`, `__iter__`, `__enter__`/`__exit__`, `__call__`,
etc.) pre-configured; plain `Mock` does NOT implement them at all, so
Python's built-in syntax that relies on a dunder (like `len(obj)`)
breaks on a plain `Mock`. Use `MagicMock` whenever the real object you
are standing in for needs to support one of these protocols.
---------------------------------------------------------------------
"""

print("\n--- Mock() vs MagicMock(): Dunder Method Support ---")

plain_mock = Mock()
try:
    len(plain_mock)                      # len() calls plain_mock.__len__()
except TypeError as e:
    print("len(Mock()) fails:", e)        # Mock has no __len__ implemented

magic_mock = MagicMock()
print("len(MagicMock()):", len(magic_mock))     # __len__ is pre-configured -> 0 by default
magic_mock.__len__.return_value = 3             # you CAN override its result
print("after setting __len__.return_value = 3:", len(magic_mock))

print("\niterating a MagicMock (works because __iter__ is pre-built in):")
magic_mock.__iter__.return_value = iter([1, 2, 3])
print("list(magic_mock):", list(magic_mock))

print("\nthe same iteration attempt on a plain Mock:")
try:
    list(plain_mock)
except TypeError as e:
    print("list(Mock()) fails:", e)
print("\nRule of thumb: need the fake to behave like a container, an")
print("iterable, a context manager, or be callable via dunders? Use")
print("MagicMock. Just need to stub plain attributes/methods? Either")
print("works, but MagicMock is the safer default for that reason.")


"""
---------------------------------------------------------------------
3. AUTO-ATTRIBUTE CREATION: SUPERPOWER AND FOOTGUN  ⭐⭐⭐
---------------------------------------------------------------------
Accessing ANY attribute on a `Mock`/`MagicMock` - even one you never
defined - auto-creates and returns a brand-new child Mock instead of
raising `AttributeError`. Calling that child auto-creates yet another
Mock as its return value. This makes mocks trivially easy to use as
stand-ins for deep, complex objects (`obj.a.b.c()` just works, no
setup needed) - but it is also a genuine, common danger: if the REAL
code under test has a TYPO in an attribute/method name, a real object
would raise `AttributeError` immediately and the test would fail
loudly. Against a bare Mock, that same typo silently "succeeds" -
the Mock happily invents `obj.calculat_total()` as a new child Mock
and returns another Mock, and your test may pass even though the
production code is calling a method that does not exist.
---------------------------------------------------------------------
"""

print("\n--- Auto-Attribute Creation: Superpower ---")

fake_pipeline_config = Mock()
fake_pipeline_config.source.database.host = "db.internal"   # never declared - just works
fake_pipeline_config.source.database.port = 5432
print("auto-created nested attributes:")
print(" host:", fake_pipeline_config.source.database.host)
print(" port:", fake_pipeline_config.source.database.port)
print(" fake_pipeline_config.anything.you.never.defined():",
      fake_pipeline_config.anything.you.never.defined())

print("\n--- Auto-Attribute Creation: The Footgun (a real object vs a bare Mock) ---")

class InvoiceCalculator:
    """The REAL class the code under test depends on."""
    def calculate_total(self, items):
        return sum(items)

def billing_report(calculator, items):
    """Code under test - NOTE the typo: 'calculat_total' is missing an 'e'."""
    return calculator.calculat_total(items)          # BUG: typo, should be calculate_total

print("calling the buggy code against the REAL object (catches the bug):")
try:
    billing_report(InvoiceCalculator(), [10, 20, 30])
except AttributeError as e:
    print(" AttributeError (as expected from a real object):", e)

print("\ncalling the SAME buggy code against a bare Mock() (hides the bug!):")
bare_mock_calculator = Mock()
suspicious_result = billing_report(bare_mock_calculator, [10, 20, 30])
print(" no error raised at all - result is just another auto-created Mock:")
print(" ", suspicious_result)
print(" A test using this mock could easily pass while the real typo bug")
print(" ships straight to production, because the Mock never complains.")

print("\n--- The Fix: spec= and autospec=True ---")
print("`spec=` (or `autospec=True` with patch()) restricts a mock to ONLY")
print("the attributes that actually exist on the real object/class - any")
print("other attribute access raises AttributeError, just like the real thing.")

spec_mock_calculator = Mock(spec=InvoiceCalculator)     # only knows calculate_total
try:
    billing_report(spec_mock_calculator, [10, 20, 30])
except AttributeError as e:
    print(" AttributeError WITH spec= (the fix catches the typo):", e)

print("\ncalling the CORRECT (typo-fixed) code against the spec'd mock works fine:")
def billing_report_fixed(calculator, items):
    return calculator.calculate_total(items)           # fixed: correct method name

spec_mock_calculator.calculate_total.return_value = 999   # stub the real method name
print(" billing_report_fixed result:", billing_report_fixed(spec_mock_calculator, [10, 20, 30]))


"""
---------------------------------------------------------------------
4. .return_value vs .side_effect  ⭐⭐⭐
---------------------------------------------------------------------
`.return_value` sets ONE fixed value every call returns. `.side_effect`
is more powerful and comes in two useful forms:
    - an ITERABLE  -> each successive call returns the NEXT item (and
      raises StopIteration once exhausted) - perfect for simulating a
      sequence of different responses across repeated calls.
    - a value that IS an exception class/instance -> raises it instead
      of returning anything, on that call.
Mixing exceptions into a `side_effect` list/iterable is exactly how you
simulate "the API times out on the first call, then succeeds" -
directly useful for testing retry logic (see the earlier Rate Limits
and Retries file for the exponential-backoff retry decorators this
kind of test would exercise).
---------------------------------------------------------------------
"""

print("\n--- return_value: One Fixed Result ---")

fixed_mock = Mock(return_value=42)
print("fixed_mock():", fixed_mock())
print("fixed_mock() again:", fixed_mock())      # always 42, no matter how many calls

print("\n--- side_effect: A Sequence of Different Results ---")

sequence_mock = Mock(side_effect=[1, 2, 3])
print("call 1:", sequence_mock())
print("call 2:", sequence_mock())
print("call 3:", sequence_mock())
try:
    sequence_mock()                              # sequence exhausted
except StopIteration:
    print("call 4: StopIteration - the side_effect sequence ran out")

print("\n--- side_effect: Raise on a Specific Call (simulating a flaky retry) ---")

flaky_api_mock = Mock(
    side_effect=[
        ConnectionError("timed out (simulated)"),   # 1st call: fails
        {"status": "ok", "data": [1, 2, 3]},           # 2nd call: succeeds
    ]
)

def call_with_one_retry(fn):
    """A tiny retry helper: try once, retry exactly once on failure."""
    try:
        return fn()
    except ConnectionError as e:
        print(f"  first attempt failed ({e}) - retrying once...")
        return fn()

print("simulating: API times out on the first call, succeeds on the retry:")
retry_result = call_with_one_retry(flaky_api_mock)
print("final result after retry logic:", retry_result)
print("flaky_api_mock.call_count:", flaky_api_mock.call_count)   # proves it was called twice


"""
---------------------------------------------------------------------
5. patch() AS A DECORATOR vs AS A CONTEXT MANAGER  ⭐⭐
---------------------------------------------------------------------
`patch()` temporarily replaces an attribute (a function, method, class)
with a Mock for a bounded scope, then automatically restores the
ORIGINAL object afterward - even if the test raises. It can be used
two equivalent ways:
    - as a DECORATOR on a test function - the mock is passed in as an
      extra positional argument, in the same order the patches are
      stacked (bottom-most decorator = first extra argument).
    - as a CONTEXT MANAGER (`with patch(...) as mock_obj:`) - useful
      when you only want the replacement active for PART of a test, or
      want to avoid extra function arguments for a quick one-off patch.
---------------------------------------------------------------------
"""

print("\n--- patch() as a Decorator ---")

@patch("time.sleep")                 # patches the real time.sleep for this function's duration
def run_step_without_really_waiting(mock_sleep):
    time.sleep(5)                     # would normally block for 5 real seconds
    return "step finished", mock_sleep.call_count

status, sleep_calls = run_step_without_really_waiting()
print(f"decorator form -> {status!r}, time.sleep was called {sleep_calls} time(s)")
print("(the whole thing ran instantly - the REAL time.sleep never executed)")

print("\n--- patch() as a Context Manager ---")

with patch("time.sleep") as mock_sleep_cm:
    time.sleep(10)                    # again, would normally block for 10 real seconds
    print("inside the `with` block, time.sleep is mocked:", mock_sleep_cm.called)
print("outside the `with` block, time.sleep is back to the REAL function again.")


"""
---------------------------------------------------------------------
6. PATCH SEMANTICS: PATCH WHERE IT'S LOOKED UP, NOT WHERE DEFINED  ⭐⭐⭐
---------------------------------------------------------------------
This is THE single most common `unittest.mock` mistake. When code does
`import requests` and then calls `requests.get(...)`, that code holds
a reference to the `requests` name INSIDE ITS OWN MODULE's namespace -
a namespace that happens to point at the same real `requests` module
object everyone else imports. `patch("some.path.requests.get")` must
target THAT SAME namespace - the module under test's - not wherever
`requests` itself was originally defined. Patching the wrong path
still "succeeds" with no error from `patch()` itself, but the call
inside the code under test silently keeps using the UNPATCHED,
original object, because it was never looking at the path you patched.

To demonstrate this with a real, runnable dotted path (instead of a
second file on disk), we build a tiny module IN MEMORY below and
register it in `sys.modules`, exactly mirroring a real project layout:

    # myapp/api_client.py  (this is what the module "really" looks like)
    import requests

    def fetch_user_data(user_id):
        response = requests.get(f"https://api.example.com/users/{user_id}")
        ...
---------------------------------------------------------------------
"""

print("\n--- Building an In-Memory Stand-In for myapp/api_client.py ---")

# A stand-in for the `requests` package's `get` function. It deliberately
# raises if it is ever actually reached UNPATCHED, so any demo below that
# forgets to intercept it fails LOUDLY instead of pretending to hit a real
# network - there is no real network access anywhere in this file.
def _unmocked_real_get(*args, **kwargs):
    raise RuntimeError("REAL requests.get reached! (this call was NOT mocked)")

requests_stub = types.ModuleType("requests")
requests_stub.get = _unmocked_real_get

api_client = types.ModuleType("myapp.api_client")
api_client.requests = requests_stub          # models `import requests` inside api_client.py

def fetch_user_data(user_id):
    """The function under test, `myapp.api_client.fetch_user_data`."""
    response = api_client.requests.get(
        f"https://api.example.com/users/{user_id}", timeout=5
    )
    if response.status_code != 200:
        raise RuntimeError(f"API error: {response.status_code}")
    return response.json()

api_client.fetch_user_data = fetch_user_data

myapp = types.ModuleType("myapp")
myapp.api_client = api_client
sys.modules["myapp"] = myapp
sys.modules["myapp.api_client"] = api_client
print("registered `myapp.api_client` in sys.modules, with fetch_user_data() inside.")

print("\n--- CORRECT: patch it where api_client LOOKS IT UP ---")

with patch("myapp.api_client.requests.get") as correctly_patched_get:
    correctly_patched_get.return_value = Mock(
        status_code=200, json=Mock(return_value={"id": 1, "name": "Grace"})
    )
    correct_result = api_client.fetch_user_data(1)
    print("result with the CORRECT patch target:", correct_result)
    print("(the mock intercepted the call - no real requests.get was ever reached)")

print("\n--- WRONG: patch the real `requests` package's own `get` instead ---")

try:
    with patch("requests.get") as wrongly_patched_get:      # patches the WRONG namespace
        wrongly_patched_get.return_value = Mock(status_code=200)
        wrong_result = api_client.fetch_user_data(2)         # still calls OUR stub, unaffected
        print("this line should never print:", wrong_result)
except RuntimeError as e:
    print("as predicted, the wrong-path patch did NOT intercept the call:")
    print(" ", e)
    print(" `patch(\"requests.get\")` patched the real, separate `requests`")
    print(" package - but api_client.fetch_user_data() reads `requests.get`")
    print(" from ITS OWN module namespace (our requests_stub), which was")
    print(" never touched. Lesson: always patch AT THE POINT OF USE.")


"""
---------------------------------------------------------------------
7. CALL ASSERTIONS: DID YOUR CODE CALL THE DEPENDENCY CORRECTLY?  ⭐⭐⭐
---------------------------------------------------------------------
Getting the right RETURN VALUE back isn't the whole story - you often
also need to verify your code called the mocked dependency the right
NUMBER of times, with the right ARGUMENTS. `Mock`/`MagicMock` record
every call automatically:
    .assert_called_once()          -> called exactly once (any args)
    .assert_called_once_with(...)  -> called exactly once, with EXACTLY
                                       these args
    .assert_called_with(...)        -> the MOST RECENT call used exactly
                                       these args
    .call_count                     -> how many times it was called
    .call_args                      -> the args of the LAST call
    .call_args_list                 -> a list of every call's args, in order
This matters a lot for DB code: it's not enough that `execute()`
returned something - you want to prove your code sent the CORRECT
parameterized query, with values passed SEPARATELY as bind parameters
rather than glued into the SQL string (see the earlier Parameterized
Queries & SQL Injection file for why that separation matters).
---------------------------------------------------------------------
"""

print("\n--- Call Assertions on a Mocked DB Connection ---")

def insert_user(connection, user_id, username):
    """A pipeline step: insert one row using a PARAMETERIZED query."""
    connection.execute(
        "INSERT INTO users (id, username) VALUES (?, ?)",
        (user_id, username),
    )
    connection.commit()

mock_connection = MagicMock()          # MagicMock so it could also support `with` later
insert_user(mock_connection, 101, "carol")

mock_connection.execute.assert_called_once()      # called exactly once, don't care about args yet
mock_connection.execute.assert_called_once_with(
    "INSERT INTO users (id, username) VALUES (?, ?)",
    (101, "carol"),
)
mock_connection.commit.assert_called_once()
print("execute() call_count:", mock_connection.execute.call_count)
print("execute() call_args:", mock_connection.execute.call_args)

print("\nproving the query was PARAMETERIZED, not string-built (a security check!):")
sql_used, params_used = mock_connection.execute.call_args.args
assert "?" in sql_used and "101" not in sql_used, "value leaked directly into SQL text!"
print(" SQL text has no embedded user data:", sql_used)
print(" values passed separately as bind params:", params_used)

print("\ncatching a MISMATCHED assertion (a wrong test that should fail loudly):")
try:
    mock_connection.execute.assert_called_with(
        "INSERT INTO users (id, username) VALUES (?, ?)",
        (999, "wrong-user"),        # deliberately wrong - proves assertions really check
    )
except AssertionError as e:
    print(" AssertionError (as expected):", str(e).splitlines()[0])


"""
---------------------------------------------------------------------
8. DATA ENGINEERING USE CASE: MOCKING A DB CONNECTION USED AS A
   CONTEXT MANAGER  ⭐⭐
---------------------------------------------------------------------
Real DB client code is frequently used as a context manager:
`with get_connection() as conn: conn.execute(...)`. That requires the
fake to implement `__enter__`/`__exit__` - another good reason
MagicMock (not plain Mock) is the right default for DB/connection-like
fakes. Combining `spec=` with a real class (here, `sqlite3.Connection`)
keeps the fake honest: it only exposes attributes/dunders the real
connection class actually has.
---------------------------------------------------------------------
"""

print("\n--- Mocking a DB Connection Context Manager ---")

def load_batch(get_connection, rows):
    """A pipeline step that opens a connection, inserts rows, and closes it."""
    with get_connection() as conn:
        for row_id, name in rows:
            conn.execute("INSERT INTO staging (id, name) VALUES (?, ?)", (row_id, name))
        conn.commit()
    return len(rows)

# spec=sqlite3.Connection -> only real Connection attributes/dunders are allowed,
# and sqlite3.Connection genuinely supports the `with ... as` protocol.
mock_conn_instance = MagicMock(spec=sqlite3.Connection)
mock_conn_instance.__enter__.return_value = mock_conn_instance   # `as conn` -> itself
mock_get_connection = Mock(return_value=mock_conn_instance)

rows_to_load = [(1, "alice"), (2, "bob"), (3, "carol")]
loaded_count = load_batch(mock_get_connection, rows_to_load)
print("rows loaded:", loaded_count)
print("execute() called this many times:", mock_conn_instance.execute.call_count)
mock_conn_instance.commit.assert_called_once()
print("commit() call verified.")

print("\nspec= still enforces the real class's surface even here:")
try:
    mock_conn_instance.this_is_not_a_real_sqlite3_method()
except AttributeError as e:
    print(" AttributeError (spec caught a call to a method that doesn't exist):", e)


"""
---------------------------------------------------------------------
9. FULL EXAMPLE: MOCKING AN API CALL - SUCCESS AND ERROR PATHS  ⭐⭐⭐
---------------------------------------------------------------------
Bringing it all together to directly answer "how would you mock an API
call in a test?" - testing `fetch_user_data()` (defined in section 6,
standing in for `myapp/api_client.py`) against THREE scenarios, none
of which touch a real network: a clean 200 success, a non-200 error
response, and a raised exception simulating a timeout.
---------------------------------------------------------------------
"""

print("\n--- Full Example: fetch_user_data() Success Path ---")

with patch("myapp.api_client.requests.get") as mocked_get:
    mocked_get.return_value = Mock(
        status_code=200,
        json=Mock(return_value={"id": 42, "name": "Dave", "active": True}),
    )
    user = api_client.fetch_user_data(42)
    print("fetched user:", user)
    mocked_get.assert_called_once_with(
        "https://api.example.com/users/42", timeout=5
    )
    print("verified requests.get was called with the correct URL and timeout.")

print("\n--- Full Example: fetch_user_data() Error Path (non-200 response) ---")

with patch("myapp.api_client.requests.get") as mocked_get:
    mocked_get.return_value = Mock(status_code=404, json=Mock(return_value={}))
    try:
        api_client.fetch_user_data(9999)
    except RuntimeError as e:
        print("correctly raised on a non-200 response:", e)

print("\n--- Full Example: fetch_user_data() Error Path (simulated timeout) ---")

with patch("myapp.api_client.requests.get") as mocked_get:
    mocked_get.side_effect = TimeoutError("connection timed out (simulated)")
    try:
        api_client.fetch_user_data(1)
    except TimeoutError as e:
        print("correctly propagated a simulated network timeout:", e)

print("\nAll three paths tested fetch_user_data()'s own LOGIC exclusively -")
print("zero real HTTP requests were made anywhere in this file.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Why mock            -> isolate the unit under test from slow/flaky/
                        costly/unavailable real dependencies (network,
                        DB, paid APIs) so tests are fast + deterministic

Mock()               -> stubs attributes/calls, NO magic-method support
MagicMock()          -> same, PLUS working __len__/__iter__/__enter__/
                        __call__/etc. -> use for container/CM/callable fakes

Auto-attributes      -> obj.anything.deeper() just works (no setup) ->
                        but also means a TYPO'd attribute silently
                        "succeeds" instead of raising AttributeError
Fix                  -> Mock(spec=RealClass) / patch(..., autospec=True)
                        restricts the fake to the real object's actual
                        surface -> typos raise AttributeError again

.return_value         -> one fixed result, every call
.side_effect (list)   -> a DIFFERENT result each successive call
.side_effect (exc)    -> raises that exception on that call instead
                        (mix values + exceptions -> simulate "fails
                        once, then succeeds" for retry-logic tests)

patch() as decorator  -> @patch("mod.name")  def test(mock_obj): ...
patch() as context mgr -> with patch("mod.name") as mock_obj: ...

PATCH RULE (the #1 mistake) -> patch the name WHERE IT'S LOOKED UP
    (the module-under-test's own namespace), NEVER where it was
    originally defined -> `patch("myapp.api_client.requests.get")`,
    not `patch("requests.get")`, when api_client did `import requests`

Call assertions       -> .assert_called_once() / .assert_called_with(...)
                        / .assert_called_once_with(...) / .call_count
                        / .call_args / .call_args_list
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - MOCKING WITH unittest.mock
=====================================================================

1. How would you mock an API call in a test? Walk through what you'd
   patch and why, using `fetch_user_data()` from this file as the
   example.

2. Why do we bother mocking dependencies at all instead of just
   running tests against the real database or API?

3. What is the concrete difference between `Mock()` and `MagicMock()`?
   Give an example of something that works on a `MagicMock` but
   raises a `TypeError` on a plain `Mock`.

4. Explain "auto-attribute creation" on a `Mock`. Why is it both
   convenient and dangerous when the code under test has a typo in an
   attribute or method name?

5. How do `spec=` and `autospec=True` fix the typo-hiding problem from
   question 4? What exactly do they restrict?

6. What's the difference between `.return_value` and `.side_effect`?
   Give an example where `.side_effect` is the only one of the two
   that can express what you need.

7. How would you use `.side_effect` to simulate "the API call times
   out on the first attempt, then succeeds on the second," to test
   retry logic?

8. What's the difference between using `patch()` as a decorator versus
   as a context manager? When would you reach for one over the other?

9. Explain the "patch where it's looked up, not where it's defined"
   rule. Using this file's `myapp.api_client` example, why did
   `patch("requests.get")` fail to intercept the call that
   `patch("myapp.api_client.requests.get")` correctly intercepted?

10. If your code does `from requests import get` instead of
    `import requests`, how does that change what path you need to
    patch, and why?

11. How would you verify not just that a mocked DB `execute()` call
    returned successfully, but that it was called with the CORRECT
    parameterized query and bind values? Which `Mock` APIs would you
    use?

12. Why might you use a `MagicMock` (instead of a plain `Mock`) to
    stand in for a database connection that's used in a `with ... as
    conn:` block?

13. What does `mock.assert_called_once_with(...)` check that
    `mock.call_count == 1` alone does not?

14. What happens if you call an assertion method with the wrong
    expected arguments, like `mock.assert_called_with(wrong_args)`
    when the mock was actually called with different arguments?

15. How does mocking in this file differ from what pytest's
    `monkeypatch` fixture gives you for a single-attribute swap - when
    would you reach for `unittest.mock.patch` instead of
    `monkeypatch`?
=====================================================================
"""
