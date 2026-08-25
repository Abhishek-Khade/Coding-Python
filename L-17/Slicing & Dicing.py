"""
=====================================================================
SLICING AND DICING IN PYTHON DATA STRUCTURES
=====================================================================

"Slicing" means extracting a CONTIGUOUS sub-portion of a sequence
using position-based ranges (start:stop:step).

"Dicing" (informally) means extracting NON-CONTIGUOUS or CONDITION-
BASED subsets - filtering by value, boolean masks, or selecting
scattered indices - not just a simple positional range.

Together, "slicing and dicing" is the everyday Data Engineering
skill of carving exactly the rows/columns/elements you need out of
a larger structure - whether it's a plain list, a NumPy array, or a
Pandas DataFrame.

TOPICS COVERED:
    1. Basic slice syntax recap: start:stop:step
    2. The slice() object - reusable, named slices
    3. Negative indices & negative steps
    4. Slice assignment & slice deletion (mutating via slices)
    5. Slicing pitfalls (out-of-range is safe, off-by-one confusion)
    6. Dicing: boolean-mask / condition-based filtering (list, NumPy)
    7. Multi-dimensional slicing (NumPy arrays, nested lists)
    8. Pandas .loc[] vs .iloc[] - label vs position-based "dicing"
    9. Slicing iterators/generators with itertools.islice
    10. Dictionary "slicing" (there's no native syntax - patterns
        that simulate it)
=====================================================================
"""

import sys

print("--- Overview ---")
print("Slicing = contiguous range extraction.")
print("Dicing   = condition-based / non-contiguous subset extraction.")


"""
---------------------------------------------------------------------
1. BASIC SLICE SYNTAX RECAP: start:stop:step  ⭐⭐⭐
---------------------------------------------------------------------
lst[start:stop:step]
    start -> inclusive, default 0
    stop  -> EXCLUSIVE, default len(lst)
    step  -> default 1; negative step reverses direction

Works identically on list, tuple, str, range - any standard
sequence type.
---------------------------------------------------------------------
"""

print("\n--- Basic Slice Syntax ---")

data = [10, 20, 30, 40, 50, 60, 70, 80]

print("data[2:5]:", data[2:5])         # [30, 40, 50]
print("data[:3]:", data[:3])           # [10, 20, 30]
print("data[5:]:", data[5:])           # [60, 70, 80]
print("data[:]:", data[:])             # full shallow copy
print("data[::2]:", data[::2])         # every 2nd element
print("data[1::2]:", data[1::2])       # every 2nd, starting at index 1


"""
---------------------------------------------------------------------
2. THE slice() OBJECT: REUSABLE, NAMED SLICES  ⭐⭐
---------------------------------------------------------------------
`a:b:c` inside [] is actually SYNTACTIC SUGAR for a slice() object.
You can build one explicitly and reuse it across multiple sequences -
handy when the same "window" needs to be applied repeatedly (e.g.,
extracting the same date-range columns from many rows).
---------------------------------------------------------------------
"""

print("\n--- The slice() Object ---")

first_half = slice(0, 4)          # equivalent to [0:4]
last_half = slice(4, None)        # equivalent to [4:]

print("data[first_half]:", data[first_half])
print("data[last_half]:", data[last_half])

# Reuse the SAME slice object across different sequences
letters = list("abcdefgh")
print("letters[first_half]:", letters[first_half])

# slice() also exposes its own start/stop/step for introspection
print("\nfirst_half.start:", first_half.start,
      "| stop:", first_half.stop, "| step:", first_half.step)


"""
---------------------------------------------------------------------
3. NEGATIVE INDICES & NEGATIVE STEPS  ⭐⭐⭐
---------------------------------------------------------------------
Negative indices count from the END. A negative STEP reverses the
direction of traversal entirely - this is how `[::-1]` reverses a
sequence in one line.
---------------------------------------------------------------------
"""

print("\n--- Negative Indices & Steps ---")

print("data[-3:]:", data[-3:])            # last 3 elements
print("data[:-3]:", data[:-3])            # all but the last 3
print("data[-5:-2]:", data[-5:-2])        # slice using two negative bounds
print("data[::-1]:", data[::-1])          # fully reversed
print("data[::-2]:", data[::-2])          # every 2nd element, reversed
print("data[6:2:-1]:", data[6:2:-1])      # reversed sub-range


