-- TSA / AUTOCLAW — Supabase 初始 schema
-- 用法：Supabase → SQL Editor → New query → 全段貼上 → Run
-- 設計原則：只存「即時查詢要用的摘要」，原始 bars 留在檔案，唔佔 500MB。

create table if not exists public.rankings (
  id          bigserial primary key,
  as_of       timestamptz not null,
  timeframe   text        not null,
  symbol      text        not null,
  score       numeric,
  rank        int,
  payload     jsonb       not null default '{}'::jsonb
);
create index if not exists rankings_asof_idx on public.rankings (as_of desc);
create index if not exists rankings_sym_idx  on public.rankings (symbol, timeframe, as_of desc);

create table if not exists public.signals (
  id          bigserial primary key,
  as_of       timestamptz not null,
  symbol      text        not null,
  action      text        not null,
  confidence  numeric,
  payload     jsonb       not null default '{}'::jsonb
);
create index if not exists signals_asof_idx on public.signals (as_of desc);
create index if not exists signals_sym_idx  on public.signals (symbol, as_of desc);

create table if not exists public.positions (
  id          bigserial primary key,
  as_of       timestamptz not null,
  account     text        not null,
  symbol      text        not null,
  lots        numeric,
  pnl         numeric,
  payload     jsonb       not null default '{}'::jsonb
);
create index if not exists positions_asof_idx on public.positions (as_of desc);

create table if not exists public.health (
  id          bigserial primary key,
  as_of       timestamptz not null default now(),
  source      text        not null,
  status      text        not null,
  payload     jsonb       not null default '{}'::jsonb
);
create index if not exists health_asof_idx on public.health (as_of desc);

-- 權限：匿名（網頁）只可讀，不可寫。寫入由 service_role 進行（自動繞過 RLS）。
alter table public.rankings  enable row level security;
alter table public.signals   enable row level security;
alter table public.positions enable row level security;
alter table public.health    enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='rankings' and policyname='public read') then
    create policy "public read" on public.rankings for select using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='signals' and policyname='public read') then
    create policy "public read" on public.signals for select using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='positions' and policyname='public read') then
    create policy "public read" on public.positions for select using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='health' and policyname='public read') then
    create policy "public read" on public.health for select using (true);
  end if;
end $$;

grant usage on schema public to anon, authenticated;
grant select on public.rankings, public.signals, public.positions, public.health to anon, authenticated;

-- 保留期：只留 90 天（避免免費 500MB 被舊資料食滿）
-- 進階：可在 Supabase 開 pg_cron 每日清理，或由 AUTOCLAW 每日跑一次刪除。
