"""Redo the skin surface from pre-MPFB shader sources; do not edit any mesh."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/BareSkinMPFB20261010'
R=P/'SourceAssets/BareSkinSurfaceRework20261010';R.mkdir(exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Finish PIE before saving the skin surface.')
original=json.loads((O/'inputs.json').read_text())
previous={d['path']:d for d in json.loads((O/'materials_saved.json').read_text())}
saved=[]
for entry in original['materials'].values():
    parent=u.load_asset(entry['parent']);name=parent.get_name();path=parent.get_path_name()
    if path in [s['path'] for s in saved]:continue
    custom=L.get_material_property_input_node(parent,u.MaterialProperty.MP_NORMAL)
    current=custom.get_editor_property('code');sha=hashlib.sha256(current.encode()).hexdigest()
    if sha!=previous[path]['shader_sha256'] and not current.startswith('// Bare skin surface rework 2026-10-10'):
        raise RuntimeError('Skin shader changed since this task saved it; retain current edits: '+path)
    code=entry['code']
    start=code.index('// One bounded micro-height offset')
    end=code.index('float4 fieldX=',start)
    code=code[:start]+'// Sample at the unchanged reference coordinate: no height/parallax offset.\n'+code[end:]
    code=code.replace('float fade=1-smoothstep(24,96,footprint);','float fade=1-smoothstep(12,56,footprint);')
    code=code.replace('MicroNormalStrength*fade*skinDetail*(8/tile)*(MicroHeightCm/.009100000013)',
                      'MicroNormalStrength*.22*fade*skinDetail*(8/tile)')
    code=code.replace('float3 detail=normalize(float3(-dot(gradient,T),-dot(gradient,B),1));',
        'float2 microSlope=float2(-dot(gradient,T),-dot(gradient,B));\n'
        'microSlope*=min(1,.10/max(length(microSlope),.000001));\n'
        'float3 detail=normalize(float3(microSlope,1));\n'
        'AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(.65,1,nail),AnatomicalNormal.z));')
    code=code.replace('float broad=.5*sin(RestPosition.x*2.3+RestPosition.y*1.8)*sin(RestPosition.z*2.7+RestPosition.x*.8);',
        'float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;')
    code=code.replace('WristTint*(1+broad*.035*forearmVariation)',
        'WristTint*float3(1.015,1,.99)*(1+broad*.018*forearmVariation)')
    code=code.replace('tone,ColourDetailStrength*skinDetail*fade','tone,ColourDetailStrength*.20*skinDetail*fade')
    code=code.replace('tone,localColourDetail*skinDetail*fade','tone,localColourDetail*.20*skinDetail*fade')
    code=code.replace('float sharedRough=.49-.04*palmar+.015*broad;',
        'float sharedRough=.50-.02*palmar+.004*broad;')
    code=code.replace('float rough=lerp(sharedRough,Surface.g,handAnatomy);',
        'float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,.65),handAnatomy);')
    code=code.replace('-.48)*skinDetail;','-.48)*skinDetail*.12*fade;')
    marker='// Keep the established cloth response'
    code=code.split(marker)[0]+'// Bare skin only; original clothing uses separate materials.\nOutColour=colour;\nOutRoughness=rough;\nOutScatter=SkinScatterStrength;\nreturn normalize(skinNormal);\n'
    code='// Bare skin surface rework 2026-10-10: original mesh, no parallax, bounded micro normal.\n'+code
    custom.set_editor_property('code',code)
    errors=L.recompile_material(parent)
    if errors:raise RuntimeError('Material compiler errors: '+name+': '+str(errors))
    E.remove_metadata_tag(parent,'MPFBSkinUpgrade')
    E.set_metadata_tag(parent,'BareSkinSurfaceRework','20261010: original mesh; no height offset; bounded micro normal; soft colour/roughness detail')
    if not E.save_loaded_asset(parent,False):raise RuntimeError('Could not save '+path)
    (R/(name+'.hlsl')).write_text(code)
    saved.append({'path':path,'baseline':'BareSkinMPFB20261010/inputs.json pre-upgrade shader',
        'shader_sha256':hashlib.sha256(code.encode()).hexdigest(),'mesh_edited':False,'runtime_tested':False})
    (R/'saved.json').write_text(json.dumps(saved,indent=2))
    print('BARE_SKIN_SURFACE_REWORK_SAVED',name,flush=True)
print('BARE_SKIN_SURFACE_REWORK_COMPLETE',len(saved),flush=True)
