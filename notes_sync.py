#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
index.html の categories から全アプリを読み取り、
Mac の「メモ」アプリに「🧱 つみき アプリ一覧」を1枚作成／上書きする。
メモは iCloud で iPhone に自動同期されるので、iPhone のメモにも反映される。
"""

import os
import re
import subprocess
import tempfile
from datetime import datetime

BASE_URL = "https://tsumiki-apps.github.io/apps/"
NOTE_TITLE = "🧱 つみき アプリ一覧"
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")


def parse_apps(html):
    """index.html の categories からカテゴリ・アプリを順番通りに取り出す。"""
    # categories = [ ... ]; の中身を取得
    m = re.search(r"const\s+categories\s*=\s*\[(.*?)\];", html, re.S)
    block = m.group(1) if m else html

    result = []  # [(label, emoji, [(emoji,title,desc,href), ...]), ...]
    # 各カテゴリ {label:"...", apps:[...]} を順に拾う
    for cat in re.finditer(
        r'emoji:"([^"]*)",\s*label:"([^"]*)",\s*apps:\[(.*?)\]\s*\}', block, re.S
    ):
        cat_emoji, label, apps_block = cat.group(1), cat.group(2), cat.group(3)
        apps = []
        for a in re.finditer(
            r'\{\s*emoji:"([^"]*)",\s*title:"([^"]*)",\s*desc:"([^"]*)",\s*href:"([^"]*)"\s*\}',
            apps_block,
            re.S,
        ):
            apps.append(a.groups())  # (emoji, title, desc, href)
        result.append((label, cat_emoji, apps))
    return result


def build_body(categories):
    """メモ用の HTML 本文を組み立てる。1行目がメモのタイトルになる。
    URL は素のテキストで入れる（Notes が自動でタップ可能なリンクにする）。"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [f"<div><b>{NOTE_TITLE}</b></div>", "<div><br></div>"]
    # つみきトップページのURLを先頭に入れる（各アプリと同じく素のテキスト）
    parts.append("<div>🧱 つみき トップ</div>")
    parts.append(f"<div>{BASE_URL}</div>")
    parts.append("<div><br></div>")
    total = 0
    for label, cat_emoji, apps in categories:
        parts.append(f"<div><b>{cat_emoji} {label}</b></div>")
        for emoji, title, desc, href in apps:
            total += 1
            url = BASE_URL + href
            # タイトル行 → URL行 → 空行。空行でURLを孤立させると
            # iOS/Notes がデータ検出で URL をタップ可能リンクに変換する。
            parts.append(f"<div>{emoji} {title}</div>")
            parts.append(f"<div>{url}</div>")
            parts.append("<div><br></div>")
    parts.append(f"<div>計 {total} 個 ／ 更新 {today}</div>")
    return "\n".join(parts)


APPLESCRIPT = r'''
on run argv
    set bodyFile to item 1 of argv
    set noteTitle to item 2 of argv
    set fh to open for access (POSIX file bodyFile)
    set theBody to (read fh as «class utf8»)
    close access fh
    tell application "Notes"
        set targetNote to missing value
        repeat with n in notes
            if name of n is noteTitle then
                set targetNote to n
                exit repeat
            end if
        end repeat
        if targetNote is missing value then
            make new note with properties {body:theBody}
        else
            set body of targetNote to theBody
        end if
    end tell
end run
'''


def main():
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    categories = parse_apps(html)
    if not categories:
        print("⚠️ index.html からアプリを読み取れませんでした。")
        return
    body = build_body(categories)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as bf:
        bf.write(body)
        body_path = bf.name
    with tempfile.NamedTemporaryFile(
        "w", suffix=".applescript", delete=False, encoding="utf-8"
    ) as sf:
        sf.write(APPLESCRIPT)
        script_path = sf.name

    try:
        subprocess.run(
            ["osascript", script_path, body_path, NOTE_TITLE],
            check=True,
        )
        n = sum(len(apps) for _, _, apps in categories)
        print(f"✅ メモを更新しました（{n}個のアプリ）→ iPhoneのメモにも同期されます")
    finally:
        os.unlink(body_path)
        os.unlink(script_path)


if __name__ == "__main__":
    main()
