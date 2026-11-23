-- Film Cinemas Australia: Cinema Community (member accounts, forums, and advertising switched off)
-- Run once in the Supabase SQL editor (Project > SQL editor > New query > paste > Run).
-- Separate from the archive: nothing here can read or change archive records.
-- Safe to re-run: objects are created only if missing; policies are replaced.

-- ---------------------------------------------------------------- tables
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null check (char_length(btrim(display_name)) between 2 and 40),
  role text not null default 'member' check (role in ('member', 'moderator', 'admin')),
  age_16_confirmed boolean not null check (age_16_confirmed),
  guidelines_accepted_at timestamptz not null default now(),
  suspended_until timestamptz,
  created_at timestamptz not null default now()
);
create unique index if not exists profiles_display_name_key on public.profiles (lower(btrim(display_name)));

create table if not exists public.forum_categories (
  id smallint primary key,
  slug text unique not null,
  name text not null,
  description text not null,
  sort smallint not null
);
insert into public.forum_categories (id, slug, name, description, sort) values
  (1, 'memories', 'Cinema memories', 'First dates, Saturday matinees, drive-in nights and the people who ran them.', 1),
  (2, 'projection', 'Projection and equipment', 'Projectors, sound, changeovers and the projection box.', 2),
  (3, 'classic-films', 'Classic films', 'Favourite classics and what you would like to see on the big screen again.', 3),
  (4, 'whats-on', 'What''s on and events', 'Screenings and special events at Australian cinemas.', 4),
  (5, 'history', 'Cinema history research', 'Questions and leads about cinema sites, names and dates.', 5),
  (6, 'feedback', 'Site feedback', 'Ideas and problems with Film Cinemas Australia.', 6)
on conflict (id) do nothing;

create table if not exists public.forum_threads (
  id bigint generated always as identity primary key,
  category_id smallint not null references public.forum_categories (id),
  author_id uuid not null references public.profiles (id) on delete cascade,
  cinema_name text check (cinema_name is null or char_length(cinema_name) <= 120),
  title text not null check (char_length(btrim(title)) between 5 and 140),
  body text not null check (char_length(btrim(body)) between 10 and 8000),
  status text not null default 'pending' check (status in ('pending', 'visible', 'hidden', 'deleted')),
  reply_count integer not null default 0,
  last_post_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  edited_at timestamptz
);
create index if not exists forum_threads_list on public.forum_threads (status, last_post_at desc);

create table if not exists public.forum_posts (
  id bigint generated always as identity primary key,
  thread_id bigint not null references public.forum_threads (id) on delete cascade,
  author_id uuid not null references public.profiles (id) on delete cascade,
  body text not null check (char_length(btrim(body)) between 2 and 8000),
  status text not null default 'pending' check (status in ('pending', 'visible', 'hidden', 'deleted')),
  created_at timestamptz not null default now(),
  edited_at timestamptz
);
create index if not exists forum_posts_thread on public.forum_posts (thread_id, created_at);

create table if not exists public.forum_reports (
  id bigint generated always as identity primary key,
  target_type text not null check (target_type in ('thread', 'post')),
  target_id bigint not null,
  reporter_id uuid not null references public.profiles (id) on delete cascade,
  reason text not null check (reason in ('spam', 'abuse', 'personal-information', 'illegal', 'off-topic', 'other')),
  detail text check (detail is null or char_length(detail) <= 1000),
  status text not null default 'open' check (status in ('open', 'actioned', 'dismissed')),
  created_at timestamptz not null default now(),
  unique (target_type, target_id, reporter_id)
);

create table if not exists public.forum_moderation_log (
  id bigint generated always as identity primary key,
  actor_id uuid references public.profiles (id) on delete set null,
  target_type text not null,
  target_id bigint not null,
  action text not null,
  note text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- helpers
create or replace function public.is_moderator() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role in ('moderator', 'admin'));
$$;

create or replace function public.can_post() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles
                 where id = auth.uid() and (suspended_until is null or suspended_until < now()));
$$;

-- New threads and replies: author is the signer-in; first two contributions wait for a moderator;
-- at most 5 contributions in 10 minutes.
create or replace function public.forum_before_insert() returns trigger
language plpgsql security definer set search_path = public as $$
declare approved int; recent int;
begin
  new.author_id := auth.uid();
  new.created_at := now();
  new.edited_at := null;
  if new.author_id is null or not public.can_post() then
    raise exception 'You need to be signed in with a member profile to post.';
  end if;
  select (select count(*) from forum_threads where author_id = new.author_id and created_at > now() - interval '10 minutes')
       + (select count(*) from forum_posts   where author_id = new.author_id and created_at > now() - interval '10 minutes')
    into recent;
  if recent >= 5 then
    raise exception 'You are posting very quickly. Please wait a few minutes and try again.';
  end if;
  select (select count(*) from forum_threads where author_id = new.author_id and status = 'visible')
       + (select count(*) from forum_posts   where author_id = new.author_id and status = 'visible')
    into approved;
  new.status := case when public.is_moderator() or approved >= 2 then 'visible' else 'pending' end;
  if tg_table_name = 'forum_threads' then
    new.reply_count := 0; new.last_post_at := now();
  end if;
  return new;
