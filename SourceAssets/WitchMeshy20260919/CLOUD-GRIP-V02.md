# 云端动作与持杖修订 V02

2026-09-20，响应用户对行走和持杖姿势的否定。旧 LocalRetarget V01 保留为追溯源，不再作为认可动作。

## 已取得的云端源

复用原 animation_Walk、animation_CastPoison、animation_ThrowPoisonBottle、animation_DeathBackward 任务，全部带角色 GLB/FBX 已下载；Idle 原本已落盘。没有新增生成/套用任务，没有新增扣费。原生云端文件保存在各 Meshy/animation_*/downloads，下载清单包含大小与散列。

V02 从 Meshy 原生角色动画直接制作，没有再次进行全身骨链重定向。保留同一 Meshy 网格、24 骨层级、UV 和 PBR；五段动作使用 120 FPS 烘焙，待机 2 s、行走 1.1 s、两次攻击与死亡各 1.5 s。攻击事件仍为施法 0.535714 s、投瓶 0.75 s。待机/行走去除水平净漂移并处理循环末端。

## 左手与法杖

读取输入权重发现 LeftHand 顶点组最大权重为 0，而法杖原来挂接 LeftHand；手的蒙皮主要由前臂驱动。V02 在手腕附近渐变分配到原有 LeftHand 骨，局部调整 1238 个顶点的权重；689 个远端手部顶点制作固定卷握形状。没有增加手指关节，不宣称已具备五指独立开合。

左手掌心的参考握点由手腕、前臂和角色朝向共同定义；法杖按 92 cm 位置的真实杖杆截面重新居中，使握点随左手骨变换。动作层保留云端手臂位置，为活体动作统一左手掌方向；死亡保留云端手腕旋转。道具和身体 PBR 不改变。

这是本地持械适配层，不属于 Meshy 云端自动完成的部分。固定卷握、衣袍避让、脚底接地和整体自然度尚未进行渲染或游戏验收，交给用户实际判断。

## 制作与导入

- `cloud_grip_v02.py`：由原始云端 GLB 制作 `Authoring/CloudGripV02` 与 `Delivery/CloudGripV02`。
- `cloud_grip_v02_manifest.json`：源时长、输出、手部制作数据。
- 工程 `Tools/Witch/import_cloud_grip_v02.py`：只替换巫婆本体、法杖和五段动画；原版本另存 `/Game/Monsters/WitchMeshy/PreviousLocalRetargetV01`，保留原 Skeleton、Physics Asset 和材质引用。
- 工程桥新增 `-PythonScript`，以同一个端口互斥锁执行现有编辑器 Python 客户端；导入全程经过桥，不绕过接入排队。

未启动 PIE、未生成验收截图或渲染，最终导入结果见 `ue_cloud_grip_v02.json`。

接入已完成：本体、法杖、五段动画保存回 F6 正式引用路径，保留原物理资产和材质。挂接逻辑已通过常规 Editor 构建，日志 `Saved/BuildEditor/build-20260920-082246.log`；编辑器重新打开后完成导入。无游戏测试结论。
