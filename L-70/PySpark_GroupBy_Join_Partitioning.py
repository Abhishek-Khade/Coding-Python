"""
=====================================================================
PYSPARK GROUPBY, JOIN & PARTITIONING - Complete Notes with
Executable Examples (Including Data Skew)
=====================================================================

PySpark is the Python API for Apache Spark, a DISTRIBUTED processing
engine. The single biggest mental shift coming from pandas is this:
a pandas DataFrame lives entirely in the memory of ONE machine, but
a Spark DataFrame is logically split into PARTITIONS - independent
chunks of rows - that are physically scattered across many EXECUTORS
(worker processes, usually on different machines) and processed in
PARALLEL. Every operation that needs rows from a DIFFERENT partition
than the one a task is currently holding (matching keys for a
groupBy or a join) requires a SHUFFLE: writing data to disk/network,
sending it across the cluster, and reading it back into new
partitions grouped by key. Shuffles are by far the most expensive
thing you can trigger in Spark - they involve network I/O and disk
I/O, not just CPU - so most Spark performance tuning is really about
minimizing, avoiding, or rebalancing shuffles.

groupBy().agg(...) in PySpark is the SAME conceptual split-apply-
combine model as pandas' groupby().agg() (see L-44,
GroupBy_Merge_Join_Pivot.py, for the relational fundamentals) - the
difference is entirely about EXECUTION ENGINE, not semantics: pandas
applies the split/apply/combine in local memory with no network
involved, while Spark's split step is a genuine network SHUFFLE that
redistributes rows across executors so that every row for a given
key ends up on the same partition. join() is the same story: it is
the same relational join pandas' merge()/join() perform, but Spark
must choose a JOIN STRATEGY (broadcast vs. shuffle/sort-merge) to
decide HOW to get matching keys physically co-located before it can
compare them.

PARTITIONING and DATA SKEW are the two concepts that have no real
pandas analogue at all, because pandas never distributes data across
machines. A PARTITION is a chunk of the DataFrame that one task on
one executor processes; how many partitions you have, and how EVENLY
rows are spread across them, directly determines whether a Spark job
finishes in balanced parallel time or gets stuck waiting on one
overloaded "straggler" task - which is exactly what DATA SKEW causes.
pyspark is NOT installed in this sandbox (no Java/cluster available),
so every section below shows REAL, correct PySpark code wrapped in a
try/except ImportError, and then SIMULATES the identical computation
using pandas so you see live, correct output proving the concept -
the partitioning/skew sections additionally print a SIMULATED
partition-layout table, clearly labeled, since pandas has no actual
partitions to inspect.
=====================================================================
"""

import random
import zlib

import numpy as np
import pandas as pd

try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

RNG = np.random.default_rng(seed=42)
random.seed(42)

print("--- Overview ---")
print("Spark DataFrames are split into PARTITIONS spread across executors.")
print("groupBy/join often require a SHUFFLE (network redistribution by key).")
print("DATA SKEW = one key has far more rows than others -> straggler task.")
if not SPARK_AVAILABLE:
    print("\n[NOTE] pyspark is not installed in this sandbox - every section")
    print("below shows REAL PySpark code (wrapped in try/except ImportError)")
    print("and then falls back to a pandas SIMULATION of the same result so")
    print("the concepts are still proven with real, live, executed output.")


"""
---------------------------------------------------------------------
1. SPARKSESSION AND THE FALLBACK PATTERN USED THROUGHOUT  ⭐⭐⭐
---------------------------------------------------------------------
Every Spark program starts by getting (or creating) a SparkSession -
the single entry point for DataFrame operations, SQL, and cluster
configuration. `.master("local[*]")` runs Spark on the local machine
using all available cores (fine for dev/testing); in production this
would instead point at a cluster manager (YARN, Kubernetes, a
standalone Spark master). Nothing below actually connects to a
cluster in this sandbox - the `try/except ImportError` pattern lets
the REAL API calls stay in the source (so you learn the true syntax)
while the script still runs clean end-to-end without pyspark
installed.
---------------------------------------------------------------------
"""

print("\n--- SparkSession Setup (Real Code vs. Sandbox Fallback) ---")

