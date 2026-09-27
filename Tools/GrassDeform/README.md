# 动态草地工具：暂停，未视觉验收通过

2026-09-27 用户反馈多轮更新仍未成功，已转 [待办](../../Docs/Backlog.md)。本目录保留当前源码与复现手段，不能因文件版本较新而自动执行作者或测试。状态与本机恢复依赖见 [暂停与发布记录](../../Docs/WorldGeneration/grass-paused-publication-20260927.md)。

- `setup_assets_m1.py`、`rest_bounds.py`：v14 原始网格尺寸限幅候选；主材质已保存，实例参数尚未全部落盘。
- `setup_assets_m3.py`、`author_footstep_puff.py`、`repair_footstep_decal.py`：脚步反馈制作链；保留旧热扰动／错误域修正，不代表草体倒伏视觉已通过。
- `author_dense_test_level.py`：密集高草地图制作，使用现有 PN/丘陵草资源。
- `inspect_blade_layout.py`、`read_blade_uvs.py`、`read_response_inputs.py`、`diagnose_footstep_blocks.py`：保留的诊断源，需按用户要求使用；读取结果和第三方数据导出只留本机。
- `run_functional_audit.ps1`、`run_response_audit.ps1`、`make_response_gif.py`：只在用户明确要求测试／录制时运行。v12 的 34 项断言通过没有覆盖最终顶点弯折；旧 GIF 文件名不是当前版本验收证明。
- `archive_paused_20260927.ps1`：本次精确归档记录，只处理脚本列出的历史文件，不可盲目重跑。

需要合法本机 PN_GrassLibrary、丘陵草、AutoFootstep 插件（含 FAutoFootstepPlayed 委托）、相关地图及其依赖。Git 只保存项目编写的脚本和源码，不分发 UE、Fab 模型、纹理、插件、导出网格数据或测试媒体。
