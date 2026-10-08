# 金刚符文制作与接入

## 用户确认

- 2026-10-06 认可 `Artwork/ApprovedConcept.png`，继续接入镇岳的传说符文。
- 被动双防+25%；≥70%生命双伤+25%；30%至不足70%攻速+25%和冷却缩减25%；低于30%上述所有类别均+50%。
- 进入低血量获得10秒、10%实际伤害吸血，低血量命中刷新；恢复血量保留剩余吸血，切武器解除全部。

## 作者资产

`Artwork/Jingang_Blade_Mask.png`：20字金刚经节选行草与小卷云，白笔迹/黑底，取R遮罩。`jingang_emission.hlsl` 将横向经文沿刀刃长度映射，沉金/琥珀/香槟渐变缓慢游动。

2026-10-06按待机截图反馈，将剑身金刚经源纹样的V方向镜像翻转，保持句子顺序、投射区域与流金时序。同步修改常规剑身及旋风派生材质，HUD经文/火焰不变。`BladeTextFlip20261006/install_flip.py` 只替换实际材质中mode9分支；全量作者通过 `rune_code.py` 更新该分支，避免重导恢复旧方向。保存回执 `BladeTextFlip20261006/install-receipt.json`，未主动试玩或截图测试。

`Artwork/Jingang_Hud_Atlas.png`：3个等宽状态栏，每栏两列四字竖排行书；`sutra_hud.hlsl` 控制颜色、呼吸、流光、切换淡入淡出。HUD位置详见 `Docs/UI/jingang-sutra-hud-plan-20261006.md`。

追加 `FlamesV2`：金色火焰沿经文笔画燃烧并向上卷动，稳定字芯保留书法可读性。仅更新正式 `M_JingangSutraHud` 的既有 Custom 节点，使用同一份 `sutra_hud.hlsl`，完整重导同样带入火焰。每像素稳态最多12次图集采样、状态切换最多24次；沿单张HUD四边形和现有时钟，边缘柔化并保留苍龙间距。`FlamesV2/run_install.ps1` 后台落盘；保存回执 `FlamesV2/install-receipt.json`，原材质及源保留在 `FlamesV2/Before/`。本轮不启动编辑器或运行视觉验收。

`Artwork/Jingang_Icon.png`：以镇魔现有银框图为边框参考，中心改为本符文“金剛”行书，灰阶银色浮雕；共享图标键 `blade_2_jingang_rune`。

以上由内置 `image_gen` 生成，完整原始图保留在本目录，不依赖临时路径。设计图、遮罩和UI图标是各自用途资产，不把效果图直接当PBR贴图。

## 玩法与生命周期

新增 `Weapons/JingangRuneComponent.h/.cpp`，由人物默认组件持有，Configure接收本角色档案。数值从改造选项解析、按装备缓存；生命比例实时读取健康组件。结束和切换武器清除短效、撤销HUD；不持久叠加角色属性。

双防进入Derived；攻速进入Derived(aspd)，剑类按现有出手时钟读取。增伤进入共同怪物承伤结算：武器物理与附魔魔法各自结算后乘倍率，魔法分支同样按命中当时的持握状态取数，避免切武器保留增益。伤害面板保留基础伤害值，改造详情和状态说明单列条件增幅。

吸血从现有人物 `NotifyConfirmedWeaponHit` 的实际伤害回执触发，复用物理、魔法攻击既有回执；权威端更新生命，禁止友军和自身回执。低血量首次进入在健康受伤入口立即观察，普通每帧只处理实时状态和HUD。

冷却按额外回转 `Delta*(1/(1-CDR)-1)` 接到既有 `ReduceAllAbilityCooldowns`。25%缩减为1.333倍回转，50%为2倍；切换武器立即恢复正常回转，已恢复的进度不倒扣。已保留但未释放的施法冷却不提前开始，快速近战动作恢复和10秒吸血计时不受CDR影响。

## 重建

`build_and_import.ps1`：共享桥互斥锁下等待现有构建，常规 Editor/Game 构建，再用无人值守 Python commandlet 保存资产。`-SkipBuild` 只导入，`-BuildOnly` 只构建。编辑器存在则保留现场停止，不杀进程。

`install_assets.py`：保存三张纹理、共享图标、每种剑身及旋风派生材质、HUD材质，然后更新模块绑定和目录。旧模式完整保留。资产导入完成以 `import_receipt.json` 为准；构建结果见对应日志。用户存档未重写。

本轮未运行游戏测试或渲染验收，未主动打开UE编辑器。

## 本轮落盘结果

2026-10-06：Editor和Game常规构建均成功；无人值守资产导入退出码0，实际保存6个资产，目录与剑身材质绑定已写入。首轮新增组件复制宏要求参数名 `OutLifetimeProps`，已修正后完成正式构建。记录见 `delivery.json` 与 `import_receipt.json`。
