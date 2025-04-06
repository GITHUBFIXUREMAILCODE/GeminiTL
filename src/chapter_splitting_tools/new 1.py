import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import numpy as np

###############################################################################
#                               Finite Field Helpers                          #
###############################################################################
def modinv(x, p):
    """
    Compute modular inverse of x under prime p using Fermat's little theorem:
    x^(p-1) ≡ 1 (mod p)  =>  x^(p-2) ≡ x^(-1) (mod p)
    """
    return pow(int(x), p - 2, p)

def add_modp(a, b, P, Q, p):
    """
    Elliptic curve point addition over the finite field F_p:
       Curve: y^2 = x^3 + a*x + b (mod p)
    Each point is a tuple (x, y). None represents the point at infinity.
    """
    if P is None:
        return Q
    if Q is None:
        return P

    (x1, y1) = P
    (x2, y2) = Q

    # If x1 == x2 but y1 != y2, then vertical line => infinity
    if (x1 % p) == (x2 % p) and (y1 % p) != (y2 % p):
        return None

    if (x1 % p) == (x2 % p) and (y1 % p) == (y2 % p):
        # Point doubling
        if y1 % p == 0:
            return None
        m = ((3 * x1 * x1 + a) % p) * modinv(2 * y1, p)
        m %= p
    else:
        # Point addition
        denom = (x2 - x1) % p
        if denom == 0:  # same x, different y => Infinity
            return None
        m = ((y2 - y1) % p) * modinv(denom, p)
        m %= p

    x3 = (m * m - x1 - x2) % p
    y3 = (m * (x1 - x3) - y1) % p
    return (x3, y3)

def mul_modp(a, b, P, n, p):
    """
    Elliptic curve scalar multiplication over F_p:
      n*P = P + P + ... + P (n times)
    Uses a simple double-and-add algorithm for clarity (not the fastest).
    """
    R = None
    base = P
    k = n
    while k > 0:
        if k & 1:
            R = add_modp(a, b, R, base, p)
        base = add_modp(a, b, base, base, p)
        k >>= 1
    return R

###############################################################################
#                          Real Arithmetic Helpers                             #
###############################################################################
def add_reals(a, b, P, Q):
    """
    Elliptic curve point addition over R:
      Curve: y^2 = x^3 + a*x + b
      Return None to represent point at infinity for vertical lines, etc.
    """
    x1, y1 = P
    x2, y2 = Q

    # Doubling
    if P == Q:
        if abs(y1) < 1e-14:
            return None  # slope => infinity
        m = (3 * x1**2 + a) / (2 * y1)
    else:
        # P + Q
        if abs(x2 - x1) < 1e-14:
            return None  # vertical line => point at infinity
        m = (y2 - y1) / (x2 - x1)

    x3 = m**2 - x1 - x2
    y3 = m * (x1 - x3) - y1
    return (x3, y3)

def mul_reals(a, b, P, n):
    """
    Scalar multiplication over R by repeated addition (inefficient, but simple).
    """
    if n == 0:
        return None
    R = P
    for _ in range(n - 1):
        R = add_reals(a, b, R, P)
        if R is None:
            break
    return R

###############################################################################
#                                Plotting                                      #
###############################################################################
def plot_curve_real(a, b, P, Q, R):
    """
    Plot continuous curve over R: y^2 = x^3 + a*x + b
    along with points P, Q, R.
    """
    plt.figure(figsize=(6, 6))
    plt.axhline(0, color='gray', linewidth=0.5)
    plt.axvline(0, color='gray', linewidth=0.5)
    plt.grid(True)

    # Generate x-range
    x_vals = np.linspace(-5, 5, 500)
    curve_vals = x_vals**3 + a * x_vals + b

    # We only plot the real portion where curve_vals >= 0 for +branch, <= 0 for -branch
    # Actually we'll just do np.sqrt(clip to >=0) for positive branch
    y_pos = np.sqrt(np.clip(curve_vals, 0, None))
    y_neg = -y_pos

    plt.plot(x_vals, y_pos, 'b', label='Curve + branch')
    plt.plot(x_vals, y_neg, 'b', label='Curve – branch')

    # Plot points
    if P: plt.plot(P[0], P[1], 'yo', label='P')
    if Q: plt.plot(Q[0], Q[1], 'go', label='Q')
    if R:
        if isinstance(R, tuple):
            plt.plot(R[0], R[1], 'ro', label='R')
        else:
            # If R is None, skip plotting
            pass

    plt.title(f"Elliptic Curve (Real): y² = x³ + {a}x + {b}")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.axis("equal")
    plt.legend()
    plt.show()

