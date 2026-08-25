"""
=====================================================================
BULK INSERTS AND BATCH PROCESSING FOR PERFORMANCE - Complete Notes
with Executable Examples
=====================================================================

Inserting rows into a database ONE AT A TIME, in a Python loop, is
one of the most common performance mistakes in data engineering code
- and one of the most frequently probed topics in DE interviews
("how would you load a million rows efficiently?").

There are TWO separate costs stacked on top of each other in the
naive pattern:

    1. PER-STATEMENT OVERHEAD - every call to `.execute()` means the
       database driver has to parse/plan the SQL, bind parameters,
       and (for a real client-server database) make a NETWORK ROUND
       TRIP to the server and wait for a reply. Do that 1,000,000
       times and you pay that tax 1,000,000 times.

    2. PER-COMMIT OVERHEAD - `.commit()` is not just bookkeeping. In
       a real database it forces a DISK FSYNC (or worse, a full WAL
       flush) so the transaction is durable even if the machine loses
       power right after. Fsyncs are physical disk operations -
       committing after every single row means paying that durability
       tax once per row instead of once per batch.

The fix is BATCHING: group many rows into a single `executemany()`
call, and commit once per batch (a few thousand rows) instead of
once per row. This module benchmarks the naive approach against
progressively better patterns using stdlib `sqlite3` against a real
on-disk temp file - no external database server needed. Every
technique shown here (batching, `executemany`, explicit transactions,
chunked loading) transfers DIRECTLY to `psycopg2` (Postgres),
`pyodbc`/`pymysql` (SQL Server/MySQL), and any other Python DB-API
2.0 driver - the API shapes are nearly identical, and the underlying
network/fsync costs the tests expose are, if anything, LARGER on a
real client-server database than they are here on local sqlite3.
=====================================================================
"""

import csv
import os
import sqlite3
import tempfile
import time

print("--- Overview ---")
print("Naive row-by-row inserts pay a per-statement AND a per-commit")
print("tax on every row. Batching with executemany() + one commit per")
print("batch removes almost all of that tax. This is the single")
print("biggest lever for bulk-load performance in Python DB-API code.")


"""
---------------------------------------------------------------------
1. BENCHMARK SETUP: A REAL ON-DISK SQLITE DATABASE  ⭐⭐
---------------------------------------------------------------------
We use a real temp FILE (not ":memory:") on purpose: an in-memory
database never touches disk, so it would hide the fsync cost that
`.commit()` incurs on a real database. A temp file gives us genuine
disk I/O behavior while still needing zero external infrastructure.
---------------------------------------------------------------------
"""

print("\n--- Benchmark Setup ---")

TMP_DIR = tempfile.mkdtemp(prefix="bulk_insert_demo_")


def fresh_connection(db_name):
    """Create a brand-new on-disk sqlite3 DB file with an empty 'events' table."""
    path = os.path.join(TMP_DIR, db_name)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, user_id INTEGER, "
        "event_type TEXT, payload TEXT)"
    )
    conn.commit()
    return conn


def gen_rows(n, start=0):
    """Generate n fake (id, user_id, event_type, payload) rows - stand-in for
    records that would normally come from an API, a queue, or a source file."""
    return [
        (start + i, (start + i) % 5000, "click", f"payload-{start + i}")
        for i in range(n)
    ]


print(f"Temp sqlite DB files will live in: {TMP_DIR}")
print("Using a real on-disk file (not ':memory:') so .commit() pays a real")
print("fsync cost, just like it would against Postgres/MySQL.")


"""
---------------------------------------------------------------------
2. APPROACH A: .execute() + .commit() PER ROW (THE WORST PATTERN)  ⭐⭐⭐
---------------------------------------------------------------------
This is the pattern almost everyone writes by accident the first
time: loop over the data, INSERT one row, commit, repeat. It is slow
for TWO independent reasons: a fresh statement round trip per row,
AND a fresh disk fsync per row. Because of the fsync cost, this
pattern is run on a SMALLER row count here (N_NAIVE) - nobody would
actually run this pattern on a million rows, which is exactly the
point being demonstrated.
---------------------------------------------------------------------
"""

