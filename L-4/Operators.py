"""
=====================================================================
PYTHON OPERATORS - Complete Notes with Executable Examples
=====================================================================

Operators are special symbols/keywords that perform operations on
values (operands). Python groups them into:

    Arithmetic  -> + - * / % // **
    Comparison  -> == != > < >= <=
    Logical     -> and or not
    Assignment  -> = += -= *= /= etc.
    Identity    -> is, is not
    Membership  -> in, not in
    Bitwise     -> & | ^ ~ << >>
=====================================================================
"""

print("--- Overview ---")
print("Operators act on operands to produce a result, e.g., 3 + 5 = 8")


"""
---------------------------------------------------------------------
1. ARITHMETIC OPERATORS
---------------------------------------------------------------------
+   Addition
-   Subtraction
*   Multiplication
/   True division   -> always returns a float
//  Floor division  -> discards the remainder, rounds toward -inf
%   Modulus         -> remainder of division
**  Exponentiation
---------------------------------------------------------------------
"""

print("\n--- Arithmetic Operators ---")
a, b = 17, 5

print(f"{a} + {b} =", a + b)
print(f"{a} - {b} =", a - b)
print(f"{a} * {b} =", a * b)
print(f"{a} / {b} =", a / b)     # 3.4  -> true division, always float
print(f"{a} // {b} =", a // b)   # 3    -> floor division
print(f"{a} % {b} =", a % b)     # 2    -> remainder
print(f"{a} ** {b} =", a ** b)   # 17^5 -> exponentiation

# Floor division with negative numbers rounds toward NEGATIVE infinity,
# not toward zero - a very common interview trap
print("\n-7 // 2 =", -7 // 2)    # -4, NOT -3 (rounds down, not truncates)
print("-7 % 2 =", -7 % 2)        # 1  (Python's modulus always matches
                                  #     the sign of the divisor)


"""
---------------------------------------------------------------------
2. COMPARISON (RELATIONAL) OPERATORS
---------------------------------------------------------------------
==   Equal to (compares VALUE)
!=   Not equal to
>    Greater than
<    Less than
>=   Greater than or equal to
<=   Less than or equal to

Comparison operators can also be CHAINED in Python:
    1 < x < 10   is equivalent to   (1 < x) and (x < 10)
---------------------------------------------------------------------
"""

print("\n--- Comparison Operators ---")
x = 5
print("x == 5 ->", x == 5)
print("x != 5 ->", x != 5)
print("x > 3 and x < 10 ->", x > 3 and x < 10)

# Chained comparison - Pythonic and efficient (short-circuits)
print("1 < x < 10 (chained) ->", 1 < x < 10)


"""
---------------------------------------------------------------------
3. LOGICAL OPERATORS
---------------------------------------------------------------------
and   True if BOTH operands are true
or    True if AT LEAST ONE operand is true
not   Inverts the boolean value

Python uses SHORT-CIRCUIT evaluation:
    - 'and' stops at the first False value
    - 'or'  stops at the first True value
This matters for performance and for avoiding errors (e.g., checking
`x != 0 and 10 / x > 1` safely avoids division by zero).
---------------------------------------------------------------------
"""

print("\n--- Logical Operators ---")
print("True and False ->", True and False)
print("True or False ->", True or False)
print("not True ->", not True)

# Short-circuit evaluation in action - the right side is never
# evaluated once the outcome is already determined
def noisy_true():
    print("  noisy_true() was called")
    return True

print("Short-circuit with 'or':")
result = True or noisy_true()      # noisy_true() never runs
print("result:", result)

# 'and'/'or' also return one of the ACTUAL operands, not just
# True/False - useful for default-value patterns
default_name = "" or "Guest"       # "" is falsy, so returns "Guest"
print("'' or 'Guest' ->", default_name)


"""
---------------------------------------------------------------------
4. ASSIGNMENT OPERATORS
---------------------------------------------------------------------
=    Assign
+=   Add and assign
-=   Subtract and assign
*=   Multiply and assign
/=   Divide and assign
//=  Floor divide and assign
%=   Modulus and assign
**=  Exponentiate and assign
:=   Walrus operator (Python 3.8+) - assign WITHIN an expression
---------------------------------------------------------------------
"""

print("\n--- Assignment Operators ---")
n = 10
n += 5    # n = n + 5
print("n after += 5:", n)
n *= 2
print("n after *= 2:", n)

# Walrus operator - assigns and returns the value in one expression
# Very handy in while-loops and comprehensions to avoid calling
# something twice
print("\nWalrus operator example:")
data = [1, 2, 3, 4, 5, 6, 7, 8]
# Without walrus: you'd compute len(data) separately before the if
if (n := len(data)) > 5:
    print(f"List is long: {n} items")


"""
---------------------------------------------------------------------
5. IDENTITY OPERATORS: is, is not
---------------------------------------------------------------------
is       True if two variables point to the SAME object in memory
is not   True if they do NOT point to the same object

This is DIFFERENT from == , which checks VALUE equality.
---------------------------------------------------------------------
"""

print("\n--- Identity Operators ---")
list1 = [1, 2, 3]
list2 = [1, 2, 3]        # same VALUES, different OBJECT in memory
list3 = list1             # same OBJECT as list1

print("list1 == list2 ->", list1 == list2)   # True  (same values)
print("list1 is list2 ->", list1 is list2)   # False (different objects)
print("list1 is list3 ->", list1 is list3)   # True  (same object)

# Small integer caching - CPython caches ints from -5 to 256 as
# singletons, a classic interview gotcha
small_a = 100
small_b = 100
print("100 is 100 ->", small_a is small_b)   # True (cached small int)

big_a = 10000
big_b = int("10000")   # built at runtime so Python can't constant-fold
                        # it into the same cached literal
print("10000 is 10000 (built separately) ->", big_a is big_b)
# often False - large ints outside the -5..256 cache range are
# normally separate objects (note: literal constants written
# directly in code can sometimes get folded/interned by the
# compiler, which is why building one value at runtime is used
# here to show the "true" uncached behavior reliably)


"""
---------------------------------------------------------------------
6. MEMBERSHIP OPERATORS: in, not in
---------------------------------------------------------------------
in       True if a value exists within a sequence/collection
not in   True if a value does NOT exist within it

Membership tests are O(1) average for sets/dicts (hash-based) but
O(n) for lists/tuples (linear scan) - important for performance
when checking membership repeatedly on large data.
---------------------------------------------------------------------
"""

print("\n--- Membership Operators ---")
fruits = ["apple", "banana", "cherry"]
print("'banana' in fruits ->", "banana" in fruits)
print("'mango' not in fruits ->", "mango" not in fruits)

# Same check but with a set - much faster for large collections
fruit_set = set(fruits)
print("'banana' in fruit_set (O(1) lookup) ->", "banana" in fruit_set)


"""
---------------------------------------------------------------------
7. BITWISE OPERATORS
---------------------------------------------------------------------
&    AND   - 1 only if both bits are 1
|    OR    - 1 if at least one bit is 1
^    XOR   - 1 only if bits differ
~    NOT   - inverts all bits (two's complement: ~x = -x - 1)
<<   Left shift  - shifts bits left, multiplies by 2 per shift
>>   Right shift - shifts bits right, divides by 2 per shift

Used in low-level operations, flags/masks, and performance-critical
or embedded code. Less common in typical data engineering scripts
but still asked as a fundamentals check.
---------------------------------------------------------------------
"""

print("\n--- Bitwise Operators ---")
p, q = 6, 3          # binary: 6 = 110, 3 = 011

print(f"{p} & {q} =", p & q)     # 010 = 2
print(f"{p} | {q} =", p | q)     # 111 = 7
print(f"{p} ^ {q} =", p ^ q)     # 101 = 5
print(f"~{p} =", ~p)             # -7  (two's complement: -(p+1))
print(f"{p} << 1 =", p << 1)     # 12  (shift left = multiply by 2)
print(f"{p} >> 1 =", p >> 1)     # 3   (shift right = divide by 2)


"""
---------------------------------------------------------------------
8. OPERATOR PRECEDENCE (BRIEF)
---------------------------------------------------------------------
Highest to lowest (simplified, most commonly relevant):
    ()                  -> parentheses (always evaluated first)
    **                  -> exponentiation
    * / // %            -> multiplication/division family
    + -                 -> addition/subtraction
    comparisons          -> == != > < >= <=
    not                 -> logical NOT
    and                 -> logical AND
    or                  -> logical OR

When in doubt, use parentheses for clarity - interviewers often
test precedence with tricky expressions like the one below.
---------------------------------------------------------------------
"""

print("\n--- Operator Precedence ---")
# ** binds tighter than unary minus on its left in some contexts -
# but unary minus binds tighter than ** on its right operand here:
tricky = -2 ** 2
print("-2 ** 2 =", tricky)        # -4, NOT 4! (** binds before unary -)
print("(-2) ** 2 =", (-2) ** 2)   # 4  (parentheses force order)

mixed = 2 + 3 * 4
print("2 + 3 * 4 =", mixed)       # 14, not 20 (* before +)


"""
=====================================================================
INTERVIEW QUESTIONS - PYTHON OPERATORS
=====================================================================

1. What is the difference between '/' and '//' in Python? What does
   -7 // 2 evaluate to, and why?

2. Explain the difference between 'is' and '=='. Give an example
   where two variables are '==' but not 'is'.

3. What is short-circuit evaluation? Why does `True or expensive_call()`
   never execute expensive_call()?

4. What does Python's small integer caching mean for the 'is'
   operator? Why can `a is b` be True for small ints (like 100) but
   False for larger ones (like 10000)?

5. What is the walrus operator (:=) and what problem does it solve?
   Give an example using it inside a while loop or comprehension.

6. Why is membership testing (`x in collection`) faster with a set
   than with a list? What's the time complexity of each?

7. What does Python's modulus operator (%) return for negative
   numbers, and how does that differ from other languages like C?

8. Evaluate `-2 ** 2` and explain why the result is -4, not 4.

9. What's the difference between `and`/`or` and `&`/`|` when used
   on booleans vs. on integers or Pandas Series? (Hint: this trips
   people up constantly with Pandas boolean masking, e.g.
   `df[(df.a > 1) & (df.b < 5)]` requires `&`, not `and`.)

10. How would you swap two variables without using a temporary
    variable? (`a, b = b, a`)

11. What does `x = x or default_value` do, and when is this pattern
    risky? (Hint: fails if 0, "", or [] are valid intended values,
    since they're falsy too.)

12. Explain chained comparisons like `1 < x < 10`. What does Python
    actually do internally, and is it more efficient than
    `1 < x and x < 10`?

13. What's the output of `bool([]) or bool({})`  and why? Explain
    truthy/falsy values in Python (empty collections, 0, None, "").

14. In a data engineering context, why must you use bitwise `&`/`|`
    (not `and`/`or`) when combining multiple filter conditions on a
    Pandas DataFrame or NumPy array?
=====================================================================
"""