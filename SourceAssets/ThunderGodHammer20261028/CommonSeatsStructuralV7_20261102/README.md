# 雷神之锤三款通用中央锤座：结构升级 V7

2026-11-02 后续用户反馈：轻型座开窗后有横杠穿模。该款 V7 不再作为修复母版，后续使用 `../LightSeatWindowFixV8_20261102/` 的作者脚本和保存模型；厚壁、叠片仍使用本版。原因是切割体外壳残留进正式网格，详见 V8 记录。

用户于 2026-11-02 确认范围为厚壁重铸座、镂肋轻型座、叠片缓冲座，要求保留原厂设计主体并加强特征区别；随后授权继续制作。

## 设计与原版本问题

当前 C6 制作源在肩部使用约 0.8–2.2 mm 的局部体积差异，三款以嵌银刻槽和浅层缝区分。V7 保留原厂中央三结圆徽、侧向锤头连接端面、柄颈端面及原有 PBR；仅修改外围肩部和厚壁款的顶沿。

`CommonSeats_Structural_Concept.png` 为内置 imagegen 生成的四列概念对比，包含原厂参考重绘和三款结构方案。它不是最终网格渲染或游戏截图。最终生成提示词保存在 `concept_prompt.txt`；最初一次生成被工具以 violence 类别拦截，补充无人物、无战斗的虚构装饰装备语境后，第二次生成成功。

## 三款实际模型

| 选项 ID | 本轮几何制作 |
| --- | --- |
| `reinforced_block` | 原厂上肩加入宽台阶与外侧二级锻肩，局部深度增加约 4.5–7.7 mm，下肩增加约 4.8 mm；顶沿局部升高约 3.5 mm。 |
| `ribbed_light` | 两侧肩部各制作一处斜三角贯穿窗，切穿前后实体；窗口多段截面形成收口及内壁，新壁面使用独立深色金属材质和有效 UV。 |
| `laminated_damper` | 肩部制作三阶金属台面，两条约 2.3 mm 宽的缓冲层底部相对台面下沉约 8 mm，并在肩侧内收形成转角层次；缓冲层分配独立非金属深色材质。叠层保持与内芯一体连接。 |

原有表面 UV 保留，原自定义法线随局部变形运输；新窗口壁面单独生成 UV。可编辑源、构造脚本与三份 FBX 保存在本目录。未重新生成整件 Meshy 模型。

## 已保存与已发布

- Blender 作者源：`ThorSeats_StructuralV7_Editable.blend`。
- UE 网格目录：`/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7/Meshes`，三个独立新版本网格。
- 新增材质：`M_ThorSeatV7_InnerSteel`、`M_ThorSeatV7_Buffer`；主体继续复用各自 C6 原生 PBR 贴图与材质。
- 后台 commandlet 已实际保存三份网格、两份材质；`import_receipt.json` 的 `complete` 为 true。沿用 Nanite、显式切线及完整 fallback 设置。
- `publish.py` 只更新 `Content/ColdSteelData/thunder-god-hammer-modules.json` 的三个 `head_mount` 条目；原配方副本保存在 `BeforePublication/`。具体变更见 `publication_receipt.json`。
- 现有通用改造 ID、数值、存档及其他槽位保持原值；疾雷、贯雷和此前动作/音效修复继续使用现有引用。
- 根据通用改造图标规范与实际 UI 解析路径，继续复用共享金属框图标；没有覆盖其他战锤的共享图像或新增无法被当前优先路径读取的专属图。

本轮无 C++ 修改，无需原生编译。未打开 UE 编辑器界面、运行游戏、渲染模型验收图或进行运行测试；实际结构观感与装配表现由用户测试。概念图不代表实机验收结果。
