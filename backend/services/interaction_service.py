"""
Core Multi-Drug Interaction Evaluation Engine
Primary Knowledge Base: @backend/data/db_drug_interactions.csv (191,000+ clinical pairs)
Expert Clinical Rules:
- NEVER suggest "spacing out doses" or "adjusting dosing intervals" for drugs with irreversible mechanisms
  (e.g., Aspirin, Clopidogrel) or long-half-life/systemic anticoagulants (e.g., Warfarin, DOACs).
- Only recommend "spacing doses" for physical chelation/binding interactions
  (e.g., Ciprofloxacin/Levothyroxine with multivalent cations like Calcium, Iron, Antacids).
- For antiplatelet + anticoagulant interactions, strictly recommend:
  "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely."
- Clean FDA Label synthesis without raw OCR/table headers or unformatted lists.
- Unified single-card grouping per pair.
"""

import os
import re
import difflib
import itertools
import httpx
from typing import Dict, Tuple, Optional, Set, List, Any

BRAND_TO_GENERIC = {
    "augmentin": "amoxicillin",
    "amoxil": "amoxicillin",
    "cipro": "ciprofloxacin",
    "cipro xr": "ciprofloxacin",
    "zithromax": "azithromycin",
    "z-pak": "azithromycin",
    "zmax": "azithromycin",
    "coumadin": "warfarin",
    "jantoven": "warfarin",
    "cordarone": "amiodarone",
    "pacerone": "amiodarone",
    "nexium": "esomeprazole",
    "prilosec": "omeprazole",
    "lipitor": "atorvastatin",
    "zocor": "simvastatin",
    "crestor": "rosuvastatin",
    "plavix": "clopidogrel",
    "lasix": "furosemide",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "aleve": "naproxen",
    "tylenol": "acetaminophen",
    "bactrim": "sulfamethoxazole",
    "septra": "sulfamethoxazole",
    "keflex": "cephalexin",
    "levaquin": "levofloxacin",
    "avelox": "moxifloxacin",
    "flagyl": "metronidazole",
    "glucophage": "metformin",
    "norvasc": "amlodipine",
    "synthroid": "levothyroxine",
    "cozaar": "losartan",
    "diovan": "valsartan",
    "prinivil": "lisinopril",
    "zestril": "lisinopril",
    "lopressor": "metoprolol",
    "toprol": "metoprolol",
    "coreg": "carvedilol",
    "xanax": "alprazolam",
    "valium": "diazepam",
    "ativan": "lorazepam",
    "prozac": "fluoxetine",
    "zoloft": "sertraline",
    "lexapro": "escitalopram",
    "celexa": "citalopram",
    "effexor": "venlafaxine",
    "cymbalta": "duloxetine",
    "zyvox": "linezolid",
    "paxil": "paroxetine",
    "luvox": "fluvoxamine",
}

SALT_AND_FORM_TOKENS = {
    "sodium", "potassium", "calcium", "hydrochloride", "hcl", "dihydrochloride",
    "sulfate", "sulphate", "phosphate", "tartrate", "succinate", "maleate",
    "mesylate", "besylate", "fumarate", "acetate", "gluconate", "citrate",
    "lactate", "bromide", "iodide", "nitrate", "propionate", "valerate",
    "dipropionate", "monohydrate", "dihydrate", "trihydrate", "er", "xr",
    "xl", "cr", "sr", "dr", "ir", "oral", "tablet", "tablets", "capsule",
    "capsules", "injection", "solution", "suspension", "syrup", "cream", "ointment"
}

DOSAGE_REGEX = re.compile(
    r'\b\d+(\.\d+)?\s*(mg|mcg|ug|g|ml|l|iu|meq|%|mmol)\b',
    re.IGNORECASE
)

SEVERITY_RANKS = {
    "CONTRAINDICATED": 6,
    "CRITICAL": 5,
    "MAJOR": 4,
    "MODERATE": 3,
    "MINOR": 2,
    "UNKNOWN": 1,
    "NONE": 0
}

def compare_severity(sev1: str, sev2: str) -> str:
    s1 = (sev1 or "UNKNOWN").upper().strip()
    s2 = (sev2 or "UNKNOWN").upper().strip()
    r1 = SEVERITY_RANKS.get(s1, 1)
    r2 = SEVERITY_RANKS.get(s2, 1)
    return sev1 if r1 >= r2 else sev2


# Drug Class Categorization for Clinical Action Rules
ANTIPLATELETS = {
    "aspirin", "clopidogrel", "prasugrel", "ticagrelor", "dipyridamole", "ticlopidine", "cilostazol"
}

ANTICOAGULANTS = {
    "warfarin", "heparin", "enoxaparin", "dalteparin", "apixaban", "rivaroxaban",
    "edoxaban", "dabigatran", "fondaparinux", "bivalirudin", "argatroban"
}

NSAIDS = {
    "ibuprofen", "naproxen", "meloxicam", "celecoxib", "diclofenac", "indomethacin",
    "ketorolac", "piroxicam", "sulindac", "etodolac", "nabumetone"
}

SSRI_SNRI_DRUGS = {
    "citalopram", "escitalopram", "sertraline", "fluoxetine", "paroxetine",
    "fluvoxamine", "vilazodone", "vortioxetine", "venlafaxine", "duloxetine",
    "desvenlafaxine", "milnacipran", "levomilnacipran"
}

MAOI_DRUGS = {
    "linezolid", "phenelzine", "tranylcypromine", "isocarboxazid", "selegiline",
    "rasagiline", "safinamide", "moclobemide", "methylene blue"
}

AZOLE_ANTIFUNGALS = {
    "ketoconazole", "itraconazole", "fluconazole", "voriconazole", "posaconazole", "isavuconazonium"
}

IMMUNOSUPPRESSANTS_NTI = {
    "tacrolimus", "cyclosporine", "sirolimus", "everolimus"
}

QT_PROLONGING_ANTIARRHYTHMICS = {
    "amiodarone", "dronedarone", "sotalol", "quinidine", "procainamide", "disopyramide", "dofetilide", "ibutilide"
}

FLUOROQUINOLONES = {
    "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin", "gemifloxacin"
}

STRONG_CYP3A4_INHIBITORS = {
    "clarithromycin", "ketoconazole", "itraconazole", "ritonavir", "cobicistat", "nefazodone"
}

CHELATION_DRUGS = {
    "ciprofloxacin", "levofloxacin", "moxifloxacin", "doxycycline", "minocycline",
    "tetracycline", "levothyroxine"
}

CHELATING_AGENTS = {
    "calcium", "iron", "magnesium", "aluminum", "antacid", "ferrous", "sucralfate", "zinc"
}

