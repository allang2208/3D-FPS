"""Scoped repair of the two hall stair assemblies, six portal seams and six PPE bodies."""
import unreal as u
import json,hashlib,importlib.util,traceback,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;BASE='/Game/Dungeons/FacilityTransit20261007/RefineV3';OWNER='FacilityTransit.DetailV3'
MAN=json.loads((ROOT/'manifest.json').read_text('utf8'));CFG=json.loads((PARENT/'Config/layout.json').read_text('utf8'))
spec=importlib.util.spec_from_file_location('facility_v3_support',PARENT/'install.py');I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
R=I.R;E=R.E;A=R.A;L=R.L;AA=R.AA
report=dict(stage='preparing',saved_assets=[],maps=[],tests_run=False,rendered=False,game_run=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for k,v in dict(ROOT=ROOT,OWNER=OWNER,BASE=BASE,MAN=MAN,report=report,record=record).items():setattr(R,k,v)

def materials():
    textures={}
    for f in (ROOT/'Authored/Textures').glob('*.png'):
        name=f.stem.removeprefix('T_FT3_');key=hashlib.sha256(f.read_bytes()).hexdigest();path=BASE+'/Textures/'+f.stem;t=R.reuse(path,key)
        if not t:
            t=R.imported(path,f);normal=name.endswith('NormalDX');color=name=='PPELabels';t.set_editor_property('srgb',color);t.set_editor_property('never_stream',False);t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_BC7 if color else u.TextureCompressionSettings.TC_MASKS)
            if normal:t.set_editor_property('flip_green_channel',False)
            R.saved(t,key)
        textures[name]=t
    for role in ('PPEFabric','PPELabels'):
        path=BASE+'/Materials/M_FT3_'+role;key='v3-'+role+':substrate-v1'
        if R.reuse(path,key):continue
        m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
        slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        def sample(name,kind):
            n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[name]);n.set_editor_property('sampler_type',kind);return n
        def scalar(v):
            n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
        def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
        if role=='PPELabels':
            base=sample(role,u.MaterialSamplerType.SAMPLERTYPE_COLOR);bout='RGB';rough=scalar(.70);rout=''
        else:
            tint=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);tint.set_editor_property('constant',u.LinearColor(.24,.22,.16,1));tone=sample('Fabric_Tone',u.MaterialSamplerType.SAMPLERTYPE_MASKS);base=L.create_material_expression(m,u.MaterialExpressionMultiply);L.connect_material_expressions(tint,'',base,'A');L.connect_material_expressions(tone,'R',base,'B');bout='';rough=sample('Fabric_Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS);rout='R'
            connect(sample('Fabric_NormalDX',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
        connect(base,bout,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');connect(rough,rout,u.MaterialProperty.MP_ROUGHNESS,'Roughness');connect(scalar(0),'',u.MaterialProperty.MP_METALLIC,'Metallic');L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Required material build failed '+str(errors))
        R.saved(m,key)

def patch_map(path,themes):
    R.guard();world=u.EditorLoadingAndSavingUtils.load_map(path)
    if not world:raise RuntimeError('Unable to load '+path)
    actors=list(AA.get_all_level_actors());changes=dict(path=path,hall_parts=0,portal_parts=0,ppe_bodies=0,saved=False)
    for m in MAN['meshes']:
        room=m['room'];kind=m['kind']
        if room=='PPE':continue
        if room=='Hall':
            label='FacilityTransit_SM_FT_Hall_'+kind
            targets=[a for a in actors if a.get_actor_label()==label]
            if targets:
                for a in targets:
                    a.modify();a.static_mesh_component.set_static_mesh(R.asset(m['mesh']));a.set_editor_property('tags',list(a.tags)+[u.Name(OWNER)])
            else:R.static(m['mesh'],[0,0,0],'SM_FT_Hall_'+kind,m['collision'],shadow=m['cast_shadow'],rail=kind=='Rails')
            changes['hall_parts']+=1
        elif room in themes:
            idx=themes.index(room);gate=CFG['gates'][idx];old=[]
            for a in actors:
                if u.Name('FacilityTransit.Theme.'+room) not in a.tags:continue
                comp=a.get_component_by_class(u.StaticMeshComponent)
                if comp and comp.static_mesh and comp.static_mesh.get_name().endswith('_'+kind):old.append(a)
            if old:
                for a in old:a.modify();a.static_mesh_component.set_static_mesh(R.asset(m['mesh']));a.set_editor_property('tags',list(a.tags)+[u.Name(OWNER)])
            else:
                a=R.static(m['mesh'],gate['position_m'],gate['route']+'_'+m['name'],m['collision'],gate['yaw_deg'],shadow=m['cast_shadow'],folder='Portals/'+gate['route']+'/'+room)
                a.set_editor_property('tags',list(a.tags)+[u.Name('FacilityTransit.Theme.'+room),u.Name('FacilityTransit.Route.'+gate['route']),u.Name(OWNER)])
            changes['portal_parts']+=1
    body=R.asset(BASE+'/Meshes/SM_FT3_PPELocker_Body')
    for a in actors:
        if isinstance(a,u.ColdSteelSceneContainer) and str(a.get_editor_property('container_id')).startswith('FacilityTransit20261007.PPE'):
            a.modify();a.body.set_static_mesh(body);changes['ppe_bodies']+=1
    E.set_metadata_tag(world,OWNER+'.Revision','20261007-stairs-junctions-ppe')
    if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Unable to save '+path)
    changes['saved']=True;report['maps'].append(changes);record()

def publish():
    parent=json.loads((PARENT/'manifest.json').read_text('utf8'));patch={(m['room'],m['kind']):m for m in MAN['meshes']};merged=[]
    for m in parent['meshes']:merged.append(patch.pop((m['room'],m['kind']),m))
    merged.extend(patch.values());parent['meshes']=merged;parent['active_detail_revision']=str(ROOT);(PARENT/'manifest.json').write_text(json.dumps(parent,indent=2),encoding='utf8')
    cfg=json.loads((PARENT/'Config/layout.json').read_text('utf8'))
    for p in cfg['containers']:
        if p['id'].startswith('PPE'):p['body']=BASE+'/Meshes/SM_FT3_PPELocker_Body'
    cfg['detail_revision']='20261007-stairs-junctions-ppe';(PARENT/'Config/layout.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    runpy.run_path(str(PARENT/'draft.py'),run_name='__main__')

def main():
    R.guard();record();materials();R.meshes();report['stage']='assets_saved';record()
    for path,themes in zip((CFG['map'],CFG['alternate_map']),CFG['preview_sets']):patch_map(path,themes)
    publish();report['stage']='maps_saved';record();u.log('FACILITY_DETAIL_V3_MAPS_SAVED')
if __name__=='__main__':
    try:main()
    except Exception:report['error']=traceback.format_exc();record();raise
