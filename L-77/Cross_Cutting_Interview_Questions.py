"""
=====================================================================
CROSS-CUTTING INTERVIEW QUESTIONS - The Top 15 "Must-Prepare" Answers
=====================================================================

This is the CAPSTONE file of the repo (L-77, the last one). It is NOT a
16th deep-dive into a brand-new topic - every idea below was already
taught in full depth in an earlier numbered file. Instead, this file
answers the syllabus's "Top 15 Must-Prepare Interview Questions
(Cross-Cutting)" section the way you'd actually answer them OUT LOUD in
a live interview: a crisp spoken-style explanation, a small correct
snippet proving the key point on the spot, and a pointer to the earlier
file for anyone who wants the full derivation.

Think of this file as a final review sheet, not a lesson. If a question
below feels too fast, go re-read the file it cross-references - that's
where the "why", the edge cases, and the buggy-vs-fixed pairs live.
=====================================================================
"""

import os
import sys
import time
import random
import tempfile
import functools
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np
import pandas as pd
from pydantic import BaseModel, ValidationError

print("--- Overview ---")
print("15 questions. Each one already has a dedicated deep-dive file in")
print("this repo - here they are answered CONCISELY, with real running")
print("code, the way you'd talk through them in an actual interview.")


"""
---------------------------------------------------------------------
1. WRITE A GENERATOR TO LAZILY READ AND PROCESS A LARGE LOG FILE  ⭐⭐⭐
---------------------------------------------------------------------
A generator function reads the file ONE LINE at a time via `for line in
f`, holding only the current line in memory - so a 50 GB log file costs
the same tiny memory footprint as a 5 KB one. The `yield` suspends the
function between lines instead of computing everything up front.
Full depth: see L-25 Generators.py and L-41 Large_Files_Chunking_and_Streaming.py
---------------------------------------------------------------------
"""

print("\n--- 1. Generator for Lazily Processing a Large Log File ---")


def _make_sample_log():
    lines = [
        "2026-08-25 10:00:01 INFO  pipeline started\n",
        "2026-08-25 10:00:02 ERROR db connection timeout\n",
        "2026-08-25 10:00:03 INFO  retrying connection\n",
        "2026-08-25 10:00:04 ERROR disk quota exceeded\n",
        "2026-08-25 10:00:05 INFO  pipeline finished\n",
    ]
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w") as f:
        f.writelines(lines)
    return path


def stream_error_lines(path):
    """Yields ERROR lines one at a time - the file handle's own internal
    buffer does the reading; nothing forces the whole file into a list."""
    with open(path) as f:
        for line in f:              # lazy: one line "in flight" at a time
            if "ERROR" in line:
                yield line.strip()


log_path = _make_sample_log()
error_gen = stream_error_lines(log_path)
print("calling stream_error_lines() returns a generator, no I/O yet:", error_gen)
print("pulling ERROR lines lazily, one at a time:")
for err in error_gen:
    print("  ", err)
os.remove(log_path)

print("Full depth: see L-25 Generators.py and L-41 Large_Files_Chunking_and_Streaming.py")


"""
---------------------------------------------------------------------
2. HOW DO YOU DEDUPLICATE MILLIONS OF RECORDS EFFICIENTLY?  ⭐⭐⭐
---------------------------------------------------------------------
Never nested-loop compare (O(n^2)). Convert each record to something
hashable and track what's been seen in a SET - O(1) average membership
checks, so the whole job is O(n). If insertion order matters, use
`dict.fromkeys(...)`, which dedupes AND preserves first-seen order.
Full depth: see L-14 Deduplication_Techniques.py and L-10 Collections_Module.py
---------------------------------------------------------------------
"""

print("\n--- 2. Deduplicating Millions of Records Efficiently ---")

records = [
    {"id": 1, "email": "a@x.com"},
    {"id": 2, "email": "b@x.com"},
    {"id": 1, "email": "a@x.com"},   # exact duplicate
    {"id": 3, "email": "c@x.com"},
    {"id": 2, "email": "b@x.com"},   # exact duplicate
]

