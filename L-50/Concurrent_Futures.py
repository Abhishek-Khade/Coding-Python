"""
=====================================================================
CONCURRENT.FUTURES - ThreadPoolExecutor & ProcessPoolExecutor as the
Modern Unified Concurrency API - Complete Notes with Executable Examples
=====================================================================

`concurrent.futures` is the HIGH-LEVEL concurrency API that sits on
top of raw `threading` and `multiprocessing`. (This file assumes you
already know the mechanics of raw `threading.Thread`,
`multiprocessing.Process`, locks, and the GIL itself - see the
Threading & Multiprocessing / GIL notes file for that depth. Here we
focus purely on the executor abstraction built on top of them.)

The problem it solves: `threading` and `multiprocessing` expose
DIFFERENT APIs for starting and coordinating work (`Thread` vs
`Process`, `Queue` vs `Queue`-that-pickles, different join/start
semantics), so switching a pipeline from threads to processes used to
mean rewriting real chunks of code. `concurrent.futures` gives you
ONE consistent interface - the `Executor` class, with `.submit()` and
`.map()` - implemented by BOTH `ThreadPoolExecutor` and
`ProcessPoolExecutor`. Write your concurrent code once against that
interface, and swapping the execution model (threads <-> processes)
is often a ONE-LINE change.

It also gives you a `Future` object for every submitted task - a
handle representing "a result that may not exist yet" - with a
critical, easy-to-miss behavior: if the worker function raises an
exception, that exception is CAPTURED by the Future and RE-RAISED in
the calling thread when you call `.result()`. This is a real
practical advantage over raw `threading.Thread`, where an uncaught
exception inside the target function just prints a traceback to
stderr and otherwise vanishes - the main thread never sees it and
your program can silently limp along on partial/missing data.
=====================================================================
"""

import random
import time
import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    ProcessPoolExecutor,
    as_completed,
    wait,
    FIRST_COMPLETED,
)

print("--- Overview ---")
print("concurrent.futures gives ThreadPoolExecutor and ProcessPoolExecutor")
print("the SAME .submit()/.map() interface, plus a Future object whose")
print(".result() blocks for (and re-raises exceptions from) a worker.")


"""
---------------------------------------------------------------------
1. WHY concurrent.futures EXISTS: ONE INTERFACE, TWO EXECUTION MODELS  ⭐⭐⭐
---------------------------------------------------------------------
Both executor classes implement the same `Executor` interface:
    submit(fn, *args, **kwargs) -> Future        (one call, async)
    map(fn, iterable)           -> results iter  (many calls, async)
    shutdown() / context manager support (`with ... as executor:`)

The function below is executed identically whether `make_executor()`
hands us a thread pool or a process pool - none of the calling code
below needs to know or care which one it got.
---------------------------------------------------------------------
"""

print("\n--- Why concurrent.futures Exists: One Interface, Two Models ---")

def double_it(n):
    return n * 2

def run_with_executor(executor_factory, label):
    # identical code path regardless of which Executor class we're given
    with executor_factory() as executor:
        results = list(executor.map(double_it, range(5)))
    print(f"{label}: {results}")

run_with_executor(lambda: ThreadPoolExecutor(max_workers=4), "ThreadPoolExecutor")
run_with_executor(lambda: ProcessPoolExecutor(max_workers=2), "ProcessPoolExecutor") \
    if __name__ == "__main__" else None

print("\nSame call shape (`executor.map(double_it, range(5))`) for both -")
print("compare that to raw threading.Thread vs multiprocessing.Process,")
print("which need genuinely different setup/join code for each.")


"""
---------------------------------------------------------------------
2. submit() AND THE Future OBJECT: .done() AND .result()  ⭐⭐⭐
---------------------------------------------------------------------
`.submit(fn, *args)` returns IMMEDIATELY with a `Future` - it does
NOT block waiting for the task to finish. The Future is a live handle
you can poll (`.done()`) or block on (`.result()`, which waits until
the task finishes and then returns its return value).
---------------------------------------------------------------------
"""

print("\n--- submit() and the Future Object ---")

def slow_task(seconds, label):
    time.sleep(seconds)
    return f"{label} finished after {seconds}s"

with ThreadPoolExecutor(max_workers=2) as executor:
    future = executor.submit(slow_task, 0.3, "task-A")
    print("immediately after submit(), future.done():", future.done())  # almost certainly False
    print("submit() did NOT block - this line ran right away.")

    result = future.result()   # BLOCKS here until slow_task() actually returns
    print("future.result():", result)
    print("after result(), future.done():", future.done())              # now True


