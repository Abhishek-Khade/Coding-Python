"""
=====================================================================
PANDAS MEMORY OPTIMIZATION - dtypes, category, and chunksize -
Complete Notes with Executable Examples
=====================================================================

pandas is EAGER and IN-MEMORY: the moment you load a DataFrame, every
column lives fully in RAM as a NumPy array (or an ExtensionArray for
things like category). Nothing about pandas automatically picks the
SMALLEST dtype that could hold your data - `read_csv` defaults integer
columns to int64 and text columns to generic Python `object` arrays,
because that is the SAFEST default, not the most memory-efficient
one. On a 500-row DataFrame nobody cares. On a 50-million-row fact
table, the gap between "safe default dtypes" and "correctly-sized
dtypes" is routinely a 5-10x difference in RAM - the difference
between a job that fits on one worker and a job that OOMs.

There are three independent levers, and a senior DE is expected to
know all three cold:
    1. DOWNCASTING numeric columns (int64 -> int8/16/32, float64 ->
       float32) when the ACTUAL value range doesn't need 64 bits.
    2. The `category` dtype for LOW-cardinality text/object columns -
       dictionary-encoding: store each unique value ONCE, and store
       small integer CODES per row instead of repeating the string.
    3. `chunksize` on `read_csv()` for files that don't fit in memory
       AT ALL - process the file in pieces and keep only a small
       running aggregate, never the whole thing, in RAM.

The one rule that ties all of this together: NEVER guess. Always
MEASURE with `.memory_usage(deep=True)` before optimizing and after,
because dtype choices that seem obviously good (like `category` on
every object column) can quietly make memory usage WORSE - measuring
is what tells you which lever actually helps for a given column.
=====================================================================
"""

import os
import tempfile

import numpy as np
import pandas as pd

print("--- Overview ---")
print("pandas defaults to SAFE dtypes (int64, object), not SMALL ones.")
print("Three levers fix that: downcast numeric dtypes, use `category`")
print("for low-cardinality text, and use `chunksize` when a file is")
print("too big for RAM at all. Always MEASURE with memory_usage(deep=True).")


# A shared synthetic "orders" dataset used throughout this file - built
# to look like a realistic extract from an OLTP orders table.
np.random.seed(42)
N_ROWS = 300_000

RAW_DF = pd.DataFrame({
    # unique row identifier: 0..299,999 -> too big for int16, fits int32
    "order_id": np.arange(N_ROWS),
    # unique per row (like a real customer/account id) -> HIGH cardinality
    "customer_id": [f"CUST-{i:07d}" for i in range(N_ROWS)],
    # only 5 distinct values repeated 300,000 times -> LOW cardinality
    "region": np.random.choice(
        ["US-EAST", "US-WEST", "EU-CENTRAL", "APAC", "LATAM"], N_ROWS
    ),
    # only 4 distinct values repeated 300,000 times -> LOW cardinality
    "status": np.random.choice(
        ["completed", "pending", "cancelled", "refunded"], N_ROWS
    ),
    # small integers, 1-50 -> fits comfortably in int8 (max 127)
    "quantity": np.random.randint(1, 51, N_ROWS),
    # cents, 100-29,999 -> too big for int8, fits int16 (max 32,767)
    "unit_price_cents": np.random.randint(100, 30_000, N_ROWS),
})


"""
---------------------------------------------------------------------
1. MEASURING REAL MEMORY: .memory_usage(deep=True)  ⭐⭐⭐
---------------------------------------------------------------------
`df.memory_usage()` on its own is a TRAP for legacy `object` columns:
pandas stores an `object` column as a NumPy array of 8-byte POINTERS,
one per row, pointing at separate Python `str` objects living
elsewhere on the heap. Without `deep=True`, memory_usage() only
reports the size of that pointer array - it has no idea how big the
actual strings behind those pointers are. `deep=True` walks every
object in the column and adds up their REAL sizes. For numeric
dtypes (int64, float64, ...) deep=True changes nothing, because the
values are stored inline in the array already - there's no pointer
to chase.

Interview note for THIS pandas version (3.0.2): as of pandas 3.0,
text columns default to a dedicated `str` dtype (PDEP-14) instead of
legacy `object`, and that dtype stores its data in a packed buffer,
not per-row Python objects - so deep=True and deep=False already
agree for it. The trap below is still very real: you hit it any time
a column IS (or gets cast to) legacy `object` - reading an older
pickle/pyarrow file into object, calling `.astype(object)`, or
running an older pandas version - so it's still essential to reach
for deep=True by default and never assume deep=False is safe.
---------------------------------------------------------------------
"""

