"""
=====================================================================
PARSING API RESPONSES INTO STRUCTURED DATA - Defensive Parsing,
Schema Validation, and pydantic
=====================================================================

Every real API eventually lies to you a little. The docs say "price
is a number" and 99% of the time it is - until one record has it as
a string because someone's backend serialized a Decimal weirdly, or
a field is just missing because it's genuinely optional, or a new
field shows up overnight because the provider shipped a v2 without
telling you. None of this is hypothetical - it is the single most
common source of 2am pipeline failures in data engineering: "the
job has run fine for six months and today it crashed on row 4,213."

This file is NOT about `json.loads()` or flattening nested JSON into
tables - see the JSON Handling file for that, and see the `requests`
file for how you actually fetch data from an API. This file picks up
right after you already have a Python list of dicts (the parsed JSON
body) and asks a narrower, more DE-flavored question: how do you
turn that list of "probably-fine-but-not-guaranteed" dicts into a
list of OBJECTS you can actually trust downstream, without either
(a) crashing your whole ETL job on the first weird record, or
(b) silently loading garbage into the warehouse?

The answer the industry has converged on is SCHEMA VALIDATION at the
ingestion boundary - defining what a record is SUPPOSED to look like
(a pydantic model), running every incoming record through it, and
treating validation failures as first-class citizens of the job
(logged, counted, quarantined) rather than either fatal crashes or
silent corruption. This is also your best defense against the #1
practical pain point of working with THIRD-PARTY APIs: they change
shape without warning, and you want to find out immediately and
loudly, not three transform steps later as a mysterious `TypeError`.
=====================================================================
"""

print("--- Overview ---")
print("Goal: turn a messy list of raw API dicts into a list of")
print("validated, type-correct objects - loudly rejecting records")
print("that are broken beyond repair, instead of crashing or")
print("silently corrupting downstream data.")


"""
---------------------------------------------------------------------
1. THE RUNNING EXAMPLE: A REALISTIC, MESSY "PRODUCTS" API RESPONSE  ⭐⭐
---------------------------------------------------------------------
This is what a real paginated REST API response looks like after
`response.json()` - a wrapper dict with metadata plus a "data" list.
Look closely at the FIVE records: one is perfectly normal, one has
`price` as a STRING instead of a float (common when APIs serialize
decimals inconsistently), one has an UNEXPECTED extra field a newer
version of the API started sending, one has a price that isn't a
number AT ALL ("N/A" - genuinely broken), and one is MISSING the
required "name" field entirely. This exact mix is the point: most
records are fine, a few are merely inconsistent (recoverable), and
at least one is truly bad (not recoverable).
---------------------------------------------------------------------
"""

print("\n--- The Running Example: A Messy Products API Response ---")

raw_api_response = {
    "status": "ok",
    "page": 1,
    "data": [
        {"id": 1, "name": "Wireless Mouse", "price": 19.99,
         "in_stock": True, "category": "Electronics"},
        {"id": 2, "name": "USB-C Cable", "price": "12.50",
         "in_stock": True},                                  # price is a STRING; category MISSING (optional)
        {"id": 3, "name": "Laptop Stand", "price": 45.0,
         "in_stock": False, "category": "Electronics",
         "warehouse_zone": "B12"},                            # unexpected EXTRA field, not in the "usual" shape
        {"id": 4, "name": "Desk Lamp", "price": "N/A",
         "in_stock": True, "category": "Home"},               # price is not a number AT ALL - truly broken
        {"price": 8.99, "in_stock": True, "category": "Office"},  # "name" is MISSING - required field, truly broken
    ],
}

print(f"received {len(raw_api_response['data'])} records from the API")
for record in raw_api_response["data"]:
    print(" ", record)


"""
---------------------------------------------------------------------
2. THE NAIVE APPROACH: DIRECT DICT INDEXING  ⭐⭐⭐
---------------------------------------------------------------------
The tempting first move is to just index straight into the parsed
JSON: `response["data"][0]["price"]`. This works fine on the happy
path and is exactly why it's dangerous - it survives code review and
the first few runs, then blows up in production on whichever record
first deviates from the assumed shape. Two DIFFERENT real exceptions
below: a `TypeError` from mixing a `str` price into arithmetic, and a
`KeyError` from a genuinely missing key. Both are "live" - triggered
by running this exact code against the exact data above, not
fabricated for the demo.
---------------------------------------------------------------------
"""

