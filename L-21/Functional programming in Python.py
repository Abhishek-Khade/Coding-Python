"""
=====================================================================
FUNCTIONAL PROGRAMMING IN PYTHON - Notes with Executable Examples
=====================================================================

Python is NOT a purely functional language (like Haskell), but it
supports functional programming STYLE and provides first-class
tooling for it. Core functional programming principles:

    1. Functions are FIRST-CLASS CITIZENS - can be assigned to
       variables, passed as arguments, returned from other functions
    2. HIGHER-ORDER FUNCTIONS - functions that take/return other
       functions (map, filter, reduce, decorators...)
    3. PURE FUNCTIONS - same input always gives same output, no
       side effects (no mutating external state, no I/O)
    4. IMMUTABILITY - prefer creating new data over mutating existing
       data (favors tuples/frozensets over lists/sets where possible)
    5. DECLARATIVE STYLE - describe WHAT to compute, not step-by-step
       HOW (comprehensions/map over explicit loops)

This matters for Data Engineering because functional-style pipelines
(pure, composable transformation functions) are easier to test,
parallelize, and reason about than pipelines full of shared mutable
state and side effects.
=====================================================================
"""

import time
import functools
import itertools

print("--- Overview ---")
print("Functional programming: first-class functions, pure functions,")
print("immutability, and declarative (not step-by-step) style.")


"""
---------------------------------------------------------------------
1. FUNCTIONS AS FIRST-CLASS CITIZENS  ⭐⭐⭐
---------------------------------------------------------------------
In Python, a function is just another OBJECT. It can be:
    - assigned to a variable
    - stored in a list/dict
    - passed as an argument to another function
    - returned from another function
---------------------------------------------------------------------
"""

print("\n--- Functions as First-Class Citizens ---")

def greet(name):
    return f"Hello, {name}!"

# Assign a function to a variable (no parentheses - we want the
# function OBJECT itself, not to CALL it)
say_hello = greet
print("calling via new variable name:", say_hello("Claude"))

# Store functions in a data structure - a common "dispatch table" pattern
operations = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
}
print("\ndispatch table lookup:")
print("operations['add'](3, 4):", operations["add"](3, 4))
print("operations['multiply'](3, 4):", operations["multiply"](3, 4))

# Pass a function as an ARGUMENT to another function
def apply_twice(func, value):
    return func(func(value))

print("\napply_twice(lambda x: x * 2, 3):", apply_twice(lambda x: x * 2, 3))


"""
---------------------------------------------------------------------
2. HIGHER-ORDER FUNCTIONS: RETURNING A FUNCTION  ⭐⭐⭐
---------------------------------------------------------------------
A "higher-order function" either takes a function as an argument,
RETURNS a function, or both. Returning a function is how Python
builds CLOSURES - functions that "remember" the environment they
were created in.
---------------------------------------------------------------------
"""

print("\n--- Higher-Order Functions: Returning a Function ---")

def make_multiplier(factor):
    """Returns a NEW function that multiplies its input by 'factor'."""
    def multiplier(x):
        return x * factor
    return multiplier

double = make_multiplier(2)
triple = make_multiplier(3)

print("double(5):", double(5))
print("triple(5):", triple(5))
print("\ndouble and triple are DIFFERENT function objects, each")
print("'remembering' its own 'factor' value - this is a CLOSURE.")


"""
---------------------------------------------------------------------
3. CLOSURES: FUNCTIONS THAT "REMEMBER" THEIR ENCLOSING SCOPE  ⭐⭐⭐
---------------------------------------------------------------------
A closure is created when an INNER function references a variable
from its ENCLOSING (outer) function's scope, and that inner function
is then returned/used outside the outer function. The inner
function keeps a reference to that outer variable, even after the
outer function has already finished executing.
---------------------------------------------------------------------
"""

print("\n--- Closures ---")

def make_counter():
    count = 0                    # this variable is "closed over"
    def increment():
        nonlocal count            # required to MODIFY the outer variable
        count += 1
        return count
    return increment

counter1 = make_counter()
counter2 = make_counter()          # a COMPLETELY separate closure/state

print("counter1():", counter1())    # 1
print("counter1():", counter1())    # 2
print("counter1():", counter1())    # 3
print("counter2():", counter2())    # 1 - independent from counter1!

