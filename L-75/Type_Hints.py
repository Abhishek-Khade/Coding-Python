"""
=====================================================================
TYPE HINTS - The typing Module for Pipeline Reliability
=====================================================================

A TYPE HINT is an annotation you attach to a variable, a function
parameter, or a function's return value, declaring what type of data
is EXPECTED there - e.g. `def clean_amount(raw: str) -> float:`.

The single most important fact to internalize about type hints, and
one of the most commonly probed "gotcha" questions in Python
interviews: TYPE HINTS DO NOTHING AT RUNTIME. Python's interpreter
does not check them, does not enforce them, and will happily run code
that violates them completely. Hints exist purely as DOCUMENTATION
for humans and as INPUT for external TOOLING - IDEs (autocomplete,
inline errors) and static analyzers like `mypy` or `pyright`, which
read your source code WITHOUT running it and flag mismatches.

This matters enormously for large data pipelines. Pipeline code is
mostly functions calling functions, passing dicts and dataframes and
records between stages written by different people at different
times. Type hints turn the informal, tribal-knowledge "contract"
between pipeline stages - "this function returns a list of dicts
with these three keys" - into something written down, machine-
checkable (by a linter, in CI, before code ships), and visible in
your editor as you write the NEXT stage that consumes it.

Contrast this with `pydantic` (covered separately): pydantic validates
types AT RUNTIME, against real data flowing through your program, and
raises real exceptions when data doesn't match. Type hints alone
never do that - they are a DEV-TIME tool that describes your CODE;
pydantic is a RUNTIME tool that validates your DATA. Confusing the two
is one of the most common mistakes people make when first learning
this feature.
=====================================================================
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, TypedDict, TypeVar, Union
from functools import reduce

print("--- Overview ---")
print("Type hints document what a function expects and returns, but")
print("Python does NOT enforce them at runtime - only external tools")
print("(mypy, pyright) and things like pydantic actually check types.")


"""
---------------------------------------------------------------------
1. BASIC ANNOTATIONS: VARIABLES, PARAMETERS, RETURN TYPES  ⭐⭐⭐
---------------------------------------------------------------------
The syntax is `name: Type` for variables and parameters, and
`-> Type` after the parameter list for a function's return value.
None of this changes how the code RUNS - it's pure metadata attached
to the function/variable for readers and tools.
---------------------------------------------------------------------
"""

print("\n--- Basic Annotations ---")

def clean_amount(raw: str) -> float:
    """Strip currency formatting from a string and parse it as a float.

    This is the canonical pipeline-ingestion signature: raw text in
    (from a CSV cell, an API field, a scraped page) -> a clean numeric
    value out. The hints tell the next engineer EXACTLY what to pass
    and what to expect back, without them having to read the body.
    """
    return float(raw.strip().replace("$", "").replace(",", ""))

row_count: int = 0          # variable annotation - documents intent
total_revenue: float = 0.0  # still just a plain float underneath

print("clean_amount('$1,204.50'):", clean_amount("$1,204.50"))
print("clean_amount(' 99.10 '):", clean_amount(" 99.10 "))

# The annotations are stored on the function object, purely as data -
# this is literally ALL that happens with them at runtime.
print("\nclean_amount.__annotations__:", clean_amount.__annotations__)


"""
---------------------------------------------------------------------
2. THE CRUCIAL GOTCHA: HINTS ARE NOT ENFORCED AT RUNTIME  ⭐⭐⭐
---------------------------------------------------------------------
This is the #1 fact interviewers probe for. Nothing about writing
`raw: str` makes Python check that the caller actually passed a str.
If the wrong type happens to support whatever operations the function
body performs, Python will run it to completion, produce a result,
and never raise an error - even though the type contract was broken.
---------------------------------------------------------------------
"""

print("\n--- Type Hints Are Purely Documentation at Runtime ---")

def add_two(a: int, b: int) -> int:
    """Hinted to take two ints and return an int."""
    return a + b

# Called CORRECTLY, per the hints:
print("add_two(3, 4)  [ints, as hinted]:       ", add_two(3, 4))

# Called with the WRONG type on purpose - strings, not ints. The hint
# says `int`, but Python performs NO check before running the body.
# `+` on two strings is perfectly legal (string concatenation), so the
# function runs to completion with NO error of any kind:
result = add_two("3", "4")
print("add_two('3', '4') [wrong type, no error]:", result, type(result))
print("Python happily ran a function annotated '-> int' and got back")
print("a str - the type hint was silently violated and NOTHING in the")
print("language itself noticed or cared.")

# clean_amount(...) has the same blind spot: pass it something that
# ISN'T a str but happens to support .strip()/.replace() and it will
# run without complaint too. Passing something that does NOT support
# those methods raises an error - but that's the SAME AttributeError
# you'd get with no type hints at all; the hint itself caught nothing.
try:
    clean_amount(1204.50)   # a float, not a str - hint says str
except AttributeError as e:
    print("\nclean_amount(1204.50) still fails, but from the METHOD")
    print("CALL inside the function, not from any type-hint check:", e)


"""
---------------------------------------------------------------------
3. MODERN GENERICS: list[int]/dict[str, float] vs List/Dict  ⭐⭐
---------------------------------------------------------------------
Before Python 3.9, the built-in containers (list, dict, tuple, set)
couldn't be parameterized directly - you had to import capitalized
versions from `typing`: `List[int]`, `Dict[str, float]`. PEP 585
(3.9+) lets you subscript the built-ins directly, which is now the
PREFERRED style; the `typing` aliases still work (for back-compat)
but are considered legacy in new code.
---------------------------------------------------------------------
"""

print("\n--- Modern (PEP 585) Generics vs Legacy typing Aliases ---")

def average_prices_modern(prices: list[float]) -> float:      # preferred, 3.9+
    return sum(prices) / len(prices)

def average_prices_legacy(prices: List[float]) -> float:      # older style
    return sum(prices) / len(prices)

def index_by_sku_modern(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["sku"]: row for row in rows}

def index_by_sku_legacy(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {row["sku"]: row for row in rows}

sample_prices = [19.99, 24.50, 9.99]
print("average_prices_modern:", average_prices_modern(sample_prices))
print("average_prices_legacy:", average_prices_legacy(sample_prices))
print("\nBoth run identically - the two styles describe the exact same")
print("runtime type. Use list[...]/dict[...] in any 3.9+ codebase;")
print("List[...]/Dict[...] mainly shows up in code targeting older")
print("Python or in a codebase that hasn't migrated yet.")


"""
---------------------------------------------------------------------
4. Optional[X] AND X | None: A VALUE THAT MIGHT BE MISSING  ⭐⭐⭐
---------------------------------------------------------------------
`Optional[X]` means "either an X, or None" - it's shorthand for
`Union[X, None]`, and in modern Python is equivalent to `X | None`.
This is the single most common hint in pipeline lookup functions:
"find me a record" legitimately might not find one, and the hint
forces the CALLER to see, right in the signature, that they must
handle a possible None before using the result.
---------------------------------------------------------------------
"""

print("\n--- Optional[X] / X | None: Records That Might Not Exist ---")

_customer_table: dict[int, str] = {101: "Acme Corp", 102: "Globex Inc"}

def find_customer_name(customer_id: int) -> Optional[str]:     # == str | None
    """Looks up a customer; returns None if no record matches the id."""
    return _customer_table.get(customer_id)

def find_customer_name_modern(customer_id: int) -> str | None:  # same meaning
    return _customer_table.get(customer_id)

found = find_customer_name(101)
missing = find_customer_name(999)
print("find_customer_name(101):", found)
print("find_customer_name(999):", missing)

# The HINT alone doesn't stop you from misusing a None downstream -
# see Section 2 - but it documents the possibility so a careful reader
# (or a type checker) catches a missing None-check before it becomes
# a production AttributeError:
try:
    print(missing.upper())      # forgot to check for None first
except AttributeError as e:
    print("\nForgetting the None-check blows up exactly as the")
    print("'Optional' hint warned it might:", e)


"""
---------------------------------------------------------------------
5. Union[X, Y] / X | Y: A VALUE THAT'S LEGITIMATELY SEVERAL TYPES  ⭐⭐⭐
---------------------------------------------------------------------
Some pipeline fields really can arrive as more than one type - e.g. a
flaky upstream API (see the "Parsing API Responses" notes) that
sometimes serializes a price as "19.99" (str) and sometimes as 19.99
(float), depending on which backend served the response. `Union[X, Y]`
- or the modern `X | Y` syntax - documents that the function has to
handle BOTH shapes, rather than silently assuming one.
---------------------------------------------------------------------
"""

print("\n--- Union[X, Y] / X | Y: A Field With More Than One Real Shape ---")

def parse_price(raw: Union[str, float]) -> float:      # == str | float
    """Handles a price field a flaky API sometimes sends as text."""
    if isinstance(raw, str):
        return float(raw.strip().replace("$", ""))
    return float(raw)          # already numeric - just normalize the type

def parse_price_modern(raw: str | float) -> float:     # same meaning, 3.10+
    return parse_price(raw)

api_responses = ["19.99", 24.5, "$8.00", 3]
parsed = [parse_price_modern(p) for p in api_responses]
print("raw API values:", api_responses)
print("parsed as floats:", parsed)
print("\nThe Union hint tells every reader (and mypy) that this field")
print("is UNRELIABLE by design, not a bug to 'fix' by assuming str.")


"""
---------------------------------------------------------------------
6. Callable[[...], ...]: TYPING A PARAMETER THAT IS ITSELF A FUNCTION  ⭐⭐
---------------------------------------------------------------------
Pipelines pass functions around constantly - decorators (see the
Decorators notes) and higher-order "apply this transform" helpers both
take a callable as an argument. `Callable[[ArgTypes...], ReturnType]`
documents exactly what signature that function-argument must have.
(`collections.abc.Callable` is the modern PEP 585-style equivalent,
usable the same way as `typing.Callable`.)
---------------------------------------------------------------------
"""

print("\n--- Callable[[...], ...]: A Parameter That's Itself a Function ---")

def combine_values(operation: Callable[[int, int], int], values: list[int]) -> int:
    """Reduces `values` down to one int using a caller-supplied binary op.

    The hint says: whatever you pass as `operation` must take two ints
    and return an int - e.g. a running total step in an aggregation
    pipeline, without hard-coding whether it sums, multiplies, etc.
    """
    return reduce(operation, values)

def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

quantities = [2, 3, 4, 5]
print("combine_values(add, quantities):     ", combine_values(add, quantities))
print("combine_values(multiply, quantities):", combine_values(multiply, quantities))
print("\nAn IDE, reading the Callable[[int, int], int] hint, will flag")
print("it if you try to pass a function with the wrong shape - e.g.")
print("one that takes a single string argument - before you ever run it.")


"""
---------------------------------------------------------------------
7. GENERICS WITH TypeVar: PRESERVING A TYPE RELATIONSHIP  ⭐⭐
---------------------------------------------------------------------
Sometimes a function's return type depends on its INPUT type, but
isn't fixed to any one concrete type - e.g. "give back the first item
of whatever kind of list you handed me". `TypeVar` lets you name that
relationship once and reuse it, so a type checker knows
`first(list[int]) -> int` and `first(list[str]) -> str` are BOTH valid
uses of the SAME generic function.
---------------------------------------------------------------------
"""

print("\n--- Generics with TypeVar: first(items: list[T]) -> T ---")

T = TypeVar("T")

def first(items: list[T]) -> T:
    """Returns the first element, preserving whatever type T the list holds."""
    if not items:
        raise ValueError("first() called on an empty list")
    return items[0]

print("first([10, 20, 30])   ->", first([10, 20, 30]), " (int in, int out)")
print("first(['a', 'b'])     ->", first(["a", "b"]), " (str in, str out)")
print("first([1.5, 2.5])     ->", first([1.5, 2.5]), " (float in, float out)")

try:
    first([])
except ValueError as e:
    print("\nfirst([]) on an empty list raises, as documented:", e)

print("\nWithout TypeVar you'd have to write `def first(items: list) -> Any`,")
print("which throws away the relationship between input and output type -")
print("a type checker couldn't tell `first([1, 2])` returns an int.")


"""
---------------------------------------------------------------------
8. TypedDict: A PRECISE SHAPE FOR DICT-SHAPED RECORDS  ⭐⭐⭐
---------------------------------------------------------------------
A huge amount of pipeline code passes plain dicts around - one row of
a CSV, one parsed JSON record. A bare `dict` hint says nothing about
WHICH keys exist or what types their values are. `TypedDict` fixes
that: it defines a dict shape with named, typed fields, checkable by
mypy/pyright, WITHOUT the runtime overhead (or validation) of a real
class or a pydantic model - genuinely useful for dict-heavy ETL code
that predates, or sits alongside, pydantic.
---------------------------------------------------------------------
"""

print("\n--- TypedDict: Giving a Dict Record a Precise Shape ---")

class OrderRecord(TypedDict):
    order_id: int
    customer: str
    total: float
    status: str      # e.g. "pending", "shipped", "cancelled"

def summarize_order(order: OrderRecord) -> str:
    """A type checker knows exactly which keys are safe to access here."""
    return f"Order #{order['order_id']} for {order['customer']}: ${order['total']:.2f} ({order['status']})"

sample_order: OrderRecord = {
    "order_id": 5091,
    "customer": "Acme Corp",
    "total": 249.99,
    "status": "shipped",
}
print(summarize_order(sample_order))

# TypedDict is STILL just a plain dict at runtime - a checker enforces
# the shape statically, but Python itself does not:
print("\ntype(sample_order) at runtime is just:", type(sample_order))
malformed: OrderRecord = {"order_id": 1}   # missing keys - mypy would flag this
print("A checker would flag `malformed` as missing keys; Python runs it fine:")
print(malformed)


"""
---------------------------------------------------------------------
9. THE REAL ENFORCEMENT STORY: STATIC CHECKERS vs PYDANTIC  ⭐⭐⭐
---------------------------------------------------------------------
So if Python itself ignores hints (Section 2), where do they actually
pay off? Two DIFFERENT places, and mixing them up is a common mistake:

  STATIC TYPE CHECKERS (mypy, or the newer pyright/ty) read your
  SOURCE CODE without running it, and report type mismatches at
  lint/CI time - e.g. "you called add_two('3', '4') but it's typed to
  take ints" gets flagged BEFORE that code ever reaches production.
  This is a DEV-TIME check on your CODE.

  PYDANTIC (covered separately) validates real DATA at RUNTIME, as it
  flows through your program - a malformed record raises a real
  ValidationError right then and there, whether or not any static
  checker ever ran. This is a RUNTIME check on your DATA.

