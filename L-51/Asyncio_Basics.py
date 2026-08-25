"""
=====================================================================
ASYNCIO BASICS - Cooperative Concurrency for I/O-Bound Work
=====================================================================

asyncio lets a SINGLE thread juggle many I/O-bound operations (API
calls, DB queries, file/network reads) at once, without the overhead
of extra OS threads or processes. The mental model to memorize:

    ONE thread runs an EVENT LOOP. The event loop holds a set of
    coroutines ("tasks"). It runs one task's code until that task
    hits an `await` on something slow (network I/O, a timer, a DB
    call) - at that exact point, the task voluntarily YIELDS control
    back to the loop, which then picks another ready task to run.
    This is COOPERATIVE multitasking: tasks decide when to give up
    control (at `await` points), nothing forces a switch mid-line.

Compare this to the OTHER two concurrency tools in Python:

    threading   -> multiple OS threads, but the GIL (Global
                   Interpreter Lock) only lets ONE thread execute
                   Python bytecode at a time anyway. The OS can
                   PREEMPT a thread mid-bytecode-instruction at any
                   moment (you don't control when), which is exactly
                   why shared mutable state needs locks/mutexes.
    multiprocessing -> separate OS PROCESSES, each with its own
                   Python interpreter and its own GIL -> genuinely
                   parallel, real multi-core CPU usage. Needed for
                   CPU-bound work; overkill for I/O-bound waiting.
    asyncio     -> ONE thread, ONE GIL holder, ZERO preemption.
                   Switches happen ONLY at `await` points that YOU
                   can see in the source code. Because only one
                   coroutine's Python code is ever running at any
                   instant, and control only changes hands at
                   explicit, visible points, there is no possibility
                   of another coroutine tearing your shared dict or
                   list mid-update the way a preempted thread could.
                   You get concurrency for I/O waiting WITHOUT ever
                   touching a Lock - the GIL-contention/locking
                   problem simply doesn't exist here, because there
                   is fundamentally only ever one thread in the room.

asyncio is the right tool specifically for I/O-BOUND work: waiting on
network responses, DB round-trips, disk I/O - situations where the
CPU is mostly idle, just waiting. It does NOT speed up CPU-bound work
(number crunching) at all, because there's still only one thread
executing Python bytecode - for that, you still want multiprocessing.
=====================================================================
"""

import asyncio
import time
import threading

print("--- Overview ---")
print("asyncio = ONE thread running an event loop that cooperatively")
print("switches between coroutines at 'await' points - great for")
print("I/O-bound waiting (APIs, DBs), useless for speeding up CPU work.")


"""
---------------------------------------------------------------------
1. PROVING IT'S ONE THREAD: THE EVENT LOOP AND COOPERATIVE SWITCHING  ⭐⭐⭐
---------------------------------------------------------------------
If asyncio concurrency really runs on a single thread, then every
coroutine scheduled by the same event loop should report the exact
same OS thread id. Unlike `threading`, where the OS can interrupt a
thread at ANY bytecode instruction, an asyncio coroutine can only be
interrupted at a point where IT says `await` - the loop can never
sneak in mid-statement.
---------------------------------------------------------------------
"""

print("\n--- Proving It's One Thread ---")

async def report_thread(label):
    print(f"  {label} starting on thread id {threading.get_ident()}")
    await asyncio.sleep(0.1)   # the ONLY point where this coroutine can be paused
    print(f"  {label} resuming on thread id {threading.get_ident()}")
    return threading.get_ident()

async def main_thread_demo():
    # both coroutines are scheduled onto the SAME event loop
    ids = await asyncio.gather(report_thread("coroutine-A"), report_thread("coroutine-B"))
    return ids

thread_ids = asyncio.run(main_thread_demo())
print("thread ids seen by both coroutines:", thread_ids)
print("same id both times ->", thread_ids[0] == thread_ids[1], "(one thread, cooperative switching)")


"""
---------------------------------------------------------------------
2. async def / await BASICS - AND THE #1 BEGINNER GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
`async def` defines a COROUTINE FUNCTION. Calling it does NOT run its
body at all - it immediately returns a coroutine OBJECT, a paused
"recipe" for the work, that does nothing until something actually
drives it forward (an `await`, or handing it to the event loop). This
trips up nearly every asyncio beginner: they call the function
expecting a result and instead get back this inert object with no
error, no warning printed to the screen by default.
---------------------------------------------------------------------
"""

