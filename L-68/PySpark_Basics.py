"""
=====================================================================
PYSPARK BASICS - RDDs vs DataFrames, Transformations vs Actions
=====================================================================

Apache SPARK is a DISTRIBUTED COMPUTE ENGINE: it takes a dataset too
big to fit on (or process fast enough on) one machine, PARTITIONS it
into chunks, ships those chunks out to many worker machines (a
"cluster"), and runs your operations on all the chunks IN PARALLEL.
PySpark is just the Python API on top of that engine.

Data engineers reach for Spark specifically when pandas stops being
viable - pandas loads an ENTIRE dataset into the memory of ONE
machine and runs every operation on ONE core (mostly). Once a
dataset is too large for a single machine's RAM, or a job needs more
throughput than one CPU can give you, Spark lets the SAME kind of
transformation logic run across dozens or thousands of machines at
once.

Spark exposes that distributed data through TWO abstractions:
    - RDD (Resilient Distributed Dataset)  - the original, low-level,
      "just a distributed collection of Python objects" API.
    - DataFrame - a newer, schema-aware, SQL-table-like API built ON
      TOP of RDDs, optimized by Spark's Catalyst query planner.

And every operation you call on either one is either:
    - a TRANSFORMATION - describes a computation, returns a NEW
      RDD/DataFrame, but runs NOTHING yet (lazy), or
    - an ACTION - actually TRIGGERS execution of everything queued up
      so far, and returns or persists a real result.

This distinction - transformations vs actions, and the LAZY
EVALUATION it enables - is the single most commonly asked PySpark
interview question, and it's the backbone of this file.
=====================================================================
"""

import functools
import math
import pandas as pd

print("--- Overview ---")
print("Spark = a distributed engine that partitions data across a cluster")
print("and runs your operations on every partition in parallel.")
print("RDD = low-level distributed collection.  DataFrame = schema-aware,")
print("optimized, table-like API built on top of RDDs.")
print("Transformations (map/filter/select/withColumn/groupBy) are LAZY -")
print("they just build a plan.  Actions (collect/count/show/write) are")
print("what actually RUN that plan.")


"""
---------------------------------------------------------------------
1. SPARK: WHAT IT IS, AND SETTING UP A SparkSession  ⭐⭐
---------------------------------------------------------------------
Every modern PySpark program starts by creating a SparkSession - the
single entry point to Spark's DataFrame API, cluster resources, and
configuration. `.master("local[*]")` tells Spark to run as its own
local "cluster" using all CPU cores on this machine - the same code
would instead point `.master(...)` at a real cluster manager (YARN,
Kubernetes, a Spark standalone cluster) in production, with ZERO
other code changes required. That portability (laptop -> cluster,
same code) is itself a big reason Spark is popular.

This sandbox doesn't have a JVM/Spark install (pyspark needs a Java
runtime it can't build here), so every section below tries the REAL
PySpark call first and falls back to a plain-Python/pandas SIMULATION
that produces the same, real, correct result - so you see the true
API on the page, and true output in the terminal either way.
---------------------------------------------------------------------
"""

print("\n--- Spark and the SparkSession ---")

try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.appName("InterviewPrepDemo")
        .master("local[*]")           # run Spark locally using all cores - a real
        .getOrCreate()                 # cluster URL goes here in production instead
    )
    SPARK_AVAILABLE = True
    print("PySpark is installed - the REAL Spark code paths below will run.")
except ImportError as e:
    SPARK_AVAILABLE = False
    spark = None
    F = None
    print(f"PySpark isn't installed in this sandbox ({e.__class__.__name__}: {e}).")
    print("Here's what running this file's code against a real Spark cluster")
    print("would produce - each section below SIMULATES the equivalent")
    print("computation in plain Python or pandas and prints real, correct")
    print("output, so the concept is still proven live, not just described.")


