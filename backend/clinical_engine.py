import re
from typing import List, Dict, Set, Tuple, Optional, Any
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Comprehensive Medical Synonym & Clinical Term Normalization Dictionary
# Maps common patient / physician terms to the canonical 131 symptom features
# ALL 131 dataset feature IDs are covered here as direct self-mappings so that
# chip selections from /api/symptoms are never rejected.
# ─────────────────────────────────────────────────────────────────────────────
SYMPTOM_SYNONYM_MAP: Dict[str, List[str]] = {
    # ── Fever & Temperature ──────────────────────────────────────────────────
    "fever": ["high_fever", "mild_fever"],
    "pyrexia": ["high_fever", "mild_fever"],
    "high_fever": ["high_fever"],
    "mild_fever": ["mild_fever"],
    "temperature": ["high_fever", "mild_fever"],
    "high_temperature": ["high_fever", "mild_fever"],
    "febrile": ["high_fever", "mild_fever"],
    "low_grade_fever": ["mild_fever"],
    "chills": ["chills", "shivering"],
    "shivering": ["shivering", "chills"],
    "rigors": ["shivering", "chills"],
    "sweating": ["sweating"],
    "night_sweats": ["sweating"],
    "excessive_sweating": ["sweating"],
    "diaphoresis": ["sweating"],

    # ── Respiratory & ENT ────────────────────────────────────────────────────
    "cough": ["cough"],
    "coughing": ["cough"],
    "dry_cough": ["cough"],
    "wet_cough": ["cough", "phlegm"],
    "phlegm": ["phlegm", "mucoid_sputum"],
    "mucoid_sputum": ["mucoid_sputum"],
    "sputum": ["phlegm", "mucoid_sputum"],
    "blood_in_sputum": ["blood_in_sputum"],
    "hemoptysis": ["blood_in_sputum"],
    "coughing_blood": ["blood_in_sputum"],
    "rusty_sputum": ["rusty_sputum"],
    "breathlessness": ["breathlessness"],
    "shortness_of_breath": ["breathlessness"],
    "dyspnea": ["breathlessness"],
    "difficulty_breathing": ["breathlessness"],
    "wheezing": ["breathlessness", "cough"],
    "chest_pain": ["chest_pain"],
    "chest_tightness": ["chest_pain", "breathlessness"],
    "chest_pressure": ["chest_pain"],
    "chest_discomfort": ["chest_pain"],
    "congestion": ["congestion"],
    "chest_congestion": ["congestion", "phlegm"],
    "nasal_congestion": ["congestion"],
    "stuffy_nose": ["congestion"],
    "runny_nose": ["runny_nose"],
    "rhinorrhea": ["runny_nose"],
    "nasal_drip": ["runny_nose"],
    "cold": ["runny_nose", "congestion", "continuous_sneezing"],
    "common_cold": ["runny_nose", "congestion", "continuous_sneezing", "cough"],
    "sneezing": ["continuous_sneezing"],
    "continuous_sneezing": ["continuous_sneezing"],
    "sinus_pressure": ["sinus_pressure"],
    "sinusitis": ["sinus_pressure", "headache", "congestion"],
    "loss_of_smell": ["loss_of_smell"],
    "anosmia": ["loss_of_smell"],
    "no_smell": ["loss_of_smell"],
    "throat_irritation": ["throat_irritation"],
    "sore_throat": ["throat_irritation", "patches_in_throat"],
    "throat_pain": ["throat_irritation"],
    "pharyngitis": ["throat_irritation", "patches_in_throat"],
    "patches_in_throat": ["patches_in_throat"],
    "hoarseness": ["throat_irritation", "cough"],
    "loss_of_voice": ["throat_irritation"],
    "voice_changes": ["throat_irritation"],
    "stridor": ["breathlessness", "cough"],
    "dyspnea_on_exertion": ["breathlessness"],

    # ── Urinary & Renal ──────────────────────────────────────────────────────
    "burning_micturition": ["burning_micturition"],
    "dysuria": ["burning_micturition"],
    "burning_urination": ["burning_micturition"],
    "painful_urination": ["burning_micturition"],
    "bladder_discomfort": ["bladder_discomfort"],
    "suprapubic_pain": ["bladder_discomfort"],
    "pelvic_pain": ["bladder_discomfort"],
    "continuous_feel_of_urine": ["continuous_feel_of_urine"],
    "urinary_frequency": ["continuous_feel_of_urine"],
    "urinary_urgency": ["continuous_feel_of_urine"],
    "foul_smell_of_urine": ["foul_smell_of_urine"],
    "smelly_urine": ["foul_smell_of_urine"],
    "foul_smelling_urine": ["foul_smell_of_urine"],
    "dark_urine": ["dark_urine"],
    "cola_colored_urine": ["dark_urine"],
    "yellow_urine": ["yellow_urine"],
    "polyuria": ["polyuria", "continuous_feel_of_urine"],
    "frequent_urination": ["polyuria", "continuous_feel_of_urine"],
    "nocturia": ["polyuria", "continuous_feel_of_urine"],
    "urinating_at_night": ["polyuria", "continuous_feel_of_urine"],
    "spotting_urination": ["spotting__urination"],
    "spotting__urination": ["spotting__urination"],
    "uti": ["burning_micturition", "continuous_feel_of_urine", "bladder_discomfort"],
    "cystitis": ["burning_micturition", "continuous_feel_of_urine", "bladder_discomfort"],
    "blood_in_urine": ["burning_micturition", "bladder_discomfort", "spotting__urination"],
    "hematuria": ["burning_micturition", "bladder_discomfort", "spotting__urination"],
    "pink_urine": ["spotting__urination"],
    "flank_pain": ["back_pain", "burning_micturition"],
    "renal_colic": ["back_pain", "bladder_discomfort"],
    "kidney_pain": ["back_pain"],
    "loin_pain": ["back_pain"],

    # ── Gastrointestinal & Abdominal ─────────────────────────────────────────
    "abdominal_pain": ["abdominal_pain", "belly_pain", "stomach_pain"],
    "stomach_pain": ["stomach_pain", "abdominal_pain"],
    "belly_pain": ["belly_pain", "abdominal_pain"],
    "stomach_ache": ["stomach_pain", "abdominal_pain"],
    "epigastric_pain": ["stomach_pain", "acidity"],
    "acidity": ["acidity"],
    "heartburn": ["acidity", "chest_pain"],
    "acid_reflux": ["acidity", "cough"],
    "pyrosis": ["acidity"],
    "gerd": ["acidity", "cough", "chest_pain"],
    "indigestion": ["indigestion"],
    "dyspepsia": ["indigestion"],
    "vomiting": ["vomiting"],
    "nausea": ["nausea"],
    "emesis": ["vomiting"],
    "throwing_up": ["vomiting"],
    "retching": ["nausea", "vomiting"],
    "diarrhoea": ["diarrhoea"],
    "diarrhea": ["diarrhoea"],
    "loose_motions": ["diarrhoea"],
    "loose_stool": ["diarrhoea"],
    "watery_stool": ["diarrhoea", "dehydration"],
    "watery_diarrhea": ["diarrhoea", "dehydration"],
    "bloody_stool": ["bloody_stool"],
    "blood_in_stool": ["bloody_stool"],
    "melena": ["bloody_stool", "stomach_bleeding"],
    "rectal_bleeding": ["bloody_stool", "stomach_bleeding"],
    "constipation": ["constipation"],
    "no_bowel_movement": ["constipation"],
    "passage_of_gases": ["passage_of_gases"],
    "flatulence": ["passage_of_gases"],
    "bloating": ["distention_of_abdomen", "swelling_of_stomach"],
    "distention_of_abdomen": ["distention_of_abdomen"],
    "abdominal_distension": ["distention_of_abdomen"],
    "swelling_of_stomach": ["swelling_of_stomach"],
    "ascites": ["distention_of_abdomen", "swelling_of_stomach"],
    "sunken_eyes": ["sunken_eyes", "dehydration"],
    "dehydration": ["dehydration"],
    "loss_of_appetite": ["loss_of_appetite"],
    "anorexia": ["loss_of_appetite"],
    "no_appetite": ["loss_of_appetite"],
    "poor_appetite": ["loss_of_appetite"],
    "ulcers_on_tongue": ["ulcers_on_tongue"],
    "mouth_ulcers": ["ulcers_on_tongue"],
    "aphthous_ulcers": ["ulcers_on_tongue"],
    "stomach_bleeding": ["stomach_bleeding"],
    "internal_itching": ["internal_itching"],
    "pain_during_bowel_movements": ["pain_during_bowel_movements"],
    "pain_in_anal_region": ["pain_in_anal_region"],
    "irritation_in_anus": ["irritation_in_anus"],
    "rectal_pain": ["pain_in_anal_region", "irritation_in_anus"],
    "anal_pain": ["pain_in_anal_region"],
    "piles": ["pain_in_anal_region", "irritation_in_anus"],
    "hemorrhoids": ["pain_in_anal_region", "irritation_in_anus"],
    "tenesmus": ["diarrhoea", "pain_in_anal_region"],
    "dysphagia": ["throat_irritation", "acidity"],
    "difficulty_swallowing": ["throat_irritation", "acidity"],
    "painful_swallowing": ["throat_irritation", "patches_in_throat"],
    "odynophagia": ["throat_irritation", "patches_in_throat"],
    "hematemesis": ["vomiting", "stomach_bleeding"],
    "vomiting_blood": ["vomiting", "stomach_bleeding"],
    "acute_liver_failure": ["acute_liver_failure"],
    "liver_failure": ["acute_liver_failure", "yellowish_skin", "yellowing_of_eyes"],
    "fluid_overload": ["fluid_overload"],
    "edema": ["fluid_overload", "swollen_legs"],
    "water_retention": ["fluid_overload"],
    "history_of_alcohol_consumption": ["history_of_alcohol_consumption"],
    "alcohol_use": ["history_of_alcohol_consumption"],
    "alcoholism": ["history_of_alcohol_consumption"],
    "alcohol_abuse": ["history_of_alcohol_consumption"],
    "receiving_blood_transfusion": ["receiving_blood_transfusion"],
    "blood_transfusion": ["receiving_blood_transfusion"],
    "receiving_unsterile_injections": ["receiving_unsterile_injections"],
    "iv_drug_use": ["receiving_unsterile_injections"],

    # ── Dermatology & Skin ───────────────────────────────────────────────────
    "itching": ["itching"],
    "pruritus": ["itching"],
    "skin_rash": ["skin_rash"],
    "rash": ["skin_rash"],
    "rashes": ["skin_rash"],
    "exanthem": ["skin_rash"],
    "blister": ["blister"],
    "blisters": ["blister"],
    "vesicles": ["blister"],
    "red_spots_over_body": ["red_spots_over_body"],
    "red_spots": ["red_spots_over_body"],
    "petechiae": ["red_spots_over_body"],
    "purpura": ["red_spots_over_body"],
    "nodal_skin_eruptions": ["nodal_skin_eruptions"],
    "skin_nodules": ["nodal_skin_eruptions"],
    "pus_filled_pimples": ["pus_filled_pimples"],
    "pustules": ["pus_filled_pimples"],
    "pimples": ["pus_filled_pimples", "blackheads"],
    "acne": ["pus_filled_pimples", "blackheads", "skin_rash"],
    "blackheads": ["blackheads"],
    "comedones": ["blackheads"],
    "skin_peeling": ["skin_peeling"],
    "peeling_skin": ["skin_peeling"],
    "desquamation": ["skin_peeling"],
    "silver_like_dusting": ["silver_like_dusting"],
    "scurring": ["scurring"],
    "yellow_crust_ooze": ["yellow_crust_ooze"],
    "dischromic_patches": ["dischromic__patches"],
    "dischromic__patches": ["dischromic__patches"],
    "skin_discoloration": ["dischromic__patches"],
    "hypopigmentation": ["dischromic__patches"],
    "red_sore_around_nose": ["red_sore_around_nose"],
    "bruising": ["bruising"],
    "easy_bruising": ["bruising"],
    "ecchymosis": ["bruising"],
    "urticaria": ["skin_rash", "itching"],
    "hives": ["skin_rash", "itching"],
    "alopecia": ["brittle_nails", "skin_rash"],
    "hair_loss": ["brittle_nails"],
    "brittle_nails": ["brittle_nails"],
    "inflammatory_nails": ["inflammatory_nails"],
    "nail_inflammation": ["inflammatory_nails"],
    "small_dents_in_nails": ["small_dents_in_nails"],
    "nail_pitting": ["small_dents_in_nails"],

    # ── Musculoskeletal & Joint ──────────────────────────────────────────────
    "joint_pain": ["joint_pain"],
    "arthralgia": ["joint_pain"],
    "arthritis": ["joint_pain", "swelling_joints", "movement_stiffness"],
    "swelling_joints": ["swelling_joints"],
    "swollen_joints": ["swelling_joints"],
    "joint_swelling": ["swelling_joints"],
    "knee_pain": ["knee_pain"],
    "hip_joint_pain": ["hip_joint_pain"],
    "hip_pain": ["hip_joint_pain"],
    "back_pain": ["back_pain"],
    "lower_back_pain": ["back_pain"],
    "lumbar_pain": ["back_pain"],
    "neck_pain": ["neck_pain"],
    "cervicalgia": ["neck_pain"],
    "stiff_neck": ["stiff_neck"],
    "neck_stiffness": ["stiff_neck"],
    "movement_stiffness": ["movement_stiffness"],
    "morning_stiffness": ["movement_stiffness", "joint_pain"],
    "joint_stiffness": ["movement_stiffness", "joint_pain"],
    "painful_walking": ["painful_walking"],
    "limping": ["painful_walking"],
    "difficulty_walking": ["painful_walking"],
    "muscle_pain": ["muscle_pain"],
    "myalgia": ["muscle_pain"],
    "body_pain": ["muscle_pain", "joint_pain"],
    "muscle_weakness": ["muscle_weakness"],
    "myasthenia": ["muscle_weakness"],
    "cramps": ["cramps"],
    "muscle_cramps": ["cramps"],
    "leg_cramps": ["cramps"],
    "muscle_wasting": ["muscle_wasting"],
    "muscle_atrophy": ["muscle_wasting"],
    "obesity": ["obesity"],
    "overweight": ["obesity"],
    "prominent_veins_on_calf": ["prominent_veins_on_calf"],
    "varicose_veins": ["prominent_veins_on_calf", "swollen_blood_vessels"],
    "swollen_blood_vessels": ["swollen_blood_vessels"],
    "swollen_legs": ["swollen_legs"],
    "leg_swelling": ["swollen_legs"],
    "pedal_edema": ["swollen_legs"],
    "swollen_extremeties": ["swollen_extremeties"],
    "swollen_extremities": ["swollen_extremeties"],
    "limb_swelling": ["swollen_extremeties"],

    # ── Neurological & Systemic ──────────────────────────────────────────────
    "headache": ["headache"],
    "migraine": ["headache", "blurred_and_distorted_vision", "acidity"],
    "head_pain": ["headache"],
    "throbbing_headache": ["headache"],
    "dizziness": ["dizziness"],
    "lightheaded": ["dizziness"],
    "giddiness": ["dizziness"],
    "loss_of_balance": ["loss_of_balance"],
    "balance_problems": ["loss_of_balance"],
    "unsteadiness": ["unsteadiness"],
    "unsteady": ["unsteadiness"],
    "spinning_movements": ["spinning_movements"],
    "room_spinning": ["spinning_movements"],
    "vertigo": ["spinning_movements", "unsteadiness", "loss_of_balance"],
    "altered_sensorium": ["altered_sensorium"],
    "confusion": ["altered_sensorium", "lack_of_concentration"],
    "disorientation": ["altered_sensorium"],
    "delirium": ["altered_sensorium"],
    "lack_of_concentration": ["lack_of_concentration"],
    "difficulty_concentrating": ["lack_of_concentration"],
    "poor_concentration": ["lack_of_concentration"],
    "visual_disturbances": ["visual_disturbances"],
    "blurred_and_distorted_vision": ["blurred_and_distorted_vision"],
    "blurred_vision": ["blurred_and_distorted_vision", "visual_disturbances"],
    "double_vision": ["blurred_and_distorted_vision"],
    "diplopia": ["blurred_and_distorted_vision"],
    "photophobia": ["visual_disturbances", "blurred_and_distorted_vision"],
    "light_sensitivity": ["visual_disturbances"],
    "pain_behind_the_eyes": ["pain_behind_the_eyes"],
    "retro_orbital_pain": ["pain_behind_the_eyes"],
    "eye_pain": ["pain_behind_the_eyes", "redness_of_eyes"],
    "redness_of_eyes": ["redness_of_eyes"],
    "red_eyes": ["redness_of_eyes"],
    "conjunctivitis": ["redness_of_eyes", "watering_from_eyes"],
    "pink_eye": ["redness_of_eyes", "watering_from_eyes"],
    "watering_from_eyes": ["watering_from_eyes"],
    "eye_discharge": ["redness_of_eyes", "watering_from_eyes"],
    "purulent_eye_discharge": ["redness_of_eyes", "watering_from_eyes"],
    "yellowing_of_eyes": ["yellowing_of_eyes"],
    "icteric_sclera": ["yellowing_of_eyes"],
    "yellow_eyes": ["yellowing_of_eyes"],
    "scleral_icterus": ["yellowing_of_eyes", "yellowish_skin"],
    "yellowish_skin": ["yellowish_skin"],
    "jaundice": ["yellowish_skin", "yellowing_of_eyes", "dark_urine"],
    "yellow_skin": ["yellowish_skin"],
    "icterus": ["yellowish_skin", "yellowing_of_eyes"],
    "fatigue": ["fatigue"],
    "tiredness": ["fatigue", "lethargy"],
    "lethargy": ["lethargy", "fatigue"],
    "malaise": ["malaise", "fatigue"],
    "weakness": ["fatigue", "muscle_weakness"],
    "exhaustion": ["fatigue"],
    "weakness_in_limbs": ["weakness_in_limbs"],
    "weak_limbs": ["weakness_in_limbs"],
    "weakness_of_one_body_side": ["weakness_of_one_body_side"],
    "one_sided_weakness": ["weakness_of_one_body_side"],
    "hemiparesis": ["weakness_of_one_body_side"],
    "hemiplegia": ["weakness_of_one_body_side"],
    "stroke_symptoms": ["weakness_of_one_body_side", "altered_sensorium"],
    "numbness": ["weakness_in_limbs"],
    "tingling": ["weakness_in_limbs"],
    "paresthesia": ["weakness_in_limbs"],
    "neuropathy": ["weakness_in_limbs"],
    "palpitations": ["palpitations", "fast_heart_rate"],
    "heart_pounding": ["palpitations", "fast_heart_rate"],
    "fast_heart_rate": ["fast_heart_rate", "palpitations"],
    "tachycardia": ["fast_heart_rate"],
    "rapid_heartbeat": ["fast_heart_rate"],
    "irregular_heartbeat": ["palpitations", "fast_heart_rate"],
    "swelled_lymph_nodes": ["swelled_lymph_nodes"],
    "swollen_lymph_nodes": ["swelled_lymph_nodes"],
    "lymphadenopathy": ["swelled_lymph_nodes"],
    "swollen_glands": ["swelled_lymph_nodes"],
    "weight_loss": ["weight_loss"],
    "losing_weight": ["weight_loss"],
    "unexplained_weight_loss": ["weight_loss"],
    "weight_gain": ["weight_gain"],
    "gaining_weight": ["weight_gain"],
    "excessive_hunger": ["excessive_hunger"],
    "polyphagia": ["excessive_hunger"],
    "always_hungry": ["excessive_hunger"],
    "increased_appetite": ["increased_appetite"],
    "hyperphagia": ["increased_appetite"],
    "anxiety": ["anxiety"],
    "anxious": ["anxiety"],
    "panic_attack": ["anxiety"],
    "panic": ["anxiety"],
    "restlessness": ["restlessness"],
    "agitation": ["restlessness"],
    "mood_swings": ["mood_swings"],
    "emotional_instability": ["mood_swings"],
    "irritability": ["irritability"],
    "irritable": ["irritability"],
    "short_tempered": ["irritability"],
    "depression": ["depression"],
    "depressed": ["depression"],
    "low_mood": ["depression"],
    "sadness": ["depression"],
    "syncope": ["dizziness", "loss_of_balance"],
    "fainting": ["dizziness", "loss_of_balance"],
    "blackout": ["altered_sensorium", "dizziness"],
    "loss_of_consciousness": ["altered_sensorium"],
    "unconscious": ["altered_sensorium"],
    "coma": ["altered_sensorium"],
    "tremor": ["shivering"],
    "shaking": ["shivering"],
    "trembling": ["shivering"],
    "tinnitus": ["spinning_movements", "unsteadiness"],
    "ringing_in_ears": ["spinning_movements"],
    "hearing_loss": ["loss_of_balance"],
    "earache": ["headache", "mild_fever"],
    "ear_pain": ["headache", "mild_fever"],
    "otalgia": ["headache", "mild_fever"],
    "ear_discharge": ["itching"],
    "nosebleed": ["headache"],
    "epistaxis": ["headache"],

    # ── Endocrine / Metabolic ────────────────────────────────────────────────
    "enlarged_thyroid": ["enlarged_thyroid"],
    "goiter": ["enlarged_thyroid"],
    "thyroid_swelling": ["enlarged_thyroid"],
    "neck_swelling": ["enlarged_thyroid", "swelled_lymph_nodes"],
    "irregular_sugar_level": ["irregular_sugar_level"],
    "blood_sugar_fluctuation": ["irregular_sugar_level"],
    "high_blood_sugar": ["irregular_sugar_level", "polyuria"],
    "hyperglycemia": ["irregular_sugar_level", "polyuria"],
    "low_blood_sugar": ["irregular_sugar_level", "excessive_hunger"],
    "hypoglycemia": ["irregular_sugar_level", "excessive_hunger"],
    "sugar_fluctuation": ["irregular_sugar_level"],
    "drying_and_tingling_lips": ["drying_and_tingling_lips"],
    "tingling_lips": ["drying_and_tingling_lips"],
    "lip_tingling": ["drying_and_tingling_lips"],
    "dry_lips": ["drying_and_tingling_lips"],
    "slurred_speech": ["slurred_speech"],
    "speech_difficulty": ["slurred_speech"],
    "dysarthria": ["slurred_speech"],
    "slurring": ["slurred_speech"],
    "cold_hands_and_feets": ["cold_hands_and_feets"],
    "cold_extremities": ["cold_hands_and_feets"],
    "cold_hands": ["cold_hands_and_feets"],
    "cold_feet": ["cold_hands_and_feets"],
    "raynaud": ["cold_hands_and_feets"],
    "puffy_face_and_eyes": ["puffy_face_and_eyes"],
    "puffy_face": ["puffy_face_and_eyes"],
    "facial_swelling": ["puffy_face_and_eyes"],
    "periorbital_edema": ["puffy_face_and_eyes"],
    "moon_face": ["puffy_face_and_eyes"],
    "abnormal_menstruation": ["abnormal_menstruation"],
    "irregular_periods": ["abnormal_menstruation"],
    "menstrual_irregularity": ["abnormal_menstruation"],
    "amenorrhea": ["abnormal_menstruation"],
    "menorrhagia": ["abnormal_menstruation"],
    "dysmenorrhea": ["abnormal_menstruation", "pain_during_bowel_movements"],

    # ── Epidemiological / Social History ────────────────────────────────────
    "family_history": ["family_history"],
    "hereditary": ["family_history"],
    "genetic_predisposition": ["family_history"],
    "extra_marital_contacts": ["extra_marital_contacts"],
    "unprotected_sex": ["extra_marital_contacts"],
    "sexual_risk": ["extra_marital_contacts"],
    "toxic_look_(typhos)": ["toxic_look_(typhos)"],
    "toxic_appearance": ["toxic_look_(typhos)"],
    "typhoid_look": ["toxic_look_(typhos)"],
}