"""
---------------------------------------------------------------------
4. SLICE ASSIGNMENT & SLICE DELETION  ⭐⭐⭐
---------------------------------------------------------------------
For MUTABLE sequences (lists), a slice can be used on the LEFT side
of an assignment to REPLACE a range of elements - even with a
DIFFERENT number of replacement elements, so the list can grow or
shrink. `del` also works on slices.
---------------------------------------------------------------------
"""

print("\n--- Slice Assignment & Deletion ---")

nums = [1, 2, 3, 4, 5, 6, 7, 8]

nums[2:5] = [99, 98]              # replace 3 elements with 2 -> list shrinks
print("after nums[2:5] = [99, 98]:", nums)

nums[1:1] = [100, 200]             # inserting via an EMPTY slice
print("after inserting via empty slice nums[1:1]:", nums)

del nums[0:2]                       # delete a range of elements
print("after del nums[0:2]:", nums)

# Extended slice assignment (with a step) requires MATCHING lengths
step_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
step_list[::2] = [-1, -1, -1, -1, -1]     # replaces every even-index item
print("after step_list[::2] = [...]:", step_list)

try:
    step_list[::2] = [0, 0]        # wrong length for a stepped slice -> error
except ValueError as e:
    print("Error assigning wrong-length values to a stepped slice:", e)


"""
---------------------------------------------------------------------
5. SLICING PITFALLS  ⭐⭐⭐
---------------------------------------------------------------------
- Out-of-range slice bounds do NOT raise an error - they're
  silently clamped to the sequence's actual length.
- This is DIFFERENT from direct indexing, where an out-of-range
  index DOES raise IndexError.
---------------------------------------------------------------------
"""

print("\n--- Slicing Pitfalls ---")

small = [1, 2, 3]

print("small[0:100] (stop way beyond length):", small[0:100])   # no error!
print("small[100:200] (both bounds beyond length):", small[100:200])  # empty list, no error

try:
    small[100]              # DIRECT indexing DOES raise an error
except IndexError as e:
    print("Error with direct out-of-range index:", e)

print("\n*** Slicing is forgiving; direct indexing is strict. ***")


"""
---------------------------------------------------------------------
6. DICING: BOOLEAN-MASK / CONDITION-BASED FILTERING  ⭐⭐⭐
---------------------------------------------------------------------
Unlike slicing (contiguous, position-based), "dicing" extracts
elements based on a CONDITION - which may select non-contiguous
elements from anywhere in the structure.

Plain Python: use a list comprehension with a filter condition.
NumPy: use BOOLEAN MASKING - indexing an array with a boolean array
of the same shape, selecting only the True positions. This is
vectorized and far faster than a Python-level loop.
---------------------------------------------------------------------
"""

print("\n--- Dicing: Condition-Based Filtering ---")

# Plain Python "dicing" with a list comprehension
prices = [12.5, 45.0, 8.75, 99.99, 3.20, 60.0]
expensive = [p for p in prices if p > 20]
print("plain-Python dicing (prices > 20):", expensive)

# NumPy boolean masking - the vectorized equivalent, MUCH faster on
# large arrays and the standard approach in data engineering code
try:
    import numpy as np

    arr = np.array(prices)
    mask = arr > 20                      # a boolean array, same shape as arr
    print("\nboolean mask:", mask)
    print("arr[mask] (dicing with the mask):", arr[mask])

    # Combining multiple conditions requires & / | (NOT and/or) and
    # each condition must be parenthesized
    combined_mask = (arr > 10) & (arr < 100)
    print("combined condition (10 < price < 100):", arr[combined_mask])
except ImportError:
    print("(numpy not installed - conceptually: arr[arr > 20] selects")
    print(" only the elements where the condition is True)")


"""
---------------------------------------------------------------------
7. MULTI-DIMENSIONAL SLICING  ⭐⭐⭐
---------------------------------------------------------------------
Plain nested Python lists require CHAINED indexing/slicing (slice
one dimension, then the next) - there's no single-expression 2D
slice for a list of lists. NumPy, by contrast, supports TRUE
multi-dimensional slicing with a comma-separated syntax:
    arr[row_slice, col_slice]
---------------------------------------------------------------------
"""

print("\n--- Multi-Dimensional Slicing ---")

matrix = [
    [1, 2, 3, 4],
    [5, 6, 7, 8],
    [9, 10, 11, 12],
]

