"""
=====================================================================
CONTEXT MANAGERS - Complete Notes with Executable Examples
=====================================================================

A CONTEXT MANAGER is any object that knows how to set something up
and, critically, GUARANTEE it gets torn down again - even if the code
in between raises an exception, returns early, or gets killed by a
signal partway through. The `with` statement is the syntax Python
gives you to use one.

The problem context managers solve is simple to state and easy to get
wrong in practice: any time you acquire a resource (a file handle, a
DB connection, a network socket, a lock, a temp directory) you must
release it, and "I'll just call .close() at the end of the function"
silently breaks the moment an exception is raised between the acquire
and the release - the cleanup line is simply never reached.

Under the hood, `with` is built on a two-method PROTOCOL:
    __enter__(self)                         -> runs at the top of `with`
    __exit__(self, exc_type, exc_val, exc_tb) -> ALWAYS runs at the
                                                  bottom, exception or not
Python calls `__exit__` unconditionally as the `with` block exits, in
the same way `finally` always runs - that guarantee is the entire
point. `contextlib` in the standard library gives you two shortcuts
for writing context managers without hand-rolling a class: the
`@contextmanager` generator decorator, and helpers like `suppress`
and `ExitStack` for common patterns.

This is a ⭐⭐⭐ Data Engineering interview topic precisely because DB
connections, file handles, and network resources are everywhere in
pipeline code, and "write one to manage a DB connection" is an
extremely common live-coding question.
=====================================================================
"""

import contextlib
import os
import tempfile

print("--- Overview ---")
print("A context manager guarantees cleanup (__exit__) runs even if")
print("an exception happens inside the `with` block - unlike manual")
print("open()/close() pairs, which leak resources on exception.")


# A scratch directory for every file-based demo below, itself opened
# with a context manager so IT cleans itself up when this script ends.
_scratch = tempfile.TemporaryDirectory()
SCRATCH_DIR = _scratch.name


"""
---------------------------------------------------------------------
1. THE PROBLEM: GUARANTEED CLEANUP, EVEN ON EXCEPTION  ⭐⭐⭐
---------------------------------------------------------------------
Manual open()/close() pairs LOOK fine, but the close() call is just a
line of code like any other - if something between open() and close()
raises, that line is skipped, and the resource (here, a file handle)
is leaked. We PROVE this below by inspecting the file object's own
`.closed` attribute after each version runs.
---------------------------------------------------------------------
"""

print("\n--- The Problem: Guaranteed Cleanup ---")

buggy_path = os.path.join(SCRATCH_DIR, "buggy.txt")

# BUGGY: manual open/close, with an exception raised in between
def write_report_broken(path):
    f = open(path, "w")            # resource acquired
    f.write("starting report...\n")
    raise ValueError("simulated failure mid-write (e.g. a bad record)")
    f.close()                       # NEVER REACHED - close() is skipped!

leaked_handle = None
try:
    write_report_broken(buggy_path)
except ValueError as e:
    print("caught exception from broken version:", e)

# We can't get `f` back out of the crashed function, so re-demonstrate
# the same leak in a way we CAN inspect from the outside:
f = open(buggy_path, "w")
try:
    f.write("more data\n")
    raise ValueError("simulated failure again")
except ValueError:
    pass    # exception handled, but notice: we never called f.close()
print("file handle still open after the buggy path? ->", not f.closed)
f.close()   # cleaning up by hand so the OS handle isn't actually leaked

# FIXED: `with` guarantees __exit__ (which calls close()) runs no
# matter what happens inside the block
fixed_path = os.path.join(SCRATCH_DIR, "fixed.txt")
try:
    with open(fixed_path, "w") as f:
        f.write("starting report...\n")
        raise ValueError("simulated failure mid-write, same as before")
except ValueError as e:
    print("caught exception from `with` version:", e)
print("file handle still open after the `with` path? ->", not f.closed)
print("\n`with` closed the file automatically DESPITE the exception -")
print("that guarantee is the entire reason context managers exist.")


"""
---------------------------------------------------------------------
2. THE PROTOCOL: __enter__ AND __exit__  ⭐⭐⭐
---------------------------------------------------------------------
Any class that defines both `__enter__` and `__exit__` can be used
after `with`. `__enter__`'s RETURN VALUE becomes whatever follows
`as` - it does NOT have to be the context manager object itself,
though it commonly is. `__exit__` always receives three arguments
describing any exception that occurred inside the block:
    exc_type -> the exception CLASS (e.g. ValueError), or None
    exc_val  -> the exception INSTANCE, or None
    exc_tb   -> the traceback object, or None
All three are None if the block finished cleanly.
---------------------------------------------------------------------
"""

print("\n--- The Protocol: __enter__ and __exit__ ---")

