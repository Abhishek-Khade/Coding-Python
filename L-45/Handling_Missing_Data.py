"""
=====================================================================
HANDLING MISSING DATA IN PANDAS - fillna, dropna, and Duplicates
=====================================================================

Real-world data is never clean. Upstream systems drop fields, APIs
time out mid-record, humans leave form fields blank, and retried
requests write the same logical record twice. Before you can trust
any aggregate (`sum`, `mean`, `groupby`), you have to know exactly
what "missing" looks like in your DataFrame and decide, deliberately,
whether to DROP the incomplete rows or FILL them in.

This file covers the three things interviewers actually probe on
this topic:
    1. What pandas uses to represent "missing" (NaN / None / pd.NA /
       NaT) and the single most common bug around it: comparing with
       `==` instead of `.isna()`.
    2. The two competing strategies for handling missing values -
       `dropna()` (lose the row, keep the data honest) and `fillna()`
       / `.interpolate()` (keep the row, invent a value) - and the
       real trade-offs of each.
    3. Duplicate records - which are really just another form of
       "bad data" that shows up constantly when upstream systems
       retry failed requests.

The recurring theme: every one of these operations can SILENTLY
change your dataset's shape or values if you call it carelessly.
None of them raise an exception when they discard 40% of your rows
or zero out half your revenue column - so knowing exactly what each
call does, and inspecting before/after, is the actual skill being
tested.
=====================================================================
"""

import numpy as np
import pandas as pd

print("--- Overview ---")
print("Missing data in pandas shows up as NaN/None/pd.NA/NaT.")
print("dropna() discards incomplete rows; fillna()/interpolate() invent")
print("values to keep them. duplicated()/drop_duplicates() handle the")
print("other half of 'dirty data': records that showed up more than once.")


"""
---------------------------------------------------------------------
1. WHAT "MISSING" ACTUALLY MEANS IN PANDAS  ⭐⭐⭐
---------------------------------------------------------------------
pandas has FOUR different-looking "nothing" values, and which one you
get depends on the column's dtype:
    np.nan   -> the classic float "Not a Number", used for missing
                values in float64 columns (and object columns too)
    None     -> Python's null object; pandas silently upcasts a
                numeric column containing None to float64 + NaN
    pd.NaT   -> "Not a Time" - the missing-value marker for
                datetime64 columns
    pd.NA    -> pandas' own newer "generic missing" scalar, used by
                the nullable dtypes (Int64, boolean, string[python])
                introduced to fix NaN's biggest problem: it can only
                live in a float column, silently converting your
                "1, 2, missing, 4" integers into "1.0, 2.0, NaN, 4.0".

The critical, most-tested fact about ALL of these: NaN is defined by
the IEEE 754 floating point spec to NEVER equal itself. This isn't a
pandas quirk - it's true of raw Python floats.
---------------------------------------------------------------------
"""

print("\n--- What 'Missing' Actually Means ---")

# Four ways "nothing" shows up, depending on dtype
mixed = pd.DataFrame({
    "float_col": [1.0, np.nan, 3.0],          # NaN: missing float
    "obj_col": ["a", None, "c"],               # None: missing object
    "date_col": [pd.Timestamp("2026-01-01"), pd.NaT, pd.Timestamp("2026-01-03")],
    "nullable_int": pd.array([1, pd.NA, 3], dtype="Int64"),  # pd.NA: nullable dtype
})
print(mixed)
print("\ndtypes:\n", mixed.dtypes)

# THE classic gotcha, proven live: NaN never equals itself
print("\nfloat('nan') == float('nan') ->", float("nan") == float("nan"))
print("np.nan == np.nan             ->", np.nan == np.nan)
print("pd.NA == pd.NA                ->", pd.NA == pd.NA, "(returns <NA>, not True/False!)")

# BUGGY: trying to find missing values with == silently finds NOTHING
buggy_mask = mixed["float_col"] == np.nan
print("\nBUGGY mask using `== np.nan`:")
print(buggy_mask.tolist(), "-> every value is False, even the real NaN!")
print("No exception is raised - this just quietly returns the wrong answer.")

