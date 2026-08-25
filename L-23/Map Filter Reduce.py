"""
=====================================================================
map(), filter(), reduce() - Complete Notes with Executable Examples
=====================================================================

These three built-ins are the classic "functional trio" for
processing iterables WITHOUT writing an explicit for-loop:

    map(func, iterable)       -> applies func to EVERY item,
                                  LAZILY, one at a time
    filter(func, iterable)     -> keeps only items where func(item)
                                  is truthy, LAZILY
    functools.reduce(func,      -> cumulatively combines ALL items
        iterable)                  into a SINGLE final result, EAGERLY
                                  (it must consume the whole iterable
                                  immediately to produce its answer)

map() and filter() are BUILT-IN functions (always available).
reduce() was moved to the `functools` module in Python 3 (it used
to be a built-in in Python 2) - this is itself a common interview
trivia question.
=====================================================================
"""

import time
from functools import reduce

print("--- Overview ---")
print("map()    -> transform every item, lazily")
print("filter() -> keep some items, lazily")
print("reduce() -> combine all items into one result, eagerly")


"""
---------------------------------------------------------------------
1. map(): APPLYING A FUNCTION TO EVERY ITEM  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  map(function, iterable)

Returns a LAZY map object (an iterator) - the function is NOT
actually applied to anything until you consume the result (e.g.,
with list(), a for-loop, or next()).
---------------------------------------------------------------------
"""

print("\n--- map(): Basics ---")

numbers = [1, 2, 3, 4, 5]

def square(x):
    return x ** 2

# Using a NAMED function
squared = map(square, numbers)
print("map() returns a lazy object:", squared, "| type:", type(squared))
print("materialized with list():", list(squared))

# Using a lambda - the most common style for one-off transformations
doubled = list(map(lambda x: x * 2, numbers))
print("map() with lambda (doubled):", doubled)

# map() over MULTIPLE iterables at once - the function receives
# ONE item from EACH iterable per call, positionally paired
list1 = [1, 2, 3]
list2 = [10, 20, 30]
summed_pairs = list(map(lambda a, b: a + b, list1, list2))
print("\nmap() over two iterables (paired addition):", summed_pairs)

# Just like zip(), map() with multiple iterables stops at the
# SHORTEST one - no error, silent truncation
short_list = [1, 2]
long_list = [10, 20, 30, 40]
truncated_map = list(map(lambda a, b: a + b, short_list, long_list))
print("map() truncates to shortest iterable:", truncated_map)


"""
---------------------------------------------------------------------
2. map() IS LAZY: PROVING IT, AND WHY IT MATTERS  ⭐⭐⭐
---------------------------------------------------------------------
Because map() is lazy, the function you pass in is NOT called for
every item upfront - it's called ON DEMAND, as each result is
requested. This is critical for processing huge or streamed data
without loading everything into memory at once.
---------------------------------------------------------------------
"""

print("\n--- map() is Lazy: Proof ---")

call_log = []

def logged_square(x):
    call_log.append(x)          # records EVERY time the function actually runs
    return x ** 2

lazy_map = map(logged_square, [1, 2, 3, 4, 5])
print("map object created - has the function run yet?")
print("call_log so far (should be EMPTY):", call_log)

first_value = next(lazy_map)      # pull just ONE value
print("\nafter pulling ONE value with next():")
print("call_log (should show only ONE call):", call_log)
print("first_value:", first_value)

remaining = list(lazy_map)          # consume the REST
print("\nafter consuming the rest:")
print("call_log (now shows ALL 5 calls):", call_log)
print("remaining values:", remaining)


"""
---------------------------------------------------------------------
3. map() OBJECTS ARE SINGLE-USE (EXHAUSTIBLE)  ⭐⭐⭐
---------------------------------------------------------------------
Like any iterator, a map object can only be consumed ONCE. After
you've iterated over it fully, it's "exhausted" - trying to iterate
again produces NOTHING, silently (no error).
---------------------------------------------------------------------
"""

print("\n--- map() Objects are Single-Use ---")

m = map(lambda x: x * 10, [1, 2, 3])
print("first consumption:", list(m))
print("second consumption of the SAME map object (empty!):", list(m))


"""
---------------------------------------------------------------------
4. filter(): KEEPING ONLY MATCHING ITEMS  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  filter(function, iterable)

Keeps only the items for which function(item) returns a TRUTHY
value. Also returns a LAZY iterator, just like map().
---------------------------------------------------------------------
"""

