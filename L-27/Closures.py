"""
=====================================================================
PYTHON CLOSURES - Complete Notes with Executable Examples
=====================================================================

A CLOSURE is a function that "remembers" values from the enclosing
(outer) scope it was DEFINED in, even after that outer scope has
already finished executing.

A closure requires THREE conditions to exist:
    1. A NESTED function (a function defined inside another function)
    2. The nested (inner) function must REFERENCE a variable from
       the ENCLOSING function's scope (a "free variable")
    3. The ENCLOSING function must RETURN the nested function (so it
       can be called later, outside its original scope)

Closures are how Python implements "functions with private, built-in
state" WITHOUT needing a full class - a lightweight alternative to
object-oriented encapsulation for simple cases.
=====================================================================
"""

print("--- Overview ---")
print("A closure = an inner function that remembers variables from")
print("its enclosing scope, even after that scope has finished.")


"""
---------------------------------------------------------------------
1. THE THREE INGREDIENTS OF A CLOSURE  ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- The Three Ingredients of a Closure ---")

def outer_function(message):           # 1. enclosing/outer function
    def inner_function():               # 2. nested inner function
        print(f"  message from closure: {message}")   # 3. references outer var
    return inner_function                 # 4. returns the inner function

my_closure = outer_function("Hello from the enclosing scope!")
print("outer_function() has already finished running.")
print("calling the returned closure LATER:")
my_closure()


"""
---------------------------------------------------------------------
2. PROVING THE VARIABLE IS REMEMBERED, NOT RE-EVALUATED  ⭐⭐⭐
---------------------------------------------------------------------
The closure doesn't re-run outer_function() or somehow "guess" the
message - it holds a genuine reference to that specific variable's
value, captured at the time the closure was created.
---------------------------------------------------------------------
"""

print("\n--- Multiple Independent Closures ---")

def make_greeter(greeting):
    def greet(name):
        return f"{greeting}, {name}!"
    return greet

say_hello = make_greeter("Hello")
say_howdy = make_greeter("Howdy")

print(say_hello("Alice"))
print(say_howdy("Bob"))
print("\nEach closure REMEMBERS its OWN 'greeting' value -")
print("they don't interfere with each other at all.")


"""
---------------------------------------------------------------------
3. INSPECTING A CLOSURE: __closure__ AND cell_contents  ⭐⭐⭐
---------------------------------------------------------------------
Python actually implements this "remembering" using CELL OBJECTS.
Every closure function has a __closure__ attribute - a tuple of
"cell" objects, one per captured free variable - and you can inspect
exactly what value each one holds.
---------------------------------------------------------------------
"""

print("\n--- Inspecting a Closure Internally ---")

print("say_hello.__closure__:", say_hello.__closure__)
print("captured variable name(s):", say_hello.__code__.co_freevars)
print("captured value:", say_hello.__closure__[0].cell_contents)

print("\nsay_howdy captures a DIFFERENT value in its own cell:")
print("captured value:", say_howdy.__closure__[0].cell_contents)


"""
---------------------------------------------------------------------
4. READING vs MODIFYING: WHY nonlocal IS NEEDED  ⭐⭐⭐
---------------------------------------------------------------------
A closure can READ an enclosing variable with NO special keyword.
But to MODIFY (reassign) that variable from inside the inner
function, you MUST declare it with `nonlocal` - otherwise Python
assumes you're creating a brand-new LOCAL variable inside the inner
function instead, which shadows the outer one entirely.
---------------------------------------------------------------------
"""

print("\n--- Reading vs Modifying: nonlocal ---")

def make_counter_broken():
    count = 0
    def increment():
        count += 1     # this LINE is actually `count = count + 1`,
                        # which makes Python treat 'count' as LOCAL
                        # to increment() - and reading it before
                        # assignment fails!
        return count
    return increment

broken_counter = make_counter_broken()
try:
    broken_counter()
except UnboundLocalError as e:
    print("Error WITHOUT nonlocal (count treated as local):", e)

def make_counter_fixed():
    count = 0
    def increment():
        nonlocal count     # explicitly refers to the ENCLOSING 'count'
        count += 1
        return count
    return increment

fixed_counter = make_counter_fixed()
print("\nWITH nonlocal:")
print(" call 1:", fixed_counter())
print(" call 2:", fixed_counter())
print(" call 3:", fixed_counter())


"""
---------------------------------------------------------------------
5. INDEPENDENT STATE: EACH CALL TO THE OUTER FUNCTION MAKES A NEW
   CLOSURE WITH ITS OWN CELLS  ⭐⭐⭐
