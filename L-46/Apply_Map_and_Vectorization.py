"""
=====================================================================
PANDAS apply(), map(), df.map() [formerly applymap], AND
VECTORIZATION - Complete Notes with Executable Examples
=====================================================================

Pandas gives you several ways to run "custom logic" against a
Series or DataFrame, and interviewers love this topic because
picking the WRONG one has real performance consequences at scale:

    Series.map(dict_or_func)   - element-wise, ONE column, best for
                                  simple value substitution/lookup
    Series.apply(func)         - element-wise, ONE column, for logic
                                  too complex to express as a mapping
    DataFrame.apply(func, axis=...) - runs func over each COLUMN
                                  (axis=0) or each ROW (axis=1)
    DataFrame.map(func)        - element-wise over EVERY cell in the
                                  whole frame (pandas < 2.1 called
                                  this `DataFrame.applymap` - it was
                                  renamed/folded into `.map()` and
                                  `applymap` was REMOVED entirely in
                                  pandas 3.0)
    Vectorization              - no Python-level loop or per-element
                                  function call at all; the whole
                                  operation is pushed down into
                                  compiled C/NumPy loops in one shot

The single most important idea in this file: `apply()` and `map()`
still call a Python function ONCE PER ELEMENT (or once per row) from
regular Python bytecode - they are convenience wrappers around a
loop, not magic. VECTORIZED operations skip the per-element Python
function call entirely and operate on whole arrays at the C level.
That difference is why "vectorization vs apply() vs a for loop" is
one of the most reliable Pandas interview questions there is - and
this file proves it with real, measured timings, not folklore.
=====================================================================
"""

import time
import numpy as np
import pandas as pd

print("--- Overview ---")
print("map()/apply() are convenience wrappers around a Python-level loop.")
print("Vectorized ops push the whole computation into compiled C/NumPy -")
print("no per-element Python function-call overhead at all.")
print(f"(pandas version in this environment: {pd.__version__})")


"""
---------------------------------------------------------------------
1. SERIES.MAP() - ELEMENT-WISE VALUE SUBSTITUTION (DICT OR FUNCTION)  ⭐⭐⭐
---------------------------------------------------------------------
`Series.map()` is the right tool when you're doing a LOOKUP/
SUBSTITUTION - swapping each value for another value, either via a
dict (or another Series used as a lookup table) or via a simple
function. It is NOT for row-wise logic across multiple columns -
that's what DataFrame.apply(axis=1) is for (section 3).

THE #1 GOTCHA: if a value in the Series has NO matching key in the
dict, `.map()` does not raise - it silently replaces it with NaN.
This quietly corrupts data if you're not expecting it.
---------------------------------------------------------------------
"""

print("\n--- Series.map(): Dict-Based Substitution ---")

status_codes = pd.Series([200, 404, 500, 200, 302, 999], name="http_status")
status_labels = {
    200: "OK",
    404: "Not Found",
    500: "Server Error",
    302: "Redirect",
    # NOTE: 999 is deliberately NOT in this dict - see the gotcha below
}

mapped_labels = status_codes.map(status_labels)
print("status codes:  ", status_codes.tolist())
print("mapped labels: ", mapped_labels.tolist())

print("\nGOTCHA: value 999 had no matching dict key, so map() produced")
print("NaN instead of raising an error - it will not warn you either:")
print(mapped_labels)

# FIX: give map() a fallback via .fillna(), or map with a function that
# uses dict.get(key, default) so unmapped codes get an explicit label
# instead of a silent NaN
safe_labels = status_codes.map(status_labels).fillna("Unknown Status")
print("\nfixed with .fillna() fallback:")
print(safe_labels.tolist())

print("\n--- Series.map(): Function-Based Substitution ---")

