-- ゆずごはん日記 — Web Push の購読情報テーブル
-- Supabaseダッシュボード → SQL Editor にこの中身を貼って実行（1回だけ）。

create table if not exists public.push_subs (
  endpoint   text primary key,   -- 端末ごとに一意（プッシュ送信先URL）
  who        text not null,      -- こうだい / ゆずは（どちらの端末か）
  p256dh     text not null,      -- 暗号鍵
  auth       text not null,      -- 認証シークレット
  created_at bigint
);

-- 2人だけのアプリなので、他テーブル同様 anon キーから読み書きを許可する。
alter table public.push_subs enable row level security;

drop policy if exists "push_subs anon all" on public.push_subs;
create policy "push_subs anon all" on public.push_subs
  for all to anon using (true) with check (true);
