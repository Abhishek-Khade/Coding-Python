"""
=====================================================================
PYTHON INHERITANCE - Complete Notes with Executable Examples
=====================================================================

INHERITANCE lets a class (the "child"/"subclass") acquire the
attributes and methods of another class (the "parent"/"superclass"),
modeling an "is-a" relationship: a `PostgresDataSource` IS-A
`DataSource`. It is the primary mechanism for CODE REUSE and
POLYMORPHISM in Python's object model.

The interview-relevant machinery sits on top of that simple idea:
    - `super()` lets a subclass call its parent's implementation
      instead of duplicating it, and lets you EXTEND behavior rather
      than replace it outright.
    - Python supports MULTIPLE inheritance (a class with more than
      one parent), which reintroduces a classic problem from C++:
      the DIAMOND PROBLEM - ambiguity about which parent's method
      runs when two parents share a common ancestor.
    - Python resolves that ambiguity deterministically using the
      C3 LINEARIZATION algorithm, exposed as a class's
      METHOD RESOLUTION ORDER (MRO) - "what is MRO?" is one of the
      most common OOP interview questions, precisely because most
      candidates have never actually looked at `ClassName.__mro__`.
    - `isinstance()` is the idiomatic way to check "is this object a
      kind of X" (it respects inheritance); `type(obj) == X` does not,
      and is a common code-smell in review.
    - Inheritance is a tool, not the default choice. Senior engineers
      are expected to know the "favor composition over inheritance"
      principle: when a class hierarchy models a "HAS-A"
      relationship (a pipeline HAS-A reader, HAS-A validator) rather
      than an "IS-A" relationship, wiring in small collaborator
      objects (composition) is usually more flexible than building a
      subclass for every combination.

This file uses a data-engineering "DataSource" hierarchy throughout,
since designing class hierarchies for extractors/loaders is a
realistic on-the-job (and interview whiteboard) scenario.
=====================================================================
"""

print("--- Overview ---")
print("Inheritance = a subclass acquires a parent's attributes and")
print("methods, modeling an 'is-a' relationship and enabling reuse.")


"""
---------------------------------------------------------------------
1. BASIC SINGLE INHERITANCE & super().__init__()  ⭐⭐⭐
---------------------------------------------------------------------
A subclass declares its parent in parentheses: `class Child(Parent):`.
Inside the subclass's own `__init__`, calling `super().__init__(...)`
delegates to the PARENT's `__init__` to do the parent's setup work,
instead of re-writing (and risking divergence from) that logic.
`super()` looks up the NEXT class in the MRO relative to the current
class - for single inheritance that's simply "the parent".
---------------------------------------------------------------------
"""

print("\n--- Basic Single Inheritance & super().__init__() ---")

class DataSource:
    """Base class for anything that can connect to and describe a source of data."""

    def __init__(self, name, connection_string):
        self.name = name
        self.connection_string = connection_string
        self.is_connected = False

    def connect(self):
        self.is_connected = True
        print(f"  [{self.name}] connected using '{self.connection_string}'")

    def describe(self):
        return f"DataSource(name={self.name!r}, connected={self.is_connected})"


class PostgresDataSource(DataSource):
    """A DataSource specialized for Postgres - adds a port, reuses the rest."""

    def __init__(self, name, connection_string, port=5432):
        super().__init__(name, connection_string)   # let the parent set name/connection_string/is_connected
        self.port = port                              # then add the subclass-specific attribute

    def describe(self):
        # extends the parent's describe() by reusing it and appending to it
        return f"{super().describe()}, port={self.port}"


pg = PostgresDataSource("warehouse", "postgresql://analytics-db", port=5433)
print(pg.describe())
pg.connect()                        # connect() is INHERITED, not redefined - full reuse
print(pg.describe())
print("PostgresDataSource.__bases__:", PostgresDataSource.__bases__)


"""
---------------------------------------------------------------------
2. OVERRIDING METHODS: EXTENDING vs FULLY REPLACING  ⭐⭐⭐
---------------------------------------------------------------------
A subclass can OVERRIDE a parent method by redefining it with the
same name. There are two very different ways to do this:
    - EXTEND: call `super().method()` first (or last), then add more
      behavior on top - the parent's logic still runs.
    - REPLACE: write a brand new method body that never calls
      `super()` at all - the parent's logic is gone entirely.
Replacing is sometimes exactly what you want, but it's also a common
SOURCE OF BUGS when a subclass author doesn't realize the parent's
version was doing important work (like a validation check) that
silently stops happening.
---------------------------------------------------------------------
"""