# ─────────────────────────────────────────────────────────────────────────────
# STRICT MEDICAL VOCABULARY GUARD
# Words/phrases that are NOT valid clinical symptoms by themselves.
# If ALL words in a user input consist of these terms, the input is rejected.
# ─────────────────────────────────────────────────────────────────────────────
_NON_SYMPTOM_WORDS = frozenset({
    # non-specific vague terms
    "bad", "good", "fine", "well", "sick", "ill", "unwell",
    "ache", "pain", "sore", "feel", "feeling", "felt",
    "have", "had", "problem", "issue", "trouble",
    "bad", "terrible", "awful", "horrible", "ok", "okay",
    "very", "really", "quite", "too", "bit", "little", "lots",
    "from", "have", "got", "since", "not",
    # objects / things
    "car", "bus", "bike", "phone", "mobile", "laptop", "computer", "device",
    "food", "water", "drink", "coffee", "tea", "milk", "juice",
    "apple", "banana", "mango", "pizza", "rice", "bread", "chips",
    "cat", "dog", "bird", "fish", "animal",
    # filler / non-clinical
    "something", "anything", "nothing", "everything",
    "much", "many", "body", "whole", "general", "overall",
    "sometimes", "often", "always", "never",
    "yesterday", "today", "morning", "night", "week", "days", "months",
    "xyz", "abc", "test", "testing", "random", "stuff",
    # Stop words
    "and", "the", "a", "an", "is", "am", "are", "was", "were", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "would", "should", 
    "could", "ought", "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", 
    "her", "its", "our", "their", "this", "that", "these", "those", "of", "to", "in", 
    "for", "with", "on", "at", "from", "by", "about", "as", "into", "like", "through", 
    "after", "over", "between", "out", "against", "during", "without", "before", "under", 
    "around", "among", "very", "much", "really", "so", "too", "quite", "rather", "somewhat", 
    "just", "only", "also", "even", "more", "most", "some", "any", "no", "not", "all", 
    "both", "half", "either", "neither", "each", "every", "other", "another", "such", 
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how", "since", "got"
})


