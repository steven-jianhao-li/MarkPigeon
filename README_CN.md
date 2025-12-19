# MarkPigeon

<div align="center">
  <!-- Logo Placeholder -->
  <img src="assets/icon.png" alt="MarkPigeon Logo" width="120">
  
  <h3>将 Markdown 转换为精美、可分享的 HTML — 一键发布到云端。</h3>

  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/steven-jianhao-li/MarkPigeon/releases)
  [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
  [![Downloads](https://img.shields.io/github/downloads/steven-jianhao-li/MarkPigeon/total)](https://github.com/steven-jianhao-li/MarkPigeon/releases)
  [![Build Status](https://img.shields.io/github/actions/workflow/status/steven-jianhao-li/MarkPigeon/ci.yml)](https://github.com/steven-jianhao-li/MarkPigeon/actions)
</div>

---

**MarkPigeon** 是一款轻量级工具，专为科研人员和写作者设计。它能将 Markdown 文件转换为带有**智能资源管理**的精美 HTML 文档，让你的文档真正可移植。

> "MarkPigeon 不仅能把 Markdown 变成漂亮的 HTML，还能一键把它变成在线网页。写完文档 → 点击分享 → 复制链接发给群友，全过程 30 秒。"

[English](README.md) | [下载最新版本](https://github.com/steven-jianhao-li/MarkPigeon/releases)

## ✨ 核心功能

* **🚀 开箱即用**：**无需 Python 环境！** 下载可执行文件，双击即可使用。
* **🎨 Typora 主题兼容**：无缝复用你喜爱的 Typora CSS 主题。Typora 里好看的，这里也好看。
* **📦 智能资源隔离**：自动将本地图片提取到专用的 `assets_<文件名>` 文件夹，并重写路径。分享时再也不担心图片丢失！
* **☁️ 一键云端分享**：上传到 GitHub Pages，立即获得公开链接。一键分享你的文档！
* **🤐 一键打包**：批量导出为独立 ZIP 文件，方便邮件分享。
* **🌍 多语言支持**：支持中文和英文界面。
* **🖥️ 双模式**：提供现代图形界面和命令行工具，满足不同使用场景。

## 📸 截图

![主界面](assets/screenshot_gui.png)
*基于 PySide6 构建的简洁现代界面*

## 🚀 快速开始

### 方式一：图形界面（推荐）
1. 从 [Releases](https://github.com/steven-jianhao-li/MarkPigeon/releases) 下载可执行文件。
2. 拖放 `.md` 文件到窗口。
3. 选择主题，点击 **开始转换** 或 **转换并分享**。

### 方式二：命令行
```bash
# 转换单个文件
markpigeon report.md --theme github

# 转换并创建 ZIP
markpigeon report.md --theme github --zip

# 转换整个目录
markpigeon docs/ --output dist/ --recursive

# 列出可用主题
markpigeon --list-themes
```

## ☁️ 云端分享

**30 秒把文档分享到网上！**

1. 点击 **转换并分享** 按钮
2. 首次使用：在设置中配置 GitHub Token（有引导）
3. 确认上传 → 等待发布完成
4. 获得公开链接：`https://用户名.github.io/markpigeon-shelf/report.html`
5. 复制链接，分享给朋友！

> **注意**：文档会上传到一个公开的 GitHub 仓库，并启用 GitHub Pages。

## 📋 导出模式

| 模式 | 说明 | 适用场景 |
|------|-------------|----------|
| **默认** | HTML + `assets_` 文件夹 | 本地查看、编辑 |
| **独立 ZIP** | 每个 MD → 单独 ZIP | 邮件发送单个文档 |
| **批量 ZIP** | 所有输出 → 一个 ZIP | 分享整个项目 |
| **云端分享** | 上传到 GitHub Pages | 通过公开链接分享 |

## 🎨 主题

MarkPigeon 内置 GitHub 风格主题，并支持任何 Typora 兼容的 CSS：

1. 将 `.css` 文件放入 `themes/` 目录
2. 从主题下拉框选择（GUI）或使用 `--theme name`（CLI）

## ⚙️ 设置

通过 **文件 → 设置** 或 `Ctrl+,` 打开设置：

| 设置项 | 说明 |
|---------|-------------|
| **GitHub Token** | 用于云端分享的个人访问令牌（需要 repo 权限） |
| **仓库名称** | 上传目标仓库（默认：`markpigeon-shelf`） |
| **隐私警告** | 上传前显示确认提示 |
| **⭐ Star 按钮** | 一键支持项目！ |

## 🛠️ 开发

```bash
# 1. 克隆仓库
git clone https://github.com/steven-jianhao-li/MarkPigeon.git
cd MarkPigeon

# 2. 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行 GUI
python -m src.main

# 5. 运行测试
pytest

# 6. 代码检查
ruff check src/ --fix
ruff format src/
```

### 项目结构

```
MarkPigeon/
├── src/
│   ├── core/              # 业务逻辑（无 UI 依赖）
│   │   ├── i18n.py        # 国际化
│   │   ├── parser.py      # Markdown 解析
│   │   ├── renderer.py    # HTML 渲染
│   │   ├── packer.py      # ZIP 打包
│   │   ├── converter.py   # 工作流编排
│   │   ├── config.py      # 配置管理
│   │   └── publisher.py   # GitHub API 集成
│   ├── interfaces/
│   │   ├── cli/           # 命令行界面
│   │   └── gui/           # 图形界面
│   └── main.py            # 入口点
├── locales/               # 翻译文件（en, zh_CN）
├── themes/                # CSS 主题
├── tests/                 # 单元测试
└── scripts/               # 发布脚本
```

## 🔄 发布流程

使用自动化发布脚本：

```bash
python scripts/release.py

# 脚本将：
# 1. 检查 Git 状态
# 2. 询问版本升级类型（major/minor/patch）
# 3. 更新代码中的版本号
# 4. 创建 Git 提交和标签
# 5. 推送以触发 GitHub Actions
```

## 📄 许可证

MIT 许可证。详见 [LICENSE](LICENSE)。

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

## 📈 Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=steven-jianhao-li/MarkPigeon&type=Date)](https://star-history.com/#steven-jianhao-li/MarkPigeon&Date)

## 👥 贡献者

感谢所有为这个项目做出贡献的人！

<a href="https://github.com/steven-jianhao-li/MarkPigeon/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=steven-jianhao-li/MarkPigeon" />
</a>
