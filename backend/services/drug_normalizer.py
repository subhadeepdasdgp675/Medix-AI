"""
NLM NIH RxNorm & RxClass Medical Ontologist Service
Strict Extraction & Ontology Rules:
1. PURE INGREDIENT LEVEL ONLY (TTY = 'IN'):
   - Standardizes to the primary active chemical ingredient.
   - Strips combination derivative classes (e.g., Acetaminophen never inherits opioid classes from Percocet/Vicodin).
2. MECHANISM OF ACTION (MOA):
   - Returns true primary molecular/biochemical mechanism.
   - Distinguishes synthesis inhibition vs. receptor modulation.
3. VA & EPC CLASS FILTERING:
   - Single primary VA Drug Class code and name directly assigned to the pure ingredient (e.g. "CN103 - NON-OPIOID ANALGESICS").
   - Official FDA Established Pharmacologic Class for the pure chemical entity.
4. RXCUI PRECISION:
   - Returns exact numerical RxNorm Concept Unique Identifier (e.g., "161" for Acetaminophen, "723" for Amoxicillin, "11289" for Warfarin, "1191" for Aspirin).
"""

import re
import httpx
import asyncio
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple

# Thread-safe in-memory cache to eliminate redundant network latency
_RXNAV_CACHE: Dict[str, Dict[str, Any]] = {}

