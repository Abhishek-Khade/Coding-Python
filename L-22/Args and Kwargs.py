"""
=====================================================================
*args AND **kwargs IN PYTHON - Complete Notes with Executable Code
=====================================================================

*args and **kwargs let a function accept a VARIABLE, UNKNOWN NUMBER
of arguments - essential for writing generic, reusable functions
(especially decorators and wrapper functions).

    *args     -> collects extra POSITIONAL arguments into a TUPLE
    **kwargs  -> collects extra KEYWORD arguments into a DICT

The NAMES "args" and "kwargs" are just CONVENTION - the `*` and `**`
are what actually matter syntactically. You could name them
`*values, **options` and it would work identically.

TOPICS COVERED:
    1. Basic *args - variable positional arguments
    2. Basic **kwargs - variable keyword arguments
    3. Combining *args and **kwargs together
    4. Required parameter ordering rules
    5. Unpacking (the REVERSE direction) with * and **
    6. Positional-only and keyword-only parameters (/ and *)
    7. Real-world use cases: wrappers, decorators, dispatch
    8. Common pitfalls and gotchas
=====================================================================
"""

print("--- Overview ---")
print("*args  -> extra positional args as a TUPLE")
print("**kwargs -> extra keyword args as a DICT")


"""
---------------------------------------------------------------------
1. BASIC *args: VARIABLE POSITIONAL ARGUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
Any number of positional arguments passed to the function get
collected into a TUPLE named 'args' (by convention).
---------------------------------------------------------------------
"""

print("\n--- Basic *args ---")

def sum_all(*args):
    print("  args received as a tuple:", args, "| type:", type(args))
    return sum(args)

print("sum_all(1, 2, 3):", sum_all(1, 2, 3))
print("sum_all(10, 20):", sum_all(10, 20))
print("sum_all():", sum_all())            # zero arguments is also valid - empty tuple

# You can mix a required parameter with *args
def greet_all(greeting, *names):
    for name in names:
        print(f"  {greeting}, {name}!")

print("\ngreet_all('Hi', 'Alice', 'Bob', 'Cid'):")
greet_all("Hi", "Alice", "Bob", "Cid")


"""
---------------------------------------------------------------------
2. BASIC **kwargs: VARIABLE KEYWORD ARGUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
Any number of keyword (name=value) arguments passed to the function
get collected into a DICT named 'kwargs' (by convention).
---------------------------------------------------------------------
"""

print("\n--- Basic **kwargs ---")

def print_config(**kwargs):
    print("  kwargs received as a dict:", kwargs, "| type:", type(kwargs))
    for key, value in kwargs.items():
        print(f"    {key} = {value}")

print_config(timeout=30, retries=3, debug=True)

# Mixing required parameters with **kwargs
def build_url(base_url, **query_params):
    if not query_params:
        return base_url
    query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
    return f"{base_url}?{query_string}"

print("\nbuild_url() result:")
print(build_url("https://api.example.com/data", page=2, limit=50, sort="asc"))


"""
---------------------------------------------------------------------
3. COMBINING *args AND **kwargs TOGETHER  ⭐⭐⭐
---------------------------------------------------------------------
Both can appear in the same function signature. The ORDER matters -
*args must come BEFORE **kwargs in the function definition.
---------------------------------------------------------------------
"""

print("\n--- Combining *args and **kwargs ---")

def full_flexible(*args, **kwargs):
    print("  args:", args)
    print("  kwargs:", kwargs)

full_flexible(1, 2, 3, name="Claude", role="assistant")

# Practical example: a GENERIC wrapper/logger that can call ANY
# function with ANY combination of arguments - the #1 real-world
# use case for *args/**kwargs together
def log_and_call(func, *args, **kwargs):
    print(f"  calling {func.__name__} with args={args}, kwargs={kwargs}")
    return func(*args, **kwargs)

def add(a, b):
    return a + b

