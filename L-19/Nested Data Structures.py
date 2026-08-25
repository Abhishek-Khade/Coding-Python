"""
=====================================================================
NESTED DATA STRUCTURES IN PYTHON - list of dicts, dict of lists,
and other JSON/API-shaped data
=====================================================================

Real-world data - API responses, JSON files, MongoDB documents,
config files - is almost NEVER a flat list or a single dict. It's
usually one of these NESTED shapes:

    LIST OF DICTS   -> [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
                        The most common shape for API results: an
                        array of RECORDS (like rows in a table).

    DICT OF LISTS   -> {"id": [1, 2], "name": ["A", "B"]}
                        "Columnar" shape - one list per FIELD. This
                        is exactly how Pandas stores a DataFrame
                        internally, and how you'd build one directly.

    DICT OF DICTS   -> {"1": {"name": "A"}, "2": {"name": "B"}}
                        Records keyed by an ID - great for O(1)
                        lookup by that ID, unlike a list of dicts
                        which requires a linear search.

    DEEPLY NESTED    -> combinations of the above, arbitrarily deep -
                        the typical shape of a real JSON API response.

This file covers: recognizing these shapes, converting between them,
safely accessing deep values, flattening, and common ETL patterns.
=====================================================================
"""

print("--- Overview ---")
print("Nested structures combine list/dict to represent real-world,")
print("JSON/API-shaped data - records, columns, and lookups.")


"""
---------------------------------------------------------------------
1. LIST OF DICTS: "ARRAY OF RECORDS"  ⭐⭐⭐
---------------------------------------------------------------------
This is the MOST common shape returned by REST APIs and JSON files -
each dict is one "row"/record, and all dicts typically share a
similar (though not strictly guaranteed identical) set of keys.
---------------------------------------------------------------------
"""

print("\n--- List of Dicts: Array of Records ---")

orders = [
    {"order_id": "ORD1", "customer": "Alice", "amount": 100.0, "status": "shipped"},
    {"order_id": "ORD2", "customer": "Bob", "amount": 250.0, "status": "pending"},
    {"order_id": "ORD3", "customer": "Alice", "amount": 75.0, "status": "shipped"},
]

print("orders:", orders)

# Accessing a field across ALL records - a list comprehension pulling
# one column out of a list of dicts
all_amounts = [o["amount"] for o in orders]
print("\nall amounts (one 'column'):", all_amounts)

# Filtering records by a condition - the most common ETL operation
# on this shape
shipped_orders = [o for o in orders if o["status"] == "shipped"]
print("shipped orders only:", shipped_orders)

# Transforming each record (e.g., adding a computed field) without
# mutating the originals
with_tax = [{**o, "amount_with_tax": round(o["amount"] * 1.08, 2)} for o in orders]
print("\nwith a computed field added:", with_tax)


"""
---------------------------------------------------------------------
2. DICT OF LISTS: "COLUMNAR" SHAPE  ⭐⭐⭐
---------------------------------------------------------------------
Here, each KEY represents a FIELD/COLUMN, and its VALUE is a list of
that field's values across all records. This is exactly how
pandas.DataFrame stores data internally, and how many APIs
(especially analytics/columnar APIs) return bulk data efficiently.
---------------------------------------------------------------------
"""

print("\n--- Dict of Lists: Columnar Shape ---")

orders_columnar = {
    "order_id": ["ORD1", "ORD2", "ORD3"],
    "customer": ["Alice", "Bob", "Alice"],
    "amount": [100.0, 250.0, 75.0],
    "status": ["shipped", "pending", "shipped"],
}

print("orders_columnar:", orders_columnar)

# Accessing one "column" is now a direct key lookup - O(1), no
# comprehension needed
print("\nall amounts (direct key access):", orders_columnar["amount"])

# Accessing one "row" (record) requires reading the SAME index across
# every list - more awkward than the list-of-dicts shape for
# row-wise operations
def get_row(columnar_data, index):
    return {key: values[index] for key, values in columnar_data.items()}

print("row at index 1 (reconstructed):", get_row(orders_columnar, 1))


