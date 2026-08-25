"""
=====================================================================
PYTHON SET - Memory Internals, Storage, Operations & Properties
=====================================================================

A set is an UNORDERED collection of UNIQUE, HASHABLE elements.
Unlike list/tuple (which store pointers in a simple array), a set is
internally implemented as a HASH TABLE - the same underlying
structure as a dict, but storing only "keys" with no associated
values.

This hash-table foundation is THE reason for every major property
of sets:
    - O(1) average membership testing (`in`)      - no linear scan
    - No duplicate elements allowed                - hash collision
                                                      on equal values
    - No guaranteed ordering                        - position is
                                                      determined by
                                                      hash, not
                                                      insertion order
    - Elements MUST be hashable                     - can't put a
                                                      list inside a
                                                      set

This file covers: hash-table internals, memory sizing, all major
operations (including set algebra), and interview questions.
=====================================================================
"""

import sys
import time

print("--- Overview ---")
print("A set = a hash table storing unique, hashable elements.")
print("Internally similar to a dict with only keys, no values.")


"""
=====================================================================
PART A: HARDWARE-LEVEL / MEMORY INTERNALS
=====================================================================
"""

"""
---------------------------------------------------------------------
1. HOW A SET IS STORED IN MEMORY: HASH TABLE  ⭐⭐⭐
---------------------------------------------------------------------
A set does NOT store elements in a simple sequential array like a
list/tuple. Instead, it maintains an internal array of "hash slots."
When you add an element:

    1. Python computes hash(element)
    2. That hash value is used to determine which SLOT in the
       internal table the element (or a pointer to it) is placed in
    3. To check membership (`x in my_set`), Python computes
       hash(x) and jumps DIRECTLY to the expected slot - no need to
       scan every element like a list would

This is why sets give average O(1) membership testing, regardless
of how many elements they contain - a fundamentally different
mechanism from a list's linear O(n) scan.
---------------------------------------------------------------------
"""

print("\n--- Hash-Table Storage Concept ---")

sample_set = {"apple", "banana", "cherry"}
for item in sample_set:
    print(f"'{item}' -> hash: {hash(item)}")

print("\nNote: iteration order is NOT the insertion order - it")
print("depends on where each hash value landed in the internal table.")


"""
---------------------------------------------------------------------
2. WHY SETS HAVE NO GUARANTEED ORDER  ⭐⭐⭐
---------------------------------------------------------------------
A list preserves order because it's a simple sequential array. A
set's internal position for an element is determined by that
element's HASH VALUE modulo the table size - NOT by when it was
inserted. This is why iterating over a set can produce elements in
a seemingly "random" (but actually hash-determined) order.
---------------------------------------------------------------------
"""

print("\n--- No Guaranteed Order ---")

insertion_order = ["zebra", "apple", "mango", "banana"]
s = set(insertion_order)
print("inserted in this order:", insertion_order)
print("set iteration order:", list(s), "  <- NOT necessarily the same")


"""
---------------------------------------------------------------------
3. MEMORY SIZE: SETS OVER-ALLOCATE MORE THAN LISTS  ⭐⭐
---------------------------------------------------------------------
A hash table needs "breathing room" (empty slots) to keep collisions
low and lookups fast. CPython keeps a set's load factor below a
threshold by resizing (growing) the internal table well before it
gets full. This means sets typically use MORE memory per element
than an equivalent list or tuple - the trade-off for O(1) lookups.
---------------------------------------------------------------------
"""

print("\n--- Memory Size: Set vs List vs Tuple ---")

for n in [0, 1, 5, 10, 50]:
    values = list(range(n))
    set_size = sys.getsizeof(set(values))
    list_size = sys.getsizeof(list(values))
    print(f"n={n:3} | set: {set_size:5} bytes | list: {list_size:5} bytes")

print("\nSets generally cost more memory per element than lists -")
print("that's the price paid for O(1) average membership testing.")


"""
---------------------------------------------------------------------
4. RESIZING: WATCHING THE HASH TABLE GROW  ⭐⭐
---------------------------------------------------------------------
Just like a list's over-allocation, a set's internal hash table
resizes in jumps as more elements are added - visible via
sys.getsizeof() growing in discrete steps, not linearly.
---------------------------------------------------------------------
"""

print("\n--- Watching a Set's Hash Table Grow ---")

growing_set = set()
prev_size = sys.getsizeof(growing_set)
print(f"start: len=0, size={prev_size} bytes")

