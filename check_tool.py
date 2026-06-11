#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""チェックルーム — 公開前のアプリをiPhone実機で確認するための仕組み。

修正中のアプリを「check-◯◯.html」という別名コピーとして同じGitHub Pagesに置き、
本番ファイルには触れずに実機で操作確認できるようにする。
一覧ページ check.html（チェックルーム）も自動で作り直す。

使い方:
  python3 check_tool.py add forecast.html money.html   # チェック版を配置/更新
  python3 check_tool.py remove forecast                 # 1件だけ撤去
  python3 check_tool.py clear                           # 全件撤去
※このスクリプトはファイルを置く/消すだけ。commit & push は別途行う。
"""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "check.html"
JST = ZoneInfo("Asia/Tokyo")

# チェック版だと一目で分かる小さな帯。pointer-events:none なので操作の邪魔はしない
BADGE = (
    '<div id="tsumikiCheckBadge" style="position:fixed;'
    'top:env(safe-area-inset-top,0px);left:50%;transform:translateX(-50%);'
    'z-index:2147483647;pointer-events:none;background:rgba(255,122,24,.92);'
    "color:#fff;font:700 11px/1 -apple-system,'Hiragino Sans',sans-serif;"
    'padding:4px 12px;border-radius:0 0 9px 9px;letter-spacing:.1em;">'
    "チェック版</div>"
)


def app_title(html: str, fallback: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return m.group(1).strip() if m else fallback


def inject_badge(html: str) -> str:
    if "tsumikiCheckBadge" in html:
        return html
    i = html.lower().rfind("</body>")
    return html[:i] + BADGE + "\n" + html[i:] if i != -1 else html + BADGE


def add(files):
    for f in files:
        src = ROOT / f
        if not src.exists():
            sys.exit(f"見つかりません: {f}")
        if src.name.startswith("check-"):
            sys.exit(f"チェック版そのものは指定できません: {f}")
        dst = ROOT / f"check-{src.name}"
        html = src.read_text(encoding="utf-8")
        dst.write_text(inject_badge(html), encoding="utf-8")
        print(f"✓ {dst.name} を配置")


def remove(names):
    for n in names:
        n = n.removeprefix("check-").removesuffix(".html")
        p = ROOT / f"check-{n}.html"
        if p.exists():
            p.unlink()
            print(f"✓ {p.name} を撤去")


def clear():
    for p in ROOT.glob("check-*.html"):
        p.unlink()
        print(f"✓ {p.name} を撤去")


def relink_check_files():
    """チェック版の中のアプリ間リンクを、チェック版があるものはチェック版同士で繋ぐ。
    （例: check-forecast.html 内の money.html へのリンク → check-money.html）"""
    present = {p.stem.removeprefix("check-") for p in ROOT.glob("check-*.html")}
    for p in ROOT.glob("check-*.html"):
        html = p.read_text(encoding="utf-8")
        # いったん全部素のリンクに戻してから（撤去済みチェック版へのリンク切れ防止）
        html = re.sub(r'href="check-([\w.-]+?)\.html"', r'href="\1.html"', html)
        html = re.sub(
            r'href="([\w.-]+?)\.html"',
            lambda m: f'href="check-{m.group(1)}.html"' if m.group(1) in present else m.group(0),
            html,
        )
        p.write_text(html, encoding="utf-8")


def rebuild_index():
    relink_check_files()
    items = []
    for p in sorted(ROOT.glob("check-*.html")):
        html = p.read_text(encoding="utf-8")
        ts = datetime.fromtimestamp(p.stat().st_mtime, JST).strftime("%-m/%-d %H:%M")
        items.append((p.name, app_title(html, p.stem), ts))

    if items:
        cards = "\n".join(
            f'<a class="card" href="{name}">'
            f'<div><div class="t">{title}</div><div class="s">{name} ・ {ts} 更新</div></div>'
            f'<div class="ch">›</div></a>'
            for name, title, ts in items
        )
        body = f'<div class="list">{cards}</div>'
        hint = ("<p class=\"hint\">✅ 確認できたら Claude に「OK、公開して」と伝えてください。<br>"
                "🔧 直したい点があれば、そのまま言葉で伝えてもらえれば修正します。</p>")
    else:
        body = '<div class="empty">いまチェック待ちのアプリはありません</div>'
        hint = ""

    INDEX.write_text(f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>チェックルーム</title>
<link rel="apple-touch-icon" href="icons/icon-check.png">
<meta name="apple-mobile-web-app-title" content="チェック">
<style>
:root{{color-scheme:light dark}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,'Hiragino Sans',sans-serif;background:#f4f6fa;color:#1c2433;
  padding:calc(env(safe-area-inset-top,0px) + 28px) 18px 48px;min-height:100vh}}
h1{{font-size:22px;margin-bottom:4px}}
.sub{{font-size:13px;color:#6b7689;margin-bottom:22px}}
.list{{display:flex;flex-direction:column;gap:12px}}
.card{{display:flex;align-items:center;justify-content:space-between;gap:12px;
  background:#fff;border-radius:16px;padding:16px 18px;text-decoration:none;color:inherit;
  box-shadow:0 1px 4px rgba(20,30,60,.08)}}
.card:active{{transform:scale(.98)}}
.t{{font-size:17px;font-weight:700}}
.s{{font-size:12px;color:#8a93a5;margin-top:4px}}
.ch{{font-size:22px;color:#c2c9d6}}
.empty{{text-align:center;color:#8a93a5;font-size:15px;padding:64px 0}}
.hint{{font-size:13px;color:#6b7689;line-height:1.9;margin-top:26px}}
@media(prefers-color-scheme:dark){{
  body{{background:#11151d;color:#e8ecf4}}
  .card{{background:#1c2230;box-shadow:none}}
  .sub,.s,.empty,.hint{{color:#8d97ab}}
}}
</style>
</head>
<body>
<h1>🔍 チェックルーム</h1>
<p class="sub">公開前のアプリをここで実機チェックできます</p>
{body}
{hint}
</body>
</html>
""", encoding="utf-8")
    print(f"✓ check.html を更新（{len(items)}件）")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "add" and len(sys.argv) > 2:
        add(sys.argv[2:])
    elif cmd == "remove" and len(sys.argv) > 2:
        remove(sys.argv[2:])
    elif cmd == "clear":
        clear()
    else:
        sys.exit(__doc__)
    rebuild_index()