print("\n--- Approach A: execute() + commit() per row ---")

N_NAIVE = 8_000     # kept small deliberately - see the docstring above
N_MAIN = 60_000      # used for the three faster approaches below
CHUNK_SIZE = 5_000

rows_naive = gen_rows(N_NAIVE)

conn_a = fresh_connection("approach_a.db")
start = time.perf_counter()
for row in rows_naive:
    conn_a.execute(
        "INSERT INTO events (id, user_id, event_type, payload) VALUES (?, ?, ?, ?)",
        row,
    )
    conn_a.commit()          # <-- fsync-equivalent cost paid on EVERY row
time_a = time.perf_counter() - start
conn_a.close()

per_row_a = time_a / N_NAIVE
print(f"Inserted {N_NAIVE:,} rows, committing every row: {time_a:.3f}s "
      f"({per_row_a * 1000:.4f} ms/row)")
# extrapolate linearly so we can compare fairly against the N_MAIN approaches below
extrapolated_a_at_main = per_row_a * N_MAIN
print(f"Extrapolated cost for {N_MAIN:,} rows at this rate: "
      f"{extrapolated_a_at_main:.2f}s (not actually run - would be needlessly slow)")


"""
---------------------------------------------------------------------
3. APPROACH B: .execute() PER ROW, ONE .commit() AT THE END  ⭐⭐⭐
---------------------------------------------------------------------
Same per-row statement overhead as Approach A, but the fsync tax is
now paid ONCE for the whole batch instead of once per row. This
alone is usually the single biggest win available, because commit is
the expensive part in a real database.
---------------------------------------------------------------------
"""

print("\n--- Approach B: execute() per row, single commit at the end ---")

rows_main = gen_rows(N_MAIN)

conn_b = fresh_connection("approach_b.db")
start = time.perf_counter()
for row in rows_main:
    conn_b.execute(
        "INSERT INTO events (id, user_id, event_type, payload) VALUES (?, ?, ?, ?)",
        row,
    )
conn_b.commit()               # <-- ONE fsync for all N_MAIN rows
time_b = time.perf_counter() - start
conn_b.close()

print(f"Inserted {N_MAIN:,} rows, single commit: {time_b:.3f}s "
      f"({time_b / N_MAIN * 1000:.4f} ms/row)")


"""
---------------------------------------------------------------------
4. APPROACH C: executemany() WITH ALL ROWS IN ONE CALL  ⭐⭐⭐
---------------------------------------------------------------------
executemany() hands the driver the WHOLE list of parameter tuples at
once instead of making Python call back into the C extension once
per row. Locally, against sqlite3, the per-call overhead being saved
is tiny (a few microseconds of Python/C boundary crossing) - but
against a real client-server database, each of those "calls" would
otherwise be a separate network round trip, so the real-world win is
usually much larger than what this local benchmark shows.
---------------------------------------------------------------------
"""

print("\n--- Approach C: executemany() in a single call ---")

conn_c = fresh_connection("approach_c.db")
start = time.perf_counter()
conn_c.executemany(
    "INSERT INTO events (id, user_id, event_type, payload) VALUES (?, ?, ?, ?)",
    rows_main,
)
conn_c.commit()
time_c = time.perf_counter() - start
conn_c.close()

print(f"Inserted {N_MAIN:,} rows, executemany() single batch: {time_c:.3f}s "
      f"({time_c / N_MAIN * 1000:.4f} ms/row)")


"""
---------------------------------------------------------------------
5. APPROACH D: CHUNKED executemany() - THE REALISTIC PRODUCTION
   PATTERN  ⭐⭐⭐
---------------------------------------------------------------------
Approach C is fast, but it requires holding ALL rows (and the whole
open transaction) in memory/at once, which doesn't scale to a real
1M+ row load streamed from a file or API. The pattern actually used
in production is CHUNKED executemany(): batch N rows at a time
(a few thousand is a common sweet spot), call executemany() per
chunk, and commit per chunk. This bounds both memory usage and the
size of any single transaction, while keeping almost all of the
executemany() speed benefit.
---------------------------------------------------------------------
"""

