"""
=====================================================================
ITERATORS vs GENERATORS - Complete Notes with Executable Examples
=====================================================================

These terms are related but NOT interchangeable - a common source
of confusion, and a favorite interview question.

    ITERABLE   -> ANY object you can loop over with a for-loop
                  (has an __iter__ method). Examples: list, tuple,
                  dict, str, set, file objects, generators.

    ITERATOR   -> an object that PRODUCES values one at a time via
                  __next__(), and knows how to signal "I'm done" by
                  raising StopIteration. Built by implementing the
                  ITERATOR PROTOCOL: both __iter__() (returns self)
                  AND __next__().

    GENERATOR  -> a SPECIFIC, CONVENIENT WAY to create an iterator -
                  either a function using `yield`, or a generator
                  EXPRESSION `(x for x in ...)`. Python automatically
                  builds the __iter__/__next__ machinery for you.

THE KEY RELATIONSHIP:
    Every GENERATOR is an ITERATOR.
    NOT every ITERATOR is a GENERATOR (you can build iterators
    manually with a class, with no `yield` involved at all).
    Not every ITERABLE is an ITERATOR (a list is iterable, but is
    NOT itself an iterator - see section 3).
=====================================================================
"""

import sys

print("--- Overview ---")
print("Every generator IS an iterator.")
print("Not every iterator is a generator.")
print("Not every iterable is an iterator.")


"""
---------------------------------------------------------------------
1. ITERABLE vs ITERATOR: THE CRITICAL DISTINCTION  ⭐⭐⭐
---------------------------------------------------------------------
An ITERABLE is anything you can call iter() on to GET an iterator.
An ITERATOR is the object that actually tracks PROGRESS through a
sequence and produces the next value on demand.

A list is ITERABLE, but it is NOT an iterator itself - calling
iter() on it produces a SEPARATE list_iterator object that does the
actual position-tracking.
---------------------------------------------------------------------
"""

print("\n--- Iterable vs Iterator ---")

my_list = [10, 20, 30]

print("my_list:", my_list, "| type:", type(my_list))

# A list has NO __next__ method - it is NOT an iterator itself
print("does my_list have __next__?:", hasattr(my_list, "__next__"))
print("does my_list have __iter__?:", hasattr(my_list, "__iter__"))

# Calling iter() on it PRODUCES an iterator - a separate object
list_iterator = iter(my_list)
print("\niter(my_list):", list_iterator, "| type:", type(list_iterator))
print("does list_iterator have __next__?:", hasattr(list_iterator, "__next__"))

print("\nmanually driving the iterator with next():")
print(next(list_iterator))
print(next(list_iterator))
print(next(list_iterator))

try:
    next(list_iterator)
except StopIteration:
    print("StopIteration raised - iterator exhausted")

print("\nBut my_list itself is UNCHANGED and can be iterated AGAIN,")
print("because EACH iter(my_list) call creates a FRESH iterator:")
print(list(my_list))          # still [10, 20, 30] - the list was never "used up"


"""
---------------------------------------------------------------------
2. HOW for-LOOPS ACTUALLY WORK UNDER THE HOOD  ⭐⭐⭐
---------------------------------------------------------------------
A `for x in some_iterable:` loop is really just syntactic sugar for
repeatedly calling iter() once, then next() many times, catching
StopIteration automatically.
---------------------------------------------------------------------
"""

print("\n--- What a for-Loop Actually Does ---")

# This for-loop:
print("using a for-loop:")
for item in [1, 2, 3]:
    print(" ", item)

# ...is EQUIVALENT to this manual version:
print("\nmanual equivalent using iter()/next():")
iterator = iter([1, 2, 3])
while True:
    try:
        item = next(iterator)
    except StopIteration:
        break
    print(" ", item)


