"""Install the photographed cliff scans, the formal Landscape relief layer, terrain and themed PCG."""
from pathlib import Path
import os,sys,json
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_trail_cover_materials as art
import author_trail_cover_level as level
import author_roadside_leaves as leaves
import landscape_themes as themes
from author_continuous_meadow import tagged

ed,lib=art.ed,art.lib
folder='/Game/ForestPathStudy/VillageRegion/CliffExposure'
spec=[('CliffField','T_CliffField','BC7','LINEAR_COLOR'),('CliffColor','T_CliffColor','DEFAULT','COLOR'),
      ('CliffNormal','T_CliffNormal','NORMALMAP','NORMAL'),('CliffData','T_CliffARH','MASKS','MASKS')]

def wire_exposure(mat,shade,code):
    pins=list(shade.get_editor_property('inputs'))
    for key in [p[0] for p in spec]+['CliffEye']:
        if not any(str(v.get_editor_property('input_name'))==key for v in pins):
            pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    shade.set_editor_property('inputs',pins)
    for key,name,comp,kind in spec:
        obj=tagged(mat,u.MaterialExpressionTextureObject,'Rock exposure '+key)
        obj.set_editor_property('texture',art.asset(folder+'/'+name));obj.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind));art.wire(obj,'',shade,key)
    eye=tagged(mat,u.MaterialExpressionCameraPositionWS,'Rock exposure camera');art.wire(eye,'',shade,'CliffEye')
    # Fully exposed stone can skip underlying meadow blades and leaf atlas reads.
    field='float exposure=Texture2DSampleLevel(CliffField,GetMaterialSharedSampler(CliffFieldSampler,Material.Clamp_WorldGroupSettings),(P.xy*.01+float2(624.,320.))/1024.,0.).r;'
    code=code.replace('float cover=saturate(F.r);',field+'\nfloat cover=saturate(F.r)*(1.-smoothstep(.69,.99,exposure));').replace('if(amount>.025)','if(amount>.025 && exposure<.985)')
    return code.replace('return GroundColor;',Path(__file__).with_name('cliff_surface.ush').read_text(encoding='utf-8-sig'))

def rock_assets():
    src=art.src;lib.make_directory(folder)
    for key,name,comp,kind in spec:
        t=art.tex(name,folder,comp,key=='CliffColor')
        if key=='CliffField':
            for axis in ('address_x','address_y'):t.set_editor_property(axis,u.TextureAddress.TA_CLAMP)
        t.set_editor_property('never_stream',False);art.save(t)
    mesh=ledge_mesh(src,'ffa5ac16-348a-4c1f-8404-6c031ebfcfce','NordicLedge','M_NordicForestLedge')
    shelf=ledge_mesh(src,'2854ca12-58fc-4b5e-80c7-33c73823f8bd','BareShelf','M_BareRockShelf')
    for path in (art.ref+'/M_ForestReferenceMesh',art.dest+'/M_ForestVillageLandscape'):
        m=art.asset(path);nodes=ed.get_material_expressions(m)
        shade=next(n for n in nodes if n.get_editor_property('desc')=='R26 continuous ground cover')
        root=next(n for n in nodes if isinstance(n,u.MaterialExpressionMakeMaterialAttributes) and art.inputs(m,n).get('BaseColor')==shade)
        leaves.configure(m,shade,root);art.compile_mat(m)
    return mesh,shelf

def ledge_mesh(src,uid,stem,material_name):
    from import_woodland_scans import imported
    pack=next((src/'Fab'/uid).rglob('*.gltf')).parent
    path=folder+'/'+material_name
    mat=art.asset(path) if lib.does_asset_exist(path) else art.tools.create_asset(material_name,folder,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True);mat.set_editor_property('used_with_nanite',True)
    for ch,kind,comp,channels in [('B','COLOR','DEFAULT',[('RGB','BASE_COLOR')]),('N','NORMAL','NORMALMAP',[('RGB','NORMAL')]),('ORM','MASKS','MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS')])]:
        name='T_'+stem+'_'+ch
        if stem=='BareShelf' and ch=='B':
            tex=art.import_asset('T_BareShelf_B.png',folder,name)
        else:
            tex=art.asset(folder+'/'+name) if lib.does_asset_exist(folder+'/'+name) else imported(next(pack.rglob('*_'+ch+'.png')),folder,name)[0]
        tex.set_editor_property('srgb',ch=='B');tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+comp));tex.set_editor_property('max_texture_size',1024);art.save(tex)
        sample=tagged(mat,u.MaterialExpressionTextureSample,'Ledge '+ch);sample.set_editor_property('texture',tex);sample.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
        for pin,prop in channels:
            if not ed.connect_material_property(sample,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    art.compile_mat(mat)
    mesh_path=folder+'/'+stem+'/StaticMeshes/'+stem
    if not lib.does_asset_exist(mesh_path):imported(src/('Geometry/'+stem+'.gltf'),folder)
    mesh=art.asset(mesh_path)
    if not mesh:raise RuntimeError('Ledge import '+mesh_path)
    if not mesh.static_materials:mesh.set_editor_property('static_materials',[u.StaticMaterial()])
    for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    lib.set_metadata_tag(mesh,'ForestEcologyLayer','Rocks');art.save(mesh)
    return mesh

def install():
    mesh,shelf=rock_assets()
    copy=level.copy
    w=level.save.load_map(copy)
    landscape=next(a for a in level.actor_list() if isinstance(a,u.Landscape) and a.get_path_name().startswith(copy+'.'))
    if not u.ForestVillageRegion.write_cliff_landscape_layer(landscape,str(art.src/'cliff-landscape-delta.i16')):raise RuntimeError('Study copy cliff layer')
    if not level.save.save_map(w,copy):raise RuntimeError('Cannot save Landscape copy')
    w=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):raise RuntimeError('Persistent level required')
    actors=level.actor_list();reg=next(a for a in actors if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(level.village+'.'))
    if not reg.bake_reference_surface(str(art.src),art.asset(art.ref+'/MI_ForestReference')):raise RuntimeError('Cliff terrain and collisions')
    if not reg.install_cliff_exposure(str(art.src),mesh,shelf):raise RuntimeError('Cliff ledges')
    if not reg.install_grass_cover(str(art.src/'Grass/near_grass.u8'),True):raise RuntimeError('Cliff near grass')
    if 'talus_source' in themes.preset('HillsLandscape')['resources']:
        from author_cliff_talus import install_sites
        install_sites(reg,art.src)
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates:raise RuntimeError('Missing original PCG templates')
    for name in ('HillsLandscape','RoadLandscape'):
        if not reg.bake_vegetation(themes.point_input(themes.preset(name),None),templates,name):raise RuntimeError('Theme '+name)
    fine,cells=level.place_meadows(w)
    counts={m.get_name():sum(c.get_instance_count() for c in reg.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh==m) for m in (mesh,shelf)}
    total=sum(counts.values())
    report=json.loads((art.src/'cliff-exposure.json').read_text())
    if total!=report['hill_ledges']+report['road_ledges'] or counts['BareShelf']!=report['bare_shelves']:raise RuntimeError('Missing baked ledges '+str(total))
    if not level.save.save_map(w,level.village):raise RuntimeError('Cliff map save')
    (art.batch/'authored.json').write_text(json.dumps(dict(models=counts,ledges=total,meshes=[mesh.get_path_name(),shelf.get_path_name()],fine_grass=fine,cells=cells,world=w.get_path_name())))
if __name__=='__main__':install()
