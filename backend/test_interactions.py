"""
Inline test suite verifying the Drug Interaction Checker:
a) Ciprofloxacin + Warfarin -> High/Critical / Major severity alert
b) Azithromycin + Amiodarone -> QT prolongation alert
c) Case-insensitivity & order-insensitivity: (Warfarin, CIPROFLOXACIN) == (ciprofloxacin, warfarin)
d) Dosage & salt stripping: 'Cipro 500mg' + 'Warfarin Sodium' -> matches
e) Brand resolution: 'Augmentin' -> 'amoxicillin'
"""

import os
import sys

# Ensure backend path is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from interaction_service import InteractionEngine, clean_drug_name

def run_tests():
    print("=== Testing clean_drug_name ===")
    assert clean_drug_name("Cipro 500mg") == "ciprofloxacin", f"Failed: {clean_drug_name('Cipro 500mg')}"
    assert clean_drug_name("Augmentin") == "amoxicillin", f"Failed: {clean_drug_name('Augmentin')}"
    assert clean_drug_name("Warfarin Sodium") == "warfarin", f"Failed: {clean_drug_name('Warfarin Sodium')}"
    assert clean_drug_name("Azithromycin 250 mg tablet") == "azithromycin", f"Failed: {clean_drug_name('Azithromycin 250 mg tablet')}"
    assert clean_drug_name("CIPROFLOXACIN HCL") == "ciprofloxacin", f"Failed: {clean_drug_name('CIPROFLOXACIN HCL')}"
    print("PASS: clean_drug_name tests passed!")

    print("\n=== Initializing InteractionEngine ===")
    engine = InteractionEngine()
    csv_path = os.path.join(backend_dir, "data", "db_drug_interactions.csv")
    engine.load_from_csv(csv_path)

    print("\n=== Test 1: Ciprofloxacin + Warfarin ===")
    res1 = engine.check_pair("Ciprofloxacin", "Warfarin")
    assert res1 is not None, "Failed: Ciprofloxacin + Warfarin not found!"
    assert res1["severity"] in ["Major", "Critical"], f"Expected Major/Critical severity, got {res1['severity']}"
    assert res1["safe_to_prescribe"] is False, "Expected safe_to_prescribe to be False"
    print(f"PASS: {res1['drug1']} + {res1['drug2']} -> Severity: {res1['severity']}, Safe: {res1['safe_to_prescribe']}")
    print(f"  Description snippet: {res1['description'][:90]}...")

    print("\n=== Test 2: Azithromycin + Amiodarone (QT Prolongation) ===")
    res2 = engine.check_pair("Azithromycin", "Amiodarone")
    assert res2 is not None, "Failed: Azithromycin + Amiodarone not found!"
    assert any(term in (res2["description"] + res2["effect"]).lower() for term in ["qt", "qtc", "arrhythmia", "torsades"]), "Expected QT prolongation alert!"
    assert res2["severity"] in ["Major", "Critical"], f"Expected Major severity, got {res2['severity']}"
    print(f"PASS: {res2['drug1']} + {res2['drug2']} -> Severity: {res2['severity']}")
    print(f"  Description snippet: {res2['description'][:90]}...")

    print("\n=== Test 3: Order & Case Insensitivity ===")
    res3_a = engine.check_pair("Warfarin", "CIPROFLOXACIN")
    res3_b = engine.check_pair("ciprofloxacin", "warfarin")
    assert res3_a is not None and res3_b is not None, "Failed: Case/order query returned None"
    assert res3_a["severity"] == res3_b["severity"], "Severities differ by order/case"
    assert res3_a["resolvedDrug1"] in ["ciprofloxacin", "warfarin"]
    assert res3_a["resolvedDrug2"] in ["ciprofloxacin", "warfarin"]
    print("PASS: Case and order insensitivity verified!")

    print("\n=== Test 4: Dosage & Salt Variations ===")
    res4 = engine.check_pair("Cipro 500mg", "Warfarin Sodium 5mg")
    assert res4 is not None, "Failed: Cipro 500mg + Warfarin Sodium 5mg not found!"
    assert res4["severity"] in ["Major", "Critical"], f"Expected Major severity, got {res4['severity']}"
    print(f"PASS: Cipro 500mg + Warfarin Sodium -> {res4['severity']}")

    print("\n=== Test 5: Brand to Generic Resolution (Augmentin + Methotrexate) ===")
    res5 = engine.check_pair("Augmentin", "Methotrexate")
    assert res5 is not None, "Failed: Augmentin + Methotrexate not found!"
    assert res5["resolvedDrug1"] == "amoxicillin" or res5["resolvedDrug2"] == "amoxicillin"
    print(f"PASS: Augmentin resolved to {res5['resolvedDrug1']} and detected interaction: {res5['severity']}")

    print("\n ALL INTERACTION CHECKER TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
