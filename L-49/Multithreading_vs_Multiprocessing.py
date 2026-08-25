"""
=====================================================================
MULTITHREADING vs MULTIPROCESSING - Practical APIs & When to Use Each
=====================================================================

Python gives you two very different tools for "doing more than one
thing at a time," and picking the wrong one is a classic way to make
a data pipeline slower, not faster.

THREADS (the `threading` module) are lightweight, live inside ONE
process, and SHARE memory - all threads can see and mutate the same
Python objects directly. That sharing is convenient but dangerous:
without coordination, two threads can corrupt shared state (a "race
condition"). Threads are also all bound by the GIL (Global Interpreter
Lock) - a lock that lets only one thread execute Python bytecode at a
time. This file does NOT re-derive the GIL itself in depth; that lives
in its own dedicated notes file. What matters here, practically: the
GIL means threads do NOT give you a CPU speedup for pure-Python
number-crunching, but they DO give you a huge speedup for anything
that spends most of its time WAITING (network I/O, disk I/O, DB
calls) - because a waiting thread releases the GIL, letting another
thread run.

PROCESSES (the `multiprocessing` module) are heavier - each one is a
full separate copy of the Python interpreter, with its OWN memory
space and its OWN GIL. That means processes genuinely run Python
bytecode in true parallel across CPU cores, which is exactly what you
want for CPU-bound work (parsing, transforming, hashing, number
crunching). The cost: no shared memory (you must explicitly ship data
between processes, which means pickling it), plus real startup and
memory overhead per process.

The one-line rule data engineers live by:
    I/O-bound (waiting on network/disk/DB)  -> threads or asyncio
    CPU-bound (crunching numbers in Python)  -> multiprocessing

Note on structure: every multiprocessing call below is driven from a
`main()` function guarded by `if __name__ == "__main__":` at the
bottom of this file - required so that worker processes (which
re-import this module on spawn-based platforms) don't recursively
spawn more processes. All the top-level `def`s stay OUTSIDE main() on
purpose: a `multiprocessing.Pool`/`Process` target must be reachable
as a plain module-level function so it can be pickled and handed to
the worker process.
=====================================================================
"""

import threading
import multiprocessing as mp
import time
from concurrent.futures import ThreadPoolExecutor


# ---------------------------------------------------------------------
# Worker/target functions used throughout - defined at module level
# (not nested, not lambdas) so multiprocessing can pickle references
# to them when handing work to a separate process.
# ---------------------------------------------------------------------

def io_worker(name, delay):
    print(f"  [{name}] starting, will take {delay}s")
    time.sleep(delay)                      # stand-in for I/O wait (network/disk)
    print(f"  [{name}] done")


unsafe_counter = 0

def increment_unsafe(iterations):
    global unsafe_counter
    for _ in range(iterations):
        current = unsafe_counter        # READ
        time.sleep(0)                    # simulates real work happening between
        unsafe_counter = current + 1     # read and write - widens the race window
        # WITHOUT a lock, another thread can run its own READ+WRITE right in
        # this gap, and one of the two increments gets silently overwritten.


safe_counter = 0
counter_lock = threading.Lock()

def increment_safe(iterations):
    global safe_counter
    for _ in range(iterations):
        with counter_lock:              # only one thread executes this block at a time
            current = safe_counter
            time.sleep(0)                # even with the same artificial gap...
            safe_counter = current + 1   # ...the lock makes this whole sequence atomic
        # NOTE: acquiring/releasing a lock every iteration has real overhead - in
        # production you'd typically hold the lock for the smallest section
        # possible, or restructure to avoid shared mutable state entirely
        # (e.g. have each thread accumulate locally, then sum once at the end).


shared_looking_global = 0     # looks shared, but will NOT actually be shared across processes

def modify_global_in_child():
    global shared_looking_global
    shared_looking_global = 999          # only changes THIS process's own copy
    print(f"  [child process] value inside child is now: {shared_looking_global}")


def compute_and_report(record_id, queue):
    result = record_id * record_id          # pretend this is real per-record work
    queue.put((record_id, result))          # SERIALIZED and sent back to the parent


def transform_record(n):
    # stand-in for a real CPU-heavy per-record transformation
    # (e.g. parsing, hashing, or a numeric model applied to one row)
    total = 0
    for i in range(n):
        total += i * i
    return total


