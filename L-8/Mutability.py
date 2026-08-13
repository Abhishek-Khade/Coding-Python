"""
=====================================================================
MUTABLE vs IMMUTABLE OBJECTS - Complete Notes with Executable Code
=====================================================================

Every object in Python is either MUTABLE (can be changed in-place
after creation) or IMMUTABLE (cannot be changed once created - any
"modification" actually creates a brand NEW object).

    IMMUTABLE types:  int, float, complex, bool, str, tuple,
                       frozenset, bytes, NoneType

    MUTABLE types:    list, dict, set, bytearray,
                       and custom class instances (by default)

This distinction affects: function arguments, default parameter
values, dictionary keys, hashing, and how assignment/copying behaves.
It is ONE OF THE MOST FREQUENTLY TESTED Python concepts in
interviews.
=====================================================================
"""

print("--- Overview ---")
print("Mutable = can change in place. Immutable = cannot; a new")
print("object is created instead.")


"""
---------------------------------------------------------------------
1. PROVING IMMUTABILITY WITH id()  ⭐⭐⭐
---------------------------------------------------------------------
id() returns a unique identifier for an object (its memory address
in CPython). If an "operation" on an object produces a DIFFERENT id,
the object was NOT modified in place - a new object was created.
---------------------------------------------------------------------
"""

print("\n--- Proving Immutability with id() ---")

# --- Immutable example: int ---
x = 10
print("x =", x, "| id:", id(x))
x += 1                     # this does NOT modify the int 10 in place
print("x =", x, "| id:", id(x), "  <-- DIFFERENT id, new object created")

# --- Immutable example: str ---
s = "hello"
print("\ns =", s, "| id:", id(s))
s += " world"               # creates a brand new string object
print("s =", s, "| id:", id(s), "  <-- DIFFERENT id, new object created")

# --- Mutable example: list ---
lst = [1, 2, 3]
print("\nlst =", lst, "| id:", id(lst))
lst.append(4)                # modifies the SAME list object in place
print("lst =", lst, "| id:", id(lst), "  <-- SAME id, modified in place")


"""
---------------------------------------------------------------------
2. WHY THIS MATTERS: SHARED REFERENCES  ⭐⭐⭐
---------------------------------------------------------------------
When you assign one variable to another (b = a), BOTH names point to
the SAME object. For mutable objects, changing it through one name
is visible through the other. For immutable objects, this is a
non-issue because "changing" always creates a new object anyway.
---------------------------------------------------------------------
"""

print("\n--- Shared References ---")

# Mutable: both variables see the change
a_list = [1, 2, 3]
b_list = a_list             # b_list points to the SAME list as a_list
b_list.append(99)
print("a_list:", a_list)    # [1, 2, 3, 99] -- changed too!
print("b_list:", b_list)
print("a_list is b_list ->", a_list is b_list)   # True, same object

# Immutable: reassigning does NOT affect the other variable
a_str = "hello"
b_str = a_str
b_str += " world"           # creates a NEW string; a_str untouched
print("\na_str:", a_str)    # still "hello"
print("b_str:", b_str)      # "hello world"


"""
---------------------------------------------------------------------
3. THE CLASSIC INTERVIEW TRAP: FUNCTION ARGUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
Python passes arguments by "object reference" (sometimes called
"pass by assignment"). Whether a function's changes are visible to
the caller depends ENTIRELY on whether the argument is mutable.
---------------------------------------------------------------------
"""

print("\n--- Function Arguments: Mutable vs Immutable ---")

def modify_list(lst):
    lst.append(100)          # mutates the SAME object passed in

def modify_number(num):
    num += 1                  # rebinds the LOCAL name to a new object;
                               # caller's variable is untouched

my_list = [1, 2, 3]
modify_list(my_list)
print("my_list after modify_list():", my_list)      # [1, 2, 3, 100]

my_num = 5
modify_number(my_num)
print("my_num after modify_number():", my_num)       # still 5

# Same trap applies to strings vs lists inside functions
def append_char(s):
    s += "!"                  # creates a new local string

