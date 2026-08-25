"""
=====================================================================
PYTHON TUPLE - Memory Internals, Storage, Operations & Properties
=====================================================================

A tuple is an ORDERED, IMMUTABLE collection. Like a list, it is
internally a DYNAMIC ARRAY OF POINTERS to objects - but because a
tuple's size and contents can NEVER change after creation, CPython
can make several important optimizations that lists cannot:

    - NO over-allocation needed (size is fixed forever, so CPython
      allocates EXACTLY the memory needed - no extra "growth room")
    - Can be safely HASHED (if all elements are hashable) - so tuples
      can be dict keys / set elements, unlike lists
    - Small tuples are CACHED/REUSED by CPython in some cases
      (implementation detail, not guaranteed)
    - Slightly less memory overhead per element than a list, since
      there is no need to track spare capacity

This file covers: memory-level storage, properties, all major
operations, and interview questions.
=====================================================================
"""

import sys
import copy
import time

print("--- Overview ---")
print("A tuple = an array of pointers, like a list, but FIXED-SIZE")
print("and IMMUTABLE once created.")


"""
=====================================================================
PART A: HARDWARE-LEVEL / MEMORY INTERNALS
=====================================================================
"""

"""
---------------------------------------------------------------------
1. HOW A TUPLE IS STORED IN MEMORY  ⭐⭐⭐
---------------------------------------------------------------------
Just like a list, a tuple holds a contiguous array of POINTERS to
objects living elsewhere on the heap - NOT the raw values inline.
This is why tuples, like lists, can hold MIXED types.

    tuple object (contiguous pointer array, FIXED size)
        [ ptr0 ] --------> PyObject for 10
        [ ptr1 ] --------> PyObject for "hello"
        [ ptr2 ] --------> PyObject for 3.14

The key structural difference from a list: this pointer array is
allocated ONCE, at EXACTLY the size needed, and can never grow or
shrink.
---------------------------------------------------------------------
"""

print("\n--- How a Tuple is Stored: Fixed-Size Pointer Array ---")

my_tuple = (10, "hello", 3.14)
for item in my_tuple:
    print(f"value={item!r:10} id(item)={id(item)}  <- object lives elsewhere")

print("id(my_tuple) =", id(my_tuple))


"""
---------------------------------------------------------------------
2. TUPLE vs LIST: MEMORY SIZE COMPARISON  ⭐⭐⭐
---------------------------------------------------------------------
Because tuples never over-allocate spare capacity (they CAN'T grow),
a tuple with N elements is generally SMALLER in memory than a list
with the same N elements.
---------------------------------------------------------------------
"""

print("\n--- Tuple vs List: Memory Size ---")

for n in [0, 1, 3, 5, 10]:
    t = tuple(range(n))
    l = list(range(n))
    print(f"n={n:2} | tuple: {sys.getsizeof(t):4} bytes | "
          f"list: {sys.getsizeof(l):4} bytes")

print("\nTuples are consistently smaller - no spare capacity reserved.")


"""
---------------------------------------------------------------------
3. NO OVER-ALLOCATION: TUPLES DON'T "GROW"  ⭐⭐⭐
---------------------------------------------------------------------
Since a tuple's size is fixed at creation, there is nothing to
"append" - any operation that looks like adding to a tuple (like
`t + (4,)`) actually creates an ENTIRELY NEW tuple object with a
freshly, exactly-sized allocation. There is no amortized O(1)
append behavior here, because tuples are not meant to grow at all.
---------------------------------------------------------------------
"""

print("\n--- Tuples Don't Grow: '+' Creates a Brand New Object ---")

t1 = (1, 2, 3)
print("id(t1) before:", id(t1))

t1 = t1 + (4,)          # NOT in-place - creates a completely new tuple
print("id(t1) after t1 + (4,):", id(t1), "  <-- DIFFERENT id")


"""
---------------------------------------------------------------------
4. HASHABILITY: WHY TUPLES CAN BE DICT KEYS  ⭐⭐⭐
---------------------------------------------------------------------
Because a tuple's structure and (by default use case) its contents
cannot change, Python CAN compute a stable hash for it - IF, and
only if, every element inside it is ALSO hashable. This makes tuples
usable as dictionary keys and set elements, unlike lists.
---------------------------------------------------------------------
"""

