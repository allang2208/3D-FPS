# 阔锋重刃的剑座与剑身材质

2026-11-07 按用户更正，仅阔锋重刃从剑座向剑尖使用所选材质。护手及宝石保留原外观。

原厂、壁垒、反击、轻量和裂角护手以 V5 母版焊接前的 V 形刃根接缝为界。接缝至现有剑身网格之间的中央承接面随剑身换材质。菱形宝石及镶边单独保留。风誓翼锋护手以中央座的上卷边为界，其上的剑身接头随剑身换材质，双梁、端帽、编结与风星使用各自原材质。

只为阔锋重刃制作护手网格副本及专用材质，沿用原几何、UV、碰撞和 LOD。`highland-claymore-modules.json` 的五个 `guard.mesh_by_blade.highland_broadblade` 条目指向这些副本；其他剑身仍用原护手，拆除阔锋时通过原有网格切换清除覆写。已有棱脊穿甲刃适配条目保持不变。

`ModularSwordVisual::IsBladeFinishCarrier` 按实际装配或改造台草稿识别阔锋护手；持握、改造台、掉落及第三人称材质描述复用相同选件与材质模式。沿用现有材质复制字段，不增加 RPC 或改变伤害、体力等属性。

- `read_inputs.py` / `inputs.json`：当前五款护手的制作输入。
- `install.py`：从当前剑身材质读取已用配方，制作专用护手材质和网格，按字段合入目录。
- `finish-recipes.json`：本次制作读取的通用及高地专属材质配方。
- `saved-assets.json`：实际资产保存回执。
- `seat_finish.py` 与 `install_seat_boundary.py` 用于制作剑座边界和就地更新现有五份专用材质。保存记录见 `saved-seat-boundary.json`。
- `build.ps1` / `build-receipt.json`：必要原生编译及回执。
- `Saved/HighlandBroadbladeGuardFinish20261106/`：后台处理日志。

没有运行游戏、联机测试、截图或渲染验收，实际效果由用户测试。

交付状态：3 份专用材质、5 份护手适配网格已保存，五个阔锋专属装配条目已接入。`FPSGAMEEditor Win64 Development` 最终构建返回 `Succeeded`（增量目标已更新），当前 DLL 时间晚于本次源码修改。首次编译期间副手弯刀头文件发生更新引起生成行号不一致，保留该源码并由后续生成/构建消化；未修改副手模块。
