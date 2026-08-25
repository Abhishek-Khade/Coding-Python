"""
=====================================================================
NUMPY ARRAYS BASICS - vs Python Lists, and Vectorization Performance
=====================================================================

A NumPy `ndarray` looks superficially like a Python list - you index
it, slice it, loop over it - but under the hood it is a completely
different data structure, and that difference is the source of
basically every NumPy interview question you'll get.

A Python `list` is an array of POINTERS. Each element is a separate,
independently-allocated Python object (a full `PyObject` with a type
tag, a refcount, and the actual value) living somewhere on the heap;
the list itself just stores addresses pointing at those objects. This
is what makes lists flexible (you can mix an int, a string, and a
dict in the same list) but slow and memory-hungry for numeric work -
every `+` between two "ints" involves chasing pointers, unboxing
Python objects, and going through the general-purpose (slow) Python
interpreter loop, once per element.

A NumPy array is a FIXED-TYPE, CONTIGUOUS block of raw memory - much
closer to a C array. Every element is the same primitive type (e.g.
8-byte float64), stored back-to-back with no per-element Python
object overhead. Because of that uniformity, NumPy can push whole-
array operations ("vectorized" operations) down into pre-compiled C
loops that operate on raw memory directly, skipping the Python
interpreter's per-element overhead entirely. This is THE reason
NumPy/Pandas vectorized code outperforms a Python `for` loop, often
by one to two orders of magnitude - the single most-asked question
in this module of the syllabus.
=====================================================================
"""

import sys
import time
import numpy as np

print("--- Overview ---")
print("A Python list stores POINTERS to separately-boxed objects.")
print("A NumPy array stores raw, fixed-type values in one contiguous")
print("memory block - which is what makes vectorized math fast.")
print("numpy version:", np.__version__)


"""
---------------------------------------------------------------------
1. CREATING ARRAYS  ⭐⭐
---------------------------------------------------------------------
The four everyday constructors: np.array (from existing data),
np.arange (like range(), but returns an array), np.zeros/np.ones
(pre-allocated, filled arrays - very common for pre-sizing a result
buffer before a loop), and np.linspace (N evenly spaced points
between two endpoints, INCLUSIVE of both ends by default).
---------------------------------------------------------------------
"""

print("\n--- Creating Arrays ---")

from_list = np.array([1, 2, 3, 4, 5])
print("np.array([1,2,3,4,5]):", from_list)

# arange: like range(), but the result is a real ndarray, and it
# accepts float steps (range() cannot).
arange_arr = np.arange(0, 10, 2)
print("np.arange(0, 10, 2):", arange_arr)

# zeros/ones: pre-allocate a buffer of a known SHAPE and dtype - much
# faster than growing a list with repeated .append() calls, because
# the memory is allocated ONCE up front instead of being reallocated
# and copied every time the underlying buffer fills up.
zeros_2d = np.zeros((2, 3))
ones_1d = np.ones(4, dtype=np.int32)
print("np.zeros((2,3)):\n", zeros_2d)
print("np.ones(4, dtype=int32):", ones_1d)

# linspace: N evenly spaced samples over [start, stop], INCLUSIVE of
# stop by default - handy for generating axes/bins, unlike arange
# where the stop is exclusive and step-based rounding can bite you.
lin = np.linspace(0, 1, 5)
print("np.linspace(0, 1, 5):", lin)


"""
---------------------------------------------------------------------
2. THE KEY STRUCTURAL DIFFERENCE: CONTIGUOUS TYPED MEMORY vs A LIST
   OF POINTERS  ⭐⭐⭐
---------------------------------------------------------------------
Every NumPy array has ONE dtype shared by every element, and that
dtype has a fixed byte size (`.itemsize`). Total memory used is then
just `itemsize * number_of_elements` (`.nbytes`) - a single flat
allocation. A Python list of the "same" ints, by contrast, allocates
one boxed int OBJECT per element (each with its own type/refcount
overhead) PLUS the list's own array of 8-byte pointers to them - so
its true memory footprint is much larger and scattered across the
heap (bad for CPU cache locality too).
---------------------------------------------------------------------
"""

print("\n--- Structural Difference: Typed Contiguous Memory vs Pointers ---")

arr = np.arange(1000, dtype=np.int64)
print("arr.dtype:", arr.dtype)
print("arr.itemsize (bytes per element):", arr.itemsize)
print("arr.nbytes (total, contiguous):", arr.nbytes)