---------------------------------------------------------------------
Every time you CALL the enclosing function, a BRAND NEW set of cell
objects is created for that call - so multiple closures produced
from separate calls are completely independent, even though they
share the SAME source code.
---------------------------------------------------------------------
"""

print("\n--- Independent State Across Multiple Closures ---")

counter_a = make_counter_fixed()
counter_b = make_counter_fixed()

print("counter_a():", counter_a())      # 1
print("counter_a():", counter_a())      # 2
print("counter_b():", counter_b())      # 1 - starts fresh, independent!
print("counter_a():", counter_a())      # 3 - unaffected by counter_b


"""
---------------------------------------------------------------------
6. CLOSURES AS A LIGHTWEIGHT ALTERNATIVE TO CLASSES  ⭐⭐⭐
---------------------------------------------------------------------
A closure can encapsulate PRIVATE state and behavior, similar to a
simple class with one method and one instance attribute - often
with less boilerplate for SIMPLE cases. This is a common interview
discussion point: "when would you use a closure instead of a
class?"
---------------------------------------------------------------------
"""

print("\n--- Closures vs a Simple Class (Same Behavior) ---")

# Closure-based counter (from above)
closure_counter = make_counter_fixed()
print("closure-based counter:", closure_counter(), closure_counter())

# Equivalent CLASS-based counter
class Counter:
    def __init__(self):
        self._count = 0
    def increment(self):
        self._count += 1
        return self._count

class_counter = Counter()
print("class-based counter:", class_counter.increment(), class_counter.increment())

print("\nBoth achieve the same 'private, persistent state' effect.")
print("Closures are a lighter-weight choice when you only need ONE")
print("behavior/method; a class is better once you need MULTIPLE")
print("related methods sharing that state.")


"""
---------------------------------------------------------------------
7. THE CLASSIC "LATE BINDING" CLOSURE TRAP (LOOPS)  ⭐⭐⭐
---------------------------------------------------------------------
This is THE most commonly tested closure pitfall. Closures capture
variables by REFERENCE to the enclosing scope's cell - NOT a
snapshot of the value AT closure-creation time. If several closures
are created inside a loop, and they all reference the SAME loop
variable, they will ALL see whatever that variable's FINAL value
ends up being, once the loop finishes - because they're all reading
from the SAME shared cell.
---------------------------------------------------------------------
"""

print("\n--- The Late-Binding Closure Trap ---")

# BUGGY: all three closures share the SAME 'i' cell
buggy_functions = []
for i in range(3):
    buggy_functions.append(lambda: i)

print("buggy closures, all called AFTER the loop finished:")
print([f() for f in buggy_functions])     # [2, 2, 2] - NOT [0, 1, 2]!

print("\nWhy? Because 'i' is looked up in the ENCLOSING scope at CALL")
print("time, not at closure-CREATION time - and by the time any of")
print("these lambdas are actually called, the loop has already")
print("finished, leaving 'i' at its FINAL value (2).")

# FIX 1: use a default argument - default values ARE evaluated
# immediately, at function-DEFINITION time, capturing the CURRENT
# value instead of a reference to the shared loop variable
fixed_with_default = []
for i in range(3):
    fixed_with_default.append(lambda i=i: i)

print("\nfixed using a default argument:")
print([f() for f in fixed_with_default])   # [0, 1, 2] - correct!

# FIX 2: wrap in an extra factory function, forcing a NEW scope
# (and therefore a NEW cell) for each iteration
def make_constant_returner(value):
    return lambda: value

fixed_with_factory = [make_constant_returner(i) for i in range(3)]
print("fixed using an extra factory function:")
print([f() for f in fixed_with_factory])   # [0, 1, 2] - also correct!


"""
---------------------------------------------------------------------
8. CLOSURES OVER MUTABLE OBJECTS: NO nonlocal NEEDED  ⭐⭐
---------------------------------------------------------------------
`nonlocal` is only required to REBIND (reassign) a name. If the
captured variable is a MUTABLE object (like a list or dict), you can
mutate its CONTENTS from the inner function WITHOUT `nonlocal`,
because you're not reassigning the outer variable itself - just
changing what it points to internally.
---------------------------------------------------------------------
"""

print("\n--- Closures Over Mutable Objects (No nonlocal Needed) ---")

def make_appender():
    items = []                # a mutable list, captured by the closure
    def append_item(item):
        items.append(item)     # MUTATING, not REASSIGNING - no nonlocal needed!
        return items
    return append_item

appender = make_appender()
print(appender("first"))
print(appender("second"))
print(appender("third"))


"""
---------------------------------------------------------------------
9. PRACTICAL USE CASE: MEMOIZATION VIA A CLOSURE  ⭐⭐⭐
---------------------------------------------------------------------
A closure over a mutable dict is exactly how you could implement a
simple manual memoization cache - the SAME general idea behind
`functools.lru_cache`, but built by hand using closures.
---------------------------------------------------------------------
"""

print("\n--- Practical Use Case: Memoization via Closure ---")

def memoize(func):
    cache = {}                    # captured by the closure below
    def wrapper(*args):
        if args not in cache:
            print(f"  computing result for {args} (not cached)")
            cache[args] = func(*args)
        else:
            print(f"  using cached result for {args}")
        return cache[args]
    return wrapper

def slow_square(n):
    return n ** 2

fast_square = memoize(slow_square)
print("fast_square(5):", fast_square(5))
print("fast_square(5) again:", fast_square(5))    # cached!
print("fast_square(6):", fast_square(6))


"""
---------------------------------------------------------------------
10. PRACTICAL USE CASE: PARAMETERIZED PIPELINE STEPS  ⭐⭐⭐
---------------------------------------------------------------------
Closures are commonly used in data pipelines to generate specialized,
pre-configured transformation functions - e.g., building a family
of validator/converter functions from a shared template.
---------------------------------------------------------------------
"""

print("\n--- Practical Use Case: Parameterized Pipeline Steps ---")

def make_range_validator(min_val, max_val):
    """Returns a closure that validates a value is within a specific range."""
    def validator(value):
        return min_val <= value <= max_val
    return validator

is_valid_percentage = make_range_validator(0, 100)
is_valid_age = make_range_validator(0, 120)

print("is_valid_percentage(50):", is_valid_percentage(50))
print("is_valid_percentage(150):", is_valid_percentage(150))
print("is_valid_age(45):", is_valid_age(45))
print("is_valid_age(200):", is_valid_age(200))

# Using generated closures to filter a dataset
values = [25, 105, 50, -5, 99]
valid_values = [v for v in values if is_valid_percentage(v)]
print("\nfiltered using the generated closure:", valid_values)


"""
---------------------------------------------------------------------
11. CLOSURES KEEP THEIR CAPTURED VARIABLES ALIVE  ⭐⭐
---------------------------------------------------------------------
Because a closure holds a REFERENCE to its captured variable's cell,
that value is NOT garbage-collected just because the outer function
returned - Python keeps it alive for as long as the closure itself
exists. This is worth knowing for reasoning about MEMORY in
long-lived pipeline callbacks that capture large objects.
---------------------------------------------------------------------
"""

print("\n--- Closures Keep Captured Data Alive ---")

def make_large_data_processor():
    large_dataset = list(range(1_000_000))     # imagine this is huge
    def process(index):
        return large_dataset[index] * 2
    return process

processor = make_large_data_processor()
print("processor(500000):", processor(500000))
print("\nThe 'large_dataset' list is STILL alive in memory, held by")
print("the closure, even though make_large_data_processor() already")
print("returned. Be mindful of this when closures capture large")
print("objects in long-running pipeline code - it can prevent that")
print("memory from ever being freed while the closure exists.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
A closure requires:            1. a nested function
                                 2. that references an enclosing
                                    variable (a "free variable")
                                 3. and the outer function returns it

Reading an enclosing variable  -> no special keyword needed
Modifying an enclosing variable -> requires `nonlocal`
Mutating a captured MUTABLE       -> no `nonlocal` needed (not a
object's CONTENTS                   reassignment)

Inspecting a closure:
    func.__closure__                  -> tuple of cell objects
    func.__code__.co_freevars           -> names of captured variables
    func.__closure__[i].cell_contents     -> the actual captured value

Classic pitfall: closures in a loop share the SAME cell -> use a
default argument or an extra factory function to capture the
CURRENT value instead of a shared reference.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CLOSURES
=====================================================================

1. What are the three necessary conditions for a closure to exist in
   Python?

2. Given `make_counter()` in this file, explain how `counter_a` and
   `counter_b` (two SEPARATE calls to `make_counter_fixed()`)
   maintain completely independent state, despite sharing the exact
   same function source code.

3. Why does modifying a variable from an enclosing scope inside a
   nested function require the `nonlocal` keyword, while just
   READING it does not?

4. What error occurs if you try to do `count += 1` inside a nested
   function WITHOUT declaring `nonlocal count` first, and WHY does
   that specific error happen (in terms of how Python decides a
   variable is local)?

5. Explain the classic "closures in a loop" bug:
       fns = [lambda: i for i in range(3)]
   What will `[f() for f in fns]` produce, and why does this happen
   in terms of WHEN Python looks up the variable `i`?

6. What are TWO different ways to fix the closures-in-a-loop bug
   from question 5?

7. Do you need `nonlocal` to APPEND to a list captured by a closure
   (e.g., `items.append(x)` where `items` was defined in the
   enclosing scope)? Why or why not?

8. How would you inspect, at runtime, exactly what value(s) a given
   closure function has captured from its enclosing scope? (Hint:
   `__closure__`, `co_freevars`, `cell_contents`.)

9. Describe how you would implement a simple memoization
   (caching) decorator using a closure over a dictionary, WITHOUT
   using `functools.lru_cache`.

10. When would you choose to implement something as a closure
    versus as a small class with an `__init__` and one method? What
    are the trade-offs?

11. If a closure captures a very large object (e.g., a huge list or
    DataFrame) from its enclosing scope, does that object get
    garbage-collected once the enclosing function returns? Why is
    this important to consider in long-running pipeline code that
    creates many closures?

12. What is a "free variable" in the context of closures? How is
    it different from a regular local variable of the inner
    function itself?

13. In a data engineering context, describe a realistic use case
    for a closure-based "validator factory" (e.g.,
    `make_range_validator(min_val, max_val)`) that generates
    several specialized validation functions from one shared
    template.

14. Why does `iter(x) is x` return `True` for a closure-created
    generator but this question is unrelated to closures directly -
    instead: why does calling the SAME outer function multiple
    times always produce BRAND NEW, independent cell objects rather
    than reusing the same cells across calls?
=====================================================================
"""