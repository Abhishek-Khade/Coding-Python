"""
=====================================================================
THE GLOBAL INTERPRETER LOCK (GIL) - Complete Notes with Executable
Examples
=====================================================================

The GIL is a single MUTEX (lock) inside the CPython interpreter that
allows only ONE thread to execute Python BYTECODE at any given
instant, no matter how many OS threads exist and no matter how many
CPU cores the machine has. If you spin up eight threads on an
eight-core machine, only one of them is ever actually running Python
code at a time - the rest are waiting for the lock.

This is a CPython implementation detail, not a rule of the Python
LANGUAGE itself. Other implementations (Jython, IronPython) don't
have it, and CPython 3.13+ ships an experimental "free-threaded"
build without it (see section 7). But for essentially every
production Python you will touch in a Data Engineering job, "Python"
means CPython-with-a-GIL, so this is the behavior that matters.

WHY does it exist? CPython manages memory largely through REFERENCE
COUNTING - every object carries a counter of how many references
point to it, and when that counter hits zero the object is freed
immediately. Incrementing/decrementing that counter has to be
thread-safe, or two threads could race on it and either corrupt
memory or leak/double-free an object. The GIL solves this with ONE
big, simple lock around the whole interpreter loop, instead of
requiring a separate fine-grained lock on every single object's
refcount (which is what a "free-threaded" build has to add back in,
at a real performance and complexity cost - see section 7).

The single most important practical consequence, and the crux of
this whole topic: the GIL makes `threading` USELESS for speeding up
CPU-bound pure-Python work, but it does NOT make `threading` useless
in general - it is released during blocking I/O, so threads are
still genuinely useful for I/O-bound work (network calls, disk
reads, DB queries). `multiprocessing` sidesteps the GIL entirely by
using separate OS processes, each with its own interpreter and its
own GIL. This file proves all three claims with real, measured
benchmarks.
=====================================================================
"""

import time
import threading
from multiprocessing import Pool
import os

print("--- Overview ---")
print("The GIL lets only ONE thread run Python bytecode at a time in CPython.")
print("-> threads do NOT speed up CPU-bound Python code.")
print("-> threads DO speed up I/O-bound code (GIL is released during waits).")
print("-> multiprocessing sidesteps the GIL with separate processes/interpreters.")


"""
---------------------------------------------------------------------
1. WHAT THE GIL ACTUALLY IS  ⭐⭐⭐
---------------------------------------------------------------------
The GIL is a mutex owned by the CPython interpreter itself (not by
your code). Every Python thread must HOLD the GIL to execute any
Python bytecode instruction. CPython periodically forces a thread
to release the GIL (by default, roughly every 5ms of continuous
execution, controlled by sys.getswitchinterval()) so other waiting
threads get a turn - this is called a "context switch", and it's
cooperative in the sense that it happens at bytecode-instruction
boundaries, not truly in parallel.
---------------------------------------------------------------------
"""

print("\n--- What the GIL Actually Is ---")

print("sys.getswitchinterval():", __import__("sys").getswitchinterval(), "seconds")
print("This is how often CPython asks a running thread to release the GIL")
print("so another waiting thread gets a chance to run.")

# Even though we can create many OS-level threads, they take turns holding
# the ONE global lock - they are never simultaneously executing bytecode.
def report_thread_activity(label):
    print(f"  [{label}] running on thread: {threading.current_thread().name}")

