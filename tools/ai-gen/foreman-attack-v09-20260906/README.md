# 工头 V09：攻击动作候选

本轮在 V08 模型上只重做 Attack，保持正式场景仍使用 V08。未修改身体网格、UV、蒙皮、材质、贴图和战斗参数；没有调用 Meshy 或新增 AI 建模。该候选已因动作自然度未满足用户预期停止采用，仅保留源与对照记录。

## 动作改动

- 右脚承重蓄力，左脚 0.24–0.50 秒前跨、0.50–0.98 秒保持承重、0.98–1.36 秒抬脚回收；骨盆有小幅重心前移，角色整体位移仍由控制器负责。
- 骨盆、脊柱、胸、颈、头分配不同幅度和时间偏移；左臂先展开平衡，接触时回收，右肘腕沿各自轨迹下抽；命中后继续压身并回收。
- 鞭子在接触之前已有从近端到远端的 65 ms 传播延迟，远端接触曲线键安排在 0.59625 秒；收势有沿鞭身传播的余振。仍使用 V08 的 33 个同级截面骨、单位缩放和 6.4 m 绑定长度。
- Attack 1.5 秒；实际玩法的 0.59625 秒命中和 0.45 秒音效代码未改。攻击首尾分别匹配原动作的首尾，不强行把两端改成同一姿态。

完整参考和阶段说明见 `reference-contract.md`。原二维动作为 39 个不等长帧；三维重心、深度及骨骼运动属于重建，不是动捕。

## 可查看文件

- `Attack-comparison.gif`：同视角身体动作对照，左 V08、右 V09，实际速度。
- `Whip-comparison.gif`：同视角完整鞭子轨迹对照，左 V08、右 V09，实际速度。
- `contact-body.jpg`、`contact-side.jpg`：准确 0.59625 秒接触姿态。
- `v09-body-frames-0/1/2.jpg`、`v09-side-frames-0/1/2.jpg`：完整 36 帧检查表。
- `foreman-attack-v09.blend`：可编辑源，原贴图已打包；`foreman-attack-v09.glb`：导出候选。

预览使用 Godot 4.7.1 默认 D3D12 / Forward+、GTX 750 Ti，4x MSAA。独立灰地和固定环境光、两盏检查灯用于两版相同比较，未修改正式游戏光照；不是完整矿洞试玩。GIF 每份 36 帧，总时长 1500 ms，展示重播不代表游戏攻击循环。

## 已完成验证

- `preservation-validation.json`：实际两份 GLB 比较；另外四动作共 696 个动画通道保留，91 个 Attack 通道改变。网格位置/索引/UV/法线/权重、逆绑定矩阵、材质和贴图字节一致；原攻击首尾保持。
- `export-validation.json`：5 动作 1349 个插值姿态，鞭子变形有限，单位骨骼缩放，绑定中心线约 6.4 m。完整动画时长为 Idle 1、Walk 1.5、Attack 1.5、Howl 3、Death 1.4 秒。
- `review-report.json`：GLB 重新导入 Blender 后检查。0.42→0.59625 秒腕部向下 1.4726 m，向前 0.8449 m，符合本角色既有下抽方向约束。前脚 0.51–0.94 秒水平漂移约 0.000088 m；Attack 最低顶点距地约 4.81–5.02 mm。
- `import.log`、`render.log`：独立 Godot 工程导入及两版全程渲染完成。身体与侧视分别覆盖完整动作和准确接触时刻。
- 本轮没有切换正式怪物或改伤害控制器，因此没有重新进行战斗行为与主场景回归。肩袖、手掌和脸部的既有模型/材质限制依然存在，动作自然度待用户反馈。

早期候选在向前/向下位移比例检查中未通过，已收回扬鞭阶段的手部位置后重导并复核；当前报告均来自修正后的候选。Blender 导出仍提示存在多个图像节点时选择首个 sampler；实际纹理字节和材质与 V08 一致。

## 重建

使用 `E:/Program Files/Blender Foundation/Blender 5.1/blender.exe`，建议带 `--background --factory-startup --python-exit-code 1`。

1. 执行 `build_attack.py`。输入 V08 Blender 源，数学函数取自 V07 `build_motion.py`，不执行旧模型修改或其他动作生成步骤。
2. Python 执行 `check_preservation.py`、`check_export.py`；Blender 执行 `check_motion.py`。
3. Python 执行 `prepare_review.py`，建立 `E:/3d/foreman-attack-v09-preview-20260906` 独立预览工程。
4. Godot console 对该工程运行 `--headless --import`，再运行 `--script res://render_review.gd` 完成实际渲染。
5. Python 执行 `package_preview.py` 生成对照 GIF 和检查表。

所有本轮源文件和检查证据保留在本目录，未覆盖 V08 或操作共享暂存区。

## 2026-09-06 整理记录

已清理数字命名逐帧截图与 Blender 自动备份；最终 GIF、动作检查表、命名近景、源文件、许可与重建输入保留。再次打包预览前先按重建步骤重新渲染。制作目录已用 `.gdignore` 排除游戏导入。

V09 攻击候选已按用户对自然度的反馈停止采用；正式工头仍用 V08。现有源和对照仅作历史参考，不代表获批版本。
