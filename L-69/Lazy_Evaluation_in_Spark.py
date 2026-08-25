"""
=====================================================================
LAZY EVALUATION IN SPARK - Complete Notes with Executable Examples
=====================================================================

LAZY EVALUATION means: when you call a transformation, Spark does NOT
touch your data. It just records "here is one more step in the plan"
and instantly hands you back a description of a bigger computation -
a DAG (Directed Acyclic Graph) of steps. Nothing actually runs until
you call an ACTION (`.collect()`, `.count()`, `.show()`, `.write()`,
...), at which point Spark looks at the WHOLE recorded plan at once,
optimizes it, and only then executes it against real data.

This is the opposite of EAGER evaluation, which is pandas' model:
every line of pandas code runs immediately, right there, top to
bottom, with no chance for anything downstream to influence how an
earlier line executes.

The companion PySpark Basics notes already covered the vocabulary for
this - RDDs vs DataFrames, and the transformation-vs-action split
(`.filter()`/`.map()`/`.select()` are transformations; `.collect()`/
`.count()`/`.show()` are actions). This file goes deeper on the ONE
mechanism that makes that split meaningful in the first place: WHY
transformations don't run immediately, HOW Spark represents the
deferred plan internally (the DAG), and what real, measurable
optimizations that deferral buys you in a distributed system - which
is exactly what interviewers are probing for when they ask "what is
lazy evaluation and why does it matter for distributed processing?"

We'll build a hand-rolled `LazyDataset` class that mimics Spark's
"build a plan, then run it" model using nothing but the Python
standard library, prove every claim with a call counter or a timer
(not just an assertion), and then show the real PySpark API
(`.explain()` on a DataFrame) that this all maps onto.
=====================================================================
"""

import time
import itertools

print("--- Overview ---")
print("Lazy evaluation = build up a PLAN of computation first, run")
print("nothing yet, and only execute the plan when an ACTION forces")
print("a real result. Eager evaluation (pandas) runs each line the")
print("instant you write it, with no plan to optimize beforehand.")


"""
---------------------------------------------------------------------
1. LAZY vs EAGER: PROVING THE DIFFERENCE WITH A CALL COUNTER  ⭐⭐⭐
---------------------------------------------------------------------
Talking about "lazy vs eager" in the abstract is cheap - an
interviewer wants to see you prove it. A `CallCounter` wraps any
function and counts how many times it actually ran. We use it below
to catch pandas (eager) executing a transformation immediately, and a
plain generator expression (lazy) NOT executing at all until iterated.
---------------------------------------------------------------------
"""

print("\n--- Lazy vs Eager: Proving It With a Call Counter ---")

class CallCounter:
    """Wraps a function and counts real invocations - our proof instrument
    for the whole file. Every 'was this actually computed?' claim below
    is backed by reading `.calls` on one of these, not by assertion."""
    def __init__(self, fn):
        self.fn = fn
        self.calls = 0
    def __call__(self, x):
        self.calls += 1
        return self.fn(x)

import pandas as pd

eager_counter = CallCounter(lambda x: x * 2)
df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
print("pandas: calls BEFORE .apply() line runs:", eager_counter.calls)
df["y"] = df["x"].apply(eager_counter)   # EAGER: this line itself walks every row, right now
print("pandas: calls IMMEDIATELY AFTER .apply() line:", eager_counter.calls)
print("-> pandas is EAGER: writing the line and running it are the same event.")

lazy_counter = CallCounter(lambda x: x * 2)
lazy_expr = (lazy_counter(x) for x in [1, 2, 3, 4, 5])   # LAZY: just builds a generator, no work yet
print("\ngenerator: calls IMMEDIATELY AFTER creating it:", lazy_counter.calls)
print("(the generator object exists, but not one element has been produced)")
materialized = list(lazy_expr)                            # forcing it - this is the "action"
print("generator: calls AFTER materializing with list():", lazy_counter.calls)
print("materialized result:", materialized)
print("-> this generator IS lazy evaluation. Spark's transformations work")
print("   the same way, but build an inspectable, optimizable PLAN object")
print("   instead of a raw, one-shot generator. That's what we build next.")


"""
---------------------------------------------------------------------
2. A HAND-ROLLED LazyDataset: TRANSFORMATIONS JUST RECORD A PLAN  ⭐⭐⭐
---------------------------------------------------------------------
`LazyDataset` wraps a Python list the way an RDD/DataFrame wraps a
distributed collection. Calling `.map()` or `.filter()` NEVER touches
`self._source` - it only appends a step to `self._chain` (our stand-in
for Spark's lineage/DAG) and returns a brand-new LazyDataset. We time
these calls to PROVE they're instant regardless of how much "expensive"
work is queued up inside them.
---------------------------------------------------------------------
"""

