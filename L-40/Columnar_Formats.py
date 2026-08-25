"""
=====================================================================
COLUMNAR FILE FORMATS - Parquet, Avro, ORC & Why They Matter for
Big Data - Complete Notes with Executable Examples
=====================================================================

Every data engineering interview eventually asks some version of
"why not just use CSV?" The honest answer is: CSV is fine for small,
human-readable data, but it falls apart at the scale data engineers
actually operate at, because of how it lays bytes out on disk.

The single biggest idea in this file is ROW-ORIENTED vs
COLUMN-ORIENTED storage:
    - CSV and Avro store data ROW BY ROW - all fields of record 1,
      then all fields of record 2, and so on. Great for writing one
      record at a time (logging, streaming) and for reading whole
      records back. Bad for analytics, where you usually want a FEW
      columns across MILLIONS of rows.
    - Parquet and ORC store data COLUMN BY COLUMN - all values of
      column A across every row, then all values of column B, and so
      on. This is what makes them "big data" formats: an analytical
      query that only touches 3 of 200 columns can skip reading the
      other 197 entirely, and because values of the SAME type and
      similar magnitude sit next to each other, they compress far
      better than a row-major text file ever could.

On top of the layout question, there's a second axis: SCHEMA. CSV
carries no schema at all - every value is just text until something
downstream decides what type it "should" be, which is a classic
silent-bug source. Parquet, Avro, and ORC all embed a real schema
inside the file itself, so a reader knows the exact column types
without guessing, and a schema violation can be caught at WRITE time
instead of quietly corrupting a warehouse table.

This file builds real Parquet files with pyarrow, inspects their
embedded schema and metadata directly, measures real file-size and
read/write-speed differences against real CSV files, demonstrates
real ORC read/write (pyarrow ships ORC support), and demonstrates
real Avro read/write via `fastavro` (falling back to a clearly
labeled simulation if `fastavro` isn't installed, since it's a
third-party library that may not be present everywhere).
=====================================================================
"""

import os
import shutil
import tempfile
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

print("--- Overview ---")
print("Row-oriented (CSV, Avro) stores whole records together - good")
print("for writing/streaming one record at a time.")
print("Column-oriented (Parquet, ORC) stores each column together -")
print("good for analytics that scan few columns across many rows.")

# A scratch directory for every file this script writes - removed at
# the very end so the script leaves no litter behind on disk.
WORKDIR = tempfile.mkdtemp(prefix="columnar_formats_")


"""
---------------------------------------------------------------------
1. ROW-ORIENTED vs COLUMN-ORIENTED STORAGE: THE CORE MENTAL MODEL  ⭐⭐⭐
---------------------------------------------------------------------
Picture a table with columns (order_id, region, total_amount) and
3 rows. A ROW-ORIENTED file lays bytes out like this on disk:

    [order_id=1, region=North, total=9.99]
    [order_id=2, region=South, total=4.50]
    [order_id=3, region=North, total=2.25]

A COLUMN-ORIENTED file lays the SAME data out like this instead:

    order_id: [1, 2, 3]
    region:   [North, South, North]
    total:    [9.99, 4.50, 2.25]

Neither layout is "better" in general - it depends on the access
pattern. OLTP systems (an app looking up "give me order #2, every
field") want row-oriented, because the whole record is contiguous.
OLAP / analytics ("what's the average total_amount by region across
10 million orders?") wants column-oriented, because it only needs 2
of the columns and can skip the rest of the file entirely.
---------------------------------------------------------------------
"""

print("\n--- Row-Oriented vs Column-Oriented: The Core Mental Model ---")

tiny_records = [
    {"order_id": 1, "region": "North", "total_amount": 9.99},
    {"order_id": 2, "region": "South", "total_amount": 4.50},
    {"order_id": 3, "region": "North", "total_amount": 2.25},
]

print("Row-oriented layout (how CSV/Avro store this):")
for rec in tiny_records:
    print(" ", rec)

print("\nColumn-oriented layout (how Parquet/ORC store the SAME data):")
columnar = {key: [rec[key] for rec in tiny_records] for key in tiny_records[0]}
for key, values in columnar.items():
    print(f"  {key}: {values}")

print("\nA query for 'just total_amount, averaged' only needs the LAST")
print("array above in the columnar layout - it never has to touch")
print("order_id or region at all.")