py_list = list(range(1000))
# sys.getsizeof(py_list) only counts the list's OWN pointer array,
# not the 1000 separately-allocated int objects it points to - so
# even this undercounts the list's true footprint.
list_pointer_array_bytes = sys.getsizeof(py_list)
one_boxed_int_bytes = sys.getsizeof(1000)  # a representative boxed int object
estimated_list_total = list_pointer_array_bytes + one_boxed_int_bytes * len(py_list)

print("sys.getsizeof(py_list) - just the pointer array:", list_pointer_array_bytes)
print("sys.getsizeof(a boxed int):", one_boxed_int_bytes, "bytes (PER ELEMENT, extra)")
print("estimated TRUE list total (pointers + boxed ints):", estimated_list_total)
print(f"\nnumpy array: {arr.nbytes} contiguous bytes vs. estimated")
print(f"list: ~{estimated_list_total} scattered bytes for the same 1000 integers")
print("-> same logical data, several times more memory for the list,")
print("   and the list's bytes are NOT next to each other in RAM.")


"""
---------------------------------------------------------------------
3. VECTORIZATION PERFORMANCE: A REAL MEASURED BENCHMARK  ⭐⭐⭐
---------------------------------------------------------------------
This is THE headline interview question for this module: "why is a
vectorized NumPy operation faster than a Python for loop?" Answer it
with a measurement, not just theory. We multiply 1,000,000 numbers by
2 two ways: (a) a pure-Python for loop over a list, appending each
result, and (b) a single vectorized `arr * 2` call. The for loop pays
Python's per-element interpreter overhead (bytecode dispatch, boxing/
unboxing ints, a method call to `.append` per element) 1,000,000
times over; the vectorized call does ONE Python-level call that then
runs a tight, pre-compiled C loop directly over contiguous memory,
with no per-element Python overhead at all.
---------------------------------------------------------------------
"""

print("\n--- Vectorization Performance Benchmark (REAL, measured) ---")

N = 1_000_000
py_data = list(range(N))
np_data = np.arange(N)

start = time.perf_counter()
py_result = []
for x in py_data:            # a genuine Python for loop, not a comprehension -
    py_result.append(x * 2)  # each iteration: bytecode dispatch, unbox x, do
                              # the multiply, box the result, call .append()
py_elapsed = time.perf_counter() - start

start = time.perf_counter()
np_result = np_data * 2  # vectorized: one call, runs in compiled C
np_elapsed = time.perf_counter() - start

print(f"Python for-loop over {N:,} elements:            {py_elapsed:.5f} sec")
print(f"NumPy vectorized `arr * 2` over {N:,} elements: {np_elapsed:.5f} sec")
print(f"measured speedup: {py_elapsed / np_elapsed:.1f}x faster with NumPy")
print("results agree:", list(py_result[:5]) == list(np_result[:5]))

print("\nDATA ENGINEERING angle: any per-row Python loop over a numeric")
print("column (unit conversion, normalization, flagging outliers) should")
print("almost always be rewritten as a vectorized NumPy/Pandas expression")
print("- at real pipeline row counts, this is the difference between a")
print("transform step taking seconds vs. minutes or hours.")


"""
---------------------------------------------------------------------
4. BROADCASTING RULES  ⭐⭐⭐
---------------------------------------------------------------------
Broadcasting lets NumPy apply an operation between arrays of
DIFFERENT shapes without you manually looping or copying data. The
rule: compare shapes element-wise from the RIGHT; two dimensions are
compatible if they're EQUAL, or one of them is 1 (or missing) - it's
then stretched (conceptually, not by actually copying memory) to
match. If neither condition holds for some dimension, broadcasting
fails with a ValueError.
---------------------------------------------------------------------
"""

print("\n--- Broadcasting Rules ---")

# Case 1: scalar broadcast against an array - the scalar is treated
# as if it had the array's shape, with no actual copying.
scalar_case = np.array([1, 2, 3]) * 10
print("scalar broadcast, [1,2,3] * 10:", scalar_case)

# Case 2: a (3, 4) array plus a (4,) array. Compared from the right:
# trailing dims are 4 and 4 (equal - OK), and the (4,) array is
# missing a leading dimension, which NumPy treats as size 1 and
# stretches across all 3 rows.
matrix_3x4 = np.arange(12).reshape(3, 4)
row_vector_4 = np.array([100, 200, 300, 400])
broadcast_result = matrix_3x4 + row_vector_4
print("\n(3,4) array:\n", matrix_3x4)
print("(4,) array:", row_vector_4)
print("(3,4) + (4,) via broadcasting:\n", broadcast_result)
print("-> row_vector_4 was conceptually applied to EVERY row, with no")
print("   explicit loop and no real memory copy of row_vector_4.")

