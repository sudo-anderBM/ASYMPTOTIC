# ASYMPTOTIC
### Physics-Informed Anomaly Detection for Resource-Efficient AI Infrastructure

**Can simple statistical models detect small infrastructure anomalies at a fraction of the computational cost?**

ASYMPTOTIC is an experimental framework for comparing five anomaly detection approaches for simulated AI data center operations. It focuses on water leakage detection, statistical residuals, detection performance, false alarms, and computational cost.

The project explores a practical question: **does a more complex detector necessarily provide better results than a lightweight model grounded in expected system behavior?**

> **Research prototype.** All operational data are synthetic. Results are experimental, energy and carbon estimates depend on explicit assumptions, and alerts require human review. This software is not designed to control or diagnose real infrastructure.

---

## Overview

AI infrastructure depends on cooling systems that consume resources and must operate reliably. Detecting unusual water consumption or energy inefficiency can help identify situations that deserve further investigation.

Fixed thresholds are easy to implement, but small deviations may remain below their alert limits. More sophisticated machine learning models offer another approach, although their computational cost and detection performance must be evaluated rather than assumed.

ASYMPTOTIC compares five detectors under controlled synthetic scenarios, including a more difficult data-generation regime.

### Research objectives

- Compare detection performance across five approaches.
- Evaluate sensitivity to small water leakage scenarios.
- Measure false alarms and detection delay.
- Benchmark fitting and prediction costs.
- Investigate robustness under noisier, nonlinear synthetic conditions.
- Provide explanations that compare observed values with expected behavior.

## Detection methods

| Detector | Approach | Main characteristic |
|---|---|---|
| Fixed rules | PUE/WUE thresholds | Simple, interpretable baseline |
| Isolation Forest | Unsupervised machine learning | General-purpose anomaly detection |
| Residual 3σ | Statistical model + standardized residual | Detects deviations from expected behavior |
| Residual CUSUM | Cumulative deviation monitoring | Accumulates small persistent changes |
| Simple z-score | Standardized statistical deviation | Lightweight statistical baseline |

### The central idea: residual analysis

A model estimates expected water consumption from operational variables such as IT energy, workload, and temperature.

The residual measures the difference between the observed and expected values:

\[
r_t = y_t - \hat{y}_t
\]

where \(y_t\) is the observed measurement and \(\hat{y}_t\) is the estimated normal value.

The standardized residual is:

\[
z_t = \frac{r_t}{\sigma_r}
\]

Here, \(\sigma_r\) represents the residual scale estimated from the reference data. The 3σ detector flags sufficiently large deviations, while CUSUM accumulates evidence of persistent deviations over time.

**Why it matters:** an anomaly can be detected because a measurement contradicts the expected behavior of the system, even when it does not cross a fixed operational threshold.

---

## Experimental results

The following results come from a synthetic water-leakage sweep using 10 random seeds and 90 evaluated events per point. They summarize one experimental configuration, not a universal performance guarantee.

### Water-leakage detection

| Detector | Normal regime | Difficult regime | Approx. fit + prediction |
|---|---|---|---:|
| Fixed rules | 0% through 50% leakage | 0% through 30% | 0.25 ms |
| Isolation Forest | 31–49% | 28–53% | 103 ms |
| Residual 3σ | 88% at 5%; 100% from 10% | 39% at 10%; 92% at 20% | 5 ms |
| Residual CUSUM | 100%; 0.2–0.35 false alarms/day | 100% from 20% | 6.5 ms |
| Simple z-score | 100% from 30% | 100% from 50% | 1.3 ms |

*Detection rates depend on leakage magnitude and experimental conditions. The table reports selected points from the sweep; it does not imply identical performance across every magnitude.*

### What the results suggest

