# G18、HK416 与步枪衔接整理发布（2026-10-01）

本次直接从 `D:/FPS3D/FPSGAME` 向授权远端 `https://github.com/allang2208/3D-FPS.git` 的 `main` 发布本对话源码、制作配方、配置和经验。按 `WORKFLOW.md` 第 8 节精确暂存；其他魔法、背包、机枪和未归属本对话的改动留在工作区。

## 当前内容

- G18：全自动、17／33 发、扩容弹匣封口、瞄具导轨座、手电／镭射位置、三种通用枪口适配和装备／配件图标。钛金制退器按用户要求不添加。
- HK416：原始分件、ADS 机瞄、前握把／手电材质、通用配件及接口、装备图标、EOTH 准星可读性；原厂后托、后握和机瞄独立分区，换件隐藏原件，装备光学镜自动隐藏机瞄。
- 416 后托／后握默认装备并计入属性，每件均为 -10% 后坐力、-10% 腰射随机散布；兼容 M4、M16、HK416、QBZ191。通用 EOTH 与多口径消音器保留用户指定属性。
- 步枪及狙击步枪使用共同腰射构图基准，换弹尾段同时回收视模位置、旋转和动作权重；机枪构图保留原有处理。
- HK416 普通／扩容空仓源帧 130 拍击、162 结束；弹鼓 116／148。使用完整 M4 左臂动作并适配接触位置，运行握把层同步重烘。
- 六家族 4.2 秒通用检视及五份运行握把层已在前轮保存。相机层沿用 M4 换弹／拍击脉冲，按机械接触和源时钟触发；此项为代码路径确认，没有游戏内强度验收。

具体实现与历史交付状态以 `Docs/Weapons/g18-*`、`hk416-*`、`eoth-reticle-readability-20261001.md`、`rifle-hip-standard-20260930.md` 和 `rifle-reload-handoff-20260930.md` 为准。共享 `UWeaponGripProfile`、动画节点和家族路由是 HK416 当前实际加载的依赖，随本次最小运行接入一同发布。

## 本机保留与恢复

公开仓库只保存作者脚本、C++、目录数据和文字；不包含可直接恢复完整游戏外观的模型／纹理／动画、UE 包、原始素材或密集骨骼／几何 JSON。`Before`、`CodeBefore` 是本机回退资料，不因目录较旧就删除。

恢复时先放回合法本机素材与既有共享依赖，再按下面顺序执行需要的制作步骤；不要批量运行所有历史导入器覆盖最终状态。

1. G18 原始输入及 `G18Integration20260929`，随后 `G18AttachmentRepair20260930`、`G18TacticalFit20260930`、`G18MuzzleFit20260930`、`G18IconsFinal20260930`。运行内容在 `/Game/Weapons/G18/Integrated20260929`，基础图标在 `/Game/ColdSteelData/Icons/ue_g18`。
2. HK416 原始输入及 `HK416Reworked20260930`、`HK416ADS20260930`、`HK416AttachmentSurface20260930`，再接入 `HK416UniversalParts20260930` 和 `HK416CommonAttachments20260930`。
3. 后续外观修订依次参考 `HK416FactoryParts20261001`、`HK416QBZ191Furniture20261001`、`HK416AttachmentRepair20261001`、`HK416InventoryIcon20261001`、`EOTHReticle20261001`、`HK416RearGripFit20261001`；保留最新接口、分区、插槽和材质绑定。
4. 空仓拍击和独立机瞄以 `HK416SlapSights20261001` 为当前弹鼓入口，普通／扩容以 `HK416StandardEmptyReload20261001` 为入口，检视以 `HK416Inspect20261001` 为入口。共享作者源在 `HK416CommonAttachments20260930`，不能恢复退役的第一版弹鼓动作。
5. 同时恢复 HK416 六动画家族、`/Game/Weapons/AnimationProfiles20261001/ue_hk416/DA_*`、原生手模、M4／AKM 来源动画、通用配件、声音、图标和淋湿材质依赖。原生变更需常规构建；资产导入是否完成以实际保存记录为准。

HK416 主要内容路径为 `/Game/Weapons/HK416/Reworked20260930`；库存／装备图标同时依赖 `Content/ColdSteelData` 的 PNG 和 Texture2D，以及现有动态装配入口。Git 克隆不是完整二进制备份。

## 素材来源与许可

- HK416：MojoLeeDa 的 [HK416 Full ReWorked](https://sketchfab.com/3d-models/hk416-full-reworked-669a9ee17dc44580b53425a08c2f83d0)，本机来源记录为 CC BY 4.0。下载包 SHA-256：`2fb6e1d0435a9534a09c6b89ab37e965b6cc6a77d1e97aa5223c42e3f44284c6`。原始来源记录保留在 `SourceAssets/HK416Reworked20260930/provenance.json`；拆件及通用化修改归因见两个通用配件目录的 `ATTRIBUTION.md`。
- G18：本机 `C:/Users/allan/Downloads/g18.zip`，包含 `source/G18.rar`，许可仍未明确，因此不公开其模型／贴图／派生图标。只发布本项目接入及制作方法。
- Infima、Manny／V7、已有通用配件、原枪声音与动作分别保留原始许可；HK416 的 CC BY 不覆盖这些依赖。G18 开火音来自工程已有 CC0 的 `1911_A_34P.wav` 派生，不冒充原枪录音。

## 废案归档

24 份文件已移入 `trash/g18-hk416-publication-20261001`，移动前后 SHA-256 一致。公开 [逐文件路径与散列](HK41620261001/archive-manifest.json)，归档内容本身保持本机。

- 第一版 `HK416DrumEmptyReload20261001`：20 份文件。其拍击遭用户否定，已由 M4 完整臂链版本替代。
- `HK416CommonAttachments20260930` 的两个独立 DLL 宿主脚本：已由本工程后台入口／现有编辑器桥替代；不操作旧 Saved 宿主或其目录连接。
- G18 钛金制退器的 Blend／FBX 两份候选：用户取消的部件，不属于当前三款枪口制作入口。

## 技能沉淀与本次边界

同步项目及个人技能库：

- `ue5-weapon-workflow/references/factory-sections-and-fitted-parts.md`：原厂分区、真实接口、UV／材质、默认件属性和跨枪兼容范围。
- `ue5-fps-arms-animation/references/rifle-inspect-and-release.md`：完整臂链、握把层重烘、检视素材识别、回位／相机源时钟与 UE Python 数组视图寿命。

本次只整理和执行用户要求的 Git 发布检查，没有修改运行行为、重建原生模块、打开 UE、重新导入资产或运行游戏测试。前轮保存结果不等同于本轮重新验证；普通空仓导入后曾出现的 Python 收尾崩溃根因仍未确认。游戏表现由用户测试。