"""
---------------------------------------------------------------------
2. RDDs: THE ORIGINAL LOW-LEVEL ABSTRACTION  ⭐⭐⭐
---------------------------------------------------------------------
An RDD (Resilient Distributed Dataset) is Spark's original data
abstraction: an IMMUTABLE collection of Python objects, split into
PARTITIONS spread across the cluster's workers. "Resilient" refers to
FAULT TOLERANCE - Spark tracks the LINEAGE (the chain of
transformations that built an RDD from its source), so if a worker
holding one partition dies, Spark can just RECOMPUTE that partition
from its lineage instead of losing data.

You build one with `spark.sparkContext.parallelize(...)`, then call
.map()/.filter()/.reduce() on it - notice those names.
---------------------------------------------------------------------
"""

print("\n--- RDDs: The Original Low-Level Abstraction ---")

raw_numbers = list(range(1, 11))   # imagine this is millions of rows from a cluster of files

if SPARK_AVAILABLE:
    # REAL PySpark RDD code - exactly what you'd write against a live cluster.
    numbers_rdd = spark.sparkContext.parallelize(raw_numbers, numSlices=4)
    # numSlices is the number of PARTITIONS - the literal unit of parallelism;
    # each partition can be processed on a different worker at the same time.
    doubled_rdd = numbers_rdd.map(lambda x: x * 2)        # TRANSFORMATION (lazy)
    evens_rdd = doubled_rdd.filter(lambda x: x % 4 == 0)   # TRANSFORMATION (lazy)
    collected = evens_rdd.collect()                         # ACTION (runs everything)
    total = evens_rdd.reduce(lambda a, b: a + b)             # ACTION (runs everything again)
    print("RDD .collect() result:", collected)
    print("RDD .reduce() (sum) result:", total)
else:
    print("Simulating the equivalent RDD chain with plain Python...")
    doubled = map(lambda x: x * 2, raw_numbers)              # SAME NAME as RDD.map()
    evens = filter(lambda x: x % 4 == 0, doubled)             # SAME NAME as RDD.filter()
    evens_list = list(evens)
    total = functools.reduce(lambda a, b: a + b, evens_list)  # SAME NAME as RDD.reduce()
    print("simulated RDD-equivalent .collect() result:", evens_list)
    print("simulated RDD-equivalent .reduce() (sum) result:", total)

print("\nNotice the METHOD NAMES: RDD.map() / RDD.filter() / RDD.reduce() are")
print("DELIBERATELY named after Python's own map()/filter()/functools.reduce()")
print("builtins from the earlier Functional Programming notes - the RDD API")
print("was designed to feel like ordinary functional-style collection")
print("processing, just distributed across a cluster instead of one process.")


"""
---------------------------------------------------------------------
3. DataFrames: THE MODERN HIGH-LEVEL ABSTRACTION  ⭐⭐⭐
---------------------------------------------------------------------
A Spark DataFrame is a distributed collection of ROWS with a fixed,
named, typed SCHEMA - conceptually a giant, cluster-spanning SQL
table (and closely related to a pandas DataFrame, just distributed).
Because it knows the schema and the exact sequence of column-level
operations you asked for, Spark can run the whole thing through
CATALYST, its query optimizer, before ever touching real data - an
optimization an RDD's opaque Python lambdas make impossible (Spark
can't see "inside" `lambda x: x * 2` the way it can see inside
`F.col("n") * 2`).
---------------------------------------------------------------------
"""

print("\n--- DataFrames: The Modern High-Level Abstraction ---")

number_records = [{"n": x} for x in raw_numbers]

if SPARK_AVAILABLE:
    df = spark.createDataFrame(number_records)                    # schema is INFERRED here
    result_df = (
        df.withColumn("doubled", F.col("n") * 2)                    # TRANSFORMATION (lazy)
        .filter(F.col("doubled") % 4 == 0)                           # TRANSFORMATION (lazy)
    )
    result_df.show()                                                  # ACTION (runs it)
    print("inferred schema:", result_df.schema)
else:
    print("Simulating the equivalent DataFrame computation with pandas...")
    df = pd.DataFrame(number_records)
    result_df = df.assign(doubled=df["n"] * 2)
    result_df = result_df[result_df["doubled"] % 4 == 0]
    print(result_df.to_string(index=False))
    print("dtypes (pandas' equivalent of a Spark schema):")
    print(result_df.dtypes.to_string())