def append_item(lst):
    lst.append("!")            # mutates the original list

text = "hi"
append_char(text)
print("\ntext after append_char():", text)           # unchanged: "hi"

items = ["hi"]
append_item(items)
print("items after append_item():", items)           # changed: ['hi', '!']


"""
---------------------------------------------------------------------
4. THE #1 PYTHON GOTCHA: MUTABLE DEFAULT ARGUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
Default argument values are evaluated ONCE, when the function is
DEFINED - not each time it's called. If the default is a mutable
object (like a list), it gets SHARED and ACCUMULATES state across
every call that doesn't pass its own argument. This is one of the
most famous Python bugs/interview questions.
---------------------------------------------------------------------
"""

print("\n--- Mutable Default Argument Gotcha ---")

def add_item_buggy(item, items=[]):    # DANGEROUS: default list is
    items.append(item)                  # created ONCE, at def time
    return items

print("call 1:", add_item_buggy("apple"))    # ['apple']
print("call 2:", add_item_buggy("banana"))   # ['apple', 'banana']  <-- BUG!
print("call 3:", add_item_buggy("cherry"))   # keeps growing across calls

# The FIX: use None as the default, create a new list INSIDE the
# function body each time it's called
def add_item_fixed(item, items=None):
    if items is None:
        items = []           # fresh list created on EVERY call
    items.append(item)
    return items

print("\nfixed call 1:", add_item_fixed("apple"))    # ['apple']
print("fixed call 2:", add_item_fixed("banana"))     # ['banana'] -- correct!


"""
---------------------------------------------------------------------
5. HASHABILITY: WHY IMMUTABLE OBJECTS CAN BE DICT KEYS/SET ELEMENTS
---------------------------------------------------------------------
An object is HASHABLE if its hash value never changes during its
lifetime - which requires immutability. This is why:
    - str, int, tuple, frozenset  -> hashable (usable as dict keys)
    - list, dict, set             -> NOT hashable (cannot be dict keys)
---------------------------------------------------------------------
"""

print("\n--- Hashability ---")

valid_dict = {
    "name": "Claude",          # str key - OK
    (1, 2): "coordinate",      # tuple key - OK (tuple is immutable)
}
print("dict with tuple key:", valid_dict)

try:
    bad_dict = {[1, 2]: "value"}   # list key -> TypeError
except TypeError as e:
    print("Error using list as dict key:", e)

try:
    bad_set = {1, 2, [3, 4]}       # list inside a set -> TypeError
except TypeError as e:
    print("Error putting a list inside a set:", e)

# A tuple is immutable, BUT if it contains a mutable element, it
# becomes unhashable too - immutability must be "all the way down"
nested_tuple = (1, 2, [3, 4])
try:
    hash(nested_tuple)
except TypeError as e:
    print("Error hashing a tuple containing a list:", e)


"""
---------------------------------------------------------------------
6. COPYING MUTABLE OBJECTS: SHALLOW vs DEEP COPY  ⭐⭐
---------------------------------------------------------------------
Because mutable objects are shared by reference, you often need an
explicit COPY to avoid unwanted side effects.

    shallow copy -> copies the outer object, but nested mutable
                    objects INSIDE it are still shared references
    deep copy    -> recursively copies EVERYTHING, including all
                    nested objects - fully independent
---------------------------------------------------------------------
"""

print("\n--- Shallow vs Deep Copy ---")

import copy

original = [[1, 2], [3, 4]]

shallow = copy.copy(original)          # or original[:] / list(original)
deep = copy.deepcopy(original)

shallow[0].append(99)     # mutates the INNER list, shared with original!
print("original after shallow copy mutation:", original)  # affected!
print("shallow:", shallow)

deep[1].append(999)        # fully independent, does NOT affect original
print("\noriginal after deep copy mutation:", original)   # unaffected
print("deep:", deep)


