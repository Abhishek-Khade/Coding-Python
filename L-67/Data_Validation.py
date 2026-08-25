"""
=====================================================================
DATA VALIDATION FOR ETL - Data Quality Checks & Schema Evolution
=====================================================================

Every ETL job makes an implicit promise to everything downstream of
it: "the rows I loaded are trustworthy." That promise is worthless
unless something actually CHECKS it before the load happens. This
file is about that checking step - not fixing bad data (that's
TRANSFORM's job), but deciding, systematically, whether a batch of
data is fit to load at all, and if not, exactly which rows and why.

Note the scope here versus the Parsing API Responses file: that file
already covers RECORD-level validation of one API response using
`pydantic` models in depth - one dict in, one validated object (or a
loud rejection) out. This file is deliberately broader: it's about
BATCH/DataFrame-level data quality - the checks a data engineer runs
across an entire pandas DataFrame (or a whole warehouse load) before
it touches production tables, plus the schema-evolution problem that
only shows up once you're tracking a data source over TIME, not just
validating one response. See that file if you want the pydantic
deep-dive; this one assumes you already trust individual records are
well-typed and asks the next-level question: is this BATCH healthy?

A production-grade DE validation layer typically checks six things:
    1. SCHEMA / TYPE       - are the columns and their types what we expect?
    2. COMPLETENESS        - are required fields actually populated?
    3. UNIQUENESS           - are supposedly-unique keys actually unique?
    4. RANGE / BOUNDS       - do values fall within sane limits?
    5. REFERENTIAL / CROSS-FIELD - do related fields/tables agree with each other?
    6. FRESHNESS / VOLUME   - did we get roughly the data we expected TODAY?

`great_expectations` (GE) is the industry-standard library for
expressing these as DECLARATIVE, reusable "expectations" - but it is
a genuinely heavy dependency (its own metadata store, doc generator,
optional Spark/SQL backends) and is often overkill, unavailable, or
politically hard to add to a small pipeline. This file shows the real
GE-style API (wrapped safely in case it isn't installed) alongside a
hand-rolled validation-rule engine that teaches the exact same
underlying concepts - named, reusable, self-documenting checks that
collect ALL failures and produce a report - using only pandas.
=====================================================================
"""

import logging

import pandas as pd
from dataclasses import dataclass
from typing import Callable

# A real pipeline would wire this into its central logging config (see
# this repo's Exception Handling notes for why print() alone isn't
# enough once a job runs unattended on a schedule) - here a minimal
# logger stands in so the "this gets logged/monitored" parts of this
# file are genuine calls, not just comments.
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("etl.validation")

print("--- Overview ---")
print("Validation != fixing data. It's deciding, with evidence, whether")
print("a batch is fit to load - and routing the rows that aren't.")


"""
---------------------------------------------------------------------
1. THE RUNNING EXAMPLE: A REALISTIC, MESSY "ORDERS" BATCH  ⭐⭐⭐
---------------------------------------------------------------------
This is what a daily orders extract looks like after landing in a
staging area - mostly fine, with a handful of DIFFERENT problems
baked in on purpose, each one representative of a real failure mode:
a duplicated order_id, a missing customer_id, a stale order_date, a
missing product_sku, an unparseable quantity, an out-of-range price,
an invalid status value, an unknown customer_id, and a total_amount
that doesn't match quantity * unit_price. Note that several rows are
otherwise PERFECTLY fine except for one field - that's realistic;
most of a batch is usually healthy, which is exactly why you can't
just eyeball it.
---------------------------------------------------------------------
"""

print("\n--- The Running Example: A Messy Orders Batch ---")