# ─────────────────────────────────────────────────────────────────────────────
# Distinctive Pathognomonic & Hallmark Symptoms
# These define crucial clinical indicators that rule-in or rule-out specific
# differential diagnoses
# ─────────────────────────────────────────────────────────────────────────────
DISEASE_HALLMARKS: Dict[str, Set[str]] = {
    "Pneumonia": {"breathlessness", "chest_pain", "cough", "high_fever", "phlegm", "rusty_sputum"},
    "Tuberculosis": {"blood_in_sputum", "weight_loss", "swelled_lymph_nodes", "chills", "sweating"},
    "Urinary tract infection": {"burning_micturition", "bladder_discomfort", "continuous_feel_of_urine", "foul_smell_of_urine"},
    "Typhoid": {"toxic_look_(typhos)", "belly_pain", "constipation", "high_fever", "headache"},
    "Gastroenteritis": {"dehydration", "sunken_eyes", "diarrhoea", "vomiting"},
    "Bronchial Asthma": {"breathlessness", "cough", "mucoid_sputum", "family_history"},
    "Common Cold": {"throat_irritation", "runny_nose", "continuous_sneezing", "loss_of_smell", "sinus_pressure", "redness_of_eyes"},
    "Dengue": {"pain_behind_the_eyes", "red_spots_over_body", "joint_pain", "back_pain", "high_fever"},
    "Malaria": {"muscle_pain", "chills", "sweating", "high_fever", "headache"},
    "Fungal infection": {"dischromic__patches", "nodal_skin_eruptions", "itching", "skin_rash"},
    "Impetigo": {"blister", "red_sore_around_nose", "yellow_crust_ooze", "skin_rash"},
    "Acne": {"blackheads", "pus_filled_pimples", "scurring", "skin_rash"},
    "GERD": {"acidity", "ulcers_on_tongue", "stomach_pain", "chest_pain"},
    "Peptic ulcer disease": {"passage_of_gases", "internal_itching", "indigestion", "abdominal_pain"},
    "Heart attack": {"sweating", "chest_pain", "breathlessness", "vomiting"},
    "Jaundice": {"yellowish_skin", "yellowing_of_eyes", "dark_urine", "abdominal_pain"},
    "Chronic cholestasis": {"itching", "yellowing_of_eyes", "yellowish_skin", "abdominal_pain"},
    "Migraine": {"visual_disturbances", "stiff_neck", "depression", "blurred_and_distorted_vision", "headache"},
    "Allergy": {"continuous_sneezing", "shivering", "watering_from_eyes", "chills"},
    "Chicken pox": {"red_spots_over_body", "mild_fever", "swelled_lymph_nodes", "skin_rash", "itching"},
    "Arthritis": {"movement_stiffness", "painful_walking", "stiff_neck", "swelling_joints", "muscle_weakness"},
    "Osteoarthritis": {"hip_joint_pain", "knee_pain", "neck_pain", "painful_walking", "swelling_joints"},
    "Cervical spondylosis": {"weakness_in_limbs", "neck_pain", "back_pain", "dizziness", "loss_of_balance"},
    "Paralysis (brain hemorrhage)": {"altered_sensorium", "weakness_of_one_body_side", "headache", "vomiting"},
    "Diabetes": {"irregular_sugar_level", "excessive_hunger", "polyuria", "increased_appetite", "blurred_and_distorted_vision"},
    "Hypertension": {"lack_of_concentration", "loss_of_balance", "dizziness", "headache", "chest_pain"},
    "Hyperthyroidism": {"enlarged_thyroid", "excessive_hunger", "fast_heart_rate", "abnormal_menstruation", "weight_loss"},
    "Hypothyroidism": {"cold_hands_and_feets", "brittle_nails", "puffy_face_and_eyes", "swollen_extremeties", "weight_gain"},
    "Hypoglycemia": {"drying_and_tingling_lips", "slurred_speech", "palpitations", "anxiety", "excessive_hunger"},
    "Psoriasis": {"silver_like_dusting", "small_dents_in_nails", "inflammatory_nails", "skin_peeling"},
    "Varicose veins": {"prominent_veins_on_calf", "swollen_blood_vessels", "swollen_legs", "cramps"},
    "Paroxysmal Positional Vertigo": {"spinning_movements", "unsteadiness", "loss_of_balance", "nausea", "headache"}
}


