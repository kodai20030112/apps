-- つぎいつ？ — Web Push の購読情報テーブル
-- ゆずごはん日記の push_subs と同形だが、アプリ専用に分離している
-- （push_subs は endpoint が主キーで他アプリと共有のため、上書き衝突を避ける目的）。
-- Supabaseダッシュボード → SQL Editor にこの中身を貼って実行（1回だけ）。

create table if not exists public.tsugi_subs (
  endpoint   text primary key,   -- 端末ごとに一意（プッシュ送信先URL）
  who        text not null,      -- 'kodai' 固定（個人用）
  p256dh     text not null,      -- 暗号鍵
  auth       text not null,      -- 認証シークレット
  created_at bigint
);

-- 個人用途のため、他テーブル同様 anon キーから読み書きを許可する。
alter table public.tsugi_subs enable row level security;

drop policy if exists "tsugi_subs anon all" on public.tsugi_subs;
create policy "tsugi_subs anon all" on public.tsugi_subs
  for all to anon using (true) with check (true);
