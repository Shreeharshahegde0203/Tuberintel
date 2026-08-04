# TuberIntel mascot + mobile OTP authentication update

This patch adds:

- Tuber Mitra mascot on the authentication screen
- subtle CSS animation with reduced-motion support
- English and Kannada authentication content
- mobile-number login
- six separate OTP fields with paste, backspace and arrow-key support
- resend countdown and change-number flow
- demo authentication using OTP `123456`
- Supabase phone-auth configuration placeholders for production

## Apply to the existing project

From the project root—the folder that contains `frontend` and `backend`—extract the patch:

```bash
unzip -o ~/Downloads/tuberintel_auth_update.zip -d .
```

Then configure the frontend:

```bash
cd frontend
cp .env.example .env.local
nano .env.local
```

For local testing keep:

```env
VITE_AUTH_MODE=demo
```

Run:

```bash
npm install
npm run dev
```

Open `http://localhost:5173/login`.

Use any valid 10-digit Indian mobile number and the local OTP:

```text
123456
```

## Production OTP

Set the following in Vercel/frontend environment variables:

```env
VITE_AUTH_MODE=supabase
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_ANON_KEY
```

Phone authentication and an SMS provider must also be enabled in the Supabase dashboard. Never expose the Supabase service-role key in the frontend.
