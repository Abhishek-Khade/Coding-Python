"""
=====================================================================
'is' vs '==' IN PYTHON - Complete Notes with Executable Examples
=====================================================================

Both operators compare two things, but they check FUNDAMENTALLY
DIFFERENT properties:

    ==   VALUE equality    -> "Do these two objects have the same
                               DATA/CONTENT?"
                               Calls the object's __eq__() method.

    is   IDENTITY equality -> "Are these two names pointing to the
                               EXACT SAME OBJECT in memory?"
                               Equivalent to: id(a) == id(b)

Confusing these two is one of the most common sources of subtle
bugs in Python code, and one of the most frequently asked
interview questions.
=====================================================================
"""

print("--- Overview ---")
print("== compares VALUES.  is compares IDENTITY (memory location).")


"""
---------------------------------------------------------------------
1. THE CORE DIFFERENCE, DEMONSTRATED  ⭐⭐⭐
---------------------------------------------------------------------
Two lists can have IDENTICAL content (== True) while being two
completely separate objects in memory (is False).
---------------------------------------------------------------------
"""

print("\n--- Core Difference ---")

list1 = [1, 2, 3]
list2 = [1, 2, 3]          # same VALUES, but a DIFFERENT object
list3 = list1               # list3 is the SAME object as list1

print("list1 =", list1, "| id:", id(list1))
print("list2 =", list2, "| id:", id(list2))
print("list3 =", list3, "| id:", id(list3))

print("\nlist1 == list2 ->", list1 == list2)   # True  - same VALUES
print("list1 is list2 ->", list1 is list2)     # False - different OBJECTS
print("list1 is list3 ->", list1 is list3)     # True  - same OBJECT


"""
---------------------------------------------------------------------
2. WHAT 'is' ACTUALLY CHECKS: id()  ⭐⭐
---------------------------------------------------------------------
'is' is literally just a shortcut for comparing memory addresses
via id(). If id(a) == id(b), then 'a is b' is True.
---------------------------------------------------------------------
"""

print("\n--- 'is' Checks id() Under the Hood ---")

a = [1, 2]
b = [1, 2]

print("id(a):", id(a))
print("id(b):", id(b))
print("id(a) == id(b) ->", id(a) == id(b))
print("a is b ->", a is b)     # matches id() comparison exactly


"""
---------------------------------------------------------------------
3. WHY YOU MUST USE 'is None', NOT '== None'  ⭐⭐⭐
---------------------------------------------------------------------
None is a SINGLETON - there is only ever ONE None object in the
entire program. 'is None' is:
    (a) the correct semantic check ("is this the absence-of-value
        marker?", an identity question, not a value-equality one)
    (b) faster (identity check, no __eq__ method call needed)
    (c) safer - it can't be fooled by a custom class that overrides
        __eq__() to claim it equals None
---------------------------------------------------------------------
"""

print("\n--- Why 'is None' is Correct ---")

value = None
print("value is None ->", value is None)      # Correct, Pythonic
print("value == None ->", value == None)      # Works here, but not
                                                # recommended - see below

# A class that overrides __eq__ can break '== None' comparisons
class Sneaky:
    def __eq__(self, other):
        return True     # claims to be equal to EVERYTHING, even None!

trickster = Sneaky()
print("\nSneaky() == None ->", trickster == None)   # True! misleading
print("Sneaky() is None ->", trickster is None)     # False - correct!


"""
---------------------------------------------------------------------
4. SMALL INTEGER CACHING (INTERNING)  ⭐⭐⭐
---------------------------------------------------------------------
CPython caches (pre-creates and reuses) small integers in the range
-5 to 256 as SINGLETON objects for performance. This means 'is' can
appear to "work" for value comparison on small ints - but this is
an IMPLEMENTATION DETAIL, not a guarantee, and breaks for larger
numbers or dynamically constructed values.
---------------------------------------------------------------------
"""

print("\n--- Small Integer Caching (a common trap) ---")

x = 100
y = 100
print("x = y = 100 -> x is y:", x is y)         # True (cached)

p = 300
q = 300
print("p = q = 300 -> p is y:", p is q)         # Often True too, due
                                                  # to compiler folding
                                                  # constants in the
                                                  # same code block!

# Build one value at RUNTIME (not a literal) to see the real
# uncached behavior reliably
m = 300
n = int("300")            # forces a genuinely separate object
print("m is n (runtime-built) ->", m is n)      # Usually False!

print("\n*** NEVER rely on 'is' for comparing numbers - always use == ***")


"""
---------------------------------------------------------------------
5. STRING INTERNING  ⭐⭐
---------------------------------------------------------------------
Similarly, CPython "interns" (reuses) some string literals -
especially short strings that look like identifiers - as a memory
optimization. This is ALSO an implementation detail, not something
to rely on.
---------------------------------------------------------------------
"""

