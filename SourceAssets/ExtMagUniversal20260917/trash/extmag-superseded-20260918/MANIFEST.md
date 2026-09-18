# 扩容弹匣废案与孤儿资产清单（2026-09-18）

提交 `2d90f10` 的说明里写过"废案与哈希在 `trash/extmag-superseded-20260918/`"，但该目录当时并未创建。本文件补上它，并说明一个关键事实：**本轮没有删除或移动任何资产**，下表只是登记现状与散列。

## 仍在磁盘上的废案／孤儿

| 路径 | 字节 | 最后写入 | SHA-256 | 状态 |
| --- | --- | --- | --- | --- |
| `Content/Weapons/ExtMagUniversal20260917/SM_ExtMag_Universal.uasset` | 128334 | 2026-09-18 00:37:49 | `5DCE167928F4D4F6B7B0B50EA1FA133F0B634080EC3ABDBE0F07F4FC8EC627DE` | 参数化扫掠版通用弹匣；`Source/` 已无引用 |
| `Content/Weapons/ExtMagUniversal20260917/SM_ExtMag_PMAG40.uasset` | 225095 | 2026-09-18 11:49:27 | `D896018BCB002D34DFF3B71922D8E7DE32613BEB6C0274F8886E2E7902173ADC` | 三枪收口前的 PMAG 过渡件；已被 M440/AKM40 取代 |
| `Content/Weapons/ExtMagUniversal20260917/M_ExtMag_Metal.uasset` | 5823 | 2026-09-17 20:36:04 | `EF826A5BC7B18C9DAB94A84D3436F262A1A7AB282224853525B34093BFF07564` | 共享金属材质；三件已改绑宿主原厂弹匣材质 |
| `Content/Weapons/ExtMagUniversal20260917/M_ExtMag_Polymer.uasset` | 5396 | 2026-09-17 20:36:04 | `F2164A40B83917A24A76EA40D3574CD998B803F9AECABECF4FF16BE43D8EE041` | 共享聚合物材质；同上 |
| `SourceAssets/ExtMagUniversal20260917/ExtMag40_Editable.blend1` | 256840744 | 2026-09-18 11:23:33 | `475145CC15CCFBE203BA8D2411DE797F09F11640BE5DEFDD1F70A00970C5504D` | Blender 备份；对应的 `ExtMag40_Editable.blend` 本体已不在目录中 |
| `SourceAssets/ExtMagUniversal20260917/Scripts/build_extmag.py` | 15156 | 2026-09-17 19:52:18 | `B8A923DF9D14A8A3064934F88E30B44CDD9FAA19F4A446A267DEB703E0209465` | 第一版参数化扫掠建模脚本，被 `export_insocket_pose.py` 取代 |

## 已知的来源缺口

- 第一版通用弹匣的 FBX（`FBX/SM_ExtMag_Universal.fbx`）与第二版"摆正 + 拟合座位"的源场景本体都不在目录里；`ExtMag40_Editable.blend1` 是唯一残留的第二版可编辑场景备份。
- 因此这三轮之间**无法再从源文件重建第一、二版资产**，只能依赖 UE 侧残留的 `.uasset`。若要保留可回溯性，后续轮次应在替换前把旧 FBX/Blend 与散列一起移入本目录，而不是留在原路径被覆盖。
- 三枪当前正式资产（`SM_ExtMag_QBZ40 / M440 / AKM40`）的输入 FBX 仍在 `FBX/`，散列与实测尺寸见同级的 `import_extmag_receipt.json`。

## 已退役（2026-09-18 收尾，本条覆盖上面「没有移动任何资产」的当时状态）

上表前三件网格与两件共享材质中的四件 UE 资产已按 [publication.md](../../../skills/ue5-weapon-workflow/references/publication.md) 的退役流程**移动**（不是删除），移动前后 SHA-256 与上表一致：

| 原路径 | 退役路径 | 字节 | SHA-256（移动前后一致） |
| --- | --- | --- | --- |
| `Content/Weapons/ExtMagUniversal20260917/SM_ExtMag_Universal.uasset` | `…/trash/extmag-superseded-20260918/Content_Weapons_ExtMagUniversal20260917/` | 128334 | `5DCE1679…627DE` |
| `Content/Weapons/ExtMagUniversal20260917/SM_ExtMag_PMAG40.uasset` | 同上 | 225095 | `D896018B…173ADC` |
| `Content/Weapons/ExtMagUniversal20260917/M_ExtMag_Metal.uasset` | 同上 | 5823 | `EF826A5B…07564` |
| `Content/Weapons/ExtMagUniversal20260917/M_ExtMag_Polymer.uasset` | 同上 | 5396 | `F2164A40…8EE041` |

- 逐件原路径、目标路径、字节数与前后散列见同目录 `MOVED.json`；退役前用 `rg` 复核 `Source/`、`Config/` 与 `Content/` 其余资产均无引用。
- 替换物：`SM_ExtMag_{M440,AKM40,QBZ40}` 逐槽绑定 `M_ExtMag_Finish_{M4,AKM,QBZ191}`（逐枪烘焙，见 `finish_install_receipt.json`）。
- 仍在原位保留：`ExtMag40_Editable.blend1`（第二版可编辑场景备份）与 `Scripts/build_extmag.py`（第一版参数化管线），按「只登记不擅自清理」处理。
