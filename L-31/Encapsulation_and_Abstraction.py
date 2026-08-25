"""
=====================================================================
PYTHON ENCAPSULATION AND ABSTRACTION - Complete Notes with Executable
Examples
=====================================================================

ENCAPSULATION is about BUNDLING data and the methods that operate on
that data together inside a class, and CONTROLLING how the outside
world is allowed to read or modify that data. In most languages
(Java, C++) this is enforced by the compiler with `private`/`protected`
keywords. Python takes a completely different philosophy, often
summarized as "we're all consenting adults here": there is NO
compiler-enforced privacy at all. Instead, Python uses NAMING
CONVENTIONS to signal intent, plus the `@property` decorator to give
you real programmatic control (validation, computed values, logging)
over attribute access WITHOUT the caller's syntax ever changing.

ABSTRACTION is a related but distinct idea: hiding IMPLEMENTATION
COMPLEXITY behind a SIMPLE interface. A well-abstracted class lets a
caller say "load the data" or "process the order" without needing to
know (or care) whether that involves parsing a CSV, querying a
database, calling three helper methods, or retrying a flaky network
call internally. Encapsulation is the MECHANISM (controlling access
to internals); abstraction is the GOAL (presenting a simple mental
model on top of that hidden complexity). This file covers both,
because in practice you rarely design one without the other.

Note: Python also has a formal tool for ENFORCING abstraction at the
class-design level - Abstract Base Classes, via the `abc` module.
That gets its own dedicated deep-dive in a later file; here we only
give it a brief teaser at the end, since the general PRINCIPLE of
abstraction (simple interface, hidden complexity) is the interview-
relevant idea for this topic.
=====================================================================
"""

print("--- Overview ---")
print("Encapsulation = bundling data + behavior, and controlling access to it.")
print("Abstraction = hiding HOW something works behind a simple interface.")


"""
---------------------------------------------------------------------
1. WHY PYTHON HAS NO TRUE PRIVATE MEMBERS: THE THREE ACCESS LEVELS  ⭐⭐⭐
---------------------------------------------------------------------
This is one of the most commonly asked OOP questions in Python
interviews: "Does Python have private variables?" The honest answer
is NO - Python has no access modifier that the interpreter actually
enforces. Instead, there are three NAMING CONVENTIONS that communicate
intent to other developers (and to tools like linters/IDEs), each
with different runtime behavior:

    name     -> PUBLIC: freely accessible, part of the intended API.
    _name    -> "PROTECTED" by convention: signals "internal use only,
                don't touch this from outside the class/subclasses",
                but Python does NOTHING to stop you accessing it.
    __name   -> "PRIVATE"-ish: triggers NAME MANGLING (see section 3),
                which makes accidental access harder but is still not
                true security - it's a collision-avoidance mechanism.
---------------------------------------------------------------------
"""

print("\n--- The Three Access Levels ---")

class Employee:
    def __init__(self, name, salary, ssn):
        self.name = name          # public - part of the normal API
        self._salary = salary     # "protected" - internal, but reachable
        self.__ssn = ssn          # "private" - name-mangled (see section 3)

emp = Employee("Dana", 95000, "123-45-6789")
print("public access - emp.name:", emp.name)
print("'protected' access - emp._salary (still works!):", emp._salary)
print("Nothing in the language stops either access above.")
print("The underscore is a SIGNAL to other engineers, not a lock.")


"""
---------------------------------------------------------------------
2. THE SINGLE UNDERSCORE: "PROTECTED" BY CONVENTION  ⭐⭐
---------------------------------------------------------------------
A single leading underscore (`_name`) is PURE CONVENTION - it changes
NO runtime behavior at all (unlike double underscore). It communicates
"this is an internal implementation detail; depend on it at your own
risk, it may change without notice." It's also respected by tooling:
`from module import *` will NOT import single-underscore names by
default. This is the level you'll use constantly in real code - for
internal helper attributes and methods that support the public API
but aren't meant to be called directly by users of the class.
---------------------------------------------------------------------
"""

print("\n--- Single Underscore: Protected by Convention ---")

