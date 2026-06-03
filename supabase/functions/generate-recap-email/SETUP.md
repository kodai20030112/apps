# Recap メール下書き（AI生成）セットアップ手順

recap.html の「Leaders へのメール下書き ✨」を動かすための、**1回だけ**の設定です。
ローカルに何もインストールせず、ブラウザ（Supabaseダッシュボード）だけで完了します。

---

## 1. 無料のGemini APIキーを取得（無料枠あり）

1. https://aistudio.google.com/apikey を開く（Googleアカウントでログイン）
2. **「Create API key」** をクリック
3. 表示された `AIza...` で始まるキーをコピー

> 無料枠で十分です。クレジットカード登録は不要。

---

## 2. Edge Function をデプロイ（コード貼り付けだけ）

1. Supabaseダッシュボード → 対象プロジェクト（`okbjqtdirrathscctyvx`）を開く
2. 左メニュー **「Edge Functions」** → **「Deploy a new function」/「Create a new function」**
3. 関数名を **`generate-recap-email`** にする（※この名前と完全一致させること）
4. エディタに、同じフォルダの **`index.ts` の中身を全部** 貼り付ける
5. **「Deploy」** を押す

---

## 3. APIキーをSecretに登録（キーはここに隠れる）

1. ダッシュボード → **Project Settings → Edge Functions → Secrets**
   （または Edge Functions 画面の「Manage secrets」）
2. **Add new secret**
   - Name: `GEMINI_API_KEY`
   - Value: 手順1でコピーした `AIza...` のキー
3. 保存

> これでキーはSupabaseサーバー側だけに置かれ、recap.html やブラウザには一切出ません。

---

## 4. 動作確認

1. recap.html を開く → 2ページ目 → 「Leaders へのメール下書き ✨」
2. 日本語／English を選んで **「✨ AIで生成」**
3. 数秒で下書きが出ればOK。「📋 コピー」「✉️ メールアプリで開く」も使えます。

---

## うまくいかないとき

| 症状 | 原因と対処 |
|---|---|
| `Failed to fetch` | 関数が未デプロイ、または関数名が `generate-recap-email` と違う |
| `GEMINI_API_KEY が未設定です` | 手順3のSecret登録がまだ／名前のスペルミス |
| `Gemini APIエラー` | キーが無効、または無料枠のレート制限。少し待って再試行 |
| `404 model not found` | `index.ts` の `model` を `gemini-flash-latest` などに変更して再デプロイ |

---

## メモ（技術詳細）

- LLM: Google Gemini `gemini-2.5-flash`（無料枠・思考トークンは無効化済み）
- 認証: recap.html は Supabase の anon キー（既に公開済み）を Bearer で送るだけ。Geminiキーはサーバー側Secret。
- CORS: 関数側で `Access-Control-Allow-Origin: *` を返すため、GitHub Pages から直接呼べる。
- 送信データ: 今週のRecap数値（名前/上長/期間/ゴール/Personal NPS/Store NPS/KPI/アクション）のみ。
