"""User-requested diagnosis and repair of the checkerboard puddle material."""
import json,unreal as u
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
PATH='/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle'
NOISE='/Game/Props/RomanFountain20260917/OverflowV8/T_FountainFlowNoiseV8'
M=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('FPSGAME is required')
if any(p.get_path_name()==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved puddle material edits')
mat=u.load_asset(PATH);texture=u.load_asset(NOISE)
if not mat or not texture:raise RuntimeError('Puddle material/noise dependency missing')
nodes=[e for e in M.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionTextureSample) and e.get_editor_property('texture')==texture]
if len(nodes)!=2:raise RuntimeError('Expected the two authored puddle noise samples')
if texture.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_MASKS:raise RuntimeError('Noise compression has changed; preserve shared fountain texture')
receipt=dict(material=PATH,texture=NOISE,compression=str(texture.get_editor_property('compression_settings')),srgb=texture.get_editor_property('srgb'),before=[dict(node=n.get_name(),sampler=str(n.get_editor_property('sampler_type'))) for n in nodes],actors=[])
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE:
    receipt['world']=UE.get_editor_world().get_path_name()
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label()!='DGN_AV2_WetPatches':continue
        c=a.get_component_by_class(u.StaticMeshComponent)
        receipt['actors'].append(dict(actor=a.get_actor_label(),mesh=c.static_mesh.get_path_name(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
receipt['compile_errors_before']=list(M.recompile_material(mat))
mat.modify()
for node in nodes:node.modify();node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
receipt['compile_errors_after']=list(M.recompile_material(mat))
receipt['after']=[dict(node=n.get_name(),sampler=str(n.get_editor_property('sampler_type'))) for n in nodes]
receipt['stage']='compiled' if not receipt['compile_errors_after'] else 'compile_failed'
out=ROOT/'Receipts/puddle-sampler-repair.json';out.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if receipt['compile_errors_after']:raise RuntimeError('Puddle shader still fails: '+'; '.join(receipt['compile_errors_after']))
if not E.save_loaded_asset(mat,False):raise RuntimeError('Puddle material save failed')
receipt.update(stage='material_saved',saved_at=datetime.now().isoformat(),pie_started=False,rendered=False)
out.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('PUDDLE_SAMPLER_REPAIRED '+json.dumps(receipt))