print("\n--- Overriding: Extending vs Fully Replacing ---")

class DataSourceV2(DataSource):
    def validate(self):
        # the base contract: a data source must have a non-empty connection string
        ok = bool(self.connection_string)
        print(f"  [base validate] connection_string non-empty: {ok}")
        return ok


class BuggyCsvSource(DataSourceV2):
    def validate(self):
        # BUGGY: fully REPLACES validate() and never calls super().validate() -
        # the base's connection_string check is silently lost.
        ok = self.name.endswith(".csv")
        print(f"  [buggy override] name ends with .csv: {ok}")
        return ok

buggy = BuggyCsvSource("orders.csv", connection_string="")   # empty connection string!
print("buggy.validate():", buggy.validate())
print("  -> BUG: passed validation with an EMPTY connection_string, because the")
print("     override replaced the base check instead of extending it.")

class FixedCsvSource(DataSourceV2):
    def validate(self):
        # FIXED: EXTENDS the base check by calling super() first, then AND-ing
        # in the subclass-specific rule - both requirements must hold.
        base_ok = super().validate()
        name_ok = self.name.endswith(".csv")
        print(f"  [fixed override] name ends with .csv: {name_ok}")
        return base_ok and name_ok

fixed = FixedCsvSource("orders.csv", connection_string="")
print("fixed.validate():", fixed.validate())
print("  -> correctly False: the base's connection_string rule still applies.")


"""
---------------------------------------------------------------------
3. MULTIPLE INHERITANCE & THE DIAMOND PROBLEM  ⭐⭐⭐
---------------------------------------------------------------------
Python allows a class to inherit from MORE than one parent:
`class Child(ParentA, ParentB):`. This becomes tricky when both
parents share a common ANCESTOR - the classic "diamond" shape:

            Base
           /    \\
        Left    Right
           \\    /
          Bottom

If `Bottom` doesn't override a method that `Left`, `Right`, AND
`Base` all define, which version runs? In C++ this is famously
ambiguous. Python resolves it DETERMINISTICALLY via the MRO
(next section) - but you still need to understand the shape of the
problem first.
---------------------------------------------------------------------
"""

print("\n--- Multiple Inheritance & the Diamond Problem ---")

class Base:
    def process(self):
        print("  Base.process: raw ingestion step")

class Left(Base):
    def process(self):
        print("  Left.process: applying schema step")
        super().process()          # cooperatively calls the NEXT class in the MRO

class Right(Base):
    def process(self):
        print("  Right.process: applying dedup step")
        super().process()          # also calls the NEXT class in the MRO

class Bottom(Left, Right):
    pass                             # does NOT override process() itself

print("Calling Bottom().process() - which class's code actually runs?")
Bottom().process()
print("Note Right.process() DID run, even though Bottom only lists Left first")
print("and Left.process()'s super() call was written with only Base in mind -")
print("this is exactly the diamond ambiguity the MRO exists to resolve.")


"""
---------------------------------------------------------------------
4. METHOD RESOLUTION ORDER (MRO) - C3 LINEARIZATION  ⭐⭐⭐
---------------------------------------------------------------------
Every class has a precise, inspectable MRO: the linear ORDER Python
searches through its ancestors to find an attribute/method. Python
computes this using the C3 LINEARIZATION algorithm, which guarantees:
    - a class always appears BEFORE its parents,
    - the LOCAL declaration order of parents is preserved
      (`class Bottom(Left, Right)` keeps Left before Right),
    - and a shared ancestor (Base) is only visited ONCE, AFTER all
      of its children.
`super()` doesn't mean "my parent" - it means "the NEXT class after
me in the MRO". That's why Right.process() ran above: Bottom's MRO
places Right between Left and Base.
---------------------------------------------------------------------
"""

print("\n--- Method Resolution Order (MRO) ---")

print("Bottom.__mro__:")
for cls in Bottom.__mro__:
    print("   ", cls)

print("\nBottom.mro()  (same information, as a callable method):")
print("  ", [c.__name__ for c in Bottom.mro()])

print("\nThis is the C3 linearization: Bottom -> Left -> Right -> Base -> object.")
print("Reading Left.process()'s `super().process()` call in light of THIS order")
print("(not just 'Left's parent is Base') is the key insight interviewers probe.")


