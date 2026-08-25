"""
=====================================================================
CLOUD SDKS - boto3 / AWS S3 (with brief GCS + Azure Blob equivalents)
=====================================================================

Every major cloud provides an "object storage" service (S3 on AWS,
Cloud Storage on GCP, Blob Storage on Azure) - a giant flat key/value
store for BYTES, addressed by a BUCKET (or "container") name plus a
STRING KEY (or "blob name"). Data engineers touch this constantly: it
is almost always the landing zone/data lake underneath a warehouse
(raw files -> S3 -> Spark/Snowflake/Redshift COPY).

`boto3` is AWS's official Python SDK. It exposes TWO parallel APIs for
the same service:
    - `boto3.client('s3')`   -> low-level, near 1:1 with the raw AWS
                                 REST API. Every call maps to one HTTP
                                 request; arguments are exactly the
                                 API's parameter names (Bucket, Key,
                                 Body, ...). This is what you reach for
                                 when you need precise control or a
                                 method the resource API hasn't wrapped.
    - `boto3.resource('s3')` -> higher-level, object-oriented. You get
                                 Python objects (`Bucket`, `Object`)
                                 with methods like `.upload_file()` and
                                 `.download_file()` - more Pythonic,
                                 slightly more "magic", built ON TOP of
                                 the same client underneath.

Neither `boto3.client(...)` nor `boto3.resource(...)` talks to the
network by itself - they just build a configured object. The network
call happens the moment you invoke a method like `.list_buckets()` or
`.get_object()`. This sandbox has no real AWS bucket to talk to, so
every section below first shows the REAL boto3 call (the exact syntax
you'd write in production), wrapped in `try/except` against the
specific exceptions `botocore` raises when there's no usable
connection or credentials - then falls back to running the identical
operation against a small hand-rolled in-memory mock that exposes the
SAME method names, so you still see real, live, correct output.
=====================================================================
"""

import io
import os
import tempfile
import time

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

print("--- Overview ---")
print("boto3 = AWS's SDK. client('s3') is low-level/raw-API-shaped;")
print("resource('s3') is higher-level/object-oriented. Both end up")
print("issuing the same underlying HTTP calls to S3.")

# A short-timeout, zero-retry config used for every REAL boto3 call
# attempted in this file - so a call with no valid credentials/network
# fails in well under a second instead of retrying for a minute.
FAST_FAIL_CONFIG = Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 0})

# The specific exceptions a real boto3 call can raise when there's no
# usable AWS access in an environment like this sandbox: no
# credentials found at all, the network/endpoint unreachable, or a
# real error response FROM AWS (e.g. an invalid/placeholder access
# key). Catching this trio (plus a final broad Exception) is the
# pattern used throughout this file.
AWS_UNAVAILABLE_ERRORS = (ClientError, BotoCoreError, Exception)


"""
---------------------------------------------------------------------
1. CLIENT vs RESOURCE: THE SAME OPERATION, TWO SHAPES  ⭐⭐⭐
---------------------------------------------------------------------
"list all my buckets" is the simplest possible S3 call - a great way
to see the two APIs side by side before anything else gets involved.
---------------------------------------------------------------------
"""

print("\n--- Client vs Resource: Listing Buckets ---")

try:
    # LOW-LEVEL CLIENT: returns a raw dict shaped exactly like the AWS
    # REST response - you dig into ['Buckets'][i]['Name'] yourself.
    client = boto3.client("s3", region_name="us-east-1", config=FAST_FAIL_CONFIG)
    response = client.list_buckets()
    bucket_names = [b["Name"] for b in response["Buckets"]]
    print("client.list_buckets() ->", bucket_names)
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"client.list_buckets() failed ({type(e).__name__}: {e})")
    print("  -> would call AWS like this in production; simulating below.")

