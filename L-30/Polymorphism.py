"""
=====================================================================
PYTHON POLYMORPHISM - Complete Notes with Executable Examples
=====================================================================

POLYMORPHISM ("many forms") means: the SAME operation - a method
call, an operator, a function - behaves DIFFERENTLY depending on the
actual object it's applied to, without the calling code needing to
know or care exactly what type that object is.

In statically-typed languages (Java, C++), polymorphism is usually
split into two flavors taught side by side: "compile-time" (method
overloading - picking an implementation based on argument types at
compile time) and "runtime" (method overriding through inheritance,
resolved via a vtable when the program runs). Python only really has
the second kind, and even that isn't tied to inheritance the way it
is in those languages - Python has no compiler doing type-based
dispatch at all. EVERY method call is resolved dynamically, at the
moment it happens, by looking at the ACTUAL object in front of you.

Python's deeper philosophy goes further than "runtime dispatch",
though: it doesn't even require a shared base class or interface for
polymorphism to work. This is DUCK TYPING - "if it walks like a duck
and quacks like a duck, treat it like a duck." If an object has the
method or attribute you're about to use, Python lets you use it,
completely regardless of its class hierarchy. Inheritance-based
polymorphism (a shared base class) is one common way to ORGANIZE
duck-typed code and document an intended contract - but it is a
convenience, not a requirement.

This file focuses on polymorphism itself. Two closely related topics
get their own dedicated deep-dive files elsewhere in this repo and
are only touched on briefly here: operator overloading and the full
suite of dunder methods (__str__, __eq__, __len__, etc.), and formal
interfaces via the `abc` module's Abstract Base Classes.
=====================================================================
"""

print("--- Overview ---")
print("Polymorphism = the same call (a method, an operator, a function)")
print("behaves differently depending on the actual object it runs on -")
print("and in Python, that object doesn't need to share any ancestor.")


"""
---------------------------------------------------------------------
1. DUCK TYPING - PYTHON'S CORE POLYMORPHISM PHILOSOPHY  ⭐⭐⭐
---------------------------------------------------------------------
"If it walks like a duck and quacks like a duck, it's a duck." In
Python, an object's SUITABILITY for an operation is judged entirely
by whether it has the right methods/attributes RIGHT NOW - not by
what class it was declared as, or what it inherits from.

This connects directly to two named coding styles:
    LBYL ("Look Before You Leap")  - check first, e.g. with
        `isinstance()` or `hasattr()`, THEN act.
    EAFP ("Easier to Ask Forgiveness than Permission") - just DO the
        operation, and handle the exception if the object turns out
        not to support it.
Python's idioms and standard library strongly favor EAFP - it matches
duck typing's spirit (don't interrogate the object, just try to use
it) and avoids race conditions / redundant checks.
---------------------------------------------------------------------
"""

print("\n--- Duck Typing: Three Unrelated Classes, One Shared Method Name ---")

# These three classes share NO base class, NO common ancestor besides
# `object` itself. They just happen to each define a `.process()`
# method with a compatible signature.
class JSONValidator:
    def process(self, item):
        return f"validated JSON-like structure: {item!r}"

class TextLogger:
    def process(self, item):
        return f"logged to audit trail: {item!r}"

class Uppercaser:
    def process(self, item):
        return str(item).upper()

# Because Python doesn't check declared types, this loop works
# uniformly over all three - it only cares that `.process()` exists.
processors = [JSONValidator(), TextLogger(), Uppercaser()]
for proc in processors:
    print(f"  {type(proc).__name__}: {proc.process('order-42')}")

print("\nNone of these classes inherit from a shared base or interface -")
print("Python never checked their type at all, only that `.process()`")
print("existed on each object at the moment it was called.")

print("\n--- EAFP vs LBYL, Side by Side ---")

mystery_objects = ["a plain string", 12345, JSONValidator()]

# LBYL: check with hasattr() BEFORE calling - an extra step, and
# technically racy in multi-threaded code (the attribute could
# vanish between the check and the call, though rare in practice).
print("LBYL style (check first):")
for obj in mystery_objects:
    if hasattr(obj, "process"):
        print(f"  {obj!r} supports .process() -> {obj.process('x')}")
    else:
        print(f"  {obj!r} has no .process() - skipping (checked in advance)")