for i in range(30):
    growing_set.add(i)
    current_size = sys.getsizeof(growing_set)
    if current_size != prev_size:
        print(f"len={len(growing_set):2} -> size JUMPED to "
              f"{current_size} bytes  <-- hash table resized")
        prev_size = current_size


"""
---------------------------------------------------------------------
5. WHY ELEMENTS MUST BE HASHABLE  ⭐⭐⭐
---------------------------------------------------------------------
Since the hash table relies entirely on hash(element) to decide
where to place/find an item, any UNHASHABLE object (like a list or
dict, which are mutable) simply cannot be used - there's no stable
address to compute or look up.
---------------------------------------------------------------------
"""

print("\n--- Hashability Requirement ---")

valid_set = {1, "two", (3, 4), 5.0}     # int, str, tuple, float - all hashable
print("valid set with mixed hashable types:", valid_set)

try:
    bad_set = {1, 2, [3, 4]}            # list is unhashable
except TypeError as e:
    print("Error adding a list to a set:", e)

try:
    bad_set2 = {1, 2, {3: 4}}           # dict is unhashable
except TypeError as e:
    print("Error adding a dict to a set:", e)


"""
---------------------------------------------------------------------
6. PERFORMANCE: SET vs LIST MEMBERSHIP TESTING  ⭐⭐⭐
---------------------------------------------------------------------
This is THE headline performance difference, and one of the most
common interview demonstrations: O(1) average (set) vs O(n) (list).
---------------------------------------------------------------------
"""

print("\n--- Performance: Membership Testing ---")

big_list = list(range(1_000_000))
big_set = set(big_list)

target = 999_999          # worst case for a list - near/at the end

start = time.perf_counter()
result_list = target in big_list
list_time = time.perf_counter() - start

start = time.perf_counter()
result_set = target in big_set
set_time = time.perf_counter() - start

print(f"'in' on list of 1,000,000:  {list_time:.6f} sec  (O(n) scan)")
print(f"'in' on set of 1,000,000:   {set_time:.6f} sec  (O(1) avg lookup)")
print(f"set is roughly {list_time / set_time:.0f}x faster here")


"""
=====================================================================
PART B: OPERATIONS ON SETS
=====================================================================
"""

"""
---------------------------------------------------------------------
7. CREATING SETS  ⭐
---------------------------------------------------------------------
Note: {} creates an EMPTY DICT, not an empty set - a classic trap!
Use set() explicitly for an empty set.
---------------------------------------------------------------------
"""

print("\n--- Creating Sets ---")

empty_set = set()                 # correct way to make an empty set
not_a_set = {}                    # this is an EMPTY DICT, not a set!
literal = {1, 2, 3}
from_list = set([1, 2, 2, 3, 3])   # duplicates auto-removed
from_string = set("hello")         # unique characters only

print("empty_set:", empty_set, "| type:", type(empty_set))
print("{} is actually a:", type(not_a_set))
print("literal:", literal)
print("from_list (dupes removed):", from_list)
print("from_string (unique chars):", from_string)


"""
---------------------------------------------------------------------
8. ADDING ELEMENTS  ⭐⭐
---------------------------------------------------------------------
add(x)      -> adds a SINGLE element                    O(1) average
update(iter)-> adds ALL elements from an iterable         O(k)
---------------------------------------------------------------------
"""

print("\n--- Adding Elements ---")

fruits = {"apple", "banana"}
fruits.add("cherry")
print("after add('cherry'):", fruits)

fruits.add("apple")             # adding a duplicate - silently ignored
print("after re-adding 'apple' (no-op):", fruits)

fruits.update(["date", "fig", "banana"])   # merges, dedupes automatically
print("after update():", fruits)


"""
---------------------------------------------------------------------
9. REMOVING ELEMENTS  ⭐⭐⭐
---------------------------------------------------------------------
remove(x)   -> removes x, raises KeyError if NOT present
discard(x)  -> removes x if present, does NOTHING if not (no error)
pop()       -> removes and returns an ARBITRARY element (sets have
               no defined order, so you can't control what's popped)
clear()     -> removes all elements
---------------------------------------------------------------------
"""

print("\n--- Removing Elements ---")

nums = {10, 20, 30, 40}

nums.remove(20)
print("after remove(20):", nums)

try:
    nums.remove(999)            # not present -> KeyError
except KeyError as e:
    print("Error removing missing value with remove():", e)

nums.discard(999)               # not present -> no error, silently ignored
print("discard(999) on missing value: no error, set unchanged:", nums)

popped = nums.pop()             # removes an ARBITRARY element
print("popped (arbitrary element):", popped, "| set now:", nums)

