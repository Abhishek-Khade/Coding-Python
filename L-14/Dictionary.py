"""
=====================================================================
PYTHON DICT - Memory Internals, Storage, Operations & Properties
=====================================================================

A dict is an ORDERED (since 3.7+) collection of KEY-VALUE pairs,
where KEYS must be unique and hashable. Internally, a dict is a HASH
TABLE - very similar to a set, but each hash slot stores a
key-value PAIR instead of just a key.

This hash-table foundation explains every core property of dicts:
    - O(1) average lookup/insert/delete by key   - direct hash-based
                                                    addressing
    - Keys must be hashable                       - same reason as
                                                    set elements
    - No duplicate keys                            - inserting an
                                                    existing key
                                                    OVERWRITES the
                                                    value
    - Insertion order preserved (Python 3.7+)      - a separate
                                                    internal array
                                                    tracks insertion
                                                    order alongside
                                                    the hash table

This file covers: hash-table internals (including WHY modern dicts
preserve order), memory sizing, all major operations, and interview
questions.
=====================================================================
"""

import sys
import time

print("--- Overview ---")
print("A dict = a hash table of key-value pairs, ordered by")
print("insertion since Python 3.7.")


"""
=====================================================================
PART A: HARDWARE-LEVEL / MEMORY INTERNALS
=====================================================================
"""

"""
---------------------------------------------------------------------
1. HOW A DICT IS STORED IN MEMORY: HASH TABLE  ⭐⭐⭐
---------------------------------------------------------------------
For each key-value pair you insert:

    1. Python computes hash(key)
    2. That hash determines a slot in the internal hash table where
       a reference to the (key, value) entry is placed
    3. Looking up d[key] recomputes hash(key) and jumps DIRECTLY to
       the expected slot - no scanning required

This is why dict lookups are O(1) average, regardless of how many
keys the dict holds - the same mechanism that gives sets their speed.
---------------------------------------------------------------------
"""

print("\n--- Hash-Table Storage Concept ---")

person = {"name": "Claude", "role": "assistant", "team": "Anthropic"}
for key in person:
    print(f"key={key!r:10} hash={hash(key)}")


"""
---------------------------------------------------------------------
2. HOW MODERN CPYTHON DICTS PRESERVE INSERTION ORDER  ⭐⭐⭐
---------------------------------------------------------------------
Before Python 3.7, dicts (like sets) had NO guaranteed order - the
hash table alone determines slot placement, not insertion sequence.

Since 3.6 (as an implementation detail) / 3.7 (as a language
guarantee), CPython dicts use a "compact dict" design:

    - A separate, DENSE array stores the actual (key, hash, value)
      entries IN INSERTION ORDER
    - The hash table itself only stores INDICES into that dense
      array, not the entries directly

This gives dicts the best of both worlds: O(1) average hash-based
lookup AND insertion-order iteration - at a small extra memory cost
for the index table. Sets do NOT have this extra structure, which is
why sets still have no guaranteed order but dicts do.
---------------------------------------------------------------------
"""

print("\n--- Insertion Order is Preserved (Python 3.7+) ---")

d = {}
d["zebra"] = 1
d["apple"] = 2
d["mango"] = 3
print("insertion order: zebra, apple, mango")
print("iteration order:", list(d.keys()), "  <- matches insertion order!")

# Compare to a set built from the same keys - no such guarantee
s = {"zebra", "apple", "mango"}
print("\nequivalent set (no order guarantee):", s)


"""
---------------------------------------------------------------------
3. MEMORY SIZE: DICT vs SET vs LIST  ⭐⭐
---------------------------------------------------------------------
A dict stores MORE information per entry than a set (key AND value,
plus the extra insertion-order bookkeeping), so it typically uses
more memory than an equivalent set, and considerably more than a
list/tuple.
---------------------------------------------------------------------
"""

print("\n--- Memory Size: Dict vs Set vs List ---")

for n in [0, 1, 5, 10, 50]:
    d_sample = {i: i for i in range(n)}
    s_sample = set(range(n))
    l_sample = list(range(n))
    print(f"n={n:3} | dict: {sys.getsizeof(d_sample):5} bytes | "
          f"set: {sys.getsizeof(s_sample):5} bytes | "
          f"list: {sys.getsizeof(l_sample):5} bytes")


"""
---------------------------------------------------------------------
4. RESIZING: WATCHING THE HASH TABLE GROW  ⭐⭐
---------------------------------------------------------------------
Like sets, dicts over-allocate hash table slots and resize in
discrete jumps as they grow, to keep the load factor low and
lookups fast.
---------------------------------------------------------------------
"""