print("\n--- Approach D: chunked executemany() ---")

conn_d = fresh_connection("approach_d.db")
start = time.perf_counter()
for i in range(0, N_MAIN, CHUNK_SIZE):
    chunk = rows_main[i:i + CHUNK_SIZE]
    conn_d.executemany(
        "INSERT INTO events (id, user_id, event_type, payload) VALUES (?, ?, ?, ?)",
        chunk,
    )
    conn_d.commit()          # commit once per CHUNK, not once per row
time_d = time.perf_counter() - start
conn_d.close()

n_chunks = -(-N_MAIN // CHUNK_SIZE)   # ceiling division
print(f"Inserted {N_MAIN:,} rows in {n_chunks} chunks of up to {CHUNK_SIZE:,}: "
      f"{time_d:.3f}s ({time_d / N_MAIN * 1000:.4f} ms/row)")

print("\n--- Summary: Speedup Ratios (all normalized to N_MAIN rows) ---")
print(f"{'approach':<45}{'time (s)':>10}{'speedup vs A':>15}")
print(f"{'A: execute+commit per row (extrapolated)':<45}"
      f"{extrapolated_a_at_main:>10.2f}{1.0:>15.1f}x")
print(f"{'B: execute per row, commit once':<45}{time_b:>10.3f}"
      f"{extrapolated_a_at_main / time_b:>15.1f}x")
print(f"{'C: executemany, single batch':<45}{time_c:>10.3f}"
      f"{extrapolated_a_at_main / time_c:>15.1f}x")
print(f"{'D: executemany, chunked (production pattern)':<45}{time_d:>10.3f}"
      f"{extrapolated_a_at_main / time_d:>15.1f}x")
print("\nThe A -> B jump (removing per-row commits) is typically the LARGEST")
print("single win, because commit is a durability barrier (fsync), not just")
print("bookkeeping. B -> C/D (batching statements) saves further overhead")
print("that is small locally but becomes much larger over a real network.")


"""
---------------------------------------------------------------------
6. WHY THIS MATTERS EVEN MORE AGAINST A REAL CLIENT-SERVER DATABASE
   ⭐⭐⭐
---------------------------------------------------------------------
This entire benchmark ran against sqlite3, which lives IN-PROCESS -
there is no network between your Python code and the "server". Every
`.execute()` call above only pays Python-to-C-extension overhead,
which is measured in microseconds.

Against Postgres, MySQL, SQL Server, Snowflake, etc., your Python
process talks to a SEPARATE server process, usually over a TCP
socket - often over the network entirely, not just localhost. Every
round trip now costs:
    - TCP/TLS overhead for the request and response
    - the server parsing and planning the statement (unless using a
      prepared/parameterized statement, which helps but doesn't
      eliminate the round trip itself)
    - waiting for the acknowledgement before your loop can continue

That per-statement cost, which was microseconds here, is typically
0.1-2+ milliseconds in a real network round trip - and `.commit()`
against a real database ALSO still has to fsync a WAL/redo log to
disk for durability, exactly like it did in this demo. In production,
the gap between "one row per statement" and "batched executemany()"
is usually MUCH bigger than what this local sqlite3 demo shows,
precisely because there's a real network hop being eliminated on top
of the fsync savings.
---------------------------------------------------------------------
"""

print("\n--- Why Production Gains Are Even Bigger ---")
print("sqlite3 is in-process: no network round trip per execute() call.")
print("Postgres/MySQL/etc. are client-server: every execute() is a real")
print("network round trip PLUS the same fsync-on-commit cost shown above.")
print("=> batching helps here; it helps MORE against a real server.")


"""
---------------------------------------------------------------------
7. EXPLICIT TRANSACTIONS: ALL-OR-NOTHING BULK LOADS  ⭐⭐⭐
---------------------------------------------------------------------
A bulk load should either fully succeed or fully fail - you never
want a batch that dies halfway through to leave the table in a
half-loaded, inconsistent state. Wrapping the whole batch in ONE
transaction (BEGIN ... COMMIT, with a ROLLBACK on failure) gives you
that guarantee for free. This section demonstrates both the BROKEN
(no transaction boundary around the batch) and FIXED (explicit
transaction) versions against a batch that fails partway through
because of a UNIQUE constraint violation.
---------------------------------------------------------------------
"""

print("\n--- Explicit Transactions: All-or-Nothing Bulk Loads ---")


def build_users_table(conn):
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT UNIQUE)"
    )
    conn.commit()


