import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Guard: give a readable error instead of a silent white screen
if (!supabaseUrl || !supabaseAnonKey || supabaseAnonKey === 'REPLACE_WITH_YOUR_SUPABASE_ANON_KEY') {
  throw new Error(
    '[config/supabase] Missing env vars. ' +
    'Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env ' +
    '(get the anon key from Supabase Dashboard → Project → Settings → API).'
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
