"""
=====================================================================
PYTHON EXCEPTION HANDLING - Complete Notes with Executable Examples
=====================================================================

Pipelines fail. A source API times out, a partner drops a malformed
file into your S3 bucket, a config value that used to be an int shows
up as an empty string. The question interviewers are actually asking
with "how do you handle exceptions" is: does your code degrade
gracefully, or does one bad record take down a job that was 99%
successful?

Python's exception system gives you four cooperating pieces:
`try` (run code that might fail), `except` (handle specific failure
types), `else` (run code ONLY when nothing went wrong), and `finally`
(run cleanup no matter what happened). On top of that, exceptions
form a CLASS HIERARCHY - which is why `except Exception` is almost
always the right "catch-all" while a bare `except:` is a trap, and
why you can build your OWN exception types to make error handling in
a pipeline precise instead of guessing from string messages.

This file also covers exception CHAINING (`raise X from Y`, and the
`__cause__`/`__context__` attributes Python sets automatically) and
the difference between RE-RAISING an error unchanged versus WRAPPING
it in a more meaningful, pipeline-specific type - both of which show
up constantly in real ETL codebases and in interviews.
=====================================================================
"""

import json
import traceback

print("--- Overview ---")
print("try = run risky code | except = handle specific failures |")
print("else = only if nothing failed | finally = always runs.")
print("Custom exception hierarchies make pipeline error handling")
print("precise instead of guessing from exception string messages.")


"""
---------------------------------------------------------------------
1. THE FULL try / except / else / finally STRUCTURE  ⭐⭐⭐
---------------------------------------------------------------------
Execution order:
    try runs first.
    If it raises  -> matching except runs, else is SKIPPED.
    If it succeeds -> else runs (NOT inside the try - so a bug in
                      else itself won't be mistaken for a try failure).
    finally ALWAYS runs last, whether an exception occurred, was
    caught, was NOT caught, or the block returned early - it even
    runs when an except block re-raises the exception, BEFORE that
    exception continues propagating up to the caller.
---------------------------------------------------------------------
"""

print("\n--- The Full try/except/else/finally Structure ---")

def risky_operation(mode):
    try:
        print(f"  [try] running with mode={mode!r}")
        if mode == "boom":
            raise ValueError("simulated bad record")
        return "parsed-ok"
    except ValueError as e:
        # this branch only runs when the try block actually raised
        print(f"  [except] logging the failure, then re-raising: {e}")
        raise   # bare re-raise - see Section 6 for why this matters
    else:
        # only reached when try did NOT raise - safe to trust the result here
        print("  [else] no exception occurred - result is trustworthy")
    finally:
        # runs unconditionally - this is where you'd close a file handle,
        # release a DB connection, or decrement an in-flight counter
        print("  [finally] cleanup runs NO MATTER WHAT happens above")

print("Case 1: success path (try succeeds -> else runs -> finally runs)")
result = risky_operation("ok")
print("  returned:", result)

print("\nCase 2: failure path, caught by the CALLER after re-raise")
print("(finally still runs INSIDE risky_operation before the exception")
print("escapes to this outer try/except)")
try:
    risky_operation("boom")
except ValueError as e:
    print(f"  [outer except] finally already ran above; now caught here: {e}")

print("\nNotice 'else' printed nothing in Case 2 - it only runs when")
print("ZERO exceptions occurred in the try block.")


"""
---------------------------------------------------------------------
2. CATCHING MULTIPLE EXCEPTION TYPES  ⭐⭐⭐
---------------------------------------------------------------------
Two idioms exist for handling more than one exception type:
    - TUPLE form: `except (TypeError, ValueError):` - use this when
      several exception types deserve the EXACT SAME recovery.
    - SEPARATE except blocks - use this when different exception
      types need DIFFERENT recovery logic, even if they were raised
      by the same line of code.
Order matters: Python checks except clauses top-to-bottom and stops
at the first match, so put MORE SPECIFIC exception types before more
GENERAL ones.
---------------------------------------------------------------------
"""

print("\n--- Catching Multiple Exception Types ---")