"""
---------------------------------------------------------------------
5. isinstance() vs type(obj) ==  FOR INHERITANCE CHECKS  ⭐⭐⭐
---------------------------------------------------------------------
`isinstance(obj, Cls)` returns True if `obj` is an instance of `Cls`
OR any SUBCLASS of `Cls` - it respects the inheritance hierarchy and
therefore SUPPORTS POLYMORPHISM. `type(obj) == Cls` only matches the
EXACT class, breaking the moment someone introduces a subclass -
which defeats the entire point of writing polymorphic code against a
base type. `isinstance` also accepts a TUPLE of types, and correctly
recognizes classes registered as "virtual subclasses" of an ABC.
`isinstance` is therefore the interview-correct, Pythonic answer.
---------------------------------------------------------------------
"""

print("\n--- isinstance() vs type(obj) == for Inheritance Checks ---")

def is_ready_data_source_isinstance(obj):
    # correct: recognizes DataSource AND any subclass of it (Postgres, CSV, ...)
    return isinstance(obj, DataSource)

def is_ready_data_source_type_eq(obj):
    # WRONG for this purpose: only matches the exact base class
    return type(obj) == DataSource

print("pg is a PostgresDataSource (a DataSource subclass):")
print("  isinstance(pg, DataSource):", is_ready_data_source_isinstance(pg))
print("  type(pg) == DataSource:   ", is_ready_data_source_type_eq(pg))
print("  -> type()== silently rejects a perfectly valid subclass instance.")

print("\nisinstance also accepts a tuple of types in one call:")
print("  isinstance(pg, (int, PostgresDataSource)):",
      isinstance(pg, (int, PostgresDataSource)))


"""
---------------------------------------------------------------------
6. COOPERATIVE MULTIPLE INHERITANCE: MIXINS  ⭐⭐
---------------------------------------------------------------------
The most PRACTICAL use of multiple inheritance in real pipeline code
isn't a deep diamond - it's MIXINS: small classes that each add one
independent piece of behavior (timestamping, retry logic) and are
combined onto a real class. Each mixin's `__init__` cooperatively
calls `super().__init__(**kwargs)` and passes along whatever it
didn't consume, so the whole MRO chain runs cleanly regardless of
combination order.
---------------------------------------------------------------------
"""

print("\n--- Cooperative Multiple Inheritance: Mixins ---")

class TimestampMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)          # pass remaining kwargs down the MRO
        import datetime
        self.created_at = datetime.datetime(2026, 8, 25, 9, 0, 0)