def normalize_input_symptoms(raw_symptoms: List[str]) -> Tuple[Set[str], List[str], Set[str], List[str]]:
    """
    Expands user-entered raw symptoms into:
      - internal_tokens: Set of canonical column tokens in the 131 dataset features
      - recognized_labels: Clean human-readable list of matching symptom terms
      - external_symptoms: Set of clinically verified external symptoms not in the 131 features
      - rejected_tokens: List of unrecognized non-medical inputs (e.g. 'car', 'banana')

    Strict rules:
      1. Direct match against SYMPTOM_SYNONYM_MAP (comprehensive, covers all 131 features)
      2. Direct match against EXTERNAL_SYMPTOM_ONTOLOGY (external verified conditions)
      3. Fuzzy whole-word multi-word matching (strict, avoids substring false positives)
      4. Single-token inputs that consist ONLY of _NON_SYMPTOM_WORDS are rejected
    """
    try:
        from services.external_clinical_kb import EXTERNAL_SYMPTOM_ONTOLOGY
    except Exception:
        EXTERNAL_SYMPTOM_ONTOLOGY = {}

    internal_tokens: Set[str] = set()
    recognized_labels: List[str] = []
    external_symptoms: Set[str] = set()
    rejected_tokens: List[str] = []

    for sym in raw_symptoms:
        if not sym or not str(sym).strip():
            continue
        clean = str(sym).strip().lower().replace(' ', '_').replace('-', '_')
        # Extract individual alpha words for word-level analysis
        clean_words = set(re.findall(r'[a-z]+', clean))

        # ── Guard: purely non-symptom words? ──────────────────────────────
        # If EVERY word in the input is a known non-medical term, reject immediately
        if clean_words and clean_words.issubset(_NON_SYMPTOM_WORDS):
            rejected_tokens.append(clean.replace('_', ' ').title())
            continue

        # ── Step 1: Direct match in internal SYMPTOM_SYNONYM_MAP ──────────
        if clean in SYMPTOM_SYNONYM_MAP:
            tokens = SYMPTOM_SYNONYM_MAP[clean]
            internal_tokens.update(tokens)
            recognized_labels.append(clean.replace('_', ' ').title())
            continue

        # ── Step 2: Direct match in External Symptom Ontology ─────────────
        if clean in EXTERNAL_SYMPTOM_ONTOLOGY:
            external_symptoms.add(clean)
            ext_meta = EXTERNAL_SYMPTOM_ONTOLOGY[clean]
            recognized_labels.append(ext_meta.get("canonical_name", clean.replace('_', ' ').title()))
            if "related_internal" in ext_meta:
                internal_tokens.update(ext_meta["related_internal"])
            continue

        # ── Step 3: Fuzzy whole-word multi-word boundary matching ──────────
        # Checks external ontology first, then internal synonym map.
        # Rules: must use WHOLE words (not substrings), min 4 chars for substring check.
        matched = False
        matched_words = set()

        # Check external ontology fuzzy
        for ext_key, ext_meta in EXTERNAL_SYMPTOM_ONTOLOGY.items():
            ext_words = set(re.findall(r'[a-z]+', ext_key))
            # Match only if all words of the key are present in the input (whole-word)
            if ext_words and len(ext_words) >= 1 and ext_words.issubset(clean_words) and len(ext_words) >= 2:
                external_symptoms.add(ext_key)
                recognized_labels.append(ext_meta.get("canonical_name", ext_key.replace('_', ' ').title()))
                if "related_internal" in ext_meta:
                    internal_tokens.update(ext_meta["related_internal"])
                matched = True
                matched_words = ext_words
                break

        if not matched:
            # Check internal synonym map fuzzy (require multi-word match OR long single-word)
            for syn_key, target_tokens in SYMPTOM_SYNONYM_MAP.items():
                syn_words = set(re.findall(r'[a-z]+', syn_key))
                # Multi-word key: all words must appear in input
                if syn_words and len(syn_words) >= 2 and syn_words.issubset(clean_words):
                    internal_tokens.update(target_tokens)
                    recognized_labels.append(syn_key.replace('_', ' ').title())
                    matched = True
                    matched_words = syn_words
                    break
                # Single-word key: must be an exact word in the input (not substring) AND >= 6 chars
                if syn_words and len(syn_words) == 1:
                    single_word = next(iter(syn_words))
                    if single_word in clean_words and len(single_word) >= 6:
                        internal_tokens.update(target_tokens)
                        recognized_labels.append(syn_key.replace('_', ' ').title())
                        matched = True
                        matched_words = syn_words
                        break

        # Identify non-medical junk
        if matched:
            unrecognized_junk = clean_words - (matched_words | _NON_SYMPTOM_WORDS)
            if unrecognized_junk:
                # Add the unrecognized parts to rejected tokens, but don't reject the valid symptom we found!
                rejected_tokens.append(" ".join(unrecognized_junk).title())

        if not matched:
            # Term did not match any verified clinical symptom or synonym
            rejected_tokens.append(clean.replace('_', ' ').title())

    return internal_tokens, list(dict.fromkeys(recognized_labels)), external_symptoms, rejected_tokens