print("\n--- Measuring Real Memory: deep=True vs deep=False ---")

region_legacy_object = RAW_DF["region"].astype(object)   # force the classic representation
region_shallow = region_legacy_object.memory_usage(deep=False)
region_deep = region_legacy_object.memory_usage(deep=True)
print(f"region as legacy object dtype, deep=False: {region_shallow:>10,} bytes  (just the pointer array)")
print(f"region as legacy object dtype, deep=True:  {region_deep:>10,} bytes  (pointers + actual string objects)")
print(f"deep=True reports {region_deep / region_shallow:.1f}x the shallow figure - deep=False was hiding almost all of it")

region_native_shallow = RAW_DF["region"].memory_usage(deep=False)
region_native_deep = RAW_DF["region"].memory_usage(deep=True)
print(f"\nregion as loaded here, dtype={RAW_DF['region'].dtype!s}: "
      f"deep=False {region_native_shallow:,} bytes == deep=True {region_native_deep:,} bytes")
print("(pandas 3.0's default text dtype isn't pointer-backed, so there's nothing for deep=True to add)")

qty_shallow = RAW_DF["quantity"].memory_usage(deep=False)
qty_deep = RAW_DF["quantity"].memory_usage(deep=True)
print(f"\nquantity column (int64), deep=False: {qty_shallow:,} bytes")
print(f"quantity column (int64), deep=True:  {qty_deep:,} bytes  (identical - no pointers to chase)")

print("\nLesson: NEVER trust deep=False as a safe default - the moment any column is (or")
print("becomes) legacy `object` dtype, deep=False silently UNDER-reports true memory usage.")
print("Always pass deep=True when sizing a DataFrame for a memory-optimization decision.")


"""
---------------------------------------------------------------------
2. DOWNCASTING NUMERIC DTYPES  ⭐⭐⭐
---------------------------------------------------------------------
`read_csv`/default construction picks int64/float64 for numeric
columns regardless of the actual value range, because int64 can
safely hold ANY integer pandas might encounter. But `order_id` here
never exceeds 299,999 (fits int32), `unit_price_cents` never exceeds
30,000 (fits int16), and `quantity` never exceeds 50 (fits int8).
`pd.to_numeric(col, downcast=...)` inspects the ACTUAL min/max of the
column and returns the smallest safe dtype - it never guesses and
never silently corrupts data. Manually doing `.astype('int8')`
WITHOUT checking the range first is the classic naive mistake: NumPy
integer casts do not raise on overflow, they silently WRAP AROUND
(two's-complement), producing corrupted negative numbers with no
error at all - the single most dangerous "memory optimization" bug.
---------------------------------------------------------------------
"""

print("\n--- Downcasting Numeric Dtypes ---")

before_bytes = RAW_DF[["order_id", "quantity", "unit_price_cents"]].memory_usage(deep=True).sum()
print(f"Before downcasting, these 3 int64 columns use: {before_bytes:,} bytes")