print("\n--- The Naive Approach: Direct Dict Indexing ---")

# Naive "total inventory value" calculation - looks reasonable, isn't safe
try:
    total_value = sum(r["price"] * 1 for r in raw_api_response["data"][:2])
    # record 0's price (19.99, a float) is fine, but record 1's price is
    # the STRING "12.50" - you can't do float + str, so this blows up
    # partway through the sum()
    print("total value:", total_value)
except TypeError as e:
    print("naive arithmetic blew up with a live TypeError:", e)

# Naive field access - assumes every record has every "usual" key
try:
    names = [r["name"] for r in raw_api_response["data"]]
    print("names:", names)
except KeyError as e:
    print("naive dict indexing blew up with a live KeyError:", e)

print("\nBoth exceptions are fatal by default - one bad record out of")
print("five just took down the entire batch, including the four")
print("records that were perfectly fine to process.")


"""
---------------------------------------------------------------------
3. DEFENSIVE PARSING: .get() WITH DEFAULTS AND MANUAL COERCION  ⭐⭐
---------------------------------------------------------------------
The next step up is defensive-by-hand: use `.get()` with sensible
defaults instead of `[]`, and write explicit coercion logic for
fields whose TYPE isn't guaranteed. This genuinely works and is
worth knowing how to write - but notice how quickly it turns into
unreadable boilerplate once you have more than 2-3 fields, and it
still doesn't give you a clear signal for "this record is
unsalvageable" versus "this record just needed cleanup." That
signal is exactly what section 5 gets from pydantic almost for free.
---------------------------------------------------------------------
"""

print("\n--- Defensive Parsing with .get() and Manual Coercion ---")


def coerce_price(raw_price):
    """Best-effort conversion of a price field to float, or None if unusable."""
    if isinstance(raw_price, (int, float)):
        return float(raw_price)
    if isinstance(raw_price, str):
        try:
            return float(raw_price)          # handles "12.50" -> 12.5
        except ValueError:
            return None                       # handles "N/A" -> can't coerce, give up
    return None


def parse_record_defensively(record):
    return {
        "id": record.get("id"),
        "name": record.get("name", "UNKNOWN"),        # default instead of a KeyError
        "price": coerce_price(record.get("price")),
        "in_stock": record.get("in_stock", False),
        "category": record.get("category", "Uncategorized"),
    }


defensively_parsed = [parse_record_defensively(r) for r in raw_api_response["data"]]
for row in defensively_parsed:
    print(" ", row)

print("\nThis no longer CRASHES, which is progress - but look at row 4:")
print("price silently became None, and row 5's name silently became")
print("'UNKNOWN'. Nothing raised an alarm. A hand-rolled function like")
print("this only catches what YOU thought to defend against, and it")
print("has no built-in concept of 'this record failed validation.'")


"""
---------------------------------------------------------------------
4. THE BETTER WAY: A pydantic SCHEMA FOR THE EXPECTED SHAPE  ⭐⭐⭐
---------------------------------------------------------------------
pydantic lets you declare what a record SHOULD look like once, as a
class, and get validation, type coercion, and defaults for free -
plus, critically, a clear exception type (`ValidationError`) when a
record can't be made to fit, with structured detail about exactly
which field failed and why. `field_validator(..., mode="before")"
runs BEFORE pydantic's own type checking, which is exactly where you
want to coerce a "sometimes-string, sometimes-float" field like
price - handle the string case yourself, then hand pydantic a clean
value (or raise, if it's truly unusable and pydantic should reject
the whole record).
---------------------------------------------------------------------
"""

print("\n--- Defining the Expected Schema with pydantic ---")

from pydantic import BaseModel, Field, field_validator, ValidationError


class Product(BaseModel):
    id: int
    name: str
    price: float = Field(ge=0)                 # must coerce to a non-negative float
    in_stock: bool = True                       # optional, defaults if missing
    category: str = "Uncategorized"              # optional, defaults if missing

    @field_validator("price", mode="before")
    @classmethod
    def coerce_price_string(cls, value):
        """Accept price as either a float/int or a numeric string ('19.99')."""
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                # re-raising ValueError here is what pydantic turns into a
                # clean ValidationError entry for this field - see section 5
                raise ValueError(f"price {value!r} could not be parsed as a number")
        return value