# a batch where the 4th row deliberately reuses an id that's already in the
# table below - simulating a bad/duplicate record arriving mid-batch from a
# messy upstream source (a very realistic ETL failure mode)
good_batch = [(1, "alice"), (2, "bob"), (3, "carol")]
bad_batch_causing_violation = [(4, "dave"), (5, "erin"), (2, "duplicate-bob")]

print("\nBROKEN: committing row-by-row with no transaction boundary")
conn_broken = fresh_connection("txn_broken.db")
build_users_table(conn_broken)
conn_broken.executemany("INSERT INTO users VALUES (?, ?)", good_batch)
conn_broken.commit()
try:
    for row in bad_batch_causing_violation:
        conn_broken.execute("INSERT INTO users VALUES (?, ?)", row)
        conn_broken.commit()       # each row is durably committed AS IT GOES
except sqlite3.IntegrityError as e:
    print(f"  hit constraint violation partway through: {e}")

leftover = conn_broken.execute("SELECT id, name FROM users ORDER BY id").fetchall()
print(f"  table now contains {len(leftover)} rows: {leftover}")
print("  -> 'dave' and 'erin' were committed BEFORE the bad row was hit -")
print("     the table is now PARTIALLY loaded, which is exactly what we")
print("     don't want from a batch that's supposed to be one logical unit.")
conn_broken.close()

print("\nFIXED: the whole batch runs inside ONE explicit transaction")
conn_fixed = fresh_connection("txn_fixed.db")
build_users_table(conn_fixed)
conn_fixed.executemany("INSERT INTO users VALUES (?, ?)", good_batch)
conn_fixed.commit()
try:
    conn_fixed.execute("BEGIN")                     # explicit transaction start
    conn_fixed.executemany(
        "INSERT INTO users VALUES (?, ?)", bad_batch_causing_violation
    )
    conn_fixed.commit()                              # would commit ALL 3 rows...
except sqlite3.IntegrityError as e:
    print(f"  hit constraint violation: {e}")
    conn_fixed.rollback()                            # ...but instead, undo ALL of them
    print("  rolled back the ENTIRE failed batch")

leftover = conn_fixed.execute("SELECT id, name FROM users ORDER BY id").fetchall()
print(f"  table now contains {len(leftover)} rows: {leftover}")
print("  -> NEITHER 'dave' nor 'erin' got left behind - the table is back")
print("     to exactly its pre-batch state, ready to safely retry the load.")
conn_fixed.close()