try:
    # HIGHER-LEVEL RESOURCE: returns an iterable of Bucket OBJECTS -
    # each with attributes/methods, not raw dict keys.
    resource = boto3.resource("s3", region_name="us-east-1", config=FAST_FAIL_CONFIG)
    bucket_names = [bucket.name for bucket in resource.buckets.all()]
    print("resource.buckets.all() ->", bucket_names)
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"resource.buckets.all() failed ({type(e).__name__}: {e})")
    print("  -> would call AWS like this in production; simulating below.")

# Simulated fallback for BOTH APIs - same information, same two shapes:
simulated_list_buckets_response = {"Buckets": [{"Name": "de-raw-lake"}, {"Name": "de-curated"}]}
print("simulated client-style result:", [b["Name"] for b in simulated_list_buckets_response["Buckets"]])
print("simulated resource-style result: same names, as Bucket objects with .name")


"""
---------------------------------------------------------------------
2. A MOCK S3 CLIENT: SAME METHOD NAMES, IN-MEMORY  ⭐⭐
---------------------------------------------------------------------
Module 13 territory (mocking external calls in tests): rather than
keep hand-writing "simulated" dicts, build ONE small stand-in object
that exposes the exact method names/signatures real boto3 clients
use - put_object, get_object, list_objects_v2, list_buckets,
upload_file, download_file, generate_presigned_url. Every remaining
section calls THIS object with the real AWS argument names, so the
calling code is identical to what you'd write against a live bucket.
---------------------------------------------------------------------
"""

print("\n--- Building a Mock S3 Client ---")


class MockS3Client:
    """In-memory stand-in for boto3.client('s3'). Buckets are dicts of
    key -> bytes; nothing ever touches a network or a disk."""

    def __init__(self):
        self._buckets = {}  # bucket_name -> {key: bytes}

    def create_bucket(self, Bucket):
        self._buckets.setdefault(Bucket, {})
        return {"Location": f"/{Bucket}"}

    def _bucket(self, name):
        if name not in self._buckets:
            # Same exception class AND shape a real boto3 call raises -
            # see Section 7 for why that structure matters.
            raise ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                "ListObjectsV2",
            )
        return self._buckets[name]

    def put_object(self, Bucket, Key, Body):
        data = Body if isinstance(Body, bytes) else Body.encode("utf-8")
        self._bucket(Bucket)[Key] = data
        return {"ETag": f'"{abs(hash(data)):x}"'}

    def get_object(self, Bucket, Key):
        bucket = self._bucket(Bucket)
        if Key not in bucket:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "GetObject",
            )
        return {"Body": io.BytesIO(bucket[Key])}

    def upload_file(self, Filename, Bucket, Key):
        with open(Filename, "rb") as f:
            self.put_object(Bucket=Bucket, Key=Key, Body=f.read())

    def download_file(self, Bucket, Key, Filename):
        data = self.get_object(Bucket=Bucket, Key=Key)["Body"].read()
        with open(Filename, "wb") as f:
            f.write(data)

    def list_objects_v2(self, Bucket, Prefix="", MaxKeys=1000, ContinuationToken=None):
        matching = sorted(k for k in self._bucket(Bucket) if k.startswith(Prefix))
        start = int(ContinuationToken) if ContinuationToken else 0
        page = matching[start : start + MaxKeys]
        result = {
            "Contents": [{"Key": k, "Size": len(self._buckets[Bucket][k])} for k in page],
            "KeyCount": len(page),
        }
        next_start = start + MaxKeys
        result["IsTruncated"] = next_start < len(matching)
        if result["IsTruncated"]:
            result["NextContinuationToken"] = str(next_start)
        return result

    def list_buckets(self):
        return {"Buckets": [{"Name": name} for name in self._buckets]}

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn=3600):
        expires_at = int(time.time()) + ExpiresIn
        return f"https://{Params['Bucket']}.s3.amazonaws.com/{Params['Key']}?X-Mock-Expires={expires_at}"


