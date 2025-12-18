功能规格说明书：一键云端分享 (Cloud Share)

模块负责人: Core Team
版本目标: v1.1.0
依赖: PyGithub (推荐) 或 requests

1. 核心逻辑设计的变更

我们需要在 src/core 下新增一个模块 publisher.py，专门负责与外部 API 交互。

1.1 数据流

本地生成: Converter 生成 HTML 和 assets_xxx/ 文件夹。

用户确认: 触发“隐私警告弹窗”。

上传执行:

检查/创建专用仓库 (默认名为 markpigeon-shelf)。

上传资源文件 (assets_xxx/image.png)。

上传 HTML 文件 (file.html)。

(首次) 开启 GitHub Pages Source 为 main 分支。

返回结果: 构造 URL 并返回给 UI 显示。

1.2 隐私与安全机制 (Privacy Guard)

隐私锁: 在上传动作触发前，必须检查 config.privacy_acknowledged 标志。

Token 存储: GitHub Personal Access Token (PAT) 必须加密存储或仅保存在用户本地 config.json (建议使用 keyring 库提升安全性，MVP 阶段可先明文存本地)。

2. 详细功能需求

2.1 配置管理 (Settings)

需要在 config.py 和 GUI 设置面板中增加以下字段：

github_token: (String) 用户提供的 PAT。

github_repo_name: (String) 默认 markpigeon-shelf。

github_username: (String) 用于构造 URL。

upload_privacy_warning: (Bool) 默认 True (显示警告)，用户勾选“不再提醒”后设为 False。

2.2 核心模块 API 设计 (src/core/publisher.py)

class GitHubPublisher:
    def __init__(self, token, repo_name):
        self.github = Github(token) # 使用 PyGithub 库
        self.repo_name = repo_name

    def check_connection(self) -> bool:
        """验证 Token 是否有效"""
        pass

    def get_or_create_repo(self):
        """
        检查仓库是否存在，不存在则创建。
        必须确保仓库是 Public (否则 Pages 需付费) 或 Private (需特定权限)。
        建议默认创建 Public 仓库以便作为静态博客。
        """
        pass

    def enable_pages(self, repo):
        """
        通过 API 开启 GitHub Pages 功能 (Source: / root)。
        """
        pass

    def upload_files(self, html_path: Path, assets_dir: Path) -> str:
        """
        核心逻辑：
        1. 读取 html_path 内容。
        2. 遍历 assets_dir 下所有图片。
        3. 调用 API 写入文件 (create_file 或 update_file)。
        4. 返回最终的 GitHub Pages URL。
        
        URL 格式: https://{username}.github.io/{repo_name}/{html_filename}
        """
        pass


2.3 UI/UX 交互设计

A. 设置面板 (Settings Tab)

新增 "Cloud / Sharing" 分组。

GitHub Token: [ 输入框 (密码掩码) ] [验证按钮]。

Helper Text: "需要 Repo 读写权限。点击此处查看如何获取 Token。"

Target Repo: [ 输入框，默认 markpigeon-shelf ]。

B. 主界面交互

在“转换”按钮旁，新增一个 "转换并分享 (Share)" 按钮（或上传图标）。

点击后流程：

如果 Token 为空 -> 弹出设置窗口。

如果 upload_privacy_warning == True -> 弹出确认框。

C. 确认弹窗 (Confirmation Dialog)

标题: ⚠️ 即将上传至互联网

内容: "您即将把文档及其图片上传至 GitHub 公开仓库。这就意味着任何人都可以通过链接访问此内容。请确保文档中不包含敏感隐私信息。"

选项:

[ ] 下次不再提醒

[ 取消 ] [ 确认上传 ]

D. 完成状态

转换成功后，在日志栏或弹窗中显示：

"✅ 已发布!"

Public Link: https://... [复制按钮] [在浏览器打开按钮]

QR Code (可选锦上添花): 生成二维码方便手机扫码看。

3. 技术难点解决方案

问题 1: 图片路径修正

现状: 本地 HTML 引用是 <img src="./assets_doc/1.png">。

云端: GitHub Pages 的目录结构若保持一致，则无需修改 HTML。

Repo Root:

doc.html

assets_doc/

1.png

结论: 只要保持上传目录结构与本地一致，相对路径在 GitHub Pages 上依然有效。

问题 2: 上传覆盖问题 (Idempotency)

如果用户修改了文档重新上传，API 会报错“文件已存在”。

解决: 使用 PyGithub 的 get_contents 获取文件的 SHA，然后使用 update_file 方法进行覆盖更新，而不是 create_file。

问题 3: GitHub Pages 生效延迟

Pages 首次开启或更新后，通常有 30-60 秒延迟。

UX: 返回链接后，提示用户“如果是首次创建，链接可能需要 1-2 分钟生效”。

4. 任务清单 (Checklist)

[ ] 引入 PyGithub 库到 requirements.txt。

[ ] 实现 src/core/publisher.py (GitHub API 封装)。

[ ] 在 config.py 添加 Token 和 Privacy 字段。

[ ] GUI 设置页添加 Token 输入框。

[ ] 实现“隐私确认弹窗”。

[ ] 实现上传进度条 (因为上传图片可能较慢，不能卡死界面)。