print("\n--- Watching a Dict's Hash Table Grow ---")

growing_dict = {}
prev_size = sys.getsizeof(growing_dict)
print(f"start: len=0, size={prev_size} bytes")

for i in range(30):
    growing_dict[i] = i
    current_size = sys.getsizeof(growing_dict)
    if current_size != prev_size:
        print(f"len={len(growing_dict):2} -> size JUMPED to "
              f"{current_size} bytes  <-- hash table resized")
        prev_size = current_size


"""
---------------------------------------------------------------------
5. WHY DICT KEYS MUST BE HASHABLE (VALUES DON'T)  ⭐⭐⭐
---------------------------------------------------------------------
Only KEYS need to be hashable, since they're what the hash table
uses for addressing. VALUES can be ANYTHING - including other
mutable objects like lists or dicts - because values are never
hashed, only stored and returned.
---------------------------------------------------------------------
"""

print("\n--- Keys Must Be Hashable, Values Can Be Anything ---")

valid_dict = {
    "name": "Claude",              # str key - fine
    (1, 2): "coordinate",          # tuple key - fine (immutable)
    "items": [1, 2, 3],            # VALUE can be a mutable list - fine!
    "nested": {"a": 1},            # VALUE can even be another dict!
}
print("valid dict with mutable VALUES:", valid_dict)

try:
    bad_dict = {[1, 2]: "value"}   # list as a KEY - fails
except TypeError as e:
    print("Error using a list as a dict KEY:", e)


"""
---------------------------------------------------------------------
6. PERFORMANCE: DICT LOOKUP vs LIST-OF-TUPLES LOOKUP  ⭐⭐⭐
---------------------------------------------------------------------
Just as with sets, this is the headline dict performance story:
O(1) average hash-based lookup vs O(n) linear search through
alternatives like a list of (key, value) tuples.
---------------------------------------------------------------------
"""

print("\n--- Performance: Dict Lookup vs Linear Search ---")

big_dict = {i: f"value_{i}" for i in range(1_000_000)}
big_list_of_pairs = list(big_dict.items())

target_key = 999_999

start = time.perf_counter()
result_dict = big_dict[target_key]
dict_time = time.perf_counter() - start

start = time.perf_counter()
result_list = next(v for k, v in big_list_of_pairs if k == target_key)
list_time = time.perf_counter() - start

print(f"dict[key] lookup:            {dict_time:.6f} sec  (O(1) avg)")
print(f"linear search list of pairs: {list_time:.6f} sec  (O(n) scan)")
print(f"dict is roughly {list_time / dict_time:.0f}x faster here")


"""
=====================================================================
PART B: OPERATIONS ON DICTS
=====================================================================
"""

"""
---------------------------------------------------------------------
7. CREATING DICTS  ⭐
---------------------------------------------------------------------
"""

print("\n--- Creating Dicts ---")

empty = {}
literal = {"a": 1, "b": 2}
from_pairs = dict([("a", 1), ("b", 2)])          # from list of tuples
from_kwargs = dict(a=1, b=2)                      # keyword arguments
from_zip = dict(zip(["a", "b", "c"], [1, 2, 3]))  # zip two lists

print("empty:", empty)
print("literal:", literal)
print("from list of pairs:", from_pairs)
print("from keyword args:", from_kwargs)
print("from zip():", from_zip)

# Dict comprehension - very common for building lookup tables
squares = {x: x ** 2 for x in range(1, 6)}
print("dict comprehension:", squares)


"""
---------------------------------------------------------------------
8. ACCESSING VALUES  ⭐⭐⭐
---------------------------------------------------------------------
d[key]         -> raises KeyError if the key doesn't exist
d.get(key)     -> returns None (or a default) if missing - NO error
d.setdefault() -> returns existing value, OR inserts a default AND
                  returns it, in a single operation
---------------------------------------------------------------------
"""

print("\n--- Accessing Values ---")

config = {"timeout": 30, "retries": 3}

print("config['timeout']:", config["timeout"])

try:
    config["missing_key"]
except KeyError as e:
    print("Error accessing missing key with []:", e)

print("config.get('missing_key'):", config.get("missing_key"))          # None, no error
print("config.get('missing_key', 'DEFAULT'):", config.get("missing_key", "DEFAULT"))

# setdefault(): get existing, or insert+return a default - useful for
# "initialize on first use" patterns
value = config.setdefault("max_conn", 100)     # not present -> inserted
print("\nsetdefault('max_conn', 100):", value)
print("config now:", config)

