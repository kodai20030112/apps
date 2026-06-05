// Supabase Edge Function: notify-reaction
// ゆずごはん日記で「いいね/コメント」が付いたとき、相手の端末へ Web Push を送る。
// クライアント(cooking.html)が、自分がいいね/コメントした直後に呼ぶ。
//
// デプロイ: Supabaseダッシュボード → Edge Functions → 新規作成「notify-reaction」にこのコードを貼り付け。
// Secret(Project Settings → Edge Functions → Secrets):
//   VAPID_PUBLIC_KEY  … cooking.html の VAPID_PUBLIC と同じ公開鍵
//   VAPID_PRIVATE_KEY … 秘密鍵（クライアントには絶対に置かない）
//   VAPID_SUBJECT     … 連絡先（例: mailto:you@example.com）
// ※ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY は Supabase が自動で渡すので登録不要。

import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(obj: unknown, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "POSTのみ対応" }, 405);

  try {
    const { kind, actor, recordName, body } = await req.json();
    if (!actor) return json({ error: "actor が必要です" }, 400);

    const pub = Deno.env.get("VAPID_PUBLIC_KEY");
    const priv = Deno.env.get("VAPID_PRIVATE_KEY");
    const subject = Deno.env.get("VAPID_SUBJECT") || "mailto:example@example.com";
    if (!pub || !priv) return json({ error: "VAPIDキーが未設定です（Secretsを確認）" }, 500);
    webpush.setVapidDetails(subject, pub, priv);

    const sb = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    // 自分以外（＝相手）の端末を取得
    const { data: subs, error } = await sb
      .from("push_subs")
      .select("*")
      .neq("who", actor);
    if (error) return json({ error: error.message }, 500);

    const name = recordName || "日記";
    const msg = kind === "like"
      ? `${actor}さんが「${name}」にいいねしました ❤️`
      : kind === "comment"
      ? `${actor}さんが「${name}」にコメントしました 💬${body ? "：" + body : ""}`
      // post: クライアントが用意した文面（保存メッセージ）をそのまま使う
      : (body || `${actor}さんが「${name}」を投稿しました 📔`);
    const payload = JSON.stringify({ title: "🍋 ゆずごはん日記", body: msg });

    let sent = 0;
    for (const s of subs || []) {
      try {
        await webpush.sendNotification(
          { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
          payload,
        );
        sent++;
      } catch (e) {
        // 410(Gone)/404 は購読切れ → DBから掃除する
        const code = (e as { statusCode?: number })?.statusCode;
        if (code === 410 || code === 404) {
          await sb.from("push_subs").delete().eq("endpoint", s.endpoint);
        } else {
          console.error("push failed:", code, (e as Error)?.message);
        }
      }
    }

    return json({ ok: true, sent });
  } catch (e) {
    return json({ error: (e as Error)?.message || String(e) }, 500);
  }
});
