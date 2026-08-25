"""
=====================================================================
PYTHON GENERATORS & yield - Complete Notes with Executable Examples
=====================================================================

A generator is a special kind of function that produces a sequence
of values LAZILY - one at a time, ON DEMAND - instead of computing
and returning them all at once. It uses `yield` instead of `return`.

This is THE single most important tool for memory-efficient
processing of large datasets in Python: a generator can represent
an "infinite" or huge stream of data while using only a CONSTANT,
tiny amount of memory - because it never holds more than "the
current item" in memory at once.

TOPICS COVERED:
    1. What makes a function a generator: yield vs return
    2. How generators pause and resume (execution state)
    3. Manually driving a generator with next() and StopIteration
    4. Memory comparison: generator vs list, at massive scale
    5. Infinite generators
    6. yield from - delegating to sub-generators
    7. Generator expressions (recap)
    8. Two-way communication: .send(), .throw(), .close()
    9. Chaining generators into a lazy processing pipeline
    10. Reading a huge file lazily - the real-world DE use case
    11. The iterator protocol vs generator functions
    12. Common pitfalls
=====================================================================
"""

import sys
import time

print("--- Overview ---")
print("A generator produces values LAZILY, one at a time, using")
print("`yield` - using constant memory regardless of how many")
print("values it will eventually produce.")


"""
---------------------------------------------------------------------
1. yield vs return: WHAT MAKES A FUNCTION A GENERATOR  ⭐⭐⭐
---------------------------------------------------------------------
Any function containing at least ONE `yield` statement is a
GENERATOR FUNCTION. Calling it does NOT run its body at all - it
immediately returns a generator OBJECT. The body only starts
executing once you begin pulling values from that object (via
next(), a for-loop, list(), etc.).
---------------------------------------------------------------------
"""

print("\n--- yield vs return ---")

def normal_function():
    print("  normal_function: running now")
    return [1, 2, 3]           # computes AND returns everything at once

def generator_function():
    print("  generator_function: yielding 1")
    yield 1
    print("  generator_function: yielding 2")
    yield 2
    print("  generator_function: yielding 3")
    yield 3

print("calling normal_function():")
result1 = normal_function()          # body runs IMMEDIATELY
print("result:", result1)

print("\ncalling generator_function():")
result2 = generator_function()        # body does NOT run yet!
print("result:", result2, "| type:", type(result2))
print("(notice: NO print statements from inside the function ran yet)")


"""
---------------------------------------------------------------------
2. HOW GENERATORS PAUSE AND RESUME: EXECUTION STATE  ⭐⭐⭐
---------------------------------------------------------------------
Each call to next(generator) runs the function's body UNTIL it hits
the next `yield`, at which point execution PAUSES (the entire
function's local state - variables, loop position - is preserved).
The NEXT call to next() resumes execution right where it left off.
---------------------------------------------------------------------
"""

print("\n--- Pausing and Resuming: Manual next() Calls ---")

gen = generator_function()

print("calling next() #1:")
print("  ->", next(gen))

print("calling next() #2:")
print("  ->", next(gen))

print("calling next() #3:")
print("  ->", next(gen))

print("\ncalling next() #4 (nothing left to yield):")
try:
    next(gen)
except StopIteration:
    print("  -> StopIteration raised: the generator is exhausted")


"""
---------------------------------------------------------------------
3. GENERATORS MAINTAIN LOCAL STATE ACROSS YIELDS  ⭐⭐⭐
---------------------------------------------------------------------
Unlike a normal function (whose local variables disappear the
moment it returns), a generator's LOCAL VARIABLES and its EXACT
position in a loop are all preserved between yields - this is what
makes step-by-step, stateful lazy computation possible.
---------------------------------------------------------------------
"""

print("\n--- Generators Maintain State Across Yields ---")

def running_total_generator(numbers):
    total = 0                    # this variable PERSISTS across yields
    for n in numbers:
        total += n
        yield total               # yields the RUNNING total each time

for value in running_total_generator([10, 20, 30, 40]):
    print("running total:", value)


"""
---------------------------------------------------------------------
4. FOR-LOOPS AUTOMATICALLY HANDLE StopIteration  ⭐⭐
---------------------------------------------------------------------
A `for` loop over a generator calls next() repeatedly under the
hood, and automatically stops (without an error) when it catches
StopIteration - you rarely need to call next() manually in real code.
---------------------------------------------------------------------
"""

print("\n--- for-loops and StopIteration ---")

def countdown(n):
    while n > 0:
        yield n
        n -= 1

