"""
=====================================================================
PANDAS SERIES & DATAFRAME BASICS - Complete Notes with Executable
Examples
=====================================================================

Pandas gives you two core data structures, and almost everything else
in the library (groupby, merge, apply, pivot_table...) is built on
top of them.

A SERIES is a 1-DIMENSIONAL LABELED ARRAY: a column of VALUES paired
with an INDEX (the labels). Think of it as a NumPy array that also
remembers a "name" for each position, instead of just a bare integer
offset.

A DATAFRAME is a 2-DIMENSIONAL LABELED TABLE. The mental model that
matters most for interviews: a DataFrame is basically a DICT OF
ALIGNED SERIES - every column is its OWN Series, and all of those
Series SHARE the same row index. That's why `df['amount']` hands you
back a real Series, and why operations that combine columns rely on
the ROW INDEX to line values up correctly.

That "lining up by index" behavior - ALIGNMENT - is the single most
important, most interview-relevant idea in this whole file. It's also
the source of one of the most common real-world pandas bugs: silent
NaNs appearing because two Series/DataFrames didn't share the index
you assumed they did.

This file covers the foundations only: creating Series/DataFrames,
the index, alignment, selection (.loc/.iloc), boolean filtering,
adding/dropping columns and rows, first-look inspection tools, and
the copy-vs-view gotcha. GroupBy/merge, missing-data handling,
apply()/vectorization, and memory optimization are deliberately left
for later files so this one stays focused on fundamentals.
=====================================================================
"""

import warnings
import numpy as np
import pandas as pd

print("--- Overview ---")
print("Series = 1D labeled array (index + values).")
print("DataFrame = 2D labeled table = a dict of Series sharing one index.")
print(f"pandas version: {pd.__version__}")


"""
---------------------------------------------------------------------
1. CREATING A SERIES: FROM A LIST vs FROM A DICT  ⭐⭐⭐
---------------------------------------------------------------------
From a LIST, pandas assigns a default 0-based RangeIndex. From a
DICT, the dict's KEYS become the index automatically - this is a
very common way real pipeline code builds a Series (e.g. one value
per business key).
---------------------------------------------------------------------
"""

print("\n--- Creating a Series ---")

# From a list -> default RangeIndex (0, 1, 2, ...)
amounts_by_position = pd.Series([250.00, 89.99, 120.50, 499.00, 75.25])
print("Series from a list:")
print(amounts_by_position)
print("index:", amounts_by_position.index)
print("values:", amounts_by_position.values, "(a raw NumPy array underneath)")

# From a dict -> keys become the index, values become... the values
amounts_by_order = pd.Series({
    "ORD-1001": 250.00,
    "ORD-1002": 89.99,
    "ORD-1003": 120.50,
})
print("\nSeries from a dict (keys -> index):")
print(amounts_by_order)
print("This is exactly a 1D labeled array: label 'ORD-1002' -> value 89.99")


"""
---------------------------------------------------------------------
2. CREATING A DATAFRAME: FROM A DICT OF LISTS vs A LIST OF DICTS  ⭐⭐⭐
---------------------------------------------------------------------
These are the two shapes you'll build DataFrames from constantly in
real ETL code:
  - a DICT OF LISTS, when you already have data organized by COLUMN
    (e.g. you queried a DB column-by-column, or built arrays in NumPy)
  - a LIST OF DICTS, when you have data organized by ROW (e.g. one
    dict per JSON record from an API, which is extremely common)
Both produce the exact same DataFrame if the data matches up.
---------------------------------------------------------------------
"""

print("\n--- Creating a DataFrame ---")

# Dict of lists: each key becomes a COLUMN name, each list is that
# column's values (all lists must be the same length).
orders_from_dict_of_lists = pd.DataFrame({
    "order_id": ["ORD-1001", "ORD-1002", "ORD-1003", "ORD-1004", "ORD-1005"],
    "customer": ["Acme Corp", "Globex", "Acme Corp", "Initech", "Globex"],
    "product": ["Widget", "Gadget", "Widget", "Gizmo", "Widget"],
    "amount": [250.00, 89.99, 120.50, 499.00, 75.25],
    "quantity": [5, 1, 2, 10, 1],
    "region": ["West", "East", "West", "North", "East"],
})
print("DataFrame from a dict of lists:")
print(orders_from_dict_of_lists)