# FIXED: .isna() / .isnull() are aliases and are the only correct way
fixed_mask = mixed["float_col"].isna()
print("\nFIXED mask using `.isna()`:")
print(fixed_mask.tolist(), "-> correctly flags index 1")
print(".isnull() is a pure alias for .isna() - use whichever reads better.")
print("Rule: NEVER compare to NaN with `==` or `!=` - always use .isna()/.notna().")


"""
---------------------------------------------------------------------
2. DETECTING MISSINGNESS ACROSS A REALISTIC DATAFRAME  ⭐⭐⭐
---------------------------------------------------------------------
Before deciding whether to drop or fill anything, profile the damage:
how many nulls per column, what fraction of each column, and whether
missingness is scattered randomly or concentrated in certain rows.
`.isna().sum()` and `.info()` are the two fastest tools for this;
a quick ASCII "missingness matrix" makes the PATTERN visible too -
e.g. whether an entire column is only missing for a certain segment
of rows, which often points at a specific upstream cause.
---------------------------------------------------------------------
"""

print("\n--- Detecting Missingness Across a DataFrame ---")

# A realistic messy dataset: an e-commerce order feed with scattered
# nulls in several columns, the kind that lands in a raw ingestion
# table before any cleaning has happened.
orders = pd.DataFrame({
    "order_id":       [101, 102, 103, 104, 105, 106, 107, 108],
    "customer_email": ["a@x.com", None, "c@x.com", "d@x.com", None, "f@x.com", "g@x.com", None],
    "region":         ["US", "US", "EU", None, "EU", "US", "APAC", "EU"],
    "quantity":       [2, 1, np.nan, 5, 3, np.nan, 1, 4],
    "unit_price":     [19.99, 9.50, 45.00, np.nan, 12.25, 8.00, np.nan, 30.00],
    "discount_pct":   [0.10, np.nan, np.nan, 0.05, np.nan, 0.0, 0.15, np.nan],
    "ship_date":      pd.to_datetime([
        "2026-01-02", "2026-01-03", None, "2026-01-05",
        "2026-01-06", None, "2026-01-08", None,
    ]),
})
print(orders)

print("\nmissing values per column (.isna().sum()):")
print(orders.isna().sum())

print("\nmissing values as a percentage of each column:")
print((orders.isna().mean() * 100).round(1).astype(str) + "%")

print("\n.info() shows non-null counts per column directly:")
orders.info()

# ASCII missingness matrix: quickly reveals PATTERN, not just totals -
# e.g. here row 7 (index 7) is missing three separate fields at once,
# which is a stronger signal of "this record failed mid-ingestion"
# than three isolated single-column nulls would be.
print("\nmissingness matrix ('.' = present, 'X' = missing):")
matrix = orders.isna().map(lambda x: "X" if x else ".")
print(matrix.to_string(index=True))


"""
---------------------------------------------------------------------
3. dropna(): how='any' vs how='all', subset=, thresh=  ⭐⭐⭐
---------------------------------------------------------------------
`dropna()` deletes rows (or columns, with axis=1) that contain nulls.
Four knobs control exactly HOW aggressive it is:
    how='any'   -> drop a row if ANY column is null (the default -
                   often too aggressive on a wide, sparsely-null table)
    how='all'   -> drop a row only if EVERY column is null (very
                   conservative - only kills fully-empty rows)
    subset=[...] -> only look at these columns when deciding to drop,
                    ignoring nulls elsewhere in the row
    thresh=N    -> keep a row only if it has at least N NON-null
                   values (a middle ground between 'any' and 'all')

The danger: `dropna()` never tells you what it threw away. Always
compare row counts before/after, and think about whether the missing
rows are random or systematically different (e.g. all from one
region) - dropping them can silently bias whatever you compute next.
---------------------------------------------------------------------
"""

print("\n--- dropna(): how, subset, thresh ---")

print("original row count:", len(orders))
print("how='any'  (drop if ANY column is null):", len(orders.dropna(how="any")), "rows survive")
print("how='all'  (drop only if EVERY column is null):", len(orders.dropna(how="all")), "rows survive")

# subset=: only care about nulls in specific columns
subset_dropped = orders.dropna(subset=["customer_email", "region"])
print("subset=['customer_email','region']:", len(subset_dropped), "rows survive")