# EAFP: just try it, and handle the failure. This is the more
# idiomatic Python style - fewer lines, no redundant lookup, and it
# reads as "try the operation" rather than "interrogate the object".
print("\nEAFP style (ask forgiveness):")
for obj in mystery_objects:
    try:
        print(f"  {obj!r} -> {obj.process('x')}")
    except AttributeError:
        print(f"  {obj!r} doesn't support .process() - caught and moved on")


"""
---------------------------------------------------------------------
2. METHOD OVERRIDING: DYNAMIC DISPATCH, NOT COMPILE-TIME BINDING  ⭐⭐⭐
---------------------------------------------------------------------
"Compile-time vs runtime polymorphism" is a distinction from
statically-typed languages and doesn't really translate to Python.
Python has no compilation step that resolves which method
implementation a call refers to - EVERY `obj.method()` call is
resolved the SAME way, at the exact moment it runs: Python looks at
`type(obj)` and walks its Method Resolution Order (MRO) until it
finds `method`, then binds and calls that implementation.

There is no notion of a variable being "declared as" a base-class
type that then gets "resolved down" to a subclass implementation -
Python variables don't carry a static type at all. The dispatch is
100% determined by the ACTUAL object, checked fresh on every call.
---------------------------------------------------------------------
"""

print("\n--- Overriding: Same Method Name, Different Implementations ---")

class Animal:
    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):          # OVERRIDES Animal.speak
        return "Woof!"

class Cat(Animal):
    def speak(self):          # OVERRIDES Animal.speak
        return "Meow!"

animals = [Dog(), Cat(), Animal()]
for a in animals:
    # Same syntax, same line of code (`a.speak()`) - three different
    # results, decided fresh each iteration by `type(a)`.
    print(f"  {type(a).__name__}.speak() -> {a.speak()}")

print("\nMRO for Dog:", [c.__name__ for c in Dog.__mro__])
print("Python looks up 'speak' by walking this list until it finds it.")

print("\n--- Proof There's No 'Fixed at Declaration' Binding ---")

mystery = Dog()
print("mystery is a Dog right now:", mystery.speak())

# Reassigning an instance's __class__ at runtime is an unusual party
# trick, but it makes the point vividly: dispatch is recalculated
# EVERY time, based on the object's CURRENT actual type - never
# cached or decided in advance.
mystery.__class__ = Cat
print("same variable, same object, class swapped at runtime:", mystery.speak())


"""
---------------------------------------------------------------------
3. SHARED-BASE-CLASS POLYMORPHISM vs PURE DUCK TYPING  ⭐⭐⭐
---------------------------------------------------------------------
Python supports two equally-valid ways to get polymorphic behavior,
and it's a common interview discussion point to contrast them:

    A) A shared base class / interface: subclasses inherit from a
       common parent that declares the expected method(s), which
       documents intent and lets `isinstance()` checks work.
    B) Pure duck typing: completely unrelated classes just happen to
       implement the same method name - no shared ancestor at all.

Python's own standard library and built-ins overwhelmingly favor (B)
by DEFAULT - `len()`, iteration, `+`, etc. all work via duck typing,
not because everything inherits from some universal "Lengthable" or
"Addable" base. A shared base class is a useful ORGANIZING tool, not
a requirement for polymorphism to function. (A full formal-interface
treatment with the `abc` module - `@abstractmethod`, enforcing that
subclasses MUST implement a method - is covered in this repo's
dedicated Abstract Base Classes file; here we just contrast the
plain, non-enforced version.)
---------------------------------------------------------------------
"""

print("\n--- Approach A: Shared Base Class (Documents the Contract) ---")

class DiscountStrategy:
    """An informal interface - not enforced, just documents intent."""
    def apply(self, price):
        raise NotImplementedError("Subclasses must implement apply()")

class PercentageOff(DiscountStrategy):
    def __init__(self, percent):
        self.percent = percent
    def apply(self, price):
        return round(price * (1 - self.percent / 100), 2)

class FlatAmountOff(DiscountStrategy):
    def __init__(self, amount):
        self.amount = amount
    def apply(self, price):
        return round(max(price - self.amount, 0), 2)

print("\n--- Approach B: Pure Duck Typing (No Shared Base At All) ---")

