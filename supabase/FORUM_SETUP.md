# Switching on Cinema Community: member accounts, forums and (later) advertising

The site's address is **https://filmcinemas.au**. Member accounts and forums are built but switched off until a Supabase project is connected. Advertising is built too and stays switched off until an administrator turns it on.

Set every account up **in Tony's name** (or a shared Film Cinemas Australia email address Tony controls), so nothing has to be moved later. Turn on two-step sign-in for each one.

Order: **A** domain → **B** Supabase → **C** email → **D** first administrator. Allow about an hour, plus waiting time for DNS.

---

## A. Point filmcinemas.au at the website

1. **GitHub:** repository → **Settings → Pages → Custom domain**, enter `filmcinemas.au`, then **Save**.
2. **Domain registrar** (wherever Tony bought filmcinemas.au) → DNS settings for the domain. Add:

   | Type | Host / name | Value |
   | --- | --- | --- |
   | A | `@` (blank) | `185.199.108.153` |
   | A | `@` (blank) | `185.199.109.153` |
   | A | `@` (blank) | `185.199.110.153` |
   | A | `@` (blank) | `185.199.111.153` |
   | CNAME | `www` | `randomnameaccount.github.io` |

   Delete any older A record or "parked page" record for `@`.
3. Wait until GitHub's Pages screen shows the DNS check as passing (minutes to a few hours), then tick **Enforce HTTPS**.

Once that's done, the old github.io address redirects to filmcinemas.au automatically, and it will keep doing so after the repository moves to Tony's account.

## B. Create the Supabase project (database and member sign-in)

1. Go to **supabase.com → Start your project**, sign up with Tony's email (free plan).
2. **New project:** name `film-cinemas-australia`, region **Sydney (ap-southeast-2)**. Generate a database password and save it in a password manager. Nobody else needs it, including Claude.
3. Wait for the project to finish setting up (a couple of minutes).
4. **SQL Editor → New query.** Paste the whole of [`supabase/forum_schema.sql`](forum_schema.sql) and select **Run**. You should see "Success. No rows returned". It is safe to run again.
5. **Authentication → URL Configuration:**
   - **Site URL:** `https://filmcinemas.au`
   - **Redirect URLs → Add URL:** `https://filmcinemas.au/**`, `https://www.filmcinemas.au/**` and `https://randomnameaccount.github.io/aussie-cinemas-website/**` (keep the last one until the domain is live).
6. **Project Settings → API** (also shown under **Connect**): copy the **Project URL** and the **anon / publishable key** and send both to Claude. These two are designed to be public. **Never send the `service_role` / secret key or the database password.**

Claude puts them into `assets/forum-config.js` and the forums switch on.

## C. Connect an email service (needed before the public can sign in)

Supabase's built-in email only reaches people on your Supabase team, a few messages an hour, so it's enough for testing only. Members get sign-in links once a sending service is connected. Resend is the simplest; Brevo works the same way.

1. Sign up at **resend.com** with Tony's email (free plan).
2. **Domains → Add domain:** `filmcinemas.au`. Resend lists a few DNS records (TXT and MX, sometimes CNAME). Add each one at the domain registrar exactly as shown, then select **Verify** in Resend.
3. **API Keys → Create API key** (permission: sending access). Copy it once; it is a password, so don't send it to Claude or anyone.
4. Back in Supabase: **Authentication → Emails → SMTP Settings → Enable custom SMTP:**
   - Sender email: `noreply@filmcinemas.au`
   - Sender name: `Film Cinemas Australia`
   - Host: `smtp.resend.com`, Port: `465`
   - Username: `resend`, Password: the API key from step 3
5. **Authentication → Emails → Templates → Magic Link:** optionally change the subject to "Your Film Cinemas Australia sign-in link".
6. **Authentication → Rate Limits:** raise "emails sent per hour" from the low default (for example to 100).

## D. Make Tony the first administrator

1. On **filmcinemas.au/forums.html**, sign in with Tony's email, open the link in the email, and create a profile.
2. In Supabase **SQL Editor**, run:

```sql
update public.profiles set role = 'admin'
where id = (select id from auth.users where email = 'TONY'S EMAIL');
```

To add Steve, or any moderator, after they've signed in and made a profile:
`update public.profiles set role = 'admin' where display_name = 'Steve Ord';` (or `'moderator'` for moderation only).

---

## Advertising (when Tony is ready)

Already in the database and on the site: two ad spaces, **home-banner** (homepage, below What's on) and **forums-banner** (forums page). Until switched on, the homepage shows the "About Cinema Partners" box and the forums show nothing. Ads are always labelled **Sponsored**, open in a new tab, never appear in archive records or search, and nothing is tracked.

To run an ad, in Supabase **Table Editor**:
1. `ads` → **Insert row:** placement (`home-banner` or `forums-banner`), advertiser, headline, optional body (up to 220 characters), link (must start with `https://`), optional image link, start and end date, status `live`.
2. `ad_placements` → set `enabled` to **true** for that placement.

If several ads are live in one space, the site picks one at random each visit. To stop an ad, set its status to `paused` or `ended`, or switch the placement off.

**Before taking money for ads:** set up the business (sole trader, partnership or company) with an ABN, and agree on advertising terms and pricing. GST registration is only needed once turnover reaches $75,000 a year.

## Before opening to the public
- Minimum age: sign-up asks people to confirm they're 16 or over. Get legal advice on whether the forums count as an age-restricted social media platform, which would need stronger age checks.
- Add a real contact email (for example `hello@filmcinemas.au`) to the community guidelines page.
- Publish a full privacy policy naming who runs the site.

## E. Switch on member suggestions ("Suggest an update")

Every cinema record, archive listing and research lead has a **Suggest an update** button. Members who are signed in can send a correction or a new detail (address, names, dates, what's there today, a source link). Suggestions never change the archive by themselves.

1. After step B4, open **SQL Editor → New query**, paste the whole of [`supabase/cinema_updates_schema.sql`](cinema_updates_schema.sql) and select **Run**. It is safe to run again.
2. Nothing else is needed: the same Project URL and anon key switch suggestions on together with the forums.

How suggestions are handled:
- They wait in **moderation.html → Member suggestions**. A moderator marks each one accepted, declined or needing more information, with a note the member sees.
- **Download accepted suggestions** gives the editor a file. The editor loads it into staging, checks the evidence, and updates records through the usual sign-off. A new or moved map pin still needs an exact match in the state's official address data.
- Once a change is live, the moderator marks the suggestion **applied**.
- Members see only their own suggestions; moderators see all. Up to 10 suggestions a member a day. Suggestions can't be deleted, so there's always a record of where a change came from.
