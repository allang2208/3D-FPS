# 手脑死亡动作 / 五动作模型

输入：`../../howl_rebuild_v02/delivery/HandBrain_SingleFace.blend`。仅新增 Death 和中性的 death_pivot 骨骼；未改造型或重做原四个动作。

素材目录包含 idle、walking、attacking、attacking-2，未见专用死亡动作帧或死亡音效；Shounao 动画映射也只有 idle/walk/slam/howl。本动作是依据原怪物形体设计的三维死亡动作，不声称复原已有死亡参考。

## 动作设计

- 0–0.36 秒：短暂抽搐，头部与主体错峰失衡。
- 0.36–1.12 秒：向自身一侧（局部 -Y）加速倾倒，支撑面沿底部转移。
- 约 1.12 秒：侧面接地；随后轻微回弹、颈部和顶部手簇松弛。
- 2.05–2.8 秒：保持尸体姿态，无回站、缩小或消失。

30 FPS，1–85 帧，2.8 秒，单次播放并停末帧。GIF 重复播放仅供查看。视频未配无关攻击音效。

根骨骼 root 静止，局部 death_pivot 驱动倒地和接地修正。UE 按非 Root Motion 播放，停末帧；尸体的位置变化在骨骼姿态内。接入时碰撞、停止伤害、击杀奖励和尸体回收需由游戏代码处理，本次未实施 UE 战斗接入。

## 交付与验证

- `HandBrain_FiveActions.blend`：可编辑源，38 骨，纹理打包，打开时显示死亡末帧。
- `SK_HandBrain_FiveActions.fbx`、`HandBrain_FiveActions.glb`：Idle、Move、Attack_Slam、Attack_Howl、Death。
- `Death.mp4`、`Death.gif`：实际重新导入 FBX 后渲染的完整动作。
- `Death_standing.png`、`Death_impact.png`、`Death_corpse.png`：回读关键帧。
- `build_validation.json`：原四动作骨骼矩阵对比、源模型接地检查。
- `fbx_validation.json`：五动作时长、每帧主体接地、有限坐标、末帧保持、静止根骨检查。

材质与独立 UE DirectX 法线贴图复用 `../../howl_rebuild_v02/delivery/textures/` 及其 `ue_materials.json`；本版本材质槽未变。前一阶段头顶手掌展开幅度的限制仍然存在，本次只制作死亡动画。