# List of dicts: each dict becomes a ROW; pandas unions the keys into
# columns. This is exactly what you get from `json.load()` on a list
# of API records.
orders_records = [
    {"order_id": "ORD-1001", "customer": "Acme Corp", "product": "Widget", "amount": 250.00, "quantity": 5, "region": "West"},
    {"order_id": "ORD-1002", "customer": "Globex",    "product": "Gadget", "amount": 89.99,  "quantity": 1, "region": "East"},
    {"order_id": "ORD-1003", "customer": "Acme Corp", "product": "Widget", "amount": 120.50, "quantity": 2, "region": "West"},
    {"order_id": "ORD-1004", "customer": "Initech",   "product": "Gizmo",  "amount": 499.00, "quantity": 10, "region": "North"},
    {"order_id": "ORD-1005", "customer": "Globex",    "product": "Widget", "amount": 75.25,  "quantity": 1, "region": "East"},
]
orders = pd.DataFrame(orders_records)
print("\nDataFrame from a list of dicts (our running 'orders' dataset):")
print(orders)

print("\nProof that a DataFrame is a dict-of-aligned-Series:")
print("type(orders['amount']):", type(orders["amount"]))
print("orders['amount'].index is orders.index:", orders["amount"].index.equals(orders.index))


"""
---------------------------------------------------------------------
3. THE INDEX: DEFAULT RangeIndex vs A CUSTOM INDEX  ⭐⭐⭐
---------------------------------------------------------------------
Every Series/DataFrame has an index, whether you set one or not. Left
alone, pandas gives you an auto-incrementing RangeIndex (0, 1, 2...),
which is fine for "just a list of rows" but doesn't reflect any real
business meaning. In real pipelines you very often want to promote a
natural key - here, order_id - to be the actual index, because it
makes lookups by that key an O(1)-ish `.loc[]` call instead of a
boolean-mask scan.
---------------------------------------------------------------------
"""

print("\n--- The Index: Default vs Custom ---")

print("default index on 'orders':", orders.index)

# set_index() returns a NEW DataFrame by default (does not mutate
# 'orders' in place) unless you pass inplace=True or reassign.
orders_by_id = orders.set_index("order_id")
print("\nafter set_index('order_id'):")
print(orders_by_id)
print("new index:", orders_by_id.index)
print("original 'orders' is untouched:", "order_id" in orders.columns)

print("\nlooking up a row by its BUSINESS KEY is now direct:")
print(orders_by_id.loc["ORD-1003"])


"""
---------------------------------------------------------------------
4. INDEX ALIGNMENT: THE SILENT NaN GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
Arithmetic between two Series does NOT just line values up by
POSITION - it lines them up by INDEX LABEL. If the two Series don't
share the exact same set of labels, pandas still "succeeds" - it
just fills in NaN anywhere a label is missing from one side. This is
a very common real-world bug: two datasets that LOOK compatible (same
length!) silently produce garbage after a join-like operation because
their indexes don't actually match.
---------------------------------------------------------------------
"""

print("\n--- Index Alignment Gotcha ---")

week1_sales = pd.Series({"Acme Corp": 500, "Globex": 300, "Initech": 150})
week2_sales = pd.Series({"Globex": 400, "Initech": 200, "Umbrella Inc": 90})

print("week1_sales:\n", week1_sales, sep="")
print("\nweek2_sales:\n", week2_sales, sep="")

total_sales = week1_sales + week2_sales
print("\nweek1_sales + week2_sales (naive add):")
print(total_sales)
print("\n'Acme Corp' -> NaN (only in week1) and 'Umbrella Inc' -> NaN (only")
print("in week2) - pandas aligned by LABEL, and any label missing from one")
print("side produces NaN, even though BOTH inputs had exactly 3 entries.")

# FIX: use the .add() method with fill_value, which treats a missing
# label as the fill value instead of NaN, for arithmetic purposes.
total_sales_fixed = week1_sales.add(week2_sales, fill_value=0)
print("\nfixed with .add(week2_sales, fill_value=0):")
print(total_sales_fixed)


"""
---------------------------------------------------------------------
5. SELECTING DATA: .loc[] (LABEL-BASED) vs .iloc[] (POSITION-BASED)  ⭐⭐⭐
---------------------------------------------------------------------
`.loc[]` selects by INDEX LABEL (and column NAME). `.iloc[]` selects
by INTEGER POSITION, completely ignoring what the labels actually
are - exactly like list indexing. Mixing them up is one of the most
common pandas mistakes, and it's a favorite "gotcha" interview
question because the two can look interchangeable on a default
RangeIndex but diverge completely once you set a custom index.
---------------------------------------------------------------------
"""