print("\n--- async def / await Basics: The Coroutine Object Gotcha ---")

async def fetch_greeting(name):
    await asyncio.sleep(0.1)   # pretend this is a network call
    return f"Hello, {name}!"

# THE MISTAKE: calling a coroutine function like a normal function
result = fetch_greeting("Data Engineer")
print("just CALLING fetch_greeting(...) gives you:", result)
print("type(result):", type(result))
print("^ that's a coroutine OBJECT, not the string - the function body")
print("  has not run a single line yet! Nothing awaited or scheduled it.")
result.close()   # avoid a "coroutine was never awaited" warning since we never run it

# THE FIX: you must either `await` it inside an async function, or hand
# it to the event loop with asyncio.run() (which is really just
# await-ing it inside a loop asyncio creates and tears down for you)
correct_result = asyncio.run(fetch_greeting("Data Engineer"))
print("\nrunning it properly with asyncio.run():", correct_result)
print("type(correct_result):", type(correct_result))


"""
---------------------------------------------------------------------
3. RUNNING THINGS CONCURRENTLY WITH asyncio.gather()  ⭐⭐⭐
---------------------------------------------------------------------
`asyncio.sleep()` is the async-friendly stand-in for `time.sleep()` -
it doesn't block the thread, it tells the event loop "wake me up
after this long, and go run something else in the meantime." Passing
several coroutines to `asyncio.gather()` schedules them ALL onto the
event loop at once; while one is paused inside `await asyncio.sleep`,
the loop runs the others. Total wall-clock time ends up close to the
SLOWEST single call, not the sum of all of them.
---------------------------------------------------------------------
"""

print("\n--- Running Concurrently with asyncio.gather() ---")

async def call_api(endpoint, latency_seconds):
    print(f"  -> calling {endpoint} (will take {latency_seconds}s)")
    await asyncio.sleep(latency_seconds)   # non-blocking "wait" - loop is free to do other work
    print(f"  <- {endpoint} responded")
    return {"endpoint": endpoint, "latency": latency_seconds}

async def run_concurrent_calls():
    start = time.perf_counter()
    results = await asyncio.gather(
        call_api("/users", 0.4),
        call_api("/orders", 0.3),
        call_api("/inventory", 0.5),
    )
    elapsed = time.perf_counter() - start
    return results, elapsed

concurrent_results, concurrent_elapsed = asyncio.run(run_concurrent_calls())
print("results:", concurrent_results)
print(f"elapsed: {concurrent_elapsed:.2f}s (close to the SLOWEST call, 0.5s - not the 1.2s sum)")


"""
---------------------------------------------------------------------
4. THE #1 asyncio MISTAKE: BLOCKING THE EVENT LOOP  ⭐⭐⭐
---------------------------------------------------------------------
This is THE single most important asyncio demo for interviews. If you
call a BLOCKING function like `time.sleep()` inside a coroutine
instead of `await asyncio.sleep()`, it does NOT yield control back to
the event loop - the one and only thread just sits there blocked.
Every other "concurrent" coroutine is frozen too, because there is
nobody else to run them. `asyncio.gather()` still LOOKS concurrent in
the code, but the tasks now run one after another, back to back, and
total time becomes the SUM of every duration - identical to plain
sequential code, just with extra asyncio machinery around it.
---------------------------------------------------------------------
"""

print("\n--- The #1 Mistake: Blocking the Event Loop with time.sleep() ---")

# BUGGY: looks async (it's an `async def` using gather!) but time.sleep()
# never awaits anything, so it never gives the loop a chance to switch
async def call_api_blocking(endpoint, latency_seconds):
    print(f"  -> calling {endpoint} (BLOCKING, will take {latency_seconds}s)")
    time.sleep(latency_seconds)   # BUG: blocks the entire thread/event loop, no yield point
    print(f"  <- {endpoint} responded")
    return {"endpoint": endpoint, "latency": latency_seconds}

