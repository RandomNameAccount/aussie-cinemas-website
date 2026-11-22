# Switching on the Cinema Community forums

The forum pages are live but switched off until a Supabase project is connected. Allow about 15 minutes for steps 1–5, and more for step 6, which depends on the domain.

## 1. Create the project
1. Sign up at supabase.com (free plan).
2. **New project**: name `film-cinemas-australia`, region **Sydney (ap-southeast-2)**. Save the database password in your password manager.

## 2. Create the forum database
1. Open **SQL editor → New query**.
2. Paste the whole of `supabase/forum_schema.sql` from this repository and select **Run**. It is safe to run again.

## 3. Allow sign-in links back to the site
**Authentication → URL Configuration**
- Site URL: `https://randomnameaccount.github.io/aussie-cinemas-website/`
- Redirect URLs: add `https://randomnameaccount.github.io/aussie-cinemas-website/**` (later also `https://filmcinemas.au/**`).

## 4. Send Claude two values
**Project Settings → API**: the **Project URL** and the **anon / publishable key**. Both are designed to be public; the database's security rules protect the data. Never send the `service_role` / secret key or the database password.

These go into `assets/forum-config.js`, and the forums switch on.

## 5. Make yourself the first administrator
Sign in on the forums page with your email, create your profile, then run this in the SQL editor:

```sql
update public.profiles set role = 'admin'
where id = (select id from auth.users where email = 'YOUR EMAIL');
```

To add a moderator: `update public.profiles set role = 'moderator' where display_name = 'Their name';`

## 6. Before opening to the public: connect an email service
Supabase's built-in email only sends to people on your Supabase team, and only a couple of messages an hour. That is enough for testing, but members won't receive sign-in links until a custom SMTP service is connected:

**Authentication → Emails → SMTP settings**. Use a provider such as Brevo or Resend, and verify the sending domain (for example `filmcinemas.au`) with the DNS records the provider gives you.

## Before public launch (open decisions)
- Minimum age: the sign-up asks people to confirm they are 16 or over. Get legal advice on whether the forums count as an age-restricted social media platform, which would need stronger age checks.
- Add a real contact email to the community guidelines page.
- Choose the legal entity (decision D-19) and publish a full privacy policy.
