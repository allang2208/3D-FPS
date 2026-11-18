"""Bind actual PBR inputs; save the barrel HISM usage fix and the painted sign material."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6'
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/DetailR6'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active PIE; exit play before R6 asset writes')
def get(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing '+path)
 return obj
def save(obj):
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save '+obj.get_path_name())
barrel=get('/Game/Props/CastingStation20260926/RealismV5/M_OakBarrel')
barrel.set_editor_property('used_with_instanced_static_meshes',True);L.recompile_material(barrel);save(barrel)
path=DEST+'/Textures/T_BlacksmithBrushPaint'
if not E.does_asset_exist(path):
 task=u.AssetImportTask();task.filename=str(OUT/'Textures/BlacksmithBrushPaint.png')
 task.destination_path=DEST+'/Textures';task.destination_name='T_BlacksmithBrushPaint';task.automated=True;task.replace_existing=False
 A.import_asset_tasks([task])
paint=get(path);paint.srgb=True;paint.compression_settings=u.TextureCompressionSettings.TC_DEFAULT
paint.address_x=paint.address_y=u.TextureAddress.TA_CLAMP;paint.max_texture_size=2048;save(paint)
path=DEST+'/Materials/M_BlacksmithBrushSign'
mat=get(path) if E.does_asset_exist(path) else A.create_asset('M_BlacksmithBrushSign',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
mat.set_editor_property('used_with_instanced_static_meshes',True)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
def node(kind):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
def link(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material pin '+pin)
def prop(a,out,name):
 if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Material property '+name)
def tex(path,kind='COLOR',uv=None):
 t=node('TextureSample');t.texture=get(path);t.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
 if uv:link(uv,'',t,'UVs')
 return t
prefix='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
wood=tex(prefix+'Color');normal=tex(prefix+'NormalDX','NORMAL');packed=tex(prefix+'ARH','MASKS')
unique=node('TextureCoordinate');unique.coordinate_index=1
mark=tex(paint.get_path_name(),'COLOR',unique)
blend=node('LinearInterpolate');link(wood,'RGB',blend,'A');link(mark,'RGB',blend,'B');link(mark,'A',blend,'Alpha')
prop(blend,'', 'BASE_COLOR');prop(normal,'RGB','NORMAL');prop(packed,'G','ROUGHNESS');prop(packed,'R','AMBIENT_OCCLUSION')
L.recompile_material(mat);save(mat)
(OUT/'materials-saved.json').write_text(json.dumps({'barrel_material':barrel.get_path_name(),'barrel_hism_usage':True,'sign_material':mat.get_path_name(),'paint':paint.get_path_name(),'paint_mode':'local UV1 alpha into opaque wood PBR; no decal projection'},indent=2),encoding='utf-8')
u.log('SMITH_R6_MATERIALS_SAVED')
