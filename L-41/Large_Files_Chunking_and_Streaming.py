"""
=====================================================================
LARGE FILES - CHUNKING AND STREAMING - Complete Notes with Executable
Examples
=====================================================================

The core problem: a file on disk can be far bigger than the RAM
available to your process. A 20GB log file will not fit into an 8GB
machine's memory - but that doesn't mean you can't process it. The
answer is to never hold the WHOLE file in memory at once - only ever
hold ONE line, ONE row, or ONE fixed-size block of it at a time, plus
whatever small running total/aggregate you're building as you go.

This is exactly the same idea as the Generators notes file, applied
specifically to file I/O: a Python file object returned by `open()`
is ALREADY a lazy iterator under the hood - `for line in f` behaves
like a generator that yields one line, hands it to you, and only
reads the next line once you ask for it. `.read()` and `.readlines()`
throw that laziness away by eagerly materializing the entire file (or
every line of it) as one big string or list, right now, all at once.

This file covers, in increasing order of control: line-by-line
iteration, a hand-written generator function that parses/cleans each
record as it streams by, fixed-size batching with `itertools.islice`
for batch database inserts, pandas' `chunksize=` as the high-level
equivalent, and raw fixed-size byte-block reads for data that isn't
line-oriented at all (binary formats, or files with absurdly long
lines). It closes with a realistic mini ETL pipeline that strings all
of this together: stream a log file, parse it, filter it, and
aggregate it - never holding more than one record in memory.
=====================================================================
"""

import os
import csv
import random
import sqlite3
import tempfile
import tracemalloc
from datetime import datetime, timedelta
from itertools import islice

import pandas as pd

print("--- Overview ---")
print("A huge file doesn't have to fit in memory - only ONE line, row, or")
print("fixed-size chunk of it needs to be in memory at any given moment.")
print("The file object, generators, itertools.islice, and pandas' chunksize=")
print("are all different flavors of the exact same lazy-iteration idea.")


random.seed(42)   # reproducible demo data across runs

# ---------------------------------------------------------------------
# Build two moderately-sized demo files (NOT tiny, but nowhere near
# gigabytes) so the techniques below can be shown working on real
# files on disk. Content is produced by a GENERATOR and written line
# by line - we never build one giant string/list of the whole file's
# contents in memory just to create the demo, which would defeat the
# entire point of this file.
# ---------------------------------------------------------------------

N_LOG_LINES = 250_000
N_CSV_ROWS = 200_000
LEVELS = ["INFO", "WARNING", "ERROR", "DEBUG"]


def generate_log_lines(n):
    """Generator - yields one fake log line at a time. Real-world log
    files are messy, so every 50,000th line is deliberately corrupted
    to exercise the error-handling in Section 3 below."""
    start = datetime(2026, 1, 1)
    for i in range(n):
        if i > 0 and i % 50_000 == 0:
            yield "CORRUPTED_LINE_NO_STRUCTURE\n"
            continue
        level = "ERROR" if i % 17 == 0 else random.choice(LEVELS)
        ts = (start + timedelta(seconds=i)).isoformat()
        yield f"{ts} {level} event_id={i} message=processed_record_{i}\n"


def generate_csv_rows(n):
    """Generator - yields one fake CSV row (as a tuple) at a time. Every
    40,000th row is missing its last column, to simulate the ragged/
    malformed rows real ingestion pipelines have to tolerate."""
    for i in range(n):
        level = "ERROR" if i % 13 == 0 else random.choice(LEVELS)
        ts = f"2026-01-01T00:{(i // 60) % 60:02d}:{i % 60:02d}"
        if i > 0 and i % 40_000 == 0:
            yield (i, ts, level)                       # missing "amount"
        else:
            yield (i, ts, level, round(random.uniform(5.0, 500.0), 2))


log_path = tempfile.NamedTemporaryFile(delete=False, suffix=".log").name
with open(log_path, "w") as f:
    for line in generate_log_lines(N_LOG_LINES):   # streamed straight to disk
        f.write(line)

csv_path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "timestamp", "level", "amount"])
    for row in generate_csv_rows(N_CSV_ROWS):       # streamed straight to disk
        writer.writerow(row)

print(f"\ndemo log file: {log_path} ({os.path.getsize(log_path):,} bytes, "
      f"{N_LOG_LINES:,} lines)")