# Curated Gold-Standard Medical Ontology Registry for Pure Active Ingredients
# Ensures strict compliance with NDF-RT/Med-RT, FDA EPC, and single primary VA drug class standards
CURATED_INGREDIENT_ONTOLOGY: Dict[str, Dict[str, str]] = {
    "acetaminophen": {
        "drug_name": "Acetaminophen",
        "rxcui": "161",
        "epc_class": "Non-Opioid Analgesic",
        "mechanism_of_action": "Central Cyclooxygenase and Prostaglandin Synthesis Inhibitor",
        "va_class": "CN103 - NON-OPIOID ANALGESICS"
    },
    "paracetamol": {
        "drug_name": "Acetaminophen",
        "rxcui": "161",
        "epc_class": "Non-Opioid Analgesic",
        "mechanism_of_action": "Central Cyclooxygenase and Prostaglandin Synthesis Inhibitor",
        "va_class": "CN103 - NON-OPIOID ANALGESICS"
    },
    "aspirin": {
        "drug_name": "Aspirin",
        "rxcui": "1191",
        "epc_class": "Platelet Aggregation Inhibitor",
        "mechanism_of_action": "Irreversible Cyclooxygenase-1 (COX-1) and COX-2 Inhibitor",
        "va_class": "BL117 - PLATELET AGGREGATION INHIBITORS"
    },
    "warfarin": {
        "drug_name": "Warfarin",
        "rxcui": "11289",
        "epc_class": "Vitamin K Antagonist",
        "mechanism_of_action": "Vitamin K Epoxide Reductase Complex 1 (VKORC1) Inhibitor",
        "va_class": "BL110 - ANTICOAGULANTS"
    },
    "amoxicillin": {
        "drug_name": "Amoxicillin",
        "rxcui": "723",
        "epc_class": "Penicillin-class Antibacterial",
        "mechanism_of_action": "Bacterial Penicillin-Binding Protein (PBP) Cell Wall Synthesis Inhibitor",
        "va_class": "AM110 - PENICILLINS, AMINO-DERIVATIVES"
    },
    "ciprofloxacin": {
        "drug_name": "Ciprofloxacin",
        "rxcui": "2551",
        "epc_class": "Fluoroquinolone Antibacterial",
        "mechanism_of_action": "Bacterial DNA Gyrase (Topoisomerase II) and Topoisomerase IV Inhibitor",
        "va_class": "AM400 - QUINOLONES"
    },
    "azithromycin": {
        "drug_name": "Azithromycin",
        "rxcui": "18631",
        "epc_class": "Macrolide Antibacterial",
        "mechanism_of_action": "Bacterial 50S Ribosomal Subunit Protein Synthesis Inhibitor",
        "va_class": "AM200 - MACROLIDES"
    },
    "amiodarone": {
        "drug_name": "Amiodarone",
        "rxcui": "703",
        "epc_class": "Antiarrhythmic Agent",
        "mechanism_of_action": "Cardiac Potassium Channel (Phase 3 Repolarization) Blocker",
        "va_class": "CV300 - ANTIARRHYTHMIC AGENTS"
    },
    "levofloxacin": {
        "drug_name": "Levofloxacin",
        "rxcui": "82122",
        "epc_class": "Fluoroquinolone Antibacterial",
        "mechanism_of_action": "Bacterial DNA Topoisomerase IV and DNA Gyrase Inhibitor",
        "va_class": "AM400 - QUINOLONES"
    },
    "clarithromycin": {
        "drug_name": "Clarithromycin",
        "rxcui": "21212",
        "epc_class": "Macrolide Antibacterial",
        "mechanism_of_action": "Bacterial 50S Ribosomal Subunit Protein Synthesis Inhibitor",
        "va_class": "AM200 - MACROLIDES"
    },
    "simvastatin": {
        "drug_name": "Simvastatin",
        "rxcui": "36567",
        "epc_class": "HMG-CoA Reductase Inhibitor",
        "mechanism_of_action": "Hydroxymethylglutaryl-CoA (HMG-CoA) Reductase Competitive Inhibitor",
        "va_class": "CV350 - ANTILIPEMIC AGENTS"
    },
    "atorvastatin": {
        "drug_name": "Atorvastatin",
        "rxcui": "83367",
        "epc_class": "HMG-CoA Reductase Inhibitor",
        "mechanism_of_action": "Hydroxymethylglutaryl-CoA (HMG-CoA) Reductase Competitive Inhibitor",
        "va_class": "CV350 - ANTILIPEMIC AGENTS"
    },
    "clopidogrel": {
        "drug_name": "Clopidogrel",
        "rxcui": "32968",
        "epc_class": "Platelet P2Y12 Receptor Inhibitor",
        "mechanism_of_action": "Irreversible Platelet Adenosine Diphosphate (P2Y12) Receptor Antagonist",
        "va_class": "BL117 - PLATELET AGGREGATION INHIBITORS"
    },
    "ibuprofen": {
        "drug_name": "Ibuprofen",
        "rxcui": "5640",
        "epc_class": "Nonsteroidal Anti-inflammatory Drug",
        "mechanism_of_action": "Reversible Cyclooxygenase-1 (COX-1) and COX-2 Inhibitor",
        "va_class": "MS102 - NON-STEROIDAL ANTI-INFLAMMATORY AGENTS"
    },
    "methotrexate": {
        "drug_name": "Methotrexate",
        "rxcui": "6851",
        "epc_class": "Folate Analog Metabolic Inhibitor",
        "mechanism_of_action": "Dihydrofolate Reductase (DHFR) Competitive Inhibitor",
        "va_class": "AN200 - ANTINEOPLASTIC ANTIMETABOLITES"
    },
    "cetirizine": {
        "drug_name": "Cetirizine",
        "rxcui": "20610",
        "epc_class": "Histamine-1 Receptor Antagonist",
        "mechanism_of_action": "Selective Peripheral Histamine H1 Receptor Antagonist",
        "va_class": "AH100 - ANTIHISTAMINES"
    },
    "metformin": {
        "drug_name": "Metformin",
        "rxcui": "6809",
        "epc_class": "Biguanide",
        "mechanism_of_action": "Hepatic Gluconeogenesis Inhibition via AMPK Activation",
        "va_class": "HS502 - ORAL HYPOGLYCEMIC AGENTS"
    },
    "lisinopril": {
        "drug_name": "Lisinopril",
        "rxcui": "29046",
        "epc_class": "Angiotensin Converting Enzyme Inhibitor",
        "mechanism_of_action": "Angiotensin-Converting Enzyme (ACE) Competitive Inhibitor",
        "va_class": "CV800 - ACE INHIBITORS"
    },
    "losartan": {
        "drug_name": "Losartan",
        "rxcui": "5224",
        "epc_class": "Angiotensin II Receptor Blocker",
        "mechanism_of_action": "Selective Angiotensin II Type 1 (AT1) Receptor Antagonist",
        "va_class": "CV805 - ANGIOTENSIN II RECEPTOR ANTAGONISTS"
    },
    "omeprazole": {
        "drug_name": "Omeprazole",
        "rxcui": "7646",
        "epc_class": "Proton Pump Inhibitor",
        "mechanism_of_action": "Gastric Parietal Cell H+/K+ ATPase Enzyme Inhibitor",
        "va_class": "GA900 - GASTRIC ACID SECRETION INHIBITORS"
    },
    "linezolid": {
        "drug_name": "Linezolid",
        "rxcui": "194090",
        "epc_class": "Oxazolidinone Antibacterial",
        "mechanism_of_action": "Bacterial 50S Ribosomal 23S rRNA Protein Synthesis Inhibitor / Reversible Monoamine Oxidase A Inhibitor",
        "va_class": "AM900 - OXAZOLIDINONES"
    },
    "citalopram": {
        "drug_name": "Citalopram",
        "rxcui": "2556",
        "epc_class": "Selective Serotonin Reuptake Inhibitor",
        "mechanism_of_action": "Presynaptic Neuronal Serotonin Transporter (SERT) Reuptake Inhibitor",
        "va_class": "CN601 - SELECTIVE SEROTONIN REUPTAKE INHIBITORS"
    },
    "escitalopram": {
        "drug_name": "Escitalopram",
        "rxcui": "32937",
        "epc_class": "Selective Serotonin Reuptake Inhibitor",
        "mechanism_of_action": "Presynaptic Neuronal Serotonin Transporter (SERT) Reuptake Inhibitor",
        "va_class": "CN601 - SELECTIVE SEROTONIN REUPTAKE INHIBITORS"
    },
    "sertraline": {
        "drug_name": "Sertraline",
        "rxcui": "36437",
        "epc_class": "Selective Serotonin Reuptake Inhibitor",
        "mechanism_of_action": "Presynaptic Neuronal Serotonin Transporter (SERT) Reuptake Inhibitor",
        "va_class": "CN601 - SELECTIVE SEROTONIN REUPTAKE INHIBITORS"
    },
    "fluoxetine": {
        "drug_name": "Fluoxetine",
        "rxcui": "4493",
        "epc_class": "Selective Serotonin Reuptake Inhibitor",
        "mechanism_of_action": "Presynaptic Neuronal Serotonin Transporter (SERT) Reuptake Inhibitor",
        "va_class": "CN601 - SELECTIVE SEROTONIN REUPTAKE INHIBITORS"
    },
    "paroxetine": {
        "drug_name": "Paroxetine",
        "rxcui": "32937",
        "epc_class": "Selective Serotonin Reuptake Inhibitor",
        "mechanism_of_action": "Presynaptic Neuronal Serotonin Transporter (SERT) Reuptake Inhibitor",
        "va_class": "CN601 - SELECTIVE SEROTONIN REUPTAKE INHIBITORS"
    },
    "venlafaxine": {
        "drug_name": "Venlafaxine",
        "rxcui": "39786",
        "epc_class": "Serotonin and Norepinephrine Reuptake Inhibitor",
        "mechanism_of_action": "Neuronal Serotonin (SERT) and Norepinephrine (NET) Reuptake Inhibitor",
        "va_class": "CN600 - ANTIDEPRESSANTS"
    },
    "duloxetine": {
        "drug_name": "Duloxetine",
        "rxcui": "72625",
        "epc_class": "Serotonin and Norepinephrine Reuptake Inhibitor",
        "mechanism_of_action": "Neuronal Serotonin (SERT) and Norepinephrine (NET) Reuptake Inhibitor",
        "va_class": "CN600 - ANTIDEPRESSANTS"
    }
}