class RetryableClient:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries      # public: safe to set/read
        self._attempt_count = 0             # "protected": internal bookkeeping

    def call(self):
        self._attempt_count += 1            # internal helper state
        return f"attempt #{self._attempt_count} (max {self.max_retries})"

    def _log_attempt(self):                 # a "protected" helper METHOD too
        print(f"  [internal] attempt count is now {self._attempt_count}")

client = RetryableClient()
print(client.call())
print(client.call())
client._log_attempt()      # works, but the underscore says "don't do this"
print("\nA linter/reviewer would flag calling client._log_attempt() from")
print("outside the class - it's a signal, not an enforced restriction.")


"""
---------------------------------------------------------------------
3. THE DOUBLE UNDERSCORE: NAME MANGLING  ⭐⭐⭐
---------------------------------------------------------------------
A leading DOUBLE underscore (`__name`, with at most one trailing
underscore) triggers real interpreter behavior called NAME MANGLING:
Python internally rewrites `__name` to `_ClassName__name` wherever it
appears inside the class body. This is NOT primarily about security -
it exists to prevent ACCIDENTAL ATTRIBUTE CLASHES in subclasses, so
that a base class's internal attribute can't be silently overwritten
by a subclass that happens to pick the same attribute name.
---------------------------------------------------------------------
"""

print("\n--- Double Underscore: Name Mangling ---")

class Account:
    def __init__(self, balance):
        self.__balance = balance     # actually stored as _Account__balance

    def get_balance(self):
        return self.__balance        # Python rewrites this automatically too

acct = Account(500)
print("acct.get_balance():", acct.get_balance())

# BUGGY: naive attempt to access the "private" attribute by its plain name
try:
    print(acct.__balance)
except AttributeError as e:
    print("Error accessing acct.__balance directly:", e)

# FIXED: the mangled name DOES exist and can be accessed - proving this
# is obfuscation, not real privacy
print("acct._Account__balance (the real, mangled attribute name):",
      acct._Account__balance)
print("vars(acct):", vars(acct))

print("\nWHY name mangling exists - avoiding subclass clashes, not security:")

class BasePipeline:
    def __init__(self):
        self.__state = "base-initialized"     # becomes _BasePipeline__state

    def base_state(self):
        return self.__state

class ChildPipeline(BasePipeline):
    def __init__(self):
        super().__init__()
        self.__state = "child-initialized"    # becomes _ChildPipeline__state -
                                                # a COMPLETELY DIFFERENT attribute!

    def child_state(self):
        return self.__state

child = ChildPipeline()
print("child.base_state():", child.base_state())     # unaffected by the child!
print("child.child_state():", child.child_state())
print("Both '__state' attributes coexist safely:",
      {k: v for k, v in vars(child).items() if "state" in k})
print("\nWithout mangling, ChildPipeline.__init__ would have silently")
print("clobbered BasePipeline's internal '__state' attribute - mangling")
print("prevents exactly that class of bug in inheritance hierarchies.")


"""
---------------------------------------------------------------------
4. @property: A CLEAN GETTER THAT LOOKS LIKE AN ATTRIBUTE  ⭐⭐⭐
---------------------------------------------------------------------
`@property` lets a method be ACCESSED using plain attribute syntax
(no parentheses), while still running real code underneath. This is
THE standard Python answer to "how do you do encapsulation without
Java-style getters/setters everywhere" - you start with a plain public
attribute, and only convert it to a property LATER if you need
validation or computed logic, without breaking any existing caller
code (since `obj.value` still looks exactly the same either way).
---------------------------------------------------------------------
"""

print("\n--- @property: A Read-Only Computed Attribute ---")

class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def area(self):                 # computed on every access, not stored
        return self.width * self.height

rect = Rectangle(4, 5)
print("rect.area (no parentheses - looks like a plain attribute):", rect.area)
rect.width = 10
print("after changing width, rect.area recomputes automatically:", rect.area)

try:
    rect.area = 999                 # no setter defined yet -> fails