print(f"demo csv file: {csv_path} ({os.path.getsize(csv_path):,} bytes, "
      f"{N_CSV_ROWS:,} rows)")


"""
---------------------------------------------------------------------
1. THE CORE PROBLEM: .read() / .readlines() LOAD EVERYTHING AT ONCE  ⭐⭐⭐
---------------------------------------------------------------------
`f.read()` returns ONE giant string containing the entire file.
`f.readlines()` returns a LIST containing every single line, all
constructed and held in memory simultaneously, before your code gets
to process even the first one. For a file bigger than available RAM,
either call can crash the process (MemoryError) or thrash the OS into
swapping, long before you get any useful work done.

We can't safely allocate multiple gigabytes in this sandbox just to
prove a memory ceiling exists - but we CAN measure the real, honest
difference in PEAK memory between "materialize everything" and
"iterate lazily" on the same moderately-sized file, using the
standard library's `tracemalloc`. The ratio holds regardless of file
size; it just gets more dramatic (and more fatal) as the file grows.
---------------------------------------------------------------------
"""

print("\n--- The Core Problem: .readlines() vs Lazy Iteration ---")

tracemalloc.start()
with open(log_path) as f:
    naive_lines = f.readlines()          # EVERY line, in memory, right now
_, peak_readlines = tracemalloc.get_traced_memory()
tracemalloc.stop()
naive_line_count = len(naive_lines)
del naive_lines                          # release it - but the point stands

tracemalloc.start()
streamed_line_count = 0
with open(log_path) as f:
    for _ in f:                           # ONE line alive in memory at a time
        streamed_line_count += 1
_, peak_iteration = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f".readlines() peak memory for {naive_line_count:,} lines: "
      f"{peak_readlines / 1024:.1f} KB")
print(f"line-by-line iteration peak memory for {streamed_line_count:,} lines: "
      f"{peak_iteration / 1024:.1f} KB")
print(f"readlines() used ~{peak_readlines / max(peak_iteration, 1):.0f}x more "
      f"peak memory to process the IDENTICAL file")
print("On a 20GB file, readlines() tries to allocate ~20GB up front;")
print("iterating the file object never allocates more than one line's worth.")


"""
---------------------------------------------------------------------
2. THE FIX: A FILE OBJECT IS ALREADY A LAZY ITERATOR  ⭐⭐⭐
---------------------------------------------------------------------
`open()` doesn't hand you a container of lines - it hands you an
ITERATOR. A file object is its own iterator (`iter(f) is f`), and
`for line in f:` repeatedly calls its `__next__()` under the hood,
each call reading and returning exactly one more line from disk. This
is the SAME __iter__/__next__/StopIteration protocol the Generators
notes file covers in depth for `yield`-based generators - a file
object is effectively a built-in, C-implemented generator over lines.
Understanding one explains the other.
---------------------------------------------------------------------
"""

print("\n--- The Fix: The File Object IS Already a Lazy Iterator ---")

with open(log_path) as f:
    print("iter(f) is f:", iter(f) is f)     # a file is its own iterator
    first_line = next(f)                      # pulls exactly ONE line from disk
    second_line = next(f)                      # pulls exactly the NEXT line
print("first line pulled via next(f): ", first_line.strip())
print("second line pulled via next(f):", second_line.strip())
print("\nEvery `for line in f:` you've ever written was already streaming -")
print("the mistake to avoid is wrapping it in list(f) or f.readlines() and")
print("throwing that laziness away for no reason.")


"""
---------------------------------------------------------------------
3. A GENERATOR FUNCTION THAT PARSES/CLEANS RECORDS WHILE STREAMING  ⭐⭐⭐
---------------------------------------------------------------------
The classic interview ask: "write a generator function to read a huge
CSV/log file line-by-line and yield parsed, cleaned records - without
loading the file fully into memory." The pattern is always the same:
open the file, loop over it (lazy), transform/validate ONE line into
ONE clean record inside the loop, `yield` it, and move on. If a line
is malformed, skip it and keep going - one bad row must never kill an
otherwise-good multi-hundred-thousand-line ingestion job.
---------------------------------------------------------------------
"""

print("\n--- A Generator That Parses a Log File Line-by-Line ---")


