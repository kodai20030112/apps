-- ゆずごはん: records テーブルに投稿者（作った人フィルター用）の列を追加する
-- Supabase ダッシュボード → SQL Editor に貼り付けて実行する。
-- who: 'こうだい'（=ゆずちゃんが作った）/ 'ゆずは'（=こうだいが作った）。
-- 既存の過去データは NULL のまま（アプリ上は「すべて」にのみ表示される）。
alter table public.records
  add column if not exists who text;
