# 蓝色尖顶法师帽与头部装备外观

物品 ID：`ue_blue_mage_hat`。设计图：`SourceAssets/BlueMageHat20261019/Design/blue-mage-hat-concept-v01.png`。首版沿用蓝色法师长袍的钴蓝织物、浅银刺绣、深蓝内衬和蓝宝石。当前需求包含设计和从头搭建头部装备；设计图已提供，尚无用户对首版外观的试玩确认。

## 模型与材质

- 帽口按当前 Jason 头部的原始蒙皮网格采样，在头顶以下 7.8 cm 定位，使用椭圆开口和约 0.5 cm 起的穿戴余量；适配数据保存在 `fit.json`。
- 帽身有独立外层、内衬、收口、汗带、卷边、帽带、星纹、藤纹和蓝宝石帽扣。宽檐与帽冠下段固定，顶部向后弯垂。
- 本次复用长袍的布料/刺绣 BaseColor、Normal、ORM 六张贴图，使织纹尺度和材质一致。新制深蓝刺绣帽带和银线材质，其余材质引用已保存的长袍资源。
- 可编辑文件：`Exports/BlueMageHat.blend`；独立骨骼交换文件：`Exports/BlueMageHat.fbx`；参数化源：`Tools/BlueMageHat/author_hat.py`。Blender 文件打包贴图并保留同源织物表面高模。
- 源模型 74,480 三角形。UE 使用三级 LOD，目标比例 100%、55%、25%，保留骨骼边界和边缘。物品展示及掉落模型另行保存为静态网格。图标已转入[法师套装图标标准](blue-mage-set-inventory-icons-20261019.md)，现为 320×320 透明 PNG，原路径保持。

## 头部装备系统

现有装备槽 1 和内部 `helmet` 标识继续使用；用户可见槽名改为“头部”。新增 `player_body.json/head_equipment` 外观配置。配置支持独立骨骼帽子，也支持后续静态头盔，并按角色头型保存位置、旋转和缩放。

`UFPSPlayerBodyComponent` 从通用装备快照提取槽 1，异步加载外观并挂到身体的 `head` 骨骼。使用现有装备存档、服务器接受流程和 `ReplicatedOutfit`；没有添加客户端任意装备 RPC，也没有另外复制每帧帽尖姿态。

所有武器姿态共用身体头部挂点，不依赖各武器第一人称手臂网格。第一人称的帽子沿用现有头部隐藏和身体投影策略；第三人称及其他玩家视角显示。当前仅配置了 Jason 头型，未来新增头型应制作对应 `fits`，避免直接套用不匹配的尺寸。

帽子加载成功后仅隐藏发型对应的头发 Groom，保留脸部、眉毛和睫毛。摘帽恢复同一发型，保存中的发型选择不会改变。异步装备请求使用代次控制，避免快速换装后的旧请求重新戴上帽子；销毁角色时释放加载句柄和组件。

## 帽尖动态

`UFPSHeadEquipmentMeshComponent` 是独立 PoseableMesh 组件，使用固定帽根及三节柔性帽尖骨骼。它从头部平移加速度和角速度计算轻量角弹簧：最大偏转 10°、频率 2.5 Hz、阻尼 0.6。只有上段蒙皮参与摆动，帽口和帽檐保持稳定。

这是骨骼弹簧物理效果，未使用 Chaos 布料或碰撞刚体。远于本地相机 22 m 时回到静止姿态；隐藏且无需投影时停用动态 Tick。传送、长帧和重新显示时重置，不保存或联网发送弹簧速度。使用固定骨骼包围盒及额外摆幅余量。

## 制作、接入与交付记录

1. `capture_head.py` 后台读取已有头型，`author_hat.py` 生成模型、蒙皮、材质源与库存图标。
2. `run_build.ps1` 通过现有 UE 批次互斥等待后台构建窗口，构建 `FPSGAMEEditor` 和 `FPSGAME`。
3. `run_asset.ps1 -Script save_assets.py` 导入独立骨骼 FBX，保存材质、三级 LOD、展示模型、掉落模型及图标纹理；不修改人物骨架。
4. `publish.py` 在资产实际保存后，只写入该物品和 `head_equipment` 配置项，复制库存 PNG。已有 `/Game/Characters/ModularOutfit20260924` Cook 目录覆盖新资产。

逐项保存结果见 `SourceAssets/BlueMageHat20261019/saved_assets.json`，物品接入结果见 `published.json`，构建结果见 `headgear-build-02-FPSGAMEEditor.txt` 和 `headgear-build-02-FPSGAME.txt`。导入失败后的续跑以源 FBX 哈希跳过已保存骨骼模型，以各阶段保存回执恢复后续工作。

本次实际落盘：`hat-import-03` commandlet 返回 0，保存回执 `completed=true`，骨骼网格 LOD 数为 3；`publish.py` 已完成槽 1 的物品和配置发布。Editor 与 Game 两个 Development 构建均成功。导入后的骨骼坐标已用于计算最终头型挂点，避免 FBX 坐标约定影响贴合位置。

本次不启动游戏、PIE 或可见编辑器，不执行视觉、动作或联机测试。穿戴贴合、帽尖手感、摘戴发型恢复与联机显示由用户在游戏中测试。