"""
---------------------------------------------------------------------
8. DATA ENGINEERING USE CASE: STREAMING A LARGE CSV INTO CHUNKED
   BULK INSERTS  ⭐⭐⭐
---------------------------------------------------------------------
The realistic ETL shape: a source file far bigger than you want to
hold in memory at once, loaded into a database in fixed-size chunks.
This combines file CHUNKING/STREAMING (read only a bounded number of
rows into memory at a time) with BATCHED executemany() loads, so
memory use stays flat regardless of file size and every insert stays
batched. This is the pattern to reach for when asked "how would you
load a huge CSV into a database in Python?".
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Chunked CSV -> Chunked Bulk Load ---")


def load_csv_in_chunks(csv_path, conn, table, columns, chunk_size=5_000):
    """Stream a CSV file into `table` using bounded-memory chunked bulk inserts.

    Only `chunk_size` rows are ever held in memory at once (the file itself
    is read lazily, line by line, by csv.reader) - this is the same
    streaming principle as reading a huge log file line-by-line, applied to
    loading its contents into a database.
    """
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

    total_loaded = 0
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        next(reader)              # skip header row
        chunk = []
        for record in reader:
            chunk.append(tuple(record))
            if len(chunk) >= chunk_size:
                conn.executemany(insert_sql, chunk)
                conn.commit()      # commit per chunk - bounds transaction size too
                total_loaded += len(chunk)
                chunk.clear()      # release this chunk's memory before reading more
        if chunk:                  # flush the final partial chunk
            conn.executemany(insert_sql, chunk)
            conn.commit()
            total_loaded += len(chunk)
    return total_loaded


# build a realistic sample CSV to load - stands in for a large extract file
csv_path = os.path.join(TMP_DIR, "orders_extract.csv")
N_CSV_ROWS = 25_000
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["order_id", "customer_id", "amount"])
    for i in range(N_CSV_ROWS):
        writer.writerow([i, i % 3000, round(9.99 + (i % 500) / 10, 2)])

conn_etl = fresh_connection("etl_orders.db")
conn_etl.execute(
    "CREATE TABLE orders (order_id INTEGER, customer_id INTEGER, amount REAL)"
)
conn_etl.commit()

start = time.perf_counter()
loaded = load_csv_in_chunks(
    csv_path, conn_etl, "orders", ["order_id", "customer_id", "amount"],
    chunk_size=CHUNK_SIZE,
)
etl_time = time.perf_counter() - start

row_count = conn_etl.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
print(f"Streamed {N_CSV_ROWS:,}-row CSV -> loaded {loaded:,} rows "
      f"({row_count:,} rows now in table) in {etl_time:.3f}s")
print("Memory footprint stayed flat at ~CHUNK_SIZE rows regardless of how")
print("large the source CSV actually is - this same function works whether")
print("the file has 25,000 rows or 25,000,000.")
conn_etl.close()


"""
---------------------------------------------------------------------
9. THE NEXT LEVEL: DATABASE-NATIVE BULK LOADERS (COPY, ETC.)  ⭐⭐
---------------------------------------------------------------------
Once executemany() isn't fast enough, the next level up is a
database-NATIVE bulk-load path that bypasses the normal SQL statement
protocol entirely. On Postgres, that's the `COPY` command - via
psycopg2's `copy_expert()` (or `copy_from()`), you stream a
file-like object straight into a table using Postgres's binary/text
bulk-load protocol, which is dramatically faster than any number of
INSERT statements. Every major warehouse has an equivalent: MySQL's
`LOAD DATA INFILE`, Redshift/Snowflake/BigQuery's native `COPY`/
`LOAD` commands that bulk-ingest directly from S3/GCS/blob storage.
These are usually the FASTEST real-world option for very large loads
- faster than pure DB-API code can ever be, because they skip
per-row SQL parsing entirely.

