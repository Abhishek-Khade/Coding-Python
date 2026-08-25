"""
=====================================================================
LOGGING BEST PRACTICES - THE logging MODULE VS print() - Complete
Notes with Executable Examples
=====================================================================

Every real data pipeline eventually fails at 3am, unattended, on a
scheduler. The ONLY way you'll ever know what happened is whatever
you logged before it died. `print()` feels fine in a notebook or a
one-off script, but it has no idea of severity, no timestamp, no
routing, and no structure - it's just text on stdout.

The stdlib `logging` module fixes all of that with three cooperating
pieces:
    - a LOGGER      - the object your code calls (.info(), .error()...)
    - a HANDLER     - decides WHERE a record goes (console, file, ...)
    - a FORMATTER   - decides what the final text looks like

Each logger and handler has its own configurable SEVERITY THRESHOLD
(DEBUG < INFO < WARNING < ERROR < CRITICAL), so the exact same code,
completely unchanged, can be as chatty or as quiet as the environment
demands - verbose on your laptop, quiet in production, with errors
still reaching a file or a monitoring system either way.
=====================================================================
"""

import io
import json
import logging
import logging.handlers
import os
import shutil
import sys
import tempfile
import time

TEMP_DIR = tempfile.mkdtemp(prefix="logging_demo_")   # used by sections 3, 7, 8;
                                                        # removed at the end of section 8

print("--- Overview ---")
print("print() writes an unstructured string to stdout and nothing else.")
print("logging gives every message a severity, a timestamp, a source, and")
print("a configurable destination - without changing the call site at all.")


"""
---------------------------------------------------------------------
1. WHY print() IS INADEQUATE FOR PRODUCTION PIPELINES  ⭐⭐⭐
---------------------------------------------------------------------
"""

print("\n--- Why print() Is Inadequate for Production Pipelines ---")

def naive_extract_step():
    print("starting extract step")
    print("extracted 4820 rows")
    print("finished extract step")

naive_extract_step()
print("\nProblems with the output above, even though it 'works':")
print("  1. no timestamp   -> can't tell WHEN this ran or how long it took")
print("  2. no severity    -> an info line looks identical to a real error")
print("  3. no routing     -> always stdout; can't send errors to a file")
print("     while info stays on the console, with no code change")
print("  4. no volume knob -> silencing noise means deleting/commenting")
print("     out print() calls, one by one, by hand")
print("  5. no structure   -> it's a flat string, so a log-monitoring tool")
print("     (Splunk/CloudWatch/Datadog) has to REGEX-parse free text")
print("     instead of filtering on real fields")

# Same information, through logging: all five problems solved at once.
demo_logger = logging.getLogger("demo.print_vs_logging")
demo_logger.setLevel(logging.DEBUG)
demo_logger.propagate = False                       # don't also bubble to root
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
demo_logger.addHandler(_handler)

demo_logger.info("starting extract step")
demo_logger.info("extracted %d rows", 4820)   # %-style args: only formatted
                                                # if this record actually gets
                                                # emitted - cheap when suppressed
demo_logger.info("finished extract step")

print("\nSame information, through logging: real timestamps, a severity")
print("on every line, and a handler/formatter that can be swapped without")
print("touching the code that emits the message.")

demo_logger.handlers.clear()   # tidy up before later sections reuse similar names


"""
---------------------------------------------------------------------
2. SEVERITY LEVELS AND setLevel() - CONTROLLING WHAT ACTUALLY GETS
   EMITTED  ⭐⭐⭐
---------------------------------------------------------------------
The five standard levels, in increasing severity, with their integer
values: DEBUG (10) < INFO (20) < WARNING (30) < ERROR (40) <
CRITICAL (50). setLevel() sets a THRESHOLD - only records at or above
that value are actually emitted; everything below is dropped for
free, before any formatting or I/O happens.
---------------------------------------------------------------------
"""

print("\n--- Severity Levels and setLevel() Filtering the SAME Calls ---")