def fake_download(file_id):
    time.sleep(0.005)          # stand-in for real network latency per request
    return f"file_{file_id}.json"


def increment_by_one(n):
    # a plain module-level function because Pool workers must be able to
    # PICKLE the target - real lambdas/closures generally cannot be.
    return n + 1


def main():
    print("--- Overview ---")
    print("Threads share memory but fight over ONE GIL -> great for I/O-bound waiting.")
    print("Processes have separate memory and separate GILs -> great for CPU-bound crunching.")

    """
    -------------------------------------------------------------------
    1. BASIC threading.Thread: CREATE, START, JOIN  ⭐⭐
    -------------------------------------------------------------------
    The core threading API is just three calls: build a Thread pointing
    at a target function, `.start()` it (schedules it to run - does NOT
    block), then `.join()` it (blocks THIS thread until that one finishes).
    Forgetting `.join()` is a classic bug: the main program can exit (or
    move on) before background threads have finished their work.
    -------------------------------------------------------------------
    """
    print("\n--- Basic threading.Thread: create, start, join ---")

    start = time.perf_counter()
    threads = [
        threading.Thread(target=io_worker, args=("worker-A", 0.3)),
        threading.Thread(target=io_worker, args=("worker-B", 0.3)),
        threading.Thread(target=io_worker, args=("worker-C", 0.3)),
    ]
    for t in threads:
        t.start()          # each call returns immediately - threads run concurrently
    for t in threads:
        t.join()            # block here until ALL three have actually finished
    elapsed = time.perf_counter() - start

    print(f"all 3 workers finished in {elapsed:.2f}s (NOT ~0.9s - they overlapped)")
    print("if this were sequential (a plain loop calling io_worker() 3x), it would")
    print("take roughly 3 x 0.3s = 0.9s instead - threads overlap the WAITING time.")

    """
    -------------------------------------------------------------------
    2. THE RACE CONDITION: SHARED MUTABLE STATE WITHOUT A LOCK  ⭐⭐⭐
    -------------------------------------------------------------------
    Because threads share memory, two threads can both read the SAME
    value of a shared variable, both compute "value + 1" from that same
    stale reading, and both write back - so one of the two increments is
    silently LOST. This is the single most-asked concurrency bug in
    interviews.

    A subtlety worth knowing: in modern CPython, the GIL is only released
    at certain checkpoints (mainly around loop iterations and calls) -
    NOT literally between every single bytecode instruction. A bare tight
    loop doing `counter += 1` can sometimes go thousands of iterations
    without ever being interrupted mid-increment, making the bug look
    deceptively "safe" in a short demo. Real races bite because the gap
    between reading and writing shared state usually contains ACTUAL work
    (a computation, a DB round-trip, an API call) - which is exactly the
    kind of gap that gives another thread room to interleave. Below we
    insert a microscopic `time.sleep(0)` between the read and the write to
    reliably widen that gap and force the interleaving to happen every
    run, so the bug is guaranteed to show up here instead of being a
    matter of luck.
    -------------------------------------------------------------------
    """
    print("\n--- Race Condition: Unsynchronized Shared Counter ---")

    global unsafe_counter
    n_threads = 8
    iterations_per_thread = 2000
    expected_total = n_threads * iterations_per_thread

    race_threads = [
        threading.Thread(target=increment_unsafe, args=(iterations_per_thread,))
        for _ in range(n_threads)
    ]
    for t in race_threads:
        t.start()
    for t in race_threads:
        t.join()

    print(f"expected count: {expected_total}")
    print(f"ACTUAL count:   {unsafe_counter}   <-- WRONG! lost updates from the race")
    print(f"lost increments: {expected_total - unsafe_counter}")

    """
    -------------------------------------------------------------------
    3. THE FIX: threading.Lock  ⭐⭐⭐
    -------------------------------------------------------------------
    A `Lock` (mutex) guarantees only ONE thread at a time can be inside
    the critical section (the `with lock:` block). Any other thread that
    tries to enter simply blocks until the lock is released - turning the
    read-modify-write into a single atomic unit from every other thread's
    point of view.
    -------------------------------------------------------------------
    """
    print("\n--- Fixed with threading.Lock ---")

    global safe_counter
    safe_threads = [
        threading.Thread(target=increment_safe, args=(iterations_per_thread,))
        for _ in range(n_threads)
    ]
    for t in safe_threads:
        t.start()
    for t in safe_threads:
        t.join()

    print(f"expected count: {expected_total}")
    print(f"ACTUAL count:   {safe_counter}   <-- correct, every increment preserved")

    """
    -------------------------------------------------------------------
    4. BASIC multiprocessing.Process: SEPARATE MEMORY  ⭐⭐⭐
    -------------------------------------------------------------------
    `multiprocessing.Process` has the SAME create/start/join API shape as
    `Thread` - but under the hood it forks/spawns a whole new OS process
    with its OWN copy of the interpreter and its OWN memory. That means a
    "global" variable is NOT actually global across processes: the child
    gets its own independent COPY at the moment it starts, and any change
    it makes is invisible to the parent (and to any other child).
    -------------------------------------------------------------------
    """
    print("\n--- multiprocessing.Process: processes do NOT share memory ---")

    print(f"before starting child: {shared_looking_global}")
    p = mp.Process(target=modify_global_in_child)
    p.start()
    p.join()
    print(f"after child finished, PARENT's value is still: {shared_looking_global}")
    print("<-- unlike threads, the child's change never touched the parent's memory")

    """
    -------------------------------------------------------------------
    5. GETTING DATA BACK: multiprocessing.Queue  ⭐⭐⭐
    -------------------------------------------------------------------
    Since processes can't share memory, "returning" a result from a child
    process means explicitly SHIPPING it back via IPC (inter-process
    communication) - `multiprocessing.Queue` is the standard way. Every
    object you put on the queue gets PICKLED (serialized) by the sender
    and unpickled by the receiver - which is exactly why not everything
    can cross a process boundary (e.g. open file handles, DB connections,
    and lambdas generally cannot be pickled).

    `multiprocessing.Manager` is the other common tool - it gives you a
    proxy dict/list/Namespace that looks like a normal shared object but
    is actually backed by a background manager process handling the
    serialization for you. Queue is lighter and preferred for simple
    "worker computes a result, send it back" patterns like this one.
    -------------------------------------------------------------------
    """
    print("\n--- multiprocessing.Queue: the correct way to pass results back ---")

    result_queue = mp.Queue()
    procs = [
        mp.Process(target=compute_and_report, args=(i, result_queue))
        for i in range(4)
    ]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
    collected = sorted(result_queue.get() for _ in procs)
    print("results collected back in the parent process:", collected)

    """
    -------------------------------------------------------------------
    6. multiprocessing.Pool + .map(): EMBARRASSINGLY PARALLEL CPU WORK  ⭐⭐⭐
    -------------------------------------------------------------------
    `Pool` manages a fixed group of worker processes for you and `.map()`
    splits an iterable of inputs across them, collecting results IN ORDER
    - the multiprocessing equivalent of the builtin `map()`. This is the
    go-to tool for "embarrassingly parallel" CPU-bound work: the same
    pure computation applied independently to each item in a list, with
    no need for the items to talk to each other.
    -------------------------------------------------------------------
    """
    print("\n--- multiprocessing.Pool.map(): CPU-bound work across records ---")

    # "records" here just carries how much work each item requires
    records = [3_000_000] * 8

    start = time.perf_counter()
    sequential_results = [transform_record(n) for n in records]
    sequential_time = time.perf_counter() - start
    print(f"plain loop  (1 process):  {sequential_time:.2f}s")

    start = time.perf_counter()
    with mp.Pool(processes=mp.cpu_count()) as pool:
        pooled_results = pool.map(transform_record, records)
    pooled_time = time.perf_counter() - start
    print(f"Pool.map()  ({mp.cpu_count()} processes): {pooled_time:.2f}s")

    print(f"results match: {sequential_results == pooled_results}")
    print(f"measured speedup: {sequential_time / pooled_time:.2f}x "
          f"(this machine has {mp.cpu_count()} CPU cores)")

    """
    -------------------------------------------------------------------
    7. I/O-BOUND CASE STUDY: DOWNLOADING 1,000 FILES FROM AN API  ⭐⭐⭐
    -------------------------------------------------------------------
    This is a direct answer to the classic interview question "how would
    you parallelize downloading 1,000 files from an API?" Downloading is
    I/O-bound - almost all the wall-clock time is spent WAITING on the
    network, not doing CPU work in Python - which is precisely the case
    `concurrent.futures.ThreadPoolExecutor` is built for. It manages a
    pool of threads for you and `.map()` (or `.submit()` + `as_completed`)
    runs your function across many inputs concurrently.

    We simulate the "download" with `time.sleep()` standing in for network
    latency, so this runs standalone with no real network calls.
    -------------------------------------------------------------------
    """
    print("\n--- I/O-Bound: Downloading 1,000 Files with ThreadPoolExecutor ---")

    num_files = 1000

    start = time.perf_counter()
    sequential_downloads = [fake_download(i) for i in range(num_files)]
    sequential_download_time = time.perf_counter() - start
    print(f"sequential downloads: {sequential_download_time:.2f}s for {num_files} files")

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=50) as executor:
        # .map() preserves input order in the results, just like builtin map()
        threaded_downloads = list(executor.map(fake_download, range(num_files)))
    threaded_download_time = time.perf_counter() - start
    print(f"threaded downloads (50 workers): {threaded_download_time:.2f}s for {num_files} files")

    print(f"results match: {sequential_downloads == threaded_downloads}")
    print(f"speedup: {sequential_download_time / threaded_download_time:.1f}x faster")
    print("this works because each thread spends its time BLOCKED on I/O, and a")
    print("blocked thread releases the GIL - so 50 'downloads' really do overlap,")
    print("even though only one thread can run actual Python bytecode at once.")

    """
    -------------------------------------------------------------------
    8. DECISION TABLE: I/O-BOUND vs CPU-BOUND  ⭐⭐⭐
    -------------------------------------------------------------------
    """
    print("\n--- Decision Table ---")
    print("I/O-bound  -> threading / concurrent.futures.ThreadPoolExecutor / asyncio")
    print("   example: calling 50 REST APIs to enrich records - each call spends")
    print("   most of its time waiting on the network, not using the CPU.")
    print("CPU-bound  -> multiprocessing / concurrent.futures.ProcessPoolExecutor")
    print("   example: parsing and transforming 50 large files' worth of data with")
    print("   heavy per-row Python computation - the CPU is the bottleneck, and")
    print("   only separate processes can use multiple cores at once (the GIL")
    print("   blocks true parallel Python execution within a single process).")

    """
    -------------------------------------------------------------------
    9. "PROCESSES AREN'T FREE": OVERHEAD TRADEOFFS  ⭐⭐
    -------------------------------------------------------------------
    Multiprocessing's parallelism is real, but it isn't magic - it trades
    GIL contention for a different set of costs that can dominate for
    small or fine-grained work:

      - STARTUP COST: spawning a new OS process (and, on spawn-based
        platforms, re-importing your module in it) is much slower than
        spawning a thread - milliseconds to tens of milliseconds per
        process, versus near-instant for a thread.
      - MEMORY DUPLICATION: each process gets its own full copy of the
        interpreter and (depending on platform/start method) may copy or
        re-load significant chunks of memory - N processes can mean
        roughly N times the baseline memory footprint.
      - PICKLING COST: every argument going INTO a worker and every result
        coming back OUT must be pickled and unpickled. For small work
        items this serialization overhead can exceed the actual
        computation, making a Pool slower than a plain loop.

    Rule of thumb: multiprocessing wins when each unit of work is CPU-
    heavy enough that the computation time dwarfs the process/pickling
    overhead. For thousands of tiny CPU-bound tasks, batch them into
    fewer, larger chunks per worker (Pool's `chunksize` argument) instead
    of dispatching one process-call per item.
    -------------------------------------------------------------------
    """
    print("\n--- Processes Aren't Free ---")

    tiny_items = list(range(20))

    start = time.perf_counter()
    _ = [n + 1 for n in tiny_items]           # trivial CPU work, plain loop
    plain_time = time.perf_counter() - start

    start = time.perf_counter()
    with mp.Pool(processes=4) as pool:
        _ = pool.map(increment_by_one, tiny_items)  # same trivial work, via Pool
    pool_time = time.perf_counter() - start

    print(f"plain loop on 20 tiny items:  {plain_time:.5f}s")
    print(f"Pool.map() on 20 tiny items:  {pool_time:.5f}s")
    print("for work this small, process startup + pickling overhead dominates -")
    print("the 'parallel' version is SLOWER, not faster. Parallelize the work,")
    print("not the overhead: only reach for Pool once the per-item cost is real.")

    """
    ===================================================================
    QUICK REFERENCE
    ===================================================================
    threading.Thread(target=fn, args=(...))  -> .start() -> .join()
    multiprocessing.Process(target=fn, ...)  -> .start() -> .join()   (same shape!)

    Threads   -> share memory        -> need Lock for shared mutable state
    Processes -> separate memory     -> need Queue/Manager to pass data back

    Race condition -> unsynchronized read-modify-write on shared state loses
                      updates -> fix with threading.Lock (`with lock: ...`)

    Global var modified in a child process -> invisible to the parent
                      -> use multiprocessing.Queue (or Manager) to return results

    multiprocessing.Pool(processes=N).map(fn, items)
                      -> embarrassingly parallel CPU-bound work across items

    concurrent.futures.ThreadPoolExecutor(max_workers=N).map(fn, items)
                      -> embarrassingly parallel I/O-bound work (API calls,
                         file downloads, DB calls)

    I/O-bound (waiting)      -> threads / ThreadPoolExecutor / asyncio
    CPU-bound (crunching)    -> multiprocessing / ProcessPoolExecutor

    Processes aren't free -> process startup cost + memory duplication +
                              pickling cost of args/results in and out

    GIL details             -> see the dedicated GIL deep-dive notes file
    ===================================================================
    """
    print("\n--- Quick Reference (see comment block above) ---")