orders_df = pd.DataFrame({
    "order_id":     [1001, 1002, 1003, 1003, 1005, 1006, 1007, 1008, 1009, 1010],
    "customer_id":  [501, 502, None, 503, 504, 999, 505, 506, 507, 508],
    "order_date":   ["2026-08-25", "2026-08-25", "2026-08-25", "2026-08-25",
                      "2026-08-25", "2026-08-25", "2026-07-01", "2026-08-25",
                      "2026-08-25", None],
    "product_sku":  ["SKU-1001", "SKU-1002", "SKU-1003", "SKU-1003", "SKU-1005",
                      None, "SKU-1007", "SKU-1008", "SKU-1009", "SKU-1010"],
    "quantity":     [2, 1, 3, 3, "N/A", 2, -5, 1, 4, 2],          # mixed int/str -> object dtype
    "unit_price":   [19.99, 45.00, 12.50, 12.50, 8.00, 25.00, 15.00, 9999.00, 30.00, -10.00],
    "total_amount": [39.98, 45.00, 37.50, 37.50, 8.00, 50.00, -75.00, 9999.00, 100.00, -20.00],
    "status":       ["shipped", "delivered", "pending", "pending", "shipped",
                      "shpiped", "cancelled", "delivered", "pending", "shipped"],
    "region":       ["US-East", "US-West", "US-East", "US-East", "EU", "US-West",
                      "US-East", "APAC", "US-West", "US-East"],
})

print(f"received {len(orders_df)} rows, {len(orders_df.columns)} columns")
print(orders_df)
print("\ndtypes as pandas inferred them:")
print(orders_df.dtypes)


"""
---------------------------------------------------------------------
2. CATEGORY 1 - SCHEMA / TYPE CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
The FIRST thing to verify isn't a value - it's whether the column is
even the type you think it is. `quantity` above is a textbook case:
one string ("N/A") among nine ints forces the WHOLE column to object
dtype, silently disabling anything that assumes it's numeric (a plain
`.sum()` would raise `TypeError` deep inside a later transform step,
far from the actual cause). The fix is to check PARSEABILITY
explicitly, at the boundary, rather than discovering it downstream.
---------------------------------------------------------------------
"""

print("\n--- Category 1: Schema / Type Checks ---")

print("quantity column dtype:", orders_df["quantity"].dtype, "(object - NOT purely numeric!)")

quantity_numeric = pd.to_numeric(orders_df["quantity"], errors="coerce")
unparseable_quantity = orders_df.loc[quantity_numeric.isna() & orders_df["quantity"].notna()]
print("rows where quantity can't be parsed as a number:")
print(unparseable_quantity[["order_id", "quantity"]])

# order_date arrives as plain text too - that's fine PRE-parsing, but we
# still need to confirm every non-null value is actually a valid date
parsed_dates = pd.to_datetime(orders_df["order_date"], errors="coerce")
unparseable_dates = orders_df.loc[parsed_dates.isna() & orders_df["order_date"].notna()]
print("\nrows where order_date can't be parsed as a date:", len(unparseable_dates), "(none here - good)")

print("\nNote: customer_id is int-like but shows dtype float64 above -")
print("pandas silently upgrades an int column to float the moment ANY")
print("value is missing (NaN has no int representation). That's not a")
print("data quality bug by itself, but a naive `dtype == 'int64'` schema")
print("check would misfire on it; use pandas' nullable `Int64` dtype")
print("(capital I) if you want to keep NaN AND stay strictly integer.")


"""
---------------------------------------------------------------------
3. CATEGORY 2 - COMPLETENESS / NOT-NULL CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
The simplest, highest-value check in the whole file: for each column
that downstream logic treats as required, what fraction of rows
actually have a value?
---------------------------------------------------------------------
"""

print("\n--- Category 2: Completeness / Not-Null Checks ---")

required_for_completeness = ["order_id", "customer_id", "order_date", "product_sku"]
for col in required_for_completeness:
    missing = orders_df[col].isna().sum()
    pct = missing / len(orders_df)
    print(f"  {col:<12} missing {missing}/{len(orders_df)} rows ({pct:.0%})")


"""
---------------------------------------------------------------------
4. CATEGORY 3 - UNIQUENESS CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
`order_id` should be a primary key - exactly one row per order. A
duplicated key is one of the most damaging failures to load silently:
it double-counts revenue in every downstream aggregation.
---------------------------------------------------------------------
"""

print("\n--- Category 3: Uniqueness Checks ---")

is_duplicate_order_id = orders_df.duplicated(subset=["order_id"], keep=False)
print("duplicated order_id rows:")
print(orders_df.loc[is_duplicate_order_id, ["order_id", "product_sku", "status"]])