print("\nSame RESULT as the RDD version in Section 2, but expressed")
print("declaratively over named, typed columns instead of opaque lambdas -")
print("this is exactly what lets Spark optimize a DataFrame plan.")


"""
---------------------------------------------------------------------
4. TRANSFORMATIONS vs ACTIONS: THE CORE INTERVIEW DISTINCTION  ⭐⭐⭐
---------------------------------------------------------------------
TRANSFORMATIONS  (.map, .filter, .select, .withColumn, .groupBy, ...)
    - Return a NEW RDD/DataFrame describing a computation.
    - Run NOTHING immediately - they're LAZY. Spark just records
      "if you ever ask for a result, here's how to build it."

ACTIONS  (.collect, .count, .show, .write, .reduce, .take, ...)
    - Actually TRIGGER execution of every transformation queued up
      so far, across the whole cluster.
    - Return a real, concrete result to your driver program (or
      write one out to storage).

This is THE recurring interview question for Spark: "why doesn't
calling .filter() do anything yet?" To prove it concretely, here's a
minimal stand-in class that implements the SAME lazy model by hand -
its .map()/.filter() only ever RECORD a pending step, and its
.collect()/.count() are the only methods that touch the real data.
---------------------------------------------------------------------
"""

print("\n--- Transformations vs Actions: The Core Interview Distinction ---")


class LazyCollection:
    """A tiny, correct stand-in for Spark's transformation/action model."""

    def __init__(self, data, pending_ops=None):
        self._data = data                    # the real underlying data (never touched by a transformation)
        self._pending_ops = pending_ops or []  # queued (name, func) steps - NOT applied yet

    def map(self, func):                      # TRANSFORMATION - lazy
        print(f"  [transformation] .map() recorded - {len(self._pending_ops) + 1} step(s) queued, nothing run yet")
        return LazyCollection(self._data, self._pending_ops + [("map", func)])

    def filter(self, func):                   # TRANSFORMATION - lazy
        print(f"  [transformation] .filter() recorded - {len(self._pending_ops) + 1} step(s) queued, nothing run yet")
        return LazyCollection(self._data, self._pending_ops + [("filter", func)])

    def _run_pending_ops(self):
        result = self._data
        for op_name, func in self._pending_ops:
            if op_name == "map":
                result = [func(x) for x in result]
            else:
                result = [x for x in result if func(x)]
        return result

    def collect(self):                        # ACTION - actually executes everything
        print(f"  [ACTION] .collect() called - NOW executing all {len(self._pending_ops)} queued step(s)")
        return self._run_pending_ops()

    def count(self):                          # ACTION - actually executes everything
        print(f"  [ACTION] .count() called - NOW executing all {len(self._pending_ops)} queued step(s)")
        return len(self._run_pending_ops())


print("building a chain of transformations (watch: nothing 'runs' yet)...")
lazy = (
    LazyCollection(list(range(1, 11)))
    .map(lambda x: x * 10)
    .filter(lambda x: x > 50)
)
print("chain built. no data has been touched. calling an ACTION now...")
print("final result:", lazy.collect())

if SPARK_AVAILABLE:
    # The REAL Spark equivalent behaves identically: printing an un-collected
    # RDD/DataFrame shows a PLAN description, not data, because nothing ran yet.
    plan_rdd = spark.sparkContext.parallelize(range(1, 11)).map(lambda x: x * 10).filter(lambda x: x > 50)
    print("real Spark RDD before an action (shows a plan/object, not data):", plan_rdd)
    print("real Spark RDD after calling .collect() (the action):", plan_rdd.collect())


