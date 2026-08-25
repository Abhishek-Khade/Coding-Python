"""
=====================================================================
APACHE AIRFLOW BASICS - DAGs, Operators, and Task Dependencies
=====================================================================

Airflow is an ORCHESTRATOR, not a processing engine - it doesn't move
or transform your data itself (Pandas/Spark/SQL do that); it decides
WHEN each step of a pipeline runs, in WHAT ORDER, WHAT happens on
failure/retry, and gives you visibility into all of it. The unit
Airflow schedules is a DAG: a Directed Acyclic Graph of TASKS.

  DIRECTED - every dependency has a direction: "B runs only after A"
             is not the same as "A runs only after B".
  ACYCLIC  - there is NO path that loops back to a task that depends
             on it, directly or transitively. This is not a stylistic
             preference - it is a HARD REQUIREMENT for scheduling to
             even be possible. If task C (transitively) depends on
             itself, there is no legal order to run the tasks in:
             whichever one you pick to run "first" is, by definition,
             still waiting on something that hasn't happened yet.
             A cycle means the graph is unschedulable, full stop.

Airflow picked the DAG model (over, say, a plain linear script) for
three concrete engineering reasons that come up constantly in
interviews:
  1. STATIC ANALYSIS - the scheduler can inspect the whole graph
     before running anything: validate it, detect independent
     branches, and decide what CAN run in parallel.
  2. PARTIAL RE-RUN / RESUMABILITY - if task 7 of 10 fails, Airflow
     re-runs task 7 onward, not tasks 1-6 again, because the graph
     records exactly what already succeeded and what depends on what.
  3. VISUALIZATION & OBSERVABILITY - a DAG is a data structure you can
     render, diff, and reason about; a 500-line linear script is not.

This sandbox does NOT have Airflow installed (it's a heavy, multi-
package system meant to run as its own service with a metadata DB,
scheduler process, and webserver). Every DAG-definition code block
below is written exactly as you'd write it against a real Airflow
2.x/3.x install - real imports, real decorators, real operator
classes. It is wrapped in `try: import airflow ... except
ImportError:` so the file still runs cleanly here; the `except`
branch prints a clear notice and then SIMULATES the DAG's execution
with plain Python, using a tiny hand-rolled DAG-runner, so you still
see real, live, order-respecting output.
=====================================================================
"""

from __future__ import annotations

import datetime as dt
from collections import deque
from collections.abc import Callable

print("--- Overview ---")
print("A DAG is a graph of tasks with directed, ACYCLIC dependencies.")
print("Airflow's whole job is: read that graph, and run each task at")
print("the right time, in the right order, retrying/alerting on failure.")


"""
---------------------------------------------------------------------
1. DAGs: DIRECTED ACYCLIC GRAPHS, AND WHY "ACYCLIC" IS NON-NEGOTIABLE  ⭐⭐⭐
---------------------------------------------------------------------
Before touching Airflow's API at all, it's worth building (and
breaking) the underlying graph algorithm by hand - this IS what
Airflow's scheduler does internally when it parses your DAG file:
compute a valid execution order (a "topological sort"), and reject
the graph outright if no such order exists.
---------------------------------------------------------------------
"""

print("\n--- DAGs: Directed Acyclic Graphs ---")


def topological_sort(dependencies: dict[str, list[str]]) -> list[str]:
    """
    Given {task_id: [upstream_task_ids]}, return ONE valid execution
    order (upstream tasks always appear before the tasks that depend
    on them). Raises ValueError if the graph contains a cycle - i.e.
    if it is NOT actually a DAG.
    """
    in_degree = {task_id: len(upstream) for task_id, upstream in dependencies.items()}
    children: dict[str, list[str]] = {task_id: [] for task_id in dependencies}
    for task_id, upstream in dependencies.items():
        for up in upstream:
            children[up].append(task_id)   # record the reverse edge

    # start with every task that has NO unmet dependencies
    ready = deque(sorted(t for t, deg in in_degree.items() if deg == 0))
    order: list[str] = []
    while ready:
        task_id = ready.popleft()
        order.append(task_id)
        for child in children[task_id]:
            in_degree[child] -= 1          # one fewer thing child is waiting on
            if in_degree[child] == 0:
                ready.append(child)

    if len(order) != len(dependencies):
        # anything left with in_degree > 0 is stuck waiting on something
        # that will NEVER become ready - that's the signature of a cycle
        stuck = sorted(set(dependencies) - set(order))
        raise ValueError(
            f"cycle detected - these tasks can never become runnable: {stuck}. "
            "A DAG cannot contain a cycle: if a task (transitively) depends on "
            "itself, there is no valid order to schedule it in."
        )
    return order


