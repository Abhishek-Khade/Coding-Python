"""
=====================================================================
IDEMPOTENT PIPELINES - Complete Notes with Executable Examples
=====================================================================

IDEMPOTENT, in the context of a data pipeline, does NOT mean "has no
side effects." It means: running the job N times with the SAME input
produces the SAME end state as running it exactly once.

    run_job(batch)                -> state S
    run_job(batch); run_job(batch) -> state S   (still! not 2x S)

The job is still allowed to DELETE rows, INSERT rows, call an API,
write a file - those are all side effects. What matters is that the
side effects are REPEATABLE: replaying the same input converges to
the same end state instead of accumulating more each time.

Why this matters in real Data Engineering: pipelines get re-run
constantly, and almost never on purpose in the "happy path" sense -
- a scheduler retries a task that failed halfway through
- an engineer manually re-triggers a backfill for one bad day
- an orchestrator (Airflow, Dagster, Step Functions) replays a DAG
  run after a crash, sometimes re-executing tasks that had already
  partially succeeded
- "at least once" delivery from a queue/event source means the same
  event can legitimately arrive twice

If the pipeline's write step is a blind "INSERT the rows I computed,"
every one of those situations silently DUPLICATES data. Idempotent
design is what makes it SAFE to just run the job again - no special
cleanup, no manual dedup, no fear of "did that already run?"
=====================================================================
"""

import sqlite3

print("--- Overview ---")
print("Idempotent pipeline = running it N times with the same input")
print("produces the SAME end state as running it once. Re-runnable")
print("by design, not by luck.")


"""
---------------------------------------------------------------------
1. IDEMPOTENT vs NON-IDEMPOTENT: THE PRECISE DEFINITION  ⭐⭐⭐
---------------------------------------------------------------------
Before touching a database, prove the concept in plain Python: two
tiny "pipelines" that both process the same batch of orders. One
ACCUMULATES a result across calls (non-idempotent); the other
COMPUTES a fresh, deterministic result and REPLACES it (idempotent).
The difference is APPEND semantics vs REPLACE/SET semantics.
---------------------------------------------------------------------
"""

print("\n--- Idempotent vs Non-Idempotent: The Precise Definition ---")

orders_batch = [10.0, 25.5, 9.99]

# NON-IDEMPOTENT: each call APPENDS to shared state -> output grows
# every time you call it, even though the INPUT never changed.
running_total_state = {"total": 0.0}

def non_idempotent_pipeline(batch):
    running_total_state["total"] += sum(batch)   # accumulates!
    return running_total_state["total"]

print("non-idempotent pipeline, called with the SAME batch twice:")
print("  run 1 ->", non_idempotent_pipeline(orders_batch))
print("  run 2 ->", non_idempotent_pipeline(orders_batch))
print("  (the answer DOUBLED for identical input - that's the bug)")

# IDEMPOTENT: each call computes a fresh result from the input alone
# and OVERWRITES the stored state - re-running just re-derives the
# same answer instead of piling on top of the last run.
idempotent_state = {"total": 0.0}

def idempotent_pipeline(batch):
    idempotent_state["total"] = sum(batch)        # SET, not accumulate
    return idempotent_state["total"]

print("\nidempotent pipeline, called with the SAME batch twice:")
print("  run 1 ->", idempotent_pipeline(orders_batch))
print("  run 2 ->", idempotent_pipeline(orders_batch))
print("  (identical result both times - safe to re-run)")

print("\nKey distinction: idempotent does NOT mean 'no side effects' -")
print("it means REPEATABLE side effects. The fix below applies this")
print("exact same 'replace, don't accumulate' idea to real SQL writes.")


"""
---------------------------------------------------------------------
2. THE CLASSIC BUG: A NAIVE INSERT-ONLY LOAD STEP  ⭐⭐⭐
---------------------------------------------------------------------
This is THE textbook non-idempotent pipeline: a "load daily sales"
job that just INSERTs whatever rows it extracted/transformed for
today's batch, with no awareness of whether this batch was already
loaded. Re-running it for the same run_date (a retry, a re-trigger,
someone fat-fingering the Airflow "Clear" button) silently DOUBLES
the data. We build this with real sqlite3 (stdlib) so the bug - and
every fix below - is REAL executed SQL, not a hypothetical.
---------------------------------------------------------------------
"""