No live Postgres server exists in this sandbox, so the call below is
attempted for real (showing the true, correct psycopg2 API) and the
expected connection failure is caught and explained.
---------------------------------------------------------------------
"""

print("\n--- The Next Level: Database-Native Bulk Loaders (COPY) ---")

import io

try:
    import psycopg2

    # This is genuine, production-correct psycopg2 code - it just has
    # nowhere to connect to in this sandbox.
    conn_pg = psycopg2.connect(
        host="localhost", dbname="warehouse", user="etl", password="...",
        connect_timeout=2,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows_main[:1000]:
        writer.writerow(row)
    buf.seek(0)
    with conn_pg.cursor() as cur:
        cur.copy_expert(
            "COPY events (id, user_id, event_type, payload) FROM STDIN WITH CSV",
            buf,
        )
    conn_pg.commit()
    conn_pg.close()
    print("Loaded via real Postgres COPY (unexpected in this sandbox!)")
except Exception as e:
    print(f"No live Postgres server here, as expected: {type(e).__name__}: {e}")
    print("In production, against a real Postgres instance, the code above")
    print("streams rows straight into the table via COPY - typically 5-20x")
    print("faster than even chunked executemany() for very large loads,")
    print("because it skips per-row SQL parsing/planning entirely.")
    print("Equivalent 'next level' tools: MySQL LOAD DATA INFILE, Redshift/")
    print("Snowflake/BigQuery native COPY/LOAD from cloud storage.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Naive worst case  -> execute() + commit() PER ROW
                     pays per-statement AND per-commit (fsync) cost
                     on every single row

Remove commit cost -> execute() per row, ONE commit() at the end
                      (usually the single biggest win - fsync is the
                      expensive part of a naive loop)

Remove statement    -> executemany(all_rows) in one call
overhead               (bigger win on a real network DB than locally)

Production pattern  -> chunked executemany(): batch N rows (e.g. 5,000),
                        commit once per chunk - bounds memory AND
                        transaction size while keeping the speed

Data safety          -> wrap the whole batch in one explicit
                        transaction (BEGIN ... COMMIT / rollback()) so
                        a mid-batch failure leaves ZERO partial rows,
                        not a half-loaded table

Local sqlite3 cost of a "round trip" -> microseconds (in-process call)
Real client-server DB round trip     -> ~0.1-2+ ms over the network
                        => batching wins are BIGGER in production than
                           in this local demo, not smaller

ETL pattern          -> stream the source file in bounded chunks,
                        executemany() + commit per chunk -> flat
                        memory use regardless of file size

Fastest of all       -> database-native bulk loaders: Postgres COPY
                        (psycopg2 copy_expert/copy_from), MySQL LOAD
                        DATA INFILE, warehouse-native COPY/LOAD from
                        cloud storage - skip SQL parsing entirely
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - BULK INSERTS AND BATCH PROCESSING
=====================================================================

1. How would you efficiently insert 1 million rows into a database
   from Python?

2. How do you connect Python to a SQL database and perform a bulk
   insert safely (i.e., without risking a half-loaded table)?

3. Why is calling `.commit()` after every single row so much slower
   than calling it once per batch, in terms of what `.commit()`
   actually does at the database/disk level?

4. In this file, Approach A (execute+commit per row) and Approach B
   (execute per row, single commit) do the SAME number of
   `.execute()` calls. Why is B still dramatically faster than A?

5. What does `executemany()` actually save you over calling
   `.execute()` in a Python loop, and why would that saving be much
   larger against Postgres/MySQL than against local sqlite3?

6. Why does this file deliberately use a much SMALLER row count for
   the naive per-row-commit approach (Approach A) than for the other
   three approaches?

7. What is a reasonable batch/chunk size for `executemany()` in a
   real ETL job, and what are the trade-offs of choosing a chunk size
   that's too small vs. too large?

8. Why should a bulk load be wrapped in a single explicit transaction
   instead of letting each row commit independently? Walk through
   what happens to already-inserted rows if row 50,000 of 100,000
   violates a constraint, under each approach.

9. In the `users` table demo, explain exactly why the "BROKEN"
   version ends up with 'dave' and 'erin' permanently in the table
   after the batch fails, while the "FIXED" version ends up with
   neither.

10. How would you load a CSV file too large to fit in memory into a
    database table, keeping memory usage flat? Describe the role of
    `chunk_size` in `load_csv_in_chunks()`.

11. What is Postgres's `COPY` command, and why can it be faster than
    even a well-batched `executemany()`? When would you reach for it
    instead of plain DB-API code?

12. Why does a network round trip to a real client-server database
    typically cost far more than a single sqlite3 `.execute()` call
    made in-process? How does that change the size of the
    naive-vs-batched performance gap you'd expect to see in
    production versus in a local sqlite3 benchmark?

13. If you're using SQLAlchemy instead of raw DB-API code, how would
    you achieve the same bulk-insert performance benefits shown here
    (e.g., `Session.bulk_insert_mappings()` / `execute()` with a list
    of parameter dicts vs. adding ORM objects one at a time)?

14. What could go wrong if you set `chunk_size` to something like
    1,000,000 on a table with many indexes or foreign key
    constraints, even though executemany() itself would happily
    accept a list that large?

15. How would you make a chunked bulk-load ETL job idempotent, so
    that re-running it after a partial failure doesn't duplicate rows
    that were already committed in earlier chunks?
=====================================================================
"""