def safe_convert_and_scale(raw_value, scale_factor):
    try:
        value = int(raw_value)                    # ValueError: "abc" isn't a number
                                                    # TypeError: None has no int() conversion
        scaled = 100 / (value * scale_factor)      # ZeroDivisionError if value*scale_factor == 0
    except (TypeError, ValueError) as e:
        # both mean the SAME thing here: "the input itself was malformed" ->
        # same recovery, so one tuple-form except is cleaner than two copies
        print(f"  [except Type/ValueError] malformed input, skipping record: {e}")
        return None
    except ZeroDivisionError as e:
        # a DIFFERENT situation: the input was well-formed but produced an
        # undefined result -> different recovery (fall back to a default)
        print(f"  [except ZeroDivisionError] division collapsed, using default: {e}")
        return 0.0
    else:
        print(f"  [else] conversion succeeded cleanly -> {scaled}")
        return scaled

print("valid input:      ", safe_convert_and_scale("42", 1))
print("non-numeric input:", safe_convert_and_scale("abc", 1))
print("None input:       ", safe_convert_and_scale(None, 1))
print("zero collapse:    ", safe_convert_and_scale("0", 1))


"""
---------------------------------------------------------------------
3. THE EXCEPTION HIERARCHY: WHY except Exception IS USUALLY RIGHT,
   BUT A BARE except: IS DANGEROUS  ⭐⭐⭐
---------------------------------------------------------------------
Every exception in Python inherits from BaseException. `Exception`
is a SUBCLASS of BaseException that covers ordinary program errors.
But a handful of "control-flow signals" - KeyboardInterrupt (Ctrl+C),
SystemExit (sys.exit()), GeneratorExit - inherit directly from
BaseException, deliberately BYPASSING Exception, so that well-written
code catching `except Exception` lets them through untouched.

A bare `except:` catches EVERYTHING, including those signals - which
means a pipeline worker could swallow the operator's Ctrl+C, or
swallow the process's own clean-shutdown request, and just keep
looping. That's why `except Exception` is the correct "catch broadly"
tool, and bare `except:` should be avoided almost always.
---------------------------------------------------------------------
"""

print("\n--- The Exception Hierarchy ---")

for exc_cls in (BaseException, KeyboardInterrupt, SystemExit, Exception, ValueError, ZeroDivisionError):
    chain = " -> ".join(c.__name__ for c in exc_cls.__mro__)
    print(f"  {exc_cls.__name__:<16} MRO: {chain}")

print("\nNotice KeyboardInterrupt and SystemExit skip Exception entirely")
print("and inherit BaseException directly - 'except Exception' will")
print("NEVER catch them, by design.")

def flaky_step(should_interrupt):
    if should_interrupt:
        raise KeyboardInterrupt("simulated Ctrl+C during a pipeline run")
    raise ValueError("bad record encountered")

print("\nDANGEROUS: a bare except: swallows a simulated Ctrl+C")
try:
    flaky_step(should_interrupt=True)
except:                                          # noqa: bare except - shown deliberately as the ANTI-pattern
    print("  [bare except] caught EVERYTHING, including KeyboardInterrupt -")
    print("  in real code this would silently eat the operator's Ctrl+C!")

print("\nSAFER: except Exception correctly lets KeyboardInterrupt through")
try:
    try:
        flaky_step(should_interrupt=True)
    except Exception as e:
        print(f"  [except Exception] would NOT reach here for this signal")
except BaseException as e:
    # only present so THIS FILE keeps running to completion for the demo;
    # in a real script you'd simply let KeyboardInterrupt propagate to the top
    print(f"  [except BaseException, outer] correctly propagated: {type(e).__name__}: {e}")

print("\nexcept Exception STILL catches ordinary bugs just fine:")
try:
    flaky_step(should_interrupt=False)
except Exception as e:
    print(f"  [except Exception] caught normal error: {type(e).__name__}: {e}")


"""
---------------------------------------------------------------------
4. CUSTOM EXCEPTION CLASSES: A PIPELINE ERROR HIERARCHY  ⭐⭐⭐
---------------------------------------------------------------------
Relying on built-in exceptions (ValueError, KeyError...) for pipeline
errors forces callers to guess meaning from string messages. A small
CUSTOM exception hierarchy - one base class plus specific subclasses -
lets calling code catch EXACTLY the failure category it cares about,
attach structured context (which field, which source), and still
catch "anything from my pipeline" with one line via the base class.
---------------------------------------------------------------------
"""

print("\n--- Custom Exception Classes: A Pipeline Error Hierarchy ---")

class PipelineError(Exception):
    """Base class for every error this pipeline raises on purpose."""

class DataValidationError(PipelineError):
    """A record failed a data quality/shape check."""
    def __init__(self, message, *, field=None, value=None):
        super().__init__(message)
        self.field = field
        self.value = value

