import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from preprocess.merge_datasets import load_and_merge

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'clinical_model.pkl')
FEATURES_PATH = os.path.join(os.path.dirname(__file__), 'models', 'clinical_features.pkl')
DISEASE_DRUGS_PATH = os.path.join(os.path.dirname(__file__), 'models', 'disease_to_drugs.pkl')
DRUG_META_PATH = os.path.join(os.path.dirname(__file__), 'models', 'drug_metadata.pkl')

def build_disease_to_drugs_map():
    """
    Builds a comprehensive, authentic clinical mapping from Disease prognosis 
    to therapeutic antimicrobial and clinical drug candidates.
    """
    return {
        'Urinary tract infection': ['Nitrofurantoin', 'Ciprofloxacin', 'Amoxicillin', 'Ofloxacin', 'Cefixime', 'Gentamicin', 'Sulfamethoxazole'],
        'Pneumonia': ['Amoxicillin', 'Azithromycin', 'Ceftriaxone', 'Ciprofloxacin', 'Clarithromycin', 'Levofloxacin'],
        'Typhoid': ['Ciprofloxacin', 'Ceftriaxone', 'Azithromycin', 'Chloramphenicol', 'Ofloxacin'],
        'Fungal infection': ['Fluconazole', 'Ketoconazole', 'Miconazole', 'Clotrimazole'],
        'Tuberculosis': ['Isoniazid', 'Rifampicin', 'Ethambutol', 'Pyrazinamide', 'Streptomycin'],
        'Gastroenteritis': ['Ciprofloxacin', 'Ofloxacin', 'Metronidazole', 'Azithromycin', 'Sulfamethoxazole'],
        'Impetigo': ['Amoxicillin', 'Cefazolin', 'Clindamycin', 'Erythromycin', 'Gentamicin'],
        'Acne': ['Minocycline', 'Clindamycin', 'Erythromycin', 'Isotretinoin', 'Tetracycline'],
        'Allergy': ['Cetirizine', 'Loratadine', 'Diphenhydramine', 'Fexofenadine', 'Prednisolone'],
        'GERD': ['Omeprazole', 'Pantoprazole', 'Esomeprazole', 'Ranitidine'],
        'Peptic ulcer disease': ['Omeprazole', 'Pantoprazole', 'Amoxicillin', 'Clarithromycin', 'Metronidazole'],
        'Common Cold': ['Acetaminophen', 'Ibuprofen', 'Amoxicillin', 'Azithromycin'],
        'Bronchial Asthma': ['Salbutamol', 'Terbutaline', 'Prednisolone', 'Fenoterol'],
        'Migraine': ['Ibuprofen', 'Naproxen', 'Acetaminophen', 'Propranolol'],
        'Diabetes': ['Metformin', 'Insulin', 'Glipizide', 'Glyburide'],
        'Hypertension': ['Amlodipine', 'Lisinopril', 'Losartan', 'Metoprolol', 'Atenolol'],
        'Malaria': ['Chloroquine', 'Hydroxychloroquine', 'Artemether', 'Quinine'],
        'Dengue': ['Acetaminophen', 'Ibuprofen'],
        'Chicken pox': ['Acyclovir', 'Valacyclovir', 'Acetaminophen'],
        'Jaundice': ['Ursodeoxycholic acid', 'Cholestyramine', 'Vitamin K'],
        'Chronic cholestasis': ['Ursodeoxycholic acid', 'Cholestyramine', 'Vitamin K'],
        'Hepatitis A': ['Ribavirin', 'Prednisolone', 'Acetaminophen'],
        'Hepatitis B': ['Entecavir', 'Tenofovir', 'Lamivudine'],
        'Hepatitis C': ['Ribavirin', 'Sofosbuvir', 'Interferon'],
        'Hepatitis D': ['Ribavirin', 'Prednisolone', 'Acetaminophen'],
        'Hepatitis E': ['Ribavirin', 'Prednisolone', 'Acetaminophen'],
        'Alcoholic hepatitis': ['Prednisolone', 'Pentoxifylline', 'Acetaminophen'],
        'AIDS': ['Zidovudine', 'Lamivudine', 'Tenofovir', 'Efavirenz', 'Ritonavir'],
        'Arthritis': ['Ibuprofen', 'Naproxen', 'Diclofenac', 'Celecoxib', 'Methotrexate'],
        'Osteoarthritis': ['Ibuprofen', 'Naproxen', 'Diclofenac', 'Celecoxib'],
        'Cervical spondylosis': ['Ibuprofen', 'Naproxen', 'Diclofenac', 'Methotrexate'],
        'Drug Reaction': ['Prednisolone', 'Diphenhydramine', 'Cetirizine', 'Epinephrine'],
        'Heart attack': ['Aspirin', 'Atorvastatin', 'Clopidogrel', 'Metoprolol', 'Nitroglycerin'],
        'Hyperthyroidism': ['Propylthiouracil', 'Methimazole', 'Propranolol'],
        'Hypothyroidism': ['Levothyroxine', 'Liothyronine'],
        'Hypoglycemia': ['Dextrose', 'Glucagon'],
        'Paralysis (brain hemorrhage)': ['Aspirin', 'Clopidogrel', 'Atorvastatin'],
        'Psoriasis': ['Methotrexate', 'Cyclosporine', 'Betamethasone'],
        'Varicose veins': ['Diosmin', 'Hydrocortisone', 'Lidocaine'],
        'Dimorphic hemorrhoids(piles)': ['Diosmin', 'Hydrocortisone', 'Lidocaine'],
        'Paroxysmal Positional Vertigo': ['Betahistine', 'Meclizine', 'Ondansetron', 'Prochlorperazine']
    }