# map() also accepts a plain function - applied to each element in turn
temperatures_celsius = pd.Series([0, 20, 37, 100, -40], name="celsius")
temperatures_fahrenheit = temperatures_celsius.map(lambda c: c * 9 / 5 + 32)
print("celsius:   ", temperatures_celsius.tolist())
print("fahrenheit:", temperatures_fahrenheit.tolist())
print("\n(this specific conversion is ALSO purely arithmetic and could be")
print("done faster with straight vectorized math - see section 5/6 - but")
print("map() with a function is fine for small Series or one-off scripts.)")


"""
---------------------------------------------------------------------
2. SERIES.APPLY() - LOGIC TOO COMPLEX FOR A SIMPLE DICT MAPPING  ⭐⭐
---------------------------------------------------------------------
`Series.apply()` behaves like `.map()` for a single Series (it also
calls your function once per element), but it's the natural choice
when the transformation is genuine LOGIC - conditionals, string
parsing, multiple branches - rather than a lookup table you could
express as a dict. Reach for `.map()` with a dict first; reach for
`.apply()` once the rule can't be written as `{key: value}` pairs.
---------------------------------------------------------------------
"""

print("\n--- Series.apply(): Logic Too Complex for a Dict ---")

emails = pd.Series([
    "alice@pattern.com",
    "bob@partner-vendor.co",
    "not-an-email",
    "eve@pattern.com",
])

def classify_email_domain(email: str) -> str:
    """Too many branches/edge cases to express as a flat {value: label} dict."""
    if "@" not in email:
        return "invalid"
    domain = email.split("@", 1)[1]
    if domain == "pattern.com":
        return "internal"
    if domain.endswith(".co") or domain.endswith(".com"):
        return "external_partner"
    return "unknown_domain"

domain_classes = emails.apply(classify_email_domain)
print("emails:  ", emails.tolist())
print("classes: ", domain_classes.tolist())


"""
---------------------------------------------------------------------
3. DATAFRAME.APPLY() - axis=0 (COLUMN-WISE) vs axis=1 (ROW-WISE)  ⭐⭐⭐
---------------------------------------------------------------------
This is a constant source of interview confusion, so anchor it with
one rule: the `axis` argument names the axis that gets COLLAPSED /
walked ALONG, and your function receives whatever's left as a Series.

    axis=0 (the default) -> func receives ONE COLUMN at a time
                             (a Series indexed by ROW label) - think
                             "apply DOWN each column"
    axis=1               -> func receives ONE ROW at a time
                             (a Series indexed by COLUMN label) - think
                             "apply ACROSS each row"
---------------------------------------------------------------------
"""

print("\n--- DataFrame.apply(): axis=0 (Column-Wise) ---")

sales_df = pd.DataFrame({
    "region_north": [100, 210, 120, 300],
    "region_south": [80, 95, 250, 90],
    "region_east":  [200, 150, 130, 220],
})
print(sales_df)

# axis=0: func gets each COLUMN (a Series of 4 values) - one result per column
column_ranges = sales_df.apply(lambda col: col.max() - col.min(), axis=0)
print("\ncolumn-wise range (max - min) per region, axis=0:")
print(column_ranges)

print("\n--- DataFrame.apply(): axis=1 (Row-Wise) ---")

# axis=1: func gets each ROW (a Series of 3 values, one per region) -
# used here to derive one new value PER ROW from MULTIPLE columns
def best_region_for_day(row: pd.Series) -> str:
    return row.idxmax()   # column name holding the max value in this row

sales_df["best_region"] = sales_df.apply(best_region_for_day, axis=1)
print(sales_df)
print("\naxis=0 walked DOWN each column (3 results, one per region column).")
print("axis=1 walked ACROSS each row (4 results, one per day/row).")


"""
---------------------------------------------------------------------
4. DATAFRAME.MAP() - THE MODERN REPLACEMENT FOR applymap()  ⭐⭐
---------------------------------------------------------------------
`DataFrame.map()` applies a function to EVERY SINGLE CELL of the
whole frame, independent of row or column - useful for a uniform
transformation like formatting, rounding, or type coercion applied
frame-wide. In pandas versions before ~2.1 this was a SEPARATE method
called `DataFrame.applymap()`. As of pandas 3.0, `applymap()` has
been REMOVED entirely - its functionality was folded into
`DataFrame.map()`, so `.map()` is now the one method that works for
both a single Series AND a whole DataFrame.
---------------------------------------------------------------------
"""

