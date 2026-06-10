-- おつかいカート（Amazon買い物アシスト）の端末間同期用テーブル
-- たびのき／クレジット明細マネージャーと同じプロジェクト（okbjqtdirrathscctyvx）。
-- Supabase ダッシュボード → SQL Editor に貼り付けて一度だけ実行する。
-- 実行するまではアプリは「この端末のみ保存」で動き、実行後に複数端末で自動同期される。

create table if not exists public.kaimono_state (
  id text primary key,                 -- 個人利用なので 'kodai' 固定の1行に丸ごと保存
  state jsonb,                         -- おつかいカートの DB（{items,settings}）をそのまま
  updated_at timestamptz default now()
);

alter table public.kaimono_state enable row level security;

-- 個人の複数端末用フルアクセスポリシー（anon キーで読み書き可）
create policy "kaimono_full_access"
  on public.kaimono_state
  for all
  to anon
  using (true)
  with check (true);

-- リアルタイム配信を有効化（変更が他の端末の画面に即反映される）
alter publication supabase_realtime add table public.kaimono_state;
