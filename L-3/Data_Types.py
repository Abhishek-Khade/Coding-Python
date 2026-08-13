"""
=====================================================================
PYTHON DATA TYPES - Complete Notes with Executable Examples
=====================================================================

Python has built-in data types grouped into categories:
    Numeric      -> int, float, complex
    Sequence     -> str, list, tuple, range
    Set          -> set, frozenset
    Mapping      -> dict
    Boolean      -> bool
    Binary       -> bytes, bytearray, memoryview
    None Type    -> NoneType

Every value in Python is an OBJECT, and every object has a type.
Use type() to check it, and isinstance() to test against it.
=====================================================================
"""

print("--- Checking Types ---")
print(type(10), type(10.5), type("hi"), type([1, 2]), type((1, 2)))
print(type({1, 2}), type({"a": 1}), type(True), type(None))


"""
---------------------------------------------------------------------
1. NUMERIC TYPES: int, float, complex
---------------------------------------------------------------------
- int    : whole numbers, arbitrary precision (no overflow in Python!)
- float  : decimal numbers, 64-bit double precision (can lose accuracy)
- complex: numbers with a real and imaginary part (a + bj)
---------------------------------------------------------------------
"""

print("\n--- Numeric Types ---")
whole = 42
decimal = 3.14159
complex_num = 2 + 3j

print("int:", whole, type(whole))
print("float:", decimal, type(decimal))
print("complex:", complex_num, "| real:", complex_num.real, "| imag:", complex_num.imag)

# Python ints have arbitrary precision - no integer overflow
big_number = 2 ** 100
print("2**100 =", big_number)

# Classic float precision pitfall (asked often in interviews)
print("0.1 + 0.2 =", 0.1 + 0.2)          # 0.30000000000000004, NOT 0.3
print("0.1 + 0.2 == 0.3 ->", 0.1 + 0.2 == 0.3)   # False!


"""
---------------------------------------------------------------------
2. SEQUENCE TYPES: str, list, tuple, range
---------------------------------------------------------------------
- str   : immutable sequence of Unicode characters
- list  : mutable, ordered, allows duplicates
- tuple : immutable, ordered, allows duplicates
- range : immutable sequence of numbers, memory-efficient (lazy)
---------------------------------------------------------------------
"""

print("\n--- Sequence Types ---")

# Strings are immutable - operations return NEW strings
s = "hello"
print("s =", s, "| upper:", s.upper(), "| original unchanged:", s)

# Lists are mutable - can be changed in place
lst = [1, 2, 3]
lst.append(4)
print("list after append:", lst)

# Tuples are immutable - cannot be changed after creation
tup = (1, 2, 3)
print("tuple:", tup)
try:
    tup[0] = 99          # raises TypeError
except TypeError as e:
    print("Error modifying tuple:", e)

# range() doesn't store all numbers in memory - it's lazy/generated
r = range(1, 1000000)
print("range object:", r, "| memory-efficient, not a real list")


"""
---------------------------------------------------------------------
3. SET TYPES: set, frozenset
---------------------------------------------------------------------
- set      : mutable, unordered, NO duplicates, fast membership tests
- frozenset: immutable version of a set (hashable, usable as dict key)
---------------------------------------------------------------------
"""

print("\n--- Set Types ---")

my_set = {1, 2, 2, 3, 3, 3}     # duplicates automatically removed
print("set (duplicates removed):", my_set)

frozen = frozenset([1, 2, 3])
print("frozenset:", frozen)

# Sets are great for fast membership checks: O(1) average vs O(n) for lists
print("3 in my_set ->", 3 in my_set)


"""
---------------------------------------------------------------------
4. MAPPING TYPE: dict
---------------------------------------------------------------------
- dict: mutable, ordered (Python 3.7+), key-value pairs
- Keys must be hashable (immutable): str, int, tuple - NOT list/dict
---------------------------------------------------------------------
"""

print("\n--- Mapping Type: dict ---")

d = {"name": "Claude", "role": "assistant"}
d["team"] = "Anthropic"        # add new key
print("dict:", d)