seen = set()
deduped = []
for rec in records:
    key = tuple(sorted(rec.items()))       # dicts aren't hashable - a sorted tuple is
    if key not in seen:
        seen.add(key)
        deduped.append(rec)

print("original count:", len(records), "-> deduped count:", len(deduped))
print("deduped:", deduped)

ids = [5, 3, 5, 5, 7, 3, 9]
unique_ordered = list(dict.fromkeys(ids))   # dict preserves first-seen insertion order
print("dict.fromkeys dedup of", ids, "->", unique_ordered)

print("Full depth: see L-14 Deduplication_Techniques.py and L-10 Collections_Module.py")


"""
---------------------------------------------------------------------
3. EXPLAIN THE GIL AND ITS IMPACT ON PARALLEL DATA PROCESSING  ⭐⭐⭐
---------------------------------------------------------------------
CPython's Global Interpreter Lock lets only ONE thread execute Python
bytecode at any instant, even on a multi-core machine. For CPU-BOUND
work (parsing, hashing, math), adding threads does NOT speed things up
- they take turns on the same core. Threads only help when they spend
time WAITING (I/O), because the GIL is released during that wait.
Full depth: see L-48 GIL.py and L-49 Multithreading_vs_Multiprocessing.py
---------------------------------------------------------------------
"""

print("\n--- 3. The GIL and Its Impact on Parallel Data Processing ---")


