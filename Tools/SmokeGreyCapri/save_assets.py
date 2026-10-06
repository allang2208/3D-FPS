"""Import capri textures and save new native skeletal, pickup and icon packages."""
import importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
DEST='/Game/Characters/ModularOutfit20260924/SmokeGreyCapri20261004'
spec=importlib.util.spec_from_file_location('capri_native_io',str(P/'Tools/BrownLeatherSet/save_assets.py'))
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
io.R=R;io.DEST=DEST;io.shared.DEST=DEST
io.SLOTS=['GunmetalButton','SmokeGreyCotton','Unused','TonalThread','InnerFacing','NativeExposedCalf']
E=io.E;A=io.A;L=io.L;shared=io.shared

def materials():
    folder=DEST+'/Materials';E.make_directory(folder);textures={}
    for channel in ['BaseColor','Normal','ORM']:
        name='T_SmokeGreyTwill_'+channel;task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'))
        task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=io.load(folder+'/'+name)
        tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False)
        tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('compression_no_alpha',True)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        shared.save(tex);textures[channel]=tex
    fabrics=[]
    for suffix,tint in [('Main',(1.,1.,1.)),('Facing',(.84,.85,.83))]:
        m,create=io.mat('M_SmokeGreyTwill_'+suffix)
        if create:
            uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4.);uv.set_editor_property('v_tiling',4.)
            for channel,tex in textures.items():
                n=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',tex)
                n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
                shared.wire(uv,n,'UVs')
                if channel=='BaseColor':
                    c=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(*tint,1))
                    mult=L.create_material_expression(m,u.MaterialExpressionMultiply);shared.wire(n,mult,'A','RGB');shared.wire(c,mult,'B');shared.output(mult,u.MaterialProperty.MP_BASE_COLOR)
                elif channel=='Normal':shared.output(n,u.MaterialProperty.MP_NORMAL,'RGB')
                else:
                    for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:shared.output(n,prop,pin)
        io.compile_save(m);fabrics.append(m)
    skin=io.load(json.loads((R/'native_calf.json').read_text())['material'])
    return [io.constant('M_Capri_Gunmetal',(.065,.073,.075),.57,1),fabrics[0],fabrics[0],io.constant('M_Capri_Thread',(.067,.070,.062),.88,0),fabrics[1],skin]

def main(reuse_materials=False):
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Cannot author capri assets during play')
    mats=[io.load(path) for path in json.loads((R/'saved_assets.json').read_text())['materials']] if reuse_materials else materials()
    saved={'materials':[m.get_path_name() for m in mats]}
    for key,name in [('pants','Jason_SmokeGreyCapri'),('pants_high','Jason_SmokeGreyCapri_HighBootsFit')]:
        data=json.loads((R/(name+'.json')).read_text());mesh=io.save_skeletal(data,'SK_'+name,mats)
        E.set_metadata_tag(mesh,'EquipmentDefinition','ue_smoke_grey_capri');shared.save(mesh);saved[key]=mesh.get_path_name()
    # Clothing-only meshes: never show severed body parts in an equipment icon.
    garment=json.loads((R/'Jason_SmokeGreyCapri_Garment.json').read_text());source=io.load(garment['source']);native=io.copy(source)
    for kind in ['icon','pickup']:
        dm=shared.dynamic(garment,native)
        if kind=='icon':
            io.T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0));path=DEST+'/Icons/SM_SmokeGreyCapri_Display'
        else:
            points=garment['positions'];center=[(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)]
            io.T.translate_mesh(dm,u.Vector(*[-v for v in center]));io.T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90));path=DEST+'/Pickups/SM_SmokeGreyCapri'
        saved['pants_'+kind]=shared.static(dm,path,mats[:5])
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('CAPRI_NATIVE_ASSETS_SAVED',flush=True)
if __name__=='__main__':main()
