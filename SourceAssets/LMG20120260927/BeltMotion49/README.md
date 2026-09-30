# 201 布箱弹链：开火进弹与阻尼

2026-09-30。按用户要求参照现用 PKM 的逐发推进和弹链阻尼制作。仅作用于 201 布料弹箱；原厂弹匣、大弹鼓及已取消的提把不在本次范围内。

## 制作内容

- 从当前整枪导出的布箱旧弹链局部分离六段封闭刚性单元，保留原表面、UV、材质及六个换弹接触骨骼；复用已有第七骨骼制作箱内循环单元。循环不再拉扯跨段蒙皮。
- 每次实际开火将弹链向机匣推进一格，沿用 PKM 的源时间 0.012–0.080 秒推进区间。动作结束后保留推进结果，最后一发有短暂供弹显示窗口；真实弹药扣除和换弹逻辑保持原值。
- 复用 `FPKMSoftChain` 的世界空间惯性、重力、固定步长及衰减计算。201 按自身长度采用毫米级自由范围，两端固定在机匣入口和布箱出口。
- 换弹只为中间自由段增加阻尼，保留现用 ClothReload44 的手部／布箱接触位置、动作和事件时序。空仓旧弹链继续隐藏。
- 新网格版本由材质槽后缀 `Belt49` 识别；无新版网格时运行时层不介入。现有材质资产复用，未重做贴图。

## 文件与落盘状态

- 局部编辑源：`LMG201_BeltMotion49.blend`；导入源：`Exports/SK_LMG201_Belt49.fbx`。
- `author_belt.py` 读取 Drum46 的现用枪体导出与 idle 捕获，写出局部源、`layout.json` 及 `Source/FPSGAME/Weapons/LMG201BeltLayout.h`。不是整枪替换脚本。
- 运行时代码：`Source/FPSGAME/Weapons/LMG201BeltDynamics.{h,cpp}`，经 `UFPSCastingMeshComponent::FinalizeBoneTransform` 应用；角色现用开火时钟和装配状态负责配置。
- `install.py` 只替换现用 `SK_LMG201_Cover10` 的旧布箱弹链两组面，并追加两个专用槽。原完整枪体字节备份写入 `Before`，已保存资产记录以 `delivery.json` 为准。
- 已完成源模型制作、正式 C++ 构建和后台资产导入保存；不是仅准备好导入脚本。

## 交付记录

- 正式构建成功：`Saved/BuildEditor/build-20260930-094907.log`，普通 `UnrealEditor-FPSGAME.dll` 已生成；摘要为 `build-result.json`。
- 后台导入 commandlet 正常结束，回执 `delivery.json` 状态为 `current_belt49_saved`。现用主体和私有弹链分件均已保存，材质绑定清单同步到 `Material21/bindings.json`。
- 现用主体 SHA256：`73e0d6d55393cdb4f753cb70566a2bfde3f02fc2d54bf0d4a4b74599b49a029a`；改动前字节备份 SHA256：`61a361224bc106b5de178502eb7ee6ed61cfd0425504f202ed81025463e41e5e`。
- 未运行游戏、PIE、自动测试或验收渲染；构建和保存成功不代表运行效果已验收。

## 使用边界

按用户规则，不启动编辑器、游戏、PIE、截图或验收渲染，不追加自动测试。运行效果由用户实测。本次没有获得视觉验收结论。

恢复时先停止项目进程，再将 `Before` 中对应 uasset 恢复到原路径，并移除本批三个源码文件及角色／网格组件中的对应接入，重新正式构建。不得整份回退共享的角色或网格组件文件，以免覆盖其他修改。
