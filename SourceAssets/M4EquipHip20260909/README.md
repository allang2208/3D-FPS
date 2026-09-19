# M4 装备与切枪腰射位置修复 — 2026-09-09

问题来自 `UpdateViewmodel()` 把所有 busy 状态都平滑移到 `M4ActionViewmodelLocation`，包括 Equipping。装备结束后又平滑移回腰射位置，形成先居中、再回右下方的两段移动。

本次让 Equipping 使用当前枪械 `HipViewmodelLocation`，换弹和检视继续保留原动作空间。`StartEquipCharge()` 同时清除上把枪残留的动作构图、ADS 进度和奔跑姿态权重，并在首帧设置当前腰射位置与朝向；因此从瞄准、换弹中切枪或快速连续切枪均不继承原来的中心位置。

沿用原 `M4InfimaRigV4/A_AKM_equip` 装备片段，63 帧、60 Hz、1.033333 秒，保留播放时长、接触动作、声音与结束后的输入恢复规则。本次没有重新制作骨骼动画。已检查原模型实际渲染 `source_equip_*.png`；可重现脚本 `inspect_equip.py` 只读现有 Blender 源。普通/空仓换弹、HK416 音效、折叠瞄具和弹鼓由原路径继续工作。

## 实现边界

- `FPSGAMECharacter.cpp`：动作展示位置排除 Equipping；装备入口清理旧展示偏移。仍为本地第一人称表现，不增加公共 Blueprint API 或网络状态。
- `FPSGAMECharacter.h`、`FPSGAMEGunplayAudit.cpp`、`FPSGAMEEquipAudit.cpp`：独立命令行验证入口 `-GunplayAudit -EquipFramingAudit`。通过真实 PlayerController 的 G/R/右键路径测试；两把枪和弹药只写入独立测试存档。
- 回退快照：`trash/M4EquipHip-before-20260909`。共享角色文件还有并行修改，只逆向本次相关行，不整文件覆盖。

## 验证

- `build-final.log`：重新扫描依赖并成功编译角色、角色 Profile、动画关联模块和审计；用户编辑器未关闭。
- `Saved/GunplayUpgrade/m4-equip-hip-final60`：16 项全部通过，独立进程正常退出。覆盖首次装备、背包装备、瞄准中切枪、换弹中切枪、装备中再次切枪、回到待机、弹药不变化。
- 逐帧 CSV 回读的 261 个装备样本：动作居中权重 0、ADS 权重 0、相对腰射基准的水平位移 0 cm。保留原有自然上下起伏。
- `Saved/GunplayUpgrade/m4-equip-regression60`：原枪械回归 49 项全部通过，0 失败、正常退出。包含开火、两种换弹、机械音时序、枪机行程、ADS 输入恢复及 1,792 次刚性组件稳定性采样。
- `Preview/装备与切枪_实机.mp4`：7.2 秒实际游戏截图序列；`Preview/腰射位置装备.gif` 展示首次装备到待机；`Preview/装备位置前后对比.png` 展示旧装备位置、新装备位置和完成后的待机。10 Hz 截帧不表示实测游戏 FPS。
- 早期 `m4-equip-hip-60` 仅作为排错记录：最终审计改用原有独占测量存储、显式初始化，并重新编译共享角色布局。上述样本数以最终 CSV 与日志一致的 261 次为准。

现有编辑器需要重新启动或加载新模块后使用本次代码，无需重新导入动画资产。
