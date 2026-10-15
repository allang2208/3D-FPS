# 技能、法杖面板与联机修复整理发布

2026-10-15。当前完整宿主与 Git 根目录为 `D:/FPS3D/FPSGAME`，发布到 `allang2208/3D-FPS` 的 `main`。本轮只整理本对话成果，保留共享工作区中其他任务的源码和暂存状态。

## 本机已完成内容

- 法杖资源／专注／选中魔法读数，P 技能页十格拖放配置，长按 R 切换；中心或空格取消选择并恢复挥杖，选法术不打断副手书专注。
- 战锤力量／体质公式采用镇岳对应系数的 90%，普通判定距离 360 cm，基础间隔 2.04125 秒；完整与缩略浮窗使用近战格式。
- 重击持续耗体 2/秒，零体力取消并过渡至待机；力竭 5 秒、移速减半、持续禁冲刺，本地暗化及循环喘息。
- 暴风雪持杖限制；陨星固定落点上方 13.2 米、穿过沿途掩体、长按范围预览，以及服务器时间／离场奖励同步。
- 已学战技再魔法的顺序后台准备，不阻塞进场；龙息实际 GPU 实例与绘制材质预热、清空、暂停驻留和首次释放复用。
- 上挑对普通、已破韧、本击恰好破韧目标的权威击飞；双手剑服务端提交、累计耗体回执和命中／修炼去重。

## 公共文件与依赖边界

主线还缺少其他任务的完整战锤基础战斗及档案事务前置，现有发布边界见 [战锤改造](../WarhammerMods20261015/README.md) 和 [联机框架](../Multiplayer20261014/README.md)。因此本轮没有把这些共享文件的整份脏内容直接提交。

- 当前龙息 R6 作者脚本、原创 HLSL、音频处理／导入脚本、说明和对应 SKILL 直接在原路径发布。
- [runtime-integration.patch](runtime-integration.patch) 保存本轮运行代码、界面、后台准备和验证入口的完整新增文件及逐块分离的修改。它包含 88 个源码路径；同一补丁各文件的前置不全相同，**不是可在公共 HEAD 上盲目执行的一键安装补丁**。
- [integration-baseline.json](integration-baseline.json) 逐文件记录 Git 基线、LF 文本前置和结果 SHA-256。`git-main` 可按所列提交恢复；`named-local-prerequisites` 需要先整合同版本档案、移动、战锤或场景准备框架。前置包含其他会话内容时只公布散列和本轮差分，不公布其整份未发布实现。
- [gameplay-data.patch](gameplay-data.patch) 保存本轮技能说明／数值、力竭登记和公式目录，基线及结果的 LF 散列见 [data-baseline.json](data-baseline.json)。该数据补丁使用零上下文，恢复时采用 `--unidiff-zero` 并先核对基线；[warhammer-balance-overrides.json](warhammer-balance-overrides.json) 保存战锤物品的本轮字段覆盖。先恢复原战锤目录再合并字段，保留原实例、强化及改造；原注册作者也应读取这些最终值。
- [warhammer-charge-and-preparation.cpp.inc](warhammer-charge-and-preparation.cpp.inc) 保留落在未公开战锤源内的蓄力／回收和分帧池准备方法，宿主散列见 [warhammer-integration-inputs.json](warhammer-integration-inputs.json)。它是具名方法接入材料，不能作为独立翻译单元编译。

完整本机已包含上述内容，**不要在当前宿主再次应用补丁**。公开配方及接入材料不等于干净检出完整构建；此前构建和玩法结果均来自完整本机整合版。

## 战锤补充接入位置

在同版本基础战斗上保留 `IsHeavyCharging`、`CancelHeavyCharge`、`TickAuthorityBluntCharge` 声明；正常组件 Tick 先调用权威蓄力维护，工具忙碌判断包含 `bBluntReturningCharge`。取消时记录当前蓄力姿态，由 `BluntChargeReturnFrom/Age/Duration` 驱动回待机，`CancelUse` 清除回收状态；动画与镜头用 `BluntChargePoseSeconds()`，不跳到释放攻击。

开始蓄力和松手释放均校验体力；服务器确认取消后，客机拒绝回执对仍在蓄力的动作调用 `CancelHeavyCharge`。`FPSStaminaModel` 已包含持续扣体和零体力调用；不要再在另一处每帧扣一次。原有攻击释放扣费和改造回执沿战锤自己的权威实现。

`WarhammerSlamFXSubsystem` 暴露 `PrepareBackground()`，复用 `PrepareSlot()`；后台每次只准备一个现有池槽，`Emit` 也调用相同方法。补上审核入口友元 `URuneSwordAuditCommandlet`、`USkillNetworkAuditCommandlet` 时仅用于显式测试。其他战锤动作、检视、模型及改造内容由其原任务负责。

## 资产恢复与归档

龙息当前为 `SourceAssets/DragonBreath20261013/VolumeV8R6_20261015`。保持厚实形态和消光，只用连续红／橙 RGB 曲线改善颜色；完整作者为 `Tools/Skills/build_dragon_breath_volume.py`，仅调色入口为 `apply_dragon_red_palette.py`。R1 RG／曝光修复及 R2 材质供体仍需保留；脚本中的历史 trash 路径只是恢复出处，不是当前生成器的读取依赖。

喘息恢复链为有来源记录的 HQ MP3 → `SourceAssets/PlayerExhaustion20261014/prepare_audio.py` → 循环 WAV → `Tools/Skills/import_exhaustion_audio.py`。具体来源和当时许可记录见该目录 `credits.md`；本次不重新下载或公开音频。48 kHz 单声道、80 ms 首尾交叉淡化，循环结束由减益时钟控制。

13 个废案文件、24,368 字节已移入 `trash/skill-magic-retired-20261015`，逐文件移动后 SHA-256 一致。范围为已被 R6 替代的 R3／R4／R5 候选、重复调色别名和一次性 Live Coding 请求脚本；[归档清单](archive-manifest.json) 保留原路径、目标、原因和替代物。当前母版、供体和失败诊断证据保留；未永久删除。

UE 包、字体、Epic／Fab 素材、贴图／图标、音频、插件、缓存、完整日志和构建产物留本机，trash 不进 Git。轮盘使用 UObject 图标，恢复后须 Cook `/Game/ColdSteelData/Skills`，仅 Stage PNG 不够。

## 技能与证据

经验已分别沉淀到技能／魔法的蓄力与持续技能、流体的 R6 颜色与实例准备、UI 的轮盘／被动读数，以及武器的公式／浮窗章节。个人维护源与工程对应章节同步；不把本例参数推广成所有武器或火焰的默认值。

此前完整宿主 Editor 与 Game 正式构建成功。45 项权威逻辑检查、30 组／110 项上挑击飞检查，以及独立监听主机／客机的上挑去重、力竭和陨星晚同步均通过，摘要见 [verification-summary.json](verification-summary.json)，详细边界见 [联机复核](../../Skills/skill-network-review-20261015.md)。本轮只做发布检查、归档读回和补丁重建检查，没有启动编辑器、游戏、试听或重复玩法测试。

真实网络用例固定了隔离档案并关闭自动档案交换，不代表登录／重连／完整换图／丢包通过；NullRHI 和无声运行不代表画面或音效通过。龙息此前首发实景证据独立记录于 [首发回归](../../Skills/dragon-first-cast-regression-20261015.md)。