print("\n--- Building a LazyDataset: Transformations Just Record a Plan ---")

class LazyDataset:
    """Teaching stand-in for a Spark RDD/DataFrame. `.map()`/`.filter()`
    are TRANSFORMATIONS: they record a step and return a new LazyDataset
    immediately. `.collect()`/`.count()` are ACTIONS: they are the only
    calls that ever touch `self._source`."""

    def __init__(self, source, chain=None):
        self._source = source           # the raw data - untouched until an action runs
        self._chain = chain or []        # the "plan": list of (op_kind, fn, label) steps
        self._cached = None              # set only by .cache()/.persist() - see section 7

    def map(self, fn, label=None):
        new_chain = self._chain + [("map", fn, label or getattr(fn, "__name__", "map_fn"))]
        return type(self)(self._source, new_chain)     # NEW object, source untouched (preserves subclass)

    def filter(self, pred, label=None):
        new_chain = self._chain + [("filter", pred, label or getattr(pred, "__name__", "filter_fn"))]
        return type(self)(self._source, new_chain)

    def _compute(self):
        """The actual execution engine - only ever called by an action."""
        rows = list(self._source)
        for kind, fn, _label in self._chain:
            rows = [fn(r) for r in rows] if kind == "map" else [r for r in rows if fn(r)]
        return rows

    def collect(self):
        return list(self._cached) if self._cached is not None else self._compute()

    def count(self):
        return len(self.collect())

    def explain(self):
        """Prints the recorded plan - our DAG - see section 4."""
        steps = " -> ".join(f"{kind}({label})" for kind, _fn, label in self._chain) or "(no steps)"
        print(f"  Source({len(self._source)} rows) -> {steps}")


def slow_double(x):
    time.sleep(0.001)     # stands in for a genuinely expensive per-row transform
    return x * 2

raw = list(range(50))
start = time.perf_counter()
plan = LazyDataset(raw).filter(lambda x: x % 2 == 0).map(slow_double, label="slow_double")
elapsed_ms = (time.perf_counter() - start) * 1000
print(f".filter().map() over {len(raw)} rows, chaining a 1ms-per-row function, took {elapsed_ms:.4f} ms")
print("-> effectively instant: NO row was touched by that call.")
print("internal state right now:")
print("  plan._cached      =", plan._cached, "(nothing computed yet)")
print("  plan._chain       =", [label for _k, _f, label in plan._chain], "(the plan, not the data)")
print("  plan._source is raw:", plan._source is raw, "(still the original, un-iterated list)")


"""
---------------------------------------------------------------------
3. ACTIONS TRIGGER REAL EXECUTION  ⭐⭐⭐
---------------------------------------------------------------------
Only now, when we call `.collect()` (an ACTION), does the chain built
in section 2 actually walk the data. The measurable time jump between
"building the plan" and "running the plan" is the whole point.
---------------------------------------------------------------------
"""

print("\n--- Actions Trigger Real Execution ---")

start = time.perf_counter()
result = plan.collect()          # THIS is where slow_double() finally runs, 25 times
elapsed_ms = (time.perf_counter() - start) * 1000
print(f"plan.collect() took {elapsed_ms:.2f} ms and returned {len(result)} rows: {result[:5]}...")
print("-> compare to the ~0 ms it took to BUILD the same plan in section 2.")
print("   That gap IS lazy evaluation: cost is paid at the action, not the transformation.")


"""
---------------------------------------------------------------------
4. THE DAG: HOW THE DEFERRED PLAN IS REPRESENTED  ⭐⭐⭐
---------------------------------------------------------------------
Spark doesn't store your transformations as a vague intention - it
builds a literal DAG of stages, where each node is an operation and
each edge is "depends on the output of." `LazyDataset._chain` is a
simplified (linear) version of that same idea; real Spark's DAG can
branch and merge, e.g. when a DataFrame is reused by two different
downstream computations, or several inputs are joined.
---------------------------------------------------------------------
"""

print("\n--- The DAG Behind a Lazy Chain ---")

