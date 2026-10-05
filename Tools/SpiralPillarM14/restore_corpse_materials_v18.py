"""Restore the V18 deformed-normal materials used by the current V19 corpse only."""
from pathlib import Path
import json, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004'
OUT=ROOT/'ProductionV18'
DEST='/Game/Monsters/SpiralPillarM14'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
(OUT/'Records').mkdir(parents=True,exist_ok=True)
report={'complete':False,'saved':[],'tested':False,'rendered':False,'user_testing_pending':True}

def record():
    (OUT/'Records/material_restore.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def duplicate(source,path):
    return u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)

def wire(source,target,pin):
    if not L.connect_material_expressions(source,'',target,pin):
        raise RuntimeError('Could not wire '+pin)

def corpse_material(source):
    material=duplicate(source.get_path_name(),DEST+'/SoftCorpseV18/'+source.get_name()+'_SoftCorpse')
    if any(isinstance(node,u.MaterialExpressionCustom) and
           node.get_editor_property('description')=='M14V18 DeformedSurfaceNormal'
           for node in L.get_material_expressions(material)):
        return material
    original=L.get_material_property_input_node(material,u.MaterialProperty.MP_NORMAL)
    if not original:
        raise RuntimeError('M14 material has no tangent normal input: '+source.get_path_name())
    material.set_editor_property('tangent_space_normal',False)
    # Translation-only tetrahedral skinning exactly embeds positions. Reconstruct
    # the deformed frame from screen derivatives, retaining the original normal map.
    custom=L.create_material_expression(material,u.MaterialExpressionCustom)
    custom.set_editor_property('description','M14V18 DeformedSurfaceNormal')
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    names=('P','UV','N','View','Fallback')
    pins=[]
    for name in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    custom.set_editor_property('code',
        'float3 dx=ddx(P),dy=ddy(P);float2 ux=ddx(UV),uy=ddy(UV);'
        'float3 g=cross(dy,dx);float g2=dot(g,g);'
        'float3 gn=g2>1e-16?g*rsqrt(max(g2,1e-16)):normalize(Fallback);'
        'gn*=dot(gn,View)>=0?1:-1;'
        'float det=ux.x*uy.y-ux.y*uy.x;'
        'if(abs(det)<1e-10)return gn;'
        'float sd=det>=0?1:-1;'
        'float3 t=(dx*uy.y-dy*ux.y)*sd;t-=gn*dot(t,gn);'
        'float t2=dot(t,t);if(t2<1e-16)return gn;t*=rsqrt(max(t2,1e-16));'
        'float3 b=(-dx*uy.x+dy*ux.x)*sd;b-=gn*dot(b,gn)+t*dot(b,t);'
        'float b2=dot(b,b);if(b2<1e-16)return gn;b*=rsqrt(max(b2,1e-16));'
        'float3 result=t*N.x+b*N.y+gn*max(N.z,0.001);'
        'return result*rsqrt(max(dot(result,result),1e-16));')
    position=L.create_material_expression(material,u.MaterialExpressionWorldPosition)
    position.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE)
    uv=L.create_material_expression(material,u.MaterialExpressionTextureCoordinate)
    view=L.create_material_expression(material,u.MaterialExpressionCameraVectorWS)
    fallback=L.create_material_expression(material,u.MaterialExpressionVertexNormalWS)
    # World-space normals are not automatically two-sided-flipped by UE.
    # Orient the geometric frame toward the visible face; do not multiply Side.
    for source_node,pin in ((position,'P'),(uv,'UV'),(original,'N'),(view,'View'),(fallback,'Fallback')):
        wire(source_node,custom,pin)
    if not L.connect_material_property(custom,'',u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Could not connect corpse normal')
    for node in L.get_material_expressions(material):
        if isinstance(node,u.MaterialExpressionSubstrateShadingModels):
            wire(custom,node,'Normal')
    return material


def main():
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14')
    living=u.get_default_object(bp.generated_class()).get_editor_property('visual_mesh')
    for slot in living.get_editor_property('materials'):
        material=corpse_material(slot.get_editor_property('material_interface'))
        L.recompile_material(material)
        save(material)
    report.update(complete=True,blueprint_changed=False,corpse_binding_changed=False)
    record()
    print('M14_CURRENT_CORPSE_MATERIALS_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