s3 = MockS3Client()
s3.create_bucket(Bucket="de-raw-lake")
print("mock 's3' client ready, methods:",
      [m for m in dir(s3) if not m.startswith("_")])


"""
---------------------------------------------------------------------
3. UPLOADING & DOWNLOADING OBJECTS  ⭐⭐⭐
---------------------------------------------------------------------
Two ways to WRITE: `put_object` (you already have the bytes in
memory) or `upload_file` (you have a local file path and want boto3
to handle the read + any multipart-upload chunking for you). Two
matching ways to READ: `get_object` (returns a stream you read into
memory) or `download_file` (writes straight to a local path).
---------------------------------------------------------------------
"""

print("\n--- Uploading & Downloading Objects ---")

# put_object: write bytes we already have in memory
s3.put_object(Bucket="de-raw-lake", Key="notes/hello.txt", Body=b"hello from put_object")
fetched = s3.get_object(Bucket="de-raw-lake", Key="notes/hello.txt")["Body"].read()
print("put_object -> get_object round trip:", fetched)

# upload_file / download_file: round-trip through REAL local files, to
# prove the bytes survive the trip through the (mock) object store.
tmp_dir = tempfile.mkdtemp(prefix="s3_demo_")
source_path = os.path.join(tmp_dir, "report.csv")
downloaded_path = os.path.join(tmp_dir, "report_downloaded.csv")

with open(source_path, "w") as f:
    f.write("order_id,amount\n1,19.99\n2,42.50\n")

s3.upload_file(Filename=source_path, Bucket="de-raw-lake", Key="exports/report.csv")
s3.download_file(Bucket="de-raw-lake", Key="exports/report.csv", Filename=downloaded_path)

with open(source_path, "rb") as f:
    original_bytes = f.read()
with open(downloaded_path, "rb") as f:
    downloaded_bytes = f.read()

print("uploaded from:", source_path)
print("downloaded to:", downloaded_path, "(a different filename!)")
print("bytes identical after the S3 round trip:", original_bytes == downloaded_bytes)

# Clean up the local temp files - the demonstration only needed them
# briefly, mirroring how a real ETL job usually cleans its scratch dir.
os.remove(source_path)
os.remove(downloaded_path)
os.rmdir(tmp_dir)


"""
---------------------------------------------------------------------
4. LISTING BY PREFIX ("FOLDERS") AND PAGINATING  ⭐⭐⭐
---------------------------------------------------------------------
S3 has NO real directories - a key like "raw/orders/date=2026-08-24/
part-0003.csv" is just one long string. Tools display a "folder" view
by grouping on '/', but under the hood `list_objects_v2(Prefix=...)`
is the ENTIRE mechanism - this is exactly how a date-partitioned ETL
job discovers "every file for this partition".

A bucket can hold far more keys than one `list_objects_v2` call
returns (capped by `MaxKeys`, default 1000). Production code uses a
`Paginator` to walk every page automatically instead of hand-tracking
tokens:

    paginator = client.get_paginator("list_objects_v2")
    all_keys = []
    for page in paginator.paginate(Bucket="de-raw-lake", Prefix="raw/orders/"):
        all_keys.extend(obj["Key"] for obj in page.get("Contents", []))

Our mock doesn't implement `get_paginator`, so below we drive the same
`ContinuationToken` loop the Paginator does internally by hand - same
concept, same eventual result, on a bucket deliberately seeded with
more keys than fit on one small page.
---------------------------------------------------------------------
"""

print("\n--- Listing by Prefix, With Pagination ---")

# Seed a realistic date-partitioned ETL layout: 23 part-files spread
# across 3 date partitions, plus a handful of unrelated keys.
for day in (22, 23, 24):
    for part in range(8 if day != 24 else 7):
        key = f"raw/orders/date=2026-08-{day}/part-{part:04d}.csv"
        s3.put_object(Bucket="de-raw-lake", Key=key, Body=f"partition {day} part {part}".encode())
