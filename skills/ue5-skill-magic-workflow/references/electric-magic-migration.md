# 雷暴领域与贯穿雷枪（2026-10-01）

## 光束制作的可复用规则

- 束身需要遮挡背景时使用Translucent覆盖，外侧窄电丝可保留Additive。单纯提高加法Opacity只增加发光贡献，不能消除背景透出；核心覆盖、翻卷密度和发光强度分别调整。
- 可见宽度和伤害半宽分别取数。用户要求射程翻倍时同步基础射程与等级成长，UI、目标搜索、墙面截断和光束末端继续共用同一派生值。
- 程序化流动用实际起终点建立世界空间轴向场，保留无缝角向坐标、近端／末端遮罩和覆盖WPO的Bounds。延长或加粗复用既有网格、纹理和有界组件，不以增加实例数量代替密度。
- 现有材质拆图重接可能产生旧Custom缺输入的中间态告警；判断本次制作是否失败应看最终完整图的编译与保存结果。DepthFade与透明速度输出冲突导致的默认棋盘格则是真实编译失败，不能混为同一种现象。
- 后续恢复入口与运行引用同步当前版本。退役柱体／光环先核对包引用再移入trash，保留仍在使用的魔法阵；原创制作配方可公开，Fab／引擎副本、导入包、二进制源和日志保持本机。制作与必要构建完成后交由用户测试，不自动启动游戏。

实际实现与数值见工程 `Docs/Skills/electric-magic-migration-20261001.md`；UI合同见 `Docs/UI/electric-spells-plan-20261001.md`。本轮后台制作、保存和必要构建，不主动运行或验收。

- 原项目为 `game-dev` 的 `storm-domain-system.js` 和 `thunder-lance-system.js`，已有 `lightningStrike` 继续保留。1原单位=1.5cm，技能1～20级；不套用火球／冰锥后来调整过的伤害与修炼规则。
- 雷暴云随施法者移动，立即落雷，然后每.9秒寻找最近可见敌人，按最近未命中目标连锁；总目标2/3/4个在1/9/17级。每跳保留70%伤害、短眩晕、感电与共用过载。整云自然结束汇总修炼，死亡／离场不结算未完成云；菜单只取消未释放动作，已经生成雷云保留。
- 雷枪按住绑定槽键起手，施法接触帧开始.5～2.5秒蓄力，满充保持、松键释放。蓄力锁移动但放开鼠标瞄准；准星与散射共用 `LanceSpreadTangent=tan(6°)*(1-progress)`，以 sqrt 随机半径均匀取圆盘，100%收成点。直线穿透多个敌人，墙面截断，伤害×蓄力比例×1.3×[1+命中前感电层数×.1]，随后击退并+2层感电。末端爆闪只装饰；原配置ground字段是死字段，不增加地面电场。
- 原项目的法杖门槛由用户后续规则覆盖：仅陨星／冰墙要求法杖。本轮两项可空手施放，双持手枪拒绝；共用法杖／左手手势，不另做独立施法控制器。
- 新组件 `UFPSElectricMagicComponent` 复用 `ApplyLightningHit` 与感电／过载；雷暴锁定仅随机暴击，雷枪实际目标骨段射线可触发要害必暴。目标搜索用局部重叠，不全场Actor轮询；装饰电弧48个、冲击系统24个、声音6并发有上限。
- 未释放付款单独预留，取消／控制／死亡退蓝回滚冷却；Profile v19补齐两项进度与分技能冷却，读档退回遗留未释放蓝耗。整次修炼四项保留原值与100×当前等级升级门槛。
- 技能卡片、当前／下级详情、修炼、图标、拖拽／混合快捷栏、状态提示、升级通知与F6调级必须一起接入。快捷键松开走现有Controller释放路由，避免对已消费按键进行IsInputKeyDown轮询误判。
- 特效恢复入口为 `Tools/Skills/build_electric_magic_assets.py`：四层蓝黑软云＋电丝、雷枪三层连续光柱／加速环、短命CPU蓄力电团／末端闪光、原两段声音的空间化副本。雷枪最新替换的实际保存／编译状态见 `Docs/Skills/thunder-lance-column-20261001.md`。原Normandy／Spline／Niagara母版只读。
- 云为世界空间：运行时必须设置CurrentPosition、Side、Up、SurfaceNormal，并在移动时更新CurrentPosition，单独SetWorldLocation不会移动按User位置计算的粒子。局部蓄力特效跟随同帧法杖尖；先设置User.Charge后Activate，避免默认参数起始帧。
- 作者、PNG恢复及imagegen完整提示词在 `SourceAssets/ElectricMagic20261001/manifest.json`，实际包回执在 `Saved/ElectricMagic20261001/asset-authoring.json`。不要把作者编译／保存当作用户视觉或运行验收；合法本机素材不公开再分发。
- 资产commandlet完全退出后再启动普通Editor构建。TargetList的插件DLL可能在编译队列早期就链接，不要假设到所有项目CPP结束才会链接；加载了AutoFootstep等模块的制作进程会占用该DLL。本轮最终Game／Editor构建成功，未启动图形编辑器或测试。