class RetryMixin:
    def __init__(self, max_retries=3, **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries

class RetryableCsvExtractor(RetryMixin, TimestampMixin, DataSource):
    def __init__(self, name, connection_string, max_retries=3):
        # every ancestor's __init__ runs exactly once, in MRO order
        super().__init__(name=name, connection_string=connection_string, max_retries=max_retries)

extractor = RetryableCsvExtractor("orders_extractor", "s3://bucket/orders.csv", max_retries=5)
print("RetryableCsvExtractor.__mro__:", [c.__name__ for c in RetryableCsvExtractor.mro()])
print("extractor.max_retries:", extractor.max_retries)     # from RetryMixin
print("extractor.created_at: ", extractor.created_at)        # from TimestampMixin
print("extractor.name:       ", extractor.name)                # from DataSource


"""
---------------------------------------------------------------------
7. ABSTRACT BASE CLASSES: ENFORCING AN INTERFACE CONTRACT  ⭐⭐
---------------------------------------------------------------------
Inheritance is also how Python enforces "every subclass MUST
implement this method" contracts, via the `abc` module. A class that
inherits from `ABC` and marks a method `@abstractmethod` CANNOT be
instantiated directly until every abstract method is overridden -
this catches "forgot to implement extract()" bugs at OBJECT CREATION
time instead of at some random point deep in a pipeline run.
---------------------------------------------------------------------
"""

print("\n--- Abstract Base Classes: Enforcing an Interface Contract ---")

from abc import ABC, abstractmethod

class Extractor(ABC):
    @abstractmethod
    def extract(self):
        """Every concrete Extractor must implement this."""

try:
    Extractor()                     # can't instantiate - it still has an unimplemented abstractmethod
except TypeError as e:
    print("Error instantiating abstract Extractor directly:", e)

class ApiExtractor(Extractor):
    def extract(self):
        return {"rows": 42, "source": "api"}

api_extractor = ApiExtractor()      # fine - the contract is satisfied
print("ApiExtractor().extract():", api_extractor.extract())


"""
---------------------------------------------------------------------
8. COMPOSITION vs INHERITANCE: FAVOR COMPOSITION  ⭐⭐⭐
---------------------------------------------------------------------
"Favor composition over inheritance" means: before modeling a
relationship as a subclass (IS-A), check whether it's really a
HAS-A relationship that a small, injected collaborator object could
express more flexibly. The warning sign for over-using inheritance
is CLASS EXPLOSION: needing a new subclass for every COMBINATION of
behaviors (a CSV source that's also rate-limited, a JSON source
that's also rate-limited, ...) instead of just composing the pieces.
---------------------------------------------------------------------
"""

print("\n--- Composition vs Inheritance: Favor Composition ---")

# --- INHERITANCE approach: one subclass per (format x validation) combination ---
class InheritedCsvSource(DataSource):
    def read(self):
        return "id,amount\n1,9.99"
    def validate(self, raw):
        return "," in raw                       # CSV-specific rule, baked into the class

class InheritedJsonSource(DataSource):
    def read(self):
        return '{"id": 1, "amount": 9.99}'
    def validate(self, raw):
        return raw.strip().startswith("{")      # JSON-specific rule, baked into the class

for src in (InheritedCsvSource("csv_src", "file://a.csv"),
            InheritedJsonSource("json_src", "file://a.json")):
    raw = src.read()
    print(f"  [inheritance] {src.name}: valid={src.validate(raw)}")
print("  -> works, but a NEW rate-limited variant needs a NEW subclass PER")
print("     format (RateLimitedCsvSource, RateLimitedJsonSource, ...) - class")
print("     explosion as more independent behaviors are added.")

# --- COMPOSITION approach: inject small reader/validator collaborators instead ---
def read_csv():
    return "id,amount\n1,9.99"

def read_json():
    return '{"id": 1, "amount": 9.99}'

def validate_csv(raw):
    return "," in raw

def validate_json(raw):
    return raw.strip().startswith("{")

class ComposedDataSource:
    """HAS-A reader function and HAS-A validator function - no subclassing needed."""

    def __init__(self, name, reader, validator):
        self.name = name
        self._reader = reader          # composed-in collaborator, not inherited behavior
        self._validator = validator    # composed-in collaborator, not inherited behavior

    def load(self):
        raw = self._reader()
        return raw, self._validator(raw)

for src in (ComposedDataSource("csv_src", read_csv, validate_csv),
            ComposedDataSource("json_src", read_json, validate_json)):
    raw, is_valid = src.load()
    print(f"  [composition] {src.name}: valid={is_valid}")
print("  -> adding a NEW capability (e.g. rate limiting) means composing in ONE")
print("     more collaborator - no new class per format x capability combination.")


"""
---------------------------------------------------------------------
9. COMMON INHERITANCE PITFALLS  ⭐⭐
---------------------------------------------------------------------
Two mistakes come up constantly in real code review and interviews:
mutable CLASS attributes accidentally being SHARED across every
instance (and every subclass), and forgetting to call
`super().__init__()` at all, leaving inherited state uninitialized.
---------------------------------------------------------------------
"""

print("\n--- Common Inheritance Pitfalls ---")

# PITFALL 1: a mutable default defined at CLASS level is ONE shared object
class BuggyPipeline:
    processed_ids = []              # BUGGY: this list is shared by ALL instances!

    def mark_processed(self, record_id):
        self.processed_ids.append(record_id)

p1 = BuggyPipeline()
p2 = BuggyPipeline()
p1.mark_processed(101)
print("p2.processed_ids after only p1 processed something:", p2.processed_ids)
print("  -> BUG: p2 sees p1's data - `processed_ids` is a single class-level list.")

class FixedPipeline:
    def __init__(self):
        self.processed_ids = []     # FIXED: a fresh list per INSTANCE, set in __init__

    def mark_processed(self, record_id):
        self.processed_ids.append(record_id)

p3 = FixedPipeline()
p4 = FixedPipeline()
p3.mark_processed(101)
print("p4.processed_ids after only p3 processed something:", p4.processed_ids)
print("  -> correctly empty: each instance owns its own list.")

# PITFALL 2: forgetting to call super().__init__() leaves parent state missing
class ForgetfulSource(DataSource):
    def __init__(self, name):
        self.name = name             # never calls super().__init__() - connection_string/is_connected never set!

forgetful = ForgetfulSource("broken_source")
try:
    forgetful.connect()
except AttributeError as e:
    print("Error from a subclass that skipped super().__init__():", e)
print("  -> the fix is simply calling super().__init__(name, connection_string)")
print("     inside ForgetfulSource.__init__, as PostgresDataSource does in Section 1.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Declare inheritance         -> class Child(Parent):
Call parent's __init__      -> super().__init__(...)
Extend a method              -> call super().method(), then add more
Fully replace a method       -> override without calling super() at all
                                 (valid, but loses the parent's logic)

Diamond shape                -> Base <- Left, Right <- Bottom(Left, Right)
super() means                -> "next class in the MRO", NOT "my parent"

Inspect MRO                  -> ClassName.__mro__   (tuple)
                                 ClassName.mro()      (list, same info)
MRO algorithm                -> C3 linearization: child before parents,
                                 declared-parent order preserved, each
                                 shared ancestor visited exactly once

isinstance(obj, Cls)         -> True for Cls AND any subclass  (preferred)
type(obj) == Cls              -> True ONLY for the exact class  (avoid)

Mixins                        -> small single-purpose parent classes,
                                 combined via multiple inheritance,
                                 cooperating through super().__init__(**kwargs)

abc.ABC + @abstractmethod    -> subclass MUST implement it, or
                                 instantiation raises TypeError

Composition over inheritance -> prefer HAS-A (inject collaborator
                                 objects/functions) over IS-A when you'd
                                 otherwise need a subclass per
                                 combination of independent behaviors

Pitfall: mutable class attr  -> defined on the class = shared by ALL
                                 instances; fix by assigning in __init__
Pitfall: skipping super()    -> parent's attributes never get set;
                                 AttributeError later when they're used
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - INHERITANCE
=====================================================================

1. What is Method Resolution Order (MRO), and what algorithm does
   Python use to compute it?

2. Given `class Bottom(Left, Right)` where both `Left` and `Right`
   inherit from `Base`, walk through `Bottom.__mro__` and explain WHY
   `Right.process()` ran before `Base.process()` when `Left.process()`
   called `super().process()`.

3. What does `super()` actually refer to - "the parent class," or
   something else? Justify your answer using the diamond example.

4. Explain the "diamond problem" in multiple inheritance. How does
   Python's MRO make it deterministic instead of ambiguous?

5. What is the difference between OVERRIDING a method to fully
   replace the parent's behavior versus EXTENDING it by calling
   `super().method()` first? Give an example of a bug caused by
   accidentally doing the former when you meant the latter.

6. Why does `isinstance(obj, Cls)` return `True` for subclass
   instances while `type(obj) == Cls` does not? Why is `isinstance`
   generally preferred in production code?

7. In `RetryableCsvExtractor(RetryMixin, TimestampMixin, DataSource)`,
   why does every mixin's `__init__` call
   `super().__init__(**kwargs)` instead of calling `DataSource`
   directly? What would break if one mixin forgot to call `super()`?

8. What happens if you instantiate an `abc.ABC` subclass that hasn't
   implemented all of its `@abstractmethod`s? At what point does the
   error occur - class definition, or instantiation?

9. Explain "favor composition over inheritance." Using the CSV/JSON
   `DataSource` example in this file, what problem does the
   inheritance version run into as you add more independent
   behaviors (e.g., rate limiting, retries)?

10. What bug does defining `processed_ids = []` at the CLASS level
    (instead of inside `__init__`) cause, and why does assigning it
    inside `__init__` fix it?

11. What happens if a subclass's `__init__` never calls
    `super().__init__()`? Walk through the `ForgetfulSource` example
    and explain exactly why `connect()` then raises an
    `AttributeError`.

12. How would you design a class hierarchy (or composition-based
    alternative) to represent multiple types of ETL data sources
    (CSV, JSON, database) that share some behavior but differ in
    how they read and validate data?

13. Can you change a class's MRO by changing the ORDER of base
    classes in `class Child(A, B):` versus `class Child(B, A):`?
    What would that change about which method runs first?

14. Why can't you always freely mix arbitrary base classes in Python
    (hint: consider two base classes with INCOMPATIBLE MROs)? You
    don't need to produce the exact error - just explain what kind
    of conflict causes `TypeError: Cannot create a consistent MRO`.

15. What's the difference between `isinstance()` also accepting a
    tuple of types (e.g. `isinstance(x, (int, float))`) and needing
    multiple `type(x) ==` comparisons chained with `or`?
=====================================================================
"""