# a real, valid (acyclic) small ETL graph
etl_edges = {
    "extract": [],
    "transform": ["extract"],
    "check_volume": ["transform"],
    "load": ["check_volume"],
}
print("valid ETL graph, computed run order:", topological_sort(etl_edges))

# BUGGY: someone mis-wired this so "load" depends (transitively) on itself -
# extract needs load to finish, load needs transform, transform needs extract
cyclic_edges = {
    "extract": ["load"],
    "transform": ["extract"],
    "load": ["transform"],
}
try:
    topological_sort(cyclic_edges)
except ValueError as e:
    print("rejected as an invalid DAG:", e)

print("\nThis is exactly the check Airflow's DAG parser performs (as a")
print("'DAG Cycle Error') before your DAG ever shows up as schedulable -")
print("it protects you from defining a pipeline that could never run.")


"""
---------------------------------------------------------------------
2. WHY AIRFLOW IS BUILT AROUND THE DAG MODEL, NOT A LINEAR SCRIPT  ⭐⭐
---------------------------------------------------------------------
Because the graph is explicit data (not "whatever order the lines of
a script happen to execute in"), the scheduler can group tasks into
LEVELS - tasks with no dependency relationship between them, which
are therefore safe to run concurrently across multiple workers.
---------------------------------------------------------------------
"""

print("\n--- Why the DAG Model (Parallelism From Graph Structure) ---")


def parallel_levels(dependencies: dict[str, list[str]]) -> list[list[str]]:
    """Group tasks into levels where every task in a level is safe to run
    concurrently, because none of them depends on another one in the SAME level."""
    order = topological_sort(dependencies)      # validates the graph is acyclic first
    depth: dict[str, int] = {}
    for task_id in order:
        upstream = dependencies[task_id]
        depth[task_id] = 0 if not upstream else max(depth[u] for u in upstream) + 1
    levels: dict[int, list[str]] = {}
    for task_id, d in depth.items():
        levels.setdefault(d, []).append(task_id)
    return [sorted(levels[d]) for d in sorted(levels)]


fanout_edges = {
    "extract_orders": [],
    "extract_customers": [],           # independent of extract_orders - no edge between them
    "join_orders_customers": ["extract_orders", "extract_customers"],
    "load_warehouse": ["join_orders_customers"],
}
for i, level in enumerate(parallel_levels(fanout_edges)):
    print(f"  level {i}: {level}")

print("\nlevel 0 has TWO independent tasks - a linear script would run")
print("them one after another for no reason; Airflow's scheduler can see,")
print("from the graph alone, that they have no shared edge and dispatch")
print("both to workers at the same time. A linear script gives the")
print("scheduler no such structure to exploit.")


"""
---------------------------------------------------------------------
3. A REALISTIC ETL DAG WITH THE MODERN TASKFLOW API (@dag / @task)  ⭐⭐⭐
---------------------------------------------------------------------
Modern Airflow (2.0+) favors the TASKFLOW API: plain Python functions
decorated with `@task`, wired together by simply CALLING them like
regular functions - Airflow infers both the task graph AND the XCom
data-passing automatically from those calls, instead of you manually
wiring PythonOperator objects. `@task.branch` is the TaskFlow spelling
of the classic BranchPythonOperator: its return value is the task_id
(or list of task_ids) that should run next; every other downstream
branch is marked SKIPPED, not failed.

The plain functions below (`_extract_impl` etc.) hold the actual logic
so both the real Airflow-decorated version AND the plain-Python
simulation below call the exact same code.
---------------------------------------------------------------------
"""

print("\n--- A Realistic ETL DAG (TaskFlow API) ---")

LOAD_THRESHOLD = 3   # business rule: don't bother loading a near-empty batch


