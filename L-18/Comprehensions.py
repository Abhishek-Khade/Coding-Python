"""
=====================================================================
PYTHON COMPREHENSIONS - Complete Notes with Executable Examples
=====================================================================

A comprehension is a compact, expressive syntax for building a new
collection by transforming and/or filtering an existing iterable -
in a SINGLE line, without an explicit for-loop and .append()/.add()/
assignment calls.

Python has FOUR comprehension forms:
    list comprehension       -> [expr for item in iterable if cond]
    set comprehension        -> {expr for item in iterable if cond}
    dict comprehension        -> {key_expr: val_expr for item in ... if cond}
    generator expression       -> (expr for item in iterable if cond)

All four share the SAME underlying syntax pattern - only the
brackets/braces (and therefore the resulting TYPE) differ.
=====================================================================
"""

import sys
import time

print("--- Overview ---")
print("Comprehensions build [list], {set}, {dict: }, or (generator)")
print("from an iterable, in one compact expression.")


"""
---------------------------------------------------------------------
1. LIST COMPREHENSION - THE BASELINE FORM  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  [expression for item in iterable]
         [expression for item in iterable if condition]

Equivalent to a for-loop that builds a list with .append().
---------------------------------------------------------------------
"""

print("\n--- List Comprehension ---")

# Traditional loop
squares_loop = []
for x in range(1, 6):
    squares_loop.append(x ** 2)
print("loop version:", squares_loop)

# Equivalent comprehension
squares_comp = [x ** 2 for x in range(1, 6)]
print("comprehension version:", squares_comp)

# With a filter condition
evens_only = [x for x in range(1, 11) if x % 2 == 0]
print("filtered (evens only):", evens_only)

# Transform AND filter together
even_squares = [x ** 2 for x in range(1, 11) if x % 2 == 0]
print("transformed + filtered:", even_squares)


"""
---------------------------------------------------------------------
2. CONDITIONAL EXPRESSION INSIDE A COMPREHENSION (TERNARY)  ⭐⭐
---------------------------------------------------------------------
Don't confuse the FILTERING `if` (at the end, decides whether to
INCLUDE an item) with the TERNARY `if/else` (at the start, decides
WHAT VALUE to produce for every item - nothing is excluded).
---------------------------------------------------------------------
"""

print("\n--- Ternary if/else vs Filtering if ---")

# FILTERING if -> placed AFTER the for-clause; excludes some items
filtered = [x for x in range(1, 6) if x % 2 == 0]
print("filtering if (excludes odd numbers):", filtered)

# TERNARY if/else -> placed BEFORE the for-clause; keeps ALL items,
# just changes their VALUE
labeled = ["even" if x % 2 == 0 else "odd" for x in range(1, 6)]
print("ternary if/else (labels every item, excludes nothing):", labeled)

# You can combine BOTH: ternary to transform, filtering to exclude
combined = ["even" if x % 2 == 0 else "odd" for x in range(1, 10) if x > 3]
print("combined ternary + filter:", combined)


"""
---------------------------------------------------------------------
3. NESTED LOOPS INSIDE A COMPREHENSION  ⭐⭐⭐
---------------------------------------------------------------------
Multiple `for` clauses inside one comprehension work exactly like
NESTED for-loops, read LEFT TO RIGHT (outermost loop first).

    [expr for x in outer for y in inner]

is equivalent to:

    for x in outer:
        for y in inner:
            ... expr ...
---------------------------------------------------------------------
"""

print("\n--- Nested Loops Inside a Comprehension ---")

# Cartesian product of two lists - classic use case
colors = ["red", "blue"]
sizes = ["S", "M", "L"]

combinations = [(color, size) for color in colors for size in sizes]
print("cartesian product:", combinations)

# Flattening a list of lists - the OUTER for comes first (iterates
# over each sublist), the INNER for comes second (iterates over
# each item within that sublist)
nested_data = [[1, 2, 3], [4, 5], [6, 7, 8, 9]]
flattened = [item for sublist in nested_data for item in sublist]
print("flattened list of lists:", flattened)

