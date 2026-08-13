"""
=====================================================================
PYTHON STRING MANIPULATION & FORMATTING - Notes with Executable Code
=====================================================================

Strings are IMMUTABLE sequences of Unicode characters. Every string
"operation" (upper, replace, slicing, concatenation, etc.) returns a
NEW string object - the original is never changed in place.

Topics covered:
    - String basics & immutability
    - Indexing & slicing
    - Common string methods
    - Splitting & joining
    - String formatting: %-operator, .format(), f-strings
    - Stripping, padding, alignment
    - Encoding/decoding
    - Regex basics (re module)
=====================================================================
"""

print("--- Overview ---")
print("Strings are immutable - every 'change' creates a new string.")


"""
---------------------------------------------------------------------
1. STRING BASICS & IMMUTABILITY
---------------------------------------------------------------------
Strings can be created with single, double, or triple quotes
(triple quotes allow multi-line strings). Since strings are
immutable, methods like .upper() return a NEW string rather than
modifying the original.
---------------------------------------------------------------------
"""

print("\n--- Immutability ---")

s = "hello world"
upper_s = s.upper()
print("original:", s)          # unchanged
print("uppercased copy:", upper_s)

try:
    s[0] = "H"          # strings don't support item assignment
except TypeError as e:
    print("Error mutating string:", e)

multiline = """This is
a multi-line
string."""
print("\nmulti-line string:\n", multiline)


"""
---------------------------------------------------------------------
2. INDEXING & SLICING  ⭐⭐
---------------------------------------------------------------------
Strings support 0-based indexing and negative indexing (from the
end). Slicing syntax: s[start:stop:step] - 'stop' is EXCLUSIVE.
---------------------------------------------------------------------
"""

print("\n--- Indexing & Slicing ---")

text = "Data Engineering"

print("text[0] =", text[0])         # 'D' - first character
print("text[-1] =", text[-1])       # 'g' - last character
print("text[0:4] =", text[0:4])     # 'Data' - stop index excluded
print("text[5:] =", text[5:])       # 'Engineering' - to the end
print("text[:4] =", text[:4])       # 'Data' - from the start
print("text[::-1] =", text[::-1])   # reverses the entire string!
print("text[::2] =", text[::2])     # every 2nd character


"""
---------------------------------------------------------------------
3. COMMON STRING METHODS  ⭐⭐
---------------------------------------------------------------------
Case:      upper(), lower(), title(), capitalize(), swapcase()
Search:    find(), index(), count(), startswith(), endswith()
Check:     isdigit(), isalpha(), isalnum(), isspace(), isupper()
Modify:    replace(), strip(), lstrip(), rstrip()
---------------------------------------------------------------------
"""

print("\n--- Common String Methods ---")

sample = "  Hello, Data Engineer!  "

print("upper():", sample.upper())
print("lower():", sample.lower())
print("title():", sample.title())
print("strip():", repr(sample.strip()))       # removes leading/trailing whitespace
print("replace():", sample.replace("Data", "Big Data"))
print("find('Data'):", sample.find("Data"))    # returns index, -1 if not found
print("find('xyz'):", sample.find("xyz"))      # -1, not found (no exception!)

try:
    sample.index("xyz")     # raises ValueError, unlike find()
except ValueError as e:
    print("index('xyz') raises:", e)

print("count('e'):", sample.lower().count("e"))
print("startswith('  Hello'):", sample.startswith("  Hello"))
print("'123'.isdigit():", "123".isdigit())
print("'abc123'.isalnum():", "abc123".isalnum())


"""
---------------------------------------------------------------------
4. SPLITTING & JOINING  ⭐⭐⭐
---------------------------------------------------------------------
split()  -> string -> list  (breaks a string apart on a delimiter)
join()   -> list -> string  (glues elements together with a
                              delimiter - MUST be called on the
                              delimiter string, not the list)

split()/join() are extremely common in data engineering for parsing
delimited text (CSV rows, log lines, pipe-separated data, etc.)
---------------------------------------------------------------------
"""

print("\n--- Splitting & Joining ---")

csv_row = "id,name,age,city"
fields = csv_row.split(",")
print("split by comma:", fields)

# split() with no argument splits on ANY whitespace (and collapses
# multiple spaces automatically) - very handy for messy text
messy = "  lots   of   spaces  "
print("split() default:", messy.split())

