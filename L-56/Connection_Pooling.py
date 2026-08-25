"""
=====================================================================
CONNECTION POOLING - Complete Notes with Executable Examples
=====================================================================

Opening a database connection is NOT free. Under the hood it usually
involves a TCP handshake with the DB server, an authentication
round-trip (sending/verifying credentials), and server-side SESSION
SETUP (allocating a backend process/thread, negotiating protocol
version, setting session defaults). Each of these is a network round
trip plus real server-side work - commonly single-digit-to-tens of
milliseconds, sometimes much more under load or across a WAN.

That cost is invisible if you open ONE connection and reuse it for
an entire batch job. It becomes the DOMINANT cost if your pipeline
opens a NEW connection per unit of work - e.g. "connect, insert one
row, disconnect" repeated 100,000 times. At even 10ms of pure
connection overhead per row, that is over 16 minutes spent just
connecting, before a single byte of real work is done.

A CONNECTION POOL solves this by keeping a small set of already-
established, live connections around. Code "checks out" a connection
from the pool, uses it, and "checks it back in" (returns it) instead
of closing it - so the expensive handshake/auth/setup cost is paid
ONCE per connection and then AMORTIZED across thousands of checkouts.

SQLAlchemy's `Engine` pools connections automatically - you rarely
build a pool by hand. This file uses SQLAlchemy's `Engine` against a
throwaway sqlite file to make the pool's internal behavior directly
observable (checkouts, checkins, timeouts, leaks) - the exact same
concepts and API apply unchanged when the URL points at a real
Postgres/MySQL server via `psycopg2`/`pyodbc`.
=====================================================================
"""

print("--- Overview ---")
print("A connection pool keeps live DB connections open and reuses")
print("them, instead of paying setup cost (TCP + auth + session) on")
print("every single unit of work in a pipeline.")


"""
---------------------------------------------------------------------
1. WHY OPENING A CONNECTION IS EXPENSIVE  ⭐⭐⭐
---------------------------------------------------------------------
Conceptually, `connect()` against a real network database does:
    1. TCP HANDSHAKE       - SYN / SYN-ACK / ACK with the DB host
    2. TLS NEGOTIATION     - if the connection is encrypted (common
                              in production)
    3. AUTHENTICATION      - client sends credentials, server
                              verifies them against its user catalog
    4. SESSION SETUP       - server allocates a backend process/
                              thread, negotiates protocol/version,
                              sets session-level defaults (timezone,
                              search_path, encoding, etc.)
Only AFTER all of that can the connection run your first query. None
of this is specific to Python - it's true for any client language.
---------------------------------------------------------------------
"""

print("\n--- Why Opening a Connection Is Expensive ---")

import time
import sqlite3

# sqlite3 is a local, in-process, file-based engine - it has no TCP
# handshake or network auth at all, so its own connect() cost is not
# a fair stand-in for a real network DB's. We time it anyway just to
# show the PATTERN of measuring connection setup cost, then reason
# about the real-world numbers conceptually below.
db_path = "/tmp/pyrepo/L-56/_demo.db"

start = time.perf_counter()
for _ in range(50):
    conn = sqlite3.connect(db_path)   # open
    conn.execute("SELECT 1")
    conn.close()                       # close - discards the setup work
local_elapsed = time.perf_counter() - start

print(f"50x open/query/close against LOCAL sqlite: {local_elapsed * 1000:.2f} ms total")
print("Even with ZERO network hop, opening a connection is measurable")
print("work. A real network DB adds a TCP handshake (~0.5-1+ round")
print("trips), TLS negotiation, and server-side auth/session setup on")
print("top of this - commonly 5-50ms+ per connection, far more across")
print("a WAN or a loaded server. A pipeline that opens one connection")
print("PER ROW (e.g. inside a `for row in rows:` loop) pays this cost")
print("N times instead of once, and it can easily dominate total")
print("runtime even when each individual query is fast.")


