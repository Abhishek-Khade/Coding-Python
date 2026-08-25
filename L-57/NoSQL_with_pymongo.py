"""
=====================================================================
NOSQL FROM PYTHON: MONGODB VIA PYMONGO - Complete Notes with
Executable Examples
=====================================================================

MongoDB is a DOCUMENT DATABASE: instead of rows in fixed-schema
tables, it stores COLLECTIONS of independent JSON-like DOCUMENTS
(which pymongo hands you back as plain Python dicts, encoded on the
wire as BSON - Binary JSON). There is no `CREATE TABLE`, no column
list, and no schema enforced by the database itself - any document,
with any set of fields, can live in any collection.

The interview-critical shift is this: a relational database is
NORMALIZED - related data is split across multiple tables and
reassembled with a JOIN at query time, because a table's rows all
share one rigid shape. A document database EMBEDS related data (like
a list of line items, or a set of tags) directly inside one document,
because a document's shape is per-document, not per-collection. You
trade "one flexible, self-contained record" for "no cross-table
JOINs and no guaranteed shape" - and knowing WHEN that trade is worth
it is the single most important thing to be able to argue in an
interview.

This file uses the real pymongo API throughout (`MongoClient`,
`insert_one`, `find`, `update_one` with `$set`, `aggregate`, ...).
There is no MongoDB server running in this sandbox, so the file
attempts one real connection, catches the resulting timeout exactly
the way production retry/fallback code would, and then re-runs every
CRUD and aggregation example against a small hand-rolled in-memory
stand-in that implements the identical method names - so every line
of Mongo syntax below is real and transfers directly to a live
cluster.
=====================================================================
"""

print("--- Overview ---")
print("SQL: fixed-schema TABLES of ROWS, joined together at query time.")
print("MongoDB: a COLLECTION of independent DOCUMENTS (Python dicts),")
print("each free to have its own fields, with related data embedded")
print("directly inside one document instead of split across tables.")


"""
---------------------------------------------------------------------
1. THE CORE MODEL SHIFT: TABLES & ROWS vs COLLECTIONS & DOCUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
A relational TABLE has a schema fixed at CREATE TABLE time: every row
has the same columns, and adding a new column requires an ALTER
TABLE that touches every existing row (usually backfilling NULLs).

A MongoDB COLLECTION has no such constraint. It's just a named
bucket of documents. Two documents in the SAME collection can have
completely different fields - there's no migration step to add a
field that only some documents need.
---------------------------------------------------------------------
"""

print("\n--- The Core Model Shift: Tables/Rows vs Collections/Documents ---")

# Two "rows" that would be awkward in one SQL table (a book has no
# battery, a laptop has no page count - a relational table would need
# both columns, NULL on whichever doesn't apply to a given product).
product_book = {
    "sku": "BOOK-001",
    "category": "book",
    "title": "Designing Data-Intensive Applications",
    "author": "Martin Kleppmann",
    "page_count": 616,
}
product_laptop = {
    "sku": "LAPTOP-047",
    "category": "electronics",
    "title": "14-inch Developer Laptop",
    "battery_life_hours": 11,
    "ports": ["USB-C", "HDMI", "headphone"],   # an ARRAY, natively, no join table
}

catalog = [product_book, product_laptop]   # standing in for one MongoDB collection
for doc in catalog:
    print(f"  {doc['sku']}: fields = {sorted(doc.keys())}")

print("\nBoth documents live in the SAME collection with DIFFERENT")
print("shapes - no ALTER TABLE, no NULL columns, no shared schema file.")


"""
---------------------------------------------------------------------
2. SCHEMA DESIGN SHOWDOWN: NORMALIZED SQL JOIN vs ONE DENORMALIZED
   MONGODB DOCUMENT  ⭐⭐⭐
---------------------------------------------------------------------
This is the single most important conceptual interview point on this
topic: how do you model an ORDER that has multiple LINE ITEMS?

In SQL you normalize: an `orders` table plus a separate
`order_items` table with a foreign key back to `orders`, and you
JOIN them to reconstruct one order. This avoids repeating
order-level data (customer, date) on every line item row.

In MongoDB you typically DENORMALIZE: the line items are embedded as
an ARRAY of sub-documents directly inside the order document, because
line items are always read and written together WITH their parent
order, and never queried independently across orders. One
`find_one()` returns the whole order, fully assembled, with no JOIN.
---------------------------------------------------------------------
"""

