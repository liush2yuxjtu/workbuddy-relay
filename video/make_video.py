#!/usr/bin/env python3
"""接力包演示视频：真人素材 + 真实运行 relay.py 的界面录制 + 中文配音 + 字幕。
在 Mac mini 上运行：python3 make_video.py  → out/demo.mp4"""
import asyncio, html, json, os, pathlib, shutil, subprocess, sys, time, urllib.request

W, H = 1080, 1920
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
TMP = HERE / "tmp"; TMP.mkdir(exist_ok=True)
RELAY = next(p for p in [HERE / "workbuddy-relay", HERE.parent / "workbuddy-relay"] if p.exists()) / "scripts" / "relay.py"
PY = os.environ.get("RELAY_PY", sys.executable)
VOICE = "zh-CN-XiaoxiaoNeural"
FONT = '"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif'
SERIF = '"Songti SC","Noto Serif CJK SC",serif'

SCENES = [
    ("clip", "39839", "晚上九点，报告还差三页，你想回家接着做。", "报告还差三页，想回家接着做"),
    ("ui", "wechat", "于是又是熟悉的流程：一个个找文件，拖进文件传输助手，回家再一个个下载，还得把需求重新跟 WorkBuddy 讲一遍。", "找文件 → 传 → 下载 → 重讲需求"),
    ("clip", "4526", "文件一多就漏，对话一换就忘。", "文件一多就漏，对话一换就忘"),
    ("ui", "title", "试试这个 WorkBuddy 技能：接力包。", "WorkBuddy 技能：接力包"),
    ("ui", "push", "要走的时候，跟 WorkBuddy 说一句：打个接力包。它会写好交接说明，带上做出来的文件，存进你自己的坚果云。", "要走时说：「打个接力包」"),
    ("clip", "4954", "合上电脑，下班。", "合上电脑，下班"),
    ("clip", "4957", "到家，打开另一台电脑。", "到家，打开另一台电脑"),
    ("ui", "pull", "说一句：接着做上次的。它把文件取回来，读完交接说明，知道你做到哪、定过什么，直接接着干。", "说：「接着做上次的」"),
    ("ui", "install", "不用 GitHub，也不用装软件。复制一段安装口令，粘贴给 WorkBuddy，跟着它设置一次坚果云就好。", "复制安装口令 → 粘贴给 WorkBuddy"),
    ("clip", "14830", "公司做一半，回家一句话接着做。安装口令，看视频最后的网址。", "公司做一半，回家一句话接着做"),
]
URL = "workbuddy-relay.vercel.app"


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    if r.returncode:
        print("CMD FAILED:", cmd, r.stderr[-2000:]); raise SystemExit(1)
    return r.stdout


def dur(p):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