try:
    bad_dict = {[1, 2]: "value"}   # list is unhashable -> TypeError
except TypeError as e:
    print("Error using list as dict key:", e)


"""
---------------------------------------------------------------------
5. BOOLEAN TYPE: bool
---------------------------------------------------------------------
bool is actually a SUBCLASS of int in Python.
True == 1 and False == 0 under the hood.
---------------------------------------------------------------------
"""

print("\n--- Boolean Type ---")
print("True + True =", True + True)          # 2  (bool behaves like int)
print("isinstance(True, int) ->", isinstance(True, int))   # True


"""
---------------------------------------------------------------------
6. BINARY TYPES: bytes, bytearray, memoryview
---------------------------------------------------------------------
- bytes     : immutable sequence of raw bytes (e.g., file/network data)
- bytearray : mutable version of bytes
- memoryview: view into another object's memory without copying
---------------------------------------------------------------------
"""

print("\n--- Binary Types ---")
b = bytes([65, 66, 67])
print("bytes:", b, "| decoded:", b.decode())

ba = bytearray([65, 66, 67])
ba[0] = 90                 # mutable, unlike bytes
print("bytearray after mutation:", ba, "| decoded:", ba.decode())


"""
---------------------------------------------------------------------
7. NoneType
---------------------------------------------------------------------
None represents the absence of a value. It is a singleton -
there is only ONE None object in memory, so always compare with
'is None', not '== None'.
---------------------------------------------------------------------
"""

print("\n--- NoneType ---")
value = None
print("value is None ->", value is None)


"""
---------------------------------------------------------------------
8. TYPE CONVERSION (CASTING)
---------------------------------------------------------------------
Implicit  -> Python automatically converts types (e.g., int -> float
             in mixed arithmetic) without data loss.
Explicit  -> You manually convert using int(), float(), str(), etc.
             This can lose data (e.g., float -> int truncates).
---------------------------------------------------------------------
"""

print("\n--- Type Conversion ---")

# Implicit conversion
result = 5 + 2.0          # int automatically becomes float
print("5 + 2.0 =", result, "| type:", type(result))

# Explicit conversion (data can be lost)
truncated = int(9.99)     # truncates, does NOT round
print("int(9.99) =", truncated)      # 9, not 10

rounded = round(9.99)
print("round(9.99) =", rounded)      # 10


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON DATA TYPES
=====================================================================

1. What is the difference between a list and a tuple, and why are
   tuples faster and hashable while lists are not?

2. Why can't a list be used as a dictionary key, but a tuple can?
   -> Because dict keys must be hashable, and hashability requires
      immutability. Lists are mutable, so Python disallows them.

3. Why does 0.1 + 0.2 not equal 0.3 in Python?
   -> Floats are stored in binary (IEEE 754 double precision), and
      0.1/0.2 cannot be represented exactly in binary, causing tiny
      rounding errors.

4. Explain why bool is a subclass of int in Python. What does
   True + True evaluate to, and why?

5. What's the difference between 'is None' and '== None', and why
   is 'is None' the recommended way to check for None?

6. What is the difference between bytes and bytearray?

7. How would you remove duplicates from a list while preserving
   order? (Hint: dict.fromkeys() or a loop with a seen-set - a plain
   set() would NOT preserve order.)

8. Explain mutable vs immutable data types with real examples, and
   why this distinction matters when passing arguments to functions.

9. Why is checking membership (`x in collection`) much faster in a
   set than in a list? (Hint: hashing vs linear search, O(1) vs O(n))

10. What happens when you try to use a mutable object (like a list)
    as a key in a dictionary or an element in a set?

11. Difference between deep copy and shallow copy for nested lists
    or dictionaries — when does mutating a shallow copy affect the
    original?

12. How does Python determine if two objects are "equal" (==) vs
    "identical" (is)? Give an example where they differ for
    otherwise-equal values.

13. What is type coercion/implicit conversion? Give an example
    where mixing int and float causes an implicit conversion.

14. Why might using float for financial/monetary calculations in a
    data pipeline be risky? (Hint: use Decimal instead for precision.)
=====================================================================
"""