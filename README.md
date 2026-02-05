# 🤖 百词斩单词对战全自动挂机脚本 (Baicizhan Auto Battle Bot)

这是一个基于 Python 的**百词斩单词对战（Word Battle）全自动挂机脚本**。

它利用 **PaddleOCR** 进行文字识别，配合 **OpenCV** 进行视觉增强，并内置了 **ECDICT** 70万词库。最核心的功能是具备**“自我进化”**能力——它能自动学习结算界面的正确答案，构建本地“偷题本”，玩得越久，准确率越高，最终实现 100% 秒杀。

## ✨ 核心功能

* **⚡ 极速识别**：采用 PaddleOCR 本地模型，结合 Win32API 后台截图，无需联网识别，毫秒级响应。
* **🧠 自我进化 (Self-Learning)**：脚本会自动扫描游戏结算界面（Win/Lose页），将正确答案存入本地 `cheat_sheet.json`。下次遇到同题直接调用标准答案。
* **📚 双重词库**：
* **一级缓存**：偷题本（100% 准确，优先匹配）。
* **二级缓存**：ECDICT 77万离线大词典（模糊匹配，兜底策略）。
* **👁️ 视觉增强**：使用 OpenCV 对截图进行二值化处理和区域遮罩，有效去除游戏背景干扰，防止 OCR 误识别。

## 🛠️ 环境依赖

* **操作系统**: Windows 10/11
* **模拟器**: 雷电模拟器 (LDPlayer) 或其他安卓模拟器
* **Python**: 建议 Python 3.10

## 🚀 快速开始

### 1. 克隆项目

### 2. 安装依赖库

请在项目目录下运行以下命令安装所需库（推荐使用阿里云镜像加速）：

```powershell
pip install paddlepaddle paddleocr numpy==1.23.5 pywin32 requests pillow shapely deep-translator opencv-python -i https://mirrors.aliyun.com/pypi/simple/

```

### 3. 📥 下载离线词典

本项目依赖 `ECDICT` 开源词典。

1. 下载 `ecdict.csv` 文件。
* [GitHub 下载地址](https://github.com/skywind3000/ECDICT/releases)


2. **解压**并将 `ecdict.csv` 文件直接放入本项目的根目录下。

### 4. 模拟器设置

* **分辨率**: 手机版 **720 x 1280** (DPI 320)
* **渲染模式**: 必须设置为 **DirectX** (在模拟器设置 -> 高级设置中修改，防止截图黑屏)。

## 📂 项目结构

```text
.
├── auto_battle.py        # 主程序代码
├── ecdict.csv            # 通用大词典 (需手动下载放入)
├── cheat_sheet.json      # 偷题本 (自动生成，记录学习到的答案)
├── README.md             # 说明文档
└── ...

```

## 🕹️ 使用方法

1. 打开雷电模拟器，进入百词斩“单词对战”界面。
2. 在终端运行脚本：
```powershell
python auto_battle.py

```


3. 等待终端显示 `🚀 V13.0 自进化版已启动！`。
4. 脚本会自动检测“开始”、“再来一局”以及题目和选项。
5. **关于学习**：当一局结束进入结算页面时，脚本会自动记录屏幕中间的单词表。建议前几局挂机让其积累数据。

## ⚙️ 技术原理

1. **视觉感知 (Eyes)**: 使用 `win32gui` 和 `PrintWindow` 接口从后台截取模拟器画面，不受窗口遮挡影响。
2. **图像预处理 (Cortex)**: 使用 `OpenCV` 将图像转换为黑底白字（二值化），并涂黑顶部状态栏和底部干扰区，极大提高 OCR 准确率。
3. **文字识别 (OCR)**: 调用 `PaddleOCR` 识别题目和选项区域的文字。
4. **决策大脑 (Brain)**:
* 优先查找 `cheat_sheet.json` (偷题本)。
* 未命中则查找 `ecdict.csv`，并将释义切分为关键词，与选项进行 `SequenceMatcher` 模糊匹配。
* 若均未命中，根据匹配分数阈值决定是否点击或随机选择（防止卡死）。


5. **反馈学习 (Learning)**: 在结算界面触发 OCR 扫描，解析“英文-中文”对，更新本地知识库。

## ⚠️ 常见问题

* **报错 `ModuleNotFoundError**`: 请检查依赖是否安装完整，参考上方安装命令。
* **报错 `未找到 ecdict.csv**`: 请务必去下载该词典文件并放在脚本旁边。
* **截图全黑**: 请检查模拟器设置里的“渲染模式”是否改为 DirectX。

## 🤝 贡献与致谢

* OCR 模型支持：[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
* 词典来源：[ECDICT](https://github.com/skywind3000/ECDICT)

## ⚖️ 免责声明

本项目仅供 Python 编程学习和图像识别技术研究使用。请勿用于商业用途或破坏游戏平衡。使用本脚本导致的任何账号风险（如封号）由使用者自行承担。

---

**Enjoy Coding!** 🎉

![Views](https://komarev.com/ghpvc/?username=lingyu369&repo=Baicizhan-Auto-Battle&label=Repository%20views&color=0e75b6&style=flat)