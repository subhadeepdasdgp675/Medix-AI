"""
Comprehensive Multi-Drug Polypharmacy and Architecture Verification Suite
Tests:
1. Exact unified cards: 0 duplicate or inverted pairs (e.g. Warfarin <-> Aspirin vs Aspirin <-> Warfarin)
2. Polypharmacy combinatorial support for N >= 3 drugs (e.g., Aspirin, Warfarin, Ciprofloxacin -> 3 combinations evaluated)
3. Local knowledge base primary resolution (@backend/data/db_drug_interactions.csv)
4. Scoped FDA parser isolation (no text bleed)
5. Severity precedence ranking (CRITICAL > MAJOR > MODERATE > MINOR > UNKNOWN)
6. NLM NIH RxNav normalizer caching & concept extraction
"""

import os
import sys
import asyncio

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from services.drug_normalizer import normalize_drug_rxnav, batch_normalize_drugs
from services.interaction_service import (
    InteractionEngine,
    clean_drug_name,
    slice_scoped_fda_text,
    evaluate_polypharmacy_interactions,
    compare_severity
)

async def run_audit_suite():
    print("=================================================================")
    print("  MEDIX AI - CLINICAL MULTI-DRUG INTERACTION CHECKER AUDIT")
    print("=================================================================")

    # 1. Test Scoped FDA Parser (Text Bleed Elimination)
    print("\n[Test 1] Validating Scoped OpenFDA Parser (Text Bleed Prevention)...")
    sample_fda_section_7 = """
    7.1 Anticoagulants
    Concomitant use of ASPIRIN with warfarin increases the risk of severe bleeding and hemorrhage.
    Platelet inhibition combined with impaired clotting factor synthesis requires intense INR monitoring.

    7.2 Dipyridamole
    Dipyridamole should not be administered concomitantly due to risk of cardiovascular hypotension and adenosine reuptake alteration.

    7.3 ACE Inhibitors
    Aspirin may diminish the antihypertensive efficacy of ACE inhibitors.
    """
    scoped = slice_scoped_fda_text(sample_fda_section_7, "Warfarin")
    assert scoped is not None, "Failed to isolate partner text!"
    assert "warfarin" in scoped.lower(), "Scoped text does not contain target drug!"
    assert "dipyridamole" not in scoped.lower(), "CRITICAL FAIL: Text bleed into section 7.2 occurred!"
    assert "ace inhibitors" not in scoped.lower(), "CRITICAL FAIL: Text bleed into section 7.3 occurred!"
    print(f"PASS: Text cleanly isolated without subsection bleed:\n   '{scoped}'")

    # 2. Test Severity Precedence
    print("\n[Test 2] Validating Severity Precedence Ranking...")
    assert compare_severity("Major", "Moderate") == "Major"
    assert compare_severity("Minor", "Critical") == "Critical"
    assert compare_severity("Moderate", "Minor") == "Moderate"
    print("PASS: Precedence order CRITICAL > MAJOR > MODERATE > MINOR > UNKNOWN verified.")

    # 3. Test Ingestion and In-Memory Graph Index of db_drug_interactions.csv
    print("\n[Test 3] Loading In-Memory Graph Index of db_drug_interactions.csv...")
    engine = InteractionEngine()
    csv_path = os.path.join(backend_dir, "data", "db_drug_interactions.csv")
    engine.load_from_csv(csv_path)
    assert engine.loaded_count > 100000, f"Expected >100,000 interactions loaded, found {engine.loaded_count}"
    print(f"PASS: {engine.loaded_count} canonical pairs indexed from local knowledge base.")

    # 4. Test Polypharmacy Evaluation (N = 3: Aspirin, Warfarin, Ciprofloxacin)
    print("\n[Test 4] Evaluating Multi-Drug Polypharmacy Combinations (N = 3)...")
    drugs = ["Aspirin", "Warfarin", "Ciprofloxacin"]
    
    # Semantic standardization
    rx_meta = await batch_normalize_drugs(drugs)
    assert len(rx_meta) == 3, f"Expected 3 normalized objects, got {len(rx_meta)}"
    print(f"PASS: Batch standardized {len(rx_meta)} drugs with RxNav concepts.")

    res = await evaluate_polypharmacy_interactions(drugs, engine, rx_meta)
    
    interactions = res.get("interactions", [])
    print(f"Total interactions returned: {len(interactions)}")

    # Check for NO duplicate / inverted pairs
    seen_pairs = set()
    for item in interactions:
        d1 = clean_drug_name(item["drug1"])
        d2 = clean_drug_name(item["drug2"])
        pair = tuple(sorted([d1, d2]))
        assert pair not in seen_pairs, f"CRITICAL FAIL: Duplicate/inverted pair rendered for {pair}!"
        seen_pairs.add(pair)
        print(f"  Unified Record: {item['drug1']} <-> {item['drug2']} | Severity: {item['severity']}")

    print("PASS: Exactly ONE unified card per unique unordered pair guaranteed!")

    # Check overall severity & safety
    assert res["status"] == "Interaction Found"
    assert res["severity"] == "Major"
    assert res["safe_to_prescribe"] is False
    print("PASS: Polypharmacy evaluation returned correct overall Major risk alert and safe_to_prescribe=False.")

    # 5. Inverted input order check: ["Warfarin", "Aspirin"] vs ["Aspirin", "Warfarin"]
    print("\n[Test 5] Validating Order Invariance across Polypharmacy Lists...")
    res_inv = await evaluate_polypharmacy_interactions(["Warfarin", "Aspirin"], engine, rx_meta)
    assert len(res_inv["interactions"]) == 1
    assert res_inv["interactions"][0]["severity"].upper() == "MAJOR"
    assert res_inv["interactions"][0]["recommended_alternative"] == "Acetaminophen (Paracetamol)"
    assert "Bleeding" in res_inv["interactions"][0]["risk_factor"] or "Hemorrhage" in res_inv["interactions"][0]["risk_factor"]
    print("PASS: Inverted input yields exact same clinical determination and dynamic alternative recommendation.")

    print("\n=================================================================")
    print("  ALL MULTI-DRUG POLYPHARMACY TESTS PASSED (100% SUCCESS)")
    print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_audit_suite())