def _extract_impl() -> list[dict]:
    """Stand-in for hitting an orders API / staging table."""
    return [
        {"order_id": "A1", "total": 42.00, "status": "paid"},
        {"order_id": "A2", "total": -5.00, "status": "refunded"},   # bad row
        {"order_id": "A3", "total": 17.50, "status": "paid"},
    ]


def _transform_impl(records: list[dict]) -> list[dict]:
    """Drop rows that fail validation (negative totals are a data-quality bug)."""
    return [r for r in records if r["total"] >= 0]


def _check_volume_impl(records: list[dict]) -> str:
    """This IS a BranchPythonOperator/@task.branch callable: its return
    value is the task_id Airflow should run next."""
    return "load" if len(records) >= LOAD_THRESHOLD else "skip_load"


def _load_impl(records: list[dict]) -> int:
    """Stand-in for an idempotent UPSERT into a warehouse table (see Section 7)."""
    print(f"  (simulated) UPSERT {len(records)} row(s) into warehouse.orders")
    return len(records)


def _skip_load_impl() -> None:
    print("  volume below threshold - skipping the load step this run")


try:
    import airflow                                          # noqa: F401
    from airflow.decorators import dag, task

    @dag(
        dag_id="pattern_orders_etl",
        schedule="0 6 * * *",              # cron: every day at 06:00
        start_date=dt.datetime(2026, 1, 1),
        catchup=False,
        tags=["etl", "orders", "pattern"],
    )
    def pattern_orders_etl():
        @task
        def extract() -> list[dict]:
            return _extract_impl()

        @task
        def transform(records: list[dict]) -> list[dict]:
            return _transform_impl(records)

        @task.branch
        def check_volume(records: list[dict]) -> str:
            return _check_volume_impl(records)

        @task
        def load(records: list[dict]) -> int:
            return _load_impl(records)

        @task
        def skip_load() -> None:
            _skip_load_impl()

        raw = extract()                       # calling the task = creating a node
        cleaned = transform(raw)                # passing raw's return -> auto XCom + auto edge
        branch = check_volume(cleaned)
        branch >> [load(cleaned), skip_load()]    # branch's CHOSEN task_id runs; the other is skipped

    pattern_orders_etl()   # instantiating the decorated function registers the DAG with Airflow

    print("Airflow is installed in this environment - DAG 'pattern_orders_etl' registered for real.")

except ImportError:
    print("Airflow isn't installed in this sandbox; here's what running this DAG would produce:")
    print()
    xcom: dict[str, object] = {}   # stand-in for Airflow's real XCom backend (a metadata-DB table)

    print("[extract] starting...")
    xcom["extract"] = _extract_impl()
    print(f"[extract] finished -> {xcom['extract']}")

    print("[transform] starting (input = extract's XCom)...")
    xcom["transform"] = _transform_impl(xcom["extract"])
    print(f"[transform] finished -> {xcom['transform']}")

    print("[check_volume] starting (a branch task)...")
    branch_choice = _check_volume_impl(xcom["transform"])
    print(f"[check_volume] finished -> {branch_choice!r} (this string IS the next task_id to run)")

    for candidate in ("load", "skip_load"):
        if candidate == branch_choice:
            print(f"[{candidate}] starting (the branch chose this task)...")
            if candidate == "load":
                xcom["load"] = _load_impl(xcom["transform"])
                print(f"[load] finished -> {xcom['load']}")
            else:
                _skip_load_impl()
        else:
            print(f"[{candidate}] SKIPPED - Airflow marks the untaken branch(es) SKIPPED, not failed")


"""
---------------------------------------------------------------------
4. TASK DEPENDENCIES: >>, <<, AND THE OLDER set_upstream/set_downstream  ⭐⭐⭐
---------------------------------------------------------------------
In the TaskFlow example above, dependencies were inferred automatically
from function CALLS (`cleaned = transform(raw)` implies raw >> transform
node-wise). But you can also wire dependencies explicitly - required
for classic Operator objects, or for tasks with no data to pass (e.g.
a "start"/"end" marker task). `>>` means "runs before" (left is
upstream); `<<` is the mirror image. `set_upstream`/`set_downstream`
are the pre-2.0 method-call spelling of the exact same edges - you'll
still see them in older codebases.
---------------------------------------------------------------------
"""

