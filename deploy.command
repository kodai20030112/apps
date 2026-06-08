#!/bin/bash
cd "$(dirname "$0")"
echo "=== 制作物アプリを公開します ==="

# 変更があればコミット。無くても止めずに進む（コミット済みでも公開できるように）
git add -A
if git diff --cached --quiet; then
  echo "新しい変更はありません。未公開分があれば公開します。"
else
  git commit -m "更新 $(date '+%Y-%m-%d %H:%M')"
fi

# いつ実行しても確実に公開する（最新まで反映済みなら push は何もしないだけ）
echo ""
echo "🚀 公開中…"
if git push; then
  echo "公開OK"
else
  echo "⚠️ 公開（push）に失敗しました。ネット接続を確認してもう一度お試しください。"
  echo "（このウィンドウは閉じてOK）"
  sleep 8
  exit 1
fi

# メモ更新は毎回実行する
echo ""
echo "📝 iPhoneのメモを更新中…"
python3 notes_sync.py || echo "（メモ更新はスキップしました）"

echo ""
echo "✅ 公開しました！1〜2分後に反映されます。"
echo "→ https://tsumiki-apps.github.io/apps/"
echo ""
echo "（このウィンドウは閉じてOK）"
sleep 5
