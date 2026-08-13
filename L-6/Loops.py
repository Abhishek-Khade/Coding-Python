"""
=====================================================================
PYTHON LOOPS - Complete Notes with Executable Examples
=====================================================================

Loops let you repeat a block of code multiple times. Python has two
loop constructs:

    for    -> iterates over a sequence/iterable (list, str, range,
              dict, generator, etc.) - the most common loop in Python
    while  -> repeats as long as a condition remains True

Supporting keywords:
    break     -> exits the loop immediately
    continue  -> skips to the next iteration
    else      -> runs ONLY if the loop completed WITHOUT a break
    pass      -> a no-op placeholder (does nothing)

Python has NO traditional C-style for(i=0; i<n; i++) loop - 'for'
always iterates over an iterable (range() simulates counting).
=====================================================================
"""

print("--- Overview ---")
print("Loops repeat code. Python favors 'for' over manual indexing.")


"""
---------------------------------------------------------------------
1. BASIC for LOOP
---------------------------------------------------------------------
'for' iterates directly over elements of any iterable - no manual
index management needed (unlike C/Java's for(i=0;...)).
---------------------------------------------------------------------
"""

print("\n--- Basic for Loop ---")

fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print("fruit:", fruit)

# range(start, stop, step) - generates numbers lazily, doesn't
# store the whole sequence in memory
print("\nUsing range():")
for i in range(2, 10, 2):     # 2, 4, 6, 8 (stop is exclusive)
    print("i:", i)


"""
---------------------------------------------------------------------
2. LOOPING WITH INDEX: enumerate()
---------------------------------------------------------------------
enumerate() gives BOTH the index and the value while looping -
more Pythonic than manually tracking an index with range(len(x)).
---------------------------------------------------------------------
"""

print("\n--- enumerate() ---")

for idx, fruit in enumerate(fruits):
    print(f"index {idx}: {fruit}")

# enumerate() can start counting from any number
print("\nenumerate starting at 1:")
for idx, fruit in enumerate(fruits, start=1):
    print(f"item #{idx}: {fruit}")


"""
---------------------------------------------------------------------
3. LOOPING OVER MULTIPLE SEQUENCES: zip()
---------------------------------------------------------------------
zip() pairs up elements from multiple iterables and stops at the
SHORTEST one - a very common tool for parallel iteration.
---------------------------------------------------------------------
"""

print("\n--- zip() ---")

names = ["Alice", "Bob", "Carol"]
scores = [85, 92, 78]

for name, score in zip(names, scores):
    print(f"{name}: {score}")

# zip() truncates silently to the shortest iterable - a common trap
short_list = [1, 2]
long_list = [10, 20, 30, 40]
print("\nzip() truncation with mismatched lengths:")
print(list(zip(short_list, long_list)))   # only 2 pairs, not 4


"""
---------------------------------------------------------------------
4. LOOPING OVER DICTIONARIES
---------------------------------------------------------------------
Iterating a dict directly gives you KEYS only. Use .items() to get
key-value pairs, .values() for values only.
---------------------------------------------------------------------
"""

print("\n--- Looping Over Dictionaries ---")

person = {"name": "Claude", "role": "assistant", "team": "Anthropic"}

print("Default iteration (keys only):")
for key in person:
    print(" key:", key)

print("\nUsing .items() (key-value pairs):")
for key, value in person.items():
    print(f" {key}: {value}")


"""
---------------------------------------------------------------------
5. while LOOP
---------------------------------------------------------------------
Repeats as long as the condition remains True. Useful when the
number of iterations isn't known in advance (unlike 'for').
CAUTION: forgetting to update the loop variable causes an infinite
loop - always ensure the condition eventually becomes False.
---------------------------------------------------------------------
"""

print("\n--- while Loop ---")

count = 0
while count < 5:
    print("count:", count)
    count += 1     # without this, infinite loop!

# while True with a break condition - common pattern for
# "loop until some event happens" (e.g., reading a stream)
print("\nwhile True with break:")
n = 0
while True:
    if n >= 3:
        break
    print("n:", n)
    n += 1


"""
---------------------------------------------------------------------
6. break AND continue
---------------------------------------------------------------------
break     -> exits the CLOSEST enclosing loop immediately
continue  -> skips the rest of the current iteration, moves to next
---------------------------------------------------------------------
"""

print("\n--- break and continue ---")

print("break example (stop at first even number >= 5):")
for num in [1, 3, 5, 6, 7, 8]:
    if num >= 5 and num % 2 == 0:
        print(f"  found {num}, stopping")
        break
    print(f"  checked {num}")

print("\ncontinue example (skip odd numbers):")
for num in range(1, 8):
    if num % 2 != 0:
        continue          # skip the print below for odd numbers
    print(f"  even number: {num}")


"""
---------------------------------------------------------------------
7. THE for-else / while-else CONSTRUCT  ⭐ (frequently misunderstood)
---------------------------------------------------------------------
The 'else' block after a loop runs ONLY IF the loop completed
WITHOUT hitting a 'break'. This is a uniquely Python feature.

Common use case: searching for an item - if found, break; if the
loop finishes without finding it, the 'else' runs as a "not found"
handler.
---------------------------------------------------------------------
"""

