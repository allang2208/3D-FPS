# 共振二代前握把：75% 尺寸与三指抓握

2026-09-11：模型和三指握持仍沿用本版；当前肩肘与腕部动画已进一步优化并切换到 `../WristNatural`，以该目录的运行记录为准。

2026-09-11 根据用户反馈将原 GameIntegration 版的模型三轴统一缩为 75%，保持原顶部安装接触点。手臂、手套、骨架与手指尺寸未缩放。沿用原模型、三视图及 5080 管线来源，不重新生成不同造型。

现行游戏资源为 `/Game/Weapons/M4AngledForegripCompact75`，由 `Weapons/M4AngledForegrip.cpp` 加载。配件 ID 仍为 `angled_foregrip`，原存档无需重新购买或转换。材质仍直接引用当前 M4 的 Body 和 Grip 材质。

食指、中指、无名指穿过开口，拇指与小拇指留在外侧。小拇指以正常屈曲收在下方外缘；掌骨保持原方向，手指不平移、不缩放。松手时三指先伸展，侧向退出过程对根关节补充约 3–4 度局部 Z 屈伸修正，回握反向进行。普通/空仓、普通弹匣/弹鼓分别烘焙，保留原取弹、插匣与机械时序。

## 产物与复现

- `M4_AngledForegrip_Integrated_Editable.blend`：模型、手臂和九条动画的可编辑汇总；各动画另有 Blend/FBX。
- `fit_compact.py`、`optimize_contact.py`：固定安装点缩放模型并进行受限姿态拟合，输出 `fit_final.json`。
- `solve_release.py`：仅对退握阶段三指屈伸求解，参数保存在 `release_profile.json`。最终动画以随附参数为准；重新拟合后需重新验证。
- `build_animation.py`、`export_static.py`、`import_assets.py`：烘焙、导出与独立资源目录导入。
- `validate_source.py`、`check_geometry.py -- --full`：骨长、缩放、手指位移、非左侧运动、原接触段和 814 个表面接触采样。
- `run_validation.ps1 -Run <唯一标签>` 与 `make_delivery.py <同一标签>`：独立测试存档的实机验证和视频生成。

## 已验证结果

`compact75-v1` 实际加载 `UnrealEditor-FPSGAME-2026093111.dll`：233 PASS、0 FAIL，包括新版模型/动画引用、三轴尺寸 75%、安装、保存恢复、开镜、射击、四种换弹、装备和替换/拆除。密集检查 814 个姿态无手指/握把三角交叉；这不是整枪整臂连续时间的绝对无碰撞证明。九条源动作的骨长、缩放及保留接触段检查通过；UE 压缩误差检查通过。

尺寸 FBX 包围盒从约 3.902 × 20.582 × 16.310 cm 改为 2.927 × 15.436 × 12.233 cm，三轴比值均约 0.750000；详见 `size_validation.json`。源与运行证据汇总为 `acceptance.json`。

实际游戏近景：`D:/FPS3D/FPSGAME/Saved/ForegripAudit/compact75-v1/grasp_closeup.png`。视频 `M4_foregrip_gameplay.mp4` 来自同次游戏的 97 张动作截图，静音，供视觉检查。已查看近景、腰射和弹鼓换弹后的握持画面。未修改声音和既有玩家存档。

UE 导入日志仍含已有 GameFeatureData 配置报错，但模型和九条动画保存、压缩检查均完成，并由新游戏进程实际加载验证。旧编辑器需重启才能加载新原生模块。