"""
---------------------------------------------------------------------
5. CATEGORY 4 - RANGE / BOUNDS CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
Values can be perfectly well-TYPED and still be nonsense: a negative
quantity, a $9,999 unit price on a product that's never sold for more
than a few hundred dollars. `Series.between()` conveniently returns
False (not an error) for NaN, so an unparseable value from Category 1
also falls out here automatically - which makes sense, since "can't
tell if it's in range" and "not in range" both mean "don't trust it."
---------------------------------------------------------------------
"""

print("\n--- Category 4: Range / Bounds Checks ---")

quantity_in_range = pd.to_numeric(orders_df["quantity"], errors="coerce").between(1, 1000)
price_in_range = orders_df["unit_price"].between(0.01, 5000.00)

print("rows with an out-of-range (or unparseable) quantity:")
print(orders_df.loc[~quantity_in_range, ["order_id", "quantity"]])
print("\nrows with an out-of-range unit_price:")
print(orders_df.loc[~price_in_range, ["order_id", "unit_price"]])


"""
---------------------------------------------------------------------
6. CATEGORY 5 - REFERENTIAL & CROSS-FIELD CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
Two related but distinct ideas:
  REFERENTIAL - does a foreign-key-style value actually exist in the
  dimension it's supposed to reference (here, a known customers set -
  standing in for a real "SELECT customer_id FROM customers" check)?
  CROSS-FIELD - do two columns of the SAME row agree with each other
  (total_amount should equal quantity * unit_price)? Notice order 1009
  passes every single individual-column check (valid quantity, valid
  price, valid status) and is STILL invalid - only a cross-field check
  catches it, which is exactly why you need more than one category.
---------------------------------------------------------------------
"""

print("\n--- Category 5: Referential & Cross-Field Checks ---")

known_customer_ids = {501, 502, 503, 504, 505, 506, 507, 508}
customer_ref_ok = orders_df["customer_id"].isin(known_customer_ids)  # NaN -> False automatically
print("rows whose customer_id doesn't reference a known customer:")
print(orders_df.loc[~customer_ref_ok, ["order_id", "customer_id"]])

allowed_statuses = {"pending", "shipped", "delivered", "cancelled"}
status_ok = orders_df["status"].isin(allowed_statuses)
print("\nrows with a status outside the allowed domain:")
print(orders_df.loc[~status_ok, ["order_id", "status"]])

qty_numeric = pd.to_numeric(orders_df["quantity"], errors="coerce")
expected_total = qty_numeric * orders_df["unit_price"]
amount_consistent = (orders_df["total_amount"] - expected_total).abs() <= 0.01
print("\nrows where total_amount doesn't match quantity * unit_price:")
mismatched = orders_df.loc[~amount_consistent, ["order_id", "quantity", "unit_price", "total_amount"]]
print(mismatched)
print("(order 1009 has an individually-valid quantity, price, AND status -")
print(" only the cross-field check exposes that total_amount is wrong.)")


"""
---------------------------------------------------------------------
7. CATEGORY 6 - FRESHNESS / VOLUME CHECKS  ⭐⭐
---------------------------------------------------------------------
Row-level checks can all pass while the BATCH itself is still broken -
e.g. an upstream cron job silently stopped early and only wrote a
tenth of the day's orders. These checks operate on the TABLE as a
whole: is the row count in the expected historical band, and is the
newest data actually recent?
---------------------------------------------------------------------
"""

print("\n--- Category 6: Freshness / Volume Checks ---")

expected_daily_rows = (8, 20)          # historical band for a normal day's orders
low, high = expected_daily_rows
volume_ok = low <= len(orders_df) <= high
print(f"row count {len(orders_df)} within expected band {expected_daily_rows}? {volume_ok}")

reference_load_date = pd.Timestamp("2026-08-25")   # "today", from the orchestrator's point of view
parsed_order_dates = pd.to_datetime(orders_df["order_date"], errors="coerce")
age_in_days = (reference_load_date - parsed_order_dates).dt.days
is_stale = age_in_days > 2
print("\nrows whose order_date is suspiciously old for a 'today' load:")
print(orders_df.loc[is_stale.fillna(False), ["order_id", "order_date"]])

# What a REAL volume-check failure looks like: a truncated extract
truncated_batch = orders_df.head(2)
truncated_ok = low <= len(truncated_batch) <= high
print(f"\nsimulated truncated extract: {len(truncated_batch)} rows -> within band? {truncated_ok}")
if not truncated_ok:
    logger.warning("volume check failed: got %d rows, expected %d-%d", len(truncated_batch), low, high)


