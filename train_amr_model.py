import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from preprocess.merge_datasets import load_and_merge

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'amr_model.pkl')
ENCODER_PATH = os.path.join(os.path.dirname(__file__), 'models', 'amr_encoders.pkl')
SUMMARY_PATH = os.path.join(os.path.dirname(__file__), 'models', 'amr_summary.pkl')

def train_amr_model():
    print("Loading real AMR multiresistance & GLASS datasets...")
    df = load_and_merge('amr_datasets')
    
    if df.empty:
        print("No AMR data found. Cannot train.")
        return
        
    print(f"Preprocessing for training... Dataset shape: {df.shape}")
    
    # Clean and standardize string columns
    categorical_cols = ["Country", "State", "City", "Pathogen", "Antibiotic"]
    for col in categorical_cols:
        df[col] = df[col].astype(str).str.strip()
        
    # Save baseline summaries for quick lookup by location/pathogen/drug
    summary_data = {
        "cities": sorted(list(set(df["City"].unique()) - {"All", "Unknown", "nan"})),
        "states": sorted(list(set(df["State"].unique()) - {"All", "Unknown", "nan"})),
        "pathogens": sorted(list(set(df["Pathogen"].unique()) - {"All", "Unknown", "nan", "?"})),
        "antibiotics": sorted(list(set(df["Antibiotic"].unique()) - {"All", "Unknown", "nan", "?"})),
        "averages": df.groupby(["Pathogen", "Antibiotic"])["Resistance %"].mean().to_dict(),
        "city_averages": df.groupby(["City", "Antibiotic"])["Resistance %"].mean().to_dict()
    }
    
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        # Add a custom 'Unknown' class if not present
        vals = list(df[col].unique())
        if "Unknown" not in vals:
            vals.append("Unknown")
        le.fit(vals)
        df[col] = df[col].map(lambda x: x if x in le.classes_ else "Unknown")
        df[col] = le.transform(df[col])
        encoders[col] = le
        
    # Features and Target
    X = df.drop(columns=['Resistance %'])
    y = df['Resistance %']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42) if len(df) > 1 else (X, X, y, y)
    
    print("Training AMR Surveillance Model (Random Forest Regressor)...")
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    r2_score = model.score(X_test, y_test)
    print(f"AMR Model trained successfully. R^2 Score: {r2_score:.2f}")
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODER_PATH)
    joblib.dump(summary_data, SUMMARY_PATH)
    print(f"AMR Model, encoders, and summary saved to {os.path.dirname(MODEL_PATH)}")

if __name__ == "__main__":
    train_amr_model()
