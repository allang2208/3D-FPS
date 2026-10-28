# 尼泊尔弯刀改造件精修与动态挂饰 · 2026-10-27

本轮包括完整改造图标重制、镇岳式挂饰物理接入，以及实体部件和三款符文的材质细化。没有修改伤害、攻速、重量等玩法数值。

## 已制作内容

- 13 套实体 PBR：3 刀身、3 握柄、3 柄尾、3 改造挂饰与原装挂绳，每套 2048×2048 BaseColor / ORM / Normal，共 39 张。
- 刀身保留轮廓、刃口和已有槽形，细化定向磨纹、锻面、百炼层纹；握柄收敛过粗微起伏；柄尾改为连续的金属表面、细磨纹和环槽层次。
- 挂绳的原有折角改为连续曲面，穿孔连接段保持原位；织物、皮穗、扣环、金属牌分别保留材质分区与法线。
- 三款符文在四种刀身的既有父材质中增加浅刻痕法线，保留符号、色调、底层刀身纹理和现有 12 个材质实例。
- 20 张共享母图映射到 26 个实际图标键，涵盖改造、原装、分类与拆除。统一金属方框、四角铆钉、银色内环、深灰底板、中性灰阶和透明外边。符文只显示核心符号。

## 挂饰物理

复用玄螭镇岳的 `USwordTasselMeshComponent`：8 个导向点、固定子步、重力、惯性、阻尼、长度约束、柄尾／握柄胶囊避让。连接孔至下方 1.8 cm 的原有系挂段固定，下面的织带及皮穗参与弯曲。金属牌、金属扣环以刚性权重保形。为短挂饰提供各自的逆质量、阻尼与细粒子半径，镇岳默认设置保持原值。

4 个新网格和 4 个材质位于 `/Game/Weapons/Kukri20261020/Refinement20261027`。UV0 用于 PBR，UV2 用于段索引与插值权重；完整保留 FBX V 翻转处理。挂饰材质同时变形位置与法线。导向点及避让体按导入后的局部坐标系转换，原始制作坐标与运行坐标分别记录在 `surfaces.json`。

第一人称主手、副手／双持和本地／远端角色装备装配沿用同一配方；纯装饰模拟不影响伤害碰撞，也不向服务器逐帧同步粒子。非游戏预览使用静止姿态。切换／拆除配件会清理旧组件，隐藏或大幅瞬移后重置模拟。

## 图标制作

`imagegen` 内置工具成功生成挂饰参考及统一空白标准框。两张刀身请求被服务以 violence 分类拒绝，记录见 `icon-generation.json`。最终全部图标统一采用 `StandardEmptyFrame.png` 作为 Blender 作者场景的框体材质，配合本轮实际模型渲染，避免边框差异或生成模型变形。没有采用旧的简化三维边框。

原装件的拆分作者文件含预览材质，最终图标制作已恢复实际原装 BaseColor / ORM / Normal，再在图标场景转换灰阶。母图 1024×1024 RGBA；实际 UI Texture2D 使用 UI 纹理组、Editor Icon 压缩、sRGB、Never Stream、无 Mip。原始生成请求、输出档案、真实模型输入和最终可编辑图标场景均保留。

## 重建与接入

- `author_refinement.py` → `Kukri_Refinement_Editable.blend`、`Textures/`、`Export/`、`surfaces.json`。
- `render_inputs.py` / `render_final_icons.py` → `Kukri_StandardIcons_Editable.blend`、`Icons/`、`icon-manifest.json`。
- `prepare_staging.py` 建立只含本批依赖的最小作者工程。
- `import_surfaces.py` / `import_icons.py` 保存材质、持久静态网格源数据和纹理，不在 PIE 中导入。
- `publish_when_available.ps1` 通过既有 UE 批次互斥等候游戏工程无编辑器／commandlet 占用，再发布 77 个资产包和 26 张运行 PNG，按字段合并当前目录。替换前文件保留于 `Before/`。

`build-editor.log` 记录本轮 FPSGAMEEditor Development 构建成功。`Receipts/import-surfaces.json` 和 `Receipts/import-icons.json` 是作者工程保存结果；`Receipts/publication.json` 的 `complete: true` 表示已经部署到游戏工程。

未启动 UE 编辑器或游戏，未运行游戏测试或追加验收。物理摆动、材质观感及联机显示由用户在游戏中检查。