print("\n--- Hashability ---")

coordinate_map = {
    (0, 0): "origin",
    (1, 0): "east",
    (0, 1): "north",
}
print("dict keyed by tuples:", coordinate_map)
print("hash((1, 2)):", hash((1, 2)))

# A tuple containing a MUTABLE element (like a list) is NOT hashable,
# because that inner element's value (and thus the "logical" content
# of the tuple) COULD still change even though the tuple itself
# can't be resized/reassigned
unhashable_tuple = (1, 2, [3, 4])
try:
    hash(unhashable_tuple)
except TypeError as e:
    print("Error hashing tuple containing a list:", e)


"""
---------------------------------------------------------------------
5. TUPLES ARE "SHALLOW" IMMUTABLE  ⭐⭐
---------------------------------------------------------------------
"Immutable" means you cannot REASSIGN an element or resize the
tuple - but if an element is itself a mutable object, THAT object
can still be changed in place. Immutability applies to the tuple's
structure (which pointers it holds), not necessarily to everything
reachable through those pointers.
---------------------------------------------------------------------
"""

print("\n--- Tuples are Shallowly Immutable ---")

t = (1, 2, [3, 4])
print("tuple before:", t)
t[2].append(5)                # allowed - mutating the inner LIST
print("tuple after mutating inner list:", t)

try:
    t[2] = [9, 9]              # NOT allowed - can't reassign a slot
except TypeError as e:
    print("Error reassigning a tuple slot:", e)


"""
---------------------------------------------------------------------
6. PERFORMANCE: TUPLES vs LISTS FOR FIXED DATA  ⭐⭐
---------------------------------------------------------------------
Because tuples have simpler memory management (no growth tracking,
no need to support in-place resizing), CPython can construct and
access them slightly faster than equivalent lists for fixed,
unchanging data - especially noticeable in tight loops.
---------------------------------------------------------------------
"""

print("\n--- Performance: Tuple vs List Creation ---")

start = time.perf_counter()
for _ in range(1_000_000):
    x = (1, 2, 3, 4, 5)
tuple_time = time.perf_counter() - start

start = time.perf_counter()
for _ in range(1_000_000):
    y = [1, 2, 3, 4, 5]
list_time = time.perf_counter() - start

print(f"tuple literal creation: {tuple_time:.5f} sec")
print(f"list literal creation:  {list_time:.5f} sec  (usually slower)")


"""
=====================================================================
PART B: OPERATIONS ON TUPLES
=====================================================================
"""

"""
---------------------------------------------------------------------
7. CREATING TUPLES  ⭐
---------------------------------------------------------------------
"""

print("\n--- Creating Tuples ---")

empty = ()
single = (5,)                    # comma REQUIRED - (5) is just an int!
not_a_tuple = (5)
literal = (1, 2, 3)
without_parens = 1, 2, 3          # parentheses are optional!
from_list = tuple([1, 2, 3])
from_string = tuple("abc")

print("empty:", empty)
print("single-element tuple (5,):", single, "| type:", type(single))
print("(5) without comma is NOT a tuple:", not_a_tuple, "| type:", type(not_a_tuple))
print("literal:", literal)
print("without parens (still a tuple!):", without_parens, "| type:", type(without_parens))
print("from list:", from_list)
print("from string:", from_string)


"""
---------------------------------------------------------------------
8. ACCESSING & SLICING  ⭐⭐
---------------------------------------------------------------------
Identical semantics to list indexing/slicing - but slicing a tuple
returns a NEW TUPLE, not a list.
---------------------------------------------------------------------
"""

print("\n--- Accessing & Slicing ---")

t = (10, 20, 30, 40, 50)

print("t[0]:", t[0])
print("t[-1]:", t[-1])
print("t[1:4]:", t[1:4])           # returns a tuple, not a list
print("t[::-1]:", t[::-1])         # reversed copy
print("type of a slice:", type(t[1:4]))


"""
---------------------------------------------------------------------
9. IMMUTABILITY IN ACTION: WHAT'S NOT ALLOWED  ⭐⭐⭐
---------------------------------------------------------------------
No append, insert, remove, pop, sort, reverse, or item assignment -
tuples have almost NONE of a list's mutating methods.
---------------------------------------------------------------------
"""