"""
---------------------------------------------------------------------
2. CONCRETE ILLUSTRATION: READING 3 COLUMNS OUT OF 200  ⭐⭐⭐
---------------------------------------------------------------------
"Skip the columns you don't need" sounds abstract until you measure
it. Below, a WIDE table (200 numeric columns, mimicking a sensor/
feature table) is written to both Parquet and CSV. Then:
    - Parquet's own file metadata is inspected to see exactly how
      many COMPRESSED BYTES belong to 3 chosen columns vs the whole
      file - Parquet can seek straight to those column chunks.
    - CSV is read back with `usecols` restricted to the same 3
      columns, to show that CSV still has to SCAN AND PARSE every
      byte on disk to find them, because a row-oriented text format
      has no way to jump directly to "just column 47".
---------------------------------------------------------------------
"""

print("\n--- Concrete Illustration: 3 Columns Out of 200 ---")

np.random.seed(1)
WIDE_ROWS = 8_000
WIDE_COLS = 200
wide_df = pd.DataFrame(
    np.random.uniform(0, 1000, size=(WIDE_ROWS, WIDE_COLS)),
    columns=[f"metric_{i}" for i in range(WIDE_COLS)],
)
wanted_columns = ["metric_5", "metric_100", "metric_199"]  # 3 of 200

wide_parquet_path = os.path.join(WORKDIR, "wide.parquet")
wide_csv_path = os.path.join(WORKDIR, "wide.csv")
wide_df.to_parquet(wide_parquet_path, engine="pyarrow", index=False)
wide_df.to_csv(wide_csv_path, index=False)

# Inspect Parquet's own metadata: how many compressed bytes actually
# belong to our 3 wanted columns, vs the file as a whole?
wide_meta = pq.ParquetFile(wide_parquet_path).metadata
total_compressed = 0
wanted_compressed = 0
for rg_idx in range(wide_meta.num_row_groups):
    row_group = wide_meta.row_group(rg_idx)
    for col_idx in range(row_group.num_columns):
        col_chunk = row_group.column(col_idx)
        total_compressed += col_chunk.total_compressed_size
        if col_chunk.path_in_schema in wanted_columns:
            wanted_compressed += col_chunk.total_compressed_size

pct = 100 * wanted_compressed / total_compressed
print(f"Parquet file total compressed size: {total_compressed:,} bytes")
print(f"Bytes belonging to just our 3 wanted columns: {wanted_compressed:,} bytes")
print(f"-> reading those 3 columns touches only {pct:.1f}% of the file's bytes")

# Now prove CSV can't do the same trick: reading "just 3 columns"
# with usecols still has to scan every line of the raw text.
t0 = time.perf_counter()
pd.read_csv(wide_csv_path)
t1 = time.perf_counter()
full_csv_read = t1 - t0

t2 = time.perf_counter()
pd.read_csv(wide_csv_path, usecols=wanted_columns)
t3 = time.perf_counter()
narrow_csv_read = t3 - t2

t4 = time.perf_counter()
pd.read_parquet(wide_parquet_path, engine="pyarrow", columns=wanted_columns)
t5 = time.perf_counter()
narrow_parquet_read = t5 - t4

print(f"\nCSV read, ALL 200 columns:      {full_csv_read:.4f}s")
print(f"CSV read, `usecols=` 3 columns:  {narrow_csv_read:.4f}s  (barely faster -")
print("  the parser still tokenizes every field on every line, it just")
print("  discards the ones it doesn't want AFTER parsing them)")
print(f"Parquet read, 3 columns only:    {narrow_parquet_read:.4f}s  (skips the")
print("  other 197 column chunks on disk entirely - never decodes them)")


"""
---------------------------------------------------------------------
3. REAL DEMO: CSV vs PARQUET - FILE SIZE AND READ/WRITE SPEED  ⭐⭐⭐
---------------------------------------------------------------------
This builds a realistic ETL-shaped dataset - e-commerce sales
records, the kind you'd stage between "extract from source system"
and "load into a warehouse" - and measures real numbers: on-disk
size and read/write time, for CSV vs Parquet, on the SAME data.
---------------------------------------------------------------------
"""

print("\n--- Real Demo: Sales Records, CSV vs Parquet ---")