# BUGGY: "smaller must be better" - cast straight to int8 without checking range.
naive_price_int8 = RAW_DF["unit_price_cents"].astype("int8")
mismatches = (naive_price_int8.astype("int64") != RAW_DF["unit_price_cents"]).sum()
print(f"\nBUGGY naive astype('int8') on unit_price_cents (range up to 30,000):")
print("  original first 5 values:      ", RAW_DF["unit_price_cents"].head(5).tolist())
print("  after astype('int8') first 5: ", naive_price_int8.head(5).tolist())
print(f"  SILENTLY CORRUPTED rows (no exception raised!): {mismatches:,} / {N_ROWS:,}")
print("  Why: int8 only holds -128..127. Values are taken mod 256 and")
print("  reinterpreted as signed - e.g. 300 wraps to 44, 20000 wraps")
print("  to a garbage negative number. This is WORSE than doing nothing.")

# FIXED: let pandas pick the smallest SAFE dtype based on the real min/max.
order_id_down = pd.to_numeric(RAW_DF["order_id"], downcast="integer")
quantity_down = pd.to_numeric(RAW_DF["quantity"], downcast="integer")
price_down = pd.to_numeric(RAW_DF["unit_price_cents"], downcast="integer")

print("\nFIXED with pd.to_numeric(..., downcast='integer'):")
print(f"  order_id:         int64 -> {order_id_down.dtype}  (range 0..{RAW_DF['order_id'].max():,} needs 32 bits)")
print(f"  quantity:         int64 -> {quantity_down.dtype}   (range 1..{RAW_DF['quantity'].max()} fits in 8 bits)")
print(f"  unit_price_cents: int64 -> {price_down.dtype}  (range up to {RAW_DF['unit_price_cents'].max():,} fits in 16 bits)")
assert (order_id_down.astype("int64") == RAW_DF["order_id"]).all(), "downcast must be lossless"
assert (price_down.astype("int64") == RAW_DF["unit_price_cents"]).all(), "downcast must be lossless"
print("  (values verified IDENTICAL to the original int64 column - zero data loss)")

after_bytes = (
    order_id_down.memory_usage(deep=True)
    + quantity_down.memory_usage(deep=True)
    + price_down.memory_usage(deep=True)
)
print(f"\nAfter downcasting, the same 3 columns use: {after_bytes:,} bytes")
print(f"REAL measured reduction: {(1 - after_bytes / before_bytes) * 100:.1f}%")

# A second, real danger of numeric coercion: dirty data. pd.to_numeric
# raises a real, catchable error by default when a value truly isn't numeric.
dirty = pd.Series(["120", "455", "N/A", "310"])
try:
    pd.to_numeric(dirty, errors="raise")
except ValueError as e:
    print(f"\npd.to_numeric(errors='raise') on dirty data correctly raised: {e}")
cleaned = pd.to_numeric(dirty, errors="coerce")  # bad values -> NaN instead of crashing the job
print("pd.to_numeric(errors='coerce') instead turns bad values into NaN:")
print(cleaned.tolist())


"""
---------------------------------------------------------------------
3. THE category DTYPE FOR LOW-CARDINALITY COLUMNS  ⭐⭐⭐
---------------------------------------------------------------------
`category` is DICTIONARY ENCODING, the same trick columnar formats
like Parquet use internally: pandas stores the small set of UNIQUE
values once (`.cat.categories`), and replaces every row's value with
a small integer CODE (`.cat.codes`) that points into that dictionary.
`region` has only 5 distinct strings repeated 300,000 times - as a
plain text column, that string data is effectively duplicated across
every one of those 300,000 rows. As `category`, each unique string is
stored exactly ONCE, and every row just stores a 1-byte code (int8
comfortably covers up to 127 categories) - this is the SAME
"object/text column has too many repeats" story interviewers ask
about, regardless of exactly which text dtype backs the column.
---------------------------------------------------------------------
"""

print("\n--- The category Dtype for Low-Cardinality Columns ---")

region_before_bytes = RAW_DF["region"].memory_usage(deep=True)
region_category = RAW_DF["region"].astype("category")
region_category_bytes = region_category.memory_usage(deep=True)

print(f"region before, dtype={RAW_DF['region'].dtype!s}: {region_before_bytes:>10,} bytes  "
      f"({RAW_DF['region'].nunique()} unique values / {N_ROWS:,} rows)")
