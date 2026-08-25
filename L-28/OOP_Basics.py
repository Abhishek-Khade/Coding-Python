"""
=====================================================================
PYTHON OOP BASICS - Classes, Objects, __init__, and self
=====================================================================

The previous module showed that a CLOSURE can give a function private,
persistent state without ever writing a class - a cell holding one
value, wrapped by one function. That trick stops scaling the moment
you need several pieces of related state PLUS several behaviors that
all operate on that state together. That's exactly the gap a CLASS
fills.

A CLASS is a blueprint - a template that describes what attributes
(data) and methods (behavior) something will have. An OBJECT (also
called an INSTANCE) is one concrete thing built from that blueprint,
with its own independent copy of the instance data. You can stamp out
as many independent objects from one class as you want, the same way
one cookie cutter (the class) produces many separate cookies
(the instances).

Two special things make a class actually usable:
    __init__   - the INITIALIZER, which sets up a new instance's
                 starting attributes right after it's created
    self       - the explicit reference to "this particular instance",
                 passed automatically into every instance method

This file covers the real mechanics behind both of those, the
instance-vs-class-attribute distinction (and its classic mutable-
default gotcha), how attribute lookup actually works under the hood,
and a running data-engineering-flavored example class.
=====================================================================
"""

print("--- Overview ---")
print("A class is a blueprint; an object/instance is one concrete")
print("thing built from that blueprint, with its own independent data.")


"""
---------------------------------------------------------------------
1. CLASS VS OBJECT: BLUEPRINT VS INSTANCE  ⭐⭐⭐
---------------------------------------------------------------------
Defining a class does NOT create any object - it just registers the
template. Each time you CALL the class like a function
(ClassName(...)), Python builds one new, independent object from that
template.
---------------------------------------------------------------------
"""

print("\n--- Class vs Object: Blueprint vs Instance ---")

class DataRecord:
    """A blueprint for one row of ingested data. No objects exist yet."""
    source_system = "unknown"     # a CLASS attribute - covered in section 4

# Defining the class above did NOT create a DataRecord. Calling it does:
record_a = DataRecord()
record_b = DataRecord()

print("record_a:", record_a)
print("record_b:", record_b)
print("are they the same object? ->", record_a is record_b)
print("do they share the same class? ->", type(record_a) is type(record_b))
print("\nSame blueprint, two completely separate objects in memory -")
print("exactly like two cookies from the same cutter are still two")
print("physically separate cookies.")


"""
---------------------------------------------------------------------
2. __init__ IS THE INITIALIZER, NOT REALLY A "CONSTRUCTOR"  ⭐⭐⭐
---------------------------------------------------------------------
`__init__` is where you set up a new instance's starting attributes.
It's commonly called "the constructor" in casual conversation, but
that's technically imprecise: `__init__` receives an ALREADY-CREATED
(but blank) object via `self` and just configures it - it never
returns a value (returning anything other than None from __init__ is
actually a TypeError).

The object is actually BUILT by `__new__`, a lower-level method that
runs BEFORE `__init__` and is responsible for allocating and
returning the new instance. You almost never override `__new__` in
everyday application code (it mostly shows up for things like
immutable types, singletons, or metaclass tricks), but knowing it
exists - and that Python calls `__new__` THEN `__init__`, in that
order - is a fair interview detail to have ready.
---------------------------------------------------------------------
"""

print("\n--- __init__ Is the Initializer, Not the Constructor ---")

class PipelineStep:
    """One named, callable stage in a data pipeline."""

    def __init__(self, name, transform_fn):
        print(f"  __init__ running for step '{name}'")
        self.name = name                # instance attribute, set on THIS object
        self.transform_fn = transform_fn
        self.run_count = 0

step = PipelineStep("uppercase", str.upper)
print("step.name:", step.name)

# Proving __new__ runs first: override it just to observe the order.
class OrderDemo:
    def __new__(cls, *args, **kwargs):
        print("  1) __new__ runs first - allocates and returns the blank object")
        instance = super().__new__(cls)   # actually allocate the instance
        return instance

    def __init__(self, value):
        print("  2) __init__ runs second - configures the object __new__ returned")
        self.value = value

_ = OrderDemo(42)

# __init__ must return None - returning anything else is a hard error.
class BadInit:
    def __init__(self):
        return "not allowed"     # __init__ can only return None

try:
    BadInit()
except TypeError as e:
    print("\nError from an __init__ that returns non-None:", e)


