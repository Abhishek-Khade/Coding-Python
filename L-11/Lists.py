"""
=====================================================================
PYTHON LIST - Memory Internals, Hardware-Level Behavior & Properties
=====================================================================

A Python `list` is NOT a simple contiguous block of raw values like
a C array. Under the hood (in CPython), a list is:

    A DYNAMIC ARRAY OF POINTERS (references) to Python objects.

This single fact explains almost every memory/performance question
asked about lists in interviews:
    - why lists can hold mixed types (int, str, list, ...)
    - why appending is usually O(1) but occasionally O(n)
    - why lists use more memory than arrays of the same "size"
    - why lists have poor CPU cache locality compared to NumPy arrays

This file explores list internals at the memory/hardware level using
sys.getsizeof(), id(), and CPython's real over-allocation behavior.
=====================================================================
"""

import sys

print("--- Overview ---")
print("A Python list = a resizable array of POINTERS to objects,")
print("NOT an array of the values themselves.")


"""
---------------------------------------------------------------------
1. HOW A LIST IS ACTUALLY STORED IN MEMORY  ⭐⭐⭐
---------------------------------------------------------------------
When you write:
    my_list = [10, "hello", 3.14]

CPython does NOT store 10, "hello", and 3.14 directly inside the
list's memory block. Instead, the list holds a contiguous array of
POINTERS (memory addresses), each pointing to a separately-allocated
Python object living elsewhere on the heap.

    list object (contiguous pointer array)
        [ ptr0 ] --------> PyObject for 10      (int, its own memory)
        [ ptr1 ] --------> PyObject for "hello"  (str, its own memory)
        [ ptr2 ] --------> PyObject for 3.14     (float, its own memory)

This is EXACTLY why a list can hold mixed types - it just stores
addresses, and any type of object can be pointed to.
---------------------------------------------------------------------
"""

print("\n--- How a List is Stored: Pointers, Not Values ---")

my_list = [10, "hello", 3.14]

for item in my_list:
    print(f"value={item!r:10} id(item)={id(item)}  <- object lives elsewhere")

print("\nid(my_list) =", id(my_list), " <- this is the LIST container's own address")
print("The list itself just holds POINTERS to the objects above,")
print("not the objects' actual data.")


"""
---------------------------------------------------------------------
2. PROVING IT: SHARED REFERENCES INSIDE LISTS  ⭐⭐
---------------------------------------------------------------------
Since lists store pointers, TWO different lists can point to the
EXACT SAME underlying object. Mutating that shared object through
one list is visible through the other - a direct consequence of the
pointer-based storage model.
---------------------------------------------------------------------
"""

print("\n--- Shared References Inside Lists ---")

shared_inner = [1, 2, 3]
list_a = [shared_inner, "a"]
list_b = [shared_inner, "b"]     # both point to the SAME inner list

shared_inner.append(99)
print("list_a:", list_a)     # inner list changed here too
print("list_b:", list_b)     # ...and here, same object
print("list_a[0] is list_b[0] ->", list_a[0] is list_b[0])   # True


"""
---------------------------------------------------------------------
3. MEMORY SIZE: sys.getsizeof() ⭐⭐⭐
---------------------------------------------------------------------
sys.getsizeof() shows the size of the LIST CONTAINER itself (the
array of pointers + overhead) - NOT the size of the objects it
points to. To get the true total memory footprint, you'd need to
add up the sizes of all referenced objects too.
---------------------------------------------------------------------
"""

print("\n--- Memory Size with sys.getsizeof() ---")

empty_list = []
print("empty list size:", sys.getsizeof(empty_list), "bytes  <- fixed overhead")

one_item = [1]
print("1-item list size:", sys.getsizeof(one_item), "bytes")

five_items = [1, 2, 3, 4, 5]
print("5-item list size:", sys.getsizeof(five_items), "bytes")

# Important: getsizeof() does NOT include the size of the objects
# pointed to - only the container's own pointer array + metadata
nested = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
print("\nlist containing ONE big nested list, size:",
      sys.getsizeof(nested), "bytes  <- misleadingly small!")
