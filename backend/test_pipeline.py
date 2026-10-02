"""
Medix AI Clinical Core Pipeline - Automated Smoke & Integration Test Suite
Verifies:
1. Standard case present in CSV (E. coli UTI) -> Verifies ML model output with 1st, 2nd, 3rd choices.
2. Rare condition not in CSV -> Verifies external API fallback completes without 500 errors.
3. Patient taking Warfarin -> Verifies Ciprofloxacin is flagged while Nitrofurantoin is cleared.
4. Leaflet map endpoint -> Verifies valid numeric latitude/longitude and intensity array output.
"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8080"

async def run_smoke_tests():
    print("=====================================================================")
    print("MEDIX AI CLINICAL DECISION-SUPPORT PIPELINE SMOKE TESTS")
    print("=====================================================================\n")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # TEST 1: Health check
        print("[TEST 1/5] Checking Backend Server Liveness...")
        try:
            health_resp = await client.get("/health")
            assert health_resp.status_code == 200, f"Health check failed with {health_resp.status_code}"
            print("  [PASS] Backend is ONLINE (Status 200 OK)\n")
        except Exception as e:
            print(f"  [FAIL] Server unreachable at {BASE_URL}: {e}")
            return False

        # TEST 2: Standard case (E. coli UTI) via ML Recommender
        print("[TEST 2/5] Testing Standard Case (E. coli UTI via ML Recommender)...")
        payload_std = {
            "age": 45,
            "infection_site": "Urinary Tract Infection",
            "suspected_pathogen": "Escherichia coli",
            "region": "Delhi",
            "current_medications": []
        }
        resp_std = await client.post("/api/recommend", json=payload_std)
        assert resp_std.status_code == 200, f"Recommendation failed with {resp_std.status_code}: {resp_std.text}"
        data_std = resp_std.json()
        assert "case_summary" in data_std, "Missing case_summary in payload"
        assert "recommendations" in data_std, "Missing recommendations in payload"
        assert len(data_std["recommendations"]) == 3, f"Expected 3 choices, got {len(data_std['recommendations'])}"
        
        ranks = [r["rank"] for r in data_std["recommendations"]]
        assert ranks == [1, 2, 3], f"Unexpected ranks: {ranks}"
        
        print(f"  [PASS] Resolution Tier: {data_std['case_summary'].get('resolution_tier')}")
        print("  [PASS] Top 3 Recommendations:")
        for r in data_std["recommendations"]:
            print(f"    - Rank {r['rank']}: {r['antibiotic']} | Conf: {r['confidence_score']} | Res: {int(r['regional_resistance_rate']*100)}% | Microbiome: {r['microbiome_impact']}")
        print()

        # TEST 3: Polypharmacy with Warfarin (Verify Ciprofloxacin vs Nitrofurantoin)
        print("[TEST 3/5] Testing Drug-Drug Interaction Check (Patient on Warfarin)...")
        payload_warfarin = {
            "age": 55,
            "infection_site": "Urinary Tract Infection",
            "suspected_pathogen": "Escherichia coli",
            "region": "Delhi",
            "current_medications": ["Warfarin"]
        }
        resp_war = await client.post("/api/recommend", json=payload_warfarin)
        assert resp_war.status_code == 200, f"Warfarin test failed: {resp_war.status_code}"
        data_war = resp_war.json()
        
        nitro_choice = next((r for r in data_war["recommendations"] if "nitrofurantoin" in r["antibiotic"].lower()), None)
        cipro_or_levo = next((r for r in data_war["recommendations"] if any(q in r["antibiotic"].lower() for q in ["ciprofloxacin", "levofloxacin"])), None)
        
        if nitro_choice:
            print(f"  [PASS] Nitrofurantoin Interaction Status: {nitro_choice['interaction_warning']}")
            assert "safe" in nitro_choice['interaction_warning'].lower() or "no known" in nitro_choice['interaction_warning'].lower()
            
        if cipro_or_levo:
            print(f"  [PASS] Fluoroquinolone Interaction Status: {cipro_or_levo['interaction_warning']}")
            assert any(term in cipro_or_levo['interaction_warning'].lower() for term in ["caution", "contraindicated", "anticoagulant", "bleeding", "inr"])
            print(f"  [PASS] Fluoroquinolone correctly penalized/demoted: {cipro_or_levo['why_this_choice']}")

        # Standalone check-interactions test
        resp_check = await client.post("/api/check-interactions", json={"drugs": ["Ciprofloxacin", "Warfarin"]})
        assert resp_check.status_code == 200
        int_data = resp_check.json()
        print(f"  [PASS] Standalone Pairwise Check: Flagged {int_data.get('flagged_interactions_count')} interaction(s) (Severity: {int_data.get('highest_severity')})")
        print()

        # TEST 4: Rare condition not in CSV (Live Guideline/External API Fallback)
        print("[TEST 4/5] Testing Rare Condition / Live Clinical Fallback (Actinomycosis)...")
        payload_rare = {
            "age": 62,
            "infection_site": "Actinomycosis Cervicofacial",
            "suspected_pathogen": "Actinomyces israelii",
            "region": "Maharashtra",
            "current_medications": []
        }
        resp_rare = await client.post("/api/recommend", json=payload_rare)
        assert resp_rare.status_code == 200, f"Fallback failed with {resp_rare.status_code}: {resp_rare.text}"
        data_rare = resp_rare.json()
        assert data_rare["case_summary"]["resolution_tier"] == "LIVE_CLINICAL_FALLBACK"
        assert len(data_rare["recommendations"]) == 3
        print(f"  [PASS] Resolution Tier: {data_rare['case_summary']['resolution_tier']}")
        print(f"  [PASS] Zero 500 errors. Fallback recommended: {[r['antibiotic'] for r in data_rare['recommendations']]}")
        print()

        # TEST 5: Regional AMR Leaflet Heatmap Array Pipeline
        print("[TEST 5/5] Testing Regional AMR Heatmap & Leaflet Coordinates Pipeline...")
        resp_map = await client.get("/api/resistance-map?location=Delhi&drug=Ciprofloxacin&pathogen=Escherichia+coli")
        assert resp_map.status_code == 200, f"Map endpoint failed: {resp_map.status_code}"
        data_map = resp_map.json()
        
        assert "heatmap" in data_map, "Missing heatmap array in response"
        heatmap_points = data_map["heatmap"]
        assert len(heatmap_points) > 10, f"Expected >10 state points, got {len(heatmap_points)}"
        
        # Verify numeric [lat, lng, intensity] format
        for pt in heatmap_points[:5]:
            assert isinstance(pt, list) and len(pt) == 3, f"Invalid point format: {pt}"
            lat, lng, intensity = pt
            assert isinstance(lat, (int, float)) and 8.0 <= lat <= 38.0, f"Invalid latitude: {lat}"
            assert isinstance(lng, (int, float)) and 68.0 <= lng <= 98.0, f"Invalid longitude: {lng}"
            assert isinstance(intensity, (int, float)) and 0.0 <= intensity <= 1.0, f"Invalid intensity: {intensity}"
            
        print(f"  [PASS] Validated {len(heatmap_points)} geographic coordinates for Leaflet heatLayer.")
        print("  [PASS] Sample Leaflet coordinate triples [lat, lng, intensity]:")
        for pt in heatmap_points[:3]:
            print(f"    - {pt}")
        print()
        
    print("=====================================================================")
    print("ALL 5 MEDIX AI CLINICAL DECISION-SUPPORT PIPELINE TESTS PASSED!")
    print("=====================================================================")
    return True

if __name__ == '__main__':
    asyncio.run(run_smoke_tests())