# Nested comprehension WITH a filter on the inner loop
nested_filtered = [item for sublist in nested_data for item in sublist if item % 2 == 0]
print("flattened + filtered (evens only):", nested_filtered)


"""
---------------------------------------------------------------------
4. NESTED (2D) COMPREHENSIONS: BUILDING A MATRIX  ⭐⭐
---------------------------------------------------------------------
A comprehension INSIDE another comprehension builds NESTED
structures (e.g., a matrix), rather than flattening them. This is
different from #3 above, where multiple `for` clauses live in the
SAME comprehension.
---------------------------------------------------------------------
"""

print("\n--- Nested Comprehensions: Building a Matrix ---")

# Build a 3x3 multiplication table
multiplication_table = [[row * col for col in range(1, 4)] for row in range(1, 4)]
print("3x3 multiplication table:")
for row in multiplication_table:
    print(" ", row)

# Transpose a matrix using a nested comprehension
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
transposed = [[row[i] for row in matrix] for i in range(len(matrix[0]))]
print("\ntransposed matrix:", transposed)


"""
---------------------------------------------------------------------
5. SET COMPREHENSION  ⭐⭐
---------------------------------------------------------------------
Syntax:  {expr for item in iterable if condition}
Automatically deduplicates results, since the underlying structure
is a hash-based set. Order is NOT guaranteed.
---------------------------------------------------------------------
"""

print("\n--- Set Comprehension ---")

words = ["cat", "dog", "lion", "ox", "cat", "dog"]
unique_lengths = {len(w) for w in words}
print("unique word lengths (dupes auto-removed):", unique_lengths)

squares_of_evens_set = {x ** 2 for x in range(10) if x % 2 == 0}
print("set comprehension with filter:", squares_of_evens_set)


"""
---------------------------------------------------------------------
6. DICT COMPREHENSION  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  {key_expr: value_expr for item in iterable if condition}
Extremely common for building lookup tables / mappings from a
sequence of records - a core ETL pattern.
---------------------------------------------------------------------
"""

print("\n--- Dict Comprehension ---")

names = ["Alice", "Bob", "Carol"]
name_lengths = {name: len(name) for name in names}
print("name -> length mapping:", name_lengths)

# Building a lookup table FROM records (very common DE pattern)
records = [
    {"id": "A1", "price": 10.0},
    {"id": "A2", "price": 25.5},
    {"id": "A3", "price": 7.25},
]
price_lookup = {r["id"]: r["price"] for r in records}
print("lookup table built from records:", price_lookup)

# Filtering + transforming in a dict comprehension
prices = {"apple": 1.5, "banana": 0.5, "cherry": 3.0, "date": 4.5}
discounted_expensive = {k: round(v * 0.9, 2) for k, v in prices.items() if v > 1.0}
print("discounted (only where price > 1.0):", discounted_expensive)

# Inverting a dict (swap keys and values) - only safe if original
# values are unique, otherwise data is silently lost
inverted = {v: k for k, v in prices.items()}
print("inverted dict:", inverted)


"""
---------------------------------------------------------------------
7. GENERATOR EXPRESSION - THE LAZY COMPREHENSION  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  (expr for item in iterable if condition)

Looks like a list comprehension but uses PARENTHESES instead of
square brackets. Critically, it does NOT build the entire result in
memory upfront - it produces values LAZILY, one at a time, only as
they're requested. This is essential for processing large or
streamed data efficiently.
---------------------------------------------------------------------
"""

print("\n--- Generator Expression (Lazy Evaluation) ---")

list_comp = [x ** 2 for x in range(1_000_000)]     # built FULLY, right now
gen_expr = (x ** 2 for x in range(1_000_000))        # built LAZILY, on demand

print("list comprehension size in memory:", sys.getsizeof(list_comp), "bytes")
print("generator expression size in memory:", sys.getsizeof(gen_expr), "bytes")
print("\nThe generator is TINY regardless of range size - it doesn't")
print("materialize the million values until you iterate over it.")