np.random.seed(42)
N_SALES_ROWS = 300_000
sales_df = pd.DataFrame(
    {
        "order_id": np.arange(N_SALES_ROWS),
        "region": np.random.choice(
            ["North", "South", "East", "West", "Central"], N_SALES_ROWS
        ),
        "category": np.random.choice(
            ["Electronics", "Apparel", "Home", "Toys", "Grocery", "Sports"],
            N_SALES_ROWS,
        ),
        "quantity": np.random.randint(1, 10, N_SALES_ROWS),
        "unit_price": np.round(np.random.uniform(3, 500, N_SALES_ROWS), 2),
        "total_amount": np.round(np.random.uniform(3, 4500, N_SALES_ROWS), 2),
        "payment_method": np.random.choice(
            ["Credit Card", "Debit Card", "PayPal", "Gift Card"], N_SALES_ROWS
        ),
        "is_returned": np.random.choice([True, False], N_SALES_ROWS, p=[0.05, 0.95]),
    }
)
print(f"sales_df shape: {sales_df.shape}")

sales_csv_path = os.path.join(WORKDIR, "sales.csv")
sales_parquet_path = os.path.join(WORKDIR, "sales.parquet")

t0 = time.perf_counter()
sales_df.to_csv(sales_csv_path, index=False)
t1 = time.perf_counter()
csv_write_time = t1 - t0

t2 = time.perf_counter()
sales_df.to_parquet(sales_parquet_path, engine="pyarrow", index=False)
t3 = time.perf_counter()
parquet_write_time = t3 - t2

csv_size = os.path.getsize(sales_csv_path)
parquet_size = os.path.getsize(sales_parquet_path)

t4 = time.perf_counter()
csv_roundtrip = pd.read_csv(sales_csv_path)
t5 = time.perf_counter()
csv_read_time = t5 - t4

t6 = time.perf_counter()
parquet_roundtrip = pd.read_parquet(sales_parquet_path, engine="pyarrow")
t7 = time.perf_counter()
parquet_read_time = t7 - t6

print(f"\n{'metric':<16}{'CSV':>14}{'Parquet':>14}{'Parquet advantage':>20}")
print(f"{'write time (s)':<16}{csv_write_time:>14.4f}{parquet_write_time:>14.4f}"
      f"{csv_write_time / parquet_write_time:>17.1f}x faster")
print(f"{'read time (s)':<16}{csv_read_time:>14.4f}{parquet_read_time:>14.4f}"
      f"{csv_read_time / parquet_read_time:>17.1f}x faster")
print(f"{'size (bytes)':<16}{csv_size:>14,}{parquet_size:>14,}"
      f"{csv_size / parquet_size:>17.1f}x smaller")

print("\nSame 300,000 rows, same 8 columns, same values - Parquet wins")
print("on all three axes because it's a compact BINARY, typed, columnar")
print("format, while CSV re-encodes every number as human-readable text")
print("and re-parses that text character by character on every read.")
print("At true 'big data' scale (billions of rows, TBs of data spread")
print("across a data lake), this gap doesn't just persist - it widens,")
print("because compression ratios improve further and I/O becomes the")
print("dominant cost, which is exactly what columnar layout minimizes.")


"""
---------------------------------------------------------------------
4. SCHEMA ENFORCEMENT: PARQUET/AVRO HAVE ONE, CSV DOESN'T  ⭐⭐⭐
---------------------------------------------------------------------
A CSV file is just text. There is no embedded metadata saying
"column quantity is an integer" - a reader has to GUESS the type by
sniffing the values, and if a single bad value sneaks into a numeric
column, the guess silently changes for the WHOLE column, with no
error raised anywhere. Parquet (and Avro) embed a real schema inside
the file itself, and a strict schema can catch that same bad value
at WRITE time instead of letting it corrupt a table downstream.
---------------------------------------------------------------------
"""

print("\n--- Schema Enforcement: Parquet/Avro vs CSV ---")

# Show Parquet's embedded schema on the file we already wrote - no
# guessing required, the types are stored right in the file's footer.
embedded_schema = pq.read_schema(sales_parquet_path)
print("Parquet's embedded schema (pq.read_schema):")
print(embedded_schema)

# BUGGY scenario: a data-quality bug lets a stray string slip into
# what should be a purely numeric "quantity" column - a very common
# real-world ETL issue (a source system emits "N/A" or a typo).
bad_records = pd.DataFrame(
    {
        "order_id": ["ORD01", "ORD02", "ORD03"],
        "quantity": [5, 3, "five"],  # <- the bug: a string among ints
    }
)
print("\nbad_records.dtypes BEFORE any file round-trip:")
print(bad_records.dtypes)