print("(the size of the pointer array is tiny; the big list it",
      "points to is a SEPARATE object, sized separately)")
print("size of the actual nested list:", sys.getsizeof(nested[0]), "bytes")


"""
---------------------------------------------------------------------
4. OVER-ALLOCATION: WHY append() IS "AMORTIZED" O(1)  ⭐⭐⭐
---------------------------------------------------------------------
If a list only ever allocated EXACTLY enough memory for its current
elements, every single append() would require allocating a brand
new, slightly bigger array and copying everything over - O(n) per
append, O(n^2) total for n appends.

Instead, CPython OVER-ALLOCATES extra capacity whenever it needs to
grow the underlying array. This means MOST append() calls are true
O(1) (just placing a pointer in already-reserved space), and only
OCCASIONALLY does a resize+copy happen. Averaged over many appends,
this gives "amortized O(1)" performance.

You can literally observe the jumps in allocated memory using
sys.getsizeof() as a list grows.
---------------------------------------------------------------------
"""

print("\n--- Over-Allocation: Watching a List Grow ---")

growing_list = []
prev_size = sys.getsizeof(growing_list)
print(f"start: len=0, size={prev_size} bytes")

for i in range(20):
    growing_list.append(i)
    current_size = sys.getsizeof(growing_list)
    if current_size != prev_size:
        print(f"len={len(growing_list):2} -> size JUMPED to "
              f"{current_size} bytes  <-- reallocation happened here")
        prev_size = current_size

print("\nNotice: the size does NOT grow by a fixed amount every")
print("append() - it jumps occasionally because CPython allocates")
print("EXTRA room in advance, anticipating future growth.")


"""
---------------------------------------------------------------------
5. TIME COMPLEXITY OF LIST OPERATIONS  ⭐⭐⭐
---------------------------------------------------------------------
Because a list is a dynamic array (contiguous pointer block), its
performance characteristics mirror those of arrays in general:

    Operation              | Complexity | Why
    -----------------------|------------|--------------------------------
    index access lst[i]    | O(1)       | direct pointer-array offset
    append (at end)        | O(1)*      | amortized, due to over-allocation
    pop() (from end)       | O(1)       | no shifting needed
    pop(0) (from start)    | O(n)       | ALL remaining pointers must shift
    insert(0, x)            | O(n)       | ALL existing pointers shift right
    membership (x in lst)   | O(n)       | linear scan, no hashing
    len(lst)                | O(1)       | length is cached, not counted
    slicing lst[a:b]        | O(k)       | k = size of the slice, copies
                            |            | pointers into a NEW list

    * amortized: occasional O(n) resize, but averaged over many
      appends it behaves like O(1)
---------------------------------------------------------------------
"""

print("\n--- Time Complexity in Action ---")

import time

big_list = list(range(200_000))

# pop() from the END - O(1), no shifting
start = time.perf_counter()
big_list.pop()
end = time.perf_counter()
print(f"pop() from end:    {end - start:.8f} sec  (O(1))")

# pop(0) from the START - O(n), everything shifts left by one slot
start = time.perf_counter()
big_list.pop(0)
end = time.perf_counter()
print(f"pop(0) from start: {end - start:.8f} sec  (O(n) - notice it's slower)")


"""
---------------------------------------------------------------------
6. WHY LISTS HAVE POOR CPU CACHE LOCALITY  ⭐⭐
---------------------------------------------------------------------
Even though the POINTER ARRAY itself is contiguous in memory, the
actual OBJECTS it points to are scattered all over the heap,
allocated wherever the memory manager found space. This means
iterating over a list and touching each element's VALUE causes the
CPU to jump around memory unpredictably (poor "cache locality").

This is a KEY REASON why NumPy arrays (which store raw values
contiguously, no pointer indirection) are dramatically faster for
numeric computation than plain Python lists.
---------------------------------------------------------------------
"""

print("\n--- Cache Locality: List of Objects vs Contiguous Array ---")

python_list = list(range(1_000_000))

