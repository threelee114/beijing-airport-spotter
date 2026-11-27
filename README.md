# 北京机场（PEK / PKX）云端拍机日报与突发预警

零第三方依赖纯 Python + GitHub Actions，实现**电脑关机、不开 Antigravity、纯国内网络也能 24×7 全天候运行**：

1. **每日次日亮点与彩绘汇总（`daily-digest.yml`）**：
   - 每天北京时间 **20:00** 自动扫描次日 PEK 与 PKX 全天计划到港航班（Flightradar24）。
   - 邮件顶部列出各机场实际抓取时间（北京时间）和覆盖情况。次日晨报会对照上次成功发出的简报，列出民航彩绘、重点机型和预计到达时间的变化。例如，原定 A340-200 换成 A320，或一班 747-8F 推迟 45 分钟。注册号暂缺时会注明待确认。
   - 自动生成包含 **🎨 彩绘与特别涂装专栏**、**✈️ 特殊/珍稀机型**、**🌍 罕见航司与国际货机** 的 HTML 邮件，并按北京每日精确日出/日落时间高亮可拍窗口（日出前 1 小时 ~ 日落后 1 小时）。
2. **实时专机 / 备降 / 临期彩绘预警（`live-alert.yml`）**：
   - 联合扫描 **FR24 实时到港 + FR24 华北雷达流 + adsb.lol（未屏蔽军政信号）**。
   - **昼夜光线过滤**：常规预警仅在预计到港时间落于 `(日出前 1 小时, 日落后 1 小时)` 内推送；**极特殊专机/机型**（如 `AF1`/`SAM`/各国元首专机、`IL-96`、`AN-124`、`747SP`、`A340-600`、`Beluga`、`C-5`/`C-17`、挂 `7700`）24 小时全天候直通。
   - 内置 18 小时去重，并自动比对每日预报表，只补推临期新增彩绘/换机目标。
   - 民航到港预警也识别 747、A380、A340 系列的常见排班代码，例如 `74H`、`388` 和 `342`。

---

## 三步免费部署到 GitHub Actions

### 第 1 步：新建 GitHub 仓库
- 登录 GitHub，点击 **New repository** 创建一个仓库（名称如 `beijing-airport-spotter`）。
  - 公开仓库（Public）GitHub Actions 无限免费，当前配置为全天每 15 分钟巡检一次；代码中不含任何个人邮箱或密钥。

### 第 2 步：配置 3 个 Secrets（邮箱与授权码）
进入仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**，依次添加：

| Secret 名称 | 填写内容 |
| :--- | :--- |
| `SMTP_163_USER` | 发信的 163 邮箱（例如 `your_email@163.com`） |
| `SMTP_163_AUTH_CODE` | 163 邮箱的 16 位 SMTP 客户端授权码 |
| `ALERT_TO_EMAIL` | 收件邮箱（例如 `your_email@163.com`） |

### 第 3 步：推送代码并手动试跑一次
在本项目目录执行：

```bash
git init
git add .
git commit -m "init beijing airport spotter workflows"
git branch -M main
git remote add origin https://github.com/<你的用户名>/beijing-airport-spotter.git
git push -u origin main
```

推送完成后，进入 GitHub 仓库的 **Actions** 页面：
- 点击 **Daily PEK/PKX Arrivals & Liveries Digest** → 右侧 **Run workflow**，即可立刻收到一封云端发出的次日亮点+彩绘测试邮件！
- 点击 **Live PEK/PKX VIP & Diversion Alert** → **Run workflow**，即可查看实时扫描日志。

---

## 与本地 Antigravity 的分工配合
- **GitHub Actions（24×7 在线）**：全权负责每天 20:00 的航班+彩绘简报和全天候突发预警。
- **本地 Antigravity（上线外网时运行）**：只需开启 **`北京外事访问与专机情报日报`**，每天 20:00 由 AI 联网深度总结外交部公告、政要访华日程及可能抵京的专机动态，单独发邮件补充，两边互不重复。
