# 强化台武器拖动图标

2026-11-09。用户要求强化台拖动武器时显示与背包相同的图标卡片。

- 范围：仅替换台上暂存装备的拖动展示，不改变强化、附魔、存档或库存事务。
- 视觉和布局：复用 UColdSteelDragVisual 指针覆盖层、UColdSteelWeaponIcons 当前装配图、目录图回退及 ColdSteelStaffIcon 细长物品等比尺寸；按背包响应格宽和物品占格显示，保留当前朝向，图标中心跟随鼠标。原文字牌只在图标尚未就绪时显示。
- 数据：读取强化台托管快照，在现有 Refresh 时请求图标；异步完成只刷新活动拖影，不重建操作列表。图片等待沿用现有队列和限时泵。
- 输入和清理：拖动不转移物品。只有背包接收后进入原 PreviewReturn / CanRetrieve / RetrieveItem 路径。背包满、拖到其他位置、取消和过期快照仍保留原事务合同。松手、取消、失焦和面板销毁移除图标覆盖层与激活回调。
- 文件：ColdSteelEnhancementWidget.h/.cpp、ColdSteelEnhancementWorldUI.cpp。没有新图片、资产或存档字段。
- 构建：需要 FPSGAMEEditor 原生构建；基础 DLL 生效需占用编辑器退出。未启动游戏、测试、截图或验收，交由用户测试。
## 本次构建结果

- UHT 与 C++ 编译通过：FPSGAMEEditor Win64 Development，使用 -NoLink，日志 Saved/BuildEditor/enhancement-drag-icon-20261109-nolink-final.log，Result: Succeeded。
- 随后共享工作区的常规 Editor 构建完成基础 DLL 链接：Saved/BuildEditor/build-20261109-225738.log 中 Link UnrealEditor-FPSGAME.dll 与 Result: Succeeded；链接响应文件包含本次两个 UI 实现对象，均早于新 DLL。DLL 于本机时间 2026-11-09 22:57:52 更新，44,498,944 字节，SHA-256 872D0D673823BE2F7A27505AEABDF55E6B583E858D82AC24C66427233FABE5A8。

- 本任务后续常规构建 Saved/BuildEditor/enhancement-drag-icon-20261109-full.log 报告 Target is up to date / Result: Succeeded。未重复抢占其他制作 commandlet，也没有启动游戏、编辑器或运行测试。下次启动编辑器使用更新后的基础 DLL。
