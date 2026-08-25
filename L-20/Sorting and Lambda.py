"""
=====================================================================
PYTHON LAMBDA FUNCTIONS & SORTING - Notes with Executable Examples
=====================================================================

PART A covers LAMBDA - Python's syntax for small, ANONYMOUS,
single-expression functions.

PART B covers SORTING - sorted()/list.sort(), the `key=` parameter
(where lambdas are used constantly), multi-field sorting, sorting
stability, and faster alternatives to lambda for sorting.

These two topics are grouped together because in real Python code,
lambda's #1 use case BY FAR is as the `key=` argument to sorted().
=====================================================================
"""

print("--- Overview ---")
print("Lambda = anonymous, single-expression function.")
print("Sorting = ordering data, often driven by a lambda 'key' function.")


"""
=====================================================================
PART A: LAMBDA FUNCTIONS
=====================================================================
"""

"""
---------------------------------------------------------------------
1. LAMBDA BASICS: SYNTAX  ⭐⭐⭐
---------------------------------------------------------------------
Syntax:  lambda arguments: expression

    - Can take any number of arguments (like a normal function)
    - Can contain only ONE EXPRESSION (no statements: no 'if' blocks,
      no loops, no multiple lines, no assignment*)
    - The expression's result is AUTOMATICALLY returned - no explicit
      'return' keyword
    - Has NO name of its own (it's "anonymous") unless assigned to
      a variable

* Python 3.8+ allows the walrus operator (:=) inside a lambda body
  as a limited form of "assignment within an expression."
---------------------------------------------------------------------
"""

print("\n--- Lambda Basics ---")

# A regular function...
def add_regular(x, y):
    return x + y

# ...and its lambda equivalent
add_lambda = lambda x, y: x + y

print("add_regular(3, 4):", add_regular(3, 4))
print("add_lambda(3, 4):", add_lambda(3, 4))

# Lambda with no arguments
greet = lambda: "Hello!"
print("\ngreet():", greet())

# Lambda with a default argument value
power = lambda base, exp=2: base ** exp
print("power(5):", power(5))          # uses default exp=2
print("power(5, 3):", power(5, 3))    # overrides default


"""
---------------------------------------------------------------------
2. LAMBDA vs def: KEY DIFFERENCES  ⭐⭐⭐
---------------------------------------------------------------------
    lambda                          | def
    --------------------------------|--------------------------------
    ONE expression only              | multiple statements allowed
    No 'return' keyword needed        | requires explicit 'return'
    No docstring support               | supports docstrings
    Anonymous (no name required)         | always has a name
    Typically used INLINE, for            | used for reusable, named
    short-lived, throwaway logic           logic referenced elsewhere
    __name__ is literally '<lambda>'         | __name__ is the function's
                                              actual name
---------------------------------------------------------------------
"""

print("\n--- Lambda vs def: __name__ Attribute ---")

def named_function():
    pass

anonymous_function = lambda: None

print("named_function.__name__:", named_function.__name__)
print("anonymous_function.__name__:", anonymous_function.__name__)
print("\nThis is why lambdas are harder to debug - stack traces show")
print("'<lambda>' instead of a meaningful function name.")


"""
---------------------------------------------------------------------
3. LAMBDA CANNOT CONTAIN STATEMENTS  ⭐⭐
---------------------------------------------------------------------
Only a single EXPRESSION is allowed - no 'if' statements (though
ternary EXPRESSIONS are fine), no 'for' loops, no multiple lines,
no plain '=' assignment.
---------------------------------------------------------------------
"""

print("\n--- Lambda Limitations: Expression-Only ---")

# A ternary EXPRESSION works fine inside a lambda (it's still ONE
# expression, just a conditional one)
classify = lambda x: "even" if x % 2 == 0 else "odd"
print("classify(4):", classify(4))
print("classify(7):", classify(7))

# This would NOT work (commented out - it's a SyntaxError):
#
#   bad_lambda = lambda x:
#       if x > 0:              # <-- statements are NOT allowed
#           return "positive"
#
# Lambdas can only ever evaluate to a single expression's result.


