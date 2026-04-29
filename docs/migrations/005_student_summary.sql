-- Migration 005: rolling per-student summary that the LLM updates over time.
-- One row per user. Surfaces a long-term mental model of the student to the
-- chat/coaching system prompts so the tutor can sound like a teacher who has
-- been working with them for weeks.
-- Run in Supabase SQL editor.

create table if not exists public.student_summary (
  user_id              uuid primary key references auth.users(id) on delete cascade,
  summary              text not null default '',
  recurring_confusions text not null default '',
  goals                text not null default '',
  message_count_at_last_refresh integer not null default 0,
  updated_at           timestamptz not null default now()
);

alter table public.student_summary enable row level security;

drop policy if exists "Users can read own summary" on public.student_summary;
create policy "Users can read own summary"
  on public.student_summary for select
  using (auth.uid() = user_id);

-- Writes are server-only via the service role; no insert/update policies for
-- end users (the backend is the only writer).

drop trigger if exists student_summary_updated_at on public.student_summary;
create trigger student_summary_updated_at
  before update on public.student_summary
  for each row execute procedure public.set_updated_at();