if SPARK_AVAILABLE:
    spark = (
        SparkSession.builder.appName("GroupByJoinPartitioning")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")  # default is 200; tuned down for a small demo
        .getOrCreate()
    )
    print("Real SparkSession created:", spark.version)
else:
    spark = None
    print("SparkSession.builder.appName(...).master('local[*]').getOrCreate()")
    print("  -> ImportError: pyspark not installed here. In production this")
    print("     returns/reuses a live SparkSession connected to a cluster.")
    print("Falling back to pandas for the rest of this file's DEMOS.")


"""
---------------------------------------------------------------------
2. groupBy().agg(...) AND THE SHUFFLE IT TRIGGERS  ⭐⭐⭐
---------------------------------------------------------------------
Semantically, Spark's groupBy() is identical to pandas' groupby():
split rows into groups by key, apply an aggregation independently
per group, combine the results. The EXECUTION is what differs: rows
for the same key can start out on ANY partition, on ANY executor, so
before Spark can sum/average per key it must physically move every
row to the partition that is responsible for its key - this network
redistribution is the SHUFFLE. A shuffle means: writing shuffle files
to local disk, transferring them over the network to other
executors, then reading them back in - by far the most expensive
step in most Spark jobs (network + disk I/O, not just CPU). pandas'
groupby() NEVER pays this cost because everything already lives in
one process's memory - there is nothing to redistribute.
---------------------------------------------------------------------
"""

print("\n--- groupBy + agg (Real PySpark) vs. pandas groupby + agg ---")

orders_pdf = pd.DataFrame(
    {
        "order_id": range(1, 21),
        "customer_id": RNG.integers(1, 6, size=20),
        "region": RNG.choice(["US", "EU", "APAC"], size=20),
        "amount": RNG.uniform(10, 500, size=20).round(2),
    }
)

if SPARK_AVAILABLE:
    orders_sdf = spark.createDataFrame(orders_pdf)

    # Real PySpark: groupBy triggers a shuffle keyed on "region" so all rows
    # sharing a region land on the same partition before the sum/avg runs.
    region_totals_sdf = orders_sdf.groupBy("region").agg(
        F.sum("amount").alias("total_amount"),
        F.avg("amount").alias("avg_amount"),
        F.count("*").alias("num_orders"),
    )
    region_totals_sdf.show()
else:
    print("Real PySpark code (not executed - no cluster here):")
    print('    region_totals = (orders_sdf.groupBy("region")')
    print('                      .agg(F.sum("amount").alias("total_amount"),')
    print('                           F.avg("amount").alias("avg_amount"),')
    print('                           F.count("*").alias("num_orders")))')
    print("    # <- this .groupBy(...) call is what triggers the shuffle")
    print("\nSIMULATED equivalent, computed live with pandas groupby+agg:")
    region_totals_pdf = orders_pdf.groupby("region").agg(
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        num_orders=("order_id", "count"),
    )
    print(region_totals_pdf.round(2))
    print("\nSame relational answer, same split-apply-combine model as L-44 -")
    print("pandas just never pays a network shuffle cost to get there.")


"""
---------------------------------------------------------------------
3. JOINS: INNER / LEFT / RIGHT / OUTER (Same Shapes as pandas merge)  ⭐⭐⭐
---------------------------------------------------------------------
Spark's DataFrame.join() supports the same join TYPES as SQL and
pandas merge()/join(): inner (only matching keys on both sides),
left/right outer (keep all rows from one side, nulls where the other
side has no match), and full outer (keep all rows from BOTH sides).
The `on=` / `how=` parameters map directly onto what you already
know from L-44's pandas merge() coverage - the relational semantics
are identical, only the execution engine differs (see Section 4 for
how Spark decides to actually PERFORM a join).
---------------------------------------------------------------------
"""

print("\n--- Joins: inner / left / right / outer ---")

customers_pdf = pd.DataFrame(
    {
        "customer_id": [1, 2, 3, 4, 7],  # note: 5 missing, 7 has no matching order
        "name": ["Ana", "Ben", "Cara", "Dev", "Gia"],
        "segment": ["SMB", "Enterprise", "SMB", "Enterprise", "SMB"],
    }
)