print("\n--- The Classic Bug: Naive INSERT-Only Load ---")

conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE sales_naive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,   -- surrogate key: says
        run_date TEXT,                          -- NOTHING about which
        product TEXT,                           -- business record this
        amount REAL                             -- is, so duplicates
    )                                            -- slip right past it
""")

def extract_daily_sales(run_date):
    """Pretend 'extract' step: same source data every time it's
    called for the same run_date - a realistic assumption for a
    daily batch pulled from an upstream system of record."""
    return [
        (run_date, "widget", 19.99),
        (run_date, "gadget", 45.00),
        (run_date, "gizmo", 12.50),
    ]

def load_naive(run_date):
    """BUGGY load: just inserts the extracted rows, every time,
    with no check for 'did I already load this run_date?'."""
    rows = extract_daily_sales(run_date)
    conn.executemany(
        "INSERT INTO sales_naive (run_date, product, amount) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()

def report_naive(run_date):
    cur = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM sales_naive WHERE run_date = ?",
        (run_date,),
    )
    return cur.fetchone()

run_date = "2026-08-24"

load_naive(run_date)
count1, total1 = report_naive(run_date)
print(f"after run 1: {count1} rows, total = ${total1:.2f}")

# Now something totally ordinary happens: the scheduler retries this
# task (maybe it timed out waiting on a downstream ack), or someone
# re-runs the same day's batch manually. The EXTRACT is identical.
load_naive(run_date)
count2, total2 = report_naive(run_date)
print(f"after run 2 (same batch, re-run): {count2} rows, total = ${total2:.2f}")

assert count2 == count1 * 2 and abs(total2 - total1 * 2) < 1e-9
print(f"\nBUG CONFIRMED: row count and total both DOUBLED ({count1} -> {count2},")
print(f"${total1:.2f} -> ${total2:.2f}) from re-running the IDENTICAL batch.")
print("This is a real, silent data-quality incident - no exception was")
print("ever raised, so nothing would page anyone. It just quietly corrupts")
print("every downstream aggregate built on this table.")


"""
---------------------------------------------------------------------
3. FIX (A): DELETE-THEN-INSERT FOR THE PARTITION/BATCH KEY  ⭐⭐⭐
---------------------------------------------------------------------
The most common real-world fix: treat each run_date (or batch_id,
partition, etc.) as a REPLACEABLE UNIT. Before inserting, DELETE any
rows that already exist for that exact partition key, inside the
SAME transaction as the insert. Re-processing a partition then always
converges to "exactly this partition's current rows" - no accumulation,
regardless of how many times it runs.
---------------------------------------------------------------------
"""

print("\n--- Fix (A): DELETE-then-INSERT by Partition Key ---")

conn.execute("""
    CREATE TABLE sales_by_date (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT,
        product TEXT,
        amount REAL
    )
""")

def load_delete_then_insert(run_date):
    """IDEMPOTENT load: wipe this partition's rows first, then insert
    the freshly extracted rows for it - all inside one transaction,
    so a crash mid-way can't leave the partition half-deleted."""
    rows = extract_daily_sales(run_date)
    with conn:   # `with conn:` commits on success, ROLLS BACK on error -
                 # the delete+insert pair must succeed or fail TOGETHER
        conn.execute("DELETE FROM sales_by_date WHERE run_date = ?", (run_date,))
        conn.executemany(
            "INSERT INTO sales_by_date (run_date, product, amount) VALUES (?, ?, ?)",
            rows,
        )

def report_by_date(run_date):
    cur = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM sales_by_date WHERE run_date = ?",
        (run_date,),
    )
    return cur.fetchone()

load_delete_then_insert(run_date)
a_count, a_total = report_by_date(run_date)
print(f"after run 1: {a_count} rows, total = ${a_total:.2f}")

