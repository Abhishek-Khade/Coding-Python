"""
=====================================================================
PANDAS GROUPBY, MERGE, JOIN & PIVOT_TABLE - Complete Notes with
Executable Examples
=====================================================================

These four operations are the backbone of almost every real
transformation step in a data pipeline: GROUPBY answers "how does
this metric break down by category?", MERGE/JOIN answer "how do I
combine two datasets that share a key?", and PIVOT_TABLE answers
"how do I reshape long data into a wide summary matrix?".

groupby() implements the SPLIT-APPLY-COMBINE model:
    1. SPLIT   - the DataFrame is broken into groups based on some
                 key (one column, several columns, or a function).
    2. APPLY   - a function (sum, mean, a custom callable, ...) runs
                 independently on EACH group.
    3. COMBINE - the individual results are stitched back into one
                 output object (a Series or DataFrame).
No group ever "sees" another group's rows during the APPLY step -
this is exactly what makes groupby a clean, parallelizable model
that mirrors SQL's `GROUP BY` and Spark's `groupBy` conceptually.

merge() and join() both COMBINE two DataFrames SIDE-BY-SIDE using a
shared KEY, the same way a SQL join does - merge() matches on
COLUMNS by default, join() matches on the INDEX by default. concat()
is fundamentally different: it just STACKS objects together (by row
or by column) based on ALIGNMENT of labels, with no key-matching
logic and no notion of "how" to combine (inner/outer/left/right).

pivot_table() takes long-format data (one row per observation) and
reshapes it into a wide summary matrix - rows become one categorical
axis, columns become another, and cell values are an aggregation
(sum, mean, ...) of a numeric column - the pandas equivalent of an
Excel pivot table.
=====================================================================
"""

import pandas as pd
import numpy as np

print("--- Overview ---")
print("groupby = split-apply-combine (per-group aggregation).")
print("merge/join = combine two frames SIDE-BY-SIDE on a shared key.")
print("concat = STACK frames together with no key-matching at all.")
print("pivot_table = reshape long data into a row x column matrix.")


"""
---------------------------------------------------------------------
1. GROUPBY MECHANICS: SPLIT-APPLY-COMBINE  ⭐⭐⭐
---------------------------------------------------------------------
Calling .groupby("col") does NOT immediately compute anything - it
returns a lazy DataFrameGroupBy object that has recorded how to
SPLIT the data. The actual APPLY + COMBINE only happens once you
call an aggregation method (.sum(), .mean(), .agg(), ...) on it.
This mirrors how a lazy query plan works and is a common interview
gotcha: printing a groupby object directly shows a memory address,
not a table.
---------------------------------------------------------------------
"""

print("\n--- GroupBy Mechanics: Split-Apply-Combine ---")

sales = pd.DataFrame({
    "region": ["East", "East", "West", "West", "East", "West", "North", "North", "South"],
    "product": ["Widget", "Gadget", "Widget", "Gadget", "Widget", "Widget", "Gadget", "Widget", "Widget"],
    "amount": [100.0, 250.0, 300.0, 150.0, 200.0, 400.0, 175.0, 225.0, 500.0],
    "date": pd.to_datetime([
        "2026-01-05", "2026-01-06", "2026-01-05", "2026-01-07",
        "2026-01-08", "2026-01-09", "2026-01-05", "2026-01-06", "2026-01-10",
    ]),
})
print(sales)

grouped = sales.groupby("region")            # SPLIT only - lazy, no computation yet
print("\ngroupby() object (lazy, not yet computed):", grouped)
print("groups discovered:", grouped.groups.keys())

# APPLY + COMBINE happens here, when we call an actual aggregation
total_by_region = grouped["amount"].sum()
print("\ntotal 'amount' per region (apply=sum, combine into a Series):")
print(total_by_region)