class SourceUnavailableError(PipelineError):
    """An upstream data source could not be reached at all."""
    def __init__(self, message, *, source=None):
        super().__init__(message)
        self.source = source

def validate_record(record):
    if "id" not in record:
        raise DataValidationError("record missing required 'id' field", field="id", value=record)
    return record

def fetch_from_source(source_name):
    if source_name == "warehouse_replica":
        raise SourceUnavailableError(f"source '{source_name}' did not respond", source=source_name)
    return {"id": 1, "source": source_name}

# selective handling: each subclass gets its OWN, appropriate recovery
for action in ("validate_bad", "fetch_down_source"):
    try:
        if action == "validate_bad":
            validate_record({"name": "no id here"})
        else:
            fetch_from_source("warehouse_replica")
    except DataValidationError as e:
        print(f"  [DataValidationError] field={e.field!r} -> skipping just this record: {e}")
    except SourceUnavailableError as e:
        print(f"  [SourceUnavailableError] source={e.source!r} -> retry/backoff instead of skipping: {e}")

# a genuinely unrelated bug (TypeError from OUR OWN code) still propagates
# normally - because it is NOT a PipelineError, `except PipelineError`
# would never mistakenly swallow it. That precision is the whole point.
try:
    validate_record({"id": 1})   # succeeds
    print("  valid record passed through untouched")
    1 / 0                        # unrelated real bug
except PipelineError as e:
    print(f"  [PipelineError] {e}")
except ZeroDivisionError as e:
    print(f"  [ZeroDivisionError] a REAL bug, correctly NOT mistaken for a pipeline data error: {e}")


"""
---------------------------------------------------------------------
5. EXCEPTION CHAINING: raise X from Y, __cause__ AND __context__  ⭐⭐⭐
---------------------------------------------------------------------
Raising a NEW exception from inside an except block never loses the
original one. Python always records it:
    - `raise NewError(...) from original_error`  sets NewError.__cause__
      to original_error EXPLICITLY - "this new error exists BECAUSE of
      that one". The traceback prints:
          "The above exception was the direct cause of the following
           exception:"
    - Raising a new exception INSIDE an except block WITHOUT `from`
      still sets NewError.__context__ to the original automatically -
      "this happened WHILE handling that one" (could be unrelated).
      The traceback prints:
          "During handling of the above exception, another exception
           occurred:"
    - `raise NewError(...) from None` explicitly SUPPRESSES the chain
      in the printed traceback (sets __suppress_context__).
---------------------------------------------------------------------
"""

print("\n--- Exception Chaining: raise X from Y ---")

def load_config_value(raw):
    try:
        return int(raw)
    except ValueError as e:
        # EXPLICIT chain: we know exactly why this failed
        raise DataValidationError(f"config value {raw!r} is not a valid integer") from e

try:
    load_config_value("not-a-number")
except DataValidationError as e:
    print(f"  caught: {e}")
    print(f"  __cause__:  {e.__cause__!r}")
    print(f"  __context__: {e.__context__!r}  (Python sets both when 'from' is used)")

def implicit_chain_demo():
    try:
        1 / 0
    except ZeroDivisionError:
        # no 'from' -> IMPLICIT chaining only: __cause__ stays None,
        # __context__ is still set automatically to the ZeroDivisionError
        raise PipelineError("failed while computing a derived metric")

print("\nFull traceback text for an IMPLICITLY chained exception -")
print("watch for the 'During handling of the above exception...' line:")
try:
    implicit_chain_demo()
except PipelineError:
    print(traceback.format_exc())

print("__cause__ for the implicit case is None (no explicit 'from'):")
try:
    implicit_chain_demo()
except PipelineError as e:
    print(f"  __cause__: {e.__cause__!r}, __context__: {type(e.__context__).__name__}")


"""
---------------------------------------------------------------------
6. RE-RAISING vs WRAPPING-AND-RAISING  ⭐⭐
---------------------------------------------------------------------
Bare `raise` (no arguments) inside an except block re-raises the
EXACT SAME exception object, with its ORIGINAL traceback intact -
use this when you only need to log/cleanup and the caller should see
the true underlying error type.

`raise NewType(...) from e` WRAPS it into a different, usually more
meaningful, type - use this when callers of YOUR function shouldn't
need to know (or catch) whatever low-level exception your
implementation happens to use internally.
---------------------------------------------------------------------
"""

print("\n--- Re-raising vs Wrapping-and-Raising ---")

def process_record_reraise(record):
    try:
        return record["value"] / record["divisor"]
    except KeyError:
        print("  [reraise] logging only, then re-raising the ORIGINAL exception type")
        raise

