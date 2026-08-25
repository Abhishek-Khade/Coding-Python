"""
=====================================================================
PYTHON MAGIC / DUNDER METHODS - Complete Notes with Executable Examples
=====================================================================

A DUNDER method (short for "double underscore", e.g. `__init__`,
`__len__`, `__add__`) is a method with a special, reserved name that
Python calls IMPLICITLY when you use certain built-in syntax or
built-in functions on an object. Collectively, these methods are
called the "Python data model" - they're how your own classes plug
into the language's built-in machinery instead of needing special
cases baked into the interpreter.

You already know one dunder intimately: `__init__` is called
implicitly by `ClassName(...)`. The same pattern extends everywhere:

    len(obj)        -> obj.__len__()
    str(obj)        -> obj.__str__()
    repr(obj)        -> obj.__repr__()
    obj1 == obj2     -> obj1.__eq__(obj2)
    obj1 + obj2      -> obj1.__add__(obj2)
    for x in obj:    -> obj.__iter__() then repeated .__next__()
    with obj as x:   -> obj.__enter__() ... obj.__exit__(...)
    obj(...)         -> obj.__call__(...)

Interviewers love dunder methods because they test whether you
understand Python's OBJECT MODEL, not just syntax - and because a
huge amount of "Pythonic" library code (pandas Series, datetime,
pathlib.Path, your own domain classes) leans on them heavily.

This file builds ONE running example - a `Money` class representing
a currency amount, plus a small `Wallet` class that holds several
`Money` transactions - and grows it, dunder by dunder, the way you'd
actually design a class for a real data-engineering pipeline (e.g.
representing and aggregating financial line-items).
=====================================================================
"""

from decimal import Decimal
from functools import total_ordering

print("--- Overview ---")
print("Dunder methods are hooks Python calls implicitly for built-in")
print("syntax: print(), ==, +, len(), for-loops, with-blocks, and")
print("calling an object like a function all delegate to a dunder.")


"""
---------------------------------------------------------------------
1. THE PYTHON DATA MODEL: A BARE CLASS BEFORE ANY DUNDERS  ⭐⭐⭐
---------------------------------------------------------------------
Every class already inherits DEFAULT versions of most dunders from
`object` - they just aren't very useful. Default `__repr__` shows
the type and memory address; default `__eq__` compares IDENTITY
(same as `is`), not value; default objects aren't ordered, sized,
iterable, callable, or usable in a `with` block at all.
---------------------------------------------------------------------
"""

print("\n--- A Bare Class Before Any Dunders ---")

class Money:
    def __init__(self, amount, currency):
        # Decimal, not float, for money - avoids classic 0.1 + 0.2
        # style binary floating-point rounding errors in financial code.
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

m1 = Money("10.00", "USD")
m2 = Money("10.00", "USD")

print("repr(m1) with NO __repr__ defined:", repr(m1))
print("print(m1) with NO __str__ defined:", m1)
print("m1 == m2 (same amount/currency, different objects):", m1 == m2)
print("\nBoth results above are USELESS for debugging: the repr gives")
print("no data, and equality falls back to identity (`is`), so two")
print("Money objects representing the SAME $10.00 compare unequal.")


"""
---------------------------------------------------------------------
2. __repr__ vs __str__  ⭐⭐⭐
---------------------------------------------------------------------
This is the single most commonly asked dunder-method interview
question. The rule of thumb:

    __repr__ -> for DEVELOPERS. Unambiguous. Ideally looks like the
                 code you'd type to recreate the object. Used by the
                 REPL, by `repr()`, and by debuggers/logs.
    __str__  -> for END USERS. Readable/friendly. Used by `print()`,
                 `str()`, and f-strings/`.format()`.

Critically: if a class defines `__repr__` but NOT `__str__`, Python
FALLS BACK to using `__repr__` for `str()`/`print()` too - there is
no separate default. We prove that live below.
---------------------------------------------------------------------
"""

print("\n--- __repr__ vs __str__ (and the Fallback) ---")

class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        # Unambiguous, developer-facing: shows the REAL internal
        # state, styled like the constructor call that built it.
        return f"Money({self.amount!r}, {self.currency!r})"

m1 = Money("10.00", "USD")

print("repr(m1):        ", repr(m1))
print("str(m1):         ", str(m1))   # no __str__ defined yet...
print("print(m1):       ", end="")
print(m1)                              # ...so this falls back too
print("f'{m1}':         ", f"{m1}")
print("\nWith ONLY __repr__ defined, str(), print(), and f-strings all")
print("fall back to calling __repr__ - proven live above: every line")
print("printed the identical developer-facing string.")