def cpu_bound_work(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


N = 3_000_000

start = time.perf_counter()
cpu_bound_work(N)
cpu_bound_work(N)
sequential_time = time.perf_counter() - start

start = time.perf_counter()
t1 = threading.Thread(target=cpu_bound_work, args=(N,))
t2 = threading.Thread(target=cpu_bound_work, args=(N,))
t1.start()
t2.start()
t1.join()
t2.join()
threaded_time = time.perf_counter() - start

print(f"sequential, 2x CPU-bound calls: {sequential_time:.3f}s")
print(f"same work, 2 THREADS:           {threaded_time:.3f}s")
print("No speedup (often slightly worse) - the GIL serializes bytecode")
print("execution, so CPU-bound threads just take turns on one core.")

print("Full depth: see L-48 GIL.py and L-49 Multithreading_vs_Multiprocessing.py")


"""
---------------------------------------------------------------------
4. MERGE TWO LARGE DATASETS WITHOUT RUNNING OUT OF MEMORY  ⭐⭐⭐
---------------------------------------------------------------------
Loading both sides fully into memory (e.g. two giant dicts) costs O(n +
m) memory. If both inputs are already sorted by the join key (true of
most exports and DB cursors with ORDER BY), a STREAMING sort-merge join
walks both with two cursors and holds only ONE record per side at a
time - O(1) extra memory regardless of dataset size.
Full depth: see L-41 Large_Files_Chunking_and_Streaming.py and L-47 Memory_Optimization_in_Pandas.py
---------------------------------------------------------------------
"""

print("\n--- 4. Merging Two Large Datasets Without Running Out of Memory ---")


def sorted_merge_join(left_sorted_iter, right_sorted_iter, key=lambda x: x[0]):
    """Both inputs must already be sorted by `key`. Walks them like a
    zipper - never materializes either side fully in memory."""
    left_iter = iter(left_sorted_iter)
    right_iter = iter(right_sorted_iter)
    l = next(left_iter, None)
    r = next(right_iter, None)
    while l is not None and r is not None:
        lk, rk = key(l), key(r)
        if lk == rk:
            yield (l, r)
            l = next(left_iter, None)
            r = next(right_iter, None)
        elif lk < rk:
            l = next(left_iter, None)
        else:
            r = next(right_iter, None)


# Stand-in for two chunks streamed from separate Parquet files / DB cursors,
# each already sorted by customer_id.
customers = [(1, "Alice"), (2, "Bob"), (4, "Dana")]
orders = [(1, "order#100"), (2, "order#101"), (3, "order#102"), (4, "order#103")]

joined = list(sorted_merge_join(customers, orders))
print("streamed merge-join result [(customer), (order)]:")
for pair in joined:
    print("  ", pair)

print("Full depth: see L-41 Large_Files_Chunking_and_Streaming.py and L-47 Memory_Optimization_in_Pandas.py")


"""
---------------------------------------------------------------------
5. LIST vs TUPLE vs SET vs DICT - WHEN TO USE EACH IN PIPELINE DESIGN  ⭐⭐⭐
---------------------------------------------------------------------
list: mutable, ordered, allows duplicates -> row-by-row streaming data.
tuple: immutable -> hashable -> usable as a dict/set key, and cheaper
than a list for fixed-shape records. set: unordered, O(1) average
membership + free deduplication. dict: O(1) average keyed lookup ->
joins, lookups, and structured config/records, and preserves insertion
order since 3.7.
Full depth: see L-7 Lists_Tuples_Sets_and_Dicts.py
---------------------------------------------------------------------
"""

print("\n--- 5. list vs tuple vs set vs dict in Pipeline Design ---")

sample_list = [1, 2, 3]
sample_tuple = (1, 2, 3)
sample_set = {1, 2, 3}
sample_dict = {"a": 1, "b": 2, "c": 3}

print("sizeof list :", sys.getsizeof(sample_list), "bytes - mutable, ordered, allows dupes")
print("sizeof tuple:", sys.getsizeof(sample_tuple), "bytes - immutable, hashable, cheaper")
print("sizeof set  :", sys.getsizeof(sample_set), "bytes - O(1) avg membership + dedup")
print("sizeof dict :", sys.getsizeof(sample_dict), "bytes - O(1) avg keyed lookup")

big_list = list(range(200_000))
big_set = set(big_list)
target = 199_999

t0 = time.perf_counter()
target in big_list
list_time = time.perf_counter() - t0

t0 = time.perf_counter()
target in big_set
set_time = time.perf_counter() - t0

print(f"\n'{target} in list' (O(n) scan): {list_time * 1e6:.1f} microseconds")
print(f"'{target} in set'  (O(1) avg):  {set_time * 1e6:.1f} microseconds")
print("\nPipeline rule of thumb: list for ordered streaming rows, tuple for")
print("fixed immutable records/keys, set for membership tests + dedup,")
print("dict for keyed joins/lookups and step configuration.")

print("Full depth: see L-7 Lists_Tuples_Sets_and_Dicts.py")


"""
---------------------------------------------------------------------
6. HOW WOULD YOU MAKE AN ETL JOB IDEMPOTENT AND FAULT-TOLERANT?  ⭐⭐⭐
---------------------------------------------------------------------
Idempotent = running the SAME batch N times leaves the destination in
the SAME final state as running it once - achieved by UPSERTING on a
stable primary/natural key instead of blind INSERTs. Fault-tolerant =
one bad record shouldn't abort the whole batch - wrap each record's
load in its own try/except and keep going.
Full depth: see L-62 Idempotent_Pipelines.py and L-63 Batch_vs_Streaming.py
---------------------------------------------------------------------
"""

print("\n--- 6. Making an ETL Job Idempotent and Fault-Tolerant ---")

warehouse = {}   # stand-in for a real table, keyed by primary key


def load_batch(recs):
    loaded, failed = 0, 0
    for rec in recs:
        try:
            warehouse[rec["id"]] = rec   # upsert by key - safe to repeat
            loaded += 1
        except Exception as e:              # one bad record can't kill the batch
            failed += 1
            print(f"   skipping bad record {rec!r}: {e}")
    return loaded, failed


batch = [{"id": 1, "amount": 10.0}, {"id": 2, "amount": 20.0}]
load_batch(batch)
print("after 1st run:       ", warehouse)
load_batch(batch)   # simulate a retry after a crash - SAME batch re-sent
load_batch(batch)
print("after 3 reruns of the SAME batch:", warehouse, "(no duplication)")

print("Full depth: see L-62 Idempotent_Pipelines.py and L-63 Batch_vs_Streaming.py")


"""
---------------------------------------------------------------------
7. WRITE A DECORATOR THAT RETRIES ON FAILURE WITH EXPONENTIAL BACKOFF  ⭐⭐⭐
---------------------------------------------------------------------
A decorator wraps a call in a loop: on exception, sleep for a delay
that DOUBLES each attempt (1x, 2x, 4x, ...) instead of hammering a
flaky dependency at a fixed rate, then re-raise once attempts run out.
`functools.wraps` preserves the wrapped function's name/docstring.
Full depth: see L-20 Decorators_and_Higher_Order_Functions.py and L-59 Rate_Limits_and_Retries.py
---------------------------------------------------------------------
"""

print("\n--- 7. A Retry Decorator with Exponential Backoff ---")


def retry_with_backoff(max_attempts=4, base_delay=0.01):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))   # 1x, 2x, 4x, ...
                    print(f"   attempt {attempt} failed ({e}); retrying in {delay:.3f}s")
                    time.sleep(delay)
        return wrapper
    return decorator


