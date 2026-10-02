-- Supabase Row Level Security (RLS) Policies for Medix AI
-- Note: These policies assume users are authenticated via Supabase Auth.
-- The user's ID in `auth.users` maps to `user_id` or `doctor_id` in our tables, or via the `profiles` table.

-- Enable RLS on all tables (if not already done)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hospitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patient_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drug_interaction_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resistance_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_logs ENABLE ROW LEVEL SECURITY;

-- 1. Profiles Table Policies
-- Users can read their own profile, and admins can read all profiles.
CREATE POLICY "Users can read own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- Allow authenticated users to insert their own profile during signup
CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- 2. Hospitals Table Policies
-- Anyone authenticated can view hospital details
CREATE POLICY "Authenticated users can read hospitals" ON public.hospitals
    FOR SELECT TO authenticated USING (true);

-- 3. Patients Table Policies
-- For simplicity, authenticated doctors can read all patient profiles, or restrict to hospital.
CREATE POLICY "Authenticated doctors can view patients" ON public.patients
    FOR SELECT TO authenticated USING (true);
    
CREATE POLICY "Authenticated doctors can insert patients" ON public.patients
    FOR INSERT TO authenticated WITH CHECK (true);

-- 4. Patient Cases Table Policies
-- Doctors can see cases they created
CREATE POLICY "Doctors can view own cases" ON public.patient_cases
    FOR SELECT TO authenticated USING (doctor_id = auth.uid());

CREATE POLICY "Doctors can insert own cases" ON public.patient_cases
    FOR INSERT TO authenticated WITH CHECK (doctor_id = auth.uid());

CREATE POLICY "Doctors can update own cases" ON public.patient_cases
    FOR UPDATE TO authenticated USING (doctor_id = auth.uid());

-- 5. AI Analysis Table Policies
-- Viewable if they can view the patient case
CREATE POLICY "Doctors can view AI analysis for their cases" ON public.ai_analysis
    FOR SELECT TO authenticated USING (
        EXISTS (SELECT 1 FROM public.patient_cases pc WHERE pc.id = patient_case_id AND pc.doctor_id = auth.uid())
    );

CREATE POLICY "Doctors can insert AI analysis for their cases" ON public.ai_analysis
    FOR INSERT TO authenticated WITH CHECK (true); -- Insert validation handled via API usually

-- 6. Prescriptions Table Policies
CREATE POLICY "Doctors can view and manage their prescriptions" ON public.prescriptions
    FOR ALL TO authenticated USING (doctor_id = auth.uid()) WITH CHECK (doctor_id = auth.uid());

-- 7. Drug Interaction Logs Table Policies
CREATE POLICY "Doctors can view and create their own interaction logs" ON public.drug_interaction_logs
    FOR ALL TO authenticated USING (doctor_id = auth.uid()) WITH CHECK (doctor_id = auth.uid());

-- 8. Resistance Logs Table Policies (Feedback)
CREATE POLICY "Authenticated users can insert resistance logs" ON public.resistance_logs
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Doctors can view resistance logs for their cases" ON public.resistance_logs
    FOR SELECT TO authenticated USING (
        EXISTS (SELECT 1 FROM public.patient_cases pc WHERE pc.id = patient_case_id AND pc.doctor_id = auth.uid())
    );

-- 9. Notifications Table Policies
CREATE POLICY "Users can manage their own notifications" ON public.notifications
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- 10. Settings Table Policies
CREATE POLICY "Authenticated users can read settings" ON public.settings
    FOR SELECT TO authenticated USING (true);

-- 11. Verification Logs Table Policies
CREATE POLICY "Doctors can view their own verification logs" ON public.verification_logs
    FOR SELECT TO authenticated USING (user_id = auth.uid());

CREATE POLICY "Users can insert verification logs" ON public.verification_logs
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
