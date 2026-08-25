"""
=====================================================================
PYTHON DATA STRUCTURES - Overview, Uses & Classification
=====================================================================

A data structure is a way of organizing and storing data so it can
be accessed and modified efficiently. Python's data structures fall
into two broad categories:

    BUILT-IN            -> ready to use, implemented in C for speed
    ABSTRACT/USER-BUILT -> built using built-ins (collections module,
                            array module, or custom classes)

For a Data Engineer, choosing the right data structure directly
impacts MEMORY footprint, PROCESSING SPEED, and CORRECTNESS when
handling large-scale data. This is one of the most interview-tested
areas in the entire language.

CLASSIFICATION COVERED IN THIS FILE:
    1. Primitive (scalar) types
    2. Non-primitive (container) types: list, tuple, set, dict, str
    3. Specialized collections (collections module)
    4. Array-based / numeric structures (array, NumPy, Pandas)
    5. Abstract Data Types built from the above (stack, queue, etc.)
=====================================================================
"""

print("--- Overview ---")
print("Data structures organize data for efficient access/modification.")


"""
---------------------------------------------------------------------
1. PRIMITIVE (SCALAR) TYPES
---------------------------------------------------------------------
Hold a SINGLE value. All are IMMUTABLE.

    int, float, bool, complex, NoneType

Use case: counters, flags, IDs, numeric computation, sentinel/null
markers.
---------------------------------------------------------------------
"""

print("\n--- Primitive Types ---")

counter = 0
price = 19.99
is_valid = True
complex_num = 2 + 3j
missing = None

for val in [counter, price, is_valid, complex_num, missing]:
    print(f"value={val!r:10} type={type(val).__name__}")


"""
---------------------------------------------------------------------
2. NON-PRIMITIVE (CONTAINER) TYPES  ⭐⭐⭐
---------------------------------------------------------------------
Hold COLLECTIONS of values. This is where most data engineering work
happens.

Structure   | Ordered? | Mutable? | Duplicates? | Indexed?
------------|----------|----------|-------------|----------
list        | Yes      | Yes      | Yes         | Yes
tuple       | Yes      | No       | Yes         | Yes
set         | No       | Yes      | No          | No
frozenset   | No       | No       | No          | No
dict        | Yes(3.7+)| Yes      | Keys:No     | By key
str         | Yes      | No       | Yes         | Yes

Uses:
    list  -> row buffers, batch collections, ordered ETL staging data
    tuple -> fixed records (e.g. a DB row), function returns,
             composite dict keys
    set   -> deduplication, fast membership checks, set algebra
             (e.g., diffing source vs target tables)
    dict  -> lookups/mappings, JSON-like records, schema definitions,
             caching/memoization
    str   -> text/log parsing, file paths, serialized data
---------------------------------------------------------------------
"""

print("\n--- Non-Primitive (Container) Types ---")

# list: ordered, mutable, allows duplicates
row_buffer = ["order_1", "order_2", "order_1"]
print("list (row buffer):", row_buffer)

# tuple: ordered, immutable - great for a fixed DB row/record
db_row = ("ORD001", "2026-08-13", 149.99)
print("tuple (fixed record):", db_row)

# set: unordered, no duplicates - great for deduplication
source_ids = {"A", "B", "C", "D"}
target_ids = {"C", "D", "E"}
print("\nset algebra for diffing source vs target tables:")
print("  in source but not target:", source_ids - target_ids)
print("  in both (intersection):", source_ids & target_ids)
print("  in either (union):", source_ids | target_ids)

# dict: key-value mapping - the natural shape of a JSON record
record = {"order_id": "ORD001", "amount": 149.99, "status": "shipped"}
print("\ndict (JSON-like record):", record)

# str: ordered sequence of characters
log_line = "2026-08-13 INFO Order ORD001 shipped"
print("\nstr (log line):", log_line)


"""
---------------------------------------------------------------------
3. SPECIALIZED COLLECTIONS (collections module)  ⭐⭐
---------------------------------------------------------------------
Purpose-built structures solving common performance/readability
problems that plain lists/dicts handle awkwardly.

    defaultdict  -> auto-initializes missing keys (no KeyError checks)
    Counter      -> frequency counting (word counts, value distributions)
    OrderedDict  -> preserves insertion order explicitly, supports
                    move_to_end() for reordering
    namedtuple   -> lightweight, immutable, self-documenting record -
                    like a mini schema
    deque        -> O(1) append/pop from BOTH ends - ideal for queues,
                    sliding windows, streaming buffers
    ChainMap     -> merges multiple dicts into one logical view
                    without copying

DE use case: Counter for column value distributions during data
profiling; deque for streaming/windowed aggregations; namedtuple for
lightweight typed records instead of full classes.
---------------------------------------------------------------------
"""

