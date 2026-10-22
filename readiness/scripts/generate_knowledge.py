"""
generate_knowledge.py
Generates the synthetic maintenance knowledge pack for Readiness Assistant:
- Manual excerpts (with doc_id, revision, applicable models, sections)
- Symptoms with plain-language aliases & alarm codes
- Candidate causes with source doc_id + section
- Procedures with safety precautions, expertise, steps, and stop-work conditions
- Past incidents with confirmed causes & supervisor verification flags
- Assets with models, revisions, and inspection histories

Includes deliberate traps:
1. Trap 1: PROC-VFD-HARMONIC-TUNING applies ONLY to DuraTorq-IM50-VFD (not DuraTorq-IM50).
2. Trap 2: DOC-MAN-CP200-A is superseded by DOC-MAN-CP200-B (clearance updated 0.08mm -> 0.04mm).
3. Trap 3: Discharge pulsation causes differ: ApexFlow-CP200 is CAUSE-IMP-VANE-RESONANCE,
   while ApexFlow-CP100 is CAUSE-VALVE-FLUTTER.
"""

import os
import json
import sys
from pathlib import Path

# Add backend directory to path to import schemas
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.graph.schema import (
    DocumentSection, ManualDocument, Symptom, Cause, ProcedureStep,
    Procedure, Part, Incident, Asset, AssetInspection, KnowledgePack
)