print("\n--- filter(): Basics ---")

nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def is_even(x):
    return x % 2 == 0

evens = filter(is_even, nums)
print("filter() returns a lazy object:", evens, "| type:", type(evens))
print("materialized with list():", list(evens))

# With a lambda
odds = list(filter(lambda x: x % 2 != 0, nums))
print("filter() with lambda (odds):", odds)

# filter() is lazy too, and single-use, just like map() - same
# caveats apply as demonstrated above for map()


"""
---------------------------------------------------------------------
5. filter(None, iterable): THE "REMOVE FALSY VALUES" IDIOM  ⭐⭐⭐
---------------------------------------------------------------------
Passing None (instead of a function) as filter()'s first argument is
special-cased: it removes all FALSY values (0, "", None, False,
[], etc.) from the iterable, keeping only truthy ones. A common,
slightly obscure idiom worth recognizing.
---------------------------------------------------------------------
"""

print("\n--- filter(None, ...): Removing Falsy Values ---")

messy_data = [1, 0, "hello", "", None, [1, 2], [], False, True, 3.14]

cleaned = list(filter(None, messy_data))
print("original:", messy_data)
print("after filter(None, ...):", cleaned)

print("\nThis is equivalent to:", [x for x in messy_data if x])


"""
---------------------------------------------------------------------
6. functools.reduce(): COMBINING ALL ITEMS INTO ONE RESULT  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  reduce(function, iterable, initial_value=<optional>)

The function must take TWO arguments: (accumulator, next_item), and
return the NEW accumulator value. reduce() applies this repeatedly,
carrying the running result forward, until the iterable is
exhausted, ending with ONE final value.

Unlike map()/filter(), reduce() is EAGER - it must process the
entire iterable immediately to produce its single result; there's
nothing to "lazily" return partway through.
---------------------------------------------------------------------
"""

print("\n--- functools.reduce(): Basics ---")

numbers = [1, 2, 3, 4, 5]

total = reduce(lambda acc, x: acc + x, numbers)
print("reduce() sum:", total)

product = reduce(lambda acc, x: acc * x, numbers)
print("reduce() product:", product)

maximum = reduce(lambda acc, x: acc if acc > x else x, numbers)
print("reduce() max (without using max()):", maximum)


"""
---------------------------------------------------------------------
7. reduce() STEP BY STEP: WATCHING THE ACCUMULATOR  ⭐⭐⭐
---------------------------------------------------------------------
Understanding reduce() deeply means tracing exactly what happens on
each step - this is THE most common way interviewers probe whether
a candidate truly understands it, versus just having memorized the
syntax.
---------------------------------------------------------------------
"""

print("\n--- reduce() Step by Step ---")

def traced_add(acc, x):
    print(f"  called with acc={acc}, x={x} -> returns {acc + x}")
    return acc + x

print("reduce(traced_add, [1, 2, 3, 4]):")
result = reduce(traced_add, [1, 2, 3, 4])
print("final result:", result)

print("""
Step-by-step trace of what happened above:
    Step 1: acc=1 (first item, no initial value given), x=2 -> 3
    Step 2: acc=3, x=3 -> 6
    Step 3: acc=6, x=4 -> 10
    Final result: 10
""")


"""
---------------------------------------------------------------------
8. reduce() WITH AN EXPLICIT INITIAL VALUE  ⭐⭐⭐
---------------------------------------------------------------------
If you provide a THIRD argument, reduce() uses it as the STARTING
accumulator value (instead of using the iterable's first item as
the starting point). This also makes reduce() behave SAFELY on an
EMPTY iterable - without an initial value, reduce() on an empty
iterable raises a TypeError.
---------------------------------------------------------------------
"""

print("\n--- reduce() with an Initial Value ---")

# Without initial value - starts from the first item
sum_no_initial = reduce(lambda acc, x: acc + x, [1, 2, 3])
print("reduce without initial value:", sum_no_initial)

# WITH an initial value - starts the accumulator at 100
sum_with_initial = reduce(lambda acc, x: acc + x, [1, 2, 3], 100)
print("reduce with initial value 100:", sum_with_initial)

# Safety: reduce() on an EMPTY list without an initial value raises
# an error, but WITH an initial value it safely returns that value
try:
    reduce(lambda acc, x: acc + x, [])         # no initial value -> crashes
except TypeError as e:
    print("\nError: reduce() on empty iterable with NO initial value:", e)