class LoyaltyPointsDiscount:
    """Not related to DiscountStrategy in any way - no inheritance."""
    def apply(self, price):
        return round(price * 0.95, 2)

class ClearanceOverride:
    """Also unrelated - just happens to define apply(price) too."""
    def apply(self, price):
        return 4.99

print("\n--- Both Styles Work IDENTICALLY in a Polymorphic Loop ---")

original_price = 49.99
discounts = [
    PercentageOff(20),        # inherits DiscountStrategy
    FlatAmountOff(10),        # inherits DiscountStrategy
    LoyaltyPointsDiscount(),  # no shared base class
    ClearanceOverride(),      # no shared base class
]
for discount in discounts:
    print(f"  {type(discount).__name__}: ${original_price} -> "
          f"${discount.apply(original_price)}")

print("\nisinstance(PercentageOff(20), DiscountStrategy):",
      isinstance(PercentageOff(20), DiscountStrategy))
print("isinstance(LoyaltyPointsDiscount(), DiscountStrategy):",
      isinstance(LoyaltyPointsDiscount(), DiscountStrategy))
print("Both objects work in the loop above regardless of that answer -")
print("the loop never checked isinstance() at all, only `.apply()`.")


"""
---------------------------------------------------------------------
4. POLYMORPHISM IN PYTHON'S OWN BUILT-INS  ⭐⭐
---------------------------------------------------------------------
The `+` operator and `len()` are themselves polymorphic: the SAME
syntax dispatches to a completely different implementation depending
on operand type, by calling that type's dunder method under the hood
(`__add__` for `+`, `__len__` for `len()`). This is the same dynamic
dispatch principle as method overriding, just triggered by operator
syntax and built-in functions instead of an explicit method call.
---------------------------------------------------------------------
"""

print("\n--- The Same '+' Behaves Differently Per Type ---")

print("1 + 2               ->", 1 + 2, "        (numeric addition)")
print("'ab' + 'cd'         ->", "ab" + "cd", "     (string concatenation)")
print("[1, 2] + [3, 4]     ->", [1, 2] + [3, 4], " (list concatenation)")

print("\n--- The Same len() Behaves Differently Per Type ---")

for value in ["hello", [1, 2, 3, 4], {"a": 1, "b": 2}]:
    # len() doesn't know or care what `value` is - it just calls
    # value.__len__() and returns whatever that implementation gives.
    print(f"  len({value!r}) -> {len(value)}")


"""
---------------------------------------------------------------------
5. OPERATOR OVERLOADING AS A FORM OF POLYMORPHISM (BRIEF)  ⭐⭐
---------------------------------------------------------------------
Defining `__add__` on your OWN class plugs it into the exact same
polymorphic `+` mechanism shown above - now `+` has yet ANOTHER
behavior, this time for your custom type. This is a real, working
example, but it's intentionally brief: the full dunder-method
catalog (__eq__, __repr__, __lt__, __hash__, and the rest) is covered
in depth in this repo's dedicated Magic/Dunder Methods file. The
point here is narrow: operator overloading IS polymorphism - it's
what lets one symbol, `+`, mean something different for every type
that chooses to define it.
---------------------------------------------------------------------
"""

print("\n--- __add__: Making '+' Polymorphic for a Custom Type ---")

class Money:
    def __init__(self, amount, currency="USD"):
        self.amount = amount
        self.currency = currency

    def __add__(self, other):
        if not isinstance(other, Money) or other.currency != self.currency:
            return NotImplemented   # lets Python try other.__radd__ or raise TypeError
        return Money(self.amount + other.amount, self.currency)

    def __repr__(self):
        return f"Money({self.amount}, {self.currency!r})"

wallet_a = Money(20)
wallet_b = Money(5)
print("wallet_a + wallet_b ->", wallet_a + wallet_b)
print("(same '+' syntax as ints/strings/lists above - now dispatching")
print("to Money.__add__ because the LEFT operand is a Money instance)")


