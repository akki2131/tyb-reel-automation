-- TYB Reel Automation core schema.
-- This project is intentionally separate from Exducate.

create extension if not exists pgcrypto;

create table if not exists public.tyb_reel_jobs (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','needs_review')),
  question_id text,
  approved_question text,
  template_pair integer check (template_pair between 1 and 4),
  music_index integer check (music_index between 1 and 5),
  cta_index integer check (cta_index between 1 and 8),
  script jsonb,
  video_path text,
  cover_path text,
  script_path text,
  error_code text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tyb_reels (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.tyb_reel_jobs(id) on delete set null,
  question_id text not null,
  approved_question text not null,
  instagram_media_id text unique,
  permalink text,
  published_at timestamptz,
  caption text,
  template_pair integer check (template_pair between 1 and 4),
  music_index integer check (music_index between 1 and 5),
  cta_index integer check (cta_index between 1 and 8),
  duration_seconds numeric,
  created_at timestamptz not null default now()
);

create table if not exists public.tyb_rotation_state (
  key text primary key default 'default',
  question_cursor integer not null default 0,
  pair_cursor integer not null default 0 check (pair_cursor between 0 and 3),
  music_cursor integer not null default 0 check (music_cursor between 0 and 4),
  cta_cursor integer not null default 0 check (cta_cursor between 0 and 7),
  used_question_ids text[] not null default '{}',
  last_successful_job_id uuid references public.tyb_reel_jobs(id) on delete set null,
  updated_at timestamptz not null default now()
);

insert into public.tyb_rotation_state(key) values ('default') on conflict (key) do nothing;

create table if not exists public.tyb_reel_insight_snapshots (
  id uuid primary key default gen_random_uuid(),
  reel_id uuid not null references public.tyb_reels(id) on delete cascade,
  captured_at timestamptz not null default now(),
  status text not null default 'success' check (status in ('success','error')),
  metrics jsonb not null default '{}'::jsonb,
  error_message text,
  created_at timestamptz not null default now()
);

create index if not exists tyb_reel_insights_reel_captured_idx
  on public.tyb_reel_insight_snapshots(reel_id, captured_at desc);

create table if not exists public.tyb_learnings (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('global','topic','hook','duration','template','cta','music')),
  statement text not null,
  evidence jsonb not null default '{}'::jsonb,
  sample_size integer not null default 0 check (sample_size >= 0),
  confidence numeric check (confidence between 0 and 1),
  applies_to jsonb not null default '{}'::jsonb,
  status text not null default 'candidate' check (status in ('candidate','approved','rejected','expired')),
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

alter table public.tyb_reel_jobs enable row level security;
alter table public.tyb_reels enable row level security;
alter table public.tyb_rotation_state enable row level security;
alter table public.tyb_reel_insight_snapshots enable row level security;
alter table public.tyb_learnings enable row level security;

revoke all on public.tyb_reel_jobs from anon, authenticated;
revoke all on public.tyb_reels from anon, authenticated;
revoke all on public.tyb_rotation_state from anon, authenticated;
revoke all on public.tyb_reel_insight_snapshots from anon, authenticated;
revoke all on public.tyb_learnings from anon, authenticated;

-- Private bucket for rendered files; privileged server-side access only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('tyb-reels', 'tyb-reels', false, 104857600,
  array['video/mp4','image/jpeg','application/json','text/plain'])
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
