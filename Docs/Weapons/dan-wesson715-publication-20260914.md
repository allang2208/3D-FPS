# Dan-Wesson 715 当前交付与资源恢复

本页汇总 2026-09-14 的当前入口。日期较早的制作文档记录当时状态，不能覆盖下表或 `DanWesson715WeaponAssets.h`。两轮已否决的模型方案见 [归档说明](../Rejected/dan-wesson715-models-20260914.md)。

| 内容 | 当前本机资源 |
|---|---|
| 枪体、完整结构法线及 Chromium 材质 | `/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny`，依赖 `Detail20260914` |
| 默认逐发动作 | `/Game/Weapons/DanWesson715/LeftRecovery20260914/Animations` |
| 速装器动作 | `/Game/Weapons/DanWesson715/LeftRecovery20260914/LoaderStow/A_DW715_speed_0` |
| 开火及分阶段速装器录音 | `/Game/Weapons/DanWesson715/RecordedAudio20260914` |
| 聚合物手电、激光器、全息镜 | `/Game/Weapons/DanWesson715/AccessoryPolymer20260914/Attachments` |
| 全景红点 | `/Game/Weapons/DanWesson715/Chrome20260914/Attachments` |
| 汇总干湿材质映射 | `/Game/Weapons/DanWesson715/AccessoryPolymer20260914/DA_DW715_WetMaterials` |

逐发换弹保留未击发子弹，非空仓直接补弹，空仓先按压退壳。安装六发速装器后，两种状态统一执行完整退弹动作，基础时长 3.85 秒；退弹接触时丢弃全部余弹并保存，不返还备弹，后续按备弹数量装入。枪匠面板说明损失代价。末发射击片段结束后才执行待处理的换弹请求。左手脱离后独立回握，不跟随右手甩回弹仓。

源码还包含手枪待机位置周围的奔跑横摆，与脚步组件的实际步相位共用时钟。必须恢复 `AutoFootstep` 插件（项目模块依赖）以及 `/Game/Audio/FreeFootsteps` 声音。插件本体不随公开源码分发；现有世界河流接口用于涉水脚步。

## 公开源码与本机资产边界

本次发布包含 715 原生接入、实例/库存/枪匠数据、配件与湿材质引用、作者脚本、相关说明和 SKILL。共享文件采用精确片段提交；其他任务正在修改的技能、战斗公式、UI 和移动功能继续保留在本机，不随本次提交发布。公开分支因此是基于已有主线的 715 功能增量，不是整个本机工作目录的镜像。

源模型、贴图、Manny/P9 派生动作、用户 MP3、Fab Chromium 材质、UE 二进制和完整网格/骨骼/材质图导出数据保留本机；未授权公开再分发，不能通过 Git 单独还原完整画面。

恢复完整资产时：

1. 从有权限的项目备份恢复完整 `Content/Weapons/DanWesson715`、其 Manny/手臂/手套共享资源、天气材质函数及 `Content/SubstrateMaterials`，保持原资源路径。排除已归档 Precision/Polish。
2. 恢复原 Fab `Revolver Model 715`、Epic Automotive Substrate Materials、原手臂/参考动作包和用户声音。来源记录分别见 [初始接入](dan-wesson715-20260913.md)、[Chrome](dan-wesson715-chrome-20260914.md)、[声音](dan-wesson715-recorded-audio-20260914.md)。GitHub 参考动作的来源和 Unlicense 文本保留在 Upgrade 作者目录；它不是现成 Manny 第一人称换弹。
3. 恢复 `SourceAssets/DanWesson715*` 中留在本机的 Blend、FBX、纹理、音频和密集导出数据。各目录 README/脚本记录上游输入；现用末端是 LeftRecovery、Chrome、RecordedAudio 和 AccessoryPolymer。仅有脚本不能替代受许可约束的上游输入。
4. 一次性 `integrate_runtime.py`、`update_catalog.py` 为历史制作记录，不能在现用工程或公开分支上重新执行覆盖源码。恢复优先使用资产备份；重新制作需要按对应上游脚本顺序处理。

## 本次发布检查

仅按用户授权检查仓库/远端、提交范围、废案归档散列、文本和脚本、许可及敏感信息；未执行游戏、PIE、渲染、试听或玩法回归。此前各轮文档中的构建记录属于各自制作阶段，不作为本次重新验证结果。