async def run_blocking_calls():
    start = time.perf_counter()
    results = await asyncio.gather(
        call_api_blocking("/users", 0.4),
        call_api_blocking("/orders", 0.3),
        call_api_blocking("/inventory", 0.5),
    )
    elapsed = time.perf_counter() - start
    return results, elapsed

blocking_results, blocking_elapsed = asyncio.run(run_blocking_calls())
print("results:", blocking_results)
print(f"elapsed: {blocking_elapsed:.2f}s (the SUM, ~1.2s - the event loop was frozen the whole time)")
print(f"\nconcurrent (asyncio.sleep) version: {concurrent_elapsed:.2f}s")
print(f"blocking   (time.sleep) version:    {blocking_elapsed:.2f}s")
print("same code shape (async def + gather), completely different behavior -")
print("the only difference is whether the sleep call actually yields to the loop.")


"""
---------------------------------------------------------------------
5. asyncio.create_task() - STARTING WORK IN THE BACKGROUND  ⭐⭐
---------------------------------------------------------------------
Just creating a coroutine OBJECT (section 2) does nothing until it's
awaited. `asyncio.create_task()` is different: it immediately
SCHEDULES the coroutine onto the running event loop as a Task, which
starts making progress in the background the moment the current
coroutine hits its next `await` - even before you explicitly `await`
the task itself. This lets you kick off work now and collect its
result later, after doing other things in between.
---------------------------------------------------------------------
"""

print("\n--- asyncio.create_task(): Background Scheduling ---")

async def background_job(name, delay):
    print(f"  [{name}] started")
    await asyncio.sleep(delay)
    print(f"  [{name}] finished")
    return f"{name}-result"

async def demo_create_task():
    # create_task() schedules this to start running as soon as we hit
    # an await below - unlike a bare coroutine object, it does NOT
    # wait for us to explicitly await IT first
    task = asyncio.create_task(background_job("background-upload", 0.3))
    print("task created - it is already scheduled, running in the background")

    # do other work while the background task makes progress on its own
    for i in range(3):
        print(f"  doing other work... step {i}")
        await asyncio.sleep(0.1)   # each await here gives the background task a chance to run

    result = await task   # now actually wait for it to finish and grab its result
    print("collected background task result:", result)

asyncio.run(demo_create_task())