s3.put_object(Bucket="de-raw-lake", Key="raw/customers/full.csv", Body=b"unrelated prefix")

prefix = "raw/orders/"
page_size = 10
all_keys = []
token = None
page_number = 0
while True:
    page_number += 1
    page = s3.list_objects_v2(Bucket="de-raw-lake", Prefix=prefix, MaxKeys=page_size, ContinuationToken=token)
    page_keys = [obj["Key"] for obj in page["Contents"]]
    all_keys.extend(page_keys)
    print(f"  page {page_number}: {len(page_keys)} keys, IsTruncated={page['IsTruncated']}")
    if not page["IsTruncated"]:
        break
    token = page["NextContinuationToken"]

print(f"total keys under prefix {prefix!r}: {len(all_keys)} (across {page_number} pages)")
print("first key:", all_keys[0])
print("note 'raw/customers/full.csv' was correctly excluded - wrong prefix")


"""
---------------------------------------------------------------------
5. S3 AS THE DATA LAKE: PANDAS DIRECTLY OVER get_object/put_object  ⭐⭐⭐
---------------------------------------------------------------------
The single most common "real DE work" pattern with boto3: never touch
local disk at all. Pull the object's bytes straight into an in-memory
buffer and hand that to pandas, and go the other way for writes. This
is `s3.get_object()['Body'].read()` -> `io.BytesIO()` -> `pd.read_csv()`
(or `pd.read_parquet()`), and the mirror image for writing.
---------------------------------------------------------------------
"""

print("\n--- Reading/Writing DataFrames Directly to S3 (No Local Disk) ---")

orders_df = pd.DataFrame(
    {"order_id": [1, 2, 3], "customer": ["alice", "bob", "carol"], "amount": [19.99, 42.50, 7.25]}
)

# WRITE a DataFrame to S3 as CSV, via an in-memory buffer:
csv_buffer = io.BytesIO()
orders_df.to_csv(csv_buffer, index=False)
s3.put_object(Bucket="de-raw-lake", Key="curated/orders.csv", Body=csv_buffer.getvalue())
print("wrote DataFrame -> CSV bytes -> put_object (no local file touched)")

# READ it straight back into a DataFrame, same way:
response_body = s3.get_object(Bucket="de-raw-lake", Key="curated/orders.csv")["Body"].read()
orders_from_csv = pd.read_csv(io.BytesIO(response_body))
print("round-tripped CSV DataFrame:")
print(orders_from_csv)
print("matches original:", orders_from_csv.equals(orders_df))

# Same shape again, but Parquet - the columnar format Module 6/12
# flag as the DE-standard for data-lake storage (schema + compression).
parquet_buffer = io.BytesIO()
orders_df.to_parquet(parquet_buffer, index=False)  # engine=pyarrow
s3.put_object(Bucket="de-raw-lake", Key="curated/orders.parquet", Body=parquet_buffer.getvalue())

parquet_bytes = s3.get_object(Bucket="de-raw-lake", Key="curated/orders.parquet")["Body"].read()
orders_from_parquet = pd.read_parquet(io.BytesIO(parquet_bytes))
print("\nround-tripped Parquet DataFrame:")
print(orders_from_parquet)
print("matches original:", orders_from_parquet.equals(orders_df))
print("\nParquet object is smaller/typed vs CSV text:",
      len(parquet_buffer.getvalue()), "bytes vs", len(csv_buffer.getvalue()), "bytes")


"""
---------------------------------------------------------------------
6. PRESIGNED URLS: TEMPORARY ACCESS WITHOUT MAKING OBJECTS PUBLIC  ⭐⭐
---------------------------------------------------------------------
`generate_presigned_url` hands out a URL that embeds a SIGNED,
TIME-LIMITED grant to one specific S3 action - so you can let a
teammate or another service fetch ONE private object over plain HTTPS
for (say) the next hour, without ever flipping the bucket/object to
public. Signing is done LOCALLY using whatever credentials boto3 has
configured - it never actually contacts AWS to produce the URL (only
using the URL later does), which is why this call can "succeed" even
in a sandbox with no real AWS network access.
---------------------------------------------------------------------
"""

