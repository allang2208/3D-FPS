# 近战格挡张掌与内倾姿态 — 2026-09-26

已通过无界面 commandlet 修改并保存普通柄和长柄各三段动画：`Guard`、`GuardHit`、`GuardBreak`。游戏继续使用原资产路径。

- 剑身沿原画面中的斜向排列，改为向玩家一侧内倾 12°，以握柄位置为转动支点。
- 左手改为五指自然分开的张掌姿态；各指保留轻微且不同的弯曲，拇指独立外展。
- 左手承托点位于握柄前方沿剑身约 28 cm 处，左肘向外、向下弯曲。两骨骼解算保持臂长，上臂通过前臂变形的最短旋转承接其扭转，辅助骨骼随完整臂段运动。
- 抬手过程提前舒展手指；格挡受击保持张掌，破防后在回收末段平滑重新握柄。普通柄和长柄分别沿用各自原来的待机端点。
- 原动画时间保留：抬起 0.20 s、受击约 0.220833 s、破防动作 0.40 s；格挡、弹反、耐力等玩法参数不在此次修改范围。

## 游戏资产

普通柄目录：`/Game/Weapons/AzureRunesword20260913`。

长柄目录：`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations`。

两个目录中均保存 `A_RuneSword_Guard`、`A_RuneSword_GuardHit`、`A_RuneSword_GuardBreak`。

## 制作源与交付

制作目录：`SourceAssets/MeleeOpenPalmGuard20260926/`。

- `pose_config.json`：内倾、承托、肘部与手指调参。
- `author_guard.py`：使用当前原生骨骼采样和已接入的 V7 裸手模型制作动画；保留可见蒙皮的 Blender 源文件。
- `Standard/`、`LongGrip/`：各自的可编辑 `.blend`、原生动画 `.fbx` 及骨轨 JSON；FBX 已写入动画的重新导入来源。
- `Before/`：本次修改前的六个动画资产备份。
- `import_receipt.json`：六个资产的保存记录。
- `install_guard_saved.log`：后台制作保存日志，进程退出码 0。

本次复用现有骨架、手臂模型与材质，不引入外部资产。未启动交互编辑器或游戏，未渲染、运行测试或进行视觉验收，交由用户实际体验后调参。