# BROKEN version first: merging on mismatched column names with no `on=`
# raises a real, catchable pandas error - the exact same class of bug that
# trips up a PySpark .join() when the two sides don't share a key column
# name and you forget to specify the join condition explicitly.
customers_bad_pdf = customers_pdf.rename(columns={"customer_id": "cust_id"})
try:
    orders_pdf.merge(customers_bad_pdf)
except pd.errors.MergeError as e:
    print("Naive join with mismatched key column names failed:", e)

# FIXED: name the columns explicitly on each side (left_on/right_on in
# pandas; Spark's equivalent is `.join(other, orders_sdf.customer_id ==
# customers_sdf.cust_id, how=...)` when key names differ across DataFrames).
fixed_merge = orders_pdf.merge(
    customers_bad_pdf, left_on="customer_id", right_on="cust_id", how="inner"
)
print("\nFixed by naming each side's key explicitly - rows matched:", len(fixed_merge))

if SPARK_AVAILABLE:
    customers_sdf = spark.createDataFrame(customers_pdf)
    inner_sdf = orders_sdf.join(customers_sdf, on="customer_id", how="inner")
    left_sdf = orders_sdf.join(customers_sdf, on="customer_id", how="left")
    right_sdf = orders_sdf.join(customers_sdf, on="customer_id", how="right")
    outer_sdf = orders_sdf.join(customers_sdf, on="customer_id", how="outer")
    print("inner:", inner_sdf.count(), "left:", left_sdf.count(),
          "right:", right_sdf.count(), "outer:", outer_sdf.count())
else:
    print("\nReal PySpark code (not executed):")
    print('    inner = orders_sdf.join(customers_sdf, on="customer_id", how="inner")')
    print('    left  = orders_sdf.join(customers_sdf, on="customer_id", how="left")')
    print('    right = orders_sdf.join(customers_sdf, on="customer_id", how="right")')
    print('    outer = orders_sdf.join(customers_sdf, on="customer_id", how="outer")')
    print("\nSIMULATED equivalent, computed live with pandas merge():")
    for how in ["inner", "left", "right", "outer"]:
        merged = orders_pdf.merge(customers_pdf, on="customer_id", how=how)
        print(f"  how={how:<6} -> {len(merged)} rows "
              f"({merged['name'].isna().sum()} unmatched left-side nulls)")


"""
---------------------------------------------------------------------
4. JOIN STRATEGIES: BROADCAST vs. SHUFFLE (SORT-MERGE) JOIN  ⭐⭐⭐
---------------------------------------------------------------------
Once Spark knows WHAT to join, its query optimizer (Catalyst) still
has to pick HOW to physically execute it:

  BROADCAST JOIN (the fast path) - if one side is small enough to fit
  entirely in memory (governed by
  `spark.sql.autoBroadcastJoinThreshold`, 10MB by default), Spark
  copies that ENTIRE small DataFrame to every executor. Each executor
  then joins its local partition of the big side against the small
  side purely in local memory - NO SHUFFLE of the large side at all.
  This is dramatically cheaper whenever one side is a small
  "dimension" table (e.g. a customers/lookup table) being joined
  against a huge "fact" table (e.g. orders).

  SHUFFLE / SORT-MERGE JOIN (the expensive path) - when BOTH sides
  are too large to broadcast, Spark must shuffle both DataFrames so
  that rows with the same join key land on the same partition (a
  full network shuffle of BOTH sides), then sort and merge matching
  keys within each partition. This is correct for any size of data
  but pays the full shuffle cost on both sides.

You can nudge Spark toward the fast path explicitly with
`F.broadcast(df)` or `.hint("broadcast")`, rather than relying on the
size-based auto-detection (useful when Spark's size estimate is
wrong, e.g. after heavy filtering it doesn't know about yet).
---------------------------------------------------------------------
"""

print("\n--- Join Strategies: Broadcast (fast) vs. Shuffle/Sort-Merge (slow) ---")