end $$;

-- Members may edit their own words for 30 minutes and may delete their own posts at any time.
-- Only moderators may change status otherwise; every moderator status change is logged.
create or replace function public.forum_before_update() returns trigger
language plpgsql security definer set search_path = public as $$
declare changed boolean;
begin
  -- trusted paths: the SQL editor / service role (no signed-in user) and the reply-count trigger
  if auth.uid() is null or current_setting('forum.internal', true) = '1' then return new; end if;
  new.id := old.id; new.author_id := old.author_id; new.created_at := old.created_at;
  if tg_table_name = 'forum_threads' then
    new.category_id := case when public.is_moderator() then new.category_id else old.category_id end;
    new.reply_count := old.reply_count; new.last_post_at := old.last_post_at;
  else
    new.thread_id := old.thread_id;
  end if;
  if public.is_moderator() then
    if new.status is distinct from old.status then
      insert into forum_moderation_log (actor_id, target_type, target_id, action)
      values (auth.uid(), case when tg_table_name = 'forum_threads' then 'thread' else 'post' end, old.id, old.status || ' -> ' || new.status);
    end if;
    return new;
  end if;
  if auth.uid() is distinct from old.author_id then
    raise exception 'You can only change your own posts.';
  end if;
  if new.status = 'deleted' and old.status <> 'deleted' then
    if tg_table_name = 'forum_threads' then new.title := old.title; end if;
    new.body := old.body; new.edited_at := old.edited_at;
    return new;
  end if;
  new.status := old.status;
  changed := new.body is distinct from old.body;
  if tg_table_name = 'forum_threads' then
    if new.title is distinct from old.title then changed := true; end if;
  end if;
  if changed then
    if now() - old.created_at > interval '30 minutes' or old.status = 'deleted' then
      raise exception 'Posts can only be edited in the first 30 minutes.';
    end if;
    new.edited_at := now();
  end if;
  return new;
end $$;

create or replace function public.forum_after_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare t bigint := coalesce(new.thread_id, old.thread_id);
begin
  perform set_config('forum.internal', '1', true);
  update forum_threads set
    reply_count = (select count(*) from forum_posts where thread_id = t and status = 'visible'),
    last_post_at = greatest(created_at, coalesce((select max(created_at) from forum_posts where thread_id = t and status = 'visible'), created_at))
  where id = t;
  perform set_config('forum.internal', '', true);
  return null;
end $$;

-- Reports: reporter is the signer-in; status starts open.
create or replace function public.forum_before_report() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    new.reporter_id := auth.uid(); new.status := 'open'; new.created_at := now();
    if new.reporter_id is null then raise exception 'Sign in to report a post.'; end if;
  elsif auth.uid() is null then
    return new;
  elsif not public.is_moderator() then
    raise exception 'Only moderators can update reports.';
  else
    insert into forum_moderation_log (actor_id, target_type, target_id, action)
    values (auth.uid(), 'report', old.id, old.status || ' -> ' || new.status);
  end if;
  return new;
end $$;

-- Members cannot give themselves a role or lift a suspension.
create or replace function public.profiles_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    new.id := auth.uid(); new.role := 'member'; new.suspended_until := null; new.created_at := now(); new.guidelines_accepted_at := now();
  elsif auth.uid() is null then
    return new;  -- SQL editor / service role
  elsif not exists (select 1 from profiles where id = auth.uid() and role = 'admin') then
    new.role := old.role;
    if not public.is_moderator() then new.suspended_until := old.suspended_until; end if;
    new.id := old.id; new.created_at := old.created_at;
  end if;
  return new;
end $$;

drop trigger if exists forum_threads_bi on public.forum_threads;
create trigger forum_threads_bi before insert on public.forum_threads for each row execute function public.forum_before_insert();
drop trigger if exists forum_posts_bi on public.forum_posts;
create trigger forum_posts_bi before insert on public.forum_posts for each row execute function public.forum_before_insert();
drop trigger if exists forum_threads_bu on public.forum_threads;
create trigger forum_threads_bu before update on public.forum_threads for each row execute function public.forum_before_update();
drop trigger if exists forum_posts_bu on public.forum_posts;
create trigger forum_posts_bu before update on public.forum_posts for each row execute function public.forum_before_update();
drop trigger if exists forum_posts_ai on public.forum_posts;
create trigger forum_posts_ai after insert or update on public.forum_posts for each row execute function public.forum_after_post();
drop trigger if exists forum_reports_b on public.forum_reports;
create trigger forum_reports_b before insert or update on public.forum_reports for each row execute function public.forum_before_report();
drop trigger if exists profiles_g on public.profiles;
create trigger profiles_g before insert or update on public.profiles for each row execute function public.profiles_guard();

-- ---------------------------------------------------------------- row-level security
alter table public.profiles enable row level security;
alter table public.forum_categories enable row level security;
alter table public.forum_threads enable row level security;
alter table public.forum_posts enable row level security;
alter table public.forum_reports enable row level security;
alter table public.forum_moderation_log enable row level security;