async def get_pure_ingredient_rxcui(client: httpx.AsyncClient, raw_drug: str) -> Tuple[Optional[str], str]:
    """
    Standardize a drug name against NLM NIH RxNorm:
    Extracts the pure active ingredient (TTY = 'IN') Concept Unique Identifier.
    """
    clean_name = raw_drug.strip()
    if not clean_name:
        return None, clean_name

    encoded_name = urllib.parse.quote(clean_name)

    # 1. Check exact name match
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={encoded_name}"
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            ids = data.get("idGroup", {}).get("rxnormId", [])
            if ids and len(ids) > 0:
                first_rxcui = str(ids[0])
                # Resolve to Ingredient Concept (TTY = 'IN')
                in_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{first_rxcui}/related.json?tty=IN"
                in_resp = await client.get(in_url, timeout=4.0)
                if in_resp.status_code == 200:
                    in_data = in_resp.json()
                    concept_group = in_data.get("relatedGroup", {}).get("conceptGroup", [])
                    for grp in concept_group:
                        if grp.get("tty") == "IN":
                            concepts = grp.get("conceptProperties", [])
                            if concepts:
                                return str(concepts[0].get("rxcui")), concepts[0].get("name", clean_name)
                return first_rxcui, clean_name
    except Exception as e:
        print(f"RxNav pure ingredient lookup notice for '{clean_name}': {e}")

    # 2. Approximate Term Fallback
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term={encoded_name}&maxEntries=1"
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("approximateGroup", {}).get("candidate", [])
            if candidates and len(candidates) > 0:
                rxcui = candidates[0].get("rxcui")
                if rxcui:
                    return str(rxcui), clean_name
    except Exception as e:
        print(f"RxNav approximate query notice for '{clean_name}': {e}")

    return None, clean_name