print("\n--- Task Dependencies: >>, <<, set_upstream/set_downstream ---")

try:
    import airflow                                            # noqa: F401
    from airflow.operators.python import PythonOperator

    with airflow.DAG(
        dag_id="pattern_orders_etl_classic",
        schedule="0 6 * * *",
        start_date=dt.datetime(2026, 1, 1),
        catchup=False,
    ) as classic_dag:
        extract_task = PythonOperator(task_id="extract", python_callable=_extract_impl)
        transform_task = PythonOperator(task_id="transform", python_callable=_transform_impl)
        load_task = PythonOperator(task_id="load", python_callable=_load_impl)

        # three EQUIVALENT ways to declare "extract -> transform -> load" -
        # a real DAG would pick exactly ONE of these, never all three:
        extract_task >> transform_task >> load_task            # modern bitshift (most idiomatic today)
        load_task << transform_task << extract_task             # the mirror-image bitshift spelling
        extract_task.set_downstream(transform_task)               # pre-2.0 method-call spelling
        transform_task.set_upstream(extract_task)                  # ...and its mirror image

    print("Airflow is installed here - 'pattern_orders_etl_classic' registered with explicit edges.")

except ImportError:
    print("Airflow isn't installed in this sandbox; here's what running this DAG would produce:")
    print("  (identical order to Section 3's simulation: extract -> transform -> load -")
    print("   >>, <<, and set_upstream/set_downstream are three spellings of the SAME edge,")
    print("   so all three produce this one order: ['extract', 'transform', 'load'])")


"""
---------------------------------------------------------------------
5. COMMON OPERATORS: PythonOperator, BashOperator, PostgresOperator,
   BranchPythonOperator  ⭐⭐
---------------------------------------------------------------------
An OPERATOR is a template for ONE kind of unit of work; a TASK is an
operator instantiated inside a specific DAG. The TaskFlow @task
decorator is really just a friendlier way to write a PythonOperator -
under the hood it still generates one. Other operators wrap other
execution environments entirely (a shell, a SQL connection) instead
of a Python callable.
---------------------------------------------------------------------
"""

print("\n--- Common Operators ---")

print("PythonOperator / @task (the Python-callable case) - real, executed logic:")
sample = _extract_impl()
print("  _extract_impl() called directly as a plain function ->", sample)
print("  (this is EXACTLY what @task or PythonOperator(python_callable=_extract_impl)")
print("   calls under the hood - Airflow just adds scheduling, retries, and logging around it)")

try:
    import airflow                                             # noqa: F401
    from airflow.operators.bash import BashOperator
    from airflow.providers.postgres.operators.postgres import PostgresOperator
    from airflow.operators.python import BranchPythonOperator

    with airflow.DAG(dag_id="pattern_operator_reference", schedule=None, start_date=dt.datetime(2026, 1, 1)) as _ref_dag:
        # BashOperator - runs a shell command; common for calling an existing CLI tool
        dump_stats = BashOperator(
            task_id="dump_disk_stats",
            bash_command="df -h > /tmp/disk_report.txt",
        )

        # PostgresOperator - runs SQL against a configured connection ("postgres_default"),
        # resolved via Airflow's Connections UI/CLI, never a hardcoded password in code
        refresh_summary_table = PostgresOperator(
            task_id="refresh_order_summary",
            postgres_conn_id="warehouse_postgres",
            sql="REFRESH MATERIALIZED VIEW order_summary;",
        )

        # BranchPythonOperator - the CLASSIC (pre-@task.branch) spelling of Section 3's branch task
        route_on_volume = BranchPythonOperator(
            task_id="check_volume",
            python_callable=_check_volume_impl,
            op_args=[sample],
        )

        dump_stats >> refresh_summary_table >> route_on_volume

    print("Airflow is installed here - BashOperator/PostgresOperator/BranchPythonOperator tasks registered.")

except ImportError:
    print("Airflow isn't installed in this sandbox for BashOperator/PostgresOperator/")
    print("BranchPythonOperator - the code above is the real, correct syntax; it just")
    print("isn't executed here (no shell task runner or live Postgres connection needed for this file).")


