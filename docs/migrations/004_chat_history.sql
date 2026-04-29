-- Migration 004: persistent chat history for notes_chat and coaching surfaces.
-- One conversation per (user_id, surface, topic_id) for notes_chat,
-- one per (user_id, surface, session_id) for coaching.
-- Run in Supabase SQL editor.

create table if not exists public.chat_conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  surface     text not null check (surface in ('notes_chat','coaching')),
  topic_id    text,
  session_id  uuid,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create unique index if not exists chat_conversations_notes_unique
  on public.chat_conversations(user_id, surface, topic_id)
  where surface = 'notes_chat';

create unique index if not exists chat_conversations_coaching_unique
  on public.chat_conversations(user_id, surface, session_id)
  where surface = 'coaching';

create index if not exists chat_conversations_user_surface
  on public.chat_conversations(user_id, surface);

create table if not exists public.chat_messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.chat_conversations(id) on delete cascade,
  role            text not null check (role in ('user','assistant')),
  content         text not null,
  created_at      timestamptz not null default now()
);

create index if not exists chat_messages_conversation_created
  on public.chat_messages(conversation_id, created_at);

-- Row-level security: only the owning user can read/write their own
-- conversations and messages. Service-role bypasses RLS entirely so the
-- backend continues to work via SUPABASE_SERVICE_ROLE_KEY.

alter table public.chat_conversations enable row level security;

drop policy if exists "Users can read own conversations" on public.chat_conversations;
create policy "Users can read own conversations"
  on public.chat_conversations for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own conversations" on public.chat_conversations;
create policy "Users can insert own conversations"
  on public.chat_conversations for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own conversations" on public.chat_conversations;
create policy "Users can update own conversations"
  on public.chat_conversations for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

alter table public.chat_messages enable row level security;

drop policy if exists "Users can read own messages" on public.chat_messages;
create policy "Users can read own messages"
  on public.chat_messages for select
  using (
    exists (
      select 1 from public.chat_conversations c
      where c.id = chat_messages.conversation_id and c.user_id = auth.uid()
    )
  );

drop policy if exists "Users can insert own messages" on public.chat_messages;
create policy "Users can insert own messages"
  on public.chat_messages for insert
  with check (
    exists (
      select 1 from public.chat_conversations c
      where c.id = chat_messages.conversation_id and c.user_id = auth.uid()
    )
  );

drop trigger if exists chat_conversations_updated_at on public.chat_conversations;
create trigger chat_conversations_updated_at
  before update on public.chat_conversations
  for each row execute procedure public.set_updated_at();
