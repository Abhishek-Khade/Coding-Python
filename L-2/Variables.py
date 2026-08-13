"""
=====================================================================
PYTHON VARIABLES - Complete Notes with Executable Examples
=====================================================================

A variable in Python is a name that refers to a value stored in
memory. Unlike many languages, Python doesn't require you to declare
a variable's type - it's inferred automatically at runtime.
=====================================================================
"""

x = 10              # int
name = "Claude"      # str
price = 99.99        # float
is_active = True     # bool

print("--- Basic Variable Assignment ---")
print(x, name, price, is_active)
print(type(x), type(name), type(price), type(is_active))


"""
---------------------------------------------------------------------
1. DYNAMIC TYPING
---------------------------------------------------------------------
A variable can be reassigned to a different type at any time.
Python figures out the type at runtime, not at declaration.
---------------------------------------------------------------------
"""

x = 10
print("\n--- Dynamic Typing ---")
print("x =", x, "| type:", type(x))

x = "now a string"   # totally valid - no error
print("x =", x, "| type:", type(x))


"""
---------------------------------------------------------------------
2. VARIABLES ARE REFERENCES, NOT CONTAINERS
---------------------------------------------------------------------
In Python, a variable is a NAME bound to an object in memory - it
doesn't "hold" the value directly like a box. This matters a lot for
mutable objects like lists, dicts, and sets.
---------------------------------------------------------------------
"""

print("\n--- References, Not Containers ---")
a = [1, 2, 3]
b = a          # b points to the SAME list object as a
b.append(4)

print("a =", a)   # [1, 2, 3, 4] -> a changed too, since a and b
print("b =", b)   # reference the same underlying list in memory


"""
---------------------------------------------------------------------
3. NAMING RULES
---------------------------------------------------------------------
- Must start with a letter or underscore (_), not a digit
- Can contain letters, digits, underscores
- Case-sensitive (Age != age)
- Can't be a reserved keyword (class, for, if, etc.)
---------------------------------------------------------------------
"""

print("\n--- Naming Rules ---")
valid_name = 1
_private = 2
camelCase = 3
snake_case = 4     # preferred style in Python (per PEP8)

print(valid_name, _private, camelCase, snake_case)

# 2invalid = 5     # <-- Uncommenting this line raises SyntaxError
                    # because identifiers can't start with a digit


"""
---------------------------------------------------------------------
4. MULTIPLE ASSIGNMENT
---------------------------------------------------------------------
Python allows assigning multiple variables in a single line, and
also allows chained assignment where all names point to the same
initial object.
---------------------------------------------------------------------
"""

print("\n--- Multiple Assignment ---")
p, q, r = 1, 2, 3
print("p, q, r =", p, q, r)

m = n = o = 0        # all point to the same object initially
print("m, n, o =", m, n, o)


"""
---------------------------------------------------------------------
5. TYPE CHECKING & CASTING
---------------------------------------------------------------------
- type() checks a variable's current type
- int(), str(), float() etc. cast (convert) between types
---------------------------------------------------------------------
"""

print("\n--- Type Checking & Casting ---")
print("type(x):", type(x))

cast_int = int("5")        # str -> int
cast_str = str(5)          # int -> str
cast_float = float("3.14") # str -> float

print("int('5') =", cast_int, "| type:", type(cast_int))
print("str(5) =", cast_str, "| type:", type(cast_str))
print("float('3.14') =", cast_float, "| type:", type(cast_float))


"""
---------------------------------------------------------------------
6. CONSTANTS (BY CONVENTION)
---------------------------------------------------------------------
Python has no true constants (nothing prevents reassignment), but
UPPERCASE naming is a widely followed convention signaling
"this value should not be changed."
---------------------------------------------------------------------
"""

print("\n--- Constants (by convention) ---")
PI = 3.14159
MAX_CONNECTIONS = 100
print("PI =", PI, "| MAX_CONNECTIONS =", MAX_CONNECTIONS)


"""
---------------------------------------------------------------------
7. SCOPE (LOCAL vs GLOBAL)
---------------------------------------------------------------------
- Local variable: defined inside a function, accessible only there
- Global variable: defined outside functions, accessible everywhere
  (use the 'global' keyword to modify a global variable from inside
  a function)
---------------------------------------------------------------------
"""

print("\n--- Scope: Local vs Global ---")
count = 0   # global variable

def increment():
    global count     # tells Python to use the outer 'count', not
                      # create a new local variable
    count += 1

increment()
increment()
print("count after two increments:", count)


"""
---------------------------------------------------------------------
8. INTERVIEW ANGLE: MUTABLE vs IMMUTABLE BEHAVIOR
---------------------------------------------------------------------
This is one of the MOST frequently asked Python fundamentals
interview questions. It demonstrates how mutable objects (lists,
dicts, sets) can be changed in-place through a function, while
immutable objects (int, str, float, tuple) cannot.
---------------------------------------------------------------------
"""

print("\n--- Interview Angle: Mutable vs Immutable ---")

def modify_list(lst):
    lst.append(100)     # mutates the SAME list object passed in

def modify_number(num):
    num += 1             # creates a NEW int object; doesn't affect
                          # the caller's variable

my_list = [1, 2, 3]
modify_list(my_list)
print("my_list after modify_list():", my_list)   # [1, 2, 3, 100]

my_num = 5
modify_number(my_num)
print("my_num after modify_number():", my_num)   # still 5