load_delete_then_insert(run_date)   # re-run the SAME batch again
b_count, b_total = report_by_date(run_date)
print(f"after run 2 (re-run): {b_count} rows, total = ${b_total:.2f}")

load_delete_then_insert(run_date)   # and a third time, for good measure
c_count, c_total = report_by_date(run_date)
print(f"after run 3 (re-run again): {c_count} rows, total = ${c_total:.2f}")

assert a_count == b_count == c_count and a_total == b_total == c_total
print("\nFIXED: identical row count and total across every re-run - the")
print("partition is fully REPLACED each time instead of appended to.")
print("This is the standard pattern for daily/hourly batch partitions.")


"""
---------------------------------------------------------------------
4. FIX (B): UPSERT / MERGE ON A NATURAL BUSINESS KEY  ⭐⭐⭐
---------------------------------------------------------------------
DELETE-then-INSERT works well when you can cleanly identify "the
whole partition." Sometimes you're loading individual records that
have a real NATURAL KEY (an order_id, a customer_id) rather than a
clean date partition, and you want later re-processing to UPDATE a
record in place if it changed, not just leave duplicates or silently
drop the update. That's an UPSERT: SQLite's
`INSERT ... ON CONFLICT (<natural_key>) DO UPDATE SET ...` maps
directly to Postgres/MySQL's `ON CONFLICT` / `ON DUPLICATE KEY
UPDATE`, and to a SQL `MERGE` statement on other engines - same idea.

Crucially, the conflict target is a NATURAL/business key, never an
autoincrement surrogate id - the surrogate id is different every
insert attempt, so it could never detect "this is the same record."
---------------------------------------------------------------------
"""

print("\n--- Fix (B): UPSERT Keyed on a Natural Business Key ---")

conn.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,   -- the NATURAL key: the upstream
                                      -- system's real order identifier
        status TEXT NOT NULL,
        amount REAL NOT NULL
    )
""")

def extract_orders_batch():
    """Same order_id appears here on a later run (e.g. the order's
    status changed from 'pending' to 'shipped') - a realistic CDC-
    style feed of order updates."""
    return [
        ("ord-1001", "pending", 59.99),
        ("ord-1002", "pending", 120.00),
    ]

def load_orders_upsert(rows):
    """UPSERT: insert new order_ids; for an order_id that already
    exists, UPDATE its status/amount instead of erroring OR silently
    duplicating. Safe to run against the exact same batch any number
    of times, and correctly reflects the LATEST version of a record."""
    conn.executemany(
        """
        INSERT INTO orders (order_id, status, amount)
        VALUES (?, ?, ?)
        ON CONFLICT (order_id) DO UPDATE SET
            status = excluded.status,     -- 'excluded' = the row that
            amount = excluded.amount      -- was proposed for insertion
        """,
        rows,
    )
    conn.commit()

load_orders_upsert(extract_orders_batch())
print("after run 1:", conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall())

# Re-run the SAME extract again (e.g. a retried task) - no duplicate rows:
load_orders_upsert(extract_orders_batch())
rows_after_replay = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
print("after run 2 (identical re-run):", rows_after_replay)
print("row count stayed at", len(rows_after_replay), "- no duplicates from re-running")

# Now the upstream order actually CHANGES status - upsert applies the update:
updated_batch = [("ord-1001", "shipped", 59.99), ("ord-1002", "pending", 120.00)]
load_orders_upsert(updated_batch)
print("after a real status change, upserted again:",
      conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall())
print("ord-1001 correctly moved to 'shipped' IN PLACE - same row, updated,")
print("not a second 'shipped' row sitting next to the old 'pending' one.")


"""
---------------------------------------------------------------------
5. FIX (C): UNIQUE CONSTRAINT + "SAFE TO RETRY" INSERTS  ⭐⭐
---------------------------------------------------------------------
A UNIQUE constraint on the natural key is a DATABASE-ENFORCED safety
net: even if application code has a bug and tries to insert the same
logical record twice, the DATABASE refuses it - failing LOUDLY with
an IntegrityError instead of silently duplicating data. That's
valuable on its own (fail-fast beats silent corruption), but a hard
failure isn't great UX for a routine retry. Pair it with
`INSERT OR IGNORE` (SQLite) / `ON CONFLICT DO NOTHING` (standard SQL)
for the specific case where "this exact record already exists" is an
EXPECTED, harmless outcome of re-running the same batch.
---------------------------------------------------------------------
"""

print("\n--- Fix (C): UNIQUE Constraint + Safe-to-Retry Inserts ---")

conn.execute("""
    CREATE TABLE processed_records (
        record_key TEXT UNIQUE NOT NULL,   -- DB-enforced natural-key
        amount REAL NOT NULL               -- uniqueness, not just a
    )                                       -- convention in app code