"""
---------------------------------------------------------------------
3. BUILDING A CUSTOM ITERATOR (NO GENERATOR/yield INVOLVED)  ⭐⭐⭐
---------------------------------------------------------------------
An iterator can be built ENTIRELY MANUALLY, as a class implementing
the ITERATOR PROTOCOL:
    __iter__(self)  -> must return the iterator object itself
    __next__(self)  -> returns the next value, or raises
                       StopIteration when exhausted

This is a real iterator - but it is NOT a generator (no `yield`
anywhere in sight).
---------------------------------------------------------------------
"""

print("\n--- Building a Custom Iterator (Class-Based) ---")

class EvenNumbers:
    """A custom ITERATOR (not a generator) yielding even numbers up to a limit."""
    def __init__(self, limit):
        self.limit = limit
        self.current = 0

    def __iter__(self):
        return self             # an iterator returns ITSELF from __iter__

    def __next__(self):
        if self.current > self.limit:
            raise StopIteration
        value = self.current
        self.current += 2
        return value

evens = EvenNumbers(10)
print("is it iterable? hasattr __iter__:", hasattr(evens, "__iter__"))
print("is it an iterator? hasattr __next__:", hasattr(evens, "__next__"))

print("\nusing it in a for-loop:")
for num in evens:
    print(" ", num)

# CRITICAL DIFFERENCE FROM A LIST: this custom object IS its own
# iterator - iter(evens) returns the SAME object, not a fresh one
evens2 = EvenNumbers(4)
print("\niter(evens2) is evens2 ->", iter(evens2) is evens2)
print("(this is TRUE for iterators, but FALSE for plain iterables")
print(" like a list, where iter(my_list) is my_list -> False)")


"""
---------------------------------------------------------------------
4. THE SAME ITERATOR AS A GENERATOR (MUCH LESS CODE)  ⭐⭐⭐
---------------------------------------------------------------------
Everything the EvenNumbers CLASS does above can be written far more
concisely as a generator FUNCTION - Python builds the __iter__ and
__next__ methods for you automatically, behind the scenes.
---------------------------------------------------------------------
"""

print("\n--- The Same Logic as a Generator (Concise) ---")

def even_numbers_generator(limit):
    current = 0
    while current <= limit:
        yield current
        current += 2

print("using the generator version in a for-loop:")
for num in even_numbers_generator(10):
    print(" ", num)

# A generator object ALSO satisfies iter(gen) is gen, just like the
# manual class-based iterator did
gen = even_numbers_generator(4)
print("\niter(gen) is gen ->", iter(gen) is gen)
print("does the generator have __next__?:", hasattr(gen, "__next__"))
print("does the generator have __iter__?:", hasattr(gen, "__iter__"))


"""
---------------------------------------------------------------------
5. SIDE-BY-SIDE COMPARISON: CLASS-BASED ITERATOR vs GENERATOR ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Side-by-Side: Lines of Code, Readability ---")

print("""
Class-based iterator (manual):          Generator function (automatic):
-------------------------------          --------------------------------
class EvenNumbers:                        def even_numbers_generator(limit):
    def __init__(self, limit):                current = 0
        self.limit = limit                    while current <= limit:
        self.current = 0                          yield current
                                                   current += 2
    def __iter__(self):
        return self

    def __next__(self):
        if self.current > self.limit:
            raise StopIteration
        value = self.current
        self.current += 2
        return value

-> requires manually tracking state       -> Python automatically saves/
   in instance attributes                    restores state at each yield
-> requires explicit StopIteration           -> loop simply ending raises
   handling                                     StopIteration for you
-> more code, more room for bugs             -> concise, less error-prone
""")


"""
---------------------------------------------------------------------
6. WHY YOU'D EVER WRITE A CLASS-BASED ITERATOR INSTEAD  ⭐⭐
---------------------------------------------------------------------
Generators are usually preferred for simplicity, but a class-based
iterator can be the better choice when you need:
    - Multiple related methods beyond just iteration (e.g., a
      reset() method, a peek() method, or properties)
    - To support being iterated MULTIPLE times independently by
      returning a NEW iterator each time from __iter__ (see below)
    - Fine-grained control over object state that's easier to
      express with explicit instance attributes
