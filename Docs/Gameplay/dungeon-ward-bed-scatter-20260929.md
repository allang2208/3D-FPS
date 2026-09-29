# 病区随机病床接入

病床复用已导入的 `/Game/Props/HospitalBed20260929/SM_HospitalBed` 及三份材质；生成器保存进 `/Game/GameMaps/Design/L_AbandonedIsolationWard_Subject`。游戏入口仍为出征祭坛 → 废弃隔离病区 · 主体样板；未加入随机地牢房池。

每次进入游戏，`Ward_BedScatter` 在五间病房内各尝试随机放置 3～5 张病床。支持正放、左侧倒、右侧倒、倒置四类姿态，权重为 55/15/15/15%，再叠加任意水平朝向。倒置按真实床头、床尾高度计算约 -13.56° 倾角，使两端能共同承地。生成是一次性的，床没有持续物理模拟或 Tick。

摆放使用旋转后的实际模型及碰撞范围，底部贴合地面上方 2 mm；距离墙体至少 65 cm，床间包围范围留出 110 cm。配置保留 14 处禁放区，覆盖双门摆动区、前后门通路及连接段。候选还需要通过世界阻挡重叠查询。每张目标最多分配 48 次尝试；无合适位置便少生成，不强行放置。布局可用同一 seed 重现，默认每次 BeginPlay 使用新 seed。

碰撞资产单独保存为 `/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_HospitalBed`，保留原始病床。床垫、布料、枕头和床架采用共 61 个贴合凸体；U 形床头／床尾沿管段拆分，避免整床包围盒封死床垫上方的空气。可见模型、贴图及材质槽沿用来源资产，碰撞使用 SimpleAndComplex，组件采用 BlockAll、QueryAndPhysics、StepUp Yes。床由一个 ISM 组件管理，保持静止供现有 `FPSTraversalComponent` 判断稳定表面、站立区、翻越路径及落点；不绕过原有高度、宽度和落点限制，不增加专用交互按键。

制作与落盘：

- 原生源码：`Source/FPSGAME/Dungeons/WardBedScatter.h`、`.cpp`。
- 配置：`SourceAssets/DungeonIsolationWard20260929/Config/room.json` 的 `bed_scatter`；完整病区安装器已接入同一配置函数。
- 碰撞作者、FBX、可编辑源、姿态配方及保存脚本：同批 `BedScatter/`。
- 正式 Editor DLL 构建成功：`Saved/BuildEditor/build-20260929-183754.log`。
- 病床及材质用途已保存；首次关卡配置因 Python 包围盒构造接口差异中止，未保存残缺地图。改用 `Box(min,max)` 对应的原生构造后，只恢复地图阶段，未重复导入已完成资源。
- 最终地图后台保存退出码 0，标记 `WARD_BEDS_SAVED`：`BedScatter/Receipts/resume-map-commandlet-02.log`；配置了 5 间病房、4 类姿态、14 处禁放区。
- 修改前地图及病床材质保存于 `BedScatter/Before/UE/`。

来源署名：**“Hospital Bed” by loxfear**，Sketchfab 模型 `f8c13a19e84343e7b644c19f7b9488d3`，CC-BY-4.0；许可证保留在 `SourceAssets/HospitalBed20260929/license.txt`。本轮复用外观并另制碰撞及摆放逻辑。

本轮未运行随机生成、游戏、PIE、渲染或翻越测试；上述为已实现的约束和已完成的编译／保存事实，实际摆放及角色接触效果由用户测试。