plan.explain()
print("\nReal Spark shows you this exact idea via rdd.toDebugString() or")
print("df.explain() (section 8) - both print the DAG of stages that will")
print("run, in order, once an action is called. Building the FULL graph")
print("BEFORE running anything is precisely what enables the two real")
print("optimizations demonstrated next - an eager engine, which runs each")
print("line as it's written, never gets to see the full picture in time")
print("to rewrite it.")


"""
---------------------------------------------------------------------
5. OPTIMIZATION #1: PREDICATE PUSHDOWN (FILTER REORDERING)  ⭐⭐⭐
---------------------------------------------------------------------
Because the whole plan is visible before execution, a lazy planner
(Spark's Catalyst optimizer, or our toy `optimize_plan` below) can
REWRITE it: if a cheap filter and an expensive map don't depend on
each other's output, run the filter FIRST so the expensive map only
ever touches rows that survive. Eager evaluation can't do this - by
the time it "sees" the filter, the expensive map on EVERY row has
already run.
---------------------------------------------------------------------
"""

print("\n--- Optimization #1: Predicate Pushdown / Filter Reordering ---")

# Rows carry a 'value' field that filtering reads and a separate 'enriched'
# field that mapping WRITES - so a filter never depends on the map's output,
# meaning it is always SAFE to run the filter before the map. This mirrors a
# real ETL step: e.g. "value" = a raw price column, and the expensive map is
# a slow enrichment call (currency conversion via an API, a regex parse, ...)
# that we'd like to run on as few rows as possible.
def make_rows(n):
    return [{"value": v, "enriched": None} for v in range(n)]

def expensive_enrich(counter, row):
    counter.calls += 1
    return {**row, "enriched": row["value"] * 1.07}      # e.g. a tax/FX adjustment

def cheap_predicate(row):
    return row["value"] > 900                             # only ~10% of rows survive

N = 1000
naive_counter = CallCounter(lambda r: r)     # only used to track call count here
naive_counter.calls = 0
rows = make_rows(N)
# NAIVE / EAGER-STYLE ORDER: map(expensive) THEN filter - every row gets enriched
mapped = [expensive_enrich(naive_counter, r) for r in rows]
naive_result = [r for r in mapped if cheap_predicate(r)]
print(f"naive order  (map -> filter): expensive_enrich called {naive_counter.calls} times "
      f"out of {N} rows, kept {len(naive_result)}")

optimized_counter = CallCounter(lambda r: r)
optimized_counter.calls = 0
# OPTIMIZED / LAZY-PLANNER ORDER: filter FIRST (cheap), THEN map only survivors
filtered = [r for r in rows if cheap_predicate(r)]
optimized_result = [expensive_enrich(optimized_counter, r) for r in filtered]
print(f"optimized order (filter -> map): expensive_enrich called {optimized_counter.calls} times "
      f"out of {N} rows, kept {len(optimized_result)}")
print(f"-> {naive_counter.calls - optimized_counter.calls} fewer expensive_enrich() calls "
      f"by reordering - same final rows: {naive_result == optimized_result}")


def optimize_plan(ops):
    """A tiny stand-in for Spark's Catalyst optimizer: given a list of ops
    tagged with the fields they READ and WRITE, push any filter that
    doesn't read a field the preceding map WRITES to run before that map.
    This is a real, general rewrite rule - predicate pushdown - not a
    special case hardcoded for this one example."""
    ops = list(ops)
    changed = True
    while changed:
        changed = False
        for i in range(len(ops) - 1):
            first, second = ops[i], ops[i + 1]
            if first["kind"] == "map" and second["kind"] == "filter" and not (second["reads"] & first["writes"]):
                ops[i], ops[i + 1] = second, first
                changed = True
    return ops


def apply_plan(rows, ops, counter):
    for op in ops:
        if op["kind"] == "map":
            rows = [expensive_enrich(counter, r) for r in rows]
        else:
            rows = [r for r in rows if op["fn"](r)]
    return rows


unoptimized_plan = [
    {"kind": "map", "fn": None, "reads": {"value"}, "writes": {"enriched"}},
    {"kind": "filter", "fn": cheap_predicate, "reads": {"value"}, "writes": set()},
]
planner_counter = CallCounter(lambda r: r)
planner_counter.calls = 0
plan_order_before = [op["kind"] for op in unoptimized_plan]
rewritten_plan = optimize_plan(unoptimized_plan)
plan_order_after = [op["kind"] for op in rewritten_plan]
planner_result = apply_plan(rows, rewritten_plan, planner_counter)
print(f"\ngeneric optimize_plan() rewrote {plan_order_before} -> {plan_order_after}")
print(f"executing the REWRITTEN plan called expensive_enrich {planner_counter.calls} times "
      f"(matches the hand-optimized order above: {planner_counter.calls == optimized_counter.calls})")