print("schema defined:", list(Product.model_fields.keys()))
print("this is the SINGLE source of truth for what a valid Product is -")
print("required fields, defaults, and the price coercion rule all live")
print("in one place instead of scattered across .get() calls.")


"""
---------------------------------------------------------------------
5. VALIDATING ONE RECORD: SUCCESS vs A CLEAR ValidationError  ⭐⭐⭐
---------------------------------------------------------------------
`Product.model_validate(dict)` is the pydantic v2 entry point for
"take a raw dict and give me back a validated instance, or tell me
exactly why you can't." Compare a MERELY-INCONSISTENT record (string
price - recoverable, thanks to the validator above) against a TRULY
BROKEN one (price "N/A" - genuinely not a number). pydantic's error
output tells you the exact field, the exact problem, and the exact
input it choked on - vastly more actionable than a bare TypeError
three functions away from where the bad data actually entered.
---------------------------------------------------------------------
"""

print("\n--- One Record at a Time: Success vs ValidationError ---")

# Record 1: normal, everything matches types exactly
good_record = raw_api_response["data"][0]
product = Product.model_validate(good_record)
print("validated normal record ->", product)

# Record 2: price is a string "12.50" - the `mode="before"` validator saves this
inconsistent_record = raw_api_response["data"][1]
coerced_product = Product.model_validate(inconsistent_record)
print("validated string-price record ->", coerced_product)
print("  note: coerced_product.price is now a real float:", coerced_product.price,
      type(coerced_product.price))

# Record 4: price is "N/A" - genuinely not a number, nothing can save this
broken_record = raw_api_response["data"][3]
try:
    Product.model_validate(broken_record)
except ValidationError as e:
    print("\nvalidating the truly broken record raised ValidationError:")
    print(e)                          # pydantic's human-readable summary
    print("\nstructured detail via e.errors():")
    for err in e.errors():
        # each error names the exact field ('loc'), the problem ('msg'),
        # and the offending input value - built for logging/alerting
        print(f"  field={err['loc']}, msg={err['msg']}, bad_input={err['input']!r}")


"""
---------------------------------------------------------------------
6. VALIDATING THE WHOLE LIST: KEEP THE JOB MOVING  ⭐⭐⭐
---------------------------------------------------------------------
This is the section that actually matters for a production pipeline.
You never want ONE bad record (out of maybe a million) to take down
the entire ingestion job - that's the same "one bad file shouldn't
kill the batch" principle from the Exception Handling file, applied
to individual API records instead of files. Loop over the raw list,
`model_validate()` each record inside a try/except, and PARTITION the
results into records that validated and records that didn't (with
their errors attached) - so the 95% of good data keeps moving while
the bad 5% gets logged/quarantined for someone to look at later,
instead of crashing everything.
---------------------------------------------------------------------
"""

print("\n--- Validating the Whole List: Partition Good vs Bad ---")

valid_products: list[Product] = []
failed_records: list[dict] = []

for record in raw_api_response["data"]:
    try:
        valid_products.append(Product.model_validate(record))
    except ValidationError as e:
        # keep the ORIGINAL record plus a compact reason - this is what
        # you'd write to a "quarantine" table or a dead-letter log
        failed_records.append({"record": record, "errors": e.errors()})

print(f"validated {len(valid_products)}/{len(raw_api_response['data'])} records successfully")
for p in valid_products:
    print("  OK:", p)

print(f"\n{len(failed_records)} record(s) failed validation and were quarantined:")
for failure in failed_records:
    reasons = [f"{err['loc'][0]}: {err['msg']}" for err in failure["errors"]]
    print("  FAILED:", failure["record"], "->", reasons)

print("\nThe pipeline can now confidently proceed with `valid_products`")
print("while `failed_records` gets logged, alerted on, or written to a")
print("dead-letter queue for manual review - the job doesn't stop.")