print("\n--- Schema Showdown: SQL Join vs One Mongo Document ---")

sql_normalized_schema = """
-- SQL: two tables, related by a foreign key
CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    order_date    DATE NOT NULL
);

CREATE TABLE order_items (
    item_id       INTEGER PRIMARY KEY,
    order_id      INTEGER REFERENCES orders(order_id),
    product_name  TEXT NOT NULL,
    quantity      INTEGER NOT NULL,
    unit_price    NUMERIC(10, 2) NOT NULL
);

-- reassembling ONE order requires a JOIN across both tables:
SELECT o.order_id, o.customer_name, i.product_name, i.quantity, i.unit_price
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
WHERE o.order_id = 1001;
"""
print(sql_normalized_schema)

mongo_denormalized_document = {
    "order_id": 1001,
    "customer_name": "Priya Shah",
    "order_date": "2026-08-20",
    "line_items": [                                        # embedded array - no join table
        {"product_name": "Wireless Mouse", "quantity": 2, "unit_price": 19.99},
        {"product_name": "USB-C Cable", "quantity": 1, "unit_price": 9.99},
    ],
}
print("MongoDB: one document, no join needed:")
print(" ", mongo_denormalized_document)

# Note: real systems often store money as integer cents or
# bson.Decimal128 instead of float, to avoid binary floating-point
# rounding - floats are used here only to keep the demo readable.
order_total = sum(item["quantity"] * item["unit_price"] for item in mongo_denormalized_document["line_items"])
print(f"\nComputing the order total needs NO join - just iterate the")
print(f"embedded array in Python: total = ${order_total:.2f}")
print("\nTrade-off: SQL avoids repeating order-level data per line item")
print("and lets you query order_items independently (e.g. 'top-selling")
print("products across ALL orders') with a simple GROUP BY. Mongo avoids")
print("the join entirely for the extremely common 'load one full order'")
print("access pattern, at the cost of harder cross-order item queries.")


"""
---------------------------------------------------------------------
3. CONNECTING WITH PYMONGO: MongoClient, DATABASE, COLLECTION  ⭐⭐⭐
---------------------------------------------------------------------
`MongoClient(...)` is LAZY - constructing it does not, by itself,
open a connection or raise an error. The client only actually tries
to reach a server (a step called "server selection") on the FIRST
operation you run against it, and that's when a timeout error would
surface. `client[db_name]` and `db[collection_name]` are lazy too -
neither the database nor the collection needs to exist beforehand;
MongoDB creates both automatically the first time you write to them.
---------------------------------------------------------------------
"""

print("\n--- Connecting with pymongo ---")

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson import ObjectId

MONGO_URI = "mongodb://localhost:27017"

try:
    # This is exactly how you'd connect to a real deployment - a local
    # server, a replica set, or an Atlas cluster - just change the URI.
    # A SHORT serverSelectionTimeoutMS keeps a doomed connection attempt
    # from hanging a script (the real-world default is 30 seconds).
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=800)
    db = client["ecommerce"]              # created lazily - no CREATE DATABASE
    collection = db["orders"]             # created lazily - no CREATE TABLE
    client.admin.command("ping")          # forces the actual round trip now
    print("Connected to a real MongoDB server.")
    using_real_mongo = True
except ServerSelectionTimeoutError as e:
    print("Could not reach a real MongoDB server:", e)
    print("In production, against a real MongoDB deployment, this script")
    print("would connect exactly as coded above, and every operation below")
    print("would run against real, persisted BSON documents on that server.")
    print("No MongoDB server is running in this sandbox, so we now simulate")
    print("the same operations below against an in-memory Python stand-in")
    print("that exposes the identical method names pymongo uses.")
    using_real_mongo = False


# ---- In-memory stand-in for a pymongo Collection (sandbox-only) ----
# This class is NOT part of the pymongo API - it exists only so this
# file still produces real, executed output without a live server.
# Every method below mirrors the REAL pymongo Collection method it
# stands in for, argument-for-argument.