drop policy if exists "profiles readable" on public.profiles;
create policy "profiles readable" on public.profiles for select using (true);
drop policy if exists "create own profile" on public.profiles;
create policy "create own profile" on public.profiles for insert to authenticated with check (id = auth.uid());
drop policy if exists "update own profile or moderate" on public.profiles;
create policy "update own profile or moderate" on public.profiles for update to authenticated using (id = auth.uid() or public.is_moderator());

drop policy if exists "categories readable" on public.forum_categories;
create policy "categories readable" on public.forum_categories for select using (true);

drop policy if exists "threads readable" on public.forum_threads;
create policy "threads readable" on public.forum_threads for select
  using (status = 'visible' or author_id = auth.uid() or public.is_moderator());
drop policy if exists "threads insert" on public.forum_threads;
create policy "threads insert" on public.forum_threads for insert to authenticated with check (public.can_post());
drop policy if exists "threads update" on public.forum_threads;
create policy "threads update" on public.forum_threads for update to authenticated using (author_id = auth.uid() or public.is_moderator());

drop policy if exists "posts readable" on public.forum_posts;
create policy "posts readable" on public.forum_posts for select
  using ((status = 'visible' and exists (select 1 from public.forum_threads t where t.id = thread_id and t.status = 'visible'))
         or author_id = auth.uid() or public.is_moderator());
drop policy if exists "posts insert" on public.forum_posts;
create policy "posts insert" on public.forum_posts for insert to authenticated
  with check (public.can_post() and exists (select 1 from public.forum_threads t where t.id = thread_id and t.status = 'visible'));
drop policy if exists "posts update" on public.forum_posts;
create policy "posts update" on public.forum_posts for update to authenticated using (author_id = auth.uid() or public.is_moderator());

drop policy if exists "reports insert" on public.forum_reports;
create policy "reports insert" on public.forum_reports for insert to authenticated with check (true);
drop policy if exists "reports moderators" on public.forum_reports;
create policy "reports moderators" on public.forum_reports for select to authenticated using (public.is_moderator());
drop policy if exists "reports moderate" on public.forum_reports;
create policy "reports moderate" on public.forum_reports for update to authenticated using (public.is_moderator());

drop policy if exists "log moderators" on public.forum_moderation_log;
create policy "log moderators" on public.forum_moderation_log for select to authenticated using (public.is_moderator());

-- No deletes from the website: content is soft-deleted (status = 'deleted') so moderation history is kept.
-- To make yourself the first administrator, after signing in once on the site and creating your profile, run:
--   update public.profiles set role = 'admin' where id = (select id from auth.users where email = 'YOUR EMAIL');

-- ================================================================ advertising (switched off)
-- Ready for Cinema Partners advertising later. Nothing shows on the site until an administrator
-- switches a placement on AND adds an ad with status 'live' inside its date range.
-- Ads are always labelled "Sponsored" on the site and never appear inside archive records or search.
-- No tracking: the site does not record who sees or clicks an ad.

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$;

create table if not exists public.ad_placements (
  key text primary key,
  label text not null,
  enabled boolean not null default false
);
insert into public.ad_placements (key, label) values
  ('home-banner', 'Homepage banner, below What''s on'),
  ('forums-banner', 'Forums page banner, below the topic list')
on conflict (key) do nothing;

create table if not exists public.ads (
  id bigint generated always as identity primary key,
  placement text not null references public.ad_placements (key),
  advertiser text not null check (char_length(btrim(advertiser)) between 2 and 120),
  headline text not null check (char_length(btrim(headline)) between 3 and 90),
  body text check (body is null or char_length(body) <= 220),
  link_url text not null check (link_url ~ '^https://'),
  image_url text check (image_url is null or image_url ~ '^https://'),
  starts_at timestamptz not null default now(),
  ends_at timestamptz not null,
  status text not null default 'draft' check (status in ('draft', 'live', 'paused', 'ended')),
  created_at timestamptz not null default now(),
  check (ends_at > starts_at)
);
create index if not exists ads_live on public.ads (placement, status, starts_at, ends_at);

alter table public.ad_placements enable row level security;
alter table public.ads enable row level security;

drop policy if exists "placements readable" on public.ad_placements;
create policy "placements readable" on public.ad_placements for select using (true);
drop policy if exists "placements admin" on public.ad_placements;
create policy "placements admin" on public.ad_placements for update to authenticated using (public.is_admin()) with check (public.is_admin());

-- The public can only ever see live, in-date ads in a switched-on placement. Admins see everything.
drop policy if exists "ads public live" on public.ads;
create policy "ads public live" on public.ads for select using (
  (status = 'live' and now() between starts_at and ends_at
   and exists (select 1 from public.ad_placements p where p.key = placement and p.enabled))
  or public.is_admin());
drop policy if exists "ads admin insert" on public.ads;
create policy "ads admin insert" on public.ads for insert to authenticated with check (public.is_admin());
drop policy if exists "ads admin update" on public.ads;
create policy "ads admin update" on public.ads for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists "ads admin delete" on public.ads;
create policy "ads admin delete" on public.ads for delete to authenticated using (public.is_admin());
