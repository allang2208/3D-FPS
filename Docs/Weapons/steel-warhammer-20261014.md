# 锻钢战锤：双手钝器基础接入

当前攻击／强化公式采用力量与体质、对应镇岳系数的 90%；普通攻击有效距离 3.6m、基础间隔 2.04125s。当前数值及旧物品更新入口见 [战锤数值调整](steel-warhammer-balance-20261014.md)，以下初版数值与时间为历史记录。

用户提供 `C:/Users/allan/Downloads/Meshy_AI_Warhammer_1014043833_texture.glb`，接续此前钢制战锤三视图。使用指定模型，不重新生成外观。原始文件保留在 `SourceAssets/SteelWarhammer20261014/Original/`。

后续当前视模、冲刺低位拖持及冲刺后出手已更新，见 [冲刺拖持接入](steel-warhammer-sprint-drag-20261014.md)。下列初版模型路径继续保留为制作记录。

普通攻击现已更新为 [三连击](steel-warhammer-combo-20261014.md)：两段斜挥接既有下砸，第三段伤害倍率 1.25。第二段已改为换手（左手在上）版本，见 [第二段换手 V5](steel-warhammer-normal-combo-swap-v5-20261015.md)；三段的节奏、挥空、连击承接与镜头随后按 [V6 去机械感](steel-warhammer-normal-combo-flow-v6-20261015.md) 重做，出击节奏与打击力再按 [V7 节奏区分](steel-warhammer-normal-combo-rhythm-v7-20261015.md) 调整。

战锤显示白模的问题见 [材质绑定与 Substrate 修复](steel-warhammer-material-repair-20261014.md)。

当前挥击分段速度和手臂末端位置修订见 [攻击节奏与肩部开口](steel-warhammer-rhythm-clearance-20261014.md)。

最新普通攻击的群体判定、左键蓄力砸地和圆形冲击波见 [战锤群攻与专属重击](steel-warhammer-heavy-slam-20261014.md)。

L 检视（双手拨弄后沿握柄中线转一整圈）见 [战锤 L 检视 V1](steel-warhammer-inspect-v1-20261015.md)；行走中自动播放的转锤半段（速度与力度 ×3）见 [战锤行走检视 V1](steel-warhammer-inspect-walk-v1-20261015.md)。

## 已制作和保存

- 武器总长 115 cm，原锤头外形、UV、颜色、金属度／粗糙度与法线保留；握柄按现有矿镐两处真实握持区域适配。世界模型 139,852 三角面，未主动减面。
- 世界网格：`/Game/Weapons/SteelWarhammer20261014/SM_SteelWarhammer`。
- 第一人称：`/Game/Weapons/SteelWarhammer20261014/SK_SteelWarhammer_BareArmsV7`，直接包含当前 V7 裸手表面，并保留皮肤使用的四套 UV 与分区顶点色。
- 骨架和 Idle、Equip、Swing、HitRecover 序列直接共用 `RusticPickaxe20260919` 当前资源。步行动作继续使用共用双手步态；没有复制整套动画。第三人称沿用矿镐动作族和现有武器捕获链。
- 按原生矿镐骨架接入衣袖、手套与原手套恢复映射。
- 背包图标由实际模型制作，512×1024，透明灰阶；正式 PNG 和 UE Texture2D 均已保存。
- 最终导入回执 `SourceAssets/SteelWarhammer20261014/import_receipt.json`：7 个资产保存，`complete=true`。后台 commandlet 返回 0；未启动编辑器或游戏。

## 物品与基础攻击

- ID：`ue_steel_warhammer`；名称：锻钢战锤；`weaponType=blunt`、标签“双手钝器”，保留 `weapon_melee` 装备身份；背包占 2×4，装备占用同组双手。
- 跟随现有一次性起始军械发放进入仓库；保留发放收据及容量事务，卸下、切换、仓库、丢弃拾取和保存使用现有物品流程。
- 普通攻击为左键举顶下砸，默认挥空周期 1.6 s、接触 0.82 s，接触后复用矿镐停顿与回握。攻速通过同一时钟缩放；武技时钟未修改。
- 实际攻击形态为 `Blunt`。攻击范围 180 cm，辅助半径 24 cm，普通攻击单目标；墙体遮挡沿用工具当前查询。战锤不进入伐木、采矿或回填结算。
- 初始攻击公式为 `40.5 + 6.2×力量 + 2×敏捷`；强化平增 5，力量／敏捷系数每级增加 1.1／0.43。此为本批初始设计参数，未进行平衡测试。
- 体力走普通近战消耗；详情、属性摘要和战斗统一读取共享评估。强化、加工和通用近战附魔沿用物品系统；未新增改造部件或专属武技。
- 联机普通下砸通过组件 RPC 发起，服务端核对当前装备、扣除体力，按接触时刻重新查询并结算；客户机播放预测动作，确认命中后进入回握。拒收同一普通下砸的额外客户端命中报告。

本批交付基础普通攻击；尚未制作战锤独立连段、蓄力重击、格挡或专属改造件。未自动调用剑类的突刺、连段或刀刃专属动作。

## 制作入口与交付边界

作者源为 `SourceAssets/SteelWarhammer20261014/SteelWarhammer_Editable.blend`。`author_warhammer.py` 输出网格、皮肤和 PBR；`author_icon.py` 输出物品图标，图标转灰阶后落盘；`import_warhammer.py` 负责 UE 导入与保存。`register_item.py` 和 `integrate_motion.py` 是本批一次性接入记录，不应在共享源码上重复执行。

`build_warhammer.ps1` 已顺序完成 Editor 和 Game 必要构建，两者退出码均为 0、结果均为 `Succeeded`；完成时间分别为 2026-10-14 12:57:07 和 13:00:43，结果见同目录 `build_receipt.json` 与各目标日志。构建结果不等于动作、握持、音效或联机效果验收。未执行测试、PIE、游戏截图或验收渲染，由用户体验。

原始 GLB 为用户提供的 Meshy 产物。裸手、骨架、动作与音效继承各原资源的来源约束；本次没有对这些源资产的公开再分发作授权判断，也没有发布到远端。
