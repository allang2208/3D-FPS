# 长杖 V10：摄像机与抓握方向修正

参考：`../PhotoGripV9/user-bottle-reference.jpg` 中前景的真实右手。
用户拒绝的 V9 画面：`C:/Users/allan/AppData/Local/Temp/codex-clipboard-7af8d8bd-8c10-4a4c-94ff-bd41b81f0b81.png`。

## 原因

V9 把指向和杖轴组成手部方向，没有规定原生手背轴必须朝向眼睛。
原生 M4 的手背轴来自 `BareUpperArmsV6/M4_bare_shape.json` 的 `anatomy.r.dorsal`。
把它送入 V9 待机变换后，手背与「手腕指向摄像机」的点积为 -0.927，朝向相反。
UE 相机局部 +X 是看向场景，不是物体朝向镜头；+Y 为屏幕右，+Z 为上。
原生 UE JSON 本身未经过 Blender 反射，不应在此额外镜像右手。

## 制作与接入

- 用「镜头到握点」及原生手背轴建立 V10 整手朝向，手背为近镜头的三分之四侧面。
- 手腕移到杖身近侧；按透视投影组织拇指向左横扣和斜向排列的四指根部。
- 以 V6 成组抓握为起点，固定整手方向后拟合原生 V7 手部皮肤与握柄外形。
- 肩肘按原骨长重新制作，前臂从画面下方偏右进入。保留原骨长、局部平移、比例和蒙皮。
- 运行时只使用一个握点相对变换，V10 命名空间和缓存版本一并更新。
- 移动、奔跑和右杖蓄力／释放仍共用原本的动作时钟与接触变换。

源文件：`author_camera_grip.py`、`camera-pose.json`。
运行时：`StaffGripContact.h`、`StaffIdlePose.h`、`StaffGripPose.cpp`、`StaffArmsMeshComponent.cpp`、`StaffWeaponComponent.cpp`。
本轮修改前的这五个文件保存在 `Before/`。

`camera-pose.json` 中的 objective 仅为制作算法的约束结果，不代表视觉或运行验收。
未主动启动 UE、游戏、截图、渲染或测试；由用户进行视觉测试。

## 构建状态

源码和生成姿态数据已落盘。首次 Live Coding 返回 `CompileNotStarted`；
LiveCodingConsole 日志明确为 `Live Coding Action Limit Reached`（100 项限制），不是源码编译通过。
用户确认关闭 UE 后，已执行 `Tools/Build/Build-Editor.ps1` 常规后台编译。
2026-09-27 17:32 开始，276 项构建完成，`Result: Succeeded`，耗时 126.67 秒。
`StaffArmsMeshComponent.cpp`、`StaffGripPose.cpp`、`StaffWeaponComponent.cpp` 已编译，
正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已链接落盘。
日志：`Saved/BuildEditor/build-20260927-173205.log`。
未修改全局 Live Coding 限制，未启动或重启 UE，未进行运行或视觉测试。
