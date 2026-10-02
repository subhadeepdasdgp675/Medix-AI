import json
import os
import importlib
import pandas as pd

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_and_merge(dataset_type: str) -> pd.DataFrame:
    """
    Reads config.json, processes all active datasets of the given type
    ('clinical_datasets' or 'amr_datasets'), and merges them.
    """
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        
    datasets = config.get(dataset_type, [])
    merged_df = pd.DataFrame()
    
    for ds in datasets:
        if not ds.get("active", False):
            continue
            
        filepath = os.path.join(os.path.dirname(__file__), '..', ds['file'])
        script_module = ds['preprocess_script']
        
        try:
            # Dynamically import the preprocessing script
            module = importlib.import_module(script_module)
            if hasattr(module, 'process'):
                df = module.process(filepath)
                if not df.empty:
                    merged_df = pd.concat([merged_df, df], ignore_index=True)
                    print(f"Successfully loaded and merged {ds['name']}")
        except Exception as e:
            print(f"Failed to process dataset {ds['name']}: {e}")
            
    return merged_df