print("\n--- .loc[] vs .iloc[] ---")

print("orders_by_id (indexed by order_id):")
print(orders_by_id)

print("\n.loc['ORD-1002']  (by LABEL):")
print(orders_by_id.loc["ORD-1002"])

print("\n.iloc[1]  (by POSITION - the 2nd row, regardless of its label):")
print(orders_by_id.iloc[1])

print("\nside by side on a single column, row 3:")
print(" .loc['ORD-1004', 'amount'] ->", orders_by_id.loc["ORD-1004", "amount"])
print(" .iloc[3, orders_by_id.columns.get_loc('amount')] ->",
      orders_by_id.iloc[3, orders_by_id.columns.get_loc("amount")])

# GOTCHA: using .loc with a plain integer, once the index is no
# longer a RangeIndex, looks for that INTEGER as a LABEL - it does
# NOT fall back to position - and raises KeyError if no such label
# exists.
try:
    orders_by_id.loc[0]
except KeyError as e:
    print("\n.loc[0] on a string-indexed DataFrame -> KeyError:", e)
    print("(there IS no label 0 anymore - the index is order_id strings now)")

# GOTCHA: .iloc is purely positional, so an out-of-range position
# raises IndexError, exactly like a Python list.
try:
    orders_by_id.iloc[99]
except IndexError as e:
    print("\n.iloc[99] (only 5 rows exist) -> IndexError:", e)

print("\nRule of thumb: '.loc' for LABELS, '.iloc' for POSITIONS - never")
print("assume they agree once a custom index is in play.")


"""
---------------------------------------------------------------------
6. BOOLEAN FILTERING & COMBINING CONDITIONS WITH & / |  ⭐⭐⭐
---------------------------------------------------------------------
`df[condition]` where `condition` is a boolean Series is the standard
way to filter rows - this is pandas' equivalent of a SQL WHERE clause.
To combine multiple conditions you MUST use the bitwise operators
`&` and `|` (with each condition PARENTHESIZED), NOT Python's `and`/
`or` - those are for single booleans, not element-wise Series, and
Python has no way to overload their short-circuiting behavior.
---------------------------------------------------------------------
"""

print("\n--- Boolean Filtering ---")

big_orders = orders[orders["amount"] > 100]
print("orders[orders['amount'] > 100]:")
print(big_orders)

# Combine two conditions - note the REQUIRED parentheses: & binds
# tighter than the comparison operators, so `a > 1 & b < 2` would
# parse wrong without them.
west_big_orders = orders[(orders["amount"] > 100) & (orders["region"] == "West")]
print("\namount > 100 AND region == 'West':")
print(west_big_orders)

east_or_north = orders[(orders["region"] == "East") | (orders["region"] == "North")]
print("\nregion == 'East' OR region == 'North':")
print(east_or_north)

# GOTCHA: `and`/`or` try to coerce the WHOLE Series to a single bool,
# which pandas explicitly refuses, because "is this Series true?" is
# ambiguous when it has more than one element.
try:
    if (orders["amount"] > 100) and (orders["region"] == "West"):
        pass
except ValueError as e:
    print("\nusing 'and' between two boolean Series -> ValueError:", e)
    print("fix: use '&' (and '|' for or), with each side in parentheses.")


"""
---------------------------------------------------------------------
7. ADDING/DROPPING COLUMNS AND ROWS  ⭐⭐
---------------------------------------------------------------------
Direct assignment (`df['new_col'] = ...`) mutates in place and is the
most common way to add a column. `.assign()` returns a NEW DataFrame
instead, which is preferable inside a CHAIN of transformations (e.g.
`orders.assign(...).query(...).sort_values(...)`) because it doesn't
mutate anything and reads top-to-bottom like a pipeline. `.drop()`
removes columns (`axis=1`/`columns=`) or rows (`axis=0`/`index=`) and
also returns a new object unless `inplace=True`.
---------------------------------------------------------------------
"""

print("\n--- Adding/Dropping Columns and Rows ---")

orders_priced = orders.copy()
# Direct assignment: mutates orders_priced in place.
orders_priced["unit_price"] = orders_priced["amount"] / orders_priced["quantity"]
print("after direct assignment of 'unit_price':")
print(orders_priced)