# join() - called on the DELIMITER, given an iterable of strings
joined = "-".join(["2026", "08", "13"])
print("join with '-':", joined)

# Common pattern: split then rejoin with a different delimiter
pipe_row = "|".join(csv_row.split(","))
print("comma -> pipe delimited:", pipe_row)

# splitlines() - splits a multi-line string into a list of lines
log_text = "line1\nline2\nline3"
print("splitlines():", log_text.splitlines())

# maxsplit parameter - limits the number of splits performed
key_value = "name=Claude=Assistant"
print("split with maxsplit=1:", key_value.split("=", maxsplit=1))


"""
---------------------------------------------------------------------
5. STRING FORMATTING: THREE METHODS  ⭐⭐⭐
---------------------------------------------------------------------
Python has THREE ways to format strings, evolving over time:

    (a) %-formatting (old-style, C-like)      -> "%s is %d" % (a, b)
    (b) .format() method (Python 2.6+)         -> "{} is {}".format(a, b)
    (c) f-strings (Python 3.6+, PREFERRED)     -> f"{a} is {b}"

f-strings are now the standard: faster, more readable, and support
inline expressions and formatting specs directly.
---------------------------------------------------------------------
"""

print("\n--- String Formatting: Three Methods ---")

name = "Claude"
version = 5
pi_value = 3.14159265

# (a) Old-style %-formatting
old_style = "%s is version %d" % (name, version)
print("%-formatting:", old_style)

# (b) .format() method
format_method = "{} is version {}".format(name, version)
print(".format():", format_method)

# .format() with positional/named placeholders (reusable, order-independent)
format_named = "{n} is version {v}, and {n} again".format(n=name, v=version)
print(".format() named:", format_named)

# (c) f-strings (PREFERRED - most readable, supports expressions inline)
f_string = f"{name} is version {version}"
print("f-string:", f_string)

# f-strings can embed ANY expression, not just variables
f_expr = f"Next version will be {version + 1}"
print("f-string with expression:", f_expr)

# Calling methods inline inside an f-string
f_method = f"Name in upper: {name.upper()}"
print("f-string with method call:", f_method)


"""
---------------------------------------------------------------------
6. FORMAT SPECIFIERS (WIDTH, PRECISION, ALIGNMENT, PADDING) ⭐⭐
---------------------------------------------------------------------
Format specs work IDENTICALLY inside f-strings and .format():
    {value:spec}

Common specs:
    :.2f    -> 2 decimal places (float)
    :,      -> thousands separator
    :>10    -> right-align in a 10-char field
    :<10    -> left-align in a 10-char field
    :^10    -> center-align in a 10-char field
    :05d    -> zero-pad an integer to 5 digits
    :.2%    -> format as a percentage with 2 decimals
    :x      -> hexadecimal
    :b      -> binary
---------------------------------------------------------------------
"""

print("\n--- Format Specifiers ---")

price = 1234567.891

print(f"2 decimal places: {price:.2f}")
print(f"thousands separator: {price:,.2f}")
print(f"right-aligned (width 15): '{price:>15,.2f}'")
print(f"left-aligned (width 15): '{price:<15,.2f}'")
print(f"center-aligned (width 20): '{'DATA':^20}'")
print(f"zero-padded int: {42:05d}")
print(f"percentage: {0.8567:.2%}")
print(f"hexadecimal: {255:x}")
print(f"binary: {10:b}")

# Debug specifier (Python 3.8+) - shows variable name AND value,
# extremely handy for quick debugging/logging
debug_var = "some_value"
print(f"debug spec: {debug_var=}")


"""
---------------------------------------------------------------------
7. STRIPPING & PADDING  ⭐
---------------------------------------------------------------------
strip()/lstrip()/rstrip()  -> remove whitespace (or given characters)
ljust()/rjust()/center()   -> pad strings to a fixed width
zfill()                    -> zero-pad numeric strings on the left
---------------------------------------------------------------------
"""

print("\n--- Stripping & Padding ---")

padded = "42"
print("zfill(5):", padded.zfill(5))          # '00042'
print("ljust(10, '*'):", "hi".ljust(10, "*"))
print("rjust(10, '*'):", "hi".rjust(10, "*"))
print("center(10, '-'):", "hi".center(10, "-"))

# strip() can also remove SPECIFIC characters, not just whitespace
messy_str = "***important***"
print("strip('*'):", messy_str.strip("*"))