# Inspecting what a closure has captured
print("\ncounter1.__closure__:", counter1.__closure__)
print("captured cell value:", counter1.__closure__[0].cell_contents)


"""
---------------------------------------------------------------------
4. PURE FUNCTIONS vs IMPURE FUNCTIONS  ⭐⭐⭐
---------------------------------------------------------------------
PURE function:
    - Given the same input, ALWAYS returns the same output
    - Has NO side effects (doesn't mutate external state, doesn't
      print/write files/make network calls)

IMPURE function:
    - May return DIFFERENT results for the same input (e.g., depends
      on external/global state, current time, randomness)
    - Mutates something outside itself, or performs I/O

Pure functions are easier to TEST, REASON ABOUT, PARALLELIZE, and
CACHE - a major reason functional style is valued in data pipelines.
---------------------------------------------------------------------
"""

print("\n--- Pure vs Impure Functions ---")

# PURE - same input always gives the same output, no side effects
def add_pure(a, b):
    return a + b

print("add_pure(2, 3) called twice:", add_pure(2, 3), add_pure(2, 3))

# IMPURE - depends on and MUTATES external/global state
running_total = 0
def add_impure(x):
    global running_total
    running_total += x        # side effect: mutates external state
    return running_total

print("\nadd_impure(5) first call:", add_impure(5))
print("add_impure(5) second call (SAME input, DIFFERENT output!):", add_impure(5))

# IMPURE - mutates its MUTABLE argument, a common source of pipeline bugs
def add_item_impure(item, target_list):
    target_list.append(item)     # side effect: mutates the caller's list
    return target_list

# PURE equivalent - returns a NEW list, doesn't touch the original
def add_item_pure(item, target_list):
    return target_list + [item]   # '+' creates a new list

original = [1, 2, 3]
result_pure = add_item_pure(4, original)
print("\noriginal after PURE add_item:", original)          # unchanged
print("result of pure function:", result_pure)


"""
---------------------------------------------------------------------
5. FUNCTION COMPOSITION: BUILDING PIPELINES FROM SMALL FUNCTIONS ⭐⭐⭐
---------------------------------------------------------------------
Functional style favors building complex transformations by
COMPOSING several small, single-purpose, pure functions - exactly
the shape of a typical ETL/data pipeline (extract -> clean ->
transform -> validate).
---------------------------------------------------------------------
"""

print("\n--- Function Composition ---")

def compose(*functions):
    """Combine multiple functions into one, applied right to left."""
    def composed(x):
        result = x
        for func in reversed(functions):
            result = func(result)
        return result
    return composed

def strip_whitespace(s):
    return s.strip()

def to_lowercase(s):
    return s.lower()

def remove_punctuation(s):
    return "".join(c for c in s if c.isalnum() or c.isspace())

clean_text = compose(remove_punctuation, to_lowercase, strip_whitespace)
raw = "   Hello, WORLD!!!   "
print(f"'{raw}' -> '{clean_text(raw)}'")

# Same idea, but as an explicit ETL-style pipeline of pure functions
def run_pipeline(value, *steps):
    for step in steps:
        value = step(value)
    return value

pipeline_result = run_pipeline(raw, strip_whitespace, to_lowercase, remove_punctuation)
print("run_pipeline() result:", repr(pipeline_result))


"""
---------------------------------------------------------------------
6. map(), filter(), reduce(): THE CLASSIC FUNCTIONAL TRIO  ⭐⭐⭐
---------------------------------------------------------------------
map(func, iterable)      -> applies func to EVERY item, lazily
filter(func, iterable)    -> keeps items where func returns truthy,
                              lazily
functools.reduce(func,     -> cumulatively combines all items into
    iterable)                 ONE final result

Both map() and filter() return LAZY ITERATOR objects in Python 3 -
not lists - so wrap them in list() to see/materialize all results.
---------------------------------------------------------------------
"""

print("\n--- map(), filter(), reduce() ---")

numbers = [1, 2, 3, 4, 5, 6, 7, 8]

mapped = map(lambda x: x ** 2, numbers)
print("map() returns a LAZY iterator:", mapped)
print("materialized with list():", list(mapped))

filtered = filter(lambda x: x % 2 == 0, numbers)
print("\nfilter() result:", list(filtered))

