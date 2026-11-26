# 大份烤羊排（2026-10-14）

时长已按 2026-10-15 用户规则统一为 600 秒；之前回执保留历史意义。最新规则与测试见 [食物与一日消耗](../Survival/food-duration-and-daily-consumption-20261015.md)。

12 个 UE 资产包及生肉骨端修正已保存。2026-10-15 后续将食物效果统一为 600 秒，并补充一日自然消耗回归；最新构建与完整运行结果以 `SourceAssets/SurvivalFoodDefaults20261015/delivery.json` 为准，下面的旧回执仅保留制作历史。

## 授权与数值

- 生食材 `raw_large_lamb`（生大羊排）；成品 `roasted_large_lamb`（大份烤羊排）。
- 共享篝火配方 `roast_large_lamb`：1 生料 → 1 成品，60 秒。沿用已有燃料、队列、交易与建筑存档；没有新增燃料系统。
- 两者背包占格 2×2，单件。未新增购买、掉落或价格。
- 生料不可食用；成品 6 秒进食，4.65 秒接触提交，恢复当前饱食度上限的 50%；水分、SAN 不变。
- 成功消费授予 `largeLambMeal`，HUD 名称 **大份烤羊排**：600 秒，体力上限 ×1.10，体力自然恢复速度 ×1.05。
- 同名仅刷新到 600 秒，不累计时长或倍率。饱食度已满仍可食用。接触前取消不消费、不授予；接触后保留已经成功提交的结果。
- 提高上限不增加当前体力；到期在所有存活体力活动分支前截回恢复后的上限。死亡重生清除增益并按无增益上限恢复体力。
- 不同食物暂沿用项目独立来源相乘的兼容默认：与香肠同时生效时恢复 ×1.1025；这不是用户单独确认的合成偏好。

异源规则依据是 `ColdSteelStatusModel.cpp` 的 `Derived("staminaRegen")`：属性恢复倍率依次乘套装、贡品、地牢来源；`FPSStaminaModel.cpp` 再乘食物来源。原代码只有香肠一种食物增益，没有专门的多食物合成规范。本批将该异源乘算模式延伸到两种食物：`1.05 × 1.05 = 1.1025`，并保留独立剩余时间；不把它表述为用户已确认的多食物规则。

## 资产

复用本机 Medieval Banquet `wktpfaks`，原始 24,208 三角面、UV 和熟肉 4K PBR 保留；20.3242 × 18.7905 × 11.0385 cm。生肉使用授权的本地程序材质，2K 烘焙；没有上传 NoAI 素材。

- 包目录：`/Game/Items/Consumables/LargeLamb20261014/{Raw,Roasted}`。
- 已实际保存 12 个包，每个网格 1 个凸碰撞、1 个材质槽；贴图允许流送、运行最大 2K。
- `Content/ColdSteelData/Icons/{raw_large_lamb,roasted_large_lamb}.png`：320×320 RGBA。
- `SourceAssets/LargeLamb20261014/` 保留原素材散列、修改前快照、程序材质、图标制作工程和握姿源。
- V7 裸手独立五指拟合；握原网格中央 +Y 肋骨，握点 `(1.5,8,6.27049)` cm，肉端咬点 `(1.48570,-6.61176,3.79721)` cm，UE 物体旋转 `(Pitch=0,Yaw=0,Roll=90)`。宽羊排在接近前降低并后移，沿用非匀速动作曲线。

## 代码位置与生命周期

`FPSPotionUseComponent`、`FPSPlayerBodyConsumable`、`FPSPlayerBodyAnimInstance` 和 `ColdSteelPickupConsumable` 接入第一人称、身体呈现和世界拾取。目录、动作、菜谱及强制烹饪目录分别在 `items.json`、`potion_use_motion.json`、`campfire-recipes.json` 和 `DefaultGame.ini`。

`UseConsumableAtContact` 从进程目录读取成品效果，在原消费交易中同时写入剩余时间与物品数量。既有 PlayerState 请求序列、实例身份与交易去重继续负责联机接触授权。

`FPSSurvivalState` 保存剩余秒数；`UFPSSurvivalComponent` 只在服务器写入世界时钟截止值，截止值仅同步拥有者。`FPSStaminaModel` 从实时截止值读取倍率，不依赖滞后档案。普通保存和旅行保留剩余游戏时间，离线不扣时；死亡等待沿用香肠暂停方式，死亡重生清空。`StatusEffectsComponent` 读取同一个状态，物品详情和角色面板同步说明效果。

## 已完成的检查

`static-review.json` 记录 46 项静态检查：旧物品／动作／菜谱／状态定义保留，原始资源散列不变，新包真实存在、尺寸和碰撞，透明图标、目录数据、独立握姿、仅拥有者同步和到期截回等。`ue-assets.json` 是实际 UE 保存回执。

2026-10-14 的 Game 共享构建 16:31:06 UTC 成功（401 项动作），Editor 模块 16:31:27 UTC 完成链接。后续 2026-10-15 的最终构建证据归入 `SourceAssets/SurvivalFoodDefaults20261015/{game,editor}-build-evidence.json`，包含来源、对象/二进制时间及源码散列。本任务保留共享文件中的炼金物品迁移等并行修改，没有修复无关模块。

已读回生熟图标并修正生肉骨端分色坐标：从局部 Generated 轴改成世界 Y -0.035 至 -0.065 m。更新后的 PBR、图标和可编辑工程已生成；三张 UE 生肉贴图及目录图标于 16:33 UTC 实际保存，回执 `raw-bone-fix-saved.json` complete=true。旧版本和散列保留在 `BeforeRawBoneMask/`。

## 安全续做与测试

再次改动源码后才需要运行 `SourceAssets/LargeLamb20261014/build_native.ps1 -Target Editor` 和 `-Target Game`；每次遵守共享互斥，已有构建时不抢锁。

资产保存已完成，无需重复导入。历史失败回执保留：`native-01` 为 19 通过、16 失败，缺少 BeginPlay 和烹饪调色板；`native-02` 为 47 通过、6 失败，缺少 PlayerState；`native-03` 的 54 项玩法断言通过，但退出清理崩溃。这些记录均不作为完整通过结论。测试夹具已补齐玩家身份及未初始化测试世界的组件清理，最终运行见最新交付回执。

需要再次回归时，给 `SourceAssets/LargeLamb20261014/run_runtime.ps1 -RunId <新名称>` 一个未使用的名称。该脚本要求空闲窗口，以独立 `UserDir`、随机测试档和测试建筑世界执行 `LargeLambMealAudit`，命令内部拒绝正式 Saved 目录。它调用真实的燃料／投料／结算／取出事务、消费组件接触与取消、效果时钟、存档恢复、上限与恢复公式，并快进游戏时钟覆盖 600 秒及两种到期顺序。临时调色板不验证正式建筑视觉材质；本测试不覆盖建筑放置、真人视角或网络传输。所有历史运行目录保留。

人工测试时仅使用测试档：在“其他建筑”放置篝火，添加现有燃料和 1 份生大羊排，60 秒后取成品；确认生料不能直接食用。进食接触前取消，再完成一次；检查饱食度增量、6 秒时长、HUD 名称和 10 分钟效果。饱食度已满时重复食用应刷新，当前体力不跳增；到期上限恢复，超额当前体力截回。与香肠同时食用、保存重载、死亡重生及联机拥有者同步分别确认。

无提交、无推送；原始付费素材和本批二进制资产仍留在本机。
