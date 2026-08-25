"""
=====================================================================
PYTHON STRING - Memory Internals, Storage, Operations & Properties
=====================================================================

A string is an IMMUTABLE, ORDERED sequence of Unicode characters.
Unlike list/tuple/set/dict, a string does NOT store pointers to
separate objects for each character - it stores the actual character
DATA inline, in a single contiguous memory block. This makes strings
structurally closer to a NumPy array than to a list.

Key memory-level facts covered in this file:
    - Strings use a "flexible" internal representation - CPython
      picks the SMALLEST fixed-width encoding that fits all
      characters in the string (1, 2, or 4 bytes per character)
    - Strings are immutable - every "modification" creates a new
      string object
    - CPython "interns" (reuses) certain strings as a memory/speed
      optimization
    - Strings are hashable (since immutable), so they can be dict
      keys and set elements

This file covers: memory-level storage, properties, all major
operations, and interview questions.
=====================================================================
"""

import sys
import time

print("--- Overview ---")
print("A string stores character DATA inline, contiguously -")
print("unlike lists/tuples, which store pointers to other objects.")


"""
=====================================================================
PART A: HARDWARE-LEVEL / MEMORY INTERNALS
=====================================================================
"""

"""
---------------------------------------------------------------------
1. HOW A STRING IS STORED IN MEMORY: INLINE CHARACTER DATA  ⭐⭐⭐
---------------------------------------------------------------------
Unlike a list `[65, 66, 67]` (which stores 3 POINTERS to 3 separate
int objects), a string "ABC" stores its character data DIRECTLY,
contiguously, inside the string object itself - much like a C array
of characters.

    list [65, 66, 67]:      [ptr]->65   [ptr]->66   [ptr]->67
                             (3 separate heap objects elsewhere)

    string "ABC":            [ 'A' | 'B' | 'C' ]
                             (data lives INLINE, in one block)

This is why strings are far more memory-efficient PER CHARACTER than
a list of individual characters would be.
---------------------------------------------------------------------
"""

print("\n--- Inline Storage vs Pointer-Based Storage ---")

s = "ABC"
list_of_chars = ['A', 'B', 'C']       # each char is its OWN string object

print(f"'ABC' (str) size:              {sys.getsizeof(s)} bytes")
print(f"['A','B','C'] (list) size:      {sys.getsizeof(list_of_chars)} bytes "
      f"(container only, excludes the 3 separate char objects)")

total_list_char_size = sum(sys.getsizeof(c) for c in list_of_chars)
print(f"  + actual char objects' size:  {total_list_char_size} bytes")
print(f"  = TRUE total for list version: "
      f"{sys.getsizeof(list_of_chars) + total_list_char_size} bytes")
print("\nThe string is dramatically more compact for the same data.")


"""
---------------------------------------------------------------------
2. FLEXIBLE STRING REPRESENTATION: 1, 2, or 4 BYTES PER CHAR  ⭐⭐⭐
---------------------------------------------------------------------
Since Python 3.3 (PEP 393), CPython does NOT always use a fixed
number of bytes per character. Instead, it inspects the string's
content and picks the SMALLEST representation that fits every
character:

    Latin-1 (1 byte/char)  -> if ALL characters fit in code points
                              0-255 (e.g., plain ASCII/Latin text)
    UCS-2   (2 bytes/char)  -> if the widest character needs up to
                              65,535 (covers most non-ASCII scripts)
    UCS-4   (4 bytes/char)  -> if ANY character needs a wider code
                              point (e.g., emoji, rare scripts)

This means a purely ASCII string uses LESS memory per character than
a string containing even ONE emoji or rare Unicode character -
because the ENTIRE string upgrades to a wider representation.
---------------------------------------------------------------------
"""

print("\n--- Flexible String Representation (PEP 393) ---")

ascii_str = "hello"                 # all chars fit in 1 byte (Latin-1)
accented_str = "héllo"               # 'é' needs 2 bytes -> whole string widens
emoji_str = "hello🚀"                 # emoji needs 4 bytes -> whole string widens

print(f"'{ascii_str}'   (pure ASCII):        {sys.getsizeof(ascii_str)} bytes")
print(f"'{accented_str}'   (has an accented char): {sys.getsizeof(accented_str)} bytes")
print(f"'{emoji_str}' (has an emoji):        {sys.getsizeof(emoji_str)} bytes")

print("\nNotice: adding ONE 'wide' character increases the memory")
print("cost of EVERY character in the string, not just that one -")
print("because the whole string switches to the wider representation.")


"""
---------------------------------------------------------------------
3. STRINGS ARE IMMUTABLE: PROVING IT WITH id()  ⭐⭐⭐
---------------------------------------------------------------------
Since character data lives inline, resizing a string in place would
require reallocating and shifting the ENTIRE block - so CPython
never even attempts it. ANY "modification" always creates a
brand-new string object at a NEW memory address.
---------------------------------------------------------------------
"""

