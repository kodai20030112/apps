// Supabase Edge Function: generate-recap-email
// Recap（週次リキャップ）の数値から、Leaders宛て送信メールの下書きをAIで生成する。
// LLM: Google Gemini（無料枠）。APIキーはこの関数のSecret(GEMINI_API_KEY)に置き、クライアントには出さない。
//
// デプロイ: Supabaseダッシュボード → Edge Functions → 新規作成「generate-recap-email」にこのコードを貼り付け。
// Secret: Project Settings → Edge Functions → Secrets で GEMINI_API_KEY を登録。

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
    const body = await req.json();
    const data = body?.data || {};
    const lang = body?.lang === "en" ? "en" : "ja";

    const apiKey = Deno.env.get("GEMINI_API_KEY");
    if (!apiKey) return json({ error: "GEMINI_API_KEY が未設定です（SupabaseのSecretsに登録してください）" }, 500);

    const prompt = buildPrompt(data, lang);

    // モデルは無料枠のある gemini-2.5-flash を使用。429や404が出る場合は gemini-flash-latest 等に変更。
    const model = "gemini-2.5-flash";
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    const payload = JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 1024,
        // 2.5系の思考トークンを無効化（本文に予算を回し、高速・低コスト化）
        thinkingConfig: { thinkingBudget: 0 },
      },
    });

    // 503(混雑)/429(レート)は一時的なことが多いので、短い待機で最大3回リトライ
    let r: Response | null = null;
    let j: any = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });
      j = await r.json();
      if (r.ok) break;
      const code = r.status;
      if ((code === 503 || code === 429) && attempt < 2) {
        await new Promise((res) => setTimeout(res, 1200 * (attempt + 1)));
        continue;
      }
      break;
    }
    if (!r || !r.ok) return json({ error: "Gemini APIエラー", detail: j }, 502);

    const text = (j?.candidates?.[0]?.content?.parts || [])
      .map((p: { text?: string }) => p.text || "")
      .join("")
      .trim();

    if (!text) return json({ error: "生成結果が空でした", detail: j }, 502);
    return json({ text });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});

// ---- データ → プロンプト ----
function buildPrompt(d: any, lang: "ja" | "en"): string {
  const facts = factLines(d, lang);

  if (lang === "en") {
    return [
      "You are a retail team member writing a short weekly Recap email to your leader/manager.",
      "Write a professional but warm email in natural English based ONLY on the data below.",
      "",
      "Guidelines:",
      "- Output ONLY the email: first line is `Subject: ...`, then a blank line, then the body.",
      "- Greet the manager by name if provided.",
      "- Lead with what went well (metrics that beat benchmark / goals hit).",
      "- Honestly acknowledge metrics that missed, and add a brief, concrete focus for next week.",
      "- If a personal goal is provided, tie the closing back to it.",
      "- Keep it concise (about 150-220 words). Sign off with the sender's first name.",
      "- Do NOT invent numbers that are not in the data. Do not use markdown bullets or asterisks.",
      "",
      "DATA:",
      facts,
    ].join("\n");
  }

  return [
    "あなたはApple Retailのチームメンバーで、上長(Leader)宛てに週次Recapの共有メールを書きます。",
    "以下のデータ「だけ」を根拠に、丁寧だが堅すぎない自然な日本語のビジネスメールを書いてください。",
    "",
    "ルール:",
    "- 出力はメール本文のみ。1行目は『件名: ...』、次に空行、その後に本文。",
    "- 宛名（上長名）があれば冒頭に入れる。",
    "- まず良かった点（ベンチ超え・Goal達成）に触れる。",
    "- 未達の項目は正直に認め、来週の具体的なフォーカスを短く添える。",
    "- 自分のゴールがあれば締めでそこに結びつける。",
    "- 150〜250字程度で簡潔に。最後は送信者の名前で締める。",
    "- データに無い数字を創作しない。箇条書き記号(*や•)やMarkdownは使わない。",
    "",
    "データ:",
    facts,
  ].join("\n");
}

function factLines(d: any, lang: "ja" | "en"): string {
  const ja = lang === "ja";
  const L: string[] = [];
  const period = `FY${d.fy || "-"} Q${d.q || "-"} Week${d.week || "-"}`;
  L.push((ja ? "送信者: " : "Sender: ") + (d.name || "-"));
  if (d.cm) L.push((ja ? "宛先(上長): " : "Manager: ") + d.cm);
  L.push((ja ? "期間: " : "Period: ") + period);
  if (d.myGoal) L.push((ja ? "自分のゴール: " : "Personal goal: ") + d.myGoal);

  const npsLine = (label: string, n: any) => {
    if (!n || n.total === 0 || n.current === null || n.current === undefined) {
      return `${label}: ${ja ? "回答なし" : "no responses"}`;
    }
    const cur = (n.current > 0 ? "+" : "") + n.current;
    const st = n.achieved
      ? (ja ? "Goal達成" : "goal achieved")
      : (n.need != null
          ? (ja ? `Goalまであと${n.need} Promoter` : `${n.need} promoters short of goal`)
          : (ja ? "Goal未達" : "below goal"));
    return `${label}: ${cur} (Goal ${n.goal}) — ${st} ${ja ? "／回答数" : "/ responses"} ${n.total}`;
  };
  L.push(npsLine(ja ? "Personal NPS" : "Personal NPS", d.personalNps));
  L.push(npsLine(ja ? "Store NPS" : "Store NPS", d.storeNps));

  if (Array.isArray(d.kpis) && d.kpis.length) {
    L.push(ja ? "KPI:" : "KPIs:");
    for (const k of d.kpis) {
      if (k.value == null && k.bench == null) continue;
      const unit = k.unit || "";
      const st = k.value == null || k.bench == null
        ? "-"
        : (k.achieved ? (ja ? "達成" : "achieved") : (ja ? "未達" : "missed"));
      L.push(`  - ${k.label}: ${k.value ?? "-"}${unit} (${ja ? "ベンチ" : "bench"} ${k.bench ?? "-"}${unit}) ${st}`);
    }
  }

  if (Array.isArray(d.actions) && d.actions.length) {
    const names = d.actions.map((a: any) => a.name).filter(Boolean);
    if (names.length) L.push((ja ? "今週のアクション: " : "Actions this week: ") + names.join(", "));
  }
  return L.join("\n");
}
