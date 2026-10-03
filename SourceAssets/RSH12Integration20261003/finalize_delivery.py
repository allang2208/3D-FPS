"""Record saved-production status, without running tests or launching an app."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
assets=json.loads((O/'import_receipt.json').read_text(encoding='utf-8-sig'))
build=json.loads((O/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not assets['complete'] or build['status']!='Succeeded':raise RuntimeError('Production still incomplete')
recipe=json.loads((O/'production_recipe.json').read_text())
recipe.update(source_acquired=True,assets_imported=True,runtime_connected=True,native_build_completed=True,
 runtime_tested=False,assets=assets['meshes'],profiles=assets['profiles'],native_build=build)
(O/'production_recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf8')
body='''# RSH-12 接入交付（2026-10-03）

RSH-12 的资产已通过后台 commandlet 导入并保存，运行代码已接入，FPSGAMEEditor 原生模块已编译落盘。没有启动 UE 编辑器、游戏、PIE，未进行测试、验收截图或验收渲染，由用户自行测试。

- 定义：`ue_rsh12`；五发容量；`ammo_127` 弹药组。
- 单持网格：`/Game/Weapons/RSH12/SK_RSH12_Manny`。双持／副手使用同目录 `Dual/r`、`Dual/l` 的独立网格。
- 直接复用当前 715 的动画序列，未复制完整动画族。三套 `DA_base` 差量资源位于 `/Game/Weapons/AnimationProfiles20261001/ue_rsh12`，修正机械轴心、下置枪口、机瞄位置和五发转轮，并对单持装填接触做离线两段手臂适配。
- 动作继续采用 715 的源时间时钟：逐发装填、空仓先退壳、非空仓保留余弹；单持和每手双持均限制为五发。原厂逐发模式不提供六发速装器。
- 保留源 FBX 的闭合枪体、UV、法线及完整 PBR 贴图。弹巢、摇臂、退壳杆、扳机和击锤独立绑定。弹药采用包内独立子弹，制作五份弹头／弹壳和 `SM_RSH12_Cartridge`。
- 材质采用本枪的源贴图适配共享 WS 表面／雨水图。原生裸手及衣袖／手套继续使用现有 715 的服装映射。
- 库存／伤害公式／弹药／装备存档／弹壳状态、枪匠原厂预览、动态图标、世界掉落、Cook 路径和授权署名已接入。图标使用源枪体和贴图制作。枪匠提供原厂选项及快速扳机数值选项；没有套用 715 的改造模型。
- 起始军械库发放一把满载五发的 RSH-12 和 50 发普通 12.7 毫米备弹；既有存档按 `ArmoryReceived` 的新定义发放，不修改用户存档文件。

初始游戏数值：射击间隔 0.38 秒，显示基础伤害 90，实际战斗公式基础项 36、敏捷 0.8、感知 1.6；未做平衡测试。普通最大补四发的源片段 5.7 秒，空仓补五发的源片段 7.7 秒，实际耗时继续受现有属性和换弹倍率影响。

来源：[Rsh-12 by Medji](https://sketchfab.com/3d-models/rsh-12-177cd570002d4e89bd378ec328a47f9c)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。原始 ZIP、FBX、贴图、官方元数据、可编辑 Blender、制作脚本和本次源码／目录备份保留在 `SourceAssets/RSH12Integration20261003`。授权署名同时保存于 `Content/ColdSteelData/Licenses/RSH12-Medji-CCBY4.txt`。认证信息及临时下载地址未保存。

制作记录：`acquisition_receipt.json` 为获取记录；`import_receipt.json` 为实际保存资产记录；`runtime_edits.json` 为接入文件记录；`build_receipt.json` 为原生构建产物记录。后台姿态写入 API `UWeaponGripProfile::SetSharedClipsFromJson` 用于保存外部制作差量；运行采样仍使用现有 `WeaponGripProfile` 管线。
'''
(O/'README.md').write_text(body,encoding='utf8')
doc=P/'Docs/Weapons/rsh12-integration-20261003.md';doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text(body,encoding='utf8')
(O/'delivery.json').write_text(json.dumps(dict(status='imported_saved_connected_built',definition='ue_rsh12',capacity=5,ammo='ammo_127',source_assets=str(O),documentation=str(doc),mesh_assets=assets['meshes'],profile_assets=assets['profiles'],compiled_dll=build['dll'],runtime_tested=False,editor_opened=False,acceptance_rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('RSH12_DELIVERY_RECORDED')