"""
---------------------------------------------------------------------
2. .agg() WITH MULTIPLE AGGREGATIONS AT ONCE - "TOTAL SALES PER
   REGION" BUSINESS USE CASE  ⭐⭐⭐
---------------------------------------------------------------------
The classic interview prompt "explain groupby + agg with a business
use case (e.g. total sales per region)" wants exactly this: one
groupby, several aggregations computed simultaneously with .agg(),
so a single pass produces a management-ready summary table instead
of three separate group operations.
---------------------------------------------------------------------
"""

print("\n--- groupby + agg: Total Sales Per Region ---")

region_summary = sales.groupby("region")["amount"].agg(["sum", "mean", "count"])
print(region_summary)
print("\nBusiness reading: 'sum' = total revenue per region (the exact")
print("'total sales per region' question), 'mean' = average order size,")
print("'count' = number of orders - three answers from one groupby call.")


"""
---------------------------------------------------------------------
3. GROUPING BY MULTIPLE COLUMNS + .get_group()  ⭐⭐
---------------------------------------------------------------------
Passing a LIST of column names groups by every unique COMBINATION of
those columns - the result has a MultiIndex. .get_group() lets you
pull out one specific group's rows directly, which is handy for
debugging a groupby pipeline ("what does the East/Widget slice
actually look like?").
---------------------------------------------------------------------
"""

print("\n--- Grouping by Multiple Columns + get_group() ---")

multi_grouped = sales.groupby(["region", "product"])["amount"].sum()
print(multi_grouped)
print("\nresult index type:", type(multi_grouped.index).__name__)

# get_group needs a tuple key when grouping by multiple columns
east_widget_rows = sales.groupby(["region", "product"]).get_group(("East", "Widget"))
print("\nget_group(('East', 'Widget')) - raw rows behind that one cell above:")
print(east_widget_rows)


"""
---------------------------------------------------------------------
4. NAMED AGGREGATION FOR CLEAN OUTPUT COLUMN NAMES  ⭐⭐⭐
---------------------------------------------------------------------
.agg(["sum", "mean", "count"]) produces columns literally named
"sum", "mean", "count" - fine for exploration, ugly for a report or
a downstream schema. NAMED AGGREGATION - .agg(new_col=("src_col",
"func")) - lets you choose the output column name directly, and mix
different source columns/functions in one call.
---------------------------------------------------------------------
"""

print("\n--- Named Aggregation for Clean Column Names ---")

named_summary = sales.groupby("region").agg(
    total_sales=("amount", "sum"),
    avg_order_value=("amount", "mean"),
    order_count=("amount", "count"),
    first_order_date=("date", "min"),
)
print(named_summary)
print("\nEvery output column has a business-meaningful name - this is")
print("the idiomatic way to build a report-ready summary table.")


"""
---------------------------------------------------------------------
5. merge(): ALL FOUR JOIN TYPES  ⭐⭐⭐
---------------------------------------------------------------------
merge() combines two DataFrames on shared COLUMN(S) (the `on=` key),
exactly like a SQL JOIN. The `how=` parameter controls which rows
survive when a key exists on only ONE side:
    inner  -> only keys present in BOTH frames
    left   -> all keys from the LEFT frame; unmatched right columns -> NaN
    right  -> all keys from the RIGHT frame; unmatched left columns -> NaN
    outer  -> all keys from EITHER frame; unmatched side(s) -> NaN
---------------------------------------------------------------------
"""

print("\n--- merge(): All Four Join Types ---")

orders = pd.DataFrame({
    "order_id": [1, 2, 3, 4],
    "customer_id": [101, 102, 103, 999],   # 999 has no matching customer
    "amount": [50.0, 75.0, 20.0, 40.0],
})
customers = pd.DataFrame({
    "customer_id": [101, 102, 104],        # 104 has no orders at all
    "customer_name": ["Alice", "Bob", "Dana"],
})
print("orders:\n", orders, sep="")
print("\ncustomers:\n", customers, sep="")