print("\n--- Specialized Collections (collections module) ---")

from collections import defaultdict, Counter, OrderedDict, namedtuple, deque, ChainMap

# defaultdict - avoids manually checking "if key not in dict"
grouped = defaultdict(list)
transactions = [("US", 100), ("IN", 50), ("US", 75), ("IN", 20)]
for country, amount in transactions:
    grouped[country].append(amount)   # no KeyError, even on first use
print("defaultdict grouping:", dict(grouped))

# Counter - instant frequency counting, common in data profiling
statuses = ["shipped", "pending", "shipped", "delivered", "shipped"]
status_counts = Counter(statuses)
print("Counter (value distribution):", status_counts)
print("most common status:", status_counts.most_common(1))

# OrderedDict - explicit order control beyond normal dict behavior
od = OrderedDict()
od["step1"] = "extract"
od["step2"] = "transform"
od["step3"] = "load"
od.move_to_end("step1")             # move 'step1' to the end
print("OrderedDict after move_to_end:", od)

# namedtuple - lightweight, self-documenting record (like a mini schema)
Order = namedtuple("Order", ["order_id", "amount", "status"])
order = Order(order_id="ORD001", amount=149.99, status="shipped")
print("namedtuple record:", order, "| access by name:", order.amount)

# deque - O(1) appends/pops from both ends, great for streaming windows
window = deque(maxlen=3)             # a fixed-size sliding window
for value in [10, 20, 30, 40, 50]:
    window.append(value)             # oldest value auto-evicted
    print("sliding window:", list(window))

# ChainMap - merges multiple dicts logically without copying data
defaults = {"timeout": 30, "retries": 3}
overrides = {"timeout": 60}
config = ChainMap(overrides, defaults)   # overrides take priority
print("\nChainMap merged config:", dict(config))


"""
---------------------------------------------------------------------
4. ARRAY-BASED / NUMERIC STRUCTURES  ⭐⭐⭐
---------------------------------------------------------------------
    array          -> built-in 'array' module: memory-efficient
                       homogeneous numeric arrays
    numpy.ndarray  -> vectorized numeric computation, the foundation
                       of Pandas
    pandas.Series/
    DataFrame      -> tabular data - the CORE structure of almost
                       all data engineering transformation work

Note: NumPy/Pandas may not be installed in every environment; this
section is illustrative of usage patterns you'll see constantly in
DE code.
---------------------------------------------------------------------
"""

print("\n--- Array-Based / Numeric Structures ---")

import array as array_module

# array module - stores only ONE type, more memory-efficient than a
# list of the same numbers (a list stores full Python int objects,
# an array stores raw C-style values)
int_array = array_module.array("i", [1, 2, 3, 4, 5])   # 'i' = signed int
print("array module (typed, memory-efficient):", int_array)

try:
    import numpy as np
    import pandas as pd

    arr = np.array([1, 2, 3, 4, 5])
    print("\nnumpy ndarray:", arr, "| vectorized *2:", arr * 2)

    df = pd.DataFrame({
        "order_id": ["ORD001", "ORD002", "ORD003"],
        "amount": [149.99, 89.50, 220.00],
    })
    print("\npandas DataFrame (core DE structure):")
    print(df)
except ImportError:
    print("\n(numpy/pandas not installed in this environment - "
          "shown conceptually above in earlier explanations)")


"""
---------------------------------------------------------------------
5. ABSTRACT DATA TYPES (ADTs) - BUILT FROM THE ABOVE  ⭐⭐
---------------------------------------------------------------------
Not built into Python directly - implemented using lists/deques/dicts.

    Stack (LIFO)         -> list or deque - undo ops, DFS, expression
                             parsing
    Queue (FIFO)          -> deque or queue.Queue - task scheduling,
                             BFS, message buffering
    Priority Queue        -> heapq - job scheduling, top-K problems
    Linked List/Tree/Graph -> custom classes - rarely hand-built in DE
                             work, but conceptually tested (e.g.,
                             representing a DAG of pipeline dependencies)
---------------------------------------------------------------------
"""

