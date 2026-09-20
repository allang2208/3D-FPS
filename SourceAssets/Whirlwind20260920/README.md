# 大旋风作者源

业务与交付状态见 [迁移记录](../../Docs/Skills/whirlwind-migration-20260920.md)。

当前接入版为 [WindupV4](WindupV4/README.md)：0.5秒连续蓄势、0.1秒实际姿态衔接、反向720°两圈，沿用V3前景材质和已确认的镜头帧同步修复。用户反馈整体效果已接受；最后追加的移动/跳跃限制仍待成功原生构建。

1. Blender 5.1：`blender -b --python WindupV4/author_whirlwind.py`，生成普通柄可编辑Blend与FBX。依赖当前项目 `MeleePommelAttack20260916` 的连续双臂求解器及 `MannyGraspDonor20260912`、`RuneSword20260913/ChargedErgoV43` 作者源。共享求解器有并行修改，本次不一并发布；保留的V4 Blend/FBX是已接入版本的直接恢复来源。
2. 编辑器停止PIE后，经 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript .../WindupV4/import_revision.py -OutputFile <新路径> -MaxOutputChars 3000` 导入普通柄。脚本随后执行同目录 `author_long_grip.py` 制作18mm加长柄版；已有目标时停止，不自动覆盖。
3. `WindupV2/make_focus_material.py` 与 `focus_blur.hlsl` 是当前背景模糊制作源；`WindupV3/make_temporal_materials.py` 制作当前前景时域材质，并输出 `Content/ColdSteelData/whirlwind-temporal-materials.json`。两者仍有效，不属于旧动画废案。
4. 普通Python运行 `make_icon.py` 创建原创技能图标；公共 `Tools/UI/prepare_cold_steel_skill_icons.py` 已登记恢复来源。

旧V1–V3普通柄/加长柄动画、对应作者输出及临时接入文件已移入本机 `trash/whirlwind-retired-20260920`。清单与发布边界见 [整理记录](../../Docs/Skills/whirlwind-publication-20260920.md)。当前资产已经保存，不需重复接入。

公开源码不包含Manny/授权武器二进制、Blend/FBX/uasset或密集逐帧姿态。没有追加游戏测试、预览或截图；用户已有反馈与本次仓库检查分别记录。