"""
---------------------------------------------------------------------
6. OPTIMIZATION #2: SKIPPING WORK ENTIRELY WHEN AN ACTION ALLOWS IT  ⭐⭐⭐
---------------------------------------------------------------------
`.take(3)` doesn't need the whole dataset - it needs 3 results. A lazy,
GENERATOR-based pipeline (the row-by-row execution model Spark's
engine actually uses, as opposed to our list-based LazyDataset above,
which materializes a full list per stage) can stop pulling from the
source the instant it has enough. `itertools.islice` forces exactly
that: only as many upstream elements are produced as are consumed.
---------------------------------------------------------------------
"""

print("\n--- Optimization #2: Skipping Unneeded Work (take(3)) ---")

TOTAL_ROWS = 10_000_000
take_counter = CallCounter(lambda x: x * 2)

def lazy_row_pipeline(source, mapper):
    for x in source:                 # pulls ONE element from `source` at a time
        y = mapper(x)                # only computed for elements actually pulled
        if y % 4 == 0:               # a predicate that a decent fraction of values satisfy
            yield y

pipeline = lazy_row_pipeline(range(TOTAL_ROWS), take_counter)   # nothing runs yet - just a generator
first_three = list(itertools.islice(pipeline, 3))                # the ACTION: "give me 3 results"
print(f"take(3) result: {first_three}")
print(f"mapper() was actually called {take_counter.calls} times, out of {TOTAL_ROWS:,} total rows")
print(f"-> {take_counter.calls} calls to get 3 results proves the pipeline stopped almost "
      f"immediately, rather than processing all {TOTAL_ROWS:,} rows.")
print("This is exactly why `df.take(3)` or `df.limit(3).collect()` on a huge Spark")
print("DataFrame can return in milliseconds: the DAG lets Spark push the row limit")
print("down and stop each partition's computation as soon as enough rows exist.")


"""
---------------------------------------------------------------------
7. .cache() / .persist(): DELIBERATELY BREAKING LAZINESS  ⭐⭐⭐
---------------------------------------------------------------------
Laziness has a sharp edge: a lazy chain is NOT a stored result - it's
a recipe. Calling two actions on the SAME unmaterialized chain reruns
the ENTIRE recipe from scratch each time. If you know you'll reuse an
intermediate result (a common ETL pattern - compute a cleaned/joined
DataFrame once, then run several different aggregations against it),
`.cache()`/`.persist()` forces materialization ONCE, and every action
after that reads the stored result instead of recomputing.
---------------------------------------------------------------------
"""

print("\n--- cache()/persist(): Breaking Laziness on Purpose ---")

class CachingLazyDataset(LazyDataset):
    """Adds real .cache()/.persist(): materializes once, on demand, and
    every action after that reuses the stored result instead of re-walking
    the chain."""
    def cache(self):
        if self._cached is None:
            self._cached = self._compute()      # pay the cost exactly once, right here
        return self
    persist = cache   # Spark uses these two names interchangeably for this idea

uncached_counter = CallCounter(lambda x: x * 2)
uncached = CachingLazyDataset(list(range(20))).filter(lambda x: x % 2 == 0).map(uncached_counter)
uncached.collect()
uncached.collect()
print(f"WITHOUT cache(): two .collect() calls -> mapper ran {uncached_counter.calls} times "
      f"(recomputed the full chain each time)")

cached_counter = CallCounter(lambda x: x * 2)
cached = CachingLazyDataset(list(range(20))).filter(lambda x: x % 2 == 0).map(cached_counter)
cached.cache()          # materialize ONCE, explicitly
cached.collect()
cached.collect()
print(f"WITH cache(): two .collect() calls after caching -> mapper ran {cached_counter.calls} times "
      f"(computed once, both collects just read the stored result)")
print(f"-> caching cut the mapper's work from {uncached_counter.calls} calls to {cached_counter.calls} "
      f"for the same two actions.")
print("The trade-off: cached results consume memory (Spark: executor memory/disk),")
print("so you only pay for it when a result is genuinely reused.")


