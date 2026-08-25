"""
=====================================================================
JSON HANDLING - Nested JSON Parsing & Flattening (Complete Notes)
=====================================================================

JSON (JavaScript Object Notation) is the de facto interchange format
for REST APIs, event streams, and semi-structured data lakes. As a
Data Engineer you spend a huge fraction of your time doing exactly
one thing to JSON: turning something DEEPLY NESTED (objects inside
objects, lists of objects) into something FLAT and TABULAR, because
that's what a database table, a Pandas DataFrame, or a Parquet file
actually wants.

Python's stdlib `json` module gives you FOUR core functions, which
split cleanly along two axes:

    STRING <-> OBJECT   vs   FILE <-> OBJECT
    dumps() / loads()        dump() / load()

("s" suffix = "string"). Everything else - custom serializers for
types JSON doesn't natively support (datetime, Decimal, custom
classes), pretty-printing, deterministic key ordering - is built on
top of those four functions via keyword arguments.

The genuinely hard interview material isn't the four functions
though - it's REAL nested JSON. An API response for a single "order"
might have a nested "customer" object, a nested "address" object
inside THAT, and a LIST of "line item" objects, each with its own
nested "product" object. Being able to (a) manually walk that
structure, (b) write a general-purpose RECURSIVE FLATTENER for it,
and (c) know when to instead reach for `pandas.json_normalize()` are
the three skills this file drills.
=====================================================================
"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pandas as pd

print("--- Overview ---")
print("json.dumps/loads  <-> strings.   json.dump/load  <-> files.")
print("The real interview skill is FLATTENING nested dicts/lists into")
print("a tabular shape a DataFrame or SQL table can consume.")


"""
---------------------------------------------------------------------
1. dumps/loads (STRING) vs dump/load (FILE)  ⭐⭐⭐
---------------------------------------------------------------------
Easy to mix up under interview pressure - the mnemonic is: the
variant WITHOUT the "s" writes/reads a FILE-LIKE object directly
(you pass it an open file handle); the variant WITH the "s" produces
or consumes a plain Python `str`.
---------------------------------------------------------------------
"""

print("\n--- dumps/loads vs dump/load ---")

record = {"order_id": 1001, "status": "shipped", "total": 59.99}

# dumps(): Python object -> JSON STRING
json_string = json.dumps(record)
print("json.dumps() ->", repr(json_string), type(json_string))

# loads(): JSON STRING -> Python object
round_tripped = json.loads(json_string)
print("json.loads()  ->", round_tripped, type(round_tripped))

# dump(): Python object -> written directly into a FILE
tmp_dir = tempfile.mkdtemp(prefix="json_handling_")
file_path = os.path.join(tmp_dir, "record.json")
with open(file_path, "w") as f:
    json.dump(record, f)          # note: no "s" - takes a file handle, returns None

# load(): FILE -> Python object, read directly (no manual .read() needed)
with open(file_path, "r") as f:
    loaded_from_file = json.load(f)
print("json.dump()/json.load() round trip ->", loaded_from_file)

os.remove(file_path)
os.rmdir(tmp_dir)
print("(temp file cleaned up)")


"""
---------------------------------------------------------------------
2. USEFUL SERIALIZATION KWARGS: indent, sort_keys, default  ⭐⭐⭐
---------------------------------------------------------------------
`indent=` pretty-prints (invaluable for logs/debugging - never ship
un-indented JSON to a human). `sort_keys=True` makes output
DETERMINISTIC, which matters for diffing JSON in tests/version
control. `default=` is the escape hatch for values JSON has no
native representation for - most commonly `datetime` objects, which
`json.dumps` cannot serialize out of the box.
---------------------------------------------------------------------
"""

print("\n--- indent=, sort_keys=, and default= ---")

pretty = json.dumps({"b": 2, "a": 1, "c": 3}, indent=2, sort_keys=True)
print("indent=2, sort_keys=True:")
print(pretty)

# BUGGY: datetime is not one of JSON's native types (object, array,
# string, number, bool, null) - json.dumps has no idea how to
# represent it and raises TypeError.
event = {"event": "order_placed", "at": datetime.now(timezone.utc)}
try:
    json.dumps(event)
except TypeError as e:
    print("\nError serializing a raw datetime:", e)

# FIXED: default= is called on any object json.dumps doesn't know how
# to handle, and must return something JSON-serializable. `str` is
# the simplest universal fallback - it calls str() on the datetime,
# producing its ISO-ish repr.
fixed_json = json.dumps(event, default=str)
print("\nfixed with default=str:", fixed_json)

# A more precise fixer targeting datetimes specifically (isoformat is
# the standard, parseable-back-out representation used by most APIs):
def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

print("fixed with a custom default= (isoformat):", json.dumps(event, default=json_default))


"""
---------------------------------------------------------------------
3. PARSING GENUINELY NESTED JSON (API-RESPONSE SHAPE)  ⭐⭐⭐
---------------------------------------------------------------------
Real API payloads nest OBJECTS inside objects and LISTS of objects.
Here's an "order" shaped exactly like something an e-commerce API
would return: a nested customer object (with a nested address object
inside IT), and a list of line-item objects. Before writing any
general tooling, you should be comfortable manually walking a
structure like this with plain dict/list indexing.
---------------------------------------------------------------------
"""

print("\n--- Parsing a Realistic Nested JSON Payload ---")

order_json_string = json.dumps({
    "order_id": "ORD-2026-0042",
    "status": "shipped",
    "customer": {
        "customer_id": "CUST-771",
        "name": "Priya Natarajan",
        "address": {
            "street": "1600 Market St",
            "city": "Philadelphia",
            "state": "PA",
            "zip": "19103",
        },
    },
    "items": [
        {"sku": "WH-1000", "name": "Wireless Headphones", "qty": 1, "unit_price": 149.99},
        {"sku": "USB-C-2M", "name": "USB-C Cable 2m", "qty": 2, "unit_price": 8.50},
    ],
    "placed_at": "2026-08-20T14:32:00Z",
})

order = json.loads(order_json_string)     # this is now a plain nested dict/list structure

# Manually walking the structure - straightforward dict/list chaining,
# but this is exactly what gets tedious (and error-prone) at scale.
print("order id:         ", order["order_id"])
print("customer name:     ", order["customer"]["name"])
print("customer city:     ", order["customer"]["address"]["city"])       # nested object -> nested object
print("number of items:  ", len(order["items"]))
print("first item sku:    ", order["items"][0]["sku"])                    # list -> object
print("second item price: ", order["items"][1]["unit_price"])

order_total = sum(item["qty"] * item["unit_price"] for item in order["items"])
print("computed order total:", round(order_total, 2))


"""
---------------------------------------------------------------------
4. WRITING A RECURSIVE FLATTENER FOR ARBITRARY NESTED JSON  ⭐⭐⭐
---------------------------------------------------------------------
Manual walking (section 3) only works when you already know the
shape. Real pipelines ingest JSON whose shape varies or is too deep
to hardcode by hand - so you need a GENERAL function that flattens
ANY nested dict/list into a single flat dict, using dotted keys for
nested objects (`customer.address.city`) and bracketed indices for
list elements (`items[0].sku`). This is the classic "flatten deeply
nested JSON into a tabular structure" interview question - and the
flat dict it produces is exactly one ROW of a table.
---------------------------------------------------------------------
"""

print("\n--- Recursive Flattening: Nested JSON -> Flat Dict ---")

def flatten_json(obj, parent_key="", sep="."):
    """Recursively flatten a nested dict/list into a single-level dict.

    Dict keys are joined with `sep` (default '.'); list indices are
    appended in brackets, e.g. {"items": [{"sku": "A"}]} becomes
    {"items[0].sku": "A"}. Scalars (str/int/float/bool/None) become
    the terminal leaf values - the recursion bottoms out on them.
    """
    flat = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            flat.update(flatten_json(value, new_key, sep))     # recurse into each value
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            new_key = f"{parent_key}[{index}]"                  # no separator before '[' - matches items[0] style
            flat.update(flatten_json(value, new_key, sep))      # recurse into each element
    else:
        flat[parent_key] = obj                                   # base case: a leaf scalar - stop recursing
    return flat

flat_order = flatten_json(order)
print("flattened order (one row, ready for a DataFrame):")
for key, value in flat_order.items():
    print(f"  {key!r}: {value!r}")

# This flat dict is now trivially one row of a table:
flat_row_df = pd.DataFrame([flat_order])
print("\nas a single-row DataFrame:")
print(flat_row_df)


"""
---------------------------------------------------------------------
5. pandas.json_normalize() - THE HIGHER-LEVEL ALTERNATIVE  ⭐⭐
---------------------------------------------------------------------
Hand-rolling `flatten_json` is what interviewers want to SEE you can
do, but in production you'd usually reach for `pandas.json_normalize`
first. It flattens nested DICTS into dotted columns automatically -
but by default it does NOT explode nested LISTS into multiple rows;
it leaves list-valued columns as Python objects. To turn a list of
sub-records (like our line items) into its own set of ROWS, you pass
`record_path=` (which list to explode) and `meta=` (which parent
fields to carry onto every exploded row) - a very common ETL pattern
for "one order, many line items" style data.
---------------------------------------------------------------------
"""

print("\n--- pandas.json_normalize() vs the Hand-Rolled Flattener ---")

# Default behavior: nested DICTS get dotted-flattened, but the
# "items" LIST stays as a single cell containing a list of dicts.
default_normalized = pd.json_normalize(order)
print("json_normalize(order) - default (dicts flattened, list untouched):")
print(default_normalized.to_string())
print("\nnote 'items' column dtype:", default_normalized["items"].dtype, "- still a raw Python list per cell")

# Using record_path + meta to explode "items" into one row PER item,
# carrying the order-level fields along as repeated metadata columns -
# this is the standard shape for loading into a relational "order_items" table.
exploded = pd.json_normalize(
    order,
    record_path="items",
    meta=["order_id", "status", ["customer", "name"]],   # dotted path into nested meta fields
    record_prefix="item_",
)
print("\njson_normalize(order, record_path='items', meta=[...]) - one row per line item:")
print(exploded.to_string())

print("\nComparison: the hand-rolled flatten_json() gives ONE dict per")
print("call (great for a single flat record / a generic recursive")
print("utility for arbitrary/unknown shapes). json_normalize() is")
print("purpose-built for turning a BATCH of API records into a")
print("DataFrame directly, and its record_path/meta args are the")
print("idiomatic way to explode nested lists into proper rows.")


"""
---------------------------------------------------------------------
6. JSON LINES (.jsonl) FORMAT: ONE JSON OBJECT PER LINE  ⭐⭐
---------------------------------------------------------------------
A single giant JSON array of records (`[{...}, {...}, ...]`) can't be
streamed - you must load the WHOLE array before you can touch record
1. JSON Lines fixes this: each line is its OWN complete, independent
JSON object, so you can read and process the file one line at a time
without ever holding the full file in memory. This is the standard
format for event logs, ML training data, and API export dumps.
---------------------------------------------------------------------
"""

print("\n--- Writing and Reading a JSON Lines (.jsonl) File ---")

jsonl_records = [
    {"user_id": 1, "event": "login", "ts": "2026-08-25T08:01:00Z"},
    {"user_id": 2, "event": "page_view", "ts": "2026-08-25T08:01:03Z"},
    {"user_id": 1, "event": "add_to_cart", "ts": "2026-08-25T08:02:11Z"},
    {"user_id": 3, "event": "login", "ts": "2026-08-25T08:03:47Z"},
    {"user_id": 2, "event": "checkout", "ts": "2026-08-25T08:05:30Z"},
]

jsonl_fd, jsonl_path = tempfile.mkstemp(suffix=".jsonl", prefix="events_")
os.close(jsonl_fd)
with open(jsonl_path, "w") as f:
    for rec in jsonl_records:
        f.write(json.dumps(rec) + "\n")     # one compact JSON object per line, newline-terminated
print(f"wrote {len(jsonl_records)} records to a demo .jsonl file")

# Reading it back: json.loads() per line, NOT json.load() on the whole
# file (the file as a whole is not valid single JSON - it's newline-
# delimited JSON, a different format).
print("\nreading line by line:")
with open(jsonl_path, "r") as f:
    for line_number, line in enumerate(f, start=1):
        parsed = json.loads(line)
        print(f"  line {line_number}: user_id={parsed['user_id']} event={parsed['event']}")


"""
---------------------------------------------------------------------
7. PROCESSING A .jsonl FILE IN CHUNKS (BATCHES OF N LINES)  ⭐⭐⭐
---------------------------------------------------------------------
Directly answers "read a JSONL file and process it in chunks": rather
than parsing one record at a time (too many tiny operations, e.g. one
DB insert per row) or loading the entire file (too much memory for a
huge file), accumulate a BATCH of N parsed records, "process" (e.g.
bulk-insert) the whole batch at once, then clear it and continue -
classic memory-bounded streaming ETL.
---------------------------------------------------------------------
"""

print("\n--- Chunked Batch Processing of a .jsonl File ---")

def process_batch(batch, batch_number):
    """Stand-in for a real bulk operation, e.g. a bulk DB insert."""
    print(f"  processing batch {batch_number} ({len(batch)} records): "
          f"user_ids={[r['user_id'] for r in batch]}")

CHUNK_SIZE = 2
batch = []
batch_number = 0
with open(jsonl_path, "r") as f:
    for line in f:
        batch.append(json.loads(line))
        if len(batch) >= CHUNK_SIZE:          # batch is full - flush it
            batch_number += 1
            process_batch(batch, batch_number)
            batch = []                         # reset for the next chunk

if batch:                                       # flush any leftover partial batch at EOF
    batch_number += 1
    process_batch(batch, batch_number)

print(f"processed all records in {batch_number} batches of up to {CHUNK_SIZE}")


"""
---------------------------------------------------------------------
8. MALFORMED-LINE RESILIENCE: json.JSONDecodeError  ⭐⭐
---------------------------------------------------------------------
Same theme as Module 5 (Exception Handling): a pipeline reading
thousands/millions of JSONL lines from an external source WILL
eventually hit a corrupted or truncated line (a partial write, a
network blip mid-export). If you let json.loads() raise unguarded,
ONE bad line kills the entire job. Catch `json.JSONDecodeError`
per-line, log/skip it, and keep going - never a bare `except:`.
---------------------------------------------------------------------
"""

print("\n--- Resilience: Skipping Malformed Lines Without Crashing ---")

# Append one deliberately corrupted line and one blank line to simulate
# real-world messy input.
with open(jsonl_path, "a") as f:
    f.write('{"user_id": 4, "event": "logout", "ts": ' + "\n")   # truncated/invalid JSON
    f.write("\n")                                                  # blank line

good_records = []
skipped_lines = 0
with open(jsonl_path, "r") as f:
    for line_number, line in enumerate(f, start=1):
        line = line.strip()
        if not line:
            continue                              # silently skip genuinely blank lines
        try:
            good_records.append(json.loads(line))
        except json.JSONDecodeError as e:
            skipped_lines += 1
            print(f"  skipping malformed line {line_number}: {e}")

print(f"\nsuccessfully parsed {len(good_records)} records, skipped {skipped_lines} bad line(s)")
print("the job completed instead of crashing on the first bad record.")

os.remove(jsonl_path)
print("\n(demo .jsonl file cleaned up)")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
STRING <-> OBJECT              OBJECT -> str: json.dumps(obj)
                                 str -> OBJECT: json.loads(s)

FILE <-> OBJECT                OBJECT -> file: json.dump(obj, f)
                                 file -> OBJECT: json.load(f)

Pretty / stable output         json.dumps(obj, indent=2, sort_keys=True)

Non-native types                json.dumps(obj, default=str)
(datetime, Decimal, ...)          -> or a custom default(obj) function
                                     raising TypeError for truly unknown types

Manual nested access            order["customer"]["address"]["city"]
                                 order["items"][0]["sku"]

Recursive flattening            flatten_json(obj, parent_key="", sep=".")
                                   dict  -> "parent.child"
                                   list  -> "parent[index]"
                                   scalar -> base case, stops recursion

pandas.json_normalize(obj)     flattens nested DICTS to dotted columns;
                                 does NOT explode lists by default ->
                                 use record_path=/meta= to explode a
                                 nested list into one row per element

JSON Lines (.jsonl)             one complete JSON object per line;
                                 read with json.loads(line) per line,
                                 NEVER json.load() on the whole file

Chunked processing              accumulate N parsed lines into a list,
                                 process_batch() when full, reset list,
                                 flush any remainder after the loop

Malformed-line resilience       try/except json.JSONDecodeError PER
                                 LINE inside the read loop - one bad
                                 line must never kill the whole read
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - JSON HANDLING
=====================================================================

1. What is the difference between `json.dumps`/`json.loads` and
   `json.dump`/`json.load`? When would you use the file variants
   instead of the string variants?

2. Why does `json.dumps()` raise a `TypeError` on a raw `datetime`
   object, and what are two different ways to fix it (`default=str`
   vs a custom `default=` function)?

3. What does `sort_keys=True` buy you, and why does it matter when
   diffing JSON output in version control or tests?

4. How do you flatten deeply nested JSON into a tabular structure?
   Walk through how `flatten_json()` in this file handles a nested
   dict (`customer.address.city`) versus a list
   (`items[0].sku`) differently.

5. In `flatten_json()`, what is the BASE CASE of the recursion, and
   what would happen if you forgot it (i.e., never stopped recursing
   on non-dict/non-list values)?

6. What is the key difference in behavior between the hand-rolled
   `flatten_json()` and `pandas.json_normalize()` when a JSON object
   contains a LIST of nested objects (like `items` in the `order`
   example)?

7. What do the `record_path=` and `meta=` arguments to
   `pandas.json_normalize()` do, and why would you need them to turn
   `order["items"]` into separate DataFrame rows?

8. Read a JSON Lines (`.jsonl`) file and process it in chunks - how
   would you structure the loop, and why is accumulating a batch of N
   records often better than processing one record at a time or
   loading the whole file at once?

9. Why can't you call `json.load()` (or `json.loads()`) on an entire
   `.jsonl` file's contents as a single call? What error would you
   get, and why?

10. How do you make a JSON-Lines-reading pipeline resilient to a
    single corrupted/truncated line, so that one bad line doesn't
    crash the entire ingestion job? Which specific exception do you
    catch, and where in the loop?

11. What is the practical difference between `except
    json.JSONDecodeError` and a bare `except:` when reading
    untrusted JSON input?

12. Given a deeply nested API response with an unknown/variable
    schema (fields that may or may not be present at different
    levels), how would you adapt `flatten_json()` to be safe against
    missing keys or `None` values partway through the structure?

13. Why is JSON Lines (`.jsonl`) a more common format than a single
    large JSON array for things like event logs or ML training data
    exports?

14. If two order records ever produced a `flatten_json()` result with
    DIFFERENT sets of keys (e.g. one order has 2 items, another has
    3), what problem would that cause when combining several
    flattened orders into one Pandas DataFrame, and how does
    `pd.DataFrame(list_of_flat_dicts)` handle it?
=====================================================================
"""
