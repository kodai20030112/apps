# -*- coding: utf-8 -*-
"""各サブアプリHTMLに「つみきへ戻る」導線を注入する。

設計（スワイプのみ・見えるボタンは置かない版）:
  - 戻る操作は「左端から右へスワイプ＝戻る」エッジスワイプ・ジェスチャーのみ（iOS純正の戻る操作）。
    指の動きに追従するチェブロン(‹)が左端中央に出て、しきい値を超えて離すと index.html へ戻る。
  - **見える「‹ つみき」ボタン（ピル）は置かない。** 各アプリ自身が左上に持つ「‹ 戻る」等の
    UIと重なって見栄えが悪くなるため、ユーザー指定で常時表示ボタンは廃止した（2026-06-07）。
    戻り導線はスワイプのジェスチャーに一本化する。

表示条件（スクリプト側で判定）:
  - ホーム画面の全画面モード（standalone）で開いている
  - かつ つみきのトップ（同一オリジン）から来ている（document.referrer で判定）
この2つを満たすときだけスワイプ導線を有効化。共有リンクを直接開いた相手や、普通のSafari
（ブラウザ自身の戻る操作がある）では有効化しない。

既にマーカーがあるファイルは“旧ブロックを新版へ置換”する。index.html は対象外。
"""
import glob
import re

MARKER = "tsumiki-back-button"

SNIPPET = """<!-- tsumiki-back-button -->
<style>
  #tsumikiEdge{position:fixed; top:0; bottom:0; left:0; width:22px; z-index:999;}
  #tsumikiPeek{
    position:fixed; top:50%; left:0; z-index:1001; margin-top:-23px;
    width:46px; height:46px; display:flex; align-items:center; justify-content:center;
    background:rgba(255,255,255,.92);
    -webkit-backdrop-filter:saturate(180%) blur(14px); backdrop-filter:saturate(180%) blur(14px);
    border:1px solid rgba(0,0,0,.06); border-radius:50%;
    box-shadow:0 6px 20px rgba(0,0,0,.18);
    color:#0071e3; font-size:24px; font-weight:600; line-height:1;
    font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Helvetica Neue",Arial,sans-serif;
    transform:translateX(-70px) scale(.8); opacity:0; pointer-events:none;
  }
</style>
<div id="tsumikiEdge"></div>
<div id="tsumikiPeek">‹</div>
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
    if(!(standalone && fromTsumiki)) return;

    var peek = document.getElementById('tsumikiPeek');
    var edge = document.getElementById('tsumikiEdge');

    function goBack(){ location.href = 'index.html'; }

    /* --- 左端エッジスワイプで戻る（iOS純正の戻る操作。見えるボタンは置かない） --- */
    var sx=0, sy=0, prog=0, dragging=false, W=window.innerWidth;
    var TRIGGER = Math.min(120, W*0.32);
    window.addEventListener('resize', function(){ W=window.innerWidth; TRIGGER=Math.min(120, W*0.32); });

    function reset(){
      dragging = false; prog = 0;
      peek.style.transition = 'transform .25s ease, opacity .25s ease';
      peek.style.transform = 'translateX(-70px) scale(.8)';
      peek.style.opacity = 0;
    }
    function start(e){
      var t = e.touches ? e.touches[0] : e;
      if(t.clientX > 26) return;
      sx = t.clientX; sy = t.clientY; prog = 0; dragging = true;
      peek.style.transition = 'none';
    }
    function move(e){
      if(!dragging) return;
      var t = e.touches ? e.touches[0] : e;
      var dx = t.clientX - sx, dy = t.clientY - sy;
      if(Math.abs(dy) > Math.abs(dx) + 12){ reset(); return; }
      if(dx < 0) dx = 0;
      prog = Math.min(dx / TRIGGER, 1);
      peek.style.transform = 'translateX(' + (-70 + prog*82) + 'px) scale(' + (0.8 + prog*0.2) + ')';
      peek.style.opacity = prog;
      if(dx > 6 && e.cancelable) e.preventDefault();
    }
    function end(){
      if(!dragging) return;
      dragging = false;
      if(prog >= 0.999){
        peek.style.transition = 'transform .25s ease, opacity .25s ease';
        peek.style.transform = 'translateX(20px) scale(1.05)';
        peek.style.opacity = 1;
        goBack();
      }else{
        reset();
      }
    }
    edge.addEventListener('touchstart', start, {passive:true});
    window.addEventListener('touchmove', move, {passive:false});
    window.addEventListener('touchend', end, {passive:true});
    window.addEventListener('touchcancel', end, {passive:true});
  })();
</script>
<!-- /tsumiki-back-button -->
"""

# 旧ブロック（マーカー間）を丸ごと置換するための正規表現
BLOCK_RE = re.compile(
    r"<!-- tsumiki-back-button -->.*?<!-- /tsumiki-back-button -->\s*",
    re.DOTALL,
)

for path in sorted(glob.glob("*.html")):
    if path == "index.html":
        continue
    html = open(path, encoding="utf-8").read()
    if MARKER in html:
        new = BLOCK_RE.sub(SNIPPET, html, count=1)
        open(path, "w", encoding="utf-8").write(new)
        print(f"↻ {path}: 戻る導線を新版（スワイプのみ）に更新")
        continue
    if "</body>" not in html:
        print(f"! {path}: </body> が見つからず注入できませんでした")
        continue
    new = html.replace("</body>", SNIPPET + "</body>", 1)
    open(path, "w", encoding="utf-8").write(new)
    print(f"✓ {path}: 戻る導線を注入（スワイプのみ）")
