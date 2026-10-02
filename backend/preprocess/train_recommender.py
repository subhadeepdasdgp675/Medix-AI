"""
Medix AI Recommender Training Pipeline
Trains a calibrated classifier on clinical isolate and culture susceptibility datasets
to predict the most clinically effective susceptible antibiotic for a given pathogen,
infection site, patient age, comorbidities, and region.
"""

import os
import re
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def build_training_dataset():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    records = []
    
    # 1. Ingest microbiology cultures cohort (Isolate-level specimen data)
    cohort_path = os.path.join(data_dir, 'microbiology_cultures_cohort.csv')
    demo_path = os.path.join(data_dir, 'microbiology_cultures_demographics.csv')
    
    if os.path.exists(cohort_path):
        print(f"Loading microbiology cultures isolate data from {cohort_path}...")
        df_mic = pd.read_csv(cohort_path, nrows=120000, low_memory=False)
        pos_mic = df_mic[
            (df_mic['was_positive'] == 1) & 
            (df_mic['susceptibility'] == 'Susceptible') & 
            (df_mic['organism'].notna()) & 
            (df_mic['organism'] != 'Null') &
            (df_mic['antibiotic'].notna()) & 
            (df_mic['antibiotic'] != 'Null')
        ].copy()
        
        # Merge with demographics if available
        demo_map = {}
        if os.path.exists(demo_path):
            df_demo = pd.read_csv(demo_path, nrows=100000, low_memory=False)
            df_demo_clean = df_demo[['anon_id', 'age', 'gender']].drop_duplicates(subset=['anon_id'])
            for _, r in df_demo_clean.iterrows():
                demo_map[r['anon_id']] = (r['age'], r['gender'])
                
        site_map = {
            'URINE': 'Urinary Tract Infection',
            'RESPIRATORY': 'Respiratory Tract Infection',
            'BLOOD': 'Bloodstream Infection'
        }
        
        for _, r in pos_mic.iterrows():
            org_raw = str(r['organism']).strip().title()
            abx = str(r['antibiotic']).strip()
            site = site_map.get(str(r['culture_description']).upper(), 'Systemic Infection')
            
            # Fetch demo
            demo_info = demo_map.get(r['anon_id'], (None, None))
            raw_age = demo_info[0]
            try:
                age_val = float(raw_age) if pd.notna(raw_age) else 45.0
            except:
                age_val = 45.0
                
            records.append({
                'pathogen': org_raw,
                'infection_site': site,
                'age': age_val,
                'comorbidity': 'None',
                'region': 'Global',
                'antibiotic': abx
            })
        print(f"Extracted {len(records)} susceptible isolate instances from microbiology cohort.")
        
    # 2. Ingest Bacteria_dataset_Multiresictance.csv
    bac_path = os.path.join(data_dir, 'Bacteria_dataset_Multiresictance.csv')
    if os.path.exists(bac_path):
        print(f"Loading multi-resistance bacteria isolates from {bac_path}...")
        df_bac = pd.read_csv(bac_path, low_memory=False)
        abx_cols = {
            'Furanes': 'Nitrofurantoin',
            'CIP': 'Ciprofloxacin',
            'Co-trimoxazole': 'Trimethoprim/Sulfamethoxazole',
            'AMC': 'Amoxicillin/Clavulanate',
            'AMX/AMP': 'Ampicillin',
            'CTX/CRO': 'Ceftriaxone',
            'IPM': 'Imipenem',
            'GEN': 'Gentamicin',
            'AN': 'Amikacin'
        }
        
        bac_count = 0
        for _, row in df_bac.iterrows():
            raw_s = str(row['Souches']).strip()
            if raw_s in ['?', 'nan', 'missing', '']:
                continue
            p = re.sub(r'^[A-Z0-9]+\s+', '', raw_s).strip().title()
            if p.lower() in ['e.coi', 'e.cli', 'e. coli']:
                p = 'Escherichia Coli'
            elif 'enterobact' in p.lower():
                p = 'Enterobacter Spp.'
            elif 'citrobact' in p.lower():
                p = 'Citrobacter Spp.'
                
            raw_ag = str(row.get('age/gender', '')).strip()
            age_val = 45.0
            if '/' in raw_ag:
                try:
                    age_val = float(raw_ag.split('/')[0])
                except:
                    age_val = 45.0
                    
            diab = str(row.get('Diabetes', '')).lower() in ['true', 'yes', '1']
            htn = str(row.get('Hypertension', '')).lower() in ['true', 'yes', '1']
            comorb = 'Diabetes' if diab else ('Hypertension' if htn else 'None')
            
            # Find susceptible antibiotics
            for col_key, drug_name in abx_cols.items():
                v = str(row.get(col_key, '')).upper().strip()
                if v == 'S':
                    records.append({
                        'pathogen': p,
                        'infection_site': 'Urinary Tract Infection',
                        'age': age_val,
                        'comorbidity': comorb,
                        'region': 'Regional/National',
                        'antibiotic': drug_name
                    })
                    bac_count += 1
                    break
        print(f"Extracted {bac_count} instances from Bacteria_dataset_Multiresictance.")

    df_all = pd.DataFrame(records)
    print(f"Total compiled dataset shape: {df_all.shape}")
    
    # Filter classes with at least 50 samples for robust statistical training
    abx_counts = df_all['antibiotic'].value_counts()
    valid_abx = abx_counts[abx_counts >= 100].index.tolist()
    df_filtered = df_all[df_all['antibiotic'].isin(valid_abx)].copy()
    print(f"Filtered to top {len(valid_abx)} high-frequency target antibiotics ({len(df_filtered)} samples).")
    print("Classes:", valid_abx)
    return df_filtered