def describe_person(name, age, city="Unknown"):
    return f"{name}, age {age}, from {city}"

print("\nlog_and_call(add, 3, 4):")
print("  result:", log_and_call(add, 3, 4))

print("\nlog_and_call(describe_person, 'Claude', age=5, city='SF'):")
print("  result:", log_and_call(describe_person, "Claude", age=5, city="SF"))


"""
---------------------------------------------------------------------
4. REQUIRED PARAMETER ORDERING RULES  ⭐⭐⭐
---------------------------------------------------------------------
Python enforces a STRICT order for parameters in a function
definition:

    def f(positional_params, *args, keyword_only_params, **kwargs):

    1. Regular positional/default parameters
    2. *args  (collects remaining positional args)
    3. Keyword-only parameters (parameters AFTER *args must be
       passed by keyword - see section 6 for more on this)
    4. **kwargs (collects remaining keyword args) - MUST BE LAST

Violating this order is a SyntaxError.
---------------------------------------------------------------------
"""

print("\n--- Required Parameter Ordering ---")

def full_signature(required, default_val="default", *args, kw_only, **kwargs):
    print("  required:", required)
    print("  default_val:", default_val)
    print("  args:", args)
    print("  kw_only:", kw_only)
    print("  kwargs:", kwargs)

full_signature(1, 2, 3, 4, 5, kw_only="must be named", extra="goes to kwargs")

# The following would be a SyntaxError if uncommented - **kwargs
# must always be the LAST parameter in the signature:
#
#   def bad_order(**kwargs, *args):   # SyntaxError!
#       pass


"""
---------------------------------------------------------------------
5. UNPACKING: THE REVERSE DIRECTION  ⭐⭐⭐
---------------------------------------------------------------------
* and ** aren't just for COLLECTING arguments in a function
definition - they're also used to UNPACK an existing list/tuple or
dict INTO a function call, spreading its contents out as individual
arguments.
---------------------------------------------------------------------
"""

print("\n--- Unpacking Existing Collections into a Call ---")

def add_three_numbers(a, b, c):
    return a + b + c

values_tuple = (1, 2, 3)
values_list = [10, 20, 30]
values_dict = {"a": 100, "b": 200, "c": 300}

print("add_three_numbers(*values_tuple):", add_three_numbers(*values_tuple))
print("add_three_numbers(*values_list):", add_three_numbers(*values_list))
print("add_three_numbers(**values_dict):", add_three_numbers(**values_dict))

# You can even unpack MULTIPLE collections into a single call
def full_name(first, middle, last):
    return f"{first} {middle} {last}"

part1 = ("John",)
part2 = ("Quincy", "Adams")
print("\nfull_name(*part1, *part2):", full_name(*part1, *part2))

# Unpacking also works when BUILDING new lists/dicts/tuples (not
# just function calls) - very handy for merging
list_a = [1, 2, 3]
list_b = [4, 5, 6]
merged_list = [*list_a, *list_b, 7, 8]
print("merged list via unpacking:", merged_list)

dict_a = {"x": 1, "y": 2}
dict_b = {"y": 99, "z": 3}          # 'y' conflicts - LATER dict wins
merged_dict = {**dict_a, **dict_b}
print("merged dict via unpacking (later dict wins on conflict):", merged_dict)


"""
---------------------------------------------------------------------
6. POSITIONAL-ONLY (/) AND KEYWORD-ONLY (*) PARAMETERS  ⭐⭐
---------------------------------------------------------------------
Beyond *args/**kwargs for VARIABLE arguments, Python lets you force
certain NAMED parameters to be passed ONLY positionally or ONLY by
keyword, using special markers in the signature:

    def f(a, b, /, c, d, *, e, f):
              ^           ^
              |           |
        everything BEFORE '/' must be POSITIONAL
                    everything AFTER '*' must be KEYWORD-ONLY
                    (c, d can be passed either way)

A bare `*` (without a name) in the signature marks the boundary for
keyword-only arguments WITHOUT needing to collect them into
**kwargs.
---------------------------------------------------------------------
"""