"""
---------------------------------------------------------------------
7. FROM VALIDATED MODELS TO A CLEAN pandas DataFrame  ⭐⭐
---------------------------------------------------------------------
Once you have a list of validated pydantic instances, `model_dump()`
turns each one back into a plain dict with guaranteed types and
keys - exactly the shape `pd.DataFrame` wants. Compare this to
building a DataFrame straight from the RAW list: pandas would happily
infer a mixed `object` dtype for the `price` column (because of the
string "12.50") instead of a clean numeric column, silently setting
you up for a broken `.sum()` or `.mean()` two transform steps later.
---------------------------------------------------------------------
"""

print("\n--- From Validated Models to a Clean DataFrame ---")

import pandas as pd

df = pd.DataFrame([p.model_dump() for p in valid_products])
print(df)
print("\ndtypes (note 'price' is a clean float64, not 'object'):")
print(df.dtypes)
print("\ntotal validated inventory value:", df["price"].sum())

# For contrast: building a DataFrame from the RAW dicts (no validation first)
raw_df = pd.DataFrame(raw_api_response["data"])
print("\nfor contrast, a DataFrame built from the RAW records has an")
print("'object' dtype price column (mixed str/float) and NaN gaps:")
print(raw_df.dtypes)


"""
---------------------------------------------------------------------
8. UNEXPECTED EXTRA FIELDS: model_config's `extra` SETTING  ⭐⭐
---------------------------------------------------------------------
Record 3 had a `warehouse_zone` field the schema never declared. By
default, pydantic v2 models IGNORE extra fields - they're silently
dropped, which is why record 3 validated cleanly back in section 6
with no `warehouse_zone` on the resulting `Product`. That's often
fine for a stable, well-understood API. But for an API you don't
control, silently dropping unrecognized fields can hide the exact
kind of schema drift you actually want to know about. Setting
`extra="forbid"` flips this: any unrecognized field becomes a loud,
immediate `ValidationError` instead of a silent drop.
---------------------------------------------------------------------
"""

print("\n--- Unexpected Extra Fields: Ignore vs Forbid ---")

extra_field_record = raw_api_response["data"][2]      # has "warehouse_zone"
default_parse = Product.model_validate(extra_field_record)
print("default behavior (extra='ignore'): warehouse_zone silently dropped")
print(" ", default_parse)


class StrictProduct(Product):
    model_config = {"extra": "forbid"}                 # no unrecognized fields allowed

try:
    StrictProduct.model_validate(extra_field_record)
except ValidationError as e:
    print("\nwith extra='forbid', the SAME record now raises loudly:")
    for err in e.errors():
        print(f"  field={err['loc']}, msg={err['msg']}")


"""
---------------------------------------------------------------------
9. WHY THIS MATTERS MOST FOR THIRD-PARTY APIS  ⭐⭐
---------------------------------------------------------------------
You control your own database schema; you do NOT control a vendor's
API. Third-party providers rename fields, change a price from a
float to a "money object" string, add new fields, or quietly start
omitting one you depended on - usually with no changelog entry you
ever see. Simulate exactly that: "the API" ships a v2 where `price`
has been renamed to `unit_price`. With naive dict access, this fails
QUIETLY (`.get("price")` just returns None/default, no error at
all) and the corruption surfaces mysteriously three transform steps
downstream. With a pydantic schema, it fails LOUDLY, IMMEDIATELY,
at the ingestion boundary, with a message that names the exact
problem.
---------------------------------------------------------------------
"""

print("\n--- Why This Discipline Matters for Third-Party APIs ---")

# The vendor ships a "v2" response - they renamed 'price' to 'unit_price'
# with zero warning, which happens constantly in the real world
v2_record = {"id": 9, "name": "Mechanical Keyboard", "unit_price": 89.99,
             "in_stock": True, "category": "Electronics"}

naive_price = v2_record.get("price", 0.0)
print(f"naive .get('price', 0.0) on the v2 record silently returns: {naive_price}")
print("-> no error, no warning, just a WRONG price flowing downstream")
print("   (this is the 'mysterious TypeError three steps later' bug in")
print("   the making - except often it's worse: no error at all, just")
print("   bad numbers quietly landing in the warehouse)")

try:
    Product.model_validate(v2_record)