start = time.perf_counter()
total = sum(python_list)          # touches each scattered int object
end = time.perf_counter()
print(f"sum() over Python list:  {end - start:.5f} sec")

try:
    import numpy as np
    numpy_array = np.arange(1_000_000)

    start = time.perf_counter()
    total_np = numpy_array.sum()   # operates on contiguous raw memory
    end = time.perf_counter()
    print(f"sum() over NumPy array: {end - start:.5f} sec  <- much faster")
    print("(NumPy stores raw values contiguously - no pointer chasing,")
    print(" excellent CPU cache locality, and vectorized/SIMD instructions)")
except ImportError:
    print("(numpy not installed - conceptually, ndarray avoids pointer")
    print(" indirection entirely, unlike list)")


"""
---------------------------------------------------------------------
7. LIST COPYING: SHALLOW COPY ONLY COPIES POINTERS  ⭐⭐
---------------------------------------------------------------------
Because lists store pointers, a "shallow copy" copies the POINTER
ARRAY (the addresses), NOT the objects being pointed to. Nested
mutable objects remain SHARED between the original and the copy.
---------------------------------------------------------------------
"""

print("\n--- Shallow Copy Copies Pointers, Not Objects ---")

original = [[1, 2], [3, 4]]
shallow_copy = original.copy()      # or original[:], or list(original)

print("original is shallow_copy ->", original is shallow_copy)          # False
print("original[0] is shallow_copy[0] ->", original[0] is shallow_copy[0])  # True!

shallow_copy[0].append(99)          # mutates the SHARED inner list
print("original after mutating shallow_copy's inner list:", original)


"""
---------------------------------------------------------------------
8. LISTS ARE MUTABLE -> NOT HASHABLE  ⭐⭐
---------------------------------------------------------------------
Since a list's contents (and thus its pointer array) can change
after creation, Python disallows using lists as dict keys or set
elements - their hash value could never be guaranteed stable.
---------------------------------------------------------------------
"""

print("\n--- Lists Are Unhashable ---")

try:
    hash([1, 2, 3])
except TypeError as e:
    print("Error hashing a list:", e)


"""
---------------------------------------------------------------------
9. QUICK PROPERTY SUMMARY
---------------------------------------------------------------------
    Ordered            -> Yes (preserves insertion order)
    Mutable             -> Yes (in-place modification allowed)
    Allows duplicates    -> Yes
    Indexed              -> Yes (0-based, supports negative indices)
    Hashable              -> No
    Homogeneous required  -> No (can mix types freely)
    Underlying storage    -> Dynamic array of POINTERS (references)
    Growth strategy        -> Over-allocation (amortized O(1) append)
    Memory overhead         -> Higher than arrays (pointer indirection
                               + per-object Python overhead)
---------------------------------------------------------------------
"""

print("\n--- Quick Property Summary (see comment block above) ---")

"""
=====================================================================
PYTHON LIST - OPERATIONS - Complete Notes with Executable Examples
=====================================================================

This file covers every major category of operation you can perform
on a Python list:

    1. Creating lists
    2. Adding elements (append, extend, insert)
    3. Removing elements (remove, pop, clear, del)
    4. Accessing & slicing
    5. Searching (index, count, in)
    6. Sorting & reversing
    7. Copying
    8. Concatenation & repetition
    9. List comprehensions
    10. Aggregate/built-in functions (len, sum, min, max, etc.)
    11. Unpacking
    12. Nested list operations (flattening, matrix-style access)
=====================================================================
"""

print("--- Overview ---")
print("Lists support a rich set of in-place and non-mutating operations.")


"""
---------------------------------------------------------------------
1. CREATING LISTS
---------------------------------------------------------------------
"""

print("\n--- Creating Lists ---")

empty = []
literal = [1, 2, 3]
from_range = list(range(5))
repeated = [0] * 5              # repetition to pre-fill a list
from_string = list("hello")     # splits into individual characters

print("empty:", empty)
print("literal:", literal)
print("from range():", from_range)
print("repeated [0]*5:", repeated)
print("from string:", from_string)