total = functools.reduce(lambda acc, x: acc + x, numbers)
print("\nreduce() (sum):", total)

# reduce() with an explicit INITIAL value
total_with_start = functools.reduce(lambda acc, x: acc + x, numbers, 100)
print("reduce() with initial value 100:", total_with_start)

# Comprehensions are usually preferred in Pythonic code over
# map()/filter() for readability - but map()/filter() shine when
# you already have a NAMED function to apply
print("\nequivalent list comprehension (often preferred):",
      [x ** 2 for x in numbers if x % 2 == 0])


"""
---------------------------------------------------------------------
7. *args AND **kwargs: FLEXIBLE FUNCTION SIGNATURES  ⭐⭐⭐
---------------------------------------------------------------------
*args     -> collects extra POSITIONAL arguments into a TUPLE
**kwargs  -> collects extra KEYWORD arguments into a DICT

Essential for writing generic, reusable higher-order functions and
decorators that need to accept ANY function's arguments.
---------------------------------------------------------------------
"""

print("\n--- *args and **kwargs ---")

def flexible_function(*args, **kwargs):
    print("  positional args (as a tuple):", args)
    print("  keyword args (as a dict):", kwargs)

flexible_function(1, 2, 3, name="Claude", role="assistant")

# Unpacking existing collections INTO a function call using the
# SAME * and ** syntax (the reverse direction)
def add_three(a, b, c):
    return a + b + c

values = (1, 2, 3)
print("\nadd_three(*values):", add_three(*values))    # unpacks tuple as args

kwargs_dict = {"a": 10, "b": 20, "c": 30}
print("add_three(**kwargs_dict):", add_three(**kwargs_dict))  # unpacks dict as kwargs


"""
---------------------------------------------------------------------
8. functools.partial: PRE-FILLING FUNCTION ARGUMENTS  ⭐⭐
---------------------------------------------------------------------
partial() creates a NEW callable with some arguments already
"locked in" - useful for adapting a general-purpose function to fit
an interface that expects fewer arguments (e.g., as a callback).
---------------------------------------------------------------------
"""

print("\n--- functools.partial ---")

def power(base, exponent):
    return base ** exponent

square = functools.partial(power, exponent=2)     # exponent is now FIXED
cube = functools.partial(power, exponent=3)

print("square(5):", square(5))
print("cube(5):", cube(5))

# Practical DE use case: pre-configuring a transformation function
# before mapping it across many records
def convert_currency(amount, rate):
    return round(amount * rate, 2)

to_eur = functools.partial(convert_currency, rate=0.92)
amounts_usd = [100, 250, 75.5]
amounts_eur = list(map(to_eur, amounts_usd))
print("\nUSD amounts:", amounts_usd)
print("converted to EUR via partial():", amounts_eur)


"""
---------------------------------------------------------------------
9. DECORATORS: FUNCTIONS THAT WRAP OTHER FUNCTIONS  ⭐⭐⭐
---------------------------------------------------------------------
A decorator is a higher-order function that takes a function,
wraps it with EXTRA behavior, and returns a new function - all
without modifying the original function's own code. The `@decorator`
syntax is just syntactic sugar for `func = decorator(func)`.
---------------------------------------------------------------------
"""

print("\n--- Decorators ---")

def timer(func):
    @functools.wraps(func)      # preserves the original function's
    def wrapper(*args, **kwargs):   # __name__/docstring - good practice
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  '{func.__name__}' took {elapsed:.6f} sec")
        return result
    return wrapper

@timer
def slow_sum(n):
    """Sums numbers from 0 to n-1."""
    return sum(range(n))

result = slow_sum(1_000_000)
print("result:", result)
print("decorated function's name preserved by @wraps:", slow_sum.__name__)
print("decorated function's docstring preserved:", slow_sum.__doc__)