"""
---------------------------------------------------------------------
6. DATA ENGINEERING EXAMPLE: CONCURRENT DB SHARD QUERIES  ⭐⭐⭐
---------------------------------------------------------------------
A very common real scenario: a sharded database (or a set of regional
API replicas) where you need results from ALL shards to build one
report. Querying them one at a time with `await` in a loop pays the
full latency of EVERY shard, added together. Firing them all off
together with `asyncio.gather()` pays roughly the latency of the
SLOWEST shard only - a huge win when I/O latency, not CPU, is the
bottleneck.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Example: Concurrent DB Shard Queries ---")

SHARDS = [
    ("shard-us-east", 0.3, 1_204),
    ("shard-us-west", 0.5, 980),
    ("shard-eu", 0.4, 1_530),
    ("shard-apac", 0.35, 812),
]

async def query_shard(shard_name, latency_seconds, row_count):
    # in production this would be, e.g.:
    #     async with aiopg.connect(dsn) as conn:
    #         async with conn.cursor() as cur:
    #             await cur.execute("SELECT COUNT(*) FROM orders")
    #             row = await cur.fetchone()
    await asyncio.sleep(latency_seconds)   # simulated network + query time
    return {"shard": shard_name, "rows": row_count}

async def query_shards_sequentially():
    start = time.perf_counter()
    results = []
    for shard_name, latency_seconds, row_count in SHARDS:
        results.append(await query_shard(shard_name, latency_seconds, row_count))
    return results, time.perf_counter() - start

async def query_shards_concurrently():
    start = time.perf_counter()
    results = await asyncio.gather(*(query_shard(*shard) for shard in SHARDS))
    return results, time.perf_counter() - start

sequential_results, sequential_elapsed = asyncio.run(query_shards_sequentially())
concurrent_shard_results, concurrent_shard_elapsed = asyncio.run(query_shards_concurrently())

total_rows = sum(r["rows"] for r in concurrent_shard_results)
print("per-shard results:", concurrent_shard_results)
print("aggregated total row count across all shards:", total_rows)
print(f"\nsequential (await one-by-one):  {sequential_elapsed:.2f}s  (sum of all 4 latencies, ~1.55s)")
print(f"concurrent (asyncio.gather):     {concurrent_shard_elapsed:.2f}s  (max latency only, ~0.5s)")
print(f"speedup: {sequential_elapsed / concurrent_shard_elapsed:.1f}x, for zero extra threads or processes")


"""
---------------------------------------------------------------------
7. ERROR HANDLING IN gather(): return_exceptions=True  ⭐⭐⭐
---------------------------------------------------------------------
By default, if ANY awaitable passed to `asyncio.gather()` raises, that
exception propagates out of `gather()` immediately - you lose easy
access to the results that DID succeed. For a data pipeline pulling
from several sources, one bad shard/endpoint shouldn't nuke the whole
batch. Passing `return_exceptions=True` makes `gather()` collect
BOTH successful results and exception objects in the output list,
in the original order, so you can separate the good from the bad
yourself.
---------------------------------------------------------------------
"""

print("\n--- Error Handling: return_exceptions=True ---")

async def query_shard_may_fail(shard_name, latency_seconds, should_fail):
    await asyncio.sleep(latency_seconds)
    if should_fail:
        raise ConnectionError(f"{shard_name} timed out")
    return {"shard": shard_name, "rows": 500}

sources = [
    ("shard-1", 0.1, False),
    ("shard-2", 0.15, True),    # this one will fail
    ("shard-3", 0.1, False),
]

async def gather_default_fails_fast():
    try:
        return await asyncio.gather(*(query_shard_may_fail(*s) for s in sources))
    except ConnectionError as e:
        return f"gather() raised immediately, losing the other results: {e}"

async def gather_tolerant():
    return await asyncio.gather(*(query_shard_may_fail(*s) for s in sources), return_exceptions=True)

default_outcome = asyncio.run(gather_default_fails_fast())
print("DEFAULT gather() behavior on partial failure:")
print(" ", default_outcome)

tolerant_outcome = asyncio.run(gather_tolerant())
print("\nWITH return_exceptions=True, nothing is lost:")
successes = [r for r in tolerant_outcome if not isinstance(r, Exception)]
failures = [r for r in tolerant_outcome if isinstance(r, Exception)]
print("  raw results list:", tolerant_outcome)
print("  succeeded:", successes)
print("  failed:", [str(f) for f in failures])
print("  -> a pipeline can now load the successes and just log/retry the failures")


"""
---------------------------------------------------------------------
8. HONEST NOTE: asyncio.sleep() IS A STAND-IN - USE aiohttp/httpx  ⭐⭐
---------------------------------------------------------------------
Every "API call" and "DB query" in this file used `asyncio.sleep()`
purely to simulate latency without needing real network access or a
live database. For an ACTUAL async HTTP call, you need a library
built on asyncio, such as `aiohttp` or `httpx.AsyncClient` - both
expose an `async def` / `await`-based API that yields control back to
the event loop while waiting on the socket, exactly like
`asyncio.sleep()` did above.