"""
---------------------------------------------------------------------
8. STRING CONCATENATION - EFFICIENCY MATTERS  ⭐⭐
---------------------------------------------------------------------
Since strings are immutable, repeatedly using '+' in a loop creates
a NEW string object every time - O(n^2) for n concatenations.
join() is far more efficient for combining many strings, since it
builds the result once.
---------------------------------------------------------------------
"""

print("\n--- Concatenation Efficiency ---")

words = ["Data", "Engineering", "with", "Python"]

# Inefficient: creates a new string object on every '+=' iteration
inefficient = ""
for w in words:
    inefficient += w + " "
print("built with += :", inefficient.strip())

# Efficient: join() builds the final string in a single pass
efficient = " ".join(words)
print("built with join():", efficient)


"""
---------------------------------------------------------------------
9. ENCODING & DECODING  ⭐
---------------------------------------------------------------------
str.encode()   -> converts a string to bytes (e.g., for network/file I/O)
bytes.decode() -> converts bytes back to a string
Default encoding is UTF-8 in Python 3.
---------------------------------------------------------------------
"""

print("\n--- Encoding & Decoding ---")

text_val = "Data Engineer"
encoded = text_val.encode("utf-8")
print("encoded to bytes:", encoded)

decoded = encoded.decode("utf-8")
print("decoded back to str:", decoded)


"""
---------------------------------------------------------------------
10. REGEX BASICS (re module)  ⭐⭐
---------------------------------------------------------------------
For pattern-based searching/extraction beyond simple string methods.
Common functions: re.search(), re.match(), re.findall(), re.sub()
---------------------------------------------------------------------
"""

print("\n--- Regex Basics ---")

import re

log_line = "2026-08-13 ERROR: Connection failed to host 192.168.1.10"

# findall() - returns ALL non-overlapping matches
ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
ips_found = re.findall(ip_pattern, log_line)
print("IP addresses found:", ips_found)

# search() - finds the FIRST match anywhere in the string
match = re.search(r"ERROR|WARNING|INFO", log_line)
print("log level found:", match.group() if match else None)

# sub() - replaces matches with a new string
masked = re.sub(ip_pattern, "[REDACTED]", log_line)
print("IP masked:", masked)


"""
=====================================================================
INTERVIEW QUESTIONS - STRING MANIPULATION & FORMATTING
=====================================================================

1. Why are strings immutable in Python? What are the performance
   implications of concatenating strings with '+' inside a loop
   versus using ''.join()?

2. What's the difference between find() and index() when a
   substring isn't present? Which one raises an exception?

3. Explain the difference between split() with no arguments and
   split(" ") - why do they behave differently on strings with
   multiple consecutive spaces?

4. What are the three ways to format strings in Python (%, .format(),
   f-strings), and why are f-strings generally preferred today?

5. How would you format a float to 2 decimal places with a thousands
   separator (e.g., 1234567.891 -> "1,234,567.89")?

6. What does `s[::-1]` do, and how does it work under the hood using
   slice notation?

7. How do you safely parse a delimited log line (e.g., CSV or
   pipe-separated) into individual fields using string methods,
   and what could go wrong if the delimiter also appears inside a
   quoted field?

8. What is the debug specifier `{var=}` in f-strings (Python 3.8+),
   and why is it useful during debugging/logging?

9. Explain the difference between `strip()`, `lstrip()`, and
   `rstrip()`. Does `strip("*")` remove ALL asterisks or just the
   ones at the edges of the string?

10. Why does string concatenation with '+' in a loop have O(n^2)
    time complexity, while `"".join(list_of_strings)` is O(n)?

11. How would you check if a string contains only digits, and what's
    the difference between `isdigit()`, `isnumeric()`, and
    `isdecimal()`?

12. What's the difference between `encode()` and `decode()`? When
    would you need to explicitly encode/decode a string in a data
    pipeline (e.g., reading a file with a non-UTF-8 encoding)?

13. Write a regex to extract all email addresses from a block of
    text. What module and functions would you use?

14. How would you remove all whitespace from a string, including
    internal spaces, not just leading/trailing? (Hint:
    `"".join(s.split())` or `re.sub(r"\\s+", "", s)`)

15. In a data engineering context, why might you prefer f-strings
    over `.format()` when building dynamic SQL queries or file
    paths — and what's the SECURITY risk of building SQL queries
    via string formatting/concatenation instead of parameterized
    queries?
=====================================================================
"""