# Case 3: an incompatible shape pair - a REAL ValueError, caught.
matrix_3x4_again = np.arange(12).reshape(3, 4)
incompatible = np.array([1, 2, 3])  # shape (3,) can't align with trailing dim 4
try:
    broken = matrix_3x4_again + incompatible
except ValueError as e:
    print("\nIncompatible shapes (3,4) and (3,) raised a real ValueError:")
    print(" ", e)
print("-> (3,) aligned against the TRAILING dimension 4: neither equal")
print("   nor 1, so broadcasting has no rule that applies - it fails")
print("   fast instead of silently guessing what you meant.")


"""
---------------------------------------------------------------------
5. INDEXING, SLICING, BOOLEAN MASKING, AND FANCY INDEXING  ⭐⭐⭐
---------------------------------------------------------------------
Basic indexing/slicing works like Python lists, but NumPy adds two
much more powerful selection tools: BOOLEAN MASKING (index with an
array of True/False the same shape, keeping only True positions) and
FANCY INDEXING (index with an array/list of explicit integer
positions, in any order, with repeats allowed).
---------------------------------------------------------------------
"""

print("\n--- Indexing, Slicing, Boolean Masking, Fancy Indexing ---")

data = np.array([10, 15, 20, 25, 30, 35, 40])
print("data:", data)
print("basic slice data[1:4]:", data[1:4])

# Boolean masking: build a True/False array from a condition, then
# index with it - this is the idiomatic, vectorized way to filter,
# with no Python-level loop or if-statement required.
threshold = 20
mask = data > threshold
print(f"\nboolean mask (data > {threshold}):", mask)
print(f"data[data > {threshold}]:", data[mask])

# Fancy indexing: pass an explicit list/array of positions - order
# and repeats are both allowed, unlike a slice.
positions = [0, 0, 3, 6]
print("\nfancy indexing data[[0, 0, 3, 6]]:", data[positions])


"""
---------------------------------------------------------------------
6. THE VIEW vs COPY GOTCHA: SLICING RETURNS A VIEW  ⭐⭐⭐
---------------------------------------------------------------------
This is a classic interview trap. Slicing a NumPy array does NOT copy
its data - it returns a VIEW: a new ndarray object that shares the
SAME underlying memory buffer as the original. Mutating the view
mutates the original array too. (This is DIFFERENT from a Python
list slice, which always makes a real, independent copy.) Boolean
masking and fancy indexing, by contrast, always return a COPY - only
basic slicing (`start:stop:step`) returns a view.
---------------------------------------------------------------------
"""

print("\n--- The View vs Copy Gotcha ---")

original = np.array([1, 2, 3, 4, 5])
view_slice = original[1:4]     # a VIEW - shares memory with 'original'
print("original before mutating the slice:", original)
print("view_slice = original[1:4]:", view_slice)

view_slice[0] = 999            # mutate the VIEW...
print("view_slice after view_slice[0] = 999:", view_slice)
print("original AFTER mutating the slice:   ", original, "  <- changed too!")
print("(compare to a plain Python list: list[1:4] always COPIES)")

# The fix: explicitly request an independent copy with .copy().
original_2 = np.array([1, 2, 3, 4, 5])
safe_copy = original_2[1:4].copy()   # a real, independent copy
safe_copy[0] = 999
print("\nusing .copy() instead:")
print("safe_copy after mutation:", safe_copy)
print("original_2 UNCHANGED:    ", original_2, "  <- .copy() protected it")

print("\nnp.shares_memory(original, view_slice):", np.shares_memory(original, view_slice))
print("np.shares_memory(original_2, safe_copy):", np.shares_memory(original_2, safe_copy))


"""
---------------------------------------------------------------------
7. AGGREGATE FUNCTIONS AND THE axis PARAMETER  ⭐⭐
---------------------------------------------------------------------
sum/mean/std (and friends: min, max, argmax, ...) work over the WHOLE
array by default. On a 2D array, `axis=` controls which dimension
gets COLLAPSED: axis=0 collapses ROWS, producing one result PER
COLUMN ("down each column"); axis=1 collapses COLUMNS, producing one
result PER ROW ("across each row"). This trips people up constantly
- the axis you pass is the one that DISAPPEARS from the result shape.
---------------------------------------------------------------------
"""

