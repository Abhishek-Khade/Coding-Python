# Python Syllabus for Data Engineers
### A structured roadmap with must-know concepts and real interview questions

---

## 📌 How to Use This Syllabus
Data Engineering interviews test Python not in isolation, but as a tool for **data movement, transformation, and scale**. This syllabus is organized in the order most interviewers probe: fundamentals → data structures → OOP → file/data handling → performance → libraries → databases → real-world ETL scenarios.

⭐ = **Frequently asked / High-weight interview topic**

---

## Module 1: Python Fundamentals
- Variables, data types, type casting
- Operators, conditionals, loops
- String manipulation & formatting (f-strings, `.format()`)
- Mutable vs Immutable objects ⭐
- `is` vs `==` ⭐
- Shallow copy vs Deep copy ⭐

**Interview Questions:**
1. What's the difference between `is` and `==` in Python?
2. Why are tuples faster than lists?
3. Explain mutable vs immutable objects with examples (list, dict vs tuple, str, int).
4. What happens internally when you do `a = b` for two lists?
5. Difference between `copy.copy()` and `copy.deepcopy()`.

---

## Module 2: Data Structures ⭐⭐⭐
This is the **most heavily tested** area — data engineers manipulate large, nested, messy data constantly.

- Lists, Tuples, Sets, Dictionaries — internal working & complexity (Big-O) ⭐
- List/Dict/Set comprehensions ⭐
- `collections` module: `defaultdict`, `Counter`, `OrderedDict`, `namedtuple`, `deque` ⭐
- Nested data structures (list of dicts, dict of lists) — common in JSON/API data
- Sorting with `key=` and `lambda`
- Stacks & Queues using Python

**Interview Questions:**
1. What is the time complexity of lookup in a list vs a dictionary vs a set?
2. How does a Python dictionary work internally (hashing)?
3. Find duplicates in a list — multiple approaches.
4. Flatten a nested list/dictionary (very common in ETL parsing).
5. When would you use a `defaultdict` over a regular `dict`?
6. Write a list comprehension to filter and transform data in one line.
7. How would you deduplicate records while preserving order?

---

## Module 3: Functions & Functional Programming ⭐⭐
Data engineers write pipelines as functions — this is core to writing clean transformation logic.

- `*args`, `**kwargs` ⭐
- Lambda functions
- `map()`, `filter()`, `reduce()` ⭐
- **Decorators** ⭐⭐⭐ (used for logging, retries, timing pipeline steps)
- **Generators & `yield`** ⭐⭐⭐ (critical for memory-efficient processing of large datasets)
- Iterators vs Generators ⭐
- Closures

**Interview Questions:**
1. What is a generator, and why would you use it while processing a 10GB file?
2. Write a decorator to log the execution time of a function.
3. Explain the difference between a decorator and a higher-order function.
4. How does `yield` differ from `return`?
5. Write a generator function to read a huge CSV file line-by-line without loading it fully into memory. (**Extremely common!**)
6. Difference between iterators and iterables.

---

## Module 4: Object-Oriented Programming (OOP)
- Classes, objects, `__init__`, `self`
- Inheritance, Polymorphism, Encapsulation, Abstraction
- Magic/Dunder methods (`__str__`, `__repr__`, `__len__`, `__eq__`) ⭐
- `@staticmethod` vs `@classmethod` vs instance methods ⭐
- Abstract Base Classes (`abc` module)

**Interview Questions:**
1. Difference between `@staticmethod` and `@classmethod`?
2. Why do we override `__repr__` and `__str__`?
3. How would you design a class to represent a data pipeline/ETL job?
4. What is method resolution order (MRO)?

---

## Module 5: Exception Handling & Robust Code ⭐⭐
Pipelines fail — interviewers test how gracefully your code handles it.

- `try / except / else / finally`
- Custom exceptions
- Handling multiple exception types
- Context managers (`with` statement) & writing your own using `__enter__`/`__exit__` or `contextlib` ⭐

