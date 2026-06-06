-- Recognition の端末間同期用テーブル（grownote_state と同じ個人用フルアクセス方式）
-- Supabase ダッシュボード → SQL Editor で一度だけ実行する。
-- プロジェクト: okbjqtdirrathscctyvx（recap / GROW / ゆずごはん日記と同じ）

create table if not exists public.recognition_state (
  id text primary key,                 -- 個人用なので 'kodai' 固定の1行に丸ごと保存
  state jsonb,                         -- recognition の DB（{members:[...]}）をそのまま
  updated_at timestamptz default now()
);

alter table public.recognition_state enable row level security;

-- 完全に個人用途のためのフルアクセスポリシー（anon キーで読み書き可）
create policy "recognition_personal_full_access"
  on public.recognition_state
  for all
  to anon
  using (true)
  with check (true);