"""
---------------------------------------------------------------------
4. LAMBDA AS AN ARGUMENT TO HIGHER-ORDER FUNCTIONS  ⭐⭐⭐
---------------------------------------------------------------------
This is lambda's PRIMARY real-world use case: as a short, throwaway
function passed directly into map(), filter(), sorted(), etc. -
without needing a separate named `def` just for one-off logic.
---------------------------------------------------------------------
"""

print("\n--- Lambda with map(), filter(), reduce() ---")

numbers = [1, 2, 3, 4, 5, 6]

# map() - applies a function to every element
doubled = list(map(lambda x: x * 2, numbers))
print("map (doubled):", doubled)

# filter() - keeps only elements where the lambda returns True
evens = list(filter(lambda x: x % 2 == 0, numbers))
print("filter (evens):", evens)

# reduce() - cumulatively combines elements into a single result
from functools import reduce
total = reduce(lambda acc, x: acc + x, numbers)
print("reduce (sum):", total)

product = reduce(lambda acc, x: acc * x, numbers)
print("reduce (product):", product)


"""
---------------------------------------------------------------------
5. IMMEDIATELY INVOKED LAMBDA (IIFE-STYLE)  ⭐
---------------------------------------------------------------------
A lambda can be defined and called in the SAME expression by
wrapping it in parentheses and immediately calling it. Rarely used
in practice - shown here mainly for conceptual completeness.
---------------------------------------------------------------------
"""

print("\n--- Immediately Invoked Lambda ---")

result = (lambda x, y: x + y)(3, 4)
print("immediately invoked lambda result:", result)


"""
---------------------------------------------------------------------
6. THE CLASSIC LAMBDA-IN-A-LOOP CLOSURE TRAP  ⭐⭐⭐
---------------------------------------------------------------------
Lambdas (like any Python function) capture variables by REFERENCE,
not by their value AT CREATION TIME. If you create several lambdas
inside a loop that all reference the LOOP VARIABLE, they all end up
sharing the SAME final value of that variable - a extremely common
interview trap.
---------------------------------------------------------------------
"""

print("\n--- Classic Lambda-in-a-Loop Closure Trap ---")

# BUGGY: all lambdas end up using the FINAL value of i (which is 2)
buggy_multipliers = []
for i in range(3):
    buggy_multipliers.append(lambda x: x * i)

print("buggy multipliers, all called with x=10:")
print([m(10) for m in buggy_multipliers])   # [20, 20, 20] - all use i=2!

# FIXED: force the CURRENT value of i to be captured immediately by
# using it as a DEFAULT ARGUMENT (defaults ARE evaluated at
# definition time, not call time)
fixed_multipliers = []
for i in range(3):
    fixed_multipliers.append(lambda x, i=i: x * i)

print("\nfixed multipliers, all called with x=10:")
print([m(10) for m in fixed_multipliers])   # [0, 10, 20] - correct!


"""
=====================================================================
PART B: SORTING
=====================================================================
"""

"""
---------------------------------------------------------------------
7. sorted() vs list.sort(): BASICS  ⭐⭐⭐
---------------------------------------------------------------------
sorted(iterable)  -> returns a NEW sorted list; works on ANY
                      iterable (list, tuple, dict, set, generator...);
                      leaves the original unchanged
list.sort()       -> sorts a LIST IN PLACE; returns None; only
                      available on lists specifically

Both accept `key=` and `reverse=` as keyword arguments.
---------------------------------------------------------------------
"""

print("\n--- sorted() vs list.sort() ---")

nums = [5, 2, 9, 1, 7]

new_sorted = sorted(nums)             # does NOT mutate nums
print("sorted(nums):", new_sorted)
print("nums unchanged:", nums)

nums.sort()                            # mutates nums IN PLACE, returns None
print("\nnums.sort() result:", nums.sort())   # prints None!
print("nums after .sort():", nums)