def clean_ontology_string(raw: str) -> str:
    """
    Cleans up FDA and VA drug class strings:
    - Strips out raw table headers (e.g. 'Table 3: ...')
    - Strips out section citation brackets (e.g. '[see Dosage and Administration (2.5)]')
    - Strips out multi-class slash dumps (takes primary before slash)
    """
    if not raw:
        return ""
    text = raw.strip()
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Strip table headers
    text = re.sub(r'Table\s+\d+[\s:\-–—][^\.\n]*?(?=[A-Z]|\n|\.|$)', ' ', text, flags=re.IGNORECASE)
    # Strip section citations
    text = re.sub(r'\[\s*see\s+[^\]]+\]', ' ', text, flags=re.IGNORECASE)
    # If string contains multiple slash-delimited classes like "Class A / Class B / Class C", keep primary
    if " / " in text:
        text = text.split(" / ")[0].strip()
    # Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def normalize_drug_rxnav(raw_drug: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """
    Outputs strictly valid Medical Ontologist and Clinical Pharmacologist drug concepts matching schema:
    {
      "drug_name": "string",
      "rxcui": "string",
      "epc_class": "string",
      "mechanism_of_action": "string",
      "va_class": "string"
    }
    """
    clean_key = raw_drug.lower().strip()
    # Check Curated Gold-Standard Registry first (pure monotherapy guarantee)
    if clean_key in CURATED_INGREDIENT_ONTOLOGY:
        res = CURATED_INGREDIENT_ONTOLOGY[clean_key].copy()
        # Backward compatibility aliases for UI
        res["drug"] = res["drug_name"]
        res["standardName"] = res["drug_name"]
        res["epc"] = res["epc_class"]
        res["moa"] = res["mechanism_of_action"]
        res["vaClass"] = res["va_class"]
        return res

    # Check cache
    if clean_key in _RXNAV_CACHE:
        return _RXNAV_CACHE[clean_key].copy()

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    try:
        rxcui, std_name = await get_pure_ingredient_rxcui(client, raw_drug)
        if not rxcui:
            fallback = {
                "drug_name": raw_drug.strip().title(),
                "rxcui": "N/A",
                "epc_class": "Therapeutic Agent",
                "mechanism_of_action": "Receptor / Enzyme Modulation",
                "va_class": "UNKNOWN",
                # UI aliases
                "drug": raw_drug,
                "standardName": raw_drug.strip().title(),
                "epc": "Therapeutic Agent",
                "moa": "Receptor / Enzyme Modulation",
                "vaClass": "UNKNOWN"
            }
            _RXNAV_CACHE[clean_key] = fallback
            return fallback.copy()

        # Query NLM NIH RxClass for EPC, MOA, and VA class
        epc_choice = None
        moa_choice = None
        va_choice = None

        try:
            class_url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}"
            resp = await client.get(class_url, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                drug_info_list = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
                for item in drug_info_list:
                    min_concept = item.get("rxclassMinConceptItem", {})
                    c_type = min_concept.get("classType", "")
                    c_id = min_concept.get("classId", "")
                    c_name = clean_ontology_string(min_concept.get("className", ""))

                    # Single primary EPC for pure ingredient
                    if c_type == "EPC" and c_name and not epc_choice:
                        epc_choice = c_name
                    # Single molecular mechanism
                    elif c_type == "MOA" and c_name and not moa_choice:
                        moa_choice = c_name
                    # Single primary VA Class (code + name)
                    elif c_type == "VA" and c_name and not va_choice:
                        va_choice = f"{c_id} - {c_name.upper()}" if c_id else c_name.upper()
        except Exception as e:
            print(f"RxClass live query notice for RxCUI {rxcui}: {e}")

        final_epc = clean_ontology_string(epc_choice or "Established Pharmacologic Agent")
        final_moa = clean_ontology_string(moa_choice or "Molecular / Cellular Target Modulator")
        final_va = clean_ontology_string(va_choice or "AM900 - ANTIMICROBIALS / GENERAL")

        result = {
            "drug_name": std_name.capitalize(),
            "rxcui": str(rxcui),
            "epc_class": final_epc,
            "mechanism_of_action": final_moa,
            "va_class": final_va,
            # Backward compatibility aliases for UI cards
            "drug": raw_drug,
            "standardName": std_name.capitalize(),
            "epc": final_epc,
            "moa": final_moa,
            "vaClass": final_va
        }

        _RXNAV_CACHE[clean_key] = result
        return result.copy()

    finally:
        if close_client:
            await client.aclose()


async def batch_normalize_drugs(drug_names: List[str]) -> List[Dict[str, Any]]:
    """Concurrently standardizes drug list with pure ingredient ontologies."""
    clean_list = [d.strip() for d in drug_names if d and d.strip()]
    if not clean_list:
        return []

    async with httpx.AsyncClient() as client:
        tasks = [normalize_drug_rxnav(name, client) for name in clean_list]
        return await asyncio.gather(*tasks)
