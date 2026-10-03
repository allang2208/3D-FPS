"""Publish author entrypoints and delivery only after actual saved UE assets."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent
m=json.loads((P/'pommel_manifest.json').read_text(encoding='utf-8'))
r=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not r.get('complete') or r['revision']!=m['revision']:raise RuntimeError('Actual cone assets must be saved first')
def write_parent(name,contents):
    backup=P/'Before'/('parent_'+name)
    if (S/name).exists() and not backup.exists():shutil.copy2(S/name,backup)
    (S/name).write_text(contents,encoding='utf-8')
for name in ['author_pommel.py','surface_recipe.py','render_menu_icon.py','import_assets.py']:
    text='"""Current Yanling pommel entrypoint: octagonal cone V3."""\nimport runpy\nfrom pathlib import Path\nrunpy.run_path(str(Path(__file__).resolve().parent / "ConeV3" / "'+name+'"),run_name="__main__")\n'
    write_parent(name,text)
delivery={'weapon':m['weapon'],'slot':m['slot'],'option':m['id'],'name':m['name'],'revision':m['revision'],'complete':True,
 'source_blend':'ConeV3/TangDao_YanlingConeV3_Editable.blend','source_export':'ConeV3/Export/'+m['mesh_name']+'.fbx',
 'source_glb':'ConeV3/Export/'+m['mesh_name']+'.glb','saved_assets':r['assets'],'mesh':r['mesh'],
 'lod_triangles_saved':r['lod_triangles_saved'],'pbr_resolution':m['pbr_resolution'],'catalog_installed':True,
 'gold_card_id_preserved':True,'gameplay_stats_unchanged':True,'installation_cm':m['location_cm'],
 'long_grip_follow':'existing pommel_offset_cm','changes':m['features'],'previous_packages_preserved':True,
 'before_sources':'trash/tang-dao-retired-20261003/SourceAssets/TangDaoMeshy20261002/YanlingPommel20261002/ConeV3/Before/','editor_launched':False,'cpp_changes':False,'native_build_required':False,
 'game_launched':False,'runtime_tested':False,'acceptance_rendered':False,'icon_production_rendered':True,
 'reference':'Reference/YanlingPommel_Overall.png; Reference/YanlingPommel_Detail.png',
 'reference_limit':'Hidden reverse faces and mount internals are inferred from the visible octagonal design and the actual grip interface.',
 'source_directory':'ConeV3'}
write_parent('delivery.json',json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
write_parent('README.md','''# 破锋燕翎配重锤：八面锥 V3

2026-10-02 用户指出 V2 锤头为钻石形、表面装饰与金属质感不符合参考后，重建为环侧宽端直接收向同一尖端的八面锥。头部为平直三角折面，最大截面位于连接环一侧，不再设置中段扩宽肩部。

源文件和重建入口位于 [ConeV3](ConeV3/README.md)，本目录四个作者／导入入口转向 V3。已保存的 UE 网格、材质、纹理与图标记录在 [import_receipt.json](import_receipt.json)，游戏的 `ue_tang_dao / pommel / yanling_breaker` 仍沿用同一身份。

连续鎏金折线甲框采用闭合倒角带状实体，贴合锥体后半段；小型龙云浮雕为实体浅浮雕并叠加细刻纹法线。环形云纹按圆环周长展开，锻钢、鎏金和漆面分别使用材质槽与 PBR。原有握柄端面与 `[0,0,-22.7]` cm 安装位置保留，长握柄跟随既有 `pommel_offset_cm`。

V1/V2 源与包退役归档在工程根 trash/tang-dao-retired-20261003，当前仅制作 ConeV3。未修改战斗属性、符文、手臂与护手。本次为制作与接入，未打开编辑器、启动游戏或做视觉验收，由用户测试。
''')
write_parent('PROVENANCE.md','''# 来源与制作记录

当前运行修订为 `ConeV3`。用户提供的总体图与锤头细节图保存在 `Reference/`，作为几何和纹饰参考；图中标注文字没有被当作新的玩法指令。

八面锥、连续折线甲框、连接环和真实接口在 Blender 5.1 中精确建模。龙云纹饰使用内置 imagegen 重新生成灰度雕刻素材，原图、提示词保存在 `ConeV3/Ornament/` 与 `ConeV3/imagegen_prompts.json`。软透明晕圈不参与浮雕高度；材质遮罩和几何高度从同一细纹配方派生。

锻钢／鎏金使用 4096 PBR，漆面使用 512 PBR。BaseColor 为线性金属反射色转换到 sRGB；ORM 为 AO／Roughness／Metallic，Normal 为 OpenGL，UE 导入翻转绿色通道。三个 Substrate 材质克隆自当前 TangDao SurfaceV2，另存旋风时序响应材质副本，不更改刀身符文。

改造图标由实际 V3 模型灰阶渲染后使用内置 imagegen 沿用认可的金属框，素材、最终 PNG 与 UE Texture 均保留。三维材质保留锻钢和暖鎏金。

旧版本源及资产按工程归档清单移至 trash，当前模型和纹理源保留。用户参考图的公开再分发许可未由本次制作认定；本次没有公开发布。未开展游戏测试或视觉验收。
''')
print('YANLING_CONE_V3_SOURCES_PUBLISHED',flush=True)
