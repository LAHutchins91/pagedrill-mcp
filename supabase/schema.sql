-- Pagedrill by Ouroboros. Apply in the Supabase SQL editor when the project exists.
-- This script does not create Stripe products or prices.
-- Caps are enforced by the application. There is no overage price.
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
  primary key (owner_id, month)
);

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
