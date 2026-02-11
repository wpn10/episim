# Base Epidemic Models

## SIR (Susceptible–Infectious–Recovered)

**Compartments:** S, I, R

**ODE System:**
```
dS/dt = -β * S * I / N
dI/dt =  β * S * I / N - γ * I
dR/dt =  γ * I
```

**Parameters:**
- `beta` (β): Transmission rate (contacts × probability per contact per day)
- `gamma` (γ): Recovery rate (1/γ = average infectious period in days)
- `N`: Total population (S + I + R, constant)

**Basic reproduction number:** R0 = β / γ

**Python implementation:**
```python
def derivatives(t, y, params):
    S, I, R = y
    N = sum(y)
    beta = params['beta']
    gamma = params['gamma']
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return [dSdt, dIdt, dRdt]
```

---

## SEIR (Susceptible–Exposed–Infectious–Recovered)

**Compartments:** S, E, I, R

**ODE System:**
```
dS/dt = -β * S * I / N
dE/dt =  β * S * I / N - σ * E
dI/dt =  σ * E - γ * I
dR/dt =  γ * I
```

**Parameters:**
- `beta` (β): Transmission rate
- `sigma` (σ): Incubation rate (1/σ = average latent period in days)
- `gamma` (γ): Recovery rate (1/γ = average infectious period in days)
- `N`: Total population

**Basic reproduction number:** R0 = β / γ (same as SIR when E→I is not rate-limiting)

**Python implementation:**
```python
def derivatives(t, y, params):
    S, E, I, R = y
    N = sum(y)
    beta = params['beta']
    sigma = params['sigma']
    gamma = params['gamma']
    dSdt = -beta * S * I / N
    dEdt = beta * S * I / N - sigma * E
    dIdt = sigma * E - gamma * I
    dRdt = gamma * I
    return [dSdt, dEdt, dIdt, dRdt]
```

---

## SEIRS (Susceptible–Exposed–Infectious–Recovered–Susceptible)

**Compartments:** S, E, I, R (R returns to S via waning immunity)

**ODE System:**
```
dS/dt = -β * S * I / N + ξ * R
dE/dt =  β * S * I / N - σ * E
dI/dt =  σ * E - γ * I
dR/dt =  γ * I - ξ * R
```

**Parameters:**
- `beta` (β): Transmission rate
- `sigma` (σ): Incubation rate
- `gamma` (γ): Recovery rate
- `xi` (ξ): Immunity waning rate (1/ξ = average duration of immunity in days)

**Python implementation:**
```python
def derivatives(t, y, params):
    S, E, I, R = y
    N = sum(y)
    beta = params['beta']
    sigma = params['sigma']
    gamma = params['gamma']
    xi = params['xi']
    dSdt = -beta * S * I / N + xi * R
    dEdt = beta * S * I / N - sigma * E
    dIdt = sigma * E - gamma * I
    dRdt = gamma * I - xi * R
    return [dSdt, dEdt, dIdt, dRdt]
```

---

## SIS (Susceptible–Infectious–Susceptible)

**Compartments:** S, I (no lasting immunity)

**ODE System:**
```
dS/dt = -β * S * I / N + γ * I
dI/dt =  β * S * I / N - γ * I
```

**Parameters:**
- `beta` (β): Transmission rate
- `gamma` (γ): Recovery rate

**Basic reproduction number:** R0 = β / γ

**Python implementation:**
```python
def derivatives(t, y, params):
    S, I = y
    N = sum(y)
    beta = params['beta']
    gamma = params['gamma']
    dSdt = -beta * S * I / N + gamma * I
    dIdt = beta * S * I / N - gamma * I
    return [dSdt, dIdt]
```

---

## Common Extensions

- **Vital dynamics:** Add birth rate μ*N to S, subtract μ from each compartment (for long-term endemic models).
- **Vaccination:** Add a vaccinated compartment V, or move a fraction of S to R at rate ν.
- **Quarantine/Isolation:** Split I into detected (quarantined) and undetected sub-compartments.
- **Age structure:** Replicate compartments per age group with a contact matrix.
- **Time-varying parameters:** β(t) for interventions (lockdowns, seasonal forcing).