"""
---------------------------------------------------------------------
8. BUILDING A REUSABLE VALIDATION RULE ENGINE  ⭐⭐⭐
---------------------------------------------------------------------
Running each check above by hand doesn't scale past a handful of
columns. What DOES scale is a small, generic structure: a NAMED rule
is just a description plus a function that takes the DataFrame and
returns a boolean Series (True = row passes). A CLOSURE-based factory
(see this repo's Closures notes) lets us generate many rules from a
few templates instead of writing one bespoke function per column.

The BUGGY instinct is to validate with a chain of asserts/raises that
stops at the FIRST failure - you fix that one, rerun, hit the SECOND
failure, fix it, rerun... burning an entire day discovering problems
one at a time. The fix: run every rule against every row regardless
of earlier failures, and collect ALL of them into one report.
---------------------------------------------------------------------
"""

print("\n--- Building a Reusable Validation Rule Engine ---")

# BUGGY: stop-at-first-failure style, using bare asserts
def validate_naive(df: pd.DataFrame) -> None:
    assert df["order_id"].is_unique, "duplicate order_id found"
    assert df["customer_id"].notna().all(), "null customer_id found"
    assert df["status"].isin(allowed_statuses).all(), "invalid status found"

try:
    validate_naive(orders_df)
except AssertionError as e:
    print("naive validator stopped at the FIRST problem it hit:", e)
    print("(it never even LOOKED at customer_id, status, price, dates, ...)")

# FIXED: a small rule engine that collects every failure, every time
@dataclass
class ValidationResult:
    rule_name: str
    description: str
    severity: str          # "critical" or "warning" - see Section 10 for what this drives
    passed: bool
    total_rows: int
    failed_rows: int
    failed_indices: list

@dataclass
class ValidationRule:
    name: str
    description: str
    severity: str
    check: Callable[[pd.DataFrame], "pd.Series"]   # True per row = row is valid

    def run(self, df: pd.DataFrame) -> ValidationResult:
        is_valid = self.check(df)
        failed_idx = df.index[~is_valid].tolist()
        return ValidationResult(
            self.name, self.description, self.severity,
            passed=len(failed_idx) == 0,
            total_rows=len(df), failed_rows=len(failed_idx),
            failed_indices=failed_idx,
        )

# Rule FACTORIES - closures that generate a check function from parameters
def not_null_rule(column):
    return lambda df: df[column].notna()

def unique_rule(column):
    return lambda df: ~df.duplicated(subset=[column], keep=False)

def numeric_range_rule(column, low, high):
    return lambda df: pd.to_numeric(df[column], errors="coerce").between(low, high)

def isin_rule(column, allowed):
    return lambda df: df[column].isin(allowed)

def cross_field_total_rule(qty_col, price_col, total_col, tolerance=0.01):
    def check(df):
        expected = pd.to_numeric(df[qty_col], errors="coerce") * df[price_col]
        return (df[total_col] - expected).abs() <= tolerance
    return check

def row_count_rule(min_rows, max_rows):
    return lambda df: pd.Series(min_rows <= len(df) <= max_rows, index=df.index)

order_rules = [
    ValidationRule("not_null_customer_id", "customer_id must not be null", "warning", not_null_rule("customer_id")),
    ValidationRule("not_null_order_date", "order_date must not be null", "warning", not_null_rule("order_date")),
    ValidationRule("not_null_product_sku", "product_sku must not be null", "warning", not_null_rule("product_sku")),
    ValidationRule("unique_order_id", "order_id must be unique", "critical", unique_rule("order_id")),
    ValidationRule("quantity_valid_range", "quantity must parse as a number in [1, 1000]", "critical", numeric_range_rule("quantity", 1, 1000)),
    ValidationRule("unit_price_valid_range", "unit_price must be in [0.01, 5000]", "warning", numeric_range_rule("unit_price", 0.01, 5000)),
    ValidationRule("status_in_allowed_set", "status must be a known lifecycle value", "critical", isin_rule("status", allowed_statuses)),
    ValidationRule("customer_id_known", "customer_id must reference an existing customer", "critical", isin_rule("customer_id", known_customer_ids)),
    ValidationRule("total_amount_consistent", "total_amount must equal quantity * unit_price", "warning", cross_field_total_rule("quantity", "unit_price", "total_amount")),
    ValidationRule("expected_row_volume", "batch row count should be within the expected daily band", "critical", row_count_rule(*expected_daily_rows)),
]