print("\n--- for-else Construct ---")

def find_item(items, target):
    for item in items:
        if item == target:
            print(f"Found {target}!")
            break
    else:
        # runs only if the loop never hit 'break'
        print(f"{target} not found in list")

find_item([1, 2, 3, 4], 3)     # breaks -> else does NOT run
find_item([1, 2, 3, 4], 99)    # no break -> else DOES run


"""
---------------------------------------------------------------------
8. NESTED LOOPS
---------------------------------------------------------------------
Loops can be nested. 'break'/'continue' only affect the INNERMOST
loop they're written in - they do NOT automatically exit outer
loops (Python has no labeled break like Java).
---------------------------------------------------------------------
"""

print("\n--- Nested Loops ---")

for i in range(3):
    for j in range(3):
        if j == 1:
            continue        # only skips inner loop's iteration
        print(f"i={i}, j={j}")


"""
---------------------------------------------------------------------
9. LOOPING WITH LIST/DICT/SET COMPREHENSIONS  ⭐⭐
---------------------------------------------------------------------
Comprehensions are compact, often FASTER alternatives to explicit
for-loops for building new collections. Heavily favored in
Pythonic/data engineering code.
---------------------------------------------------------------------
"""

print("\n--- Comprehensions (Compact Loops) ---")

# Traditional loop
squares_loop = []
for x in range(1, 6):
    squares_loop.append(x ** 2)
print("squares (loop):", squares_loop)

# Equivalent list comprehension - more Pythonic, often faster
squares_comp = [x ** 2 for x in range(1, 6)]
print("squares (comprehension):", squares_comp)

# Comprehension with a condition (filter)
evens = [x for x in range(1, 11) if x % 2 == 0]
print("evens only:", evens)

# Dict comprehension
square_map = {x: x ** 2 for x in range(1, 6)}
print("dict comprehension:", square_map)

# Set comprehension
unique_lengths = {len(word) for word in ["cat", "dog", "lion", "ox"]}
print("set comprehension (unique word lengths):", unique_lengths)

# Generator expression - like a list comprehension but LAZY,
# doesn't build the whole list in memory (crucial for big data!)
gen = (x ** 2 for x in range(1, 6))
print("generator expression object:", gen)
print("consuming generator:", list(gen))


"""
---------------------------------------------------------------------
10. ITERATING EFFICIENTLY OVER LARGE DATA (DATA ENGINEERING FOCUS) ⭐⭐⭐
---------------------------------------------------------------------
For large files/datasets, avoid loading everything into memory at
once. Loop line-by-line or in chunks instead.
---------------------------------------------------------------------
"""

print("\n--- Efficient Iteration for Large Data ---")

# Simulating a "large file" with an in-memory list of lines here,
# but the pattern is IDENTICAL to real file iteration:
#
#     with open("huge_file.txt") as f:
#         for line in f:          # reads ONE line at a time - lazy!
#             process(line)
#
# This NEVER loads the full file into memory at once.

simulated_lines = [f"row_{i}" for i in range(5)]
for line in simulated_lines:
    print("processing:", line)


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON LOOPS
=====================================================================

1. What is the difference between 'break' and 'continue'?

2. Explain the for-else construct. When does the 'else' block
   actually execute? Give a practical use case (e.g., searching for
   an item in a list).

3. Why does Python not have a traditional C-style
   `for(i=0; i<n; i++)` loop? How does `range()` achieve the same
   result?

4. What happens if the two iterables passed to `zip()` have
   different lengths? How would you use `itertools.zip_longest()`
   to handle that instead?

5. Why is a list comprehension often faster than an equivalent
   explicit `for` loop with `.append()`?

6. What's the difference between a list comprehension `[x for x in
   range(10)]` and a generator expression `(x for x in range(10))`?
   Why would you prefer a generator when processing a huge dataset?

7. How would you iterate over a file too large to fit in memory,
   line by line, without ever loading the whole file at once?

8. What does iterating directly over a dictionary give you (keys,
   values, or both)? How do you get key-value pairs instead?

9. Why doesn't `break` inside a nested loop exit the OUTER loop as
   well? How would you break out of multiple nested loops in Python
   (since there's no labeled break)?

10. What is an infinite loop, and how would you deliberately write
    a safe one (e.g., `while True` with a `break` condition) for
    something like polling an API until a condition is met?

11. What's wrong with modifying a list WHILE iterating over it in a
    for loop (e.g., removing items during iteration)? What's the
    safe way to do it instead? (Hint: iterate over a copy, use list
    comprehension, or iterate in reverse.)

12. How would you flatten a list of lists using a nested list
    comprehension in a single line?

13. Explain enumerate() and why it's preferred over manually
    tracking an index with `range(len(my_list))`.

14. In a data pipeline, why might you choose a generator-based loop
    over building an entire list in memory before processing it?
=====================================================================
"""