"""
---------------------------------------------------------------------
5. LAZY EVALUATION: WHY SPARK WAITS BEFORE RUNNING ANYTHING  ⭐⭐⭐
---------------------------------------------------------------------
Because transformations don't run immediately, Spark can look at the
ENTIRE chain of them before executing a single one, and OPTIMIZE the
physical plan - e.g. merging two `.filter()` calls into one pass over
the data, pushing filters down before an expensive join/shuffle, or
picking a broadcast join instead of a full shuffle join when one side
is small. pandas can't do this: each line of pandas code runs
EAGERLY, the instant it's called, with no visibility into what the
NEXT line will do.

Below, two `.filter()` predicates are combined into ONE by hand -
exactly the kind of rewrite Catalyst performs automatically - and we
count actual predicate evaluations to make the savings concrete.
---------------------------------------------------------------------
"""

print("\n--- Lazy Evaluation: Why Spark Waits Before Running Anything ---")

big_data = list(range(1, 1_000_001))

# "Naive eager" style - what you get if each filter step runs on its own,
# fully materializing an intermediate list, the way pandas would.
naive_calls = {"count": 0}


def gt_100(x):
    naive_calls["count"] += 1
    return x > 100


def lt_900(x):
    naive_calls["count"] += 1
    return x < 900


step1 = [x for x in big_data if gt_100(x)]      # full pass #1, materializes a big intermediate list
step2 = [x for x in step1 if lt_900(x)]          # full pass #2
print("naive two-pass approach: predicate calls =", naive_calls["count"], "| intermediate lists = 2")

# "Catalyst-style" optimization - the SAME two conditions, combined into ONE
# predicate, evaluated in a SINGLE pass with no intermediate list at all.
optimized_calls = {"count": 0}


def combined_predicate(x):
    optimized_calls["count"] += 1
    return x > 100 and x < 900


optimized = [x for x in big_data if combined_predicate(x)]
print("optimized single-pass approach: predicate calls =", optimized_calls["count"], "| intermediate lists = 0")
print("results match:", step2 == optimized)

if SPARK_AVAILABLE:
    # A real DataFrame's .explain() shows you the ACTUAL physical plan Catalyst
    # picked - a great way to see filter-combining / pushdown for yourself.
    demo_df = spark.createDataFrame([{"n": x} for x in raw_numbers])
    demo_df.filter(F.col("n") > 2).filter(F.col("n") < 8).explain()

print("\nThis is exactly why lazy evaluation matters: Spark gets to see the")
print("WHOLE chain of transformations up front and choose a cheaper physical")
print("plan, instead of naively running each step the instant it's written -")
print("which is exactly what pandas (and the 'naive' block above) must do.")


"""
---------------------------------------------------------------------
6. A REALISTIC ETL EXAMPLE, RDD STYLE  ⭐⭐⭐
---------------------------------------------------------------------
A small, realistic ETL step: given raw order records, keep only
completed orders, and sum revenue PER COUNTRY. Written the RDD way -
filter, then map to (key, value) pairs, then reduceByKey - which is
still fully lazy: .filter()/.map()/.reduceByKey() are ALL
transformations; only the final .collect() is an action.
---------------------------------------------------------------------
"""

print("\n--- ETL Example, RDD Style: Filter -> Map -> Aggregate ---")

order_records = [
    {"order_id": 1, "country": "US", "amount": 250.00, "status": "completed"},
    {"order_id": 2, "country": "US", "amount": 80.50, "status": "refunded"},
    {"order_id": 3, "country": "DE", "amount": 120.00, "status": "completed"},
    {"order_id": 4, "country": "DE", "amount": 60.00, "status": "completed"},
    {"order_id": 5, "country": "US", "amount": 300.00, "status": "completed"},
    {"order_id": 6, "country": "UK", "amount": 45.00, "status": "refunded"},
]

if SPARK_AVAILABLE:
    orders_rdd = spark.sparkContext.parallelize(order_records)
    completed_totals_rdd = (
        orders_rdd
        .filter(lambda r: r["status"] == "completed")     # TRANSFORMATION
        .map(lambda r: (r["country"], r["amount"]))          # TRANSFORMATION
        .reduceByKey(lambda a, b: a + b)                       # TRANSFORMATION (still lazy, even with a shuffle!)
    )
    print("RDD-style revenue by country:", dict(completed_totals_rdd.collect()))  # ACTION