def parse_log_line(line):
    """Turns one raw log line into a clean dict, or raises ValueError."""
    parts = line.strip().split(" ", 3)
    if len(parts) != 4 or not parts[2].startswith("event_id=") \
            or not parts[3].startswith("message="):
        raise ValueError(f"malformed line: {line!r}")
    timestamp_str, level, event_id_part, message_part = parts
    return {
        "timestamp": timestamp_str,
        "level": level,
        "event_id": int(event_id_part.removeprefix("event_id=")),
        "message": message_part.removeprefix("message="),
    }


def stream_log_records(path):
    """Generator - yields ONE parsed, cleaned record dict at a time.
    At most one raw line and one parsed dict are ever alive at once,
    no matter how many millions of lines `path` contains."""
    with open(path) as f:                # file stays open only while
        for raw_line in f:                # this generator is being consumed
            try:
                yield parse_log_line(raw_line)
            except ValueError as e:
                print(f"  skipping malformed line: {e}")
                continue


records_preview = stream_log_records(log_path)
print("type of stream_log_records(...):", type(records_preview))
print("nothing has been read from disk yet - the generator hasn't started")
print("first 2 clean records, pulled on demand:")
print(" ", next(records_preview))
print(" ", next(records_preview))

print("\n--- The Same Pattern for a Huge CSV File (using csv.DictReader) ---")


def stream_csv_records(path):
    """Generator - yields ONE cleaned/typed CSV row at a time. csv.reader/
    DictReader already iterate the underlying file lazily; this wrapper
    just adds type conversion and drops rows that fail to convert."""
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                yield {
                    "id": int(row["id"]),
                    "timestamp": row["timestamp"],
                    "level": row["level"],
                    "amount": float(row["amount"]),   # None -> TypeError
                }
            except (TypeError, ValueError) as e:
                print(f"  skipping malformed csv row {row}: {e}")
                continue


csv_preview = stream_csv_records(csv_path)
print("first 2 clean CSV records:")
print(" ", next(csv_preview))
print(" ", next(csv_preview))


"""
---------------------------------------------------------------------
4. CHUNKED READING WITH itertools.islice - FIXED-SIZE BATCHES  ⭐⭐⭐
---------------------------------------------------------------------
Streaming ONE record at a time is memory-safe, but many real
operations (bulk database inserts, sending records to an API in
batches, writing Parquet row groups) are far more efficient in fixed-
size BATCHES than one-at-a-time. `itertools.islice(iterator, n)`
pulls exactly the next `n` items off a shared iterator without
touching what comes after - repeat it in a loop against the SAME
iterator object and you get consecutive, non-overlapping batches,
still only ever materializing one batch (not the whole file) at once.
(Python 3.12+ ships `itertools.batched()` as a built-in shortcut for
exactly this pattern; this sandbox runs 3.11, so we build it by hand
below - the underlying technique is identical either way.)

DATA ENGINEERING USE CASE: batch-inserting a huge ingestion file into
a database 1,000 rows at a time, instead of either one-row-at-a-time
(slow - one round trip per row) or all-rows-at-once (memory-unsafe).
---------------------------------------------------------------------
"""

print("\n--- Chunked Batches via itertools.islice ---")


def batch_iterable(iterable, batch_size):
    """Generator - yields successive lists of up to `batch_size` items
    pulled from `iterable`, without ever holding more than one batch."""
    iterator = iter(iterable)             # islice re-anchors to THIS iterator
    while True:
        batch = list(islice(iterator, batch_size))   # pulls the NEXT n items
        if not batch:                                  # iterator exhausted
            return
        yield batch


conn = sqlite3.connect(":memory:")        # stand-in for a real DB connection -
conn.execute(                              # the executemany() call below is
    "CREATE TABLE events (event_id INTEGER, level TEXT, timestamp TEXT)"
)                                           # identical against psycopg2/pyodbc

total_inserted = 0
batch_count = 0
for batch in batch_iterable(stream_log_records(log_path), 1000):
    rows = [(r["event_id"], r["level"], r["timestamp"]) for r in batch]
    conn.executemany(                      # one round trip per 1,000 rows,
        "INSERT INTO events VALUES (?, ?, ?)", rows   # not per row
    )
    total_inserted += len(rows)
    batch_count += 1
    if batch_count <= 3 or batch_count % 60 == 0:
        print(f"  batch {batch_count}: inserted {len(rows)} rows "
              f"({total_inserted:,} total so far)")

