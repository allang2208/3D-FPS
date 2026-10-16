# ASH-12 瞄具接合检查与优化（2026-10-15）

按用户要求，沿用 M16 一轮的实际接触面、夹座、机瞄避让和光学插座同步标准，检查 ASH-12 的六款瞄具。ASH 已有上导轨，本轮保留该结构。

## 检查结论

| 瞄具 | 实际装配情况 | 处理 |
| --- | --- | --- |
| 普通全息 | ASH 专用接触底座，底面与约 -2.958 mm 的轨冠面相接，无前准星几何相交 | 保留 |
| 全景红点 | 同上 | 保留 |
| 2 倍棱镜 | 同上，支承段位于可用导轨内 | 保留 |
| LPVO | 同上，长镜筒从机瞄上方通过，无前准星几何相交 | 保留 |
| EOTH | 仍加载通用裸镜座，没有 ASH 的接触底座；与原厂前准星有 57 对相交三角形 | 制作 ASH 私有装配，镜身后移 34 mm，瞄准插座同步 |
| 热成像 | 通用裸镜座底脚约高出轨冠面 2.95 mm | 制作 ASH 私有薄型接触底座 |

以上是现用源网格在实际运行安装坐标中的几何检查，不是游戏画面验收。`contact_review.json` 记录原 EOTH 与前准星相交，以及后移 34 mm 后该项为零。其余四款没有为了统一外观而重新制作。

## 制作与接入

EOTH 的上方支承板随镜身向后延伸，下方承重点位于 ASH 原导轨上的约 63–125 mm 段，避开前准星并保留实际承托。原镜身、镜片、分划、材质、UV、顶点色和角点法线保留，只作刚体后移；原四个光学插座同移，ADS 继续从 `SightRear` 取点。

热成像增加约 3 mm 的薄接触底座、下夹肩和紧固件，底座有原横向卡榫的凹槽。镜身与显示面保持原位，`ZoomPivot`、瞄准插座和共享旋钮模型不变。

两款新增安装件复用现有 ASH 接触底座的材质，新增几何具有有效物理尺度 UV；没有修改共享 EOTH、共享热成像模型、其它枪型或武器数值。

新增运行资产：

- `/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_eoth_holographic`
- `/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_thermal_scope`

`CommonHK416Parts.h` 和 `ThermalScopeAssets.h` 只为 `ue_ash12` 返回上述私有路径；沿用现有枪匠预览、持枪、图标和掉落装配的资源解析入口，热成像旋钮仍使用 Common 版本。

## 制作证据与边界

源目录 `SourceAssets/ASH12OpticSeat20261015/` 包含实际资产导出、宿主导轨坐标、测量、检查记录、可编辑 Blend、FBX、接入脚本及源码修改前备份。制作入口是 `capture.py` → `measure.py` / `contact_review.py` → `author.py` → `install.py`。

`build_editor_console.log` 记录 `FPSGAMEEditor Win64 Development` 构建成功。模型导入禁用旧运行时 FastBuild，保留作者法线，使用高精度切线及 UV，并在启用 RHI 的环境中完成网格与距离场构建，避免旧 ASH 无效边界问题。保存回执见同目录 `install_receipt.json`。

最终通过已有编辑器的互斥桥保存两份资产：`install_bridge_06.json` 返回 `success=True`、`ASH_TWO_OPTICS_INSTALLED`；`install_receipt.json` 的两项 `full_build_complete=true`，总状态 `complete=true`，包括最终光学插座与渲染边界。为完成保存结束了已有 PIE，没有关闭编辑器或在交付后启动游戏。

未主动启动编辑器或游戏，未进行截图、渲染或游戏运行验收。实际 ADS 观感与操作由用户确认；Editor 构建不代表打包版本已经更新。