def clinical_bayesian_rank(
    normalized_symptoms: Set[str],
    disease_symptoms_kb: Dict[str, Set[str]],
    ml_probabilities: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Combines Evidence-Based Clinical Jaccard Matching, Hallmark Pattern Scoring,
    and Machine Learning model posteriors using a weighted ensemble architecture.
    """
    if not normalized_symptoms:
        return []

    ranked_results = []
    ml_probs = ml_probabilities or {}

    for disease, proto_syms in disease_symptoms_kb.items():
        matched = proto_syms & normalized_symptoms
        if not matched:
            continue

        matched_count = len(matched)
        input_count = len(normalized_symptoms)
        proto_count = len(proto_syms)

        # Sensitivity / Recall: percentage of user's symptoms explained by this disease
        recall = matched_count / input_count if input_count > 0 else 0.0

        # Specificity / Precision: percentage of disease prototype symptoms present
        precision = matched_count / proto_count if proto_count > 0 else 0.0

        # F1 score for balanced overlap
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Hallmark clinical alignment
        hallmarks = DISEASE_HALLMARKS.get(disease, set())
        matched_hallmarks = hallmarks & normalized_symptoms
        hallmark_bonus = len(matched_hallmarks) * 12.0

        # Negative penalty for diseases where distinctive hallmarks are completely absent
        missing_hallmark_penalty = 0.0
        if hallmarks and not matched_hallmarks and matched_count < 3:
            missing_hallmark_penalty = 8.0

        # Base clinical score
        clinical_evidence_score = (
            (matched_count * 15.0) +
            (recall * 35.0) +
            (f1 * 25.0) +
            hallmark_bonus -
            missing_hallmark_penalty
        )

        # ML model probability integration
        ml_prob = ml_probs.get(disease, 0.0)
        # Weighted hybrid: 75% Clinical Jaccard/Hallmark evidence + 25% Random Forest probability
        ensemble_score = (0.75 * clinical_evidence_score) + (0.25 * (ml_prob * 100.0))

        ranked_results.append({
            "disease": disease,
            "score": ensemble_score,
            "matchedSymptoms": sorted(list(matched)),
            "matchedCount": matched_count,
            "recall": round(recall * 100, 1),
            "precision": round(precision * 100, 1),
            "mlProb": ml_prob
        })

    # Sort descending by ensemble score
    ranked_results.sort(key=lambda x: x["score"], reverse=True)

    # Compute calibrated posterior confidence percentage
    if ranked_results:
        top_score = ranked_results[0]["score"]
        if ranked_results[0]["matchedCount"] >= 3:
            calibrated_conf = min(98.0, max(88.0, 75.0 + (ranked_results[0]["recall"] * 0.23)))
        elif ranked_results[0]["matchedCount"] == 2:
            calibrated_conf = min(92.0, max(82.0, 70.0 + (ranked_results[0]["recall"] * 0.20)))
        else:
            calibrated_conf = min(85.0, max(75.0, 65.0 + (ranked_results[0]["recall"] * 0.15)))

        ranked_results[0]["confidencePct"] = round(calibrated_conf)

        for i in range(1, len(ranked_results)):
            rel_ratio = ranked_results[i]["score"] / top_score if top_score > 0 else 0.5
            ranked_results[i]["confidencePct"] = round(max(20.0, calibrated_conf * rel_ratio * 0.85))

    return ranked_results