nums.clear()
print("after clear():", nums)


"""
---------------------------------------------------------------------
10. SET ALGEBRA: UNION, INTERSECTION, DIFFERENCE  ⭐⭐⭐
---------------------------------------------------------------------
This is where sets truly shine for data engineering - comparing
datasets, deduplicating, and reconciling records.

    union()               |    -> all elements from both sets
    intersection()        &    -> elements in BOTH sets
    difference()          -    -> elements in the first but NOT
                                  the second
    symmetric_difference() ^    -> elements in EITHER set, but NOT
                                  in both
---------------------------------------------------------------------
"""

print("\n--- Set Algebra ---")

source_table = {"A", "B", "C", "D"}
target_table = {"C", "D", "E", "F"}

print("source_table:", source_table)
print("target_table:", target_table)

print("\nunion (all records, either table):",
      source_table.union(target_table))
print("using | operator:", source_table | target_table)

print("\nintersection (records in BOTH tables):",
      source_table.intersection(target_table))
print("using & operator:", source_table & target_table)

print("\ndifference (in source, NOT in target - i.e. 'missing from target'):",
      source_table.difference(target_table))
print("using - operator:", source_table - target_table)

print("\nreverse difference (in target, NOT in source - 'extra in target'):",
      target_table - source_table)

print("\nsymmetric difference (records that DON'T match on either side):",
      source_table.symmetric_difference(target_table))
print("using ^ operator:", source_table ^ target_table)


"""
---------------------------------------------------------------------
11. IN-PLACE SET ALGEBRA (MUTATING VERSIONS)  ⭐⭐
---------------------------------------------------------------------
Each set-algebra operation has an IN-PLACE counterpart that mutates
the set it's called on, rather than returning a new set.

    update()                     |=   -> in-place union
    intersection_update()        &=   -> in-place intersection
    difference_update()          -=   -> in-place difference
    symmetric_difference_update() ^=   -> in-place symmetric difference
---------------------------------------------------------------------
"""

print("\n--- In-Place Set Algebra ---")

working_set = {"A", "B", "C", "D"}
other_set = {"C", "D", "E"}

working_set &= other_set        # in-place intersection
print("after &= (in-place intersection):", working_set)


"""
---------------------------------------------------------------------
12. SUBSET, SUPERSET, DISJOINT CHECKS  ⭐⭐
---------------------------------------------------------------------
issubset()     <=   -> True if EVERY element of this set is in another
issuperset()   >=   -> True if this set contains ALL of another's elements
isdisjoint()        -> True if the two sets share NO elements at all
< / >               -> "proper" subset/superset (must NOT be equal)
---------------------------------------------------------------------
"""

print("\n--- Subset, Superset, Disjoint ---")

small = {1, 2}
big = {1, 2, 3, 4}
unrelated = {99, 100}

print("small.issubset(big):", small.issubset(big))
print("small <= big:", small <= big)
print("big.issuperset(small):", big.issuperset(small))
print("small.isdisjoint(unrelated):", small.isdisjoint(unrelated))
print("small.isdisjoint(big):", small.isdisjoint(big))

# Proper subset: subset AND not equal
print("small < big (proper subset):", small < big)
print("big < big (proper subset of itself? False):", big < big)


"""
---------------------------------------------------------------------
13. MEMBERSHIP TESTING & AGGREGATES  ⭐
---------------------------------------------------------------------
"""

print("\n--- Membership & Aggregates ---")

values = {4, 8, 15, 16, 23, 42}
print("8 in values:", 8 in values)
print("99 in values:", 99 in values)
print("len:", len(values))
print("sum:", sum(values))
print("min:", min(values), "| max:", max(values))


"""
---------------------------------------------------------------------
14. SET COMPREHENSIONS  ⭐⭐
---------------------------------------------------------------------
Like list comprehensions, but produce a set - automatically
deduplicating results.
---------------------------------------------------------------------
"""

print("\n--- Set Comprehensions ---")

words = ["cat", "dog", "lion", "ox", "cat", "dog"]
unique_lengths = {len(w) for w in words}
print("unique word lengths:", unique_lengths)

squares_of_evens = {x ** 2 for x in range(10) if x % 2 == 0}
print("squares of even numbers:", squares_of_evens)


"""
---------------------------------------------------------------------
15. frozenset: THE IMMUTABLE, HASHABLE SET  ⭐⭐⭐
---------------------------------------------------------------------
A frozenset behaves exactly like a set for READING/algebra
operations, but cannot be modified after creation (no add/remove).
Because it's immutable, it's HASHABLE - so a frozenset can itself be
used as a dict key or placed INSIDE another set, unlike a regular
set.
---------------------------------------------------------------------
"""