conn.commit()
db_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"batches: {batch_count}, rows in DB: {db_count:,}")
conn.close()


"""
---------------------------------------------------------------------
5. PANDAS' chunksize= - THE HIGH-LEVEL EQUIVALENT  ⭐⭐
---------------------------------------------------------------------
`pandas.read_csv(path, chunksize=N)` doesn't return a DataFrame at
all - it returns an ITERATOR of DataFrames, each with (at most) N
rows, read from disk on demand exactly like the generator patterns
above. You process/aggregate each chunk and discard it before the
next one is read, so a file with tens of millions of rows can be
summarized on a machine that could never hold the whole thing as one
DataFrame. `on_bad_lines="skip"` mirrors the malformed-row handling
from Section 3, so one ragged row doesn't kill the whole read.
---------------------------------------------------------------------
"""

print("\n--- Pandas chunksize= for read_csv() ---")

total_rows = 0
total_amount = 0.0
error_rows = 0
chunk_reader = pd.read_csv(csv_path, chunksize=25_000, on_bad_lines="skip")
for chunk_num, chunk in enumerate(chunk_reader, start=1):   # one 25k-row
    total_rows += len(chunk)                                  # DataFrame alive
    total_amount += chunk["amount"].sum()                      # at a time
    error_rows += int((chunk["level"] == "ERROR").sum())
    print(f"  processed chunk {chunk_num} ({len(chunk)} rows) - "
          f"running total_amount so far: {total_amount:,.2f}")

print(f"\nfinal totals across {total_rows:,} rows (no full DataFrame ever "
      f"held in memory):")
print(f"  total_amount = {total_amount:,.2f}")
print(f"  ERROR rows   = {error_rows:,}")


"""
---------------------------------------------------------------------
6. RAW FIXED-SIZE BYTE BLOCKS - THE NON-LINE-ORIENTED CASE  ⭐⭐
---------------------------------------------------------------------
Line-by-line iteration assumes the data actually HAS meaningful lines.
For binary formats (images, Parquet footers, network captures) or
text with pathologically long "lines" (a single-line 5GB minified
JSON blob), you instead read fixed-size BYTE blocks in a loop with
`f.read(block_size)` until it returns an empty bytes object, which is
Python's file-API signal for "end of file reached."
---------------------------------------------------------------------
"""

print("\n--- Raw Fixed-Size Byte Blocks (Non-Line-Oriented Reads) ---")

BLOCK_SIZE = 65_536   # 64 KiB per read - independent of line boundaries
total_bytes = 0
newline_count = 0
with open(log_path, "rb") as f:
    while True:
        block = f.read(BLOCK_SIZE)     # AT MOST 64 KiB ever in memory here
        if not block:                   # b"" (empty bytes) means EOF
            break
        total_bytes += len(block)
        newline_count += block.count(b"\n")   # still countable without lines

print(f"bytes read via block reads: {total_bytes:,} "
      f"(os.path.getsize agrees: {os.path.getsize(log_path):,})")
print(f"newlines counted across blocks: {newline_count:,} "
      f"(expected {N_LOG_LINES:,} - matches, even though we never")
print("split on lines - newline boundaries can straddle block edges, and")
print("bytes.count() still finds them correctly across separate .read() calls.")


"""
---------------------------------------------------------------------
7. MINI PIPELINE: STREAM -> PARSE -> FILTER -> AGGREGATE  ⭐⭐⭐
---------------------------------------------------------------------
This is the realistic version of "write a generator to lazily read
and process a large log file": chain a file-line generator, a parsing
generator, and a filtering generator expression together. Because
every stage is lazy, NOTHING runs until the final `for`/`sum` pulls
the first value - and at any instant, only one line/record is in
flight through the whole pipeline, regardless of the file's size.
---------------------------------------------------------------------
"""

print("\n--- Mini ETL Pipeline: Stream, Parse, Filter ERRORs, Count ---")

tracemalloc.start()
records = stream_log_records(log_path)                       # stage 1: parse
error_records = (r for r in records if r["level"] == "ERROR")  # stage 2: filter
error_count = 0
for _ in error_records:                                        # stage 3: reduce
    error_count += 1
_, peak_pipeline = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"ERROR lines found: {error_count:,} (out of {N_LOG_LINES:,} total lines)")
print(f"peak memory for the FULL streamed pipeline: {peak_pipeline / 1024:.1f} KB")
print(f"compare to Section 1's .readlines() peak: {peak_readlines / 1024:.1f} KB "
      f"for the SAME file")
