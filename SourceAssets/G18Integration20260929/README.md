# G18 制作源

运行接入记录见 `../../Docs/Weapons/g18-integration-20260929.md`。

## 来源与许可记录

- G18 枪体、骨架和 PBR：用户本地提供的 `C:/Users/allan/Downloads/g18.zip`，内含 `source/G18.rar`。提取原件保留在 `Original/`。包内未附可确认的授权文件；未把第三方源件、贴图或衍生二进制发布到外部，也不将其标为 CC0。
- 原生裸手：项目 `SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/`，沿用本项目 Manny 手臂来源与许可记录。
- 动作意图：项目 M1911 Contact、ReloadTiming、Locomotion、RevolverInspect、QuickCombat 和双持 NaturalAim／SprintSmoothV5／SpinRecoveryV5。上游 P9 动作为 Infima Games Low Poly Shooter Pack - Free Sample，出处和 Standard Unity Asset Store EULA 记录见 `../M1911P9Retarget20260913/CREDITS.md`。本次仅在本机制作适配。
- 附件：`attachment_authoring.json` 逐项保留输入 FBX 与运行资产路径，沿用各源目录许可；只改变 G18 需要的接口或材料。
- 普通及消音枪声：由现有 CC0-1.0 的 `1911_A_34P.wav` 设计。原出处 [The Free Firearm Sound Library](https://opengameart.org/content/the-free-firearm-sound-library)。`media_sources.json` 记录源哈希、处理方式及四组变体。不是 G18 录音。
- 机械声：项目 M4HK416／AKM 已有声音，复制为独立 G18 名称，来源表保留在 `import_receipt.json`，沿用原源许可。

## 生成入口

1. Blender 后台运行 `author_g18.py -- single`、`-- r`、`-- l`，生成原生手臂枪体、动画 FBX、可编辑 Blend 和作者记录。
2. Python 运行 `prepare_media.py`，制作材质输入与独立音效。
3. Blender 后台运行 `author_parts.py`，生成配件与图标用几何。
4. Python 运行 `author_icons.py`，落盘目录及改装图标。
5. 项目 `Tools/ModularOutfit/Run-Authoring.ps1` 运行 `import_assets.py`，实际导入并保存资产，随后发布三个 JSON 目录中的 G18 条目。
6. `build_editor.ps1` 使用同一个 UE 批次互斥执行必要后台构建，不启动编辑器。

`integrate_code.py` 是本次首次代码落地脚本，不是可重复执行的迁移工具。不要重复运行；其执行前的相关工作区文本保存在 `CodeBefore/`，不能把这些快照当作整个项目可回退基线。

`import_receipt.json` 记录保存结果；FBX、Blend、原件和加工中间件均为可重建输入。没有为本次接入启动 PIE、运行游戏或执行自测／视觉验收。