print("counting down with a for-loop:")
for num in countdown(5):
    print(" ", num)


"""
---------------------------------------------------------------------
5. MEMORY COMPARISON: GENERATOR vs LIST AT SCALE  ⭐⭐⭐
---------------------------------------------------------------------
This is the CORE reason generators matter for data engineering: a
generator representing a MILLION (or a BILLION) items uses the
SAME tiny amount of memory as one representing just ONE item -
because it never materializes more than the current value.
---------------------------------------------------------------------
"""

print("\n--- Memory Comparison: Generator vs List ---")

def number_generator(n):
    for i in range(n):
        yield i

list_version = [i for i in range(10_000_000)]
gen_version = number_generator(10_000_000)

print(f"list of 10,000,000 ints:  {sys.getsizeof(list_version):,} bytes")
print(f"generator (same count):    {sys.getsizeof(gen_version)} bytes")
print("\nThe generator's memory footprint DOES NOT scale with the")
print("number of items it will eventually produce.")


"""
---------------------------------------------------------------------
6. INFINITE GENERATORS  ⭐⭐⭐
---------------------------------------------------------------------
Because a generator only computes ONE value at a time, it can
represent a THEORETICALLY INFINITE sequence - something completely
impossible to represent as an actual list (which would need
infinite memory). You simply stop pulling values whenever you want.
---------------------------------------------------------------------
"""

print("\n--- Infinite Generators ---")

def infinite_counter(start=0):
    n = start
    while True:                # no termination condition - runs forever
        yield n
        n += 1

counter = infinite_counter(1)
first_five = [next(counter) for _ in range(5)]
print("first 5 values from an INFINITE generator:", first_five)

# Consuming an infinite generator with a manual break condition
print("\ntaking values until one exceeds 20:")
counter2 = infinite_counter(1)
for value in counter2:
    if value > 20:
        break
    print(" ", value, end="")
print()


"""
---------------------------------------------------------------------
7. yield from: DELEGATING TO A SUB-GENERATOR  ⭐⭐⭐
---------------------------------------------------------------------
`yield from` delegates iteration to ANOTHER iterable/generator,
yielding each of ITS values in turn - avoiding a manual nested loop
with an explicit `for ... yield`. Extremely useful for flattening
nested generators or composing generator functions.
---------------------------------------------------------------------
"""

print("\n--- yield from: Delegating to a Sub-Generator ---")

def inner_generator():
    yield 1
    yield 2
    yield 3

def outer_without_yield_from():
    for value in inner_generator():     # manual delegation
        yield value
    yield 4

def outer_with_yield_from():
    yield from inner_generator()          # equivalent, more concise
    yield 4

print("manual delegation:", list(outer_without_yield_from()))
print("yield from delegation:", list(outer_with_yield_from()))

# yield from also works directly on any iterable, not just generators
def flatten_lists(list_of_lists):
    for sublist in list_of_lists:
        yield from sublist          # delegates to each sublist directly

nested = [[1, 2], [3, 4, 5], [6]]
print("\nflattening nested lists with yield from:", list(flatten_lists(nested)))


"""
---------------------------------------------------------------------
8. GENERATOR EXPRESSIONS: THE LAZY COMPREHENSION SYNTAX (RECAP)  ⭐⭐
---------------------------------------------------------------------
Syntax: (expr for item in iterable if condition) - parentheses
instead of square brackets. Functionally equivalent to writing a
tiny one-line generator function, but more compact for simple cases.
---------------------------------------------------------------------
"""

print("\n--- Generator Expressions (Recap) ---")

gen_expr = (x ** 2 for x in range(5))
print("generator expression:", gen_expr)
print("consumed:", list(gen_expr))

# Passed directly into a function expecting an iterable - no extra
# parentheses needed when it's the ONLY argument
total = sum(x ** 2 for x in range(1, 6))
print("sum() consuming a generator expression directly:", total)


"""
---------------------------------------------------------------------
9. TWO-WAY COMMUNICATION: .send(), .throw(), .close()  ⭐⭐
---------------------------------------------------------------------
Generators aren't purely one-directional. `.send(value)` resumes
the generator AND passes `value` in as the RESULT of the CURRENT
`yield` expression - enabling basic coroutine-like patterns.
`.throw()` raises an exception INSIDE the generator at its paused
point. `.close()` stops the generator early, raising GeneratorExit
inside it.
---------------------------------------------------------------------
"""

print("\n--- Two-Way Communication: .send() ---")

