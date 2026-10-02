from pydantic import BaseModel
from typing import List, Optional

class PrescribedDrug(BaseModel):
    drug_name: str
    dosage_details: str                          # e.g., "500 mg • Every 12 hours"
    duration: str                                # e.g., "5-7 Days"
    local_resistance_pct: Optional[str] = None   # e.g., "20% LOCAL RESISTANCE"

class VitalSigns(BaseModel):
    temperature_f: Optional[str] = None
    pulse_bpm: Optional[str] = None
    spo2_pct: Optional[str] = None
    respiratory_rate: Optional[str] = None
    blood_pressure: Optional[str] = None

class PatientReportPayload(BaseModel):
    patient_name: str
    age_gender: str                              # e.g., "20 Yrs / Male"
    case_reference: str                          # e.g., "CASE-95B9F813"
    registered_date: str
    physical_measurements: Optional[str] = None  # e.g., "170.0 cm • 70.0 kg"
    hospital_location: Optional[str] = None      # e.g., "Kolkata"
    
    primary_condition: str                       # e.g., "Heart attack"
    diagnosis_confidence: str                    # e.g., "90%"
    prescribed_antibiotics: List[PrescribedDrug] = []
    vitals: VitalSigns
    
    symptoms: List[str] = []
    comorbidities: List[str] = []
    allergies: List[str] = []
    previous_antibiotic_exposure: Optional[str] = None
    physician_notes: Optional[str] = None
    language: str = "en"                         # "en" | "hi" | "bn"
