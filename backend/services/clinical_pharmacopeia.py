"""
Medix AI Clinical Pharmacopeia & Indication-Specific Regimen Engine
Adheres strictly to FDA, BNF, WHO Model Formulary, and NLM RxNorm standards.

Rules:
1. Classification Purity:
   - Single-ingredient drugs mapped strictly to true pharmacologic class (e.g., Acetaminophen is "Aniline Derivative / Non-Opioid Analgesic & Antipyretic").
   - Antivirals, antibiotics, antifungals mapped strictly to accurate chemical/mechanism class.
2. Indication-Matched Dosing:
   - Adult Chickenpox / Varicella-Zoster: Oral Acyclovir 800 mg 5 times daily (q4h while awake) for 7 days; Oral Valacyclovir 1000 mg TID (q8h) for 7 days.
   - Adult Uncomplicated UTI: Oral Nitrofurantoin 100 mg BID (q12h) for 5 days; Fosfomycin 3 g oral single dose.
3. AMR Applicability:
   - Evaluated ONLY for antimicrobials (antibacterials, antivirals, antifungals).
   - Non-antimicrobials (Acetaminophen, Antihistamines, NSAIDs): amr_applicable = False, metrics = N/A / null.
   - Wild-type community viral infections (e.g., Varicella-Zoster): report "<1% (Rare)" rather than arbitrary bacterial rates.
4. Separation of Therapeutic Intent:
   - Explicitly splits into "1st Choice" (etiotropic), "Alternative" (etiotropic), and "Symptomatic".
5. Adverse Effects Purity:
   - Only true side effects (nausea, headache, nephrotoxicity); no mechanism text.
"""

from typing import Dict, List, Any, Optional