A classic interview trip-up: "can I just use the `requests` library
inside my async code?" NO - `requests` is built on blocking socket
calls with no `await` anywhere in it. Calling `requests.get(...)`
inside a coroutine behaves exactly like the `time.sleep()` mistake in
section 4: it blocks the ONE thread the whole event loop runs on,
freezing every other "concurrent" coroutine until it returns.
---------------------------------------------------------------------
"""

print("\n--- Honest Note: Real HTTP Calls Need an Async-Native Client ---")

async def fetch_real_endpoint_example(url):
    # This is the REAL, correct pattern for production async HTTP calls.
    # It is not executed against the network here - just shown as the
    # true API you'd actually write.
    try:
        import aiohttp
    except ImportError:
        print("  (aiohttp not installed in this sandbox - showing the real pattern only)")
        return None
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:      # `await`-based, non-blocking I/O
            return await response.json()

asyncio.run(fetch_real_endpoint_example("https://example-internal-api.pattern.com/health"))
print("requests.get(...) inside a coroutine -> BLOCKS the event loop, just like time.sleep().")
print("aiohttp / httpx.AsyncClient        -> built on asyncio, actually yields at I/O waits.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Mental model:      ONE thread -> ONE event loop -> cooperative
                    switching at `await` points only.

vs threading:       OS threads, GIL still serializes bytecode, OS can
                    PREEMPT mid-instruction -> needs locks.
vs multiprocessing: separate processes/interpreters -> true parallel
                    CPU work, no shared-memory GIL issue.
vs asyncio:         one thread, one GIL holder, zero preemption ->
                    no locks needed for I/O-bound concurrency.

async def foo():   -> defines a COROUTINE FUNCTION.
foo()               -> returns a coroutine OBJECT, runs NOTHING yet.
await foo()          -> actually drives the coroutine, gets the result.
asyncio.run(foo())    -> creates a loop, runs foo() to completion, top-level entry point.

asyncio.sleep(s)    -> async-friendly wait; YIELDS to the loop.
time.sleep(s)        -> blocking wait; FREEZES the whole loop. Never
                        use inside a coroutine.

asyncio.gather(*coros)              -> run several coroutines
                                        concurrently; total time ~=
                                        the SLOWEST one.
asyncio.gather(..., return_exceptions=True)
                                     -> collect exceptions alongside
                                        successes instead of failing
                                        the whole batch immediately.
asyncio.create_task(coro)           -> schedule now, runs in the
                                        background even before you
                                        `await` it yourself.

Real async I/O clients:  aiohttp, httpx.AsyncClient
NEVER use inside async code: requests, time.sleep, other blocking calls
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - ASYNCIO BASICS
=====================================================================

1. Explain `asyncio` and where it fits in data engineering (concurrent
   API/DB calls). What kind of workload is it good for, and what kind
   is it NOT good for?

2. What is the GIL, and how does asyncio's single-thread model relate
   to it? Why does asyncio avoid GIL-contention/locking problems
   entirely, when `threading` does not?

3. Walk through the fundamental difference between `threading`
   (preemptive OS-level switching), `multiprocessing` (true
   parallelism), and `asyncio` (single-thread cooperative
   switching). When would you reach for each one in a data pipeline?

4. If you write `result = fetch_greeting("x")` where `fetch_greeting`
   is an `async def` function, what is `result` actually? Why doesn't
   calling it run the function body?

5. What is the difference between `asyncio.run(coro())` and just
   calling `coro()` directly?

6. Why is `asyncio.sleep()` described as "non-blocking" while
   `time.sleep()` is "blocking"? What specifically happens
   differently at the OS/event-loop level?

7. In this file's section 4, both the working and the buggy version
   use `async def` and `asyncio.gather()` - so why does the buggy
   version (using `time.sleep()`) end up taking the SUM of all
   durations instead of roughly the MAX, like the working version?

8. What does `asyncio.gather(coro1(), coro2(), coro3())` actually do?
   Roughly how long does it take compared to `await`-ing each one
   sequentially in a loop?

9. What is the difference between just creating a coroutine object
   and calling `asyncio.create_task()` on a coroutine? Which one
   starts running immediately, and which one waits for you to
   `await` it?

10. In a pipeline pulling data from four DB shards, how would you
    fetch all four concurrently and combine the results? Roughly what
    total latency would you expect compared to fetching them one at
    a time?

11. What happens by default if one coroutine passed to
    `asyncio.gather()` raises an exception? How does
    `return_exceptions=True` change that behavior, and why is it
    useful for a pipeline that shouldn't fail entirely because one
    of several sources timed out?

12. Can you use the `requests` library for HTTP calls inside an
    `async def` coroutine and still get concurrency benefits? Why or
    why not - what would actually happen if you tried?

13. Name two libraries you'd use instead of `requests` to make real,
    non-blocking HTTP calls inside asyncio code.

14. How would you parallelize downloading 1,000 files from an API -
    would you reach for asyncio, threading, or multiprocessing, and
    why, given that this is I/O-bound work?

15. Explain, in your own words, what "cooperative multitasking" means
    in the context of asyncio, and specifically WHERE in the source
    code a task can be paused and resumed.
=====================================================================
"""
