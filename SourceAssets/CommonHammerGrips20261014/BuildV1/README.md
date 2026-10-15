# 通用战锤握持包覆 BuildV1

由 `../ConceptV1/three-grips-design.png` 接续制作三款：斜纹速握包覆、叠革缓震包覆、菱编蓄力包覆。遮挡侧按同一缠绕／分节／编织结构构造。首个适配宿主为 `ue_steel_warhammer`，不自动兼容尺寸不同的其他近战武器。

## 制作源

- `read_factory.py` 从当前原装模块读取尺寸与截面资料，结果为 `factory_geometry.json`。
- `author_grips.py` 生成 `CommonHammerGrips_Editable.blend` 和三份 `Export/*.fbx`。同一 Blender 源中将三件横向排开便于编辑，导出时保持原模块局部坐标与安装原点。
- 总长 49 cm。原装上端与下端各保留 2.5 cm 的原几何、UV、表面法线及同源材质，覆盖物主体在两端之间重建。新表面以截面连续过渡接到原有切口；实体编带在承托层外排列，避免叠加整层旧包覆。
- 斜纹织带具有实体厚度和搭接边；皮革软垫为九节，附侧缝；菱编为正反方向的四条皮带，交点按高度交替抬起／压低。
- `author_textures.py` 制作周期连续的 2K 织物与皮革材质贴图，每类包含 BaseColor、切线 Normal、ORM。按 12 cm 物理平铺尺度从程序高度场求法线，属于程序制作 PBR，不声称是照片扫描。运行材质保留灰褐织物、棕色皮革与黑褐编革色彩。沿用原装金属收口材质。
- `render_icon_sources.py` 从最终模型制作独立灰阶图标源，不回写运行材质。`icon_prompt_template.txt`、`icon_generation.json` 记录基于真实模型源和已认可框体生成最终图标的输入。`Icons/` 是正式 PNG，只有边框外缘透明。

## 接入

`import_grips.py` 保存纹理、材质、静态网格与三张共享图标后，才调用 `register_grips.py` 发布正式目录。后者只合并 `grip` 槽，保留其他改造栏目、已退出的长柄改造项状态、符文数值与并行编辑；后续模型重制也保留已配置数值。

当前模型：`/Game/Weapons/CommonHammerGrips20261014/BuildV1/UV1/SM_CommonHammerGrip_<id>_V1`。
共享选项目录：`Content/ColdSteelData/common-hammer-grips.json`。
共享图标键：`grip_<id>`。
战锤通过 `grip.options_library` 引用选项，模块目录记录每款实际模型及 Z=40.5 cm 的安装位置。沿用现有持握、改造草稿／应用／取消、物品预览及世界掉落装配入口。

`catalog.py` 已同步用户后续确定的数值：斜纹攻速 +15%、体力消耗 −10%、韧性伤害 −15%；叠革体力消耗 −25%；菱编攻速 +5%、体力消耗 +10%、重击蓄力速度 +25%。`effects` 从同一 `stats` 生成，无独立触发特效。`../Balance20261014/apply_balance.py` 专门发布数值，不重跑模型导入。建模阶段的旧回执保持原始阶段含义，当前数值交付见 `../Balance20261014/README.md`。

后台导入走 `import_background.ps1` 的工程进程前置条件与资产批次互斥。已有编辑器时改用既有 `mcp_call_codex.ps1 -PythonScript` 批次，不打开第二个界面或强制结束进程。`-FreshPackagesOnly` 在其他无界面任务运行时仅允许新目标包或本批未发布的部分保存，不覆盖已存在的其他包；原装材质只读取。

首次导入已保存三款模型、三份材质、六张 PBR 纹理与三张图标，`import_receipt.json.complete=true`。导入日志曾提示细小封边的近零切线，已在作者入口为退化 UV 三角面补上有效平面映射，保留有效原装／编带 UV。`import_mesh_uv.py` 将修订网格保存到独立 `UV1` 目录并更新三款槽位引用，未覆盖原始已保存网格；`uv_import_receipt.json.complete=true`，最后后台 commandlet 退出码 0。重建入口使用 `catalog.py` 的 `MESH_DIR`，继续指向 UV1。

曾尝试在已有编辑器内提交修订保存，但 Python 远程节点不可连接，请求未执行；该进程随后自行退出，修订通过后台批次完成。本任务未启动或关闭交互编辑器。早期枚举拼写错误及修复前导入日志作为制作记录保留，不作为最终失败状态。

没有 C++ 修改，无需额外原生构建；必要材质编译随资产制作完成。没有运行游戏、联机或验收渲染，实际握持与外观由用户体验。