print(f"region as category:                {region_category_bytes:>10,} bytes")
print(f"REAL measured reduction: {(1 - region_category_bytes / region_before_bytes) * 100:.1f}%")

print("\nWhy it works - dictionary encoding under the hood:")
print(" .cat.categories (stored ONCE):", list(region_category.cat.categories))
print(" .cat.codes dtype (stored PER ROW):", region_category.cat.codes.dtype)
print(" .cat.codes, first 8 rows:", region_category.cat.codes.head(8).tolist())
print("Each row now costs 1 byte (an int8 code) instead of repeating one")
print("of only 5 possible strings over and over across 300,000 rows.")

status_before_bytes = RAW_DF["status"].memory_usage(deep=True)
status_category_bytes = RAW_DF["status"].astype("category").memory_usage(deep=True)
print(f"\nSame win on 'status' ({RAW_DF['status'].nunique()} unique values): "
      f"{status_before_bytes:,} -> {status_category_bytes:,} bytes "
      f"({(1 - status_category_bytes / status_before_bytes) * 100:.1f}% reduction)")


"""
---------------------------------------------------------------------
4. THE DANGER: category ON A HIGH-CARDINALITY COLUMN  ⭐⭐
---------------------------------------------------------------------
`category` only wins when values REPEAT, because the saving comes
from storing each unique value ONCE instead of N times. Apply it to
a column where almost every value is unique - a customer/account id,
a UUID, a timestamp - and there is no repetition to exploit. You pay
for the codes array (one integer per row) on top of a categories
index that is now ALMOST AS BIG as the original data, plus the fixed
overhead of the category machinery itself (the CategoricalDtype
object, the codes<->categories mapping). Net result: MORE memory, not
less. This is exactly why step 1 (measure!) matters more than any
rule of thumb.
---------------------------------------------------------------------
"""

print("\n--- The Danger: category on a HIGH-Cardinality Column ---")

cust_before_bytes = RAW_DF["customer_id"].memory_usage(deep=True)
cust_category_bytes = RAW_DF["customer_id"].astype("category").memory_usage(deep=True)
cardinality_ratio = RAW_DF["customer_id"].nunique() / len(RAW_DF)

print(f"customer_id: {RAW_DF['customer_id'].nunique():,} unique values / {N_ROWS:,} rows "
      f"(cardinality ratio = {cardinality_ratio:.2f})")
print(f"customer_id before, dtype={RAW_DF['customer_id'].dtype!s}: {cust_before_bytes:>10,} bytes")
print(f"customer_id as category:                    {cust_category_bytes:>10,} bytes")
if cust_category_bytes > cust_before_bytes:
    extra = cust_category_bytes - cust_before_bytes
    print(f"category made it WORSE by {extra:,} bytes ({extra / cust_before_bytes * 100:.1f}% MORE memory)")
else:
    print("(if your pandas build shows category smaller here, it's still paying for a")
    print(" codes array with ZERO deduplication benefit - see explanation below)")
print("\nWhy this is dangerous even when the numbers look close: pandas still has to")
print("store a ~300,000-entry categories index (basically the full original data,")
print("since almost nothing repeats) PLUS a 300,000-entry codes array on top of it -")
print("you pay for both representations, for NO deduplication win. Rule of thumb:")
print("category tends to help when unique_values / total_rows is well under ~50%,")
print("and the lower that ratio, the bigger the win - but always MEASURE per column,")
print("on your actual dtypes, rather than assuming.")


"""
---------------------------------------------------------------------
5. READING WITH OPTIMIZED DTYPES FROM THE START  ⭐⭐
---------------------------------------------------------------------
Downcasting AFTER loading still pays the cost of the wasteful int64/
object load in the first place (peak memory during read_csv can spike
even higher than the final naive DataFrame). If you already know the
column ranges and cardinalities (very common for a recurring pipeline
ingesting the same schema daily), it's strictly better to hand
`read_csv` a `dtype=` mapping up front - it never allocates the
oversized dtype at all.
---------------------------------------------------------------------
"""