# thresh=: keep rows with at least N non-null values out of 7 columns
thresh_dropped = orders.dropna(thresh=6)
print("thresh=6 (need >=6 of 7 columns present):", len(thresh_dropped), "rows survive")
print(thresh_dropped[["order_id", "quantity", "unit_price", "discount_pct"]])

print("\nTRADE-OFF: how='any' dropped", len(orders) - len(orders.dropna(how="any")),
      "of", len(orders), "rows here - almost half the feed, just because SOME")
print("column (often discount_pct, which is legitimately often absent) was null.")
print("Silently losing that much of a dataset to one loosely-related column is")
print("exactly the kind of mistake dropna() makes easy to commit by accident.")


"""
---------------------------------------------------------------------
4. fillna(): constant, mean/median/mode, and per-column strategies  ⭐⭐⭐
---------------------------------------------------------------------
`fillna()` keeps every row and substitutes a value for each null.
Common fill values:
    a literal constant       -> df["col"].fillna(0)
    the column's mean         -> for roughly-symmetric numeric data
    the column's median         -> more robust to outliers than mean
    the column's mode()[0]        -> for categorical/object columns
      (mode() returns a Series, since a column can be multi-modal -
      always index [0] to get a single fill value)
A dict lets you apply a DIFFERENT strategy per column in one call,
which is the realistic pattern for a multi-column messy table.
---------------------------------------------------------------------
"""

print("\n--- fillna(): Constants, Statistics, and Per-Column Dicts ---")

clean = orders.copy()

# Fill numeric columns with sensible per-column statistics, and the
# categorical column with its most frequent value - all in one call
fill_values = {
    "quantity": clean["quantity"].median(),        # robust to any outlier order size
    "unit_price": clean["unit_price"].mean(),        # prices tend to be roughly symmetric
    "discount_pct": 0.0,                               # business rule: "no data" means "no discount"
    "region": clean["region"].mode()[0],                 # most common region, for a categorical
}
print("fill values chosen per column:", fill_values)

clean = clean.fillna(fill_values)
print("\nafter per-column fillna() (email/ship_date deliberately left as-is):")
print(clean[["order_id", "region", "quantity", "unit_price", "discount_pct"]])

# BUGGY: filling every numeric NaN with 0 looks harmless but silently
# corrupts any aggregate computed afterward - see section 10 for why.
naive_fill = orders["unit_price"].fillna(0)
print("\nBUGGY: mean unit_price after fillna(0):", round(naive_fill.mean(), 2),
      " vs the TRUE mean of known prices:", round(orders["unit_price"].mean(), 2))
print("Zero-filling doesn't mean 'unknown' to pandas - it means 'this item is free',")
print("and every aggregate computed on that column from now on is now wrong.")


"""
---------------------------------------------------------------------
5. FORWARD-FILL AND BACKWARD-FILL FOR TIME-SERIES-LIKE DATA  ⭐⭐
---------------------------------------------------------------------
For data with a meaningful ORDER (a time series, or any row sequence
where "the last known value" is a reasonable guess), a statistic like
mean() throws away that order. `.ffill()` propagates the last valid
observation FORWARD into the gap; `.bfill()` propagates the next
valid observation BACKWARD. Note pandas 3.0 removed the old
`fillna(method="ffill")` spelling entirely - the dedicated methods are
now the only way to do this.
---------------------------------------------------------------------
"""

print("\n--- Forward-Fill and Backward-Fill for Time-Series Data ---")

daily_active_users = pd.Series(
    [1200, np.nan, np.nan, 1350, 1400, np.nan, 1500],
    index=pd.date_range("2026-01-01", periods=7, freq="D"),
    name="dau",
)
print(daily_active_users)

# The old keyword spelling is gone in pandas 3.0 - confirm live, then use the real API
try:
    daily_active_users.fillna(method="ffill")
except TypeError as e:
    print("\nfillna(method='ffill') in pandas 3.0:", e)

print("\n.ffill() - carries the last known DAU forward through the gap:")
print(daily_active_users.ffill())

print("\n.bfill() - carries the NEXT known DAU backward instead:")
print(daily_active_users.bfill())

print("\nffill().bfill() chained - fills a LEADING gap too (ffill alone can't):")
leading_gap = pd.Series([np.nan, np.nan, 10, 20, np.nan])
print("raw:            ", leading_gap.tolist())
print("ffill() only:   ", leading_gap.ffill().tolist(), "<- leading NaNs survive, nothing came before them")
print("ffill().bfill():", leading_gap.ffill().bfill().tolist())