"""
---------------------------------------------------------------------
7. IMMUTABLE CONTAINERS CAN "HOLD" MUTABLE OBJECTS  ⭐⭐
---------------------------------------------------------------------
A tuple itself is immutable (you can't reassign its slots), but if
one of its ELEMENTS is a mutable object (like a list), that inner
object can still be mutated. "Immutable" refers to the container's
structure, not necessarily everything reachable through it.
---------------------------------------------------------------------
"""

print("\n--- Immutable Container Holding a Mutable Object ---")

t = (1, 2, [3, 4])
print("tuple before:", t)

t[2].append(5)          # allowed! mutating the LIST inside the tuple
print("tuple after mutating inner list:", t)   # (1, 2, [3, 4, 5])

try:
    t[2] = [9, 9]        # NOT allowed - can't reassign a tuple slot
except TypeError as e:
    print("Error reassigning tuple element:", e)


"""
---------------------------------------------------------------------
8. QUICK REFERENCE TABLE
---------------------------------------------------------------------
Type          | Mutable? | Hashable? | Common Use
--------------|----------|-----------|---------------------------------
int/float     | No       | Yes       | Numbers
bool          | No       | Yes       | True/False (subclass of int)
str           | No       | Yes       | Text; dict keys
tuple         | No       | Yes*      | Fixed records; dict keys
frozenset     | No       | Yes       | Immutable set; dict keys
list          | Yes      | No        | Ordered, growable collections
dict          | Yes      | No        | Key-value mappings
set           | Yes      | No        | Unique, unordered collections
bytearray     | Yes      | No        | Mutable byte sequences

* tuple is hashable ONLY if all its elements are hashable too.
---------------------------------------------------------------------
"""

print("\n--- Quick Reference Check ---")
for obj in [10, 3.14, True, "text", (1, 2), frozenset([1, 2]),
            [1, 2], {"a": 1}, {1, 2}]:
    try:
        hash(obj)
        hashable = True
    except TypeError:
        hashable = False
    print(f"{obj!r:20} type={type(obj).__name__:12} hashable={hashable}")


"""
=====================================================================
INTERVIEW QUESTIONS - MUTABLE vs IMMUTABLE OBJECTS
=====================================================================

1. What is the difference between a mutable and an immutable object?
   Give at least 3 examples of each.

2. Why does modifying a list passed into a function affect the
   caller's original list, while modifying an int passed into a
   function does NOT?

3. What is the "mutable default argument" bug? Show an example and
   explain the correct fix using None.

4. Why can a tuple be used as a dictionary key, but a list cannot?

5. What does it mean for an object to be "hashable"? Why does
   immutability generally imply hashability (with tuples as a
   nuanced exception)?

6. Given `t = (1, 2, [3, 4])`, can you modify the list inside the
   tuple? Is the tuple still considered immutable? Explain why this
   isn't a contradiction.

7. What's the difference between a shallow copy and a deep copy?
   Give an example where a shallow copy causes an unintended side
   effect on nested data.

8. Explain what `id()` tells you, and how you'd use it to prove
   whether an operation modified an object in place or created a
   new one.

9. Why does `a = 5; b = 5; a is b` often return True, but
   `a = [1,2]; b = [1,2]; a is b` always returns False?

10. If you assign `b = a` where `a` is a list, and then do
    `b = b + [4]` (not `b.append(4)`), does `a` change? Why or why
    not? (Hint: `+` creates a new list, `append()` mutates in place.)

11. How would you write a function that safely accumulates results
    across multiple calls WITHOUT falling into the mutable default
    argument trap?

12. Why are strings immutable in Python, and what are the
    performance implications for string-building operations in a
    loop?

13. In a data engineering context: if you pass a Pandas DataFrame
    into a function and modify it using `df.drop(columns=['x'],
    inplace=True)`, does that affect the caller's original
    DataFrame? Why does this matter for writing safe transformation
    functions in a pipeline?

14. What happens if you try to add a list as an element of a set?
    Why does Python raise a TypeError, and what would you use
    instead (e.g., converting the list to a tuple)?
=====================================================================
"""