def emit_one_of_each(logger):
    """The exact same five calls every time - only the CONFIGURED level
    changes what actually gets through."""
    logger.debug("debug: raw row payload = %r", {"id": 1, "sku": "ABC"})
    logger.info("info: extracted batch of %d rows", 500)
    logger.warning("warning: 3 rows had a missing 'sku' field")
    logger.error("error: failed to connect to warehouse on attempt 1")
    logger.critical("critical: warehouse connection exhausted all retries")

def make_capturing_logger(name, level):
    """An isolated logger + in-memory handler, so we can print exactly what
    it captured without cluttering this file's real console output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger, buffer

print("\nconfigured at DEBUG (everything passes):")
debug_logger, debug_buffer = make_capturing_logger("demo.level_debug", logging.DEBUG)
emit_one_of_each(debug_logger)
print(debug_buffer.getvalue().rstrip())

print("\nSAME five calls, logger now configured at WARNING:")
warn_logger, warn_buffer = make_capturing_logger("demo.level_warning", logging.WARNING)
emit_one_of_each(warn_logger)
print(warn_buffer.getvalue().rstrip())

print("\nSAME five calls again, configured at CRITICAL:")
crit_logger, crit_buffer = make_capturing_logger("demo.level_critical", logging.CRITICAL)
emit_one_of_each(crit_logger)
print(crit_buffer.getvalue().rstrip())

print("\nnothing about emit_one_of_each() changed between the three runs -")
print("only logger.setLevel() did. Flip one setting and DEBUG-level noise")
print("disappears in production while WARNING+ still reaches whatever the")
print("handler is pointed at.")


"""
---------------------------------------------------------------------
3. THE THREE CORE PIECES: LOGGERS, HANDLERS, AND FORMATTERS  ⭐⭐⭐
---------------------------------------------------------------------
A LOGGER is the entry point your code calls. A HANDLER decides WHERE
a record goes. A FORMATTER decides what the final text looks like.
One logger can own MULTIPLE handlers, each with its OWN level and
its OWN formatter - the standard "console + file" pattern below.
---------------------------------------------------------------------
"""

print("\n--- The Three Core Pieces: Loggers, Handlers, Formatters ---")

pipeline_logger = logging.getLogger("etl.pipeline")
pipeline_logger.setLevel(logging.DEBUG)   # the logger's own gate: let
                                            # DEBUG+ through to its handlers
pipeline_logger.propagate = False

log_path = os.path.join(TEMP_DIR, "pipeline.log")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)     # console: INFO and above only
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.DEBUG)       # file: everything, for later audit
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)-8s %(name)s:%(lineno)d - %(message)s"))

pipeline_logger.addHandler(console_handler)
pipeline_logger.addHandler(file_handler)

print("\nemitting one call at each level - watch the console output below:")
pipeline_logger.debug("connecting to source database with pool size=5")
pipeline_logger.info("extract step started")
pipeline_logger.warning("retrying source query after a transient timeout")
pipeline_logger.error("load step failed to write partition 2026-08-25")

print("\n(the DEBUG line above did NOT appear on console - its handler is")
print("gated at INFO - but it WAS written to the file, because the file")
print("handler's own level is DEBUG. proof, by reading the file back:)")

with open(log_path) as f:
    file_contents = f.read()
print(file_contents.rstrip())

print("\nsame logger, same four calls, two different outcomes - filtering")
print("happens per-HANDLER, not just per-logger. A logger's setLevel() is")
print("the first gate; each handler can raise that bar further for its")
print("own destination.")

file_handler.close()
pipeline_logger.removeHandler(file_handler)   # release the file before section 8


"""
---------------------------------------------------------------------
4. logging.getLogger(__name__) AND THE ROOT LOGGER PITFALL  ⭐⭐⭐
---------------------------------------------------------------------
getLogger() is a REGISTRY lookup, not a constructor - calling it
twice with the SAME name returns the SAME object. Passing __name__
(the module's dotted import path) both tags every line with exactly
which module emitted it, and builds a naming HIERARCHY that child
loggers PROPAGATE up through, so one parent can be configured once.
---------------------------------------------------------------------
"""

print("\n--- logging.getLogger(__name__) and the Root Logger Pitfall ---")

same_a = logging.getLogger("etl.extract")
same_b = logging.getLogger("etl.extract")
print("logging.getLogger('etl.extract') is logging.getLogger('etl.extract'):",
      same_a is same_b)

print("\nthis is why real code writes `logger = logging.getLogger(__name__)`")
print("at module scope: __name__ becomes a dotted path like 'etl.extract',")
print("so every emitted line is automatically tagged with its source module")
print("via %(name)s, and 'etl' becomes the PARENT of 'etl.extract'.")

parent_logger = logging.getLogger("etl_hierarchy_demo")
child_logger = logging.getLogger("etl_hierarchy_demo.extract")   # simulates __name__

hierarchy_buffer = io.StringIO()
parent_handler = logging.StreamHandler(hierarchy_buffer)
parent_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
parent_logger.addHandler(parent_handler)
parent_logger.setLevel(logging.INFO)   # configured ONCE, on the parent...

child_logger.info("extracted batch from source")   # ...but this is the CHILD logger
print("\nchild_logger has no handler and no level of its own, yet its INFO")
print("message still reached the parent's handler, via PROPAGATION:")
print(hierarchy_buffer.getvalue().rstrip())

print("\nTHE PITFALL: skip getLogger(__name__) and call the module-level")
print("functions directly, and you're logging through the shared, global")
print("ROOT logger instead of your own:")

logging.info("this INFO message goes through the root logger")
print("(nothing printed above: the root logger's default level is WARNING,")
print("so this INFO call was silently dropped)")

logging.warning("this WARNING message also goes through the root logger")
print("^ that one printed, to stderr, in a bare default format - and as a")
print("SIDE EFFECT, the very first of these root-level calls silently")
print("attached a default handler to the ROOT logger (an implicit")
print("logging.basicConfig()) that every OTHER module in the process now")
print("shares too. Two unrelated modules both calling logging.error()")
print("end up fighting over the SAME global configuration - exactly what")
print("getLogger(__name__) avoids.")

logging.getLogger().handlers.clear()   # undo the implicit basicConfig so
                                         # later sections in this file start clean


"""
---------------------------------------------------------------------
5. logger.exception() - AUTOMATIC TRACEBACK CAPTURE  ⭐⭐
---------------------------------------------------------------------
Called from inside an `except` block, logger.exception() logs at
ERROR level AND automatically attaches the full traceback (it's
shorthand for logger.error(..., exc_info=True)) - no manual
traceback formatting required.
---------------------------------------------------------------------
"""

print("\n--- logger.exception(): Automatic Traceback Capture ---")

exc_logger = logging.getLogger("etl.transform")
exc_logger.setLevel(logging.DEBUG)
exc_logger.propagate = False
exc_buffer = io.StringIO()
exc_handler = logging.StreamHandler(exc_buffer)
exc_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
exc_logger.addHandler(exc_handler)

def parse_price(raw_value):
    return float(raw_value)   # raises ValueError on non-numeric input

print("the MANUAL way - logger.error() with the exception stringified:")
try:
    parse_price("N/A")
except ValueError as e:
    exc_logger.error("failed to parse price: %s", e)   # loses WHERE it failed
print(exc_buffer.getvalue().rstrip())
exc_buffer.truncate(0)
exc_buffer.seek(0)

print("\nthe IDIOMATIC way - logger.exception(), called only inside an")
print("except block, with the full traceback attached automatically:")
try:
    parse_price("N/A")
except ValueError:
    exc_logger.exception("failed to parse price")
print(exc_buffer.getvalue().rstrip())

print("\nthe second version shows the exact exception TYPE, the failing")
print("line, and the full call stack - everything you'd need to debug a")
print("scheduled job's failure after the fact, for the cost of one extra")
print("method name. (Calling .exception() outside an except block still")
print("runs, but with no active exception there's no traceback to attach.)")

exc_logger.removeHandler(exc_handler)


"""
---------------------------------------------------------------------
6. STRUCTURED / CONTEXTUAL LOGGING WITH extra={...}  ⭐⭐⭐
---------------------------------------------------------------------
Free-text log lines are fine for a human staring at a terminal, but
monitoring tools (Splunk, CloudWatch Logs Insights, Datadog) work far
better against real FIELDS they can filter/aggregate on. `extra={}`
attaches arbitrary fields to a LogRecord without touching the message
string - a formatter can then promote them into a structured line.
---------------------------------------------------------------------
"""

print("\n--- Structured/Contextual Logging: extra={...} and JSON Lines ---")

class JsonFormatter(logging.Formatter):
    """Renders each LogRecord as one JSON line, promoting any fields passed
    via extra={...} to top-level keys - the shape a log shipper
    (Filebeat/Fluentd/a CloudWatch agent) expects for structured ingestion."""

    # every attribute a plain LogRecord has by default, with NO extras -
    # anything else found on a record must have come from extra={...}
    _STANDARD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._STANDARD_KEYS:
                payload[key] = value   # promoted straight from extra={...}
        return json.dumps(payload)

structured_logger = logging.getLogger("etl.structured")
structured_logger.setLevel(logging.INFO)
structured_logger.propagate = False
json_handler = logging.StreamHandler(sys.stdout)
json_handler.setFormatter(JsonFormatter())
structured_logger.addHandler(json_handler)

print("\na plain message vs the same event with structured extra fields:")
structured_logger.info("pipeline batch finished")
structured_logger.info(
    "pipeline batch finished",
    extra={"run_id": "etl-2026-08-25-0300", "row_count": 4820, "duration_ms": 1523},
)

print("\nboth lines above are valid JSON - but only the second lets a")
print("downstream dashboard filter on 'duration_ms > 5000' or group by")
print("run_id, without ever parsing the human-readable message text.")

structured_logger.removeHandler(json_handler)


"""
---------------------------------------------------------------------
7. PRACTICAL USE CASE: LOGGING A SCHEDULED ETL JOB END-TO-END  ⭐⭐⭐
---------------------------------------------------------------------
This directly answers the classic interview prompt: "how would you
log and monitor failures in a scheduled Python ETL job?" The shape
below - a start log, per-step progress, per-record failures logged as
WARNING (so one bad row never kills the batch), and a final summary
log with counts - is the pattern a scheduler and a monitoring alert
can both key off of.
---------------------------------------------------------------------
"""

print("\n--- Practical Use Case: Logging a Scheduled ETL Job End-to-End ---")

job_logger = logging.getLogger("etl.scheduled_job")
job_logger.setLevel(logging.INFO)   # DEBUG-level detail gets suppressed here,
                                      # same "volume knob" as section 2
job_logger.propagate = False
job_handler = logging.StreamHandler(sys.stdout)
job_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
job_logger.addHandler(job_handler)

RAW_RECORDS = [
    {"sku": "WIDGET-1", "price": "19.99", "qty": 3},
    {"sku": "WIDGET-2", "price": "not_a_price", "qty": 1},   # bad price
    {"sku": "WIDGET-3", "price": "8.50", "qty": 2},
    {"sku": "WIDGET-4", "price": "12.00", "qty": "oops"},    # bad qty
    {"sku": "WIDGET-5", "price": "4.25", "qty": 10},
]

def run_pipeline(records, run_id):
    """Extract -> transform -> load, with logging at every stage that a
    scheduler or a monitoring rule could realistically act on."""
    start = time.perf_counter()
    job_logger.info("pipeline run started", extra={"run_id": run_id})
    job_logger.info("extract step: pulled %d raw records", len(records))

    loaded, failed = 0, 0
    for i, record in enumerate(records):
        try:
            price = float(record["price"])
            qty = int(record["qty"])
            total = round(price * qty, 2)
            job_logger.debug("row %d transformed ok: total=%s", i, total)   # filtered out at INFO
            loaded += 1
        except (ValueError, KeyError) as e:
            # a single malformed record must NEVER abort the whole
            # scheduled run - log it, count it, and keep going.
            job_logger.warning(
                "row %d skipped: %s (record=%r)", i, e, record,
                extra={"run_id": run_id, "row_index": i},
            )
            failed += 1
            continue

    job_logger.info("load step: wrote %d rows to the warehouse", loaded)

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    job_logger.info(
        "pipeline run finished: %d loaded, %d failed", loaded, failed,
        extra={
            "run_id": run_id,
            "row_count": loaded,
            "rows_failed": failed,
            "duration_ms": duration_ms,
        },
    )
    return loaded, failed

loaded_count, failed_count = run_pipeline(RAW_RECORDS, run_id="etl-2026-08-25-run7")

print(f"\nrun_pipeline() returned: loaded={loaded_count}, failed={failed_count}")
print("in production, that final summary line - with run_id, row_count,")
print("rows_failed, and duration_ms all in `extra` - is exactly what a")
print("monitoring rule ('page if rows_failed > 0 on three consecutive")
print("runs') would query on, on top of just eyeballing the console.")

job_logger.removeHandler(job_handler)


"""
---------------------------------------------------------------------
8. LOG ROTATION FOR LONG-RUNNING SCHEDULED JOBS  ⭐
---------------------------------------------------------------------
A job that runs daily/hourly forever will, given enough time, write
an unbounded log file. `logging.handlers` ships two handlers that
rotate automatically so that never happens: RotatingFileHandler
(size-based) and TimedRotatingFileHandler (schedule-based).
---------------------------------------------------------------------
"""

print("\n--- Log Rotation for Long-Running Scheduled Jobs ---")

print("RotatingFileHandler(path, maxBytes=..., backupCount=...)")
print("    -> rotates once the current file crosses maxBytes")
print("TimedRotatingFileHandler(path, when='midnight', backupCount=...)")
print("    -> rotates on a wall-clock schedule (hourly/daily/midnight/...)")

# in production, a daily scheduled ETL job would typically use:
#     handler = logging.handlers.TimedRotatingFileHandler(
#         "/var/log/etl/pipeline.log", when="midnight", backupCount=14)
# keeping 14 days of history and deleting anything older automatically.
# That's time-based, so it can't be triggered on demand here - instead we
# exercise the SIZE-based rotator below, which behaves identically in kind.

rotating_path = os.path.join(TEMP_DIR, "rotating.log")
rotating_handler = logging.handlers.RotatingFileHandler(
    rotating_path, maxBytes=200, backupCount=3)
rotating_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

rotation_logger = logging.getLogger("etl.rotation_demo")
rotation_logger.setLevel(logging.INFO)
rotation_logger.propagate = False
rotation_logger.addHandler(rotating_handler)

for i in range(40):
    rotation_logger.info("heartbeat message #%d from the scheduled job", i)

rotating_handler.close()
rotation_logger.removeHandler(rotating_handler)

rotated_files = sorted(name for name in os.listdir(TEMP_DIR) if name.startswith("rotating.log"))
print(f"\nafter 40 log lines with maxBytes=200, backupCount=3, the log")
print("directory now contains these files (old ones renamed automatically):")
for name in rotated_files:
    size = os.path.getsize(os.path.join(TEMP_DIR, name))
    print(f"  {name}  ({size} bytes)")
print("\nfiles beyond backupCount are deleted automatically - the log")
print("directory can never grow past a bounded size, which is exactly what")
print("a job running unattended for months needs.")

shutil.rmtree(TEMP_DIR, ignore_errors=True)   # this demo's tempdir is done
print(f"\ncleaned up temporary log directory: {TEMP_DIR}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
print()                        -> no level, no timestamp, no routing,
                                   no structure, always stdout
logging                        -> all of the above, configurable,
                                   without changing call sites

Severity levels (low -> high):
    DEBUG (10) -> INFO (20) -> WARNING (30) -> ERROR (40) -> CRITICAL (50)
logger.setLevel(X)             -> drop anything below X, for free

Three core pieces:
    logger      -> what your code calls (.info/.warning/.error/...)
    handler     -> WHERE a record goes (console/file/network/...)
    formatter   -> what the final text looks like
    one logger  -> many handlers, each with its OWN level/formatter

logger = logging.getLogger(__name__)
    -> tags every line with its source module (%(name)s)
    -> builds a hierarchy ("pkg.mod" propagates up to "pkg")
    -> avoids the shared, implicitly-configured ROOT logger

logger.exception("msg")        -> only inside except: ERROR + full
                                   traceback attached automatically

extra={"run_id": ..., "row_count": ..., "duration_ms": ...}
    -> attaches real fields a formatter can promote into JSON, for
       Splunk/CloudWatch/Datadog-style filtering and aggregation

Scheduled ETL job pattern:
    job start        -> INFO, with run_id
    per-step progress -> INFO ("extract step: pulled N records")
    per-record failure -> WARNING, caught, counted, loop continues
    job finish        -> INFO summary, extra={row_count, rows_failed,
                          duration_ms}

Log rotation (long-running scheduled jobs):
    RotatingFileHandler(path, maxBytes=, backupCount=)      -> size-based
    TimedRotatingFileHandler(path, when=, backupCount=)     -> time-based
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - LOGGING BEST PRACTICES
=====================================================================

1. Why is print() inadequate for logging in a real production data
   pipeline? Name at least three concrete limitations.

2. What are the five standard logging severity levels, in order, and
   their corresponding integer values?

3. What does logger.setLevel() actually control, and why is it a
   better "volume knob" than deleting or commenting out log
   statements to reduce noise?

4. Explain the three core pieces of the logging module - loggers,
   handlers, and formatters. What is each one responsible for?

5. In the `pipeline_logger` example, the SAME four log calls produced
   different output on the console than in the file. Why - and where
   in the configuration does that difference actually live?

6. Why is `logging.getLogger(__name__)` the standard idiom at the top
   of a module, instead of just calling `logging.info()` directly?

7. What happens the first time any module in a process calls
   `logging.debug()/info()/warning()` etc. with no handlers yet
   configured on the root logger? Why is this a hidden pitfall in a
   multi-module application?

8. What is logger propagation, and how did `child_logger` in this
   file end up logging through a handler it never directly attached?

9. What does `logger.exception()` do that `logger.error(str(e))`
   does not, and why must it be called from inside an `except` block
   to be useful?

10. How would you emit a structured (JSON) log line with fields like
    `run_id`, `row_count`, and `duration_ms` so a tool like
    Splunk/CloudWatch/Datadog could filter or aggregate on those
    fields directly, instead of parsing free text out of a message?

11. Walk through how you'd log and monitor failures in a scheduled
    Python ETL job end-to-end: what gets logged at job start, during
    per-record processing, and at job completion, and at what
    severity level each time?

12. In `run_pipeline()`, why is a single malformed record logged at
    WARNING and swallowed by a `try/except` instead of being allowed
    to raise and crash the whole batch? When WOULD you want a failure
    to propagate instead?

13. What problem does `RotatingFileHandler`/`TimedRotatingFileHandler`
    solve for a job that runs on a schedule indefinitely? What
    happens to files beyond `backupCount`?

14. If two different handlers are attached to the same logger with
    different `setLevel()` values, which one determines whether a
    given message is emitted, and why can a message that clears the
    logger's own level still be dropped by a handler?

15. What's the difference between `logging.basicConfig()` and
    manually building a logger with your own handlers and formatters,
    as this file does? Why might a library (as opposed to an
    application) avoid calling `basicConfig()` or attaching handlers
    of its own at all?
=====================================================================
"""