print("\n--- DataFrame.map(): Whole-Frame Element-Wise Formatting ---")

prices_df = pd.DataFrame({
    "widget_a": [19.5, 22.0, 17.25],
    "widget_b": [8.0, 9.75, 11.1],
})

# BUGGY (on this environment): applymap() no longer exists in pandas 3.0
try:
    prices_df.applymap(lambda x: f"${x:.2f}")
except AttributeError as e:
    print("calling the OLD .applymap() on pandas 3.0 raises:")
    print(" ", e)

# FIXED: DataFrame.map() is the direct replacement, same behavior
formatted_prices = prices_df.map(lambda x: f"${x:.2f}")
print("\nfixed with DataFrame.map() (the pandas 3.0+ way):")
print(formatted_prices)


"""
---------------------------------------------------------------------
5. THE PERFORMANCE CORE: RAW LOOP vs iterrows() vs .apply() vs
   VECTORIZATION - A REAL MEASURED BENCHMARK  ⭐⭐⭐
---------------------------------------------------------------------
This is the single highest-value section in this file: "why is
vectorization faster than a Python for loop?" is one of the most
common Pandas interview questions there is (Syllabus Module 7 flags
it directly, and it's Top-15 Q11). Talking about it in the abstract
is weak - actually MEASURING it on a few-hundred-thousand-row
DataFrame, computing the IDENTICAL result four different ways, is
the convincing answer.

Scenario: an orders table with price, quantity, and a discount
percent per row. We need `line_total = price * quantity *
(1 - discount_pct / 100)` for every row - a classic ETL calculation.
---------------------------------------------------------------------
"""

print("\n--- Benchmark Setup: A Few-Hundred-Thousand-Row Orders Table ---")

N_ROWS = 200_000
rng = np.random.default_rng(seed=42)   # seeded for reproducible timings

orders_df = pd.DataFrame({
    "price": rng.uniform(5.0, 500.0, size=N_ROWS),
    "quantity": rng.integers(1, 20, size=N_ROWS),
    "discount_pct": rng.uniform(0.0, 30.0, size=N_ROWS),
})
print(f"orders_df has {len(orders_df):,} rows")
print(orders_df.head(3))


def compute_line_total(price: float, quantity: float, discount_pct: float) -> float:
    """The exact business logic, factored out so every approach below
    runs the IDENTICAL calculation - this is a fair benchmark, not a
    strawman."""
    return price * quantity * (1 - discount_pct / 100)


# --- (a) RAW PYTHON for LOOP, appending to a list ---
# Even without touching pandas row-indexing machinery, this still pays
# the cost of a Python bytecode loop iterating 200,000 times, with a
# Python-level function call and float arithmetic on every iteration.
prices_list = orders_df["price"].tolist()
quantities_list = orders_df["quantity"].tolist()
discounts_list = orders_df["discount_pct"].tolist()

start = time.perf_counter()
loop_results = []
for i in range(len(orders_df)):
    loop_results.append(
        compute_line_total(prices_list[i], quantities_list[i], discounts_list[i])
    )
loop_time = time.perf_counter() - start

# --- (b) DataFrame.apply(axis=1) ---
# Pandas builds a Series object for EVERY ROW before handing it to the
# lambda - that Series construction is extra overhead on top of the
# same per-row Python function call as the raw loop.
start = time.perf_counter()
apply_results = orders_df.apply(
    lambda row: compute_line_total(row["price"], row["quantity"], row["discount_pct"]),
    axis=1,
)
apply_time = time.perf_counter() - start