class _InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class _InsertManyResult:
    def __init__(self, inserted_ids):
        self.inserted_ids = inserted_ids

class _UpdateResult:
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count

class _DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _get_field(doc, dotted_key):
    """Reads doc['a']['b'] via the dotted key 'a.b', Mongo-style."""
    value = doc
    for part in dotted_key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def _matches(doc, query):
    """A tiny subset of MongoDB's query-matching, just enough for this file."""
    for key, condition in query.items():
        actual = _get_field(doc, key)
        if isinstance(condition, dict) and any(k.startswith("$") for k in condition):
            for op, expected in condition.items():
                if op == "$gt" and not (actual is not None and actual > expected):
                    return False
                if op == "$gte" and not (actual is not None and actual >= expected):
                    return False
                if op == "$lt" and not (actual is not None and actual < expected):
                    return False
                if op == "$lte" and not (actual is not None and actual <= expected):
                    return False
                if op == "$ne" and actual == expected:
                    return False
                if op == "$in" and actual not in expected:
                    return False
        else:
            if actual != condition:
                return False
    return True


class InMemoryCollection:
    """Dict-based stand-in for a pymongo Collection - same method names."""

    def __init__(self, name):
        self.name = name
        self._docs = []

    def insert_one(self, document):
        doc = dict(document)
        doc.setdefault("_id", ObjectId())        # real Mongo auto-generates this too
        self._docs.append(doc)
        return _InsertOneResult(doc["_id"])

    def insert_many(self, documents):
        ids = [self.insert_one(d).inserted_id for d in documents]
        return _InsertManyResult(ids)

    def find_one(self, query=None):
        for doc in self._docs:
            if _matches(doc, query or {}):
                return doc
        return None

    def find(self, query=None):
        return [doc for doc in self._docs if _matches(doc, query or {})]

    def count_documents(self, query=None):
        return len(self.find(query or {}))

    def update_one(self, query, update):
        for doc in self._docs:
            if _matches(doc, query):
                self._apply_update(doc, update)
                return _UpdateResult(matched_count=1, modified_count=1)
        return _UpdateResult(matched_count=0, modified_count=0)

    def update_many(self, query, update):
        matched = 0
        for doc in self._docs:
            if _matches(doc, query):
                self._apply_update(doc, update)
                matched += 1
        return _UpdateResult(matched_count=matched, modified_count=matched)

    def _apply_update(self, doc, update):
        has_operators = any(k.startswith("$") for k in update)
        if not has_operators:
            # REAL MongoDB behavior: an update document with no $operators
            # is treated as a full REPLACEMENT of the document (like
            # replace_one) - every existing field not in `update` is
            # dropped, except _id. See section 6 below.
            preserved_id = doc["_id"]
            doc.clear()
            doc.update(update)
            doc["_id"] = preserved_id
            return
        for op, changes in update.items():
            if op == "$set":
                for k, v in changes.items():
                    doc[k] = v
            elif op == "$inc":
                for k, v in changes.items():
                    doc[k] = doc.get(k, 0) + v
            elif op == "$unset":
                for k in changes:
                    doc.pop(k, None)
            elif op == "$push":
                for k, v in changes.items():
                    doc.setdefault(k, []).append(v)

    def delete_one(self, query):
        for i, doc in enumerate(self._docs):
            if _matches(doc, query):
                del self._docs[i]
                return _DeleteResult(deleted_count=1)
        return _DeleteResult(deleted_count=0)

    def delete_many(self, query):
        keep, removed = [], 0
        for doc in self._docs:
            if _matches(doc, query):
                removed += 1
            else:
                keep.append(doc)
        self._docs = keep
        return _DeleteResult(deleted_count=removed)

    def aggregate(self, pipeline):
        docs = list(self._docs)
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if _matches(d, stage["$match"])]
            elif "$group" in stage:
                docs = self._group(docs, stage["$group"])
        return docs

    def _group(self, docs, spec):
        id_expr = spec["_id"]
        groups = {}
        for doc in docs:
            key = _get_field(doc, id_expr[1:]) if isinstance(id_expr, str) and id_expr.startswith("$") else id_expr
            groups.setdefault(key, []).append(doc)
        results = []
        for key, group_docs in groups.items():
            row = {"_id": key}
            for field, accumulator in spec.items():
                if field == "_id":
                    continue
                (op, expr), = accumulator.items()
                if op == "$sum":
                    row[field] = len(group_docs) if expr == 1 else sum(_get_field(d, expr[1:]) for d in group_docs)
                elif op == "$avg":
                    vals = [_get_field(d, expr[1:]) for d in group_docs]
                    row[field] = sum(vals) / len(vals)
            results.append(row)
        return results