except AttributeError as e:
    print("Error trying to assign to a getter-only property:", e)


"""
---------------------------------------------------------------------
5. @x.setter: VALIDATING WRITES (THE CLASSIC ENCAPSULATION ANSWER)  ⭐⭐⭐
---------------------------------------------------------------------
This is the single most common "how do you implement encapsulation in
Python" interview answer: define a private-by-convention backing
attribute (`_value`), expose it through a `@property` getter, and add
a matching `@value.setter` that VALIDATES any new value before storing
it. Callers still write `obj.value = x` - completely normal attribute
syntax - but that assignment now runs your validation logic. This
gives you the safety of a "setter method" with none of the Java-style
boilerplate.
---------------------------------------------------------------------
"""

print("\n--- @x.setter: Validating Writes ---")

class Temperature:
    """Stores a temperature in Celsius; rejects values below absolute zero."""

    def __init__(self, celsius):
        self.celsius = celsius     # goes through the setter below, even here!

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:                     # absolute zero, physically impossible
            raise ValueError(f"{value}°C is below absolute zero (-273.15°C)")
        self._celsius = value

    @property
    def fahrenheit(self):                        # a second, read-only computed property
        return self._celsius * 9 / 5 + 32

temp = Temperature(25)
print("temp.celsius:", temp.celsius)
print("temp.fahrenheit (computed from celsius):", temp.fahrenheit)

temp.celsius = 100          # goes through validation transparently
print("after temp.celsius = 100:", temp.celsius, "->", temp.fahrenheit, "F")

# BUGGY: what a naive class WITHOUT a property/setter allows
class NaiveTemperature:
    def __init__(self, celsius):
        self.celsius = celsius     # plain public attribute - no validation at all

naive = NaiveTemperature(25)
naive.celsius = -500           # physically impossible, but nothing stops it!
print("\nnaive.celsius (no validation, accepted an impossible value):",
      naive.celsius)

# FIXED: the property-based Temperature class rejects the same bad value
try:
    temp.celsius = -500
except ValueError as e:
    print("Temperature correctly rejected an invalid value:", e)


"""
---------------------------------------------------------------------
6. @x.deleter: CONTROLLING ATTRIBUTE DELETION  ⭐
---------------------------------------------------------------------
Less commonly used than getter/setter, but a complete property has
three parts: `@property` (get), `@x.setter` (set), and `@x.deleter`
(runs on `del obj.x`). Useful for cleanup logic or for blocking
deletion of an attribute that must always exist.
---------------------------------------------------------------------
"""

print("\n--- @x.deleter: Controlling Deletion ---")

class Session:
    def __init__(self, token):
        self._token = token

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value

    @token.deleter
    def token(self):
        print("  revoking token before deletion...")
        self._token = None

session = Session("abc123")
print("session.token:", session.token)
del session.token                  # runs the deleter logic above
print("session.token after del:", session.token)