"""
---------------------------------------------------------------------
3. EXCEPTIONS INSIDE WORKERS: .result() RE-RAISES THEM  ⭐⭐⭐
---------------------------------------------------------------------
This is the single most useful (and most commonly missed) behavior
difference vs raw threading. If the callable passed to `.submit()`
raises, the Future stores that exception object. Calling `.result()`
on it RE-RAISES the exact same exception, IN THE CALLING THREAD -
so you can catch it with a normal try/except right where you're
already reading results, no extra plumbing required.

Contrast that with a raw `threading.Thread`: if its target raises,
Python prints a traceback to stderr from a machinery-level exception
hook and then just... moves on. The main thread's own try/except
CANNOT catch it, because the exception never crosses the thread
boundary - it happened in a different call stack entirely.
---------------------------------------------------------------------
"""

print("\n--- Exceptions Inside Workers: result() Re-Raises Them ---")

def risky_division(a, b):
    return a / b

# --- Contrast case: raw threading.Thread SWALLOWS the exception ---
print("Raw threading.Thread version (exception goes into the void):")
thread = threading.Thread(target=risky_division, args=(10, 0))
thread.start()
thread.join()   # join() does NOT re-raise the worker's exception
print("main thread reached this line just fine - notice the ZeroDivisionError")
print("traceback above (printed by Python's default thread excepthook) never")
print("became a Python exception object the main thread could catch.")
try:
    pass  # there's nothing to catch - the exception already vanished above
except ZeroDivisionError:
    print("this will NEVER print")

# --- concurrent.futures version: the SAME exception, but recoverable ---
print("\nThreadPoolExecutor version (exception is captured and re-raised):")
with ThreadPoolExecutor(max_workers=2) as executor:
    good_future = executor.submit(risky_division, 10, 2)
    bad_future = executor.submit(risky_division, 10, 0)

    print("good_future.result():", good_future.result())
    try:
        bad_future.result()   # re-raises ZeroDivisionError HERE, in main thread
    except ZeroDivisionError as e:
        print("caught cleanly via future.result():", e)

    # .exception() is the non-raising equivalent - returns the exception
    # object (or None) instead of raising it
    print("bad_future.exception():", repr(bad_future.exception()))


"""
---------------------------------------------------------------------
4. .map() - APPLY A FUNCTION ACROSS MANY ITEMS, ORDER PRESERVED  ⭐⭐
---------------------------------------------------------------------
`executor.map(fn, iterable)` is the concurrent equivalent of the
built-in `map()`: it submits every item concurrently, but the
RESULTS come back in the SAME ORDER as the input, regardless of which
task actually finished first internally. This makes it the natural
choice whenever you need "apply this to every item" and care about
matching results back up to their inputs positionally.
---------------------------------------------------------------------
"""

print("\n--- map(): Concurrent Apply, Input Order Preserved ---")

def fetch_length(url):
    # stand-in for an I/O-bound call (e.g. an HTTP request) - see
    # section 8 below for a fuller, failure-tolerant version of this
    time.sleep(random.uniform(0.02, 0.1))
    return len(url)

urls = [
    "https://pattern.com/products",
    "https://pattern.com/orders",
    "https://pattern.com/inventory/skus",
    "https://pattern.com/a",
]

with ThreadPoolExecutor(max_workers=4) as executor:
    lengths = list(executor.map(fetch_length, urls))

print("urls:   ", urls)
print("lengths:", lengths)
print("lengths[i] always corresponds to urls[i], no matter which finished first.")


"""
---------------------------------------------------------------------
5. as_completed() - PROCESS RESULTS AS SOON AS THEY FINISH  ⭐⭐⭐
---------------------------------------------------------------------
`.map()` is great when you want order preserved, but it forces you to
wait for results IN SUBMISSION ORDER even if a later task finishes
first. `as_completed(futures)` instead yields each Future the moment
IT finishes, in COMPLETION order - ideal when you want to start
handling/logging results as soon as they're ready (e.g. a live
progress display, or triggering downstream work per-item instead of
waiting for the slowest task in the batch).
---------------------------------------------------------------------
"""

print("\n--- as_completed(): Results in Completion Order, Not Submission Order ---")

def simulate_api_call(name, delay):
    time.sleep(delay)   # varying "network latency"
    return f"{name} responded"

# deliberately-varied delays so submission order != completion order
calls = [("call-A", 0.30), ("call-B", 0.05), ("call-C", 0.20), ("call-D", 0.10)]

with ThreadPoolExecutor(max_workers=4) as executor:
    future_to_name = {
        executor.submit(simulate_api_call, name, delay): name
        for name, delay in calls
    }
    print("submitted in order:", [name for name, _ in calls])
    print("processing as each one finishes:")
    for future in as_completed(future_to_name):
        name = future_to_name[future]
        print(f"  {name} finished -> {future.result()}")