safe_empty_result = reduce(lambda acc, x: acc + x, [], 0)   # safe with initial value
print("reduce() on empty iterable WITH initial value 0:", safe_empty_result)


"""
---------------------------------------------------------------------
9. reduce() FOR NON-NUMERIC AGGREGATION  ⭐⭐
---------------------------------------------------------------------
reduce() isn't just for sums/products - it can combine ANY sequence
of values into a single result: strings, lists, dicts, custom
objects.
---------------------------------------------------------------------
"""

print("\n--- reduce() for Non-Numeric Aggregation ---")

words = ["Data", "Engineering", "with", "Python"]
sentence = reduce(lambda acc, w: acc + " " + w, words)
print("reduce() building a sentence:", sentence)

# Flattening a list of lists using reduce()
nested = [[1, 2], [3, 4], [5, 6]]
flattened = reduce(lambda acc, sublist: acc + sublist, nested, [])
print("reduce() flattening nested lists:", flattened)

# Merging a list of dicts into one dict using reduce()
dict_list = [{"a": 1}, {"b": 2}, {"a": 3, "c": 4}]
merged = reduce(lambda acc, d: {**acc, **d}, dict_list, {})
print("reduce() merging dicts (later keys win):", merged)

# Finding the record with the max value in a list of dicts
records = [{"name": "Bob", "score": 75}, {"name": "Amy", "score": 92}, {"name": "Cid", "score": 60}]
top_scorer = reduce(lambda acc, r: r if r["score"] > acc["score"] else acc, records)
print("reduce() finding max record:", top_scorer)


"""
---------------------------------------------------------------------
10. COMBINING map(), filter(), AND reduce() INTO A PIPELINE  ⭐⭐⭐
---------------------------------------------------------------------
A classic functional "MapReduce"-style pipeline: filter out
unwanted records, transform the remaining ones, then aggregate them
into a single result - conceptually identical to the pattern behind
distributed processing frameworks like Spark.
---------------------------------------------------------------------
"""

print("\n--- Combining map(), filter(), reduce() ---")

orders = [
    {"customer": "Alice", "amount": 100.0, "status": "shipped"},
    {"customer": "Bob", "amount": 250.0, "status": "cancelled"},
    {"customer": "Alice", "amount": 75.0, "status": "shipped"},
    {"customer": "Cid", "amount": 300.0, "status": "shipped"},
]

# Step 1: FILTER - keep only shipped orders
shipped = filter(lambda o: o["status"] == "shipped", orders)

# Step 2: MAP - extract just the amount from each shipped order
amounts = map(lambda o: o["amount"], shipped)

# Step 3: REDUCE - sum all the extracted amounts into one total
total_shipped_revenue = reduce(lambda acc, amt: acc + amt, amounts, 0)

print("total revenue from shipped orders:", total_shipped_revenue)

print("\nNote: filter() and map() above are still LAZY - nothing is")
print("computed until reduce() actually consumes the chain, pulling")
print("one item through all three stages at a time.")


"""
---------------------------------------------------------------------
11. map()/filter() vs LIST COMPREHENSIONS: WHICH IS MORE PYTHONIC? ⭐⭐⭐
---------------------------------------------------------------------
For SIMPLE transform/filter logic, comprehensions are usually
considered more readable/Pythonic than map()/filter() + lambda -
this is a common opinion (and interview discussion point), though
not a hard rule.

map()/filter() tend to be preferred when:
    - you already have a NAMED function (not a throwaway lambda)
    - you're composing several functional-style operations together
    - performance in a VERY tight loop matters slightly (map() with
      a named/builtin function can be marginally faster, since it
      avoids the comprehension's per-iteration bytecode for building
      list append calls - though the difference is usually small
      and shouldn't be over-optimized for)
---------------------------------------------------------------------
"""

print("\n--- map()/filter() vs Comprehensions ---")

nums = list(range(1, 11))

# Equivalent expressions, different styles
map_filter_style = list(map(lambda x: x ** 2, filter(lambda x: x % 2 == 0, nums)))
comprehension_style = [x ** 2 for x in nums if x % 2 == 0]

print("map()+filter() style:", map_filter_style)
print("comprehension style:  ", comprehension_style)
print("\nMost Python style guides prefer the comprehension for")
print("readability, especially once multiple lambdas start stacking up.")

# When map() shines: applying an EXISTING named function (e.g. str,
# int, or a library function) - no lambda needed at all
string_numbers = ["1", "2", "3", "4"]
converted = list(map(int, string_numbers))       # no lambda required!
print("\nmap(int, [...]) - clean with an existing named function:", converted)