def run_validation_suite(df, rules):
    return [rule.run(df) for rule in rules]      # every rule runs, no matter what earlier ones found

def print_validation_report(results):
    print(f"{'RULE':<26}{'SEVERITY':<10}{'STATUS':<7}{'FAILED/TOTAL'}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{r.rule_name:<26}{r.severity:<10}{status:<7}{r.failed_rows}/{r.total_rows}")
    failed_rules = [r for r in results if not r.passed]
    print(f"\n{len(failed_rules)}/{len(results)} rules found at least one bad row.")

results = run_validation_suite(orders_df, order_rules)
print_validation_report(results)


"""
---------------------------------------------------------------------
9. THE great_expectations STYLE: EXPECTATIONS AS DATA CONTRACTS  ⭐⭐
---------------------------------------------------------------------
`great_expectations` formalizes exactly what Section 8 built by hand:
a library of DECLARATIVE, named expectations
(`expect_column_values_to_not_be_null`, `expect_column_values_to_be_between`,
`expect_column_values_to_be_in_set`, `expect_column_values_to_be_unique`,
`expect_table_row_count_to_be_between`, ...) that read like documentation,
generate their OWN human-readable "data docs" website, and can validate
against pandas, SQL, or Spark with the same expectation definitions.
The trade-off is real infrastructure weight - a whole "Expectation
Suite" + "Checkpoint" model that's often more machinery than a small
pipeline needs. It is genuinely NOT installed in this environment
(and often isn't in a lightweight ETL job either), so the import is
guarded - if it's missing, we fall back to the equivalent rule from
our own engine, which is exactly what GE is doing under the hood.
---------------------------------------------------------------------
"""

print("\n--- The great_expectations Style: Declarative Data Contracts ---")

try:
    import great_expectations as ge   # pragma: no cover - heavy optional dependency

    ge_df = ge.from_pandas(orders_df)
    null_result = ge_df.expect_column_values_to_not_be_null("customer_id")
    range_result = ge_df.expect_column_values_to_be_between("unit_price", min_value=0.01, max_value=5000)
    set_result = ge_df.expect_column_values_to_be_in_set("status", list(allowed_statuses))
    unique_result = ge_df.expect_column_values_to_be_unique("order_id")
    print("great_expectations IS installed - ran real expectations:")
    print(" ", null_result["success"], range_result["success"], set_result["success"], unique_result["success"])

except ImportError:
    print("great_expectations is NOT installed here (as expected - it's a")
    print("heavy, optional dependency). Falling back to the equivalent")
    print("checks from our own rule engine, which express the SAME idea:")

    ge_equivalent = {
        "expect_column_values_to_not_be_null('customer_id')": results[0],
        "expect_column_values_to_be_between('unit_price', 0.01, 5000)": results[5],
        "expect_column_values_to_be_in_set('status', allowed_statuses)": results[6],
        "expect_column_values_to_be_unique('order_id')": results[3],
    }
    for expectation_name, result in ge_equivalent.items():
        print(f"  {expectation_name:<58} -> {'PASS' if result.passed else 'FAIL'} ({result.failed_rows} bad rows)")

print("\nEither way, the CONCEPT is identical: a named, reusable,")
print("self-documenting assertion about what 'good data' means for this")
print("column - checked automatically, every run, instead of by memory.")


"""
---------------------------------------------------------------------
10. WHAT TO DO WITH FAILURES: QUARANTINE vs HARD-FAIL THE BATCH  ⭐⭐⭐
---------------------------------------------------------------------
A rule's "critical"/"warning" label above only affects how loudly a
BAD ROW is reported - every row-level failure, of either severity,
gets QUARANTINED (routed to a rejects table with a reason) while the
rest of the batch loads normally, because "one bad row" is never a
reason to withhold nine good ones. HARD-FAILING THE WHOLE BATCH is a
different, rarer decision reserved for TABLE-LEVEL invariants so
broken that no row can be trusted: a required column missing
entirely, or a required column that's almost ENTIRELY null (which
points to an upstream extraction bug, not a few dirty records).
---------------------------------------------------------------------
"""

