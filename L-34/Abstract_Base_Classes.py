"""
=====================================================================
ABSTRACT BASE CLASSES (the abc module) - Complete Notes with
Executable Examples
=====================================================================

Python is a DUCK-TYPED language: "if it walks like a duck and quacks
like a duck, it's a duck." You normally don't need to declare formal
interfaces - if an object has the method you call, it works, full
stop. So why does Python ALSO ship a formal `abc` module for defining
strict, enforced interfaces?

Because duck typing has a real cost in larger codebases: if a class
is SUPPOSED to implement `.connect()` and `.read()` but a developer
forgets `.read()`, duck typing won't tell you until some code path
finally CALLS `.read()` on that object - which might be minutes,
days, or a production incident later, deep inside a call stack far
from where the object was created. An Abstract Base Class (ABC) moves
that failure all the way up to INSTANTIATION time: you get a loud,
immediate `TypeError` the moment you try to create the broken
subclass, not a mysterious `AttributeError` buried in a log file.

ABCs give you three concrete things duck typing alone does not:
    1. A FORMAL CONTRACT - the base class declares exactly which
       methods a subclass MUST implement to be considered "complete."
    2. FAIL-FAST INSTANTIATION - missing an abstract method raises
       `TypeError` at `SubClass()` time, not at first-use time.
    3. SELF-DOCUMENTING APIS - anyone reading the ABC immediately
       sees the full required interface in one place, instead of
       having to grep the codebase for every method some caller
       happens to invoke.

This makes `abc` a natural fit for designing pluggable components -
exactly the shape of an ETL "connector" interface, which is the
running example used below.
=====================================================================
"""

from abc import ABC, abstractmethod
import collections.abc

print("--- Overview ---")
print("abc.ABC + @abstractmethod turn an informal duck-typed contract")
print("into one Python enforces: instantiate an incomplete subclass")
print("and you get an immediate TypeError, not a later AttributeError.")


"""
---------------------------------------------------------------------
1. DUCK TYPING'S BLIND SPOT: ERRORS SURFACE LATE  ⭐⭐⭐
---------------------------------------------------------------------
Without an ABC, "requiring" a method is just a comment or a docstring
- Python has no way to enforce it. A subclass that forgets to
implement a required method looks completely fine right up until the
specific code path that calls the missing method finally runs.
---------------------------------------------------------------------
"""

print("\n--- Duck Typing's Blind Spot ---")

# An informal, UNENFORCED "interface" - just a convention in a comment.
class DuckTypedConnector:
    # Subclasses are "supposed to" implement connect() and read(),
    # but nothing in the language actually requires it.
    def close(self):
        print("  closing connection")

class ForgetfulConnector(DuckTypedConnector):
    def connect(self):
        print("  connected")
    # oops - forgot to implement read()!

conn = ForgetfulConnector()          # <-- this line succeeds, no warning at all
conn.connect()                        # <-- this line also succeeds
print("Object created and partially used with NO error so far...")

try:
    conn.read()                       # <-- the bug only surfaces HERE, on first use
except AttributeError as e:
    print("Error only surfaces when .read() is finally CALLED:", e)

print("\nIn a real pipeline, that .read() call could be buried deep")
print("inside a scheduler, minutes or days after the object was built.")
print("An ABC would have caught this at `ForgetfulConnector()` time.")


"""
---------------------------------------------------------------------
2. abc.ABC AND @abstractmethod: ENFORCING THE CONTRACT  ⭐⭐⭐
---------------------------------------------------------------------
Inherit from `ABC` and mark required methods with `@abstractmethod`.
Python then refuses to INSTANTIATE any subclass that hasn't overridden
every abstract method - the check happens at `SubClass()` call time,
via a special metaclass (`ABCMeta`) that ABC sets up for you.
---------------------------------------------------------------------
"""

print("\n--- abc.ABC and @abstractmethod ---")

class Shape(ABC):
    @abstractmethod
    def area(self):
        """Subclasses MUST override this to be instantiable."""

# BUGGY: Square never implements the abstract method `area`.
class BrokenSquare(Shape):
    def __init__(self, side):
        self.side = side
    # area() is missing entirely!

try:
    BrokenSquare(4)                   # fails at INSTANTIATION, not at .area() call