_calls = {"n": 0}


@retry_with_backoff(max_attempts=4, base_delay=0.01)
def flaky_api_call():
    _calls["n"] += 1
    if _calls["n"] < 3:
        raise ConnectionError("simulated transient network error")
    return "200 OK"


print("result:", flaky_api_call())
print("total attempts made:", _calls["n"])

print("Full depth: see L-20 Decorators_and_Higher_Order_Functions.py and L-59 Rate_Limits_and_Retries.py")


"""
---------------------------------------------------------------------
8. WHY IS PARQUET BETTER THAN CSV FOR DATA WAREHOUSING?  ⭐⭐⭐
---------------------------------------------------------------------
Parquet is COLUMNAR (a query touching 2 of 50 columns reads only those
2), carries an embedded SCHEMA + dtypes (no re-inferring int vs string
on every load), and compresses far better than row-oriented text CSV
because each column's values are similar and stored contiguously.
Full depth: see L-40 Columnar_Formats.py and L-38 CSV_Handling.py
---------------------------------------------------------------------
"""

print("\n--- 8. Why Parquet Beats CSV for Data Warehousing ---")

df_pq_demo = pd.DataFrame(
    {"id": range(5000), "region": (["US", "EU"] * 2500), "amount": [1.5] * 5000}
)

csv_path = os.path.join(tempfile.gettempdir(), "_l77_demo.csv")
parquet_path = os.path.join(tempfile.gettempdir(), "_l77_demo.parquet")
df_pq_demo.to_csv(csv_path, index=False)
df_pq_demo.to_parquet(parquet_path, index=False)

csv_bytes = os.path.getsize(csv_path)
parquet_bytes = os.path.getsize(parquet_path)
print(f"CSV size:     {csv_bytes:,} bytes")
print(f"Parquet size: {parquet_bytes:,} bytes  ({csv_bytes / parquet_bytes:.1f}x smaller)")

only_amount = pd.read_parquet(parquet_path, columns=["amount"])   # column pruning
print("reading just 1 of 3 columns from parquet (column pruning):", only_amount.shape)
print("\nParquet wins on: columnar layout, embedded schema/dtypes, and")
print("far better compression than row-oriented, untyped text CSV.")

os.remove(csv_path)
os.remove(parquet_path)

print("Full depth: see L-40 Columnar_Formats.py and L-38 CSV_Handling.py")


"""
---------------------------------------------------------------------
9. HOW DO YOU HANDLE MALFORMED / MISSING DATA DURING INGESTION?  ⭐⭐⭐
---------------------------------------------------------------------
Two complementary layers: (1) column-level cleanup with pandas -
`pd.to_numeric(errors="coerce")` turns unparsable values into NaN
instead of crashing the load, then `fillna`/`dropna` per a chosen
policy; (2) row-level VALIDATION with pydantic to quarantine individual
bad records instead of letting one bad row kill the whole ingest job.
Full depth: see L-45 Handling_Missing_Data.py and L-67 Data_Validation.py
---------------------------------------------------------------------
"""

print("\n--- 9. Handling Malformed / Missing Data During Ingestion ---")