def plot_curve_modp(a, b, p, P, Q, R):
    """
    Plot discrete points of the elliptic curve over F_p:
       y^2 ≡ x^3 + a*x + b (mod p).
    We’ll find all (x, y) with 0 <= x,y < p that satisfy the equation.
    Then highlight P, Q, R if present.
    """
    # Enumerate all valid points
    all_points = []
    for x in range(p):
        rhs = (x**3 + a*x + b) % p
        # Find y s.t. y^2 = rhs (mod p)
        for y in range(p):
            if (y * y) % p == rhs:
                all_points.append((x, y))

    # Create the plot
    plt.figure(figsize=(6, 6))
    plt.grid(True)
    xs = [pt[0] for pt in all_points]
    ys = [pt[1] for pt in all_points]
    plt.scatter(xs, ys, color='blue', s=20, label='Curve points')

    # Mark P, Q, and R in different colors
    if P in all_points:
        plt.scatter(P[0], P[1], color='yellow', s=100, edgecolors='black', label='P')
    if Q in all_points:
        plt.scatter(Q[0], Q[1], color='green', s=100, edgecolors='black', label='Q')
    if R in all_points:
        plt.scatter(R[0], R[1], color='red', s=100, edgecolors='black', label='R')

    plt.title(f"Elliptic Curve over F_{p}: y² ≡ x³ + {a}x + {b} (mod {p})")
    plt.xlabel("x (mod p)")
    plt.ylabel("y (mod p)")
    plt.legend()
    # We often just show 0..p-1, but let's keep square proportions
    plt.xlim(-1, p)
    plt.ylim(-1, p)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.show()

###############################################################################
#                               Main GUI Logic                                 #
###############################################################################
def compute():
    try:
        # Collect parameters
        field_type = field_mode.get()       # "Real" or "Finite Field"
        op = mode.get()                     # "Addition" or "Multiplication"
        a_val = float(entry_a.get())
        b_val = float(entry_b.get())

        # For real arithmetic, we interpret them as floats
        # For mod p, we interpret a, b, p as integers (though a,b mod p anyway)
        if field_type == "Finite Field":
            p_val = int(entry_p.get())
            # reduce a_val,b_val mod p
            A = int(a_val) % p_val
            B = int(b_val) % p_val
        else:
            p_val = None  # Not used in real field
            A = a_val
            B = b_val

        # Read point P
        x1 = float(entry_px.get())
        y1 = float(entry_py.get())

        # Prepare placeholders for Q or n
        Q = None
        n_val = None

        if op == "Addition":
            # For addition, we have Q
            x2 = float(entry_qx.get())
            y2 = float(entry_qy.get())
            Q = (x2, y2)
        else:
            # For multiplication, we have n
            n_val = int(entry_n.get())

        # Perform the actual operation
        if field_type == "Real":
            # Real arithmetic
            P = (x1, y1)
            if op == "Addition":
                Q = (Q[0], Q[1])
                R = add_reals(A, B, P, Q)
            else:  # Multiplication
                R = mul_reals(A, B, P, n_val)
        else:
            # Finite field F_p
            P = (int(x1) % p_val, int(y1) % p_val)
            if op == "Addition":
                Q = (int(Q[0]) % p_val, int(Q[1]) % p_val)
                R = add_modp(A, B, P, Q, p_val)
            else:
                R = mul_modp(A, B, P, n_val, p_val)

        # Update the R output
        if R is None:
            # point at infinity
            result_x.set("∞")
            result_y.set("∞")
        else:
            if field_type == "Real":
                # Round for display
                rx, ry = R
                result_x.set(f"{rx:.4f}")
                result_y.set(f"{ry:.4f}")
            else:
                rx, ry = R
                result_x.set(str(rx))
                result_y.set(str(ry))

        # Now do the plotting
        if field_type == "Real":
            if op == "Addition":
                plot_curve_real(A, B, P, Q, R)
            else:
                plot_curve_real(A, B, P, None, R)
        else:
            if op == "Addition":
                plot_curve_modp(A, B, p_val, P, Q, R)
            else:
                plot_curve_modp(A, B, p_val, P, None, R)

    except Exception as e:
        # If any error occurs (like invalid input), show "Err"
        result_x.set("Err")
        result_y.set("Err")