## 雷枪表现与充能提示（2026-10-01 后续）

角色 Turn/LookUp 不再用含雷枪的移动锁阻止瞄准；保留原移动和近战技能视角合同。体力条上方现有动作提示显示“雷枪充能 0～99%”，100%显示“已充能完毕”；与重击、脚架共用 `ColdSteelUI::ActionProgressColor` 原红→黄→蓝→绿渐变。准星按实际相机投影绘制缩小圆周和短刻度，满充只剩中心点，未满充实际光束及伤害射线统一使用圈内随机方向。

杖前54cm白蓝双环与12枚符文来自独立作者 `Tools/Skills/build_thunder_lance_circle.py` 和 `/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle`；离同帧杖尖前方12cm，随瞄准朝向和充能增亮。已有电团保留，系统生命周期需 Infinite，组件既有Tick更新和取消路径清理；全量作者 charge() 和局部 hold_thunder_lance_charge_20261001.py 同步此规则。魔法阵已后台编译保存，Game／Editor普通构建成功，状态见 `Docs/Skills/thunder-lance-charge-aim-20261001.md`；不主动启动游戏或验收。

## 雷枪连续光柱（2026-10-01）

参考 `game-dev/combat-fx.js:spawnRailgunBeam`，发射表现改为白热芯／白蓝中层／蓝外辉光三层连续圆柱和4个沿轴扫动加速环；3层直径比例40:19:9，第一人称实际96／45.6／21.6cm，约.373秒平方曲线淡出。`AFPSLightningArc::InitializeColumn` 复用现有短命Arc容器与灯，7个无碰撞组件；不新增伤害或全场轮询。连锁、雷暴、过载继续调用原 `InitializeArc`。

作者 `Tools/Skills/build_thunder_lance_column.py` 拥有 ThunderLanceV2 的 `M_ThunderLanceColumn`／`M_ThunderLanceCoil`，几何只依赖引擎 Cylinder。运行资源数组按固定索引异步加载这些材质；火线、瞄准、随机散射、贯穿骨段射线及墙面终点共用原施法参数。全量电系作者 beam() 调用新入口，不重新保存旧闪电包。当前保存、构建与未测试范围见工程 `Docs/Skills/thunder-lance-column-20261001.md`。

本次两份材质实际后台保存，Game／普通Editor最终构建均成功；编辑器关闭后未重新打开或运行测试，观感由用户确认。

## 后续可读性调整（2026-10-01）

用户报告光柱偏细／偏弱、圆形准星不合适、魔法阵看不到后，光柱改为192／91.2／43.2cm，发光9／14／24，原Hold保持亮度后单次线性Fade；仍为七组件、约.373秒，不扩大伤害半宽。准星改枪械四向直线，内端随实际散射投影收拢，长度同时收短，满充只剩点；进度色和文字合同保留。魔法阵64cm、杖前24cm，线条加粗、14倍发光，组件加入角色实例列表并挂接相机，世界位置仍更新为同帧杖尖。加法材质仅在Opacity应用一次覆盖和消散，避免重复削薄。制作与实际保存／构建状态见 `Docs/Skills/magic-readability-and-blizzard-material-fix-20261001.md`；本轮未运行视觉验收。

用户随后将电矛光柱完整亮度停留时间改为2秒，以便观察效果；数值入口为 `ColdSteelElectricMagicModel.cpp` 的雷枪 `Hit.Duration=2.f`，仍接原.153秒淡出，总可见约2.153秒。发射伤害只结算一次，材质不必重建。当前构建状态见 `Docs/Skills/thunder-lance-column-20261001.md`；不自动启动游戏。

用户再提供彗星亚兹勒截图后，发射重做为ThunderFluxV3：原创48×32分段宿主与无缝密度数据驱动白蓝芯／翻卷中外层／跳动分叉电丝，约45ms建立全束，初段增亮、前冲高速，四个规则环取消，四组件替代原七组件。保持2秒+.153秒观察时长；杖前一次现有冲击爆闪、末端冲击尺寸×1.25、已有镜头震动.7（尊重开关）。雷枪实际三项运行引用切到新目录，其他电系技能不改。当前定向作者 `build_thunder_flux_v3.py`，旧 `build_thunder_lance_column.py` 作为兼容入口，全量作者同步调用；先生成原创FBX／密度PNG再恢复资产。旧V2包保留。完整源、参数、保存／构建状态见 `Docs/Skills/thunder-lance-flux-20261001.md`，未实机验收。

后续按用户要求射程翻倍：thunderLance配置RangeBase=1800、RangePerLevel=30，1.5cm单位换算及装备加成继续共用模型，1级27.45m、20级36m（装备加成前）。表现增强50%对应三层直径264／168／87cm、电丝291cm、发光12／21／31.5／42、杖前爆闪1.2、末端系数1.875和灯强3600。束身改Translucent实际遮挡背景，电丝保留Additive；提高核心／翻卷层覆盖，保留2秒+.153秒时长和伤害半宽。定向／兼容／全量作者同步当前配方，最新制作与构建状态见同一工程记录，回执在 `Saved/ThunderFluxStrength20261001`；未实机测试。