raw_rows = [
    {"id": 1, "price": "19.99", "qty": 3},
    {"id": 2, "price": "not_a_number", "qty": 5},   # malformed price
    {"id": 3, "price": "9.50", "qty": None},        # missing qty
]

df_raw = pd.DataFrame(raw_rows)
df_raw["price"] = pd.to_numeric(df_raw["price"], errors="coerce")   # malformed -> NaN
print("after to_numeric(errors='coerce'):")
print(df_raw)
df_raw["qty"] = df_raw["qty"].fillna(0)
df_ingest_clean = df_raw.dropna(subset=["price"])
print("\nafter fillna(qty) + dropna(price):")
print(df_ingest_clean)


class IngestRow(BaseModel):
    id: int
    price: float
    qty: int


validated, quarantined = [], []
for r in raw_rows:
    try:
        validated.append(IngestRow(**r))
    except ValidationError as e:
        quarantined.append((r, str(e).splitlines()[0]))

print("\nrow-level validation: OK =", len(validated), " quarantined =", len(quarantined))
for bad, reason in quarantined:
    print("   quarantined:", bad, "->", reason)

print("Full depth: see L-45 Handling_Missing_Data.py and L-67 Data_Validation.py")


"""
---------------------------------------------------------------------
10. EXPLAIN *args / **kwargs WITH A PIPELINE CONFIGURATION EXAMPLE  ⭐⭐⭐
---------------------------------------------------------------------
`*args` collects any number of extra POSITIONAL arguments into a tuple;
`**kwargs` collects any number of extra NAMED arguments into a dict.
Together they let a pipeline runner accept an arbitrary number of step
functions plus arbitrary named configuration, without a rigid fixed
signature - exactly how real orchestration frameworks are built.
Full depth: see L-16 Args_and_Kwargs.py
---------------------------------------------------------------------
"""

print("\n--- 10. *args / **kwargs for Pipeline Configuration ---")


def run_pipeline(*steps, **config):
    data = config.get("initial_data", [])
    verbose = config.get("verbose", False)
    for step in steps:
        data = step(data)
        if verbose:
            print(f"   after {step.__name__}: {data}")
    return data


pipeline_result = run_pipeline(
    lambda d: [x * 2 for x in d],
    lambda d: [x for x in d if x > 5],
    initial_data=[1, 3, 5, 7],
    verbose=True,
)
print("final result:", pipeline_result)

print("Full depth: see L-16 Args_and_Kwargs.py")


"""
---------------------------------------------------------------------
11. PANDAS apply() vs VECTORIZED OPS - WHICH IS FASTER AND WHY?  ⭐⭐⭐
---------------------------------------------------------------------
`apply()` calls a Python-level function once PER ROW - full interpreter
overhead every single time. A vectorized expression (`s * 2 + 1`) pushes
the WHOLE column into compiled NumPy loops over contiguous memory in
one shot. Vectorized is almost always faster; `apply` is a last resort
for logic that truly can't be expressed as a vector operation.
Full depth: see L-46 Apply_Map_and_Vectorization.py
---------------------------------------------------------------------
"""

print("\n--- 11. Pandas apply() vs Vectorized Operations ---")

s = pd.Series(np.random.randint(1, 100, size=300_000))

t0 = time.perf_counter()
apply_result = s.apply(lambda x: x * 2 + 1)
apply_time = time.perf_counter() - t0

t0 = time.perf_counter()
vector_result = s * 2 + 1
vector_time = time.perf_counter() - t0

assert apply_result.equals(vector_result)
print(f"apply():    {apply_time:.4f}s")
print(f"vectorized: {vector_time:.4f}s  ({apply_time / vector_time:.0f}x faster)")
print("Same result, very different cost - vectorized wins by avoiding a")
print("Python function call for every single row.")

print("Full depth: see L-46 Apply_Map_and_Vectorization.py")


