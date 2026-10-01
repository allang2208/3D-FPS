"""Production UI images from original HK416 geometry, not acceptance renders."""
import bpy,bmesh,ast,json,math,sys,shutil,struct
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];I=O/'Icons';SC=O/'IconScenes'
I.mkdir(exist_ok=True);SC.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
auth=json.loads((O/'authoring.json').read_text());RI=Matrix(auth['root_matrix']).inverted();AI=Matrix(auth['source_to_weapon_root']).inverted()
# Reuse the established transparent icon studio and neutral removal glyph.
tree=ast.parse((O.parent/'G18IconsFinal20260930/author_icons.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'scene','remove_symbol','reset'}],type_ignores=[]),'icon studio','exec'))
def shader(name,color=(.4,.4,.4,1),metal=0,rough=.55):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return mat,bs
def source(part):
    file=O/'HK416_Gameplay_Editable.blend' if part=='equipment' else Path(auth['static'][part]['fbx']).with_name('SM_HK416_'+part+'_Editable.blend')
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n in auth['source_parts'] and auth['source_parts'][n]['role']=='body'] if part=='equipment' else ['SM_HK416_'+part]
    objects=[]
    for ob in dst.objects:
        bpy.context.scene.collection.objects.link(ob);ob.modifiers.clear();ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        ob.hide_set(False);ob.hide_render=False;ob.data.transform(RI)
        if part=='factory_sights':
            # Keep the entire rear diopter and its base; discard only the front sight.
            bm=bmesh.new();bm.from_mesh(ob.data)
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if (AI@v.co).y>0],context='VERTS');bm.to_mesh(ob.data);bm.free()
        for uv in ob.data.uv_layers:uv.active_render=False
        if ob.data.uv_layers:ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
        objects.append(ob)
    return objects,str(file)
selected_parts=next((set(arg.split('=',1)[1].split(',')) for arg in sys.argv if arg.startswith('--parts=')),None)
records=json.loads((O/'icon_render_receipt.json').read_text()) if '--resume' in sys.argv or selected_parts else {}
jobs=[('ue_hk416','equipment',False),('ue_hk416_optic_false','factory_sights',True),
 ('ue_hk416_optic_holographic','holographic',True),('ue_hk416_muzzle_false','factory_barrel',True),
 ('ue_hk416_muzzle_true','suppressor',True),('ue_hk416_underbarrel_false','none',True),
 ('ue_hk416_underbarrel_vertical_foregrip','vertical',True),('ue_hk416_tactical_false','none',True),
 ('ue_hk416_tactical_laser','laser',True),('ue_hk416_tactical_flashlight','flashlight',True)]
if selected_parts:
    jobs=[job for job in jobs if job[1] in selected_parts]
    for key,_,_ in jobs:records.pop(key,None)
for key,part,gray in jobs:
    if key in records:continue
    if part=='equipment':
        # Equipment uses the actual UE assembly/materials and the inventory
        # aspect ratio. Refresh this export after changing the weapon assets.
        production=O.parent/'HK416InventoryIcon20261001/ue_hk416.png'
        if not production.exists():raise RuntimeError('Run HK416InventoryIcon20261001/export_icon.ps1 to author the equipment image')
        shutil.copy2(production,I/(key+'.png'));width,height=struct.unpack('>II',production.read_bytes()[16:24])
        records[key]={'file':str(I/(key+'.png')),'source':'UE ColdSteelWeaponIconCatalog current assembly','size':[width,height],'grayscale':False,'alpha':'transparent'}
        (O/'icon_render_receipt.json').write_text(json.dumps(records,indent=2));continue
    reset();objects,file=remove_symbol() if part=='none' else source(part)
    s,palette=scene(objects,(1,0,0),gray);s.render.filepath=str(I/(key+'.png'))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(SC/(key+'.blend')));bpy.ops.render.render(write_still=True)
    records[key]={'file':str(I/(key+'.png')),'scene':str(SC/(key+'.blend')),'source':file,'size':[1024,1024],'grayscale':gray,'alpha':'transparent','materials':palette}
    (O/'icon_render_receipt.json').write_text(json.dumps(records,indent=2));print('HK416_ICON_SAVED',key,flush=True)
for slot,representative in [('optic','optic_false'),('muzzle','muzzle_false'),('underbarrel','underbarrel_vertical_foregrip'),('tactical','tactical_laser')]:
    key='ue_hk416_category_'+slot;base='ue_hk416_'+representative
    if selected_parts and base not in {job[0] for job in jobs}:continue
    shutil.copy2(I/(base+'.png'),I/(key+'.png'));records[key]={**records[base],'file':str(I/(key+'.png')),'same_physical_part_as':base}
(O/'icon_render_receipt.json').write_text(json.dumps(records,indent=2));print('HK416_ICONS_COMPLETE',len(records),flush=True)