CLINICAL_REGIMENS: Dict[str, Dict[str, Any]] = {
    "Chicken pox": {
        "canonical_name": "Varicella (Chickenpox)",
        "etiology_type": "Viral (Varicella-Zoster Virus)",
        "recommendations": [
            {
                "treatment_tier": "1st Choice",
                "intent": "Etiotropic",
                "drug_name": "Valacyclovir",
                "rxcui": 372756,
                "established_class": "Nucleoside Analog DNA Polymerase Inhibitor",
                "dosage": {
                    "dose": "1000 mg",
                    "route": "Oral",
                    "frequency": "Every 8 hours (Three times daily)",
                    "duration": "7 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "None/Rare (<1%)",
                    "resistance_percentage": "<1%"
                },
                "side_effects": [
                    "Headache",
                    "Nausea",
                    "Abdominal pain",
                    "Transient elevation of liver transaminases"
                ]
            },
            {
                "treatment_tier": "Alternative",
                "intent": "Etiotropic",
                "drug_name": "Acyclovir",
                "rxcui": 281,
                "established_class": "Nucleoside Analog DNA Polymerase Inhibitor",
                "dosage": {
                    "dose": "800 mg",
                    "route": "Oral",
                    "frequency": "5 times daily (Every 4 hours while awake)",
                    "duration": "7 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "None/Rare (<1%)",
                    "resistance_percentage": "<1%"
                },
                "side_effects": [
                    "Nausea",
                    "Vomiting",
                    "Diarrhea",
                    "Headache",
                    "Reversible nephrotoxicity (crystal nephropathy with inadequate hydration)"
                ]
            },
            {
                "treatment_tier": "Symptomatic",
                "intent": "Symptomatic (Antipyretic / Analgesic)",
                "drug_name": "Acetaminophen",
                "rxcui": 161,
                "established_class": "Aniline Derivative / Non-Opioid Analgesic & Antipyretic",
                "dosage": {
                    "dose": "650 mg",
                    "route": "Oral",
                    "frequency": "Every 4 to 6 hours as needed (Maximum 3000 mg/24 hours)",
                    "duration": "3 to 5 days (as needed for fever and pain)"
                },
                "amr_data": {
                    "applicable": False,
                    "local_resistance_level": "N/A",
                    "resistance_percentage": None
                },
                "side_effects": [
                    "Hepatotoxicity (at excessive doses)",
                    "Hypersensitivity / Rash",
                    "Nausea"
                ]
            },
            {
                "treatment_tier": "Symptomatic",
                "intent": "Symptomatic (Antipruritic)",
                "drug_name": "Diphenhydramine",
                "rxcui": 3498,
                "established_class": "First-Generation Ethanolamine Histamine H1-Receptor Antagonist",
                "dosage": {
                    "dose": "25 mg",
                    "route": "Oral",
                    "frequency": "Every 6 hours as needed for pruritus",
                    "duration": "3 to 5 days (as needed for severe itching)"
                },
                "amr_data": {
                    "applicable": False,
                    "local_resistance_level": "N/A",
                    "resistance_percentage": None
                },
                "side_effects": [
                    "Sedation / Somnolence",
                    "Anticholinergic dry mouth",
                    "Dizziness",
                    "Urinary retention"
                ]
            }
        ]
    },
    "Urinary tract infection": {
        "canonical_name": "Uncomplicated Urinary Tract Infection (UTI)",
        "etiology_type": "Bacterial (Uropathogenic E. coli / Enterobacterales)",
        "recommendations": [
            {
                "treatment_tier": "1st Choice",
                "intent": "Etiotropic",
                "drug_name": "Nitrofurantoin",
                "rxcui": 7454,
                "established_class": "Nitrofuran Antibacterial",
                "dosage": {
                    "dose": "100 mg (monohydrate/macrocrystals)",
                    "route": "Oral",
                    "frequency": "Every 12 hours with meals",
                    "duration": "5 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "Low",
                    "resistance_percentage": "14%"
                },
                "side_effects": [
                    "Nausea",
                    "Headache",
                    "Anorexia",
                    "Urine discoloration (dark yellow/brown)"
                ]
            },
            {
                "treatment_tier": "Alternative",
                "intent": "Etiotropic",
                "drug_name": "Fosfomycin",
                "rxcui": 4543,
                "established_class": "Phosphonic Acid Derivative Antibacterial",
                "dosage": {
                    "dose": "3 g (tromethamine sachet)",
                    "route": "Oral",
                    "frequency": "Single dose mixed in water",
                    "duration": "1 day (Single dose)"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "Low",
                    "resistance_percentage": "9%"
                },
                "side_effects": [
                    "Diarrhea",
                    "Nausea",
                    "Headache",
                    "Vaginitis"
                ]
            },
            {
                "treatment_tier": "Alternative",
                "intent": "Etiotropic",
                "drug_name": "Trimethoprim/Sulfamethoxazole",
                "rxcui": 10528,
                "established_class": "Folate Synthesis Inhibitor Combination Antibacterial",
                "dosage": {
                    "dose": "160 mg / 800 mg (Double Strength)",
                    "route": "Oral",
                    "frequency": "Every 12 hours",
                    "duration": "3 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "Medium",
                    "resistance_percentage": "28%"
                },
                "side_effects": [
                    "Rash / Hypersensitivity",
                    "Gastrointestinal upset",
                    "Hyperkalemia",
                    "Photosensitivity"
                ]
            },
            {
                "treatment_tier": "Symptomatic",
                "intent": "Symptomatic (Urinary Analgesic)",
                "drug_name": "Phenazopyridine",
                "rxcui": 8163,
                "established_class": "Azo Dye Urinary Tract Mucosal Analgesic",
                "dosage": {
                    "dose": "200 mg",
                    "route": "Oral",
                    "frequency": "Three times daily after meals",
                    "duration": "2 days (maximum alongside antibacterial)"
                },
                "amr_data": {
                    "applicable": False,
                    "local_resistance_level": "N/A",
                    "resistance_percentage": None
                },
                "side_effects": [
                    "Bright orange/red urine discoloration",
                    "Headache",
                    "Dizziness",
                    "Methemoglobinemia (rare at high doses)"
                ]
            }
        ]
    },
    "Pneumonia": {
        "canonical_name": "Community-Acquired Pneumonia (CAP)",
        "etiology_type": "Bacterial (S. pneumoniae, Atypicals)",
        "recommendations": [
            {
                "treatment_tier": "1st Choice",
                "intent": "Etiotropic",
                "drug_name": "Amoxicillin/Clavulanate",
                "rxcui": 17562,
                "established_class": "Aminopenicillin and Beta-Lactamase Inhibitor Combination",
                "dosage": {
                    "dose": "875 mg / 125 mg",
                    "route": "Oral",
                    "frequency": "Every 12 hours",
                    "duration": "5 to 7 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "Low",
                    "resistance_percentage": "12%"
                },
                "side_effects": [
                    "Diarrhea",
                    "Nausea",
                    "Candidiasis",
                    "Skin rash"
                ]
            },
            {
                "treatment_tier": "Alternative",
                "intent": "Etiotropic",
                "drug_name": "Azithromycin",
                "rxcui": 18631,
                "established_class": "Macrolide / Azalide Antibacterial",
                "dosage": {
                    "dose": "500 mg Day 1, then 250 mg daily",
                    "route": "Oral",
                    "frequency": "Once daily",
                    "duration": "5 days"
                },
                "amr_data": {
                    "applicable": True,
                    "local_resistance_level": "Low",
                    "resistance_percentage": "16%"
                },
                "side_effects": [
                    "Nausea",
                    "Diarrhea",
                    "QTc interval prolongation",
                    "Abdominal cramping"
                ]
            },
            {
                "treatment_tier": "Symptomatic",
                "intent": "Symptomatic (Antipyretic / Analgesic)",
                "drug_name": "Acetaminophen",
                "rxcui": 161,
                "established_class": "Aniline Derivative / Non-Opioid Analgesic & Antipyretic",
                "dosage": {
                    "dose": "650 mg",
                    "route": "Oral",
                    "frequency": "Every 4 to 6 hours as needed",
                    "duration": "3 to 5 days"
                },
                "amr_data": {
                    "applicable": False,
                    "local_resistance_level": "N/A",
                    "resistance_percentage": None
                },
                "side_effects": [
                    "Hepatotoxicity (at excessive doses)",
                    "Rash",
                    "Nausea"
                ]
            }
        ]
    }
}

