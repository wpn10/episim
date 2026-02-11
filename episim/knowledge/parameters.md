# Epidemic Parameter Ranges by Disease

Reference ranges from WHO, CDC, and peer-reviewed literature. Use these to sanity-check extracted parameter values.

## COVID-19 (SARS-CoV-2)

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 (wild type) | 2.0–3.5 | — | WHO, Li et al. 2020 |
| R0 (Delta) | 5.0–8.0 | — | Liu & Rocklöv 2021 |
| R0 (Omicron) | 8.0–15.0 | — | Liu & Rocklöv 2022 |
| Incubation period (1/σ) | 3–7 | days | Lauer et al. 2020 |
| Infectious period (1/γ) | 7–14 | days | WHO |
| Infection fatality rate | 0.5–1.5% | — | Meyerowitz-Katz & Merone 2020 |
| Hospitalization rate | 5–20% | — | CDC |

## Influenza (Seasonal)

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 | 1.2–2.0 | — | Biggerstaff et al. 2014 |
| Incubation period (1/σ) | 1–4 | days | CDC |
| Infectious period (1/γ) | 3–7 | days | Carrat et al. 2008 |
| Attack rate | 5–20% | — | CDC seasonal estimates |
| Case fatality rate | 0.01–0.1% | — | WHO |

## Dengue

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 | 1.5–6.0 | — | Johansson et al. 2011 |
| Intrinsic incubation (1/σ) | 4–10 | days | WHO |
| Infectious period (1/γ) | 3–7 | days | WHO |
| Extrinsic incubation (mosquito) | 8–12 | days | Chan & Johansson 2012 |
| Case fatality (severe) | 1–5% | — | WHO |

## Ebola

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 | 1.5–2.5 | — | WHO Ebola Response Team 2014 |
| Incubation period (1/σ) | 6–21 | days | WHO |
| Infectious period (1/γ) | 4–10 | days | WHO |
| Case fatality rate | 25–90% | — | WHO (varies by outbreak) |

## Malaria (P. falciparum)

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 | 1–3000 (highly variable) | — | Smith et al. 2007 |
| Intrinsic incubation | 7–30 | days | CDC |
| Infectious period | 1–3 | years (untreated) | WHO |
| Case fatality (untreated severe) | 15–30% | — | WHO |

## Measles

| Parameter | Range | Unit | Source |
|-----------|-------|------|--------|
| R0 | 12–18 | — | Guerra et al. 2017 |
| Incubation period (1/σ) | 10–14 | days | CDC |
| Infectious period (1/γ) | 6–8 | days | CDC |
| Case fatality rate | 0.1–0.3% (developed) | — | WHO |

## General Parameter Relationships

- **R0 = β / γ** for simple SIR/SIS models
- **R0 = (β × σ) / (γ × (σ + μ))** for SEIR with vital dynamics
- **Attack rate ≈ 1 - S(∞)/N** — final size of epidemic
- **Peak timing** scales inversely with R0: higher R0 → earlier peak
- **Herd immunity threshold = 1 - 1/R0**