- **Fixed thresholds can miss subtle anomalies.** In the tested configuration, small leakage scenarios did not trigger the baseline rules.
- **Residual 3σ provides a useful accuracy–cost trade-off.** It detected 88% of events at 5% leakage in the normal regime, with approximately 5 ms of combined fitting and prediction time.
- **CUSUM is sensitive to persistent changes.** Its higher sensitivity comes with a higher false-alarm rate in the reported normal-regime experiment.
- **The difficult regime changes the picture.** Added noise and nonlinear behavior reduce the performance of the linear residual model.
- **Computational simplicity matters.** In this benchmark, residual 3σ required roughly 20 times less fitting and prediction time than Isolation Forest.

These findings motivate further testing with more realistic data, independent validation, and additional operating conditions. They do not establish that one detector is universally superior.

---

## Architecture

The application separates the API, detection logic, scenario generation, event evaluation, and benchmarking.

```text
ASYMPTOTIC/
├── greenai/
│   ├── detectors.py       # Five detection approaches
│   ├── base_data.py       # Synthetic reference data
│   ├── scenarios.py       # Controlled anomaly injection
│   ├── events.py          # Event-level evaluation
│   ├── explain.py         # Observed vs. expected explanations
│   ├── bench.py           # Performance and uncertainty metrics
│   ├── service.py         # Application services
│   └── sweep.py           # Multi-seed benchmark experiments
├── stack_b_api_web/
│   └── main.py            # FastAPI application
├── static/
│   └── mock/              # Illustrative frontend responses
├── tests/                 # Automated tests
└── results/               # Benchmark sweep outputs
```

The project also integrates the CIFOX participant kit's shared data and application components. Exact files and directories may evolve as the project develops.

### API

The application exposes four main endpoints:

| Endpoint | Purpose |
|---|---|
| `/api/detectors` | Detector information and available methods |
| `/api/scenario` | Generate or evaluate a controlled scenario |
| `/api/explain` | Explain an observed anomaly |
| `/api/sweep` | Run a parameter sweep |

All responses represent simulated data and use `simulated: true`. Dates are serialized in ISO 8601 format, unknown values are represented as `null`, and invalid parameters return HTTP 422 responses.

---

## Methodology and reproducibility

The benchmark separates model fitting from evaluation to reduce data leakage.

1. Generate synthetic operational data for multiple sites.
2. Split the data into a clean reference period and an evaluation period.
3. Fit detectors using reference data only.
4. Inject controlled anomalies into evaluation windows.
5. Evaluate detection rates, false alarms, detection delays, and missed excess consumption.
6. Repeat experiments across random seeds and operating regimes.
7. Measure runtime and Python allocation peaks.

The dataset configuration described in the project contains 504 rows: 168 hours across three simulated sites.

| Site | Cooling configuration |
|---|---|
| SIM-A | Air cooling |
| SIM-B | Evaporative cooling |
| SIM-C | Liquid cooling |

The evaluation configuration uses a 72-hour reference period and a 96-hour evaluation period, with 21 injected anomalies in the original kit split. The benchmark can also generate independent synthetic scenarios.

### Preventing label leakage

Scenario labels and anomaly ground-truth fields must not be used as detector inputs. Operational metadata that directly reveals the injected scenario can also invalidate a comparison.

For this reason, the detector comparison disables the OT-event shortcut (`use_ot=False`). The objective is to evaluate the behavior of the detectors, not their ability to recover information already encoded in a label.

### Metrics

- **Detection rate:** proportion of injected events successfully detected.
- **False alarms per day:** alerts generated during normal operation.
- **Detection delay:** elapsed time between the beginning of an event and its detection.
- **Missed excess consumption:** simulated excess resource consumption not detected.
- **Runtime:** measured fitting and prediction duration.
- **Memory:** peak Python-traced allocation, not total process RAM.
- **Energy and carbon:** estimates derived from explicit assumptions, not direct physical measurements.

Confidence intervals and repeated runs help characterize uncertainty. A single benchmark run should never be treated as definitive evidence.

---

## Installation

### Requirements