if not using_real_mongo:
    collection = InMemoryCollection("orders")

print("`collection` is now a", type(collection).__name__, "- same method calls either way.")


"""
---------------------------------------------------------------------
4. INSERTING DOCUMENTS: insert_one() and insert_many()  ⭐⭐
---------------------------------------------------------------------
`insert_one()` takes a single dict and returns an object exposing
`.inserted_id` (an ObjectId, MongoDB's default primary key type).
`insert_many()` takes a list of dicts and returns `.inserted_ids`.
Neither call needs the collection - or its schema - to exist first.
---------------------------------------------------------------------
"""

print("\n--- Inserting Documents ---")

result = collection.insert_one({
    "order_id": 1001,
    "customer_name": "Priya Shah",
    "region": "west",
    "status": "shipped",
    "total": order_total,
    "line_items": mongo_denormalized_document["line_items"],
})
print("insert_one() ->", result.inserted_id)

many_result = collection.insert_many([
    {"order_id": 1002, "customer_name": "Diego Alvarez", "region": "east",
     "status": "shipped", "total": 84.50,
     "line_items": [{"product_name": "Keyboard", "quantity": 1, "unit_price": 84.50}]},
    {"order_id": 1003, "customer_name": "Wen Zhao", "region": "west",
     "status": "processing", "total": 240.00,
     "line_items": [{"product_name": "Monitor", "quantity": 1, "unit_price": 240.00}]},
    {"order_id": 1004, "customer_name": "Amara Obi", "region": "east",
     "status": "shipped", "total": 61.98,
     "line_items": [{"product_name": "USB-C Cable", "quantity": 2, "unit_price": 30.99}]},
])
print("insert_many() ->", len(many_result.inserted_ids), "documents inserted")
print("total documents in collection now:", collection.count_documents({}))


"""
---------------------------------------------------------------------
5. QUERYING: find_one(), find(), AND QUERY OPERATORS  ⭐⭐⭐
---------------------------------------------------------------------
`find_one()` returns a single dict (or None). `find()` returns a
cursor you iterate (a list here) of every matching document. Filters
are plain dicts; comparisons beyond equality use MongoDB's
"$operator" keys, e.g. `{"total": {"$gt": 100}}` for "total > 100" -
these compose the same way a SQL WHERE clause's comparisons do.
---------------------------------------------------------------------
"""

print("\n--- Querying: find_one() and find() with operators ---")

one_order = collection.find_one({"order_id": 1002})
print("find_one({'order_id': 1002}) ->", one_order["customer_name"], "-", one_order["status"])

big_orders = collection.find({"total": {"$gt": 100}})            # SQL: WHERE total > 100
print("\nfind({'total': {'$gt': 100}}):")
for doc in big_orders:
    print(f"  order {doc['order_id']}: ${doc['total']:.2f}")

shipped_west = collection.find({"status": "shipped", "region": "west"})   # SQL: WHERE status=... AND region=...
print("\nfind({'status': 'shipped', 'region': 'west'}) (implicit AND across keys):")
for doc in shipped_west:
    print(f"  order {doc['order_id']}: {doc['customer_name']}")


"""
---------------------------------------------------------------------
6. UPDATING DOCUMENTS: update_one(), update_many(), AND THE $set
   GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
This is a genuinely common Mongo interview trap: `update_one(filter,
update)` treats `update` as a FULL REPLACEMENT document whenever it
has NO keys starting with "$" - it does NOT merge fields in. Forget
`$set` and you silently wipe out every other field on that document.
Wrapping the change in `{"$set": {...}}` updates ONLY the named
field(s) and leaves everything else untouched.
---------------------------------------------------------------------
"""

