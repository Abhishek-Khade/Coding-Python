"""
=====================================================================
DASK - PARALLEL, PANDAS-LIKE PROCESSING IN PYTHON - Complete Notes
with Executable Examples
=====================================================================

DASK is a Python-NATIVE library for parallel and distributed
computing. Its core pitch is simple but important: it takes APIs you
ALREADY know - pandas, NumPy, plain Python functions - and scales
them from a single CPU core, to all the cores on your laptop, to a
full multi-machine cluster, WITHOUT you having to learn a new API or
leave the Python/pandas ecosystem.

This is the single most important fact to know for interviews, and
it is exactly what separates Dask from Apache Spark:

    - Spark's core engine is written in Scala and runs on the JVM.
      PySpark is a WRAPPER around that JVM engine - your Python code
      gets translated into JVM operations under the hood, and you're
      using a DIFFERENT API (`pyspark.sql.DataFrame`, `groupBy`,
      camelCase methods) than the pandas you already know.

    - Dask is pure Python, all the way down. `dask.dataframe` is
      LITERALLY a collection of ordinary pandas DataFrames (one per
      "partition"), coordinated by a Python task scheduler. There is
      no JVM, no serialization boundary between "your code" and "the
      engine", and the method names are the SAME ones pandas uses
      (`.groupby()`, `.merge()`, `.mean()`, boolean filtering, etc.).

Dask has three main pieces, all covered below:
    1. dask.dataframe / dask.array - parallel, pandas-/NumPy-like
       collections, built from many smaller partitions.
    2. dask.delayed - wraps ARBITRARY Python functions (not just
       DataFrame code) into a lazy, parallelizable task graph.
    3. dask.distributed - a real scheduler (LocalCluster on your
       laptop, or a genuine multi-machine cluster) that runs the same
       task graphs, with a live diagnostics dashboard.

All of Dask is built on LAZY EVALUATION: operations build up a task
graph describing the work, and nothing actually runs until you call
`.compute()`. This mirrors the lazy-evaluation model used by Spark's
transformations-vs-actions split - the same underlying idea, applied
inside a pure-Python engine instead of a JVM one.
=====================================================================
"""

import glob
import os
import shutil
import tempfile
import time
import warnings

import numpy as np
import pandas as pd

import dask
import dask.dataframe as dd
from dask import delayed

warnings.filterwarnings("ignore")  # silence noisy-but-harmless dask/pandas FutureWarnings for clean teaching output

print("--- Overview ---")
print("Dask scales the pandas/NumPy APIs you already know from one core")
print("to a full cluster - it is pure Python, with NO JVM involved,")
print("unlike Spark (JVM engine) wrapped for Python via PySpark.")


"""
---------------------------------------------------------------------
1. WHAT A DASK DATAFRAME ACTUALLY IS: MANY PANDAS DATAFRAMES  ⭐⭐⭐
---------------------------------------------------------------------
A `dask.dataframe.DataFrame` is NOT a new data structure written from
scratch - it is a thin coordinating wrapper around a collection of
ordinary pandas DataFrames, called PARTITIONS. Operations you call on
the Dask DataFrame get applied to each pandas partition (potentially
on a different CPU core, or a different machine), and the results are
combined. Proving this to yourself is the fastest way to understand
why the API feels identical to pandas: it's because, underneath, it
literally IS pandas.
---------------------------------------------------------------------
"""

print("\n--- What a Dask DataFrame Actually Is ---")

small_df = pd.DataFrame({"n": range(12)})
small_ddf = dd.from_pandas(small_df, npartitions=3)  # split into 3 partitions

print("type of the whole Dask DataFrame:", type(small_ddf))
print("number of partitions:", small_ddf.npartitions)

one_partition = small_ddf.partitions[0].compute()  # pull ONE partition and materialize it
print("type of a single partition once materialized:", type(one_partition))
print("partition 0's actual pandas data:\n", one_partition)
print("\nEach partition is a genuine, ordinary pandas.DataFrame - Dask")
print("just decides which partition(s) each task graph node touches.")