def train_and_export():
    df = build_training_dataset()
    
    feature_cols = ['pathogen', 'infection_site', 'age', 'comorbidity', 'region']
    target_col = 'antibiotic'
    
    X = df[feature_cols]
    y = df[target_col]
    
    categorical_features = ['pathogen', 'infection_site', 'comorbidity', 'region']
    numerical_features = ['age']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features),
            ('num', StandardScaler(), numerical_features)
        ]
    )
    
    base_rf = RandomForestClassifier(
        n_estimators=100, 
        max_depth=16, 
        min_samples_split=5, 
        random_state=42, 
        n_jobs=-1
    )
    
    # Wrap in calibrated classifier for well-calibrated probabilities
    calibrated_clf = CalibratedClassifierCV(estimator=base_rf, method='sigmoid', cv=3)
    
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', calibrated_clf)
    ])
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)
    
    print("\nTraining Calibrated Multi-Tier Recommender Pipeline...")
    pipeline.fit(X_train, y_train)
    
    train_acc = pipeline.score(X_train, y_train)
    test_acc = pipeline.score(X_test, y_test)
    print(f"Training Accuracy: {train_acc * 100:.2f}% | Test Accuracy: {test_acc * 100:.2f}%")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'antibiotic_recommender.joblib')
    metadata_path = os.path.join(models_dir, 'recommender_metadata.json')
    
    print(f"Exporting model pipeline to {model_path}...")
    joblib.dump(pipeline, model_path)
    
    # Extract metadata (known classes, pathogens, infection sites)
    classes = list(pipeline.named_steps['classifier'].classes_)
    known_pathogens = sorted(list(df['pathogen'].unique()))
    known_sites = sorted(list(df['infection_site'].unique()))
    
    metadata = {
        "model_type": "CalibratedClassifierCV(RandomForestClassifier)",
        "features": feature_cols,
        "classes": classes,
        "known_pathogens": known_pathogens,
        "known_infection_sites": known_sites,
        "sample_count": len(df),
        "accuracy_test": round(test_acc, 4)
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved recommender metadata to {metadata_path}.")

if __name__ == '__main__':
    train_and_export()