bad_csv_path = os.path.join(WORKDIR, "bad_records.csv")
bad_records.to_csv(bad_csv_path, index=False)
reloaded_from_csv = pd.read_csv(bad_csv_path)
print("\nCSV round-trip: NO error raised. 'quantity' silently became a")
print("text column for ALL rows, not just the bad one:")
print(reloaded_from_csv.dtypes)
print(reloaded_from_csv)
print("Anything downstream doing `df['quantity'].sum()` will now either")
print("crash far away from the real bug, or - worse - silently coerce")
print("in some other unexpected way. The schema drift was invisible.")

# FIXED-style behavior: define the schema we EXPECT and hand it to
# pyarrow explicitly. Parquet's schema is not just descriptive - when
# you assert a schema at write time, a type mismatch is caught RIGHT
# HERE, at the point the bad data was produced, not months later in a
# warehouse query.
strict_schema = pa.schema([("order_id", pa.string()), ("quantity", pa.int64())])
try:
    pa.Table.from_pandas(bad_records, schema=strict_schema)
except pa.lib.ArrowInvalid as e:
    print("\nParquet/Arrow with an explicit schema CAUGHT it immediately:")
    print(" ", e)


"""
---------------------------------------------------------------------
5. WHY COLUMNAR COMPRESSES BETTER: ENCODING INTERNALS  ⭐⭐
---------------------------------------------------------------------
Compression algorithms find patterns in NEARBY bytes. In a row-major
file, the bytes right next to each other are a region string, then a
price, then a boolean, then a category string - wildly different
data with no shared pattern. In a column-major file, the bytes next
to each other are hundreds of THOUSANDS of values of the SAME type
and often the SAME small set of distinct values (like 5 regions
repeated 300,000 times) - which compresses extremely well, and lets
formats like Parquet use cheap tricks like DICTIONARY encoding
(store each distinct value once, then just indices) and RLE
(run-length encoding for repeated runs) before general compression
even runs.
---------------------------------------------------------------------
"""

print("\n--- Why Columnar Compresses Better: Encoding Internals ---")

# Compare compression codecs on the SAME columnar data.
for codec in ("snappy", "gzip", "none"):
    codec_path = os.path.join(WORKDIR, f"sales_{codec}.parquet")
    sales_df.to_parquet(codec_path, engine="pyarrow", compression=codec, index=False)
    print(f"  compression={codec:<8} -> {os.path.getsize(codec_path):>10,} bytes")
print("(snappy trades a bit of ratio for speed; gzip compresses smaller")
print("but slower; 'none' shows Parquet's binary+dictionary layout alone")
print("is already much smaller than CSV, even with NO compression at all)")

# Inspect real per-column encoding/size stats: a LOW-cardinality
# column ("region": 5 distinct values) vs a HIGH-cardinality one
# ("order_id": 300,000 distinct values).
sales_meta = pq.ParquetFile(sales_parquet_path).metadata
row_group0 = sales_meta.row_group(0)
print("\nPer-column stats in row group 0 (compressed vs uncompressed bytes):")
for col_idx in range(row_group0.num_columns):
    col = row_group0.column(col_idx)
    ratio = col.total_compressed_size / col.total_uncompressed_size
    print(f"  {col.path_in_schema:<15} compressed={col.total_compressed_size:>8,}  "
          f"uncompressed={col.total_uncompressed_size:>8,}  ratio={ratio:.2f}  "
          f"encodings={col.encodings}")
print("\nLow-cardinality columns like 'region' or 'payment_method' compress")
print("far tighter (dictionary + RLE encoding) than high-cardinality ones")
print("like 'order_id' - exactly because same-type, often-repeated values")
print("sit contiguously in a column instead of being scattered one-per-row.")


"""
---------------------------------------------------------------------
6. PREDICATE & COLUMN PUSHDOWN  ⭐⭐⭐
---------------------------------------------------------------------
Parquet stores per-ROW-GROUP statistics (min, max, null count) for
every column, right in the file's metadata. A query engine (or
pandas via pyarrow's `filters=` argument) can read JUST that
metadata first, and skip entire row groups whose min/max range can't
possibly satisfy the filter - without ever decoding their data. This
is PREDICATE PUSHDOWN. Asking for specific columns only (as in
Section 2) is COLUMN PUSHDOWN. Real engines (Spark, Trino, DuckDB)
combine both automatically.
---------------------------------------------------------------------
"""