- Python 3.12 recommended by the original kit.
- Python 3.13 was used in the development environment for the reported local tests and timings.
- Git.
- A supported operating system and compatible Python packages.

No GPU, paid API key, cloud account, or Node.js runtime is required for the Python API and static web interface.

From the repository root, create a virtual environment and install the project's declared dependencies:

**Windows PowerShell**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

**Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install the dependencies from the applicable requirements files provided by the repository. For example, if the backend requirements are maintained in `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

If the repository uses separate requirements files, install the backend and optional machine-learning dependencies specified by those files instead. Do not install optional dependencies unless the selected experiment requires them.

### Run the application

From the repository root, with the environment activated:

```bash
python -m uvicorn stack_b_api_web.main:app --host 127.0.0.1 --port 8000
```

Open the local application in your browser:

```text
http://127.0.0.1:8000/static/deteccion.html
```

The API is bound to localhost, making it suitable for local development and demonstrations.

### Run the tests

With the development dependencies installed:

```bash
python -m pytest tests -q
```

The backend development checkpoint recorded 39 passing tests before the final sweep-related integration work. Run the command above against the current checkout to verify its actual state.

### Run a benchmark sweep

Use the command-line options supported by the current implementation:

```bash
python -m greenai.sweep --help
```

The sweep module evaluates leakage magnitudes across multiple seeds and operating regimes. Generated JSON results are stored under `results/` when configured to do so.

For reproducible comparisons, retain the generated results, the random seeds, the environment details, and the exact detector parameters.

---

## Design principles

**Interpretability over black-box confidence.** Detection should be explainable in terms of observed measurements and expected behavior.

**Fair comparisons.** Every detector must receive the same permitted input data and evaluation events.

**Efficiency is part of the evaluation.** A model's value depends on both detection quality and the resources needed to produce it.

**Uncertainty must be visible.** Results should include their operating conditions and limitations rather than being presented as universal guarantees.

**Human oversight remains essential.** An alert is a signal for investigation, not a diagnosis of an actual leak or equipment failure.

---

## Limitations

ASYMPTOTIC is a research prototype, and its conclusions are constrained by the experimental design.

1. **Synthetic data only.** Performance has not been established on real data center telemetry.
2. **Limited robustness validation.** The difficult regime uses another synthetic generator; it is not a substitute for independent real-world validation.
3. **Linear residual model.** Nonlinear relationships, changing baselines, and operating drift may reduce detection performance.
4. **Hardware-dependent timing.** Reported runtimes were measured on a Windows 11 development machine with Python 3.13. They will vary across systems.
5. **Estimated energy and carbon.** These values depend on assumed power and emissions factors and are not direct measurements.
6. **Memory measurement scope.** `tracemalloc` measures Python-traced allocations, not complete process memory usage.
7. **No physical water-per-query measurement.** The prototype does not model a deployed inference service's utilization, cooling allocation, or shared facility overhead sufficiently to attribute water consumption to an individual AI request.
8. **Human verification required.** No detector should independently trigger operational interventions based on these experimental results.

The results support further investigation into lightweight, physics-informed and statistical detection methods. They do not certify infrastructure safety, establish causal relationships, or justify engineering decisions without additional evidence.

---

## Project context

ASYMPTOTIC builds on ideas explored in ThermoShield, a previous educational prototype involving heat diffusion, simulated sensors, and residual-based anomaly detection.

The residual approach was adapted to the CIFOX synthetic operations dataset. The current project extends that foundation into a controlled comparison of statistical and machine-learning detectors, with an emphasis on resource efficiency and transparent evaluation.

The project is intended for experimentation, education, and further research in applied mathematics, machine learning, and sustainable computing.

## License

Original project code and documentation are distributed under the MIT License, subject to the repository's actual license files and the licenses of third-party dependencies.

See the repository's dependency documentation for applicable third-party notices.

---

**ASYMPTOTIC — Measure the deviation. Explain the signal. Account for the cost.**
