# 流体交互五项接入（2026-09-24）

## 已制作并落盘

1. **角色涉水**：本地玩家在现有脚步节奏中触发左右脚水花；入水、奔跑、落地按速度和水深调整强度。其他 Character 角色由共享调度器按移动距离触发，近处 40 m 内参与。河流、已注册的喷泉池和地牢积水使用同一水面查询与已有水花／涟漪池。NPC 使用移动距离节奏，不依赖各模型独立动画通知。
2. **火球／陨星击水**：沿实际飞行段寻找首次水面交点，触发水花、扩大的涟漪和短暂蒸汽；同一投射过程只触发一次。湿命中的新增烟雾转浅色，关闭新增的贴地灰烟层。伤害、飞行轨迹、陨星持续伤害规则保留；本轮没有增加“遇水取消魔法伤害”的规则。
3. **巫婆毒池地形边界**：落地时采样 16 个方向，每方向最多 3 次地面查询及 1 次遮挡查询，收缩不支持的高度／断层／遮挡区域。四个向量材质参数保存同一组径向边界，贴花与伤害判定都使用相同插值；原有每次伤害的视线遮挡仍保留。毒池蒸气出生点也限制在边界内部。
4. **风向**：爆燃余烟、击水蒸汽及毒液薄雾取自 `AFPSWeatherManager::GetWeatherWind()`。附近屋顶遮挡衰减到 12%；缓存最多 128 格，2 秒有效，每帧最多 2 条新增屋顶射线。Niagara 风向每 0.2 秒刷新；短命毒雾在出生时取样，随后以阻力渐进跟随。
5. **统一细节预算**：共享距离、引擎特效质量和数量额度，降低额外液滴／薄雾／烟团数量，给命中与玩家涉水保留额度。水花仍为 12 槽、涟漪 8 条；蒸汽新增 6 槽；毒液仍为 192 液滴＋48 雾片＋40 残留贴花。危险毒池和投射物主体不随装饰预算消失。新增系统没有运行时三维流体求解，也没有新增纹理。

## 实现范围与性能边界

- 共享调度器：`Source/FPSGAME/WorldGeneration/FluidPresentationSubsystem.{h,cpp}`。每次 0.025 秒调度最多 8 个 Character；使用初始关卡、关卡加入和 Actor 生成事件登记，不在每帧搜索世界。
- 装饰额度为容量 72、每秒补充 180 的权重额度，非精确 GPU 粒子计数或帧时间保证。低优先级细节不能使用最后 12 个额度。已存在的魔法主体、灯光、危险贴花没有因此被隐藏。
- 地形毒池是有限方向的落地采样，半径内的极窄缝隙可能超出采样精度；不是逐像素流体碰撞。毒池生命内不会重建地形形状，动态遮挡仍由原有伤害视线判定处理。
- 复用已接受的自然水花材质和贴图。水花资产仅修改液滴数量的预算输入，没有重建贴图或 Crown 材质，保留之前去除方形底片的修复。
- 每个新增烟团使用现有 Mantaflow 密度图的 R 通道，保留原有贴片边缘裁切与寿命消散。

## 已保存资产

- `/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic`
- `/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalImpact`
- `/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam`（新增）
- `/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash`
- `/Game/Fluids/VenomProjectiles20260924/M_WitchPoisonPool`

后台制作入口：`Tools/Fluids/author_fluid_interactions.py`。火系烟雾和毒池原始制作脚本也已更新新参数／材质输入；水花完整重制后应再次运行本增量入口接入预算。

资产生成记录：`SourceAssets/FluidInteractions20260924/assets-saved.json`、`author-cmd-01.log`。commandlet 退出码 0；Niagara 和材质完成制作编译及保存。编辑材质输入过程出现过未接线的中间编译提示，最终材质编译与保存完成。

常规 C++ 构建：`Saved/BuildEditor/build-20260924-152017.log`，Succeeded，正式 `UnrealEditor-FPSGAME.dll` 已生成。

构建同时遇到现有冶炼代码的四处编译问题，已作最小修正：`ColdSteelSmeltingWidget.h` 的三个 UPROPERTY 分开声明；`SmeltingSystem.h` 改为同目录头文件路径；`ColdSteelSmeltingWidget.cpp` 改用垂直容器的添加 API 与数组 `IsValidIndex`。未改冶炼功能设计。

**遵循用户规则，没有启动编辑器或游戏，没有运行自测、截图、视觉验收或性能采样。实际观感与帧率由用户运行后确认。**
