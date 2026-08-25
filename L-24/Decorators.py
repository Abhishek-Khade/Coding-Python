"""
=====================================================================
PYTHON DECORATORS - Complete Notes with Executable Examples
=====================================================================

A decorator is a HIGHER-ORDER FUNCTION that takes a function (or
class) as input, WRAPS it with extra behavior, and returns a new
callable - all WITHOUT modifying the original function's own source
code.

    @my_decorator
    def my_function():
        ...

is just SYNTACTIC SUGAR for:

    def my_function():
        ...
    my_function = my_decorator(my_function)

For Data Engineers, decorators are the standard tool for adding
CROSS-CUTTING concerns to pipeline functions - logging, timing,
retries, validation, caching - without cluttering the actual
business logic of each function.
=====================================================================
"""

import time
import functools
import random

print("--- Overview ---")
print("@decorator is sugar for: func = decorator(func)")


"""
---------------------------------------------------------------------
1. THE SIMPLEST POSSIBLE DECORATOR  ⭐⭐⭐
---------------------------------------------------------------------
A decorator is just a function that:
    1. Takes a function as its ONE argument
    2. Defines an INNER function ("wrapper") that adds behavior
       before/after calling the original
    3. Returns that inner function
---------------------------------------------------------------------
"""

print("\n--- The Simplest Possible Decorator ---")

def shout_decorator(func):
    def wrapper():
        result = func()
        return result.upper()
    return wrapper

@shout_decorator
def greet():
    return "hello"

print("greet():", greet())

# Proving the @ syntax is literally just this, manually:
def greet_manual():
    return "hello"

greet_manual = shout_decorator(greet_manual)     # exactly what @ does
print("greet_manual() (manually decorated):", greet_manual())


"""
---------------------------------------------------------------------
2. DECORATING FUNCTIONS WITH ARGUMENTS: *args, **kwargs  ⭐⭐⭐
---------------------------------------------------------------------
A REAL decorator must work on functions with ANY signature - so the
wrapper needs *args/**kwargs to accept and forward whatever
arguments the original function expects.
---------------------------------------------------------------------
"""

print("\n--- Decorating Functions with Arguments ---")