class Announce:
    """Minimal context manager - just logs its own lifecycle."""
    def __enter__(self):
        print("  __enter__ called: setting things up")
        return "the value bound to `as`"     # note: NOT `self` this time

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"  __exit__ called: exc_type={exc_type}, exc_val={exc_val}")
        print("  tearing things down")
        # returning None (falls through) means "don't suppress anything"

with Announce() as value:
    print("  inside the block, `as` gave us:", repr(value))
print("block exited cleanly - __enter__'s return value became `value`")


"""
---------------------------------------------------------------------
3. THE __exit__ RETURN-VALUE GOTCHA: SUPPRESSING EXCEPTIONS  ⭐⭐⭐
---------------------------------------------------------------------
This is a classic trick question. If `__exit__` returns a value that
is truthy (most notably `True`), Python treats the exception as
HANDLED and SWALLOWS it - execution continues normally after the
`with` block as if nothing happened. Returning `False` (or `None`,
the default) lets the exception propagate normally. This is easy to
get backwards, and doing it BY ACCIDENT is a real bug: it hides
errors that should have crashed the pipeline.
---------------------------------------------------------------------
"""

print("\n--- The __exit__ Gotcha: Suppressing Exceptions ---")

class NonSuppressing:
    """Returns False/None -> exception propagates normally (the safe default)."""
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("  NonSuppressing.__exit__ ran, returning False")
        return False    # <-- do NOT suppress; let the exception continue

class Suppressing:
    """Returns True -> exception is SWALLOWED, code after `with` still runs."""
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"  Suppressing.__exit__ ran, swallowing {exc_type.__name__}")
        return True     # <-- suppresses ANY exception raised in the block!

try:
    with NonSuppressing():
        raise RuntimeError("boom - should NOT be suppressed")
    print("this line never runs - exception propagated past the `with`")
except RuntimeError as e:
    print("caught outside the `with`, as expected:", e)

with Suppressing():
    raise RuntimeError("boom - SHOULD be suppressed")
print("execution reached this line - the exception above was swallowed!")
print("\nLesson: returning True from __exit__ is powerful but dangerous -")
print("an unconditional `return True` will silently hide EVERY error,")
print("including ones you never intended to catch (e.g. a typo'd name).")


"""
---------------------------------------------------------------------
4. WRITING A CONTEXT MANAGER FOR A DB CONNECTION  ⭐⭐⭐
---------------------------------------------------------------------
The canonical interview ask: "write a context manager to manage a DB
connection." The pattern that matters is COMMIT ON CLEAN EXIT,
ROLLBACK ON EXCEPTION - `__exit__`'s exc_type argument is exactly what
tells you which case you're in. We use a small mock connection here
(no real DB server in this sandbox) but the shape is identical to
wrapping psycopg2/pyodbc/sqlite3 connections in production.
---------------------------------------------------------------------
"""

print("\n--- Custom Class-Based Context Manager for a DB Connection ---")

class MockDBConnection:
    """Stands in for a real DB-API connection (psycopg2/pyodbc/sqlite3)."""
    def __init__(self, name):
        self.name = name
        self.open = False
        self.pending = []       # uncommitted statements
        self.committed = []     # statements that made it to "disk"

    def connect(self):
        self.open = True
        print(f"  [{self.name}] connection opened")

    def execute(self, statement):
        if not self.open:
            raise RuntimeError("connection is not open")
        self.pending.append(statement)
        print(f"  [{self.name}] executed: {statement!r}")

    def commit(self):
        self.committed.extend(self.pending)
        print(f"  [{self.name}] COMMIT ({len(self.pending)} statement(s))")
        self.pending = []

    def rollback(self):
        print(f"  [{self.name}] ROLLBACK - discarding {len(self.pending)} statement(s)")
        self.pending = []

    def close(self):
        self.open = False
        print(f"  [{self.name}] connection closed")

class DBConnectionManager:
    """Class-based context manager: connect on enter, commit/rollback
    + close on exit, based on whether the block raised."""
    def __init__(self, name):
        self.name = name
        self.conn = None

    def __enter__(self):
        self.conn = MockDBConnection(self.name)
        self.conn.connect()
        return self.conn       # `as` gets the CONNECTION, not the manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()          # clean exit -> save the work
        else:
            self.conn.rollback()        # exception -> discard the work
        self.conn.close()               # ALWAYS release the connection
        return False                     # never suppress - let caller see errors

print("Clean run (should COMMIT):")
with DBConnectionManager("orders_db") as conn:
    conn.execute("INSERT INTO orders VALUES (1, 'widget')")
    conn.execute("INSERT INTO orders VALUES (2, 'gadget')")
print("committed rows:", conn.committed)

print("\nFailing run (should ROLLBACK):")
try:
    with DBConnectionManager("orders_db") as conn:
        conn.execute("INSERT INTO orders VALUES (3, 'gizmo')")
        raise ValueError("simulated bad record - abort the transaction")