inner = orders.merge(customers, on="customer_id", how="inner")
print("\nhow='inner' (only customer_id in BOTH -> 101, 102; drops 999 and 104):")
print(inner)

left = orders.merge(customers, on="customer_id", how="left")
print("\nhow='left' (all 4 orders kept; customer_id 999 -> customer_name NaN):")
print(left)

right = orders.merge(customers, on="customer_id", how="right")
print("\nhow='right' (all 3 customers kept; Dana(104) -> order columns NaN):")
print(right)

outer = orders.merge(customers, on="customer_id", how="outer")
print("\nhow='outer' (union of keys; BOTH 999 and 104 rows have NaN gaps):")
print(outer.sort_values("customer_id").reset_index(drop=True))


"""
---------------------------------------------------------------------
6. .join(): THE INDEX-BASED SHORTCUT  ⭐⭐
---------------------------------------------------------------------
.join() is a convenience method built on top of merge(), tuned for
the common case where the key you want to combine on is already the
INDEX of one or both frames, rather than a plain column. The core
difference to remember for interviews:
    merge() -> matches on COLUMNS by default (`on=...`)
    join()  -> matches on the INDEX by default (left frame's index
               against the right frame's index, or an `on=` column
               of the left against the right's index)
Reach for .join() when your key is already the index (e.g. after a
groupby, or a lookup table indexed by ID) - it reads cleaner than
forcing a column-based merge with reset_index() calls everywhere.
---------------------------------------------------------------------
"""

print("\n--- .join(): The Index-Based Shortcut ---")

customers_indexed = customers.set_index("customer_id")   # key now lives in the INDEX
orders_indexed = orders.set_index("customer_id")

joined = orders_indexed.join(customers_indexed, how="left")
print("orders_indexed.join(customers_indexed, how='left'):")
print(joined)

print("\nEquivalent using merge() on the index explicitly:")
merged_equiv = orders_indexed.merge(customers_indexed, left_index=True, right_index=True, how="left")
print(merged_equiv)
print("\njoin() is the shorter spelling of exactly this merge() call -")
print("use join() once your key is already the index, merge() when")
print("you're combining on plain columns (the far more common case).")


"""
---------------------------------------------------------------------
7. pd.concat(): STACKING, NOT KEY-MATCHING  ⭐⭐⭐
---------------------------------------------------------------------
concat() does NOT look at key values to decide which rows correspond
to which - it just glues objects together along an axis and ALIGNS
on whatever labels already exist (index for axis=0, columns for
axis=1). This directly answers the syllabus question "difference
between merge(), join(), and concat()":
    merge()  -> combine on COLUMN values, with join-type logic (how=)
    join()   -> combine on the INDEX, same join-type logic under the hood
    concat() -> simply STACK frames (rows or columns); no how= logic
                deciding "match" vs "no match" - only alignment
---------------------------------------------------------------------
"""

print("\n--- pd.concat(): Stacking, Not Key-Matching ---")

more_orders = pd.DataFrame({
    "order_id": [5, 6],
    "customer_id": [101, 105],
    "amount": [60.0, 15.0],
})
stacked_rows = pd.concat([orders, more_orders], axis=0, ignore_index=True)
print("concat(axis=0) - stacks ROWS on top of each other (like SQL UNION ALL):")
print(stacked_rows)

extra_col = pd.DataFrame({"priority": ["low", "high", "high", "low"]}, index=orders.index)
stacked_cols = pd.concat([orders, extra_col], axis=1)
print("\nconcat(axis=1) - stacks COLUMNS side by side, aligned by INDEX POSITION:")
print(stacked_cols)

print("\nThree-way comparison:")
print(" merge()  -> match on COLUMN values, how= controls unmatched rows")
print(" join()   -> match on the INDEX,     how= controls unmatched rows")
print(" concat() -> no matching at all,     just stack + align labels")


