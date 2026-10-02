"""
Drug Normalization & Clinical Interaction Engine
Provides:
- Robust drug name cleaning (dosages, salt removal, lowercase)
- Brand-to-generic mapping (e.g. Augmentin -> Amoxicillin, Cipro -> Ciprofloxacin)
- Fuzzy matching against known drug registry
- Bidirectional lookup via sorted tuples
- High-priority clinical interaction rules (e.g. Ciprofloxacin + Warfarin, Azithromycin + Amiodarone)
"""

import re
import difflib
from typing import Dict, Tuple, Optional, Set, List, Any

# Common brand names to generic names
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
}

# Common salt variations and formulation suffixes
SALT_AND_FORM_TOKENS = {
    "sodium", "potassium", "calcium", "hydrochloride", "hcl", "dihydrochloride",
    "sulfate", "sulphate", "phosphate", "tartrate", "succinate", "maleate",
    "mesylate", "besylate", "fumarate", "acetate", "gluconate", "citrate",
    "lactate", "bromide", "iodide", "nitrate", "propionate", "valerate",
    "dipropionate", "monohydrate", "dihydrate", "trihydrate", "er", "xr",
    "xl", "cr", "sr", "dr", "ir", "oral", "tablet", "tablets", "capsule",
    "capsules", "injection", "solution", "suspension", "syrup", "cream", "ointment"
}

# Dosage regex pattern (e.g., 500mg, 500 mg, 0.5g, 10ml, 5%, 250mcg, 10meq, 100iu)
DOSAGE_REGEX = re.compile(
    r'\b\d+(\.\d+)?\s*(mg|mcg|ug|g|ml|l|iu|meq|%|mmol)\b',
    re.IGNORECASE
)

# High-priority clinical interaction rules for guaranteed accuracy
# Each entry: tuple(sorted([generic1, generic2])): { "severity": "...", "description": "...", "effect": "..." }
CLINICAL_RULES: Dict[Tuple[str, str], Dict[str, str]] = {
    tuple(sorted(["ciprofloxacin", "warfarin"])): {
        "severity": "Major",
        "description": "Ciprofloxacin potently inhibits CYP1A2 and alters gut flora, significantly decreasing warfarin metabolism and displacing it from protein binding sites. This induces severe hypoprothrombinemia, dangerously elevating INR and causing life-threatening hemorrhage.",
        "effect": "Severe risk of bleeding, hematuria, gastrointestinal hemorrhage, and elevated INR."
    },
    tuple(sorted(["levofloxacin", "warfarin"])): {
        "severity": "Major",
        "description": "Levofloxacin enhances the anticoagulant effect of Warfarin by reducing gut synthesis of Vitamin K and metabolic competition, significantly elevating INR and major bleeding risk.",
        "effect": "Marked prolongation of prothrombin time (INR) and heightened bleeding risk."
    },
    tuple(sorted(["amiodarone", "azithromycin"])): {
        "severity": "Major",
        "description": "Concurrent use of Amiodarone and Azithromycin produces additive electrophysiological delays in cardiac ventricular repolarization, causing severe QTc interval prolongation, Torsades de Pointes, and fatal ventricular arrhythmias.",
        "effect": "Severe QTc prolongation, Torsades de Pointes, and cardiac arrest."
    },
    tuple(sorted(["amiodarone", "ciprofloxacin"])): {
        "severity": "Major",
        "description": "Combining Amiodarone with Ciprofloxacin produces additive prolongation of the QTc interval, precipitating potentially fatal ventricular tachyarrhythmias and Torsades de Pointes.",
        "effect": "Additive QTc prolongation and high risk of ventricular arrhythmia."
    },
    tuple(sorted(["amiodarone", "levofloxacin"])): {
        "severity": "Major",
        "description": "Levofloxacin combined with Amiodarone synergistically prolongs cardiac repolarization (QT interval), dramatically increasing risk of Torsades de Pointes and sudden cardiac death.",
        "effect": "Severe QTc prolongation and ventricular arrhythmia."
    },
    tuple(sorted(["clarithromycin", "simvastatin"])): {
        "severity": "Major",
        "description": "Clarithromycin is a potent CYP3A4 inhibitor that markedly elevates serum concentrations of Simvastatin, drastically increasing the risk of severe myopathy and life-threatening rhabdomyolysis.",
        "effect": "Rhabdomyolysis, severe muscle breakdown, and acute renal failure."
    },
    tuple(sorted(["methotrexate", "amoxicillin"])): {
        "severity": "Major",
        "description": "Penicillins such as Amoxicillin compete for renal tubular secretion with Methotrexate, leading to elevated serum methotrexate levels and severe bone marrow suppression, nephrotoxicity, and gastrointestinal toxicity.",
        "effect": "Methotrexate toxicity, severe neutropenia, thrombocytopenia, and renal impairment."
    },
    tuple(sorted(["warfarin", "aspirin"])): {
        "severity": "Major",
        "description": "Aspirin irreversibly inhibits platelet aggregation and causes gastric mucosal injury, which synergistically combines with warfarin anticoagulation to dramatically increase major GI bleeding and intracranial hemorrhage risk.",
        "effect": "Severe gastrointestinal bleeding and hemorrhagic stroke."
    }
}


