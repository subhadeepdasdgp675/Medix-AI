import os
import glob
import pandas as pd

def audit_all_csvs():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    csv_files = sorted(glob.glob(os.path.join(data_dir, '*.csv')))
    
    audit_results = []
    
    for f in csv_files:
        filename = os.path.basename(f)
        size_mb = os.path.getsize(f) / (1024 * 1024)
        
        # Read header & shape (or sample if huge)
        try:
            if size_mb > 100:
                # Read first 1000 rows to get columns and inspect
                df_sample = pd.read_csv(f, nrows=100)
                shape_str = f">100k rows (Sampled {size_mb:.1f} MB)"
                cols = list(df_sample.columns)
            else:
                df = pd.read_csv(f, low_memory=False)
                shape_str = f"{df.shape[0]} rows x {df.shape[1]} cols"
                cols = list(df.columns)
                df_sample = df.head(5)
                
            cols_summary = ", ".join(cols[:8]) + ("..." if len(cols) > 8 else "")
            
            # Determine functional classification and relevance
            role = "Excluded"
            rationale = "Not required for core 3 clinical workflows"
            
            name_lower = filename.lower()
            if "bacteria_dataset_multiresictance" in name_lower or "kaggle_amr" in name_lower or "microbiology_cultures" in name_lower:
                role = "ML Isolate Training Candidate"
                rationale = "Isolate-level specimen, pathogen, susceptibility/resistance data suitable for predictive recommender"
            elif "amr_global_regional" in name_lower or "who_glass" in name_lower or "mortality_burden" in name_lower:
                role = "Regional AMR Surveillance"
                rationale = "Regional/national pathogen resistance rates for Leaflet map & resistance scoring"
            elif "db_drug_interactions" in name_lower:
                role = "Drug-Drug Interactions"
                rationale = "Pairwise drug clinical interaction, severity, and mechanism table"
            elif "drugscom" in name_lower:
                role = "Excluded (Review/Sentiment)"
                rationale = "Patient user reviews and sentiment ratings; no clinical AMR/interaction relevance"
            elif "symptom" in name_lower or "training.csv" in name_lower or "testing.csv" in name_lower:
                role = "Disease/Symptom Diagnostic"
                rationale = "Symptom-disease mappings for infectious disease syndromic classification"
                
            audit_results.append({
                "Filename": filename,
                "Size (MB)": f"{size_mb:.2f}",
                "Shape": shape_str,
                "Key Columns": cols_summary,
                "Classification": role,
                "Rationale": rationale
            })
        except Exception as e:
            audit_results.append({
                "Filename": filename,
                "Size (MB)": f"{size_mb:.2f}",
                "Shape": "Error",
                "Key Columns": str(e)[:40],
                "Classification": "Error",
                "Rationale": "Could not parse CSV"
            })
            
    print("\n# Medix AI Automated Dataset Audit Report\n")
    print(f"Total CSVs audited in `{data_dir}`: {len(audit_results)}\n")
    
    # Markdown Table
    headers = ["Filename", "Size (MB)", "Shape", "Key Columns", "Classification", "Decision Rationale"]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in audit_results:
        row_str = f"| `{r['Filename']}` | {r['Size (MB)']} | {r['Shape']} | {r['Key Columns']} | **{r['Classification']}** | {r['Rationale']} |"
        print(row_str)
        
    print("\n### Selected Datasets for Pipeline Construction:")
    print("1. **Multi-tier ML Recommender Training**: `Kaggle_AMR_Dataset_v1.0.csv` & `Bacteria_dataset_Multiresictance.csv` (supplemented with clinical syndromic reference from `microbiology_cultures_cohort.csv`).")
    print("2. **Regional Resistance Surveillance & Heatmap**: `amr_global_regional_resistance_2016_2023.csv` and `amr_pathogen_reference_who_glass_8pathogens.csv`.")
    print("3. **Drug-Drug Interactions**: `db_drug_interactions.csv` (excluding sentiment review tables `drugsCom*`).\n")

if __name__ == '__main__':
    audit_all_csvs()
