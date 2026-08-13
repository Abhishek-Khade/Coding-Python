"""
=====================================================================
PYTHON CONDITIONALS - Complete Notes with Executable Examples
=====================================================================

Conditionals let a program make decisions and execute different
code paths based on whether an expression evaluates to True or
False. Python's conditional constructs:

    if / elif / else
    Nested if statements
    Ternary (conditional) expressions
    Truthy / Falsy evaluation
    match-case (structural pattern matching, Python 3.10+)

Python has NO switch-case statement (until match-case in 3.10) and
uses INDENTATION (not braces) to define blocks.
=====================================================================
"""

print("--- Overview ---")
print("Conditionals control which code branch executes.")


"""
---------------------------------------------------------------------
1. BASIC if / elif / else
---------------------------------------------------------------------
- 'if' evaluates first; if False, Python checks 'elif' blocks in
  order; 'else' runs only if ALL prior conditions were False.
- Only ONE branch executes - Python stops at the first True condition.
- Indentation defines the block (typically 4 spaces, PEP8 standard).
---------------------------------------------------------------------
"""

print("\n--- Basic if / elif / else ---")

age = 25

if age < 13:
    category = "child"
elif age < 20:
    category = "teenager"
elif age < 60:
    category = "adult"
else:
    category = "senior"

print(f"age {age} -> category: {category}")


"""
---------------------------------------------------------------------
2. NESTED CONDITIONALS
---------------------------------------------------------------------
Conditionals can be nested inside each other for compound logic.
Deep nesting hurts readability - often better replaced with
combined boolean expressions (using 'and'/'or') or early returns.
---------------------------------------------------------------------
"""

print("\n--- Nested Conditionals ---")

username = "admin"
password = "1234"

if username == "admin":
    if password == "1234":
        print("Access granted (nested check)")
    else:
        print("Wrong password")
else:
    print("Unknown user")

# Same logic flattened using 'and' - generally preferred for
# readability over deep nesting
print("\nFlattened version using 'and':")
if username == "admin" and password == "1234":
    print("Access granted (flattened check)")
else:
    print("Access denied")


"""
---------------------------------------------------------------------
3. TERNARY (CONDITIONAL) EXPRESSIONS
---------------------------------------------------------------------
Syntax:  value_if_true if condition else value_if_false

A one-line way to assign a value based on a condition. Great for
simple cases, but nesting multiple ternaries hurts readability and
is generally discouraged in production code / style guides.
---------------------------------------------------------------------
"""

print("\n--- Ternary Expressions ---")

num = 7
result = "even" if num % 2 == 0 else "odd"
print(f"{num} is {result}")

# Nested ternary (works, but readability suffers - use sparingly)
score = 85
grade = "A" if score >= 90 else "B" if score >= 80 else "C"
print(f"score {score} -> grade {grade}")


"""
---------------------------------------------------------------------
4. TRUTHY AND FALSY VALUES
---------------------------------------------------------------------
Every object in Python has an inherent boolean value used in
conditionals, even if it's not an explicit bool.

FALSY values (treated as False):
    False, None, 0, 0.0, 0j, "", [], (), {}, set(), range(0)

TRUTHY values (treated as True):
    Everything else - including "0" (non-empty string!),
    [0] (non-empty list containing a falsy item), etc.
---------------------------------------------------------------------
"""

print("\n--- Truthy / Falsy Values ---")

falsy_values = [False, None, 0, 0.0, "", [], (), {}, set()]
for val in falsy_values:
    print(f"if {val!r}: -> {'True (truthy)' if val else 'False (falsy)'}")

print()
# Classic gotcha: a non-empty string "0" or "False" is TRUTHY,
# even though it visually looks like a falsy value
tricky_values = ["0", "False", [0], (None,)]
for val in tricky_values:
    print(f"if {val!r}: -> {'True (truthy)' if val else 'False (falsy)'}")

# Practical use: checking if a list/dict is empty WITHOUT len()
data = []
if not data:
    print("\n'data' is empty (Pythonic check using 'not data')")


"""
---------------------------------------------------------------------
5. 'in' WITH CONDITIONALS (MEMBERSHIP-BASED BRANCHING)
---------------------------------------------------------------------
Combining membership operators with conditionals is very common
when validating input against a known set of allowed values.
---------------------------------------------------------------------
"""

print("\n--- Membership-Based Conditionals ---")

valid_statuses = {"active", "pending", "closed"}
status = "pending"

