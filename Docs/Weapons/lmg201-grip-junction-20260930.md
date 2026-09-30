# 201 后握把连接面与材质修复

> 发布说明：此页保留当时制作记录；本机模型、回执与图片不公开，已退役资料从 trash 恢复。当前恢复入口见 [201 发布记录](lmg201-publication-20261001.md)。

2026-09-30。用户要求修复后握把连接处和粗糙表面。当前修订为 GripJunction44，已后台导入保存。

## 修改

- 移除 G43 独立通用连接座。原厂及稳定、平衡、幽灵握把分别沿自身颈部边界生成连续过渡，不再用同一个连接块覆盖不同肩宽。
- 原厂保留原有下部网格和绑定；三种改装握把先重接破碎表面，再形成连接颈，转移源 UV／角点法线，制作约 45,000 三角形的游戏网格。握持安装枢轴、原厂隐藏分区和手部动作不变。
- 新颈部写入实际 UV0，接缝处延续原 UV；专用 UV 蒙版使源结构法线和 AO 平滑退出新安装面。
- 每个握把本体及颈部共用聚合物材质，粗糙度中心 0.53 → 0.46，微纹波动减小，额外颗粒法线强度归零。

## 已保存

- 现用枪体 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。
- `Accessories22/Meshes` 内三个改装后握把。
- `DA_LMG201_AttachmentWetMaterials` 与四份 `GripJunction44/Materials` 私有材质。
- `Material21/bindings.json` 当前绑定已更新。

保存回执：delivery.json（本机历史资料：`SourceAssets/LMG20120260927/GripJunction44/delivery.json`）。制作方法与恢复入口：[J44 README](../../SourceAssets/LMG20120260927/GripJunction44/README.md)。完整已保存枪体导出为 `GripJunction44/Exports/After_Body.fbx`，游戏编辑源为 `GripJunction44/RuntimeSource/LMG201_GripJunction44_Runtime.blend`。

首次后台导入因高密度制作中间网格发生内存不足；本轮写出的稳定握把中间版本按回执与原备份恢复，再使用游戏网格完成保存。最后 commandlet 退出码为 0，记录 `J44_CURRENT_SAVED 5`。这表示制作和保存完成，不是外观验收；本轮没有修改 C++，没有打开 UE GUI、运行游戏或追加渲染测试，效果交由用户测试。
