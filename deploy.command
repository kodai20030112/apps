#!/bin/bash
cd "$(dirname "$0")"
echo "=== 制作物アプリを公開します ==="
git add -A
git commit -m "更新 $(date '+%Y-%m-%d %H:%M')" || { echo "変更がありません（公開済み）"; sleep 3; exit 0; }
git push
echo ""
echo "✅ 公開しました！1〜2分後に反映されます。"
echo "→ https://tsumiki-apps.github.io/apps/"
echo ""
echo "（このウィンドウは閉じてOK）"
sleep 5
