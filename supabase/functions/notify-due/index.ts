// Supabase Edge Function: notify-due
// つぎいつ？ — 毎日1回 cron で起動し、「予定日が近い／過ぎた」項目を
// この端末（tsugi_subs）へ Web Push で知らせる。1周期につき1回だけ通知する。
//
// デプロイ: Supabaseダッシュボード → Edge Functions → 新規作成「notify-due」にこのコードを貼り付け。
// Secret(Project Settings → Edge Functions → Secrets) … notify-reaction と共用でOK:
//   VAPID_PUBLIC_KEY  … tsugi.html の VAPID_PUBLIC と同じ公開鍵
//   VAPID_PRIVATE_KEY … 秘密鍵
//   VAPID_SUBJECT     … 連絡先（例: mailto:you@example.com）
// ※ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY は Supabase が自動で渡す。
//
// 起動: Supabase の cron（pg_cron + pg_net、または Scheduled Functions）で
//   毎日 例) 09:00 JST = 00:00 UTC にこの関数を POST 実行する。SETUP.md 参照。

import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2";

const ROW_ID = "kodai";
const TZ_OFFSET_MIN = 9 * 60; // JST

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
function json(obj: unknown, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { ...CORS, "Content-Type": "application/json" },
  });
}

/* ---- 日付ユーティリティ（クライアントと同じ計算） ---- */
function todayJST(): Date {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const jst = new Date(utc + TZ_OFFSET_MIN * 60000);
  return new Date(jst.getFullYear(), jst.getMonth(), jst.getDate());
}
function parseYMD(s: string): Date {
  if (!s) return todayJST();
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}
function toYMD(d: Date): string {
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}
function addMonths(date: Date, n: number): Date {
  const d = new Date(date), day = d.getDate();
  d.setDate(1); d.setMonth(d.getMonth() + n);
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last)); return d;
}
function addInterval(date: Date, value: number, unit: string): Date {
  const d = new Date(date), v = Number(value) || 0;
  if (unit === "day") d.setDate(d.getDate() + v);
  else if (unit === "week") d.setDate(d.getDate() + v * 7);
  else if (unit === "month") return addMonths(date, v);
  else if (unit === "year") return addMonths(date, v * 12);
  return d;
}
type Item = {
  id: string; name: string; emoji?: string;
  intervalValue: number; intervalUnit: string;
  lastDate: string; leadDays?: number; notifiedFor?: string | null;
  needsBooking?: boolean; bookLeadDays?: number | null;
  booked?: boolean; bookNotifiedFor?: string | null;
};
function nextDate(it: Item): Date { return addInterval(parseYMD(it.lastDate), it.intervalValue, it.intervalUnit); }
function daysUntil(it: Item): number {
  return Math.round((nextDate(it).getTime() - todayJST().getTime()) / 86400000);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST" && req.method !== "GET") return json({ error: "POST/GETのみ" }, 405);

  try {
    const pub = Deno.env.get("VAPID_PUBLIC_KEY");
    const priv = Deno.env.get("VAPID_PRIVATE_KEY");
    const subject = Deno.env.get("VAPID_SUBJECT") || "mailto:example@example.com";
    if (!pub || !priv) return json({ error: "VAPIDキーが未設定です（Secretsを確認）" }, 500);
    webpush.setVapidDetails(subject, pub, priv);

    const sb = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    // 状態を読む
    const { data: row, error: e1 } = await sb
      .from("tsugi_state").select("state").eq("id", ROW_ID).maybeSingle();
    if (e1) return json({ error: e1.message }, 500);
    const items: Item[] = (row?.state?.items as Item[]) || [];
    if (!items.length) return json({ ok: true, due: 0, note: "項目なし" });

    // 抽出（いずれも「この周期でまだ通知していない」もののみ）:
    //  visitDue … 予定日が近い／過ぎた
    //  bookDue  … 予約が必要で未予約、かつ予約催促日数に入った
    const visitDue: { it: Item; du: number; cycle: string }[] = [];
    const bookDue: { it: Item; du: number; cycle: string }[] = [];
    for (const it of items) {
      if (!it.intervalValue || !it.lastDate) continue;
      const du = daysUntil(it);
      const cycle = toYMD(nextDate(it));   // この周期の識別子
      const lead = it.leadDays != null ? it.leadDays : 3;
      if (du <= lead && it.notifiedFor !== cycle) visitDue.push({ it, du, cycle });

      const bookLead = it.bookLeadDays != null ? it.bookLeadDays : 30;
      if (it.needsBooking && !it.booked && du <= bookLead && it.bookNotifiedFor !== cycle) {
        bookDue.push({ it, du, cycle });
      }
    }
    if (!visitDue.length && !bookDue.length) return json({ ok: true, due: 0, note: "通知対象なし" });

    // 購読端末
    const { data: subs, error: e2 } = await sb
      .from("tsugi_subs").select("*").eq("who", ROW_ID);
    if (e2) return json({ error: e2.message }, 500);

    // 文面を組み立て（予約催促 → 予定日 の順）
    const sections: string[] = [];
    if (bookDue.length) {
      const lines = bookDue.map(({ it, du }) => {
        const when = du > 0 ? "予定日まであと" + du + "日" : "予定日が近いです";
        return "・" + (it.emoji || "🗓️") + (it.name) + "（" + when + "）";
      });
      sections.push("📅 そろそろ予約を取ろう\n" + lines.join("\n"));
    }
    if (visitDue.length) {
      const lines = visitDue.map(({ it, du }) => {
        const when = du < 0 ? (-du) + "日すぎ" : du === 0 ? "今日" : "あと" + du + "日";
        return "・" + (it.emoji || "🗓️") + (it.name) + "（" + when + "）";
      });
      sections.push("⏰ そろそろ予定日です\n" + lines.join("\n"));
    }
    const body = sections.join("\n\n");
    const payload = JSON.stringify({ title: "⏰ つぎいつ？", body });

    let sent = 0;
    for (const s of subs || []) {
      try {
        await webpush.sendNotification(
          { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
          payload,
        );
        sent++;
      } catch (e) {
        const code = (e as { statusCode?: number })?.statusCode;
        if (code === 410 || code === 404) {
          await sb.from("tsugi_subs").delete().eq("endpoint", s.endpoint);
        } else {
          console.error("push failed:", code, (e as Error)?.message);
        }
      }
    }

    // 通知済みフラグを立てて保存（次の周期まで再通知しない）
    if (sent > 0) {
      const visitMarks = new Map(visitDue.map(d => [d.it.id, d.cycle]));
      const bookMarks = new Map(bookDue.map(d => [d.it.id, d.cycle]));
      for (const it of items) {
        if (visitMarks.has(it.id)) it.notifiedFor = visitMarks.get(it.id)!;
        if (bookMarks.has(it.id)) it.bookNotifiedFor = bookMarks.get(it.id)!;
      }
      const newState = { ...(row?.state || {}), items };
      await sb.from("tsugi_state").upsert({ id: ROW_ID, state: newState, updated_at: new Date().toISOString() });
    }

    return json({ ok: true, visitDue: visitDue.length, bookDue: bookDue.length, sent });
  } catch (e) {
    return json({ error: (e as Error)?.message || String(e) }, 500);
  }
});