# --- (c) DataFrame.iterrows() - the worst common option ---
# iterrows() also builds a new Series per row (with type-unification
# across the row's dtypes, since a Series must have a single dtype),
# and hands it back through a generator - typically the slowest of
# all four approaches, despite "looking like" ordinary Python.
start = time.perf_counter()
iterrows_results = []
for _, row in orders_df.iterrows():
    iterrows_results.append(
        compute_line_total(row["price"], row["quantity"], row["discount_pct"])
    )
iterrows_time = time.perf_counter() - start

# --- (d) TRUE VECTORIZATION - no per-row Python call at all ---
# This expression is evaluated column-at-a-time: price*quantity produces
# one whole new NumPy array in a single compiled C loop, then the
# subtraction/multiplication against discount_pct is another single
# compiled pass - the Python interpreter only issues a handful of
# instructions total, regardless of whether there are 200 or 200,000 rows.
start = time.perf_counter()
vectorized_results = orders_df["price"] * orders_df["quantity"] * (
    1 - orders_df["discount_pct"] / 100
)
vectorized_time = time.perf_counter() - start

# Sanity check: all four approaches must agree (within float tolerance)
assert np.allclose(loop_results, vectorized_results)
assert np.allclose(apply_results, vectorized_results)
assert np.allclose(iterrows_results, vectorized_results)

print("\n--- Measured Results (identical calculation, four ways) ---")
print(f"{'method':<28}{'seconds':>12}{'rows/sec':>16}")
for label, elapsed in [
    ("raw Python for loop", loop_time),
    ("DataFrame.apply(axis=1)", apply_time),
    ("DataFrame.iterrows()", iterrows_time),
    ("vectorized (numpy/pandas)", vectorized_time),
]:
    rows_per_sec = N_ROWS / elapsed if elapsed > 0 else float("inf")
    print(f"{label:<28}{elapsed:>12.4f}{rows_per_sec:>16,.0f}")

print("\n--- Speedup vs Vectorization ---")
for label, elapsed in [
    ("raw Python for loop", loop_time),
    ("DataFrame.apply(axis=1)", apply_time),
    ("DataFrame.iterrows()", iterrows_time),
]:
    speedup = elapsed / vectorized_time if vectorized_time > 0 else float("inf")
    print(f"vectorization is ~{speedup:,.0f}x faster than {label}")


"""
---------------------------------------------------------------------
6. WHY VECTORIZATION WINS: WHAT'S ACTUALLY HAPPENING UNDER THE HOOD  ⭐⭐⭐
---------------------------------------------------------------------
The benchmark above isn't a fluke of this machine - it reflects a
real architectural difference, and this is the part interviewers
actually want you to articulate:

    - A Python `for` loop, `.apply()`, and `.iterrows()` all execute
      ONE Python-bytecode-interpreted function call PER ROW (or per
      element). Each call has real overhead: looking up the function
      object, pushing a new stack frame, boxing/unboxing Python
      float/int objects, and returning a result - repeated 200,000
      times. `.iterrows()` adds even more: it materializes a brand
      new pandas Series for every single row (with dtype unification
      across that row's columns) before your code ever runs.
    - A vectorized expression (`df["a"] * df["b"]`) instead dispatches
      ONCE into NumPy's compiled C implementation, which loops over
      the underlying contiguous memory buffer directly - no per-
      element Python object creation, no per-element interpreter
      bytecode, no per-row Series construction. The "loop" still
      technically happens, but it happens in compiled C, operating
      on raw machine floats/ints packed in memory (SIMD-friendly),
      not in the CPython interpreter.

In short: `.apply()` and `.iterrows()` are still "a for loop wearing
a pandas costume" - they don't avoid Python's per-element overhead,
they just hide the `for` keyword from you.
---------------------------------------------------------------------
"""

print("\n--- Why Vectorization Wins (Conceptual Summary) ---")
print("loop / apply / iterrows -> Python bytecode runs ONCE PER ROW")
print("vectorized numpy/pandas -> ONE dispatch into a compiled C loop")
print("over the whole column's raw memory buffer, no per-row Python cost")