"""
---------------------------------------------------------------------
3. WHAT self REALLY IS: EXPLICIT INSTANCE, AUTO-PASSED  ⭐⭐⭐
---------------------------------------------------------------------
`self` is not magic syntax - it's an ordinary parameter that happens
to receive "the instance this method was called on". Python fills it
in automatically whenever you call a method through an INSTANCE
(instance.method(...)), but the underlying mechanism is plain: an
instance method is just a function stored on the CLASS, and
`instance.method(args)` is syntactic sugar for `Class.method(instance,
args)`. You can prove this by calling it both ways and getting
identical results.
---------------------------------------------------------------------
"""

print("\n--- What self Really Is ---")

class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1       # 'self' says WHICH object's count to bump
        return self.count

c = Counter()

# The normal way: Python auto-passes c as 'self'.
print("c.increment() ->", c.increment())

# The desugared way: call the UNBOUND function on the class directly,
# passing the instance manually. Identical effect.
print("Counter.increment(c) ->", Counter.increment(c))

print("\nc.increment() is just syntactic sugar for Counter.increment(c) -")
print("Python looks up 'increment' on type(c), then calls it with c as")
print("the first argument. Nothing about 'self' is a reserved keyword;")
print("it's a strong NAMING CONVENTION every Python codebase follows.")

# You can see the bound-vs-unbound distinction directly:
print("\nc.increment (bound method):", c.increment)
print("Counter.increment (plain function):", Counter.increment)


"""
---------------------------------------------------------------------
4. INSTANCE ATTRIBUTES VS CLASS ATTRIBUTES  ⭐⭐⭐
---------------------------------------------------------------------
An INSTANCE attribute lives on one specific object (usually set via
`self.x = ...` inside __init__) - every instance gets its own copy.
A CLASS attribute is defined directly in the class body and is SHARED
by the class itself and every instance that doesn't override it - it
exists in exactly ONE place in memory, no matter how many instances
you create. Class attributes are great for shared config, constants,
or default values that genuinely should be identical across
instances.
---------------------------------------------------------------------
"""

print("\n--- Instance Attributes vs Class Attributes ---")

class PipelineJob:
    environment = "production"   # CLASS attribute - one copy, shared by all

    def __init__(self, job_id):
        self.job_id = job_id     # INSTANCE attribute - one copy per object

job_1 = PipelineJob("job-001")
job_2 = PipelineJob("job-002")

print("job_1.job_id:", job_1.job_id, "| job_2.job_id:", job_2.job_id)
print("job_1.environment:", job_1.environment, "| job_2.environment:", job_2.environment)

# Reassigning the class attribute through the CLASS affects everyone
# who hasn't shadowed it with their own instance attribute:
PipelineJob.environment = "staging"
print("\nafter PipelineJob.environment = 'staging':")
print("job_1.environment:", job_1.environment, "| job_2.environment:", job_2.environment)

# But assigning to `self.environment = ...` on ONE instance creates a
# NEW instance attribute that shadows the class attribute for that
# object only - it does not touch the shared class-level value.
job_1.environment = "dev-override"
print("\nafter job_1.environment = 'dev-override' (instance-level set):")
print("job_1.environment:", job_1.environment, "| job_2.environment:", job_2.environment)
print("PipelineJob.environment (the class itself):", PipelineJob.environment)


"""
---------------------------------------------------------------------
5. THE CLASSIC PITFALL: MUTABLE CLASS ATTRIBUTES  ⭐⭐⭐
---------------------------------------------------------------------
This is one of the most common Python interview gotchas. If you
define a MUTABLE class attribute (a list, dict, or set) intending it
as a per-instance default, every instance that hasn't set its own
version ends up sharing and MUTATING the exact same object - because
there's still only one copy of that class attribute in memory. The
fix is to create a fresh mutable object PER INSTANCE, inside
__init__.
---------------------------------------------------------------------
"""

print("\n--- The Mutable Class Attribute Pitfall ---")

# BUGGY: 'errors' looks like a per-instance default, but it's really
# ONE list shared by the class and every instance of it.
class PipelineRunBroken:
    errors = []     # DANGER: a single shared list, not a fresh one per object

    def __init__(self, run_id):
        self.run_id = run_id

    def log_error(self, message):
        self.errors.append(message)   # mutating the SHARED class list!

run_1 = PipelineRunBroken("run-1")
run_2 = PipelineRunBroken("run-2")

run_1.log_error("null value in column 'price'")
print("run_1.errors:", run_1.errors)
print("run_2.errors:", run_2.errors, "  <- BUG: run_2 never logged anything!")
print("run_1.errors is run_2.errors ->", run_1.errors is run_2.errors)

