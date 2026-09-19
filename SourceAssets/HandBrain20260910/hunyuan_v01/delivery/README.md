# 手脑 · 混元 3.1 动画候选 v01

路线：混元 3.1 生成主体及攻击参考模型 → 本地保留 UV 的减面与切口整理 → 独立攻击手臂、冠部手掌 → 功能骨架及蒙皮 → Idle / Move / Attack_Slam → FBX、GLB 回读与实际渲染。

## 文件

- `HandBrain_Animated.blend`：可编辑骨架、蒙皮、3 个 Action，贴图打包。
- `SK_HandBrain_Animated.fbx`：UE 导入候选，3 个动作，嵌入颜色和法线图。
- `HandBrain_Animated.glb`：带 PBR 和动画的便携检查文件。
- `textures/`、`ue_materials.json`：UE 独立贴图与各材质对应关系。颜色 sRGB；粗糙度及法线关闭 sRGB，金属度 0。独立法线已经翻转绿色通道为 DirectX，不要再次翻转。FBX 内嵌法线保留原始 OpenGL，UE 接入时应改用这些独立 DirectX 法线。
- `ThreeAnimations.gif`：三个动作并列预览。另有各自动作 GIF / MP4。
- `FBX_impact_proof.png`：重新导入 FBX 后的命中姿态渲染。
- `animation_contract.json`：时序，Attack_Slam 在 1 秒命中。

高模保留在上一级 `handbrain_hunyuan_v01.glb`，约 50 万三角面；可编辑静态高模为 `handbrain_hunyuan_v01.blend`。生成来源、脚本与检查报告都在上一级。

## 已验证

动画网格共 163463 三角面、3 个网格、25 根骨骼，最多 3 权重/顶点。GLB 和 FBX 回读均无未绑定顶点，坐标有限，颜色/法线图正常加载。

Idle 2 秒循环；Move 1 秒循环；Attack_Slam 2 秒单次播放。30 FPS 烘焙；两个循环首尾矩阵误差接近零。砸击第 31 个烘焙帧（1 秒）最低点 Z≈0.012 米。GIF 的重复播放只便于观看，不表示攻击在游戏中循环。

制作坐标 +X 朝前、Z 朝上，主体高约 2 米。Move 是原地蠕行；真实位移由 UE 负责，不能再叠加动画根位移。

## 当前边界

这是首版动画资产，尚未做 UE 导入、PIE、AI、碰撞和伤害运行验收。原移动速度 160 是二维像素配置，不能直接当厘米或米套入 UE。

主体采用保留 UV 的三角面简化，不是全手工四边形重拓扑。攻击臂和展开冠部来自另一张原动作参考，做了切分、蒙皮和伸缩收纳；手掌尚非逐根手指关节控制。背面与遮挡区域是三维重建。Idle 的微动为新增设计，原参考只有静态一帧。

本轮未制作独立 Howl 技能，也未替换游戏正式怪物。原始图像由用户提供，二进制资产不公开提交。