print("\n--- Aggregate Functions and axis= ---")

grid = np.array([
    [1, 2, 3],
    [4, 5, 6],
])
print("grid:\n", grid, " shape:", grid.shape)

print("\ngrid.sum() [no axis - flattens everything]:", grid.sum())
print("grid.mean():", grid.mean())
print("grid.std():", round(float(grid.std()), 4))

# axis=0: collapse the ROW dimension -> one number per COLUMN
print("\ngrid.sum(axis=0) [collapse rows, per-COLUMN totals]:", grid.sum(axis=0))
print("  -> column 0 total: 1 + 4 =", 1 + 4)

# axis=1: collapse the COLUMN dimension -> one number per ROW
print("grid.sum(axis=1) [collapse columns, per-ROW totals]:", grid.sum(axis=1))
print("  -> row 0 total: 1 + 2 + 3 =", 1 + 2 + 3)

print("\nDATA ENGINEERING angle: with rows=records and columns=features,")
print("axis=0 gives per-FEATURE stats (e.g. mean of each column across")
print("all records - classic normalization); axis=1 gives per-RECORD")
print("stats (e.g. total across that one row's features).")


"""
---------------------------------------------------------------------
8. DTYPE UPCASTING AND SILENT OVERFLOW  ⭐⭐
---------------------------------------------------------------------
NumPy arrays use FIXED-WIDTH integer types (int8, int16, int32, ...),
unlike Python's built-in `int`, which grows arbitrarily large
automatically. Choosing a narrow dtype to save memory is a real,
common optimization (see Module 7's "memory optimization" topic) -
but it comes with a real DATA-QUALITY trap: arithmetic that exceeds
the dtype's range does NOT raise an error, it silently WRAPS AROUND.
This can corrupt a pipeline's numbers with no warning at all.
---------------------------------------------------------------------
"""

print("\n--- dtype Upcasting/Overflow Gotcha ---")

small = np.array([100, 120], dtype=np.int8)   # int8 range: -128 to 127
print("small (int8):", small, " dtype:", small.dtype)

with np.errstate(over="ignore"):  # suppress the RuntimeWarning so output stays clean
    overflowed = small + np.int8(20)   # 100+20=120 (fine), but 120+20=140 overflows int8
print("small + 20 ([100,120] + 20):", overflowed, "  <- second value SILENTLY WRAPPED!")
print("(120 + 20 = 140, which does not fit in int8's -128..127 range,")
print(" so it wraps around to 140 - 256 = -116, exactly what's shown above)")

# Upcasting: an operation between two DIFFERENT dtypes promotes the
# result to the wider/more precise type automatically (no overflow).
int_arr = np.array([1, 2, 3], dtype=np.int32)
float_arr = np.array([1.5, 2.5, 3.5], dtype=np.float64)
mixed = int_arr + float_arr
print("\nint32 + float64 upcasts result to:", mixed.dtype, "->", mixed)

print("\nTAKEAWAY: pick a narrow dtype deliberately for memory savings,")
print("but validate your data's actual value RANGE first - NumPy will")
print("never warn you by default when a narrow-dtype column silently")
print("overflows during a transform step.")


