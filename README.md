# 接力包 · WorkBuddy 跨电脑接力技能

> 公司电脑做了一半，回家想接着做？不用再"微信文件传输助手"来回传文件了。

**接力包**是一个 WorkBuddy 技能（Skill）。在一台电脑上说一句 **「打个接力包」**，WorkBuddy 会把这次对话的要点（交接说明）和做出来的文件一起打包，存进你的坚果云（或任何同步文件夹 / U 盘）；到另一台电脑上说一句 **「接着做上次的」**，它就把文件取回来、读完交接说明，接着干。

- ✅ 不需要 GitHub、Google Drive、Notion，国内网络直接用
- ✅ 不用装任何软件（只用 WorkBuddy 自带的能力 + 免费坚果云账号）
- ✅ 不止传文件，还把"做到哪了、你定过什么"一起带过去
- ✅ Windows / macOS 都能用

> WorkBuddy 官方的"多端同步"解决的是 **电脑 ↔ 手机** 查看；接力包解决的是 **电脑 ↔ 电脑** 接着干。两者可以一起用。

## 安装（复制一段话，粘贴给 WorkBuddy）

打开落地页，点「复制安装口令」，粘贴到 WorkBuddy 对话框发送即可。口令里已经包含了完整技能内容，**不需要访问 GitHub**。

也可以手动安装：把本仓库的 `workbuddy-relay` 文件夹（含 `SKILL.md` 和 `scripts/relay.py`）放到：

- macOS：`~/.workbuddy/skills/workbuddy-relay/`
- Windows：`C:\Users\你的用户名\.workbuddy\skills\workbuddy-relay\`

## 第一次使用（每台电脑一次，约 2 分钟）

1. 打开 [jianguoyun.com](https://www.jianguoyun.com) 用手机号注册（免费版每月上传 1GB，够用）。
2. 头像 →「账户信息」→「安全选项」→「第三方应用管理」→「添加应用密码」→「生成密码」。
3. 对 WorkBuddy 说：「帮我设置接力包」，把账号和**应用密码**发给它。

另一台电脑重复第 3 步（同一个账号）。

不想用坚果云？已有百度网盘同步空间 / OneDrive / iCloud 云盘 / U 盘，告诉 WorkBuddy 那个文件夹就行。

## 日常用法

| 你说 | WorkBuddy 做 |
|---|---|
| 「打个接力包」「下班了，存一下」 | 写交接说明 + 打包文件 + 上传 |
| 「接着做上次的」「继续那个季度报告」 | 取回最新/对应的接力包，读完交接说明，告诉你做到哪了，然后接着干 |
| 「我有哪些接力包」 | 列出最近的接力包 |

## 文件结构

```
workbuddy-relay/
├── SKILL.md          # 给 WorkBuddy 看的工作说明
└── scripts/relay.py  # 打包/上传/取回脚本（只用 Python 标准库，WorkBuddy 自带 Python 即可运行）
```

## 隐私

- 坚果云账号和应用密码只保存在你自己电脑的 `~/.workbuddy-relay/config.json`。
- 接力包只存在你自己的坚果云 / 同步文件夹里的 `WorkBuddy接力` 文件夹，别人看不到。

MIT License

## 仓库里有什么

| 路径 | 内容 |
|---|---|
| `workbuddy-relay/` | 技能本体（放进 `~/.workbuddy/skills/`） |
| `安装口令.txt` | 一键安装口令（含完整技能内容，粘贴给 WorkBuddy 即可） |
| `site/` | 落地页 |
| `media/demo.mp4` | 演示视频 |
| `video/make_video.py` | 演示视频的制作脚本（真人素材来自 Mixkit，界面部分为真实运行 relay.py 后录屏） |

落地页：https://workbuddy-relay.vercel.app