"""
---------------------------------------------------------------------
12. HOW WOULD YOU PARALLELIZE PROCESSING OF 100 INDEPENDENT FILES?  ⭐⭐⭐
---------------------------------------------------------------------
Each file is independent -> an "embarrassingly parallel" workload: hand
the list of paths to a worker pool and let it map one function over
all of them. Use `ProcessPoolExecutor` when the per-file work is
CPU-bound (parsing/computing); use `ThreadPoolExecutor` instead when
each "file" is really a network/S3 fetch (I/O-bound).
Full depth: see L-50 Concurrent_Futures.py and L-71 Dask.py
---------------------------------------------------------------------
"""

print("\n--- 12. Parallelizing Processing of Many Independent Files ---")


def _make_files(n):
    paths = []
    for i in range(n):
        fd, path = tempfile.mkstemp(suffix=f"_{i}.txt")
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(str(x) for x in range(100)))
        paths.append(path)
    return paths


def sum_file(path):
    with open(path) as f:
        return sum(int(line) for line in f)


file_paths = _make_files(12)   # stand-in for "100 independent files"
try:
    with ProcessPoolExecutor(max_workers=4) as pool:
        totals = list(pool.map(sum_file, file_paths))
    print("processed", len(file_paths), "files across a 4-worker PROCESS pool")
except Exception as e:
    print("ProcessPoolExecutor unavailable here, falling back to sequential:", e)
    totals = [sum_file(p) for p in file_paths]

print("per-file totals:", totals)
for p in file_paths:
    os.remove(p)

print("Full depth: see L-50 Concurrent_Futures.py and L-71 Dask.py")


"""
---------------------------------------------------------------------
13. MULTIPROCESSING vs MULTITHREADING - A DATA ENGINEERING EXAMPLE  ⭐⭐⭐
---------------------------------------------------------------------
Threads share one process (and one GIL): great for I/O-bound waits
(API/DB calls) because the GIL is released while waiting. Processes
each get their OWN interpreter and GIL: necessary for CPU-bound work
(parsing, transforming) to actually use multiple cores. Below, threads
overlap simulated network waits; processes speed up real CPU work.
Full depth: see L-49 Multithreading_vs_Multiprocessing.py
---------------------------------------------------------------------
"""

print("\n--- 13. Multiprocessing vs Multithreading: a DE Example ---")


def fake_api_call(i):
    time.sleep(0.05)                         # I/O-bound wait - GIL released
    return f"payload-{i}"


def cpu_heavy_transform(n):
    return sum(x * x for x in range(n))       # CPU-bound - pure bytecode


t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(fake_api_call, range(8)))
thread_io_time = time.perf_counter() - t0
print(f"8 'API calls' via THREAD pool:           {thread_io_time:.3f}s (waits overlap)")

t0 = time.perf_counter()
try:
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(cpu_heavy_transform, [1_500_000] * 4))
    process_cpu_time = time.perf_counter() - t0
    print(f"4 CPU-heavy transforms via PROCESS pool: {process_cpu_time:.3f}s")
except Exception as e:
    print("ProcessPoolExecutor unavailable here:", e)

print("\nI/O-bound (API/DB/file waits) -> threads or asyncio.")
print("CPU-bound (parsing, math, hashing)   -> processes.")

print("Full depth: see L-49 Multithreading_vs_Multiprocessing.py")


"""
---------------------------------------------------------------------
14. CONNECT PYTHON TO A SQL DATABASE AND BULK INSERT SAFELY  ⭐⭐⭐
---------------------------------------------------------------------
"Safely" means two things: PARAMETERIZED placeholders (never f-string
values into SQL - that's a SQL-injection hole), and ONE transaction for
the whole batch via `executemany` + a single `commit()` - not one
commit per row, which is what actually makes bulk loading fast.
Full depth: see L-52 Connecting_to_Databases.py and L-55 Bulk_Inserts_and_Batch_Processing.py
---------------------------------------------------------------------
"""

print("\n--- 14. Connecting to a SQL Database and Bulk Inserting Safely ---")

conn = sqlite3.connect(":memory:")   # stand-in for psycopg2/pyodbc against a real server
conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, name TEXT, amount REAL)")

bulk_rows = [(i, f"event_{i}", float(i) * 1.5) for i in range(1, 10001)]