class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        # Readable, end-user facing: what you'd show on a receipt.
        return f"{self.currency} {self.amount:.2f}"

m1 = Money("10.00", "USD")
print("\nNow WITH __str__ defined too:")
print("repr(m1):        ", repr(m1))
print("str(m1) / print():", m1)
print("\nThey now genuinely differ - repr() is still the debug view,")
print("print()/str() is now the friendly view.")

# Interview gotcha: containers (list, dict, ...) always print their
# ELEMENTS using repr(), even when the element defines __str__ too.
print("\nGotcha - printing a LIST of Money still uses repr() per item:")
print([m1, Money("5.50", "usd")])


"""
---------------------------------------------------------------------
3. __eq__ AND __hash__: WHY DEFINING ONE WITHOUT THE OTHER BREAKS
   HASHABILITY  ⭐⭐⭐
---------------------------------------------------------------------
By default, objects are hashable using their `id()` (identity), which
is consistent with the default identity-based `__eq__`. But the moment
you define `__eq__` yourself, Python has NO WAY to know if your new
equality is still consistent with the old identity-based hash - so it
protects you by AUTOMATICALLY setting `__hash__ = None` on your class,
making instances UNHASHABLE (can't go in a `set` or be used as a
`dict` key), UNLESS you also define `__hash__` yourself.

The invariant that must hold: if `a == b`, then `hash(a) == hash(b)`.
---------------------------------------------------------------------
"""

print("\n--- __eq__ and __hash__ Must Be Defined Together ---")

class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        return f"{self.currency} {self.amount:.2f}"

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented   # let Python try other.__eq__(self), or fall back to False
        return self.amount == other.amount and self.currency == other.currency

m1 = Money("10.00", "USD")
m2 = Money("10.00", "USD")
print("m1 == m2 with __eq__ defined:", m1 == m2)

print("\nBUT defining __eq__ silently disabled hashing:")
print("Money.__hash__ is:", Money.__hash__)
try:
    seen = {m1, m2}      # a set needs to hash its elements
except TypeError as e:
    print("TypeError putting Money in a set:", e)

try:
    ledger = {m1: "rent payment"}   # a dict key needs to be hashable too
except TypeError as e:
    print("TypeError using Money as a dict key:", e)

# FIX: define __hash__ using the SAME fields __eq__ compares, so the
# invariant (a == b implies hash(a) == hash(b)) genuinely holds.
class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        return f"{self.currency} {self.amount:.2f}"

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self):
        return hash((self.amount, self.currency))

m1 = Money("10.00", "USD")
m2 = Money("10.00", "USD")
print("\nWITH __hash__ defined consistently with __eq__:")
print("hash(m1) == hash(m2):", hash(m1) == hash(m2))
unique = {m1, m2}
print("{m1, m2} as a set collapses to:", unique)

# Data-engineering use case: deduplicating raw transaction records
# pulled from an upstream source that sometimes double-sends events.
raw_transactions = [Money("10.00", "USD"), Money("10.00", "USD"), Money("25.00", "USD")]
deduped = list(set(raw_transactions))
print("\nDE use case - deduping ingested transactions with a set:")
print("raw count:", len(raw_transactions), "-> deduped count:", len(deduped))


"""
---------------------------------------------------------------------
4. __len__: MAKING len() WORK ON A CUSTOM CONTAINER  ⭐⭐
---------------------------------------------------------------------
`__len__` must return a non-negative int. It's what powers `len(obj)`,
and (via a default fallback) also affects truthiness - an object
with `__len__` returning 0 is treated as falsy in an `if` check,
unless `__bool__` is separately defined.
---------------------------------------------------------------------
"""

print("\n--- __len__ ---")

class Wallet:
    """Holds a running list of Money transactions - a tiny in-memory ledger."""
    def __init__(self, transactions=None):
        self._transactions = list(transactions) if transactions else []

    def add(self, money):
        self._transactions.append(money)

    def __len__(self):
        return len(self._transactions)

wallet = Wallet([Money("10.00", "USD"), Money("25.00", "USD")])
print("len(wallet):", len(wallet))
wallet.add(Money("5.00", "USD"))
print("len(wallet) after add:", len(wallet))
print("empty wallet is falsy:", bool(Wallet()))   # __len__ == 0 -> falsy
print("non-empty wallet is truthy:", bool(wallet))