print("\n--- Predicate & Column Pushdown ---")

region_col_stats = row_group0.column(1)  # column index 1 == "region"
print(f"row group 0 stats for 'region': min={region_col_stats.statistics.min!r}, "
      f"max={region_col_stats.statistics.max!r}")
print("A query filtering region == 'Zephyr' could SKIP this row group")
print("entirely just from these min/max bounds, with zero data decoded.")

# Column pushdown: only decode 2 of 8 columns.
t0 = time.perf_counter()
pd.read_parquet(sales_parquet_path, engine="pyarrow", columns=["region", "total_amount"])
t1 = time.perf_counter()
print(f"\nColumn pushdown (2 of 8 columns): {t1 - t0:.4f}s")

# Predicate pushdown via pyarrow's filters kwarg (row-group/page-level
# skipping happens underneath this call).
t2 = time.perf_counter()
filtered = pd.read_parquet(
    sales_parquet_path, engine="pyarrow", filters=[("region", "==", "West")]
)
t3 = time.perf_counter()
print(f"Predicate pushdown (region == 'West'): {t3 - t2:.4f}s, "
      f"returned {len(filtered):,} of {len(sales_df):,} rows")


"""
---------------------------------------------------------------------
7. AVRO: ROW-ORIENTED BUT SCHEMA-BASED (KAFKA / STREAMING)  ⭐⭐
---------------------------------------------------------------------
Avro is the odd one out: it's ROW-ORIENTED (records are written
whole, one after another) - great for streaming, where you produce
one event at a time and can't wait to batch a whole column together
- but it still embeds a rich SCHEMA (a JSON schema definition) right
alongside the data, plus first-class SCHEMA EVOLUTION rules (adding
a field with a default is backward-compatible; a schema registry can
enforce compatibility across producers/consumers). This combination
is exactly why Avro is the standard serialization format for Kafka
topics: one event at a time, but never "just untyped bytes".

`fastavro` is the common Python library for this. It's a third-party
package that may not be installed everywhere, so the real API is
shown below and actually exercised if available, with a clearly
labeled simulated fallback otherwise - the code is 100% what you'd
run against a real Kafka pipeline either way.
---------------------------------------------------------------------
"""

print("\n--- Avro: Row-Oriented but Schema-Based (Kafka/Streaming) ---")

try:
    import fastavro
    from fastavro import reader as avro_reader
    from fastavro import writer as avro_writer
    FASTAVRO_AVAILABLE = True
except ImportError:
    FASTAVRO_AVAILABLE = False

# A real Avro schema: a JSON-like dict, the same shape you'd register
# in a Confluent Schema Registry for a Kafka topic.
avro_schema = {
    "type": "record",
    "name": "SalesEvent",
    "namespace": "com.pattern.sales",
    "fields": [
        {"name": "order_id", "type": "string"},
        {"name": "region", "type": "string"},
        {"name": "total_amount", "type": "double"},
        # A field added LATER, with a default - this is what makes
        # adding it backward-compatible for consumers on the OLD
        # schema: they simply never see it, while new consumers read
        # a sane default for events produced before this field existed.
        {"name": "loyalty_points", "type": "int", "default": 0},
    ],
}

avro_events = [
    {"order_id": "ORD01", "region": "North", "total_amount": 19.99, "loyalty_points": 20},
    {"order_id": "ORD02", "region": "South", "total_amount": 4.50, "loyalty_points": 5},
    {"order_id": "ORD03", "region": "West", "total_amount": 250.00, "loyalty_points": 250},
]

avro_path = os.path.join(WORKDIR, "sales_events.avro")

if FASTAVRO_AVAILABLE:
    parsed_schema = fastavro.parse_schema(avro_schema)
    with open(avro_path, "wb") as out_f:
        avro_writer(out_f, parsed_schema, avro_events)
    print(f"wrote {len(avro_events)} events to a REAL Avro file "
          f"({os.path.getsize(avro_path)} bytes)")
    with open(avro_path, "rb") as in_f:
        read_back = list(avro_reader(in_f))
    print("read back:")
    for rec in read_back:
        print(" ", rec)
else:
    # This is the exact code that WOULD run above - shown here as a
    # clearly labeled simulation so the concept and real API are both
    # visible even without the dependency installed.
    print("fastavro is not installed in this environment - SIMULATED output")
    print("(the code above this branch is the real, correct fastavro API):")
    for rec in avro_events:
        print("  [simulated write+read]", rec)

