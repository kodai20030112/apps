# -*- coding: utf-8 -*-
"""各サブアプリHTMLの </body> 直前に「‹ つみき」戻るボタンを注入する。

表示条件（スクリプト側で判定）:
  - ホーム画面の全画面モード（standalone）で開いている
  - かつ つみきのトップ（同一オリジン）から来ている（document.referrer で判定）
この2つを満たすときだけ表示。共有リンクを直接開いた相手や、普通のSafariには出ない。

二重注入を防ぐため、既にマーカーがあるファイルはスキップ。index.html は対象外。
"""
import glob

MARKER = "tsumiki-back-button"

SNIPPET = """<!-- tsumiki-back-button -->
<style>
  #tsumikiBack{
    position:fixed; top:calc(env(safe-area-inset-top) + 8px); left:12px; z-index:1000;
    display:none; align-items:center; gap:3px;
    background:rgba(255,255,255,.82);
    -webkit-backdrop-filter:saturate(180%) blur(12px); backdrop-filter:saturate(180%) blur(12px);
    border:1px solid rgba(0,0,0,.08); border-radius:999px;
    padding:7px 14px 7px 11px; font-size:14px; font-weight:600;
    color:#0071e3; text-decoration:none; line-height:1;
    font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Helvetica Neue",Arial,sans-serif;
    box-shadow:0 4px 14px rgba(0,0,0,.12); -webkit-tap-highlight-color:transparent;
  }
  #tsumikiBack:active{transform:scale(.96);}
</style>
<a id="tsumikiBack" href="index.html">‹ つみき</a>
<script>
  (function(){
    var standalone = (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches)
      || window.navigator.standalone === true;
    var fromTsumiki = false;
    try{
      if(document.referrer){
        var r = new URL(document.referrer);
        fromTsumiki = (r.origin === location.origin);
      }
    }catch(e){}
    if(standalone && fromTsumiki){
      var b = document.getElementById('tsumikiBack');
      if(b) b.style.display = 'inline-flex';
    }
  })();
</script>
<!-- /tsumiki-back-button -->
"""

for path in sorted(glob.glob("*.html")):
    if path == "index.html":
        continue
    html = open(path, encoding="utf-8").read()
    if MARKER in html:
        print(f"- {path}: 既に注入済み・スキップ")
        continue
    if "</body>" not in html:
        print(f"! {path}: </body> が見つからず注入できませんでした")
        continue
    new = html.replace("</body>", SNIPPET + "</body>", 1)
    open(path, "w", encoding="utf-8").write(new)
    print(f"✓ {path}: 戻るボタンを注入")