HIGH_PRIORITY_CLINICAL_RULES: Dict[Tuple[str, str], Dict[str, str]] = {
    # 1. Linezolid + SSRIs / SNRIs (MAO-A Inhibition + Reuptake Inhibition = Fatal Serotonin Syndrome)
    tuple(sorted(["linezolid", "citalopram"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid is a reversible, non-selective monoamine oxidase A (MAO-A) inhibitor that prevents central serotonin catabolism. Co-administration with Citalopram, a selective serotonin reuptake inhibitor (SSRI), synergistically compounds synaptic reuptake inhibition to cause excessive systemic serotonin accumulation, precipitating potentially fatal Serotonin Syndrome characterized by severe hyperthermia, autonomic instability, clonus, and neuromuscular rigidity.",
        "fda_summary": "Linezolid is contraindicated in patients taking selective serotonin reuptake inhibitors such as citalopram due to the potential for fatal serotonin syndrome. Avoid concomitant use.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Fatal Serotonin Syndrome and Neuromuscular Rigidity",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "escitalopram"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid is a reversible, non-selective monoamine oxidase A (MAO-A) inhibitor that prevents central serotonin catabolism. Co-administration with Escitalopram, a selective serotonin reuptake inhibitor (SSRI), synergistically compounds synaptic reuptake inhibition to cause excessive systemic serotonin accumulation, precipitating potentially fatal Serotonin Syndrome characterized by severe hyperthermia, autonomic instability, clonus, and neuromuscular rigidity.",
        "fda_summary": "Linezolid is contraindicated in patients receiving escitalopram due to life-threatening serotonin syndrome risk. Avoid concomitant use.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Fatal Serotonin Syndrome and Autonomic Instability",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "sertraline"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid acts as a non-selective monoamine oxidase A (MAO-A) inhibitor preventing metabolic breakdown of serotonin. Concomitant administration with Sertraline results in massive synaptic serotonin accumulation, triggering life-threatening Serotonin Syndrome (altered mental status, tremor, rigidity, hyperthermia).",
        "fda_summary": "Linezolid should not be administered to patients receiving serotonergic psychiatric medications like sertraline unless there are no alternatives and benefits outweigh risks of fatal serotonin toxicity. Avoid concomitant use.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Severe Serotonin Toxicity and Hyperthermia",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "fluoxetine"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid inhibits MAO-A catabolism while Fluoxetine potently blocks 5-HT reuptake; because Fluoxetine and its active metabolite norfluoxetine have prolonged half-lives (up to 2 weeks), co-administration creates prolonged risk of catastrophic Serotonin Syndrome.",
        "fda_summary": "Concomitant use of linezolid with fluoxetine is contraindicated. Allow at least 5 weeks washout between discontinuation of fluoxetine and initiation of linezolid.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Prolonged Catastrophic Serotonin Toxicity",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "paroxetine"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid inhibits MAO-A-mediated monoamine clearance, synergizing with Paroxetine-mediated SERT inhibition to cause toxic central 5-HT2A and 5-HT1A overstimulation, producing acute Serotonin Syndrome.",
        "fda_summary": "Linezolid is contraindicated with paroxetine due to severe serotonergic toxicity. Avoid concomitant administration.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Central 5-HT Overstimulation and Acute Serotonin Syndrome",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "venlafaxine"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid inhibits monoamine oxidase A, preventing metabolic inactivation of serotonin and norepinephrine, compounding Venlafaxine's dual reuptake inhibition to precipitate severe Serotonin Syndrome and hypertensive crisis.",
        "fda_summary": "Co-administration of linezolid with serotonin and norepinephrine reuptake inhibitors like venlafaxine is contraindicated due to high risk of serotonin syndrome.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Severe Serotonin Syndrome and Hypertensive Crisis",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },
    tuple(sorted(["linezolid", "duloxetine"])): {
        "severity": "CONTRAINDICATED",
        "description": "Linezolid inhibits MAO-A catabolism, compounding Duloxetine's dual 5-HT and NE reuptake inhibition to cause dangerous intrasynaptic accumulation of serotonin, precipitating acute Serotonin Syndrome.",
        "fda_summary": "Linezolid is contraindicated in patients receiving duloxetine due to life-threatening serotonin toxicity. Avoid concomitant use.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Life-Threatening Serotonin Toxicity",
        "recommended_alternative": "Vancomycin",
        "culprit_drug": "linezolid"
    },

    # 2. Antiplatelets / Anticoagulants / NSAIDs
    tuple(sorted(["aspirin", "warfarin"])): {
        "severity": "MAJOR",
        "description": "Aspirin irreversibly inhibits platelet cyclooxygenase-1 (COX-1), suppressing thromboxane A2-mediated platelet aggregation and causing gastric mucosal damage, which synergistically impairs hemostasis alongside Warfarin-mediated suppression of vitamin K-dependent clotting factors, dramatically increasing major GI bleeding and intracranial hemorrhage risk.",
        "fda_summary": "Concomitant use of antiplatelet agents such as aspirin with warfarin substantially elevates the risk of severe bleeding complications. Patients receiving this combination require close clinical oversight and regular prothrombin time/INR monitoring.",
        "clinical_action": "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely.",
        "risk_factor": "Major Gastrointestinal and Intracranial Hemorrhage",
        "recommended_alternative": "Acetaminophen (Paracetamol)",
        "culprit_drug": "aspirin"
    },
    tuple(sorted(["ibuprofen", "warfarin"])): {
        "severity": "MAJOR",
        "description": "Ibuprofen reversibly inhibits platelet COX-1 and displaces Warfarin from plasma protein binding sites while causing gastric erosion; combined with Warfarin anticoagulation, this exponentially increases the risk of upper gastrointestinal bleeding and uninhibited hemorrhage.",
        "fda_summary": "Concomitant administration of NSAIDs such as ibuprofen with warfarin is associated with an increased risk of severe gastrointestinal bleeding. Avoid concomitant use when possible.",
        "clinical_action": "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely.",
        "risk_factor": "Severe Gastrointestinal Bleeding and Hemorrhage",
        "recommended_alternative": "Acetaminophen (Paracetamol)",
        "culprit_drug": "ibuprofen"
    },
    tuple(sorted(["naproxen", "warfarin"])): {
        "severity": "MAJOR",
        "description": "Naproxen inhibits platelet COX-1 and causes direct gastric mucosal injury, while Warfarin impairs systemic coagulation cascade factors II, VII, IX, and X; combination results in synergistic, life-threatening hemorrhagic risk.",
        "fda_summary": "Co-administration of NSAIDs with oral anticoagulants markedly increases hemorrhagic complications, particularly GI bleeds. Concomitant use should be avoided.",
        "clinical_action": "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely.",
        "risk_factor": "Upper Gastrointestinal Hemorrhage and Systemic Coagulopathy",
        "recommended_alternative": "Acetaminophen (Paracetamol)",
        "culprit_drug": "naproxen"
    },

    # 3. QT Prolongation & Torsades de Pointes
    tuple(sorted(["amiodarone", "azithromycin"])): {
        "severity": "CONTRAINDICATED",
        "description": "Amiodarone (Class III antiarrhythmic) and Azithromycin (macrolide) produce additive delays in myocardial ventricular repolarization via potassium hERG channel inhibition, causing extreme QTc interval prolongation and provoking polymorphic ventricular tachycardia (Torsades de Pointes) and fatal cardiac arrest.",
        "fda_summary": "Concomitant administration of drugs that prolong the QT interval may result in additive electrophysiological effects and increased risk of ventricular arrhythmias, including Torsades de Pointes. Avoid concomitant use.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Fatal Polymorphic Ventricular Tachycardia (Torsades de Pointes)",
        "recommended_alternative": "Doxycycline",
        "culprit_drug": "azithromycin"
    },
    tuple(sorted(["amiodarone", "ciprofloxacin"])): {
        "severity": "CONTRAINDICATED",
        "description": "Combining Amiodarone with Ciprofloxacin produces additive inhibition of cardiac IKr repolarization currents, leading to severe QTc prolongation, Torsades de Pointes, and life-threatening ventricular fibrillation.",
        "fda_summary": "Co-administration of fluoroquinolones with class III antiarrhythmics like amiodarone poses serious risk of cardiac arrhythmias and QTc prolongation. Concomitant use is contraindicated.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Severe QTc Prolongation and Sudden Cardiac Arrest",
        "recommended_alternative": "Amoxicillin-Clavulanate",
        "culprit_drug": "ciprofloxacin"
    },

    # 4. Metabolic Inhibitions & Clearance
    tuple(sorted(["ciprofloxacin", "warfarin"])): {
        "severity": "MAJOR",
        "description": "Ciprofloxacin potently inhibits hepatic CYP1A2 and displaces Warfarin from plasma albumin, producing dangerously elevated INR and high risk of life-threatening hemorrhage.",
        "fda_summary": "Fluoroquinolones may enhance the anticoagulant effect of warfarin. Co-administration requires frequent monitoring of prothrombin time/INR and dose adjustment as clinically indicated.",
        "clinical_action": "Avoid concomitant use where safe alternative antimicrobials exist. If required, reduce warfarin dose preemptively, monitor INR within 48-72 hours, and watch for active hemorrhage.",
        "risk_factor": "Supratherapeutic INR and Uncontrolled Hemorrhage",
        "recommended_alternative": "Amoxicillin-Clavulanate",
        "culprit_drug": "ciprofloxacin"
    },
    tuple(sorted(["clarithromycin", "simvastatin"])): {
        "severity": "CONTRAINDICATED",
        "description": "Clarithromycin is a potent CYP3A4 inhibitor that markedly elevates serum concentrations of Simvastatin, drastically increasing the risk of severe myopathy and life-threatening rhabdomyolysis.",
        "fda_summary": "Concomitant administration of clarithromycin with simvastatin is contraindicated due to increased risk of myopathy, including rhabdomyolysis.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Acute Rhabdomyolysis and Severe Myopathy",
        "recommended_alternative": "Rosuvastatin",
        "culprit_drug": "clarithromycin"
    },
    tuple(sorted(["clarithromycin", "colchicine"])): {
        "severity": "CONTRAINDICATED",
        "description": "Clarithromycin potently inhibits CYP3A4 and P-glycoprotein (P-gp), which blocks the primary metabolic clearance and efflux pathways of Colchicine. This causes toxic accumulation of colchicine, precipitating fatal multi-organ failure, severe neuromyopathy, bone marrow suppression, and cardiovascular collapse.",
        "fda_summary": "Co-administration of colchicine with strong CYP3A4 and P-gp inhibitors like clarithromycin is contraindicated in patients with renal or hepatic impairment and should be avoided in all patients due to life-threatening toxicity.",
        "clinical_action": "Avoid concomitant use. Select non-interacting antimicrobial alternatives (e.g., azithromycin or non-macrolide) or temporarily withhold colchicine.",
        "risk_factor": "Fatal Colchicine Toxicity and Multi-Organ Failure",
        "recommended_alternative": "Azithromycin",
        "culprit_drug": "clarithromycin"
    },
    tuple(sorted(["ketoconazole", "tacrolimus"])): {
        "severity": "MAJOR",
        "description": "Ketoconazole potently inhibits intestinal and hepatic CYP3A4 and P-glycoprotein, causing massive systemic accumulation of Tacrolimus and dramatically increasing the risk of acute nephrotoxicity, neurotoxicity, and QT interval prolongation.",
        "fda_summary": "Co-administration of azole antifungals with tacrolimus substantially increases tacrolimus blood concentrations. Significant dose reductions and intensive therapeutic drug monitoring are required.",
        "clinical_action": "Reduce tacrolimus dose preemptively by 50% to 75%, closely monitor tacrolimus whole-blood trough levels, and assess renal function frequently.",
        "risk_factor": "Profound Tacrolimus Accumulation and Acute Nephrotoxicity",
        "recommended_alternative": "Micafungin",
        "culprit_drug": "ketoconazole"
    },
    tuple(sorted(["itraconazole", "tacrolimus"])): {
        "severity": "MAJOR",
        "description": "Itraconazole is a potent inhibitor of CYP3A4 and P-glycoprotein, preventing tacrolimus metabolism and leading to profound drug accumulation and severe acute renal failure.",
        "fda_summary": "Itraconazole significantly elevates tacrolimus blood concentrations; frequent blood concentration monitoring and dose reductions are necessary.",
        "clinical_action": "Reduce tacrolimus dose substantially, perform frequent therapeutic drug monitoring of whole-blood trough levels, and monitor serum creatinine closely.",
        "risk_factor": "Severe Acute Renal Failure and Neurotoxicity",
        "recommended_alternative": "Anidulafungin",
        "culprit_drug": "itraconazole"
    },
    tuple(sorted(["fluconazole", "tacrolimus"])): {
        "severity": "MAJOR",
        "description": "Fluconazole inhibits CYP3A4 metabolism of Tacrolimus, leading to elevated blood trough levels and heightened risk of severe nephrotoxicity and neurotoxicity.",
        "fda_summary": "Concomitant use of fluconazole with tacrolimus increases tacrolimus exposure. Monitor whole blood concentrations and adjust dosage as clinically indicated.",
        "clinical_action": "Adjust tacrolimus dosage downward, monitor tacrolimus blood trough concentrations closely, and monitor for signs of acute nephrotoxicity.",
        "risk_factor": "Elevated Trough Concentrations and Nephrotoxicity",
        "recommended_alternative": "Caspofungin",
        "culprit_drug": "fluconazole"
    },
    tuple(sorted(["voriconazole", "tacrolimus"])): {
        "severity": "MAJOR",
        "description": "Voriconazole strongly inhibits CYP3A4, causing profound increases in tacrolimus blood concentrations and exposing patients to severe nephrotoxicity and metabolic complications.",
        "fda_summary": "When initiating voriconazole in patients already taking tacrolimus, it is recommended that the tacrolimus dose be reduced to one-third and blood levels monitored frequently.",
        "clinical_action": "Reduce tacrolimus dose to one-third of baseline immediately upon initiation of voriconazole and monitor blood trough levels frequently.",
        "risk_factor": "Critical Calcineurin Inhibitor Toxicity and Renal Impairment",
        "recommended_alternative": "Micafungin",
        "culprit_drug": "voriconazole"
    },
    tuple(sorted(["amiodarone", "levofloxacin"])): {
        "severity": "MAJOR",
        "description": "Amiodarone and Levofloxacin exert additive delays in myocardial ventricular repolarization by blocking cardiac hERG potassium channels, causing synergistic QTc interval prolongation and provoking life-threatening Torsades de Pointes.",
        "fda_summary": "Co-administration of fluoroquinolones with class III antiarrhythmics such as amiodarone poses serious risk of additive QT prolongation and ventricular arrhythmias.",
        "clinical_action": "Avoid concomitant use. Choose an alternative antimicrobial without QT-prolonging liability and perform continuous ECG telemetry if co-administration is unavoidable.",
        "risk_factor": "Life-Threatening QTc Prolongation and Torsades de Pointes",
        "recommended_alternative": "Ceftriaxone",
        "culprit_drug": "levofloxacin"
    },
    tuple(sorted(["amiodarone", "moxifloxacin"])): {
        "severity": "CONTRAINDICATED",
        "description": "Moxifloxacin has the highest intrinsic QT-prolonging potential among fluoroquinolones. Combining Moxifloxacin with Amiodarone causes profound, synergistic prolongation of ventricular repolarization, triggering polymorphic ventricular tachycardia (Torsades de Pointes) and sudden cardiac arrest.",
        "fda_summary": "Concomitant use of moxifloxacin with Class IA or Class III antiarrhythmic agents like amiodarone is contraindicated due to increased risk of fatal cardiac arrhythmias.",
        "clinical_action": "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.",
        "risk_factor": "Fatal Cardiac Arrhythmia and Ventricular Fibrillation",
        "recommended_alternative": "Amoxicillin-Clavulanate",
        "culprit_drug": "moxifloxacin"
    },
    tuple(sorted(["amoxicillin", "methotrexate"])): {
        "severity": "MAJOR",
        "description": "Penicillins compete for organic anion transporter (OAT1/OAT3)-mediated renal tubular secretion with Methotrexate, leading to elevated serum methotrexate levels and severe bone marrow suppression, pancytopenia, and acute nephrotoxicity.",
        "fda_summary": "Penicillins may reduce the renal clearance of methotrexate, leading to increased serum levels and risk of toxicity.",
        "clinical_action": "Monitor complete blood counts and renal function closely; consider dose reduction or alternative antibiotic.",
        "risk_factor": "Severe Bone Marrow Suppression and Pancytopenia",
        "recommended_alternative": "Azithromycin",
        "culprit_drug": "amoxicillin"
    }
}


def clean_drug_name(raw: str) -> str:
    """Standardizes raw drug string."""
    if not raw or not isinstance(raw, str):
        return ""

    text = raw.lower().strip()
    text = re.sub(r'\(.*?\)', ' ', text)
    text = DOSAGE_REGEX.sub(' ', text)
    text = re.sub(r'[^\w\s-]', ' ', text)

    tokens = text.split()
    if not tokens:
        return ""

    joined = " ".join(tokens)
    if joined in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[joined]
    if tokens[0] in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[tokens[0]]

    filtered = [t for t in tokens if t not in SALT_AND_FORM_TOKENS and not t.isdigit()]
    if not filtered:
        filtered = [t for t in tokens if not t.isdigit()]
        if not filtered:
            filtered = tokens

    cand = " ".join(filtered)
    if cand in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[cand]
    if filtered[0] in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[filtered[0]]

    return cand


def clean_fda_label_text(raw_text: str) -> str:
    """
    Cleans up FDA label text:
    - Strips raw table headers (e.g., 'Table 3: ...', '7 DRUG INTERACTIONS', '( 7 )')
    - Strips section citation brackets (e.g., '[see Dosage and Administration (2.5)]', '[see Warnings and Precautions (5.1)]')
    - Removes XML/HTML tags and normalize whitespaces.
    """
    if not raw_text:
        return ""
    text = raw_text
    # Strip HTML/XML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Strip raw table headers (e.g. Table 3: Drugs that Can Increase..., Table 1 - ...)
    text = re.sub(r'Table\s+\d+[\s:\-–—][^\.\n]*?(?=[A-Z]|\n|\.|$)', ' ', text, flags=re.IGNORECASE)
    # Strip section citation brackets e.g. [see Dosage and Administration (2.5)], [see Clinical Pharmacology (12.3)]
    text = re.sub(r'\[\s*see\s+[^\]]+\]', ' ', text, flags=re.IGNORECASE)
    # Strip raw numbered section references e.g. (7.1), 7.1 CLINICAL PHARMACOLOGY
    text = re.sub(r'\(\s*7(?:\.\d+)?\s*\)', ' ', text)
    text = re.sub(r'7\s+DRUG\s+INTERACTIONS', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'7\.\d+\s+[A-Za-z\s]+', ' ', text)
    # Collapse extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
def slice_scoped_fda_text(fda_text: str, partner_drug: str) -> Optional[str]:
    """
    Isolates the specific clinical interaction subsection mentioning the partner drug.
    Prevents text bleed into adjacent numbered subsections (e.g. 7.1 vs 7.2 vs 7.3).
    """
    if not fda_text or not partner_drug:
        return None

    clean_target = clean_drug_name(partner_drug)
    sections = re.split(r'\n\s*(?:7\.\d+|Table\s+\d+|[A-Z0-9\s-]{4,30}:)', fda_text)
    
    for sec in sections:
        if clean_target in sec.lower():
            cleaned = clean_fda_label_text(sec)
            if cleaned and len(cleaned) > 20:
                return cleaned

    # Fallback to paragraph splitting if numbered sections are not present
    paragraphs = [p.strip() for p in fda_text.split('\n\n') if p.strip()]
    for p in paragraphs:
        if clean_target in p.lower():
            cleaned = clean_fda_label_text(p)
            if cleaned and len(cleaned) > 20:
                return cleaned

    return clean_fda_label_text(fda_text) if clean_target in fda_text.lower() else None

def synthesize_clinical_action(d1_clean: str, d2_clean: str, severity: str = "MODERATE", default_guidance: str = "") -> str:
    """
    Enforces Evidence-Based Clinical Action Rules:
    1. NEVER suggest 'spacing out doses' for irreversible drugs, systemic anticoagulants, or life-threatening pharmacodynamics.
    2. For contraindicated pairs, explicitly state:
       'Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities.'
    3. Antiplatelet + Anticoagulant: Strictly recommend avoidance / lowest dose / gastroprotection (PPI) / bleed monitoring.
    4. Chelation / multivalent cations: Recommend spacing by 2-4 hours.
    """
    s_upper = (severity or "").upper().strip()
    if s_upper == "CONTRAINDICATED":
        return "Avoid concomitant use. Discontinue or select non-interacting therapeutic alternatives. If essential in emergencies, monitor intensively for acute toxicities."

    is_ap1 = d1_clean in ANTIPLATELETS
    is_ap2 = d2_clean in ANTIPLATELETS
    is_ac1 = d1_clean in ANTICOAGULANTS
    is_ac2 = d2_clean in ANTICOAGULANTS
    is_ns1 = d1_clean in NSAIDS
    is_ns2 = d2_clean in NSAIDS

    # Antiplatelet / NSAID + Anticoagulant Rule
    if (is_ap1 or is_ns1) and (is_ac1 or is_ac2):
        return "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely."
    if (is_ap2 or is_ns2) and (is_ac1 or is_ac2):
        return "Avoid combination unless clearly indicated; if essential, use lowest effective dose, consider gastroprotection (e.g., PPI), and monitor bleed/INR status closely."

    # Two anticoagulants or two antiplatelets
    if (is_ac1 and is_ac2) or (is_ap1 and is_ap2):
        return "Avoid concurrent therapy due to additive hemorrhagic toxicity. If transitioning between agents, adhere strictly to overlapping bridging protocols and frequent coagulation monitoring."

    # Chelation rule (only acceptable place to recommend spacing)
    is_chel_target = d1_clean in CHELATION_DRUGS or d2_clean in CHELATION_DRUGS
    is_chel_agent = any(c in d1_clean or c in d2_clean for c in CHELATING_AGENTS)
    if is_chel_target and is_chel_agent:
        return "Space administration by at least 2 hours before or 4 hours after cation ingestion to prevent gastrointestinal chelation and malabsorption."

    # Disallow 'spacing out' for any systemic drug
    if default_guidance and not any(w in default_guidance.lower() for w in ["spacing out", "spacing doses", "dosing intervals", "space doses"]):
        return default_guidance

    if s_upper in ["MAJOR", "CRITICAL"]:
        return "Avoid concomitant use where safer therapeutic alternatives exist. If co-administration is clinically required, adjust dosing and closely monitor target biomarkers and clinical toxicities."

    return "Monitor patient closely for adverse reactions, assess baseline organ function, and evaluate alternative therapeutic agents with lower interaction potential."


# Medical Category Alternatives & Risk Factor Mapping Dictionary
# Based on Clinical Pharmacopeia, NLM RxNorm, and FDA Safety Guidelines
CLINICAL_ALTERNATIVE_TAXONOMY: List[Dict[str, Any]] = [
    # 1. Anticoagulants + Antiplatelets / NSAIDs -> Switch NSAID/Antiplatelet to Paracetamol / COX-2 with gastroprotection
    {
        "matcher": lambda d1, d2, text: (d1 in ANTICOAGULANTS or d2 in ANTICOAGULANTS) and (d1 in ANTIPLATELETS or d2 in ANTIPLATELETS or d1 in NSAIDS or d2 in NSAIDS),
        "culprit_detector": lambda d1, d2: d1 if (d1 in ANTIPLATELETS or d1 in NSAIDS) else d2,
        "victim_detector": lambda d1, d2: d2 if (d1 in ANTIPLATELETS or d1 in NSAIDS) else d1,
        "alternative": "Acetaminophen (Paracetamol)",
        "risk_factor": "Gastrointestinal Bleeding and Coagulopathy"
    },
    # 2. Anticoagulants + CYP1A2 / Fluoroquinolone inhibitors -> Switch Fluoroquinolone to Amoxicillin-Clavulanate or Ceftriaxone
    {
        "matcher": lambda d1, d2, text: (d1 in ANTICOAGULANTS or d2 in ANTICOAGULANTS) and (d1 in FLUOROQUINOLONES or d2 in FLUOROQUINOLONES),
        "culprit_detector": lambda d1, d2: d1 if d1 in FLUOROQUINOLONES else d2,
        "victim_detector": lambda d1, d2: d2 if d1 in FLUOROQUINOLONES else d1,
        "alternative": "Amoxicillin-Clavulanate",
        "risk_factor": "Severe Hemorrhage and Supratherapeutic INR"
    },
    # 3. Two Anticoagulants (Dual Anticoagulation)
    {
        "matcher": lambda d1, d2, text: d1 in ANTICOAGULANTS and d2 in ANTICOAGULANTS,
        "culprit_detector": lambda d1, d2: d1,
        "victim_detector": lambda d1, d2: d2,
        "alternative": "Monotherapy Anticoagulant Protocol",
        "risk_factor": "Severe Uncontrolled Internal Hemorrhage"
    },
    # 4. Serotonergic Crisis: MAOI + SSRI/SNRI or Dual Serotonergic Agents -> Switch to Vancomycin (if Linezolid) or Bupropion/Mirtazapine
    {
        "matcher": lambda d1, d2, text: (d1 in MAOI_DRUGS and d2 in SSRI_SNRI_DRUGS) or (d2 in MAOI_DRUGS and d1 in SSRI_SNRI_DRUGS),
        "culprit_detector": lambda d1, d2: d1 if d1 in MAOI_DRUGS else d2,
        "victim_detector": lambda d1, d2: d2 if d1 in MAOI_DRUGS else d1,
        "alternative": "Vancomycin",
        "risk_factor": "Fatal Serotonin Syndrome and Neuromuscular Crisis"
    },
    # 5. Dual SSRI/SNRI or Serotonin Toxicity from general agents
    {
        "matcher": lambda d1, d2, text: (d1 in SSRI_SNRI_DRUGS and d2 in SSRI_SNRI_DRUGS) or "serotonin syndrome" in text.lower(),
        "culprit_detector": lambda d1, d2: d2,
        "victim_detector": lambda d1, d2: d1,
        "alternative": "Bupropion",
        "risk_factor": "Serotonin Toxicity and Central Nervous System Hyperactivity"
    },
    # 6. Cardiac QTc Prolongation: Antiarrhythmic + Fluoroquinolone / Macrolide
    {
        "matcher": lambda d1, d2, text: ((d1 in QT_PROLONGING_ANTIARRHYTHMICS or d2 in QT_PROLONGING_ANTIARRHYTHMICS) and (d1 in FLUOROQUINOLONES or d2 in FLUOROQUINOLONES or any(m in (d1, d2) for m in ['azithromycin', 'clarithromycin', 'erythromycin']))) or "torsades" in text.lower() or "qt prolongation" in text.lower() or "qtc" in text.lower(),
        "culprit_detector": lambda d1, d2: d1 if (d1 in FLUOROQUINOLONES or any(m in d1 for m in ['azithromycin', 'clarithromycin', 'erythromycin'])) else d2,
        "victim_detector": lambda d1, d2: d2 if (d1 in FLUOROQUINOLONES or any(m in d1 for m in ['azithromycin', 'clarithromycin', 'erythromycin'])) else d1,
        "alternative": "Doxycycline",
        "risk_factor": "Fatal Ventricular Arrhythmia (Torsades de Pointes)"
    },
    # 7. Statin + Strong CYP3A4 Inhibitor (Macrolide or Azole) -> Switch to Rosuvastatin / Pravastatin or non-inhibiting Azithromycin
    {
        "matcher": lambda d1, d2, text: (any(s in (d1, d2) for s in ['simvastatin', 'atorvastatin', 'lovastatin']) and (any(i in (d1, d2) for i in STRONG_CYP3A4_INHIBITORS) or any(a in (d1, d2) for a in AZOLE_ANTIFUNGALS))) or "rhabdomyolysis" in text.lower(),
        "culprit_detector": lambda d1, d2: d1 if any(i in d1 for i in STRONG_CYP3A4_INHIBITORS) or any(a in d1 for a in AZOLE_ANTIFUNGALS) else d2,
        "victim_detector": lambda d1, d2: d2 if any(i in d1 for i in STRONG_CYP3A4_INHIBITORS) or any(a in d1 for a in AZOLE_ANTIFUNGALS) else d1,
        "alternative": "Rosuvastatin",
        "risk_factor": "Severe Rhabdomyolysis and Acute Renal Failure"
    },
    # 8. Immunosuppressant (Tacrolimus/Cyclosporine) + Azole Antifungal -> Switch Azole to Echinocandin (Micafungin/Anidulafungin)
    {
        "matcher": lambda d1, d2, text: (d1 in IMMUNOSUPPRESSANTS_NTI or d2 in IMMUNOSUPPRESSANTS_NTI) and (d1 in AZOLE_ANTIFUNGALS or d2 in AZOLE_ANTIFUNGALS),
        "culprit_detector": lambda d1, d2: d1 if d1 in AZOLE_ANTIFUNGALS else d2,
        "victim_detector": lambda d1, d2: d2 if d1 in AZOLE_ANTIFUNGALS else d1,
        "alternative": "Micafungin",
        "risk_factor": "Profound Immunosuppressant Toxicity and Acute Renal Failure"
    },
    # 9. Methotrexate + Penicillins / NSAIDs (Renal secretion blockade) -> Switch to Ceftriaxone or Acetaminophen
    {
        "matcher": lambda d1, d2, text: "methotrexate" in (d1, d2),
        "culprit_detector": lambda d1, d2: d1 if d2 == "methotrexate" else d2,
        "victim_detector": lambda d1, d2: "methotrexate",
        "alternative": "Ceftriaxone",
        "risk_factor": "Bone Marrow Suppression and Severe Pancytopenia"
    },
    # 10. Colchicine + Strong CYP3A4 / P-gp inhibitor
    {
        "matcher": lambda d1, d2, text: "colchicine" in (d1, d2) and any(c in (d1, d2) for c in STRONG_CYP3A4_INHIBITORS),
        "culprit_detector": lambda d1, d2: d1 if d2 == "colchicine" else d2,
        "victim_detector": lambda d1, d2: "colchicine",
        "alternative": "Azithromycin",
        "risk_factor": "Fatal Colchicine Toxicity and Multi-Organ Failure"
    },
    # 11. Digoxin + P-gp / AV Nodal blockers (Amiodarone, Verapamil, Clarithromycin)
    {
        "matcher": lambda d1, d2, text: "digoxin" in (d1, d2) or "digitalis" in text.lower(),
        "culprit_detector": lambda d1, d2: d1 if d2 == "digoxin" else d2,
        "victim_detector": lambda d1, d2: "digoxin",
        "alternative": "Metoprolol Succinate",
        "risk_factor": "Digitalis Toxicity and Fatal Heart Block"
    },
    # 12. Dual Renin-Angiotensin System Blockade (ACE Inhibitor + ARB)
    {
        "matcher": lambda d1, d2, text: any(d1.endswith(s) for s in ['pril', 'sartan']) and any(d2.endswith(s) for s in ['pril', 'sartan']),
        "culprit_detector": lambda d1, d2: d2,
        "victim_detector": lambda d1, d2: d1,
        "alternative": "Amlodipine",
        "risk_factor": "Refractory Hypotension, Hyperkalemia, and Acute Renal Impairment"
    },
    # 13. Dual Central Nervous System / Respiratory Depressants (Opioids + Benzodiazepines)
    {
        "matcher": lambda d1, d2, text: any(b in (d1, d2) for b in ['alprazolam', 'diazepam', 'lorazepam', 'clonazepam']) and any(o in (d1, d2) for o in ['tramadol', 'codeine', 'morphine', 'oxycodone', 'fentanyl', 'hydrocodone']),
        "culprit_detector": lambda d1, d2: d1 if any(b in d1 for b in ['alprazolam', 'diazepam', 'lorazepam', 'clonazepam']) else d2,
        "victim_detector": lambda d1, d2: d2 if any(b in d1 for b in ['alprazolam', 'diazepam', 'lorazepam', 'clonazepam']) else d1,
        "alternative": "Buspirone",
        "risk_factor": "Fatal Central Nervous System Depression and Severe Hypoventilation"
    },
    # 14. Chelation / Multivalent Cations with Antibacterials or Levothyroxine
    {
        "matcher": lambda d1, d2, text: (d1 in CHELATION_DRUGS or d2 in CHELATION_DRUGS) and any(c in (d1, d2) for c in CHELATING_AGENTS),
        "culprit_detector": lambda d1, d2: d1 if any(c in d1 for c in CHELATING_AGENTS) else d2,
        "victim_detector": lambda d1, d2: d2 if any(c in d1 for c in CHELATING_AGENTS) else d1,
        "alternative": "Temporally Spaced Formulation (2h Pre / 4h Post)",
        "risk_factor": "Severe Chelation Complexation and Complete Therapeutic Failure"
    }
]


def resolve_dynamic_alternative(
    c1: str,
    c2: str,
    evidence_text: str = "",
    rx_meta_map: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[str, str, str, str]:
    """
    Dynamically determines:
    1. culprit_drug: The offending agent causing the clash or inhibition.
    2. victim_drug: The drug whose clearance, safety, or stability is compromised.
    3. recommended_alternative: Safe in-class or therapeutic replacement with zero clearance interference.
    4. risk_factor: Clinically validated pathological threat.
    
    If not in curated clinical rules, synthesizes dynamic safe replacement from Established Pharmacologic Class (EPC).
    """
    clean_text = (evidence_text or "").lower()
    rx_meta_map = rx_meta_map or {}

    # Check Taxonomy Rules First
    for rule in CLINICAL_ALTERNATIVE_TAXONOMY:
        try:
            if rule["matcher"](c1, c2, clean_text):
                culprit = rule["culprit_detector"](c1, c2)
                victim = rule["victim_detector"](c1, c2)
                return (
                    culprit.capitalize(),
                    victim.capitalize(),
                    rule["alternative"],
                    rule["risk_factor"]
                )
        except Exception:
            continue

    # Fallback to Dynamic Pharmacologic Class Synthesis via NLM RxNav / RxClass metadata
    meta1 = rx_meta_map.get(c1, {})
    meta2 = rx_meta_map.get(c2, {})
    epc1 = (meta1.get("epc") or "").lower()
    epc2 = (meta2.get("epc") or "").lower()

    # Determine risk factor from clinical evidence text
    detected_risk = "Severe Toxic Drug Accumulation and Adverse Organ Toxicity"
    if any(k in clean_text for k in ["bleed", "hemorrhag", "inr", "coagulat"]):
        detected_risk = "Severe Hemorrhage and Elevated Bleeding Risk"
    elif any(k in clean_text for k in ["qt", "torsade", "arrhythmi", "cardiac"]):
        detected_risk = "Cardiac Ventricular Repolarization Delay and Arrhythmia"
    elif any(k in clean_text for k in ["serotonin", "hyperthermi", "clonus"]):
        detected_risk = "Acute Serotonin Syndrome and Neuromuscular Hyperactivity"
    elif any(k in clean_text for k in ["rhabdomyol", "myopath", "creatine kinase"]):
        detected_risk = "Rhabdomyolysis and Severe Skeletal Myopathy"
    elif any(k in clean_text for k in ["renal", "nephro", "kidney"]):
        detected_risk = "Acute Nephrotoxicity and Impaired Renal Clearance"
    elif any(k in clean_text for k in ["hypotension", "pressure", "shock"]):
        detected_risk = "Severe Hemodynamic Collapse and Refractory Hypotension"

    # Identify candidate alternative based on pharmacologic class of the offending agent
    candidate_alt = "Non-Interacting Monotherapy Alternative"
    culprit_cand = c2.capitalize()
    victim_cand = c1.capitalize()

    if "antibacterial" in epc2 or "antimicrobial" in epc2:
        candidate_alt = "Azithromycin" if "quinolone" in epc2 else "Amoxicillin-Clavulanate"
        culprit_cand = c2.capitalize()
        victim_cand = c1.capitalize()
    elif "antibacterial" in epc1 or "antimicrobial" in epc1:
        candidate_alt = "Azithromycin" if "quinolone" in epc1 else "Amoxicillin-Clavulanate"
        culprit_cand = c1.capitalize()
        victim_cand = c2.capitalize()
    elif "anti-inflammatory" in epc2 or "nsaid" in epc2:
        candidate_alt = "Acetaminophen (Paracetamol)"
        culprit_cand = c2.capitalize()
        victim_cand = c1.capitalize()
    elif "anti-inflammatory" in epc1 or "nsaid" in epc1:
        candidate_alt = "Acetaminophen (Paracetamol)"
        culprit_cand = c1.capitalize()
        victim_cand = c2.capitalize()
    elif "antidepressant" in epc2 or "serotonin" in epc2:
        candidate_alt = "Bupropion"
        culprit_cand = c2.capitalize()
        victim_cand = c1.capitalize()
    elif "reductase inhibitor" in epc2 or "statin" in epc2:
        candidate_alt = "Pravastatin"
        culprit_cand = c2.capitalize()
        victim_cand = c1.capitalize()

    return (culprit_cand, victim_cand, candidate_alt, detected_risk)


def rewrite_boilerplate_mechanism(d1_clean: str, d2_clean: str, raw_desc: str) -> str:
    """
    Rewrites generic CSV boilerplate strings (e.g. '[Drug A] may increase the serotonergic activities of [Drug B]').
    Identifies physiological mechanism, target enzymes/receptors, and precise causal direction.
    """
    if not raw_desc:
        return f"Co-administration of {d1_clean.capitalize()} and {d2_clean.capitalize()} results in altered pharmacokinetics and additive pharmacological effects."

    # Check MAOI + Serotonergic / SSRI / SNRI
    is_maoi1 = d1_clean in MAOI_DRUGS
    is_maoi2 = d2_clean in MAOI_DRUGS
    is_ssri1 = d1_clean in SSRI_SNRI_DRUGS
    is_ssri2 = d2_clean in SSRI_SNRI_DRUGS

    if (is_maoi1 and is_ssri2) or (is_maoi2 and is_ssri1):
        maoi_name = d1_clean.capitalize() if is_maoi1 else d2_clean.capitalize()
        ssri_name = d2_clean.capitalize() if is_maoi1 else d1_clean.capitalize()
        return (
            f"{maoi_name}, acting as a monoamine oxidase A (MAO-A) inhibitor, prevents central serotonin catabolism. "
            f"When co-administered with {ssri_name} (serotonin reuptake inhibitor), this synergistically compounds synaptic "
            f"serotonin accumulation, precipitating potentially life-threatening Serotonin Syndrome (hyperthermia, autonomic instability, and neuromuscular rigidity)."
        )

    # Check Antiplatelet / NSAID + Anticoagulant
    is_ap1 = d1_clean in ANTIPLATELETS or d1_clean in NSAIDS
    is_ap2 = d2_clean in ANTIPLATELETS or d2_clean in NSAIDS
    is_ac1 = d1_clean in ANTICOAGULANTS
    is_ac2 = d2_clean in ANTICOAGULANTS

    if (is_ap1 and is_ac2) or (is_ap2 and is_ac1):
        ap_name = d1_clean.capitalize() if is_ap1 else d2_clean.capitalize()
        ac_name = d2_clean.capitalize() if is_ap1 else d1_clean.capitalize()
        return (
            f"{ap_name} suppresses platelet cyclooxygenase-mediated thromboxane A2 aggregation and induces gastric mucosal irritation, "
            f"synergistically impairing hemostasis alongside {ac_name}-mediated inhibition of clotting factor synthesis/activity, "
            f"dramatically elevating the risk of major upper gastrointestinal hemorrhage and life-threatening systemic bleeding."
        )

    # Check Tacrolimus / Immunosuppressant + Azole Antifungal
    is_imm1 = d1_clean in IMMUNOSUPPRESSANTS_NTI
    is_imm2 = d2_clean in IMMUNOSUPPRESSANTS_NTI
    is_azole1 = d1_clean in AZOLE_ANTIFUNGALS
    is_azole2 = d2_clean in AZOLE_ANTIFUNGALS

    if (is_imm1 and is_azole2) or (is_imm2 and is_azole1):
        imm_name = d1_clean.capitalize() if is_imm1 else d2_clean.capitalize()
        azole_name = d2_clean.capitalize() if is_imm1 else d1_clean.capitalize()
        return (
            f"{azole_name} potently inhibits cytochrome P450 CYP3A4 and P-glycoprotein efflux transport, "
            f"significantly impairing metabolic clearance of {imm_name} and causing dangerous systemic drug accumulation, "
            f"which drastically elevates the risk of severe acute nephrotoxicity, neurotoxicity, and life-threatening immunosuppression-related complications."
        )

    # Check Amiodarone / Antiarrhythmic + Fluoroquinolone (Additive QTc prolongation)
    is_arr1 = d1_clean in QT_PROLONGING_ANTIARRHYTHMICS
    is_arr2 = d2_clean in QT_PROLONGING_ANTIARRHYTHMICS
    is_fq1 = d1_clean in FLUOROQUINOLONES
    is_fq2 = d2_clean in FLUOROQUINOLONES

    if (is_arr1 and is_fq2) or (is_arr2 and is_fq1):
        arr_name = d1_clean.capitalize() if is_arr1 else d2_clean.capitalize()
        fq_name = d2_clean.capitalize() if is_arr1 else d1_clean.capitalize()
        return (
            f"Concurrent administration of {arr_name} and {fq_name} produces additive electrophysiological delays in "
            f"myocardial ventricular repolarization via cardiac IKr (hERG) potassium channel blockade, "
            f"causing extreme QTc interval prolongation and provoking polymorphic ventricular tachycardia (Torsades de Pointes) and fatal cardiac arrest."
        )

    # Check Colchicine + Strong CYP3A4/P-gp Inhibitor
    if ("colchicine" in (d1_clean, d2_clean)) and any(c in (d1_clean, d2_clean) for c in STRONG_CYP3A4_INHIBITORS):
        other = d1_clean.capitalize() if d2_clean == "colchicine" else d2_clean.capitalize()
        return (
            f"{other} strongly inhibits hepatic/intestinal CYP3A4 and P-glycoprotein-mediated efflux, "
            f"preventing metabolic clearance of Colchicine and leading to severe intracellular colchicine toxicity, "
            f"precipitating potentially fatal multi-organ failure, bone marrow aplasia, and neuromyopathy."
        )

    # Rewrite generic boilerplate template phrases
    cleaned_desc = raw_desc
    boilerplate_patterns = [
        (r'may increase the serotonergic activities of', 'potentiates serotonergic neurotransmission and elevates synaptic serotonin concentration alongside'),
        (r'may increase the anticoagulant activities of', 'potentiates systemic anticoagulation and exacerbates bleeding diathesis with'),
        (r'may increase the hypertensive activities of', 'causes additive vasopressor stimulation and acute blood pressure surges when combined with'),
        (r'may increase the bradycardic activities of', 'synergistically slows cardiac sinus nodal conduction and AV conduction with'),
        (r'may increase the central nervous system depressant.*activities of', 'produces profound additive central nervous system and respiratory depression with')
    ]
    for pattern, replacement in boilerplate_patterns:
        cleaned_desc = re.sub(pattern, replacement, cleaned_desc, flags=re.IGNORECASE)

    return cleaned_desc


def resolve_severity_override(
    base_severity: str,
    fda_text: str = "",
    faers_reactions: List[str] = None,
    description: str = "",
    d1_clean: str = "",
    d2_clean: str = ""
) -> str:
    """
    CRITICAL CLINICAL SEVERITY ADJUDICATION:
    The input CSV database often contains OUTDATED, DEFAULT, or MISCLASSIFIED severity ratings
    (such as marking severe MAOI or bleeding risks as 'MODERATE').
    Independently recalculates and enforces the interaction_level:

    1. CONTRAINDICATED:
       - FDA label states co-administration is contraindicated or to be avoided.
       - Fatal or acute life-threatening syndromes (e.g., Serotonin Syndrome from MAOI + SSRI/SNRI;
         Colchicine + Clarithromycin; Moxifloxacin + Amiodarone).
    2. MAJOR:
       - Synergistic risk of major organ failure, severe hemorrhage, or ventricular arrhythmias/QTc prolongation
         (e.g., Warfarin + Aspirin/NSAIDs; Tacrolimus + Azole antifungals; Amiodarone + Fluoroquinolones).
       - Requires substantial dose reduction or close therapeutic monitoring to prevent hospitalization.
    3. MODERATE:
       - Non-life-threatening interactions resulting in altered efficacy or manageable side effects requiring monitoring.
    4. MINOR / NONE:
       - Minimal clinical impact.
    """
    combined_evidence = f"{fda_text} {description} {' '.join(faers_reactions or [])}".lower()
    sev = (base_severity or "MODERATE").upper().strip()

    # Clinical Pharmacological Class Rules
    if d1_clean and d2_clean:
        # Rule 1: MAOI + SSRI/SNRI -> ALWAYS CONTRAINDICATED
        if ((d1_clean in MAOI_DRUGS and d2_clean in SSRI_SNRI_DRUGS) or
            (d2_clean in MAOI_DRUGS and d1_clean in SSRI_SNRI_DRUGS)):
            return "CONTRAINDICATED"

        # Rule 2: Colchicine + Strong CYP3A4 Inhibitor -> CONTRAINDICATED
        if ("colchicine" in (d1_clean, d2_clean)) and any(c in (d1_clean, d2_clean) for c in STRONG_CYP3A4_INHIBITORS):
            return "CONTRAINDICATED"

        # Rule 3: Amiodarone + Moxifloxacin -> CONTRAINDICATED
        if tuple(sorted([d1_clean, d2_clean])) == ("amiodarone", "moxifloxacin"):
            return "CONTRAINDICATED"

        # Rule 4: Tacrolimus / Cyclosporine + Azoles -> MAJOR
        if ((d1_clean in IMMUNOSUPPRESSANTS_NTI and d2_clean in AZOLE_ANTIFUNGALS) or
            (d2_clean in IMMUNOSUPPRESSANTS_NTI and d1_clean in AZOLE_ANTIFUNGALS)):
            return "MAJOR"

        # Rule 5: Warfarin + Aspirin / NSAIDs -> MAJOR
        if (((d1_clean in ANTIPLATELETS or d1_clean in NSAIDS) and d2_clean in ANTICOAGULANTS) or
            ((d2_clean in ANTIPLATELETS or d2_clean in NSAIDS) and d1_clean in ANTICOAGULANTS)):
            return "MAJOR"

        # Rule 6: Amiodarone / Antiarrhythmics + Fluoroquinolones -> MAJOR or CONTRAINDICATED
        if ((d1_clean in QT_PROLONGING_ANTIARRHYTHMICS and d2_clean in FLUOROQUINOLONES) or
            (d2_clean in QT_PROLONGING_ANTIARRHYTHMICS and d1_clean in FLUOROQUINOLONES)):
            if "moxifloxacin" in (d1_clean, d2_clean):
                return "CONTRAINDICATED"
            return "MAJOR"

    contraindicated_triggers = [
        "contraindicated", "contraindication", "fatal", "torsades de pointes", "torsades",
        "serotonin syndrome", "avoid concomitant use", "concomitant use is contraindicated",
        "do not use concomitantly"
    ]
    major_triggers = [
        "severe hemorrhage", "severe bleeding", "life-threatening", "rhabdomyolysis",
        "qt prolongation", "prolongs the qt", "ventricular arrhythmia", "cardiac arrest",
        "respiratory depression", "bone marrow suppression", "nephrotoxicity", "renal failure"
    ]

    if any(term in combined_evidence for term in contraindicated_triggers):
        return "CONTRAINDICATED"

    if any(term in combined_evidence for term in major_triggers):
        if SEVERITY_RANKS.get(sev, 1) < SEVERITY_RANKS["MAJOR"]:
            return "MAJOR"

    return sev


def synthesize_fda_summary(raw_fda_text: str, partner_drug: str) -> Optional[str]:
    """
    Synthesizes clean 1-2 sentence clinical summary of FDA package insert guidance.
    Filters out raw OCR tables, table headers, and citation brackets.
    """
    if not raw_fda_text:
        return None

    clean_text = clean_fda_label_text(raw_fda_text)

    # Split into clean sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    partner_clean = clean_drug_name(partner_drug)

    meaningful_sentences = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean or len(s_clean) < 20:
            continue
        # Skip sentences that are just lists of comma-separated drugs
        if s_clean.count(',') > 4 and not any(v in s_clean.lower() for v in ['may', 'increase', 'risk', 'concomitant', 'inhibit', 'contraindicated']):
            continue
        if partner_clean in s_clean.lower() or any(w in s_clean.lower() for w in ['concomitant', 'bleeding', 'toxicity', 'arrhythmia', 'monitor', 'inhibit', 'contraindicated', 'syndrome']):
            meaningful_sentences.append(s_clean)

    if meaningful_sentences:
        candidate = " ".join(meaningful_sentences[:2]).strip()
        if not candidate.endswith(('.', '!', '?')):
            candidate += '.'
        return candidate

    return None


class InteractionEngine:
    def __init__(self):
        self.interactions: Dict[Tuple[str, str], str] = {}
        self.known_drugs: Set[str] = set()
        self.loaded_count = 0

    def load_from_csv(self, csv_path: str):
        import pandas as pd
        if not os.path.exists(csv_path):
            return

        df = pd.read_csv(csv_path)
        count = 0
        for d1, d2, desc in zip(df['Drug 1'].astype(str), df['Drug 2'].astype(str), df['Interaction Description'].astype(str)):
            c1 = clean_drug_name(d1)
            c2 = clean_drug_name(d2)
            desc_str = desc.strip()
            if not c1 or not c2:
                continue

            self.known_drugs.add(c1)
            self.known_drugs.add(c2)
            key = tuple(sorted([c1, c2]))
            if key not in self.interactions or len(desc_str) > len(self.interactions[key]):
                self.interactions[key] = desc_str
                count += 1

        self.loaded_count = count

    def resolve_drug(self, raw: str) -> str:
        cleaned = clean_drug_name(raw)
        if not self.known_drugs or cleaned in self.known_drugs:
            return cleaned

        for w in cleaned.split():
            if w in self.known_drugs:
                return w

        pref = [kd for kd in self.known_drugs if kd.startswith(cleaned) or cleaned.startswith(kd)]
        if pref:
            pref.sort(key=len)
            return pref[0]

        matches = difflib.get_close_matches(cleaned, self.known_drugs, n=1, cutoff=0.82)
        if matches:
            return matches[0]

        return cleaned

    def check_local_pair(self, drug_a: str, drug_b: str) -> Optional[Dict[str, Any]]:
        da_clean = self.resolve_drug(drug_a)
        db_clean = self.resolve_drug(drug_b)
        if not da_clean or not db_clean or da_clean == db_clean:
            return None

        rule_key = tuple(sorted([da_clean, db_clean]))
        if rule_key in HIGH_PRIORITY_CLINICAL_RULES:
            rule = HIGH_PRIORITY_CLINICAL_RULES[rule_key]
            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": da_clean,
                "resolvedDrug2": db_clean,
                "severity": rule["severity"].upper(),
                "description": rule["description"],
                "effect": rule["description"],
                "fda_summary": rule.get("fda_summary"),
                "clinical_action": rule.get("clinical_action"),
                "safe_to_prescribe": False,
                "source": "Clinical Guidelines"
            }

        if rule_key in self.interactions:
            raw_desc = self.interactions[rule_key]
            # Rewrite generic boilerplate / inverted mechanism
            desc = rewrite_boilerplate_mechanism(da_clean, db_clean, raw_desc)
            desc_lower = desc.lower()

            major_markers = [
                'fatal', 'death', 'cardiac', 'arrhythmia', 'qtc', 'qt prolongation',
                'torsades', 'bleeding', 'hemorrhage', 'toxicity', 'severe',
                'rhabdomyolysis', 'serotonin syndrome', 'apnea', 'respiratory depression'
            ]
            base_severity = "MAJOR" if any(m in desc_lower for m in major_markers) else "MODERATE"
            final_severity = resolve_severity_override(base_severity, description=desc, d1_clean=da_clean, d2_clean=db_clean)
            action = synthesize_clinical_action(da_clean, db_clean, severity=final_severity)

            is_safe = final_severity not in ["CONTRAINDICATED", "CRITICAL", "MAJOR"]

            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": da_clean,
                "resolvedDrug2": db_clean,
                "severity": final_severity,
                "description": desc,
                "effect": desc,
                "clinical_action": action,
                "safe_to_prescribe": is_safe,
                "source": "Clinical Interaction Registry"
            }

        return None

    def check_pair(self, drug_a: str, drug_b: str) -> Optional[Dict[str, Any]]:
        """Backward compatible check_pair method for test suites and scripts."""
        return self.check_local_pair(drug_a, drug_b)


async def fetch_openfda_label_advisory(client: httpx.AsyncClient, drug1: str, drug2: str) -> Optional[str]:
    clean1 = clean_drug_name(drug1)
    clean2 = clean_drug_name(drug2)
    url = (
        f"https://api.fda.gov/drug/label.json"
        f"?search=(openfda.generic_name:%22{clean1}%22+OR+openfda.brand_name:%22{clean1}%22)"
        f"+AND+drug_interactions:%22{clean2}%22&limit=1"
    )
    try:
        resp = await client.get(url, timeout=2.5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                raw_interaction = results[0].get("drug_interactions", [""])[0]
                if raw_interaction:
                    return synthesize_fda_summary(raw_interaction, drug2)
    except Exception:
        pass
    return None


async def fetch_openfda_faers_data(client: httpx.AsyncClient, drug1: str, drug2: str) -> Optional[Dict[str, Any]]:
    d1 = clean_drug_name(drug1).upper()
    d2 = clean_drug_name(drug2).upper()
    url = f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:"{d1}"+AND+patient.drug.medicinalproduct:"{d2}"&count=patient.reaction.reactionmeddrapt.exact'
    try:
        resp = await client.get(url, timeout=2.5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                total_reports = sum(item.get("count", 0) for item in results[:10])
                top_terms = [{"reaction": item['term'].title(), "cases": item.get('count', 0)} for item in results[:4]]
                return {
                    "total_cases": total_reports,
                    "top_reactions": top_terms
                }
    except Exception:
        pass
    return None


async def evaluate_polypharmacy_interactions(
    drugs: List[str],
    engine: InteractionEngine,
    rx_meta_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates multi-drug polypharmacy interactions for an arbitrary list of N drugs (>= 2).
    Enforces the requested Expert Clinical Pharmacologist JSON schema and Clinical Rules.
    """
    clean_drugs = [d.strip() for d in drugs if d and d.strip()]
    total_pairs = len(list(itertools.combinations(clean_drugs, 2))) if len(clean_drugs) >= 2 else 0

    if len(clean_drugs) < 2:
        return {
            "total_pairs_evaluated": 0,
            "flagged_interactions_count": 0,
            "highest_severity": "NONE",
            "status": "Safe",
            "severity": "None",
            "safe_to_prescribe": True,
            "interactions": [],
            "rxNormMetadata": rx_meta_list
        }

    consolidated_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}

    async with httpx.AsyncClient() as client:
        for d1, d2 in itertools.combinations(clean_drugs, 2):
            c1 = clean_drug_name(d1)
            c2 = clean_drug_name(d2)
            if not c1 or not c2 or c1 == c2:
                continue

            canonical_key = tuple(sorted([c1, c2]))
            if canonical_key in consolidated_pairs:
                continue

            pair_display = f"{canonical_key[0].capitalize()} ↔ {canonical_key[1].capitalize()}"

            # 1. Primary Knowledge Base: Local Clinical DB + High-Priority Rules
            local_match = engine.check_local_pair(d1, d2)

            # 2. Secondary Service: Clean synthesized FDA advisory
            fda_advisory = None
            if local_match and local_match.get("fda_summary"):
                fda_advisory = local_match["fda_summary"]
            else:
                fda_advisory = await fetch_openfda_label_advisory(client, d1, d2)
                if not fda_advisory:
                    fda_advisory = await fetch_openfda_label_advisory(client, d2, d1)

            # 3. Secondary Service: FAERS Post-Marketing Surveillance
            faers_data = await fetch_openfda_faers_data(client, d1, d2)
            if not faers_data:
                faers_data = await fetch_openfda_faers_data(client, d2, d1)

            # Check if interaction flagged
            if local_match or fda_advisory:
                raw_severity = local_match["severity"] if local_match else "MODERATE"
                raw_mechanism = (
                    local_match["description"] if local_match
                    else f"Co-administration of {d1} and {d2} may result in altered pharmacokinetics and increased adverse reaction frequency."
                )

                # Mechanism rewrite for physiological accuracy and enzyme/receptor pathways
                primary_contraindication = rewrite_boilerplate_mechanism(c1, c2, raw_mechanism)

                default_fda = f"Prescribing information cautions regarding concurrent administration of {d1} with {d2}."
                clean_fda = clean_fda_label_text(fda_advisory) if fda_advisory else default_fda

                faers_top = [r["reaction"] for r in (faers_data.get("top_reactions", []) if faers_data else [])]

                # Severity Conflict Resolution (Hierarchy Override)
                assigned_severity = resolve_severity_override(
                    base_severity=raw_severity,
                    fda_text=clean_fda,
                    faers_reactions=faers_top,
                    description=primary_contraindication,
                    d1_clean=c1,
                    d2_clean=c2
                )

                # Actionable Clinical Guidance
                if local_match and local_match.get("clinical_action") and raw_severity == assigned_severity:
                    action = local_match["clinical_action"]
                else:
                    action = synthesize_clinical_action(c1, c2, severity=assigned_severity)

                is_safe_flag = assigned_severity not in ["CONTRAINDICATED", "CRITICAL", "MAJOR"]

                # Build fast RxNav lookup map for candidate drugs
                rx_meta_map = {}
                for m in rx_meta_list:
                    if isinstance(m, dict):
                        d_name = clean_drug_name(m.get("drug", ""))
                        if d_name:
                            rx_meta_map[d_name] = m

                # Extract Clinical Alternative and Risk Factor dynamically for emergency alert hot-swap
                # 1. First check curated high-priority clinical rules
                rec_alt = None
                risk_factor = None
                culprit_clean = None
                victim_clean = None

                if local_match:
                    rec_alt = local_match.get("recommended_alternative")
                    risk_factor = local_match.get("risk_factor")
                    culprit_clean = local_match.get("culprit_drug")

                # 2. If not specified in local rule, run dynamic taxonomy & pharmacologic class inference
                if not rec_alt or not risk_factor:
                    dyn_culprit, dyn_victim, dyn_alt, dyn_risk = resolve_dynamic_alternative(
                        c1, c2,
                        evidence_text=f"{primary_contraindication} {clean_fda}",
                        rx_meta_map=rx_meta_map
                    )
                    rec_alt = rec_alt or dyn_alt
                    risk_factor = risk_factor or dyn_risk
                    culprit_disp = culprit_clean.capitalize() if culprit_clean else dyn_culprit
                    victim_disp = dyn_victim if dyn_culprit != dyn_victim else (c2.capitalize() if culprit_disp == c1.capitalize() else c1.capitalize())
                else:
                    culprit_disp = culprit_clean.capitalize() if culprit_clean else c1.capitalize()
                    victim_disp = c2.capitalize() if culprit_disp.lower() == c1.lower() else c1.capitalize()

                # Drug A is the culprit to replace, Drug B is the victim/interacting partner
                drug_a_disp = culprit_disp
                drug_b_disp = victim_disp

                emergency_voice_alert = (
                    f"Clinical Safety Alert: Severe interaction detected. {drug_a_disp} significantly impairs {drug_b_disp} safety and clearance, "
                    f"multiplying {risk_factor}. Consider switching {drug_a_disp} to {rec_alt}."
                )

                record = {
                    "interaction_level": assigned_severity.upper(),
                    "pair": pair_display,
                    "drug_a": drug_a_disp,
                    "drug_b": drug_b_disp,
                    "recommended_alternative": rec_alt,
                    "risk_factor": risk_factor,
                    "emergency_voice_alert": emergency_voice_alert,
                    "primary_contraindication": primary_contraindication,
                    "fda_label_advisory": clean_fda,
                    "faers_surveillance": faers_data or {
                        "total_cases": 0,
                        "top_reactions": []
                    },
                    "clinical_action": action,
                    # Backward compatibility fields for UI and test suites
                    "drug1": d1,
                    "drug2": d2,
                    "severity": assigned_severity.upper(),
                    "description": primary_contraindication,
                    "fda_advisory": clean_fda,
                    "clinical_mechanism": primary_contraindication,
                    "clinical_guidance": action,
                    "faers": {
                        "co_admin_reports": faers_data["total_cases"] if faers_data else 0,
                        "top_adverse_reactions": faers_top
                    } if faers_data else None,
                    "safe_to_prescribe": is_safe_flag
                }

                consolidated_pairs[canonical_key] = record

    interactions = list(consolidated_pairs.values())
    interactions.sort(key=lambda x: SEVERITY_RANKS.get(x["interaction_level"].upper(), 1), reverse=True)

    highest_sev = interactions[0]["interaction_level"].upper() if interactions else "NONE"
    is_safe = highest_sev not in ["CONTRAINDICATED", "CRITICAL", "MAJOR"]

    return {
        "total_pairs_evaluated": total_pairs,
        "flagged_interactions_count": len(interactions),
        "highest_severity": highest_sev,
        "status": "Interaction Found" if interactions else "Safe",
        "severity": highest_sev.capitalize() if highest_sev != "NONE" else "None",
        "summary": f"Identified {len(interactions)} verified clinical interaction pair(s) across {total_pairs} combination(s) evaluated." if interactions else "No severe pharmacological contraindications detected across our 191,000+ clinical interaction database and NLM RxClass.",
        "safe_to_prescribe": is_safe,
        "interactions": interactions,
        "rxNormMetadata": rx_meta_list
    }