print("\n--- Updating: the $set gotcha (buggy vs fixed) ---")

before = dict(collection.find_one({"order_id": 1003}))
target_id = before["_id"]      # save the _id - it's the only field the buggy update WON'T erase
print("order 1003 BEFORE any update:", sorted(before.keys()))

# BUGGY: no "$" operator, so pymongo/MongoDB treats this as a full
# replacement document - every field except _id is dropped! Note this
# even wipes out "order_id" itself, so we must look the document back
# up by "_id" afterward - a filter on "order_id" would now match nothing.
collection.update_one({"order_id": 1003}, {"status": "cancelled"})
after_buggy = collection.find_one({"_id": target_id})
print("BUGGY update_one(filter, {'status': 'cancelled'}) - fields now:", sorted(after_buggy.keys()))
print("  -> customer_name, total, line_items, and order_id itself are ALL GONE.")

# Restore the document, then do it the FIXED way.
collection.update_one({"_id": target_id}, {"$set": before})
collection.update_one({"_id": target_id}, {"$set": {"status": "cancelled"}})
after_fixed = collection.find_one({"_id": target_id})
print("\nFIXED update_one(filter, {'$set': {'status': 'cancelled'}}) - fields now:", sorted(after_fixed.keys()))
print("  status:", after_fixed["status"], "| customer_name still present:", after_fixed["customer_name"])

update_many_result = collection.update_many({"region": "east"}, {"$set": {"priority_shipping": True}})
print(f"\nupdate_many({{'region': 'east'}}, {{'$set': ...}}) -> matched {update_many_result.matched_count} document(s)")


"""
---------------------------------------------------------------------
7. DELETING DOCUMENTS: delete_one() and delete_many()  ⭐⭐
---------------------------------------------------------------------
Same filter-dict shape as find() and update - `delete_one()` removes
the FIRST match, `delete_many()` removes EVERY match. Both return an
object with `.deleted_count`, mirroring an SQL DELETE's row count.
---------------------------------------------------------------------
"""

print("\n--- Deleting Documents ---")

before_count = collection.count_documents({})
delete_result = collection.delete_one({"order_id": 1002})
print(f"delete_one({{'order_id': 1002}}) -> deleted_count={delete_result.deleted_count}")
print(f"collection size: {before_count} -> {collection.count_documents({})}")

delete_many_result = collection.delete_many({"status": "processing"})
print(f"delete_many({{'status': 'processing'}}) -> deleted_count={delete_many_result.deleted_count}")
print("remaining documents:", [d["order_id"] for d in collection.find({})])


"""
---------------------------------------------------------------------
8. SCHEMA FLEXIBILITY IN PRACTICE: EVOLVING FIELDS WITHOUT A
   MIGRATION  ⭐⭐
---------------------------------------------------------------------
A common real scenario: product decides orders should now optionally
carry a `gift_message`. In SQL that's an ALTER TABLE (and a NULL on
every pre-existing row). In MongoDB you just start writing the new
field on NEW documents - old documents simply don't have it, and
code that reads it defensively (`doc.get(...)`) never breaks.
---------------------------------------------------------------------
"""

print("\n--- Schema Flexibility: Adding a Field With No Migration ---")

collection.insert_one({
    "order_id": 1005, "customer_name": "Lena Fischer", "region": "west",
    "status": "shipped", "total": 33.00,
    "line_items": [{"product_name": "Notebook", "quantity": 3, "unit_price": 11.00}],
    "gift_message": "Happy graduation!",     # a field NO earlier document has
})
for doc in collection.find({}):
    print(f"  order {doc['order_id']}: gift_message = {doc.get('gift_message', '<none>')}")
print("\nNo ALTER TABLE, no backfill - older documents just lack the key,")
print("and defensive reads with .get(..., default) handle both shapes.")


