> 当前版本（2026-11-04）：厚背重劈、百炼弧锋已改为连续厚度与凸弧磨刃的 R5 网格；三款图标均使用标准母版和实际部件输入，经 imagegen 重制。已后台导入保存 13 个资产，并更新改造件与共享图标引用。制作、导入、登记入口现指向 [ContinuousBladesR5_20261104/README.md](ContinuousBladesR5_20261104/README.md)。未运行游戏测试，外观由用户验收。

以下均为历史记录；旧制作顺序和旧版本状态不代表当前入口。

> 2026-11-04 材质统一历史：厚背重劈与百炼弧锋接续 [原厂同源材质](OtherBladesFactoryFinish20261104/README.md)，当时未重建两款外形。

> 2026-11-04 材质接续：钩月 R4 已采用 [原厂同源主体与磨刃 PBR](CrescentReferenceR4_20261104/FactoryFinish20261104/README.md)，已保存游戏纹理和共享改造图标。当前作者、导入与登记入口均指向该材质版本。

> 2026-11-04 当前状态：按用户认可的参考稿 Draft02 建模钩月 R4，并已后台导入保存、登记游戏引用。入口见 [CrescentReferenceR4_20261104/README.md](CrescentReferenceR4_20261104/README.md)。R3 与 R2 均已被否决，不作为当前制作版本；厚背重劈与百炼弧锋仍未重新制作。

> 2026-11-03 更新：用户否决三款 R2。当前只重建钩月，正式作者入口为 [CrescentR3/README.md](CrescentR3/README.md)。其余两款保持未认可状态；R2 直接制作／部署入口已停止，接口辅助函数仍供新月牙模型复用。

> 2026-11-03：以下 V1 形变方案因三款斧刃扭曲被用户否决，保留为历史记录。当前制作和交付以 [RebuildV2/README.md](RebuildV2/README.md) 为准；旧作者／导入／登记入口已切换至 R2，旧源码保留在 RebuildV2/Before/LegacyScripts。

# 三款通用斧刃模型制作与接入

用户于 2026-11-02 在基础数值和三款设计完成后要求继续模型接入。

- `axe_swift_crescent`：轻型钩月斧刃；窄弧轮廓、较薄侧面、两道几何浅槽。
- `axe_heavy_cleaver`：厚背重劈斧刃；加宽腹部、厚脊和加强楔面。
- `axe_folded_arc`：百炼弧锋斧刃；中等厚度、柔和弧锋和细密百炼钢纹。

采用原装 `SM_TacticalHatchet_Head_Factory` 的几何、UV 和作者法线制作；完整保留 Z≤18 cm 的斧颈，实际握柄分界面仍为 Z=11.5 cm。三款都保持原局部坐标、原点和根缩放；主手／副手与双持继续使用既有 Kukri 动作族。攻击采样点通过相同形变映射到各自刃口，有效攻击距离继续使用物品数值。

`author_blades.py` 复用 Kukri 的几何派生、逆转置法线、UV 和 PBR 烘焙助手，输出可编辑 Blend、三个 FBX、三套 2K BaseColor／Normal／ORM。斧颈采样原装表面，新斧面使用程序碳钢／百炼材质并烘焙；法线为 OpenGL 切线空间，UE 导入翻转绿色通道。ORM 的 R 为 1（不虚构原装 AO），G 为粗糙度，B 为金属度。

`import_blades.py` 复用原装模块的导入与 Substrate 材质制作函数。新网格在既有 `ModulesV1` 命名空间内，使用已编译的 `TacticalHatchetImportLibrary` 保留作者法线并生成切线、启用 Nanite。原装件与六款握柄／柄尾资产无需重导。

图标按实际模型生成三张独立灰阶部件输入，采用共享金属方框母版。正式共享键为 `blade_1_<选项ID>.png`，沿用已有近战图标解析；不为每把斧复制一套图标。图标场景的灰阶转换独立于游戏材质。

`register_blades.py` 在资产保存后追加模块配方和共享选项：`Content/ColdSteelData/shared-axe-blade-options.json` → `tactical-hatchet-gunsmith.json` 的 `blade_1`；几何配方追加至 `tactical-hatchet-modules.json`。物品改造仍由 `gunsmith_parts` 保存。原装模块登记脚本已改为保留后续斧刃与共享库引用，避免重跑时删除新选项。

制作顺序：`author_blades.py` → `render_icon_inputs.py`／`import_blades.py` → 图标生成、`deploy_icons.py` → `import_icons.py` → `register_blades.py`。图标生成提示与来源单独保留。导入通过无界面 commandlet；如编辑器已经运行则使用既有互斥桥。

本轮不改运行时 C++，无须重新编译。正式落盘状态以 `delivery.json`、导入和登记回执为准；未启动游戏测试或验收渲染。
