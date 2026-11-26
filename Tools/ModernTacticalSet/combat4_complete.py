"""Collect existing production receipts after clothing and backpack publication."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR4';F=P/'SourceAssets/BackpackFit20261024/ModernTacticalShirtR420261115'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
published=read(R/'published.json');packs=read(F/'saved_assets.json');pack_publication=read(F/'published.json')
if not published['completed'] or not packs['completed'] or pack_publication['status']!='saved_and_integrated':raise RuntimeError('Production is not complete')
published['backpacks_pending']=False;published['backpack_revision']=F.name
(R/'published.json').write_text(json.dumps(published,ensure_ascii=False,indent=2),encoding='utf-8')
lower=read(R/'lower-authored.json');authored=read(R/'authored.json');saved=read(R/'saved.json');art=read(R/'artwork.json')
record=dict(completed=True,wear_assets=len(authored['rows']),world_upper_variants=sum(x['rig'] in ['Jason','Kaitlin'] and not x.get('kind') for x in authored['rows']),first_person_sleeves=24,glove_variants=len(lower['glove_removed_faces']),degenerate_faces_removed=sum(lower['glove_removed_faces'].values()),pants_variants=10,boot_variants=2,inventory_icons=list(art['items']),backpack_meshes=len(packs['meshes']),backpack_statics=len(packs['statics']),backpack_revision=F.name,interactive_editor_launched=False,gameplay_tested=False,materials='Existing earth-brown R3 cloth PBR retained',clothing_publication=str(R/'published.json'),backpack_publication=str(F/'published.json'))
record['native_neck_fit']=read(R/'collar-fitted.json')['rigs']
record['storage_recovery']=str(R/'Receipts/storage-recovery.json')
(R/'completion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'README.md').write_text('''# TS01 Combat Shirt R4 — 2026-11-15

男女独立胸背衣片、低圆领连续领肩片、沿裁片切分的插肩线。采用原生身体碰撞、固定袖口锚点和离线布料余量塑形；实际褶皱写入游戏网格。袖袋改为圆角，护肘改为椭圆，领口、袖口、衣摆与接缝保留内衬和缝线。

防弹衣按新上衣的胸背和肩部表面重新适配，所有布层和装饰共用变形，快拆扣保持刚性。裤装圆化后膝布片并增加局部受力折痕，保留每种靴型的收口；靴子补充踝部屈曲形状，鞋底、鞋楦与金属鞋眼保持原形。手套移除 UE 单精度存储下塌陷的面，保留原生手指、腕部权重。

保留 CombatShirtR3 的土棕色布料 PBR 资产。R4 模型依赖该材质目录和原生身体骨架，不能单独删除这些依赖。头盔及保留盔外长发的配置沿用原修订。

Authored 保存实际制作数据；Simulation 保存离线布料场景；Models、Exports 保存原生绑定作者源和 FBX/GLB；Icons 保存标准透明物品图及相机对齐模型。Wear 的三个 LOD 显式保存。四件物品沿用原物品 ID，更新穿着、掉落和展示路径。七款背包双身体配对由标准 BackpackFit 流程重新制作并接入。

实际落盘和接入回执见 completion.json、published.json、saved.json、artwork-saved.json 及背包修订目录。未启动交互编辑器或游戏，未追加动作、游戏或联机验收。

制作中 D 盘空间不足：本轮 14 份 Blender 自动备份已保留到 E:/CodexWork/TS01CombatR4_20261115/BlenderAutoBackups；当前正式作者源仍位于本目录。JSON 制作数据采用 NTFS 透明压缩。游戏 Content 实际挂载在 F:/FPSGAMEData/Content，已保存资产发布到该实际目录。详见 Receipts/storage-recovery.json。
''',encoding='utf-8')
print('R4_PRODUCTION_COMPLETE',json.dumps(record,ensure_ascii=False),flush=True)
