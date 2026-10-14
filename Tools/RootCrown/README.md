# 根冠当前制作入口

当前角色为根冠 M-01，蓝图入口保持 `/Game/Monsters/RootCrown/BP_RootCrownRigPreview`。

当前动作/资源使用多个版本，按 [发布与恢复清单](../../Docs/Publication/RootCrownEcology20261014/README.md) 的顺序选择制作与导入阶段；不要批量运行目录内脚本。

- 冠缘铡击使用 `author_slash.py --double-downstroke` 与 `apply_slash_v2.py`。
- 扇叶针射使用 `author_needles.py --upper-fan` 与 `install_upper_fan_arc.py`；弹体和声音仍来自 NeedlesV01。
- 第三招为触发地雷，保留 RootsV01 的种植动作/模型，再接 `install_mines.py`。
- 旧慢速铡击的 `install_slash.py` 已归档到 trash；基础 `install_needles.py` 会暂时设置旧针射动作，重建时须继续上扇叶阶段。
- `check_*`、`audit_*`、诊断读取和作者脚本中的预览步骤，仅在用户明确要求其对应检查/预览时执行；制作与实际资产保存照常按授权范围完成。

模型、贴图、音频、UE 包和密集作者数据留本机，公开源码不包含完整授权内容依赖。
