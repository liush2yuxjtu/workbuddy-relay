#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接力包 relay.py —— 让 WorkBuddy 的工作在多台电脑之间接力（不需要 GitHub / Google Drive / Notion）

只用 Python 标准库。两种"中转站"：
  webdav : 坚果云等支持 WebDAV 的国内网盘（推荐，免装客户端）
  folder : 任何会自动同步的文件夹（坚果云/百度网盘同步空间/OneDrive/iCloud）或 U 盘

用法：
  relay.py setup webdav --user 邮箱 --password 应用密码 [--url https://dav.jianguoyun.com/dav/]
  relay.py setup folder --path "D:/坚果云/WorkBuddy接力"
  relay.py status
  relay.py push --title 主题 --note 交接.md [--files 文件或文件夹 ...]
  relay.py list [-n 10]
  relay.py pull [包名|latest] [--to 目录]
"""
import argparse, base64, datetime, json, os, platform, re, shutil, socket, ssl, sys
import tempfile, urllib.error, urllib.parse, urllib.request, zipfile
import xml.etree.ElementTree as ET

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(HOME, ".workbuddy-relay")
CONF = os.path.join(CONF_DIR, "config.json")
DEFAULT_URL = "https://dav.jianguoyun.com/dav/"
ROOT = "WorkBuddy接力"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".DS_Store", ".idea"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
MAX_FILE = 400 * 1024 * 1024  # 坚果云单文件上限 500MB，留余量

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def die(msg, code=1):
    print("❌ " + msg)
    sys.exit(code)


def human(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def load_conf():
    if not os.path.exists(CONF):
        die("还没设置中转站。请先运行 setup（坚果云或同步文件夹）。", 2)
    with open(CONF, encoding="utf-8") as f:
        return json.load(f)


def save_conf(c):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONF, 0o600)
    except Exception:
        pass


def device_name():
    name = os.environ.get("RELAY_DEVICE") or os.environ.get("COMPUTERNAME", "")
    if not name and platform.system() == "Darwin":
        try:
            import subprocess
            name = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            name = ""
    name = name or socket.gethostname().split(".")[0]
    name = re.sub(r"[^\w\-]", "", name)[:20]
    return "我的电脑" if (not name or name.isdigit()) else name


def safe(s):
    s = re.sub(r'[\\/:*?"<>|\s]+', "-", s.strip())
    return s.strip("-")[:40] or "未命名"


# ---------------- 中转站：WebDAV ----------------
class WebDAV:
    def __init__(self, c):
        self.base = c["url"].rstrip("/") + "/"
        tok = base64.b64encode(f'{c["user"]}:{c["password"]}'.encode()).decode()
        self.auth = "Basic " + tok
        self.root = c.get("root", ROOT)
        self.ctx = ssl.create_default_context()

    def _url(self, *parts):
        segs = [self.root] + [p for p in parts if p]
        return self.base + "/".join(urllib.parse.quote(s) for s in segs)

    def req(self, method, url, data=None, headers=None, ok=(200, 201, 204, 207)):
        h = {"Authorization": self.auth, "User-Agent": "workbuddy-relay/" + VERSION}
        h.update(headers or {})
        r = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, context=self.ctx, timeout=120) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            if e.code in ok:
                return e.code, e.read()
            if e.code == 401:
                die("账号或应用密码不对（注意：要用坚果云『第三方应用密码』，不是登录密码）。")
            if e.code in (403, 503, 429):
                die(f"网盘拒绝了请求（{e.code}），可能是请求太频繁或空间/流量用完，过半小时再试。")
            return e.code, b""
        except urllib.error.URLError as e:
            die(f"连不上网盘：{e.reason}。请检查网络。")

    def ensure_root(self):
        code, _ = self.req("MKCOL", self._url(), ok=(201, 405, 301))
        return code in (201, 405, 301, 200)

    def test(self):
        code, _ = self.req("PROPFIND", self.base, headers={"Depth": "0"}, ok=(207, 200))
        if code not in (207, 200):
            die(f"连接测试失败（{code}）。")
        self.ensure_root()

    def put(self, local, name):
        with open(local, "rb") as f:
            data = f.read()
        code, _ = self.req("PUT", self._url(name), data=data,
                           headers={"Content-Type": "application/zip"})
        if code not in (200, 201, 204):
            die(f"上传失败（{code}）。")

    def list(self):
        code, body = self.req("PROPFIND", self._url() + "/", headers={"Depth": "1"}, ok=(207,))
        if code == 404:
            return []
        out = []
        ns = {"d": "DAV:"}
        for resp in ET.fromstring(body).findall("d:response", ns):
            href = urllib.parse.unquote(resp.findtext("d:href", "", ns))
            name = href.rstrip("/").split("/")[-1]
            if not name.endswith(".zip"):
                continue
            size = resp.findtext(".//d:getcontentlength", "0", ns)
            out.append((name, int(size or 0)))
        return out

    def get(self, name, dest):
        code, data = self.req("GET", self._url(name), ok=(200,))
        if code != 200:
            die(f"找不到接力包：{name}")
        with open(dest, "wb") as f:
            f.write(data)


# ---------------- 中转站：同步文件夹 / U 盘 ----------------
class Folder:
    def __init__(self, c):
        self.dir = os.path.join(c["path"], c.get("root", ROOT)) if c.get("nest", True) else c["path"]

    def test(self):
        os.makedirs(self.dir, exist_ok=True)
        t = os.path.join(self.dir, ".relay-test")
        with open(t, "w") as f:
            f.write("ok")
        os.remove(t)

    def put(self, local, name):
        os.makedirs(self.dir, exist_ok=True)
        shutil.copyfile(local, os.path.join(self.dir, name))

    def list(self):
        if not os.path.isdir(self.dir):
            return []
        return [(n, os.path.getsize(os.path.join(self.dir, n)))
                for n in os.listdir(self.dir) if n.endswith(".zip")]

    def get(self, name, dest):
        src = os.path.join(self.dir, name)
        if not os.path.exists(src):
            die(f"找不到接力包：{name}（如果是网盘同步文件夹，可能还没同步下来，稍等一会儿）")
        shutil.copyfile(src, dest)


def store(c):
    return WebDAV(c) if c["mode"] == "webdav" else Folder(c)


# ---------------- 命令 ----------------
def cmd_setup(a):
    if a.mode == "webdav":
        if not (a.user and a.password):
            die("需要 --user（坚果云账号邮箱/手机号）和 --password（第三方应用密码）")
        c = {"mode": "webdav", "url": a.url or DEFAULT_URL, "user": a.user,
             "password": a.password, "root": ROOT}
    else:
        if not a.path:
            die("需要 --path（同步文件夹或 U 盘里的一个文件夹）")
        c = {"mode": "folder", "path": os.path.abspath(os.path.expanduser(a.path)), "root": ROOT}
    store(c).test()
    c["device"] = device_name()
    save_conf(c)
    where = "坚果云（WebDAV）" if c["mode"] == "webdav" else c["path"]
    print(f"✅ 中转站已设置好：{where}\n   这台电脑叫：{c['device']}\n   配置保存在：{CONF}")


def cmd_status(a):
    c = load_conf()
    s = store(c)
    s.test()
    pk = sorted(s.list(), reverse=True)
    where = f"坚果云 WebDAV（{c['user']}）" if c["mode"] == "webdav" else c["path"]
    print(f"✅ 中转站正常：{where}\n   这台电脑：{c.get('device', device_name())}\n   现有接力包：{len(pk)} 个")


def collect(paths):
    files = []
    for p in paths:
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(p):
            files.append((p, os.path.basename(p)))
        elif os.path.isdir(p):
            base = os.path.basename(p.rstrip("/\\")) or "文件夹"
            for root, dirs, fs in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for f in fs:
                    if f in SKIP_FILES or f.startswith("~$"):
                        continue
                    full = os.path.join(root, f)
                    files.append((full, os.path.join(base, os.path.relpath(full, p))))
        else:
            print(f"⚠️ 跳过（不存在）：{p}")
    return files


def cmd_push(a):
    c = load_conf()
    if not os.path.isfile(a.note):
        die(f"找不到交接说明：{a.note}")
    seen, files = {os.path.realpath(a.note)}, []
    for full, arc in collect(a.files or []):
        rp = os.path.realpath(full)
        if rp not in seen:
            seen.add(rp)
            files.append((full, arc))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    name = f"{stamp}_{safe(a.title)}_{c.get('device', device_name())}.zip"
    tmp = os.path.join(tempfile.gettempdir(), name)
    kept, skipped, total = [], [], 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(a.note, "交接.md")
        for full, arc in files:
            sz = os.path.getsize(full)
            if sz > MAX_FILE:
                skipped.append((arc, sz))
                continue
            z.write(full, os.path.join("文件", arc).replace("\\", "/"))
            kept.append({"path": arc.replace("\\", "/"), "size": sz})
            total += sz
        meta = {"title": a.title, "from": c.get("device"), "time": datetime.datetime.now().isoformat(timespec="minutes"),
                "files": kept, "skipped": [s[0] for s in skipped], "version": VERSION}
        z.writestr("manifest.json", json.dumps(meta, ensure_ascii=False, indent=2))
    zsize = os.path.getsize(tmp)
    if zsize > MAX_FILE:
        os.remove(tmp)
        die(f"打包后 {human(zsize)}，太大了。请少带几个大文件（比如视频）再试。")
    store(c).put(tmp, name)
    os.remove(tmp)
    print(f"✅ 已打包上传：{name}\n   交接说明 + {len(kept)} 个文件（原始 {human(total)}，压缩后 {human(zsize)}）")
    for arc, sz in skipped:
        print(f"⚠️ 太大没带上：{arc}（{human(sz)}）—— 这类大文件请用 U 盘或网盘单独传")
    print("👉 到另一台电脑的 WorkBuddy 里说：『接着做上次的』")


def cmd_list(a):
    c = load_conf()
    pk = sorted(store(c).list(), reverse=True)[: a.n]
    if not pk:
        print("（中转站里还没有接力包）")
        return
    print("最近的接力包（新→旧）：")
    for i, (n, sz) in enumerate(pk, 1):
        m = re.match(r"(\d{8})-(\d{4})_(.+)_(.+)\.zip$", n)
        if m:
            d, t, title, dev = m.groups()
            print(f"{i}. {d[4:6]}月{d[6:]}日 {t[:2]}:{t[2:]} ｜ {title} ｜ 来自 {dev} ｜ {human(sz)}  [{n}]")
        else:
            print(f"{i}. {n}  {human(sz)}")


def cmd_pull(a):
    c = load_conf()
    s = store(c)
    pk = sorted(s.list(), reverse=True)
    if not pk:
        die("中转站里还没有接力包。请先在另一台电脑上打包。")
    target = a.name or "latest"
    if target == "latest":
        name = pk[0][0]
    elif target.isdigit() and 1 <= int(target) <= len(pk):
        name = pk[int(target) - 1][0]
    else:
        hits = [n for n, _ in pk if target in n]
        if not hits:
            die(f"没找到包含『{target}』的接力包，可以先运行 list 看看。")
        name = hits[0]
    to = os.path.abspath(os.path.expanduser(a.to or os.path.join(HOME, "WorkBuddy", "接力")))
    dest = os.path.join(to, name[:-4])
    os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(tempfile.gettempdir(), name)
    s.get(name, tmp)
    with zipfile.ZipFile(tmp) as z:
        for info in z.infolist():
            p = os.path.normpath(os.path.join(dest, info.filename))
            if not p.startswith(os.path.normpath(dest)):
                continue  # 防止路径穿越
            z.extract(info, dest)
    os.remove(tmp)
    note = os.path.join(dest, "交接.md")
    print(f"✅ 已取回：{name}\n   放在：{dest}\nNOTE_PATH={note}\n")
    if os.path.exists(note):
        with open(note, encoding="utf-8") as f:
            print("======== 交接.md ========\n" + f.read())


def main():
    p = argparse.ArgumentParser(description="WorkBuddy 接力包")
    p.add_argument("--version", action="version", version=VERSION)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("setup"); s.add_argument("mode", choices=["webdav", "folder"])
    s.add_argument("--user"); s.add_argument("--password"); s.add_argument("--url"); s.add_argument("--path")
    sp.add_parser("status")
    s = sp.add_parser("push"); s.add_argument("--title", required=True); s.add_argument("--note", required=True)
    s.add_argument("--files", nargs="*")
    s = sp.add_parser("list"); s.add_argument("-n", type=int, default=10)
    s = sp.add_parser("pull"); s.add_argument("name", nargs="?"); s.add_argument("--to")
    a = p.parse_args()
    {"setup": cmd_setup, "status": cmd_status, "push": cmd_push, "list": cmd_list, "pull": cmd_pull}[a.cmd](a)


if __name__ == "__main__":
    main()