"""
---------------------------------------------------------------------
6. SCHEDULING: schedule/CRON EXPRESSIONS, start_date, AND THE catchup
   BACKFILL GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
`schedule` (the modern name; older code says `schedule_interval`)
takes a cron expression, a `datetime.timedelta`, or a preset like
"@daily". `catchup` decides what happens to the GAP between
`start_date` and "now" the first time a DAG is turned on:
  catchup=True  (the Airflow-level DEFAULT) -> Airflow immediately
                schedules and runs ONE DagRun for every historical
                interval it missed - a real, very common "why did
                Airflow just kick off 400 tasks?!" surprise.
  catchup=False -> Airflow only ever runs the single most recent
                interval going forward. Almost always what you want
                unless you are deliberately backfilling.
---------------------------------------------------------------------
"""

print("\n--- Scheduling: Cron Expressions, start_date, and catchup ---")

schedule_cron = "0 6 * * *"          # minute hour day-of-month month day-of-week -> every day at 06:00
start_date = dt.datetime(2025, 1, 1)
now = dt.datetime(2026, 8, 25)
missed_days = (now - start_date).days

print(f"schedule='{schedule_cron}' (daily), start_date={start_date.date()}, now={now.date()}")
print(f"If someone flips this DAG on TODAY with catchup=True, Airflow would immediately")
print(f"queue roughly {missed_days} historical DagRuns - one per missed daily interval -")
print(f"all racing to run at once (bounded only by pool/parallelism limits). That is")
print(f"almost certainly NOT what anyone intended just from 'turning the DAG on'.")
print(f"With catchup=False, exactly ONE DagRun (the current interval) runs instead.")


"""
---------------------------------------------------------------------
7. XComs: PASSING SMALL DATA BETWEEN TASKS  ⭐⭐
---------------------------------------------------------------------
XCom ("cross-communication") is Airflow's mechanism for one task to
hand a small piece of data to another. The TaskFlow API does this
automatically: a task's `return` value becomes its XCom, and simply
passing that return value into another @task call wires up BOTH the
data AND the dependency edge in one line (Section 3's `transform(raw)`).
Classic operators do it manually via `ti.xcom_push(...)`/`xcom_pull(...)`.
XComs are stored in Airflow's metadata database, so they are meant for
SMALL values (IDs, counts, short lists/dicts) - never a full DataFrame
or file's contents; for large payloads, pass a file/S3 PATH through
XCom instead of the data itself.
---------------------------------------------------------------------
"""

print("\n--- XComs: Passing Small Data Between Tasks ---")

# the TaskFlow style already demonstrated live in Section 3's simulation:
#   xcom["transform"] = _transform_impl(xcom["extract"])
# is precisely what `cleaned = transform(raw)` compiles down to under the hood.
print("TaskFlow auto-XCom (Section 3): transform's ARGUMENT was extract's RETURN VALUE -")
print(f"  extract's XCom value:   {sample}")
print(f"  passed straight into:   _transform_impl(...) -> {_transform_impl(sample)}")

# classic manual spelling, shown for reference (needs a real TaskInstance, so guarded):
try:
    import airflow   # noqa: F401
    # inside a classic PythonOperator's python_callable(**context):
    #     context['ti'].xcom_push(key='row_count', value=len(records))
    #     ...later, in a downstream task...
    #     count = context['ti'].xcom_pull(task_ids='extract', key='row_count')
    print("Airflow is installed here - manual ti.xcom_push/xcom_pull would run against the live metadata DB.")
except ImportError:
    print("(manual ti.xcom_push()/xcom_pull() needs a live Airflow TaskInstance context - not")
    print(" runnable standalone here, but the two lines above are the real, correct syntax)")


"""
---------------------------------------------------------------------
8. IDEMPOTENCY: WHY AIRFLOW TASKS MUST TOLERATE RETRIES  ⭐⭐⭐
---------------------------------------------------------------------
This ties directly back to the earlier idempotent-pipelines notes in
this repo - but Airflow makes it a HARD requirement, not just a nice-
to-have, because Airflow itself re-runs tasks as normal operation:
`retries=N` in default_args triggers an automatic re-run on failure,
an operator can be manually "Cleared" in the UI to re-run it, and a
backfill re-runs a task for a historical interval that may have
already executed. If a task isn't idempotent, EVERY one of those
completely normal Airflow behaviors silently corrupts your data
(duplicate rows, double-counted totals) instead of safely no-op'ing.
---------------------------------------------------------------------
"""

