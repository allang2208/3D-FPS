import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V2=ROOT.parent/'DungeonCombatExpansion20260922';BASE='/Game/Dungeons/SlimeSheet20260922';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
saved=[]
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    saved.append(a.get_path_name())
def node(k):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+k))
def wire(src,dst,pin):
    if not L.connect_material_expressions(src,'',dst,pin):raise RuntimeError('Wire '+pin)
def out(n,p):
    if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError(p)
def scalar(name,v):
    n=node('ScalarParameter');n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',v);return n
def custom(code,inputs,width=3):
    n=node('Custom');n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));pins=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n