---------------------------------------------------------------------
"""

print("\n--- When a Class-Based Iterator Makes More Sense ---")

class RepeatableRange:
    """
    An ITERABLE (not itself an iterator!) that can be iterated
    MULTIPLE times independently - impossible with a plain
    generator object, which is single-use.
    """
    def __init__(self, limit):
        self.limit = limit

    def __iter__(self):
        # returns a FRESH iterator each time - enables re-iteration!
        return iter(range(self.limit))

repeatable = RepeatableRange(3)
print("first full iteration:", list(repeatable))
print("second full iteration (works again!):", list(repeatable))

print("\nCompare this to a plain generator OBJECT, which can only")
print("ever be iterated ONCE (see the exhaustion pitfall below).")


"""
---------------------------------------------------------------------
7. THE #1 PITFALL: GENERATORS ARE SINGLE-USE, PLAIN ITERABLES ARE NOT
---------------------------------------------------------------------
This is the most commonly tested practical difference. A generator
OBJECT (the result of calling a generator function, or writing a
generator expression) behaves like the "iterator" case above - it
gets consumed and CANNOT be restarted. A list (an ITERABLE, not an
iterator) can be iterated as many times as you like.
---------------------------------------------------------------------
"""

print("\n--- Pitfall: Generators are Single-Use ---")

my_list_again = [1, 2, 3]
print("iterating a LIST twice:")
print(" first pass:", list(my_list_again))
print(" second pass:", list(my_list_again))       # works fine again!

def gen_func():
    yield 1
    yield 2
    yield 3

my_generator = gen_func()
print("\niterating a GENERATOR OBJECT twice:")
print(" first pass:", list(my_generator))
print(" second pass:", list(my_generator))          # empty - already exhausted!

print("\nTo iterate the same generator LOGIC twice, you must call")
print("the generator FUNCTION again to get a brand new generator object:")
print(" fresh generator:", list(gen_func()))


"""
---------------------------------------------------------------------
8. MEMORY: BOTH GENERATORS AND CUSTOM ITERATORS ARE LAZY  ⭐⭐
---------------------------------------------------------------------
The MEMORY EFFICIENCY benefit of "lazy, one-at-a-time" processing
applies EQUALLY to hand-written iterators and to generators - it's
a property of the ITERATOR PROTOCOL itself, not something unique to
`yield`. Generators are just the EASIEST way to get that property.
---------------------------------------------------------------------
"""

print("\n--- Memory: Both are Lazy, Regardless of Implementation ---")

class LazyRange:
    """A custom lazy iterator - no list is ever fully built."""
    def __init__(self, n):
        self.n = n
        self.current = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.n:
            raise StopIteration
        value = self.current
        self.current += 1
        return value

def lazy_range_generator(n):
    i = 0
    while i < n:
        yield i
        i += 1

custom_iterator_obj = LazyRange(10_000_000)
generator_obj = lazy_range_generator(10_000_000)
list_obj = list(range(10_000_000))

print(f"class-based iterator size:  {sys.getsizeof(custom_iterator_obj)} bytes")
print(f"generator size:              {sys.getsizeof(generator_obj)} bytes")
print(f"fully-built list size:        {sys.getsizeof(list_obj):,} bytes")
print("\nBoth the class-based iterator AND the generator stay tiny -")
print("laziness is a property of the PROTOCOL, not of `yield` specifically.")


"""
---------------------------------------------------------------------
9. NOT ALL ITERATORS ARE GENERATORS: OTHER BUILT-IN EXAMPLES  ⭐⭐
---------------------------------------------------------------------
Python has MANY built-in iterator types that are NOT generators -
they're implemented in C, without any `yield` involved at all, but
they still fully satisfy the iterator protocol.
---------------------------------------------------------------------
"""

print("\n--- Other Built-In Iterators (Not Generators) ---")

examples = [
    ("map object", map(str, [1, 2, 3])),
    ("filter object", filter(None, [0, 1, 2])),
    ("zip object", zip([1, 2], ["a", "b"])),
    ("reversed object", reversed([1, 2, 3])),
    ("enumerate object", enumerate(["x", "y"])),
    ("dict_keyiterator", iter({"a": 1}.keys())),
]

for name, obj in examples:
    is_generator = hasattr(obj, "gi_frame")     # a generator-specific attribute
    print(f"{name:20} type={type(obj).__name__:20} "
          f"has __next__={hasattr(obj, '__next__')}  is_generator={is_generator}")


"""
=====================================================================
QUICK REFERENCE: THE RELATIONSHIP
=====================================================================

    ITERABLE
        |
        | (calling iter() on it produces...)
        v
    ITERATOR  (__iter__ returns self, __next__ produces values)
        |
        | (one convenient way to BUILD an iterator...)
        v
    GENERATOR  (a function with yield, or a generator expression)


    Object type          | Iterable? | Iterator? | Generator?
    ----------------------|-----------|-----------|------------
    list, tuple, dict, str | Yes       | No        | No
    file object              | Yes       | Yes       | No (but generator-like)
    map(), filter(), zip()     | Yes       | Yes       | No (C-implemented)
    custom class w/ __next__     | Yes       | Yes       | No
    function using yield           | Yes       | Yes       | Yes
    (x for x in ...) expression      | Yes       | Yes       | Yes
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - ITERATORS vs GENERATORS
=====================================================================