"""
---------------------------------------------------------------------
7. DECISION GUIDE: VECTORIZE FIRST, apply() AS A LAST RESORT, NEVER
   .iterrows() OVER ROWS  ⭐⭐⭐
---------------------------------------------------------------------
A practical rule of thumb, in priority order:

    1. Can this be written as arithmetic/boolean ops on whole
       columns (`df["a"] + df["b"]`, `np.where(cond, x, y)`,
       `.str.contains()`, `pd.cut()`, etc.)? -> VECTORIZE. Always
       prefer this. It's faster AND usually more readable.
    2. Is it a simple value-for-value lookup/substitution on ONE
       column? -> `Series.map()` with a dict.
    3. Is the per-element logic genuinely too branchy/stateful for a
       vectorized expression or a dict (complex conditional chains,
       regex-heavy string parsing, calling an external/non-vectorized
       function)? -> `.apply()` is acceptable - it's still Python-
       loop speed, but it's the correct tool once true vectorization
       isn't feasible.
    4. Never reach for `.iterrows()` to process DataFrame rows in new
       code - the benchmark above shows it's typically the SLOWEST of
       every option, specifically because it rebuilds a Series per
       row on top of the same per-row Python overhead `.apply()` and
       a plain loop already pay. If you must iterate row-by-row
       (rare), `itertuples()` is meaningfully faster than
       `iterrows()` because it yields lightweight namedtuples instead
       of constructing a full Series per row - but it's still not
       vectorization, and should be a last resort after step 1-3.
---------------------------------------------------------------------
"""

print("\n--- Decision Guide ---")
print("1. Whole-column arithmetic/boolean logic possible? -> VECTORIZE")
print("2. Simple one-column value substitution?           -> Series.map(dict)")
print("3. Logic too complex to vectorize or map?           -> .apply()")
print("4. Iterating rows in new code?                      -> avoid .iterrows();")
print("   prefer itertuples() if you truly must, but vectorize first")