print("\n--- Positional-Only (/) and Keyword-Only (*) Markers ---")

def strict_signature(pos_only, /, normal, *, kw_only):
    print(f"  pos_only={pos_only}, normal={normal}, kw_only={kw_only}")

# Valid calls
strict_signature(1, 2, kw_only=3)
strict_signature(1, normal=2, kw_only=3)

try:
    strict_signature(pos_only=1, normal=2, kw_only=3)   # pos_only can't be named!
except TypeError as e:
    print("Error passing pos_only as a keyword:", e)

try:
    strict_signature(1, 2, 3)                             # kw_only can't be positional!
except TypeError as e:
    print("Error passing kw_only positionally:", e)

# A bare '*' with no name - marks everything after it as keyword-only,
# WITHOUT collecting the rest into a **kwargs dict
def create_user(name, *, admin=False, active=True):
    return {"name": name, "admin": admin, "active": active}

print("\ncreate_user('Claude', admin=True):", create_user("Claude", admin=True))
try:
    create_user("Claude", True)     # admin MUST be passed by keyword
except TypeError as e:
    print("Error passing keyword-only arg positionally:", e)


"""
---------------------------------------------------------------------
7. REAL-WORLD USE CASE: DECORATORS  ⭐⭐⭐
---------------------------------------------------------------------
*args/**kwargs are ESSENTIAL for writing a decorator that can wrap
ANY function, regardless of that function's own specific signature -
without *args/**kwargs, a decorator could only wrap functions with
one exact, hardcoded set of parameters.
---------------------------------------------------------------------
"""

print("\n--- Real-World Use Case: Decorators ---")

def log_calls(func):
    def wrapper(*args, **kwargs):        # accepts ANY signature at all
        print(f"  calling {func.__name__}(args={args}, kwargs={kwargs})")
        result = func(*args, **kwargs)    # forwards them all through unchanged
        print(f"  {func.__name__} returned {result!r}")
        return result
    return wrapper

@log_calls
def multiply(a, b):
    return a * b

@log_calls
def describe(name, age=0, **extra_fields):
    return f"{name} ({age}): {extra_fields}"

print("calling multiply(4, 5):")
multiply(4, 5)

print("\ncalling describe('Claude', age=5, role='assistant'):")
describe("Claude", age=5, role="assistant")


"""
---------------------------------------------------------------------
8. REAL-WORLD USE CASE: FLEXIBLE CONFIG / FACTORY FUNCTIONS  ⭐⭐
---------------------------------------------------------------------
**kwargs is commonly used for building objects/records where the
SET of possible fields is large, optional, or evolving over time -
avoiding a function signature with dozens of default parameters.
---------------------------------------------------------------------
"""

print("\n--- Real-World Use Case: Flexible Config Objects ---")

def create_pipeline_config(name, **overrides):
    defaults = {"batch_size": 1000, "retries": 3, "timeout": 30, "parallel": False}
    config = {**defaults, **overrides}    # overrides win on any conflicts
    config["name"] = name
    return config

print("default config:", create_pipeline_config("daily_etl"))
print("\noverridden config:",
      create_pipeline_config("realtime_etl", batch_size=100, parallel=True))


