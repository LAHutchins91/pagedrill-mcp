-- Pagedrill by Ouroboros. Apply in the Supabase SQL editor when the project exists.
-- This script does not create Stripe products or prices.
-- Caps and the hourly check window are enforced per user in usage_monthly.
-- usage_charge and usage_allow_check increment those rows. There is no overage price.
-- Files expire 24 hours after last use. POST /internal/purge deletes expired rows.

create table if not exists public.profiles (
  id uuid primary key,
  email text,
  plan text not null default 'trial',
  subscription_status text not null default 'trialing',
  retention_hours integer not null default 24 check (retention_hours = 24),
  stripe_customer_id text,
  stripe_subscription_id text,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.usage_monthly (
  owner_id uuid not null references public.profiles (id) on delete cascade,
  month text not null check (month ~ '^[0-9]{4}-[0-9]{2}$'),
  formats integer not null default 0 check (formats >= 0),
  previews integer not null default 0 check (previews >= 0),
  files integer not null default 0 check (files >= 0),
  checks integer not null default 0 check (checks >= 0),
  free_formats integer not null default 0 check (free_formats >= 0),
  free_previews integer not null default 0 check (free_previews >= 0),
  free_files integer not null default 0 check (free_files >= 0),
  check_window_start timestamptz,
  check_window_count integer not null default 0 check (check_window_count >= 0),
  primary key (owner_id, month)
);

alter table public.usage_monthly add column if not exists free_formats integer not null default 0;
alter table public.usage_monthly add column if not exists free_previews integer not null default 0;
alter table public.usage_monthly add column if not exists free_files integer not null default 0;
alter table public.usage_monthly add column if not exists check_window_start timestamptz;
alter table public.usage_monthly add column if not exists check_window_count integer not null default 0;

create table if not exists public.files (
  id uuid primary key,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  filename text not null,
  kind text not null,
  head_sha text not null,
  size integer not null check (size >= 0),
  created_at timestamptz not null default now(),
  last_used_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create table if not exists public.file_versions (
  file_id uuid not null references public.files (id) on delete cascade,
  number integer not null check (number > 0),
  sha256 text not null,
  size integer not null check (size >= 0),
  op text not null check (op in ('import', 'apply', 'restore')),
  created_at timestamptz not null default now(),
  primary key (file_id, number)
);

create table if not exists public.proposals (
  id uuid primary key,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  file_id uuid not null references public.files (id) on delete cascade,
  base_sha text not null,
  result_sha text not null,
  size integer not null,
  diff jsonb not null,
  flags jsonb not null default '[]'::jsonb,
  verification jsonb not null,
  checklist jsonb not null,
  notice text,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  applied_at timestamptz
);

create table if not exists public.upload_nonces (
  nonce text primary key,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  file_id uuid not null,
  filename text not null,
  exp timestamptz not null
);

create table if not exists public.support_requests (
  id uuid primary key,
  email text not null,
  message text not null,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.usage_monthly enable row level security;
alter table public.files enable row level security;
alter table public.file_versions enable row level security;
alter table public.proposals enable row level security;
alter table public.upload_nonces enable row level security;
alter table public.support_requests enable row level security;

insert into storage.buckets (id, name, public)
values ('pagedrill-files', 'pagedrill-files', false)
on conflict (id) do nothing;

-- Atomic counters. The insert does not set a count, so the following update is the only increment.
create or replace function public.usage_charge(
  p_owner uuid,
  p_month text,
  p_metric text,
  p_cap integer
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  current_value integer;
begin
  if p_metric not in ('formats', 'previews', 'files', 'checks', 'free_formats', 'free_previews', 'free_files') then
    raise exception 'unknown usage metric';
  end if;
  if p_month !~ '^[0-9]{4}-[0-9]{2}$' then
    raise exception 'unknown usage month';
  end if;

  insert into public.usage_monthly (owner_id, month)
  values (p_owner, p_month)
  on conflict (owner_id, month) do nothing;

  if p_metric = 'formats' then
    select formats into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set formats = formats + 1 where owner_id = p_owner and month = p_month returning formats into current_value;
  elsif p_metric = 'previews' then
    select previews into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set previews = previews + 1 where owner_id = p_owner and month = p_month returning previews into current_value;
  elsif p_metric = 'files' then
    select files into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set files = files + 1 where owner_id = p_owner and month = p_month returning files into current_value;
  elsif p_metric = 'free_formats' then
    select free_formats into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set free_formats = free_formats + 1 where owner_id = p_owner and month = p_month returning free_formats into current_value;
  elsif p_metric = 'free_previews' then
    select free_previews into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set free_previews = free_previews + 1 where owner_id = p_owner and month = p_month returning free_previews into current_value;
  elsif p_metric = 'free_files' then
    select free_files into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    if current_value >= p_cap then return -1; end if;
    update public.usage_monthly set free_files = free_files + 1 where owner_id = p_owner and month = p_month returning free_files into current_value;
  else
    select checks into current_value from public.usage_monthly where owner_id = p_owner and month = p_month for update;
    update public.usage_monthly set checks = checks + 1 where owner_id = p_owner and month = p_month returning checks into current_value;
  end if;

  return current_value;
end;
$$;

create or replace function public.usage_allow_check(
  p_owner uuid,
  p_month text,
  p_now timestamptz,
  p_limit integer
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  window_start timestamptz;
  window_count integer;
begin
  if p_month !~ '^[0-9]{4}-[0-9]{2}$' then
    raise exception 'unknown usage month';
  end if;

  insert into public.usage_monthly (owner_id, month)
  values (p_owner, p_month)
  on conflict (owner_id, month) do nothing;

  select check_window_start, check_window_count
    into window_start, window_count
  from public.usage_monthly
  where owner_id = p_owner and month = p_month
  for update;

  if window_start is null or p_now >= window_start + interval '1 hour' then
    update public.usage_monthly
      set check_window_start = p_now,
          check_window_count = 1
    where owner_id = p_owner and month = p_month;
    return true;
  end if;

  window_count := window_count + 1;
  update public.usage_monthly
    set check_window_count = window_count
  where owner_id = p_owner and month = p_month;
  return window_count <= p_limit;
end;
$$;

revoke all on function public.usage_charge(uuid, text, text, integer) from public;
revoke all on function public.usage_allow_check(uuid, text, timestamptz, integer) from public;
grant execute on function public.usage_charge(uuid, text, text, integer) to service_role;
grant execute on function public.usage_allow_check(uuid, text, timestamptz, integer) to service_role;
