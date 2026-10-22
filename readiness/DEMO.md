# ⏱️ Readiness Assistant — 60-Second Reviewer Walkthrough

> **Notice:** Demo with synthetic data. Not for real safety decisions.

Welcome to the **Readiness Assistant** demo. This walkthrough allows an evaluator to experience the core product promise in under 60 seconds:
> *"The right maintenance knowledge, for the right equipment, at the moment a fault occurs, with evidence behind every recommendation."*

---

## 🚀 Quick Setup (1 Command)
```bash
docker compose up -d
```
Open your browser to:
- 📱 **Technician Copilot**: `http://localhost:3000` (select "Technician Copilot" tab)
- 🖥️ **Supervisor Reliability Board**: `http://localhost:3000` (select "Supervisor Dashboard" tab)
- 🔌 **FastAPI Interactive Docs**: `http://localhost:8000/docs`

---

## ⚡ The 3-Step Demo Walkthrough

### Step 1: Diagnose Pump P-101 (Graph Decides, LLM Explains)
1. In the **Technician Copilot**, select equipment **`P-101`** (Primary Boiler Feed Pump A, model `ApexFlow-CP200`).
2. Tap the quick symptom pill: **"Severe radial vibration"** (or enter: *"Violent radial vibration on pump drive-end bearing"* with alarm `ALM-VIB-101`).
3. Click **"Diagnose Asset"**.
4. **Observe the Sub-Second Real-Time Execution:**
   - **Engine Overhead**: < 15 ms (deterministic BM25 + alias traversal, zero LLM delay).
   - **First Token Latency**: **~711 ms** (p50 measured via Google Gemma 4 HTTP/2 stream).
   - **Latency Badge**: Green pill confirming first token, total duration, and cache status.
   - **Candidate Causes**: Deterministically ranked:
     - 🥇 `CAUSE-BRG-WEAR` (Bearing Ball & Race Fatigue Wear) — **HIGH** evidence strength.
     - 🥈 `CAUSE-SHAFT-MISALIGN` (Shaft Angular / Radial Misalignment) — **MODERATE** evidence strength.
   - **Evidence Reasons**: Lists exact historical incidents (`INC-0001`, `INC-0007`) and applicable manual citations.
   - **Source Grounding**: Clickable citation to manual `DOC-MAN-CP200-B` §4.2.

---

### Step 2: The Safety Gate Interception (Stop-Work Gatekeeper)
1. Tap the quick scenario pill: **"Acrid smoke & arcing (STOP WORK)"** (alarm `ALM-ELEC-ARC`).
2. Click **"Diagnose Asset"**.
3. **Observe the Safety Gate:**
   - The AI diagnosis is **HALTED**.
   - A bright red pulsing banner displays: **"CRITICAL SAFETY STOP-WORK HAZARD DETECTED"**.
   - Mandatory LOTO isolation procedure `PROC-LOTO-ISOLATE` (§2.1) is pushed to the top.
   - Technician is instructed to evacuate and escalate immediately to electrical personnel.

---

### Step 3: Closed-Loop Maintenance Memory (Technician -> Supervisor Gate -> Graph Precedent)
The AI and technician **never mark an asset ready or repaired**. Only a supervisor approval can establish verified graph memory:

1. Under the diagnosis for **`P-101`**, scroll to **"Record Field Finding & Measurements"**:
   - Type: `Physical Measurement`
   - Parameter: `radial_vibration_mm_s`
   - Value: `7.6 mm/s`
   - Notes: *"Bearing temperature measured 86°C. High acoustic emissions."*
   - Click **"Record Finding"**.
2. Click **"Generate Draft Work Order"**:
   - Work order generated (e.g. `WO-A1B2C3`).
   - Select confirmed root cause: `CAUSE-BRG-WEAR`.
   - Action taken: *"Replaced degraded 6312 ball bearing with new 6312-C3 bearing using induction heater; aligned coupling."*
   - Parts used: `PART-BRG-6312`.
   - Click **"Submit Resolution"** (moves to `pending_approval`).
3. Switch role to **Elena Rostova (Supervisor)** via top-right dropdown, and select the **Supervisor Dashboard**:
   - Open the **"Approvals Queue"** tab (displays `1` pending badge).
   - Review the technician's submitted work order.
   - Click **"Verify & Approve"** (records 2.5 hours downtime and notes).
4. **Observe the Incremental Graph Hot-Swap:**
   - The in-memory `JsonGraphStore` atomically gains a new **Verified Outcome edge**:
     - `origin`: `technician_reported`
     - `verification_status`: `verified`
     - `approved_by`: `supervisor`
   - Switch to the **"Graph Explorer (@xyflow)"** tab:
     - Click on the new emerald green node `INC-...` or edge to inspect full provenance metadata.
   - Switch to the **"Readiness Board"** tab:
     - Notice asset `P-101` readiness score immediately recovers to **100/100 (Optimal)**!

---

## 🎯 Deliberate Traps Verified

| Trap | Description | How to Verify in Demo |
| :--- | :--- | :--- |
| **Trap 1: Wrong-Model Procedure Exclusion** | `PROC-VFD-HARMONIC-TUNING` applies **only** to motor `DuraTorq-IM50-VFD`. | Diagnose `M-104` (standard `DuraTorq-IM50`) with VFD whine. Notice `PROC-VFD-HARMONIC-TUNING` is strictly filtered out and never recommended. |
| **Trap 2: Superseded Manual Revision** | Manual `DOC-MAN-CP200-A` (0.080mm tolerance) is superseded by `DOC-MAN-CP200-B` (0.038mm). | View asset **`P-102`** on the Supervisor Readiness Board. It is flagged with **"SUPERSEDED_MANUAL_IN_USE"** and penalized with a 20-point readiness reduction. |
| **Trap 3: Model-Specific Root Causes** | Identical symptom *"Discharge pressure needle surging"* maps to different root causes per model. | Diagnose `P-101` (`ApexFlow-CP200`) -> outputs `CAUSE-IMP-VANE-RESONANCE`.<br>Diagnose `P-103` (`ApexFlow-CP100`) -> outputs `CAUSE-VALVE-FLUTTER`. |

---

## 📊 Live Metrics & Latency
To inspect live p50/p95 latency metrics from the backend:
```bash
curl http://localhost:8000/api/metrics
```
Or execute the automated latency benchmark:
```bash
docker compose exec backend python scripts/bench.py
```
*(Real measured numbers: p50 First Token = 711.8 ms, p95 First Token = 1515.8 ms, Total p95 = 1515.8 ms < 4000 ms target).*