""")

conn.execute("INSERT INTO processed_records (record_key, amount) VALUES (?, ?)",
             ("rec-1", 10.0))

# Plain INSERT of the SAME natural key: the database itself refuses it.
try:
    conn.execute("INSERT INTO processed_records (record_key, amount) VALUES (?, ?)",
                 ("rec-1", 10.0))
except sqlite3.IntegrityError as e:
    print("plain duplicate INSERT fails LOUDLY (as intended):", e)

# INSERT OR IGNORE (SQLite) / ON CONFLICT (record_key) DO NOTHING (ANSI SQL):
# re-inserting the same key is now a harmless no-op, and a NEW key still
# inserts normally - exactly the behavior you want in retry logic.
cur = conn.execute(
    "INSERT OR IGNORE INTO processed_records (record_key, amount) VALUES (?, ?)",
    ("rec-1", 10.0),
)
print("INSERT OR IGNORE of the same key -> rows actually inserted:", cur.rowcount)

cur = conn.execute(
    "INSERT OR IGNORE INTO processed_records (record_key, amount) VALUES (?, ?)",
    ("rec-2", 20.0),
)
print("INSERT OR IGNORE of a genuinely NEW key -> rows actually inserted:", cur.rowcount)
conn.commit()

print("final table:", conn.execute("SELECT * FROM processed_records ORDER BY record_key").fetchall())
print("\nPattern: enforce the constraint so bugs fail LOUD in general use,")
print("but reach for OR IGNORE / DO NOTHING specifically in the retry path,")
print("where 'already applied' is a success, not an error.")


"""
---------------------------------------------------------------------
6. IDEMPOTENCY KEYS FOR EVENT-DRIVEN / API-TRIGGERED PIPELINES  ⭐⭐⭐
---------------------------------------------------------------------
For a pipeline TRIGGERED by an event (a webhook, a queue message, an
API call) rather than a scheduled batch, there's usually no clean
"run_date" partition to delete-and-replace. The standard fix is an
IDEMPOTENCY KEY: every event carries a unique id (request_id / event_id),
and BEFORE doing any real work, the pipeline checks a "have I already
processed this exact id?" record. If yes, it's a no-op - the caller
gets treated as already-satisfied instead of the work running twice.
This is the same technique Stripe/PayPal-style payment APIs use to
make a retried "charge this card" call safe.
---------------------------------------------------------------------
"""

print("\n--- Idempotency Keys for Event-Driven Pipelines ---")

conn.execute("""
    CREATE TABLE processed_events (
        request_id TEXT PRIMARY KEY,   -- the idempotency key
        processed_at TEXT
    )
""")

account_balance = {"amount": 100.0}   # the "real work" this event performs
side_effect_log = []

def apply_credit_event(request_id, credit_amount):
    """Process one event exactly-once, no matter how many times this
    function is CALLED with the same request_id. The guard is a
    single atomic INSERT OR IGNORE into processed_events: if that
    insert actually added a row, this is the FIRST time we've seen
    this id, so do the real work; if rowcount is 0, someone (a queue
    redelivery, a retried webhook) already got this id in - skip."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO processed_events (request_id, processed_at) VALUES (?, datetime('now'))",
        (request_id,),
    )
    if cur.rowcount == 0:
        print(f"  event {request_id}: already processed - no-op (safe replay)")
        conn.commit()
        return False

    # Only reached the FIRST time this request_id is seen:
    account_balance["amount"] += credit_amount
    side_effect_log.append((request_id, credit_amount))
    conn.commit()
    print(f"  event {request_id}: applied credit of ${credit_amount:.2f}")
    return True