1. Define "iterable," "iterator," and "generator." How do the three
   terms relate to each other, and is any one of them a SUBSET of
   another?

2. Is a Python `list` an iterator? Why or why not? What method(s)
   does it lack that an iterator must have?

3. What does calling `iter()` on a list actually return? Is that
   result the SAME object as the list, or a different one?

4. What two methods must a class implement to satisfy the
   ITERATOR PROTOCOL? What should `__iter__` return, and what should
   `__next__` do when there's nothing left to produce?

5. Is EVERY generator an iterator? Is every iterator a generator?
   Justify both answers with an example.

6. What does a `for` loop actually do "under the hood," in terms of
   calling `iter()` and `next()`? Rewrite a simple for-loop manually
   using these two functions.

7. Why can a plain Python list be iterated over MULTIPLE times
   (e.g., in two separate for-loops), while a generator OBJECT
   cannot?

8. Give two examples of built-in Python objects that ARE iterators
   but are NOT generators (i.e., they satisfy the iterator protocol
   without using `yield` or generator expression syntax anywhere).

9. Why might you choose to write a class-based iterator instead of
   a generator function, even though the generator would usually be
   less code? (Hint: think about needing to iterate the SAME
   logical sequence multiple times, independently.)

10. If a class's `__iter__` method returns `self`, what does that
    imply about whether instances of that class can be iterated
    over more than once, independently, at the same time?

11. Does the MEMORY-EFFICIENCY benefit of lazy, one-at-a-time
    processing come specifically from using `yield`, or is it a
    more general property of anything that follows the iterator
    protocol? Justify your answer.

12. What check could you perform at runtime to distinguish a
    generator object from some other kind of iterator (e.g., a
    `map` object or a custom class-based iterator)?

13. In a data engineering context, if you needed a reusable object
    representing "the rows of this CSV file" that could be iterated
    over independently by MULTIPLE consumers at different times,
    would a single generator object or a custom iterable class (with
    `__iter__` returning a FRESH iterator each time) be the better
    design? Why?

14. What exception must a correctly-implemented `__next__()` method
    raise once there are no more items to produce? What happens if
    it forgets to do this?
=====================================================================
"""