"""
---------------------------------------------------------------------
6. .interpolate() AS A MIDDLE GROUND  ⭐
---------------------------------------------------------------------
Where ffill/bfill just copy a neighboring value, `.interpolate()`
estimates a value ON THE TREND LINE between the surrounding points
(linear by default; `method="time"` accounts for uneven date
spacing). This is often a better guess for a smoothly-changing metric
than either a flat carry-forward or a global mean.
---------------------------------------------------------------------
"""

print("\n--- .interpolate() as a Middle Ground ---")

print("original:                ", daily_active_users.tolist())
print("ffill:                   ", daily_active_users.ffill().tolist())
print("linear interpolate:      ", daily_active_users.interpolate().tolist())
print("\ninterpolate() guessed 1300 for day 2 (halfway between 1200 and 1400 in TIME),")
print("not a flat copy of 1200 like ffill() gives - a better fit for a trending metric.")


"""
---------------------------------------------------------------------
7. DETECTING DUPLICATE ROWS: .duplicated()  ⭐⭐⭐
---------------------------------------------------------------------
`.duplicated()` returns a boolean Series flagging rows that are exact
repeats of an earlier row (by default, across ALL columns). `keep=`
controls WHICH copy of each duplicate group is left unflagged:
    keep='first' (default) -> first occurrence is NOT flagged
    keep='last'              -> last occurrence is NOT flagged
    keep=False                 -> ALL copies in a duplicate group are
                                    flagged, including the first
This is the direct answer to "how do you detect duplicate records in
a DataFrame?" - it's almost always the first line of any dedup step.
---------------------------------------------------------------------
"""

print("\n--- Detecting Duplicate Rows with .duplicated() ---")

simple_dupes = pd.DataFrame({
    "sku": ["A100", "B200", "A100", "C300", "A100"],
    "warehouse": ["west", "east", "west", "west", "west"],
})
print(simple_dupes)

print("\nduplicated() default (keep='first'):")
print(simple_dupes.duplicated())
print("duplicated(keep='last'):")
print(simple_dupes.duplicated(keep="last"))
print("duplicated(keep=False) - flag EVERY copy, including the first:")
print(simple_dupes.duplicated(keep=False))
print("\ntotal duplicate rows found:", simple_dupes.duplicated().sum())


"""
---------------------------------------------------------------------
8. REMOVING DUPLICATES: drop_duplicates(subset=...) - THE FLAKY-RETRY
   PATTERN  ⭐⭐⭐
---------------------------------------------------------------------
The realistic trap: a full-row `.duplicated()` only catches EXACT
duplicates. A flaky upstream order API that times out and gets
retried often re-POSTs the SAME logical order with a different
`received_at` timestamp (or a `retry_attempt` counter) - so the rows
are NOT byte-identical, and a naive full-row duplicate check misses
them entirely. The fix is `subset=` on the columns that define
"same logical record" (here, `order_id`), combined with `keep=` to
decide which physical copy to retain.
---------------------------------------------------------------------
"""

print("\n--- drop_duplicates(subset=...): Flaky API Retry Records ---")

# order_id 2002 and 2004 were each POSTed twice by a retrying client -
# same order, but received_at and retry_attempt differ, so the rows
# are NOT identical across all columns.
raw_feed = pd.DataFrame({
    "order_id":      [2001, 2002, 2002, 2003, 2004, 2004],
    "customer":      ["A", "B", "B", "C", "D", "D"],
    "amount":        [50.00, 20.00, 20.00, 15.00, 99.99, 99.99],
    "retry_attempt": [0, 0, 1, 0, 0, 1],
    "received_at":   pd.to_datetime([
        "2026-02-01 10:00:00", "2026-02-01 10:01:00", "2026-02-01 10:01:05",
        "2026-02-01 10:02:00", "2026-02-01 10:03:00", "2026-02-01 10:03:04",
    ]),
})
print(raw_feed)

print("\nBUGGY: full-row .duplicated() (default, all columns) finds:",
      raw_feed.duplicated().sum(), "duplicates")