# Retry decorator - a very common real-world DE pattern (e.g.,
# retrying a flaky API call)
def retry(max_attempts=3):
    """A decorator FACTORY - takes arguments, returns the actual decorator."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except ValueError as e:
                    print(f"  attempt {attempt} failed: {e}")
                    if attempt == max_attempts:
                        raise
            return None
        return wrapper
    return decorator

attempt_counter = {"count": 0}

@retry(max_attempts=3)
def flaky_operation():
    attempt_counter["count"] += 1
    if attempt_counter["count"] < 3:
        raise ValueError("simulated transient failure")
    return "success!"

print("\nretry decorator in action:")
print("final result:", flaky_operation())


"""
---------------------------------------------------------------------
10. GENERATORS & yield: LAZY FUNCTIONAL PIPELINES  ⭐⭐⭐
---------------------------------------------------------------------
A generator function uses `yield` instead of `return` to produce
values LAZILY, one at a time, pausing its state between each value.
Generators are the functional-programming-friendly way to build
memory-efficient, composable data pipelines - especially important
for large datasets.
---------------------------------------------------------------------
"""

print("\n--- Generators & yield ---")

def read_lines_lazily(lines):
    """Simulates lazily reading lines from a huge file, one at a time."""
    for line in lines:
        yield line.strip()

def filter_errors(lines):
    """A generator that filters another generator - LAZY chaining!"""
    for line in lines:
        if "ERROR" in line:
            yield line

def extract_timestamps(lines):
    """Another generator stage - transforms each item lazily."""
    for line in lines:
        yield line.split(" ")[0]

raw_lines = [
    "2026-08-13 INFO startup complete\n",
    "2026-08-13 ERROR connection failed\n",
    "2026-08-13 INFO heartbeat\n",
    "2026-08-13 ERROR timeout\n",
]

# Chaining generators = a lazy, functional-style processing PIPELINE -
# NOTHING is computed until the final list()/for-loop consumes it
pipeline = extract_timestamps(filter_errors(read_lines_lazily(raw_lines)))
print("lazily chained generator pipeline result:", list(pipeline))

print("\nNone of the intermediate generators built a full list in")
print("memory - each line flows through all three stages one at a time.")


"""
---------------------------------------------------------------------
11. itertools: FUNCTIONAL TOOLS FOR ITERATORS  ⭐⭐⭐
---------------------------------------------------------------------
The itertools module provides fast, memory-efficient, composable
building blocks for iterator-based (functional-style) code.
---------------------------------------------------------------------
"""

print("\n--- itertools: Functional Iterator Tools ---")

# chain() - lazily concatenates multiple iterables into one stream
combined = itertools.chain([1, 2], [3, 4], [5])
print("itertools.chain():", list(combined))

# islice() - "slices" a lazy iterator/generator (see earlier topic)
counter_gen = itertools.count(start=10, step=5)    # infinite generator!
first_four = list(itertools.islice(counter_gen, 4))
print("itertools.count() + islice():", first_four)

# groupby() - groups CONSECUTIVE equal elements (data must be
# pre-sorted by the grouping key for this to group correctly!)
records_sorted = sorted(
    [{"dept": "Sales", "name": "Bob"}, {"dept": "Eng", "name": "Amy"},
     {"dept": "Sales", "name": "Cid"}],
    key=lambda r: r["dept"]
)
print("\nitertools.groupby() (input MUST be sorted by the key first):")
for dept, group in itertools.groupby(records_sorted, key=lambda r: r["dept"]):
    print(f"  {dept}: {[r['name'] for r in group]}")

# starmap() - like map(), but unpacks each item as *args to the function
pairs = [(2, 3), (4, 5), (6, 7)]
products = list(itertools.starmap(lambda a, b: a * b, pairs))
print("\nitertools.starmap():", products)


"""
---------------------------------------------------------------------
12. functools.lru_cache: MEMOIZING PURE FUNCTIONS  ⭐⭐⭐
---------------------------------------------------------------------
Since PURE functions always return the same output for the same
input, their results can be safely CACHED (memoized) - repeated
calls with the same arguments skip recomputation entirely.
functools.lru_cache (or functools.cache in 3.9+) does this
automatically via a decorator.
---------------------------------------------------------------------
"""

print("\n--- functools.lru_cache: Memoization ---")

call_count = {"count": 0}

@functools.lru_cache(maxsize=None)
def expensive_pure_computation(n):
    call_count["count"] += 1
    return n ** 2

print("first call with 5:", expensive_pure_computation(5))
print("second call with 5 (CACHED, function body NOT re-run):",
      expensive_pure_computation(5))
print("call with a new value, 6:", expensive_pure_computation(6))
print("\ntotal actual function executions:", call_count["count"])   # only 2, not 3!

print("cache info:", expensive_pure_computation.cache_info())


"""
---------------------------------------------------------------------
13. RECURSION: A FUNCTIONAL-STYLE ALTERNATIVE TO LOOPS  ⭐⭐
---------------------------------------------------------------------
Functional programming often favors recursion over explicit
mutable-state loops. Python supports recursion, but has NO tail-call
optimization, and a fairly low default recursion limit - so deep
recursion (as might occur processing a huge nested structure) can
raise a RecursionError.
---------------------------------------------------------------------
"""

print("\n--- Recursion ---")

def factorial_recursive(n):
    if n <= 1:                # base case - required to stop recursion
        return 1
    return n * factorial_recursive(n - 1)   # recursive case

print("factorial_recursive(6):", factorial_recursive(6))

import sys
print("Python's default recursion limit:", sys.getrecursionlimit())

def infinite_recursion(n):
    return infinite_recursion(n + 1)      # no base case - will hit the limit!

try:
    infinite_recursion(0)
except RecursionError as e:
    print("Error from unbounded recursion:", e)


"""
=====================================================================
QUICK REFERENCE: FUNCTIONAL PROGRAMMING TOOLKIT
=====================================================================
Concept                | Python Tool
------------------------|------------------------------------------
Anonymous function       | lambda
Apply to every item        | map(), list/generator comprehensions
Filter items                | filter(), comprehension with 'if'
Cumulative combination        | functools.reduce()
Pre-fill arguments              | functools.partial()
Wrap/extend behavior              | decorators (@decorator syntax)
Lazy value production               | generators (yield), generator
                                       expressions