"""
---------------------------------------------------------------------
2. WHAT A CONNECTION POOL ACTUALLY IS  ⭐⭐⭐
---------------------------------------------------------------------
A connection pool is a pre-established set of LIVE connections that
get CHECKED OUT, used, and CHECKED BACK IN - never closed after a
single use. The expensive handshake/auth/setup cost is paid once per
physical connection, at pool-creation (or first-use) time, then
amortized across every checkout that follows.

SQLAlchemy's `create_engine()` builds an `Engine` wrapping exactly
this kind of pool (a `QueuePool` by default, for both real network
DBs and file-based sqlite). Calling `engine.connect()` does NOT open
a fresh physical connection each time - it CHECKS OUT one from the
pool (creating one only if the pool is empty and under its size
limit). Calling `.close()` on that connection does not actually
close the socket - it returns the connection to the pool.
---------------------------------------------------------------------
"""

print("\n--- What a Connection Pool Actually Is ---")

from sqlalchemy import create_engine, text

pool_db_path = "/tmp/pyrepo/L-56/_pool_demo.db"
engine = create_engine(
    f"sqlite:///{pool_db_path}",
    pool_size=3,        # keep up to 3 connections alive in the pool
    max_overflow=2,     # allow up to 2 MORE temporary connections under burst load
    pool_timeout=5,      # see section 4
)

print("pool status right after creating the engine (nothing opened yet):")
print(" ", engine.pool.status())

# Simulate a pipeline doing 8 sequential units of work, each needing
# a connection - exactly the "one connection per unit of work"
# pattern that would be disastrous WITHOUT pooling.
seen_dbapi_ids = set()
for i in range(8):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        # identity of the underlying DBAPI connection object - if
        # pooling is working, this repeats across only a FEW distinct
        # values instead of being unique on every iteration
        seen_dbapi_ids.add(id(conn.connection.dbapi_connection))

conn_word = "connection was" if len(seen_dbapi_ids) == 1 else "connections were"
print(f"\n8 checkouts done, but only {len(seen_dbapi_ids)} distinct")
print(f"underlying physical {conn_word} ever created - the pool")
print("REUSED it/them instead of opening a new one every time:")
print(" ", engine.pool.status())
print(" checked out right now:", engine.pool.checkedout())
print(" checked in (idle, ready to reuse):", engine.pool.checkedin())


"""
---------------------------------------------------------------------
3. POOL SIZING PARAMETERS  ⭐⭐⭐
---------------------------------------------------------------------
pool_size      - number of connections kept OPEN AND IDLE in the pool
                  even when unused. This is your normal steady-state
                  capacity.
max_overflow   - EXTRA connections allowed temporarily beyond
                  pool_size, for bursts. They are closed (not kept)
                  once returned and the pool is back at pool_size.
pool_timeout   - how long (seconds) a caller will WAIT for a free
                  connection before giving up, when the pool AND its
                  overflow are both fully checked out.
pool_recycle   - max age (seconds) of a pooled connection before it's
                  discarded and replaced, even if otherwise healthy.
                  Prevents using a connection the DB server (or a
                  firewall/load balancer) has silently killed after
                  sitting idle too long - a real, common production
                  bug ("MySQL server has gone away" is the classic
                  symptom of NOT setting this).

Realistic guidelines:
  WEB APP  (many short-lived requests, high concurrency, one process
            often serving many simultaneous users):
      - pool_size moderate (5-20), max_overflow to absorb traffic
        spikes, pool_timeout SHORT (a few seconds) - fail fast rather
        than pile up worker threads waiting on a starved pool.
      - pool_recycle set below the DB/proxy's own idle-connection
        kill time (e.g. 1800s) since connections may sit idle
        between requests.

  DATA PIPELINE / BATCH JOB (few, long, sequential-or-lightly-
            parallel steps, one process, usually short-lived overall):
      - pool_size can be SMALL (often 1 is enough for a single-
        threaded ETL script!) or set to match your actual worker
        concurrency (e.g. a thread pool of 8 workers -> pool_size=8).
        There is no benefit to a large idle pool nobody will use.
      - max_overflow can be small/zero - pipeline concurrency is
        usually known and fixed, unlike unpredictable web traffic.
      - pool_timeout can be more generous - a batch job waiting a
        few extra seconds for a connection rarely matters the way a
        user-facing request does.
---------------------------------------------------------------------
"""

