# 隼喙凿锋斧刃

战术手斧专属特殊改造，`ue_tactical_hatchet / blade_1 / hatchet_falcon_edge`。用户要求参考先前提供的两张现代战斧照片制作；原图留在 `References/`，仅作本项目设计参考，不据此推定公开分发授权。

## 外形与材料

保留斧颈原装安装面及下探钩刃，将原装方形斧背收成短而下倾的隼喙。上部斧面开圆角三角贯穿孔，孔缘加工小倒角。新斧面为哑光深灰碳钢，切削刃与背喙露出银色磨削面，开孔内壁使用加工钢面。采用图中材质、负形和背喙语言，重新组合轮廓及比例，不复制原图品牌、铭文或整件设计。

本轮参考与宿主几何足以确定局部形态，采用 Blender 精确改造现有网格。实际安装截面为 Z=11.5 cm，Z≤18 cm 的原装网格保持位置，源 UV 和法线按形变继承；上部开孔使用真实布尔几何。几何、2K BaseColor/Normal/ORM、FBX 与可编辑 Blend 由 `author_falcon.py` 生成。法线为 OpenGL，UE 导入翻转绿色通道；ORM 的 R 为 1，G/B 为粗糙度/金属度。

## 属性

名称、外观与数值真源为 `design.json`：物理伤害+20%、暴击伤害+35%、攻击速度-10%、攻击体力消耗+15%。不加暴击率、距离、削韧倍率或穿透。暴击伤害沿既有近战暴击加成加算，物伤与耗体沿现有改造乘区计算，武技动作时钟不受普攻攻速改造影响。

定位为暴击爆发；通用轻型负责速度、厚背负责单次伤害与削韧、百炼负责较温和的综合增益。破阵握柄保留穿透与削韧，长柄保留距离与物伤。新斧刃不引入独立攻击动作或触发技能。

复用 `WarhammerGunsmith` 目录解析、`GunsmithSystem::Calculate`、实际攻击武器 `ColdSteelSkills::Snapshot` 及既有伤害结算。近战暴击伤害字段为 `melee_critical_damage_bonus`，不把数值借给另一把手枪或法杖。组合技继续沿既有主副手合同，不添加新的共享叠加规则。

## 制作与接入

1. `author_falcon.py` 生成源网格、PBR、FBX 及 `falcon_edge.json`；攻击采样点通过相同形变映射到新的主刃口。
2. `render_icon_input.py` 只为改造图标生成实际模型灰阶素材；沿共享 imagegen 金属框标准制作正式图标，提示词和来源保存于本目录。
3. `run_build.ps1` 后台编译特殊改造分类，不抢占正在执行的其他构建。
4. `run_import.ps1` 用 UE 批次互斥和无界面 commandlet 保存新命名网格、材质、三张贴图与 UI 图标。
5. `register_falcon.py` 仅追加战斧专属选项和模块配方，保留原有共享库、握柄、柄尾及挂坠。安装 ID 由现有 `gunsmith_parts` 存档，无需新存档字段。

网格沿用导入助手允许的 `ModulesV1/SM_TacticalHatchet_Head_FalconEdge` 独立资产名；材质和贴图放在独立 `FalconEdge20261103/` 目录。首次导入已保存 PBR 后因网格目录限制停止，继续导入时复用已保存材质，从网格步骤恢复。原始错误记录保留在 `import-attempt1.log`。

接入结果以 `import_receipt.json`、`registration_receipt.json` 与 `delivery.json` 为准。默认不运行检查、测试、地图、预览或验收渲染；图标制作渲染不作为游戏内外观验收。由用户在游戏内确认效果。

## 本次交付

- 模型、2K PBR、FBX、可编辑 Blend 和金属框改造图标制作完成。
- `FPSGAMEEditor Win64 Development` 后台构建成功，退出码 0。
- 续导入完成，实际保存 6 个 UE 资产：网格、材质、3 张 PBR 贴图及 UI 图标；已追加战斧专属选项和实际模块配方。
- 未运行游戏、联机测试或验收渲染。本次交付不引用之前握柄的测试结果。
