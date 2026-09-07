# 分区聚合物标准与支持模块发布

## 已完成

用户确定的最终方向已写入 `skills/godot-weapon-workflow/references/polymer-style.md`，并接入枪械 SKILL 和主流程。本机 `C:/Users/allan/.codex/skills/godot-3d-dev/` 的入口与对应分卷同步。新枪及新改造件默认执行连续枪体、稀疏精细小砖、干净分区聚合物、逐件装配与动作/镜片验收。

本地 AKM 最终源、连续机匣、15 个小砖点缀和分区聚合物保留；移除已淘汰体素运行入口，最终点缀生成器不再依赖废弃生成器。1,686 个废案及派生文件（383.2 MiB）移入 `trash/weapon-style-20260907/`，原位置、归档位置与大小逐项登记。Git 只记录清单与说明，归档实体留在本机。

## 发布范围

从 `origin/main` 的 `6063b98` 建立独立发布工作区，避免推送本地 master 的混合历史。本次发布文档、现行 SKILL 分卷、自写的 `rifle_polymer_finish.gd`、两份聚合物 shader，以及无需外部模型的验证脚本。没有上传第三方枪模、手模、动画或音频。

这些模块提供可复用实现和当前四枪的适配案例，不会自动将远端旧游戏切换成当前本地整枪版本。远端缺少完整视模、改造资产和共享运行链，沿用 `docs/grip-material-publication-20260907.md` 与 `docs/firearm-publication-20260906.md` 的发布边界。本地四枪已接入的结果见 `docs/rifle-layered-polymer-review.md`，不能视为远端完整游戏验收。

## 本次验证

- 两个技能入口通过 skill-creator 的 quick_validate；新分卷与主流程链接检查通过。
- 废案运行引用搜索无匹配；归档清单逐项检查文件存在与大小；保留最终可编辑源。
- 本地 `test_akm_brick.gd`：点缀组、配件装卸恢复与换弹弹匣跟随通过，移动量约 0.5065 米。
- 本地 `test_rifle_polymer_parts.gd`：75 个逐件装卸组合通过；退出报告 13 个 ObjectDB 实例及 1 个资源未释放，未将此结果写为无错误的全项目通过。
- `test_published_polymer.gd` 在独立最小 Godot 项目测试：程序化 ArrayMesh 的位置/法线/UV/索引保持不变，源蓝通道映射正确，重复应用复用网格与材质，配件外壳转聚合物，镜片材质保留。Forward+ / Vulkan 实际渲染两份 shader，最终日志无脚本或着色器错误。
- 独立渲染只证明支持模块与 shader 可用，不能替代真实枪械装配视觉验收；历史整枪专项和广域失败见四枪检查记录。

复现支持模块检查：新建最小 Godot 项目，将 `scripts/rifle_polymer_finish.gd`、`assets/materials/{rifle_layered_polymer,akm_clean_polymer}.gdshader`、`tests/test_published_polymer.gd` 按相同路径复制，使用 Godot 4.7.1 运行 `--path <最小项目> --script res://tests/test_published_polymer.gd --max-fps 60 --quit-after 300`，检查输出和错误日志；截图写入该项目 user://polymer-support.png。此测试依赖真实渲染器，不使用 headless。