if status in valid_statuses:
    print(f"'{status}' is a valid status")
else:
    print(f"'{status}' is NOT a valid status")


"""
---------------------------------------------------------------------
6. match-case (STRUCTURAL PATTERN MATCHING) - Python 3.10+
---------------------------------------------------------------------
Python's closest equivalent to switch-case, but more powerful -
it can match on VALUES, TYPES, and even STRUCTURE/PATTERNS
(e.g., unpacking tuples/lists/dicts directly in the case clause).

Use '_' as the wildcard/default case (like 'else').
---------------------------------------------------------------------
"""

print("\n--- match-case (Python 3.10+) ---")

def http_status_message(code):
    match code:
        case 200:
            return "OK"
        case 404:
            return "Not Found"
        case 500 | 502 | 503:          # match multiple values with '|'
            return "Server Error"
        case _:                         # wildcard - default case
            return "Unknown Status"

for code in [200, 404, 502, 999]:
    print(f"{code} -> {http_status_message(code)}")

# Pattern matching on STRUCTURE - matches and unpacks in one step
print("\nStructural pattern matching example:")
def describe_point(point):
    match point:
        case (0, 0):
            return "origin"
        case (x, 0):
            return f"on the x-axis at {x}"
        case (0, y):
            return f"on the y-axis at {y}"
        case (x, y):
            return f"point at ({x}, {y})"
        case _:
            return "not a point"

for pt in [(0, 0), (5, 0), (0, 3), (2, 7)]:
    print(f"{pt} -> {describe_point(pt)}")


"""
---------------------------------------------------------------------
7. GUARD CLAUSES / EARLY RETURNS (BEST PRACTICE)
---------------------------------------------------------------------
Rather than deeply nesting conditionals, many production codebases
prefer "guard clauses" - early returns that exit a function as soon
as an invalid condition is detected. This keeps the "happy path"
code unindented and easier to read.
---------------------------------------------------------------------
"""

print("\n--- Guard Clauses (Best Practice) ---")

def process_order(order):
    if order is None:
        return "Error: order is None"
    if not order.get("items"):
        return "Error: order has no items"
    if order.get("total", 0) <= 0:
        return "Error: invalid total"
    # happy path - reached only if all checks passed
    return f"Processing order with {len(order['items'])} item(s)"

print(process_order(None))
print(process_order({"items": []}))
print(process_order({"items": ["book"], "total": 25}))


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON CONDITIONALS
=====================================================================

1. What are "truthy" and "falsy" values in Python? List all the
   built-in values that evaluate to False in a boolean context.

2. Why is `if "0":` True, even though the string looks like it
   represents zero? Explain the difference between the STRING "0"
   and the INTEGER 0 in a boolean context.

3. What is the Pythonic way to check if a list/dict/string is empty?
   (Answer: `if not my_list:` rather than `if len(my_list) == 0:`)

4. How does Python's ternary expression differ syntactically from
   languages like Java/C++ (`condition ? true_val : false_val`)?

5. What is match-case, and how is it different from a traditional
   switch statement in other languages? Can it match on structure
   (like tuples or dict shapes), not just values?

6. How do you match multiple values in a single `case` block using
   match-case? (Hint: the `|` OR pattern, e.g. `case 500 | 502 | 503:`)

7. What is a "guard clause" and why is it often preferred over deeply
   nested if/else blocks in production code?

8. Given `x = [0]`, is `if x:` True or False? Why does an empty
   list behave differently from a list containing a falsy element
   like 0?

9. Why can chained comparisons like `1 < x < 10` be more efficient
   and more readable than `1 < x and x < 10`?

10. In Pandas, why does `if df:` raise a ValueError
    ("The truth value of a DataFrame is ambiguous")? How should you
    check a DataFrame's condition instead (e.g., `.empty`, `.any()`,
    `.all()`)?

11. What's the output of the following, and why?
        x = None
        y = x or "default"
    Explain how 'or' is being used here as a fallback pattern, and
    when this pattern can silently produce wrong results (e.g., if
    0 or "" were valid intended values instead of a missing value).

12. How would you refactor a deeply nested if/elif/else chain that
    checks a variable against many possible values into a cleaner
    match-case or dictionary-based dispatch?

13. What happens if you forget the wildcard `case _:` at the end of
    a match-case block and none of the patterns match? (Hint: it
    simply falls through with no error - unlike some languages'
    switch statements which require explicit default handling to
    avoid silent no-ops.)
=====================================================================
"""