"""
---------------------------------------------------------------------
2. dask.dataframe: THE SAME PANDAS API, RUN IN PARALLEL  ⭐⭐⭐
---------------------------------------------------------------------
The whole point: you write the SAME filtering / groupby / aggregation
code you'd write for pandas. `dd.from_pandas(df, npartitions=N)`
converts an existing in-memory pandas DataFrame into a partitioned
Dask DataFrame. Below, the identical logical operation is run once
in plain pandas and once in Dask, to show the API is a 1:1 match.
---------------------------------------------------------------------
"""

print("\n--- dask.dataframe: Same API as pandas ---")

np.random.seed(42)
n_rows = 500
orders_df = pd.DataFrame({
    "order_id": range(1, n_rows + 1),
    "region": np.random.choice(["west", "east", "north", "south"], n_rows),
    "category": np.random.choice(["electronics", "home", "apparel", "toys"], n_rows),
    "amount": np.round(np.random.uniform(5, 500, n_rows), 2),
})

# --- plain pandas: the version you already know how to write ---
pandas_result = (
    orders_df[orders_df["amount"] > 50]
    .groupby("region")["amount"]
    .agg(["sum", "mean", "count"])
    .sort_index()
)
print("pandas .groupby().agg() result:\n", pandas_result)

# --- the SAME operation on a Dask DataFrame - notice the method names ---
orders_ddf = dd.from_pandas(orders_df, npartitions=4)  # 4 partitions -> up to 4 pandas DataFrames processed in parallel
dask_result = (
    orders_ddf[orders_ddf["amount"] > 50]   # boolean filtering: identical syntax to pandas
    .groupby("region")["amount"]             # groupby: identical syntax to pandas
    .agg(["sum", "mean", "count"])           # agg: identical syntax to pandas
    .compute()                                # <- the ONLY new concept: run the built-up graph now
    .sort_index()
)
print("\ndask .groupby().agg() result (after .compute()):\n", dask_result)
print("\nidentical results:", pandas_result.round(4).equals(dask_result.round(4)))
print("Notice the code above is line-for-line the same as pandas, plus")
print("one `.compute()` at the very end - that's the entire API delta.")


"""
---------------------------------------------------------------------
3. READING MANY FILES AS ONE LOGICAL DASK DATAFRAME  ⭐⭐
---------------------------------------------------------------------
Real pipelines rarely start from one in-memory pandas DataFrame - they
start from files. `dd.read_csv()` accepts a GLOB PATTERN and reads
every matching file as partitions of ONE logical DataFrame, exactly
as if `pd.concat([pd.read_csv(f) for f in files])` had been called,
except each file is only loaded lazily, on demand, and can be
processed on a separate core.
---------------------------------------------------------------------
"""

print("\n--- Reading Many Files as One Logical DataFrame ---")

scratch_dir = tempfile.mkdtemp(prefix="dask_orders_")
try:
    # simulate a typical ETL "landing zone": one CSV file per day
    for day in range(4):
        daily_chunk = orders_df.iloc[day * 125:(day + 1) * 125]
        daily_chunk.to_csv(os.path.join(scratch_dir, f"orders_day{day}.csv"), index=False)

    file_pattern = os.path.join(scratch_dir, "orders_day*.csv")
    print("files on disk:", sorted(os.path.basename(f) for f in glob.glob(file_pattern)))

    files_ddf = dd.read_csv(file_pattern)  # ONE glob pattern -> ONE Dask DataFrame across all 4 files
    print("\npartitions created from the glob (1 per file):", files_ddf.npartitions)
    print("total rows across all files:", len(files_ddf))  # len() triggers a real compute internally
    print("\nregion totals across ALL 4 files, computed in one call:")
    print(files_ddf.groupby("region")["amount"].sum().compute().sort_index())
finally:
    shutil.rmtree(scratch_dir, ignore_errors=True)  # clean up the scratch CSVs


"""
---------------------------------------------------------------------
4. LAZY EVALUATION: NOTHING RUNS UNTIL .compute()  ⭐⭐⭐
---------------------------------------------------------------------
Just like Spark builds a logical plan of TRANSFORMATIONS and only
runs it when an ACTION is called, Dask builds a TASK GRAPH as you
chain operations, and does no real work until `.compute()` (or
`.persist()`) is called. Chaining `.groupby()`, filtering, and column
selection on a Dask DataFrame is essentially free - it just records
instructions. `.visualize()` renders that task graph to an actual
image file (a PNG showing every task node and its dependencies) - not
run here since it needs Graphviz, but the graph it WOULD draw is the
exact same structure inspected below via `.dask`.
---------------------------------------------------------------------
"""

