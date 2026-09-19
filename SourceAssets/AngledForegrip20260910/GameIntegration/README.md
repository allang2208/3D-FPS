# 共振二代前握把：M4 游戏接入

2026-09-11：本目录保留原尺寸四指版制作记录；当前游戏已切换到 `../Compact75` 的 75% 尺寸三指版，详见该目录 README 与 acceptance.json。

游戏入口为 M4 枪匠的“前握把 → 共振二代前握把”。配件属于 `underbarrel`，使用库存实例已有的草稿、应用和存档流程；与棱镜阻手器互斥。未额外改变枪械数值。

最终资源目录是 `/Game/Weapons/M4AngledForegripFinal`。`M4AngledForegrip` 是早期候选目录，最终运行不引用它。静态网格以 M4 bind space 导出，运行挂在 `WPN_root` 并抵消一次 bind transform。材质直接引用当前 M4 的 `Body_001` 与 `Grip_Default_001`；没有改写 M4 原材质。

`M4_AngledForegrip_Integrated_Editable.blend` 包含实际 M4、原手臂／手套、前握把和 9 条动作。每条动作另有独立 Blend 与 FBX。制作过程沿用上一级目录的三视图、5080 原始候选及人工硬表面重建；本次为游戏手模适配微调镂空内沿和底部装饰位置。

左手食指、中指、无名指、小指穿过开口，拇指留在外侧。保留原骨架、蒙皮和骨长，以局部屈伸轴调整手指；肩、肘、前臂扭转骨和手腕一起适配。掌骨不做额外大幅旋转。待机、开镜、两种射击和装备有专用支撑姿态；装备仍由右手完成拉栓。

普通与弹鼓的普通／空仓换弹分别制作退握和回握。先松指、从侧面退出，再回到原取弹动作；回握反向进行。普通源帧 16 至结束前 24 帧、弹鼓源帧 28 至结束前 24 帧保留原左手接触。弹鼓以最新 `M4DrumContact20260910` 为源，保留其直线插入修正。右手、枪根、弹匣等机械轨道及原事件时钟保持。

复现入口：

- `fit_frame.py`：游戏开口与装饰适配。
- `refine_grasp.py`：受局部屈伸范围约束的接触调整，结果 `fit_final.json`。
- `export_static.py`、`build_animation.py`：静态 FBX 与动作／源文件。
- `validate_source.py`：骨长、缩放、手指局部位移、非左侧运动和保留接触段比较。
- `check_geometry.py -- --full`：446 个稳定、装备、退握、回握与取弹／插入采样；检查手指三角面与握把，结果不等同于整个手臂、整枪或连续时间的绝对零交叉证明。
- `import_assets.py`：导入并保存最终独立路径，检查时长、RAW／COMPRESSED 和原动作比较。
- `run_validation.ps1 -Run <唯一标签>`：独立 `ForegripAudit_...` 存档，真实新游戏进程验证。
- `make_delivery.py <同一标签>`：只有源、几何和运行断言通过才生成 `acceptance.json` 与实机视频。

最终 `final-v2` 新进程加载 `UnrealEditor-FPSGAME-2026092055.dll`，320 PASS、0 FAIL；446 个手指／握把接触采样无交叠。完整结果见 `acceptance.json`；实机截图在工程 `Saved/ForegripAudit/final-v2/`，视频为 `M4_foregrip_gameplay.mp4`（静音，仅供动作视觉检查）。原有编辑器实例不会被此流程关闭；新原生模块需要新进程加载。

最终动画制作以随附 `fit_final.json` 的已验证参数为准；重新运行拟合工具后应重做对应接触与运行检查。首次最终测试 `final-v1` 仅在另一种握把的可选动画回退预期上失败；测试现已遵循运行解析顺序，`final-v2` 通过。早期同名候选导入被其他编辑器文件锁阻止，随后成功保存并回读独立 Final 路径；旧候选日志不作为最终保存成功证据。

导入检查沿用引擎已有 SDK，设置仅限子进程的 `UE_SKIP_UBT_SDK_SETUP=1`，避免反复平台发现与共享构建锁争用。此设置不替代原生编译或实际运行验证。原始素材和贴图沿用项目现有许可，不公开发布这些二进制资源。