# .assign(): returns a NEW DataFrame, doesn't touch orders_priced.
# Great for chaining - each keyword becomes a new (or overwritten)
# column, and you can reference columns just created earlier in the
# SAME .assign() call via a lambda.
orders_chained = orders.assign(
    unit_price=lambda d: d["amount"] / d["quantity"],
    is_bulk=lambda d: d["quantity"] >= 5,
)
print("\nvia .assign() (chainable, non-mutating):")
print(orders_chained)

# Dropping a column vs dropping a row.
without_region = orders_chained.drop(columns=["region"])
print("\nafter .drop(columns=['region']):")
print(without_region.head(2))

without_first_row = orders_chained.drop(index=0)
print("\nafter .drop(index=0) (drops the row LABELED 0):")
print(without_first_row)


"""
---------------------------------------------------------------------
8. FIRST-LOOK INSPECTION: .shape, .dtypes, .info(), .describe(),
   .head()/.tail()  ⭐⭐⭐
---------------------------------------------------------------------
DATA ENGINEERING USE CASE: this is the very first thing you run
against any new DataFrame you're handed - before writing a single
transformation - to answer "how big is this, what types am I dealing
with, are there obvious nulls/outliers, what does a sample row look
like?" Skipping this step is how silent type mismatches and null
columns make it all the way to production.
---------------------------------------------------------------------
"""

print("\n--- First-Look Inspection Toolkit ---")

print("orders.shape:", orders.shape, "(rows, columns)")
print("\norders.dtypes:")
print(orders.dtypes)

print("\norders.head(2):")
print(orders.head(2))
print("\norders.tail(2):")
print(orders.tail(2))

print("\norders.info():")
orders.info()

print("\norders.describe() (numeric columns only by default):")
print(orders.describe())

print("\norders.describe(include='str') (categorical/text columns):")
# Pandas 3 gives text columns a real 'str' dtype instead of the old
# generic 'object' dtype - pass 'str' explicitly rather than 'object'
# to select them (avoids a Pandas4Warning about the old behavior).
print(orders.describe(include="str"))


"""
---------------------------------------------------------------------
9. COPY vs VIEW: CHAINED-ASSIGNMENT GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
This trips up almost everyone eventually: `df[condition]['col'] = x`
chains TWO separate `__getitem__`/`__setitem__` operations. The first
`df[condition]` may hand back either a VIEW or a COPY of the original
data - pandas itself doesn't guarantee which - so the second
assignment can silently update a throwaway temporary object instead
of `df`, and your real DataFrame is left unchanged.

Older pandas (pre-3.0) surfaced this as a `SettingWithCopyWarning`
and sometimes let the mutation happen anyway (unreliably). Pandas 3.0
turns on COPY-ON-WRITE (CoW) by default, which removes that ambiguity
entirely: `df[condition]` is now ALWAYS a copy, so the chained
assignment is now guaranteed to be a no-op on the original - and
pandas raises it loudly as `pandas.errors.ChainedAssignmentError`
instead of the old warning class (which no longer exists in 3.0). The
lesson and the fix are the same as always: use a SINGLE `.loc[]` call
that does the row-and-column selection AND the assignment together.
---------------------------------------------------------------------
"""

print("\n--- Copy vs View: Chained Assignment Gotcha ---")

orders_flagged = orders.copy()

# BUGGY: two chained indexing operations - the assignment lands on
# an intermediate object, not on orders_flagged itself.
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    try:
        orders_flagged[orders_flagged["amount"] > 100]["flagged"] = True
    except Exception as e:
        print("chained assignment also raised:", type(e).__name__, e)
    for w in caught:
        print(f"caught warning ({w.category.__name__}):")
        print(" ", str(w.message).splitlines()[0])

print("\ndid the chained assignment actually change orders_flagged? 'flagged' in columns:",
      "flagged" in orders_flagged.columns)

# FIXED: a single .loc[] call - one row selector, one column name,
# one assignment - so pandas knows unambiguously what to mutate.
orders_flagged.loc[orders_flagged["amount"] > 100, "flagged"] = True
orders_flagged["flagged"] = orders_flagged["flagged"].fillna(False)
print("\nfixed with a single .loc[row_mask, 'col'] = value:")
print(orders_flagged)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Series   -> 1D labeled array:  index + values
DataFrame -> 2D labeled table: a dict of Series sharing one index

