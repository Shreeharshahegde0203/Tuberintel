-- Run in the Supabase SQL editor after creating the project.
-- Application tables are created by Alembic/SQLAlchemy using DATABASE_URL.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'potato-inspections',
  'potato-inspections',
  true,
  12582912,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Public read is intentional for the demonstration bucket. For sensitive farmer
-- deployments, use a private bucket and signed URLs instead.
create policy "Public inspection image read"
on storage.objects for select
using (bucket_id = 'potato-inspections');
