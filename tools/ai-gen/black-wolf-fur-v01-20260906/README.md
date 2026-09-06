# 黑狼黑色皮毛优化 V01

基于当前游戏的 `assets/models/wolf_quaternius.gltf` 制作独立候选，保持黑狼身份、体型、51 根骨骼和 12 个现成动作。本轮没有切换游戏正式引用。

## 修改内容

- 为原无 UV 网格补独立 UV 图集，烘焙 2048×2048 颜色、粗糙度、切线法线贴图。
- 黑色底毛配炭灰毛束高光、略浅底绒；短毛通过材质表现，不使用透明毛片或毛发模拟。
- 黑鼻增加细孔与适度湿润反光，保留双侧琥珀色眼睛。
- 合并前验证同位置硬法线分裂顶点的蒙皮权重相同，随后焊接并平滑法线，重新归一化最多 4 个骨骼权重。
- 保留源网格所有空间位置、1962 个三角面，焊接后的编辑网格为 983 顶点。GLB 因 UV 接缝会重新分裂部分顶点，属于正常导出行为。
- 未添加僵尸犬的收腹、坏死伤口或浑浊眼睛。近景仍能看出原模型的棱角轮廓。

## 文件

| 文件 | 用途 |
|---|---|
| black-wolf-fur-v01.blend | 可编辑模型、蒙皮、原动作、打包贴图及可调烘焙材质 |
| black-wolf-fur-v01.glb | 含贴图和原动画的独立候选 |
| textures/albedo.png、roughness.png、normal.png | 2K 游戏材质贴图 |
| comparison-left.jpg、comparison-right.jpg | 同灯光下原黑狼与优化版对照 |
| black-wolf-review.jpg | 四视角评审图 |
| rendered/wolf/head-detail.png、fur-detail.png | 实际模型头部、体毛近景 |
| Idle.gif、Gallop.gif、Attack.gif、Death.gif | Godot 实际模型预览 |
| build_black_wolf.py | 独立构建脚本，从正式原黑狼读取；不依赖僵尸犬模型 |
| check_asset.py | 导出回读和原动作对照 |
| prepare_review.py、render_review.gd、package_preview.py | 独立 Godot 预览工程与预览打包 |

## 验证和时序

对 GLB 重新导入后按 60 Hz 检查全部 12 个动作，共 1262 个姿态。动作名称和时长与原素材一致，采样骨骼世界位置最大差约 0.00000358 个源模型单位；权重和最大误差约 0.000000119，最多 4 个骨骼影响。UV 有效，变形后顶点无非有限坐标或越界飞点。

原动作时长：Idle / Idle_2 各 3.333333 秒，Idle_2_HeadLow 4 秒，Gallop 0.566667 秒，Attack 1.333333 秒，Death / Walk 各 1.066667 秒，Eating 2.533333 秒，Gallop_Jump 0.933333 秒，Idle_HitReact1 / 2 各 0.666667 秒，Jump_ToIdle 1.333333 秒。

Gallop 延用前后肢交错收展与推进；Attack 延用前躯降低、前探咬击及回收；Death 延用失衡侧倒。预览采用原素材速度，正式黑狼脚本的 Attack 会用 2.5 倍速。GIF 为展示而重复播放，不代表 Attack / Death 在游戏中循环。本轮没有重制动作、修改接触窗口或做新的战斗控制器。

实际渲染使用 Godot 4.7.1、默认 D3D12 / Forward+、GTX 750 Ti，原版和优化版使用相同评审灯光及 0.3 缩放。完成模型/材质/动画预览检查，没有进行主场景战斗与性能验收。源动作已有局部低于零平面的情况，本轮未做落脚与死亡接地修正。

## 来源与重建

原模型来源沿用仓库记录：Quaternius / Ultimate Animated Animals，CC0。本轮使用现成的本地黑狼，不下载新模型。毛发源图复用本任务此前生成的 `fur-source.png`（1254×1254）：内置 imagegen 于 2026-09-06 生成，原文件为 `C:/Users/allan/.codex/generated_images/01a0763c-58a5-7572-993f-9d06fd3ec78c/exec-8b5ea642-ee0a-4149-84b8-e6f5c40a19a5.png`，要求灰黑犬类结块短毛、无角色和灯光阴影。黑色配色在 Blender 材质节点中重映射，最终烘焙图为 2K。

在 `E:/3d/3-dfps` 运行：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/ai-gen/black-wolf-fur-v01-20260906/build_black_wolf.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python tools/ai-gen/black-wolf-fur-v01-20260906/check_asset.py
python tools/ai-gen/black-wolf-fur-v01-20260906/prepare_review.py
& 'E:/3d/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64_console.exe' --headless --path E:/3d/black-wolf-fur-preview-20260906 --import
& 'E:/3d/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64_console.exe' --path E:/3d/black-wolf-fur-preview-20260906 --script res://render_review.gd --position 40,40
python tools/ai-gen/black-wolf-fur-v01-20260906/package_preview.py
```

导入前先设 Blender 30 fps，确保 glTF 秒数转为帧数时不被默认 24 fps 改写。

## 2026-09-06 整理记录

已清理数字命名逐帧截图与 Blender 自动备份；最终 GIF、动作检查表、命名近景、源文件、许可与重建输入保留。再次打包预览前先按重建步骤重新渲染。制作目录已用 `.gdignore` 排除游戏导入。