# Nested list: must slice ROWS first, then slice/index each row separately
first_two_rows = matrix[0:2]
print("nested list - first two rows:", first_two_rows)

first_two_rows_first_two_cols = [row[0:2] for row in matrix[0:2]]
print("nested list - first two rows, first two cols (needs a comprehension):",
      first_two_rows_first_two_cols)

try:
    import numpy as np

    np_matrix = np.array(matrix)
    print("\nnumpy - true 2D slicing arr[0:2, 0:2]:")
    print(np_matrix[0:2, 0:2])          # single expression, both dimensions

    print("\nnumpy - all rows, only column 1: arr[:, 1]")
    print(np_matrix[:, 1])

    print("\nnumpy - reverse ROW order: arr[::-1, :]")
    print(np_matrix[::-1, :])
except ImportError:
    print("(numpy not installed - it enables arr[rows, cols] in one step)")


"""
---------------------------------------------------------------------
8. PANDAS .loc[] vs .iloc[] - LABEL vs POSITION-BASED "DICING" ⭐⭐⭐
---------------------------------------------------------------------
For Data Engineers, this is the single most-used "slicing and dicing"
tool in daily work.

    .iloc[]  -> POSITION-based (integer index), like list slicing -
                stop is EXCLUSIVE, just like Python slices
    .loc[]   -> LABEL-based (index name / column name), and its
                slice stop is INCLUSIVE (a common source of
                confusion coming from plain Python slicing!)

Boolean masking ALSO works directly with Pandas for row filtering -
the "dicing" equivalent of NumPy's boolean indexing.
---------------------------------------------------------------------
"""

print("\n--- Pandas .loc[] vs .iloc[] ---")

try:
    import pandas as pd

    df = pd.DataFrame({
        "order_id": ["ORD1", "ORD2", "ORD3", "ORD4", "ORD5"],
        "amount": [100, 250, 75, 300, 150],
        "status": ["shipped", "pending", "shipped", "shipped", "pending"],
    }, index=["a", "b", "c", "d", "e"])

    print("Full DataFrame:\n", df)

    print("\n.iloc[0:2] (position-based, stop EXCLUSIVE):")
    print(df.iloc[0:2])

    print("\n.loc['a':'c'] (label-based, stop INCLUSIVE!):")
    print(df.loc["a":"c"])       # includes 'c' - different from position slicing!

    print("\n.loc[:, 'amount'] (all rows, one column by label):")
    print(df.loc[:, "amount"])

    # Boolean-mask "dicing" - filter rows by a condition, the
    # single most common Pandas operation in ETL/data cleaning
    print("\nboolean dicing: df[df['amount'] > 100]")
    print(df[df["amount"] > 100])

    print("\ncombined condition dicing: amount > 100 AND status == 'shipped'")
    print(df[(df["amount"] > 100) & (df["status"] == "shipped")])
except ImportError:
    print("(pandas not installed - .iloc is position-based/exclusive-stop,")
    print(" .loc is label-based/inclusive-stop, both support boolean masks)")


"""
---------------------------------------------------------------------
9. SLICING ITERATORS/GENERATORS: itertools.islice  ⭐⭐
---------------------------------------------------------------------
Plain slice syntax (`gen[2:5]`) does NOT work on generators or other
iterators - they have no defined length or random access. Use
itertools.islice() instead, which consumes the iterator lazily,
without loading everything into memory - critical for large/streamed
data.
---------------------------------------------------------------------
"""

print("\n--- Slicing Generators with itertools.islice ---")

from itertools import islice

def number_stream():
    """A generator simulating an infinite/streamed data source."""
    n = 0
    while True:
        yield n
        n += 1

gen = number_stream()

try:
    gen[2:5]              # generators do NOT support slice syntax directly
except TypeError as e:
    print("Error slicing a generator directly:", e)

first_five = list(islice(number_stream(), 5))          # like gen[:5]
print("islice(gen, 5) (first 5 items):", first_five)

middle_slice = list(islice(number_stream(), 3, 8))       # like gen[3:8]
print("islice(gen, 3, 8):", middle_slice)

stepped_slice = list(islice(number_stream(), 0, 20, 4))   # like gen[0:20:4]
print("islice(gen, 0, 20, 4):", stepped_slice)