Create a Series:
    pd.Series([...])            -> default RangeIndex
    pd.Series({...})            -> dict keys become the index

Create a DataFrame:
    pd.DataFrame({col: [...]})  -> dict of lists (column-oriented)
    pd.DataFrame([{...}, ...])  -> list of dicts (row-oriented, JSON-like)

Index:
    df.index                    -> current index (RangeIndex by default)
    df.set_index('col')         -> promote a column to the index
                                    (returns a NEW df unless inplace=True)

Alignment gotcha:
    series_a + series_b         -> aligned by LABEL, not position;
                                    mismatched labels -> NaN
    series_a.add(series_b, fill_value=0)  -> fixed version

Selection:
    df.loc[label]                -> by LABEL (rows and/or columns)
    df.iloc[position]            -> by INTEGER POSITION
    df.loc[bad_int]  on custom index -> KeyError
    df.iloc[out_of_range]        -> IndexError

Boolean filtering:
    df[df['col'] > x]            -> SQL-WHERE-style filter
    (cond1) & (cond2)            -> AND   (parens required)
    (cond1) | (cond2)            -> OR    (parens required)
    cond1 and cond2               -> ValueError: ambiguous truth value

Add/drop:
    df['new'] = ...               -> mutates in place
    df.assign(new=lambda d: ...)  -> returns a NEW df, chainable
    df.drop(columns=[...])        -> drop column(s)
    df.drop(index=[...])          -> drop row(s)

First-look inspection:
    df.shape -> (rows, cols)      df.dtypes -> per-column dtype
    df.info()                     df.describe()
    df.head(n) / df.tail(n)

Copy vs view:
    df[mask]['col'] = x           -> chained assignment; on a copy
                                      (pandas 3.0 CoW -> raises
                                      ChainedAssignmentError; old
                                      pandas -> SettingWithCopyWarning)
    df.loc[mask, 'col'] = x        -> the fix: one indexing operation
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PANDAS SERIES & DATAFRAME BASICS
=====================================================================

1. What IS a pandas Series, structurally? What IS a DataFrame, in
   terms of Series?

2. Given a dict like {"Acme Corp": 500, "Globex": 300}, what becomes
   the index and what becomes the values if you pass it to
   `pd.Series(...)`?

3. When would you build a DataFrame from a "dict of lists" versus a
   "list of dicts"? Which shape does a typical JSON API response
   naturally map to?

4. What index does pandas give a DataFrame by default if you don't
   set one, and what's the tradeoff of promoting a real column (like
   `order_id`) to be the index via `set_index()`?

5. Explain why `week1_sales + week2_sales` can produce `NaN` values
   even when both Series have exactly the same number of entries.
   What operation and argument would you use to treat a missing
   label as 0 instead of producing NaN?

6. What is the core difference between `.loc[]` and `.iloc[]`? Give
   an example where they would return the SAME row and one where
   they would NOT.

7. If `orders_by_id` is indexed by a string `order_id`, why does
   `orders_by_id.loc[0]` raise a `KeyError` instead of returning the
   first row?

8. Why does `df.iloc[99]` raise `IndexError` while `df.loc['some_label']`
   for a missing label raises `KeyError` instead? What's the
   conceptual difference being enforced?

9. Why does `df[(df['amount'] > 100) and (df['region'] == 'West')]`
   raise a `ValueError`, and how do you fix it?

10. Why are parentheses required around each condition when combining
    them with `&` or `|` (e.g. `(df['a'] > 1) & (df['b'] < 2)`)?

11. What's the difference between adding a column via direct
    assignment (`df['x'] = ...`) and via `.assign(x=...)`? When would
    you prefer `.assign()`?

12. Explain what's wrong with `df[df['amount'] > 100]['flagged'] = True`
    and how you'd rewrite it correctly using `.loc[]`.

13. In pandas 3.0+, what replaced `SettingWithCopyWarning`, and why
    does Copy-on-Write make that chained-assignment mistake even more
    clearly a no-op than it was before?

14. If you're handed an unfamiliar DataFrame, what's the sequence of
    inspection calls (shape, dtypes, info, describe, head/tail) you'd
    run first, and what is each one telling you that the others
    don't?

15. What does `df.describe(include='str')` show you that the
    default `df.describe()` does not, and why does pandas 3 want
    `'str'` there instead of the old `'object'`?
=====================================================================
"""