# FIXED: build a brand-new list inside __init__, so each instance gets
# its OWN object, assigned as a genuine instance attribute.
class PipelineRunFixed:
    def __init__(self, run_id):
        self.run_id = run_id
        self.errors = []     # a fresh list, created fresh for THIS instance

fixed_1 = PipelineRunFixed("run-1")
fixed_2 = PipelineRunFixed("run-2")

fixed_1.log_error = lambda message: fixed_1.errors.append(message)  # demo helper
fixed_1.errors.append("null value in column 'price'")
print("\nfixed_1.errors:", fixed_1.errors)
print("fixed_2.errors:", fixed_2.errors, "  <- correct: untouched")
print("fixed_1.errors is fixed_2.errors ->", fixed_1.errors is fixed_2.errors)

print("\nRule of thumb: IMMUTABLE class attributes (int, str, tuple,")
print("bool) are safe to share, because you can't mutate them in")
print("place - any 'change' just creates a new instance attribute that")
print("shadows the class one (see section 4). MUTABLE class attributes")
print("(list, dict, set) are dangerous as shared defaults - always")
print("build those fresh inside __init__ instead.")


"""
---------------------------------------------------------------------
6. EVERY OBJECT (USUALLY) HAS A __dict__  ⭐⭐
---------------------------------------------------------------------
Most ordinary objects store their instance attributes in a plain
dictionary, accessible as `obj.__dict__`. This is genuinely useful
for debugging: it shows you EXACTLY what instance state an object
carries, with no guessing.
---------------------------------------------------------------------
"""

print("\n--- The Object's __dict__ ---")

print("fixed_1.__dict__:", fixed_1.__dict__)
print("fixed_2.__dict__:", fixed_2.__dict__)

# Setting a new attribute dynamically just adds a key to __dict__ -
# Python doesn't require attributes to be pre-declared anywhere.
fixed_1.retry_count = 2
print("\nafter fixed_1.retry_count = 2:")
print("fixed_1.__dict__:", fixed_1.__dict__)

# Class attributes do NOT live in an instance's __dict__ - they live
# on the CLASS's own __dict__ instead (which is a mappingproxy, not a
# plain dict, since the class itself is more tightly controlled).
print("\n'environment' in job_2.__dict__ ->", "environment" in job_2.__dict__)
print("'environment' in type(job_2).__dict__ ->", "environment" in PipelineJob.__dict__)


"""
---------------------------------------------------------------------
7. HOW ATTRIBUTE LOOKUP ACTUALLY WORKS  ⭐⭐⭐
---------------------------------------------------------------------
When you write `obj.attr`, Python does NOT look in one single place.
Roughly, it checks:
    1. The INSTANCE's own __dict__ first.
    2. If not found there, the CLASS's __dict__ (then each parent
       class's __dict__, in Method Resolution Order - see the
       Inheritance file later in this module).
    3. If still not found anywhere, raise AttributeError.
This is EXACTLY why section 4's "instance attribute shadows class
attribute" behavior happens: the instance dict is always checked
first, so once an instance has its own entry for a name, the class's
version is never even reached for that lookup.
---------------------------------------------------------------------
"""

print("\n--- How Attribute Lookup Works: Instance Dict, Then Class Dict ---")

class LookupDemo:
    label = "class-level default"     # only in the CLASS's __dict__

demo = LookupDemo()
print("demo.label (not yet in demo.__dict__):", demo.label)
print("'label' in demo.__dict__ ->", "label" in demo.__dict__)
print("found by falling through to the class's __dict__ instead.")

# Now shadow it with an instance attribute of the same name:
demo.label = "instance-level override"
print("\nafter demo.label = 'instance-level override':")
print("demo.label:", demo.label, "  <- instance dict is checked FIRST")
print("LookupDemo.label:", LookupDemo.label, "  <- class's copy is untouched")

# A missing attribute anywhere raises AttributeError, not a silent None:
try:
    demo.nonexistent_attribute
except AttributeError as e:
    print("\nlooking up a truly missing attribute raises:", e)


"""
---------------------------------------------------------------------
8. RUNNING EXAMPLE: A PipelineStep CLASS WITH REAL BEHAVIOR  ⭐⭐⭐
---------------------------------------------------------------------
Pulling sections 2-7 together into one realistic data-engineering
class: each PipelineStep wraps one transformation function, tracks
how many times it's been run (instance state), and reports through a
shared class-level counter of how many steps exist in total (class
state) - a natural, non-buggy use of a class attribute, since it's
only ever mutated through the class itself, never per-instance.
---------------------------------------------------------------------
"""

print("\n--- Running Example: PipelineStep With Real Behavior ---")

