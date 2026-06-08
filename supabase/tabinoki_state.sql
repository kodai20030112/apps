-- たびのき（ふたりの旅のしおり）の共有同期用テーブル
-- ゆずごはん日記と同じプロジェクト（okbjqtdirrathscctyvx）で、
-- Supabase ダッシュボード → SQL Editor に貼り付けて一度だけ実行する。
-- 実行するまではアプリは「この端末のみ保存」で動き、実行後にふたりで自動同期される。

create table if not exists public.tabinoki_state (
  id text primary key,                 -- ふたり共有なので 'shared' 固定の1行に丸ごと保存
  state jsonb,                         -- たびのきの DB（{trips:[...]}）をそのまま
  updated_at timestamptz default now()
);

alter table public.tabinoki_state enable row level security;

-- ふたり共有用のフルアクセスポリシー（anon キーで読み書き可）
create policy "tabinoki_shared_full_access"
  on public.tabinoki_state
  for all
  to anon
  using (true)
  with check (true);

-- リアルタイム配信を有効化（変更が相手の画面に即反映される）
alter publication supabase_realtime add table public.tabinoki_state;