print("\n--- Immutability: What's Not Allowed ---")

t = (1, 2, 3)

for bad_op, desc in [
    (lambda: t.append(4), "append()"),
    (lambda: t.remove(1), "remove()"),
    (lambda: t.__setitem__(0, 99), "item assignment"),
]:
    try:
        bad_op()
    except (AttributeError, TypeError) as e:
        print(f"Error calling {desc}: {e}")


"""
---------------------------------------------------------------------
10. THE ONLY TWO TUPLE METHODS  ⭐⭐
---------------------------------------------------------------------
Because tuples are immutable, they only have TWO built-in methods
(vastly fewer than a list's ~11 methods):

    count(x)  -> number of times x appears
    index(x)  -> index of the FIRST occurrence of x
---------------------------------------------------------------------
"""

print("\n--- The Only Two Tuple Methods ---")

t = (1, 2, 2, 3, 2, 4)
print("count(2):", t.count(2))
print("index(2):", t.index(2))               # first occurrence only
print("index(2, 2):", t.index(2, 2))          # search starting at index 2


"""
---------------------------------------------------------------------
11. CONCATENATION & REPETITION  ⭐
---------------------------------------------------------------------
+   -> creates a NEW tuple by joining two tuples
*   -> creates a NEW tuple by repeating elements
(Both always create fresh tuples - never modify in place, since
that's impossible for an immutable type.)
---------------------------------------------------------------------
"""

print("\n--- Concatenation & Repetition ---")

t1 = (1, 2, 3)
t2 = (4, 5, 6)

print("t1 + t2:", t1 + t2)
print("t1 * 3:", t1 * 3)


"""
---------------------------------------------------------------------
12. UNPACKING  ⭐⭐⭐
---------------------------------------------------------------------
Tuple unpacking is used EVERYWHERE in Python - function returns,
for-loops over pairs, swapping variables, etc.
---------------------------------------------------------------------
"""

print("\n--- Unpacking ---")

point = (3, 7)
x, y = point                     # classic tuple unpacking
print("x:", x, "| y:", y)

a, b = 1, 2
a, b = b, a                       # swap without a temp variable -
print("swapped: a =", a, ", b =", b)   # works because the RIGHT side
                                         # builds a tuple (b, a) FIRST,
                                         # then unpacks it into a, b

# Star unpacking - capture "the rest" into a list
first, *middle, last = (1, 2, 3, 4, 5)
print("first:", first, "| middle:", middle, "| last:", last)

# Unpacking in a for-loop - extremely common with zip() or
# dict.items(), both of which yield tuples
pairs = [(1, "a"), (2, "b"), (3, "c")]
print("\nunpacking tuples in a for-loop:")
for number, letter in pairs:
    print(f"  {number} -> {letter}")


"""
---------------------------------------------------------------------
13. NAMEDTUPLE: SELF-DOCUMENTING TUPLES  ⭐⭐
---------------------------------------------------------------------
collections.namedtuple() creates a tuple subclass where elements can
be accessed by NAME as well as by index - giving you the memory
efficiency and immutability of a tuple with the readability of a
class/dict.
---------------------------------------------------------------------
"""

print("\n--- namedtuple ---")

from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])
p = Point(3, 7)

print("p:", p)
print("access by name: p.x =", p.x, "| p.y =", p.y)
print("access by index: p[0] =", p[0], "| p[1] =", p[1])
print("still a tuple? isinstance(p, tuple):", isinstance(p, tuple))

try:
    p.x = 99            # namedtuples are STILL immutable
except AttributeError as e:
    print("Error mutating namedtuple:", e)


"""
---------------------------------------------------------------------
14. TUPLES AS FUNCTION RETURN VALUES  ⭐⭐
---------------------------------------------------------------------
Python functions can "return multiple values" - but under the hood
this is really just returning ONE tuple, which the caller then
unpacks.
---------------------------------------------------------------------
"""

print("\n--- Tuples as Multiple Return Values ---")

def get_min_max(numbers):
    return min(numbers), max(numbers)     # actually returns a TUPLE

result = get_min_max([4, 8, 15, 16, 23, 42])
print("returned tuple:", result, "| type:", type(result))

lo, hi = get_min_max([4, 8, 15, 16, 23, 42])   # unpacked immediately
print("unpacked: lo =", lo, ", hi =", hi)


