"""
=====================================================================
@STATICMETHOD vs @CLASSMETHOD vs INSTANCE METHODS - Complete Notes
with Executable Examples
=====================================================================

Every function defined inside a class body is one of THREE kinds of
method, and Python interviewers love this question because it tests
whether you actually understand how `self` and `cls` get bound, not
just whether you can recite the decorator names.

INSTANCE METHOD (the default, no decorator):
    Receives the specific INSTANCE as its first argument (`self`).
    It can read/write that instance's attributes AND, through
    `self.__class__` or `type(self)`, reach the class itself.
    Use this for anything that needs to know WHICH object it's
    operating on.

@classmethod:
    Receives the CLASS itself as its first argument (`cls`), never a
    specific instance. It operates on class-level state, or - its
    single most common real-world use - builds and RETURNS a new
    instance of that class. This is how you write ALTERNATE
    CONSTRUCTORS: `MyClass.from_json(...)`, `MyClass.from_csv_row(...)`.

@staticmethod:
    Receives NEITHER `self` NOR `cls`. It is a completely ordinary
    function that just happens to live inside the class's namespace
    because it's conceptually related to it - typically a pure
    utility/validation helper that needs no instance or class data
    at all. You could move it outside the class and it would work
    identically; it's there purely for organization and discoverability.

The interview-killer detail: `@classmethod` + `cls(...)` is what makes
ALTERNATE CONSTRUCTORS work correctly with INHERITANCE - a subclass
that inherits the classmethod unchanged will build an instance of
ITSELF, not of the hardcoded base class. This file demonstrates all of
that with runnable code.
=====================================================================
"""

print("--- Overview ---")
print("Instance method  -> gets `self`  -> operates on ONE object")
print("Classmethod      -> gets `cls`   -> operates on the CLASS itself")
print("Staticmethod     -> gets neither -> just a plain function, namespaced")


"""
---------------------------------------------------------------------
1. INSTANCE METHODS: THE DEFAULT CASE  ⭐⭐
---------------------------------------------------------------------
An instance method's first parameter is conventionally named `self`
and is bound AUTOMATICALLY by Python to whichever object the method
was called on (`obj.method()` is sugar for `Class.method(obj)`).
Through `self`, it can freely read/write THAT instance's attributes.
It can also reach CLASS-level state via `self.__class__` (or the
`type(self)` builtin) - so instance methods are actually the most
"powerful" of the three: they can touch instance state, class state,
or both.

The full `DataRecord` class defined here is reused for the rest of
this file - later sections just exercise its other methods.
---------------------------------------------------------------------
"""

print("\n--- Instance Methods: The Default Case ---")

import json

class DataRecord:
    # a CLASS-level attribute, shared by every instance unless shadowed
    total_records_created = 0

    def __init__(self, name, value, source="manual"):
        self.name = name              # INSTANCE state - unique per object
        self.value = value             # INSTANCE state
        self.source = source            # INSTANCE state - where it came from
        self.touch_count = 0             # INSTANCE state
        DataRecord.total_records_created += 1   # mutating CLASS state directly

    def touch(self):
        """Instance method: reads AND writes this specific instance's state."""
        self.touch_count += 1          # modifies INSTANCE state
        return self.touch_count

    def describe(self):
        """Instance method reaching CLASS state through self.__class__."""
        # self.__class__ (or type(self)) is how an instance method can see
        # class-level data - this is the bridge between the two worlds
        return (f"{self.name}={self.value} (touched {self.touch_count}x, "
                f"1 of {self.__class__.total_records_created} records total)")

    def to_dict(self):
        """Instance method: serializes THIS instance's own state."""
        return {"name": self.name, "value": self.value, "source": self.source}

    @classmethod
    def record_count(cls):
        """Classmethod: reports on CLASS-level state - no instance involved."""
        return f"{cls.__name__} has created {cls.total_records_created} record(s) so far"

    @classmethod
    def from_json(cls, json_string):
        """Alternate constructor: parse a JSON string, then build an instance."""
        data = json.loads(json_string)
        # cls(...) - NOT DataRecord(...) - see section 6 for why this matters
        return cls(name=data["name"], value=data["value"], source="json")

    @classmethod
    def from_csv_row(cls, row):
        """Alternate constructor: parse a raw CSV row (list of strings)."""
        name, raw_value = row
        return cls(name=name, value=float(raw_value), source="csv")

    @staticmethod
    def is_valid_name(name):
        """Pure validation logic - needs NO instance or class data at all."""
        return isinstance(name, str) and len(name) > 0 and name.replace("_", "").isalnum()

    @staticmethod
    def sanitize_value(raw_value):
        """Pure utility - converts a raw string/number into a clean float."""
        try:
            return float(str(raw_value).strip().replace(",", ""))
        except ValueError:
            return None

