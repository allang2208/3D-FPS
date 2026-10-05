# 苍龙共享爪材质可见性恢复

当前 `install_ue.py` 仅处理仍被 V9 使用的共享 `Materials/M_AzureDragonClaw`：景深后显示、关闭场景深度吞没、移除旧 DepthFade。不再读取或重建已归档的 EnergyV3 材质；旧三材质版本在 trash。

本轮整理只改恢复配方，没有重新保存材质。历史 `install-receipt.json` 仍记录 2026-10-05 当时三份材质的实际保存，不能把它当作本次脚本运行结果。当前完整恢复沿根 `run_install.ps1`，必要构建沿 `CoherentV9/run_build.ps1`。V9 仍未达标，待办见项目 `Docs/Backlog.md`。