print("\n--- Quarantine vs Hard-Fail ---")

class DataQualityError(Exception):
    """Raised for a batch-level invariant so severe the whole load must stop."""

REQUIRED_COLUMNS = {
    "order_id", "customer_id", "order_date", "product_sku",
    "quantity", "unit_price", "total_amount", "status",
}
NEVER_MOSTLY_NULL = ["order_id", "customer_id"]

def enforce_critical_invariants(df, required_columns=REQUIRED_COLUMNS, watch_columns=NEVER_MOSTLY_NULL, null_threshold=0.9):
    missing_cols = required_columns - set(df.columns)
    if missing_cols:
        raise DataQualityError(f"batch is missing required column(s) {sorted(missing_cols)} - cannot safely load")
    for col in watch_columns:
        null_rate = df[col].isna().mean()
        if null_rate >= null_threshold:
            raise DataQualityError(f"column '{col}' is {null_rate:.0%} null - looks like an extraction failure, not routine bad data")

# Path A: quarantine - route bad ROWS out, keep the batch moving
def quarantine_split(df, rule_results):
    reasons = {i: [] for i in df.index}
    for r in rule_results:
        for idx in r.failed_indices:
            reasons[idx].append(r.rule_name)
    is_clean = pd.Series([len(reasons[i]) == 0 for i in df.index], index=df.index)
    clean_df = df.loc[is_clean].copy()
    rejects_df = df.loc[~is_clean].copy()
    rejects_df["rejection_reasons"] = [", ".join(reasons[i]) for i in rejects_df.index]
    return clean_df, rejects_df

enforce_critical_invariants(orders_df)      # passes: no required column missing, no column catastrophically null
print("critical invariants OK for orders_df - proceeding to row-level quarantine.")

clean_df, rejects_df = quarantine_split(orders_df, results)
print(f"\n{len(clean_df)} clean rows -> would load into the warehouse orders table.")
print(f"{len(rejects_df)} rejected rows -> routed to a rejects table/file with reasons:")
print(rejects_df[["order_id", "rejection_reasons"]])
logger.info("validation gate: %d loaded, %d quarantined", len(clean_df), len(rejects_df))

# Path B: hard-fail - a structural problem no amount of row-quarantining can fix
print("\nsimulating a batch with 'unit_price' dropped entirely upstream:")
corrupted_missing_col = orders_df.drop(columns=["unit_price"])
try:
    enforce_critical_invariants(corrupted_missing_col)
except DataQualityError as e:
    logger.error("hard-fail: %s", e)
    print("  batch load ABORTED (nothing partially loaded):", e)

print("\nsimulating a batch where customer_id came back almost entirely null:")
corrupted_mostly_null = orders_df.copy()
corrupted_mostly_null["customer_id"] = None   # whole-column assign, not .loc (pandas 3.0's
                                                # stricter .loc setitem rejects None into a
                                                # float64 column with a LossySetitemError)
try:
    enforce_critical_invariants(corrupted_mostly_null)
except DataQualityError as e:
    logger.error("hard-fail: %s", e)
    print("  batch load ABORTED (nothing partially loaded):", e)


"""
---------------------------------------------------------------------
11. SCHEMA EVOLUTION: NEW, MISSING, AND CHANGED-TYPE COLUMNS  ⭐⭐⭐
---------------------------------------------------------------------
Upstream sources change shape without warning, and the THREE ways
they change need three DIFFERENT responses:
    NEW column      -> log a warning, keep going (nothing downstream
                        depends on it yet - it's just ignored/dropped
                        by an explicit column SELECT until you decide
                        to intentionally start using it).
    MISSING column   -> almost always a hard-fail: something downstream
                        is DEFINITELY reading that column, and there is
                        no safe default for "the price just isn't here."
    CHANGED type     -> depends: check whether the new type is still
                        losslessly coercible to the old one (a warn-and-
                        recast situation) or genuinely incompatible
                        (treat like a missing column).
---------------------------------------------------------------------
"""