def process_record_wrap(record):
    try:
        return record["value"] / record["divisor"]
    except KeyError as e:
        print("  [wrap] converting a low-level KeyError into our own DataValidationError")
        raise DataValidationError(f"record missing required key: {e}") from e

bad_record = {"value": 10}   # missing "divisor"

try:
    process_record_reraise(bad_record)
except Exception as e:
    print(f"  caller sees ORIGINAL type unchanged: {type(e).__name__}: {e}")

try:
    process_record_wrap(bad_record)
except Exception as e:
    print(f"  caller sees OUR pipeline-specific type: {type(e).__name__}: {e}")
    print(f"  but the original is still reachable via __cause__: {type(e.__cause__).__name__}")


"""
---------------------------------------------------------------------
7. THE finally + return GOTCHA  ⭐
---------------------------------------------------------------------
A `return` (or `break`/`continue`) statement placed INSIDE a `finally`
block silently DISCARDS any exception that was in flight - the
exception simply never propagates. This is a real, subtle production
bug: someone "helpfully" adds a return in finally for an early exit
and unknowingly swallows every error the function could raise.
---------------------------------------------------------------------
"""

print("\n--- The finally + return Gotcha ---")

def buggy_finally():
    try:
        raise ValueError("this should propagate to the caller")
    finally:
        return "finally wins"   # DANGER: this swallows the ValueError completely

print("buggy_finally() returned:", buggy_finally())
print("The ValueError never reached us - 'return' inside finally ate it.")

def fixed_finally():
    try:
        raise ValueError("this correctly propagates")
    finally:
        print("  [finally] cleanup only - no return/break/continue here")

try:
    fixed_finally()
except ValueError as e:
    print(f"caught correctly after cleanup ran: {e}")


