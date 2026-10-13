# 木工实景加工改造（2026-10-09）

用户不认可二维小游戏，要求参考项目打铁和枪械组装的实景操作。采用当前 V4 工作台，不重导/修改模型或配方经济。

## 参考与职责

`Building/ForgeInteraction.cpp` 的 Enter/RestorePlayer：工作台局部相机、保存 PreviousView、临时隐藏 WorkingPawn、关闭恢复。`Building/GunAssemblyInteraction.cpp` 的 CursorOnPlane：屏幕射线变换至台面局部坐标后求交；局部工件随工作台四向旋转。`UI/GunAssemblyActionWidget.cpp` 的底部轻 HUD：共享冷钢字体、玻璃及36px操作尺寸。木工继续复用现有控制器的输入锁、UIOnly与返回游标模式，避免重复叠加锁。

## 实施方案

新增临时本地 WoodworkingWorldView Actor，附着真实工作台 Body，使用 V4 WoodworkingSawPivot 挂点。相机俯视真实锯台；动态板材按现有 Wood/Target/Damage 掩码生成有厚度的顶面、底面和切口侧壁。目标线与损伤标记放在板材局部表面，不绘制二维金属桌背景。网格对应掩码像素边界，保留离散精度；不承诺连续曲面或实体物理切削。

每次仅一个后台纯几何任务，复制有界掩码快照；主线程接回 mesh，丢弃其他图案/准备轮次结果。姿态按现有 Pose 每帧同步，几何按 revision 合并更新，限制更新频率；不在输入中同步加载资产，不烹制运行时碰撞。移动输入走屏幕→台面→工作坐标→MoveBoard，Q/E/撤销/计时/评分继续使用原系统。

实景 HUD 中央透明且作为拖动命中区；上方一条标题/计时/清除率/完整度，下方消息、旋转、撤销、急停、主要操作。准备阶段显示图案选择，运行阶段收起；结果保留分数与重新准备。窄窗操作横向滚动，矮窗减少辅助说明，详情默认收起。无工作台开发练习仍明确标为二维调试，保留已修复的闭合路径防护。

关闭/放弃、Destruct、EndPlay、工作台销毁/掉落/记录移除、角色失效恢复原相机与 HiddenActors；异步资产与几何任务无裸 UObject 回调。失焦/窗口失活/鼠标越界/布局变化取消进料；急停不返还时间。每次进入使用新 Actor，退出幂等，不创建保存对象。

## 本轮范围与验证

修改木工Widget和Controller，新增世界显示Actor、纯几何规划函数和两种本地材质。现有WoodworkingSystem、Mask、Saw、配方JSON、V4模型、调色板以及ClosePolyline保持原哈希。备份在本次执行目录 Before。

按授权做离线几何覆盖/边界、坐标往返、生命周期静态检查，以及 Editor/Game 构建。不启动游戏、PIE、截图、真实存档或终止他人进程。相机视野、遮挡、鼠标手感、世界光照及多次进入退出的完整效果留给用户实测。
