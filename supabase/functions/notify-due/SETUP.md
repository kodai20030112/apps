# つぎいつ？ 予定日リマインド（Web Push）セットアップ手順

予定日が近づいたら、**アプリを閉じていても** iPhoneに通知が届くようにする設定です。
**1回だけ** ブラウザ（Supabaseダッシュボード）とiPhoneで作業します。

対象プロジェクト: `okbjqtdirrathscctyvx`（recap / GROW / Recognition と同じ）

> アプリ自体（一覧・「あと◯日」表示・端末間同期）は、この通知設定をしなくても
> `tsugi_state` テーブルを作るだけで動きます。プッシュ通知が欲しいときだけ以下を実施。

---

## 1. テーブルを2つ作る（SQLを貼って実行）

1. Supabaseダッシュボード → 対象プロジェクト → **「SQL Editor」** → **New query**
2. `supabase/tsugi_state.sql` の中身を貼って **Run**（同期用）
3. もう一度 New query → `supabase/tsugi_subs.sql` の中身を貼って **Run**（通知購読用）

---

## 2. Edge Function をデプロイ（コード貼り付け）

1. 左メニュー **「Edge Functions」** → **「Create a new function」**
2. 関数名を **`notify-due`** にする（※この名前と完全一致）
3. 同じフォルダの **`index.ts` の中身を全部** 貼り付け → **「Deploy」**

---

## 3. VAPIDキーを Secret に登録

`notify-reaction`（ゆずごはん日記）を既に設定済みなら **同じ Secret を共用**するので、この手順は不要です。
まだなら **Project Settings → Edge Functions → Secrets** で以下を登録:

| Name | Value |
|---|---|
| `VAPID_PUBLIC_KEY` | `BOp-K1Eif_TEF21_2O_oGWuE23r2ppFzl6b1hafxV0i_1VktjXRRWnTj3vAmG_GXzaVx-HcRwQsfBoljV-_lmdk` |
| `VAPID_PRIVATE_KEY` | **（秘密鍵。リポジトリには置かない。`notify-reaction` と同じ値）** |
| `VAPID_SUBJECT` | `mailto:あなたのメール@example.com` |

> `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` は Supabase が自動で渡すので登録不要。
> 公開鍵は `tsugi.html` の `VAPID_PUBLIC` に既に同じ値が入っています（変更不要）。

---

## 4. 毎日自動でチェックする（cron を1回設定）

SQL Editor で **New query** → 下を貼って **Run**（毎日 09:00 JST = 00:00 UTC に起動）。
`<ANON_KEY>` は `tsugi.html` の `SUPABASE_ANON` の値に置き換える。

```sql
-- 拡張を有効化（初回のみ。すでに有効ならスキップされる）
create extension if not exists pg_cron;
create extension if not exists pg_net;

select cron.schedule(
  'tsugi-notify-due',
  '0 0 * * *',            -- 毎日 00:00 UTC = 09:00 JST
  $$
  select net.http_post(
    url     := 'https://okbjqtdirrathscctyvx.supabase.co/functions/v1/notify-due',
    headers := '{"Content-Type":"application/json","Authorization":"Bearer <ANON_KEY>"}'::jsonb,
    body    := '{}'::jsonb
  );
  $$
);
```

> 時刻を変えたいときは `'0 0 * * *'` を編集（分 時 日 月 曜、UTC）。
> 例）毎日 08:00 JST にしたいなら前日 23:00 UTC → `'0 23 * * *'`。
> 設定をやり直すときは先に `select cron.unschedule('tsugi-notify-due');`。

---

## 5. iPhoneで通知をオンにする

iOSのWeb Pushは **ホーム画面に追加したアプリ** からしか使えません。

1. Safariで `tsugi.html` を開く → 共有 → **「ホーム画面に追加」**
2. ホーム画面の **つぎいつ？アイコン** から開く（Safariのタブからではなく）
3. 上部の **「🔔 通知を受け取る → オンにする」** をタップ → 許可ダイアログで「許可」

> これで端末が `tsugi_subs` に登録されます。

---

## 6. 動作確認

- 予定日が「あと◯日（◯＝通知日数以内）」になっている項目を1つ用意
- Edge Functions の `notify-due` ページで **「Invoke」/「Run」** を押す（手動実行）
- iPhoneに通知が届けば成功 🎉（1周期につき1回だけ届く仕様）

---

## うまくいかないとき

| 症状 | 原因と対処 |
|---|---|
| 通知が来ない | 手順5が未実施／通知を「許可」していない |
| 何度Invokeしても来ない | その周期はもう通知済み。「行ってきた✓」を押すと次の周期で再び対象に |
| `VAPIDキーが未設定です` | 手順3のSecret登録がまだ／スペルミス |
| iPhoneで許可ダイアログが出ない | Safariのタブから開いている。**ホーム画面のアイコン**から開く（iOS16.4以上が必要） |
| cronが動かない | `pg_cron`/`pg_net` 拡張が無効、または `<ANON_KEY>` 未置換 |

---

## メモ（技術詳細）

- トリガー: cron(pg_cron+pg_net) が毎日 `notify-due` を anon Bearer で叩く。
- 判定: 関数が service_role で `tsugi_state` を読み、各項目の `次の予定日 - 今日(JST) <= leadDays`
  かつ `notifiedFor != その周期` の項目を抽出して送信。
- 重複防止: 送信したら項目に `notifiedFor = 周期キー(次の予定日)` を書き戻す。
  「行ってきた✓」で `lastDate` が更新されると周期キーが変わり、次の周期で再び通知対象になる。
- 購読切れ(410/404)は送信時に自動で `tsugi_subs` から削除。