print("\n--- Lazy Evaluation and the Task Graph ---")

lazy_pipeline = (
    orders_ddf[orders_ddf["category"] == "electronics"]
    .groupby("region")["amount"]
    .mean()
)
print("result of chaining filter -> groupby -> mean, BEFORE .compute():")
print(" type:", type(lazy_pipeline))
print(" (no actual numbers exist yet - this is a lazy, unevaluated plan)")
print(" number of tasks in the underlying graph:", len(lazy_pipeline.dask))

# lazy_pipeline.visualize(filename="task_graph.png")   # in a real environment with graphviz
# installed, this line would write an actual PNG image of the task graph above to disk.

t0 = time.perf_counter()
materialized = lazy_pipeline.compute()   # THIS is the moment real computation happens
compute_time = time.perf_counter() - t0
print(f"\n.compute() actually ran the graph in {compute_time:.4f}s, producing real values:")
print(materialized.sort_index())


"""
---------------------------------------------------------------------
5. dask.delayed: PARALLELIZING ARBITRARY PYTHON FUNCTIONS  ⭐⭐⭐
---------------------------------------------------------------------
`dask.dataframe` only helps with tabular, pandas-shaped work. Most
real pipelines also have custom Python logic - a slow API call, a
CPU-bound transformation, a validation step - that doesn't fit a
DataFrame API at all. `@dask.delayed` wraps ANY plain Python function
so that calling it doesn't run it immediately - it returns a Delayed
OBJECT representing "this call, to be run later", and Dask
automatically figures out which delayed calls are independent (and
can run in parallel) versus dependent on each other's results (and
must run in order), purely from how you pass their outputs around.
---------------------------------------------------------------------
"""

print("\n--- dask.delayed: Parallelizing Custom Python Functions ---")

def clean_record(raw_value):
    """Simulates a moderately slow per-record cleaning/validation step."""
    time.sleep(0.4)
    return round(raw_value * 1.08, 2)   # e.g. applying a tax rate

def summarize_batch(*cleaned_values):
    """Simulates a fast final aggregation step over already-cleaned values."""
    time.sleep(0.1)
    return round(sum(cleaned_values), 2)

raw_batch = [120.0, 45.5, 300.0, 78.25]

# --- sequential baseline: one function call strictly after another ---
t0 = time.perf_counter()
sequential_cleaned = [clean_record(v) for v in raw_batch]
sequential_total = summarize_batch(*sequential_cleaned)
sequential_time = time.perf_counter() - t0
print(f"sequential total: {sequential_total}  (took {sequential_time:.2f}s)")

# --- the SAME functions, wrapped with @delayed, run through Dask's scheduler ---
delayed_clean_record = delayed(clean_record)
delayed_summarize_batch = delayed(summarize_batch)

t0 = time.perf_counter()
delayed_cleaned = [delayed_clean_record(v) for v in raw_batch]   # 4 INDEPENDENT delayed calls - can run concurrently
delayed_total = delayed_summarize_batch(*delayed_cleaned)         # DEPENDS on all 4 - waits for them, then runs
parallel_total = delayed_total.compute()                          # this single .compute() runs the whole graph
parallel_time = time.perf_counter() - t0
print(f"parallel (delayed) total: {parallel_total}  (took {parallel_time:.2f}s)")

print(f"\nmeasured speedup: {sequential_time / parallel_time:.2f}x on this machine's CPU cores")
print("Same numeric result either way - the delayed version got there")
print("faster because the 4 independent clean_record() calls ran")
print("concurrently instead of one strictly after another.")


