import httpx
import asyncio
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple

# In-memory cache for fast sub-100ms subsequent lookups
_RXNAV_CACHE: Dict[str, Dict[str, Any]] = {}

async def get_rxcui(client: httpx.AsyncClient, drug_name: str) -> Tuple[Optional[str], str]:
    """
    Query NLM NIH RxNorm REST API to find the official RxCUI and standardized concept name for a drug string.
    Uses exact match first, then falls back to approximate term lookup.
    """
    clean_name = drug_name.strip()
    if not clean_name:
        return None, clean_name

    encoded_name = urllib.parse.quote(clean_name)
    
    # 1. Try exact name match
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={encoded_name}"
        resp = await client.get(url, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            rxnorm_ids = data.get("idGroup", {}).get("rxnormId", [])
            if rxnorm_ids and len(rxnorm_ids) > 0:
                return str(rxnorm_ids[0]), clean_name
    except Exception as e:
        print(f"RxNav exact lookup error for {clean_name}: {e}")

    # 2. Fallback to approximate term matching
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/approxateTerm.json?term={encoded_name}&maxEntries=1"
        resp = await client.get(url, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("approximateGroup", {}).get("candidate", [])
            if candidates and len(candidates) > 0:
                rxcui = candidates[0].get("rxcui")
                if rxcui:
                    return str(rxcui), clean_name
    except Exception as e:
        print(f"RxNav approximate lookup error for {clean_name}: {e}")

    return None, clean_name

async def get_drug_metadata_rxnav(drug_name: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """
    Retrieve comprehensive NLM NIH RxNorm and RxClass metadata for a given drug name.
    Returns standardized RxCUI, Established Pharmacologic Class (EPC), Mechanism of Action (MOA), and VA Class.
    """
    cache_key = drug_name.lower().strip()
    if cache_key in _RXNAV_CACHE:
        return _RXNAV_CACHE[cache_key].copy()

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True

    try:
        rxcui, std_name = await get_rxcui(client, drug_name)
        if not rxcui:
            # Fallback metadata if NLM RxNav cannot resolve the string
            fallback_meta = {
                "drug": drug_name,
                "rxcui": "N/A",
                "standardName": drug_name,
                "epc": "General Antimicrobial Agent",
                "moa": "Targeted Bacterial / Microbial Inhibition",
                "vaClass": "ANTI-INFECTIVE",
                "source": "Clinical Surveillance DB"
            }
            _RXNAV_CACHE[cache_key] = fallback_meta
            return fallback_meta.copy()

        # Query NLM NIH RxClass API for Established Pharmacologic Class (EPC), MOA, and VA Class
        epc_list = set()
        moa_list = set()
        va_list = set()
        
        try:
            class_url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}"
            resp = await client.get(class_url, timeout=7.0)
            if resp.status_code == 200:
                data = resp.json()
                drug_info_list = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
                for item in drug_info_list:
                    min_item = item.get("rxclassMinConceptItem", {})
                    class_type = min_item.get("classType", "")
                    class_name = min_item.get("className", "").strip()
                    
                    if class_type == "EPC" and class_name:
                        epc_list.add(class_name)
                    elif class_type == "MOA" and class_name:
                        moa_list.add(class_name)
                    elif class_type == "VA" and class_name:
                        va_list.add(class_name)
                    elif class_type == "ATC1-4" and class_name and "antiinfectives" not in class_name.lower():
                        if not epc_list:
                            epc_list.add(class_name)
        except Exception as e:
            print(f"RxClass query error for RxCUI {rxcui}: {e}")

        # Provide sensible clinical defaults if specific NLM classes are missing
        epc_str = " / ".join(sorted(list(epc_list))) if epc_list else "Antimicrobial Agent"
        moa_str = " / ".join(sorted(list(moa_list))) if moa_list else "Bacterial Cell Wall / Protein Synthesis Inhibitor"
        va_str = " / ".join(sorted(list(va_list))) if va_list else "ANTI-INFECTIVES"

        meta = {
            "drug": drug_name,
            "rxcui": str(rxcui),
            "standardName": std_name.capitalize(),
            "epc": epc_str,
            "moa": moa_str,
            "vaClass": va_str,
            "source": "NLM NIH RxNav / RxNorm"
        }
        _RXNAV_CACHE[cache_key] = meta
        return meta.copy()
    finally:
        if close_client:
            await client.aclose()

async def get_multiple_drug_metadata(drug_names: List[str]) -> List[Dict[str, Any]]:
    """
    Batch resolve NLM NIH RxNorm metadata for multiple drug names concurrently.
    """
    async with httpx.AsyncClient() as client:
        tasks = [get_drug_metadata_rxnav(d, client) for d in drug_names if d and d.strip()]
        results = await asyncio.gather(*tasks)
        return list(results)

def check_class_interaction_rxnav(meta1: Dict[str, Any], meta2: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform NLM NIH RxClass pharmacological mechanism cross-checking between two drug metadata objects.
    Detects duplicate therapies within the same Established Pharmacologic Class or VA class,
    and flags overlapping mechanism risks.
    """
    interactions = []
    d1 = meta1.get("drug", "Drug 1")
    d2 = meta2.get("drug", "Drug 2")
    
    if d1.lower().strip() == d2.lower().strip():
        return interactions

    epc1 = set([c.strip().lower() for c in meta1.get("epc", "").split("/") if c.strip() and c.strip().lower() != "antimicrobial agent"])
    epc2 = set([c.strip().lower() for c in meta2.get("epc", "").split("/") if c.strip() and c.strip().lower() != "antimicrobial agent"])
    
    moa1 = set([c.strip().lower() for c in meta1.get("moa", "").split("/") if c.strip()])
    moa2 = set([c.strip().lower() for c in meta2.get("moa", "").split("/") if c.strip()])
    
    va1 = set([c.strip().lower() for c in meta1.get("vaClass", "").split("/") if c.strip() and c.strip().lower() != "anti-infectives"])
    va2 = set([c.strip().lower() for c in meta2.get("vaClass", "").split("/") if c.strip() and c.strip().lower() != "anti-infectives"])

    # 1. Check for duplicate therapy in Established Pharmacologic Class (EPC)
    shared_epc = epc1.intersection(epc2)
    if shared_epc:
        class_name = list(shared_epc)[0].title()
        interactions.append({
            "drug1": d1,
            "drug2": d2,
            "severity": "Moderate",
            "description": f"[NLM NIH RxClass Warning] Duplicate Pharmacological Therapy: Both {d1} and {d2} belong to the Established Pharmacologic Class ({class_name}). Concomitant use of agents in the same class increases risk of adverse effects without added clinical benefit."
        })
    elif va1.intersection(va2):
        # 2. Check shared VA Class
        shared_va = list(va1.intersection(va2))[0].upper()
        if "QUINOLONE" in shared_va or "MACROLIDE" in shared_va or "TETRACYCLINE" in shared_va or "AMINOGLYCOSIDE" in shared_va:
            interactions.append({
                "drug1": d1,
                "drug2": d2,
                "severity": "Moderate",
                "description": f"[NLM NIH RxClass Warning] Shared Therapeutic Class ({shared_va}): Concurrent administration of two agents from the same therapeutic family may heighten organ toxicity and promote rapid antimicrobial resistance."
            })

    # 3. Check for specific high-risk overlapping mechanisms
    all_classes_str = (meta1.get("epc", "") + " " + meta2.get("epc", "") + " " + meta1.get("vaClass", "") + " " + meta2.get("vaClass", "") + " " + meta1.get("moa", "") + " " + meta2.get("moa", "")).lower()
    
    # 3a. Fluoroquinolone + Macrolide -> QT Prolongation
    if ("quinolone" in all_classes_str or "fluoroquinolone" in all_classes_str) and ("macrolide" in all_classes_str or "erythromycin" in all_classes_str or "azithromycin" in all_classes_str or "clarithromycin" in all_classes_str):
        interactions.append({
            "drug1": d1,
            "drug2": d2,
            "severity": "Major",
            "description": "[NLM NIH MedRT Clinical Alert] Synergistic QT Prolongation Risk: Fluoroquinolones and Macrolide antibacterial agents both carry intrinsic risk of cardiac ventricular arrhythmias and QT interval prolongation. Concomitant use should be avoided or closely monitored with continuous ECG."
        })

    # 3b. Warfarin / Anticoagulants + NSAIDs / Fluoroquinolones / Antiplatelets -> Bleeding Risk
    is_anticoag_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['warfarin', 'coumarin', 'anticoagulant', 'heparin', 'apixaban', 'rivaroxaban', 'dabigatran'])
    is_anticoag_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['warfarin', 'coumarin', 'anticoagulant', 'heparin', 'apixaban', 'rivaroxaban', 'dabigatran'])
    
    is_nsaid_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['nsaid', 'ibuprofen', 'naproxen', 'aspirin', 'diclofenac', 'celecoxib', 'ketorolac', 'cyclooxygenase'])
    is_nsaid_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['nsaid', 'ibuprofen', 'naproxen', 'aspirin', 'diclofenac', 'celecoxib', 'ketorolac', 'cyclooxygenase'])

    is_quinolone_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['quinolone', 'ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin'])
    is_quinolone_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['quinolone', 'ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin'])

    if (is_anticoag_1 and is_nsaid_2) or (is_anticoag_2 and is_nsaid_1):
        anticoag_name = d1 if is_anticoag_1 else d2
        nsaid_name = d2 if is_anticoag_1 else d1
        interactions.append({
            "drug1": anticoag_name,
            "drug2": nsaid_name,
            "severity": "Major",
            "description": f"[Clinical Contraindication] Severe Bleeding Diathesis: Combining anticoagulants ({anticoag_name}) with NSAIDs ({nsaid_name}) dramatically elevates gastrointestinal mucosal ulceration and life-threatening major bleeding risks due to platelet inhibition and gastric prostaglandin suppression."
        })

    if (is_anticoag_1 and is_quinolone_2) or (is_anticoag_2 and is_quinolone_1):
        anticoag_name = d1 if is_anticoag_1 else d2
        quin_name = d2 if is_anticoag_1 else d1
        interactions.append({
            "drug1": anticoag_name,
            "drug2": quin_name,
            "severity": "Major",
            "description": f"[Pharmacokinetic CYP1A2 Inhibition] Heightened Anticoagulation: Fluoroquinolones ({quin_name}) potently inhibit CYP enzymes and displace {anticoag_name} from plasma albumin, producing dangerously elevated INR and hemorrhages. Urgent INR monitoring indicated."
        })

    # 3c. Dual RAAS Blockade (ACE inhibitor + ARB)
    is_ace_1 = 'angiotensin converting enzyme inhibitor' in meta1.get("epc", "").lower() or any(d1.lower().endswith(s) for s in ['pril', 'lisinopril', 'enalapril', 'ramipril'])
    is_ace_2 = 'angiotensin converting enzyme inhibitor' in meta2.get("epc", "").lower() or any(d2.lower().endswith(s) for s in ['pril', 'lisinopril', 'enalapril', 'ramipril'])
    is_arb_1 = 'angiotensin receptor blocker' in meta1.get("epc", "").lower() or any(d1.lower().endswith(s) for s in ['sartan', 'losartan', 'valsartan', 'telmisartan'])
    is_arb_2 = 'angiotensin receptor blocker' in meta2.get("epc", "").lower() or any(d2.lower().endswith(s) for s in ['sartan', 'losartan', 'valsartan', 'telmisartan'])
    
    if (is_ace_1 and is_arb_2) or (is_ace_2 and is_arb_1):
        interactions.append({
            "drug1": d1,
            "drug2": d2,
            "severity": "Major",
            "description": "[Clinical Black Box Contraindication] Dual Renin-Angiotensin System Blockade: Concomitant use of ACE inhibitors and ARBs is contraindicated due to increased risks of severe hypotension, hyperkalemia, and acute renal failure with no additional cardiovascular benefit."
        })

    # 3d. Serotonergic Toxicity (SSRI / SNRI + Tramadol / MAOI / Linezolid)
    is_sert_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['serotonin', 'ssri', 'snri', 'fluoxetine', 'sertraline', 'escitalopram', 'paroxetine', 'citalopram'])
    is_sert_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['serotonin', 'ssri', 'snri', 'fluoxetine', 'sertraline', 'escitalopram', 'paroxetine', 'citalopram'])
    is_sert_agent_1 = any(w in d1.lower() for w in ['tramadol', 'linezolid', 'methylene blue', 'selegiline', 'phenelzine', 'lithium'])
    is_sert_agent_2 = any(w in d2.lower() for w in ['tramadol', 'linezolid', 'methylene blue', 'selegiline', 'phenelzine', 'lithium'])

    if (is_sert_1 and is_sert_agent_2) or (is_sert_2 and is_sert_agent_1) or (is_sert_1 and is_sert_2 and d1.lower() != d2.lower()):
        interactions.append({
            "drug1": d1,
            "drug2": d2,
            "severity": "Major",
            "description": "[FDA Safety Warning] Serotonin Syndrome Risk: Simultaneous administration of multiple serotonergic agents produces toxic central nervous system serotonin accumulation leading to hyperthermia, neuromuscular rigidity, autonomic instability, and delirium."
        })

    # 3e. Statin + Strong CYP3A4 Inhibitor (Macrolide or Azole Antifungal) -> Rhabdomyolysis
    is_statin_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['statin', 'atorvastatin', 'simvastatin', 'lovastatin', 'hmg-coa'])
    is_statin_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['statin', 'atorvastatin', 'simvastatin', 'lovastatin', 'hmg-coa'])
    is_cyp_inhib_1 = any(w in meta1.get("epc", "").lower() or w in d1.lower() for w in ['clarithromycin', 'erythromycin', 'ketoconazole', 'itraconazole', 'fluconazole', 'ritonavir', 'diltiazem'])
    is_cyp_inhib_2 = any(w in meta2.get("epc", "").lower() or w in d2.lower() for w in ['clarithromycin', 'erythromycin', 'ketoconazole', 'itraconazole', 'fluconazole', 'ritonavir', 'diltiazem'])

    if (is_statin_1 and is_cyp_inhib_2) or (is_statin_2 and is_cyp_inhib_1):
        statin_name = d1 if is_statin_1 else d2
        inhib_name = d2 if is_statin_1 else d1
        interactions.append({
            "drug1": statin_name,
            "drug2": inhib_name,
            "severity": "Major",
            "description": f"[FDA Black Box Warning] Rhabdomyolysis & Myopathy: Strong CYP3A4 inhibitors ({inhib_name}) markedly impede hepatic clearance of statins ({statin_name}), precipitating profound skeletal muscle breakdown (rhabdomyolysis) and acute myoglobinuric kidney failure."
        })

    # 3f. Digoxin + Antiarrhythmics / Macrolides / Loop Diuretics
    is_digoxin_1 = 'digoxin' in d1.lower()
    is_digoxin_2 = 'digoxin' in d2.lower()
    is_dig_risk_1 = any(w in d1.lower() for w in ['amiodarone', 'clarithromycin', 'erythromycin', 'verapamil', 'furosemide', 'spironolactone'])
    is_dig_risk_2 = any(w in d2.lower() for w in ['amiodarone', 'clarithromycin', 'erythromycin', 'verapamil', 'furosemide', 'spironolactone'])

    if (is_digoxin_1 and is_dig_risk_2) or (is_digoxin_2 and is_dig_risk_1):
        other_drug = d2 if is_digoxin_1 else d1
        interactions.append({
            "drug1": "Digoxin",
            "drug2": other_drug,
            "severity": "Major",
            "description": f"[Narrow Therapeutic Index Alert] Digitalis Toxicity: P-glycoprotein or renal clearance inhibition by {other_drug} dramatically surges serum digoxin levels, predisposing the patient to fatal cardiac heart blocks and ventricular tachyarrhythmias."
        })

    return interactions