Static hints alone catch bugs in the codebase; pydantic (or similar)
catches bad data that HAS ALREADY ARRIVED. A robust pipeline typically
uses BOTH: hints + mypy in CI to keep the code itself correct, and
pydantic at the ingestion boundary to keep bad data out.
---------------------------------------------------------------------
"""

print("\n--- Static Checkers (mypy) vs Runtime Enforcement (pydantic) ---")

import importlib.util
import subprocess
import sys

if importlib.util.find_spec("mypy") is not None:
    # mypy IS installed here - actually run it against this very file
    # and show the real result, rather than a simulated one.
    completed = subprocess.run(
        [sys.executable, "-m", "mypy", "--ignore-missing-imports", __file__],
        capture_output=True,
        text=True,
    )
    print("Ran `mypy` on this file for real. Exit code:", completed.returncode)
    print(completed.stdout.strip()[-600:] or completed.stderr.strip()[-600:])
else:
    print("mypy is not installed in this environment, so here is exactly")
    print("what running it against Section 2's `add_two` call would look")
    print("like on a real project (this is REAL mypy output text, just")
    print("not executed live here):")
    print()
    print("  $ mypy pipeline.py")
    print("  pipeline.py:10: error: Argument 1 to \"add_two\" has incompatible")
    print("      type \"str\"; expected \"int\"  [arg-type]")
    print("  pipeline.py:10: error: Argument 2 to \"add_two\" has incompatible")
    print("      type \"str\"; expected \"int\"  [arg-type]")
    print("  Found 2 errors in 1 file (checked 1 source file)")
    print()
    print("Note this is caught WITHOUT ever running the program - purely")
    print("from reading the source and the hints. That's the whole point:")
    print("bugs get caught in CI, before a bad type ever reaches production.")

# Now the CONTRASTING case: pydantic enforcing types on REAL data, at
# RUNTIME - this genuinely runs and genuinely raises on bad input.
try:
    from pydantic import BaseModel, ValidationError

    class OrderModel(BaseModel):
        order_id: int
        customer: str
        total: float
        status: str

    print("\npydantic validating a GOOD record at runtime:")
    good = OrderModel(order_id=5091, customer="Acme Corp", total=249.99, status="shipped")
    print(" ", good)

    print("\npydantic validating a BAD record at runtime (total is text):")
    try:
        OrderModel(order_id=5091, customer="Acme Corp", total="not-a-number", status="shipped")
    except ValidationError as e:
        print("  ValidationError raised for real, on real data:")
        print(" ", str(e).splitlines()[0])
    print("\nThis is the crucial contrast with Section 2: a bare type hint")
    print("let 'add_two(\"3\", \"4\")' run silently; pydantic REFUSES bad data")
    print("the instant it arrives, because it actually checks at runtime.")
except ImportError:
    print("\n(pydantic not installed here - see the pydantic notes file for")
    print("the full runtime-validation story.)")


"""
---------------------------------------------------------------------
10. PUTTING IT TOGETHER: A FULLY TYPE-HINTED extract -> transform ->
    load CHAIN  ⭐⭐⭐