"""
---------------------------------------------------------------------
6. STRUCTURAL TYPING WITH typing.Protocol  ⭐⭐
---------------------------------------------------------------------
Pure duck typing (section 3's Approach B) has one downside: static
type checkers (mypy, pyright) and IDEs can't verify it, since there's
no declared relationship between the classes. `typing.Protocol` (PEP
544) bridges the gap: it lets you describe a "shape" a class must
have (which methods, which signatures) WITHOUT that class inheriting
from anything - the class doesn't even need to know the Protocol
exists. This is sometimes called "static duck typing."
---------------------------------------------------------------------
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class Processable(Protocol):
    def process(self, item: str) -> str: ...

# Reusing the Section 1 classes - none of them import or reference
# Processable, yet they satisfy it structurally, just by shape.
print("\n--- Protocol: Checking Structure, Not Inheritance ---")
for proc in [JSONValidator(), TextLogger(), Uppercaser(), Money(1)]:
    print(f"  {type(proc).__name__} matches Processable protocol: "
          f"{isinstance(proc, Processable)}")

print("\nA type checker could use `Processable` as a parameter hint")
print("(def run(p: Processable) -> None) and accept ANY of these")
print("classes - full duck-typing flexibility, with static checking.")


"""
---------------------------------------------------------------------
7. DATA ENGINEERING USE CASE: POLYMORPHIC PIPELINE EXPORTERS  ⭐⭐⭐
---------------------------------------------------------------------
This is the pattern that makes polymorphism matter day-to-day in a
data pipeline: a heterogeneous list of exporter objects, each
targeting a different output format, all invoked through the exact
SAME `.export(data)` call. The calling loop never branches on format
at all - adding a new output format later means writing one new
class, NOT touching the loop.
---------------------------------------------------------------------
"""

import csv
import io
import json

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False

class CSVExporter:
    def export(self, data):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
        return buffer.getvalue()

class JSONExporter:
    def export(self, data):
        return json.dumps(data)

class ParquetExporter:
    """Stub-level: a real production version would tune compression
    codec, row-group size, and partitioning explicitly. This shows
    the real, transferable pyarrow API rather than skipping it."""
    def export(self, data):
        if not PYARROW_AVAILABLE:
            # Never let a missing optional dependency crash the
            # pipeline - simulate the outcome and keep going.
            return f"[simulated] would write {len(data)} rows to Parquet"
        table = pa.Table.from_pylist(data)
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink)
        return f"wrote Parquet buffer: {len(sink.getvalue())} bytes ({len(data)} rows)"

print("\n--- One Loop, Three Completely Different Export Formats ---")

records = [
    {"id": 1, "name": "Widget", "price": 9.99},
    {"id": 2, "name": "Gadget", "price": 19.99},
]
exporters = [CSVExporter(), JSONExporter(), ParquetExporter()]

for exporter in exporters:
    result = exporter.export(records)
    preview = result if len(result) <= 70 else result[:70] + "..."
    print(f"  {type(exporter).__name__}.export(records) -> {preview}")

print("\nAdding a fourth format (e.g. AvroExporter) means writing ONE")
print("new class with an .export() method and appending it to the")
print("`exporters` list above - the for-loop itself never changes.")


"""
---------------------------------------------------------------------
8. WHEN DUCK TYPING BITES: THE MISSING-METHOD CASE  ⭐⭐
---------------------------------------------------------------------
Duck typing's flexibility has a real cost: nothing stops you from
putting an object that DOESN'T implement the expected method into a
polymorphic loop, and Python won't complain until that exact line
runs. In production pipeline code, this means one malformed object
can crash an entire batch job on item #4,999 of 5,000 unless you
handle it deliberately.
---------------------------------------------------------------------
"""

print("\n--- Buggy: One Bad Object Crashes the Whole Loop ---")

class MisconfiguredExporter:
    pass  # forgot to implement export() - an easy real-world mistake

exporters_with_a_bug = [CSVExporter(), MisconfiguredExporter(), JSONExporter()]

try:
    for exporter in exporters_with_a_bug:
        exporter.export(records)   # blows up on the SECOND item
    print("(unreachable - the loop above always raises)")
except AttributeError as e:
    print("Naive loop crashed partway through the batch:", e)
    print("Every exporter AFTER the bad one never even ran.")

print("\n--- Fixed: EAFP Per-Item, So One Bad Object Doesn't Sink the Batch ---")

for exporter in exporters_with_a_bug:
    try:
        result = exporter.export(records)
        print(f"  {type(exporter).__name__}: exported OK")
    except AttributeError:
        print(f"  {type(exporter).__name__}: missing .export() - "
              f"logged and skipped, batch continues")

print("\nEvery well-formed exporter still ran - only the broken one")
print("was skipped, with a clear, localized error message.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Duck typing         -> if it has the method/attribute, use it; the
                        class hierarchy is irrelevant
EAFP (preferred)     -> try the operation, catch the exception
LBYL                 -> hasattr()/isinstance() check BEFORE acting

Method overriding    -> Python resolves EVERY obj.method() call
                        dynamically, at call time, via type(obj) and
                        its MRO - there is no "compile-time" phase
"compile vs runtime  -> not a meaningful distinction in Python; all
 polymorphism"           dispatch is the same dynamic lookup, always

Base-class approach  -> subclasses share a common parent; documents
                        intent, enables isinstance() checks
Pure duck typing     -> unrelated classes, same method name, zero
                        shared ancestry - both work in the same loop

Built-in polymorphism -> `+` -> __add__, `len()` -> __len__, etc.
Operator overloading  -> define __add__ etc. to plug your own type
                          into that same mechanism (full depth: the
                          Magic/Dunder Methods file)
typing.Protocol       -> "static duck typing" - structural shape
                          checking with NO required inheritance
                          (full ABC/enforced-interface depth: the
                          Abstract Base Classes file)

Data pipeline pattern -> list of heterogeneous objects, ONE shared
                          method call (e.g. .export(data)) in a loop
                          -> add new types without touching the loop

Missing-method risk   -> guard polymorphic loops with try/except
                          AttributeError (or hasattr()) so one bad
                          object can't crash an entire batch
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - POLYMORPHISM
=====================================================================

1. What does "if it walks like a duck and quacks like a duck..."
   mean in the context of Python, and how does that philosophy
   differ from polymorphism in a statically-typed language like
   Java or C++?

2. Explain the difference between EAFP and LBYL. Which style does
   idiomatic Python favor, and why?

3. In this file's `DiscountStrategy` example, does a class need to
   inherit from `DiscountStrategy` to be usable in the polymorphic
   `discounts` loop? Why or why not?

4. Why doesn't Python have "method overloading" in the C++/Java
   sense (multiple same-named methods distinguished by parameter
   types)? What does Python typically do instead to get similar
   flexibility?

5. When you call `a.speak()` in a loop over a mixed list of `Dog`,
   `Cat`, and `Animal` instances, at what point does Python decide
   WHICH `speak()` implementation runs? Describe the actual lookup
   mechanism.

6. What is Method Resolution Order (MRO), and how would you inspect
   a class's MRO from code?

7. In the file, `mystery.__class__` is reassigned from `Dog` to
   `Cat` at runtime, and `mystery.speak()` immediately starts
   returning `"Meow!"`. What does this prove about how and when
   Python dispatches methods?

8. How does the `+` operator achieve different behavior across
   `int`, `str`, and `list`? Which dunder method does it call under
   the hood, and what does `NotImplemented` (as returned from
   `Money.__add__`) signal to Python when types don't match?

9. What is the difference between duck typing and structural typing
   via `typing.Protocol`? Why might a codebase prefer `Protocol`
   over both plain duck typing and an ABC?

10. In the `CSVExporter` / `JSONExporter` / `ParquetExporter`
    example, what would you need to change if you added a fourth
    `AvroExporter` class? What does that answer illustrate about
    why polymorphism matters in pipeline design?

11. Given a loop that calls `.export(data)` on a list of exporter
    objects, one of which doesn't implement `.export()`, would you
    guard it with `hasattr()` beforehand or a `try/except
    AttributeError` around each call? Justify your choice, including
    what happens to the REST of the batch in each approach.

12. Is operator overloading (defining `__add__`, `__eq__`, etc.) a
    form of polymorphism? Explain the connection to method
    overriding.

13. Contrast polymorphism achieved through inheritance/overriding
    (Section 3, Approach A) with polymorphism achieved through pure
    duck typing with no shared base class at all (Approach B). What
    do you gain and lose with each?

14. Why is the "compile-time vs runtime polymorphism" distinction
    commonly drawn in Java/C++ interviews not really meaningful to
    draw in Python?

15. How would you design a data pipeline's transformation step so
    that adding a brand-new record type doesn't require modifying
    any existing `if isinstance(...)` chain? (Hint: what does this
    file's `processors`/`exporters` loop pattern avoid doing?)
=====================================================================
"""
