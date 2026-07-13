# Windows 构建与部署指导

本文档适用于以下交付方式：在开发电脑上完成前端构建和 PyInstaller 打包，然后只把运行包复制到 Windows 部署服务器。部署服务器不需要安装 Python、Conda、Node.js 或项目依赖。

## 1. 已验证的构建基线

- 构建系统：64 位 Windows
- Conda 环境：`backend-opc-py311`
- Python：`3.11.15`，64 位
- 依赖锁：`requirements-py311.txt`
- PyInstaller：`6.21.0`
- pywebview：`6.2.1`
- asyncua：`2.0.1`
- OpenOPC-Python3x：`1.3.1`

构建出的 exe 已包含 Python 解释器和 Python 包。服务器上原来安装的 Python 3.6 不参与 exe 运行，也不需要卸载。

PyInstaller 不是跨平台编译器。Windows 部署包必须在 Windows 上构建；64 位 Python 生成的是 64 位 exe。

## 2. 构建电脑准备

需要安装：

1. Anaconda 或 Miniconda。
2. Node.js 和 npm，用于重新构建前端。
3. Git，仅用于获取和管理源码，不参与服务器运行。

首次创建环境：

```powershell
conda create -n backend-opc-py311 python=3.11.15 -y
conda activate backend-opc-py311
cd D:\Codes\backend-opc\backend
python -m pip install -r requirements-py311.txt
python -m pip check
```

`pip check` 应输出：

```text
No broken requirements found.
```

不要在装有大量无关包的全局 Anaconda 环境中打包。PyInstaller 会分析当前环境，额外的 GUI 包可能显著增大 exe，甚至带入不需要的运行时。

## 3. 构建前端

每次正式发版都应从前端源码重新构建，不要依赖来源不明或过期的 `backend\dist`。

```powershell
cd D:\Codes\backend-opc\frontend
npm ci
npm run build
```

构建结果位于：

```text
D:\Codes\backend-opc\frontend\dist
```

将它完整替换到后端目录。执行删除前，先确认当前项目路径正确：

```powershell
cd D:\Codes\backend-opc\backend
if (Test-Path -LiteralPath .\dist) {
    Remove-Item -LiteralPath .\dist -Recurse -Force
}
Copy-Item -LiteralPath ..\frontend\dist -Destination .\dist -Recurse
Test-Path -LiteralPath .\dist\index.html
```

最后一条命令必须返回 `True`。前端 `dist` 会被嵌入 exe，部署时不需要再单独复制它。

## 4. 打包前检查

确认使用的是正确环境和解释器位数：

```powershell
conda activate backend-opc-py311
cd D:\Codes\backend-opc\backend
python --version
python -c "import struct; print(struct.calcsize('P') * 8)"
python -m pip check
```

预期结果为 Python 3.11、`64` 和无损坏依赖。

再执行不连接外部服务的基础检查：

```powershell
python -c "import Application; print('Application import OK')"
python -c "from Application import create_app; r=create_app().test_client().get('/'); print(r.status_code, r.content_type)"
```

首页应返回 `200`。这些检查可能初始化本地 SQLite 表，因此建议在构建副本中执行，不要直接在生产数据库目录执行。

## 5. 先生成控制台测试版

正式隐藏控制台前，先生成能够显示启动错误的测试版：

```powershell
python -m PyInstaller `
  --clean `
  -F `
  --add-data "dist;dist" `
  --hidden-import=tzdata `
  --name Application-debug `
  --distpath release\debug `
  --workpath .pyinstaller\debug-work `
  --specpath .pyinstaller `
  Application.py
```

测试版位于：

```text
release\debug\Application-debug.exe
```

把一份用于测试的 `.env` 放到 exe 同目录，然后从该目录启动。确认窗口、首页、日志、数据库和网络配置正常后再生成正式版。

## 6. 生成正式无控制台版本

项目中的 `Application.spec` 已配置 `console=False`、前端 `dist` 和 `tzdata`。推荐使用 spec 构建，并把输出与前端 `dist` 分开：

```powershell
conda activate backend-opc-py311
cd D:\Codes\backend-opc\backend
python -m PyInstaller `
  --clean `
  --distpath release\production `
  --workpath .pyinstaller\production-work `
  Application.spec