def running_average():
    total = 0
    count = 0
    average = None
    while True:
        value = yield average    # pauses here; .send() resumes with a value
        total += value
        count += 1
        average = total / count

avg_gen = running_average()
next(avg_gen)                       # "prime" the generator - advance to the first yield

print("send(10):", avg_gen.send(10))
print("send(20):", avg_gen.send(20))
print("send(30):", avg_gen.send(30))

# .close() stops a generator early
avg_gen.close()
try:
    avg_gen.send(40)          # generator is now closed - raises StopIteration
except StopIteration:
    print("\ngenerator correctly stopped after .close()")


"""
---------------------------------------------------------------------
10. CHAINING GENERATORS: A LAZY DATA PROCESSING PIPELINE  ⭐⭐⭐
---------------------------------------------------------------------
Real ETL code frequently chains several generator functions
together, where each stage LAZILY processes one item at a time and
passes it to the next stage - NOTHING is computed until the final
consumer (a for-loop, list(), sum(), etc.) actually pulls a value
through the entire chain.
---------------------------------------------------------------------
"""

print("\n--- Chaining Generators: A Lazy Pipeline ---")

def read_raw_lines(lines):
    """Stage 1: simulate reading raw lines from a huge log file."""
    for line in lines:
        yield line.strip()

def parse_log_line(lines):
    """Stage 2: parse each line into a structured record."""
    for line in lines:
        timestamp, level, message = line.split(" ", 2)
        yield {"timestamp": timestamp, "level": level, "message": message}

def filter_errors(records):
    """Stage 3: keep only ERROR-level records."""
    for record in records:
        if record["level"] == "ERROR":
            yield record

raw_log_lines = [
    "2026-08-13T10:00:00 INFO startup complete\n",
    "2026-08-13T10:01:00 ERROR connection failed\n",
    "2026-08-13T10:02:00 INFO heartbeat\n",
    "2026-08-13T10:03:00 ERROR timeout occurred\n",
]

# Build the pipeline - NOTHING has run yet, this just wires up
# generator objects
pipeline = filter_errors(parse_log_line(read_raw_lines(raw_log_lines)))

print("pulling results through the entire lazy pipeline:")
for error_record in pipeline:
    print(" ", error_record)


"""
---------------------------------------------------------------------
11. READING A HUGE FILE LAZILY: THE CLASSIC DE USE CASE  ⭐⭐⭐
---------------------------------------------------------------------
Iterating a real file object with a `for` loop is ALREADY generator-
based - Python reads ONE line at a time from disk, never loading
the entire file into memory. This is the single most common
real-world application of the generator concept in data engineering.
---------------------------------------------------------------------
"""

print("\n--- Reading a Huge File Lazily (Real DE Pattern) ---")

# Create a sample file to demonstrate with
sample_path = "/tmp/sample_large_log.txt"
with open(sample_path, "w") as f:
    for i in range(100_000):
        f.write(f"2026-08-13 INFO event_{i}\n")

def count_matching_lines(filepath, keyword):
    """Processes a file LINE BY LINE - constant memory, regardless
    of the file's total size (could be gigabytes)."""
    count = 0
    with open(filepath) as f:
        for line in f:            # this IS a generator-based iteration
            if keyword in line:
                count += 1
    return count

matches = count_matching_lines(sample_path, "event_9")
print(f"lines containing 'event_9': {matches}")
print("\nThis approach uses CONSTANT memory whether the file is")
print("100KB or 100GB - only ONE line is ever in memory at a time.")

import os
os.remove(sample_path)


"""
---------------------------------------------------------------------
12. THE ITERATOR PROTOCOL: WHAT A GENERATOR ACTUALLY IS  ⭐⭐⭐
---------------------------------------------------------------------
A generator is really just a CONVENIENT SHORTCUT for building an
object that implements the ITERATOR PROTOCOL - i.e., an object with
BOTH `__iter__` (returns itself) AND `__next__` (produces the next
value or raises StopIteration) methods. You can build the same thing
manually with a class - `yield` just does it automatically for you.
---------------------------------------------------------------------
"""

print("\n--- The Iterator Protocol: Manual Equivalent ---")

# The manual, CLASS-BASED equivalent of a simple generator
class CountdownIterator:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self               # an iterator returns ITSELF

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value

print("class-based iterator (manual, verbose):")
for value in CountdownIterator(3):
    print(" ", value)

# The SAME behavior, but as a generator function - far less code
def countdown_generator(start):
    current = start
    while current > 0:
        yield current
        current -= 1