def clean_drug_name(raw: str) -> str:
    """
    Cleans and standardizes a drug name:
    1. Lowercase & strip whitespace
    2. Strip dosages (e.g. 500mg, 10 ml)
    3. Strip common salt variations and formulation suffixes
    4. Map brand name aliases to generic names
    5. Clean remaining punctuation
    """
    if not raw or not isinstance(raw, str):
        return ""

    text = raw.lower().strip()

    # 1. Remove parenthetical remarks (e.g. "Cipro (oral)")
    text = re.sub(r'\(.*?\)', ' ', text)

    # 2. Remove dosages like 500mg, 250 mg, 0.5g, 10ml, etc.
    text = DOSAGE_REGEX.sub(' ', text)

    # 3. Remove punctuation except dashes
    text = re.sub(r'[^\w\s-]', ' ', text)

    # 4. Tokenize
    tokens = text.split()
    if not tokens:
        return ""

    # Check if full text matches brand name
    joined = " ".join(tokens)
    if joined in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[joined]
    if tokens[0] in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[tokens[0]]

    # 5. Filter out salt and formulation tokens
    filtered = [t for t in tokens if t not in SALT_AND_FORM_TOKENS and not t.isdigit()]

    if not filtered:
        filtered = [t for t in tokens if not t.isdigit()]
        if not filtered:
            filtered = tokens

    candidate = " ".join(filtered)

    # Check again if filtered matches brand map
    if candidate in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[candidate]
    if filtered[0] in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[filtered[0]]

    return candidate