print("\n--- Schema Evolution: New, Missing, and Changed-Type Columns ---")

expected_schema = orders_df.dtypes.astype(str).to_dict()
print("expected schema (captured from a known-good batch):")
for col, dtype in expected_schema.items():
    print(f"  {col:<14} {dtype}")

# Simulate tomorrow's incoming batch: a new column, a dropped column,
# and total_amount arriving as text instead of a float
incoming_v2 = orders_df.copy()
incoming_v2["gift_wrap"] = False                      # NEW, unrequested column
incoming_v2 = incoming_v2.drop(columns=["unit_price"])  # MISSING required column
incoming_v2["total_amount"] = incoming_v2["total_amount"].astype(str)  # CHANGED type

def diff_schema(expected: dict, actual_df: pd.DataFrame) -> dict:
    actual = actual_df.dtypes.astype(str).to_dict()
    expected_cols, actual_cols = set(expected), set(actual)
    return {
        "new_columns": sorted(actual_cols - expected_cols),
        "missing_columns": sorted(expected_cols - actual_cols),
        "changed_type_columns": [
            (col, expected[col], actual[col])
            for col in sorted(expected_cols & actual_cols)
            if expected[col] != actual[col]
        ],
    }

diff = diff_schema(expected_schema, incoming_v2)
print("\nschema diff against tomorrow's simulated incoming batch:")
print(" ", diff)

for col in diff["new_columns"]:
    logger.warning("new unexpected column '%s' - logging and continuing, not failing", col)

for col, expected_dtype, actual_dtype in diff["changed_type_columns"]:
    recoverable = pd.to_numeric(incoming_v2[col], errors="coerce").notna().all()
    if recoverable:
        logger.warning("column '%s' changed dtype %s -> %s but is still losslessly numeric - recast and continue",
                        col, expected_dtype, actual_dtype)
    else:
        logger.error("column '%s' changed dtype %s -> %s and is NOT recoverable - treat like a missing column", col, expected_dtype, actual_dtype)

if diff["missing_columns"]:
    try:
        raise DataQualityError(f"required column(s) {diff['missing_columns']} disappeared from the source - hard-failing the batch")
    except DataQualityError as e:
        logger.error("hard-fail: %s", e)
        print("  batch load ABORTED due to schema evolution:", e)


"""
---------------------------------------------------------------------
12. WHERE VALIDATION LIVES IN THE PIPELINE  ⭐⭐⭐
---------------------------------------------------------------------
Validation is a GATE, not a garnish: it sits as an explicit step
BETWEEN transform and load, every run, never skipped "just this once"
under deadline pressure - the entire point is catching the batch that
would otherwise get through unnoticed. Structurally:

    extract() -> transform() -> [VALIDATION GATE] -> load()
                                        |
                          enforce_critical_invariants() (hard-fail path)
                                        |
                          run_validation_suite() + quarantine_split()
                                        |
                       clean_df -> load()   rejects_df -> rejects table

And the gate's OWN output is itself something to log and monitor -
row counts loaded vs. quarantined, which named rules failed and how
often, trending over days - exactly the observability theme from this
repo's Exception Handling notes ("one bad record shouldn't kill the
batch") applied one level up: one bad VALIDATION RUN shouldn't go
unnoticed either.
---------------------------------------------------------------------
"""

print("\n--- Where Validation Lives in the Pipeline ---")

def run_etl_batch(raw_df):
    transformed_df = raw_df.copy()  # transform step would normalize/derive fields here
    try:
        enforce_critical_invariants(transformed_df)
    except DataQualityError as e:
        logger.error("batch aborted before load: %s", e)
        return None
    rule_results = run_validation_suite(transformed_df, order_rules)
    clean, rejects = quarantine_split(transformed_df, rule_results)
    logger.info("validation gate: %d/%d rows passed, %d quarantined",
                len(clean), len(transformed_df), len(rejects))
    print(f"  load(): writing {len(clean)} rows to warehouse.orders")
    print(f"  quarantine(): writing {len(rejects)} rows to warehouse.orders_rejects")
    return clean