print("\ngenerator function (automatic, concise):")
for value in countdown_generator(3):
    print(" ", value)

print("\nBoth satisfy the iterator protocol - generators just do it")
print("automatically, without writing __iter__/__next__ by hand.")


"""
---------------------------------------------------------------------
13. COMMON PITFALLS  ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Common Pitfalls ---")

# Pitfall 1: generators are SINGLE-USE - once exhausted, they stay
# exhausted; you must create a NEW generator to iterate again
gen = (x for x in range(3))
print("first consumption:", list(gen))
print("second consumption of the SAME generator (empty!):", list(gen))

# Pitfall 2: you CANNOT get len() of a generator, or index into it -
# it has no defined length until fully consumed
gen2 = (x for x in range(5))
try:
    len(gen2)
except TypeError as e:
    print("\nError: generators have no len():", e)

gen3 = (x for x in range(5))
try:
    gen3[0]
except TypeError as e:
    print("Error: generators don't support indexing:", e)

# Pitfall 3: a generator's body only starts running on the FIRST
# next() call - exceptions inside it are NOT raised until then, not
# at generator-creation time (a common source of confusing bugs)
def risky_generator():
    yield 1 / 0        # ZeroDivisionError, but NOT yet!

g = risky_generator()             # NO error here - body hasn't run
print("\ngenerator created successfully (error not yet triggered):", g)
try:
    next(g)                        # error occurs HERE, on first next()
except ZeroDivisionError as e:
    print("Error only appears once the generator actually runs:", e)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
`yield`               -> makes a function a generator; pauses execution,
                         preserving local state, until the next value
                         is requested
next(gen)              -> resumes execution until the next yield (or
                         raises StopIteration if exhausted)
for x in gen:            -> automatically calls next() repeatedly,
                         stopping cleanly on StopIteration
yield from sub_gen         -> delegates iteration to another
                         iterable/generator
gen.send(value)              -> resumes the generator, injecting
                         `value` as the result of the paused yield
gen.close()                    -> stops the generator early
(x for x in iterable)             -> a generator EXPRESSION (lazy,
                         inline, comprehension-style syntax)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - GENERATORS & yield
=====================================================================

1. What makes a function a "generator function" in Python? What
   does CALLING that function actually do - does its body run
   immediately?

2. What is the key difference in behavior between `return` and
   `yield`? What happens to a generator function's LOCAL VARIABLES
   between successive calls to `next()`?

3. Why does a generator use dramatically less memory than an
   equivalent list, especially for very large or infinite sequences?
   Demonstrate this conceptually with `sys.getsizeof()`.

4. What exception is raised when a generator is fully exhausted and
   `next()` is called on it again? How does a `for` loop handle this
   automatically?

5. Can a generator represent an "infinite" sequence? Why can't a
   list do the same thing?

6. What does `yield from` do, and how is it different from writing
   a manual `for item in sub_generator: yield item` loop?

7. What is `.send(value)` used for on a generator? What does it mean
   to "prime" a generator with an initial `next()` call before using
   `.send()`?

8. Why can't you call `len()` on a generator, or access an item by
   index (`gen[0]`)? What does this tell you about what a generator
   actually "knows" about its own contents?

9. If a generator function contains a bug that would raise an
   exception (e.g., division by zero) inside its body, WHEN does
   that exception actually get raised - at generator creation time,
   or at some later point? Why?

10. Explain the ITERATOR PROTOCOL (`__iter__` and `__next__`). How
    does a generator function relate to this protocol - is it
    "cheating," or does it genuinely implement the same interface?

11. Why is reading a file with `for line in file:` already a
    generator-based, memory-efficient operation? How does this
    scale to a 100GB file versus a 100KB file, memory-wise?

12. How would you build a LAZY data processing pipeline out of
    several chained generator functions (e.g., read -> parse ->
    filter), and why is nothing actually computed until the final
    consumer (like a for-loop or `list()`) pulls values through it?

13. What's the difference between a generator FUNCTION (defined with
    `def` and `yield`) and a generator EXPRESSION (the
    `(x for x in ...)` syntax)? When would you prefer one over the
    other?

14. In a data engineering context, why would you use a generator
    instead of a list comprehension when processing a dataset too
    large to fit in memory - e.g., streaming rows from a database
    cursor or reading a massive CSV file line by line?

15. Can you re-use (iterate a second time over) an already-exhausted
    generator object? What would you need to do instead if you
    needed to iterate over the same sequence of values twice?
=====================================================================
"""