print("\n--- Immutability: Proving it with id() ---")

s = "hello"
print("s =", s, "| id:", id(s))

s += " world"          # does NOT modify in place - builds a NEW string
print("s =", s, "| id:", id(s), "  <-- DIFFERENT id, new object created")

try:
    s[0] = "H"          # item assignment is disallowed entirely
except TypeError as e:
    print("Error mutating a string in place:", e)


"""
---------------------------------------------------------------------
4. STRING INTERNING: REUSING IDENTICAL STRINGS  ⭐⭐⭐
---------------------------------------------------------------------
As a memory/performance optimization, CPython "interns" certain
strings - meaning it reuses the SAME object for identical string
values instead of creating duplicates. This happens automatically
for:
    - String literals that LOOK like identifiers (letters, digits,
      underscores only) and are reasonably short
    - All single-character strings
    - Strings the compiler can determine at compile time (constant
      folding)

This is an IMPLEMENTATION DETAIL, not a language guarantee - never
rely on 'is' for string comparison; always use '=='.
---------------------------------------------------------------------
"""

print("\n--- String Interning ---")

a = "hello"
b = "hello"
print("a is b (identifier-like literal) ->", a is b)     # often True (interned)

c = "hello world!"          # contains a space/punctuation - may not intern
d = "hello world!"
print("c is d (string with punctuation) ->", c is d)      # implementation-dependent

# Strings BUILT at runtime (not literals) generally are NOT interned
e = "".join(["hel", "lo"])
print("a is e (built at runtime) ->", a is e)               # usually False

# You can force interning manually with sys.intern() if needed for
# performance-critical code with many repeated string comparisons
import sys as sys_module
f = sys_module.intern("hello_forced")
g = sys_module.intern("hello_forced")
print("manually interned strings, f is g ->", f is g)        # guaranteed True

print("\n*** ALWAYS use '==' for string value comparison, never 'is' ***")


"""
---------------------------------------------------------------------
5. HASHABILITY: WHY STRINGS CAN BE DICT KEYS  ⭐⭐
---------------------------------------------------------------------
Because strings are immutable, their hash value is stable for their
entire lifetime - making them hashable, and therefore usable as
dict keys and set elements (the most common dict key type in
practice).
---------------------------------------------------------------------
"""

print("\n--- Hashability ---")

d = {"name": "Claude", "role": "assistant"}
print("dict with string keys:", d)
print("hash('name'):", hash("name"))


"""
---------------------------------------------------------------------
6. CONCATENATION COST: WHY '+' IN A LOOP IS EXPENSIVE  ⭐⭐⭐
---------------------------------------------------------------------
Since strings are immutable and stored inline, EVERY '+=' in a loop
allocates a brand-new block and copies ALL prior characters into it.
For n concatenations, this is O(n) per step -> O(n^2) total.
''.join() avoids this by computing the total size ONCE and copying
each piece exactly once -> O(n) total.
---------------------------------------------------------------------
"""

print("\n--- Concatenation Cost: += vs join() ---")

parts = [f"word{i}" for i in range(20_000)]

start = time.perf_counter()
result_plus = ""
for p in parts:
    result_plus += p          # O(n) reallocation+copy on EVERY iteration
plus_time = time.perf_counter() - start

start = time.perf_counter()
result_join = "".join(parts)   # single allocation, single copy pass
join_time = time.perf_counter() - start

print(f"'+=' in a loop:  {plus_time:.5f} sec  (O(n^2) overall)")
print(f"''.join():       {join_time:.5f} sec  (O(n) overall - much faster)")


"""
=====================================================================
PART B: OPERATIONS ON STRINGS
=====================================================================
(For deep coverage of formatting/f-strings/regex, see the dedicated
"String Manipulation & Formatting" notes - this section focuses on
the operations most tied to the memory model above.)
---------------------------------------------------------------------
"""

"""
---------------------------------------------------------------------
7. INDEXING & SLICING - CREATE NEW STRING OBJECTS  ⭐⭐
---------------------------------------------------------------------
Since strings are immutable, EVERY slice creates a brand-new string
object with its own freshly copied character data - there is no
"view" into the original like there might be with some array
libraries.
---------------------------------------------------------------------
"""

print("\n--- Indexing & Slicing ---")

text = "Data Engineering"

print("text[0]:", text[0])
print("text[-1]:", text[-1])
sliced = text[0:4]
print("text[0:4]:", sliced, "| id differs from original:", id(sliced) != id(text))
print("text[::-1] (reversed COPY):", text[::-1])


"""
---------------------------------------------------------------------
8. STRING CONCATENATION & REPETITION  ⭐
---------------------------------------------------------------------
+   -> creates a NEW string by joining two strings
*   -> creates a NEW string by repeating characters
Both allocate fresh memory - never mutate in place (impossible for
an immutable type).
---------------------------------------------------------------------
"""

print("\n--- Concatenation & Repetition ---")