print("first delivery of event 'evt-9001':")
apply_credit_event("evt-9001", 25.0)
print("DUPLICATE delivery of the SAME event (queue redelivery / webhook retry):")
apply_credit_event("evt-9001", 25.0)
print("a genuinely DIFFERENT event still applies normally:")
apply_credit_event("evt-9002", 10.0)

print(f"\nfinal balance: ${account_balance['amount']:.2f} (started at $100.00)")
print("side effects actually applied:", side_effect_log)
assert account_balance["amount"] == 135.0   # 100 + 25 + 10, NOT 100 + 25 + 25 + 10
print("Correct: the replayed 'evt-9001' contributed NOTHING the second time.")


"""
---------------------------------------------------------------------
7. WHY THIS MATTERS FOR RETRY LOGIC  ⭐⭐⭐
---------------------------------------------------------------------
The Rate Limits & Retries notes (this repo's file on `tenacity`/
`backoff` and the hand-rolled `retry_with_backoff` decorator) cover
HOW to retry a flaky call. This file covers the other half of that
same problem: retrying is only SAFE if the thing being retried is
idempotent. A retry decorator has no idea whether the FIRST attempt's
side effect already landed before it timed out or errored - it just
calls the function again. If that function is a naive INSERT-only
load, `retry_with_backoff` will faithfully retry it straight into a
duplicate-data bug. If it's built on delete-then-insert, upsert, or
an idempotency-key guard (Sections 3-6), retrying is completely safe.
---------------------------------------------------------------------
"""

print("\n--- Why This Matters for Retry Logic ---")

def flaky_upsert_step(rows, attempt_tracker={"calls": 0}):
    """Simulates a load step that FAILS partway on its first attempt
    (e.g. a dropped connection after the first row) - a realistic
    reason a retry decorator would fire - then succeeds on retry."""
    attempt_tracker["calls"] += 1
    if attempt_tracker["calls"] == 1:
        # Even the "failed" attempt gets partway through - because it's
        # built on the upsert from Section 4, that partial write is
        # ALREADY idempotent, so re-running it is not a problem.
        load_orders_upsert(rows[:1])
        raise ConnectionError("connection dropped mid-batch (simulated)")
    load_orders_upsert(rows)
    return "load succeeded"