"""
---------------------------------------------------------------------
8. pivot_table(): RESHAPING INTO A REGION x PRODUCT MATRIX  ⭐⭐⭐
---------------------------------------------------------------------
pivot_table() turns long-format rows (one row per sale) into a wide
summary grid: one categorical column becomes the ROW index, another
becomes the COLUMN index, and a numeric column is aggregated into
each cell. `aggfunc=` controls HOW cells are aggregated (default is
"mean" - easy to forget!); `fill_value=` replaces cells with no
matching data (a NaN from a region/product combo that never
occurred) with a real value, e.g. 0.
---------------------------------------------------------------------
"""

print("\n--- pivot_table(): Region x Product Sales Matrix ---")

pivot = pd.pivot_table(
    sales,
    values="amount",
    index="region",
    columns="product",
    aggfunc="sum",       # explicit - pivot_table defaults to "mean", which would
                          # silently give the WRONG number for a "total sales" ask
    fill_value=0,         # region/product pairs with no sales -> 0, not NaN
)
print(pivot)
print("\nSouth has no 'Gadget' sales at all - without fill_value=0 that cell")
print("would be NaN, silently breaking any downstream arithmetic (e.g. a row")
print("total). fill_value=0 makes 'no sales recorded' explicit and safe to sum.")


"""
---------------------------------------------------------------------
9. ETL GOTCHA: THE MERGE "FAN-OUT" BUG FROM DUPLICATE KEYS  ⭐⭐⭐
---------------------------------------------------------------------
The most common silent data-corruption bug in real ETL merges: if
the RIGHT frame has DUPLICATE keys, a merge you expected to be
one-row-per-order suddenly MULTIPLIES rows - every left row is
paired with EVERY matching right row (a cartesian product on that
key), inflating row counts and any downstream SUM(). This often
slips through code review because the merge doesn't error - it just
quietly returns more rows than it should.
---------------------------------------------------------------------
"""

print("\n--- ETL Gotcha: The Merge Fan-Out Bug ---")

# A dirty customer dimension table - customer 101 was accidentally
# loaded TWICE (e.g. a re-run of an upstream job without dedup)
dirty_customers = pd.DataFrame({
    "customer_id": [101, 101, 102, 104],
    "customer_name": ["Alice", "Alice", "Bob", "Dana"],
    "segment": ["Retail", "Retail", "Retail", "VIP"],   # duplicate row, not even a data conflict
})

print("orders row count BEFORE merge:", len(orders))
fanned_out = orders.merge(dirty_customers, on="customer_id", how="left")
print("row count AFTER merging against a customer table with a duplicate key:", len(fanned_out))
print(fanned_out)
print("\nOrder 1 (customer 101) appears TWICE - it fanned out because")
print("customer_id 101 matched TWO rows on the right side. A naive")
print("`fanned_out['amount'].sum()` would now DOUBLE-COUNT that order's")
print("revenue - a silent correctness bug, not a crash.")

# DETECTION: the validate= parameter asserts the expected cardinality
# and raises a MergeError the moment it's violated, BEFORE bad data
# propagates downstream.
print("\nDetecting it up front with merge(..., validate='many_to_one'):")
try:
    orders.merge(dirty_customers, on="customer_id", how="left", validate="many_to_one")
except pd.errors.MergeError as e:
    print("MergeError caught (exactly as expected):", e)

# FIX: de-duplicate the dimension table on its key before merging -
# the real fix belongs upstream, but this is the defensive fix here.
clean_customers = dirty_customers.drop_duplicates(subset="customer_id")
print("\ndirty_customers deduplicated on 'customer_id':")
print(clean_customers)