else:
    print("Simulating the equivalent RDD-style aggregation with plain Python...")
    completed = filter(lambda r: r["status"] == "completed", order_records)
    country_amount_pairs = map(lambda r: (r["country"], r["amount"]), completed)
    totals_by_country = {}
    for country, amount in country_amount_pairs:
        totals_by_country[country] = totals_by_country.get(country, 0) + amount   # manual reduceByKey
    print("RDD-style revenue by country:", totals_by_country)


"""
---------------------------------------------------------------------
7. THE SAME ETL EXAMPLE, DataFrame STYLE  ⭐⭐⭐
---------------------------------------------------------------------
The exact same result, written the DataFrame way: `.filter()` +
`.groupBy()` + `.agg()`, reading almost like SQL. This is why
DataFrames are now the default choice for most PySpark pipelines -
fewer lines, declarative (SQL-like) intent instead of manual pair
bookkeeping, and Catalyst gets a real shot at optimizing it (e.g.
pushing the status filter down before any shuffle for the groupBy).
---------------------------------------------------------------------
"""

print("\n--- The Same ETL Example, DataFrame Style ---")

if SPARK_AVAILABLE:
    orders_df = spark.createDataFrame(order_records)
    totals_df = (
        orders_df
        .filter(F.col("status") == "completed")               # TRANSFORMATION
        .groupBy("country")                                      # TRANSFORMATION
        .agg(F.sum("amount").alias("total_amount"))                # TRANSFORMATION
    )
    totals_df.show()                                              # ACTION
else:
    print("Simulating the equivalent DataFrame aggregation with pandas...")
    orders_df = pd.DataFrame(order_records)
    totals_df = (
        orders_df[orders_df["status"] == "completed"]
        .groupby("country")["amount"]
        .sum()
        .reset_index(name="total_amount")
    )
    print(totals_df.to_string(index=False))

print("\nSame numbers as Section 6's RDD version, in a fraction of the code.")
print("DataFrames win on conciseness and optimizability for STRUCTURED data;")
print("RDDs remain the right tool when the data or logic doesn't fit a")
print("schema-shaped, column-oriented mold - see the next section.")


"""
---------------------------------------------------------------------
8. WHEN RDDs STILL WIN: FULL CONTROL OVER UNSTRUCTURED DATA  ⭐⭐
---------------------------------------------------------------------
DataFrames need a SCHEMA. Raw, messy, unstructured input - arbitrary
log lines, malformed records mixed with good ones, custom binary
parsing - often doesn't have one until AFTER you've parsed it, which
is exactly the kind of arbitrary Python logic RDDs are built for.
`.mapPartitions()` is a good example of RDD-level control a DataFrame
doesn't expose directly: it hands your function an entire PARTITION
as an iterator (not one row at a time), which is the idiomatic place
to do expensive PER-PARTITION setup - e.g. opening one DB connection
or compiling one regex ONCE per partition, instead of once per row.
---------------------------------------------------------------------
"""

print("\n--- When RDDs Still Win: Full Control Over Unstructured Data ---")

raw_log_lines = [
    "2026-08-25T10:00:01 INFO user=101 action=login",
    "2026-08-25T10:00:03 ERROR user=102 action=payment_failed",
    "not a valid log line at all",
    "2026-08-25T10:00:07 INFO user=103 action=logout",
]


def parse_log_line(line):
    parts = line.split()
    if len(parts) < 4 or "=" not in parts[2] or "=" not in parts[3]:
        return None                       # malformed line - skip it, don't crash the job
    return {
        "ts": parts[0],
        "level": parts[1],
        "user": parts[2].split("=")[1],
        "action": parts[3].split("=")[1],
    }


if SPARK_AVAILABLE:
    def parse_partition(lines_iterator):
        # one-time-per-partition setup would go HERE (e.g. `conn = db.connect()`)
        for line in lines_iterator:
            parsed = parse_log_line(line)
            if parsed is not None:
                yield parsed

    lines_rdd = spark.sparkContext.parallelize(raw_log_lines, numSlices=2)
    parsed_records = lines_rdd.mapPartitions(parse_partition).collect()   # TRANSFORMATION then ACTION
    print("parsed log records:", parsed_records)