t0 = time.perf_counter()
conn.executemany(
    "INSERT INTO events (id, name, amount) VALUES (?, ?, ?)", bulk_rows   # ? placeholders
)
conn.commit()   # ONE commit for all 10,000 rows
elapsed = time.perf_counter() - t0

count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"bulk-inserted {count:,} rows via executemany() in {elapsed:.3f}s")
print("sample row:", conn.execute("SELECT * FROM events WHERE id = 1").fetchone())
conn.close()

print("\n# against a real warehouse (Postgres), the equivalent safe pattern:")
print("#   psycopg2.extras.execute_values(cur, 'INSERT INTO events VALUES %s', rows)")
print("# or a native COPY ... FROM for the fastest possible bulk load.")

print("Full depth: see L-52 Connecting_to_Databases.py and L-55 Bulk_Inserts_and_Batch_Processing.py")


"""
---------------------------------------------------------------------
15. DESIGN AN END-TO-END PIPELINE: API EXTRACT -> PANDAS TRANSFORM ->
    LOAD INTO A WAREHOUSE  ⭐⭐⭐
---------------------------------------------------------------------
This is the capstone question - it's every earlier concept in one
sentence. The walkthrough: (1) EXTRACT paginated JSON from an API,
validating each record on the way in so one malformed row doesn't sink
the batch (Q9); (2) TRANSFORM with pandas - fill missing fields,
compute derived columns, dedupe by natural key (Q5, Q11); (3) LOAD via
an idempotent UPSERT keyed by primary key, so reruns never duplicate
rows (Q6, Q14). Below is a small but genuinely complete version of
exactly that, run three times end-to-end to prove it's idempotent.
Full depth: this question ties together nearly every file in the repo;
see especially L-58 Requests_Library.py, L-60 Parsing_API_Responses.py,
L-44 GroupBy_Merge_Join_Pivot.py, L-62 Idempotent_Pipelines.py, and
L-64 Apache_Airflow_Basics.py for how this gets orchestrated on a
schedule in production.
---------------------------------------------------------------------
"""

print("\n--- 15. End-to-End Pipeline: API Extract -> Pandas Transform -> Warehouse Load ---")


class ApiRecord(BaseModel):
    id: int
    name: str
    amount: float
    category: str | None = None


def extract_from_api(page: int) -> list[dict]:
    """Stands in for `requests.get(url, params={"page": page}).json()["results"]`
    against a real paginated REST API - see L-58 Requests_Library.py and
    L-60 Parsing_API_Responses.py for the real HTTP + pagination code."""
    fake_pages = {
        1: [
            {"id": 1, "name": "widget", "amount": 9.99, "category": "hardware"},
            {"id": 2, "name": "gadget", "amount": "bad_value"},   # malformed -> quarantined
            {"id": 3, "name": "gizmo", "amount": 4.50},            # missing category
        ],
        2: [
            {"id": 4, "name": "doohickey", "amount": 19.99, "category": "hardware"},
        ],
    }
    return fake_pages.get(page, [])   # page 3+ is empty -> natural end of pagination


def extract_all():
    validated, quarantined = [], []
    for page in (1, 2, 3):
        for row in extract_from_api(page):
            try:
                validated.append(ApiRecord(**row))
            except ValidationError as e:
                quarantined.append((row, str(e).splitlines()[0]))
    return validated, quarantined


def transform(records) -> pd.DataFrame:
    frame = pd.DataFrame([r.model_dump() for r in records])
    frame["category"] = frame["category"].fillna("unknown")     # handle missing data
    frame["amount_usd"] = (frame["amount"] * 1.0).round(2)        # derived column
    return frame.drop_duplicates(subset=["id"])                  # dedupe by natural key