value2 = config.setdefault("timeout", 999)      # already present -> unchanged
print("setdefault('timeout', 999) (already exists):", value2)


"""
---------------------------------------------------------------------
9. ADDING / UPDATING VALUES  ⭐⭐
---------------------------------------------------------------------
d[key] = value  -> adds a new key OR overwrites an existing one
update()        -> merges another dict (or iterable of pairs) in,
                    overwriting on key conflicts
| (merge, 3.9+) -> creates a NEW merged dict without mutating either
|= (3.9+)       -> in-place merge
---------------------------------------------------------------------
"""

print("\n--- Adding / Updating Values ---")

d = {"a": 1, "b": 2}
d["c"] = 3                      # add new key
d["a"] = 100                    # overwrite existing key
print("after direct assignment:", d)

d.update({"b": 200, "d": 4})     # merges in-place, overwrites 'b'
print("after update():", d)

# Dict union operator (Python 3.9+) - creates a NEW dict
defaults = {"timeout": 30, "retries": 3}
overrides = {"timeout": 60}
merged = defaults | overrides    # overrides wins on conflicts
print("\nmerged with | (new dict):", merged)
print("defaults unchanged:", defaults)

defaults |= overrides            # in-place merge
print("defaults after |= (in-place):", defaults)


"""
---------------------------------------------------------------------
10. REMOVING ITEMS  ⭐⭐
---------------------------------------------------------------------
del d[key]     -> removes the key, raises KeyError if missing
pop(key)       -> removes AND returns the value; can supply a default
                  to avoid KeyError
popitem()      -> removes and returns the LAST inserted (key, value)
                  pair (LIFO order, since Python 3.7+)
clear()        -> removes all items
---------------------------------------------------------------------
"""

print("\n--- Removing Items ---")

d = {"a": 1, "b": 2, "c": 3}

del d["a"]
print("after del d['a']:", d)

popped_val = d.pop("b")
print("pop('b') returns:", popped_val, "| dict now:", d)

safe_pop = d.pop("missing_key", "NOT_FOUND")   # avoids KeyError
print("pop() with default for missing key:", safe_pop)

d2 = {"x": 1, "y": 2, "z": 3}
last_item = d2.popitem()          # removes the LAST inserted pair
print("\npopitem() (removes last inserted):", last_item, "| dict now:", d2)

d2.clear()
print("after clear():", d2)


"""
---------------------------------------------------------------------
11. ITERATING OVER DICTS  ⭐⭐⭐
---------------------------------------------------------------------
Default iteration gives KEYS only. Use .keys(), .values(), .items()
explicitly for clarity and to get values or pairs.
---------------------------------------------------------------------
"""

print("\n--- Iterating Over Dicts ---")

person = {"name": "Claude", "role": "assistant", "team": "Anthropic"}

print("default iteration (keys only):")
for key in person:
    print(" ", key)

print("\n.keys():", list(person.keys()))
print(".values():", list(person.values()))
print(".items():", list(person.items()))

print("\niterating with .items():")
for key, value in person.items():
    print(f"  {key}: {value}")


"""
---------------------------------------------------------------------
12. MEMBERSHIP TESTING  ⭐⭐
---------------------------------------------------------------------
`in` checks KEYS by default, NOT values - a very common point of
confusion.
---------------------------------------------------------------------
"""

print("\n--- Membership Testing ---")

d = {"a": 1, "b": 2}

print("'a' in d (checks KEYS):", "a" in d)          # True
print("1 in d (checks KEYS, not values!):", 1 in d)   # False - 1 is a VALUE
print("1 in d.values():", 1 in d.values())            # True - correct way


"""
---------------------------------------------------------------------
13. MERGING & GROUPING PATTERNS  ⭐⭐⭐
---------------------------------------------------------------------
Very common data engineering patterns using dicts.
---------------------------------------------------------------------
"""

print("\n--- Merging & Grouping Patterns ---")

# Grouping records by a key - classic ETL pattern
transactions = [("US", 100), ("IN", 50), ("US", 75), ("IN", 20), ("UK", 30)]

grouped = {}
for country, amount in transactions:
    grouped.setdefault(country, []).append(amount)    # elegant one-liner
print("grouped by country:", grouped)

# Aggregating (summing) values per key
totals = {}
for country, amount in transactions:
    totals[country] = totals.get(country, 0) + amount
print("summed totals per country:", totals)