"""
---------------------------------------------------------------------
3. CONVERTING BETWEEN LIST-OF-DICTS AND DICT-OF-LISTS  ⭐⭐⭐
---------------------------------------------------------------------
This conversion ("pivoting" the data's orientation) comes up
constantly - APIs might return one shape while a downstream tool
(like Pandas or a plotting library) expects the other.
---------------------------------------------------------------------
"""

print("\n--- Converting Between the Two Shapes ---")

def list_of_dicts_to_dict_of_lists(records):
    """Convert row-oriented data to column-oriented data."""
    if not records:
        return {}
    keys = records[0].keys()
    return {key: [record[key] for record in records] for key in keys}

def dict_of_lists_to_list_of_dicts(columnar):
    """Convert column-oriented data to row-oriented data."""
    keys = list(columnar.keys())
    length = len(next(iter(columnar.values())))
    return [{key: columnar[key][i] for key in keys} for i in range(length)]

converted_columnar = list_of_dicts_to_dict_of_lists(orders)
print("list-of-dicts -> dict-of-lists:", converted_columnar)

converted_back = dict_of_lists_to_list_of_dicts(orders_columnar)
print("dict-of-lists -> list-of-dicts:", converted_back)

# In practice, Pandas does this conversion for you automatically -
# it accepts EITHER shape directly
try:
    import pandas as pd

    df_from_records = pd.DataFrame(orders)                # list of dicts
    df_from_columns = pd.DataFrame(orders_columnar)         # dict of lists
    print("\nPandas accepts either shape directly:")
    print(df_from_records.equals(df_from_columns))          # True - same result
except ImportError:
    print("\n(pandas not installed - it accepts BOTH shapes as DataFrame input)")


"""
---------------------------------------------------------------------
4. DICT OF DICTS: RECORDS KEYED BY ID  ⭐⭐⭐
---------------------------------------------------------------------
When you need FAST lookup by a unique ID (rather than scanning a
list of dicts), keying the outer structure by that ID gives O(1)
access - a huge win over a list-of-dicts linear search.
---------------------------------------------------------------------
"""

print("\n--- Dict of Dicts: Keyed by ID ---")

orders_by_id = {
    "ORD1": {"customer": "Alice", "amount": 100.0, "status": "shipped"},
    "ORD2": {"customer": "Bob", "amount": 250.0, "status": "pending"},
    "ORD3": {"customer": "Alice", "amount": 75.0, "status": "shipped"},
}

print("orders_by_id:", orders_by_id)
print("\ndirect O(1) lookup by ID:", orders_by_id["ORD2"])

# Converting a list of dicts to a dict-of-dicts keyed by a chosen field
def index_by_key(records, key_field):
    return {record[key_field]: {k: v for k, v in record.items() if k != key_field}
            for record in records}

indexed = index_by_key(orders, "order_id")
print("\nindexed by order_id (built from list of dicts):", indexed)


"""
---------------------------------------------------------------------
5. DEEPLY NESTED JSON: THE REAL-WORLD SHAPE  ⭐⭐⭐
---------------------------------------------------------------------
Actual API/JSON responses combine ALL of the above - dicts
containing lists of dicts containing more dicts, arbitrarily deep.
---------------------------------------------------------------------
"""

print("\n--- Deeply Nested JSON (Real-World Shape) ---")

api_response = {
    "status": "success",
    "user": {
        "id": 101,
        "name": "Claude",
        "address": {"city": "San Francisco", "zip": "94107"},
        "orders": [
            {"order_id": "ORD1", "items": [
                {"sku": "SKU100", "qty": 2},
                {"sku": "SKU101", "qty": 1},
            ]},
            {"order_id": "ORD2", "items": [
                {"sku": "SKU102", "qty": 5},
            ]},
        ],
    },
}

print("deep access: api_response['user']['address']['city']:")
print(" ", api_response["user"]["address"]["city"])

print("\ndeep access into a nested list of dicts:")
print(" ", api_response["user"]["orders"][0]["items"][1]["sku"])

# Iterating through all levels
print("\nwalking through every order and every item:")
for order in api_response["user"]["orders"]:
    for item in order["items"]:
        print(f"  order={order['order_id']} sku={item['sku']} qty={item['qty']}")


