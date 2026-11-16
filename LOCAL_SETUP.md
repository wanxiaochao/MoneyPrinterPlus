# 本机 Mac 部署

这是 MoneyPrinterPlus 的个人 Fork，保留上游版权与许可说明。

## 启动

双击 `start-macos.command`，页面地址为 `http://127.0.0.1:8501/`。
在终端按 Ctrl+C 停止服务。端口可通过 `MONEYPRINTER_PORT` 修改。
终端中可用 `MONEYPRINTER_OPEN_BROWSER=0 ./start-macos.command` 关闭自动打开浏览器。

## 独立环境

使用 Python 3.11 和项目内 `.venv/`。首次安装或重建运行 `./setup-macos.sh`。
`requirements-macos.txt` 保留上游核心依赖，跳过代码中未使用的 wxPython、PyAudio，
并固定 httpx 0.27.2，避免上游 OpenAI 1.16.2 客户端与新版 httpx 不兼容。
启动器优先使用 `.local-bin/` 中的 FFmpeg，也可使用系统 FFmpeg。
服务只监听本机 127.0.0.1，关闭使用统计和文件监听。

## 模型与密钥

本次本地配置默认使用已有的 Ollama `qwen2.5:7b`，不需要 DeepSeek Key 就能生成文案。
`config/config.yml` 与 `config/session.yml` 是本地运行配置，已在上游 gitignore 中排除。
项目的虚拟环境、FFmpeg 二进制、密钥、日志和生成产物不上传 GitHub。

生成视频所需的 Pexels/Pixabay 素材 Key、云端配音服务，或本地配音/识别服务需另行配置。
纯本地视频合并不要求配音服务。原项目的 Stable Diffusion 成片分支尚未完成，
本次部署未将其标为可用，也未接入健身工坊的 LTX/Qwen3-TTS 流程。

## 后续修改

`origin` 指向个人 Fork，`upstream` 指向原作者仓库。
安装和启动脚本是本地部署补充；原视频、混剪与发布业务流程保持上游实现。
自动发布仍保留在原版菜单中，未配置或执行任何平台发布。