print("\n--- Presigned URLs ---")

try:
    client = boto3.client("s3", region_name="us-east-1", config=FAST_FAIL_CONFIG)
    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": "de-raw-lake", "Key": "curated/orders.csv"}, ExpiresIn=3600
    )
    print("client.generate_presigned_url() succeeded (signing is local, no network needed):")
    print(" ", url[:90], "...")
    print("  (this URL would still 404/403 against real AWS - there is no real bucket behind it)")
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"generate_presigned_url() failed ({type(e).__name__}: {e})")
    print("  -> would call AWS like this in production; simulating below.")
    url = None

mock_url = s3.generate_presigned_url(
    "get_object", Params={"Bucket": "de-raw-lake", "Key": "curated/orders.csv"}, ExpiresIn=3600
)
print("mock presigned URL:", mock_url)


"""
---------------------------------------------------------------------
7. STRUCTURED ERROR HANDLING: ClientError AND ITS ERROR CODE  ⭐⭐⭐
---------------------------------------------------------------------
Never write a blanket `except Exception` around an AWS call and give
up - `botocore.exceptions.ClientError` carries a structured
`.response["Error"]["Code"]` (things like `NoSuchKey`, `NoSuchBucket`,
`AccessDenied`, `InvalidAccessKeyId`) that tells you EXACTLY what went
wrong, so a caller can react differently per case: retry, skip, or
raise. Checking the code is the idiomatic pattern; string-matching the
error message is not.
---------------------------------------------------------------------
"""

print("\n--- Structured Error Handling with ClientError ---")

try:
    # A real call against a bucket that (almost certainly) doesn't
    # belong to whatever credentials are configured here.
    client = boto3.client("s3", region_name="us-east-1", config=FAST_FAIL_CONFIG)
    client.get_object(Bucket="this-bucket-does-not-exist-in-this-sandbox", Key="x")
except ClientError as e:
    code = e.response["Error"]["Code"]
    print(f"real call raised ClientError with structured code: {code!r}")
    print("  -> would branch production logic on this code; simulating NoSuchKey/NoSuchBucket below.")
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"real call raised {type(e).__name__} (no network/credentials at all): {e}")
    print("  -> simulating NoSuchKey/NoSuchBucket handling below.")


def read_object_or_explain(bucket, key):
    """Realistic ETL helper: fetch one object, and turn AWS's specific
    error codes into an actionable decision instead of just crashing."""
    try:
        data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        print(f"  [{key}] read fine ({len(data)} bytes)")
        return data
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchKey":
            print(f"  [{key}] missing - treating as an empty/skippable partition, not a crash")
            return None
        elif code == "NoSuchBucket":
            print(f"  [{bucket}] bucket missing - this IS fatal, re-raising")
            raise
        else:
            print(f"  [{key}] unexpected AWS error code {code!r} - re-raising")
            raise


print("\nsimulated cases against the mock:")
read_object_or_explain("de-raw-lake", "curated/orders.csv")   # exists -> reads fine
read_object_or_explain("de-raw-lake", "curated/does_not_exist.csv")  # NoSuchKey -> handled
try:
    read_object_or_explain("bucket-that-was-never-created", "anything")  # NoSuchBucket -> re-raised
except ClientError:
    print("  caller correctly saw the re-raised NoSuchBucket ClientError")


"""
---------------------------------------------------------------------
8. BRIEF: GOOGLE CLOUD STORAGE (google-cloud-storage)  ⭐
---------------------------------------------------------------------
GCS's `google-cloud-storage` library maps onto the exact same shape:
a Client, a bucket, and blob "get/put" operations. Almost certainly
not installed in this sandbox, so the ImportError fallback IS the
expected path here - but the code below is real, correct, idiomatic
usage as you'd write it against a real GCP project.
---------------------------------------------------------------------
"""