def build_drug_metadata_map(drugs_info_path: str):
    """
    Loads real pharmacological descriptions, mechanisms, and side effect profiles
    from drugsInfo.csv, augmenting with standard dosing guidelines.
    """
    meta_map = {}
    if os.path.exists(drugs_info_path):
        df = pd.read_csv(drugs_info_path)
        for _, row in df.iterrows():
            name = str(row['DrugName']).strip()
            desc = str(row['DrugDescription']) if pd.notna(row['DrugDescription']) else ""
            mech = str(row['DrugMechanism']) if pd.notna(row['DrugMechanism']) else ""
            pdyn = str(row['DrugPharmacodynamics']) if pd.notna(row['DrugPharmacodynamics']) else ""
            cats = str(row['DrugCategories']) if pd.notna(row['DrugCategories']) else ""
            
            meta_map[name] = {
                "description": desc,
                "mechanism": mech,
                "sideEffects": pdyn[:250] + "..." if len(pdyn) > 250 else (pdyn if pdyn else "Check clinical prescribing guidelines for side effects."),
                "categories": cats
            }
            
    # Standard fallback / dosing guidelines for all candidate drugs
    standard_dosages = {
        'Amoxicillin': {'dosage': '500 mg', 'frequency': 'Every 8 hours', 'duration': '5-7 Days'},
        'Ciprofloxacin': {'dosage': '500 mg', 'frequency': 'Every 12 hours', 'duration': '5-7 Days'},
        'Nitrofurantoin': {'dosage': '100 mg', 'frequency': 'Every 12 hours', 'duration': '5 Days'},
        'Cefixime': {'dosage': '400 mg', 'frequency': 'Once daily', 'duration': '7 Days'},
        'Ofloxacin': {'dosage': '400 mg', 'frequency': 'Every 12 hours', 'duration': '5-7 Days'},
        'Gentamicin': {'dosage': '5 mg/kg', 'frequency': 'Once daily IV/IM', 'duration': '5-7 Days'},
        'Azithromycin': {'dosage': '500 mg', 'frequency': 'Once daily', 'duration': '3-5 Days'},
        'Ceftriaxone': {'dosage': '1-2 g', 'frequency': 'Once daily IV/IM', 'duration': '7-10 Days'},
        'Fluconazole': {'dosage': '150 mg', 'frequency': 'Once daily or single dose', 'duration': '1-7 Days'},
        'Ketoconazole': {'dosage': '200 mg', 'frequency': 'Once daily', 'duration': '14 Days'},
        'Isoniazid': {'dosage': '300 mg', 'frequency': 'Once daily', 'duration': '6 Months'},
        'Rifampicin': {'dosage': '600 mg', 'frequency': 'Once daily', 'duration': '6 Months'},
        'Metronidazole': {'dosage': '400 mg', 'frequency': 'Every 8 hours', 'duration': '7 Days'},
        'Cetirizine': {'dosage': '10 mg', 'frequency': 'Once daily', 'duration': 'As needed'},
        'Omeprazole': {'dosage': '20 mg', 'frequency': 'Once daily before breakfast', 'duration': '14 Days'},
        'Pantoprazole': {'dosage': '40 mg', 'frequency': 'Once daily before breakfast', 'duration': '14 Days'},
        'Acetaminophen': {'dosage': '500-650 mg', 'frequency': 'Every 6 hours as needed', 'duration': '3-5 Days'},
        'Ibuprofen': {'dosage': '400 mg', 'frequency': 'Every 8 hours with food', 'duration': '3-5 Days'},
        'Clindamycin': {'dosage': '300 mg', 'frequency': 'Every 6 hours', 'duration': '7-10 Days'},
        'Erythromycin': {'dosage': '500 mg', 'frequency': 'Every 6 hours', 'duration': '7 Days'},
        'Chloramphenicol': {'dosage': '50 mg/kg', 'frequency': 'Divided every 6 hours', 'duration': '7-10 Days'},
        'Amikacin': {'dosage': '15 mg/kg', 'frequency': 'Once daily IV/IM', 'duration': '7-10 Days'},
        'Imipenem': {'dosage': '500 mg', 'frequency': 'Every 6 hours IV', 'duration': '7-10 Days'},
        'Cefazolin': {'dosage': '1 g', 'frequency': 'Every 8 hours IV', 'duration': '7 Days'},
        'Cefoxitin': {'dosage': '1-2 g', 'frequency': 'Every 6-8 hours IV', 'duration': '7 Days'},
        'Sulfamethoxazole': {'dosage': '800/160 mg', 'frequency': 'Every 12 hours', 'duration': '7-10 Days'},
        'Cotrimoxazole': {'dosage': '960 mg', 'frequency': 'Every 12 hours', 'duration': '7 Days'}
    }
    
    for drg, info in standard_dosages.items():
        if drg not in meta_map:
            meta_map[drg] = {
                "description": f"Standard antimicrobial/therapeutic agent for clinical indication: {drg}.",
                "mechanism": "Inhibits pathogen synthesis / therapeutic target.",
                "sideEffects": "Gastrointestinal discomfort, nausea, headache. Check prescribing info.",
                "categories": "Anti-infective / Therapeutic"
            }
        meta_map[drg].update(info)
        
    return meta_map

