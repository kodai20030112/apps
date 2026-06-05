# いいね/コメント通知（Web Push）セットアップ手順

相手がいいね・コメントをつけたら、**アプリを閉じていても** iPhoneに通知が届くようにする設定です。
**1回だけ** ブラウザ（Supabaseダッシュボード）と各iPhoneで作業します。

対象プロジェクト: `okbjqtdirrathscctyvx`（Yuzu-gohan）

---

## 1. 通知の購読テーブルを作る（SQLを貼って実行）

1. Supabaseダッシュボード → 対象プロジェクトを開く
2. 左メニュー **「SQL Editor」** → **New query**
3. `supabase/push_subs.sql` の中身を全部貼り付けて **Run**

> `push_subs` テーブルができます。

---

## 2. Edge Function をデプロイ（コード貼り付け）

1. 左メニュー **「Edge Functions」** → **「Create a new function」**
2. 関数名を **`notify-reaction`** にする（※この名前と完全一致）
3. 同じフォルダの **`index.ts` の中身を全部** 貼り付け
4. **「Deploy」**

---

## 3. VAPIDキーを Secret に登録

ダッシュボード → **Project Settings → Edge Functions → Secrets** → **Add new secret** で
以下の3つを登録します。

| Name | Value |
|---|---|
| `VAPID_PUBLIC_KEY` | `BOp-K1Eif_TEF21_2O_oGWuE23r2ppFzl6b1hafxV0i_1VktjXRRWnTj3vAmG_GXzaVx-HcRwQsfBoljV-_lmdk` |
| `VAPID_PRIVATE_KEY` | **（秘密鍵。下記「秘密鍵について」を参照）** |
| `VAPID_SUBJECT` | `mailto:あなたのメール@example.com`（自分のメールに変更） |

> `SUPABASE_URL` と `SUPABASE_SERVICE_ROLE_KEY` は Supabase が自動で渡すので登録不要。
> 公開鍵は `cooking.html` の `VAPID_PUBLIC` に既に同じ値が入っています（変更不要）。

### 秘密鍵について（重要）

このリポジトリは **公開** のため、`VAPID_PRIVATE_KEY` はここには書きません。
秘密鍵は Supabase の Secrets にだけ登録し、ファイルには残さないでください。

- 秘密鍵を紛失した／作り直したい場合は、ターミナルで以下を実行して新しいペアを生成できます:
  ```
  npx -y web-push generate-vapid-keys --json
  ```
  生成したら **公開鍵** を `cooking.html` の `VAPID_PUBLIC` と Secret `VAPID_PUBLIC_KEY` に、
  **秘密鍵** を Secret `VAPID_PRIVATE_KEY` にだけ設定する（鍵ペアは必ず公開鍵・秘密鍵を揃える）。

---

## 4. 各iPhoneで通知をオンにする（こうだい・ゆずは 両方）

iOSのWeb Pushは **ホーム画面に追加したアプリ** からしか使えません。2人ともこの作業が必要です。

1. Safariで `cooking.html` を開く → 共有 → **「ホーム画面に追加」**
2. ホーム画面の **ゆずごはん日記アイコン** から開く（Safariのタブからではなく）
3. 名前（こうだい / ゆずは）を選ぶ
4. 日記を1件保存するか、いいねを押す → **通知の許可ダイアログで「許可」**

> これで端末が `push_subs` に登録されます。

---

## 5. 動作確認

- 片方の端末でいいね/コメントをつける
- もう片方の端末（アプリを閉じていてもOK）に通知バナーが届けば成功 🎉

---

## うまくいかないとき

| 症状 | 原因と対処 |
|---|---|
| 通知が来ない | 受け取る側が手順4を未実施／通知を「許可」していない |
| `Failed to fetch` | 関数が未デプロイ、または名前が `notify-reaction` と違う |
| `VAPIDキーが未設定です` | 手順3のSecret登録がまだ／名前のスペルミス |
| iPhoneで許可ダイアログが出ない | Safariのタブから開いている。**ホーム画面のアイコン**から開く（iOS16.4以上が必要） |
| 自分のいいねで自分に通知が来る | 端末の `who` と登録名がズレている。アプリで名前を選び直すと直る |

---

## メモ（技術詳細）

- 送信トリガー: クライアント(cooking.html)が、いいね/コメント直後に `notify-reaction` を anon Bearer で呼ぶ。
- 宛先: 関数が service_role で `push_subs` を読み、`who != actor`（＝相手）の端末だけに送る。
- 購読切れ(410/404)は送信時に自動で `push_subs` から削除。
- いいねは「付けたとき」だけ通知（取り消し時は通知しない）。