# Consuming a generator expression - values are computed ON DEMAND
gen = (x ** 2 for x in range(5))
print("\nconsuming a generator expression:")
for val in gen:
    print(" ", val)

# A generator can only be consumed ONCE - it's exhausted afterward
print("\ntrying to reuse the SAME exhausted generator:")
print("list(gen) after full consumption:", list(gen))     # empty!


"""
---------------------------------------------------------------------
8. GENERATOR EXPRESSIONS AS FUNCTION ARGUMENTS (NO EXTRA PARENS)  ⭐⭐
---------------------------------------------------------------------
When a generator expression is the ONLY argument to a function, you
can drop the extra parentheses - a common, idiomatic shorthand.
---------------------------------------------------------------------
"""

print("\n--- Generator Expressions as the Sole Function Argument ---")

nums = [1, 2, 3, 4, 5]

# Both are equivalent - the second drops the redundant outer parens
total_verbose = sum((x ** 2 for x in nums))
total_idiomatic = sum(x ** 2 for x in nums)
print("sum with explicit parens:", total_verbose)
print("sum with idiomatic shorthand (no extra parens):", total_idiomatic)

# any()/all() are extremely common with generator expressions,
# since they short-circuit and never need the full list materialized
print("any(x > 4 for x in nums):", any(x > 4 for x in nums))
print("all(x > 0 for x in nums):", all(x > 0 for x in nums))


"""
---------------------------------------------------------------------
9. PERFORMANCE: COMPREHENSION vs EXPLICIT LOOP  ⭐⭐⭐
---------------------------------------------------------------------
List comprehensions are usually FASTER than an equivalent explicit
for-loop with .append(), because the comprehension's iteration runs
as a single optimized bytecode operation internally, avoiding the
repeated attribute lookup (`.append`) and function-call overhead on
every iteration.
---------------------------------------------------------------------
"""

print("\n--- Performance: Comprehension vs Explicit Loop ---")

n = 1_000_000

start = time.perf_counter()
loop_result = []
for x in range(n):
    loop_result.append(x * 2)
loop_time = time.perf_counter() - start

start = time.perf_counter()
comp_result = [x * 2 for x in range(n)]
comp_time = time.perf_counter() - start

print(f"explicit loop + append(): {loop_time:.4f} sec")
print(f"list comprehension:       {comp_time:.4f} sec  (usually faster)")


"""
---------------------------------------------------------------------
10. THE WALRUS OPERATOR (:=) INSIDE COMPREHENSIONS  ⭐⭐
---------------------------------------------------------------------
Python 3.8+ allows assigning to a variable INSIDE a comprehension
using `:=`, avoiding the need to compute an expensive expression
TWICE (once for the filter, once for the output value).
---------------------------------------------------------------------
"""

print("\n--- Walrus Operator Inside a Comprehension ---")

def expensive_computation(x):
    """Pretend this is a costly function call - e.g. an API lookup."""
    return x * x

data_source = [1, 2, 3, 4, 5, 6]

# WITHOUT walrus - expensive_computation() is called TWICE per item
without_walrus = [expensive_computation(x) for x in data_source
                  if expensive_computation(x) > 10]
print("without walrus (calls function twice per qualifying item):",
      without_walrus)

# WITH walrus - computed ONCE, reused for both the filter and output
with_walrus = [result for x in data_source
               if (result := expensive_computation(x)) > 10]
print("with walrus (computed only once per item):", with_walrus)


"""
---------------------------------------------------------------------
11. SCOPING: COMPREHENSION VARIABLES DON'T LEAK  ⭐⭐
---------------------------------------------------------------------
Unlike a plain for-loop, the loop variable inside a comprehension
has its OWN internal scope in Python 3 - it does NOT leak out into
the surrounding function/module namespace.
---------------------------------------------------------------------
"""

print("\n--- Scoping: Comprehension Variables Don't Leak ---")