"""
---------------------------------------------------------------------
8. DATA ENGINEERING USE CASE: NORMALIZING AN INGESTED ORDERS TABLE  ⭐⭐⭐
---------------------------------------------------------------------
Pulling it all together on one small, realistic ingestion task: a
raw orders extract needs (1) a human-readable status via a dict
lookup, (2) a derived per-row flag needing multi-column logic, (3) a
uniform display-formatting pass over every numeric cell, and (4) the
actual dollar calculation - and each step deliberately uses the tool
that's actually appropriate for it, per the decision guide above.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Normalizing an Orders Extract ---")

raw_orders = pd.DataFrame({
    "order_id": [1001, 1002, 1003, 1004],
    "status_code": [1, 2, 3, 9],           # 9 is an unrecognized/new code
    "price": [49.99, 12.50, 200.0, 75.0],
    "quantity": [2, 5, 1, 3],
    "discount_pct": [0.0, 10.0, 25.0, 0.0],
})

# Step 1: Series.map() with a dict - simple value substitution
STATUS_LABELS = {1: "pending", 2: "shipped", 3: "delivered"}
raw_orders["status"] = raw_orders["status_code"].map(STATUS_LABELS).fillna("unknown")

# Step 2: DataFrame.apply(axis=1) - genuine multi-column conditional
# logic (a large, low-discount order) that isn't a simple lookup
def is_priority_order(row: pd.Series) -> bool:
    return row["price"] * row["quantity"] > 150 and row["discount_pct"] < 20

raw_orders["is_priority"] = raw_orders.apply(is_priority_order, axis=1)

# Step 3: VECTORIZED math for the actual dollar figure - no reason to
# use apply() here, it's pure arithmetic on whole columns
raw_orders["line_total"] = raw_orders["price"] * raw_orders["quantity"] * (
    1 - raw_orders["discount_pct"] / 100
)

# Step 4: DataFrame.map() for a uniform display-formatting pass over
# just the currency columns - one function, every cell, frame-wide
raw_orders[["price", "line_total"]] = raw_orders[["price", "line_total"]].map(
    lambda x: round(x, 2)
)

print(raw_orders)
print("\nEach step used the CHEAPEST tool that could correctly express")
print("it - vectorized math for arithmetic, map() for lookups/uniform")
print("formatting, and apply() reserved only for genuine row-wise logic.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Series.map(dict)        -> element-wise lookup/substitution, ONE column
                            unmapped keys silently become NaN!
Series.map(func)        -> element-wise function, ONE column
Series.apply(func)      -> same as map(func) for a Series; use when
                            logic is too complex for a flat dict

DataFrame.apply(f, axis=0) -> f receives each COLUMN (default axis)
DataFrame.apply(f, axis=1) -> f receives each ROW (multi-col logic)

DataFrame.map(func)     -> element-wise over EVERY cell, whole frame
                            (this REPLACED DataFrame.applymap(), which
                            is REMOVED as of pandas 3.0)

Speed, fastest to slowest (measured above, ~200k rows):
    vectorized (numpy/pandas)  ->  fastest, no per-row Python call
    raw Python for loop        ->  per-row Python overhead
    DataFrame.apply(axis=1)    ->  per-row overhead + Series build
    DataFrame.iterrows()       ->  slowest: per-row Series + dtype
                                    unification on top of everything

Rule of thumb:
    vectorize whenever possible
    -> map() for simple one-column lookups
    -> apply() only when logic truly can't be vectorized/mapped
    -> never .iterrows() over rows in new code
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - apply(), map(), DataFrame.map() & VECTORIZATION
=====================================================================

1. Why is a vectorized NumPy/Pandas operation faster than a Python
   `for` loop doing the same calculation, in terms of what's actually
   executing at each step?

2. Compare Pandas `apply()` vs a fully vectorized operation - which
   is faster, and why? Use the `line_total` benchmark in this file to
   support your answer with real numbers.

3. What happens when `Series.map()` is given a dict that doesn't
   contain a key present in the Series (see `status_codes.map(status_labels)`
   with the unmapped `999` value)? How would you guard against it?

4. When would you choose `Series.map()` over `Series.apply()`, and
   vice versa?

5. Explain the difference between `DataFrame.apply(func, axis=0)`
   and `DataFrame.apply(func, axis=1)`. What does your function
   actually receive as its argument in each case?

6. What was `DataFrame.applymap()`, and what happened to it in
   pandas 3.0? What should you use instead, and does it behave any
   differently?

7. Why is `DataFrame.iterrows()` typically the SLOWEST way to process
   a DataFrame row-by-row, even slower than `.apply(axis=1)`? What
   extra work does it do on every single row?

8. If `.iterrows()` is discouraged, what's a faster alternative for
   the rare case where you truly must iterate rows one at a time, and
   why is it faster?

9. Given `sales_df` in this file, write the `axis=0` call that
   returns each region's max-minus-min range, and the `axis=1` call
   that returns the name of the best-performing region per row.

10. In the orders-normalization use case, justify why `status` used
    `.map()`, `is_priority` used `.apply(axis=1)`, and `line_total`
    used plain vectorized arithmetic - what would go wrong (or just
    be needlessly slow) if you swapped the approaches?

11. Does `Series.apply()` or `DataFrame.apply(axis=1)` ever run
    faster than a hand-written Python `for` loop over the same data?
    Why or why not?

12. What is "boxing/unboxing" in the context of Python objects vs
    raw C/NumPy values, and how does it relate to why per-row Python
    function calls are expensive at scale?

13. If a transformation genuinely cannot be vectorized (e.g. it calls
    an external API per row, or applies a deeply branching regex),
    is it still worth trying to vectorize part of it? Give an example
    of partially vectorizing a mixed workload.

14. How would you rewrite `compute_line_total()`'s row-wise `.apply()`
    version as a single vectorized pandas expression, and what
    changes about how many times the Python interpreter actually
    runs?

15. Why does `np.allclose()` (rather than `==`) get used in this file
    to check that the loop, apply, iterrows, and vectorized results
    all agree?
=====================================================================
"""