record_1 = DataRecord("cpu_temp", 71.2)
record_2 = DataRecord("disk_free_gb", 512)

record_1.touch()
record_1.touch()
print(record_1.describe())
print(record_2.describe())
print("\nEach instance has its OWN 'touch_count', but both see the SAME")
print("shared 'total_records_created' class attribute via self.__class__.")


"""
---------------------------------------------------------------------
2. @CLASSMETHOD: OPERATES ON THE CLASS, NOT A SPECIFIC INSTANCE  ⭐⭐⭐
---------------------------------------------------------------------
A classmethod's first parameter is conventionally named `cls` and is
bound to the CLASS (not any particular object), via the
`@classmethod` decorator. It CANNOT see any one instance's data
(there may not even BE an instance yet) - it only sees class-level
attributes, and can create new instances via `cls(...)`.
---------------------------------------------------------------------
"""

print("\n--- @classmethod: Operating on the Class Itself ---")

print(DataRecord.record_count())      # called directly on the class - no instance needed
record_3 = DataRecord("mem_used_pct", 63)
print(DataRecord.record_count())      # reflects the new total automatically


"""
---------------------------------------------------------------------
3. THE #1 REAL-WORLD USE OF @classmethod: ALTERNATE CONSTRUCTORS  ⭐⭐⭐
---------------------------------------------------------------------
`__init__` can only do ONE thing: take arguments and assign them
directly to attributes. But real data often arrives as a JSON string,
a CSV row, a database row, etc. - it needs PARSING before you have
the right arguments for `__init__`. A classmethod alternate
constructor does that parsing and then calls `cls(...)` to build and
RETURN the finished instance. This is, by far, the most common
practical use of @classmethod, and a near-guaranteed interview
follow-up after "what's the difference?".
---------------------------------------------------------------------
"""

print("\n--- Alternate Constructors via @classmethod ---")

json_record = DataRecord.from_json('{"name": "latency_ms", "value": 42.5}')
csv_record = DataRecord.from_csv_row(["queue_depth", "17"])

print("built from JSON:", json_record.to_dict())
print("built from CSV row:", csv_record.to_dict())
print("\nBoth still went through the SAME __init__ underneath - the")
print("classmethod's only job was translating a raw format into the")
print("right constructor arguments before calling cls(...).")


"""
---------------------------------------------------------------------
4. @staticmethod: A PLAIN FUNCTION, JUST NAMESPACED INSIDE THE CLASS  ⭐⭐⭐
---------------------------------------------------------------------
A staticmethod gets NO automatic first argument at all - not `self`,
not `cls`. It behaves exactly like a free function defined at module
level; the ONLY reason to put it inside the class is that it's
conceptually related (a pure validation/utility helper that the class
"owns") and you want callers to find it as `DataRecord.is_valid_name`
instead of a loose top-level function. It cannot read instance OR
class state unless you pass that data in explicitly as an argument.
---------------------------------------------------------------------
"""

print("\n--- @staticmethod: A Namespaced Utility Function ---")