if __name__ == "__main__":
    main()


"""
=====================================================================
INTERVIEW QUESTIONS - MULTITHREADING vs MULTIPROCESSING
=====================================================================

1. What is the GIL, and how does it affect multithreading in Python?
   (high level only - see the dedicated GIL notes file for the deep
   dive on how the GIL itself works internally.)

2. When would you use multiprocessing over multithreading in a data
   pipeline? Give a concrete example.

3. How would you parallelize downloading 1,000 files from an API?
   Walk through why `ThreadPoolExecutor` is the right tool here rather
   than `multiprocessing.Pool`.

4. In this file's race condition demo, `unsafe_counter` ends up LOWER
   than the expected total. Explain exactly how two threads can each
   increment the counter yet the total only goes up by one.

5. Why does wrapping the read-modify-write in `with counter_lock:`
   fix the race condition from question 4? What is `Lock` actually
   guaranteeing?

6. Why does modifying `shared_looking_global` inside a child
   `multiprocessing.Process` NOT change its value in the parent
   process, when the equivalent code with `threading.Thread` WOULD
   affect the shared value?

7. What is `multiprocessing.Queue` used for, and why can't you just
   return a value normally from a function running in a separate
   process?

8. What does it mean for data passed to/from a `multiprocessing.Pool`
   worker to be "pickled"? What kinds of objects can't be pickled,
   and why does that matter when designing worker functions?

9. Why must multiprocessing code be guarded with
   `if __name__ == "__main__":`? What actually goes wrong without it?

10. Explain `asyncio` and where it fits alongside threads and
    processes for concurrent API/DB calls in a data pipeline.

11. Give a data engineering example of CPU-bound work that would
    benefit from `multiprocessing.Pool`, and a separate example of
    I/O-bound work that would benefit from `ThreadPoolExecutor`.
    Why would swapping the two choices hurt performance?

12. What overhead does `multiprocessing` introduce that `threading`
    does not? Under what conditions could using a `Pool` actually make
    a workload SLOWER than a plain sequential loop?

13. If you have 100 independent files to process where each file's
    processing is dominated by heavy pandas/numpy computation, would
    you reach for threads or processes? What if each file's
    processing were dominated by waiting on a slow network file
    system instead?

14. What is `multiprocessing.Manager`, and how does it differ from
    `multiprocessing.Queue` for sharing data between processes?

15. Why do blocked/waiting threads (e.g. during `time.sleep()` or a
    network call) let other Python threads make progress, while
    CPU-bound Python threads mostly cannot run truly in parallel?
=====================================================================
"""