def double_result(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result * 2
    return wrapper

@double_result
def add(a, b):
    return a + b

print("add(3, 4) doubled:", add(3, 4))


"""
---------------------------------------------------------------------
3. functools.wraps: PRESERVING METADATA  ⭐⭐⭐
---------------------------------------------------------------------
WITHOUT @functools.wraps, the decorated function LOSES its original
__name__, __doc__, and other metadata - it looks like it's actually
named "wrapper" everywhere (stack traces, help(), introspection
tools, logging). @functools.wraps fixes this by copying that
metadata from the original function onto the wrapper.
---------------------------------------------------------------------
"""

print("\n--- functools.wraps: Preserving Metadata ---")

def bad_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper           # metadata NOT preserved

def good_decorator(func):
    @functools.wraps(func)    # copies __name__, __doc__, etc. onto wrapper
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@bad_decorator
def process_orders_bad():
    """Processes all pending orders."""
    pass

@good_decorator
def process_orders_good():
    """Processes all pending orders."""
    pass

print("WITHOUT @wraps:")
print("  __name__:", process_orders_bad.__name__)     # 'wrapper' - WRONG!
print("  __doc__:", process_orders_bad.__doc__)         # None - lost!

print("\nWITH @wraps:")
print("  __name__:", process_orders_good.__name__)     # correct!
print("  __doc__:", process_orders_good.__doc__)         # preserved!


"""
---------------------------------------------------------------------
4. TIMING DECORATOR: MEASURING PIPELINE STEP DURATION  ⭐⭐⭐
---------------------------------------------------------------------
One of the most common real-world DE decorators - wrap any pipeline
step to automatically log how long it took, without touching that
step's own code.
---------------------------------------------------------------------
"""

print("\n--- Timing Decorator ---")

def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  [TIMER] '{func.__name__}' completed in {elapsed:.4f} sec")
        return result
    return wrapper

@timed
def extract_data(n):
    """Simulates extracting n records from a source."""
    time.sleep(0.05)          # simulate I/O latency
    return list(range(n))

@timed
def transform_data(records):
    """Simulates a transformation step."""
    time.sleep(0.02)
    return [r * 2 for r in records]

raw = extract_data(1000)
transformed = transform_data(raw)
print("pipeline result length:", len(transformed))


"""
---------------------------------------------------------------------
5. LOGGING DECORATOR: RECORDING CALLS, ARGS, AND RESULTS  ⭐⭐⭐
---------------------------------------------------------------------
Another extremely common DE pattern - automatically log every call
to a pipeline function, including its inputs and outputs, for
observability/debugging, without adding print/logging calls inside
every function's own body.
---------------------------------------------------------------------
"""

print("\n--- Logging Decorator ---")

def logged(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"  [LOG] calling {func.__name__}(args={args}, kwargs={kwargs})")
        try:
            result = func(*args, **kwargs)
            print(f"  [LOG] {func.__name__} succeeded, returned: {result!r}")
            return result
        except Exception as e:
            print(f"  [LOG] {func.__name__} FAILED with: {e!r}")
            raise            # re-raise so the error still propagates normally
    return wrapper

@logged
def load_record(record_id):
    if record_id < 0:
        raise ValueError("record_id cannot be negative")
    return {"id": record_id, "status": "loaded"}

print("load_record(5):")
load_record(5)

print("\nload_record(-1) (will fail and be logged):")
try:
    load_record(-1)
except ValueError:
    print("  (caller correctly received the re-raised exception)")


"""
---------------------------------------------------------------------
6. RETRY DECORATOR: HANDLING FLAKY OPERATIONS  ⭐⭐⭐
---------------------------------------------------------------------
Data pipelines frequently call flaky external systems (APIs,
databases, network resources). A retry decorator automatically
re-attempts a failed call up to N times, often with a DELAY between
attempts (and ideally EXPONENTIAL BACKOFF) - without cluttering the
actual business logic with try/except/retry loops.
---------------------------------------------------------------------
"""

print("\n--- Retry Decorator ---")

def retry(max_attempts=3, delay_seconds=0.1, backoff=2, exceptions=(Exception,)):
    """
    A DECORATOR FACTORY - it takes configuration arguments and
    RETURNS the actual decorator. This extra layer of nesting is
    required whenever a decorator itself needs to accept arguments.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay_seconds
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    print(f"  [RETRY] attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(current_delay)
                        current_delay *= backoff     # exponential backoff
            print(f"  [RETRY] all {max_attempts} attempts failed - giving up")
            raise last_exception
        return wrapper
    return decorator

# Simulating an unreliable external call (e.g., a flaky API)
call_attempts = {"count": 0}

@retry(max_attempts=4, delay_seconds=0.05, exceptions=(ConnectionError,))
def flaky_api_call():
    call_attempts["count"] += 1
    if call_attempts["count"] < 3:
        raise ConnectionError("simulated network failure")
    return "API response: success"

print("calling a flaky API through the retry decorator:")
result = flaky_api_call()
print("final result:", result)
print("total attempts made:", call_attempts["count"])


"""
---------------------------------------------------------------------
7. VALIDATION DECORATOR: ENFORCING PRECONDITIONS  ⭐⭐
---------------------------------------------------------------------
A decorator that checks the function's arguments (or its result)
BEFORE/AFTER the actual call - useful for enforcing data quality
rules at the boundary of a pipeline step.
---------------------------------------------------------------------
"""

print("\n--- Validation Decorator ---")

def validate_positive(*param_names):
    """A decorator factory: validates that named parameters are > 0."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Combine positional and keyword args into ONE dict to
            # check by parameter name, regardless of how they were passed
            import inspect
            bound = inspect.signature(func).bind(*args, **kwargs)
            bound.apply_defaults()
            for name in param_names:
                if bound.arguments.get(name, 1) <= 0:
                    raise ValueError(f"'{name}' must be positive, got {bound.arguments[name]}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@validate_positive("amount")
def process_payment(amount, currency="USD"):
    return f"processed {amount} {currency}"

print("process_payment(100):", process_payment(100))

try:
    process_payment(-50)
except ValueError as e:
    print("Error from validation decorator:", e)


"""
---------------------------------------------------------------------
8. STACKING MULTIPLE DECORATORS: APPLICATION ORDER  ⭐⭐⭐
---------------------------------------------------------------------
When multiple decorators are stacked, they apply BOTTOM-UP (the one
closest to the function runs FIRST, wrapping it; then the next one
wraps THAT result, and so on) - but at CALL time, execution flows
TOP-DOWN through the wrappers.

    @decorator_a
    @decorator_b
    def func(): ...

is equivalent to:  func = decorator_a(decorator_b(func))
---------------------------------------------------------------------
"""

print("\n--- Stacking Multiple Decorators ---")

def decorator_a(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  entering decorator_a")
        result = func(*args, **kwargs)
        print("  exiting decorator_a")
        return result
    return wrapper

def decorator_b(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  entering decorator_b")
        result = func(*args, **kwargs)
        print("  exiting decorator_b")
        return result
    return wrapper

@decorator_a
@decorator_b
def core_function():
    print("  running core_function")
    return "done"

print("calling core_function() with stacked decorators:")
core_function()

print("""
Execution order observed:
    entering decorator_a   <- outermost decorator runs FIRST at call time
    entering decorator_b   <- then the next one in
    running core_function  <- the actual function
    exiting decorator_b     <- unwinds in REVERSE order
    exiting decorator_a
""")


"""
---------------------------------------------------------------------
9. COMBINING MULTIPLE REAL-WORLD DECORATORS ON ONE FUNCTION  ⭐⭐⭐
---------------------------------------------------------------------
In practice, pipeline functions often stack SEVERAL of these
decorators together - e.g., time it, retry it, AND log it, all on
one function.
---------------------------------------------------------------------
"""

print("\n--- Combining Real-World Decorators ---")

attempt_tracker = {"count": 0}

@timed
@retry(max_attempts=2, delay_seconds=0.02, exceptions=(RuntimeError,))
@logged
def fetch_and_process(source_id):
    attempt_tracker["count"] += 1
    if attempt_tracker["count"] < 2:
        raise RuntimeError("transient failure")
    return f"processed source {source_id}"

print("calling a fully decorated pipeline function:")
final_result = fetch_and_process(42)
print("final_result:", final_result)


"""
---------------------------------------------------------------------
10. CLASS-BASED DECORATORS: USING __call__  ⭐⭐
---------------------------------------------------------------------
A decorator doesn't have to be a function - any CALLABLE works. A
class implementing __call__ can act as a decorator too, and is
sometimes preferred when the decorator needs to maintain more
complex internal STATE (e.g., a call counter) across invocations.
---------------------------------------------------------------------
"""

print("\n--- Class-Based Decorators ---")

class CallCounter:
    """A class-based decorator that counts how many times a function is called."""
    def __init__(self, func):
        functools.update_wrapper(self, func)   # class equivalent of @wraps
        self.func = func
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        print(f"  '{self.func.__name__}' has now been called {self.call_count} time(s)")
        return self.func(*args, **kwargs)

@CallCounter
def process_batch(batch_id):
    return f"batch {batch_id} processed"

process_batch(1)
process_batch(2)
process_batch(3)
print("total calls recorded:", process_batch.call_count)


"""
---------------------------------------------------------------------
11. DECORATING METHODS INSIDE A CLASS  ⭐⭐
---------------------------------------------------------------------
Decorators work on instance methods too - the wrapper's *args
automatically captures 'self' as the first positional argument,
since Python passes it just like any other argument.
---------------------------------------------------------------------
"""

print("\n--- Decorating Methods Inside a Class ---")

class DataPipeline:
    @timed
    @logged
    def run_step(self, step_name):
        time.sleep(0.01)
        return f"completed step: {step_name}"

pipeline = DataPipeline()
pipeline.run_step("extract")


"""
---------------------------------------------------------------------
12. MEMOIZATION/CACHING DECORATOR: functools.lru_cache  ⭐⭐⭐
---------------------------------------------------------------------
A built-in decorator that automatically caches a PURE function's
results, skipping recomputation for repeated calls with the same
arguments - already covered in the Functional Programming file, but
worth recapping here as a real-world decorator example.
---------------------------------------------------------------------
"""

print("\n--- functools.lru_cache Recap ---")

compute_count = {"count": 0}

@functools.lru_cache(maxsize=128)
def expensive_lookup(key):
    compute_count["count"] += 1
    return key.upper()

expensive_lookup("abc")
expensive_lookup("abc")        # cached - function body does NOT re-run
expensive_lookup("xyz")
print("actual function executions:", compute_count["count"])   # 2, not 3


"""
---------------------------------------------------------------------
13. COMMON PITFALLS  ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Common Pitfalls ---")

# Pitfall 1: forgetting *args/**kwargs -> decorator breaks on any
# function that takes arguments
def broken_decorator(func):
    def wrapper():          # no *args/**kwargs!
        return func()
    return wrapper

@broken_decorator
def needs_an_argument(x):
    return x * 2

try:
    needs_an_argument(5)
except TypeError as e:
    print("Error: decorator without *args/**kwargs breaks argument-taking functions:", e)

# Pitfall 2: forgetting to RETURN the wrapper (or the result) from
# inside the decorator - silently breaks the function's return value
def forgot_to_return(func):
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)     # called, but result is discarded!
        # missing: return ...
    return wrapper

@forgot_to_return
def compute_value():
    return 42

print("\nresult when decorator forgets to return the value:",
      compute_value())      # None, even though compute_value() returns 42!

# Pitfall 3: decorator factories WITHOUT the extra nesting level -
# a decorator that needs ARGUMENTS must have THREE levels of nested
# functions (factory -> decorator -> wrapper), easy to get wrong
print("\nDecorator WITH arguments needs 3 nested levels:")
print("  def decorator_factory(config):      # level 1: takes config")
print("      def decorator(func):             # level 2: takes the function")
print("          def wrapper(*a, **kw):        # level 3: does the actual work")
print("              ...")
print("          return wrapper")
print("      return decorator")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
@my_decorator
def f(): ...              is sugar for:  f = my_decorator(f)

Decorator template (no arguments):
    def my_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # before
            result = func(*args, **kwargs)
            # after
            return result
        return wrapper

Decorator FACTORY template (accepts arguments, e.g. @retry(times=3)):
    def my_decorator(config_arg):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # use config_arg here
                return func(*args, **kwargs)
            return wrapper
        return decorator

Common real-world DE decorators: @timed, @logged, @retry(...),
@validate_positive(...), @functools.lru_cache
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON DECORATORS
=====================================================================

1. What does `@my_decorator` above a function definition actually
   translate to, in terms of plain function calls and reassignment?

2. Why must a general-purpose decorator's inner `wrapper` function
   accept `*args, **kwargs`? What breaks if it doesn't?

3. What does `functools.wraps` do, and what specifically goes wrong
   (in terms of `__name__`, `__doc__`, introspection) if you omit it
   from a decorator?

4. What is a "decorator factory" (a decorator that itself takes
   configuration arguments, like `@retry(max_attempts=3)`)? How many
   levels of nested functions does it require, and why?

5. If you stack two decorators:
       @decorator_a
       @decorator_b
       def func(): ...
   in what ORDER do they wrap the function, and in what order does
   execution actually flow when `func()` is called?

6. Design a `@retry` decorator that retries a function up to N times
   on failure, with a configurable delay between attempts. What
   exceptions should it catch, and why is catching a broad
   `Exception` sometimes risky in this context?

7. How would you write a decorator that TIMES a function's
   execution and logs it, without modifying the function's own
   code at all?

8. Can a decorator be implemented as a CLASS instead of a function?
   What special method must that class define to make an instance
   callable, and when might a class-based decorator be preferable
   (e.g., needing to maintain state across calls)?

9. If a decorated function is actually a METHOD inside a class
   (e.g., `self.run_step(...)`), does the decorator need any special
   handling for `self`? Why or why not?

10. What happens if a decorator's `wrapper` function forgets to
    `return` the result of calling the original function? How would
    this bug manifest to someone USING the decorated function?

11. How does `functools.lru_cache` work as a decorator, and what
    KIND of function (in terms of purity/side effects) is it safe
    to apply to?

12. Why might you choose to write a custom `@validate_positive(...)`
    style decorator to enforce preconditions on pipeline function
    arguments, rather than putting `if` checks inside every
    function's body?

13. In a data engineering context, describe a realistic scenario
    where you'd stack THREE decorators on a single pipeline function
    (e.g., timing + retry + logging). Why is this cleaner than
    writing all that logic manually inside the function itself?

14. What's the difference between a decorator that takes NO
    arguments (`@my_decorator`) and one that takes arguments
    (`@my_decorator(some_arg)`) in terms of how many function calls
    happen before the actual wrapping takes place?
=====================================================================
"""