"""
---------------------------------------------------------------------
6. SAFE ACCESS: AVOIDING KeyError / TypeError ON MISSING DATA  ⭐⭐⭐
---------------------------------------------------------------------
Real API data is often INCONSISTENT - a field might be missing on
some records. Direct chained indexing (`d["a"]["b"]["c"]`) will
crash the ENTIRE pipeline on the first missing key. Use .get()
chains with sensible defaults, or a small helper function.
---------------------------------------------------------------------
"""

print("\n--- Safe Access on Inconsistent/Missing Data ---")

incomplete_response = {"user": {"id": 102, "name": "NoAddressUser"}}

try:
    incomplete_response["user"]["address"]["city"]     # crashes!
except KeyError as e:
    print("Error with direct chained access on missing key:", e)

# Safe chained .get() with defaults at every level
safe_city = incomplete_response.get("user", {}).get("address", {}).get("city", "N/A")
print("safe .get() chain result:", safe_city)

# A small reusable helper for deep, safe access using a path of keys
def safe_get(data, path, default=None):
    """Safely access a nested value given a list of keys/indices."""
    current = data
    for key in path:
        try:
            current = current[key]
        except (KeyError, IndexError, TypeError):
            return default
    return current

result1 = safe_get(api_response, ["user", "address", "city"])
result2 = safe_get(incomplete_response, ["user", "address", "city"], default="N/A")
print("safe_get() on complete data:", result1)
print("safe_get() on incomplete data:", result2)


"""
---------------------------------------------------------------------
7. FLATTENING NESTED JSON INTO TABULAR FORM  ⭐⭐⭐
---------------------------------------------------------------------
Before loading nested JSON into a table/DataFrame/SQL database, it
usually needs to be FLATTENED - nested keys become dotted/prefixed
column names, and any nested LIST of records typically needs its own
separate table (a one-to-many relationship).
---------------------------------------------------------------------
"""

print("\n--- Flattening Nested JSON ---")

def flatten_dict(nested, parent_key="", separator="."):
    """Recursively flattens a nested dict into dotted key names."""
    items = {}
    for key, value in nested.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, separator))
        else:
            items[new_key] = value
    return items

nested_record = {
    "user": {
        "id": 101,
        "name": "Claude",
        "address": {"city": "San Francisco", "zip": "94107"},
    },
    "status": "active",
}

flattened_record = flatten_dict(nested_record)
print("flattened dict (dotted keys):", flattened_record)

# Pandas has a built-in equivalent: json_normalize()
try:
    import pandas as pd
    normalized_df = pd.json_normalize(nested_record)
    print("\npandas.json_normalize() output:")
    print(normalized_df)
except ImportError:
    print("\n(pandas not installed - pd.json_normalize() flattens nested")
    print(" JSON directly into a DataFrame with dotted column names)")


"""
---------------------------------------------------------------------
8. MODIFYING NESTED STRUCTURES: SHARED REFERENCE GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
Because nested lists/dicts are all connected by REFERENCES, copying
the OUTER structure with a shallow copy does NOT protect the inner
structures - mutating a nested record through a "copy" can still
affect the original.
---------------------------------------------------------------------
"""

print("\n--- Shared Reference Gotcha in Nested Structures ---")

original_orders = [{"order_id": "ORD1", "items": ["A", "B"]}]
shallow_copy_orders = original_orders.copy()      # or original_orders[:]

shallow_copy_orders[0]["items"].append("C")        # mutates the SHARED inner list
print("original_orders after mutating the 'copy':", original_orders)   # affected!

import copy
deep_copy_orders = copy.deepcopy(original_orders)
deep_copy_orders[0]["items"].append("D")
print("original_orders after mutating a DEEP copy:", original_orders)   # unaffected


"""
---------------------------------------------------------------------
9. AGGREGATING / GROUPING NESTED DATA  ⭐⭐⭐
---------------------------------------------------------------------
A classic ETL task: group a list of records by some field, and
compute an aggregate (sum, count, average) for each group.
---------------------------------------------------------------------
"""

print("\n--- Aggregating / Grouping Nested Data ---")

from collections import defaultdict