print("\n--- Reading With Optimized Dtypes From the Start ---")

csv_fd, csv_path = tempfile.mkstemp(suffix=".csv", prefix="orders_")
os.close(csv_fd)
RAW_DF.to_csv(csv_path, index=False)
print(f"wrote a temp CSV for the read_csv demos: {csv_path}")
print(f"file size on disk: {os.path.getsize(csv_path):,} bytes")

naive_read = pd.read_csv(csv_path)
naive_read_bytes = naive_read.memory_usage(deep=True).sum()
print(f"\nnaive pd.read_csv(path) dtypes:\n{naive_read.dtypes}")
print(f"naive read, total memory: {naive_read_bytes:,} bytes")

optimized_read = pd.read_csv(
    csv_path,
    dtype={
        "order_id": "int32",
        "customer_id": "string",   # a real id column: leave as string, NOT category (see section 4)
        "region": "category",
        "status": "category",
        "quantity": "int8",
        "unit_price_cents": "int16",
    },
)
optimized_read_bytes = optimized_read.memory_usage(deep=True).sum()
print(f"\noptimized pd.read_csv(path, dtype={{...}}) dtypes:\n{optimized_read.dtypes}")
print(f"optimized read, total memory: {optimized_read_bytes:,} bytes")
print(f"REAL measured reduction from dtype-at-read-time alone: "
      f"{(1 - optimized_read_bytes / naive_read_bytes) * 100:.1f}%")


"""
---------------------------------------------------------------------
6. chunksize: PROCESSING A FILE TOO BIG FOR MEMORY  ⭐⭐⭐
---------------------------------------------------------------------
Everything above assumes the FULL dataset fits in RAM once optimized.
Sometimes it simply doesn't - a 40GB CSV on a machine with 16GB of
RAM. `pd.read_csv(path, chunksize=N)` returns a lazy TextFileReader
you iterate over: each iteration hands you ONE chunk (an ordinary
DataFrame of N rows) and then DISCARDS it from memory once you move
to the next chunk - only ONE chunk is ever resident at a time. The
pattern is always the same: keep a small RUNNING aggregate across
chunks, never the raw rows themselves. This directly answers "how do
you handle a dataset that doesn't fit in memory using pandas?".
---------------------------------------------------------------------
"""

print("\n--- chunksize: Processing a File Too Big for Memory ---")

CHUNK_SIZE = 50_000
running_qty_by_region = pd.Series(dtype="int64")   # small running aggregate, NOT the raw data
running_row_count = 0
chunks_seen = 0

chunk_reader = pd.read_csv(
    csv_path,
    chunksize=CHUNK_SIZE,
    dtype={"region": "category", "quantity": "int8"},   # combine with lever #1/#3 too
    usecols=["region", "quantity"],                       # only read the columns this job needs
)
for chunk in chunk_reader:
    chunks_seen += 1
    running_row_count += len(chunk)
    # .add(..., fill_value=0) merges this chunk's partial sums into the running total
    running_qty_by_region = running_qty_by_region.add(
        chunk.groupby("region", observed=True)["quantity"].sum(), fill_value=0
    )

print(f"processed {chunks_seen} chunks of up to {CHUNK_SIZE:,} rows each "
      f"({running_row_count:,} rows total) - never more than one chunk in memory")
print("\nrunning total quantity by region, aggregated across chunks:")
print(running_qty_by_region.astype("int64").sort_values(ascending=False))

# Sanity check: the chunked aggregate must match a direct groupby on the full data.
direct_check = RAW_DF.groupby("region", observed=True)["quantity"].sum()
matches = (running_qty_by_region.astype("int64").sort_index() == direct_check.sort_index()).all()
print(f"\nmatches a direct in-memory groupby on the full DataFrame: {matches}")