print("\n--- Brief: Google Cloud Storage ---")

try:
    from google.cloud import storage  # noqa: F401  (not installed here)

    gcs_client = storage.Client()
    bucket = gcs_client.bucket("de-raw-lake")
    bucket.blob("curated/orders.csv").upload_from_string(csv_buffer.getvalue())
    downloaded = bucket.blob("curated/orders.csv").download_as_bytes()
    print("google-cloud-storage upload/download succeeded:", len(downloaded), "bytes")
except ImportError:
    print("google-cloud-storage is not installed in this sandbox - showing the real API shape only:")
    print("  client = storage.Client()")
    print("  bucket = client.bucket('de-raw-lake')")
    print("  bucket.blob('curated/orders.csv').upload_from_string(csv_bytes)")
    print("  data = bucket.blob('curated/orders.csv').download_as_bytes()")
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"google-cloud-storage call failed ({type(e).__name__}) - no real GCP project configured here.")


"""
---------------------------------------------------------------------
9. BRIEF: AZURE BLOB STORAGE (azure-storage-blob)  ⭐
---------------------------------------------------------------------
Azure's equivalent: a "container" instead of a bucket, a "blob name"
instead of a key, and a `BlobServiceClient` as the entry point. Same
note applies - not installed here, so this demonstrates the real
syntax behind an ImportError fallback.
---------------------------------------------------------------------
"""

print("\n--- Brief: Azure Blob Storage ---")

try:
    from azure.storage.blob import BlobServiceClient  # noqa: F401  (not installed here)

    service = BlobServiceClient.from_connection_string("<connection-string>")
    container_client = service.get_container_client("de-raw-lake")
    container_client.upload_blob(name="curated/orders.csv", data=csv_buffer.getvalue(), overwrite=True)
    downloaded = container_client.download_blob("curated/orders.csv").readall()
    print("azure-storage-blob upload/download succeeded:", len(downloaded), "bytes")
except ImportError:
    print("azure-storage-blob is not installed in this sandbox - showing the real API shape only:")
    print("  service = BlobServiceClient.from_connection_string(conn_str)")
    print("  container_client = service.get_container_client('de-raw-lake')")
    print("  container_client.upload_blob(name='curated/orders.csv', data=bytes_, overwrite=True)")
    print("  data = container_client.download_blob('curated/orders.csv').readall()")
except AWS_UNAVAILABLE_ERRORS as e:
    print(f"azure-storage-blob call failed ({type(e).__name__}) - no real Azure account configured here.")