except ValidationError as e:
    print("\npydantic catches the SAME drift immediately and loudly:")
    for err in e.errors():
        print(f"  field={err['loc']}, msg={err['msg']}")
    print("-> the job fails fast, at the ingestion boundary, with a")
    print("   message that points straight at what the vendor changed -")
    print("   instead of a confusing bug report from three teams over.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Naive dict indexing        -> response["data"][0]["price"]
                               fragile: live KeyError/TypeError on
                               any record that deviates from "usual"

Defensive-by-hand          -> record.get("field", default) +
                               manual coercion functions
                               works, but boilerplate-heavy and has
                               no concept of "record failed validation"

pydantic schema            -> class Product(BaseModel): ...
    Field(ge=0)                 adds constraints beyond just type
    field_validator(mode=       coerces BEFORE type checking - use
      "before")                 for "sometimes string, sometimes
                                 float" fields like price

Parse one record           -> Product.model_validate(raw_dict)
    success                    -> returns a typed, validated instance
    failure                    -> raises pydantic.ValidationError
        e.errors()                  -> list of {loc, msg, input} dicts

Parse a whole batch         -> loop + try/except ValidationError,
                                partition into valid_products vs
                                failed_records - keeps the job moving
                                instead of crashing on record #1

Models -> DataFrame          -> pd.DataFrame([m.model_dump()
                                              for m in valid_models])
                                 guarantees clean, uniform dtypes

Extra/unknown fields         -> model_config extra="ignore" (default,
                                 v2) drops them silently; extra=
                                 "forbid" raises loudly instead -
                                 use "forbid" when schema drift itself
                                 is the thing you want to detect

Third-party API discipline   -> validate at the INGESTION boundary
                                 so a vendor's silent schema change
                                 fails fast and clearly, not as a
                                 mysterious bug several steps later
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PARSING API RESPONSES INTO STRUCTURED DATA
=====================================================================

1. What's wrong with writing `response["data"][0]["price"]` directly
   against a real API response, even if it works fine in testing?

2. In this file, one record raised a `TypeError` and another raised a
   `KeyError` when accessed naively. What specifically caused each
   one, and why are they different failure modes?

3. What's the difference between "defensive parsing" with `.get()`
   and default values versus schema validation with pydantic? Why
   does the `.get()` approach not scale well past a few fields?

4. Walk through the `Product` model in this file. Why does the price
   coercion logic live in a `field_validator` with `mode="before"`
   instead of `mode="after"`, or instead of just declaring
   `price: float` and hoping pydantic coerces the string itself?

5. What does `Product.model_validate(raw_dict)` do, and what does it
   raise when the input can't be made to fit the schema?

6. What information does `ValidationError.errors()` give you that a
   plain `str(exception)` from a `TypeError` does not? Why does that
   matter for logging/alerting in a production pipeline?

7. Design a loop that validates a list of 1 million raw API records
   using a pydantic model, without letting a single bad record crash
   the whole job. What would you do with the records that fail?

8. How does this "partition good records from bad, keep the job
   moving" pattern relate to the general exception-handling principle
   of "one bad file shouldn't kill the whole batch"?

9. Why did record 3 (with the extra `warehouse_zone` field) validate
   successfully with `Product` but fail with `StrictProduct`? What
   pydantic setting controls this, and what are the two values?

10. In what situation would you deliberately choose `extra="forbid"`
    over the default `extra="ignore"` behavior, given that "ignore"
    seems safer on the surface?

11. Why is `pd.DataFrame([m.model_dump() for m in valid_products])`
    preferable to building a DataFrame directly from the raw list of
    dicts, in terms of the resulting column dtypes?

12. Explain, using the `unit_price` vs `price` rename example in this
    file, why naive `.get("price", default)` parsing is arguably MORE
    dangerous than code that would just crash - in terms of what each
    one does when a third-party API silently changes shape.

13. If you were designing an ETL job that pulls from a vendor API you
    don't control, where exactly in the pipeline would you put the
    pydantic validation step, and why does that placement matter?

14. How would you extend the `Product` model to require that
    `category` be one of a fixed, known set of values, and what
    should happen to a record with a category outside that set?

15. What's the practical difference between a validation failure you
    catch and quarantine versus one you let propagate as an uncaught
    `ValidationError`? When would each be the right choice in a real
    ingestion job?
=====================================================================
"""