print("\n--- Pool Sizing Parameters ---")

pipeline_engine = create_engine(
    f"sqlite:///{pool_db_path}",
    pool_size=1,          # single-threaded batch script - one is enough
    max_overflow=0,        # no bursty concurrent callers to absorb
    pool_timeout=30,
    pool_recycle=1800,     # discard/replace connections older than 30 min
)
webapp_engine = create_engine(
    f"sqlite:///{pool_db_path}",
    pool_size=20,          # many concurrent requests need many idle conns ready
    max_overflow=10,       # absorb traffic spikes above steady state
    pool_timeout=3,         # fail fast rather than stack up waiting requests
    pool_recycle=1800,
)
print("pipeline_engine pool_size=1, max_overflow=0  -> tuned for a lone batch script")
print("webapp_engine   pool_size=20, max_overflow=10 -> tuned for concurrent web traffic")
print("Same Engine API, deliberately different sizing for the workload shape.")


"""
---------------------------------------------------------------------
4. POOL EXHAUSTION: WHEN pool_timeout FIRES  ⭐⭐⭐
---------------------------------------------------------------------
If every connection in the pool (up to pool_size + max_overflow) is
CHECKED OUT and none are returned, the next caller BLOCKS, waiting up
to `pool_timeout` seconds for one to free up. If nothing frees up in
time, SQLAlchemy raises a `TimeoutError` rather than waiting forever
- a real failure mode you must handle (retry, alert, fail the job)
in production pipelines with too much concurrency for too small a
pool.
---------------------------------------------------------------------
"""

print("\n--- Pool Exhaustion and pool_timeout ---")

import threading
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

small_engine = create_engine(
    f"sqlite:///{pool_db_path}",
    pool_size=2,       # deliberately tiny
    max_overflow=0,     # no burst room at all
    pool_timeout=1,      # fail fast for this demo instead of the 30s default
)

def hold_a_connection(barrier, hold_seconds=1.5):
    """Simulates a slow/long-running unit of work occupying a pooled connection."""
    conn = small_engine.connect()
    barrier.wait()          # signal "I'm holding a connection now"
    time.sleep(hold_seconds)
    conn.close()             # returned to the pool once this worker is done

start_barrier = threading.Barrier(3)   # 2 worker threads + this thread
workers = [threading.Thread(target=hold_a_connection, args=(start_barrier,)) for _ in range(2)]
for w in workers:
    w.start()
start_barrier.wait()   # released once both workers have checked out a connection

print("both pool slots occupied by worker threads:", small_engine.pool.status())
try:
    # a 3rd caller: pool_size=2, max_overflow=0 -> nothing left to hand out
    extra_conn = small_engine.connect()
    extra_conn.close()
    print("unexpectedly got a connection")
except PoolTimeoutError as e:
    print("pool exhausted - TimeoutError raised as expected:")
    print(" ", str(e).splitlines()[0])

for w in workers:
    w.join()
print("after workers finish and return their connections:", small_engine.pool.status())


"""
---------------------------------------------------------------------
5. LEAKED CONNECTIONS: WHY `with engine.connect()` MATTERS  ⭐⭐⭐
---------------------------------------------------------------------
A "leaked" connection is one checked out via `engine.connect()` that
is NEVER returned - most commonly because an exception is raised
between the checkout and a manual `.close()` call, so the `.close()`
line is simply never reached. One leak looks harmless. In a pipeline
processing thousands of records with an occasional bad row, leaks
accumulate silently until the pool is fully exhausted and every
subsequent caller starts timing out - a classic slow-burn production
incident that's confusing to debug because the ERROR shows up far
from the code that caused it.

The fix is the same pattern from context managers: `with
engine.connect() as conn:` guarantees the connection is released via
`__exit__` NO MATTER how the block exits - success, a handled
exception, or an unhandled one - because Python calls `__exit__`
during exception unwinding just like `finally` does.
---------------------------------------------------------------------
"""

