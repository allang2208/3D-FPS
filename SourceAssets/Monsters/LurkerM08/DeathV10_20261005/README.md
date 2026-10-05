# M08 死亡支撑修订 V10（2026-10-05）

用户反馈死亡动画沉入地下。本轮仅替换死亡动作，保留 V09 的空气炮、飞扑提速和其他动作，继续使用原模型、蒙皮、物理资产及共享尸体流程。

## 原因与制作

旧 V04 死亡片段在侧翻时附加 29 cm 骨盆下沉，死亡阶段又退出了活体接触步态。制作中还发现固定世界空间弯曲方向会让宽前臂在胸部侧倾后向支撑面下方折叠，连带拉低肘部皮肤；单纯整体抬高模型会引入悬浮。

V10 将倒地拆为失去支撑、侧倾和落稳三个阶段。骨盆主下压改为 10.5 cm，后段再加入约 1 cm 的承重变化；前后肢、左右侧按先后顺序卸力。二段 IK 在保持原骨长的情况下，选择更接近原弯曲方向、且肘／膝在支撑面上方的解，避免把关节折到地面下方。

逐帧制作使用原模型全部 625,042 个顶点的蒙皮绑定计算最低表面，再烘焙必要的高度补偿；同时在物理交接前参考现有躯干／头颈／背环胶囊留出间隙。最终制作记录中的最大整身支撑补偿约 8.56 cm。该数值是离线动作求解数据，不代表游戏内碰撞测试。动作时长仍为 1.4 s，保留现有 55%（0.77 s）布娃娃交接时点，预算不足时仍可播放到完整末帧。

没有修改共享死亡代码、PhysicsAsset、碰撞通道、尸体寿命或现有布娃娃预算。参考平面上的源动作支撑与游戏中的斜坡、台阶、墙面及物理接触效果分开，后者仍由用户测试。

## 制作文件与实际接入

- 作者入口：`Tools/LurkerM08/author_death_v10.py`。
- 可编辑源：`M08_Death_Grounded_V10.blend`。
- 导出：`Animations/A_M08_Death_DeathV10.fbx`，120 fps、169 帧。
- 安装入口：`Tools/LurkerM08/install_death_v10.py`，已追加到原完整安装链。
- 原动作集备份：`Before/DA_M08_AnimationSet.uasset`；旧动作引用：`before_references.json`。
- 新动作：`/Game/Monsters/LurkerM08/DeathV10/Animations/A_M08_Death_DeathV10`。
- 运行入口：原 `DA_M08_AnimationSet` 的 `Death`，F6 稳定 ID 继续为 `LurkerM08`。

本轮通过已运行编辑器的 `mcp_call_codex.ps1 -PythonScript` 互斥批次完成导入与保存，未新开编辑器。批次退出码 0、`success=True`；新死亡动画和原动作集已实际保存，`installation.json` 状态为 `death_v10_saved_and_bound`。本轮无原生修改，不需要构建。

未运行游戏、测试、截图或验收渲染。动画与物理交接的最终效果由用户体验确认。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