def create_knowledge_pack() -> KnowledgePack:
    # 1. Manual Documents
    manuals = [
        ManualDocument(
            doc_id="DOC-MAN-SAFETY-01",
            title="Industrial Plant Emergency Isolation & Stop-Work Standard Operating Procedure",
            revision="Rev 2.1",
            effective_date="2024-01-01",
            applicable_models=["*"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-SAFE-01",
                    title="Emergency Stop-Work & Lockout/Tagout Protocol",
                    content="MANDATORY STOP-WORK: If abnormal thermal signatures, burning odor, visible smoke, electrical arcing, or sudden mechanical shaft seizure is detected, the technician MUST immediately initiate emergency stop, de-energize breaker, and install Lockout/Tagout (LOTO) padlocks. Do not attempt diagnostic measurement while energized under active fault conditions. Immediately escalate to the Plant Electrical Supervisor."
                ),
                DocumentSection(
                    section_id="SEC-SAFE-02",
                    title="Hazardous Fluid Containment & Personal Protective Equipment",
                    content="For high-pressure hydrocarbon and chemical feed pumps, barrier fluid or process liquid leakage exceeding 5 drops per minute requires immediate containment tray placement and PPE Level C (chemical splash face shield and nitrile gloves)."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-CP200-A",
            title="ApexFlow CP-200 Centrifugal Feed Pump Maintenance Manual (Superseded)",
            revision="Rev A",
            effective_date="2021-04-10",
            applicable_models=["ApexFlow-CP200"],
            superseded_by="DOC-MAN-CP200-B",
            sections=[
                DocumentSection(
                    section_id="SEC-CP200-A-01",
                    title="Obsolete Bearing Clearance Tolerances",
                    content="SUPERSEDED SPECIFICATION: Maximum radial bearing clearance was formerly 0.080 mm. This specification was found to allow excessive shaft whip under cavitation and has been rescinded."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-CP200-B",
            title="ApexFlow CP-200 Centrifugal Heavy-Duty Feed Pump Operations & Maintenance Manual",
            revision="Rev B",
            effective_date="2024-01-15",
            applicable_models=["ApexFlow-CP200"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-CP200-01",
                    title="Pump Alignment & Dynamic Vibration Limits",
                    content="ApexFlow CP-200 requires laser coupling alignment within 0.05 mm angular and 0.03 mm radial offset. ISO 10816-3 overall vibration velocity must remain below 4.5 mm/s RMS in zone A/B. Vibration exceeding 7.1 mm/s RMS indicates severe mechanical unbalance or bearing degradation."
                ),
                DocumentSection(
                    section_id="SEC-CP200-02",
                    title="Hydraulic Performance, Cavitation & NPSH Requirements",
                    content="Net Positive Suction Head required (NPSHr) is 3.2 meters at best efficiency point. Suction pressure dropping below 1.2 bar gauge results in cavitation bubble collapse against the first-stage impeller eye, characterized by popping/gravel rattling noise and hydraulic shock pulses."
                ),
                DocumentSection(
                    section_id="SEC-CP200-03",
                    title="Mechanical Seal & API Plan 11 Flush Regulation",
                    content="Fitted with cartridge mechanical seal. API Plan 11 flush circulation delivers process fluid from discharge orifice back to seal chamber. Orifice blockage starves seal faces of lubrication, causing dry running, face scorch marks, and subsequent fluid leakage from the gland drain."
                ),
                DocumentSection(
                    section_id="SEC-CP200-04",
                    title="Bearing Housing Maintenance & Active Clearances",
                    content="Equipped with deep-groove 6312 ball bearings (drive end) and paired angular contact 7312 bearings (non-drive end). Maximum allowable radial play is 0.038 mm (nominal 0.025 mm). Relubricate with synthetic ISO VG 68 polyurea grease every 2,000 operating hours. Overgreasing induces churning and temperatures above 85°C."
                ),
                DocumentSection(
                    section_id="SEC-CP200-05",
                    title="Impeller Vane Pass Pressure Pulsation & Acoustic Resonance",
                    content="CP-200 5-vane impellers operating below 65% minimum continuous stable flow (MCSF) generate acoustic pressure pulsation at 5x running speed. If pulsation amplitude exceeds 1.5 bar peak-to-peak at the discharge nozzle, verify minimum flow bypass valve position and examine diffuser ring for erosion."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-CP100-A",
            title="ApexFlow CP-100 Light Industrial Utility Pump Maintenance Guide",
            revision="Rev A",
            effective_date="2022-06-01",
            applicable_models=["ApexFlow-CP100"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-CP100-01",
                    title="General Construction & Belt Drive Overview",
                    content="ApexFlow CP-100 is an end-suction single-stage utility pump. Unlike CP-200, CP-100 incorporates an external spring-loaded swing check valve directly bolted to the discharge flange."
                ),
                DocumentSection(
                    section_id="SEC-CP100-02",
                    title="Discharge Check Valve Flutter & Line Pulsation",
                    content="Discharge pressure pulsations on CP-100 models are predominantly caused by worn hinge pins or broken return springs in the discharge swing check valve, creating high-frequency disc chatter and gauge oscillation. Do not confuse with impeller acoustic resonance."
                ),
                DocumentSection(
                    section_id="SEC-CP100-03",
                    title="Packing Gland & Component Seal Adjustments",
                    content="Component mechanical seal with external spring. Allow 10-15 drops per minute leakage during running-in; steady stream signifies cracked silicon carbide primary ring."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-IM50-C",
            title="DuraTorq IM-50 3-Phase Squirrel Cage Induction Motor Technical Specification",
            revision="Rev C",
            effective_date="2024-03-01",
            applicable_models=["DuraTorq-IM50"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-IM50-01",
                    title="Electrical Safety, Voltage Unbalance & Winding Temperature",
                    content="DuraTorq IM-50 is a 37kW, 400V 50Hz, 4-pole Class F insulation motor. Phase-to-phase resistance must balance within 1.5%. Phase voltage unbalance exceeding 1% causes a 6% increase in winding temperature. RTD temperature trip setpoint is 130°C."
                ),
                DocumentSection(
                    section_id="SEC-IM50-02",
                    title="Insulation Resistance Megohmmeter Testing",
                    content="Measure winding insulation resistance with 1000V DC Megger. Minimum acceptable insulation resistance at 40°C is 100 Megaohms. Values below 5 Megaohms indicate severe moisture ingress or winding insulation breakdown; do not re-energize."
                ),
                DocumentSection(
                    section_id="SEC-IM50-03",
                    title="Motor Bearings, End-Shield Tolerances & Air Gap",
                    content="Drive-end bearing 6310 C3 clearance. Air gap uniformity between stator and rotor must be checked at 4 cardinal positions; deviation exceeding 10% indicates worn bearing bracket or bent rotor shaft."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-IM50-VFD-A",
            title="DuraTorq IM-50-VFD Inverter-Duty Drive & Carrier Frequency Supplement",
            revision="Rev A",
            effective_date="2024-04-01",
            applicable_models=["DuraTorq-IM50-VFD"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-VFD-01",
                    title="PWM Carrier Frequency Harmonics & Shaft Voltage Discharge",
                    content="CRITICAL APPLICABILITY: This section applies solely to DuraTorq-IM50-VFD equipped with external inverter drives. High PWM carrier frequency (>8 kHz) induces common-mode shaft voltages causing electrical discharge machining (EDM) fluting across bearing raceways. Inspect carbon grounding brush and verify carrier setting."
                )
            ]
        ),
        ManualDocument(
            doc_id="DOC-MAN-SEAL-01",
            title="ApexSeal Cartridge Mechanical Seal Technical Manual",
            revision="Rev 1.0",
            effective_date="2023-09-01",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            superseded_by=None,
            sections=[
                DocumentSection(
                    section_id="SEC-SEAL-01",
                    title="Cartridge Seal Face Materials & Leakage Limits",
                    content="Silicon carbide vs carbon stationary face. Any visible steady spray or continuous puddle indicates secondary O-ring degradation or primary face fracturing due to particulate intrusion."
                )
            ]
        )
    ]

    # 2. Symptoms
    symptoms = [
        Symptom(
            id="SYMP-VIB-01",
            name="High Radial Vibration",
            description="Radial vibration amplitude exceeding ISO limits on pump or motor bearing housings.",
            aliases=["vibrating violently", "pump shaking", "heavy hum", "shuddering on skid", "excessive rattle", "bearing vibration"],
            alarm_codes=["ALM-VIB-101", "ALM-VIB-HI", "VIB-TRIP-01"],
            category="mechanical"
        ),
        Symptom(
            id="SYMP-CAV-01",
            name="Cavitation Noise & Suction Crackling",
            description="Loud popping, crackling, or gravel-in-casing noise accompanied by erratic suction pressure.",
            aliases=["sounds like marbles", "gravel rattling inside casing", "crackling sound", "hollow thumping", "suction rattling", "popping inside pump"],
            alarm_codes=["ALM-SUCT-P-LO", "ALM-NPSH-01"],
            category="hydraulic"
        ),
        Symptom(
            id="SYMP-SEAL-01",
            name="Mechanical Seal Fluid Leakage",
            description="Process or barrier fluid dripping or pooling beneath seal gland.",
            aliases=["liquid dripping from seal gland", "puddle under seal plate", "barrier fluid loss", "seal leaking barrier fluid", "wet seal housing", "spray from pump shaft"],
            alarm_codes=["ALM-SEAL-LVL-LO", "ALM-DRAIN-HI"],
            category="mechanical"
        ),
        Symptom(
            id="SYMP-TEMP-01",
            name="High Motor Bearing Temperature",
            description="Motor end-shield or bearing cap temperature exceeding 85°C.",
            aliases=["motor end-shield burning hot", "bearing housing overheating", "smell of hot grease", "hot to touch motor bearing", "motor bearing hot"],
            alarm_codes=["ALM-MTR-BRG-HI", "ALM-TEMP-M-104", "RTD-BRG-TRIP"],
            category="thermal"
        ),
        Symptom(
            id="SYMP-DISCH-PULS-01",
            name="Discharge Pressure Pulsation",
            description="Rapid oscillation of discharge pressure needle and rhythmic vibration in discharge piping.",
            aliases=["pulsing needle on pressure gauge", "pipe hammering on discharge", "rhythmic surge", "discharge line surging", "pressure fluctuating rapidly"],
            alarm_codes=["ALM-PRESS-PULS", "ALM-DISCH-FLUTTER"],
            category="hydraulic"
        ),
        Symptom(
            id="SYMP-FLOW-LO-01",
            name="Low Discharge Flow Rate",
            description="Pump delivery rate is substantially below duty point flow specifications.",
            aliases=["pump not moving fluid", "discharge gpm low", "sluggish output flow", "insufficient delivery", "low pump output"],
            alarm_codes=["ALM-FLOW-LO", "FLOW-WARN-01"],
            category="hydraulic"
        ),
        Symptom(
            id="SYMP-CURR-HI-01",
            name="High Motor Amperage Draw",
            description="Motor running current draws greater than full-load rated amperes.",
            aliases=["motor tripping overload relay", "drawing high amperage", "breaker popping on start", "high amps on motor", "overcurrent trip"],
            alarm_codes=["ALM-ELEC-OVR-01", "MCC-TRIP-OC"],
            category="electrical"
        ),
        Symptom(
            id="SYMP-SMOKE-FIRE-01",
            name="Electrical Arcing & Burning Odor",
            description="Visible sparks, electrical flash, or acrid insulation smoke originating from terminal head or stator casing.",
            aliases=["smoke coming from motor junction box", "burning electrical smell", "blue sparks seen in terminal head", "acrid smoke", "motor smoking", "terminal box sparking"],
            alarm_codes=["ALM-ARC-DETECT", "ALM-FIRE-SMOKE-01"],
            category="safety_emergency"
        ),
        Symptom(
            id="SYMP-SEIZURE-01",
            name="Sudden Mechanical Shaft Seizure",
            description="Sudden screech followed by immediate shaft lockup and rotor stall.",
            aliases=["loud metallic screech then sudden lockup", "shaft locked solid", "grinding metal stall", "pump seized", "motor locked rotor"],
            alarm_codes=["ALM-STALL-LOCK", "SPEED-ZERO-TRIP"],
            category="safety_emergency"
        ),
        Symptom(
            id="SYMP-VFD-HARMONIC-01",
            name="Inverter Acoustic Whine & Resonant Vibration",
            description="High-frequency electrical whining sound synchronizing with VFD inverter switching.",
            aliases=["high frequency singing", "whining noise changing with rpm", "vfd whine", "inverter screech"],
            alarm_codes=["ALM-VFD-RESONANCE", "DRV-FLT-HARMONIC"],
            category="electrical"
        ),
        Symptom(
            id="SYMP-OIL-CONTAM-01",
            name="Lubricating Oil Emulsification",
            description="Lube oil sight glass displays milky, cloudy, or frothy fluid appearance.",
            aliases=["oil sight glass looks milky", "water in bearing reservoir", "foamy brown oil", "cloudy grease", "contaminated bearing lube"],
            alarm_codes=["ALM-OIL-CLOUDY"],
            category="mechanical"
        ),
        Symptom(
            id="SYMP-MOTOR-HUM-01",
            name="Excessive Electromagnetic Hum",
            description="Prominent 100Hz/120Hz magnetic hum accompanied by radial vibration harmonics.",
            aliases=["magnetic hum louder than usual", "buzzing stator core", "unbalanced motor noise", "stator humming"],
            alarm_codes=["ALM-MTR-ACOUSTIC"],
            category="electrical"
        ),
        Symptom(
            id="SYMP-LOOSE-MOUNT-01",
            name="Baseplate Soft Foot & Bolt Looseness",
            description="Deflection and high 1x vibration caused by unbolted or distorted foundation footing.",
            aliases=["chattering hold-down bolts", "vibration dropping when foot loosened", "uneven base contact", "soft foot rocking"],
            alarm_codes=["ALM-BASE-VIB"],
            category="mechanical"
        ),
        Symptom(
            id="SYMP-AIR-INGRESS-01",
            name="Suction Air Ingress",
            description="Air bubble entrainment through suction flange gasket causing erratic flow and micro-surges.",
            aliases=["milky fluid at discharge", "spluttering pump flow", "bubbles in suction sight glass", "suction sucking air"],
            alarm_codes=["ALM-AIR-ENTRAIN"],
            category="hydraulic"
        ),
        Symptom(
            id="SYMP-PUMP-OVERHEAT-01",
            name="Pump Casing Thermal Overheating",
            description="Casing temperature exceeds fluid saturation temperature due to closed-discharge recirculation.",
            aliases=["volute too hot to touch", "steaming casing", "fluid boiling in pump", "pump running dry and hot"],
            alarm_codes=["ALM-PUMP-TEMP-HI"],
            category="thermal"
        )
    ]

    # 3. Candidate Causes
    causes = [
        Cause(
            id="CAUSE-BRG-WEAR",
            name="Bearing Ball & Race Fatigue Wear",
            description="Excessive clearance, spalling, or micro-pitting in bearing raceways generating high radial vibration and localized heat.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-04",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            component_id="COMP-BEARING"
        ),
        Cause(
            id="CAUSE-SUCT-STARVE",
            name="Suction Strainer Clogging / Inadequate NPSHa",
            description="Foreign debris blinding suction basket or depressed supply vessel pressure causing local cavitation and head drop.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-02",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            component_id="COMP-IMPELLER"
        ),
        Cause(
            id="CAUSE-SEAL-FACE-DAMAGE",
            name="Mechanical Seal Face Scoring / Thermal Shock",
            description="Distortion or thermal crack in silicon carbide seal faces due to flush orifice restriction or dry running.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-03",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            component_id="COMP-SEAL"
        ),
        Cause(
            id="CAUSE-SHAFT-MISALIGN",
            name="Pump-to-Motor Shaft Misalignment",
            description="Angular or parallel coupling misalignment exceeding 0.05 mm creating 1x and 2x running speed vibration.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-01",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            component_id="COMP-COUPLING"
        ),
        Cause(
            id="CAUSE-IMP-VANE-RESONANCE",
            name="Impeller Vane Pass Acoustic Resonance",
            description="5-vane impeller interaction with casing volute tongue during operation below 65% MCSF creating pressure pulsation.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-05",
            applicable_models=["ApexFlow-CP200"],  # Applies only to CP200!
            component_id="COMP-IMPELLER"
        ),
        Cause(
            id="CAUSE-VALVE-FLUTTER",
            name="Discharge Check Valve Hinge Pin Flutter",
            description="Worn check valve hinge pin or fatigued return spring inducing high-frequency disc chatter and pressure spikes.",
            source_doc_id="DOC-MAN-CP100-A",
            section="SEC-CP100-02",
            applicable_models=["ApexFlow-CP100"],  # Applies only to CP100!
            component_id="COMP-VALVE"
        ),
        Cause(
            id="CAUSE-VFD-CARRIER-NOISE",
            name="Inverter PWM Carrier Frequency Misconfiguration",
            description="Improper drive carrier frequency inducing common-mode rotor voltage and bearing EDM fluting.",
            source_doc_id="DOC-MAN-IM50-VFD-A",
            section="SEC-VFD-01",
            applicable_models=["DuraTorq-IM50-VFD"],  # Applies only to VFD motor model!
            component_id="COMP-MOTOR-VFD"
        ),
        Cause(
            id="CAUSE-ELEC-ARC-INTERNAL",
            name="Stator Phase-to-Phase Insulation Breakdown",
            description="Corona discharge or thermal breakdown of winding varnish resulting in inter-turn arcing and scorched copper.",
            source_doc_id="DOC-MAN-SAFETY-01",
            section="SEC-SAFE-01",
            applicable_models=["DuraTorq-IM50", "DuraTorq-IM50-VFD"],
            component_id="COMP-STATOR"
        ),
        Cause(
            id="CAUSE-BRG-CATASTROPHIC",
            name="Catastrophic Bearing Cage Collapse & Seizure",
            description="Total mechanical failure of bearing ball retainer causing ball bunching, friction welding, and shaft lockup.",
            source_doc_id="DOC-MAN-SAFETY-01",
            section="SEC-SAFE-01",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            component_id="COMP-BEARING"
        ),
        Cause(
            id="CAUSE-LUB-DEGRADATION",
            name="Oxidized / Overfilled Bearing Lubricant",
            description="Excess grease churning or thermal oxidation causing grease thickening, elevated friction, and temperature rise.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-04",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            component_id="COMP-BEARING"
        ),
        Cause(
            id="CAUSE-AIR-LEAK-FLANGE",
            name="Suction Flange Gasket Infiltration",
            description="Sub-atmospheric suction joint allowing ambient air infiltration into impeller eye, disturbing prime.",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-02",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            component_id="COMP-FLANGE"
        ),
        Cause(
            id="CAUSE-MTR-OVERLOAD",
            name="Hydraulic Runout Overload",
            description="Pump operating past design flow into runout region drawing excessive brake horsepower from motor.",
            source_doc_id="DOC-MAN-IM50-C",
            section="SEC-IM50-01",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            component_id="COMP-MOTOR"
        )
    ]

    # 4. Procedures
    procedures = [
        Procedure(
            id="PROC-SAFE-EMERGENCY-SHUTDOWN",
            title="Emergency Electrical Isolation & Lockout/Tagout (LOTO)",
            source_doc_id="DOC-MAN-SAFETY-01",
            section="SEC-SAFE-01",
            applicable_models=["*"],
            required_expertise="Qualified Electrical Person",
            safety_precautions=[
                "Wear minimum 8 cal/cm2 Arc Flash PPE and Class 0 insulated gloves",
                "Verify absence of voltage using an approved, calibrated contact probe before touching terminals"
            ],
            stop_work_conditions=[
                "Visible smoke or active electrical arcing",
                "Burning electrical odor or molten conductor evidence",
                "Sudden mechanical seizure with stalled energized rotor"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Immediately depress Emergency Stop pushbutton at local control station.",
                    expected_observation="Motor de-energizes and indicator light turns red/tripped.",
                    caution="Do not stand directly in front of starter cabinet during emergency trip."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Open motor circuit breaker in MCC-415 and attach personal red safety padlock and danger tag.",
                    expected_observation="Breaker handle locked in positive open position."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Perform live-dead-live zero voltage verification at motor terminal junction box.",
                    expected_observation="0.0 VAC across all phase pairs L1-L2, L2-L3, L3-L1 and to ground."
                ),
                ProcedureStep(
                    step_num=4,
                    instruction="Escalate fault report immediately to Plant Electrical Supervisor.",
                    expected_observation="Supervisor signs handover log."
                )
            ],
            escalation_criteria="Any indication of arc flash, phase-to-ground flashover, or smoke requires supervisor sign-off before breaker re-closure."
        ),
        Procedure(
            id="PROC-BRG-CLEARANCE-CHK",
            title="Precision Dial-Indicator Bearing Clearance & Runout Verification",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-04",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            required_expertise="Mechanical Technician II",
            safety_precautions=[
                "Confirm asset is locked out and depressurized before mounting dial indicators",
                "Wear safety glasses and cut-resistant gloves"
            ],
            stop_work_conditions=[
                "Shaft cannot be rotated by hand (locked/seized)",
                "Severe metal shavings found inside bearing cavity"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Mount magnetic base dial indicator on pump bearing bracket with stylus perpendicular to shaft journal.",
                    expected_observation="Indicator zeroed cleanly at 12 o'clock position."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Using a wooden pry bar, apply gentle upward radial force (approx 30 kg) and record total indicator reading (TIR).",
                    expected_observation="Radial clearance reading between 0.025 mm and 0.038 mm.",
                    caution="Do not exceed 50 kg leverage to avoid brinelling race."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Compare measured TIR to maximum allowable tolerance of 0.038 mm (note: obsolete Rev A allowed 0.080 mm).",
                    expected_observation="If TIR > 0.038 mm, bearing replacement is mandated."
                )
            ],
            escalation_criteria="If radial play exceeds 0.050 mm or axial float exceeds 0.12 mm, issue replacement work order."
        ),
        Procedure(
            id="PROC-NPSH-SUCT-CLEAN",
            title="Suction Strainer Inspection & Available NPSH Verification",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-02",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            required_expertise="Operations Tech / Mechanical Tech I",
            safety_precautions=[
                "Close suction block valve and vent basket strainer cavity to atmosphere before unbolting cover",
                "Ensure drain valve discharge is directed to industrial drain sump"
            ],
            stop_work_conditions=[
                "Hazardous chemical fumes escaping from strainer drain",
                "Suction block valve passing (will not achieve zero differential pressure)"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Observe differential pressure gauge across duplex suction strainer basket.",
                    expected_observation="Differential pressure Delta-P < 0.25 bar. If Delta-P > 0.5 bar, strainer is choked."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Switch to standby basket or depressurize and remove strainer screen for inspection.",
                    expected_observation="Clean 40-mesh stainless screen free of scale and polymer buildup."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Verify suction static pressure gauge reading exceeds minimum 1.20 bar gauge while running.",
                    expected_observation="Stable suction pressure > 1.20 barg without fluctuation."
                )
            ],
            escalation_criteria="If clean strainer still yields suction pressure < 1.0 bar gauge, check suction line foot valve or supply vessel blanketing."
        ),
        Procedure(
            id="PROC-SEAL-FLUSH-INSPECT",
            title="Mechanical Seal API Plan 11 Flush & Barrier System Check",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-03",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"],
            required_expertise="Mechanical Technician II",
            safety_precautions=[
                "Wear face shield and acid/chemical resistant gloves when inspecting seal drain area",
                "Do not place fingers near rotating shaft collar"
            ],
            stop_work_conditions=[
                "Continuous steady fluid stream (> 100 ml/min) pouring from gland plate",
                "Active vapor plume escaping seal cavity"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Touch Plan 11 flush recirculation line 50 mm upstream of gland inlet to test temperature.",
                    expected_observation="Line should feel warm (approx 40-50°C), confirming active fluid flow."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Inspect Plan 11 orifice union for particulate blockage or crystallization.",
                    expected_observation="Orifice port clear; no crystallized salt or scale."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Measure leakage rate at gland drain port over 5 minutes with graduated cylinder.",
                    expected_observation="Normal seepage < 3 drops per minute. Liquid pooling indicates face damage."
                )
            ],
            escalation_criteria="Leakage exceeding 15 drops/min requires scheduled cartridge seal replacement."
        ),
        Procedure(
            id="PROC-LASER-ALIGN",
            title="Dynamic Laser Shaft Alignment (Pump to Motor)",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-01",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            required_expertise="Millwright / Mechanical Tech II",
            safety_precautions=[
                "Confirm LOTO is applied to motor main breaker",
                "Remove coupling guard only after locking out"
            ],
            stop_work_conditions=[
                "Motor hold-down bolt sheared or stripped thread in baseplate",
                "Severe soft foot (> 0.20 mm) that cannot be shimmed"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Mount laser emitter and receiver on pump and motor shaft hubs.",
                    expected_observation="Laser beams centered in target detectors."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Execute soft foot test by loosening each motor foot bolt one by one.",
                    expected_observation="Deflection under each foot < 0.05 mm."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Rotate shafts 360 degrees and adjust stainless steel shims under motor feet.",
                    expected_observation="Final angular misalignment < 0.05 mm/100mm, parallel offset < 0.03 mm."
                )
            ],
            escalation_criteria="If coupling hubs show fretting corrosion or elastomer insert is shredded, replace coupling insert before realignment."
        ),
        Procedure(
            id="PROC-PULSATION-CP200",
            title="ApexFlow CP-200 Impeller Acoustic Resonance & Bypass Check",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-05",
            applicable_models=["ApexFlow-CP200"],  # Applies only to CP200
            required_expertise="Senior Reliability Engineer / Tech II",
            safety_precautions=[
                "Ensure discharge pressure dampener is rated for 25 bar design pressure",
                "Do not close minimum flow bypass line during testing"
            ],
            stop_work_conditions=[
                "Piping discharge hanger visibly bending or pipe clamp weld cracked"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Verify minimum continuous flow bypass valve position on ApexFlow CP-200.",
                    expected_observation="Bypass valve indicated open at >= 35% stroke when main discharge throttled."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Connect high-frequency pressure transducer to discharge piezometer ring.",
                    expected_observation="Pressure pulsation amplitude < 0.8 bar peak-to-peak at 5x running speed."
                )
            ],
            escalation_criteria="If pulsation persists > 1.5 bar peak-to-peak at full flow, inspect impeller tip vane clearance."
        ),
        Procedure(
            id="PROC-VALVE-CP100",
            title="ApexFlow CP-100 Discharge Check Valve Pin & Spring Inspection",
            source_doc_id="DOC-MAN-CP100-A",
            section="SEC-CP100-02",
            applicable_models=["ApexFlow-CP100"],  # Applies only to CP100
            required_expertise="Mechanical Technician I",
            safety_precautions=[
                "Isolate discharge block valve and depressurize check valve spool piece",
                "Tag discharge line as pressurized hazard before unbolting bonnet"
            ],
            stop_work_conditions=[
                "Liquid weeping past discharge block valve when vented"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Unbolt bonnet plate of external swing check valve on CP-100 discharge spool.",
                    expected_observation="Bonnet gasket intact without scoring."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Examine check valve hinge pin and torsion spring for wear or fracture.",
                    expected_observation="Hinge pin straight, disc swings smoothly without radial slop, return spring tension intact."
                )
            ],
            escalation_criteria="If hinge pin has > 0.5 mm wear groove, replace hinge pin and disc assembly."
        ),
        Procedure(
            id="PROC-VFD-HARMONIC-TUNING",
            title="DuraTorq IM-50-VFD Carrier Frequency & Grounding Ring Audit",
            source_doc_id="DOC-MAN-IM50-VFD-A",
            section="SEC-VFD-01",
            applicable_models=["DuraTorq-IM50-VFD"],  # TRAP: ONLY DuraTorq-IM50-VFD!
            required_expertise="Certified VFD Specialist / Electrical Tech III",
            safety_precautions=[
                "Wait 10 minutes after VFD main breaker opened for DC bus capacitor bank discharge (< 50 VDC)",
                "Verify DC bus voltage with multimeter before touching drive terminals"
            ],
            stop_work_conditions=[
                "DC bus voltage reads > 50 V after 10 minute bleed-down",
                "Inverter IGBT module shows visible scorch mark or swelling"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Access VFD parameter group P-04 (Carrier Frequency) and verify setting is configured to exactly 4.0 kHz.",
                    expected_observation="Parameter P-04 displays 4.0 kHz (not 8.0 or 12.0 kHz).",
                    caution="Do not set carrier frequency above 4.0 kHz without sine-wave filter."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Inspect shaft grounding carbon brush or Aegis microfiber ring on drive end.",
                    expected_observation="Brush microfibers making clean 360-degree contact with polished copper shaft collar."
                )
            ],
            escalation_criteria="If fluting marks detected on bearing raceways, replace bearing with ceramic-hybrid insulated bearing."
        ),
        Procedure(
            id="PROC-MOTOR-MEGGER-TEST",
            title="1000V Megohmmeter Motor Stator Insulation Resistance Test",
            source_doc_id="DOC-MAN-IM50-C",
            section="SEC-IM50-02",
            applicable_models=["DuraTorq-IM50", "DuraTorq-IM50-VFD"],
            required_expertise="Qualified Electrical Person",
            safety_precautions=[
                "Disconnect motor leads from MCC drive/starter to avoid damaging electronic protection cards",
                "Discharge windings to ground after test for at least 4 times the test duration"
            ],
            stop_work_conditions=[
                "Moisture or conductive water standing inside motor terminal head",
                "Cracked porcelain feedthrough insulators"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Apply 1000V DC test voltage between Phase U and Motor Ground for 60 seconds.",
                    expected_observation="Insulation resistance reading > 100 Megaohms (minimum acceptable 5 Megaohms)."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Repeat test for Phase V-to-Ground and Phase W-to-Ground.",
                    expected_observation="All three phases within 10% balanced resistance."
                )
            ],
            escalation_criteria="Insulation resistance below 5.0 Megaohms requires oven bake-out or motor rewinding."
        ),
        Procedure(
            id="PROC-LUB-FLUSH-FILL",
            title="Bearing Housing Flush and Relubrication Standard Procedure",
            source_doc_id="DOC-MAN-CP200-B",
            section="SEC-CP200-04",
            applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"],
            required_expertise="Mechanical Technician I",
            safety_precautions=[
                "Allow bearing housing to cool below 50°C before opening drain plug",
                "Collect old grease/oil into designated hazardous waste container"
            ],
            stop_work_conditions=[
                "Brass cage flakes or magnetic particles in drained grease"
            ],
            steps=[
                ProcedureStep(
                    step_num=1,
                    instruction="Remove bottom grease relief plug and clean port with brass wire probe.",
                    expected_observation="Drain path completely open."
                ),
                ProcedureStep(
                    step_num=2,
                    instruction="Inject 35 grams of synthetic polyurea grease (ISO VG 68) while shaft is rotated slowly by hand.",
                    expected_observation="Fresh grease emerges from relief port with clean consistency.",
                    caution="Do not overfill housing beyond 40% void volume."
                ),
                ProcedureStep(
                    step_num=3,
                    instruction="Run machine for 30 minutes uncoupled with relief plug removed to expel excess lubricant.",
                    expected_observation="Bearing temperature stabilizes below 70°C."
                )
            ],
            escalation_criteria="If temperature continues to climb past 85°C after relubrication, shut down and inspect bearing internal clearances."
        )
    ]

    # 5. Parts
    parts = [
        Part(id="PART-BRG-6312", part_number="SKF-6312-C3", name="Deep Groove Ball Bearing 60x130x31mm", applicable_models=["ApexFlow-CP200"], estimated_lead_time_days=1),
        Part(id="PART-BRG-7312", part_number="SKF-7312-BEP", name="Angular Contact Ball Bearing Pair", applicable_models=["ApexFlow-CP200"], estimated_lead_time_days=2),
        Part(id="PART-BRG-6310", part_number="SKF-6310-C3", name="Induction Motor Drive-End Bearing", applicable_models=["DuraTorq-IM50", "DuraTorq-IM50-VFD"], estimated_lead_time_days=1),
        Part(id="PART-SEAL-CP200", part_number="APX-SEAL-200-SIC", name="Cartridge Mechanical Seal Assembly (SiC/Carbon)", applicable_models=["ApexFlow-CP200"], estimated_lead_time_days=3),
        Part(id="PART-SEAL-CP100", part_number="APX-SEAL-100-STD", name="Component Mechanical Seal Assembly", applicable_models=["ApexFlow-CP100"], estimated_lead_time_days=2),
        Part(id="PART-VALVE-PIN-100", part_number="APX-VALVE-PIN-100", name="Discharge Check Valve Hinge Pin & Torsion Spring", applicable_models=["ApexFlow-CP100"], estimated_lead_time_days=1),
        Part(id="PART-STRAINER-BASKET", part_number="APX-STR-40M-SS", name="Suction Strainer Basket 40-Mesh 316SS", applicable_models=["ApexFlow-CP200", "ApexFlow-CP100"], estimated_lead_time_days=2),
        Part(id="PART-COUPLING-INSERT", part_number="LOVEJOY-HRC-150", name="Flexible Elastomer Coupling Spider Insert", applicable_models=["ApexFlow-CP200", "ApexFlow-CP100", "DuraTorq-IM50"], estimated_lead_time_days=1),
        Part(id="PART-VFD-BRUSH", part_number="AEGIS-SGR-50", name="Shaft Grounding Microfiber Ring Assembly", applicable_models=["DuraTorq-IM50-VFD"], estimated_lead_time_days=5)
    ]

    # 6. Past Incidents (14 incidents, 10 verified + 4 unverified)
    incidents = [
        Incident(
            id="INC-2024-001",
            asset_id="P-101",
            symptom_id="SYMP-VIB-01",
            confirmed_cause_id="CAUSE-BRG-WEAR",
            procedure_used_id="PROC-BRG-CLEARANCE-CHK",
            outcome_status="resolved",
            technician="tech_dave",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-02-10",
            resolution_notes="Measured 0.062 mm radial clearance on non-drive end 7312 bearing. Replaced bearing pair and repacked grease. Vibration dropped from 8.2 mm/s to 1.8 mm/s."
        ),
        Incident(
            id="INC-2024-002",
            asset_id="P-101",
            symptom_id="SYMP-CAV-01",
            confirmed_cause_id="CAUSE-SUCT-STARVE",
            procedure_used_id="PROC-NPSH-SUCT-CLEAN",
            outcome_status="resolved",
            technician="tech_mike",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-03-04",
            resolution_notes="Found suction strainer basket 60% choked with corrosion scale. Cleaned screen and restored NPSHa; crackling noise vanished."
        ),
        Incident(
            id="INC-2024-003",
            asset_id="P-102",
            symptom_id="SYMP-SEAL-01",
            confirmed_cause_id="CAUSE-SEAL-FACE-DAMAGE",
            procedure_used_id="PROC-SEAL-FLUSH-INSPECT",
            outcome_status="resolved",
            technician="tech_dave",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-04-12",
            resolution_notes="Plan 11 flush orifice was clogged with pipe dope. Seal ran dry and scored stationary carbon face. Replaced cartridge seal and cleaned flush port."
        ),
        Incident(
            id="INC-2024-004",
            asset_id="M-104",
            symptom_id="SYMP-TEMP-01",
            confirmed_cause_id="CAUSE-LUB-DEGRADATION",
            procedure_used_id="PROC-LUB-FLUSH-FILL",
            outcome_status="resolved",
            technician="tech_mike",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-05-18",
            resolution_notes="Technician previously overfilled bearing with grease gun without opening relief plug. Drained excess grease; temp dropped from 94°C to 68°C."
        ),
        Incident(
            id="INC-2024-005",
            asset_id="P-101",
            symptom_id="SYMP-DISCH-PULS-01",
            confirmed_cause_id="CAUSE-IMP-VANE-RESONANCE",
            procedure_used_id="PROC-PULSATION-CP200",
            outcome_status="resolved",
            technician="tech_dave",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-06-22",
            resolution_notes="ApexFlow CP-200 minimum flow bypass valve positioner had slipped to 15%. Re-calibrated bypass actuator to maintain 40% MCSF minimum, resolving 5x vane pass surge."
        ),
        Incident(
            id="INC-2024-006",
            asset_id="P-103",
            symptom_id="SYMP-DISCH-PULS-01",
            confirmed_cause_id="CAUSE-VALVE-FLUTTER",
            procedure_used_id="PROC-VALVE-CP100",
            outcome_status="resolved",
            technician="tech_mike",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-07-08",
            resolution_notes="On CP-100, discharge check valve hinge pin was worn oval causing disc flutter. Replaced pin and spring; pressure needle stabilized."
        ),
        Incident(
            id="INC-2024-007",
            asset_id="M-105",
            symptom_id="SYMP-VIB-01",
            confirmed_cause_id="CAUSE-SHAFT-MISALIGN",
            procedure_used_id="PROC-LASER-ALIGN",
            outcome_status="resolved",
            technician="tech_dave",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-08-14",
            resolution_notes="Laser alignment revealed 0.14 mm angular misalignment between M-105 and P-102. Re-shimmed motor inboard feet; 2x vibration reduced by 80%."
        ),
        Incident(
            id="INC-2024-008",
            asset_id="P-102",
            symptom_id="SYMP-VIB-01",
            confirmed_cause_id="CAUSE-BRG-WEAR",
            procedure_used_id="PROC-BRG-CLEARANCE-CHK",
            outcome_status="resolved",
            technician="tech_mike",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-09-02",
            resolution_notes="Found 0.048 mm radial clearance on pump drive end bearing. Replaced with SKF 6312 C3 and confirmed alignment."
        ),
        Incident(
            id="INC-2024-009",
            asset_id="M-104",
            symptom_id="SYMP-CURR-HI-01",
            confirmed_cause_id="CAUSE-MTR-OVERLOAD",
            procedure_used_id="PROC-MOTOR-MEGGER-TEST",
            outcome_status="resolved",
            technician="tech_dave",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-09-29",
            resolution_notes="Discharge throttle valve failed open causing pump to run into runout (135% design gpm). Throttled discharge to duty point, current returned to 58 Amps."
        ),
        Incident(
            id="INC-2024-010",
            asset_id="P-101",
            symptom_id="SYMP-OIL-CONTAM-01",
            confirmed_cause_id="CAUSE-SEAL-FACE-DAMAGE",
            procedure_used_id="PROC-SEAL-FLUSH-INSPECT",
            outcome_status="resolved",
            technician="tech_mike",
            supervisor_approved=True,
            approved_by="supervisor_sarah",
            incident_date="2024-10-15",
            resolution_notes="Deflector flinger ring loose on shaft allowed seal leakage wash to penetrate bearing isolator. Replaced seal and installed new isolator labyrinth."
        ),
        # 4 Unverified or pending verification incidents
        Incident(
            id="INC-2024-011",
            asset_id="P-103",
            symptom_id="SYMP-FLOW-LO-01",
            confirmed_cause_id="CAUSE-SUCT-STARVE",
            procedure_used_id="PROC-NPSH-SUCT-CLEAN",
            outcome_status="pending_verification",
            technician="tech_dave",
            supervisor_approved=False,
            approved_by=None,
            incident_date="2024-10-19",
            resolution_notes="Flushed suction basket. Awaiting supervisor signoff."
        ),
        Incident(
            id="INC-2024-012",
            asset_id="M-104",
            symptom_id="SYMP-TEMP-01",
            confirmed_cause_id="CAUSE-BRG-WEAR",
            procedure_used_id="PROC-BRG-CLEARANCE-CHK",
            outcome_status="pending_verification",
            technician="tech_mike",
            supervisor_approved=False,
            approved_by=None,
            incident_date="2024-10-20",
            resolution_notes="Greased bearing. Needs thermal imaging confirmation."
        ),
        Incident(
            id="INC-2024-013",
            asset_id="P-102",
            symptom_id="SYMP-CAV-01",
            confirmed_cause_id="CAUSE-AIR-LEAK-FLANGE",
            procedure_used_id="PROC-NPSH-SUCT-CLEAN",
            outcome_status="pending_verification",
            technician="tech_dave",
            supervisor_approved=False,
            approved_by=None,
            incident_date="2024-10-21",
            resolution_notes="Re-torqued suction flange bolts. Requires flow test verification."
        ),
        Incident(
            id="INC-2024-014",
            asset_id="M-105",
            symptom_id="SYMP-MOTOR-HUM-01",
            confirmed_cause_id="CAUSE-SHAFT-MISALIGN",
            procedure_used_id="PROC-LASER-ALIGN",
            outcome_status="pending_verification",
            technician="tech_mike",
            supervisor_approved=False,
            approved_by=None,
            incident_date="2024-10-22",
            resolution_notes="Coupling inspected. Alignment check scheduled."
        )
    ]

    # 7. Assets (5 assets with inspection history)
    assets = [
        Asset(
            id="P-101",
            name="Primary Boiler Feed Pump A",
            category="centrifugal_pump",
            model="ApexFlow-CP200",
            revision="Rev B",
            manual_id="DOC-MAN-CP200-B",
            effective_date="2024-01-15",
            criticality="high",
            motor_id="M-104",
            inspection_history=[
                AssetInspection(inspection_id="INSP-P101-01", date="2024-01-10", inspector="inspector_bill", result="pass", notes="Routine commissioning inspection."),
                AssetInspection(inspection_id="INSP-P101-02", date="2024-07-15", inspector="inspector_bill", result="conditional", notes="Vibration slightly elevated (3.8 mm/s). Scheduled monitoring.")
            ]
        ),
        Asset(
            id="P-102",
            name="Secondary Transfer Pump B",
            category="centrifugal_pump",
            model="ApexFlow-CP200",
            revision="Rev B",
            manual_id="DOC-MAN-CP200-B",
            effective_date="2024-01-15",
            criticality="medium",
            motor_id="M-105",
            inspection_history=[
                AssetInspection(inspection_id="INSP-P102-01", date="2024-02-12", inspector="inspector_bill", result="pass", notes="Standard quarterly visual inspection."),
                AssetInspection(inspection_id="INSP-P102-02", date="2024-08-18", inspector="inspector_bill", result="pass", notes="Laser alignment verified.")
            ]
        ),
        Asset(
            id="P-103",
            name="Condensate Return Pump C",
            category="centrifugal_pump",
            model="ApexFlow-CP100",
            revision="Rev A",
            manual_id="DOC-MAN-CP100-A",
            effective_date="2022-06-01",
            criticality="low",
            motor_id=None,
            inspection_history=[
                AssetInspection(inspection_id="INSP-P103-01", date="2023-11-05", inspector="inspector_bill", result="pass", notes="Annual service check."),
                AssetInspection(inspection_id="INSP-P103-02", date="2024-05-10", inspector="inspector_bill", result="defect_noted", notes="Check valve spring slack noted; replaced.")
            ]
        ),
        Asset(
            id="M-104",
            name="Feed Pump Electric Motor Drive A",
            category="induction_motor",
            model="DuraTorq-IM50",
            revision="Rev C",
            manual_id="DOC-MAN-IM50-C",
            effective_date="2024-03-01",
            criticality="high",
            motor_id=None,
            inspection_history=[
                AssetInspection(inspection_id="INSP-M104-01", date="2024-03-05", inspector="inspector_bill", result="pass", notes="Motor megger test passed (>500 MOhm)."),
                AssetInspection(inspection_id="INSP-M104-02", date="2024-09-12", inspector="inspector_bill", result="pass", notes="Thermal inspection normal (62°C).")
            ]
        ),
        Asset(
            id="M-105",
            name="Transfer Pump Electric Motor Drive B",
            category="induction_motor",
            model="DuraTorq-IM50",
            revision="Rev C",
            manual_id="DOC-MAN-IM50-C",
            effective_date="2024-03-01",
            criticality="medium",
            motor_id=None,
            inspection_history=[
                AssetInspection(inspection_id="INSP-M105-01", date="2024-04-01", inspector="inspector_bill", result="pass", notes="Initial alignment inspection."),
                AssetInspection(inspection_id="INSP-M105-02", date="2024-10-01", inspector="inspector_bill", result="conditional", notes="Soft foot noted on right rear foot. Re-shimmed.")
            ]
        )
    ]

    return KnowledgePack(
        manuals=manuals,
        symptoms=symptoms,
        causes=causes,
        procedures=procedures,
        parts=parts,
        incidents=incidents,
        assets=assets
    )