print("The pipeline's memory is flat regardless of file size - only readlines()")
print("scales with N. This is the pattern to reach for whenever an interviewer")
print("asks how you'd process a file 'too large to fit into memory.'")


print("\n--- Cleanup ---")
os.remove(log_path)
os.remove(csv_path)
print(f"removed temporary demo files: {log_path}, {csv_path}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
f.read() / f.readlines()        -> loads the WHOLE file / ALL lines
                                    into memory at once (avoid on big files)

for line in f:                  -> file object is its own lazy iterator,
                                    ONE line in memory at a time

generator function + yield      -> parse/clean ONE record per line as
                                    it streams by (skip bad lines, keep going)

itertools.islice(iter(x), n)    -> pulls the NEXT n items from a shared
    (looped)                       iterator -> fixed-size batches for
                                    bulk DB inserts / batch API calls

pd.read_csv(path, chunksize=N)  -> returns an ITERATOR of N-row
                                    DataFrames; aggregate per chunk,
                                    never hold the full file as one df

f.read(block_size) in a loop    -> fixed-size BYTE blocks for binary
    (mode "rb")                     data or non-line-oriented text;
                                    b"" return value means EOF

Full pipeline pattern:
    stream lines -> parse/clean each -> filter -> aggregate
    every stage lazy => O(1) memory regardless of file size
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - LARGE FILES: CHUNKING AND STREAMING
=====================================================================

1. How do you process a file that is too large to fit into memory?

2. Write a generator function to read a huge CSV file line-by-line
   and yield cleaned/parsed records without loading it fully into
   memory. (Extremely common!)

3. Write a generator to lazily read and process a large log file -
   walk through what `stream_log_records()` in this file does and why
   it never holds more than one record in memory.

4. Why does `f.readlines()` defeat the purpose of streaming, even
   though `for line in f:` on the same file object does not? What,
   concretely, is different about what each one returns?

5. Explain why a plain `open()` file object satisfies the iterator
   protocol on its own (`iter(f) is f`) - how does this relate to how
   a `yield`-based generator implements the same protocol?

6. In `batch_iterable()`, why must `iter(iterable)` be created ONCE,
   outside the loop, and reused across every call to
   `itertools.islice()`? What would go wrong if you passed the
   original `iterable` fresh into `islice()` on every loop iteration?

7. How would you efficiently insert a million rows into a database
   from Python, and why is batching (e.g. 1,000 rows via
   `executemany()`) preferable to both one-row-at-a-time inserts and
   one giant insert of everything at once?

8. How do you handle a dataset that doesn't fit into memory using
   pandas? What does `chunksize=` actually return from `read_csv()`,
   and how is it different from just calling `read_csv()` normally
   and slicing the result afterward?

9. What does `on_bad_lines="skip"` do in `pd.read_csv()`, and how
   does that compare to the manual `try/except` malformed-row handling
   in `stream_csv_records()`?

10. When would you need to read a file in raw fixed-size byte blocks
    (`f.read(block_size)`) instead of iterating it line-by-line? Give
    a concrete example of data where line-based iteration breaks down.

11. In Section 6, why is `newline_count` still correct even though
    each 64 KiB block is read independently, and a real newline
    character could in principle fall right at the boundary between
    two separate `.read()` calls?

12. `stream_log_records()` opens the file with a `with` block INSIDE
    the generator function itself, not in the caller. Under what
    circumstances does that file actually get closed, and what would
    happen if the generator were created but never fully iterated?

13. Read a JSON Lines (`.jsonl`) file and process it in chunks - how
    would you adapt the `stream_log_records()` pattern in this file to
    parse a `.jsonl` file instead of a whitespace-delimited log file?

14. What is the difference between chunking by a fixed NUMBER OF
    LINES/ROWS (Section 4's batching, pandas' `chunksize=`) versus
    chunking by a fixed NUMBER OF BYTES (Section 6)? When does each
    one matter?

15. How would you design `stream_log_records()` to support resuming
    after a crash partway through a huge file, without re-processing
    everything already ingested? (Hint: think about `f.tell()` and
    `f.seek()`, and what you'd need to persist as a checkpoint.)
=====================================================================
"""
