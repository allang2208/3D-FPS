# 手册打开后停在资源加载提示：材质槽修复

用户截图显示“手册资源加载未完成”。实际并非异步请求一直未返回：日志已经进入纸页初始化，随后 `CreateDynamicMaterialInstance` 报告 `Material index 1 is invalid`，初始化返回，`bReady` 未置为 true。

## 根因与修复

V9 骨骼纸页的 `M_BookPages`、`RecipeLeft`、`RecipeRight` 三个材质槽名称存在，但保存的 `MaterialInterface` 全为 null。导入脚本迭代 UE 的结构体数组时只修改了循环变量；没有将修改后的结构体逐项写回数组。

- 将纸边槽绑定 `M_BookLeafEdge`，正反面槽绑定 `M_BookLeafPaper`。
- 在原导入脚本中增加 `materials[i] = slot`，再写回整个材质数组。
- 通过后台 commandlet 在主工程保存原 V9 纸页包，保留模型、31 骨骼控制链、双面 UV 和纸页角色逻辑。没有重导几何或修改 C++。

## 证据与执行范围

`SourceAssets/AlchemyManualLoadRepair20261016/repair-receipt.json` 记录三个槽修复前均为 null，修复后均为指定材质，包保存返回 true。临时纸页组件也能读到三个正确的材质引用及 31 个纸页控制骨骼。

此前正在运行的可交互编辑器退出，桥未发现可连接节点，修复脚本没有通过桥执行。等另一个后台 UE 批次结束后，使用 `save_headless.ps1` 完成实际保存；未启动编辑器、游戏或场景验收。本次无 C++ 修改，无需重新构建 Editor/Game。实际打开、翻页和外观效果由用户再次体验。

当前恢复链、退役文件归档和最终检查状态见 [手册收尾发布](../Publication/AlchemyManual20261016/README.md)。本文所述阶段结果保留为历史记录；本次整理未重新运行测试。