if SPARK_AVAILABLE:
    # Fast path: force a broadcast of the small `customers_sdf` table so the
    # large `orders_sdf` side never gets shuffled across the network at all.
    broadcast_join_sdf = orders_sdf.join(
        F.broadcast(customers_sdf), on="customer_id", how="inner"
    )
    # Equivalent using a join hint instead of the broadcast() wrapper function:
    hinted_join_sdf = orders_sdf.join(
        customers_sdf.hint("broadcast"), on="customer_id", how="inner"
    )
    broadcast_join_sdf.explain()  # physical plan shows "BroadcastHashJoin"
else:
    print("Real PySpark code (not executed):")
    print("    # small `customers_sdf` fits in memory on every executor ->")
    print("    # broadcast it and skip shuffling the large orders_sdf side:")
    print('    fast = orders_sdf.join(F.broadcast(customers_sdf), on="customer_id")')
    print('    fast = orders_sdf.join(customers_sdf.hint("broadcast"), on="customer_id")')
    print("    # both sides large -> Spark falls back to a full shuffle +")
    print("    # sort-merge join instead, co-locating matching keys first:")
    print('    slow = big_orders_sdf.join(big_customers_sdf, on="customer_id")')
    print("\n[No physical query plan to show without a real cluster - the point")
    print(" to remember: broadcast avoids shuffling the LARGE side entirely;")
    print(" sort-merge shuffles BOTH sides. There's nothing for pandas to")
    print(" simulate here since a single-machine merge never chooses a")
    print(" distributed strategy in the first place - it's always 'local'.]")


"""
---------------------------------------------------------------------
5. PARTITIONING FUNDAMENTALS: repartition() vs. coalesce()  ⭐⭐⭐
---------------------------------------------------------------------
A PARTITION is a chunk of the DataFrame's rows that one task, running
on one executor core, processes independently. More partitions means
more parallelism (up to your cluster's core count) but also more
per-task overhead; too FEW partitions means cores sit idle; too MANY
means overhead dominates and you get a flood of tiny tasks.

  .repartition(n)          -> can INCREASE or DECREASE the partition
                               count. ALWAYS triggers a full shuffle,
                               because it round-robins (or hash-
                               partitions, if you pass column(s)) rows
                               across a brand new set of partitions.
  .repartition(n, "col")   -> like above, but HASH-partitions by a
                               column's value, so all rows for a given
                               key land in the same partition -
                               commonly done BEFORE a big groupBy/join
                               on that same key to control skew.
  .coalesce(n)              -> can only DECREASE the partition count.
                               Avoids a full shuffle by simply MERGING
                               adjacent existing partitions together
                               on the SAME executors where possible -
                               much cheaper, but can't rebalance data
                               that's already unevenly distributed.

pandas has no partitions at all - the block below SIMULATES how rows
would be distributed by printing an analogous partition-count table.
---------------------------------------------------------------------
"""

print("\n--- Partitioning: repartition() vs. coalesce() ---")

if SPARK_AVAILABLE:
    print("orders_sdf.rdd.getNumPartitions():", orders_sdf.rdd.getNumPartitions())

    repartitioned_sdf = orders_sdf.repartition(8)                       # round-robin, full shuffle
    repartitioned_by_key_sdf = orders_sdf.repartition(8, "customer_id")  # hash by key, full shuffle
    coalesced_sdf = orders_sdf.coalesce(2)                              # merge adjacent, no full shuffle

    print("after repartition(8):", repartitioned_sdf.rdd.getNumPartitions())
    print("after repartition(8, 'customer_id'):", repartitioned_by_key_sdf.rdd.getNumPartitions())
    print("after coalesce(2):", coalesced_sdf.rdd.getNumPartitions())