```

正式 exe 位于：

```text
release\production\Application.exe
```

不要使用默认输出目录把 `Application.exe` 写入 `backend\dist`。否则下一次 `--add-data "dist;dist"` 构建时，旧 exe 可能被当作前端静态文件再次嵌入，造成包体膨胀。

## 7. 组装部署目录

建议先新建一个干净的交付目录，例如：

```text
backend-opc-release\
├─ Application.exe
├─ .env
├─ repository\
│  └─ history.db          # 仅在需要保留/迁移历史数据时复制
├─ certificate.pem        # 如生产环境已有，建议沿用
└─ private_key.pem        # 必须与 certificate.pem 成对
```

必须复制：

- `Application.exe`
- 适用于部署服务器的 `.env`

按实际情况复制：

- `repository\history.db`：不复制时程序会创建新数据库；需要历史数据时，必须停机后复制生产数据库。
- `certificate.pem` 和 `private_key.pem`：生产环境已有证书时，建议备份并成对沿用；缺失时程序会尝试重新生成。

不要复制：

- Conda 环境目录
- Python 安装目录
- `node_modules`
- 前端源码及单独的 `dist`
- `.pyinstaller`、`build-*`、`__pycache__`
- 本机日志、导出文件和烟雾测试文件
- `requirements-py311.txt`（可作为运维留档，但 exe 运行不需要）

## 8. `.env` 配置注意事项

应用在冻结模式下从 exe 所在目录加载 `.env`。至少核对以下配置项：

```text
DATABASE_FREQUENCY
CACHE_MAX_SIZE
CACHE_TTL
CACHE_TASK_THREADS
SERVER_NAME
GATEWAY_HOST
OPC_TAGS
IP
PORT
OPC_UA_URL
OPC_UA_NAMESPACE_URI
```

其中 `DATABASE_FREQUENCY` 在当前代码中没有可靠默认值，缺失或不是整数会导致应用导入失败。

`.env` 包含现场地址和其他敏感配置，不应提交到 Git。运行时数据库同样应通过停机备份和部署流程管理，不适合继续作为源码提交。注意：本仓库中的 `.env` 和 `repository\history.db` 目前已经被 Git 跟踪，仅加入 `.gitignore` 不会自动取消跟踪。确认两者均已安全备份后，可执行：

```powershell
git rm --cached .env repository/history.db
```

然后提交该变更。该命令只从 Git 索引移除文件，不应删除工作目录和部署目录中实际使用的 `.env` 或数据库。IDE 配置 `.idea` 也已经被跟踪；如决定清理，可另外执行 `git rm -r --cached .idea`。

## 9. 部署服务器前置条件

1. 64 位 Windows，且必须有桌面环境；Windows Server Core 不适合直接显示 pywebview 窗口。
2. 建议安装 .NET Framework 4.6.2 或更高版本。
3. 建议安装 Microsoft Edge WebView2 Runtime，以使用 Edge Chromium 渲染前端页面。
4. 应用目录必须可写。程序会在当前工作目录写入：
   - `repository\history.db`
   - `logs\`
   - `export\`
   - `certificate.pem`
   - `private_key.pem`
5. 防火墙和网络应允许：
   - 应用访问 `GATEWAY_HOST` 上的 OpenOPC Gateway 服务。
   - 应用访问 `.env` 中配置的模型服务 `IP:PORT`。
   - 如外部客户端要访问内置 OPC UA Server，允许配置的 OPC UA 端口，当前现场通常为 `48400`。

pywebview 官方说明，Windows 下的 Edge Chromium 渲染需要 .NET Framework 4.6.2 和 Edge WebView2 Runtime：<https://pywebview.idepy.com/en/guide/web_engine>。

## 10. 部署步骤

1. 停止旧程序，确认任务管理器中已没有旧的 `Application.exe`。
2. 完整备份旧部署目录，重点保留 `.env`、数据库、证书和私钥。
3. 将新交付目录复制到新的版本目录，不建议直接覆盖唯一可回滚副本。
4. 从 exe 所在目录启动程序。
5. 检查窗口首页能否正常打开。
6. 检查 `logs\myflask.log` 中是否出现启动完成、OPC Gateway、模型服务或端口错误。
7. 验证数据库是否持续写入、导出和二维码功能是否正常。
8. 使用现场 OPC 客户端验证 OPC UA 节点和端口。

程序中的数据库、日志、导出和证书路径是相对于“当前工作目录”，并不都固定为 exe 路径。使用快捷方式时，应把“起始位置/Start in”设置为 exe 所在目录；使用 PowerShell 启动时可执行：

```powershell
Set-Location -LiteralPath D:\实际部署目录\backend-opc-release
.\Application.exe
```

## 11. 验证和回滚

推荐先在与生产服务器相同 Windows 版本的测试机上运行控制台测试版。至少验证：

- 应用不会立即退出。
- 首页静态资源完整，无白屏和 404。
- `.env` 加载路径正确。
- OpenOPC Gateway 可连接并能读取现场点位。
- 模型服务返回合法 JSON。
- OPC UA 端口没有被其他程序占用。
- 数据库、日志、导出目录可写。
- 关闭窗口后进程能够退出。

如新版本异常：

1. 结束新版本的所有 `Application.exe` 进程。
2. 保留并备份新版本运行期间产生的日志。
3. 恢复旧版本目录。
4. 如果新版本已经写入生产数据库，应先备份数据库，再决定是否回退数据库文件，避免丢失新增数据。

## 12. 已知事项

- OPC Gateway 或模型服务不可达不会影响 PyInstaller 打包，但会在运行时产生连接错误或空数据。
- 正式版使用无控制台模式，启动早期异常不容易直接看到；排障时优先运行 `Application-debug.exe`。
- `asyncua 2.0.1` 会提示 `set_security_IDs` 已弃用，目前仍可运行，后续可改为新版身份令牌 API。
- `-F/--onefile` 首次启动需要把内部文件解压到临时目录，可能被杀毒软件拖慢；部署前应完成白名单和启动耗时验证。
- 生产证书和私钥必须成对备份，不要提交到 Git 或通过不安全渠道传输。