"""
---------------------------------------------------------------------
5. ORDERING: __lt__ / __le__ / __gt__ / __ge__ AND
   functools.total_ordering  ⭐⭐
---------------------------------------------------------------------
To make objects sortable/comparable with <, <=, >, >=, you can define
all four comparison dunders yourself - or define just `__eq__` plus
ONE of them (usually `__lt__`) and let `@functools.total_ordering`
generate the other three for you. It's a small runtime-speed trade
for a lot less boilerplate, and it's a very common interview mention.
---------------------------------------------------------------------
"""

print("\n--- Ordering: __lt__ and functools.total_ordering ---")

@total_ordering
class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        return f"{self.currency} {self.amount:.2f}"

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self):
        return hash((self.amount, self.currency))

    def __lt__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            # comparing apples to oranges - refuse rather than silently
            # comparing raw numbers across currencies
            raise TypeError(f"cannot compare {self.currency} to {other.currency}")
        return self.amount < other.amount

# @total_ordering fills in __le__, __gt__, __ge__ using just __eq__ + __lt__
amounts = [Money("50.00", "USD"), Money("5.00", "USD"), Money("25.00", "USD")]
print("unsorted:", amounts)
print("sorted():", sorted(amounts))
print("Money('5.00','USD') < Money('50.00','USD'):", amounts[1] < amounts[0])
print("Money('50.00','USD') >= Money('50.00','USD'):", amounts[0] >= Money("50.00", "USD"))

try:
    Money("10.00", "USD") < Money("10.00", "EUR")
except TypeError as e:
    print("mismatched-currency comparison correctly raises:", e)

print("\ntotal_ordering generated __le__/__gt__/__ge__ from just __eq__")
print("and __lt__ - the alternative is hand-writing all four yourself,")
print("which is more code but avoids one extra layer of method calls.")


"""
---------------------------------------------------------------------
6. OPERATOR OVERLOADING: __add__ / __radd__ / __iadd__  ⭐⭐⭐
---------------------------------------------------------------------
`__add__`  handles  `a + b`          (a.__add__(b))
`__radd__` handles  `b + a`          ONLY when b.__add__(a) returned
                                       NotImplemented (or b doesn't
                                       define __add__ at all) - this
                                       is exactly what makes sum()
                                       work, since sum() starts with
                                       `0 + first_element`.
`__iadd__` handles  `a += b`         if defined; otherwise `a += b`
                                       silently falls back to
                                       `a = a + b` (i.e. __add__).
---------------------------------------------------------------------
"""

print("\n--- Operator Overloading: __add__, __radd__, __iadd__ ---")