print("\n--- Leaked Connections vs the Context Manager Fix ---")

leak_engine = create_engine(f"sqlite:///{pool_db_path}", pool_size=2, max_overflow=0)

# accidentally keeps the checked-out connection referenced/alive,
# the way storing it on a job object, a thread-local, or letting an
# exception traceback hold it would in real buggy pipeline code
leaked_refs = []

def process_row_buggy(row_id):
    """BUGGY: manual close() on the happy path only - skipped on error."""
    conn = leak_engine.connect()
    leaked_refs.append(conn)               # simulates the reference escaping
    if row_id == 2:
        raise ValueError(f"malformed data in row {row_id}")
    conn.close()

for row_id in (1, 2):
    try:
        process_row_buggy(row_id)
    except ValueError as e:
        print(f" row {row_id} failed (connection NOT closed): {e}")

print("after processing 2 rows, 1 connection leaked:", leak_engine.pool.status())

def process_row_fixed(row_id):
    """FIXED: the context manager releases the connection on EVERY exit path."""
    with leak_engine.connect() as conn:
        if row_id == 99:
            raise ValueError(f"malformed data in row {row_id}")
        conn.execute(text("SELECT 1"))
    # conn is guaranteed released here, whether or not the row raised

try:
    process_row_fixed(99)
except ValueError as e:
    print(f" row 99 failed (connection safely released anyway): {e}")

print("pool status after the fixed version - no additional leak:")
print(" ", leak_engine.pool.status())
print("\nRule of thumb: NEVER call engine.connect() outside a `with`")
print("block in pipeline code - the one exception path you forget to")
print("close() is the one that eventually exhausts the pool in prod.")


"""
---------------------------------------------------------------------
6. SERVERLESS PIPELINES & EXTERNAL POOLERS (FORWARD-LOOKING NOTE)  ⭐⭐
---------------------------------------------------------------------
Everything above assumes ONE long-lived process holding ONE pool
across many operations - true for a typical batch script or a
long-running service. Short-lived, serverless/lambda-style pipeline
invocations break that assumption: each invocation is a FRESH
process that creates its OWN Engine/pool, uses it for one (often
tiny) unit of work, then the whole process is torn down - so the
"amortize setup cost across many operations" benefit of pooling
barely applies WITHIN a single invocation, and a burst of concurrent
invocations can each open their own handful of connections
simultaneously, multiplying total connections against the database
far beyond what any one pool's `pool_size` would suggest.

In real production Data Engineering stacks (especially serverless
ETL fan-out against Postgres), an EXTERNAL pooler such as PgBouncer
is commonly placed IN FRONT of the database: it holds the real
long-lived pool of physical Postgres connections centrally, while
every short-lived invocation makes a cheap connection to PgBouncer
itself (a lightweight local hop) instead of paying full Postgres
connection setup cost per invocation. This is worth mentioning by
name in interviews as the standard fix for "many short-lived
processes each wanting their own pool."
---------------------------------------------------------------------
"""

print("\n--- Serverless Pipelines and External Poolers ---")
print("Each Lambda-style invocation creating its OWN Engine means the")
print("pool is rebuilt from scratch every invocation - little benefit")
print("within one invocation, and many invocations firing at once can")
print("collectively overwhelm the DB's max_connections limit.")
print("Production fix: put PgBouncer (or a similar external pooler)")
print("in front of Postgres, so many short-lived clients share one")
print("centrally-managed pool of real DB connections.")

# cleanup demo artifacts
for engine_obj in (engine, pipeline_engine, webapp_engine, small_engine, leak_engine):
    engine_obj.dispose()