"""
---------------------------------------------------------------------
7. DATA ENGINEERING USE CASE: A REUSABLE optimize_dataframe() STEP  ⭐⭐⭐
---------------------------------------------------------------------
In a real pipeline you rarely hand-pick dtypes column by column every
run - you write ONE generic transformation step that inspects
whatever DataFrame just came out of an extractor and optimizes it
automatically, combining every lever from this file: downcast every
numeric column, and convert an object column to category ONLY when
its cardinality ratio is low enough to actually help (directly
applying the lesson from section 4, instead of a blind rule).
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: optimize_dataframe() Pipeline Step ---")


def optimize_dataframe(df: pd.DataFrame, category_threshold: float = 0.5) -> pd.DataFrame:
    """Return a memory-optimized COPY of df: downcast numeric columns,
    and convert low-cardinality object columns to category. Never
    mutates the input - a pipeline step should be side-effect-free."""
    out = df.copy()
    n_rows = len(out)
    for col in out.columns:
        dtype = out[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            out[col] = pd.to_numeric(out[col], downcast="integer")
        elif pd.api.types.is_float_dtype(dtype):
            out[col] = pd.to_numeric(out[col], downcast="float")
        elif not isinstance(dtype, pd.CategoricalDtype) and pd.api.types.is_string_dtype(dtype):
            # covers legacy `object` text AND pandas 3.0's default `str` dtype
            ratio = out[col].nunique() / n_rows if n_rows else 0
            if ratio < category_threshold:
                out[col] = out[col].astype("category")
            # else: high-cardinality text (ids, free text) - leave as-is,
            # per the section 4 lesson - category would make it worse.
    return out


optimized_pipeline_df = optimize_dataframe(naive_read)
print("dtypes after optimize_dataframe():")
print(optimized_pipeline_df.dtypes)

before_pipeline = naive_read.memory_usage(deep=True).sum()
after_pipeline = optimized_pipeline_df.memory_usage(deep=True).sum()
print(f"\nbefore: {before_pipeline:,} bytes -> after: {after_pipeline:,} bytes "
      f"({(1 - after_pipeline / before_pipeline) * 100:.1f}% reduction)")
print("Note customer_id correctly stayed as an id/string column - its")
print(f"cardinality ratio ({RAW_DF['customer_id'].nunique() / N_ROWS:.2f}) is above the threshold.")


"""
---------------------------------------------------------------------
8. FINAL BEFORE/AFTER SUMMARY: NAIVE LOAD vs FULLY OPTIMIZED  ⭐⭐⭐
---------------------------------------------------------------------
Putting it all together on the exact same underlying data: the naive
load (plain read_csv, pandas' safe defaults) versus reading with
optimized dtypes chosen from the start (section 5's dtype= mapping).
This is the number you'd actually quote in an interview answer to
"how would you optimize memory usage of a large DataFrame?".
---------------------------------------------------------------------
"""

print("\n--- Final Summary: Naive Load vs Fully Optimized Load ---")

naive_total = naive_read.memory_usage(deep=True).sum()
optimized_total = optimized_read.memory_usage(deep=True).sum()
reduction_pct = (1 - optimized_total / naive_total) * 100

print(f"{'':22}{'naive (defaults)':>20}{'optimized':>18}")
for col in RAW_DF.columns:
    n_bytes = naive_read[col].memory_usage(deep=True)
    o_bytes = optimized_read[col].memory_usage(deep=True)
    print(f"{col:22}{n_bytes:>20,}{o_bytes:>18,}")
print(f"{'TOTAL':22}{naive_total:>20,}{optimized_total:>18,}")
print(f"\nREAL measured total reduction: {reduction_pct:.1f}% "
      f"({naive_total:,} bytes -> {optimized_total:,} bytes)")

# Clean up the temp file this file created for the read_csv/chunksize demos.
try:
    os.remove(csv_path)
    print(f"\ncleaned up temp file: {csv_path}")
except OSError as e:
    print(f"\ncould not remove temp file {csv_path}: {e}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Measure first, always:
    df.memory_usage(deep=True)        -> per-column REAL bytes
    df.memory_usage(deep=True).sum()  -> total REAL bytes
    (deep=False under-reports any object/string column - it only
     sees the 8-byte pointer array, not the strings themselves)

Downcast numeric columns:
    pd.to_numeric(col, downcast="integer")  -> smallest safe int type
    pd.to_numeric(col, downcast="float")    -> smallest safe float type
    NEVER hand-pick .astype("int8") without checking the range first
    -> silent overflow (wraps around), no exception raised

category dtype (dictionary encoding):
    unique values stored ONCE (.cat.categories)
    each row stores a small int CODE (.cat.codes), not the value
    WINS   -> low cardinality (few unique values, many repeats)
    LOSES  -> high cardinality (ids, UUIDs) - codes + near-full
              categories index costs MORE than the plain column

Read with the right dtypes from the start:
    pd.read_csv(path, dtype={"col": "category", "n": "int8", ...})
    -> avoids ever allocating the oversized default in the first place

chunksize for data that doesn't fit in memory AT ALL:
    for chunk in pd.read_csv(path, chunksize=N, dtype={...}):
        running_result = running_result.add(chunk.groupby(...).sum(),
                                              fill_value=0)
    -> only ONE chunk resident in memory at any time

Rule of thumb for category: unique_values / total_rows well under
~0.5 -> category likely helps; close to 1.0 -> category likely hurts.
Always confirm with memory_usage(deep=True), never assume.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PANDAS MEMORY OPTIMIZATION
=====================================================================

1. How would you optimize the memory usage of a large DataFrame?
   Walk through your process end to end.

2. Why does `df.memory_usage()` without `deep=True` give a misleading
   number for a DataFrame with `object` (string) columns? What is it
   actually measuring instead?

3. How do you handle a dataset that doesn't fit in memory using
   pandas (`chunksize`)? Walk through what stays in memory at any
   given moment while iterating chunks.

4. In this file's chunksize example, why is `running_qty_by_region`
   updated with `.add(..., fill_value=0)` instead of just being
   overwritten each iteration?

5. What does `pd.to_numeric(col, downcast="integer")` actually do
   under the hood, and how is it safer than manually calling
   `.astype("int8")`?

6. Explain what happens, concretely, when you `.astype("int8")` a
   column containing the value 300, without downcasting first. Why
   does this NOT raise an exception the way you might expect?

7. Explain how the `category` dtype achieves its memory savings in
   terms of `.cat.categories` and `.cat.codes`. Which one is stored
   once, and which one is stored per row?

8. Why did converting `region` (5 unique values) to `category` save a
   large percentage of memory in this file, while converting
   `customer_id` (300,000 unique values) to `category` made memory
   usage WORSE? What's the underlying reason for the difference?

9. What rule of thumb would you use to decide whether a given
   `object` column is a good candidate for `category`, and how would
   you actually verify your guess before shipping it?

10. Why is it better to pass a `dtype=` mapping directly to
    `pd.read_csv()` than to load the DataFrame with default dtypes
    and downcast it afterward?

11. In `optimize_dataframe()`, why does the function operate on a
    COPY of the input DataFrame rather than mutating it in place?
    Why does that matter in a pipeline made of chained steps?

12. If a numeric column contains a stray non-numeric value like
    "N/A", what's the difference between
    `pd.to_numeric(col, errors="raise")` and
    `pd.to_numeric(col, errors="coerce")`, and when would you want
    each in a production ETL job?

13. You need to compute a sum grouped by region over a 40GB CSV on a
    machine with 16GB RAM. Describe the `chunksize` approach you'd
    use, including what you would and would NOT keep in memory.

14. Besides `dtype` choices, what's one reason reading with
    `usecols=` (as used in the chunksize example) also reduces memory
    usage, independent of category/downcasting?

15. Why can converting float64 to float32 with
    `pd.to_numeric(col, downcast="float")` be riskier to reason about
    than integer downcasting, in terms of what you might lose?
=====================================================================
"""