Iterator composition                  | itertools (chain, islice,
                                       groupby, starmap, ...)
Cache pure function results             | functools.lru_cache / cache
Flexible argument passing                 | *args, **kwargs
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - FUNCTIONAL PROGRAMMING IN PYTHON
=====================================================================

1. What does it mean for functions to be "first-class citizens" in
   Python? Give three concrete things you can do with a function
   object that you can also do with an int or a string.

2. What is a "pure function"? Why are pure functions easier to
   test, cache, and parallelize than impure ones?

3. What is a closure? Explain how `make_counter()` in this file
   creates independent, isolated state for `counter1` and
   `counter2` without using any class.

4. Why is `nonlocal` required inside a closure's inner function if
   you want to MODIFY (not just read) a variable from the enclosing
   scope?

5. What's the difference between `map()`/`filter()` and an
   equivalent list comprehension? Which is generally considered more
   "Pythonic," and when might you still prefer map()/filter()?

6. What does `functools.reduce()` do, and how would you use it to
   find the maximum value in a list without using the built-in
   `max()` function?

7. How does a decorator work "under the hood"? What does
   `@my_decorator` above a function definition actually translate
   to in terms of a plain function call and reassignment?

8. Why is `functools.wraps()` used inside a decorator's inner
   `wrapper` function? What breaks if you omit it?

9. What is a "decorator factory" (a decorator that itself takes
   arguments, like `@retry(max_attempts=3)`)? How many levels of
   nested functions does it typically require?

10. How does `functools.partial()` differ from writing a small
    wrapper function/lambda that calls the original function with
    some arguments pre-filled? Is there any real difference besides
    style?

11. Why are generators considered a "functional" tool for building
    data pipelines? What's the key memory/performance advantage of
    chaining several generator functions together instead of
    building a full list at each pipeline stage?

12. What precondition must be true about your data BEFORE using
    `itertools.groupby()`, in order for the grouping to work
    correctly? What happens if you skip that precondition?

13. Explain how `functools.lru_cache` works, and why it can ONLY be
    safely applied to functions whose behavior is a pure function of
    their arguments (i.e., no side effects, no dependence on mutable
    global state).

14. In a data engineering context, why might a purely functional-
    style transformation pipeline (a series of small pure functions,
    each returning a new value rather than mutating in place) be
    preferred over a pipeline built from functions that mutate a
    shared DataFrame or list in place?

15. What is the "lambda in a loop" closure bug (recap), and how is
    it related to how closures generally capture variables by
    REFERENCE rather than by VALUE at the time the closure is
    created?
=====================================================================
"""