"""
---------------------------------------------------------------------
6. dask.distributed: LocalCluster AND Client - SAME CODE, BIGGER
   SCHEDULER  ⭐⭐
---------------------------------------------------------------------
By default, `.compute()` uses a lightweight scheduler running inside
your current process. `dask.distributed` swaps in a REAL scheduler
with its own worker processes and a live diagnostics dashboard
(task progress, memory use, worker load) - useful even on a single
laptop, and it is the EXACT SAME `Client`/`LocalCluster` API you'd use
to connect to a genuine multi-machine cluster in production. This is
Dask's answer to "how do I go from my laptop to a cluster": you don't
rewrite the pipeline - you just point the same code at a bigger
Client.
---------------------------------------------------------------------
"""

print("\n--- dask.distributed: LocalCluster and Client ---")

try:
    from dask.distributed import Client, LocalCluster

    # processes=False runs workers as threads in THIS process instead of separate OS
    # processes - it sidesteps some multiprocessing/"spawn" quirks when running as a
    # plain top-level script, while still exercising the real Client/Cluster API. In
    # production you'd typically leave the default (processes=True) for true
    # multi-core isolation, or connect to an already-running remote cluster instead.
    cluster = LocalCluster(n_workers=2, threads_per_worker=1, processes=False, dashboard_address=":0")
    client = Client(cluster)
    try:
        print("client connected:", client)
        print("diagnostics dashboard would be reachable at:", client.dashboard_link)

        # the SAME orders_ddf code from section 2, now actually scheduled across
        # real worker processes instead of the lightweight local scheduler
        cluster_result = orders_ddf.groupby("category")["amount"].sum().compute()
        print("\ngroupby computed on the LocalCluster's workers:")
        print(cluster_result.sort_index())
    finally:
        client.close()      # always release the client...
        cluster.close()     # ...and shut down the worker processes when done
        print("\nClient and LocalCluster closed cleanly.")
except ImportError:
    # dask.distributed ships as a separate package (`pip install "dask[distributed]"`);
    # some minimal installs only have dask.dataframe/delayed. The code above is the
    # real, correct API either way - this is just a fallback so the file still runs.
    print("dask.distributed is not installed here - in a real environment the code")
    print("above would print a live dashboard URL like http://127.0.0.1:8787/status")
    print("and run the same groupby computation across real worker processes.")