except ValueError as e:
    print("exception correctly propagated out:", e)
print("committed rows after rollback:", conn.committed)   # empty - rolled back


"""
---------------------------------------------------------------------
5. THE @contextlib.contextmanager SHORTCUT  ⭐⭐⭐
---------------------------------------------------------------------
Writing a full class with __init__/__enter__/__exit__ is verbose for
simple cases. `@contextlib.contextmanager` turns a GENERATOR function
with EXACTLY ONE `yield` into a context manager:
    - everything BEFORE `yield`  = the __enter__ logic
    - the yielded value           = what `as` binds to
    - everything AFTER `yield`   = the __exit__ logic
An exception raised inside the `with` block is raised AT the `yield`
line inside the generator - so you wrap the yield in try/except/else/
finally to get the same commit-vs-rollback behavior as the class
version above.
---------------------------------------------------------------------
"""

print("\n--- The @contextlib.contextmanager Shortcut ---")

@contextlib.contextmanager
def db_transaction(name):
    conn = MockDBConnection(name)
    conn.connect()              # __enter__-equivalent code
    try:
        yield conn               # value bound to `as`; block runs here
    except Exception:
        conn.rollback()          # an exception reached us -> discard
        raise                     # re-raise so the caller still sees it
    else:
        conn.commit()            # no exception -> safe to persist
    finally:
        conn.close()              # ALWAYS runs, exception or not

print("Clean run (generator-based, should COMMIT):")
with db_transaction("analytics_db") as conn:
    conn.execute("UPDATE metrics SET value = 42")
print("committed rows:", conn.committed)

print("\nFailing run (generator-based, should ROLLBACK):")
try:
    with db_transaction("analytics_db") as conn:
        conn.execute("UPDATE metrics SET value = -1")
        raise RuntimeError("simulated constraint violation")
except RuntimeError as e:
    print("exception correctly propagated out:", e)
print("committed rows after rollback:", conn.committed)   # empty again

print("\nSame externally-visible behavior as the class version, in far")
print("fewer lines - this is the idiomatic choice for simple, one-off")
print("context managers in real pipeline code.")


"""
---------------------------------------------------------------------
6. NESTING MULTIPLE CONTEXT MANAGERS IN ONE `with`  ⭐⭐
---------------------------------------------------------------------
A single `with` statement can open several context managers at once,
comma-separated - each gets its own `as` target, and Python still
guarantees ALL of them are exited (in reverse order) even if a later
one fails to enter or the block raises. This is the common pattern
for e.g. reading from one file and writing to another.
---------------------------------------------------------------------
"""

print("\n--- Nesting Multiple Context Managers ---")

src_path = os.path.join(SCRATCH_DIR, "source.csv")
dst_path = os.path.join(SCRATCH_DIR, "cleaned.csv")
with open(src_path, "w") as f:
    f.write("id,value\n1,10\n2,\n3,30\n")     # row 2 has a missing value

with open(src_path) as src, open(dst_path, "w") as dst:
    header = next(src)
    dst.write(header)
    for line in src:
        id_, value = line.strip().split(",")
        if value:                              # simple ETL-style cleaning
            dst.write(f"{id_},{value}\n")

with open(dst_path) as f:
    print("cleaned.csv contents:")
    print(" ", f.read().replace("\n", "\n  ").rstrip())
print("\nBoth files were closed automatically, even though the loop body")
print("could have raised at any point (e.g. a malformed row).")


"""
---------------------------------------------------------------------
7. contextlib.suppress: SILENCING A SPECIFIC EXPECTED EXCEPTION  ⭐⭐
---------------------------------------------------------------------
`contextlib.suppress(*exception_types)` is a tiny, honest context
manager for the common "it's fine if this fails for this ONE known
reason" case - e.g. deleting a file that might already be gone. It's
strictly narrower (and safer) than the `return True` trick from
section 3, because you name exactly which exception type(s) to ignore.
---------------------------------------------------------------------
"""

print("\n--- contextlib.suppress ---")

missing_path = os.path.join(SCRATCH_DIR, "does_not_exist.tmp")

# Without suppress: this would raise FileNotFoundError
with contextlib.suppress(FileNotFoundError):
    os.remove(missing_path)
print("os.remove() on a missing file did not crash the script")

try:
    with contextlib.suppress(FileNotFoundError):
        raise PermissionError("suppress only catches the type(s) you list")
except PermissionError as e:
    print("correctly NOT suppressed (wrong exception type):", e)


"""
---------------------------------------------------------------------
8. contextlib.ExitStack: A DYNAMIC NUMBER OF RESOURCES  ⭐⭐⭐
---------------------------------------------------------------------
`with a, b, c:` only works when you know the resource COUNT up front.
Real ETL jobs often need to open an unknown number of files decided
at runtime (e.g. "every .csv in this batch"). `ExitStack` lets you
push any number of context managers onto one stack via
`enter_context()`, and guarantees they are ALL exited, in reverse
order, when the `with ExitStack()` block ends - exception or not.
---------------------------------------------------------------------
"""

