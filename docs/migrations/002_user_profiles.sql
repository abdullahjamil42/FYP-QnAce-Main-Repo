-- Migration 002: user_profiles table
-- Stores display name and CV storage reference for each user.
-- Run in Supabase SQL editor.

create table if not exists public.user_profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  full_name   text,
  cv_path     text,          -- storage path: "{user_id}/resume.pdf"
  cv_url      text,          -- public URL from the CV bucket
  cv_filename text,          -- original filename uploaded by the user
  cv_uploaded_at timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.user_profiles enable row level security;

drop policy if exists "Users can read own profile" on public.user_profiles;
create policy "Users can read own profile"
  on public.user_profiles for select
  using (auth.uid() = id);

drop policy if exists "Users can insert own profile" on public.user_profiles;
create policy "Users can insert own profile"
  on public.user_profiles for insert
  with check (auth.uid() = id);

drop policy if exists "Users can update own profile" on public.user_profiles;
create policy "Users can update own profile"
  on public.user_profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Keep updated_at current automatically
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists user_profiles_updated_at on public.user_profiles;
create trigger user_profiles_updated_at
  before update on public.user_profiles
  for each row execute procedure public.set_updated_at();