def load(frame: pd.DataFrame, warehouse_conn: sqlite3.Connection):
    """UPSERT keyed on id - re-running this exact batch any number of times
    leaves the warehouse table in the SAME final state (idempotent load)."""
    warehouse_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS warehouse_events (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            amount_usd REAL
        )
        """
    )
    warehouse_conn.executemany(
        """
        INSERT INTO warehouse_events (id, name, category, amount_usd)
        VALUES (:id, :name, :category, :amount_usd)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            amount_usd = excluded.amount_usd
        """,
        frame[["id", "name", "category", "amount_usd"]].to_dict("records"),
    )
    warehouse_conn.commit()


warehouse_conn = sqlite3.connect(":memory:")


def run_pipeline_once(run_label):
    records, quarantined = extract_all()
    frame = transform(records)
    load(frame, warehouse_conn)
    row_count = warehouse_conn.execute("SELECT COUNT(*) FROM warehouse_events").fetchone()[0]
    print(
        f"[{run_label}] upserted {len(frame)} row(s), "
        f"quarantined {len(quarantined)} malformed row(s), "
        f"warehouse now has {row_count} row(s)"
    )


run_pipeline_once("run 1")
run_pipeline_once("run 2 (re-run - proves idempotency)")
run_pipeline_once("run 3 (re-run again)")

print("\nfinal warehouse contents:")
for row in warehouse_conn.execute("SELECT * FROM warehouse_events ORDER BY id"):
    print("  ", row)

warehouse_conn.close()

print("\nFull depth: see L-58 Requests_Library.py, L-60 Parsing_API_Responses.py,")
print("L-44 GroupBy_Merge_Join_Pivot.py, L-62 Idempotent_Pipelines.py, and")
print("L-64 Apache_Airflow_Basics.py")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
1.  Large file          -> generator + `for line in f`, one line at a time
2.  Millions of dupes    -> hash to a set (O(1) avg); dict.fromkeys for order
3.  GIL                  -> 1 thread runs bytecode at a time; no CPU speedup
4.  Merge w/o OOM        -> streaming sort-merge join, two cursors, O(1) mem
5.  list/tuple/set/dict  -> ordered / immutable+hashable / membership+dedup / keyed lookup
6.  Idempotent ETL       -> upsert by key + per-record try/except
7.  Retry decorator      -> loop + try/except + delay *= 2 each attempt
8.  Parquet > CSV        -> columnar + embedded schema + better compression
9.  Malformed data       -> to_numeric(errors="coerce") + pydantic quarantine
10. *args/**kwargs       -> flexible positional steps + named config
11. apply vs vectorized  -> vectorized wins: whole column in one C/NumPy pass
12. 100 files            -> worker pool .map() over the file list
13. multiproc vs thread  -> I/O -> threads/asyncio; CPU -> processes
14. Bulk insert safely   -> ? placeholders + executemany + one commit
15. End-to-end pipeline  -> validate on extract, clean+derive in pandas,
                            upsert-load for idempotency

Pro tip (from the syllabus): interviewers rarely ask "what is Python" -
they hand you a DATA PROBLEM (messy JSON, dedup, a file too big for
memory, a retry-safe pipeline) and want to watch you SOLVE it in
Python. Practice by writing the small script, not by memorizing the
definition.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CROSS-CUTTING TOP 15
=====================================================================

1. Write a generator to lazily read and process a large log file.

2. How do you deduplicate millions of records efficiently in Python?

3. Explain the GIL and its impact on parallel data processing.

4. Design a Python function to merge two large datasets without
   running out of memory.

5. Difference between list, tuple, set, dict - and when to use each in
   pipeline design.

6. How would you make an ETL job idempotent and fault-tolerant?

7. Write a decorator that retries a function on failure with
   exponential backoff.

8. Why is Parquet better than CSV for data warehousing?

9. How do you handle malformed or missing data during ingestion?

10. Explain *args/**kwargs with a pipeline configuration example.

11. Compare Pandas apply() vs vectorized operations - which is faster
    and why?

12. How would you parallelize processing of 100 independent files?

13. Explain multiprocessing vs multithreading with a data engineering
    example.

14. How do you connect Python to a SQL database and perform a bulk
    insert safely?

15. Walk through how you'd design an end-to-end pipeline: extract from
    an API, transform with Pandas, load into a warehouse.
=====================================================================
"""