"""
---------------------------------------------------------------------
7. DATA ENGINEERING USE CASE: PARALLEL ETL ACROSS PARTITIONED FILES
   ⭐⭐⭐
---------------------------------------------------------------------
Putting sections 3-5 together: a realistic small ETL job reads
several partitioned source files, applies a per-row transformation
that isn't a built-in pandas method (via `map_partitions`, which runs
an arbitrary function on each partition - the DataFrame analogue of
`dask.delayed`), filters, aggregates, and writes results back out -
all without ever loading the full dataset into memory at once.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Use Case: Parallel ETL ---")

etl_scratch_dir = tempfile.mkdtemp(prefix="dask_etl_")
try:
    for day in range(4):
        daily_chunk = orders_df.iloc[day * 125:(day + 1) * 125]
        daily_chunk.to_csv(os.path.join(etl_scratch_dir, f"orders_day{day}.csv"), index=False)

    def apply_regional_discount(partition_df):
        """Runs on EACH partition (i.e. each source file) independently."""
        result = partition_df.copy()
        result["amount_after_discount"] = np.where(
            result["region"].isin(["west", "north"]), result["amount"] * 0.9, result["amount"]
        )
        return result

    raw_ddf = dd.read_csv(os.path.join(etl_scratch_dir, "orders_day*.csv"))
    transformed_ddf = raw_ddf.map_partitions(apply_regional_discount)  # custom per-partition logic, still lazy

    etl_summary = (
        transformed_ddf[transformed_ddf["amount_after_discount"] > 100]
        .groupby(["region", "category"])["amount_after_discount"]
        .sum()
        .compute()
    )
    print("post-discount revenue by region/category (orders over $100):")
    print(etl_summary.sort_index().head(8))

    output_dir = os.path.join(etl_scratch_dir, "output")
    transformed_ddf.to_csv(os.path.join(output_dir, "cleaned_orders-*.csv"), index=False)
    written_files = sorted(os.listdir(output_dir))
    print(f"\nwrote {len(written_files)} output partition file(s), e.g.: {written_files[0]}")
finally:
    shutil.rmtree(etl_scratch_dir, ignore_errors=True)


"""
---------------------------------------------------------------------
8. GOTCHA: DASK DOESN'T KNOW GLOBAL ROW POSITIONS  ⭐⭐
---------------------------------------------------------------------
A common trap for pandas users: positional row indexing (`.iloc[n]`
for a single ROW) relies on knowing exactly how many rows come before
it. In pandas that's trivial - it's all one object in memory. In
Dask, the data is split across independent partitions that may not
even know each other's lengths without doing real work, so
`ddf.iloc[n]` for row selection is NOT supported and raises a real,
documented error, unlike column selection (`ddf.iloc[:, 0]`), which
works fine since columns are identical across every partition.
---------------------------------------------------------------------
"""

print("\n--- Gotcha: No Cheap Positional Row Indexing ---")

try:
    row = orders_ddf.iloc[3]   # BUGGY (from a pandas habit): looks reasonable, isn't supported
    print(row)
except NotImplementedError as e:
    print("error from ddf.iloc[3] (row selection):", e)

# FIXED: column-position selection works fine (columns are the same in every partition)...
print("\nddf.iloc[:, 0] (column selection) works fine:")
print(orders_ddf.iloc[:, 0].head(3))

# ...and if you genuinely need row N, either filter by a real condition/index, or
# accept the cost and materialize first (only reasonable once data is small enough):
fixed_row = orders_ddf.compute().iloc[3]
print("\nfixed by computing first, then using pandas .iloc on the materialized result:")
print(fixed_row)


"""
---------------------------------------------------------------------
9. DASK vs SPARK: WHEN TO CHOOSE WHICH  ⭐⭐⭐
---------------------------------------------------------------------
This is a near-guaranteed interview question once Dask comes up: "why
not just use Spark?" / "when would you pick Dask over Spark?" There
is no universally correct answer - it depends on team, scale, and
workload shape. Both printed guides below are genuinely fair; neither
tool is strictly better.
---------------------------------------------------------------------
"""

print("\n--- Dask vs Spark: A Balanced Decision Guide ---")

print("""
CHOOSE DASK WHEN:
  - Your team is Python-native and your codebase is already pandas/
    NumPy/scikit-learn-based - Dask is an incremental scale-up, not a
    rewrite (dask.dataframe mirrors the pandas API almost exactly).
  - You need to parallelize CUSTOM, non-tabular Python logic
    (dask.delayed) - simulations, per-record business rules, calls
    into arbitrary libraries - not just SQL-shaped groupby/join work.
  - You're doing scientific / array-heavy computing (dask.array
    scales NumPy the same way dask.dataframe scales pandas) or ML
    with dask-ml, where the workload is naturally NumPy-shaped.
  - You want a gentle on-ramp: prototype on a laptop with the default
    scheduler, then scale the SAME code to LocalCluster or a real
    cluster later, with no JVM, no separate cluster-only API to learn.
  - Your data comfortably fits on a single beefy machine or a modest
    handful of nodes (roughly: gigabytes to low double-digit
    terabytes), not many-terabyte, many-hundred-node scale.

CHOOSE SPARK WHEN:
  - You're operating at VERY large scale - multi-terabyte to
    petabyte datasets across many nodes - where Spark's mature,
    battle-tested, JVM-based execution engine and shuffle/query
    optimizer (Catalyst/Tungsten) have had over a decade of
    production hardening.
  - You need deep integration with the broader big-data ecosystem:
    Hive, Delta Lake/Iceberg, YARN/Kubernetes-native cluster
    managers, and enterprise data-platform tooling that assumes Spark.
  - Your organization is already running Spark clusters and has
    existing operational expertise (job scheduling, tuning, on-call
    runbooks) built around it - switching engines has a real cost.
  - Your team is comfortable being JVM-adjacent (tuning executor
    memory, garbage collection, shuffle partitions) in exchange for
    that battle-tested performance at extreme scale.