def get_validated_clinical_recommendations(disease_name: str, confidence_score: float = 95.0, case_id: str = "CASE-8901") -> Optional[Dict[str, Any]]:
    """
    Returns strict clinical pharmacopeia data structure with:
    - Zero conversational filler
    - Valid RxCUIs, Established NLM classes
    - Indication-matched dosing
    - Proper AMR applicability gating (False for non-antimicrobials)
    """
    try:
        from services.external_clinical_kb import EXTERNAL_DISEASE_REGIMENS
    except Exception:
        EXTERNAL_DISEASE_REGIMENS = {}

    all_regimens = {**CLINICAL_REGIMENS, **EXTERNAL_DISEASE_REGIMENS}

    # Normalize disease
    matched_key = None
    for k in all_regimens:
        if k.lower() == disease_name.lower() or k.lower() in disease_name.lower() or disease_name.lower() in k.lower():
            matched_key = k
            break
            
    if not matched_key:
        return None
        
    regimen = all_regimens[matched_key]
    conf_str = f"{confidence_score:.1f}%" if isinstance(confidence_score, float) else f"{confidence_score}%"

    
    clean_recs = []
    for r in regimen["recommendations"]:
        clean_recs.append({
            "treatment_tier": r["treatment_tier"],
            "drug_name": r["drug_name"],
            "rxcui": r["rxcui"],
            "established_class": r["established_class"],
            "dosage": r["dosage"],
            "amr_data": r["amr_data"],
            "side_effects": r["side_effects"]
        })
        
    return {
        "case_id": case_id,
        "diagnosis": regimen["canonical_name"],
        "confidence": conf_str,
        "recommendations": clean_recs
    }