print("\nnotice call-B (shortest delay) is handled FIRST above, even though")
print("call-A was SUBMITTED first - that's the whole point of as_completed().")
print("Compare to section 4's map(), which would have forced call-A's result")
print("to be yielded first regardless of how long it actually took.")


"""
---------------------------------------------------------------------
6. ProcessPoolExecutor FOR CPU-BOUND WORK: SAME SHAPE, DIFFERENT ENGINE  ⭐⭐⭐
---------------------------------------------------------------------
For CPU-bound work, threads don't help (the GIL serializes Python
bytecode execution across threads in one process - see the
Threading/GIL notes file for why). `ProcessPoolExecutor` runs each
task in its own separate OS process, each with its own interpreter
and its own GIL, so CPU-bound work genuinely runs in parallel across
cores. The code shape is IDENTICAL to ThreadPoolExecutor - only the
class name changes.

Two hard requirements this example must respect:
    - the worker function must be defined at MODULE level (not
      nested), because arguments/results are PICKLED to cross the
      process boundary, and pickle can't serialize local functions
    - the code that CREATES the process pool must be guarded by
      `if __name__ == "__main__":`, so child processes that re-import
      this module (on platforms using the "spawn" start method)
      don't try to recursively spawn their own pools
---------------------------------------------------------------------
"""

print("\n--- ProcessPoolExecutor for CPU-Bound Work ---")

def cpu_intensive_task(n):
    # a genuinely CPU-bound loop - no I/O, no sleep
    total = 0
    for i in range(n):
        total += i * i
    return total

def run_cpu_bound_comparison():
    workloads = [2_000_000] * 4

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        thread_results = list(executor.map(cpu_intensive_task, workloads))
    thread_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as executor:
        process_results = list(executor.map(cpu_intensive_task, workloads))
    process_elapsed = time.perf_counter() - start

    print("ThreadPoolExecutor results:", thread_results)
    print("ProcessPoolExecutor results:", process_results)
    print(f"thread pool elapsed:  {thread_elapsed:.3f}s  (GIL limits this to ~1 core)")
    print(f"process pool elapsed: {process_elapsed:.3f}s  (real parallelism across cores,")
    print("                       though small workloads can be dominated by process")
    print("                       start-up overhead - the win grows with bigger tasks)")

if __name__ == "__main__":
    run_cpu_bound_comparison()


"""
---------------------------------------------------------------------
7. max_workers, wait(), AND CANCELLATION  ⭐⭐
---------------------------------------------------------------------
`max_workers` caps how many tasks run concurrently - important for
not overwhelming a downstream API, a database, or the machine's own
CPU/memory. `wait(futures, timeout=..., return_when=...)` is a lower
-level tool than as_completed() when you need to react to "at least
one is done" without necessarily consuming results yet. And
`future.cancel()` can cancel a task that HASN'T started running yet
(once it's running, cancel() returns False - you can't interrupt
work already in progress).
---------------------------------------------------------------------
"""

print("\n--- max_workers, wait(), and Cancellation ---")

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(slow_task, 0.15, f"job-{i}") for i in range(4)]

    done, not_done = wait(futures, timeout=0.1, return_when=FIRST_COMPLETED)
    print(f"after a short 0.1s wait(): {len(done)} done, {len(not_done)} still pending")

    # with only 2 workers, jobs 2 and 3 haven't even STARTED yet - cancel one
    cancelled = futures[-1].cancel()
    print(f"cancelling the last-queued future succeeded: {cancelled}")

# the `with` block's __exit__ calls shutdown(wait=True), so by the time we're
# here every non-cancelled future has already completed
print("remaining results:", [f.result() for f in futures if not f.cancelled()])


"""
---------------------------------------------------------------------
8. DATA ENGINEERING USE CASE: PARTIAL-FAILURE-TOLERANT ETL BATCH  ⭐⭐⭐
---------------------------------------------------------------------
A very common ETL shape: you have N files (or API pages, or S3 keys)
to fetch/process, I/O latency dominates each one (so threads are the
right tool, not processes), you want to cap concurrency so you don't
hammer the source system, and ONE bad file must NOT kill the whole
batch job (straight out of Module 5's "how do you handle exceptions
in a pipeline processing multiple files" question). We combine
`max_workers`, `as_completed()`, and per-future try/except to build
exactly that.
---------------------------------------------------------------------
"""

print("\n--- ETL Use Case: Partial-Failure-Tolerant Batch File Processing ---")

def process_file(file_id):
    # simulated I/O-bound "fetch + parse" step
    time.sleep(random.uniform(0.02, 0.08))
    if file_id in (3, 7):
        raise ValueError(f"file_{file_id}.csv is corrupt (bad row 42)")
    return {"file_id": file_id, "rows_loaded": 100 + file_id * 10}

file_ids = list(range(10))
succeeded, failed = [], []