final_clean = run_etl_batch(orders_df)
print(f"\nrun_etl_batch() completed - {len(final_clean)} rows made it to the warehouse.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Six categories of ETL data quality checks:
    Schema/type       -> are columns/types what we expect? (pd.to_numeric/
                          to_datetime with errors="coerce" to find breaks)
    Completeness       -> df[col].isna().sum() / len(df) per required column
    Uniqueness         -> df.duplicated(subset=[key], keep=False)
    Range/bounds       -> Series.between(low, high) (NaN -> False, free win)
    Referential/cross  -> df[col].isin(known_values); (a - b*c).abs() <= tol
    Freshness/volume   -> row-count band + max(date) staleness vs. "today"

Rule engine pattern:
    ValidationRule(name, description, severity, check_fn) -> ValidationResult
    check_fn(df) -> bool Series, True = row passes
    run ALL rules always -> collect ALL failures -> one report, never
    stop at the first problem found

great_expectations -> declarative version of the same idea:
    expect_column_values_to_not_be_null / _to_be_between / _to_be_in_set /
    _to_be_unique / expect_table_row_count_to_be_between
    (heavy optional dependency - guard the import, fall back to your
    own rule engine, which IS the same concept with no extra install)

Failure routing:
    row-level bad value       -> QUARANTINE that row, keep loading the rest
    required column missing   -> HARD-FAIL the whole batch
    required column ~all null -> HARD-FAIL the whole batch (extraction bug)

Schema evolution:
    NEW column      -> log + continue   (nothing depends on it yet)
    MISSING column  -> hard-fail         (downstream WILL read it)
    CHANGED type    -> warn + recast if losslessly coercible,
                       else treat like a missing column

Pipeline placement:
    extract -> transform -> [VALIDATE: hard-fail check, then rule
    suite + quarantine] -> load             (never skipped; its own
    pass/fail counts get logged/monitored like any other pipeline metric)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - DATA VALIDATION FOR ETL
=====================================================================

1. How would you validate incoming data quality before loading it
   into a warehouse?

2. How do you handle schema evolution in incoming data?

3. Walk through the six categories of data quality checks in this
   file (schema/type, completeness, uniqueness, range, referential/
   cross-field, freshness/volume) and give a concrete example of each
   against the `orders_df` data.

4. In `run_validation_suite`, why does every rule run against every
   row regardless of what earlier rules found, instead of stopping at
   the first failure like `validate_naive` does?

5. What is the difference between a rule's "critical"/"warning"
   severity label in this file's rule engine and the separate
   decision to hard-fail an entire batch in
   `enforce_critical_invariants`? Why are they two different things?

6. Why does the duplicated `order_id` 1003 get caught by a uniqueness
   rule but not by a not-null or a range rule?

7. Explain why order 1009 fails validation even though its
   `quantity`, `unit_price`, and `status` are all individually valid.
   Which category of check is the only one that catches it, and why?

8. When would you route a bad row to a quarantine/rejects table
   versus hard-failing the entire batch? Give one concrete example of
   each from this file.

9. Why does pandas silently upgrade an integer column like
   `customer_id` to `float64` the instant one value goes missing, and
   what does that mean for writing a naive `dtype == "int64"` schema
   check?

10. What is the conceptual relationship between
    `great_expectations.expect_column_values_to_be_between(...)` and
    the hand-rolled `numeric_range_rule(...)` factory in this file?
    Why might a team choose the heavier library anyway, despite the
    dependency cost?

11. Using only `df.columns` and `df.dtypes`, how would you detect that
    an upstream source added a new column overnight, dropped a
    required one, or changed an existing column's type? Walk through
    what `diff_schema()` does here.

12. Why is a brand-new, unexpected column usually safe to just log and
    continue, while a missing expected column usually is not?

13. In `diff_schema`'s handling of a changed-type column (like
    `total_amount` arriving as text), how does this file decide
    between "warn and recast" versus "treat like a missing column"?

14. Where should the validation step sit in an ETL pipeline, and why
    does it need to run strictly between transform and load rather
    than, say, being a "nice to have" that only runs when someone
    remembers?

15. How would you implement a freshness/volume check that flags "we
    only got a fraction of our usual daily order volume today" without
    hard-coding today's exact expected row count?

16. If a new required column were added downstream, how would you
    extend `REQUIRED_COLUMNS` and `expected_schema` in this file to
    make sure a future regression in that column gets caught by the
    same gate?
=====================================================================
"""
