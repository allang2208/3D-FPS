# 僵尸犬 V01 · 黑狼资产改造候选

基于游戏正在使用的 Quaternius 黑狼制作，保留原有 51 骨骼和 12 个现成动作。交付独立候选模型，没有接入怪物生成器或修改原黑狼。

## 外观与蒙皮

- 灰败、结块的短毛；皮毛通过颜色、粗糙度和法线表现，没有新增毛发模拟或透明毛片。
- 左侧肋腹大面积坏死脱毛，右肩与右后腿较小伤口，左脸腐损与单侧浑浊眼睛。不同方向的伤口不做镜像。
- 原网格局部收腹、伤口浅凹，平滑法线并细分为 7848 三角面；仍保留原黑狼的低多边形轮廓，近景口鼻与耳缘尚有明显棱角。
- 补 UV；原权重随细分插值，每顶点最多 4 骨骼影响并重新归一化。没有重新自动绑骨，也没有重新生成攻击动作。
- 游戏材质为单个不透明 PBR 材质，使用 2048×2048 的 albedo、roughness、normal 三张贴图。

## 交付文件

| 文件 | 用途 |
|---|---|
| zombie-dog-v01.blend | 可编辑网格、骨架、现成动作；保留用于烘焙的材质节点和打包图像 |
| zombie-dog-v01.glb | 独立候选；内含模型、蒙皮、12 个动作与贴图 |
| textures/ | 2K 游戏贴图 |
| fur-source.png / wound-source.png | AI 生成的材质输入；来源见 source-contract.md |
| comparison-left.jpg / comparison-right.jpg | 相同灯光、视角、缩放下的原黑狼与候选对照 |
| zombie-dog-review.jpg | 四视角实际模型渲染 |
| rendered/zombie/wound-detail.png / head-detail.png | 伤口和头部近景 |
| Idle.gif / Gallop.gif / Attack.gif / Death.gif | Godot 实际模型动作预览；GIF 重复播放便于检查，单次技能和死亡的游戏循环语义不由 GIF 决定 |
| *-frames-*.jpg | 逐帧接触表 |
| build-report.json / asset-validation.json / preview-report.json | 构建、导出回读与 GIF 时长记录 |

## 验证结果及范围

重新导入最终 GLB，对全部 12 个动作按 60 Hz 共检查 1262 个姿态：51 根骨骼保留，动作名称和时长与原始资产一致；采样骨骼世界位置最大差约 0.00000358 个源模型单位；权重和最大误差约 0.000000119，无空权重或超过 4 个影响的顶点。候选 UV 有效，所有采样变形顶点为有限坐标且未发生越界飞点。

实际渲染使用 Godot 4.7.1 默认 D3D12 / Forward+（GTX 750 Ti），固定评审灯光。查看了左右对照、伤口/头部近景、奔跑/攻击/死亡接触表；此结果是模型和材质预览，不是正式游戏战斗或性能验收。候选有原动作时序下的局部低于零平面情况，死亡最低约 -0.058 米（0.3 缩放），没有在本轮重制动作或宣称完成地面接触修正。

GIF 时长分别为 Idle 3.330 秒、Gallop 0.570 秒、Attack 1.330 秒、Death 1.070 秒，与素材原速差不超过 GIF 的 5 毫秒量化容差。当前黑狼游戏脚本会加速 Attack，本候选使用素材原速便于检查皮肤变形。

## 再生成

在 `E:/3d/3-dfps` 执行，Blender 路径使用本机安装位置：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/ai-gen/zombie-dog-v01-20260906/inspect_source.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/ai-gen/zombie-dog-v01-20260906/build_zombie_dog.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/ai-gen/zombie-dog-v01-20260906/check_asset.py
python tools/ai-gen/zombie-dog-v01-20260906/prepare_review.py
& 'E:/3d/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64_console.exe' --headless --path E:/3d/zombie-dog-preview-20260906 --import
& 'E:/3d/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64_console.exe' --path E:/3d/zombie-dog-preview-20260906 --script res://render_review.gd --position 40,40
python tools/ai-gen/zombie-dog-v01-20260906/package_preview.py
```

实际渲染输出与候选文件位于本目录。材质源图已保存，再生成不需要重新调用图像生成服务。

## 2026-09-06 整理记录

已清理数字命名逐帧截图与 Blender 自动备份；最终 GIF、动作检查表、命名近景、源文件、许可与重建输入保留。再次打包预览前先按重建步骤重新渲染。制作目录已用 `.gdignore` 排除游戏导入。
