# 缚群 — Meshy 主体、独立衣物与 UE 接入

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户提供 `C:/Users/allan/Downloads/Meshy_AI_Fleshmaw_Leviathan_1006141038_texture.glb`，要求判断可用后制作衣物并接入 FPSGAME。保留下载原件；制作源位于 `SourceAssets/BoundCongregateMeshy20261006`。

## 主体判断

- 197,398 个三角面、153,072 个包含 UV 分缝的顶点；1 个材质，已有 UV。
- 原件是静态网格，没有骨架或蒙皮。
- 内嵌 2048² BaseColor、2048² Normal、4096² Metallic/Roughness；直接提取并沿用原 UV。
- 实际包含十条落地接肢，另有悬空小臂、嗅探颈、背部卷触手与细触须。獠牙口腔和脓包有几何体积，可继续作为主体制作。
- 本次未再次减面、重网格化或重做主体贴图。用户提供的 Meshy 文件为主体来源；不以本次本机接入声明公开再分发许可。

## 制作内容

56 骨骼专用骨架；各落地肢体采用独立上肢、下肢与手/足骨，触手和嗅探部位用独立链条。蒙皮沿焊接后的表面图传播并保留原网格 UV 分缝。

衣物为左侧灰绿破袍、较短右侧衬布、两条不同捐献肢体上的残袖，以及肩背束带和 M 标牌。大嘴和中央脓包保持外露。可见布料具有实体厚度，模拟使用独立连续单层代理；固定接缝、释放破损下摆。身体和腿部碰撞使用独立布料胶囊，远处以迟滞和混合逐渐退回蒙皮。

提供 Idle、Walk、TurnLeft、TurnRight、Bite、Hit、Death 七类动作。2026-10-07 已将移动替换为十足错相的 WalkV2、TurnLeftV2、TurnRightV2：行走标定速度 50 cm/s，运行速度默认 60 cm/s；撕咬接触点保持 0.92 秒。运行时脚底处理读取有限频率的地面采样，在动画线程完成十条接肢的 IK。动作源、接入和未测试范围见 [移动动画 V2](bound-congregate-locomotion-v2-20261007.md)。

## 游戏接入

- 类：`ABoundCongregate`，独立动画实例 `UBoundCongregateAnimInstance`。
- 资产目录：`/Game/Monsters/BoundCongregate`。
- 生成入口：F6 → 缚群，蓝图 `BP_BoundCongregate`。
- 使用共享 `MonsterAIController` / Behavior Tree 的感知、追击和返回；本体只执行动作与攻击时序。
- 2026-10-07 已补齐蓝图的共享 `BP_MonsterAIController` 引用及其 `BT_Monster`，修正原生控制器未配置行为树的问题。
- 接入共享属性、防御、韧性、受击、中断、死亡奖励和尸体寿命。撕咬由服务端单次结算，中断或死亡取消待触发命中。
- 默认生命 1800、等级 10、普通阶级、物防 45、魔防 25、撕咬伤害 55，可在蓝图继续调整。
- 运动胶囊和导航采用现有 225 cm / 450 cm 支持代理，使用现有宽体楼梯移动。
- 非人形死亡使用 M14 V19 连续软体标准，独立代理、全表面绑定和变形法线材质。旧死亡片段仅作为数据缺失时的后备。
- 音频引用现有 M10 呼吸、撕咬与死亡素材，使用空间衰减。
- 不修改既有随机遭遇种群分布；当前入口为明确可选的 F6 怪物生成。

## 制作与导入

1. Blender 执行 `Tools/BoundCongregate/assess_source.py`：仅完成用户要求的主体可用性观察。
2. Python 3.11 执行 `prepare_rig.py` 与 `author_fabric.py`。
3. Blender 执行 `author_model.py`，生成 `.blend`、完整带衣物的 FBX 和七段动画 FBX。
4. 编辑器关闭、现有编译结束后，执行 `finish_background.ps1`，依次完成正常 Editor/Game 构建以及后台资产导入。
5. `import_assets.py` 实际导入贴图、材质、骨架、模型与动画，制作命中碰撞与 Chaos 布料，生成软体尸体并保存蓝图。

`Records/background-stage.txt` 记录后台当前阶段；`Records/delivery.json` 只有在所有资产保存完成后才写入 `complete: true`。脚本存在或外部 FBX 导出本身不代表 UE 接入完成。

## 交付边界

2026-10-06 已完成 Editor/Game 正常构建和后台导入保存，`Records/delivery.json` 为 `complete: true`。实际蓝图为 `/Game/Monsters/BoundCongregate/BP_BoundCongregate`，模型朝向补偿 -90°；软体尸体包含 681 个代理节点、2232 个四面体。最终后台流程正常结束，编辑器未自动打开。

制作中已处理物理资产工厂的交互对话框限制、动画导入参数的编辑器属性接口，以及软体尸体复制期间的异步派生数据缓存同步问题。后台制作会在当前进程关闭骨骼资产异步编译，已绑定的尸体不会再次被当成活体骨架重绑；不修改项目运行配置。

主体可用性观察包含离线静态视图。本次未运行游戏、PIE、布料与动作验收渲染、性能测试或回归。绑定质量、转身落脚、衣物碰撞和实战体验由用户测试；原始下载文件与完整主体制作源保留。

## 2026-10-07 白模修正

用户反馈游戏内仍显示白模。该次运行日志明确记录五种活体材质缺少 `SkeletalMesh` 用途，导致游戏绘制改用默认材质。原始颜色、法线与粗糙度贴图已存在，问题发生在材质着色器用途设置。

`repair_material_usage.py` 已在无界面 commandlet 中执行，为活体及尸体实际引用的材质补齐 `used_with_skeletal_mesh`、`used_with_clothing`，完成重编译和包保存。只修改用途，不重建材质图，保留尸体变形法线。`import_assets.py` 同步设置这两个用途，后续重导不会再次漏掉。执行记录位于 `Records/material_usage_fix_20261007.json`，本次后台进程退出码为 0。

`render_textured_source.py` 使用已有 Blender 制作源和实际贴图输出 `Preview20261007/BoundCongregate_Textured_Source.png`。这是离线材质预览，不是 UE 游戏截图。本次未启动或重启编辑器、未运行游戏或动作布料测试；游戏内结果由用户测试。