def simple_retry(fn, *args, max_attempts=3):
    """A minimal stand-in for retry_with_backoff (see L-59) - the
    point here isn't the backoff math, it's that blindly calling
    `fn` again is only safe because `fn` is idempotent."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args)
        except ConnectionError as e:
            print(f"  attempt {attempt} failed ({e}) - retrying is SAFE because")
            print("  the underlying write is an upsert, not a blind insert")
    raise RuntimeError("exhausted retries")

result = simple_retry(flaky_upsert_step, [("ord-2001", "pending", 15.0)])
print("final result:", result)
print("orders table after the retried step:",
      conn.execute("SELECT * FROM orders WHERE order_id = 'ord-2001'").fetchall())
print("exactly ONE row for ord-2001 despite the partial write + retry -")
print("that's only true because the write itself was made idempotent first.")


"""
---------------------------------------------------------------------
8. WHY THIS MATTERS FOR ORCHESTRATION TOOLS (AIRFLOW, ETC.)  ⭐⭐
---------------------------------------------------------------------
Orchestrators like Airflow don't just run each task once and forget
it - they're built around RE-EXECUTING tasks: a manual "Clear" +
retry on a failed task instance, a backfill that (re-)runs a DAG for
past `execution_date`/`data_interval` values, or `catchup=True`
replaying every missed schedule after a pause. Airflow's whole task
model assumes tasks can be safely re-run for the same
`execution_date` - which is only true if the task itself is
idempotent. This is exactly why real Airflow tasks are usually
written around a `{{ ds }}` (the run's logical date) as the SAME
partition key used in Section 3, not "today's wall-clock date."
---------------------------------------------------------------------
"""

print("\n--- Why This Matters for Orchestration (Airflow) ---")

try:
    from airflow.decorators import task   # not installed in this sandbox

    @task
    def load_sales_partition(ds=None):
        # `ds` is Airflow's injected logical/execution date for this
        # run - the SAME partition key idea as `run_date` above. Using
        # it (not datetime.now()) means a backfill for 2026-01-05
        # always reprocesses 2026-01-05, no matter what day it's
        # actually re-run on.
        load_delete_then_insert(ds)

except ImportError:
    print("airflow is not installed in this sandbox - showing the real")
    print("task code above as a comment, and simulating what re-running")
    print("(a backfill, or clearing a failed task) would do:")
    print()
    print("  Airflow clears/re-runs task 'load_sales_partition' for ds=2026-08-24 twice:")
    load_delete_then_insert("2026-08-24")
    first_sim = report_by_date("2026-08-24")
    load_delete_then_insert("2026-08-24")   # simulated "Clear" + re-run
    second_sim = report_by_date("2026-08-24")
    print(f"    run count -> {first_sim}, re-run count -> {second_sim} (identical)")
    print("  Because the task is built on delete-then-insert keyed by `ds`,")
    print("  Airflow can freely retry/backfill/clear this task without any")
    print("  risk of it duplicating that day's data.")


"""
---------------------------------------------------------------------
9. DESIGN PRINCIPLE: SEPARATE "COMPUTE" FROM "COMMIT"  ⭐⭐
---------------------------------------------------------------------
A subtler but very re-usable idea: split a pipeline step into a PURE
computation (extract + transform, no side effects, safe to call any
number of times) and a thin COMMIT step (the only place that touches
the database/API, and the only place that needs idempotency logic).
This keeps the "how do I make this idempotent" reasoning confined to
one small, testable function instead of smeared across the whole job.
---------------------------------------------------------------------
"""

print("\n--- Design Principle: Separate Compute from Commit ---")

def compute_daily_summary(run_date):
    """PURE function: no DB, no I/O, deterministic for a given
    run_date. Trivially safe to call 100 times - it has no side
    effects to duplicate in the first place."""
    rows = extract_daily_sales(run_date)
    total = sum(amount for _, _, amount in rows)
    return {"run_date": run_date, "num_rows": len(rows), "total": total}

def commit_daily_summary(summary):
    """The ONLY function that writes anything - and it's built on the
    delete-then-insert pattern from Section 3, so it's the ONE place
    idempotency has to be handled at all."""
    with conn:
        conn.execute("DELETE FROM sales_by_date WHERE run_date = ? AND product = 'SUMMARY'",
                     (summary["run_date"],))
        conn.execute(
            "INSERT INTO sales_by_date (run_date, product, amount) VALUES (?, 'SUMMARY', ?)",
            (summary["run_date"], summary["total"]),
        )

summary = compute_daily_summary(run_date)
print("computed (pure, side-effect-free):", summary)
commit_daily_summary(summary)
commit_daily_summary(summary)   # committing the identical summary twice
summary_rows = conn.execute(
    "SELECT COUNT(*) FROM sales_by_date WHERE run_date = ? AND product = 'SUMMARY'",
    (run_date,),
).fetchone()[0]
print("SUMMARY rows for this run_date after committing twice:", summary_rows)
assert summary_rows == 1
print("Exactly one SUMMARY row - re-committing the same computed result")
print("converged, it didn't accumulate.")

conn.close()


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Idempotent      -> run_job(x) == run_job(run_job(x)) in END STATE
                   (repeatable side effects, NOT "no side effects")
Non-idempotent  -> re-running with the same input changes the outcome
                   (classic case: blind INSERT on every run)

Fix patterns for the LOAD step:
  (A) DELETE-then-INSERT   -> replace a whole partition/batch key
                               (run_date, batch_id) atomically
  (B) UPSERT / MERGE        -> INSERT ... ON CONFLICT(natural_key)
                               DO UPDATE  (never key on a surrogate id)
  (C) UNIQUE + OR IGNORE     -> DB refuses true dup inserts loudly by
                               default; OR IGNORE / DO NOTHING makes
                               "already applied" a safe retry outcome
  Idempotency key            -> record request_id/event_id BEFORE doing
                               the work; second delivery = no-op

Ties to:
  Retries      -> a retried step calls the SAME function again; that's
                   only safe if the function is idempotent
  Orchestration -> Airflow "Clear"/backfill/catchup re-executes tasks
                   for a given `ds` (logical date) - only safe if tasks
                   are keyed and idempotent by that same `ds`

Design checklist:
  - partition/batch by a deterministic key (run_date, batch_id) -
    never "today" / wall-clock time
  - prefer upserts / delete-then-insert over blind INSERT
  - key writes to EXTERNAL systems (APIs, queues) by an idempotency
    key, checked before the work runs, not just before the write
  - separate pure COMPUTE from the one thin COMMIT step that actually
    needs idempotency handling
  - let a UNIQUE constraint be the last line of defense, not the
    only line of defense
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - IDEMPOTENT PIPELINES
=====================================================================

1. What does "idempotent" mean in the context of a data pipeline?
   Why is "produces no side effects" a WRONG definition, and what's
   the precise one?

2. How would you structure a Python ETL script to be re-runnable
   without duplicating data - walk through the actual write pattern
   you'd use.

3. In Section 2's `load_naive` function, exactly WHY did running it
   twice for the same `run_date` double the row count? What line of
   code is the actual bug?

4. Walk through the DELETE-then-INSERT fix in `load_delete_then_insert`.
   Why does it need to run inside a single transaction (`with conn:`)
   instead of as two separate statements?

5. What is an UPSERT? Write the SQL shape of an
   `INSERT ... ON CONFLICT ... DO UPDATE` and explain what
   `excluded.<column>` refers to.

6. Why must the conflict target of an upsert be a NATURAL/business
   key (like `order_id`) rather than an autoincrement surrogate id?
   What would go wrong if you keyed the conflict on the surrogate id
   instead?

7. What's the difference in intent between letting a UNIQUE
   constraint raise an IntegrityError on a duplicate insert, versus
   using `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`? When would
   you want each behavior?

8. Design an idempotency-key mechanism for a webhook-triggered
   pipeline: what table/data structure would you use, and exactly
   when do you check it relative to doing the real work?

9. In Section 6's `apply_credit_event`, why is the check-and-insert
   into `processed_events` done as a SINGLE `INSERT OR IGNORE`
   statement instead of a separate `SELECT` to check, followed by an
   `INSERT` if not found?

10. How would you make an ETL job idempotent AND fault-tolerant at
    the same time? Concretely, how does idempotency change what a
    retry decorator (like `retry_with_backoff`) is allowed to do
    safely?

11. Why do orchestration tools like Airflow encourage writing tasks
    against a logical `execution_date`/`ds` rather than
    `datetime.now()`? How does that connect to backfills and to the
    "Clear and retry" action on a failed task?

12. What's the benefit of separating a pipeline step into a pure
    "compute" function and a thin "commit" function, from an
    idempotency-design standpoint?

13. You inherit a pipeline that does a blind `INSERT` on every run
    and has been running in production for a year. What would you
    check first to find out whether it has already produced
    duplicate data, and how would you migrate it to one of the fix
    patterns without an outage?

14. Batch partition replacement (DELETE-then-INSERT by `run_date`)
    versus row-level upsert (by natural key) - when would you reach
    for one over the other?

15. Give a concrete example of a NON-idempotent operation that shows
    up in real pipelines (something other than a raw INSERT) - e.g.
    an operation involving `+=`, an auto-incrementing counter, or a
    "send an email/notification" side effect - and explain how you'd
    redesign it to be idempotent.
=====================================================================
"""
