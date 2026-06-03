# -*- coding: utf-8 -*-
"""Workジャンルの各アプリの </head> 直前に career.js の読み込みを注入する。
二重注入は MARKER で防ぐ。"""
MARKER = 'src="career.js"'
SNIPPET = '<script src="career.js"></script>\n'

WORK_APPS = ["nps", "recap", "recognition", "grownote", "team5whys",
             "reflection", "vault", "osusowake", "schedule"]

for stem in WORK_APPS:
    path = stem + ".html"
    html = open(path, encoding="utf-8").read()
    if MARKER in html:
        print(f"- {path}: 既に注入済み・スキップ")
        continue
    if "</head>" not in html:
        print(f"! {path}: </head> が無く注入できません")
        continue
    html = html.replace("</head>", SNIPPET + "</head>", 1)
    open(path, "w", encoding="utf-8").write(html)
    print(f"✓ {path}: career.js を注入")