"""
---------------------------------------------------------------------
9. AGGREGATION PIPELINE: $match + $group  ⭐⭐⭐
---------------------------------------------------------------------
The aggregation pipeline is Mongo's answer to SQL's WHERE + GROUP BY:
a LIST of stages, each transforming the documents flowing through it.
`{"$match": {...}}` filters documents (like WHERE); `{"$group":
{"_id": "$field", "total": {"$sum": "$other_field"}}}` buckets by a
field and reduces each bucket (like GROUP BY + SUM/AVG/COUNT). This
is conceptually identical to the pandas `df.groupby("region")["total"]
.sum()` pattern from L-44/GroupBy_Merge_Join_Pivot.py earlier in this
repo - same "filter, then bucket, then reduce" shape, different API.
---------------------------------------------------------------------
"""

print("\n--- Aggregation Pipeline: $match + $group ---")

pipeline = [
    {"$match": {"status": "shipped"}},                     # SQL: WHERE status = 'shipped'
    {"$group": {"_id": "$region",                          # SQL: GROUP BY region
                "order_count": {"$sum": 1},                # SQL: COUNT(*)
                "total_revenue": {"$sum": "$total"},        # SQL: SUM(total)
                "avg_order_value": {"$avg": "$total"}}},    # SQL: AVG(total)
]
for row in collection.aggregate(pipeline):
    print(f"  region={row['_id']!r}: orders={row['order_count']}, "
          f"revenue=${row['total_revenue']:.2f}, avg=${row['avg_order_value']:.2f}")

print("\nThe pandas equivalent, once orders are loaded into a DataFrame:")
print("  df[df.status == 'shipped'].groupby('region')['total'].agg(['count', 'sum', 'mean'])")


"""
---------------------------------------------------------------------
10. WHEN MONGODB WINS vs WHEN A RELATIONAL DATABASE WINS  ⭐⭐⭐
---------------------------------------------------------------------
Neither database is "better" - the right choice depends on the
workload's SHAPE and its CONSISTENCY requirements. Interviewers care
far more about you reasoning through the trade-off than about you
picking a "winner".

MongoDB / document store tends to win when:
    - the schema is genuinely evolving or per-record variable (event
      payloads, feature flags, user-generated form data)
    - write throughput is high and records are semi-structured
      (application logs, IoT/sensor events, clickstreams)
    - the dominant access pattern reads/writes ONE aggregate (a full
      order, a full user profile) as a unit, rarely joined to others
    - you need to shard/scale writes horizontally across many nodes

A relational database tends to win when:
    - you need real ACID transactions across MULTIPLE related
      entities (e.g., debit one account and credit another, atomically)
    - the data has many-to-many relationships queried from either
      side, with genuine multi-table JOINs (reporting, BI, finance)
    - you want the database itself to ENFORCE a strict schema and
      referential integrity (foreign keys), not just application code
    - the workload is read-heavy with complex, ad-hoc analytical
      queries across normalized tables
---------------------------------------------------------------------
"""

print("\n--- Decision Guide: MongoDB vs a Relational Database ---")

def recommend_database(needs_multi_entity_acid, schema_is_evolving, is_high_volume_semistructured_writes, needs_complex_joins):
    """A simplified, interview-style decision function - not a real rulebook."""
    if needs_multi_entity_acid or needs_complex_joins:
        return "relational (needs cross-entity transactions and/or multi-table joins)"
    if schema_is_evolving or is_high_volume_semistructured_writes:
        return "MongoDB (flexible schema and/or high-volume semi-structured writes)"
    return "either could work - pick based on team familiarity and existing infra"