"""
---------------------------------------------------------------------
12. PERFORMANCE: map() vs LIST COMPREHENSION  ⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Performance: map() vs List Comprehension ---")

n = 2_000_000
data = list(range(n))

start = time.perf_counter()
result_map = list(map(str, data))          # using a BUILT-IN function
map_time = time.perf_counter() - start

start = time.perf_counter()
result_comp = [str(x) for x in data]
comp_time = time.perf_counter() - start

print(f"map(str, data):        {map_time:.4f} sec")
print(f"[str(x) for x in data]: {comp_time:.4f} sec")
print("\n(Results vary by Python version/build - the difference is")
print("usually small; don't over-optimize based on this alone.)")


"""
---------------------------------------------------------------------
13. itertools.starmap: map() FOR "PRE-PAIRED" ARGUMENTS  ⭐⭐
---------------------------------------------------------------------
Regular map() passes one item from EACH iterable positionally.
itertools.starmap() instead takes ONE iterable of ALREADY-GROUPED
argument tuples, and UNPACKS each tuple into the function - useful
when your data already comes as (a, b) pairs rather than two
separate parallel lists.
---------------------------------------------------------------------
"""

print("\n--- itertools.starmap() ---")

from itertools import starmap

pairs = [(2, 3), (4, 5), (6, 7)]

# Regular map() would need the pair UNPACKED manually via a lambda:
via_map = list(map(lambda pair: pair[0] * pair[1], pairs))
print("via map() with manual unpacking:", via_map)

# starmap() unpacks each tuple automatically
via_starmap = list(starmap(lambda a, b: a * b, pairs))
print("via itertools.starmap():", via_starmap)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Function              | Returns          | Evaluation | Module
------------------------|------------------|------------|-------------
map(func, iterable)      | iterator (lazy)   | lazy       | built-in
filter(func, iterable)    | iterator (lazy)    | lazy       | built-in
reduce(func, iterable)     | single final value  | eager      | functools
filter(None, iterable)      | removes falsy values | lazy       | built-in
itertools.starmap(func,      | iterator (lazy)       | lazy       | itertools
    iterable_of_tuples)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - map(), filter(), reduce()
=====================================================================

1. What does map() actually RETURN in Python 3 - a list, or
   something else? How is this different from Python 2's map()?

2. Prove, using a side-effect (like appending to a log list inside
   the mapped function), that map() is LAZY - i.e., that the
   function isn't called until the result is actually consumed.

3. What happens if you try to iterate over the SAME map() or
   filter() object a second time, after already consuming it once?

4. What does `filter(None, some_list)` do? Why is passing `None`
   (instead of an actual function) treated specially?

5. Why is `functools.reduce()` in a separate module in Python 3,
   rather than being a built-in like it was in Python 2? (This is
   largely a trivia/history question, but often asked.)

6. Trace through `reduce(lambda acc, x: acc + x, [1, 2, 3, 4])`
   step by step. What is the accumulator's value after each step?

7. What's the difference in behavior between calling `reduce()`
   WITH an initial value versus WITHOUT one? What happens if you
   call `reduce()` on an EMPTY iterable with no initial value?

8. How would you use `reduce()` to find the maximum value in a list
   WITHOUT using the built-in `max()` function?

9. Why is `reduce()` considered "eager" while `map()`/`filter()` are
   "lazy"? Can `reduce()` ever return a PARTIAL result partway
   through processing the iterable?

10. Given multiple iterables passed into `map(func, iter1, iter2)`,
    what happens if `iter1` and `iter2` have DIFFERENT lengths? Does
    it raise an error?

11. When would you prefer `map()`/`filter()` over an equivalent list
    comprehension, and vice versa? Is there a strong PEP8/Pythonic
    preference either way?

12. What is `itertools.starmap()`, and how does it differ from
    regular `map()` when your data is already a list of tuples
    (e.g., `[(2, 3), (4, 5)]`)?

13. How would you build a "mini MapReduce" pipeline in plain Python
    using `filter()`, `map()`, and `reduce()` together - e.g.,
    filtering only "shipped" orders, extracting their amounts, and
    summing them into one total?

14. In a data engineering context, why might chaining `filter()` and
    `map()` (both lazy) before a final `reduce()` or `sum()` call be
    more memory-efficient than doing the equivalent with list
    comprehensions and intermediate lists, when processing a very
    large dataset?
=====================================================================
"""