"""
---------------------------------------------------------------------
8. THE REAL THING: PySpark LAZY TRANSFORMATIONS AND .explain()  ⭐⭐⭐
---------------------------------------------------------------------
Everything above is a teaching model of one real API: a PySpark
DataFrame builds up an unexecuted logical plan as you chain
`.filter()`/`.select()`/`.withColumn()`, and `.explain()` prints the
plan Spark's Catalyst optimizer produced - often already showing
pushed-down filters, exactly like section 5's `optimize_plan()`.
pyspark is not installed in this sandbox, so this runs for real when
available and otherwise prints a clearly-labeled simulated plan so the
real syntax and real output shape are both visible either way.
---------------------------------------------------------------------
"""

print("\n--- The Real Thing: PySpark Lazy Transformations and .explain() ---")

try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col

    spark = SparkSession.builder.appName("lazy_eval_demo").master("local[*]").getOrCreate()
    df = spark.createDataFrame([(i, i * 1.07) for i in range(1000)], ["value", "enriched"])

    # Both of these lines are TRANSFORMATIONS: nothing runs yet, exactly like
    # LazyDataset.map()/.filter() above - Spark is just extending its DAG.
    plan_df = df.filter(col("value") > 900).select("value", "enriched")

    print("Logical + physical plan BEFORE any action (Catalyst's optimized DAG):")
    plan_df.explain(True)     # an ACTION-adjacent call: doesn't return data, but forces planning

    result_count = plan_df.count()    # the actual ACTION - this is where execution happens
    print("plan_df.count() (the action that finally executes the plan):", result_count)
    spark.stop()

except ImportError:
    print("pyspark not installed in this sandbox - showing the real API and a labeled")
    print("SIMULATED result of what running this code on a real cluster would print:\n")
    print("  from pyspark.sql import SparkSession")
    print("  from pyspark.sql.functions import col")
    print("  spark = SparkSession.builder.appName('lazy_eval_demo').getOrCreate()")
    print("  df = spark.createDataFrame([(i, i * 1.07) for i in range(1000)], ['value', 'enriched'])")
    print("  plan_df = df.filter(col('value') > 900).select('value', 'enriched')")
    print("  plan_df.explain(True)   # <-- nothing has executed yet; this only prints the DAG")
    print("  plan_df.count()          # <-- THIS is the action that triggers real execution\n")
    print("  [SIMULATED .explain(True) OUTPUT]")
    print("  == Physical Plan ==")
    print("  *(1) Project [value#0, enriched#1]")
    print("  +- *(1) Filter (isnotnull(value#0) AND (value#0 > 900))")
    print("     +- *(1) Scan ExistingRDD[value#0,enriched#1]")
    print("  -- Note the Filter runs BEFORE the Project reaches the data source: this IS")
    print("     predicate pushdown, chosen automatically because Catalyst saw the WHOLE")
    print("     plan (filter + select) before executing any of it.")
    print("  [SIMULATED plan_df.count()] -> 99")


"""
---------------------------------------------------------------------
9. WHY THIS MATTERS FOR DISTRIBUTED PROCESSING  ⭐⭐⭐
---------------------------------------------------------------------
Everything above generalizes from "runs on one machine" to "runs
across a cluster" in a way eager evaluation cannot:
  - Less data crosses the network. Pushing filters down before a
    shuffle-heavy join or a wide transformation means fewer rows are
    ever serialized between executors - shuffles are the single
    biggest cost in most Spark jobs.
  - Fault tolerance is CHEAP. Because a lazy chain is a deterministic
    recipe (lineage) rather than a materialized result, a lost
    partition on a dead executor is recovered by just re-running its
    slice of the DAG from the source - no replication or write-ahead
    logging required for that data.
  - Whole-plan compilation. Catalyst/Tungsten can fuse many logical
    steps into one compiled, vectorized pass ("whole-stage codegen")
    ONLY because it can see every step up front - an eager engine
    that executes line-by-line never gets that chance.
---------------------------------------------------------------------
"""

print("\n--- Why This Matters for Distributed Processing ---")