# CAUTION: repeating a MUTABLE object with '*' shares references!
matrix_wrong = [[0] * 3] * 3        # all 3 rows are the SAME list object
matrix_wrong[0][0] = 99
print("\nBUGGY matrix (shared rows):", matrix_wrong)   # all rows affected!

matrix_correct = [[0] * 3 for _ in range(3)]   # each row is a NEW list
matrix_correct[0][0] = 99
print("CORRECT matrix (independent rows):", matrix_correct)


"""
---------------------------------------------------------------------
2. ADDING ELEMENTS  ⭐⭐
---------------------------------------------------------------------
append(x)     -> adds a SINGLE element to the end            O(1)*
extend(iter)  -> adds ALL elements of an iterable to the end  O(k)
insert(i, x)  -> inserts x at index i, shifting others right   O(n)
+ (concat)    -> creates a NEW list, does not mutate either one
---------------------------------------------------------------------
"""

print("\n--- Adding Elements ---")

fruits = ["apple", "banana"]

fruits.append("cherry")             # adds one item
print("after append:", fruits)

fruits.extend(["date", "fig"])       # adds multiple items
print("after extend:", fruits)

# Common mistake: append() with a list ADDS THE WHOLE LIST as ONE
# nested element, instead of merging - extend() is what you want
mistake = ["a", "b"]
mistake.append(["c", "d"])
print("\nappend() with a list (WRONG for merging):", mistake)

correct = ["a", "b"]
correct.extend(["c", "d"])
print("extend() with a list (CORRECT for merging):", correct)

fruits.insert(1, "apricot")          # insert at a specific index
print("\nafter insert(1, 'apricot'):", fruits)


"""
---------------------------------------------------------------------
3. REMOVING ELEMENTS  ⭐⭐⭐
---------------------------------------------------------------------
remove(x)  -> removes the FIRST occurrence of value x  (ValueError
              if not found)                                    O(n)
pop(i)     -> removes AND RETURNS the item at index i
              (default: last item)                       O(1) at end,
                                                           O(n) elsewhere
clear()    -> removes ALL elements, list becomes empty          O(n)
del lst[i] -> deletes item at index i (no return value)          O(n)
del lst[a:b] -> deletes a SLICE of items
---------------------------------------------------------------------
"""

print("\n--- Removing Elements ---")

nums = [10, 20, 30, 40, 50]

nums.remove(30)                       # removes the VALUE 30
print("after remove(30):", nums)

try:
    nums.remove(999)                   # not found -> ValueError
except ValueError as e:
    print("Error removing missing value:", e)

popped_last = nums.pop()               # removes & returns LAST item
print("popped (default, last):", popped_last, "| list now:", nums)

popped_first = nums.pop(0)             # removes & returns item at index 0
print("popped(0):", popped_first, "| list now:", nums)

del nums[0]                             # deletes by index, no return value
print("after del nums[0]:", nums)

nums_to_clear = [1, 2, 3]
nums_to_clear.clear()
print("after clear():", nums_to_clear)

slice_del = [1, 2, 3, 4, 5]
del slice_del[1:3]                       # deletes a range of items
print("after del slice_del[1:3]:", slice_del)


"""
---------------------------------------------------------------------
4. ACCESSING & SLICING  ⭐⭐
---------------------------------------------------------------------
lst[i]        -> single element access, supports negative indices
lst[a:b]      -> slice from a (inclusive) to b (exclusive)
lst[a:b:step] -> slice with a step
Slicing ALWAYS returns a NEW list (does not mutate the original).
---------------------------------------------------------------------
"""

print("\n--- Accessing & Slicing ---")

letters = ["a", "b", "c", "d", "e", "f"]

print("letters[2]:", letters[2])
print("letters[-1]:", letters[-1])          # last element
print("letters[1:4]:", letters[1:4])        # ['b', 'c', 'd']
print("letters[:3]:", letters[:3])          # from start
print("letters[3:]:", letters[3:])          # to end
print("letters[::2]:", letters[::2])        # every 2nd element
print("letters[::-1]:", letters[::-1])      # reversed COPY