# sorted() works on ANY iterable, not just lists
print("\nsorted() on a tuple:", sorted((3, 1, 2)))
print("sorted() on a set:", sorted({5, 3, 4}))
print("sorted() on a dict (sorts the KEYS):", sorted({"b": 2, "a": 1}))
print("sorted() on a generator:", sorted(x for x in [4, 2, 8]))


"""
---------------------------------------------------------------------
8. THE key= PARAMETER: SORTING BY A DERIVED VALUE  ⭐⭐⭐
---------------------------------------------------------------------
`key=` takes a FUNCTION applied to EACH element to compute the
value it should actually be sorted BY - the elements themselves stay
unchanged, only the SORT ORDER is determined by the key function's
output. This is lambda's most common real-world use case.
---------------------------------------------------------------------
"""

print("\n--- Sorting with key= ---")

words = ["banana", "kiwi", "apple", "fig"]

# Sort by LENGTH instead of alphabetically
by_length = sorted(words, key=lambda w: len(w))
print("sorted by length:", by_length)

# Sort case-INsensitively (without permanently altering the strings)
mixed_case = ["Banana", "apple", "Cherry", "date"]
case_insensitive = sorted(mixed_case, key=lambda w: w.lower())
print("case-insensitive sort:", case_insensitive)

# Sorting a list of dicts by a specific field - EXTREMELY common
records = [
    {"name": "Bob", "age": 25},
    {"name": "Amy", "age": 30},
    {"name": "Cid", "age": 20},
]
by_age = sorted(records, key=lambda r: r["age"])
print("\nsorted records by age:", by_age)


"""
---------------------------------------------------------------------
9. reverse= FOR DESCENDING ORDER  ⭐
---------------------------------------------------------------------
"""

print("\n--- reverse= for Descending Order ---")

print("sorted(nums, reverse=True):", sorted([3, 1, 4, 1, 5], reverse=True))
print("sorted by age, descending:",
      sorted(records, key=lambda r: r["age"], reverse=True))


"""
---------------------------------------------------------------------
10. SORTING BY MULTIPLE FIELDS  ⭐⭐⭐
---------------------------------------------------------------------
Return a TUPLE from the key function - Python sorts tuples
lexicographically (compares the 1st elements first, breaks ties
with the 2nd, and so on). To sort one field ASCENDING and another
DESCENDING at the same time, negate the numeric field in the tuple.
---------------------------------------------------------------------
"""

print("\n--- Sorting by Multiple Fields ---")

employees = [
    {"dept": "Sales", "name": "Alice", "salary": 70000},
    {"dept": "Sales", "name": "Bob", "salary": 90000},
    {"dept": "Engineering", "name": "Cid", "salary": 95000},
    {"dept": "Engineering", "name": "Dee", "salary": 95000},
]

# Sort by department (A-Z), then by salary DESCENDING within each dept
sorted_multi = sorted(employees, key=lambda e: (e["dept"], -e["salary"]))
print("sorted by dept asc, salary desc:")
for e in sorted_multi:
    print(" ", e)


"""
---------------------------------------------------------------------
11. SORT STABILITY: WHY EQUAL ELEMENTS KEEP THEIR RELATIVE ORDER ⭐⭐⭐
---------------------------------------------------------------------
Python's sort (Timsort) is STABLE - if two elements compare as
EQUAL under the given key, their RELATIVE ORDER from the original
sequence is preserved. This lets you sort by multiple criteria in
SEPARATE steps, from least to most important, and get a correct
combined result.
---------------------------------------------------------------------
"""

print("\n--- Sort Stability ---")

# Because sort is stable, sorting by dept AFTER already sorting by
# name gives the same combined ordering as a single multi-key sort
by_name_first = sorted(employees, key=lambda e: e["name"])
by_dept_then = sorted(by_name_first, key=lambda e: e["dept"])   # stable!

print("two-step stable sort (name, then dept):")
for e in by_dept_then:
    print(" ", e)

print("\nNotice: within each department, names remain alphabetically")
print("ordered - stability preserved that sub-ordering from the")
print("FIRST sort pass.")