else:
    print("Real PySpark code (not executed):")
    print("    orders_sdf.rdd.getNumPartitions()          # inspect current count")
    print("    orders_sdf.repartition(8)                  # round-robin, FULL shuffle, can go up/down")
    print("    orders_sdf.repartition(8, 'customer_id')    # hash by key, FULL shuffle")
    print("    orders_sdf.coalesce(2)                      # merge adjacent, NO full shuffle, down-only")

    def simulate_hash_partition(customer_id, num_partitions):
        # Deterministic stand-in for Spark's hash-partitioning: a stable
        # hash of the key mod the partition count decides which partition
        # a row lands in. Python's built-in hash() isn't stable across
        # runs (PYTHONHASHSEED), so crc32 is used here for a reproducible demo.
        return zlib.crc32(str(customer_id).encode()) % num_partitions

    num_partitions = 4
    simulated = orders_pdf.copy()
    simulated["simulated_partition"] = simulated["customer_id"].map(
        lambda c: simulate_hash_partition(c, num_partitions)
    )
    print(f"\n[SIMULATED] row counts per hash-partition as if "
          f"repartition({num_partitions}, 'customer_id') had run:")
    print(simulated["simulated_partition"].value_counts().sort_index().rename("row_count"))
    print("\nThis is only a printed illustration of the CONCEPT - pandas never")
    print("actually splits this DataFrame across separate tasks/executors.")


"""
---------------------------------------------------------------------
6. DATA SKEW: DEFINITION AND DIAGNOSIS  ⭐⭐⭐
---------------------------------------------------------------------
DATA SKEW happens when the rows for one (or a few) key values vastly
outnumber the rows for every other key. Because groupBy/join hash-
partition rows by key, EVERY row for that hot key is forced onto the
SAME partition - so the single task handling that partition has to
process far more data than every other task. Spark can't start the
NEXT stage until ALL tasks in the current stage finish, so the whole
job idles waiting on that one overloaded "straggler" task while every
other executor sits finished and idle. This is precisely what the
syllabus question "how do you handle data skew in a PySpark join?"
is asking about - and it's also the most direct, concrete answer:
skew is a partition SIZE imbalance caused by a key FREQUENCY
imbalance, not a data-correctness problem.

Below, a REAL skewed dataset is built (one customer_id makes up 90%
of all rows) and the imbalance is measured directly with a groupby
row count - a single hot key dwarfing every other key is exactly the
signature you'd look for in a real Spark UI's "Stage" tab (one task
taking far longer, and reading far more shuffle data, than the rest).
---------------------------------------------------------------------
"""

print("\n--- Data Skew: Building and Diagnosing a Real Skewed Dataset ---")

TOTAL_ROWS = 10_000
HOT_CUSTOMER = "CUST_HOT"
hot_row_count = int(TOTAL_ROWS * 0.90)               # the hot key owns 90% of all rows
cold_row_count = TOTAL_ROWS - hot_row_count
cold_customers = [f"CUST_{i:03d}" for i in range(1, 51)]  # remaining 10% spread over 50 keys

skewed_pdf = pd.DataFrame(
    {
        "customer_id": (
            [HOT_CUSTOMER] * hot_row_count
            + list(RNG.choice(cold_customers, size=cold_row_count))
        ),
        "amount": RNG.uniform(5, 300, size=TOTAL_ROWS).round(2),
    }
).sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle row order like real ingested data

skew_counts = skewed_pdf.groupby("customer_id").size().sort_values(ascending=False)
print("Top 5 keys by row count (the skew signature):")
print(skew_counts.head(5))
print(f"\nHottest key '{skew_counts.index[0]}' alone accounts for "
      f"{skew_counts.iloc[0] / TOTAL_ROWS:.1%} of all {TOTAL_ROWS} rows.")
print("In real Spark, EVERY one of those rows hash-partitions onto the SAME")
print("partition -> that partition's task becomes a straggler the entire")
print("job waits on, while tasks for the other 50 keys finish almost instantly.")


"""
---------------------------------------------------------------------
7. MITIGATING SKEW: SALTING THE HOT KEY  ⭐⭐⭐
---------------------------------------------------------------------
SALTING artificially splits one hot key's rows across several
SYNTHETIC sub-keys so no single partition gets overloaded, then
combines the partial results back together in a second aggregation
pass:

  Stage 1 (spread out) - append a random suffix (0..N-1) to every
  row's key, turning "CUST_HOT" into "CUST_HOT_0", "CUST_HOT_1", ...
  Now the hot key's rows are hash-partitioned across N different
  partitions instead of just one, and each partition gets a roughly
  even, manageable slice.

  Stage 2 (combine) - aggregate on the SALTED key first (this is the
  expensive, now-parallelized shuffle), then strip the salt suffix
  and aggregate AGAIN on the true original key (this second shuffle
  is cheap - it only has to combine a handful of partial results per
  original key, not the full raw row count).

This trades ONE unbalanced shuffle for TWO balanced ones, which is
almost always a net win when skew is severe.
---------------------------------------------------------------------
"""

