-- Daily publication guard and recovery support for TYB Reels.
-- One guarded production publication slot per Asia/Kolkata calendar day.

create table if not exists public.tyb_daily_runs (
  run_date date primary key,
  status text not null default 'claimed' check (status in ('claimed','published','failed')),
  claimed_at timestamptz not null default now(),
  published_at timestamptz,
  github_run_id text,
  trigger_source text,
  job_id uuid references public.tyb_reel_jobs(id) on delete set null,
  updated_at timestamptz not null default now()
);

alter table public.tyb_daily_runs enable row level security;
revoke all on public.tyb_daily_runs from anon, authenticated;
grant all on public.tyb_daily_runs to service_role;

create or replace function public.claim_tyb_daily_run(
  p_run_date date,
  p_github_run_id text,
  p_trigger_source text
) returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_rows integer;
  v_status text;
  v_published_job uuid;
begin
  -- A published Reel in the actual publication table is authoritative.
  select r.job_id into v_published_job
    from public.tyb_reels r
   where r.publish_status = 'published'
     and r.published_at >= (p_run_date::timestamp at time zone 'Asia/Kolkata')
     and r.published_at < ((p_run_date + 1)::timestamp at time zone 'Asia/Kolkata')
   order by r.published_at desc
   limit 1;

  if v_published_job is not null then
    insert into public.tyb_daily_runs(run_date,status,claimed_at,published_at,job_id,github_run_id,trigger_source,updated_at)
    values (p_run_date,'published',now(),now(),v_published_job,p_github_run_id,p_trigger_source,now())
    on conflict (run_date) do update
      set status='published', published_at=coalesce(public.tyb_daily_runs.published_at,excluded.published_at),
          job_id=coalesce(public.tyb_daily_runs.job_id,excluded.job_id), updated_at=now();
    return jsonb_build_object('should_run',false,'reason','already_published');
  end if;

  insert into public.tyb_daily_runs(run_date, status, claimed_at, github_run_id, trigger_source, updated_at)
  values (p_run_date, 'claimed', now(), p_github_run_id, p_trigger_source, now())
  on conflict (run_date) do nothing;
  get diagnostics v_rows = row_count;
  if v_rows = 1 then
    return jsonb_build_object('should_run', true, 'reason', 'daily_slot_claimed');
  end if;

  update public.tyb_daily_runs
     set status = 'claimed',
         claimed_at = now(),
         published_at = null,
         github_run_id = p_github_run_id,
         trigger_source = p_trigger_source,
         updated_at = now()
   where run_date = p_run_date
     and status <> 'published'
     and (status = 'failed' or claimed_at < now() - interval '30 minutes');
  get diagnostics v_rows = row_count;
  if v_rows = 1 then
    return jsonb_build_object('should_run', true, 'reason', 'stale_or_failed_claim_recovered');
  end if;

  select status into v_status from public.tyb_daily_runs where run_date = p_run_date;
  return jsonb_build_object('should_run', false, 'reason', coalesce(v_status, 'already_claimed'));
end;
$$;

create or replace function public.mark_tyb_daily_published(
  p_run_date date,
  p_job_id uuid
) returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
begin
  update public.tyb_daily_runs
     set status = 'published',
         published_at = now(),
         job_id = p_job_id,
         updated_at = now()
   where run_date = p_run_date;
  if not found then
    raise exception 'No daily run claim exists for %', p_run_date;
  end if;
  return jsonb_build_object('published', true, 'run_date', p_run_date);
end;
$$;

create or replace function public.mark_tyb_daily_failed(
  p_run_date date
) returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
begin
  update public.tyb_daily_runs
     set status = 'failed', updated_at = now()
   where run_date = p_run_date and status <> 'published';
  return jsonb_build_object('failed_marked', found, 'run_date', p_run_date);
end;
$$;

revoke execute on function public.claim_tyb_daily_run(date, text, text) from public, anon, authenticated;
revoke execute on function public.mark_tyb_daily_published(date, uuid) from public, anon, authenticated;
revoke execute on function public.mark_tyb_daily_failed(date) from public, anon, authenticated;
grant execute on function public.claim_tyb_daily_run(date, text, text) to service_role;
grant execute on function public.mark_tyb_daily_published(date, uuid) to service_role;
grant execute on function public.mark_tyb_daily_failed(date) to service_role;
