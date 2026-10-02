import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://ggtiadergsqblwpemdhi.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdndGlhZGVyZ3NxYmx3cGVtZGhpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTk4MzAwMDAsImV4cCI6MjAzNTQwNjAwMH0.placeholder_anon_key';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