# Slice assignment - can replace a RANGE of elements, even with a
# DIFFERENT number of new elements (list can grow or shrink!)
letters_copy = ["a", "b", "c", "d", "e"]
letters_copy[1:3] = ["X", "Y", "Z"]          # replaces 2 items with 3
print("\nafter slice assignment (2 items -> 3 items):", letters_copy)


"""
---------------------------------------------------------------------
5. SEARCHING  ⭐⭐
---------------------------------------------------------------------
index(x)   -> returns index of FIRST occurrence (ValueError if
              not found)                                        O(n)
count(x)   -> returns how many times x appears                   O(n)
x in lst   -> membership test, returns True/False                 O(n)
---------------------------------------------------------------------
"""

print("\n--- Searching ---")

data = [10, 20, 30, 20, 40, 20]

print("index(20):", data.index(20))               # first match only: index 1
print("index(20, 2):", data.index(20, 2))          # search starting from index 2
print("count(20):", data.count(20))
print("40 in data:", 40 in data)
print("99 in data:", 99 in data)

try:
    data.index(999)
except ValueError as e:
    print("Error searching missing value:", e)


"""
---------------------------------------------------------------------
6. SORTING & REVERSING  ⭐⭐⭐
---------------------------------------------------------------------
sort()        -> sorts the list IN PLACE, returns None
sorted(lst)   -> returns a NEW sorted list, leaves original unchanged
reverse()     -> reverses the list IN PLACE
reversed(lst) -> returns a reverse ITERATOR (lazy), not a list

sort()/sorted() accept:
    key=      -> a function to determine sort order
    reverse=  -> True for descending order
---------------------------------------------------------------------
"""

print("\n--- Sorting & Reversing ---")

nums_unsorted = [5, 2, 9, 1, 7]

nums_unsorted.sort()                     # mutates in place, returns None
print("after sort():", nums_unsorted)

nums_unsorted.sort(reverse=True)
print("after sort(reverse=True):", nums_unsorted)

# sorted() does NOT mutate - returns a new list
original = [5, 2, 9, 1, 7]
new_sorted = sorted(original)
print("\noriginal (unchanged):", original)
print("sorted() result:", new_sorted)

# Sorting with a key function - very common in data engineering
# (e.g., sort records by a specific field)
records = [{"name": "Bob", "age": 25}, {"name": "Amy", "age": 30},
           {"name": "Cid", "age": 20}]
by_age = sorted(records, key=lambda r: r["age"])
print("\nsorted by age:", by_age)

by_name = sorted(records, key=lambda r: r["name"])
print("sorted by name:", by_name)

# reverse() mutates in place; reversed() returns a lazy iterator
letters_list = ["a", "b", "c"]
letters_list.reverse()
print("\nafter reverse() (in place):", letters_list)

rev_iter = reversed(["x", "y", "z"])
print("reversed() iterator object:", rev_iter)
print("consumed as a list:", list(rev_iter))


"""
---------------------------------------------------------------------
7. COPYING  ⭐⭐⭐
---------------------------------------------------------------------
lst.copy()  -> shallow copy (same as lst[:] or list(lst))
copy.deepcopy(lst) -> fully independent recursive copy

A plain assignment (b = a) does NOT copy at all - it's just another
name for the SAME list object.
---------------------------------------------------------------------
"""

print("\n--- Copying ---")

original_list = [[1, 2], [3, 4]]

no_copy = original_list                  # same object! NOT a copy
shallow1 = original_list.copy()
shallow2 = original_list[:]
shallow3 = list(original_list)

print("no_copy is original_list ->", no_copy is original_list)         # True
print("shallow1 is original_list ->", shallow1 is original_list)       # False
print("shallow1[0] is original_list[0] ->", shallow1[0] is original_list[0])  # True (shared inner list)

import copy
deep = copy.deepcopy(original_list)
deep[0].append(999)
print("\noriginal_list after deep copy mutation:", original_list)       # unaffected