threads = [threading.Thread(target=report_thread_activity, args=(f"t{i}",)) for i in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print("All three threads ran - but at any given instant, only ONE of them")
print("was actually holding the GIL and executing Python bytecode.")


"""
---------------------------------------------------------------------
2. WHY THE GIL EXISTS: REFERENCE COUNTING  ⭐⭐⭐
---------------------------------------------------------------------
CPython frees memory via REFERENCE COUNTING: every object has a
hidden counter (sys.getrefcount) of how many things point to it, and
it's deallocated the instant that count hits zero. If two threads
could increment/decrement the SAME object's refcount at the exact
same time without protection, you'd get a race condition - possibly
freeing an object that's still in use (a crash), or leaking one that
never gets freed. The GIL sidesteps needing a separate lock on every
single object by using ONE lock for the whole interpreter - simple
and fast for single-threaded code, at the cost of no real
multi-core parallelism for pure-Python bytecode.
---------------------------------------------------------------------
"""

print("\n--- Why the GIL Exists: Reference Counting ---")

import sys

shared_list = [1, 2, 3]
print("refcount of shared_list before any new reference:", sys.getrefcount(shared_list))

another_reference = shared_list
print("refcount after 'another_reference = shared_list':", sys.getrefcount(shared_list))

del another_reference
print("refcount after deleting that reference:", sys.getrefcount(shared_list))

print("\nEvery one of those +1/-1 operations happens on EVERY object, EVERY")
print("time it's referenced or dereferenced, all over the interpreter -")
print("constantly, even in single-threaded code. Making each one individually")
print("thread-safe (a lock per object) would be slow and enormously complex.")
print("One global lock around bytecode execution was CPython's original,")
print("pragmatic trade-off: simpler, faster for the common single-threaded")
print("case, at the cost of true CPU parallelism within one process.")


"""
---------------------------------------------------------------------
3. PROOF: THREADING GIVES NO SPEEDUP FOR CPU-BOUND WORK  ⭐⭐⭐
---------------------------------------------------------------------
Here is the real, measured benchmark. We define a pure-Python
CPU-bound function (a tight counting loop - no I/O, no library calls
that might release the GIL) and compare:
    (a) running it N_TASKS times back-to-back on ONE thread
    (b) running it N_TASKS times concurrently across N_TASKS threads
If the GIL truly serializes bytecode execution, (a) and (b) should
take roughly the SAME wall-clock time - NOT 1/N_TASKS the time, even
though this machine has multiple cores and N_TASKS threads are all
"running".
---------------------------------------------------------------------
"""

print("\n--- Proof: No Threading Speedup for CPU-Bound Work ---")

def cpu_bound_count(n):
    """Pure-Python busy work: no I/O, nothing that releases the GIL."""
    count = 0
    for _ in range(n):
        count += 1
    return count

ITERATIONS = 10_000_000
N_TASKS = 4
print(f"cpu_count() on this machine: {os.cpu_count()}")
print(f"workload: {N_TASKS} tasks x {ITERATIONS:,} increments each\n")

# (a) Sequential: one thread does all the work, one task after another
start = time.perf_counter()
for _ in range(N_TASKS):
    cpu_bound_count(ITERATIONS)
sequential_time = time.perf_counter() - start
print(f"single-threaded (sequential): {sequential_time:.3f}s")

# (b) Threaded: N_TASKS threads, each doing one task, "concurrently"
start = time.perf_counter()
cpu_threads = [threading.Thread(target=cpu_bound_count, args=(ITERATIONS,)) for _ in range(N_TASKS)]
for t in cpu_threads:
    t.start()
for t in cpu_threads:
    t.join()
threaded_time = time.perf_counter() - start
print(f"multi-threaded ({N_TASKS} threads):  {threaded_time:.3f}s")

speedup = sequential_time / threaded_time
print(f"\nmeasured speedup from threading: {speedup:.2f}x")
print(f"(a 'real' {N_TASKS}-way parallel speedup would be close to {N_TASKS:.1f}x)")
if speedup < 1.5:
    print("-> Confirmed: threading gave essentially NO speedup for CPU-bound")
    print("   work, despite using multiple threads and multiple cores being")
    print("   available. The GIL forced the threads to take turns, so total")
    print("   CPU work done was still serialized onto roughly one core.")


"""
---------------------------------------------------------------------
4. WHY I/O-BOUND THREADING STILL WORKS: THE GIL IS *RELEASED*
   DURING BLOCKING I/O  ⭐⭐⭐
---------------------------------------------------------------------
This is the crux of the "does the GIL make threading pointless"
question - and the answer is NO. CPython's GIL is released
EXPLICITLY around any operation that blocks waiting on something
outside the interpreter: file reads, socket/network calls, and
`time.sleep()`. The C code implementing these calls releases the GIL
before blocking, lets OTHER Python threads run during the wait, and
re-acquires the GIL only once the blocking call returns and Python
bytecode needs to run again. So while one thread is "waiting" (for a
network response, a disk read, or a sleep timer), the GIL sits idle
and available - other threads can make full, real progress. That's
why threading is still an excellent tool for I/O-bound work like
concurrent API calls or DB queries, even in GIL-locked CPython.

We use `time.sleep()` here as an honest stand-in for real network/
disk latency - the mechanism (GIL released while blocked) is
IDENTICAL to what happens during a real `requests.get(...)` call or
a socket read.
---------------------------------------------------------------------
"""

print("\n--- Proof: Threading DOES Help for I/O-Bound Work ---")

def io_bound_task(duration):
    """Stands in for a network/disk wait - e.g. requests.get(url) or a
    DB query. The GIL is released for the duration of the sleep, exactly
    as it is released during any real blocking I/O call in CPython."""
    time.sleep(duration)

SLEEP_SECONDS = 0.3
N_IO_TASKS = 4
print(f"workload: {N_IO_TASKS} tasks x {SLEEP_SECONDS}s of blocking wait each\n")

# (a) Sequential: each wait happens one after another
start = time.perf_counter()
for _ in range(N_IO_TASKS):
    io_bound_task(SLEEP_SECONDS)
sequential_io_time = time.perf_counter() - start
print(f"single-threaded (sequential): {sequential_io_time:.3f}s")

# (b) Threaded: all waits happen concurrently
start = time.perf_counter()
io_threads = [threading.Thread(target=io_bound_task, args=(SLEEP_SECONDS,)) for _ in range(N_IO_TASKS)]
for t in io_threads:
    t.start()
for t in io_threads:
    t.join()
threaded_io_time = time.perf_counter() - start
print(f"multi-threaded ({N_IO_TASKS} threads):  {threaded_io_time:.3f}s")

io_speedup = sequential_io_time / threaded_io_time
print(f"\nmeasured speedup from threading: {io_speedup:.2f}x")
print(f"(sequential should cost ~{N_IO_TASKS * SLEEP_SECONDS:.1f}s total; threaded")
print(f" should cost ~{SLEEP_SECONDS:.1f}s total - roughly ONE wait period, not {N_IO_TASKS})")
if io_speedup > 2.5:
    print("-> Confirmed: threading gives a REAL, near-linear speedup here,")
    print("   because each thread releases the GIL the instant it starts")
    print("   sleeping/waiting, letting the others run during that dead time.")

print("\nSame mechanism applies directly to `requests.get()`, file I/O,")
print("socket reads, and most DB driver calls - which is exactly why")
print("`threading` (and `concurrent.futures.ThreadPoolExecutor`) remains a")
print("standard tool for concurrent API calls in data engineering pipelines,")
print("despite the GIL.")


"""
---------------------------------------------------------------------
5. SIDESTEPPING THE GIL ENTIRELY: multiprocessing  ⭐⭐⭐
---------------------------------------------------------------------
`multiprocessing` doesn't fight the GIL - it avoids the problem by
using separate OS PROCESSES instead of threads. Each process gets
its own Python interpreter, its own memory space, and therefore its
own INDEPENDENT GIL. N processes on N cores can genuinely execute
Python bytecode in true parallel, because there is no single lock
shared between them. The trade-off: processes can't share memory
directly (data must be pickled and sent between them, which has
real overhead), and process startup is heavier than thread startup -
so multiprocessing wins for CPU-bound work made of large chunks, not
many tiny ones.

Here we run the EXACT SAME CPU-bound workload from section 3, split
across a multiprocessing.Pool instead of threads, and this time we
DO see a real, measured speedup.
---------------------------------------------------------------------
"""

print("\n--- Proof: multiprocessing DOES Speed Up CPU-Bound Work ---")

if __name__ == "__main__":
    print(f"workload: {N_TASKS} tasks x {ITERATIONS:,} increments each (same as section 3)\n")
    print(f"single-threaded (sequential, from section 3): {sequential_time:.3f}s")

    start = time.perf_counter()
    with Pool(processes=N_TASKS) as pool:
        pool.map(cpu_bound_count, [ITERATIONS] * N_TASKS)
    multiprocessing_time = time.perf_counter() - start
    print(f"multiprocessing ({N_TASKS} processes):    {multiprocessing_time:.3f}s")

    mp_speedup = sequential_time / multiprocessing_time
    print(f"\nmeasured speedup from multiprocessing: {mp_speedup:.2f}x")
    if mp_speedup > 1.3:
        print("-> Confirmed: unlike threading, multiprocessing produced a REAL")
        print(f"   speedup ({mp_speedup:.2f}x) on this {os.cpu_count()}-core machine, because")
        print("   each process has its OWN GIL and runs on its own core, truly")
        print("   in parallel. The speedup is capped by core count and by the")
        print("   real overhead of starting processes and pickling data/results")
        print("   between them - it will not scale to a flat N-times for very")
        print("   small tasks, but it is genuine parallelism, not an illusion.")


"""
---------------------------------------------------------------------
6. DATA ENGINEERING ANGLE: C EXTENSIONS (NumPy/pandas) ALSO RELEASE
   THE GIL  ⭐⭐
---------------------------------------------------------------------
This is why "just use NumPy/pandas" is often the real answer to a
GIL question in a Data Engineering interview. Vectorized NumPy/
pandas operations are implemented in C, and many of them explicitly
release the GIL while the heavy C loop runs (the same mechanism as
I/O), letting other Python threads make progress concurrently. This
means a thread pool CAN give real speedups for certain NumPy-heavy
workloads too - not just I/O - but only for the portion of time
spent inside GIL-releasing C code, not for pure-Python bytecode.
The practical takeaway for pipeline design: push CPU-heavy work into
vectorized library calls or into `multiprocessing` workers; don't
expect plain Python loops on threads to parallelize.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Angle: Vectorized Code Can Release the GIL Too ---")

try:
    import numpy as np

    def numpy_bound_work(n):
        arr = np.arange(n, dtype=np.int64)
        return arr.sum()   # the heavy C loop inside .sum() releases the GIL

    N_ARR = 20_000_000
    N_WORKERS = 4

    start = time.perf_counter()
    for _ in range(N_WORKERS):
        numpy_bound_work(N_ARR)
    seq_np_time = time.perf_counter() - start

    start = time.perf_counter()
    np_threads = [threading.Thread(target=numpy_bound_work, args=(N_ARR,)) for _ in range(N_WORKERS)]
    for t in np_threads:
        t.start()
    for t in np_threads:
        t.join()
    thr_np_time = time.perf_counter() - start

    np_speedup = seq_np_time / thr_np_time
    print(f"sequential numpy .sum() x{N_WORKERS}: {seq_np_time:.3f}s")
    print(f"threaded numpy .sum() x{N_WORKERS}:   {thr_np_time:.3f}s  (speedup: {np_speedup:.2f}x)")
    print("\nNumPy's C-level .sum() DOES release the GIL while it crunches")
    print("numbers, unlike the pure-Python loop in section 3 - so in principle")
    print("threads calling it can genuinely overlap. Whether that shows up as")
    print("a clean speedup on any given run also depends on core count and")
    print("memory-bandwidth contention (this array workload is memory-bound,")
    print("so on a small/shared machine the threads can end up contending for")
    print("memory bandwidth rather than cleanly parallelizing) - which is why")
    print("real pipelines benchmark this case-by-case rather than assuming it")
    print("always wins the way the pure I/O case in section 4 reliably does.")
except ImportError:
    print("numpy not available in this environment - concept still holds:")
    print("C extensions that explicitly release the GIL (NumPy, pandas'")
    print("underlying C/Cython code, hashlib, zlib, etc.) let threads run")
    print("truly concurrently for the portion of work done in that C code.")


"""
---------------------------------------------------------------------
7. FORWARD-LOOKING: PYTHON 3.13+ FREE-THREADED (NO-GIL) BUILDS  ⭐
---------------------------------------------------------------------
Starting with CPython 3.13, an EXPERIMENTAL "free-threaded" build
(PEP 703, built with `--disable-gil`, installed as the `python3.13t`
variant) can run WITHOUT the GIL, using per-object and finer-grained
locking instead. This is still experimental as of 3.13/3.14: it is
not yet the default build, many C-extension packages (NumPy, pandas,
etc.) are still catching up their C-API usage to be safe without the
GIL, and single-threaded performance takes a measurable hit in
current builds because of the added locking overhead. Know that it
EXISTS and roughly WHY it's hard (fine-grained locking has to replace
what the one big lock used to guarantee), but don't overclaim
production-readiness in an interview - as of this writing it is
opt-in and still stabilizing, not something you'd default to for a
production Data Engineering pipeline.
---------------------------------------------------------------------
"""

print("\n--- Forward-Looking: Free-Threaded (No-GIL) Python ---")

print("sys.version_info:", sys.version_info[:2])
has_gil_flag = getattr(sys, "_is_gil_enabled", None)
if has_gil_flag is not None:
    print("sys._is_gil_enabled():", sys._is_gil_enabled())
else:
    print("This interpreter predates the free-threaded build's sys._is_gil_enabled()")
    print("check (added in 3.13) - this script is running on a standard,")
    print("GIL-enabled CPython build, which is still the default today.")
print("Python 3.13+ offers an EXPERIMENTAL no-GIL build (PEP 703). Worth")
print("knowing it exists and why it's non-trivial (fine-grained locking has")
print("to replace the one big lock's safety guarantees) - not yet the default,")
print("and the ecosystem of C extensions is still adapting to it.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
GIL         -> one mutex; only 1 thread runs Python bytecode at a time
Why it exists -> protects CPython's reference-counting from races,
                without needing a lock on every single object

CPU-bound + threading    -> NO real speedup (GIL serializes bytecode)
I/O-bound + threading    -> REAL speedup (GIL released while blocked)
CPU-bound + multiprocessing -> REAL speedup (separate process = separate GIL)

Measured in this file (numbers vary by machine):
    section 3: sequential vs threaded CPU work -> ~1.0x  ("no" speedup)
    section 4: sequential vs threaded I/O wait -> ~N x   (near-linear)
    section 5: sequential vs multiprocessing   -> real, sub-linear-to-N x

GIL released during: time.sleep(), file/socket I/O, many C-extension
    calls (NumPy/pandas internals, hashlib, zlib, ...)
GIL NOT released during: plain Python bytecode loops (for/while/+=/
    function calls written in pure Python)

Rule of thumb:
    I/O-bound (waiting on network/disk/DB)  -> threading /
                                                concurrent.futures.ThreadPoolExecutor
                                                / asyncio
    CPU-bound (pure-Python number crunching) -> multiprocessing /
                                                concurrent.futures.ProcessPoolExecutor
                                                (or push work into vectorized
                                                NumPy/pandas/C code)

Python 3.13+ -> experimental free-threaded (no-GIL) build exists
                (PEP 703); not yet the default; ecosystem still adapting
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - THE GLOBAL INTERPRETER LOCK (GIL)
=====================================================================

1. What is the GIL, and how does it affect multithreading in Python?

2. Why does CPython have a GIL at all - what problem was it designed
   to solve, in terms of how CPython manages memory?

3. In section 3's benchmark, `cpu_bound_count()` was run 4 times
   sequentially and then again across 4 threads. Why did the threaded
   version NOT run roughly 4x faster, even though the machine has
   multiple cores?

4. In section 4, running 4 `time.sleep(0.3)` calls across 4 threads
   completed in roughly 0.3s total instead of 1.2s. Explain exactly
   WHY the GIL doesn't prevent this speedup - what does the CPython
   C code do with the GIL while a thread is blocked in `time.sleep()`
   or waiting on a socket?

5. Given that the GIL exists, why is `threading` still considered a
   standard, useful tool for a data pipeline that makes many
   concurrent API calls?

6. How does `multiprocessing` avoid the GIL problem entirely, when
   `threading` cannot? What do you give up in exchange (think about
   memory sharing and process startup cost)?

7. Why did the `multiprocessing.Pool` benchmark in section 5 show a
   real speedup while the `threading` benchmark in section 3, running
   the exact same `cpu_bound_count()` workload, did not?

8. Some NumPy/pandas operations can benefit from being run across
   multiple threads even though they're "CPU-bound" - why does that
   not contradict what you just learned about the GIL and threading?

9. If you needed to download and process 1,000 files from a REST
   API as fast as possible, would you reach for `threading` or
   `multiprocessing` first, and why?

10. What would you expect to happen if you replaced `multiprocessing`
    with `threading` in a pipeline stage that does heavy pure-Python
    JSON parsing/transformation on a large in-memory list? What if
    that same stage instead spent most of its time waiting on a
    database cursor?

11. What is `sys.getswitchinterval()`, and what does it control?

12. Is the GIL part of the Python LANGUAGE specification, or an
    implementation detail of CPython specifically? What does that
    distinction imply about other Python implementations (e.g.
    Jython) or about future CPython versions?

13. What is PEP 703 / the "free-threaded" CPython build introduced
    experimentally in 3.13? Why is removing the GIL not simply "free
    performance" - what has to be added back in its place, and what
    is the current trade-off?

14. Why can't two Python threads increment the SAME shared counter
    variable's underlying reference count safely without some form
    of locking, and how does the GIL provide that safety today
    without you having to write any explicit locks yourself?

15. When would you use `multiprocessing` over `multithreading` in a
    data pipeline (this sets up a deeper head-to-head comparison of
    the two - covered in full in the next file)?
=====================================================================
"""