print("\n--- Abstract Data Types (ADTs) ---")

# Stack (LIFO) using a list - append/pop from the END
stack = []
stack.append("task1")
stack.append("task2")
stack.append("task3")
print("stack after pushes:", stack)
print("pop (LIFO - last in, first out):", stack.pop())
print("stack after pop:", stack)

# Queue (FIFO) using deque - append at one end, popleft from the other
task_queue = deque()
task_queue.append("job1")
task_queue.append("job2")
task_queue.append("job3")
print("\nqueue after pushes:", task_queue)
print("popleft (FIFO - first in, first out):", task_queue.popleft())
print("queue after popleft:", task_queue)

# Priority Queue using heapq - always pops the SMALLEST item
import heapq

jobs = []
heapq.heappush(jobs, (3, "low priority job"))
heapq.heappush(jobs, (1, "high priority job"))
heapq.heappush(jobs, (2, "medium priority job"))
print("\npriority queue (heapq), popped in priority order:")
while jobs:
    priority, job_name = heapq.heappop(jobs)
    print(f"  priority={priority}: {job_name}")


"""
---------------------------------------------------------------------
6. QUICK DECISION GUIDE FOR DATA ENGINEERS
---------------------------------------------------------------------
Need                          | Best Structure
-------------------------------|---------------------------
Fast lookups by key            | dict
Deduplicate values             | set
Preserve order + duplicates    | list
Immutable fixed record         | tuple / namedtuple
Frequency counts               | Counter
FIFO/streaming buffer          | deque
Tabular/columnar data          | pandas.DataFrame
Numeric vectorized ops         | numpy.ndarray
Nested JSON/API response       | dict + list combo
Composite dict key             | tuple
---------------------------------------------------------------------
"""

print("\n--- Quick Decision Guide (see comment block above) ---")
print("Pick structures based on: lookup speed, order, duplicates,")
print("mutability needs, and memory footprint.")


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON DATA STRUCTURES (OVERVIEW LEVEL)
=====================================================================

1. What's the difference between a primitive and a non-primitive
   (container) data type in Python?

2. Why would you choose a set over a list for deduplication, and
   what's the time-complexity difference for membership checks
   (`in`) between the two?

3. When would you use a namedtuple instead of a plain dict or a
   full class to represent a record? What are the trade-offs?

4. Explain a real data engineering use case for `defaultdict` versus
   a regular `dict` with manual `if key not in dict` checks.

5. Why is `deque` preferred over a plain `list` for implementing a
   queue or a sliding window? (Hint: `list.pop(0)` is O(n); deque's
   `popleft()` is O(1).)

6. What's the difference between a `Counter` and manually counting
   values with a `defaultdict(int)`? When would you use `Counter`
   specifically?

7. How does `array.array` differ from a regular Python `list` when
   storing large amounts of numeric data? Why might it be more
   memory-efficient?

8. Why is `pandas.DataFrame` considered the "core" data structure in
   most data engineering pipelines, and what is it built on top of
   internally? (Hint: NumPy ndarrays under the hood.)

9. Explain how you'd implement a Stack and a Queue in Python using
   only built-in types, and why the choice of underlying structure
   (list vs deque) matters for performance.

10. What is a priority queue, and why would you use Python's
    `heapq` module instead of manually sorting a list every time you
    need the smallest/highest-priority item?

11. Give a data engineering scenario where you'd use set algebra
    (union, intersection, difference) - e.g., comparing source and
    target datasets during a data reconciliation/audit step.

12. How would you represent a DAG (Directed Acyclic Graph) of
    pipeline task dependencies in Python, and what data structure(s)
    would you use? (Hint: dict of lists/sets for adjacency;
    relevant to tools like Airflow under the hood.)

13. What's the difference between `OrderedDict` and a regular `dict`
    in modern Python (3.7+), given that regular dicts now also
    preserve insertion order? When would `OrderedDict` still be the
    better choice?

14. If you needed to merge multiple configuration dictionaries where
    later ones should override earlier ones, but WITHOUT physically
    copying/merging the data, what structure would you use?
    (Hint: ChainMap)
=====================================================================
"""