def main():
    print("Generating Readiness Assistant Synthetic Knowledge Pack...")
    pack = create_knowledge_pack()

    out_dir = Path(__file__).resolve().parent.parent / "knowledge"
    manuals_dir = out_dir / "manuals"
    os.makedirs(manuals_dir, exist_ok=True)

    # 1. Write individual markdown manual excerpts
    for manual in pack.manuals:
        md_filename = f"{manual.doc_id.lower().replace('-', '_')}.md"
        md_path = manuals_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {manual.title}\n\n")
            f.write(f"**Document ID**: `{manual.doc_id}`  \n")
            f.write(f"**Revision**: `{manual.revision}`  \n")
            f.write(f"**Effective Date**: `{manual.effective_date}`  \n")
            f.write(f"**Applicable Models**: {', '.join(manual.applicable_models)}  \n")
            if manual.superseded_by:
                f.write(f"**SUPERSEDED BY**: `{manual.superseded_by}`  \n")
            f.write("\n---\n\n")

            for sec in manual.sections:
                f.write(f"## {sec.section_id}: {sec.title}\n\n")
                f.write(f"{sec.content}\n\n")

        print(f"  Wrote manual markdown: {md_filename}")

    # 2. Write structured JSON files
    json_targets = {
        "knowledge_pack.json": pack.model_dump(),
        "manuals.json": [m.model_dump() for m in pack.manuals],
        "symptoms.json": [s.model_dump() for s in pack.symptoms],
        "causes.json": [c.model_dump() for c in pack.causes],
        "procedures.json": [p.model_dump() for p in pack.procedures],
        "parts.json": [pt.model_dump() for pt in pack.parts],
        "incidents.json": [inc.model_dump() for inc in pack.incidents],
        "assets.json": [a.model_dump() for a in pack.assets],
    }

    for filename, data in json_targets.items():
        filepath = out_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  Wrote JSON data file: {filename}")

    # 3. Verification of relations and provenance
    doc_sections = set()
    for m in pack.manuals:
        for s in m.sections:
            doc_sections.add((m.doc_id, s.section_id))

    print("\nVerifying provenance links:")
    for cause in pack.causes:
        if (cause.source_doc_id, cause.section) not in doc_sections:
            raise ValueError(f"Cause {cause.id} references invalid source ({cause.source_doc_id}, {cause.section})")
    print(f"  [OK] All {len(pack.causes)} causes verified to have valid source doc_id + section.")

    for proc in pack.procedures:
        if (proc.source_doc_id, proc.section) not in doc_sections:
            raise ValueError(f"Procedure {proc.id} references invalid source ({proc.source_doc_id}, {proc.section})")
    print(f"  [OK] All {len(pack.procedures)} procedures verified to have valid source doc_id + section.")

    print("\nSuccessfully generated synthetic knowledge pack.")


if __name__ == "__main__":
    main()