# A concrete echo of "fault tolerance via lineage": because our LazyDataset's
# chain is a pure, deterministic recipe over `_source`, recomputing it from
# scratch always reproduces the same result - the same guarantee that lets
# Spark recover a lost partition by re-running its lineage instead of
# needing a replicated copy of every intermediate result.
recovery_counter = CallCounter(lambda x: x * 2)
lineage_ds = CachingLazyDataset(list(range(10))).filter(lambda x: x % 2 == 0).map(recovery_counter)
first_run = lineage_ds.collect()
# simulate "losing" the materialized result and recomputing purely from lineage
lineage_ds._cached = None
recomputed = lineage_ds.collect()
print("first run:      ", first_run)
print("'lost and recomputed from lineage':", recomputed)
print("identical:", first_run == recomputed, "-> deterministic lineage is what makes this safe")
print("\nSummary: laziness isn't merely an efficiency trick - it's the precondition")
print("that lets a distributed engine both OPTIMIZE the whole job and RECOVER from")
print("partial failure without re-running work that doesn't need it.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Lazy evaluation    -> record a PLAN (DAG); do NOT touch data yet
Eager evaluation   -> pandas model; each line executes immediately

Transformation (Spark) -> returns a new plan, instant, no data read
Action (Spark)          -> forces execution of the WHOLE plan so far

LazyDataset._chain      -> our DAG stand-in: list of pending steps
LazyDataset._compute()  -> only method that ever reads real data
LazyDataset._cached     -> None until an action OR .cache() runs

Why laziness enables optimization:
  predicate pushdown  -> filter (cheap) reordered before map (expensive):
                         fewer expensive calls, proven with CallCounter
  work skipping        -> .take(n)/.limit(n) stop pulling from a lazy
                         generator once n results exist - proven: calls
                         << total rows
  whole-plan compile   -> Catalyst/Tungsten fuse steps because the FULL
                         plan is visible before anything runs

cache()/persist()  -> force materialization ONCE on purpose so reused
                      results aren't recomputed from the chain each time
                      (uncached: N recomputations: cached: 1 computation)

Real API   -> spark_df.explain(True)   shows the actual physical plan
           -> spark_df.filter(...).select(...)   builds the plan lazily
           -> spark_df.count()/.collect()/.show()   are the actions

Distributed payoff -> less network shuffle, cheap lineage-based fault
                       tolerance, whole-stage codegen - none available
                       to a purely eager engine.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - LAZY EVALUATION IN SPARK
=====================================================================

1. What is lazy evaluation, and why is it useful in distributed
   processing? (Answer in terms of both optimization AND fault
   tolerance, not just "it's faster.")

2. Precisely define lazy evaluation vs eager evaluation. Why is
   pandas considered eager while Spark DataFrames are lazy?

3. In this file, `LazyDataset.map()`/`.filter()` never touch
   `self._source`. What DO they do, and what finally triggers real
   execution?

4. What is a DAG in the context of Spark, and what does each node
   and edge represent? Why can Spark's DAG branch/merge in ways our
   linear `LazyDataset._chain` cannot?

5. Explain predicate pushdown using the `expensive_enrich` /
   `cheap_predicate` example: why did reordering filter-before-map
   reduce the number of `expensive_enrich()` calls, and why is this
   optimization only possible because evaluation is lazy?

6. Walk through `optimize_plan()`'s rewrite rule. Why does it check
   `second["reads"] & first["writes"]` before swapping a map and a
   filter? What would go wrong if it swapped them unconditionally?

7. Why did `take(3)` over a 10,000,000-row generator pipeline in
   section 6 only call the mapper a handful of times instead of
   10,000,000 times? Would this same short-circuiting happen with
   the list-based `LazyDataset` from section 2? Why or why not?

8. What problem do `.cache()`/`.persist()` solve? In the section 7
   demo, why did the uncached `LazyDataset` call its mapper more
   times than the cached one for the same two `.collect()` calls?

9. What's the practical cost of calling `.cache()` on a Spark
   DataFrame you only plan to use once? When is caching actively
   harmful rather than helpful?

10. How does lazy evaluation (via lineage/DAG) give Spark fault
    tolerance without needing to replicate every intermediate
    result, the way the "recompute from lineage" demo in section 9
    illustrates?

11. What does `df.explain(True)` show you in real PySpark, and how
    does it relate to the Physical Plan simulated in section 8?

12. Why does building the FULL plan before executing anything let
    Catalyst do "whole-stage codegen," and why is that impossible
    for an eager, line-by-line execution model?

13. Give a concrete example (outside this file) of a Spark job where
    NOT having predicate pushdown would meaningfully increase network
    shuffle or cluster cost.

14. If two different downstream jobs both call `.filter()` on the
    SAME unmaterialized DataFrame, does Spark share the filtered
    result between them automatically? What would you do to make it
    share the work?

15. What is the difference between a transformation and an action in
    Spark (briefly - see the PySpark Basics notes for the full
    treatment), and specifically how does that split depend on lazy
    evaluation existing at all?
=====================================================================
"""
