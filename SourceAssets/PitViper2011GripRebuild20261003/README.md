# 2011 防滑纹重制与显示修复

**当前入口（整理于 2026-10-03）：** `author_grips.py` 和 `import_rebuilt.py` 仅转发 `../PitViper2011ViperLongitudinalGrip20261003` 与 `../PitViper2011CommonLongitudinalGrips20261003`。图标入口使用当前 VIP 源。下文保留此前短覆片的制作经过；其 Exports、Icons、Textures、Before 和已完成诊断现已移入 trash，不能作为当前生产输入。

用户反馈：蝮蛇 VIP 防滑纹太卡通，需按既有参考图重制；其余三款通用防滑纹在 2011 握把上没有体现。

## 定向排查结果

`source_diagnosis.json` 记录原始作者场景中握把薄片的朝向。通用薄片共 672 个面，全部朝向握把内侧；`asset_diagnosis.json` 记录运行目录实际绑定的三种通用材质均为单面材质。外侧背面剔除是此次三款共同缺失的直接原因。VIP 薄片朝向正确，但原作者图案由两组规则交叉线生成，并配线条徽记，与参考图的大小变化、错列斜向鳞片及紧凑实心徽记不同。

排查只读取相关作者模型和已绑定资产，不启动游戏，不作视觉验收。

## 完成内容

- 共用握把表面重建为左右封闭掌侧薄层，明确外表面绕序，扩大原来仅 10 mm 宽的覆盖条带，保留原生下部卡口、前握持面及后保险。
- 保持原生骨架网格空间和 `WPN_root` 参考骨链抵消，不修改枪体、手模或动作。
- 通用薄层保留三套共享材质、10 cm 物理 UV 比例、改造 ID、数值与现有图标。
- VIP 表面按 `Reference/viper-vip-grip-concept.png` 重做：错列鳞片、圆肩尖尾、向侧边逐渐变细的鳞片、斜向加工刻纹、浅起伏与低对比石墨黑基色。
- 金属细边改为窄的暗香槟色镶线，徽记改为紧凑的实心几何蝮蛇徽记；金属继续使用 WS 母版派生实例，表面仍保持非金属材质身份。
- 更新四张 VIP 表面图，导入两套网格、纹理与金属实例，保留既有雨湿材质映射。`import_receipt.json` 记录实际保存结果。
- 通用旧作者入口改用 `Tools/Weapons/pit_viper_grip_fitting.py`，VIP 旧作者入口转到本批 `author_grips.py`，防止后续重导恢复原来的问题。

原始记录与本批覆盖资产的磁盘备份保存在 `Before`。本批只改相关作者脚本和资源，没有 C++ 改动，无需原生模块构建。单持、双持副手、法杖副手、改造预览及物品图标仍沿用原有防滑纹装配合同。

## 制作与接入入口

- `author_grips.py`：后台 Blender 制作两套网格与 VIP 表面贴图，写回原有作者入口引用。
- `Exports/SM_PitViper2011_VipViperGrip_Editable.blend`：当前 VIP 可编辑模型。
- `Exports/SM_PitViper2011_GripSurface_Editable.blend`：通用薄层可编辑模型。
- `import_rebuilt.py`：通过项目现有互斥桥或无界面 commandlet 实际导入保存，沿用原有 UE 资产路径。
- `author_icon.py`：从当前模型制作蝮蛇专属改造图标素材，属于 UI 资源制作，不是验收渲染；通用图标不重制。
- `import_icon.py`：将专属灰阶金属框 PNG 部署到实际 `FramedFirearms` 路径，并导入保存原有 Texture2D；结果由 `icon_delivery.json` 记录。

鳞片、刻纹与徽记为原创本地制作。贴合源沿用 D_U 的 [Low Poly TTI JW4 Pit Viper 2011](https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153)，原接入记录为 CC BY 4.0；继续保留原模型署名与修改说明。参考图为此前本任务的生成概念图。

已完成制作及实际资产保存；未运行游戏或做视觉、接触与存档测试，最终效果由用户确认。

2026-10-03 后续 VIP 调整源为 `../PitViper2011ViperLongitudinalGrip20261003`。`authoring.json.vip` 及 `author_icon.py` 指向其长形握把侧面；此目录旧 VIP Exports 留作历史源。`author_grips.py` 保留通用三款生产，再调用新的 VIP 制作源，避免恢复旧短覆片。新下沿沿握把本体斜向分界裁切，弹匣、底板与底部扩口不参与覆盖；该 VIP 批次未重制通用防滑纹。

2026-10-03 随后按用户要求，三款通用防滑纹也已同步为相同握把侧面范围，当前源在 `../PitViper2011CommonLongitudinalGrips20261003`。`authoring.json.common` 指向新源，旧 common Exports 留作历史；完整作者入口最后调用该源。沿实际裁切后顶点写入物理平铺 UV，不拉伸纹理，属性和通用图标保持；已后台导入保存原共用网格路径，未运行游戏或测试。


2026-10-03 整理发布：旧短覆片产物及历史诊断已归档；作者和整体导入入口仅转发当前 VIP/通用长覆片。归档清单与恢复范围见 `Docs/Weapons/pit-viper2011-publication-20261003.md`，所有移动文件均可从 trash 恢复。