else:
    print("Simulating .mapPartitions() with plain Python (manual chunking)...")

    def split_into_partitions(data, num_partitions):
        chunk_size = math.ceil(len(data) / num_partitions)
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    parsed_records = []
    for i, partition in enumerate(split_into_partitions(raw_log_lines, 2)):
        print(f"  processing partition {i} ({len(partition)} line(s))...")
        for line in partition:
            parsed = parse_log_line(line)   # one-time-per-partition setup would go before this loop
            if parsed is not None:
                parsed_records.append(parsed)
    print("parsed log records:", parsed_records)

print("\nThe malformed line was silently dropped rather than crashing the")
print("job - real ETL logic over unstructured data leans on exactly this")
print("kind of full, per-record (or per-partition) Python control.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Spark      -> distributed compute engine; partitions data across a
              cluster, runs operations on all partitions in parallel

RDD        -> low-level, distributed collection of Python objects
              .map() / .filter() / .reduce()  (named after Python's
              own functional builtins on purpose)
              "Resilient" -> lost partitions are recomputed from
              lineage, not replicated

DataFrame  -> high-level, schema-aware, table-like API on top of RDDs
              .select() / .withColumn() / .filter() / .groupBy()
              optimized by the CATALYST query planner before running

TRANSFORMATIONS (lazy - just build a plan, run nothing):
    .map()  .filter()  .select()  .withColumn()  .groupBy()  .agg()
    .reduceByKey()  .mapPartitions()

ACTIONS (trigger real execution, return/persist a real result):
    .collect()  .count()  .show()  .write()  .reduce()  .take()

Lazy evaluation matters because -> Spark sees the WHOLE chain before
running anything, so it can optimize the physical plan (combine
filters, push predicates down, pick join strategies) instead of
executing each line eagerly and naively like pandas does.

RDD vs DataFrame, when to use which:
    unstructured/custom parsing, per-partition control -> RDD
    structured, column-oriented, aggregate/SQL-shaped work -> DataFrame
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PYSPARK BASICS
=====================================================================

1. What is the difference between a transformation and an action in
   Spark, and why does that distinction matter for performance?

2. What is lazy evaluation, and why is it useful in a distributed
   processing engine like Spark?

3. What does the "R" in RDD (Resilient Distributed Dataset) actually
   refer to - what happens if a worker holding one partition dies?

4. Why are RDD methods named .map(), .filter(), and .reduce() - what
   is the connection to Python's own map()/filter()/functools.reduce()?

5. What is the key structural difference between an RDD and a
   DataFrame, and why does that difference let Spark's Catalyst
   optimizer help DataFrames but not RDDs?

6. In Section 4's `LazyCollection` example, why does calling .map()
   or .filter() print nothing about the DATA itself, while .collect()
   does?

7. Given `df.filter(cond1).filter(cond2)`, describe how Catalyst
   might rewrite that plan before running it, and why that's cheaper
   than running each `.filter()` as its own separate pass.

8. Name three PySpark transformations and three PySpark actions.

9. In the RDD-style ETL example (Section 6), which calls are lazy
   transformations and which single call actually triggers execution?

10. Why is `.reduceByKey()` classified as a transformation (lazy),
    even though it involves a shuffle across the cluster?

11. What does `.mapPartitions()` let you do that `.map()` doesn't,
    and why is that useful for something like opening a database
    connection during an ETL job?

12. Rewrite `orders.filter(status == "completed").groupBy(country)
    .agg(sum(amount))` as: (a) the DataFrame version, and (b) the
    equivalent RDD version using .filter()/.map()/.reduceByKey().

13. When would you deliberately choose the RDD API over the
    DataFrame API in a real pipeline, given that DataFrames are more
    concise and more optimizable?

14. What does `numSlices` control when you call
    `spark.sparkContext.parallelize(data, numSlices=4)`, and how does
    it relate to how much parallelism your job actually gets?

15. Why can calling `.collect()` on a very large distributed
    DataFrame be dangerous, and what would you use instead to inspect
    or process the data safely?
=====================================================================
"""