except TypeError as e:
    print("Error instantiating an incomplete ABC subclass:", e)

# FIXED: implement every abstract method and it instantiates cleanly.
class Square(Shape):
    def __init__(self, side):
        self.side = side
    def area(self):
        return self.side ** 2

square = Square(4)
print("Fixed subclass instantiates fine. square.area():", square.area())

try:
    Shape()                           # can't instantiate the ABC itself either
except TypeError as e:
    print("Error instantiating the ABC directly:", e)


"""
---------------------------------------------------------------------
3. ABSTRACT METHODS CAN HAVE A DEFAULT BODY  ⭐⭐
---------------------------------------------------------------------
A commonly missed nuance: `@abstractmethod` does NOT mean "this method
must be empty." The decorated method can contain real, shared logic -
subclasses are still FORCED to override it (so the contract is still
enforced), but their override can call back into the base
implementation with `super().method(...)` to reuse that shared logic
instead of duplicating it.
---------------------------------------------------------------------
"""

print("\n--- Abstract Methods With a Default Implementation ---")

class Exporter(ABC):
    @abstractmethod
    def export(self, rows):
        # This is a REAL default implementation, not just a stub -
        # subclasses can still call it via super().export(rows).
        print(f"  [base] validating {len(rows)} row(s) before export")

class JSONExporter(Exporter):
    def export(self, rows):
        super().export(rows)          # reuse the base class's validation logic
        print(f"  [json] writing {rows} as JSON")

# Still enforced: a subclass that skips overriding export() entirely
# cannot be instantiated, even though export() has a real body above.
class BrokenExporter(Exporter):
    pass

try:
    BrokenExporter()
except TypeError as e:
    print("Still enforced even though the abstract method has a body:", e)

json_exporter = JSONExporter()
json_exporter.export([{"id": 1}, {"id": 2}])
print("The subclass got shared validation logic AND its own logic,")
print("by calling super().export(rows) instead of duplicating code.")


"""
---------------------------------------------------------------------
4. ABSTRACT PROPERTIES: @property + @abstractmethod  ⭐⭐
---------------------------------------------------------------------
You can require subclasses to provide a PROPERTY, not just a method,
by stacking `@property` ABOVE `@abstractmethod` (order matters -
`@property` must be the outermost decorator). This is useful for
enforcing "every subclass must expose this piece of read-only
metadata," e.g. a connector's `source_name`.
---------------------------------------------------------------------
"""

print("\n--- Abstract Properties ---")

class Connector(ABC):
    @property
    @abstractmethod
    def source_name(self):
        """Subclasses must expose a human-readable source name."""

class BrokenConnector(Connector):
    pass   # doesn't define source_name at all

try:
    BrokenConnector()
except TypeError as e:
    print("Missing abstract property blocks instantiation too:", e)

class NamedConnector(Connector):
    @property
    def source_name(self):
        return "demo-source"

nc = NamedConnector()
print("nc.source_name (accessed like an attribute, no parens):", nc.source_name)