###############################################################################
#                                  TK GUI                                      #
###############################################################################
root = tk.Tk()
root.title("Elliptic Curve Calculator")

# FIELD SELECTION: Real or Finite Field
tk.Label(root, text="Field:").grid(row=0, column=0, padx=5, pady=5)
field_mode = tk.StringVar(value="Real")
field_menu = ttk.Combobox(root, textvariable=field_mode, values=["Real", "Finite Field"], state="readonly")
field_menu.grid(row=0, column=1, padx=5, pady=5)

# If finite field, specify p
tk.Label(root, text="p (if finite):").grid(row=0, column=2, padx=5, pady=5)
entry_p = tk.Entry(root, width=5)
entry_p.insert(0, "17")  # default prime
entry_p.grid(row=0, column=3, padx=5, pady=5)

# CURVE COEFFICIENTS: a, b
tk.Label(root, text="Curve: y² = x³ + a*x + b").grid(row=1, column=0, columnspan=4, pady=(10, 0))
tk.Label(root, text="a:").grid(row=2, column=0, pady=2)
entry_a = tk.Entry(root, width=5)
entry_a.insert(0, "-7")
entry_a.grid(row=2, column=1, pady=2)

tk.Label(root, text="b:").grid(row=2, column=2, pady=2)
entry_b = tk.Entry(root, width=5)
entry_b.insert(0, "10")
entry_b.grid(row=2, column=3, pady=2)

# OPERATION MODE: Addition or Multiplication
tk.Label(root, text="Operation:").grid(row=3, column=0, pady=(10, 2))
mode = tk.StringVar(value="Addition")
mode_menu = ttk.Combobox(root, textvariable=mode, values=["Addition", "Multiplication"], state="readonly")
mode_menu.grid(row=3, column=1, pady=(10, 2))

# SCALAR n (used only if multiplication is selected)
tk.Label(root, text="n:").grid(row=3, column=2, pady=(10, 2))
entry_n = tk.Entry(root, width=5)
entry_n.insert(0, "2")
entry_n.grid(row=3, column=3, pady=(10, 2))

# POINT P
tk.Label(root, text="P:").grid(row=4, column=0)
entry_px = tk.Entry(root, width=5)
entry_px.insert(0, "1")
entry_px.grid(row=4, column=1)
entry_py = tk.Entry(root, width=5)
entry_py.insert(0, "2")
entry_py.grid(row=4, column=2, columnspan=2)

# POINT Q (Only for addition)
tk.Label(root, text="Q:").grid(row=5, column=0)
entry_qx = tk.Entry(root, width=5)
entry_qx.insert(0, "3")
entry_qx.grid(row=5, column=1)
entry_qy = tk.Entry(root, width=5)
entry_qy.insert(0, "4")
entry_qy.grid(row=5, column=2, columnspan=2)

# RESULT R
tk.Label(root, text="R = ").grid(row=6, column=0, pady=(10, 0))
result_x = tk.StringVar()
result_y = tk.StringVar()
tk.Entry(root, textvariable=result_x, width=8, state="readonly").grid(row=6, column=1, pady=(10, 0))
tk.Entry(root, textvariable=result_y, width=8, state="readonly").grid(row=6, column=2, columnspan=2, pady=(10, 0))

# COMPUTE BUTTON
tk.Button(root, text="Compute", command=compute).grid(row=7, column=0, columnspan=4, pady=10)

root.mainloop()