"""
---------------------------------------------------------------------
12. operator.itemgetter / attrgetter: FASTER THAN LAMBDA  ⭐⭐
---------------------------------------------------------------------
For simple "sort by this field/attribute" cases, `operator`
module's itemgetter()/attrgetter() are slightly FASTER than an
equivalent lambda, because they're implemented in C and avoid
Python-level function-call overhead on every comparison.
---------------------------------------------------------------------
"""

print("\n--- operator.itemgetter / attrgetter ---")

from operator import itemgetter, attrgetter
import time

# itemgetter works on dicts, lists, tuples - anything subscriptable
sorted_itemgetter = sorted(records, key=itemgetter("age"))
print("sorted with itemgetter('age'):", sorted_itemgetter)

# itemgetter can also extract MULTIPLE fields at once, for
# multi-key sorting
sorted_multi_itemgetter = sorted(employees, key=itemgetter("dept", "name"))
print("\nsorted with itemgetter('dept', 'name'):")
for e in sorted_multi_itemgetter:
    print(" ", e)

# attrgetter works on OBJECT ATTRIBUTES instead of dict/list items
class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary
    def __repr__(self):
        return f"Employee({self.name!r}, {self.salary})"

employee_objects = [Employee("Bob", 90000), Employee("Amy", 70000)]
sorted_objects = sorted(employee_objects, key=attrgetter("salary"))
print("\nsorted objects with attrgetter('salary'):", sorted_objects)

# Quick performance comparison: lambda vs itemgetter over many calls
big_records = [{"val": i} for i in range(200_000)]

start = time.perf_counter()
sorted(big_records, key=lambda r: r["val"])
lambda_time = time.perf_counter() - start

start = time.perf_counter()
sorted(big_records, key=itemgetter("val"))
itemgetter_time = time.perf_counter() - start

print(f"\nsort with lambda key:      {lambda_time:.4f} sec")
print(f"sort with itemgetter key:  {itemgetter_time:.4f} sec  (usually faster)")


"""
---------------------------------------------------------------------
13. SORTING CUSTOM OBJECTS: __lt__ vs key=  ⭐⭐
---------------------------------------------------------------------
Two approaches to make custom objects sortable:
    (a) define comparison dunder methods (__lt__ at minimum) on the
        class itself - lets you call sorted(objects) with NO key=
    (b) just pass a key= function/lambda at sort time - no changes
        needed to the class

(b) is usually simpler and more flexible - you're not locked into
ONE "natural" ordering for the class.
---------------------------------------------------------------------
"""

print("\n--- Sorting Custom Objects ---")

class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price
    def __repr__(self):
        return f"Product({self.name!r}, {self.price})"
    def __lt__(self, other):          # defines the "natural" ordering
        return self.price < other.price

products = [Product("Widget", 25), Product("Gadget", 10), Product("Gizmo", 15)]

# Works WITHOUT key=, because __lt__ is defined
sorted_by_dunder = sorted(products)
print("sorted using __lt__ (no key= needed):", sorted_by_dunder)

# Or sort by a DIFFERENT field entirely using key=, without touching the class
sorted_by_name = sorted(products, key=lambda p: p.name)
print("sorted by name using key= instead:", sorted_by_name)


"""
---------------------------------------------------------------------
14. functools.cmp_to_key: COMPARATOR-STYLE SORTING  ⭐
---------------------------------------------------------------------
Modern Python sorting prefers `key=` (compute a sort value per
item). But if you have OLD-STYLE comparator logic (a function taking
TWO items and returning negative/zero/positive), cmp_to_key() adapts
it to work with sorted()/list.sort().
---------------------------------------------------------------------
"""

print("\n--- functools.cmp_to_key ---")

from functools import cmp_to_key

def compare_by_length_then_alpha(a, b):
    """Old-style comparator: negative if a<b, 0 if equal, positive if a>b."""
    if len(a) != len(b):
        return len(a) - len(b)
    if a < b:
        return -1
    elif a > b:
        return 1
    return 0

