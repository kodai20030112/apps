#!/usr/bin/env python3
"""日報メール生成＆送信スクリプト（GitHub Actions用）。

その日（日本時間）の git コミットを集計し、Kodai指定フォーマットの日報を作って
Gmail SMTP で本人宛に送信する。AIは使わず、コミットメッセージをそのまま整形する。

必要な環境変数（GitHub Secrets で設定）:
    SMTP_USER          送信元Gmailアドレス（例: kodai.20030112@gmail.com）
    SMTP_APP_PASSWORD  Googleアプリパスワード（16文字）
    MAIL_TO            宛先（未設定なら SMTP_USER と同じ）

リポジトリは fetch-depth: 0 でチェックアウトされている前提（git log を全部読むため）。
"""
import os
import smtplib
import subprocess
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def get_today_commits():
    """日本時間で「今日」の日付に作られたコミットを (時刻, 件名) のリストで返す。"""
    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")

    # 直近2日分だけ取り出して JST で今日のものに絞る（runnerのTZに依存しないようISO日時で判定）
    result = subprocess.run(
        [
            "git", "log",
            "--since=2 days ago",
            "--no-merges",
            "--pretty=format:%aI\x1f%s",
        ],
        capture_output=True, text=True,
    )
    commits = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or "\x1f" not in line:
            continue
        aiso, subject = line.split("\x1f", 1)
        try:
            dt = datetime.fromisoformat(aiso).astimezone(JST)
        except ValueError:
            continue
        if dt.strftime("%Y-%m-%d") == today:
            commits.append((dt, subject.strip()))
    commits.sort(key=lambda x: x[0])
    return now, commits


def build_body(now, commits):
    if not commits:
        return "お疲れ様です！今日は何もサポートしませんでした！"

    n = len(commits)
    lines = [f"お疲れ様です！今日は{n}個のサポートをしました。", ""]
    for i, (_, subject) in enumerate(commits, 1):
        lines.append(f"{i}個目→{subject}")
        lines.append("")
    lines.append("今日もおつかれさまでした😊")
    return "\n".join(lines).rstrip() + "\n"


def main():
    smtp_user = (os.environ.get("SMTP_USER") or "").strip()
    app_password = (os.environ.get("SMTP_APP_PASSWORD") or "").strip()
    to_addr = (os.environ.get("MAIL_TO") or smtp_user).strip()

    if not smtp_user or not app_password:
        print("ERROR: SMTP_USER / SMTP_APP_PASSWORD が未設定です（GitHub Secretsを確認）", file=sys.stderr)
        return 1

    now, commits = get_today_commits()
    today = now.strftime("%Y-%m-%d")
    body = build_body(now, commits)

    print(f"[daily-report] {today} JST / commits today: {len(commits)}")
    print("---- body preview ----")
    print(body)
    print("----------------------")

    msg = EmailMessage()
    msg["Subject"] = f"📋 日報 {today}"
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(smtp_user, app_password)
            server.send_message(msg)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: 送信失敗: {e}", file=sys.stderr)
        return 1

    print("SENT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