class PipelineStepDemo:
    total_steps_created = 0     # CLASS attribute: one shared counter

    def __init__(self, name, transform_fn):
        self.name = name                 # instance attribute
        self.transform_fn = transform_fn  # instance attribute
        self.run_count = 0                # instance attribute
        PipelineStepDemo.total_steps_created += 1   # mutate via the CLASS, safely

    def run(self, value):
        """Apply this step's transform to a value and track that it ran."""
        self.run_count += 1
        return self.transform_fn(value)

    def describe(self):
        return f"'{self.name}' has run {self.run_count} time(s)"

uppercase_step = PipelineStepDemo("uppercase", str.upper)
strip_step = PipelineStepDemo("strip_whitespace", str.strip)

raw_value = "  dirty input  "
after_strip = strip_step.run(raw_value)
after_upper = uppercase_step.run(after_strip)

print("raw_value:", repr(raw_value))
print("after strip_step.run():", repr(after_strip))
print("after uppercase_step.run():", repr(after_upper))
print(strip_step.describe())
print(uppercase_step.describe())
print("PipelineStepDemo.total_steps_created:", PipelineStepDemo.total_steps_created)

# Run uppercase_step again to show its OWN run_count moves independently:
uppercase_step.run("more data")
print("\nafter running uppercase_step a second time:")
print(uppercase_step.describe(), "  <- only THIS instance's counter changed")
print(strip_step.describe(), "  <- untouched, it's a separate instance")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
class            -> the blueprint/template (defined once)
object/instance  -> one concrete thing built from the class (ClassName())

__new__   -> allocates and returns the raw object (runs FIRST, rarely
             overridden)
__init__  -> INITIALIZES an already-created object via self (runs
             SECOND); must return None

self               -> explicit reference to "this instance"
instance.method(a)  ->  desugars to  ->  Class.method(instance, a)

Instance attribute -> self.x = ...  in __init__      -> one copy PER object
Class attribute    -> x = ...       in the class body -> one copy, SHARED

Mutable class-attribute pitfall:
    class Foo:
        items = []          # DANGER - shared by every instance
    ---------------------------------------------------
    class Foo:
        def __init__(self):
            self.items = []  # SAFE - fresh list per instance

obj.__dict__        -> dict of THIS instance's own attributes
type(obj).__dict__  -> mappingproxy of the CLASS's own attributes

Attribute lookup order for obj.attr:
    1. instance.__dict__
    2. class.__dict__ (then parent classes, in MRO)
    3. AttributeError if found nowhere
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - OOP BASICS (CLASSES, OBJECTS, __init__, self)
=====================================================================

1. What is the difference between a class and an object/instance in
   Python?

2. Why is `__init__` more accurately called an "initializer" rather
   than a "constructor"? What method actually constructs the object,
   and in what order do the two run?

3. What happens if `__init__` tries to `return` something other than
   `None`?

4. What exactly is `self`? Is it a reserved keyword? What would
   happen if you named it something else, like `this` or `obj`?

5. Given `Counter` and its `increment` method from this file, explain
   why `c.increment()` and `Counter.increment(c)` produce the exact
   same result. What is Python actually doing when it resolves
   `c.increment()`?

6. What's the difference between an instance attribute and a class
   attribute? Give an example of when a class attribute is the right
   choice.

7. Walk through the classic "mutable default class attribute" bug:
       class Foo:
           items = []
   Why does mutating `items` through one instance affect every other
   instance of `Foo`? How do you fix it?

8. Would the same bug happen with an IMMUTABLE class attribute, like
   `count = 0`, if an instance does `self.count += 1`? Why or why not?

9. What is `obj.__dict__`, and what does (and doesn't) show up in it
   for a typical instance?

10. Describe, step by step, what Python does when you access
    `obj.attribute` - where does it look first, and where does it
    look next if the first place doesn't have it?

11. In `PipelineStepDemo`, `total_steps_created` is a class attribute
    incremented every time `__init__` runs. Why is this usage safe,
    unlike the `errors = []` example in question 7?

12. If you set `job_1.environment = "dev-override"` on one instance
    of `PipelineJob` (which has a class attribute `environment`),
    does that change what `PipelineJob.environment` or `job_2.environment`
    report? Explain why in terms of attribute lookup.

13. How would you design a class to represent one stage of a data
    pipeline (inputs, a transform function, and some run/error
    tracking)? What would you make instance-level vs class-level?

14. When would you actually need to override `__new__` instead of
    just using `__init__`?

15. What is the difference between a "bound method" (like
    `c.increment`) and the plain function stored on the class (like
    `Counter.increment`)?
=====================================================================
"""