print("is_valid_name('cpu_temp'):", DataRecord.is_valid_name("cpu_temp"))
print("is_valid_name(''):", DataRecord.is_valid_name(""))
print("is_valid_name('bad name!'):", DataRecord.is_valid_name("bad name!"))
print("sanitize_value('1,024.5'):", DataRecord.sanitize_value("1,024.5"))
print("sanitize_value('garbage'):", DataRecord.sanitize_value("garbage"))
print("\nNote: this is functionally IDENTICAL to a free function outside")
print("the class - it's grouped here purely for organization, so callers")
print("naturally find validation logic next to the class it validates for.")


"""
---------------------------------------------------------------------
5. SIDE BY SIDE: CALLING EACH KIND ON THE CLASS vs ON AN INSTANCE  ⭐⭐⭐
---------------------------------------------------------------------
This is where the three kinds visibly diverge. An instance method
NEEDS a bound instance to supply `self` - call it on the bare class
and Python has nothing to fill that slot with, so it raises
TypeError. A classmethod and a staticmethod, by contrast, work
identically whether you call them on the class OR on an instance,
because neither one depends on a specific object's state.
---------------------------------------------------------------------
"""

print("\n--- Side by Side: Calling on the CLASS vs an INSTANCE ---")

sample = DataRecord("sample_metric", 100)

# INSTANCE METHOD called on an INSTANCE - works, `self` is supplied automatically
print("instance method on an INSTANCE:", sample.describe())

# BUGGY: INSTANCE METHOD called on the bare CLASS - nothing to bind to `self`
try:
    DataRecord.describe()
except TypeError as e:
    print("instance method on the CLASS (broken):", e)

# FIXED: you CAN call it on the class if you pass the instance manually -
# this is literally what `sample.describe()` does under the hood
print("instance method on the CLASS (manual self):", DataRecord.describe(sample))

# CLASSMETHOD called on the CLASS - the normal, intended usage
print("\nclassmethod on the CLASS:", DataRecord.record_count())
# CLASSMETHOD called on an INSTANCE - ALSO works fine: Python still resolves
# `cls` to the instance's CLASS, not the instance itself
print("classmethod on an INSTANCE:", sample.record_count())

# STATICMETHOD called on the CLASS - normal usage
print("\nstaticmethod on the CLASS:", DataRecord.is_valid_name("disk_io"))
# STATICMETHOD called on an INSTANCE - ALSO works, since it needs no `self`/`cls`
print("staticmethod on an INSTANCE:", sample.is_valid_name("disk_io"))

print("\nSummary: instance methods REQUIRE an instance to supply `self`.")
print("classmethods and staticmethods don't care which one you call them")
print("on - both routes reach the exact same underlying function.")


"""
---------------------------------------------------------------------
6. THE INHERITANCE GOTCHA: cls(...) RETURNS THE SUBCLASS  ⭐⭐⭐
---------------------------------------------------------------------
This is a favorite "gotcha" follow-up. Inside a classmethod, `cls` is
bound to WHICHEVER class the method was actually called through - the
base class, or a subclass that inherited it unchanged. If the
classmethod builds the new object with `cls(...)`, an alternate
constructor called via a SUBCLASS correctly returns an instance of
that SUBCLASS. If you instead hardcode the base class name (the
buggy version below), you silently get the WRONG type back whenever
a subclass uses the inherited constructor.
---------------------------------------------------------------------
"""

print("\n--- The Inheritance Gotcha: cls(...) vs Hardcoding the Class ---")

class BuggyDataRecord:
    def __init__(self, name, value, source="manual"):
        self.name = name
        self.value = value
        self.source = source

    @classmethod
    def from_json_buggy(cls, json_string):
        data = json.loads(json_string)
        # BUG: hardcodes the base class instead of using `cls` -
        # this throws away the whole point of a classmethod constructor
        return BuggyDataRecord(name=data["name"], value=data["value"], source="json")

class BuggyTimestampedRecord(BuggyDataRecord):
    """A subclass that adds a timestamp - but changes nothing about construction."""
    def __init__(self, name, value, source="manual"):
        super().__init__(name, value, source)
        self.created_at = "2026-08-25T00:00:00Z"   # fixed for reproducible output