print("\nAll three (S3, GCS, Azure Blob) share one shape once you know it:")
print("  bucket/container name + string key/blob-name + put-bytes/get-bytes.")
print("Learn boto3's put_object/get_object well and the other two SDKs")
print("read as a find-and-replace of nouns, not a new mental model.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
boto3.client('s3')      -> low-level, raw dict responses, Bucket=/Key=
boto3.resource('s3')    -> high-level, Bucket/Object PYTHON OBJECTS

Writing:  put_object(Bucket, Key, Body=bytes)   -> bytes already in memory
          upload_file(Filename, Bucket, Key)     -> reads a local file for you
Reading:  get_object(Bucket, Key)['Body'].read() -> bytes back in memory
          download_file(Bucket, Key, Filename)   -> writes straight to disk

S3 "folders" = key PREFIXES only, no real directories:
    list_objects_v2(Bucket=b, Prefix="raw/orders/")
    paginator = client.get_paginator("list_objects_v2")  -> auto-pages
    (manual pagination: loop on NextContinuationToken while IsTruncated)

Data lake pattern, no local disk:
    buf = io.BytesIO(s3.get_object(Bucket=b, Key=k)["Body"].read())
    df = pd.read_csv(buf)  /  pd.read_parquet(buf)
    buf = io.BytesIO(); df.to_csv(buf) / df.to_parquet(buf); put_object(..., Body=buf.getvalue())

generate_presigned_url(...)  -> temporary signed URL, no ACL change,
                                  signing is LOCAL (no network call)

Error handling:
    except ClientError as e: e.response["Error"]["Code"]
    common codes -> NoSuchKey, NoSuchBucket, AccessDenied, InvalidAccessKeyId
    NEVER blanket-except and ignore the code - branch on it

Universal object-storage shape (AWS/GCP/Azure):
    bucket/container + key/blob-name + get-bytes/put-bytes
    google-cloud-storage -> storage.Client().bucket(n).blob(k).upload_from_string(...)
    azure-storage-blob   -> BlobServiceClient(...).get_container_client(n).upload_blob(...)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CLOUD SDKS (boto3 / S3, GCS, AZURE BLOB)
=====================================================================

1. How would you read a file from, and write a file to, S3 using
   boto3? Walk through both the `client` and `resource` ways.

2. What's the practical difference between `boto3.client('s3')` and
   `boto3.resource('s3')`? When would you reach for the low-level
   client instead of the resource API?

3. What's the difference between `put_object`/`get_object` and
   `upload_file`/`download_file`? When would you use each?

4. S3 doesn't have real folders - so what does a "folder" like
   `raw/orders/date=2026-08-24/` actually mean to S3, and which
   boto3 call and parameter would you use to list everything "in"
   it?

5. `list_objects_v2` caps out at 1000 keys per call by default. How
   do you reliably list EVERY object under a prefix that might have
   tens of thousands of keys? What does `client.get_paginator(...)`
   do for you that hand-rolling the loop yourself doesn't?

6. Describe the pattern for reading a CSV or Parquet object from S3
   directly into a pandas DataFrame WITHOUT writing anything to local
   disk first. What's `io.BytesIO()` doing in that pattern?

7. Why is Parquet generally a better fit than CSV for objects living
   in an S3-backed data lake?

8. What is a presigned URL, and why would you generate one instead
   of just making the object public? Why can `generate_presigned_url`
   succeed even when you don't have valid AWS credentials at all?

9. Why should you catch `botocore.exceptions.ClientError` and inspect
   `e.response["Error"]["Code"]` instead of writing a blanket
   `except Exception` around an S3 call? Give two different error
   codes you might branch on and how you'd handle each differently.

10. In `read_object_or_explain()` from this file, why does a
    `NoSuchKey` error get swallowed and treated as "skip this
    partition", while a `NoSuchBucket` error gets re-raised instead?
    What's the reasoning for treating those two differently in an
    ETL job?

11. If your Python process has no AWS credentials configured at all,
    what specific `botocore` exception do you expect calling
    `client.list_buckets()` to raise, versus what you'd expect if
    credentials exist but are simply wrong/expired?

12. How would the same "list objects under a prefix" and "upload/
    download bytes" operations look if you were using
    `google-cloud-storage` or `azure-storage-blob` instead of boto3?
    What maps to what (bucket vs container, key vs blob name)?

13. In a scheduled ETL job that reads new files landing under a
    date-partitioned S3 prefix every hour, how would you use
    `Prefix` plus pagination to discover only that hour's/day's
    files, tying back to the idempotent-pipeline ideas from Module
    11?

14. Why does creating `boto3.client('s3')` or `boto3.resource('s3')`
    never itself raise a connection error, even with zero
    credentials configured - and which specific method call is
    actually the first thing that touches the network?

15. How would you unit test a function that calls `put_object`/
    `get_object` without hitting real AWS at all? (Hint: think about
    what this file's `MockS3Client` is doing, and how that connects
    to Module 13's `unittest.mock`.)
=====================================================================
"""