# ---------- 1. 真实运行接力包脚本（两台"电脑" = 两个独立的用户目录 + 本地 WebDAV 中转站）----------
def real_run():
    dav = TMP / "dav"; shutil.rmtree(dav, ignore_errors=True); dav.mkdir()
    srv = subprocess.Popen([sys.executable, "-c", "import sys;from wsgidav.server.server_cli import run;sys.argv=['wsgidav']+sys.argv[1:];run()", "--host", "127.0.0.1", "--port", "18088",
                            "--root", str(dav), "--auth", "anonymous"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    try:
        def run(home, *args, cwd=None):
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), RELAY_DEVICE=home.name)
            r = subprocess.run([PY, str(RELAY), *args], env=env, cwd=cwd, capture_output=True, text=True)
            return (r.stdout + r.stderr).strip()
        a = TMP / "公司电脑"; b = TMP / "家里电脑"
        for d in (a, b): shutil.rmtree(d, ignore_errors=True)
        work = a / "WorkBuddy" / "Q3季度报告"; (work / "图表").mkdir(parents=True)
        (work / "交接.md").write_text("""# 交接：Q3 季度销售报告
## 用户想要什么
给老板的 8 页 PPT，金额口径按含税。
## 已经做完的
- 数据清洗；第 1–5 页图表
## 关键决定和用户的偏好
- 华东单独一页；不放环比，只放同比
## 还没做完的 / 下一步
1. 第 6 页：渠道对比  2. 第 7 页：结论  3. 附录
""", encoding="utf-8")
        (work / "销售明细_清洗后.xlsx").write_bytes(os.urandom(48000))
        (work / "Q3报告_草稿v3.pptx").write_bytes(os.urandom(260000))
        for n in ("华东同比.png", "渠道占比.png"): (work / "图表" / n).write_bytes(os.urandom(90000))
        for home in (a, b):
            print(run(home, "setup", "webdav", "--user", "demo@example.com", "--password", "app-pass", "--url", "http://127.0.0.1:18088/"))
        push = run(a, "push", "--title", "Q3季度报告", "--note", str(work / "交接.md"), "--files",
                   str(work / "销售明细_清洗后.xlsx"), str(work / "Q3报告_草稿v3.pptx"), str(work / "图表"))
        if "✅" not in push: raise SystemExit("push failed: " + push)
        lst = run(b, "list")
        pull = run(b, "pull", "latest")
        pull = pull.split("======== 交接.md ========")[0].strip()
        res = {"push": push, "list": lst, "pull": pull}
        (OUT / "real_run.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return res
    finally:
        srv.terminate()


def clean(s):  # 演示里隐藏本机路径
    out = []
    for line in s.splitlines():
        if "放在：" in line: line = "   放在：WorkBuddy/接力/" + line.split("/")[-1]
        if line.startswith("NOTE_PATH"): continue
        out.append(line)
    return "\n".join(out)


# ---------- 2. 配音 ----------
async def tts_all():
    try:
        import edge_tts
    except ImportError:
        edge_tts = None
    files = []
    for i, (_, _, vo, _) in enumerate(SCENES):
        mp3 = TMP / f"vo{i}.mp3"
        if not mp3.exists():
            ok = False
            if edge_tts:
                try:
                    await edge_tts.Communicate(vo, VOICE, rate="+6%").save(str(mp3)); ok = True
                except Exception as e:
                    print("edge-tts failed:", e)
            if not ok and not shutil.which("say"):
                sh(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t",f"{len(vo)*0.2:.2f}",str(mp3)]); ok = True
            if not ok:
                aiff = TMP / f"vo{i}.aiff"
                sh(["say", "-v", "Tingting", "-r", "200", "-o", str(aiff), vo])
                sh(["ffmpeg", "-y", "-i", str(aiff), str(mp3)])
        files.append(mp3)
    return files


# ---------- 3. 界面场景（HTML 动画，用浏览器录屏）----------
BASE_CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;height:{H}px;overflow:hidden;font-family:{FONT};background:#EEF0EA;color:#16302A}}
.cap{{position:absolute;left:50px;right:50px;bottom:200px;text-align:center;line-height:1.35}}
.cap span{{display:inline;background:#16302A;color:#fff;font-size:54px;font-weight:800;padding:10px 26px;border-radius:16px;box-decoration-break:clone;-webkit-box-decoration-break:clone;box-shadow:0 10px 30px rgba(0,0,0,.25)}}
.win{{position:absolute;left:50px;right:50px;top:300px;background:#fff;border-radius:28px;box-shadow:0 30px 80px -30px rgba(0,0,0,.45);overflow:hidden}}
.bar{{height:84px;background:#F4F6F2;border-bottom:1px solid #DDE2DA;display:flex;align-items:center;gap:14px;padding:0 30px;font-size:32px;font-weight:700}}
.dot{{width:18px;height:18px;border-radius:50%;background:#E0E4DD}}
.body{{padding:40px 36px;display:flex;flex-direction:column;gap:30px;min-height:980px}}
.u{{align-self:flex-end;background:#1E6B4F;color:#fff;border-radius:30px 30px 6px 30px;padding:22px 30px;font-size:40px;max-width:80%}}
.a{{align-self:flex-start;background:#F1F4EF;border-radius:30px 30px 30px 6px;padding:22px 30px;font-size:36px;line-height:1.5;max-width:90%}}
.tool{{background:#16302A;color:#E6EEEA;border-radius:20px;padding:22px 26px;font:28px/1.55 ui-monospace,Menlo,monospace;white-space:pre-wrap}}
.tool .h{{color:#F0B429;font-family:{FONT};font-weight:700;margin-bottom:8px}}
.hide{{opacity:0;transform:translateY(24px)}}
.show{{opacity:1;transform:none;transition:all .45s cubic-bezier(.2,.8,.2,1)}}
.tag{{position:absolute;top:120px;left:0;right:0;text-align:center;font-size:40px;font-weight:800;color:#1E6B4F;letter-spacing:4px}}
"""

TIMELINE_JS = """
<script>
const steps=[...document.querySelectorAll('[data-t]')];
const T0=performance.now();
function tick(){const t=(performance.now()-T0)/1000;
 steps.forEach(el=>{const at=+el.dataset.t; if(t>=at && !el.classList.contains('show')){el.classList.add('show');
   if(el.dataset.type){const full=el.dataset.type;let i=0;el.textContent='';const iv=setInterval(()=>{el.textContent=full.slice(0,++i);if(i>=full.length)clearInterval(iv)},55);}
   if(el.dataset.lines){const lines=JSON.parse(el.dataset.lines);const pre=el.querySelector('.o');let k=0;const iv=setInterval(()=>{pre.textContent+=(k?'\\n':'')+lines[k++];if(k>=lines.length)clearInterval(iv)},260);}
 }});
 requestAnimationFrame(tick)}
tick();
</script>"""


def page(inner, cap, extra_css=""):
    return f"<html><head><meta charset='utf-8'><style>{BASE_CSS}{extra_css}</style></head><body>{inner}<div class='cap'><span>{html.escape(cap)}</span></div>{TIMELINE_JS}</body></html>"


def chat(title, items):
    return f"<div class='win'><div class='bar'><span class='dot'></span><span class='dot'></span><span class='dot'></span>&nbsp;{html.escape(title)}</div><div class='body'>{''.join(items)}</div></div>"


def ui_html(name, cap, d, real):
    if name == "wechat":
        files = ["销售明细_清洗后.xlsx", "Q3报告_草稿v3.pptx", "华东同比.png", "渠道占比.png", "会议纪要.docx", "原始数据_9月.csv", "第5页截图.png"]
        items = []
        for i, f in enumerate(files):
            items.append(f"<div class='u hide' data-t='{0.3 + i * (d * 0.6 / len(files)):.2f}' style='background:#95EC69;color:#111;font-size:34px'>📄 {f}</div>")
        items.append(f"<div class='a hide' data-t='{d*0.72:.2f}' style='background:#FDECEA;color:#B4412F;font-weight:700'>⚠️ 文件过大，发送失败（素材视频 1.4GB）</div>")
        items.append(f"<div class='a hide' data-t='{d*0.85:.2f}'>回家后：新开对话…「我们上次做到哪了？」</div>")
        return page(chat("文件传输助手", items), cap)
    if name == "title":
        inner = f"""<div style='position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:40px;background:#16302A;color:#F5F6F1'>
        <div class='hide' data-t='0.1' style='width:300px;height:96px;border-radius:48px;background:#F0B429;transform:rotate(-18deg)'></div>
        <div class='hide' data-t='0.4' style='font-family:{SERIF};font-size:150px;font-weight:900;letter-spacing:10px'>接力包</div>
        <div class='hide' data-t='0.8' style='font-size:46px;opacity:.8'>WorkBuddy 跨电脑接力技能</div></div>"""
        return page(inner, cap)
    if name in ("push", "pull"):
        if name == "push":
            title, said = "WorkBuddy · 公司电脑", "下班了，打个接力包"
            out = clean(real["push"]); head = "▶ 运行技能：接力包 · 打包上传"
            reply = "已经打好接力包啦：交接说明 + 4 个文件。<br>到另一台电脑说一句 <b>「接着做上次的」</b> 就行。"
            extra = ""
        else:
            title, said = "WorkBuddy · 家里电脑", "接着做上次的"
            out = clean(real["pull"]); head = "▶ 运行技能：接力包 · 取回"
            reply = "上次做到 <b>第 5 页</b>。你定过：华东单独一页，只放同比。<br>下一步做第 6–8 页（渠道对比、结论、附录），我直接开始？"
            extra = ""
        lines = out.splitlines()
        items = [f"<div class='u hide' data-t='0.3' data-type='{html.escape(said)}'></div>",
                 f"<div class='tool hide' data-t='{d*0.25:.2f}' data-lines='{html.escape(json.dumps(lines, ensure_ascii=False))}'><div class='h'>{head}</div><span class='o'></span></div>",
                 f"<div class='a hide' data-t='{d*0.62:.2f}'>{reply}</div>", extra]
        return page(chat(title, items), cap)
    if name == "install":
        inner = f"""<div class='tag'>第一次：每台电脑装一次</div>
        <div class='win' style='top:230px'><div class='bar'>&nbsp;{URL}</div><div class='body' style='min-height:0'>
          <div style='font-family:{SERIF};font-size:64px;font-weight:900'>做了一半的活，<br>换台电脑一句话接着做。</div>
          <div class='hide' data-t='0.6' style='align-self:flex-start;background:#F0B429;color:#3B2A00;font-weight:800;font-size:40px;border-radius:18px;padding:22px 34px'>复制安装口令</div>
          <div class='hide' data-t='1.4' style='color:#1E6B4F;font-weight:800;font-size:34px'>✓ 已复制，去 WorkBuddy 粘贴吧</div></div></div>
        <div class='win' style='top:960px'><div class='bar'>&nbsp;WorkBuddy</div><div class='body' style='min-height:0'>
          <div class='u hide' data-t='{d*0.35:.2f}' style='font-size:30px'>请帮我安装一个 WorkBuddy 技能「接力包」… <span style='opacity:.7'>（粘贴）</span></div>
          <div class='a hide' data-t='{d*0.6:.2f}'>✅ 安装好了！我们花 2 分钟连上你的坚果云：<br>① 打开 jianguoyun.com 注册 ② 生成「应用密码」③ 发给我</div></div></div>"""
        return page(inner, cap)
    raise ValueError(name)


async def record_ui(name, cap, d, real, out):
    from playwright.async_api import async_playwright
    htmlp = TMP / f"{name}.html"; htmlp.write_text(ui_html(name, cap, d, real), encoding="utf-8")
    vdir = TMP / f"rec_{name}"; shutil.rmtree(vdir, ignore_errors=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(vdir), record_video_size={"width": W, "height": H})
        pg = await ctx.new_page()
        t0 = time.time()
        await pg.goto(htmlp.as_uri())
        await pg.wait_for_timeout(int((d + 0.6) * 1000))
        await ctx.close(); await b.close()
    webm = next(vdir.glob("*.webm"))
    lead = 0.35  # 跳过页面加载的白屏
    sh(["ffmpeg", "-y", "-ss", str(lead), "-i", str(webm), "-t", f"{d:.2f}", "-vf", f"scale={W}:{H},fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", str(out)])


# ---------- 4. 真人素材片段 ----------
def fetch_clip(cid):
    dst = TMP / f"mixkit_{cid}.mp4"
    if dst.exists() and dst.stat().st_size > 10000: return dst
    for q in ("1080", "720", "360"):
        url = f"https://assets.mixkit.co/videos/{cid}/{cid}-{q}.mp4"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f: shutil.copyfileobj(r, f)
            if dst.stat().st_size > 10000: print("clip", cid, q); return dst
        except Exception as e:
            print("clip fail", url, e)
    raise SystemExit(f"cannot fetch clip {cid}")


async def caption_png(cap, out, cta=False):
    from playwright.async_api import async_playwright
    extra = ""
    if cta:
        extra = f"""<div style='position:absolute;left:60px;right:60px;top:560px;background:rgba(22,48,42,.92);border-radius:36px;padding:60px 40px;text-align:center;color:#F5F6F1'>
          <div style='width:220px;height:70px;border-radius:35px;background:#F0B429;transform:rotate(-18deg);margin:0 auto 40px'></div>
          <div style='font-family:{SERIF};font-size:120px;font-weight:900;letter-spacing:8px'>接力包</div>
          <div style='font-size:42px;margin-top:20px;opacity:.85'>WorkBuddy 跨电脑接力技能</div>
          <div style='margin-top:50px;font-size:48px;font-weight:800;color:#F0B429'>{URL}</div>
          <div style='font-size:34px;margin-top:14px;opacity:.75'>打开网页 → 复制安装口令 → 粘贴给 WorkBuddy</div></div>"""
    doc = f"<html><head><meta charset='utf-8'><style>{BASE_CSS} body{{background:transparent}}</style></head><body>{extra}<div class='cap'><span>{html.escape(cap)}</span></div></body></html>"
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": W, "height": H})
        await pg.set_content(doc); await pg.screenshot(path=str(out), omit_background=True); await b.close()


async def make_clip(cid, cap, d, out, idx):
    src = fetch_clip(cid)
    png = TMP / f"cap{idx}.png"; await caption_png(cap, png, cta=(idx == len(SCENES) - 1))
    sd = dur(src); start = max(0.0, min(1.0, sd - d - 0.1))
    zoom = "1.0+0.0006*on" if idx % 2 == 0 else "1.06-0.0006*on"   # 轻推/轻拉，像剪辑师手调的
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,"
          f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,"
          f"eq=saturation=1.08:contrast=1.04[v];[v][1:v]overlay=0:0,format=yuv420p")
    loop = ["-stream_loop", "-1"] if sd < d + start else []
    sh(["ffmpeg", "-y", *loop, "-ss", f"{start:.2f}", "-i", str(src), "-i", str(png), "-filter_complex", vf, "-t", f"{d:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", str(out)])


async def main():
    real = real_run()
    vos = await tts_all()
    segs = []
    for i, (kind, ref, vo, cap) in enumerate(SCENES):
        d = dur(vos[i]) + 0.45
        seg = TMP / f"seg{i}.mp4"
        if kind == "ui":
            await record_ui(ref, cap, d, real, seg)
        else:
            await make_clip(ref, cap, d, seg, i)
        segav = TMP / f"segav{i}.mp4"
        sh(["ffmpeg", "-y", "-i", str(seg), "-i", str(vos[i]), "-filter_complex", f"[1:a]adelay=150|150,apad,atrim=0:{d:.2f}[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{d:.2f}", str(segav)])
        segs.append(segav); print("seg", i, kind, ref, f"{d:.1f}s")
    lst = TMP / "concat.txt"; lst.write_text("".join(f"file '{s}'\n" for s in segs))
    raw = TMP / "raw.mp4"
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(raw)])
    final = OUT / "demo.mp4"
    sh(["ffmpeg", "-y", "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
        "-maxrate", "2500k", "-bufsize", "5000k", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final)])
    sh(["ffmpeg", "-y", "-ss", "8", "-i", str(final), "-frames:v", "1", "-q:v", "4", str(OUT / "poster.jpg")])
    print("DONE", final, f"{dur(final):.1f}s", f"{final.stat().st_size/1e6:.1f}MB")


if __name__ == "__main__":
    asyncio.run(main())