buggy_result = BuggyTimestampedRecord.from_json_buggy('{"name": "req_count", "value": 9001}')
print("buggy: called via subclass, but got back type:", type(buggy_result).__name__)
print("  -> WRONG: lost .created_at because it's a plain BuggyDataRecord, not")
print("     a BuggyTimestampedRecord, even though we called it via the subclass!")

# Now the FIXED version, using cls(...) as in section 3's DataRecord.from_json
class TimestampedRecord(DataRecord):
    """Subclass of the properly-written DataRecord from section 1."""
    def __init__(self, name, value, source="manual"):
        super().__init__(name, value, source)
        self.created_at = "2026-08-25T00:00:00Z"

fixed_result = TimestampedRecord.from_json('{"name": "req_count", "value": 9001}')
print("\nfixed: called via subclass, got back type:", type(fixed_result).__name__)
print("  -> CORRECT: DataRecord.from_json used `cls(...)`, so calling it")
print("     through TimestampedRecord built a TimestampedRecord.")
print("  created_at attribute present:", fixed_result.created_at)


"""
---------------------------------------------------------------------
7. DATA ENGINEERING USE CASE: A PIPELINE STEP CLASS USING ALL THREE  ⭐⭐⭐
---------------------------------------------------------------------
A realistic ETL pipeline "step" class typically needs all three kinds
at once: an INSTANCE METHOD to actually run the transform using its
own configured state, a CLASSMETHOD alternate constructor to build
the step from a config dict (as loaded from YAML/JSON pipeline
configs), and a STATICMETHOD for a pure, reusable validation rule
that doesn't need any step-specific state.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: A Pipeline Step Class ---")

class PipelineStep:
    registered_steps = 0

    def __init__(self, step_name, min_value, max_value):
        self.step_name = step_name
        self.min_value = min_value
        self.max_value = max_value
        PipelineStep.registered_steps += 1

    def run(self, records):
        """Instance method: uses THIS step's own min/max bounds to filter data."""
        return [r for r in records if self.is_in_range(r["value"], self.min_value, self.max_value)]

    @classmethod
    def from_config(cls, config):
        """Alternate constructor: builds a step from a pipeline config dict,
        exactly the way a real orchestrator (Airflow, Dagster, a config file
        loader) would hand you step definitions at DAG-build time."""
        return cls(
            step_name=config["name"],
            min_value=config["bounds"]["min"],
            max_value=config["bounds"]["max"],
        )

    @staticmethod
    def is_in_range(value, min_value, max_value):
        """Pure utility rule - doesn't need `self` or `cls`, just the numbers."""
        return min_value <= value <= max_value

step_config = {"name": "filter_valid_latency", "bounds": {"min": 0, "max": 500}}
latency_filter = PipelineStep.from_config(step_config)   # classmethod: alt constructor

incoming_records = [{"value": 42}, {"value": 750}, {"value": -3}, {"value": 199}]
clean_records = latency_filter.run(incoming_records)      # instance method: uses self state

print("step built from config:", latency_filter.step_name, latency_filter.min_value, latency_filter.max_value)
print("records after filtering:", clean_records)
print("standalone rule check via staticmethod:", PipelineStep.is_in_range(1000, 0, 500))
print("total steps registered so far:", PipelineStep.registered_steps)


"""
---------------------------------------------------------------------
8. DECISION GUIDE: WHICH ONE DO I REACH FOR?  ⭐⭐
---------------------------------------------------------------------
A quick, practical checklist for choosing between the three when
writing (or reviewing) a method during an interview or on the job.
---------------------------------------------------------------------
"""

print("\n--- Decision Guide ---")

print("Does the method need THIS object's specific data (self.something)?")
print("  YES -> instance method (the default choice)")
print("Does it need to build/return a NEW instance, or touch CLASS-level")
print("state shared by all instances (like a registry or counter)?")
print("  YES -> @classmethod (use `cls(...)` if it constructs an instance,")
print("         so subclasses get built correctly too - see section 6)")
print("Does it need NEITHER self NOR cls - just take inputs, return outputs?")
print("  YES -> @staticmethod (it's really just a namespaced free function)")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Instance method   def method(self, ...)        -> needs a bound instance
                                                    reads/writes self.*
                                                    reaches class via
                                                    self.__class__