print("\n--- String Interning (another trap) ---")

s1 = "hello"
s2 = "hello"
print("s1 is s2 (short literal) ->", s1 is s2)      # Often True (interned)

s3 = "hello world!"
s4 = "hello world!"
print("s3 is s4 (longer/complex literal) ->", s3 is s4)   # May be False

# Building strings dynamically at runtime defeats interning entirely
s5 = "".join(["hel", "lo"])
print("s1 is s5 (built at runtime) ->", s1 is s5)   # Usually False

print("\n*** NEVER rely on 'is' for comparing strings - always use == ***")


"""
---------------------------------------------------------------------
6. WHEN 'is' IS THE CORRECT CHOICE  ⭐⭐
---------------------------------------------------------------------
Use 'is' ONLY for identity checks against singletons:
    - None        -> if x is None
    - True/False  -> if x is True   (though "if x:" is usually better)
    - Sentinel objects you define yourself for "no value provided"
---------------------------------------------------------------------
"""

print("\n--- Correct Uses of 'is' ---")

def get_config(value=None):
    if value is None:            # correct: checking for the singleton
        return "using default config"
    return f"using provided config: {value}"

print(get_config())
print(get_config("custom"))

# Custom sentinel pattern - useful when None itself is a valid
# input value and you need a DIFFERENT "not provided" marker
_MISSING = object()      # a unique sentinel object, guaranteed unique

def get_setting(value=_MISSING):
    if value is _MISSING:
        return "no value passed at all"
    return f"value passed (even if None): {value!r}"

print(get_setting())
print(get_setting(None))       # None IS a valid, explicitly passed value


"""
---------------------------------------------------------------------
7. COMPARING CUSTOM OBJECTS  ⭐⭐
---------------------------------------------------------------------
By default, custom class instances use identity-based equality
(inherited from object) UNLESS the class overrides __eq__(). This
is why two "equal-looking" custom objects are NOT == equal unless
you explicitly define what equality means for them.
---------------------------------------------------------------------
"""

print("\n--- Comparing Custom Objects ---")

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    # No __eq__ defined - uses default identity-based comparison

p1 = Point(1, 2)
p2 = Point(1, 2)          # same x, y values, but different object
print("p1 == p2 (no __eq__ defined) ->", p1 == p2)   # False!
print("p1 is p2 ->", p1 is p2)                        # False

class PointWithEq:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __eq__(self, other):        # now == compares VALUES
        return self.x == other.x and self.y == other.y

p3 = PointWithEq(1, 2)
p4 = PointWithEq(1, 2)
print("\np3 == p4 (custom __eq__ defined) ->", p3 == p4)   # True!
print("p3 is p4 ->", p3 is p4)                              # Still False


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Use ==   -> comparing VALUES: numbers, strings, lists, dicts, custom
             objects with meaningful equality
Use is   -> comparing IDENTITY: None, True/False, sentinels, or when
             you specifically need to know "is this the SAME object"

Rule of thumb: if you're not 100% sure, use == for values, is only
for None/True/False/sentinels.
=====================================================================
"""


"""
=====================================================================
INTERVIEW QUESTIONS - 'is' vs '=='
=====================================================================

1. What is the fundamental difference between 'is' and '=='?

2. Why should you always use `if x is None:` instead of
   `if x == None:`? Give a scenario where '== None' could give a
   misleading result.

3. What does CPython's small integer caching (-5 to 256) mean for
   the 'is' operator? Why is relying on it dangerous?

4. Given:
       a = [1, 2, 3]
       b = [1, 2, 3]
   What does `a == b` return? What does `a is b` return? Explain why
   they differ.

5. What is string interning, and why might `s1 is s2` unexpectedly
   return True for two separately-created string literals with the
   same content?

6. If a custom class does not define `__eq__()`, what does `==`
   fall back to comparing? Is it the same as `is` in that case?

7. Why is 'is' generally FASTER than '==' when applicable? (Hint:
   identity comparison is a single pointer/id comparison, while
   '==' may call a potentially expensive __eq__ method.)

8. What's a "sentinel object" pattern, and why might you use
   `_MISSING = object()` instead of `None` as a default argument
   to distinguish "no argument passed" from "None was explicitly
   passed"?

9. Can two variables satisfy `a is b` but NOT `a == b`? Under what
   circumstances might that happen? (Hint: consider a class that
   overrides `__eq__` to return False even when comparing an object
   to itself - unusual, but possible.)

10. Explain why `True == 1` is True, but explain what `True is 1`
    evaluates to and why (even though bool is a subclass of int).

11. In a data engineering context, why might using 'is' instead of
    '==' to compare two DataFrame column values or two Pandas Series
    lead to unexpected/incorrect results?

12. What does Python do internally when you write `a is b`? Is it
    equivalent to any other expression you could write yourself?
=====================================================================
"""