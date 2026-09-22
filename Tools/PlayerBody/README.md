# 玩家全身制作与恢复工具

- `prepare_manny_assets.py`：普通 Python，从本机 UE 5.8 模板补充缺失动画；只复制动画，不提供 Manny Mesh/Skeleton 的完整迁移。
- `import_manny_assets.py`：编辑器注册动画并记录时长等来源元数据。
- `install_body_skin.py`：生成独立皮肤材质和 `SKM_Manny_PlayerSkin`，更新配置；保留原 Manny 和第一人称手臂。
- `body_build_state.py`：只读项目路径、PID、PIE 与未保存包，不保存或关闭编辑器。
- `inspect_body_sources.py`、`inspect_body_runtime.py`、`probe_body_crouch.py`、`enable_body_diagnostic_view.py`：按用户明确授权的诊断范围调用；其中运行时探针/视角切换不是离线素材恢复步骤。

编辑器脚本使用 `Tools/AssetPipeline/mcp_call_codex.ps1` 的 `execute_python` 接口与批次互斥，不绕过现有桥。原生构建使用 `Tools/Build/Build-Editor.ps1`，共享编辑器及未保存内容的处理遵循项目规则。

依赖、归档清单和发布范围见 [玩家模型发布说明](../../Docs/Characters/player-body-publication-20260922.md)。
