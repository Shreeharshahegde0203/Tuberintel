# TuberIntel Google Compact Authentication v2

This patch supersedes both the earlier compact-login patch and the phone/SMS OTP patches.

## Included
- Compact single-screen green login UI
- Animated Tuber Mitra mascot
- Google sign-in through Supabase
- Protected routes and automatic redirect to `/login`
- Google user name and sign-out control in the application header
- English/Kannada login content
- No phone field, OTP boxes, Twilio, or hardcoded OTP

## Apply
From the project root containing `backend` and `frontend`:

```bash
unzip -o ~/Desktop/tuberintel_google_compact_auth_v2.zip -d .
cd frontend
npm install @supabase/supabase-js
npm run dev
```

Keep your existing `frontend/.env.local`. It should contain:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
VITE_MEDIA_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_SB_PUBLISHABLE_KEY
```