"""
---------------------------------------------------------------------
5. DATA ENGINEERING EXAMPLE: A DataConnector ABC  ⭐⭐⭐
---------------------------------------------------------------------
This is the classic "connector" pattern behind real ETL frameworks:
one abstract base class defines the required lifecycle
(connect -> read -> close), and each concrete data source implements
that lifecycle in its own way. Any code written against
`DataConnector` works with ANY current or future connector, without
caring whether it's a CSV file, a REST API, a database, or a queue.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Example: DataConnector ABC ---")

class DataConnector(ABC):
    """Formal contract every data source connector must satisfy."""

    def __init__(self, source):
        self.source = source
        self._is_connected = False

    @abstractmethod
    def connect(self):
        """Open whatever resource is needed (file handle, socket, session)."""

    @abstractmethod
    def read(self):
        """Return the records available from this source."""

    @abstractmethod
    def close(self):
        """Release the resource opened in connect()."""

    def run(self):
        # A concrete "template method" built entirely on the abstract
        # contract above - it works for ANY subclass, present or future,
        # because it only relies on the guaranteed interface.
        self.connect()
        rows = self.read()
        self.close()
        return rows


class CSVConnector(DataConnector):
    def connect(self):
        self._is_connected = True
        print(f"  [csv] opened file handle for '{self.source}'")

    def read(self):
        if not self._is_connected:
            raise RuntimeError("must call connect() before read()")
        # Simulated CSV rows - in production this would use csv.DictReader
        # over an open file handle from connect().
        return [{"id": 1, "amount": 19.99}, {"id": 2, "amount": 42.00}]

    def close(self):
        self._is_connected = False
        print(f"  [csv] closed file handle for '{self.source}'")


class APIConnector(DataConnector):
    def __init__(self, source, api_key):
        super().__init__(source)
        self.api_key = api_key
        self._session = None

    def connect(self):
        # In production: self._session = requests.Session(); auth headers, etc.
        self._session = {"authorized": True, "key": self.api_key}
        print(f"  [api] opened session against '{self.source}'")

    def read(self):
        if not self._session:
            raise RuntimeError("must call connect() before read()")
        # Simulated paginated API response - in production this would be
        # requests.get(self.source, headers=..., params={"page": n}).json()
        return [{"id": 101, "amount": 7.50}]

    def close(self):
        self._session = None
        print(f"  [api] closed session against '{self.source}'")


try:
    DataConnector("nowhere")          # can't instantiate the abstract base itself
except TypeError as e:
    print("Cannot instantiate the abstract DataConnector directly:", e)

# Both concrete connectors satisfy the SAME contract, so calling code
# doesn't need to know or care which one it's holding.
connectors = [
    CSVConnector("orders.csv"),
    APIConnector("https://api.example.com/orders", api_key="secret-key-placeholder"),
]

for connector in connectors:
    print(f"running {type(connector).__name__} via the shared run() template:")
    rows = connector.run()
    print("  rows:", rows)


"""
---------------------------------------------------------------------
6. collections.abc: READY-MADE ABSTRACT INTERFACES  ⭐⭐
---------------------------------------------------------------------
Python doesn't just let YOU build ABCs - the standard library ships a
whole family of them in `collections.abc` describing the built-in
protocols: `Iterable`, `Iterator`, `Sequence`, `Mapping`, `Callable`,
etc. `isinstance()` checks against these are the idiomatic way to ask
"does this object support the FOR-LOOP protocol / dict protocol /
etc." without hardcoding a check against `list`, `dict`, and every
other concrete type you can think of.
---------------------------------------------------------------------
"""

print("\n--- collections.abc: Ready-Made Interfaces ---")

candidates = [[1, 2, 3], "a string", {"a": 1}, 42, (x for x in range(3))]

for value in candidates:
    is_iterable = isinstance(value, collections.abc.Iterable)
    print(f"  {value!r:30} isinstance(..., Iterable) -> {is_iterable}")

print("\n42 is NOT Iterable - trying to loop over it fails immediately,")
print("just like an unimplemented @abstractmethod fails at the right time:")
try:
    iter(42)
except TypeError as e:
    print("Error:", e)

print("\nisinstance(my_dict, collections.abc.Mapping):",
      isinstance({"a": 1}, collections.abc.Mapping))
print("This is how many libraries validate 'give me anything dict-like'")
print("without requiring the caller's exact type to literally be `dict`.")


"""
---------------------------------------------------------------------
7. VIRTUAL SUBCLASSING: register() AS A LIGHTER ALTERNATIVE  ⭐⭐
---------------------------------------------------------------------
Sometimes you want a class to be RECOGNIZED as implementing an ABC's
interface (so `isinstance()` returns True) WITHOUT actually inheriting
from it - e.g. a third-party class you don't control, or two
unrelated class hierarchies that both happen to satisfy the same
shape. `ABC.register()` creates this "virtual subclass" relationship:
`isinstance()`/`issubclass()` say yes, but Python does NOT enforce
that the abstract methods are implemented (no instantiation-time
check like real inheritance gets) and MRO/`super()` don't apply.
---------------------------------------------------------------------
"""

print("\n--- Virtual Subclassing via register() ---")

class ReadableSource(ABC):
    @abstractmethod
    def read(self):
        """Anything registered here claims to support .read()."""


class LegacyFileReader:
    # Does NOT inherit from ReadableSource at all - maybe this class
    # lives in another team's package and can't be touched.
    def read(self):
        return "legacy data"


ReadableSource.register(LegacyFileReader)

legacy = LegacyFileReader()
print("isinstance(legacy, ReadableSource):", isinstance(legacy, ReadableSource))
print("issubclass(LegacyFileReader, ReadableSource):",
      issubclass(LegacyFileReader, ReadableSource))
print("\nNote: real inheritance gets an ENFORCED contract (TypeError on")
print("missing methods at instantiation); register() only gets you the")
print("isinstance()/issubclass() check - it trusts you that the shape")
print("actually matches, with no verification at all.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Why ABCs over plain duck typing:
    duck typing  -> missing method fails LATE, at first CALL time
    ABC           -> missing method fails EARLY, at INSTANTIATION time
                     (formal contract + self-documenting interface)

Basic usage:
    class Base(ABC):              -> inherit from abc.ABC
        @abstractmethod
        def method(self): ...     -> subclasses MUST override

Instantiating Base() directly           -> TypeError
Instantiating a subclass missing        -> TypeError (same mechanism)
    an abstract method

Abstract method WITH a body:
    @abstractmethod def m(self): <real code>  -> still enforced;
    subclass calls super().m(...) to reuse the shared logic

Abstract property:
    @property
    @abstractmethod                -> @property must be OUTERMOST
    def prop(self): ...

DataConnector pattern:
    abstract connect()/read()/close()  -> concrete CSVConnector,
    APIConnector, etc. all plug into the SAME calling code (run())

collections.abc:
    isinstance(x, collections.abc.Iterable)  -> protocol check
    isinstance(x, collections.abc.Mapping)     -> dict-like check

Virtual subclassing:
    SomeABC.register(OtherClass)   -> isinstance()/issubclass() say
                                       True, but NOTHING is enforced
                                       (no inheritance, no MRO, no
                                       instantiation-time check)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - ABSTRACT BASE CLASSES (abc MODULE)
=====================================================================

1. Python already supports duck typing - why would you ever need a
   formal `abc.ABC` / `@abstractmethod` mechanism on top of that?

2. At what exact moment does Python raise `TypeError` for an
   incomplete ABC subclass - when the class is DEFINED, or when it is
   INSTANTIATED? Why does that timing matter compared to a plain
   duck-typed class that only fails when the missing method is
   finally called?

3. In this file, `BrokenSquare` doesn't implement `area()`. What
   specific error is raised, and at what line does it occur?

4. Can `@abstractmethod` methods contain a real, executable body, or
   must they always be empty (`pass` / docstring-only)? Demonstrate
   how a subclass would reuse that body via `super()`.

5. Why does the `Exporter` example still raise `TypeError` for
   `BrokenExporter`, even though `Exporter.export()` has a full,
   working implementation?

6. How do you declare an ABSTRACT PROPERTY (not just an abstract
   method)? What is the correct decorator order, and why does the
   order matter?

7. Walk through the `DataConnector` design in this file: why is
   defining `connect()`, `read()`, and `close()` as abstract methods
   better, from an interview/design perspective, than just trusting
   every subclass to implement them by convention?

8. What does the `run()` method on `DataConnector` demonstrate about
   mixing CONCRETE and ABSTRACT methods on the same base class?

9. If you added a third connector, e.g. `S3Connector`, what is the
   minimum you would need to implement for it to be usable
   interchangeably with `CSVConnector` and `APIConnector`?

10. What is `collections.abc.Iterable`, and how does
    `isinstance(x, collections.abc.Iterable)` differ from just
    checking `isinstance(x, list)`?

11. What is "virtual subclassing" via `ABC.register()`? How does it
    differ from actual inheritance in terms of what Python enforces
    at instantiation time?

12. If `LegacyFileReader` is registered with `ReadableSource` via
    `register()` but never actually implements `.read()` correctly,
    will `BrokenConnector()`-style instantiation-time errors catch
    that mistake? Why or why not?

13. Can you instantiate `abc.ABC` itself, or a class that inherits
    from it but implements ALL of its abstract methods? Contrast the
    two outcomes.

14. Under the hood, what makes `abc.ABC` actually enforce the
    "cannot instantiate with missing abstract methods" rule? (Hint:
    metaclasses - `ABCMeta`.)

15. When designing a pluggable ETL system with many interchangeable
    connectors, what are the trade-offs of using a real `abc.ABC`
    base class versus just relying on duck typing and documentation?
=====================================================================
"""