"""
---------------------------------------------------------------------
9. DATA ENGINEERING USE CASE: MEMORY-AWARE DTYPE SELECTION AT SCALE
   ⭐⭐
---------------------------------------------------------------------
Combining sections 2 and 8: when loading a large numeric column
(e.g. a "quantity" or "age" column from a Parquet/CSV file into a
NumPy-backed Pandas column), choosing the SMALLEST dtype that safely
covers the real data range shrinks memory `nbytes` proportionally
and lets vectorized operations move more values through the CPU
cache per pass - but only after confirming the value range fits.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Memory-Aware dtype Selection ---")

raw_quantities = np.random.randint(0, 200, size=200_000)  # simulates a loaded column
default_arr = raw_quantities.astype(np.int64)   # NumPy's default int width
print("default int64 array nbytes:", default_arr.nbytes)

data_max, data_min = int(default_arr.max()), int(default_arr.min())
print(f"actual data range: [{data_min}, {data_max}]")

# int16 safely covers -32768..32767, comfortably fitting this range -
# ALWAYS check the true min/max first, per the overflow gotcha above.
if np.iinfo(np.int16).min <= data_min and data_max <= np.iinfo(np.int16).max:
    optimized_arr = default_arr.astype(np.int16)
    print("optimized int16 array nbytes:", optimized_arr.nbytes)
    print(f"memory reduction: {default_arr.nbytes / optimized_arr.nbytes:.1f}x smaller")
else:
    print("data range does not safely fit int16 - keeping wider dtype")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Creating arrays:
    np.array(list)              -> from existing Python data
    np.arange(start, stop, step) -> like range(), returns ndarray
    np.zeros(shape) / np.ones(shape) -> pre-allocated, filled buffer
    np.linspace(start, stop, n)  -> n evenly spaced points, INCLUSIVE

Structural difference:
    Python list  -> array of POINTERS to separately boxed objects
    NumPy array  -> one contiguous block of FIXED-TYPE raw values
    .dtype / .itemsize / .nbytes -> inspect an array's memory layout

Vectorization:
    Python for-loop  -> per-element interpreter overhead x N
    arr * 2 (vectorized) -> one call, runs in compiled C over
                             contiguous memory -> measured 10-100x+

Broadcasting (compare shapes from the RIGHT):
    dims match, OR one dim is 1/missing -> stretched, OK
    otherwise                            -> ValueError

Indexing:
    arr[start:stop:step]  -> VIEW (shares memory!)
    arr[bool_mask]         -> COPY (boolean masking)
    arr[[i, j, k]]           -> COPY (fancy indexing)
    view.copy()               -> force an independent copy

Aggregates + axis:
    arr.sum()/.mean()/.std()  -> whole-array scalar (no axis)
    axis=0 -> collapses ROWS    -> one result per COLUMN
    axis=1 -> collapses COLUMNS -> one result per ROW

dtype gotchas:
    narrow int dtype + overflow -> SILENT wraparound, no error
    mixed dtypes in an op        -> auto-upcast to the wider type
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - NUMPY ARRAYS BASICS
=====================================================================

1. Why is a vectorized NumPy operation (e.g. `arr * 2`) faster than
   an equivalent Python `for` loop over a list, in terms of what
   actually happens at the memory and interpreter level?

2. Structurally, how does a Python list store its elements
   differently from how a NumPy array stores its elements? Why does
   that difference matter for both memory usage and speed?

3. What do `.dtype`, `.itemsize`, and `.nbytes` each tell you about
   an ndarray, and how are the three related mathematically?

4. In the benchmark in this file, what specifically makes the
   Python for-loop over `py_data` slow on a per-element basis, that
   `np_data * 2` avoids entirely?

5. Explain NumPy's broadcasting rule for comparing two array shapes.
   Why does a `(3, 4)` array broadcast successfully against a `(4,)`
   array, but fail against a `(3,)` array?

6. What exception does NumPy raise when two array shapes cannot be
   broadcast together, and at what point (which dimension) does the
   comparison actually fail?

7. What is the difference between boolean masking (`arr[arr > x]`)
   and fancy indexing (`arr[[0, 2, 5]]`)? Do either of them return a
   view or a copy?

8. In this file, `view_slice = original[1:4]` followed by
   `view_slice[0] = 999` also changed `original`. Why does basic
   slicing behave this way in NumPy, and how is this different from
   slicing a plain Python list?

9. How would you fix the view-mutation issue from question 8 if you
   genuinely needed an independent copy of the sliced data?

10. Given a 2D array `grid` of shape `(3, 4)`, what is the resulting
    shape of `grid.sum(axis=0)` versus `grid.sum(axis=1)`, and which
    dimension does each collapse?

11. What happens numerically when you add `20` to an `int8` array
    holding the value `120`? Why does NumPy not raise an error here,
    and why is this dangerous in a real data pipeline?

12. What is dtype "upcasting"? What dtype results from adding an
    `int32` array to a `float64` array, and why?

13. Why would a data engineer deliberately choose a narrower integer
    dtype (like `int16` instead of the default `int64`) for a large
    column, and what must they verify before doing so safely?

14. Compare `np.arange` and `np.linspace` - when would you prefer
    one over the other, and what's the "inclusive endpoint"
    difference between them?

15. If you were optimizing a Pandas ETL transform step that currently
    uses `df['col'].apply(lambda x: x * 2)`, what NumPy-backed
    change would you make, and why would you expect it to be faster
    at scale?
=====================================================================
"""