print("\nIn a real Kafka pipeline: a producer serializes each event with")
print("this schema (often looked up from a schema registry by an ID sent")
print("alongside the bytes), and each consumer deserializes it the same")
print("way - one record at a time, but always with a known, typed shape.")


"""
---------------------------------------------------------------------
8. ORC: THE HADOOP / HIVE COLUMNAR FORMAT  ⭐
---------------------------------------------------------------------
ORC (Optimized Row Columnar) is Parquet's older sibling: also
column-oriented, also carries an embedded schema and per-stripe
statistics for predicate pushdown, but it grew up specifically
inside the Hadoop/Hive ecosystem and has deeper native integration
there (including support for ACID transactions in Hive tables).
Parquet has become the more common cross-engine default outside of
Hive-heavy shops (Spark, Trino, Snowflake, BigQuery, pandas/Arrow
all treat Parquet as a first-class citizen), but ORC still shows up
constantly in legacy Hadoop/Hive warehouses, so recognizing it - and
knowing it's "the same idea as Parquet, different ecosystem" - is
worth having ready for an interview.
---------------------------------------------------------------------
"""

print("\n--- ORC: The Hadoop/Hive Columnar Format ---")

try:
    import pyarrow.orc as orc
    ORC_AVAILABLE = True
except ImportError:
    ORC_AVAILABLE = False

orc_path = os.path.join(WORKDIR, "sales.orc")
sales_table = pa.Table.from_pandas(sales_df, preserve_index=False)

if ORC_AVAILABLE:
    orc.write_table(sales_table, orc_path)
    orc_size = os.path.getsize(orc_path)
    t0 = time.perf_counter()
    orc_roundtrip = orc.read_table(orc_path)
    t1 = time.perf_counter()
    print(f"wrote/read a REAL ORC file: {orc_size:,} bytes, "
          f"read in {t1 - t0:.4f}s, {orc_roundtrip.num_rows:,} rows")
    print(f"(for comparison, the Parquet version of the same data was "
          f"{parquet_size:,} bytes)")
else:
    # Real, correct ORC API, shown for reference even if unavailable:
    #   import pyarrow.orc as orc
    #   orc.write_table(pa.Table.from_pandas(sales_df), "sales.orc")
    #   table = orc.read_table("sales.orc")
    print("pyarrow's ORC support is not available in this environment -")
    print("SIMULATED output (the code above this branch is the real API):")
    print(f"  [simulated] would write ~{parquet_size:,}-{int(parquet_size*1.3):,} "
          f"bytes and read back {len(sales_df):,} rows")