"""
---------------------------------------------------------------------
9. COMMON PITFALLS  ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Common Pitfalls ---")

# Pitfall 1: *args is a TUPLE (immutable) - you can't append to it
def bad_attempt(*args):
    try:
        args.append(99)     # tuples have no .append() method!
    except AttributeError as e:
        print("  Error: *args is a tuple, not a list:", e)

bad_attempt(1, 2, 3)

# Pitfall 2: forgetting that unpacking a dict with ** requires the
# CALLED function to actually accept those exact keyword names
def specific_function(a, b):
    return a + b

wrong_keys_dict = {"x": 1, "y": 2}
try:
    specific_function(**wrong_keys_dict)   # neither 'x' nor 'y' match a, b
except TypeError as e:
    print("  Error unpacking a dict with mismatched keys:", e)

# Pitfall 3: passing an already-unpacked argument AGAIN by name
# causes a "multiple values for argument" error
def show(a, b):
    return (a, b)

try:
    show(1, a=2)          # 'a' is being given a value TWICE
except TypeError as e:
    print("  Error: got multiple values for argument:", e)

# Pitfall 4: *args/**kwargs make a function's signature "invisible"
# in tools like help()/IDE autocompletion - always document expected
# arguments via docstrings for functions using *args/**kwargs
def documented_flexible(*args, **kwargs):
    """
    Accepts any positional args and keyword args.

    Expected kwargs:
        name (str): the record's name
        amount (float): the record's amount
    """
    pass

print("\n  Docstring becomes important since signature itself is generic:")
print(" ", documented_flexible.__doc__.strip().splitlines()[0])


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Syntax in a function DEFINITION:
    def f(*args)        -> collect extra positional args into a tuple
    def f(**kwargs)      -> collect extra keyword args into a dict
    def f(*args, **kwargs) -> collect BOTH (args must come first)

Syntax when CALLING a function (unpacking, reverse direction):
    f(*my_list)          -> spreads list/tuple items as positional args
    f(**my_dict)          -> spreads dict items as keyword args

Parameter ordering in a definition:
    positional, defaults, *args, keyword_only, **kwargs

Special markers:
    /   -> everything BEFORE this must be positional-only
    *   -> everything AFTER this must be keyword-only
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - *args AND **kwargs
=====================================================================

1. What data type does `*args` collect its values into, and what
   data type does `**kwargs` use? Why does that distinction matter
   (e.g., can you `.append()` to `args`)?

2. What is the correct parameter ordering in a function definition
   that uses regular parameters, `*args`, keyword-only parameters,
   and `**kwargs` all together?

3. What's the difference between using `*`/`**` in a function
   DEFINITION versus using them in a function CALL? Give an example
   of each.

4. Why are `*args`/`**kwargs` essential for writing a generic
   decorator that can wrap ANY function, regardless of that
   function's specific parameter list?

5. What does the bare `*` (with no name) do in a function signature
   like `def f(a, *, b):`? How is this different from `**kwargs`?

6. What does the `/` marker do in a function signature like
   `def f(a, b, /, c):`? Why might a library author want to force
   certain parameters to be positional-only?

7. If you have a dictionary `{"x": 1, "y": 2}` and try to call
   `some_func(**that_dict)`, what determines whether this call
   succeeds or raises a `TypeError`?

8. What happens if you call `f(1, a=2)` where `f`'s first parameter
   is named `a`? Why does Python raise an error here?

9. How would you merge two dictionaries into a new one using `**`
   unpacking, and what happens if both dictionaries share a common
   key?

10. Why can't `**kwargs` appear BEFORE `*args` in a function
    signature? What error would you get if you tried?

11. In a decorator's `wrapper(*args, **kwargs)` function, why is it
    important to forward `*args` and `**kwargs` to the wrapped
    function using `func(*args, **kwargs)` rather than
    `func(args, kwargs)`?

12. How would you write a function that accepts a flexible,
    evolving set of optional configuration fields (some pipelines
    need `batch_size`, others need `parallel`, etc.) without adding
    dozens of individual default parameters to the signature?

13. Given `def f(a, b=2, *args, c, **kwargs): ...`, is `c` a
    required or optional argument? Can it be passed positionally?
    Explain why, based on where it sits relative to `*args`.

14. Why does using `*args`/`**kwargs` in a public function's
    signature reduce the usefulness of IDE autocompletion and
    `help()` output? How would you mitigate this?
=====================================================================
"""