@total_ordering
class Money:
    def __init__(self, amount, currency):
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        return f"{self.currency} {self.amount:.2f}"

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self):
        return hash((self.amount, self.currency))

    def __lt__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(f"cannot compare {self.currency} to {other.currency}")
        return self.amount < other.amount

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(f"cannot add {self.currency} to {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __radd__(self, other):
        # Only reached when `other` is NOT a Money (e.g. the int 0 that
        # sum() starts its accumulator with). Treat plain 0 as identity.
        if other == 0:
            return self
        return NotImplemented

    def __iadd__(self, other):
        # Money is immutable-by-convention here, so += just returns a
        # NEW Money rather than mutating self in place - same result
        # as __add__, but shown explicitly since interviewers ask for it.
        return self.__add__(other)

    def __call__(self, multiplier):
        # covered in section 9 - defined here since we redefine the
        # whole class body each section as it grows.
        return Money(self.amount * Decimal(str(multiplier)), self.currency)

m1 = Money("10.00", "USD")
m2 = Money("5.50", "USD")
print("m1 + m2:", m1 + m2)

m1 += Money("1.00", "USD")
print("m1 after m1 += Money('1.00','USD'):", m1)

# DE use case: summing a batch of per-row cost fields pulled out of an
# ETL stage into a single running total - this is EXACTLY why __radd__
# matters, since sum() internally computes 0 + costs[0] + costs[1] + ...
costs = [Money("12.50", "USD"), Money("7.25", "USD"), Money("3.00", "USD")]
batch_total = sum(costs)
print("sum(costs) via __radd__:", batch_total)

try:
    Money("10.00", "USD") + Money("10.00", "EUR")
except TypeError as e:
    print("mismatched-currency addition correctly raises:", e)


"""
---------------------------------------------------------------------
7. __iter__ / __next__: MAKING A CUSTOM OBJECT ITERABLE  ⭐⭐
---------------------------------------------------------------------
A `for x in obj:` loop calls `iter(obj)` once (which calls
`obj.__iter__()`), then calls `next()` on WHATEVER THAT RETURNED
repeatedly until it raises `StopIteration`. This is the exact
iterator protocol covered conceptually in the earlier Iterators vs
Generators material in this series - here we implement it by hand on
a class instead of using a generator function.

Making `__iter__` return `self` (with the object tracking its own
cursor via `__next__`) is the classic pattern, but it means the
object is a SINGLE-PASS iterator, just like a generator - exhausted
after one full loop unless you reset it.
---------------------------------------------------------------------
"""

print("\n--- __iter__ / __next__ ---")

class Wallet:
    def __init__(self, transactions=None):
        self._transactions = list(transactions) if transactions else []
        self._cursor = 0

    def add(self, money):
        self._transactions.append(money)

    def __len__(self):
        return len(self._transactions)

    def __iter__(self):
        self._cursor = 0     # reset on each NEW iteration request
        return self

    def __next__(self):
        if self._cursor >= len(self._transactions):
            raise StopIteration
        item = self._transactions[self._cursor]
        self._cursor += 1
        return item

wallet = Wallet([Money("10.00", "USD"), Money("25.00", "USD"), Money("5.00", "USD")])
print("iterating with a for-loop:")
for tx in wallet:
    print(" ", tx)

print("iterating again (works because __iter__ resets the cursor):")
print(list(wallet))

print("\nNote: the idiomatic shortcut for a simple wrapper like this is")
print("often just `def __iter__(self): return iter(self._transactions)`,")
print("which delegates to the list's own iterator and naturally")
print("supports independent, concurrent passes without manual cursor")
print("bookkeeping - the hand-rolled __next__ above exists to show the")
print("actual protocol underneath.")


"""
---------------------------------------------------------------------
8. __enter__ / __exit__: A QUICK PREVIEW OF CONTEXT MANAGERS  ⭐
---------------------------------------------------------------------
A full file on Context Managers (the `with` statement, `contextlib`)
comes later in this series - this is just enough to recognize the
two dunders involved:

    with obj as x:      -> x = obj.__enter__()
        ...body...
    (body ends/raises)  -> obj.__exit__(exc_type, exc_value, traceback)

If `__exit__` returns a truthy value, it SUPPRESSES any exception
that occurred in the body; returning `False`/`None` (the usual
choice) lets the exception propagate normally after cleanup runs.
---------------------------------------------------------------------
"""

print("\n--- __enter__ / __exit__ (Preview) ---")

class Wallet:
    def __init__(self, transactions=None):
        self._transactions = list(transactions) if transactions else []
        self._pending = None

    def add(self, money):
        self._transactions.append(money)

    def __len__(self):
        return len(self._transactions)

    def __enter__(self):
        # start a "pending batch" - nothing is committed to the real
        # ledger until the block exits successfully
        self._pending = []
        return self

    def add_pending(self, money):
        self._pending.append(money)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._transactions.extend(self._pending)   # commit
            print(f"  batch committed ({len(self._pending)} transactions)")
        else:
            print(f"  batch rolled back due to {exc_type.__name__}: {exc_value}")
        self._pending = None
        return False   # never suppress the exception

wallet = Wallet()
with wallet as batch:
    batch.add_pending(Money("10.00", "USD"))
    batch.add_pending(Money("5.00", "USD"))
print("len(wallet) after a clean batch:", len(wallet))

try:
    with wallet as batch:
        batch.add_pending(Money("100.00", "USD"))
        raise ValueError("simulated bad row mid-batch")
except ValueError as e:
    print("caught after __exit__ ran:", e)
print("len(wallet) after a rolled-back batch (unchanged):", len(wallet))


"""
---------------------------------------------------------------------
9. __call__: MAKING AN INSTANCE CALLABLE LIKE A FUNCTION  ⭐⭐
---------------------------------------------------------------------
Defining `__call__` lets you write `instance(...)` directly. This is
how function decorators returning objects, scikit-learn-style
transformers, and configurable "callable pipeline steps" work: the
object carries STATE (like a class), but is USED like a function.
`Money.__call__` was defined back in section 6's class body (each
section redefines the whole growing class) - it applies a multiplier
(e.g. a tax or surcharge rate) and returns a NEW Money.
---------------------------------------------------------------------
"""

print("\n--- __call__ ---")

price = Money("100.00", "USD")
print("callable(price):", callable(price))
with_tax = price(Decimal("1.08"))       # price(1.08) -> price.__call__(1.08)
print("price(1.08) applies an 8% surcharge ->", with_tax)
print("original price is unchanged (immutable style):", price)

# DE angle: a family of pre-configured, callable "transform steps" -
# each one is an object with its own state (its multiplier) but is
# invoked exactly like a plain function inside a pipeline.
apply_tax = lambda m: m(Decimal("1.08"))
apply_discount = lambda m: m(Decimal("0.90"))
for step in (apply_tax, apply_discount):
    print(" pipeline step result:", step(price))


"""
=====================================================================
QUICK REFERENCE
=====================================================================
__repr__          -> developer-facing, unambiguous  (repr(), REPL, debuggers)
__str__            -> user-facing, readable           (str(), print(), f"{}")
  no __str__?      -> falls back to __repr__ automatically
  containers        -> ALWAYS print elements via repr(), even if __str__ exists

__eq__             -> defines `==`; return NotImplemented for unrelated types
__hash__           -> REQUIRED alongside __eq__ to stay hashable
  define __eq__ alone -> Python sets __hash__ = None -> TypeError in set/dict
  fix                  -> hash the SAME fields __eq__ compares

__len__            -> powers len(obj); len()==0 also makes obj falsy

__lt__/__le__/__gt__/__ge__ -> powers <, <=, >, >=, and sorted()/sort()
  @functools.total_ordering -> generate the other 3 from __eq__ + __lt__

__add__            -> a + b
__radd__           -> b + a, ONLY when b's own __add__ fails/absent
                        (this is what makes sum([...]) work)
__iadd__           -> a += b (falls back to __add__ if not defined)

__iter__ / __next__ -> for x in obj: ...   (StopIteration ends the loop)
  __iter__ returning self + a cursor -> single-pass, like a generator
  __iter__ returning iter(self._list) -> supports independent passes

__enter__ / __exit__ -> with obj as x: ...  (full topic: later file)
  __exit__ returning True/truthy -> SUPPRESSES the exception

__call__           -> makes an instance usable as instance(...)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - MAGIC / DUNDER METHODS
=====================================================================

1. Why do we override __repr__ and __str__? What is each one FOR,
   and who is the intended audience for each?

2. If a class defines __repr__ but not __str__, what does
   print(instance) actually call? Demonstrate the reasoning, not
   just the answer.

3. Does a list like [m1, m2] use __str__ or __repr__ to print its
   elements, even when both are defined on the element's class? Why
   does that design choice make sense for debugging?

4. Why does defining __eq__ on a class, without also defining
   __hash__, make instances of that class UNHASHABLE? What does
   Python do internally to __hash__ when you define __eq__ alone?

5. What invariant must hold between __eq__ and __hash__, and what
   goes wrong (in terms of set/dict internals) if you violate it?

6. Given the Money class in this file, walk through exactly what
   happens when you try to put two Money instances into a set BEFORE
   __hash__ is defined - what's the exact exception and message?

7. What must __len__ return, and how does defining it affect an
   object's truthiness in an `if` statement?

8. What's the difference between manually defining all four
   comparison dunders (__lt__, __le__, __gt__, __ge__) versus using
   @functools.total_ordering? What's the trade-off?

9. Explain __radd__: why does Money need to define __radd__ (not
   just __add__) for sum(costs) to work, given that sum() starts
   its accumulation from the integer 0?

10. What does Python do when a.__add__(b) returns NotImplemented?
    How does that relate to when __radd__ actually gets called?

11. Does __iadd__ mutate an object in place, or can it return a new
    object instead? What happens if a class doesn't define __iadd__
    at all but does define __add__?

12. Describe the iterator protocol in terms of the dunders involved:
    what does a for-loop call first, and what does it call
    repeatedly after that, and what signals it to stop?

13. In the Wallet class's first __iter__/__next__ implementation,
    why does returning `self` from __iter__ make it a single-pass
    iterator, and what's the idiomatic fix if you need multiple
    independent passes?

14. What are __enter__ and __exit__ each responsible for in a `with`
    statement, and what does it mean if __exit__ returns True versus
    False/None when an exception occurred in the block?

15. What does defining __call__ let you do with an instance, and
    give a real-world scenario (e.g. a configurable pipeline step)
    where a callable OBJECT is preferable to a plain function.

16. How would you design a class to represent a data pipeline/ETL
    job using dunder methods (e.g. __call__ to run it, __repr__ for
    logging, __len__ for how many steps it has)?
=====================================================================
"""