"""
---------------------------------------------------------------------
9. DATA ENGINEERING USE CASE: CHOOSING A FORMAT PER PIPELINE STAGE  ⭐⭐⭐
---------------------------------------------------------------------
A realistic pipeline rarely uses just one format end to end - the
right choice depends on what that STAGE of the pipeline is doing:
    - Ingestion from a streaming source (Kafka)         -> Avro
    - Landing/raw zone (whatever the source hands you)  -> CSV/JSON
    - Curated/analytics-ready lake or warehouse tables   -> Parquet
      (or ORC, in a Hive-centric shop)
Partitioning a Parquet dataset by a commonly-filtered column (like
`region` or a date) is a very common real technique on top of this:
it lets a reader skip whole DIRECTORIES, not just row groups, before
even opening a file.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Format per Pipeline Stage ---")

partitioned_dir = os.path.join(WORKDIR, "sales_partitioned")
sales_df.to_parquet(
    partitioned_dir, engine="pyarrow", partition_cols=["region"], index=False
)
print("partitioned Parquet dataset written, one directory per region:")
for entry in sorted(os.listdir(partitioned_dir)):
    print(" ", entry)

# Reading just ONE partition never even opens the files for the other
# 4 regions - directory pruning, on top of row-group and column
# pruning from the sections above.
t0 = time.perf_counter()
west_only = pd.read_parquet(os.path.join(partitioned_dir, "region=West"))
t1 = time.perf_counter()
print(f"\nread only the 'region=West' partition: {t1 - t0:.4f}s, "
      f"{len(west_only):,} rows (never touched the other 4 partitions)")

print("\nTypical pipeline shape:")
print("  Kafka topic (Avro events)")
print("    -> raw/bronze landing zone (CSV or JSON, as received)")
print("    -> curated/silver+gold layer (partitioned Parquet, or ORC")
print("       tables if the warehouse is Hive-based)")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Layout:
    Row-oriented       -> CSV, Avro      (whole record written together)
    Column-oriented    -> Parquet, ORC   (each column written together)

Why columnar wins for analytics:
    - reads only the columns a query needs (column pushdown)
    - skips row groups/stripes via min/max stats (predicate pushdown)
    - same-type values sit together -> dictionary/RLE + compression

Schema:
    CSV      -> none; everything is text until something infers types
    Parquet  -> embedded schema in the file footer (pq.read_schema)
    Avro     -> embedded JSON schema + first-class schema evolution
    ORC      -> embedded schema, like Parquet, Hive/Hadoop-native

Best fit:
    CSV      -> human-readable interchange, small/legacy data
    Avro     -> streaming (Kafka), row-at-a-time, evolving schemas
    Parquet  -> batch analytics, data lakes, cross-engine default
    ORC      -> batch analytics inside Hive/Hadoop-centric warehouses

Real numbers from this file's demo (300,000-row sales dataset):
    CSV write / Parquet write   -> Parquet several times faster
    CSV read  / Parquet read    -> Parquet several times faster
    CSV size  / Parquet size    -> Parquet several times smaller
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")

# Clean up every temp file/directory this script created.
shutil.rmtree(WORKDIR, ignore_errors=True)


"""
=====================================================================
INTERVIEW QUESTIONS - COLUMNAR FORMATS (PARQUET, AVRO, ORC)
=====================================================================

1. Why is Parquet preferred over CSV in big data pipelines? Cover
   columnar storage, compression, and schema in your answer.

2. Compare read/write speed and storage size: CSV vs Parquet vs
   Avro. Which one wins on which axis, and why?

3. Explain the difference between row-oriented and column-oriented
   storage. Why is Avro row-oriented despite being a "big data"
   format, while Parquet and ORC are column-oriented?

4. In this file, `wanted_columns` selects 3 of 200 columns from
   `wide_df`. Explain mechanically why Parquet can read those 3
   columns without touching the other 197, while `pd.read_csv(...,
   usecols=...)` on the same data still has to scan every line.

5. What is PREDICATE PUSHDOWN, and how do Parquet's per-row-group
   min/max statistics make it possible without decoding the actual
   column data?

6. What is COLUMN PUSHDOWN, and how is it different from predicate
   pushdown? (Hint: think about what `columns=[...]` vs
   `filters=[...]` each let a reader skip.)

7. Why do low-cardinality columns (like `region` in this file, with
   only 5 distinct values) compress far better in Parquet than
   high-cardinality columns (like `order_id`)? Name at least one
   specific encoding technique (dictionary encoding, RLE) involved.

8. `bad_records` in this file has a `quantity` column with a stray
   string value. Walk through what happens to that column's dtype
   after a CSV round-trip, versus what happens when you try to
   build a `pyarrow.Table` from it with an explicit `pa.schema(...)`
   that declares `quantity` as `int64`. Why does one approach catch
   the bug immediately and the other doesn't catch it at all?

9. What does it mean that Parquet and Avro both carry an "embedded
   schema"? How does a downstream reader benefit from that versus
   reading a CSV file with no schema at all?

10. Why is Avro the conventional serialization format for Kafka
    topics, given that it's row-oriented rather than columnar?

11. In the Avro schema used in this file, `loyalty_points` was added
    with a `"default": 0`. Explain why giving it a default is what
    makes adding this field backward-compatible for consumers still
    running the OLD schema.

12. How does ORC compare to Parquet? What ecosystem is ORC most
    associated with, and why might a team still choose it over
    Parquet today?

13. Describe a realistic multi-stage pipeline that uses THREE
    different file/serialization formats end to end, and justify
    the choice of format at each stage.

14. What is partition pruning, and how is it different from row-
    group-level predicate pushdown within a single Parquet file?
    (Hint: look at how `sales_df` was written with
    `partition_cols=["region"]` in this file, and what happens when
    only the `region=West` partition is read.)

15. At what scale of data does the CSV-vs-Parquet gap shown in this
    file's Section 3 demo start to matter in practice, and why does
    the gap widen rather than shrink as data volume grows?
=====================================================================
"""
