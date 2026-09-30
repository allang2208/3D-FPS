"""Read the two reported garment bindings and their actual saved LODs."""
import json, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/CharcoalGarmentRepair20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import source_snapshot, snapshot, transform
from garment_pipeline import write
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
item=c['items']['ue_field_sweater_charcoal']; write(R/'before-item.json',item)
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
sources={'Body':body['body_mesh'],'Traversal':'/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7.SK_Traversal_BareArmsV7'}
for profile,native_path in sources.items():
    paths={'shirt':item['rig_meshes'][profile],'skin':c['profiles'][native_path]['native_bare_skin'],'native':native_path}
    write(R/'Before'/profile/'paths.json',paths)
    for name,path in paths.items():
        asset=u.load_asset(path)
        dm,d=source_snapshot(asset)
        d['slots']=[{'name':str(m.material_slot_name),'material':m.material_interface.get_path_name() if m.material_interface else None} for m in asset.get_editor_property('materials')]
        write(R/'Before'/profile/(name+'.json'),d)
        if name!='native':
            for lod in range(3):write(R/'Before'/profile/(name+'_LOD'+str(lod)+'.json'),snapshot(asset,lod))
        print('CHARCOAL_SOURCE',profile,name,len(d['positions']),len(d['triangles']),flush=True)
    native=u.load_asset(native_path); _,d=source_snapshot(native)
    clips=({'Idle':body['clips']['Unarmed.Idle'],'Rifle':body['clips']['Rifle.Idle']} if profile=='Body' else {a:'/Game/Movement/Traversal/Native/A_Traversal_'+a for a in ['Vault','Mantle','Climb']})
    poses={}
    for name,path in clips.items():
        clip=u.load_asset(path); opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=native;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
        for i in range(11):
            time=clip.get_play_length()*i/10;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
            poses[name+'_'+str(i)]=dict(clip=path,time=time,bones={n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in d['rest']})
    write(R/'Before'/profile/'poses.json',poses)
print('CHARCOAL_COLLECT_DONE',flush=True)