"""
---------------------------------------------------------------------
7. DATA ENGINEERING ENCAPSULATION: A VALIDATING PipelineConfig  ⭐⭐⭐
---------------------------------------------------------------------
A very realistic use of properties in a data engineering codebase:
a pipeline configuration object that validates its settings the
moment they're set (batch size must be positive, retry count can't be
negative, etc.), so bad config fails FAST and LOUD at assignment time
instead of causing a confusing failure deep inside a running job hours
later.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Validating PipelineConfig ---")

class PipelineConfig:
    def __init__(self, batch_size, max_retries, source_path):
        self.batch_size = batch_size          # each goes through validation below
        self.max_retries = max_retries
        self.source_path = source_path

    @property
    def batch_size(self):
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"batch_size must be a positive int, got {value!r}")
        self._batch_size = value

    @property
    def max_retries(self):
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value):
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"max_retries must be a non-negative int, got {value!r}")
        self._max_retries = value

    @property
    def source_path(self):
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        if not value or not isinstance(value, str):
            raise ValueError(f"source_path must be a non-empty string, got {value!r}")
        self._source_path = value

    def __repr__(self):
        return (f"PipelineConfig(batch_size={self.batch_size}, "
                f"max_retries={self.max_retries}, source_path={self.source_path!r})")

config = PipelineConfig(batch_size=500, max_retries=3, source_path="s3://bucket/raw/")
print("valid config:", config)

# BUGGY: a bad config value discovered LATE, deep inside job logic, if it
# were just a plain attribute with no validation
print("\nattempting several invalid updates - each is caught IMMEDIATELY:")
for bad_kwarg, bad_value in [
    ("batch_size", -10),
    ("max_retries", -1),
    ("source_path", ""),
]:
    try:
        setattr(config, bad_kwarg, bad_value)
    except ValueError as e:
        print(f"  rejected {bad_kwarg}={bad_value!r}: {e}")

print("config is still valid after rejected updates:", config)


"""
---------------------------------------------------------------------
8. ABSTRACTION: HIDING COMPLEXITY BEHIND ONE CLEAN METHOD  ⭐⭐⭐
---------------------------------------------------------------------
Abstraction means the CALLER only needs to know about a simple,
stable interface - not the messy details behind it. A textbook data
engineering example: a `DataLoader` that can pull records from a CSV
file, a JSON file, or a database, but exposes exactly ONE public
method - `.load()` - to every caller. All the format-specific logic
lives in "protected" helper methods the caller never touches directly.
Swapping the source format later means changing internals only; every
caller's code (`loader.load()`) never has to change.
---------------------------------------------------------------------
"""

print("\n--- Abstraction: DataLoader Hides Source-Format Complexity ---")

import csv
import io
import json
import sqlite3


class DataLoader:
    """Loads records from CSV, JSON, or a SQL database behind one .load() call."""

    def __init__(self, source_type, source):
        self._source_type = source_type    # "protected": implementation detail
        self._source = source

    def load(self):
        """The ONE method every caller needs to know about."""
        if self._source_type == "csv":
            return self._load_csv()
        elif self._source_type == "json":
            return self._load_json()
        elif self._source_type == "db":
            return self._load_db()
        else:
            raise ValueError(f"unsupported source_type: {self._source_type!r}")

    # --- everything below is hidden implementation detail ---

    def _load_csv(self):
        reader = csv.DictReader(io.StringIO(self._source))
        return list(reader)

    def _load_json(self):
        return json.loads(self._source)

    def _load_db(self):
        # self._source is expected to be a (connection, query) tuple
        connection, query = self._source
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


csv_text = "id,name\n1,Widget\n2,Gadget\n"
json_text = json.dumps([{"id": 3, "name": "Gizmo"}])

conn = sqlite3.connect(":memory:")     # stand-in for a real DB (e.g. postgres via psycopg2)
conn.execute("CREATE TABLE products (id INTEGER, name TEXT)")
conn.execute("INSERT INTO products VALUES (4, 'Doohickey')")
conn.commit()

csv_loader = DataLoader("csv", csv_text)
json_loader = DataLoader("json", json_text)
db_loader = DataLoader("db", (conn, "SELECT id, name FROM products"))

# The caller calls the EXACT SAME method regardless of what's underneath -
# this IS abstraction: one interface, three totally different implementations.
for name, loader in [("CSV", csv_loader), ("JSON", json_loader), ("DB", db_loader)]:
    print(f"{name} loader.load() ->", loader.load())

conn.close()
print("\nEvery caller above only ever called .load() - none of them needed")
print("to know whether that meant parsing text or running SQL underneath.")


"""
---------------------------------------------------------------------
9. A TEASER OF FORMAL ABSTRACTION: THE abc MODULE  ⭐
---------------------------------------------------------------------
Everything in section 8 is abstraction as a DESIGN PRINCIPLE - nothing
stopped someone from writing a fourth DataLoader-like class that
forgets to implement `.load()` correctly. Python also has a way to
ENFORCE that every subclass in a family implements a required
interface: Abstract Base Classes, via the `abc` module and
`@abstractmethod`. A class inheriting from an ABC that leaves an
abstract method unimplemented cannot even be INSTANTIATED - Python
raises a `TypeError` immediately, catching the mistake at class-
definition time instead of at some later call site. That mechanism -
`ABC`, `@abstractmethod`, virtual subclasses, and `__subclasshook__` -
is covered in full depth in its own dedicated file; here's just enough
to recognize the shape of it:
---------------------------------------------------------------------
"""

print("\n--- Teaser: Formal Abstraction via the abc Module ---")

from abc import ABC, abstractmethod

class BaseLoader(ABC):
    @abstractmethod
    def load(self):
        """Every real loader MUST implement this - enforced at instantiation."""
        raise NotImplementedError

try:
    BaseLoader()                # cannot instantiate - .load() is unimplemented
except TypeError as e:
    print("Error instantiating an incomplete abstract class:", e)

class CsvOnlyLoader(BaseLoader):
    def load(self):
        return ["implemented!"]

print("a COMPLETE subclass instantiates fine:", CsvOnlyLoader().load())
print("\n(Full abc-module mechanics - ABCMeta, register(), abstractproperty,")
print("etc. - are covered in a dedicated later file on Abstract Base Classes.)")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Access level      Syntax     Runtime effect               Meaning
public             name       none                          part of the API
"protected"        _name      none (pure convention)        internal, don't touch
"private"          __name     NAME MANGLING -> _Class__name  avoid subclass clashes

Name mangling reason -> prevent accidental attribute clashes in
                         subclasses, NOT security/hiding secrets.

@property           -> turns a method into a read-like attribute (getter)
@x.setter            -> validates/transforms on `obj.x = value`
@x.deleter            -> runs custom logic on `del obj.x`

Encapsulation -> controlling access to internal STATE (properties,
                 underscore conventions).
Abstraction   -> hiding internal COMPLEXITY behind a simple, stable
                 interface (e.g. DataLoader.load()).
Formal abstraction -> `abc.ABC` + `@abstractmethod` enforces that
                       subclasses implement required methods (full
                       depth in a later file).
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - ENCAPSULATION AND ABSTRACTION
=====================================================================

1. Does Python have "true" private variables like Java or C++? If
   not, what does it have instead?

2. Explain the practical difference between `_name` and `__name` -
   which one actually changes runtime behavior, and which one is
   pure convention?

3. What is "name mangling"? Given a class `Account` with
   `self.__balance`, what is the ACTUAL attribute name stored on an
   instance, and how would you access it directly from outside the
   class?

4. Why does Python implement name mangling at all - what problem
   does it solve? (Hint: think about inheritance, not security.)

5. Walk through the `BasePipeline`/`ChildPipeline` example: why don't
   `self.__state` in the base class and `self.__state` in the
   subclass overwrite each other?

6. What does the `@property` decorator do, and why would you use it
   instead of a plain public attribute?

7. In the `Temperature` class, why does `self.celsius = celsius`
   inside `__init__` still trigger the setter's validation logic?

8. Walk through what `@celsius.setter` does and why the setter method
   must be named identically to the property (`celsius`, not
   `set_celsius`).

9. What happens if you try to assign to a property that only has a
   getter defined (no `@x.setter`)? What exception is raised?

10. Design a `PipelineConfig` class (or similar) where `batch_size`
    must always be a positive integer. How would you guarantee that
    invariant holds no matter how a caller tries to set it?

11. What is the difference between encapsulation and abstraction, in
    your own words? How do they relate to each other?

12. Referencing the `DataLoader` example: how can a class expose a
    single `.load()` method while completely changing its internal
    behavior depending on whether the source is CSV, JSON, or a
    database - and why is that useful for callers?

13. What happens if you instantiate a class inheriting from `abc.ABC`
    that has not implemented all of its `@abstractmethod` methods?
    At what point does Python catch this - class definition,
    instantiation, or call time?

14. Why might you START a class with a plain public attribute and
    only convert it to a `@property` LATER, rather than always
    writing properties upfront for every attribute?

15. Give a real-world data engineering example where hiding
    implementation complexity behind one simple method (abstraction)
    made a pipeline easier to maintain or extend later.
=====================================================================
"""
