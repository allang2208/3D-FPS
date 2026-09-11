# 手脑穿地、毒蛆空喷与状态栏

当前宿主 `D:/FPS3D/FPSGAME`，村庄入口 `/Game/GameMaps/L_Normandy_FPS_Test`。本轮保留怪物模型、PBR 材质和动作，修改物理支撑、毒滴碰撞及玩家状态显示。证据目录为 `SourceAssets/MonsterFeedback20260911`。

## 手脑死亡穿地

原验收只检查胶囊碰撞体与地面，遗漏了物理与渲染骨骼不重合、胶囊未覆盖手掌两个问题。修复前同一村庄用当前蒙皮矩阵测得最低表面低于地面 88.367 cm，10,210 个采样点中 7,323 个低于地面超过 3 cm；cranium 刚体与渲染骨骼相差 65.801 cm。旧的 30 项通过不能代表当前尸体可见性通过。

`HandBrainMonster::BuildPhysicsAsset` 现在创建一个不参与碰撞的 root 刚体，保证死亡轴 `death_pivot` 上方存在物理根；base、neck、cranium 使用实际身体顶点拟合的凸包支撑宽阔手掌。死亡时收缩的攻击手和扇形附件不扩大主体凸包。保留厘米/骨骼缩放换算、约束、CCD 与 16/8 求解迭代，给小幅骨骼放松及关节混合表面留 2 cm 支撑余量。

正式资源为 `/Game/Monsters/HandBrain/SurfaceV07/PA_HandBrain`，由 `Tools/MonsterFeedback/rebuild_active_handbrain_physics.py` 对蓝图实际引用的网格重建并强制保存。脚本没有重新导入模型或改动材质。重建前的网格与蓝图备份在证据目录 `before`；旧 PhysicsAsset 首次重建前未单独备份，旧几何、源码和失败画面保留于日志及 Git 历史。

新增 `MonsterSurfaceAudit` 从当前物理混合后的蒙皮矩阵读取顶点，对死亡前实际地面组件采样。不能用 `GetCPUSkinnedVertices` 代替：它会刷新动画姿态，覆盖刚刚测量的物理混合状态。验收同时要求物理骨骼与渲染骨骼重合、可见表面接地，并保存实际尸体截图。

## 毒蛆播放喷毒但没有伤害

村庄的 `BP_LocalFogVolume_Master_C_7.Box` 为 `OverlapAllDynamic`。原 `SweepSingleByObjectType` 将它当作首次命中，24 颗毒滴均在该雾体内起步接触并销毁。发射计数增加，所以旧的村庄检查漏报。

毒滴改为收集沿途接触，按距离选择玩家主碰撞胶囊或 Visibility 真正阻挡的表面，忽略仅重叠的雾效和触发盒。玩家胶囊本身忽略 Visibility，因此仍单独识别玩家主胶囊。墙体遮挡、伤害一次、固定喷射朝向、攻击时序和中毒概率保持原合同。

村庄增加实际玩家命中检查；专用场地在毒蛆和玩家之间放置覆盖发射点的 `OverlapAllDynamic` 盒，验证穿过触发盒仍命中、后方实体墙仍挡住毒滴。

## 左上角 Buff / Debuff 栏

此前 UE 没有独立状态效果栏。参考为原 `game-dev/src/ui/status-bar.js`、`src/ui/panels/hud-core.js` 和 `game-style.css`；本轮实际运行原 JS/CSS 查看样式，源文件散列见 `reference/source.json`。新实现为 `StatusEffectsComponent`、`StatusEffectsHUD`，显示目录为 `Content/ColdSteelData/status_effects.json`。

- 保留原版左 104、上 12，54×44 卡片、12 px 横间隔、单行容器、圆角彩色边框、图标、层数、秒数和底部剩余进度。抵消游戏分辨率 DPI 曲线，避免 720p 时卡片和数字缩得难以辨认。
- 按住左 Alt 显示鼠标，悬停查看浅色中文说明；松开 Alt 回到游戏。状态超出一行可用滚轮翻看。无状态时自动隐藏。
- 中毒和恐惧直接读取实际战斗组件，变化事件刷新，倒计时每 0.1 秒更新；死亡隐藏，真实重生后重新绑定新玩家。
- 中毒倒计时明确表示“下一次消退一层”，恐惧使用实际失效时间。效果名称、说明和颜色包含原版 31 种显示定义；通用记录支持计时、持续及剩余场数。
- 本轮接通的实际战斗效果是中毒和恐惧。通用 Buff/护盾记录用于显示接口验收，不代表新增了护盾减伤或搬迁了全部 31 种效果的玩法。

## 重跑和证据

`Tools/MonsterFeedback/Run-Regression.ps1` 支持 Maggot（村庄）、Arena、HandBrain、Status、AI 和 Nurse，使用独立存档、独立新游戏进程。`-Width/-Height` 测显示尺寸；`-CorpseYaw` 改变手脑死亡朝向，只用于验收。

构建及每次报告须检查明确完成标记和失败列表。最终数字与资源散列见本目录对应的 `SourceAssets/MonsterFeedback20260911/acceptance-summary.json`。构建期间并行攀爬改动的新时间参数已同步到定义与调用，未覆盖其余实现；这两个共享文件保留在并行工作区，不随本轮怪物/UI 提交整份暂存。

二进制资源与截图遵守项目本机恢复规则，留在完整 D 盘宿主；公开 Git 提交源码、显示目录、工具和验收摘要。没有以本次开发态验证替代打包、联机或人工试玩验收。