print("\n--- Idempotency: Why Airflow Tasks Must Tolerate Retries ---")


def load_non_idempotent(records: list[dict], target: list[dict]) -> None:
    """BUGGY: every re-run/retry APPENDS again, so re-running the same
    task duplicates rows - exactly what a retried Airflow task will do."""
    target.extend(records)


def load_idempotent(records: list[dict], target: dict[str, dict]) -> None:
    """FIXED: UPSERT by primary key - safe to call any number of times."""
    for r in records:
        target[r["order_id"]] = r


records = _transform_impl(_extract_impl())

naive_table: list[dict] = []
load_non_idempotent(records, naive_table)
load_non_idempotent(records, naive_table)   # simulates Airflow retrying/re-triggering this task
print(f"non-idempotent load run TWICE  -> {len(naive_table)} rows (WRONG - duplicated!)")

idempotent_table: dict[str, dict] = {}
load_idempotent(records, idempotent_table)
load_idempotent(records, idempotent_table)   # same retry scenario
print(f"idempotent load run TWICE      -> {len(idempotent_table)} rows (correct - upsert by key)")

print("\nSection 3/9's `_load_impl` is written as an UPSERT for exactly this reason -")
print("it can be safely retried by Airflow with no manual cleanup step.")


"""
---------------------------------------------------------------------
9. HAND-ROLLED DAG RUNNER: LIVE TOPOLOGICAL EXECUTION  ⭐⭐⭐
---------------------------------------------------------------------
Putting it all together: a minimal stand-in for what an Airflow
EXECUTOR does at run time - given a dependency graph and a callable
per task, compute a valid order (reusing Section 1's topological_sort,
so an invalid/cyclic graph is rejected the same way) and run each task
in that order, threading each task's return value into its downstream
tasks as arguments (our own tiny XCom table), and printing each
task's start and output so the dependency order is visibly proven.
---------------------------------------------------------------------
"""

print("\n--- Hand-Rolled DAG Runner: Live Topological Execution ---")


def run_dag(
    task_fns: dict[str, Callable[..., object]],
    dependencies: dict[str, list[str]],
) -> dict[str, object]:
    """Execute `task_fns` in a valid topological order, threading each
    upstream task's return value into its downstream task(s) as positional
    arguments - a miniature version of Airflow's scheduler + XCom passing."""
    order = topological_sort(dependencies)          # raises ValueError if this isn't a real DAG
    xcom: dict[str, object] = {}
    for task_id in order:
        upstream_results = [xcom[u] for u in dependencies[task_id]]
        print(f"[{task_id}] starting (upstream inputs: {upstream_results!r})")
        result = task_fns[task_id](*upstream_results)
        xcom[task_id] = result
        print(f"[{task_id}] finished -> {result!r}")
    return xcom


task_fns = {
    "extract": _extract_impl,
    "transform": _transform_impl,
    "load": _load_impl,
}
run_edges = {
    "extract": [],
    "transform": ["extract"],
    "load": ["transform"],
}

print("first run:")
final_xcom = run_dag(task_fns, run_edges)
print("final XCom table:", final_xcom)

print("\nsecond run of the SAME dag (simulating Airflow retrying/re-running it) -")
print("safe because `load` is idempotent (Section 8):")
run_dag(task_fns, run_edges)

print("\nfeeding run_dag a CYCLIC graph instead - it fails the same way Section 1 did,")
print("proving the runner enforces the acyclic requirement, not just documents it:")
try:
    run_dag(task_fns, {"extract": ["load"], "transform": ["extract"], "load": ["transform"]})
except ValueError as e:
    print("run_dag correctly refused to execute an invalid DAG:", e)