---------------------------------------------------------------------
This is the payoff for large pipelines: when every stage's parameters
and return type are hinted, the DATA CONTRACT between stages is
self-documenting. Anyone (or any IDE) looking at `transform`'s
signature immediately knows what `extract` must hand it, and what
`load` will receive - no need to read every function body to find out.
---------------------------------------------------------------------
"""

print("\n--- A Fully Type-Hinted ETL Chain ---")

class RawRecord(TypedDict):
    id: str
    amount: str          # arrives as text from the source system
    region: str

class CleanRecord(TypedDict):
    id: int
    amount: float
    region: str

def extract(source_rows: list[dict[str, str]]) -> list[RawRecord]:
    """Extract stage: reshape raw source rows into a typed RawRecord list."""
    return [RawRecord(id=r["id"], amount=r["amount"], region=r["region"]) for r in source_rows]

def transform(raw_records: list[RawRecord]) -> list[CleanRecord]:
    """Transform stage: the signature makes the RawRecord -> CleanRecord
    contract explicit - anyone extending this pipeline sees exactly what
    changes shape here (id: str -> int, amount: str -> float)."""
    cleaned: list[CleanRecord] = []
    for rec in raw_records:
        cleaned.append(CleanRecord(
            id=int(rec["id"]),
            amount=clean_amount(rec["amount"]),
            region=rec["region"].upper(),
        ))
    return cleaned

def load(records: list[CleanRecord], destination: dict[int, CleanRecord]) -> int:
    """Load stage: hints document that this MUTATES `destination` in place
    and returns a count - no ambiguity about side effects vs return value."""
    for rec in records:
        destination[rec["id"]] = rec
    return len(records)

raw_source_rows = [
    {"id": "1", "amount": "$120.50", "region": "us-east"},
    {"id": "2", "amount": "$89.00", "region": "eu-west"},
    {"id": "3", "amount": "$310.25", "region": "us-west"},
]

warehouse: dict[int, CleanRecord] = {}
extracted = extract(raw_source_rows)
transformed = transform(extracted)
loaded_count = load(transformed, warehouse)

print("extracted (RawRecord[]):", extracted)
print("\ntransformed (CleanRecord[]):", transformed)
print("\nrows loaded:", loaded_count)
print("warehouse state:", warehouse)
print("\nEvery arrow in extract -> transform -> load is a typed function")
print("boundary. An IDE autocompletes `rec['amount']` as a float only")
print("AFTER transform, never before - the hints make that boundary")
print("visible instead of implicit tribal knowledge.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Basic hint syntax        -> def f(x: int) -> str:  |  count: int = 0

CRUCIAL FACT              -> hints are NOT enforced at runtime; Python
                              runs mismatched-type calls without error

Modern generics (3.9+)    -> list[int], dict[str, float]        (preferred)
Legacy typing aliases     -> List[int], Dict[str, float]        (older code)

Optional[X]  == X | None  -> value might legitimately be missing
Union[X, Y]  == X | Y     -> value is legitimately one of several types

Callable[[int, int], int] -> parameter that is itself a function
TypeVar (T)               -> def first(items: list[T]) -> T: preserves
                              the input/output type relationship
TypedDict                 -> precise, named, typed dict shape - no
                              runtime validation, just a documented shape

REAL enforcement:
    mypy / pyright / ty   -> static analysis of your CODE, dev-time,
                              catches mismatches in CI before deploy
    pydantic               -> runtime validation of your DATA, raises
                              real exceptions on real bad input

Pipeline payoff -> hints make the extract -> transform -> load data
contract self-documenting and IDE-autocomplete-friendly.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - TYPE HINTS & THE typing MODULE
=====================================================================

1. What's the benefit of type hints in large data pipelines? (Straight
   from the syllabus - answer in terms of self-documenting contracts
   between stages, and IDE/tooling support.)

2. Does Python raise any error if you call `add_two("3", "4")` when
   `add_two` is annotated `def add_two(a: int, b: int) -> int:`? What
   actually happens, and why?

3. If type hints aren't enforced by the interpreter, what two
   DIFFERENT mechanisms actually catch type problems in a real
   project, and how do they differ in WHEN they run and WHAT they
   check (your code vs your data)?

4. Explain the difference between `mypy` (or `pyright`) and
   `pydantic` in one sentence each. Why is it a mistake to say "I have
   type hints, so my data is validated"?

5. What's the difference between `List[int]` (from `typing`) and
   `list[int]` (built-in generic)? Which is preferred in modern
   (3.9+) Python, and why would you still see the older style?

6. What does `Optional[str]` mean, and what is it equivalent to using
   the modern `|` syntax? Why is it a good fit for a function like
   `find_customer_name` that looks up a record by id?

7. When would you use `Union[str, float]` (or `str | float`) instead
   of just picking one type? Give a concrete data-pipeline example
   (hint: think about `parse_price` and a flaky upstream API).

8. What does `Callable[[int, int], int]` describe? Write a function
   signature that accepts a two-argument, int-returning function as
   one of its parameters.

9. Explain what a `TypeVar` is for. Why does `def first(items: list[T]) -> T`
   convey more information to a type checker than
   `def first(items: list) -> Any`?

10. What is `TypedDict` for, and how is it different from a full
    class or a pydantic `BaseModel`? Why might dict-heavy ETL code
    prefer it over defining a class for every record shape?

11. Is a `TypedDict` a real, distinct runtime type, or is it still
    just a plain `dict` once your program is running? What does that
    imply about what a `TypedDict` can and cannot catch on its own?

12. Walk through the `extract -> transform -> load` example in this
    file. What does the change from `RawRecord` to `CleanRecord` in
    `transform`'s signature communicate to another engineer reading
    only the function signatures, without reading any function body?

13. If a static type checker like mypy runs entirely without executing
    your code, how can it possibly know that `add_two("3", "4")` is a
    type error? What is it actually analyzing?

14. Describe a situation where a static type checker would report ZERO
    errors on a function, yet the function still crashes (or silently
    misbehaves) in production. What kind of bug is a static checker
    fundamentally unable to catch?

15. How would you combine type hints (with mypy in CI) and pydantic
    models in the SAME pipeline so that they cover each other's blind
    spots? Which one is protecting you from a bad DEPLOY, and which
    one is protecting you from bad DATA?
=====================================================================
"""
