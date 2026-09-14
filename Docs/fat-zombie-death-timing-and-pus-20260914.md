# 胖子完整死亡动画与即时脓液

用户要求：死亡时完整播放原动画，倒地后才启用布娃娃；排查并修复脓液未立即显示。本次不启动游戏、截图或执行玩法测试，照常完成代码与材质制作、必要构建。

## 本次反馈的证据

读取用户已有 `Saved/Logs/FPSGAME.log`：

- `FatZombie_0` 在 04:13:39.314 UTC 扣血到 0，04:13:39.863 开启布娃娃。原 .55 秒计时提前打断了约 2.5667 秒的死亡动画。
- 04:13:41.880 才出现 `FAT_PUS_SPAWN`，生成 960 个地面三角形。原来代码等待死亡动画总时长后生成，并另加 .35 秒淡入。
- 随后记录 `M_FatZombie_Pus` 在 `PCD3D_SM6` 编译失败：`vector swizzle 'a' is out of bounds`。材质把 VertexColor 默认 RGB 输出作为 `float3 V`，却在透明度公式读取 `V.a`，导致引擎使用默认材质。生成事件不等于脓液外观已正常显示。

## 当前行为

- 生命归零时立即在死亡原位置生成一次脓液，不等死亡动画或布娃娃；初始 `Visibility=1`，取消淡入等待。
- 脓液的 6 秒持续期从实际生成时开始，首跳仍为 .5 秒，之后每 .5 秒造成 8 点基础魔法伤害；保留敌对判定、随机液洼/液滴、贴地范围与结束淡出。
- 原死亡动画按原速度完整播放。布娃娃计时取实际片段长度与可配最小等待的较大值，因此旧实例保存的 `.55` 不再提前切断动画。
- 物理交接前显式采样最终动画帧并刷新骨骼，从倒地末姿接入已制作的布娃娃。正常片段完成后不再额外施加致死方向冲量，避免尸体倒下后又被踢动；无死亡片段时才使用原物理冲量兜底。
- 材质透明度改为显式连接 VertexColor 的 `A` 输出到单独 `Coverage` 标量，RGB 继续表达厚度和浑浊变化。保留现有水体纹理、黄绿色调、反光及浮沫。
- `build_pus_material.py` 读取材质编译返回值；此次在原 FatZombieAuthoring 宿主保存材质，再使用引擎 `CookShaders` 对指定材质构建 Windows 着色器，不生成画面预览。只将本次两个脓液材质包交付回主工程。

## 文件

`FatZombie.h/.cpp`、`FatZombieAnimInstance.h/.cpp`、`FatZombiePusPool.cpp`、`Tools/FatZombie/build_pus_material.py`，以及 `/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus` 和 `MI_FatZombie_Pus`。

修改前两个材质包保存在 `Saved/FatZombieDeathTiming/before/`。原模型、四段动画资产、枪械命中配置及布娃娃关节保持本轮修改前的资产。

## 构建记录

- Editor 最终构建成功，退出码 0，日志 `Saved/Logs/FatZombie-death-timing-Editor-final.log`，模块后缀 6141230。
- 首次 Editor 构建被同期开发面板 `DevelopmentTuningPanel.cpp` 的 `Slot` 遮蔽成员错误阻塞；本次只将四处局部变量及其使用改成 `LabelSlot`、`CardSlot`、`CopySlot`、`SwitchSlot`，未修改面板行为。
- 最初尝试在资源宿主关闭异步着色器编译，触发 UE 编译任务队列的 `AllJobs.GetNumPendingJobs() == 0` 断言，进程退出码 3，尚未执行材质脚本；日志 `Saved/Logs/FatZombie-pus-alpha-material-build.log`。随后恢复引擎默认编译调度，改为资源保存加指定材质的着色器构建。
- 材质脚本执行完成，退出码 0，日志 `Saved/Logs/FatZombie-pus-alpha-authoring.log`；两个更新后的材质包已从资源宿主复制回主工程的 `Content/Monsters/FatZombieMeshy/Pus/`。
- 首次独立材质构建完成，退出码 0，但资源宿主默认只构建 `PCD3D_SM5`，日志 `Saved/Logs/FatZombie-pus-alpha-shader-build.log`。资源宿主的 `Config/DefaultEngine.ini` 已改为主工程同用的 DX12/SM6 目标；主工程渲染配置未修改。
- SM6 材质构建完成，退出码 0，日志 `Saved/Logs/FatZombie-pus-alpha-sm6-build.log`。04:45:17 UTC 明确记录 `Working on Windows PCD3D_SM6` 及 `M_FatZombie_Pus` 的 SM6 编译，04:45:18 完成；未再出现透明度通道越界或材质编译错误。
- 首次 Game 构建被同时更新的生命组件与枪匠界面声明不同步阻塞，退出码 6，日志 `Saved/Logs/FatZombie-death-timing-Game-build.log`；当前头文件已包含对应声明，使用最新文件重新构建。
- Game 最终构建成功，退出码 0，日志 `Saved/Logs/FatZombie-death-timing-Game-final.log`，输出 `Binaries/Win64/FPSGAME.exe`。
- 未启动游戏或生成预览。实际观感、完整倒地与布娃娃衔接由用户重开编辑器后测试。