print("It misses both retries, because retry_attempt/received_at differ per copy -")
print("the rows LOOK unique even though they represent the SAME order twice.")

print("\nFIXED: .duplicated(subset=['order_id']) finds:",
      raw_feed.duplicated(subset=["order_id"]).sum(), "duplicates")

# keep='last' -> keep the LATEST retry attempt for each order, which
# is usually the one that actually succeeded end-to-end
deduped = raw_feed.drop_duplicates(subset=["order_id"], keep="last")
print("\ndrop_duplicates(subset=['order_id'], keep='last') - keeps the final retry:")
print(deduped)
print("\nRow count:", len(raw_feed), "->", len(deduped),
      "- this is exactly the kind of idempotency check an ETL load step needs")
print("before summing `amount`, or 2002/2004 would each be double-counted in revenue.")


"""
---------------------------------------------------------------------
9. PUTTING IT TOGETHER: AN IDEMPOTENT ORDER-FEED CLEANING STEP  ⭐⭐
---------------------------------------------------------------------
A real ingestion pipeline runs missing-data handling and dedup
together, in a fixed order, as one function - so re-running it on the
same batch (e.g. after a pipeline retry of its own) always produces
the same clean output. This is the "idempotent pipeline" idea from
ETL design applied concretely to a messy DataFrame.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Idempotent Order-Feed Cleaning ---")

def clean_order_feed(df: pd.DataFrame) -> pd.DataFrame:
    """Dedup a raw order feed, then fill/drop nulls with explicit, auditable rules.

    Order matters: dedup FIRST, so statistics used for filling (mean,
    median) aren't skewed by the same logical order being counted
    multiple times.
    """
    deduped = df.drop_duplicates(subset=["order_id"], keep="last")
    result = deduped.dropna(subset=["order_id", "customer"])   # can't process an order with no id/customer
    result = result.fillna({"amount": result["amount"].median()})
    return result.reset_index(drop=True)

cleaned_feed = clean_order_feed(raw_feed)
print(cleaned_feed)
print("\nrunning it again on the ALREADY-cleaned output changes nothing further")
print("(no more duplicates, no more nulls) - that's what makes it idempotent:")
print(cleaned_feed.equals(clean_order_feed(cleaned_feed)))


"""
---------------------------------------------------------------------
10. DECISION GUIDE: DROP vs FILL  ⭐⭐⭐
---------------------------------------------------------------------
    DROP the row (dropna) when:
        - Missingness is rare (a small % of rows) and looks RANDOM,
          not concentrated in one segment (check with groupby +
          isna().mean() before assuming this).
        - The missing column is essential to the analysis and there
          is no defensible way to guess it (e.g. a missing order_id -
          you cannot invent a primary key).
        - You have enough data that losing a few rows doesn't bias
          downstream aggregates.

    FILL the row (fillna / interpolate) when:
        - Missingness is common enough that dropping would lose a
          meaningful chunk of the dataset.
        - There's a defensible way to estimate the value: a stable
          business rule (blank discount = 0%), a robust statistic
          (median for skewed numeric data), the previous reading in
          a time series (ffill), or a trend (interpolate).
        - You need to preserve every row for OTHER columns' analysis
          even though one column has a gap.

    THE INTERVIEW TRAP - filling numeric NaN with 0 "to make it work":
        0 is not a neutral placeholder - it is a REAL, WRONG value
        that participates fully in every future sum() and mean().
        Section 4 showed this directly: fillna(0) on unit_price
        pulled the average price down from a real average to a much
        lower, WRONG average, and every revenue calculation built on
        that column downstream inherits the same silent corruption.
        Prefer: a real business-rule constant (0 IS correct for a
        genuinely-absent discount), a column statistic (mean/median),
        or dropping the row - never 0 "because it's a number and it
        made the error go away."

    Also worth naming in an interview: pandas/statistics literature
    calls these mechanisms MCAR (missing completely at random - safe
    to drop or fill with a simple statistic), MAR (missing depends on
    OTHER observed columns - e.g. discount_pct is null only for one
    region - a per-group fill is more honest than a single global
    one), and MNAR (missingness depends on the value itself - e.g.
    high earners not reporting income - no purely statistical fix
    exists; this needs a domain-informed rule).