NEITHER IS "WRONG": plenty of production data platforms use BOTH -
Dask for Python-heavy feature engineering or custom parallel jobs,
Spark for the large-scale warehouse/lake ETL backbone.
""")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Dask core idea      -> same pandas/NumPy/Python APIs, scaled from one
                        core to a cluster, pure Python (no JVM)

dd.from_pandas(df, npartitions=N)   -> pandas DataFrame -> Dask DataFrame
dd.read_csv("dir/*.csv")            -> many files -> ONE logical Dask DataFrame
ddf.groupby(...).agg(...)           -> identical syntax to pandas
ddf.map_partitions(func)            -> run a custom function per partition
ddf.compute()                       -> actually run the task graph now
ddf.persist()                       -> compute now, keep result in distributed memory
ddf.visualize()                     -> render the task graph to an image (needs graphviz)
len(ddf.dask)                       -> number of tasks currently in the graph

dask.delayed(func)(args)   -> wraps ANY python function into a lazy,
                               parallelizable Delayed object
.compute() on a Delayed    -> runs the whole dependency graph;
                               independent calls run concurrently

dask.distributed.LocalCluster + Client
    -> real scheduler + worker processes, live dashboard,
       SAME API used to connect to an actual multi-node cluster

Gotcha: ddf.iloc[n] (row)  -> NOT supported (NotImplementedError);
        ddf.iloc[:, n] (col) -> supported fine

Dask vs Spark, one line each:
    Dask  -> Python-native, no JVM, easy pandas on-ramp, custom
             Python logic via delayed, best up to "big but not
             planet-scale" data
    Spark -> JVM engine, PySpark is a wrapper around it, best for
             multi-terabyte/many-node production data engineering
             with a mature ecosystem (Hive, Delta Lake, etc.)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - DASK
=====================================================================

1. What IS a Dask DataFrame, structurally - what is it made of under
   the hood, and how does that explain why its API looks so much like
   pandas?

2. What is the single biggest architectural difference between Dask
   and Spark, and why does it matter for a Python-native team?

3. When would you choose Dask over Spark, or vice versa? (This is
   Module 12's flagship question - be ready to give a real, balanced
   answer, not just "Dask is for small data.")

4. What does `dd.from_pandas(df, npartitions=N)` actually do, and
   what determines a good choice of `npartitions` for a given
   dataset?

5. How does `dd.read_csv()` handle a glob pattern like
   `"orders_day*.csv"` matching multiple files, and how is that
   different from calling `pd.read_csv()` on each file yourself?

6. Explain lazy evaluation in Dask: what happens when you chain
   `.groupby()` and filtering calls on a Dask DataFrame, and what
   specifically triggers real computation?

7. What does `.visualize()` produce, and why is inspecting the task
   graph useful when debugging a slow or unexpectedly large Dask
   pipeline?

8. What problem does `dask.delayed` solve that `dask.dataframe` does
   NOT solve? Give an example of work that fits `delayed` but doesn't
   fit a DataFrame API.

9. In the `clean_record`/`summarize_batch` example in this file, why
   are the four `clean_record` calls able to run concurrently, while
   `summarize_batch` has to wait for all of them first? How does Dask
   figure that out automatically?

10. What is the purpose of `dask.distributed`'s `LocalCluster` and
    `Client`, if `.compute()` already works without them? What does
    the dashboard give you that you don't get from the default
    scheduler?

11. If your Dask code already runs correctly against a `LocalCluster`
    on your laptop, what would change to run it against a real,
    multi-machine production cluster instead?

12. Why does `ddf.iloc[3]` (selecting a single ROW by position) raise
    `NotImplementedError` in Dask, while `ddf.iloc[:, 0]` (selecting a
    COLUMN by position) works fine? What does this reveal about how
    Dask DataFrames are partitioned?

13. What is `map_partitions()` used for, and how is it conceptually
    similar to `dask.delayed`?

14. Dask's documentation describes it as scaling "from a laptop to a
    cluster with the same code." What specifically stays the same,
    and what (if anything) has to change?

15. Both Dask and Spark use lazy evaluation with a
    transformations/actions-style split. Contrast what triggers
    execution in each (e.g. `.compute()` vs a Spark action like
    `.collect()` or `.show()`), and explain why lazy evaluation is
    valuable for a distributed engine's query optimizer in general.
=====================================================================
"""
