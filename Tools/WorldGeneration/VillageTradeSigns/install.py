"""Author the store finishes and sign supports, then fit them to a private copy of the village."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent/p) for p in ('AbandonedVillage','VillageBlacksmith','VillageGunshop')]
from author_shop import require
from trade_sign_layout import MOUNTS, ROOT, JOINERY, apply
from ForgeR2 import surfaces as smith
from gunshop_shell_author import build_mesh
from gunshop_shell_geometry import Mesh, models

BATCH = Path(os.environ['VILLAGE_TRADE_SIGNS_BATCH'])
HOST = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if HOST != BATCH/'Host':
    raise RuntimeError('An isolated village authoring host is required')
SOURCE = PROJECT/'SourceAssets/HillsVillageTradeSigns'
LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
file = LEVEL.removeprefix('/Game/')+'.umap'
lib = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
api = u.AssetToolsHelpers.get_asset_tools()
packages = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(obj):
    if not lib.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    packages.append(obj.get_path_name().split('.')[0])


def create(name,cls,factory):
    path = ROOT+'/'+name
    return require(path) if lib.does_asset_exist(path) else api.create_asset(name,ROOT,cls,factory)


def finishes():
    parent = create('M_TradeSignOak',u.Material,u.MaterialFactoryNew())
    parent.modify()
    edit.delete_all_material_expressions(parent)
    color = edit.create_material_expression(parent,u.MaterialExpressionTextureSampleParameter2D)
    color.set_editor_property('parameter_name','PaintedFace')
    color.texture = require(smith.TEX+'Color')
    color.sampler_type = getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+
                                 ('VIRTUAL_' if color.texture.virtual_texture_streaming else '')+'COLOR')
    smith.prop(color,'RGB','BASE_COLOR')
    norm = smith.sample(parent,require(smith.TEX+'NormalDX'),'NORMAL')
    pack = smith.sample(parent,require(smith.TEX+'ORM'),'MASKS')
    fine = smith.sample(parent,require('/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_NormalDX'),'NORMAL')
    uv = edit.create_material_expression(parent,u.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('u_tiling',3.7)
    uv.set_editor_property('v_tiling',1.25)
    smith.wire(uv,'',fine,'UVs')
    relief = smith.custom(parent,'return normalize(float3(Main.xy + 0.22 * Fine.xy, max(0.18, Main.z)));',
                          [('Main',norm,'RGB'),('Fine',fine,'RGB')])
    smith.prop(relief,'','NORMAL')
    smith.prop(pack,'R','AMBIENT_OCCLUSION')
    smith.prop(pack,'G','ROUGHNESS')
    edit.layout_material_expressions(parent)
    edit.recompile_material(parent)
    save(parent)
    for shop in MOUNTS:
        name = 'T_'+shop+'Sign_Color'
        task = u.AssetImportTask()
        task.filename = str(SOURCE/(name+'.png'))
        task.destination_path = ROOT
        task.destination_name = name
        task.automated = task.replace_existing = True
        api.import_asset_tasks([task])
        tex = require(ROOT+'/'+name)
        tex.modify()
        tex.srgb = True
        if tex.virtual_texture_streaming != color.texture.virtual_texture_streaming:
            tex.set_editor_property('virtual_texture_streaming',color.texture.virtual_texture_streaming)
        tex.address_x = tex.address_y = u.TextureAddress.TA_CLAMP
        save(tex)
        mat = create('MI_'+shop+'Sign',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        mat.modify()
        edit.set_material_instance_parent(mat,parent)
        edit.set_material_instance_texture_parameter_value(mat,'PaintedFace',tex)
        if edit.get_material_instance_texture_parameter_value(mat,'PaintedFace') != tex:
            raise RuntimeError('Could not bind face for '+shop)
        save(mat)


def geometry(model,path,collision=None):
    dm,names,materials = build_mesh(model)
    opts = u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
        enable_recompute_tangents=True,enable_collision=bool(collision),enable_nanite=False)
    asset = lib.load_asset(path) if lib.does_asset_exist(path) else None
    if not asset:
        asset,result = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
        if result!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not create '+path)
    write = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        replace_materials=True,new_materials=materials,new_material_slot_names=names)
    _,result = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,asset,write,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not write '+path)
    if collision:
        body = asset.get_editor_property('body_setup')
        if collision=='post':
            box = u.KBoxElem()
            box.set_editor_property('center',u.Vector(0,0,138))
            for field,size in zip(('x','y','z'),(14.,14.,282.)):
                box.set_editor_property(field,size)
            agg = body.get_editor_property('agg_geom')
            agg.set_editor_property('box_elems',[box])
            body.set_editor_property('agg_geom',agg)
        else:
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(asset)


finishes()
ground = Mesh()
# The rear of each oak ground beds into irregular masonry, the front supports the iron plate.
ground.box('Oak',-7.8,7.8,.2,27,-39,8,1.2)
geometry(ground,ROOT+'/SM_TradeWallGround')
post = Mesh()
post.box('Oak',-7,7,-7,7,-12,287,.95)
post.prism('DarkWood',[(-8,-8,285),(8,-8,285),(8,-8,288),(0,-8,293),(-8,-8,288)],(0,16,0))
# A solid, double-sided arrow points along each lane above the smaller guild panel.
post.box('Oak',-3,3,-43,4,273,281,.55)
post.prism('Sawn',[(-3,-40,270),(-3,-54,277),(-3,-40,284)],(6,0,0))
geometry(post,ROOT+'/SM_TradeWaypost','post')
geometry(models()['StreetJoinery'],JOINERY,'joinery')

original = HOST/'Content'/file
before = digest(original)
backup = BATCH/'Before'/before/original.name
backup.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(original,backup)
world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError('Village map unavailable')
placements = apply(PROJECT)
if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):
    raise RuntimeError('Could not save fitted signs')
for relative in [pkg.removeprefix('/Game/')+'.uasset' for pkg in packages]+[file]:
    dest = BATCH/'Saved'/relative
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(HOST/'Content'/relative,dest)
receipt = dict(revision='WeatheredTradeSignsR1',level=LEVEL,packages=packages,placements=placements,
               source=str(SOURCE.resolve()),map_before=before,map_after=digest(original),before=str(backup))
(BATCH/'staged.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