"""
---------------------------------------------------------------------
8. DATA ENGINEERING SCENARIO: PROCESSING A BATCH OF FILES WHERE ONE
   BAD FILE MUST NOT KILL THE WHOLE JOB  ⭐⭐⭐
---------------------------------------------------------------------
This is Interview Question #1 for this module: "how do you handle
exceptions in a data pipeline processing multiple files so one bad
file doesn't kill the whole job?" The pattern: put the try/except
INSIDE the loop (not around it), catch your OWN precise exception
type(s) plus a narrow safety-net for the truly unexpected, log and
`continue` past failures, then report a summary at the end.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Scenario: Batch File Processing ---")

# simulated "files" - a mix of valid and deliberately malformed content,
# standing in for files pulled from S3/a landing directory
incoming_files = [
    {"name": "orders_2026_08_20.json", "content": '{"order_id": 1, "amount": 99.5}'},
    {"name": "orders_2026_08_21.json", "content": '{"order_id": 2, "amount": "not-a-number"}'},
    {"name": "orders_2026_08_22.json", "content": '{"order_id": 3, "amount": 150.0}'},
    {"name": "orders_2026_08_23.json", "content": '{this is not valid json'},
    {"name": "orders_2026_08_24.json", "content": '{"amount": 42.0}'},
    {"name": "orders_2026_08_25.json", "content": '{"order_id": 6, "amount": -5.0}'},
]

def parse_order_file(name, content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise DataValidationError(f"{name}: not valid JSON") from e
    if "order_id" not in data:
        raise DataValidationError(f"{name}: missing 'order_id' field")
    if not isinstance(data.get("amount"), (int, float)):
        raise DataValidationError(f"{name}: 'amount' is not numeric (got {data.get('amount')!r})")
    if data["amount"] < 0:
        raise DataValidationError(f"{name}: 'amount' cannot be negative ({data['amount']})")
    return data

successes = []
failures = []

for file in incoming_files:
    try:
        record = parse_order_file(file["name"], file["content"])
    except DataValidationError as e:
        # a KNOWN, expected category of failure for a bad input file
        print(f"  [SKIP] {file['name']}: {e}")
        failures.append((file["name"], str(e)))
        continue                                  # <-- the key line: keep the loop alive
    except Exception as e:
        # narrow safety net for a truly unexpected bug elsewhere in
        # parse_order_file - still logged and skipped, never crashes the job
        print(f"  [SKIP-UNEXPECTED] {file['name']}: {type(e).__name__}: {e}")
        failures.append((file["name"], str(e)))
        continue
    else:
        successes.append(record)
        print(f"  [OK] {file['name']}: order_id={record['order_id']}, amount={record['amount']}")

print("\n--- Batch Summary ---")
print(f"  total files:  {len(incoming_files)}")
print(f"  succeeded:    {len(successes)}")
print(f"  failed:       {len(failures)}")
for name, reason in failures:
    print(f"    - {name}: {reason}")
print("\nThe job finished and reported results for ALL files, even")
print("though 4 of the 6 were malformed - that's the whole point.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
try                             -> code that might raise
except SpecificError:           -> handles ONLY that type (+ subclasses)
except (TypeA, TypeB):          -> same recovery for several types
else:                           -> runs ONLY if try raised NOTHING
finally:                        -> ALWAYS runs (even on re-raise/return)

except Exception:               -> safe catch-all (ordinary bugs)
except:  (bare)                 -> DANGEROUS - also catches
                                    KeyboardInterrupt / SystemExit
BaseException                   -> root of everything
  |-- KeyboardInterrupt, SystemExit  (control-flow signals, skip Exception)
  |-- Exception                      (ordinary errors - subclass THIS)
        |-- ValueError, KeyError, ZeroDivisionError, YourCustomError...

Custom hierarchy:
    class PipelineError(Exception): pass
    class DataValidationError(PipelineError): ...
    class SourceUnavailableError(PipelineError): ...
    -> catch narrow subclass for specific recovery, or PipelineError
       for "anything from my own pipeline", without swallowing
       unrelated real bugs.

raise NewErr(...) from e        -> EXPLICIT chain, sets __cause__
                                    ("...was the direct cause of...")
raise NewErr(...)  (in except)  -> IMPLICIT chain, sets __context__ only
                                    ("During handling of the above...")
raise NewErr(...) from None     -> suppresses the chain in the traceback
raise   (bare, in except)       -> re-raises ORIGINAL exception+traceback

Loop-over-files pattern -> try/except INSIDE the loop, catch known
error type(s) + narrow Exception safety net, log + `continue`, then
print a success/failure summary - one bad file never kills the job.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - EXCEPTION HANDLING
=====================================================================

1. How do you handle exceptions in a data pipeline that processes
   multiple files, so that one bad file doesn't kill the entire job?
   Walk through the `incoming_files` loop in this file.

2. What is the difference between `except Exception` and a bare
   `except:`? Why can a bare `except:` be dangerous in a long-running
   pipeline process?

3. Explain the order of execution in a full
   try/except/else/finally block. Under what condition does the
   `else` block run, and under what condition does it get skipped?

4. Does `finally` run if the `except` block itself re-raises the
   exception (as in `risky_operation` in Section 1)? Does it run if
   the try block has a bare `return` inside it?

5. What is wrong with `fixed_finally`'s buggy twin, `buggy_finally`,
   which puts a `return` statement inside `finally`? What actually
   happens to the `ValueError` it was supposed to raise?

6. When would you use the tuple form `except (TypeError, ValueError):`
   versus two separate `except` blocks for the same two exception
   types?

7. Design a small custom exception hierarchy for a data pipeline
   (like `PipelineError` / `DataValidationError` /
   `SourceUnavailableError` in this file). Why is this more useful
   to callers than raising bare `ValueError`/`ConnectionError`
   everywhere?

8. What does `raise NewError(...) from original_error` do that a
   plain `raise NewError(...)` inside an except block does not? Which
   attribute does each set - `__cause__` or `__context__`?

9. What text does Python print in a traceback for an EXPLICITLY
   chained exception (`from e`), versus an IMPLICITLY chained one
   (no `from`, but raised inside an except block)?

10. What does `raise SomeError(...) from None` do, and when might you
    want that?

11. What is the difference between a bare `raise` (no arguments) and
    `raise NewError(...) from e`? When would you choose re-raising
    the original over wrapping it in a new type?

12. Where does `KeyboardInterrupt` sit in the exception class
    hierarchy relative to `Exception` and `BaseException`? Why was it
    designed that way?

13. In `process_record_wrap`, after catching the wrapped
    `DataValidationError`, how would you get back to the ORIGINAL
    `KeyError` that caused it?

14. Why does the safety-net `except Exception` in the batch file loop
    (Section 8) still let a real bug like `KeyboardInterrupt` or
    `SystemExit` propagate out of the loop, instead of also
    swallowing those?

15. If `validate_record` in Section 4 raised a plain `TypeError` due
    to a genuine bug (not a data quality issue), would
    `except PipelineError:` catch it? Why does that matter for
    debugging?
=====================================================================
"""