print("\n--- frozenset ---")

fs = frozenset([1, 2, 3])
print("frozenset:", fs)

try:
    fs.add(4)                  # frozensets have no mutating methods
except AttributeError as e:
    print("Error mutating frozenset:", e)

# frozenset CAN be hashed - so it works as a dict key or set element
lookup = {frozenset([1, 2]): "pair A", frozenset([3, 4]): "pair B"}
print("dict keyed by frozensets:", lookup)

set_of_sets = {frozenset([1, 2]), frozenset([3, 4])}   # only frozensets allowed here
print("a set containing frozensets:", set_of_sets)

try:
    regular_set_inside = {1, 2, {3, 4}}   # a regular (mutable) set can't nest
except TypeError as e:
    print("Error putting a regular set inside a set:", e)


"""
---------------------------------------------------------------------
16. DEDUPLICATION: THE MOST COMMON REAL-WORLD USE CASE  ⭐⭐⭐
---------------------------------------------------------------------
Converting a list to a set and back is the fastest way to remove
duplicates - but it does NOT preserve original order.
---------------------------------------------------------------------
"""

print("\n--- Deduplication ---")

records = ["order1", "order2", "order1", "order3", "order2"]

deduped_unordered = list(set(records))     # fast, but order NOT preserved
print("deduped (order NOT guaranteed):", deduped_unordered)

# Order-preserving deduplication - use dict.fromkeys() (3.7+ dicts
# preserve insertion order)
deduped_ordered = list(dict.fromkeys(records))
print("deduped (order preserved):", deduped_ordered)


"""
=====================================================================
QUICK PROPERTY SUMMARY
=====================================================================
    Ordered               -> No (position determined by hash)
    Mutable                 -> Yes (set) / No (frozenset)
    Allows duplicates        -> No
    Indexed                   -> No (no positional access, no slicing)
    Hashable                   -> No (set) / Yes (frozenset)
    Homogeneous required        -> No, but elements must be hashable
    Underlying storage            -> Hash table (like a dict with no values)
    Membership test complexity      -> O(1) average, O(n) worst case
    Memory overhead                   -> Higher than list/tuple per
                                        element (hash table needs
                                        empty slots for performance)
=====================================================================
"""

print("\n--- Quick Property Summary (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON SET
=====================================================================

MEMORY / HARDWARE-LEVEL:

1. How is a set implemented internally in CPython? How does this
   differ structurally from how a list or tuple is stored?

2. Why does a set provide O(1) average time complexity for
   membership testing (`x in my_set`), while a list requires O(n)?

3. Why does a set generally use MORE memory per element than a list
   or tuple of the same size?

4. Why is the iteration order of a set NOT guaranteed to match
   insertion order? What actually determines the order elements
   appear in?

5. Why must every element placed in a set be hashable? What
   specifically would go wrong internally if you could put a
   mutable object like a list into a set?

6. What is a hash collision, and how does a hash table (and thus a
   set) handle two different elements that hash to the same slot?

GENERAL / OPERATIONS:

7. Why does writing `{}` NOT create an empty set? What's the
   correct way to create one?

8. What's the difference between `remove()` and `discard()` when
   removing an element that doesn't exist in the set?

9. What does `set.pop()` actually remove, given that a set has no
   defined order? Can you predict which element will be removed?

10. Explain the difference between `union()`, `intersection()`,
    `difference()`, and `symmetric_difference()` with a practical
    data engineering example (e.g., comparing source vs target
    tables during a reconciliation job).

11. What's the difference between `intersection()` (returns a new
    set) and `intersection_update()` / `&=` (mutates in place)?

12. What is a `frozenset`, and why is it hashable when a regular
    `set` is not? Give an example of when you'd need to put a set
    inside another set or use one as a dict key.

13. How would you deduplicate a list of items while PRESERVING their
    original order? Why doesn't simply converting to a `set` and
    back achieve this?

14. What's the difference between `issubset()` (`<=`) and a "proper
    subset" check (`<`)? When would they give different results for
    two equal sets?

15. In a real ETL/data reconciliation scenario, how would you use
    set operations to find: (a) records that exist in the source but
    are missing from the target, and (b) records that exist in the
    target but shouldn't be there (i.e., not in the source)?

16. Why can't you use a regular `list` comprehension syntax to build
    a set (`[x for x in ...]`), and what syntax do you use instead
    for a set comprehension?
=====================================================================
"""