---------------------------------------------------------------------
"""

print("\n--- Decision Guide: Drop vs Fill ---")
print("Rare + random + no safe guess  -> dropna()")
print("Common + estimable + must keep rows -> fillna() / interpolate()")
print("Filling numeric NaN with 0 'to make it work' -> corrupts every aggregate downstream")
print("(see section 4: fillna(0) understated the true mean unit_price)")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Missing-value markers:
    np.nan   -> missing float           pd.NaT -> missing datetime64
    None     -> missing object (often upcasts numeric cols to float)
    pd.NA    -> generic missing, nullable dtypes (Int64, boolean, ...)

Detecting missingness:
    df.isna() / df.isnull()   -> element-wise boolean mask (aliases)
    df.isna().sum()           -> null count per column
    df.isna().mean() * 100    -> null percentage per column
    df.info()                 -> shows non-null count per column
    NEVER use `== np.nan`      -> NaN != NaN by IEEE 754; always False

dropna():
    how='any'  -> drop row if ANY column null           (default)
    how='all'  -> drop row only if EVERY column null
    subset=[.] -> only consider these columns
    thresh=N   -> keep row if >= N non-null values present

fillna():
    fillna(0 / "unknown")        -> literal constant
    fillna(col.mean()/.median()) -> numeric statistic
    fillna(col.mode()[0])        -> categorical/object fill
    fillna({"a": x, "b": y})     -> different strategy per column
    .ffill() / .bfill()          -> carry last/next value across a gap
    .interpolate()                -> estimate along the trend, not a flat copy

Duplicates:
    df.duplicated()                    -> bool mask, keep='first' default
    df.duplicated(keep='last'/False)   -> change which copy(ies) are flagged
    df.drop_duplicates(subset=[...])   -> dedup by LOGICAL key, not full row
                                           (flaky-retry records differ in
                                           other columns like timestamps)

Drop vs fill: drop when missingness is rare/random/unguessable; fill
when it's common and estimable. NEVER fillna(0) on a numeric column
just to silence an error - it corrupts every aggregate after it.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - HANDLING MISSING DATA & DUPLICATES
=====================================================================

1. How do you detect and handle duplicate/null records in a
   DataFrame? (Walk through your full process, not just one method.)

2. Why does `float('nan') == float('nan')` evaluate to `False`, and
   what does that mean for how you must check a column for missing
   values instead of using `==`?

3. What is the difference between `np.nan`, `None`, `pd.NaT`, and
   `pd.NA`? When would a column end up holding each one?

4. What does `dropna(how='any')` do differently from
   `dropna(how='all')`? Given the `orders` DataFrame in this file,
   why did `how='any'` drop nearly half the rows?

5. What does the `thresh=` parameter of `dropna()` let you express
   that `how=` alone cannot?

6. When is filling a missing value with the column mean a reasonable
   choice, and when should you prefer the median instead?

7. Why is filling missing values in a numeric column with `0` often a
   dangerous default, even though it "makes the error go away"? Walk
   through the concrete effect on `.mean()` shown in this file.

8. How would you fill different columns of the same DataFrame with
   different strategies in a single `fillna()` call?

9. What is the difference between `.ffill()` and `.bfill()`, and why
   might chaining `.ffill().bfill()` be necessary to fully fill a
   Series with a leading gap?

10. What does `.interpolate()` do differently from `.ffill()`, and
    for what kind of column (e.g., a trending time series) does that
    difference actually matter?

11. What does `df.duplicated()` return by default, and how do the
    `keep='first'`, `keep='last'`, and `keep=False` options change
    which rows are flagged?

12. In the `raw_feed` example, a full-row `.duplicated()` call found
    zero duplicates even though `order_id` 2002 and 2004 were each
    submitted twice. Why did it miss them, and what change to the
    call fixes it?

13. Why does the order of operations matter in `clean_order_feed()` -
    specifically, why dedup the DataFrame BEFORE computing a fill
    value like `.median()` from it?

14. What does it mean for a data-cleaning function to be "idempotent",
    and how did `clean_order_feed()` demonstrate that property?

15. How would you decide, for a given column with missing values,
    whether to drop the affected rows or fill them? What role does
    the MISSINGNESS MECHANISM (random vs. dependent on other columns
    vs. dependent on the value itself) play in that decision?
=====================================================================
"""