x = "outer value, defined before the comprehension"
result = [x for x in range(5)]         # this 'x' is LOCAL to the comprehension
print("result:", result)
print("x after the comprehension (unchanged!):", x)

# Contrast with a regular for-loop, where the loop variable DOES leak
for y in range(3):
    pass
print("\ny after a regular for-loop (DOES leak):", y)


"""
---------------------------------------------------------------------
12. WHEN NOT TO USE A COMPREHENSION (READABILITY LIMITS)  ⭐⭐
---------------------------------------------------------------------
Comprehensions are great for SIMPLE transform/filter logic. Once you
need multiple nested conditions, side effects, or several
statements per item, an explicit loop is more readable and more
Pythonic - "readability counts."
---------------------------------------------------------------------
"""

print("\n--- When NOT to Use a Comprehension ---")

# Overly complex - hard to read, avoid this style
messy = [((x, y) if x != y else None)
         for x in range(3) for y in range(3) if x != y or y == 0]
print("an overly complex comprehension (avoid this):", messy)

# Better: use a plain loop with clear, named steps for complex logic
clear_result = []
for x in range(3):
    for y in range(3):
        if x != y or y == 0:
            if x != y:
                clear_result.append((x, y))
            else:
                clear_result.append(None)
print("equivalent logic as a readable loop:", clear_result)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Comprehension type   | Syntax                          | Builds
----------------------|----------------------------------|------------
List                  | [expr for x in it if cond]        | list
Set                    | {expr for x in it if cond}         | set (unique)
Dict                    | {k: v for x in it if cond}          | dict
Generator                | (expr for x in it if cond)           | generator
                                                                 (lazy)

Filtering `if`   -> goes AFTER the for-clause, EXCLUDES items
Ternary `if/else` -> goes BEFORE the for-clause, TRANSFORMS every item
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON COMPREHENSIONS
=====================================================================

1. What are the four types of comprehensions in Python, and what
   type of object does each one produce?

2. What's the difference between the "filtering if" (at the end of
   a comprehension) and the "ternary if/else" (at the beginning)?
   Can you use both in the same comprehension?

3. Why is a list comprehension generally FASTER than an equivalent
   explicit for-loop using .append()?

4. What is the key difference between a list comprehension
   `[x for x in range(n)]` and a generator expression
   `(x for x in range(n))`? Why would you prefer one over the other
   when processing a very large dataset?

5. Can a generator expression be consumed more than once? What
   happens if you try to iterate over an already-exhausted
   generator?

6. How would you flatten a list of lists into a single flat list
   using a nested comprehension with two `for` clauses?

7. What's the difference between writing
   `[[expr for x in inner] for inner in outer]` (nested
   comprehension building a 2D structure) versus
   `[expr for outer_item in outer for x in inner]` (multiple `for`
   clauses in ONE comprehension, producing a flat result)?

8. Does the loop variable inside a comprehension "leak" into the
   surrounding scope, the way a regular `for` loop's variable does?

9. What problem does the walrus operator (`:=`) solve when used
   inside a comprehension's filter condition? Give an example where
   NOT using it results in a function being called twice
   unnecessarily.

10. How would you build a dictionary from a list of records (e.g.,
    a list of dicts with an "id" field) using a single dict
    comprehension, to create a fast O(1) lookup table by id?

11. Why might a deeply nested or overly clever comprehension be
    considered BAD practice, even if it technically works? When
    would you choose an explicit loop instead?

12. What's the risk of inverting a dictionary using
    `{v: k for k, v in d.items()}` if the original dictionary's
    values are not unique?

13. In a data engineering context, why might you prefer a generator
    expression over a list comprehension when passing data into
    `sum()`, `any()`, `all()`, or a database bulk-insert function
    that consumes an iterable?

14. What does `set(x for x in some_list)` accomplish, and how is it
    different from `{x for x in some_list}` (a set comprehension)?
    Are they functionally equivalent?
=====================================================================
"""