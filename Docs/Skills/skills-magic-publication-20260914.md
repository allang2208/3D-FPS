# 技能／魔法工作流发布与本机恢复（2026-09-14）

用户确认当前火球左手 V3「基本达到预期」，指定作为后续技能／魔法开发标准，并授权将确认的废案移入 trash、更新 SKILL 和推送 `https://github.com/allang2208/3D-FPS.git`。随后用户明确选择：本轮仅发布工作流、制作脚本及归档记录，混合玩法代码保留本地。

## 本轮发布范围

- 新建 `skills/ue5-skill-magic-workflow/SKILL.md` 及火球特效参考；技能数据、修炼存档、快捷栏和手部占用使用同一流程。
- 在手臂技能加入完整骨段、肩带前送、连续收手与蒙皮变细原因；在 C++、UI 与项目入口连接该标准。个人 SKILL 与工程镜像同步本轮内容。
- 发布火球手势作者脚本、V3 姿态／时钟参数、VFX 制作与来源读取脚本、来源与历史制作记录。
- 不暂存本地交织的角色、近战、技能模型、快捷栏、存档或其他玩法改动；不带入其他任务原先已暂存的 `Docs/AssetSetup.md` 内容。本轮不是完整火球运行代码发布。

本地实现说明中的 `Source/FPSGAME/Skills`、角色／UI 挂接路径描述的是完整 UE 宿主。公开分支缺少尚未发布的混合运行代码时，不能根据这些文档宣称克隆后已经具备完整可用技能系统。

## 已归档废案

归档至本机 `trash/skills-magic-20260914`，保留原相对层级：

- `FireballCast20260914/BeforeNaturalV2`：旧动作源、作者参数和七份 FBX。
- `FireballCast20260914/BeforeArmVolumeV3`：存在发射手臂变细问题的 V2 源、作者参数和七份 FBX。
- `FireballCast20260914/natural-v2-author.log`：被 V3 制作日志替代的旧日志。

共 19 个文件，343,448,467 字节。移动前核对绝对路径及目录联接，移动后逐文件比对大小和 SHA-256，并核对当前替代物存在。完整清单：[skills-magic-20260914.json](../AssetArchives/skills-magic-20260914.json)。trash 为本机恢复区，不公开上传。

现用 Blend、Export、V3 日志、参考照片、源读取数据，以及 Epic／Spline VFX 资产包继续保留。旧 flames／flight 生成器仍参与当前重建链，不能因为旧系统不再运行就移走。

## 恢复制作环境

### 左手动作

从合法本地备份恢复 `SourceAssets/GASPTraversal20260910/Native/TraversalArms_Editable.blend` 及其 Manny 网格／材质依赖。作者脚本取其中 `SK_M4_Infima`、`SK_Manny_Arms_Export` 和 `M4_idle` 第 0 帧为来源；不依赖归档的旧施法输出。

`SourceAssets/FireballCast20260914/author_cast.py` 读取 `Content/ColdSteelData/Skills/fireball_hand_pose.json`。在完整宿主里继续读取 `FPSFireballComponent.h` 和 `FireballCastMotion.h` 的时钟；仅有本次公开制作资料时使用 `motion_config.json` 的 V3 时长／曲线快照。两者使用同一作者轨迹和修复方法，输出可编辑 Blend 与七份 300 Hz FBX。不会因为发布文档而重新制作或覆盖用户刚认可的模型输出。

### 火球特效

恢复合法本地 Epic Niagara Examples 包、Dr.Game Free Spline VFX 的 FireFlame 纹理、原项目火球命中音频，并恢复宿主的 `NiagaraToolset_System`／`NiagaraExt_*` 与 `RainAssetEditor` 编辑 API。它们是制作前提，不由这些 Python 脚本自动安装。仅有 stock UE Python 和本次源码不能保证具备这些接口。

`Tools/Skills/build_fireball_assets.py` 依次完成基础系统 → 表面火焰 → 飞行方向 → 慢燃核心 → 外焰。保留整个调用链的脚本和生成输入；针对已有外焰用途错误可运行 `fix_fireball_outer_material_usage.py`，该脚本不重新设计火焰参数。具体来源与参数见本目录各阶段记录和 `SourceAssets/Fireball*20260914/authoring.json`。

## 公开资源边界与状态

公开源码、原创配置、提示词和来源记录；Manny/Fab 衍生 Blend/FBX/uasset、贴图、声音、用户参考照片及完整源骨架／材质图转储保持本机。`.gitignore` 明确排除三份源转储，只放行施法姿态 JSON，不整目录开放技能图标和第三方二进制。

用户认可的是 V3 当前手臂效果。历史 V3 制作输出与必要 Editor 构建成功，详见 [动作记录](fireball-left-hand-20260914.md)；本轮仅做获授权的仓库、归档、脚本语法和技能文档检查，不运行游戏、生成截图或渲染，也不扩大为完整玩法回归。

发布检查：精确清单共 40 个文本文件；10 个 Python 脚本通过语法解析，11 份 JSON 可读取；新增或修改的相对文档链接均在发布树中，7 份相关 SKILL 文件的本轮内容与个人镜像一致。V3 作者时长／曲线快照与本机现用头文件一致，技能格式及暂存 diff 检查通过，敏感信息模式扫描无匹配。原暂存区的 `Docs/AssetSetup.md` 修改保持独立。这些结果仅针对本次源码资料发布，不代表实机测试。