"""
=====================================================================
QUICK REFERENCE
=====================================================================
DAG              -> Directed Acyclic Graph of tasks; NO cycles, ever,
                     or there is no valid order to run them in
Why DAGs          -> static graph -> parallel levels, partial re-run,
                     visualization; a linear script gives you none of that

TaskFlow API:
    @dag(schedule=..., start_date=..., catchup=...)   -> defines a DAG
    @task                                                -> ~ PythonOperator
    @task.branch                                          -> returns next task_id;
                                                             untaken branch = SKIPPED
    calling a @task function wires the edge AND the XCom automatically

Dependencies (three equivalent spellings of the SAME edge):
    a >> b            -> a runs before b (modern, most common)
    b << a             -> identical edge, mirror-image spelling
    a.set_downstream(b) / b.set_upstream(a)  -> pre-2.0 method spelling

Operators:
    PythonOperator / @task     -> run a Python callable
    BashOperator                -> run a shell command
    PostgresOperator / hooks     -> run SQL via a Connection (no hardcoded creds)
    BranchPythonOperator/@task.branch -> return value = next task_id to run

Scheduling:
    schedule="<cron>" / timedelta / "@daily"   -> when it *would* run
    start_date                                   -> earliest interval
    catchup=True  -> backfills EVERY missed interval immediately (gotcha!)
    catchup=False -> only the current interval runs (usual safe default)

XComs      -> small return-value data passed task-to-task; TaskFlow does
              it automatically; NEVER put large data (DataFrames/files) in one

Idempotency -> a task MUST be safe to retry/re-run/backfill, because
               Airflow itself re-runs tasks as normal operation ->
               design loads as UPSERT-by-key, not append/increment

Hand-rolled DAG runner = topological_sort() + execute in that order,
threading each task's return value to its downstream task(s)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - APACHE AIRFLOW BASICS
=====================================================================

1. What does the "acyclic" in Directed Acyclic Graph actually forbid,
   and why does a cycle make a pipeline unschedulable rather than
   merely inefficient?

2. Walk through what `topological_sort()` in this file does with the
   `cyclic_edges` dict, and explain WHY its in-degree bookkeeping
   ends up detecting that cycle instead of just running forever.

3. Why did Airflow's designers choose an explicit DAG data structure
   instead of letting people just write a linear Python script for
   their pipeline? Give at least two concrete engineering reasons.

4. In the TaskFlow API, how does writing `cleaned = transform(raw)`
   both create a task dependency AND pass data between tasks, without
   you calling `>>` or touching XCom explicitly?

5. What is the difference between `@task` and `@task.branch`? What
   happens to the tasks NOT chosen by a branch task's return value -
   do they fail, or something else?

6. Name three different ways to declare "task A runs before task B"
   in Airflow, and explain why they all produce the identical edge.

7. What's the practical difference between `PythonOperator`,
   `BashOperator`, and `PostgresOperator`? When would you reach for
   a `PostgresOperator`/hook instead of writing the SQL logic inside
   a `PythonOperator`?

8. Explain the `catchup` parameter. If a DAG has `start_date` set to
   18 months ago, a daily `schedule`, and someone turns it on today
   with `catchup=True`, what actually happens - and why does this
   surprise so many people in production?

9. What is an XCom, and what kind of data is it appropriate (and NOT
   appropriate) to pass through one? Why shouldn't you XCom an entire
   Pandas DataFrame?

10. Why must Airflow tasks be designed to be idempotent, specifically
    in terms of Airflow's own retry/backfill/manual-clear behaviors -
    not just as a general "good practice" for pipelines?

11. In this file's `load_non_idempotent` vs `load_idempotent`, what
    specifically makes one unsafe to re-run and the other safe? What
    real-world load pattern does `load_idempotent` correspond to?

12. Describe, at a high level, what an Airflow EXECUTOR does at run
    time, and how the hand-rolled `run_dag()` function in this file
    mirrors that (topological order + XCom-style value threading).

13. If `run_dag()` is called with a graph that turns out to be cyclic,
    what happens, and why does that failure occur BEFORE any task
    function is ever actually called?

14. What is the practical difference between a "task retry" (Airflow
    re-running a failed task automatically) and a "backfill" (Airflow
    running historical intervals)? Why does idempotency matter for
    both, for the same underlying reason?

15. How would you design a Python ETL script (or Airflow DAG) to be
    safely re-runnable without duplicating data, for a load step that
    writes to a table with no natural unique key to upsert on?
=====================================================================
"""