print("\n--- Mitigating Skew: Salting the Hot Key (Real Working Demo) ---")

if SPARK_AVAILABLE:
    skewed_sdf = spark.createDataFrame(skewed_pdf)
    NUM_SALT_BUCKETS = 8

    # Stage 1: spread the hot key's rows across NUM_SALT_BUCKETS synthetic keys
    salted_sdf = skewed_sdf.withColumn(
        "salted_key",
        F.concat(F.col("customer_id"), F.lit("_"), (F.rand() * NUM_SALT_BUCKETS).cast("int")),
    )
    partial_sdf = salted_sdf.groupBy("salted_key").agg(F.sum("amount").alias("partial_sum"))

    # Stage 2: strip the salt suffix and combine the partial sums per real key
    final_sdf = (
        partial_sdf.withColumn("customer_id", F.element_at(F.split("salted_key", "_"), 1))
        .groupBy("customer_id")
        .agg(F.sum("partial_sum").alias("total_amount"))
    )
    final_sdf.orderBy(F.desc("total_amount")).show(5)
else:
    print("Real PySpark code (not executed) - shown above the pandas demo runs below.")

    NUM_SALT_BUCKETS = 8

    def salt_key(customer_id: str, num_buckets: int) -> str:
        # Real, working salting logic - a random suffix per ROW, not per key,
        # so the hot key's rows land in different buckets from each other.
        return f"{customer_id}_{random.randint(0, num_buckets - 1)}"

    salted_pdf = skewed_pdf.copy()
    salted_pdf["salted_key"] = salted_pdf["customer_id"].map(
        lambda c: salt_key(c, NUM_SALT_BUCKETS)
    )

    print(f"\nBEFORE salting - rows for the hot key land on ONE group:")
    print(f"  '{HOT_CUSTOMER}': {skew_counts.iloc[0]} rows in a single group")

    stage1_counts = salted_pdf.groupby("salted_key").size().sort_values(ascending=False)
    hot_salted_counts = stage1_counts[stage1_counts.index.str.startswith(HOT_CUSTOMER)]
    print(f"\nAFTER salting into {NUM_SALT_BUCKETS} buckets - same rows now spread across "
          f"{len(hot_salted_counts)} groups:")
    print(hot_salted_counts.sort_index())
    print(f"  max bucket = {hot_salted_counts.max()} rows vs. the original "
          f"{skew_counts.iloc[0]} rows -> "
          f"{skew_counts.iloc[0] / hot_salted_counts.max():.1f}x smaller per-group load")

    # Stage 1 aggregation (on the now-balanced salted key)
    partial_pdf = salted_pdf.groupby("salted_key")["amount"].sum().reset_index(name="partial_sum")
    # Stage 2: strip the salt suffix, then combine partial sums per TRUE key
    partial_pdf["customer_id"] = partial_pdf["salted_key"].str.rsplit("_", n=1).str[0]
    final_pdf = (
        partial_pdf.groupby("customer_id")["partial_sum"]
        .sum()
        .rename("total_amount")
        .sort_values(ascending=False)
    )
    print("\nFinal combined totals (correctness check - matches a plain groupby):")
    print(final_pdf.head(3).round(2))
    direct_check = skewed_pdf.groupby("customer_id")["amount"].sum().sort_values(ascending=False)
    matches = np.isclose(final_pdf.head(3).values, direct_check.head(3).values).all()
    print("Matches a direct (unsalted) groupby sum on the same data:", matches)