with ThreadPoolExecutor(max_workers=4) as executor:   # cap concurrency at 4
    future_to_file = {executor.submit(process_file, fid): fid for fid in file_ids}

    for future in as_completed(future_to_file):
        file_id = future_to_file[future]
        try:
            record = future.result()
            succeeded.append(record)
            print(f"  file_{file_id}: OK -> {record['rows_loaded']} rows loaded")
        except ValueError as e:
            failed.append(file_id)
            print(f"  file_{file_id}: FAILED -> {e}")

print(f"\nbatch complete: {len(succeeded)} succeeded, {len(failed)} failed {failed}")
print("the whole job finished and reported EXACTLY which files need a retry -")
print("one bad file never took down the other nine.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Why it exists  -> ONE Executor interface (submit/map) implemented by
                  BOTH ThreadPoolExecutor and ProcessPoolExecutor;
                  swap the class name, keep the rest of the code

executor.submit(fn, *args)   -> returns a Future immediately (non-blocking)
future.done()                -> True/False, non-blocking poll
future.result()              -> BLOCKS until finished; returns the value;
                                 RE-RAISES the worker's exception here
future.exception()           -> like result() but returns the exception
                                 object instead of raising (or None)

Raw threading.Thread          -> uncaught exception in target just prints
                                  a traceback and VANISHES; join() does
                                  NOT re-raise it to the caller

executor.map(fn, iterable)    -> concurrent apply, results in INPUT order
as_completed(futures)         -> yields futures in COMPLETION order, as
                                  soon as each one finishes

ThreadPoolExecutor            -> I/O-bound work (network, disk, DB calls);
                                  limited by the GIL for CPU-bound code
ProcessPoolExecutor           -> CPU-bound work; separate processes, real
                                  parallel cores; args/results must be
                                  picklable; guard creation with
                                  `if __name__ == "__main__":`

max_workers=N                 -> caps concurrency (protects downstream
                                  systems / the machine itself)
wait(futures, timeout=, return_when=) -> lower-level than as_completed();
                                  react to "at least one done" without
                                  consuming results
future.cancel()                -> True only if the task hasn't STARTED yet

ETL pattern: max_workers cap + as_completed() + per-future try/except
             -> partial-failure-tolerant batch processing
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CONCURRENT.FUTURES
=====================================================================

1. What problem does `concurrent.futures` solve that raw `threading`
   and `multiprocessing` don't? What specifically stays the same in
   your code when you swap `ThreadPoolExecutor` for
   `ProcessPoolExecutor`?

2. What does `executor.submit()` return, and why doesn't calling it
   block the calling thread?

3. What does `future.result()` do if the task isn't finished yet? What
   does it do if the worker function raised an exception - be
   specific about WHERE that exception gets raised.

4. In this file's raw `threading.Thread` example, `risky_division(10, 0)`
   raises `ZeroDivisionError` inside the worker thread, yet the
   surrounding `try/except` in the main thread never catches it. Why
   not, and what does `thread.join()` actually wait for if not that?

5. What is the difference between `future.result()` and
   `future.exception()`?

6. Explain the difference between `executor.map(fn, items)` and
   `as_completed(futures)` in terms of the ORDER results become
   available. When would you prefer one over the other?

7. In the `as_completed()` example (`call-A` through `call-D` with
   different simulated delays), why does `call-B` get processed first
   in the loop even though `call-A` was submitted first?

8. Why must a function passed to `ProcessPoolExecutor.submit()` or
   `.map()` be defined at module level rather than as a nested/local
   function or a lambda?

9. Why do we wrap `ProcessPoolExecutor` usage in
   `if __name__ == "__main__":`? What could go wrong on platforms that
   use the "spawn" process start method if we didn't?

10. Given identical code using `.map()` over the same CPU-bound
    function, why would `ProcessPoolExecutor` typically outperform
    `ThreadPoolExecutor` for that workload, but NOT necessarily for an
    I/O-bound workload like the `simulate_api_call` example?

11. What does `max_workers` control, and why would you deliberately
    cap it low (e.g. 4) rather than submitting all N tasks with an
    unbounded pool?

12. In the ETL batch example, `file_3` and `file_7` raise
    `ValueError`. Walk through exactly what happens to the batch job
    as a whole - does one failing file stop the other files from
    being processed? How does the code know which files need a
    retry afterward?

13. What does `future.cancel()` return if the task has already started
    running? Why can't you cancel work that's already in progress?

14. When would you reach for `wait()` with `return_when=FIRST_COMPLETED`
    instead of `as_completed()`?

15. In a data engineering context, how would you decide whether a
    parallelizable task (e.g. "download 1,000 files from an API" vs
    "compute a hash over 1,000 large in-memory arrays") should use
    `ThreadPoolExecutor` or `ProcessPoolExecutor`?
=====================================================================
"""