import os
for path in (db_path, pool_db_path):
    if os.path.exists(path):
        os.remove(path)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Why pooling matters -> new connection = TCP handshake + auth +
                        server-side session setup, paid EVERY time
                        without pooling. Dominates runtime when a
                        pipeline connects per-row instead of reusing.

Connection pool        -> pre-opened, live connections CHECKED OUT,
                           used, and CHECKED BACK IN - never closed
                           for real between uses.

engine.connect()        -> checks out (or creates, up to the limit)
.close() / `with` exit   -> returns the connection to the pool

pool_size      -> steady-state connections kept open & idle
max_overflow   -> extra temporary connections allowed under burst
pool_timeout   -> seconds to WAIT for a free connection before
                   raising TimeoutError
pool_recycle   -> max connection age before it's discarded/replaced

Pipeline sizing  -> small pool_size (often 1 per worker), small/zero
                     max_overflow, more generous pool_timeout
Web app sizing   -> larger pool_size + max_overflow for concurrency,
                     SHORT pool_timeout to fail fast

Pool exhausted  -> every slot checked out, none returned -> next
                    caller blocks up to pool_timeout, then
                    TimeoutError

Leaked connection -> checked out, never returned (often via a missed
                       .close() on an exception path) -> slowly
                       exhausts the pool over many operations
Fix              -> `with engine.connect() as conn:` always releases
                      it, on every exit path (success or exception)

Serverless note -> each invocation's OWN pool barely amortizes
                    anything and can multiply total DB connections;
                    production fix = external pooler (PgBouncer) in
                    front of the real database
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CONNECTION POOLING
=====================================================================

1. What is connection pooling, and why does it matter for pipelines?

2. Conceptually, what makes opening a new database connection
   expensive? Name the distinct steps involved (network handshake,
   auth, server-side session setup).

3. In this file, section 2 opens 8 connections via `engine.connect()`
   in a loop but only ever creates a handful of distinct physical
   connections. Explain, in terms of what `.close()` actually does
   on a pooled connection, why that happens.

4. What is the difference between `pool_size` and `max_overflow`?
   If `pool_size=5` and `max_overflow=2`, what is the maximum number
   of simultaneous connections the engine will allow?

5. What does `pool_timeout` control, and what exception does
   SQLAlchemy raise when it's exceeded? What could cause this to
   happen in a real production pipeline?

6. Why would you set `pool_size` MUCH smaller for a batch/ETL script
   than for a web application serving concurrent requests?

7. What problem does `pool_recycle` solve? What real-world symptom
   (e.g. from MySQL) shows up when it's NOT set and the DB/network
   silently kills idle connections?

8. What is a "leaked" connection? Walk through how `process_row_buggy`
   in section 5 leaks a connection on an exception path.

9. Why does wrapping the same logic in `with engine.connect() as
   conn:` fix the leak from question 8? Tie this back to how context
   managers guarantee `__exit__` runs during exception unwinding.

10. If a pipeline leaks one connection per 10,000 rows processed due
    to a rare malformed-row exception, why might this NOT cause any
    visible failure for a long time, and then suddenly cause
    widespread timeouts?

11. How would you monitor whether a running application is close to
    exhausting its connection pool, using the kind of pool
    introspection shown in this file (`pool.status()`,
    `checkedout()`, `checkedin()`)?

12. Why does a serverless/Lambda-style pipeline invocation get much
    less benefit from an in-process connection pool than a long-running
    service does?

13. What problem does an external pooler like PgBouncer solve when
    many short-lived serverless invocations each try to talk to the
    same Postgres database?

14. Explain the trade-off in choosing a SHORT vs LONG `pool_timeout`:
    what does a short timeout protect against, and what does it risk
    for legitimate but momentarily slow callers?

15. Why is raw `sqlite3.connect()`/`.close()` per call not a fair
    stand-in for measuring real network-database connection cost, and
    what does the local timing in section 1 still teach you despite
    that?
=====================================================================
"""