"""
---------------------------------------------------------------------
8. MITIGATING SKEW: BROADCAST ON THE SMALL SIDE + ADAPTIVE QUERY
   EXECUTION (AQE)  ⭐⭐
---------------------------------------------------------------------
Salting is the general-purpose fix, but two other techniques matter
just as much in interviews:

  BROADCAST JOIN AS A SKEW FIX - if the skew is on the SMALL side of
  a join (e.g. a lookup/dimension table, not the fact table), the
  cleanest fix is often simply to broadcast it (Section 4). A
  broadcast join never shuffles the large side by key AT ALL, so a
  skewed key distribution in the small side is irrelevant - every
  executor already has the WHOLE small table locally. This only
  works while the small side genuinely fits comfortably in executor
  memory; it does nothing if the skew is on the LARGE side.

  ADAPTIVE QUERY EXECUTION (AQE) - modern Spark (3.0+) can detect and
  fix skew automatically at runtime, without manual salting:
  `spark.sql.adaptive.enabled` and `spark.sql.adaptive.skewJoin.enabled`
  make Spark inspect actual shuffle partition sizes after a stage
  runs, and if one partition is disproportionately large, it SPLITS
  that oversized partition into several smaller sub-partitions and
  joins each piece independently - conceptually automating exactly
  the "spread the hot key out" idea behind manual salting. This is
  the modern default answer to "how do you handle skew" in most
  current Spark deployments, with manual salting as the fallback for
  older Spark versions or cases AQE doesn't catch.
---------------------------------------------------------------------
"""

print("\n--- Mitigating Skew: Broadcast (Small Side) + AQE ---")

if SPARK_AVAILABLE:
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
    print("AQE skew-join handling enabled:",
          spark.conf.get("spark.sql.adaptive.skewJoin.enabled"))

    # If the skew were on customers_sdf (the small side) instead of the fact
    # table, broadcasting it sidesteps the skew entirely - no shuffle by key
    # happens on that side at all:
    skew_safe_join_sdf = orders_sdf.join(F.broadcast(customers_sdf), on="customer_id")
    skew_safe_join_sdf.show(3)
else:
    print("Real PySpark code (not executed):")
    print('    spark.conf.set("spark.sql.adaptive.enabled", "true")')
    print('    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")')
    print("    # -> Spark auto-splits any oversized shuffle partition it detects")
    print('    safe_join = orders_sdf.join(F.broadcast(customers_sdf), on="customer_id")')
    print("    # -> broadcasting sidesteps skew entirely IF the skew is on the")
    print("    #    small side; it does nothing for skew on the large side.")
    print("\n[Nothing to simulate execution-wise here - AQE is a cluster runtime")
    print(" behavior with no single-machine pandas equivalent; the broadcast")
    print(" mechanics were already demonstrated concretely in Section 4.]")