fixed = orders.merge(clean_customers, on="customer_id", how="left", validate="many_to_one")
print("\nrow count AFTER fix (matches original order count - no fan-out):", len(fixed))
print(fixed)
print("\nvalidate='many_to_one' now PASSES silently, proving the right side")
print("has at most one row per key - the merge is safe to trust in a pipeline.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
groupby(col)                    -> lazy split; .sum()/.agg() triggers apply+combine
groupby([c1, c2])                -> groups on every unique (c1, c2) combo -> MultiIndex
.get_group((v1, v2))              -> pull the raw rows for one specific group
.agg(["sum", "mean", "count"])     -> multiple stats at once, generic column names
.agg(total=("amt", "sum"))          -> NAMED aggregation -> clean report column names

merge(df, on=key, how=...)      -> match on COLUMNS (SQL-style join)
    how="inner"                  -> keys in BOTH frames only
    how="left"                    -> all left keys, unmatched right -> NaN
    how="right"                    -> all right keys, unmatched left -> NaN
    how="outer"                     -> union of keys, either side -> NaN
.join(df, how=...)               -> match on the INDEX by default (merge shortcut)
pd.concat([a, b], axis=0)        -> stack ROWS (union), no key-matching at all
pd.concat([a, b], axis=1)         -> stack COLUMNS, aligned by index label/position

pivot_table(values, index,       -> long data -> wide row x column matrix
            columns, aggfunc,        aggfunc default is "mean" - set explicitly!
            fill_value=0)             fill_value replaces missing combos' NaN

Fan-out bug   -> duplicate keys on merge's right side multiply left rows
Detect it     -> merge(..., validate="one_to_one"/"one_to_many"/
                          "many_to_one"/"many_to_many") -> raises MergeError
Fix it        -> drop_duplicates(subset=key) on the offending side first
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - GROUPBY, MERGE, JOIN & PIVOT_TABLE
=====================================================================

1. Explain the split-apply-combine model behind groupby(). At what
   exact point does pandas actually perform the computation - is it
   when you call .groupby(), or something later?

2. Using the `sales` DataFrame in this file, write the groupby + agg
   call that answers "what is the total, average, and count of sales
   per region" in a single pass.

3. What is the difference between .agg(["sum", "mean"]) and named
   aggregation like .agg(total=("amount", "sum"))? Why would you
   prefer the named form in a production reporting pipeline?

4. If you group `sales` by ["region", "product"], what does the
   resulting index look like, and how do you pull out just the rows
   for a single (region, product) combination?

5. Explain the difference between merge(), join(), and concat() in
   Pandas (this is asked almost verbatim in interviews) - specifically,
   what does each one match on, and which of them has no key-matching
   logic at all?

6. Given the `orders` and `customers` DataFrames in this file, walk
   through exactly which rows appear, and which columns get NaN, for
   an inner, left, right, and outer merge on `customer_id`.

7. Why does join() default to matching on the index while merge()
   defaults to matching on columns? When would you specifically reach
   for .join() instead of .merge()?

8. What does pd.concat(axis=1) do if the two DataFrames don't share
   the same index? What would you see in the result?

9. Walk through the "fan-out" bug demonstrated in this file: why did
   merging `orders` against `dirty_customers` produce MORE rows than
   `orders` originally had, and why is this dangerous for a
   downstream .sum()?

10. How does the `validate=` parameter of merge() help catch the
    fan-out bug before it silently corrupts a pipeline? What are the
    four string values it accepts, and what does each assert?

11. Once validate="many_to_one" raises a MergeError, what is the
    correct fix - and why is drop_duplicates() on the dimension table
    usually a workaround rather than the real fix?

12. In pivot_table(), what is the default aggfunc if you don't specify
    one, and why is relying on that default risky when the business
    question is specifically "total sales" rather than "average sales"?

13. What does fill_value=0 do in pivot_table(), and what would the
    matrix look like without it for a region/product combination that
    has zero recorded sales?

14. How would you detect duplicate keys in a dimension table BEFORE
    merging, without waiting for a MergeError to tell you?

15. Describe a real ETL scenario where a merge fan-out bug could pass
    code review and unit tests but still corrupt a production report -
    what would you add to your pipeline to guard against it?
=====================================================================
"""