scenarios = [
    ("Payments ledger: debit + credit must succeed or fail together",
     recommend_database(needs_multi_entity_acid=True, schema_is_evolving=False,
                         is_high_volume_semistructured_writes=False, needs_complex_joins=False)),
    ("Clickstream/event logging with fields that change release to release",
     recommend_database(needs_multi_entity_acid=False, schema_is_evolving=True,
                         is_high_volume_semistructured_writes=True, needs_complex_joins=False)),
    ("BI reporting warehouse joining customers, orders, and products",
     recommend_database(needs_multi_entity_acid=False, schema_is_evolving=False,
                         is_high_volume_semistructured_writes=False, needs_complex_joins=True)),
]
for description, recommendation in scenarios:
    print(f"  scenario: {description}\n    -> {recommendation}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
SQL                              -> MongoDB
------------------------------------------------------------------
TABLE (fixed schema)             -> COLLECTION (schema-less bucket)
ROW                              -> DOCUMENT (a dict/BSON object)
COLUMN                           -> FIELD (per-document, not fixed)
PRIMARY KEY                      -> "_id" (ObjectId by default)
JOIN across tables                -> embedded array/sub-document
CREATE TABLE / ALTER TABLE        -> nothing - just write a new shape

Connecting:
    MongoClient(uri, serverSelectionTimeoutMS=...) -> client (lazy!)
    db = client["dbname"]; collection = db["collname"]  (both lazy)

CRUD:
    insert_one(doc) / insert_many([docs])   -> .inserted_id(s)
    find_one(filter) / find(filter)          -> dict / cursor of dicts
    update_one(filter, {"$set": {...}})       -> merges fields in
    update_one(filter, {...no $ operator...})  -> REPLACES whole doc!
    delete_one(filter) / delete_many(filter)    -> .deleted_count

Query operators: $gt $gte $lt $lte $ne $in $nin  (compose like WHERE)
Aggregation:     $match ~ WHERE   ;   $group ~ GROUP BY + SUM/AVG/COUNT

Choose MongoDB    -> evolving schema, high-volume semi-structured
                     writes, single-aggregate access pattern, sharding
Choose relational -> multi-entity ACID transactions, complex joins,
                     strict schema/referential integrity
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - NOSQL / MONGODB VIA PYMONGO
=====================================================================

1. What is the fundamental structural difference between a SQL table
   and a MongoDB collection - specifically, what does "schema-less"
   actually mean in practice for two documents in the same collection?

2. Using the order/line-items example in this file, explain how you
   would model a one-to-many relationship (one order, many line
   items) in a normalized SQL schema versus as a single MongoDB
   document. What do you gain and lose by embedding the line items?

3. Why might you choose to EMBED related data inside one document
   instead of REFERENCING it from a separate collection (Mongo's
   equivalent of a foreign key)? When would referencing be better?

4. Why does `MongoClient(...)` not raise an error immediately if no
   server is reachable? At what point does the connection actually
   get attempted, and what exception does pymongo raise if it fails?

5. What does `db = client["mydb"]` do if the database "mydb" doesn't
   exist yet? Compare this to `CREATE DATABASE` in SQL.

6. Walk through what happens if you call
   `collection.update_one({"order_id": 1003}, {"status": "cancelled"})`
   without wrapping the update in `$set`. Why does this happen, and
   how is it different from `collection.update_one({"order_id": 1003},
   {"$set": {"status": "cancelled"}})`?

7. Write a pymongo filter dict to find all orders with a total
   greater than 100 AND a status of "shipped".

8. What is the difference between `find_one()` and `find()` in terms
   of return type, and how would you iterate the result of `find()`?

9. Explain a MongoDB aggregation pipeline with `$match` followed by
   `$group` and how it maps onto a SQL `WHERE` clause followed by a
   `GROUP BY` with aggregate functions like `SUM`/`AVG`/`COUNT`.

10. What is `_id` in a MongoDB document, what type is it by default,
    and can you supply your own value for it on insert?

11. Give a concrete data engineering scenario where MongoDB (or a
    document store generally) would be a BETTER fit than a relational
    database, and one where a relational database would clearly win.
    Justify both with the actual access pattern, not just a preference.

12. Why can MongoDB scale write throughput horizontally (sharding)
    more straightforwardly than many traditional relational setups,
    and what do you typically give up to get that scalability?

13. If your application needs to atomically update two DIFFERENT
    documents in two different collections together (e.g., debit one
    account's balance and credit another's), why does that push you
    toward a relational database with multi-statement ACID
    transactions rather than MongoDB's per-document guarantees?

14. How would you handle a field that only some documents in a
    collection have, when reading them back in Python (i.e., how do
    you avoid a `KeyError`)?

15. Describe how you'd migrate an evolving MongoDB document shape
    over time (e.g., renaming a field, or adding a required new one)
    without a schema migration tool, and what risks that introduces
    compared to a SQL `ALTER TABLE`.
=====================================================================
"""
