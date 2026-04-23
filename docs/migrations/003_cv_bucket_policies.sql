-- Migration 003: Storage RLS policies for the CV bucket
-- Run in Supabase SQL editor.

-- Allow authenticated users to upload/replace their own CV
drop policy if exists "Users can upload own CV" on storage.objects;
create policy "Users can upload own CV"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'CV'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to update (replace) their own CV
drop policy if exists "Users can update own CV" on storage.objects;
create policy "Users can update own CV"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'CV'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow authenticated users to read their own CV
drop policy if exists "Users can read own CV" on storage.objects;
create policy "Users can read own CV"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'CV'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow public read if bucket is set to public (for the View link)
drop policy if exists "Public can read CV files" on storage.objects;
create policy "Public can read CV files"
  on storage.objects for select
  to anon
  using (bucket_id = 'CV');
