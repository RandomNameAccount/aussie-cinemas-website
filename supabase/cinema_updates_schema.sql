-- Film Cinemas Australia: member suggestions for cinema records ("Suggest an update").
-- Run AFTER forum_schema.sql (it uses public.profiles, public.can_post() and public.is_moderator()).
-- Safe to re-run: objects are created only if missing; functions and policies are replaced.
--
-- How it works
--   * Only signed-in members with a profile (and not suspended) can send a suggestion.
--   * A suggestion never changes the archive. It waits in a queue for a moderator.
--   * A moderator marks it accepted, declined or needs more information, with a note the member can read.
--   * Accepted suggestions are downloaded by an editor and applied through the normal staging and
--     sign-off process, so the public website only changes after an editor has checked the evidence.
--   * Members see only their own suggestions; moderators see all of them. Nobody else can read them.

create table if not exists public.cinema_updates (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references public.profiles (id) on delete cascade,
  target_type text not null check (target_type in ('record', 'archive', 'lead', 'new')),
  target_id text check (target_id is null or target_id ~ '^[a-z0-9-]{2,60}$'),
  target_name text not null check (char_length(btrim(target_name)) between 2 and 120),
  topics text[] not null check (cardinality(topics) between 1 and 6
    and topics <@ array['location', 'name', 'dates', 'today', 'description', 'other']::text[]),
  details text not null check (char_length(btrim(details)) between 20 and 3000),
  address text check (address is null or char_length(address) <= 200),
  locality text check (locality is null or char_length(locality) <= 80),
  state text check (state is null or state in ('QLD', 'NSW', 'VIC', 'TAS', 'SA', 'WA', 'NT', 'ACT')),
  basis text not null check (basis in ('worked', 'visited', 'family', 'research', 'document', 'other')),
  source_url text check (source_url is null or (source_url ~ '^https?://' and char_length(source_url) <= 500)),
  source_note text check (source_note is null or char_length(source_note) <= 300),
  credit_me boolean not null default false,
  own_words boolean not null check (own_words),
  status text not null default 'pending' check (status in ('pending', 'accepted', 'declined', 'needs_info', 'applied', 'withdrawn')),
  review_note text check (review_note is null or char_length(review_note) <= 1000),
  reviewed_by uuid references public.profiles (id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists cinema_updates_status_idx on public.cinema_updates (status, created_at);
create index if not exists cinema_updates_author_idx on public.cinema_updates (author_id, created_at);
create index if not exists cinema_updates_target_idx on public.cinema_updates (target_type, target_id);
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'cinema_updates_target_ck') then
    alter table public.cinema_updates add constraint cinema_updates_target_ck check ((target_type = 'new') = (target_id is null));
  end if;
end $$;

-- New suggestions: the author is whoever is signed in; status always starts as pending;
-- at most 10 suggestions a day per member.
create or replace function public.cinema_updates_before_insert() returns trigger
language plpgsql security definer set search_path = public as $$
declare recent int;
begin
  new.author_id := auth.uid();
  if new.author_id is null or not public.can_post() then
    raise exception 'You need to be signed in with a member profile to suggest an update.';
  end if;
  select count(*) into recent from cinema_updates where author_id = new.author_id and created_at > now() - interval '1 day';
  if recent >= 10 then
    raise exception 'You have sent 10 suggestions today. Thank you! Please send more tomorrow.';
  end if;
  new.status := 'pending'; new.review_note := null; new.reviewed_by := null; new.reviewed_at := null;
  new.created_at := now();
  new.details := btrim(new.details); new.target_name := btrim(new.target_name);
  return new;
end $$;
drop trigger if exists cinema_updates_before_insert on public.cinema_updates;
create trigger cinema_updates_before_insert before insert on public.cinema_updates
  for each row execute function public.cinema_updates_before_insert();

-- Updates: a member may only withdraw their own pending suggestion. Moderators may set the status
-- and review note (stamped with who and when). Nothing else can change after sending.
create or replace function public.cinema_updates_before_update() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return new; end if;  -- SQL editor / service role
  if public.is_moderator() then
    if new.status is distinct from old.status or new.review_note is distinct from old.review_note then
      new.reviewed_by := auth.uid(); new.reviewed_at := now();
    end if;
    new.author_id := old.author_id; new.target_type := old.target_type; new.target_id := old.target_id;
    new.target_name := old.target_name; new.topics := old.topics; new.details := old.details;
    new.address := old.address; new.locality := old.locality; new.state := old.state; new.basis := old.basis;
    new.source_url := old.source_url; new.source_note := old.source_note; new.credit_me := old.credit_me;
    new.own_words := old.own_words; new.created_at := old.created_at;
    return new;
  end if;
  if old.author_id = auth.uid() and old.status = 'pending' and new.status = 'withdrawn' then
    new := old; new.status := 'withdrawn'; return new;
  end if;
  raise exception 'Only a moderator can change a suggestion after it is sent.';
end $$;
drop trigger if exists cinema_updates_before_update on public.cinema_updates;
create trigger cinema_updates_before_update before update on public.cinema_updates
  for each row execute function public.cinema_updates_before_update();

alter table public.cinema_updates enable row level security;
drop policy if exists "updates insert" on public.cinema_updates;
create policy "updates insert" on public.cinema_updates for insert to authenticated with check (public.can_post());
drop policy if exists "updates read own or moderate" on public.cinema_updates;
create policy "updates read own or moderate" on public.cinema_updates for select to authenticated
  using (author_id = auth.uid() or public.is_moderator());
drop policy if exists "updates withdraw own or moderate" on public.cinema_updates;
create policy "updates withdraw own or moderate" on public.cinema_updates for update to authenticated
  using (author_id = auth.uid() or public.is_moderator());
-- no delete policy: suggestions are kept as the record of where a change came from