words_to_sort = ["ccc", "a", "bb", "aa", "b"]
sorted_with_comparator = sorted(words_to_sort, key=cmp_to_key(compare_by_length_then_alpha))
print("sorted using a comparator via cmp_to_key():", sorted_with_comparator)


"""
---------------------------------------------------------------------
15. SORTING DICTIONARIES BY KEY OR VALUE  ⭐⭐⭐
---------------------------------------------------------------------
Dicts have no built-in "sort" (they're ordered by insertion, not by
key/value) - but you can build a NEW dict sorted by key or value
using sorted() on .items().
---------------------------------------------------------------------
"""

print("\n--- Sorting Dictionaries ---")

scores = {"Bob": 85, "Amy": 92, "Cid": 78}

sorted_by_key = dict(sorted(scores.items()))
print("sorted by KEY:", sorted_by_key)

sorted_by_value = dict(sorted(scores.items(), key=lambda item: item[1]))
print("sorted by VALUE:", sorted_by_value)

sorted_by_value_desc = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
print("sorted by VALUE, descending:", sorted_by_value_desc)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
sorted(iterable, key=None, reverse=False)  -> new list, works on any iterable
list.sort(key=None, reverse=False)          -> in-place, list only, returns None

key= function ideas:
    len                        -> sort by length
    str.lower                  -> case-insensitive sort
    lambda r: r["field"]        -> sort dicts by a field
    lambda r: (a, b)             -> sort by multiple fields
    lambda r: (a, -b)             -> mixed ascending/descending
    itemgetter("field")             -> faster equivalent of the lambda above
    attrgetter("attr")                -> sort objects by an attribute
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - LAMBDA & SORTING
=====================================================================

LAMBDA:

1. What is a lambda function, and how does it differ from a regular
   function defined with `def`? What are its key LIMITATIONS?

2. Why does `lambda: None`'s `__name__` attribute show `'<lambda>'`,
   and why does this make debugging harder in stack traces?

3. Can a lambda contain an `if` statement? Can it contain a ternary
   `if/else` EXPRESSION? Explain the difference.

4. What is the classic "lambda in a loop" closure bug? Given:
       fns = [lambda x: x * i for i in range(3)]
   what will `[f(10) for f in fns]` actually produce, and why? How
   do you fix it?

5. Why is lambda most commonly used as the `key=` argument to
   `sorted()`, `map()`, or `filter()`, rather than being assigned to
   a variable and reused like a normal function?

SORTING:

6. What's the difference between `sorted()` and `list.sort()`?
   Which one works on any iterable, and which one is list-only?
   Which one returns `None`?

7. What does the `key=` parameter to `sorted()` actually do? Does it
   change the values being sorted, or just the ORDER they end up in?

8. How would you sort a list of dictionaries by one field ascending
   and a second field descending, at the same time, using a single
   `key=` function?

9. What does it mean for Python's sort to be "stable"? Give an
   example of how you could exploit stability to sort by multiple
   criteria using SEPARATE sequential sort calls.

10. Why is `operator.itemgetter("field")` often faster than an
    equivalent `lambda x: x["field"]` when used as a sort key on a
    large dataset?

11. How would you make a custom class sortable with a plain
    `sorted(my_objects)` call, without passing a `key=` argument at
    all? Which dunder method is the minimum required?

12. How would you sort a Python dictionary by its VALUES in
    descending order, and produce a new dictionary reflecting that
    order? (Remember dicts have no native `.sort()` method.)

13. What is `functools.cmp_to_key()` used for, and when would you
    need it instead of the more common `key=` approach?

14. In a data engineering context, if you need to sort millions of
    records by a computed/derived value (not a raw field), would you
    prefer `key=lambda`, `itemgetter`, or pre-computing the sort key
    once with a decorate-sort-undecorate (Schwartzian transform)
    pattern? Why might pre-computing the key be faster for an
    expensive key function?
=====================================================================
"""