"""
---------------------------------------------------------------------
15. AGGREGATE FUNCTIONS ON TUPLES  ⭐
---------------------------------------------------------------------
Tuples support the same aggregate built-ins as lists.
---------------------------------------------------------------------
"""

print("\n--- Aggregate Functions ---")

t = (4, 8, 15, 16, 23, 42)
print("len:", len(t))
print("sum:", sum(t))
print("min:", min(t))
print("max:", max(t))
print("sorted(t) (returns a LIST, not a tuple!):", sorted(t))


"""
---------------------------------------------------------------------
16. COPYING TUPLES  ⭐
---------------------------------------------------------------------
Since tuples are immutable, "copying" one is mostly meaningless for
top-level safety - t.copy()-style operations aren't even needed;
slicing or tuple() just returns the SAME object in CPython (a minor
optimization, since the data can never change anyway).
---------------------------------------------------------------------
"""

print("\n--- Copying Tuples (Mostly a Non-Issue) ---")

original = (1, 2, 3)
sliced_copy = original[:]
constructed_copy = tuple(original)

print("original is sliced_copy ->", original is sliced_copy)          # True! (safe optimization)
print("original is constructed_copy ->", original is constructed_copy)  # True!

print("\nThis optimization is safe ONLY because tuples are immutable -")
print("there's no risk of one 'copy' mutating and affecting the other.")

# deepcopy still matters if the tuple contains MUTABLE elements
nested = (1, [2, 3])
deep = copy.deepcopy(nested)
deep[1].append(99)
print("\noriginal nested tuple after deepcopy mutation:", nested)   # unaffected


"""
=====================================================================
QUICK PROPERTY SUMMARY
=====================================================================
    Ordered              -> Yes
    Mutable                -> No
    Allows duplicates       -> Yes
    Indexed                 -> Yes (0-based, negative indices supported)
    Hashable                 -> Yes, IF all elements are hashable
    Homogeneous required      -> No (mixed types allowed)
    Underlying storage         -> Fixed-size array of POINTERS
    Growth strategy              -> None - size is permanent
    Memory overhead                -> Lower than list (no spare capacity)
    Number of built-in methods       -> Only 2: count(), index()
    Can be a dict key / set element    -> Yes (if hashable)
=====================================================================
"""

print("\n--- Quick Property Summary (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON TUPLE
=====================================================================

MEMORY / HARDWARE-LEVEL:

1. How is a tuple stored in memory, and how does that differ
   structurally from how a list is stored?

2. Why do tuples generally use LESS memory than lists containing the
   same elements?

3. Why don't tuples need an "over-allocation" growth strategy like
   lists do?

4. Why can a tuple be used as a dictionary key, while a list cannot?
   What specific property makes something usable as a dict key?

5. If a tuple contains a mutable object (like a list), is the tuple
   still hashable? Why or why not?

6. Is a tuple "fully immutable" or only "shallowly immutable"?
   Explain with an example where you CAN modify something "inside"
   a tuple.

7. Why can tuple literals sometimes be created/accessed slightly
   faster than equivalent lists in CPython?

GENERAL / OPERATIONS:

8. Why does `(5)` NOT create a tuple, but `(5,)` does? What's the
   role of the trailing comma?

9. What are the only two built-in methods available on a tuple, and
   why does a tuple have so few methods compared to a list?

10. How does the classic "swap two variables" trick
    (`a, b = b, a`) work internally in terms of tuple packing and
    unpacking?

11. When a Python function appears to "return multiple values" (e.g.
    `return x, y`), what is it actually returning under the hood?

12. What is a `namedtuple`, and why would you choose it over a
    regular tuple or a dictionary to represent a record?

13. What does `sorted(some_tuple)` return - a tuple or a list?
    Why is that the case?

14. How would you convert a tuple to a list, modify it, and convert
    it back to a tuple? Why would you ever need to do this instead
    of just using a list from the start?

15. In a data engineering context, when would you deliberately
    choose a tuple over a list to represent a data record (e.g., a
    row fetched from a database)? What guarantees does immutability
    give you in that scenario?

16. Given `t = (1, 2, [3, 4])`, what happens when you run
    `t[2].append(5)`? Does this violate tuple immutability? Explain
    why or why not.
=====================================================================
"""