**Interview Questions:**
1. How do you handle exceptions in a data pipeline processing multiple files (so one bad file doesn't kill the whole job)?
2. What is a context manager? Write one to manage a DB connection.
3. Difference between `except Exception` and a bare `except:`.
4. How would you implement retry logic for a flaky API call?

---

## Module 6: File Handling & Data Formats ⭐⭐⭐
Central to Data Engineering — reading/writing at scale.

- Reading/writing files: `open()`, context managers
- **CSV** (`csv` module vs Pandas) ⭐
- **JSON** (nested JSON parsing) ⭐⭐
- **Parquet, Avro, ORC** — columnar formats and why they matter for big data ⭐⭐
- Working with large files efficiently (chunking, streaming) ⭐⭐⭐
- `pathlib` vs `os` module

**Interview Questions:**
1. How do you process a file too large to fit into memory?
2. Why is Parquet preferred over CSV in big data pipelines? (columnar storage, compression, schema)
3. How do you flatten deeply nested JSON into a tabular structure?
4. Read a JSON Lines (`.jsonl`) file and process it in chunks.
5. Compare read/write speed and storage: CSV vs Parquet vs Avro.

---

## Module 7: Pandas & NumPy ⭐⭐⭐
The backbone of transformation logic in most DE interviews and take-home tests.

- Series & DataFrame basics
- `groupby`, `merge`, `join`, `pivot_table` ⭐⭐
- Handling missing data (`fillna`, `dropna`) ⭐
- `apply()`, `map()`, `applymap()` and vectorization ⭐⭐
- Memory optimization (`dtypes`, `category` type, chunksize) ⭐⭐
- Merging/joining large datasets efficiently
- NumPy arrays vs Python lists — performance difference ⭐

**Interview Questions:**
1. Why is vectorized operation in NumPy/Pandas faster than a Python `for` loop?
2. How do you handle a dataset that doesn't fit in memory using Pandas (`chunksize`)?
3. Difference between `merge()`, `join()`, and `concat()` in Pandas.
4. How would you optimize memory usage of a large DataFrame?
5. Explain `groupby` + `agg` with a business use case (e.g., total sales per region).
6. How do you detect and handle duplicate/null records in a DataFrame?

---

## Module 8: Concurrency & Performance ⭐⭐
Relevant for parallelizing ETL jobs.

- Multithreading vs Multiprocessing ⭐⭐
- GIL (Global Interpreter Lock) — what it is and why it matters ⭐⭐⭐
- `concurrent.futures`, `threading`, `multiprocessing`
- When to use threads (I/O-bound) vs processes (CPU-bound) ⭐⭐
- `asyncio` basics for concurrent I/O (API calls, DB calls)

**Interview Questions:**
1. What is the GIL, and how does it affect multithreading in Python?
2. When would you use multiprocessing over multithreading in a data pipeline?
3. How would you parallelize downloading 1,000 files from an API?
4. Explain `asyncio` and where it fits in data engineering (concurrent API/DB calls).

---

## Module 9: Databases & SQL Integration ⭐⭐⭐
- Connecting to databases: `psycopg2`, `pyodbc`, `sqlite3`
- **SQLAlchemy** ORM basics ⭐⭐
- Writing parameterized queries (SQL injection prevention) ⭐
- Bulk inserts / batch processing for performance ⭐⭐
- Connection pooling
- Working with NoSQL from Python (MongoDB via `pymongo`)

**Interview Questions:**
1. How do you prevent SQL injection when running dynamic queries from Python?
2. How would you efficiently insert 1 million rows into a database from Python?
3. What is connection pooling, and why does it matter for pipelines?
4. Difference between executing raw SQL vs using an ORM (SQLAlchemy) — trade-offs?

---

## Module 10: APIs, Web Scraping & External Data ⭐
- `requests` library — GET/POST, headers, auth, pagination handling ⭐
- Handling rate limits & retries (`backoff`, `tenacity`)
- Parsing API responses (JSON) into structured data
- Basics of `BeautifulSoup` for scraping (less common but occasionally asked)

**Interview Questions:**
1. How do you handle pagination when pulling data from a REST API?
2. How do you implement exponential backoff for API retries?
3. How would you design a Python script to incrementally pull only *new* data from an API daily?

---

## Module 11: ETL/ELT Design & Orchestration ⭐⭐⭐
Where Python meets real Data Engineering system design.

- Writing idempotent pipelines ⭐⭐⭐ (Very frequently discussed conceptually)
- Batch vs Streaming processing
- Basics of **Apache Airflow** (DAGs, operators, task dependencies) ⭐⭐
- Logging best practices (`logging` module vs `print`) ⭐
- Config management (`.env`, `configparser`, avoiding hardcoded secrets)
- Data validation (`pydantic`, `great_expectations` basics)

**Interview Questions:**
1. What does "idempotent" mean in the context of a data pipeline, and how do you design for it?
2. How would you structure a Python ETL script to be re-runnable without duplicating data?
3. How do you handle schema evolution in incoming data?
4. Explain how you'd log and monitor failures in a scheduled Python ETL job.
5. How would you validate incoming data quality before loading it into a warehouse?

---

## Module 12: Big Data Tools with Python ⭐⭐
- **PySpark basics**: RDDs vs DataFrames, transformations vs actions ⭐⭐⭐
- Lazy evaluation in Spark ⭐⭐
- `groupBy`, `join`, partitioning in PySpark
- Working with **Dask** for parallel Pandas-like processing (increasingly asked)
- Cloud SDKs: `boto3` (AWS), `google-cloud-storage` (GCP), `azure-storage-blob`

**Interview Questions:**
1. Difference between transformations and actions in Spark, and why does it matter?
2. What is lazy evaluation, and why is it useful in distributed processing?
3. How would you read/write files to S3 using `boto3`?
4. How do you handle data skew in a PySpark join?
5. When would you choose Dask over Spark, or vice versa?

---

## Module 13: Testing & Code Quality
- Unit testing with `pytest` ⭐
- Mocking external calls (`unittest.mock`) — mocking DB/API in tests ⭐
- Type hints (`typing` module) for pipeline reliability
- Code style: PEP8, linting (`flake8`, `black`)

**Interview Questions:**
1. How do you unit test a function that reads from a database?
2. What's the benefit of type hints in large data pipelines?
3. How would you mock an API call in a test?

---

## 🎯 Top 15 "Must-Prepare" Interview Questions (Cross-Cutting)
1. Write a generator to lazily read and process a large log file.
2. How do you deduplicate millions of records efficiently in Python?
3. Explain GIL and its impact on parallel data processing.
4. Design a Python function to merge two large datasets without running out of memory.
5. Difference between list, tuple, set, dict — and when to use each in pipeline design.
6. How would you make an ETL job idempotent and fault-tolerant?
7. Write a decorator that retries a function on failure with exponential backoff.
8. Why is Parquet better than CSV for data warehousing?
9. How do you handle malformed/missing data during ingestion?
10. Explain `*args`/`**kwargs` with a pipeline configuration example.
11. Compare Pandas `apply()` vs vectorized operations — which is faster and why?
12. How would you parallelize processing of 100 independent files?
13. Explain multiprocessing vs multithreading with a data engineering example.
14. How do you connect Python to a SQL database and perform a bulk insert safely?
15. Walk through how you'd design an end-to-end pipeline: extract from API → transform with Pandas → load into a warehouse.

---

## 📚 Suggested Learning Order
1. Python Fundamentals → Data Structures → Functions
2. OOP → Exception Handling
3. File Handling & Data Formats
4. Pandas/NumPy (heavy practice)
5. Databases & SQL Integration
6. Concurrency & Performance
7. ETL Design + Airflow basics
8. PySpark / Big Data tools
9. Testing & Code Quality
10. Mock interviews focused on the "Top 15" list above

---

### 💡 Pro Tip for Interviews
Most DE interviews don't ask "what is Python" — they ask you to **solve a data problem using Python**: parsing messy JSON, deduplicating records, handling a file too big for memory, or designing a retry-safe pipeline. Practice by writing small scripts that solve these scenarios rather than memorizing definitions.