@classmethod      def method(cls, ...)          -> no specific instance
                                                    reads/writes cls.*
                                                    cls(...) builds a NEW
                                                    instance (alt constructor)

@staticmethod     def method(...)                -> no self, no cls
                                                    plain function, just
                                                    namespaced in the class

Calling on CLASS vs INSTANCE:
    Class.instance_method()      -> TypeError (missing `self`)
    Class.instance_method(obj)   -> works (self supplied manually)
    obj.instance_method()        -> works (self supplied automatically)

    Class.classmethod()          -> works, cls = Class
    obj.classmethod()            -> works, cls = type(obj), NOT obj itself

    Class.staticmethod()         -> works
    obj.staticmethod()           -> works (identical either way)

Alternate constructors:        MyClass.from_json(...) / .from_csv_row(...)
                                 -> parse raw input, then `return cls(...)`

Inheritance gotcha:            cls(...) inside a classmethod -> subclass's
                                 inherited constructor returns an instance
                                 of the SUBCLASS. Hardcoding the base class
                                 name instead breaks this silently.

Rule of thumb:  needs self?  -> instance method
                needs cls / builds an instance / touches class state?
                              -> classmethod
                needs neither?  -> staticmethod
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - @STATICMETHOD vs @CLASSMETHOD vs INSTANCE METHODS
=====================================================================

1. What is the difference between @staticmethod and @classmethod?

2. What implicit first argument does an instance method receive, and
   what implicit first argument does a classmethod receive instead?
   What determines what each one is bound to?

3. Why does calling `DataRecord.describe()` directly on the class (with
   no instance) raise a TypeError, while `DataRecord.record_count()`
   does not?

4. What is the single most common real-world use case for
   @classmethod? Using `DataRecord.from_json` and
   `DataRecord.from_csv_row` from this file as examples, explain what
   an "alternate constructor" is and why `__init__` alone isn't
   enough.

5. Inside `from_json`, why do we write `return cls(...)` instead of
   `return DataRecord(...)`? What breaks if you hardcode the class
   name instead, once a subclass is involved (see
   `BuggyTimestampedRecord.from_json_buggy` vs `TimestampedRecord`)?

6. If `TimestampedRecord` inherits `from_json` from `DataRecord`
   without overriding it, and you call
   `TimestampedRecord.from_json(...)`, what type is returned? Why?

7. Give an example of a good candidate for @staticmethod. Why doesn't
   it need access to `self` or `cls`? Could you have written it as a
   free function outside the class instead - what would functionally
   change?

8. What happens if you call a classmethod on an INSTANCE rather than
   the class, e.g. `sample.record_count()` instead of
   `DataRecord.record_count()`? What does `cls` get bound to in that
   case?

9. What happens if you call a staticmethod on an instance versus on
   the class? Why does it not matter which one you use?

10. Can an instance method access class-level attributes (like
    `total_records_created`)? How, and is a classmethod ever
    strictly required to do that?

11. Why can't a @staticmethod modify a specific instance's state, and
    why can't a @classmethod either (in the general case)?

12. Design a class representing a data pipeline/ETL job (Module 4,
    Q3) using all three method types: what would you make an instance
    method, what would you make a classmethod, and what would you
    make a staticmethod? Justify each choice.

13. If you needed to add a `from_dict` alternate constructor to
    `PipelineStep` in addition to `from_config`, would you implement
    it as a classmethod or a staticmethod, and why?

14. What is the practical difference between a classmethod and simply
    writing a module-level function that takes the class as its
    first argument?

15. True or false: `@staticmethod` methods can be overridden by a
    subclass the same way instance methods and classmethods can.
    Explain what "overriding" actually means for each of the three.
=====================================================================
"""