"""
---------------------------------------------------------------------
10. DICTIONARY "SLICING": NO NATIVE SYNTAX, BUT COMMON PATTERNS ⭐⭐
---------------------------------------------------------------------
Dicts have NO built-in slicing (`d[1:3]` raises TypeError) since
they're accessed by key, not position. Common patterns simulate
"slicing" a dict by KEYS, by VALUE CONDITION, or by POSITION
(relying on 3.7+ insertion order).
---------------------------------------------------------------------
"""

print("\n--- Dictionary 'Slicing' Patterns ---")

config = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

try:
    config[1:3]           # dicts have no slice support - Python builds
                           # a slice(1, 3, None) object and tries to use
                           # it as a DICT KEY, which doesn't exist
except KeyError as e:
    print("Error slicing a dict directly (raises KeyError, not TypeError!):", e)

# Pattern 1: "slice" by an explicit list of keys
wanted_keys = ["a", "c", "e"]
subset_by_keys = {k: config[k] for k in wanted_keys if k in config}
print("subset by explicit keys:", subset_by_keys)

# Pattern 2: "dice" by a VALUE condition
subset_by_value = {k: v for k, v in config.items() if v > 2}
print("subset by value condition (v > 2):", subset_by_value)

# Pattern 3: "slice" the first N items by relying on insertion order
first_n_items = dict(islice(config.items(), 3))
print("first 3 items (position-based, via islice):", first_n_items)


"""
=====================================================================
QUICK REFERENCE: SLICING vs DICING BY STRUCTURE
=====================================================================
Structure         | Slicing (positional range)  | Dicing (condition-based)
------------------|------------------------------|----------------------------
list/tuple/str     | lst[a:b:c]                   | [x for x in lst if cond]
NumPy ndarray       | arr[a:b:c]                    | arr[arr > threshold]
Pandas DataFrame     | df.iloc[a:b]                  | df[df['col'] > threshold]
                    | df.loc[label_a:label_b]         | df.loc[mask]
Generator/Iterator   | itertools.islice(gen, a, b)     | filter(cond, gen)
Dict                 | NOT supported natively (use     | {k:v for k,v in
                    | islice on .items() by position) |  d.items() if cond}
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - SLICING AND DICING
=====================================================================

1. What's the difference between "slicing" and boolean-mask
   "dicing," conceptually? Give an example of each on the same list.

2. Why does `small_list[0:1000]` NOT raise an error, while
   `small_list[1000]` DOES raise IndexError? Explain the difference
   in how Python handles out-of-range slice bounds vs indices.

3. What is a `slice()` object, and how does `lst[a:b:c]` relate to
   it internally?

4. How would you reverse a list using slicing? What does
   `lst[::-1]` actually do step by step?

5. Can you assign a DIFFERENT number of elements than the original
   slice length when doing slice assignment on a list (e.g.
   `lst[1:3] = [10, 20, 30, 40]`)? What happens to the list's length?

6. Why do you need `&` and `|` (not `and`/`or`) when combining
   multiple boolean conditions for NumPy/Pandas boolean masking, and
   why must each condition be wrapped in parentheses?

7. What's the critical difference between `.iloc[]` and `.loc[]`
   slicing in Pandas regarding whether the STOP boundary is
   inclusive or exclusive?

8. Why can't you directly slice a generator (e.g., `my_gen[2:5]`)?
   What tool would you use instead, and why is it more appropriate
   for large or infinite data streams?

9. How would you select every OTHER row of a NumPy 2D array, and
   every OTHER column, in a single expression?

10. Why is NumPy's boolean-mask filtering (`arr[arr > threshold]`)
    generally much faster than an equivalent Python list
    comprehension (`[x for x in lst if x > threshold]`) on large
    datasets?

11. How would you extract the "first N items" from a dictionary,
    given that dicts have no native slicing syntax? What assumption
    does this rely on regarding dict ordering?

12. What happens if you try to do `matrix[0:2, 0:2]` on a plain
    nested Python list (list of lists) instead of a NumPy array?
    Why does this fail, and how would you achieve the same result
    using nested list comprehensions?

13. In a data engineering ETL script, you need to pull only the
    rows from a large DataFrame where `status == 'shipped'` AND
    `amount > 100`. Write the Pandas boolean-dicing expression for
    this, and explain why this approach scales better than
    iterating row-by-row with a Python loop.

14. What does `itertools.islice(gen, 3, 8, 2)` do, and how does its
    behavior map onto the standard slice syntax `x[3:8:2]`?
=====================================================================
"""