"""
---------------------------------------------------------------------
8. CONCATENATION & REPETITION  ⭐
---------------------------------------------------------------------
+   -> concatenates two lists into a NEW list
+=  -> extends the list IN PLACE (equivalent to extend())
*   -> repeats a list's elements N times (NEW list)
---------------------------------------------------------------------
"""

print("\n--- Concatenation & Repetition ---")

list1 = [1, 2, 3]
list2 = [4, 5, 6]

combined = list1 + list2               # creates a NEW list
print("list1 + list2:", combined)
print("list1 unchanged:", list1)

list1 += [7, 8]                          # mutates list1 IN PLACE (like extend)
print("\nlist1 += [7, 8]:", list1)

repeated_list = [1, 2] * 3
print("[1, 2] * 3:", repeated_list)


"""
---------------------------------------------------------------------
9. LIST COMPREHENSIONS  ⭐⭐⭐
---------------------------------------------------------------------
Compact, often faster syntax for building lists compared to
explicit loops with .append().
---------------------------------------------------------------------
"""

print("\n--- List Comprehensions ---")

squares = [x ** 2 for x in range(1, 6)]
print("squares:", squares)

evens_only = [x for x in range(1, 11) if x % 2 == 0]
print("evens only:", evens_only)

# Nested comprehension - flatten a list of lists
nested_data = [[1, 2], [3, 4], [5, 6]]
flattened = [item for sublist in nested_data for item in sublist]
print("flattened:", flattened)

# Conditional expression INSIDE the comprehension (ternary-style)
labeled = ["even" if x % 2 == 0 else "odd" for x in range(1, 6)]
print("labeled odd/even:", labeled)


"""
---------------------------------------------------------------------
10. AGGREGATE / BUILT-IN FUNCTIONS ON LISTS  ⭐⭐
---------------------------------------------------------------------
len()   -> number of elements
sum()   -> total (numeric lists only)
min()   -> smallest element
max()   -> largest element
any()   -> True if AT LEAST ONE element is truthy
all()   -> True if ALL elements are truthy
---------------------------------------------------------------------
"""

print("\n--- Aggregate / Built-in Functions ---")

values = [4, 8, 15, 16, 23, 42]

print("len:", len(values))
print("sum:", sum(values))
print("min:", min(values))
print("max:", max(values))
print("any(x > 40 for x in values):", any(x > 40 for x in values))
print("all(x > 0 for x in values):", all(x > 0 for x in values))


"""
---------------------------------------------------------------------
11. UNPACKING  ⭐⭐
---------------------------------------------------------------------
Lists (like tuples) support unpacking into individual variables,
including the '*' "star" syntax to capture "the rest" of a list.
---------------------------------------------------------------------
"""

print("\n--- Unpacking ---")

first, second, third = [1, 2, 3]
print("unpacked:", first, second, third)

head, *rest = [1, 2, 3, 4, 5]
print("head:", head, "| rest:", rest)

*init, last = [1, 2, 3, 4, 5]
print("init:", init, "| last:", last)

first_val, *middle, last_val = [1, 2, 3, 4, 5]
print("first:", first_val, "| middle:", middle, "| last:", last_val)


"""
---------------------------------------------------------------------
12. NESTED LIST OPERATIONS (MATRIX-STYLE ACCESS)  ⭐
---------------------------------------------------------------------
Lists of lists are commonly used to represent matrices/2D grids or
row-based tabular data before loading into Pandas.
---------------------------------------------------------------------
"""

print("\n--- Nested List (Matrix-Style) Operations ---")

matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
]

print("matrix[1][2] (row 1, col 2):", matrix[1][2])   # 6

# Transpose a matrix using zip() + unpacking - a classic interview trick
transposed = [list(row) for row in zip(*matrix)]
print("transposed matrix:", transposed)

# Sum each row / each column
row_sums = [sum(row) for row in matrix]
col_sums = [sum(col) for col in zip(*matrix)]
print("row sums:", row_sums)
print("column sums:", col_sums)


