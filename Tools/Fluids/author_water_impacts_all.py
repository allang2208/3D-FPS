"""Extend accepted water hits; keep the fixed atlas/crown material and base water graphs."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
import author_river_pilot as b
import author_river_splash_natural as natural


def augment_static_surface(material):
    from water_wake_authoring import wake_inputs
    lib=b.LIB
    code=(b.OUT/'RippleField.hlsl').read_text()
    owned=[n for n in lib.get_material_expressions(material) if isinstance(n,u.MaterialExpressionCustom)
           and n.get_editor_property('description')=='All water impact field']
    if owned:
        wake_inputs(material,owned[0])
        owned[0].set_editor_property('code',code)
        return
    baseline={}
    for name in ('NORMAL','BASE_COLOR','ROUGHNESS','OPACITY'):
        prop=getattr(u.MaterialProperty,'MP_'+name)
        baseline[name]=(lib.get_material_property_input_node(material,prop),lib.get_material_property_input_node_output_name(material,prop))
        if baseline[name][0] is None:
            raise RuntimeError('Missing '+name+' on '+material.get_path_name())
    position=b.node(material,u.MaterialExpressionWorldPosition)
    time=b.node(material,u.MaterialExpressionTime)
    enabled=b.scalar(material,'WaterImpactEnabled',0)
    # Still water, same ripple shader. Physical puddle depth must not erase surface normals.
    flow=b.vector(material,'WaterImpactFlow',(.5,.5,0,1))
    depth=b.scalar(material,'WaterImpactDepth',12)
    inputs={'Pilot':enabled,'Position':position,'Clock':time,'Depth':depth,'Flow':flow}
    inputs.update({'Hit'+str(i):(b.vector(material,'WaterHit'+str(i),(0,0,-10000,0)),'RGBA') for i in range(8)})
    inputs.update({'Meta'+str(i):(b.vector(material,'WaterHitMeta'+str(i),(0,1,1,0)),'RGBA') for i in range(8)})
    ripple=b.custom(material,code,inputs,3,'All water impact field')
    wake_inputs(material,ripple)
    vertex=b.node(material,u.MaterialExpressionVertexColor)
    puddle='Puddle' in material.get_name()
    foam=b.custom(material,'float edge='+('saturate(Vertex.r)' if puddle else '1.0')+';return R.z*edge*'+('.12;' if puddle else '.26;'),
                  {'R':ripple,'Vertex':vertex})
    normal=b.custom(material,'return normalize(float3(Base.xy+R.xy*'+('saturate(Vertex.r)' if puddle else '1.0')+',Base.z));',
                    {'Base':baseline['NORMAL'],'R':ripple,'Vertex':vertex},3)
    b.prop(material,normal,'NORMAL')
    b.prop(material,b.custom(material,'return lerp(Base,float3(.55,.63,.60),saturate(F));',{'Base':baseline['BASE_COLOR'],'F':foam},3),'BASE_COLOR')
    b.prop(material,b.custom(material,'return lerp(Base,.34,saturate(F));',{'Base':baseline['ROUGHNESS'],'F':foam}),'ROUGHNESS')
    b.prop(material,b.custom(material,'return saturate(Base+F*.36);',{'Base':baseline['OPACITY'],'F':foam}),'OPACITY')
    b.EAL.set_metadata_tag(material,'WaterImpacts.Authored','20260924')


def author():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('Preserve active game; stop PIE before authoring water materials')
    paths=[b.DEST+'/M_RiverPilot',b.DEST+'/NS_RiverBulletSplash',
           '/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3',
           '/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle']
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p in dirty for p in paths):raise RuntimeError('Preserve unsaved water asset edits')
    b.SAVED.clear()
    b.surface()
    for path in paths[2:]:
        material=u.load_asset(path)
        if not material:raise RuntimeError('Missing existing water master '+path)
        augment_static_surface(material)
        b.save(material)
    # Only rebuild emitter expressions for smaller shallow-water hits. The accepted
    # repaired atlas, frame guards, resident mips and crown material stay as saved.
    natural.system(u.load_asset(b.DEST+'/M_RiverDrop'),u.load_asset(b.DEST+'/M_RiverCrown'))
    receipt=dict(revision='all-water-secondary-20260924',saved=b.SAVED,
                 unchanged_atlas=True,unchanged_crown_material=True,splash_pool=12,
                 global_ripple_slots=8,secondary_rings_per_hit=2,tests_run=False)
    (ROOT/'SourceAssets/WaterImpactAll20260924/assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('ALL_WATER_ASSETS_SAVED '+json.dumps(receipt))


if __name__=='__main__':
    author()
