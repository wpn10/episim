# ODE Solver Guide for Epidemic Models

## scipy.integrate.solve_ivp

The standard interface for solving initial value problems in Python.

### Basic Usage

```python
from scipy.integrate import solve_ivp
import numpy as np

def derivatives(t, y, params):
    S, I, R = y
    N = sum(y)
    beta, gamma = params['beta'], params['gamma']
    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]

t_span = (0, 365)
y0 = [999999, 1, 0]
params = {'beta': 0.3, 'gamma': 0.1}
t_eval = np.linspace(t_span[0], t_span[1], 1000)

sol = solve_ivp(
    fun=lambda t, y: derivatives(t, y, params),
    t_span=t_span,
    y0=y0,
    method='RK45',
    t_eval=t_eval,
    max_step=1.0,
    rtol=1e-8,
    atol=1e-8
)

# sol.t = time points array
# sol.y = solution array, shape (n_compartments, n_points)
# sol.y[0] = S(t), sol.y[1] = I(t), etc.
```

### Method Selection

| Method | When to Use | Notes |
|--------|------------|-------|
| `RK45` (default) | Most epidemic models | 4th-order Runge-Kutta, good general choice |
| `RK23` | Quick estimates, less accuracy needed | Faster but less accurate |
| `DOP853` | High accuracy needed | 8th-order, good for smooth problems |
| `Radau` | Stiff systems | Implicit Runge-Kutta, auto stiffness detection |
| `BDF` | Very stiff systems | Backward differentiation, good for stiff ODEs |
| `LSODA` | Unknown stiffness | Auto-switches between stiff and non-stiff |

**When is an epidemic model stiff?**
- Very fast and very slow dynamics coexist (e.g., rapid transmission + slow waning immunity)
- Very large population with small initial infected (S ≈ N, I ≈ 1)
- Compartments with very different time scales (hours vs. months)
- If `RK45` takes many steps or fails, try `Radau` or `BDF`

### Key Parameters

**`max_step`** — Maximum allowed step size.
- Set `max_step=1.0` (1 day) for daily-scale epidemic models
- Prevents the solver from jumping over rapid dynamics (e.g., missing the infection peak)
- Critical for getting accurate peak timing

**`rtol` and `atol`** — Relative and absolute error tolerances.
- Default: `rtol=1e-8, atol=1e-8` for high accuracy
- For quick exploration: `rtol=1e-6, atol=1e-6`
- Tighter tolerances = more accurate but slower

**`t_eval`** — Time points at which to store the solution.
- Use `np.linspace(0, simulation_days, 1000)` for smooth plots
- Does NOT affect solver step size (only output points)

**`dense_output=True`** — Enables interpolation between solver steps.
- Use `sol.sol(t)` to evaluate at any time point after solving

### Common Pitfalls

1. **Negative compartment values:** ODE solvers can produce small negative values due to numerical error. Clamp with `max(0, value)` in post-processing, not inside the derivatives function.

2. **Population not conserved:** If `sum(y)` drifts from N, check that all flows out of one compartment enter another. Use `N = params['population']` as a constant rather than `sum(y)` if conservation is guaranteed.

3. **Division by zero:** When a compartment approaches 0, terms like `β*S*I/N` naturally go to 0. No special handling needed.

4. **Very large populations:** With N > 10^8, use `rtol=1e-10` or normalize the system (divide all compartments by N to work with fractions).

5. **Time-varying parameters:** Pass a function `beta(t)` and call it inside derivatives. The solver handles variable step sizes automatically.

### Output Processing

```python
# Convert solve_ivp output to a dict keyed by compartment name
compartments = ["S", "I", "R"]
results = {"t": sol.t}
for i, name in enumerate(compartments):
    results[name] = sol.y[i]

# Compute metrics
peak_idx = np.argmax(results["I"])
peak_day = results["t"][peak_idx]
peak_cases = results["I"][peak_idx]
attack_rate = 1 - results["S"][-1] / params['population']
```

### Wrapper Pattern for Generated Simulators

```python
def run_simulation(params, y0, t_span, num_points=1000):
    from scipy.integrate import solve_ivp
    import numpy as np
    from model import COMPARTMENTS, derivatives

    t_eval = np.linspace(t_span[0], t_span[1], num_points)
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, params),
        t_span=t_span,
        y0=y0,
        method='RK45',
        t_eval=t_eval,
        max_step=1.0,
        rtol=1e-8,
        atol=1e-8
    )
    results = {"t": sol.t}
    for i, name in enumerate(COMPARTMENTS):
        results[name] = sol.y[i]
    return results
```