print("\n--- contextlib.ExitStack for a Dynamic Number of Resources ---")

batch_paths = [os.path.join(SCRATCH_DIR, f"part_{i}.csv") for i in range(4)]
for i, path in enumerate(batch_paths):
    with open(path, "w") as f:
        f.write(f"id,value\n{i},{i * 10}\n")

def load_batch(paths):
    """Opens an unknown-at-write-time number of files and sums a column,
    guaranteeing every handle is closed even if one file is bad."""
    total = 0
    with contextlib.ExitStack() as stack:
        handles = [stack.enter_context(open(p)) for p in paths]
        print(f"  opened {len(handles)} file(s) via ExitStack")
        for handle in handles:
            next(handle)                       # skip header
            for line in handle:
                total += int(line.strip().split(",")[1])
    return total   # by the time we return, ALL handles are already closed

result = load_batch(batch_paths)
print("sum across all batch files:", result)

# ExitStack also cleans up correctly if a LATER file in the list is bad
bad_paths = batch_paths + [os.path.join(SCRATCH_DIR, "missing_part.csv")]
try:
    load_batch(bad_paths)
except FileNotFoundError as e:
    print("bad file correctly raised, and earlier handles were still closed:", e)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Problem solved             -> guaranteed cleanup, even on exception
                               (manual close() can be skipped; `with`
                               cannot)

Protocol (class-based):
    __enter__(self)                    -> return value becomes `as` target
    __exit__(self, exc_type,
              exc_val, exc_tb)          -> ALWAYS runs; args are None
                                           if the block exited cleanly
    __exit__ returns truthy (True)     -> SUPPRESSES the exception
    __exit__ returns falsy (False/None) -> exception propagates normally

Generator shortcut:
    @contextlib.contextmanager
    def cm():
        ...setup...                     # = __enter__
        try:
            yield value                  # exactly ONE yield; `as value`
        except Exception:
            ...handle/rollback...
            raise                         # re-raise unless suppressing
        else:
            ...commit on clean exit...
        finally:
            ...teardown, always runs...  # = __exit__

DB connection pattern       -> commit on clean exit, rollback on
                               exception, close in ALL cases

Nesting                     -> with a() as x, b() as y:  (comma form)
contextlib.suppress(Exc)    -> narrowly silence one known exception type
contextlib.ExitStack()      -> stack.enter_context(cm) per resource,
                               for a COUNT decided at runtime
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")

_scratch.cleanup()


"""
=====================================================================
INTERVIEW QUESTIONS - CONTEXT MANAGERS
=====================================================================

1. What is a context manager, and what specific problem does the
   `with` statement solve that manual `open()`/`close()` pairs do not?

2. Write a context manager to manage a DB connection. What should it
   do differently on a clean exit versus when an exception occurs
   inside the `with` block?

3. What are the exact method signatures of `__enter__` and `__exit__`
   required to make an object usable with `with`?

4. What does the value returned by `__enter__` become? Does it have
   to be the context manager object itself (`self`)?

5. What are `exc_type`, `exc_val`, and `exc_tb` in `__exit__`, and
   what are all three set to when the `with` block completes without
   raising?

6. What happens if `__exit__` returns `True`? Why is this considered
   a common gotcha, and when (if ever) is it the right thing to do?

7. In `DBConnectionManager.__exit__` in this file, why does it
   explicitly `return False` instead of just letting the function
   fall through to the end?

8. How do you turn a generator function into a context manager using
   `contextlib`? What is required about the number of `yield`
   statements it may contain?

9. In a `@contextlib.contextmanager` function, where does an exception
   raised inside the `with` block actually get raised from the
   generator's point of view? Why do you wrap the `yield` in
   `try/except/finally`?

10. What is the difference between putting cleanup code after `yield`
    with no try/finally versus wrapping it in `finally`? What breaks
    if you skip the `finally`?

11. How do you open two files in the same `with` statement, and in
    what order are they closed if the block raises partway through?

12. What problem does `contextlib.ExitStack` solve that the comma-
    separated `with a, b, c:` form cannot? Give a realistic ETL
    example.

13. How is `contextlib.suppress(SomeError)` different from wrapping
    code in `try: ... except SomeError: pass`? Why might you prefer
    it?

14. If an exception occurs while opening the THIRD of five files
    pushed onto an `ExitStack`, what happens to the first two files
    that were already opened?

15. Design-wise, when would you reach for a class-based context
    manager (`__enter__`/`__exit__`) instead of the
    `@contextlib.contextmanager` generator shortcut, or vice versa?
=====================================================================
"""