"""
---------------------------------------------------------------------
9. DATA ENGINEERING USE CASE: A SKEW-AWARE AGGREGATION PIPELINE STEP  ⭐⭐⭐
---------------------------------------------------------------------
Putting it together the way you'd actually write it in a pipeline:
check partition balance BEFORE committing to a big groupBy/join,
choose a repartition strategy deliberately (rather than accepting
whatever partitioning ingestion left you with), and only reach for
salting when the skew is severe enough to matter - it adds real
complexity (two aggregation passes) so it isn't free.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Deciding Whether Skew Needs Salting ---")


def needs_salting(group_counts: pd.Series, hot_key_share_threshold: float = 0.20) -> bool:
    """Cheap, real diagnostic: does the largest group dominate the dataset?

    Mirrors a real pipeline check you'd run against
    `df.groupBy(key).count()` results before deciding whether a full
    salting pass is worth the added complexity, or whether Spark's
    normal hash-partitioned shuffle (or AQE) will handle it fine.
    """
    if group_counts.empty:
        return False
    hot_share = group_counts.iloc[0] / group_counts.sum()
    return hot_share >= hot_key_share_threshold


balanced_pdf = pd.DataFrame(
    {"customer_id": RNG.choice(cold_customers, size=TOTAL_ROWS)}
)  # same 50-key universe as the skewed dataset, but with NO hot key at all
balanced_counts = balanced_pdf.groupby("customer_id").size().sort_values(ascending=False)
print("Balanced dataset hot-key share:",
      f"{balanced_counts.iloc[0] / balanced_counts.sum():.1%}",
      "-> needs_salting:", needs_salting(balanced_counts))
print("Skewed dataset hot-key share:  ",
      f"{skew_counts.iloc[0] / skew_counts.sum():.1%}",
      "-> needs_salting:", needs_salting(skew_counts))
print("\nA real pipeline step would run this check right after ingestion,")
print("route skewed keys through the salted two-stage aggregation from")
print("Section 7, and leave everything else on the normal groupBy/join path -")
print("paying salting's extra complexity only where it actually earns its keep.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Partition        -> a chunk of rows processed by one task on one executor
Shuffle           -> network+disk redistribution of rows by key across
                     executors; triggered by groupBy, join (unless
                     broadcast), repartition(), and most wide transforms

groupBy().agg()   -> same split-apply-combine as pandas groupby(), but
                     the "split" is a real network shuffle in Spark

Join strategies:
    Broadcast join    -> small side copied whole to every executor;
                          large side is NEVER shuffled. Fast path.
    Shuffle/sort-merge -> both sides shuffled + sorted by key when
                          neither side is small enough to broadcast.
    F.broadcast(df) / df.hint("broadcast") -> force the fast path

Partitioning:
    df.rdd.getNumPartitions()     -> inspect current partition count
    df.repartition(n)             -> up OR down, ALWAYS full shuffle
    df.repartition(n, "col")      -> hash by key, full shuffle
    df.coalesce(n)                -> DOWN only, merges adjacent
                                      partitions, no full shuffle

Data skew -> one key's row count dwarfs the others -> that
             partition's task becomes a straggler the whole
             stage/job waits on

Mitigations:
    1. Salting     -> split hot key into N synthetic sub-keys,
                       aggregate twice (on salted key, then combined)
    2. Broadcast    -> sidesteps skew when it's on the SMALL join side
    3. AQE          -> spark.sql.adaptive.skewJoin.enabled = true;
                       Spark auto-splits oversized shuffle partitions
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYSPARK GROUPBY, JOIN & PARTITIONING
=====================================================================

1. How do you handle data skew in a PySpark join? Walk through at
   least two distinct mitigation techniques.

2. Why does `orders_sdf.groupBy("region").agg(...)` require a
   shuffle in Spark when the equivalent `orders_pdf.groupby("region")
   .agg(...)` in pandas never does?

3. What is a partition in Spark, and how does the NUMBER of
   partitions affect parallelism? What happens if you have far too
   few partitions for your cluster's core count? Far too many?

4. Explain the difference between a broadcast join and a shuffle
   (sort-merge) join. Under what condition does Spark choose each
   one automatically, and what configuration controls that decision?

5. What is `spark.sql.autoBroadcastJoinThreshold`, and why might you
   override Spark's automatic choice with `F.broadcast(df)` or
   `.hint("broadcast")` explicitly?

6. What is the difference between `.repartition(n)` and
   `.coalesce(n)`? Specifically: can each increase partition count,
   and does each always trigger a full shuffle?

7. Why might `df.repartition(8, "customer_id")` still produce
   unevenly sized partitions even though you asked for exactly 8?

8. Given the `skewed_pdf` dataset in this file (one customer_id is
   90% of all rows), explain concretely what happens to Spark's
   groupBy execution if you group that data by `customer_id` with no
   mitigation in place.

9. Describe how key salting works, step by step. Why does it require
   TWO aggregation passes instead of one, and what does the second
   pass actually combine?

10. If the SMALL side of a join is the one that's skewed, why might
    broadcasting it be a simpler fix than salting?

11. What is Adaptive Query Execution (AQE), and specifically what does
    `spark.sql.adaptive.skewJoin.enabled` do differently from Spark's
    default static query plan?

12. Why is a shuffle considered expensive in Spark, in terms of what
    physical resources it consumes, compared to a purely in-memory
    pandas groupby?

13. What symptom would you look for in the Spark UI's Stages tab to
    diagnose data skew in a running job?

14. Why does salting trade one unbalanced shuffle for two balanced
    shuffles, and why is that usually still a net win?

15. Semantically, how do PySpark's `join()` how= options (inner,
    left, right, outer) map onto pandas' `merge()` how= options from
    L-44 - what's identical, and what's purely an execution-engine
    difference?
=====================================================================
"""