def match_to_known_drugs(cleaned_drug: str, known_drugs: Set[str], cutoff: float = 0.8) -> str:
    """
    Matches a cleaned drug name to known drug names in the dataset:
    - Exact match
    - Substring / word prefix match
    - Close match using difflib
    """
    if not cleaned_drug:
        return cleaned_drug

    if cleaned_drug in known_drugs:
        return cleaned_drug

    # Check if any known drug is an exact single word contained in cleaned_drug
    words = cleaned_drug.split()
    for w in words:
        if w in known_drugs:
            return w

    # Check if cleaned_drug is a prefix of a known drug or vice-versa
    prefix_matches = [kd for kd in known_drugs if kd.startswith(cleaned_drug) or cleaned_drug.startswith(kd)]
    if prefix_matches:
        prefix_matches.sort(key=len)
        return prefix_matches[0]

    # Fuzzy match with difflib
    matches = difflib.get_close_matches(cleaned_drug, known_drugs, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    return cleaned_drug


class InteractionEngine:
    def __init__(self):
        # Key: tuple(sorted([clean_drug_1, clean_drug_2])): str (description)
        self.interactions: Dict[Tuple[str, str], str] = {}
        # Set of all known clean drug names
        self.known_drugs: Set[str] = set()
        self.loaded_count = 0

    def load_from_csv(self, csv_path: str):
        """
        Loads interactions from CSV and indexes bidirectional sorted tuples.
        """
        import pandas as pd
        import os

        if not os.path.exists(csv_path):
            print(f"Warning: CSV file not found at {csv_path}")
            return

        print(f"Loading drug interactions database from {csv_path}...")
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
            # Keep first or longest description
            if key not in self.interactions or len(desc_str) > len(self.interactions[key]):
                self.interactions[key] = desc_str
                count += 1

        self.loaded_count = count
        print(f"InteractionEngine: Successfully indexed {count} unique pairs across {len(self.known_drugs)} unique drugs.")

    def resolve_drug(self, raw_drug: str) -> str:
        """
        Cleans and resolves raw drug string to canonical dataset drug name.
        """
        cleaned = clean_drug_name(raw_drug)
        if self.known_drugs:
            resolved = match_to_known_drugs(cleaned, self.known_drugs)
            return resolved
        return cleaned

    def check_pair(self, drug_a: str, drug_b: str) -> Optional[Dict[str, Any]]:
        """
        Checks interaction between two drugs (raw or cleaned).
        Returns dict with keys: severity, description, effect, safe_to_prescribe
        or None if no interaction is detected.
        """
        da_clean = self.resolve_drug(drug_a)
        db_clean = self.resolve_drug(drug_b)

        if not da_clean or not db_clean or da_clean == db_clean:
            return None

        # 1. Check high-priority clinical rules first
        rule_key = tuple(sorted([da_clean, db_clean]))
        if rule_key in CLINICAL_RULES:
            rule = CLINICAL_RULES[rule_key]
            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": da_clean,
                "resolvedDrug2": db_clean,
                "severity": rule["severity"],
                "description": f"[High-Risk Clinical Protocol] {rule['description']}",
                "effect": rule.get("effect", rule['description']),
                "safe_to_prescribe": False if rule["severity"] in ["Major", "Critical"] else True,
                "source": "Clinical Guidelines"
            }

        # Also check with initial clean names before fuzzy resolution
        raw_c1 = clean_drug_name(drug_a)
        raw_c2 = clean_drug_name(drug_b)
        raw_rule_key = tuple(sorted([raw_c1, raw_c2]))
        if raw_rule_key in CLINICAL_RULES:
            rule = CLINICAL_RULES[raw_rule_key]
            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": raw_c1,
                "resolvedDrug2": raw_c2,
                "severity": rule["severity"],
                "description": f"[High-Risk Clinical Protocol] {rule['description']}",
                "effect": rule.get("effect", rule['description']),
                "safe_to_prescribe": False if rule["severity"] in ["Major", "Critical"] else True,
                "source": "Clinical Guidelines"
            }

        # 2. Check canonical CSV interaction dictionary
        int_key = tuple(sorted([da_clean, db_clean]))
        if int_key in self.interactions:
            desc = self.interactions[int_key]
            desc_lower = desc.lower()

            major_markers = [
                'fatal', 'death', 'cardiac', 'arrhythmia', 'qtc', 'qt prolongation',
                'torsades', 'bleeding', 'hemorrhage', 'toxicity', 'severe',
                'rhabdomyolysis', 'serotonin syndrome', 'apnea', 'respiratory depression'
            ]
            severity = "Major" if any(m in desc_lower for m in major_markers) else "Moderate"

            effect = desc
            if "may increase the" in desc:
                effect = desc.split("may increase the", 1)[1].strip().capitalize()
            elif "may decrease the" in desc:
                effect = desc.split("may decrease the", 1)[1].strip().capitalize()

            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": da_clean,
                "resolvedDrug2": db_clean,
                "severity": severity,
                "description": f"[Clinical Interaction Registry] {desc}",
                "effect": effect,
                "safe_to_prescribe": False if severity == "Major" else True,
                "source": "Clinical Registry"
            }

        # Check raw clean pair in CSV interaction dictionary
        if raw_rule_key in self.interactions:
            desc = self.interactions[raw_rule_key]
            desc_lower = desc.lower()
            major_markers = [
                'fatal', 'death', 'cardiac', 'arrhythmia', 'qtc', 'qt prolongation',
                'torsades', 'bleeding', 'hemorrhage', 'toxicity', 'severe',
                'rhabdomyolysis', 'serotonin syndrome', 'apnea', 'respiratory depression'
            ]
            severity = "Major" if any(m in desc_lower for m in major_markers) else "Moderate"
            return {
                "drug1": drug_a,
                "drug2": drug_b,
                "resolvedDrug1": raw_c1,
                "resolvedDrug2": raw_c2,
                "severity": severity,
                "description": f"[Clinical Interaction Registry] {desc}",
                "effect": desc,
                "safe_to_prescribe": False if severity == "Major" else True,
                "source": "Clinical Registry"
            }

        return None