"""
=====================================================================
INTERVIEW QUESTIONS - OPERATIONS ON LISTS
=====================================================================

1. What's the difference between `append()` and `extend()`? What
   happens if you `append()` a list instead of `extend()`-ing it?

2. What's the difference between `remove()` and `pop()`? Which one
   removes by value, and which by index?

3. Why is `list.pop()` O(1) but `list.pop(0)` O(n)?

4. What's the difference between `sort()` and `sorted()`? Which one
   mutates the original list, and which returns a new one?

5. How do you sort a list of dictionaries by a specific key? What
   argument of `sorted()` do you use?

6. What's the difference between `reverse()` and `reversed()`? What
   does `reversed()` actually return - a list or something else?

7. Why does `[[0] * 3] * 3` create a matrix where modifying one row
   affects all rows? How would you correctly initialize an
   independent 2D list?

8. What's the difference between slicing (`lst[:]`), `.copy()`, and
   `copy.deepcopy()` for copying a list of lists?

9. What does slice assignment do, e.g. `lst[1:3] = [10, 20, 30]`?
   Can the replacement have a DIFFERENT number of elements than the
   slice being replaced?

10. How would you flatten a list of lists into a single flat list
    using a list comprehension?

11. What does the star/unpacking syntax `head, *rest = my_list` do?
    Give a scenario where this is more readable than manual slicing.

12. How would you remove duplicate elements from a list while
    preserving their original order? Why doesn't converting directly
    to a `set` work if order matters?

13. What's the time complexity of `x in my_list` for searching, and
    why is a `set` generally preferred for repeated membership
    checks on large data?

14. How would you transpose a matrix (list of lists) in a single
    line using `zip()`? Explain what `zip(*matrix)` does.

15. In a data pipeline, if you have a large list of records
    (dicts) and need to filter, transform, and sort them, what
    combination of list comprehensions, `sorted()`, and `key=`
    would you use to do this efficiently in as few passes as
    possible?
=====================================================================
"""
"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON LIST: MEMORY & HARDWARE LEVEL
=====================================================================

1. How is a Python list actually stored in memory? Is it an array
   of values, or an array of something else?

2. Why can a Python list hold mixed data types (e.g., int, str,
   list) in a single list, unlike a C array or a NumPy array?

3. What does sys.getsizeof() actually measure for a list? Does it
   include the size of the objects the list's elements point to?

4. What is "over-allocation," and why does CPython over-allocate
   memory when a list grows? How does this make append() "amortized
   O(1)" instead of true O(1) every single time?

5. Why is `list.append()` generally fast (O(1) amortized), but
   `list.insert(0, x)` or `list.pop(0)` are O(n)?

6. Why do Python lists have worse CPU cache locality than NumPy
   arrays, even though the list's own pointer array is contiguous
   in memory?

7. If you do `b = a.copy()` where `a` is a list of lists, and then
   mutate `b[0]`, does `a[0]` change too? Explain why, in terms of
   what a shallow copy actually copies.

8. Why can't a list be used as a dictionary key or a set element?

9. Why does a list typically use MORE memory than an equivalent
   `array.array` or NumPy array holding the same numeric values?

10. What's the time complexity of `x in my_list` for a list of size
    n? How does this compare to `x in my_set` for a set of the same
    size, and why?

11. Explain why slicing a list (`lst[a:b]`) creates a NEW list
    object, and what gets copied - the objects themselves, or just
    the pointers to them?

12. If you have a very large list and you know its approximate
    final size in advance, how could you avoid repeated
    over-allocation/resizing overhead? (Hint: pre-sizing patterns,
    or using list comprehensions which can size more efficiently
    than repeated appends in a loop.)

13. Why does `id(my_list)` stay the SAME after calling
    `my_list.append(x)`, but change after `my_list = my_list + [x]`?
    What does this tell you about which operations mutate in place
    versus create a new object?

14. In a data engineering context, why might loading a huge dataset
    into a plain Python list (instead of a NumPy array or Pandas
    DataFrame) be a poor choice for numeric processing, from a
    memory and performance perspective?
=====================================================================
"""