# Group orders by customer, summing their total amount
totals_by_customer = defaultdict(float)
for order in orders:
    totals_by_customer[order["customer"]] += order["amount"]

print("total amount per customer:", dict(totals_by_customer))

# Group full records (not just a sum) by customer
records_by_customer = defaultdict(list)
for order in orders:
    records_by_customer[order["customer"]].append(order)

print("\nall records grouped by customer:")
for customer, customer_orders in records_by_customer.items():
    print(f"  {customer}: {customer_orders}")


"""
---------------------------------------------------------------------
10. SORTING NESTED DATA BY A FIELD  ⭐⭐
---------------------------------------------------------------------
Sorting a list of dicts (or even nested records) by one or more
fields, using `key=` with a lambda.
---------------------------------------------------------------------
"""

print("\n--- Sorting Nested Data ---")

sorted_by_amount = sorted(orders, key=lambda o: o["amount"], reverse=True)
print("sorted by amount, descending:", sorted_by_amount)

# Sorting by MULTIPLE fields - tuple key, sorted lexicographically
sorted_by_status_then_amount = sorted(orders, key=lambda o: (o["status"], -o["amount"]))
print("\nsorted by status, then amount descending within each status:")
for o in sorted_by_status_then_amount:
    print(" ", o)


"""
=====================================================================
QUICK REFERENCE: WHICH SHAPE FOR WHICH NEED
=====================================================================
Need                                   | Best Shape
----------------------------------------|---------------------------
Represent rows/records from an API       | list of dicts
Feed data into pandas.DataFrame()          | either shape works
Fast lookup of ONE record by unique ID       | dict of dicts (keyed)
Column-wise/vectorized processing              | dict of lists
Represent a single deeply nested API response    | nested dict + list combo
Load nested JSON into a relational table           | flatten first
                                                  (dotted keys / separate
                                                  child tables)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - NESTED DATA STRUCTURES
=====================================================================

1. What's the difference between a "list of dicts" and a "dict of
   lists"? Give a real-world example of when an API might return
   each shape.

2. How would you convert a list of dicts into a dict of lists
   (i.e., pivot from row-oriented to column-oriented), and why
   might you need to do this before feeding data into certain
   libraries?

3. Why would you convert a list of dicts into a dict of dicts keyed
   by an ID field? What performance benefit does this give you for
   repeated lookups?

4. Given a deeply nested JSON API response, how would you safely
   access a value several levels deep WITHOUT risking a KeyError or
   TypeError if an intermediate key is missing?

5. What does it mean to "flatten" nested JSON, and why is this
   often a NECESSARY step before loading data into a relational
   database or a flat CSV file?

6. If a nested JSON record contains a LIST of child records (e.g.,
   a user with multiple orders, each with multiple items), how
   would you model this in a relational database - one flat table,
   or multiple related tables? Why?

7. Given `copy1 = original_list_of_dicts.copy()`, why can modifying
   a NESTED list/dict inside `copy1` still affect
   `original_list_of_dicts`? What copying approach avoids this?

8. How would you group a list of order records by "customer" and
   compute the total amount spent by each customer? What data
   structure and Python tool (e.g., `collections.defaultdict`)
   would you use?

9. How would you sort a list of dicts by MULTIPLE fields at once
   (e.g., first by status ascending, then by amount descending
   within each status)?

10. What is `pandas.json_normalize()`, and what problem does it
    solve when working with deeply nested JSON data?

11. If an API sometimes omits certain fields on some records (e.g.,
    not every order has a "discount" field), how would you safely
    extract that field across ALL records without crashing on the
    ones missing it?

12. In a data engineering context, why might a REST API choose to
    return data as a "dict of lists" (columnar) rather than a "list
    of dicts" (row-oriented), especially for large analytical
    payloads?

13. How would you write a general-purpose recursive function to
    flatten an arbitrarily nested dictionary (with dicts nested many
    levels deep) into a single flat dictionary with dotted key
    names?

14. Given a list of dicts representing orders, each containing a
    NESTED list of item dicts, how would you compute the total
    quantity of items across ALL orders using a nested comprehension
    or nested loop?
=====================================================================
"""