s1 = "data"
s2 = "engineer"
print("s1 + s2:", s1 + s2)
print("'-' * 20:", "-" * 20)


"""
---------------------------------------------------------------------
9. MEMBERSHIP TESTING: SUBSTRING SEARCH  ⭐⭐
---------------------------------------------------------------------
`in` on strings checks for SUBSTRING presence, not just single
characters - implemented internally with an efficient substring
search algorithm, not a naive character-by-character scan.
---------------------------------------------------------------------
"""

print("\n--- Membership Testing (Substring Search) ---")

log = "2026-08-13 ERROR: connection timeout"
print("'ERROR' in log:", "ERROR" in log)
print("'WARNING' in log:", "WARNING" in log)


"""
---------------------------------------------------------------------
10. COMPARING STRINGS: == vs is (RECAP FROM EARLIER TOPIC)  ⭐⭐⭐
---------------------------------------------------------------------
Always compare string VALUES with ==. Comparing with 'is' relies on
interning, an implementation detail that varies across Python
versions/implementations and even runtime conditions.
---------------------------------------------------------------------
"""

print("\n--- Comparing Strings: == vs is ---")

x = "data" + "base"          # built via concatenation of literals
y = "database"

print("x == y:", x == y)     # True - always correct for VALUE comparison
print("x is y:", x is y)     # may be True OR False depending on compiler
                              # optimizations - NEVER rely on this


"""
---------------------------------------------------------------------
11. IMMUTABLE CONTAINERS OF STRINGS: TUPLES/FROZENSETS OF STRINGS
---------------------------------------------------------------------
Because strings are hashable, they combine naturally with other
immutable, hashable containers - a very common pattern for
composite keys and fixed vocabularies.
---------------------------------------------------------------------
"""

print("\n--- Strings Inside Other Immutable Structures ---")

composite_key = ("2026-08-13", "US", "electronics")
sales_lookup = {composite_key: 15000}
print("dict with a tuple-of-strings key:", sales_lookup)

valid_statuses = frozenset({"active", "pending", "closed"})
print("frozenset of strings:", valid_statuses)


"""
=====================================================================
QUICK PROPERTY SUMMARY
=====================================================================
    Ordered               -> Yes
    Mutable                 -> No
    Allows duplicate chars    -> Yes
    Indexed                    -> Yes (0-based, negative indices)
    Hashable                     -> Yes
    Underlying storage              -> Inline, contiguous character
                                      data (NOT a pointer array)
    Internal encoding                 -> Flexible: 1, 2, or 4 bytes
                                      per character (PEP 393), chosen
                                      per-string based on content
    Growth strategy                     -> None - immutable, so no
                                      resizing; concatenation always
                                      creates a new object
    Special optimization                  -> String interning (reuse
                                      of identical literals, an
                                      implementation detail)
=====================================================================
"""

print("\n--- Quick Property Summary (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON STRING (MEMORY/HARDWARE LEVEL)
=====================================================================

1. How is a Python string stored in memory, and how is this
   FUNDAMENTALLY different from how a list stores its elements?

2. What is PEP 393's "flexible string representation," and why
   might adding a single emoji to an otherwise-ASCII string increase
   the memory used by EVERY character in that string, not just the
   emoji?

3. Why are strings immutable in Python, and what would it mean
   (from a memory layout perspective) if strings WERE mutable, given
   that their character data is stored inline?

4. What is string interning? Why can't you reliably use `is` to
   compare two strings for equality, even if they look identical?

5. Why does concatenating strings with `+=` inside a loop have
   O(n^2) time complexity overall, while `''.join()` achieves O(n)?
   Explain in terms of what happens in memory on each `+=` step.

6. Why are strings hashable, while lists are not? Connect this back
   to string immutability.

7. If a string is sliced (e.g., `s[2:5]`), does the result share
   memory with the original string, or is entirely new memory
   allocated? How does this differ from how NumPy array slicing
   sometimes works (returning a view)?

8. Why is a plain Python `str` more memory-efficient per character
   than storing the same text as a `list` of single-character
   strings?

9. In a data engineering context, if you're processing millions of
   log lines and need to build one massive combined string, why
   should you collect the lines in a list and use `''.join()` at
   the end, rather than concatenating with `+=` in the loop?

10. Why might `sys.getsizeof("hello")` differ from
    `sys.getsizeof("héllo")` even though both strings have the same
    number of characters?

11. What does `sys.intern()` do, and in what kind of performance-
    critical scenario might you use it explicitly rather than
    relying on CPython's automatic interning?

12. Why can a tuple of strings, or a frozenset of strings, safely be
    used as a dictionary key, while a list of strings cannot?

13. Does Python's substring search (`"sub" in "some string"`) scan
    character-by-character in the naive worst-case way, or does
    CPython use a more efficient algorithm under the hood? Why does
    this matter for log-parsing performance in a pipeline?
=====================================================================
"""