def train_clinical_model():
    print("Loading real clinical datasets...")
    df = load_and_merge('clinical_datasets')
    
    if df.empty:
        print("Error: No clinical data found. Cannot train.")
        return
        
    print(f"Preprocessing for training... Dataset size: {df.shape}")
    
    # Features and Target
    X = df.drop(columns=['Disease'])
    y = df['Disease']
    
    X = X.fillna(0)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Clinical Disease & Recommendation Model (Random Forest)...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    accuracy = model.score(X_test, y_test)
    print(f"Model trained successfully. Test Accuracy: {accuracy * 100:.2f}%")
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    
    feature_columns = list(X.columns)
    joblib.dump(feature_columns, FEATURES_PATH)
    
    disease_to_drugs = build_disease_to_drugs_map()
    joblib.dump(disease_to_drugs, DISEASE_DRUGS_PATH)
    
    drugs_info_file = os.path.join(os.path.dirname(__file__), 'data', 'drugsInfo.csv')
    drug_meta = build_drug_metadata_map(drugs_info_file)
    joblib.dump(drug_meta, DRUG_META_PATH)
    
    print(f"Model, feature list, disease mappings, and drug metadata saved to {os.path.dirname(MODEL_PATH)}")

if __name__ == "__main__":
    train_clinical_model()