"""
---------------------------------------------------------------------
14. DICT COMPREHENSIONS WITH CONDITIONS  ⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Dict Comprehensions with Conditions ---")

prices = {"apple": 1.5, "banana": 0.5, "cherry": 3.0, "date": 4.5}

expensive_items = {k: v for k, v in prices.items() if v > 1.0}
print("filtered (price > 1.0):", expensive_items)

doubled_prices = {k: v * 2 for k, v in prices.items()}
print("transformed (doubled prices):", doubled_prices)

# Swapping keys and values (only safe if values are unique & hashable)
swapped = {v: k for k, v in prices.items()}
print("keys/values swapped:", swapped)


"""
---------------------------------------------------------------------
15. NESTED DICTS (COMMON WITH JSON DATA)  ⭐⭐⭐
---------------------------------------------------------------------
Most real-world API/JSON data is deeply nested dicts and lists.
Safe access with .get() chains avoids KeyError crashes.
---------------------------------------------------------------------
"""

print("\n--- Nested Dicts (JSON-like Data) ---")

api_response = {
    "user": {
        "id": 101,
        "name": "Claude",
        "address": {"city": "San Francisco", "zip": "94107"},
    },
    "status": "active",
}

print("nested access:", api_response["user"]["address"]["city"])

# Safe nested access with .get() chains - avoids crashing on missing keys
safe_value = api_response.get("user", {}).get("address", {}).get("country", "N/A")
print("safe .get() chain for missing key:", safe_value)


"""
=====================================================================
QUICK PROPERTY SUMMARY
=====================================================================
    Ordered                -> Yes (insertion order, Python 3.7+)
    Mutable                  -> Yes
    Duplicate keys allowed     -> No (last assignment wins)
    Duplicate values allowed    -> Yes
    Indexed                      -> By key, not by position
    Keys must be hashable          -> Yes
    Values can be anything           -> Yes, including mutable objects
    Underlying storage                 -> Hash table + dense insertion-
                                        ordered entry array (3.7+)
    Lookup/insert/delete complexity      -> O(1) average, O(n) worst case
    Memory overhead                        -> Higher than set (stores
                                        keys AND values AND order info)
=====================================================================
"""

print("\n--- Quick Property Summary (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON DICT
=====================================================================

MEMORY / HARDWARE-LEVEL:

1. How is a dict implemented internally in CPython? How does its
   storage differ from a set's, given both are hash tables?

2. Why did dicts NOT guarantee insertion order before Python 3.7,
   and what internal structural change made ordering possible?

3. Why is a dict's memory footprint generally larger than an
   equivalent set's, even though both are hash tables?

4. Why must dict KEYS be hashable, but dict VALUES can be any type,
   including mutable ones like lists?

5. Why is `d[key]` lookup O(1) on average, and under what
   circumstances could it degrade toward O(n) in the worst case?
   (Hint: many hash collisions.)

GENERAL / OPERATIONS:

6. What's the difference between `d[key]` and `d.get(key)` when the
   key doesn't exist? Which one is safer to use, and when would you
   still prefer `d[key]`?

7. What does `setdefault()` do, and how is it different from just
   checking `if key not in d` and then assigning?

8. Why does `1 in my_dict` check the dict's KEYS and not its values?
   How would you check if a VALUE exists in a dict instead?

9. What's the difference between `pop(key)` and `popitem()`? Which
   one lets you specify WHICH item to remove, and which one removes
   an item automatically?

10. How would you merge two dictionaries in Python, and what
    happens if both dictionaries have a key in common? Show at
    least two different ways (update(), the `|` operator).

11. How would you group a list of (key, value) tuples into a
    dictionary of lists, without manually checking
    `if key not in dict` every time? (Hint: `setdefault()` or
    `collections.defaultdict`.)

12. Explain how you'd safely access a deeply nested value in a dict
    (e.g., from parsed JSON) without risking a `KeyError` if an
    intermediate key is missing.

13. What happens if you insert the same key into a dict literal
    twice, e.g. `{"a": 1, "a": 2}`? Which value wins?

14. Why can you swap keys and values in a dict comprehension
    (`{v: k for k, v in d.items()}`), but this could silently lose
    data if the original values aren't unique? Explain the failure
    case.

15. In a data engineering context, why is a dict often the natural
    Python representation for a single JSON record, and what are
    the performance implications of looking up fields by key versus
    scanning a list of tuples for the matching field?

16. What's the difference in behavior between `dict.fromkeys()` used
    with a MUTABLE default value (like a list) versus an immutable
    one (like 0)? Why can this cause a subtle shared-reference bug?
=====================================================================
"""