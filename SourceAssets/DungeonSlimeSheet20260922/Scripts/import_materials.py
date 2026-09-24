"""Converging meniscus and a single drop origin. Puddle shape and gameplay stay intact."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
exec(compile((ROOT/'Scripts/material_helpers.py').read_text(),str(ROOT/'Scripts/material_helpers.py'),'exec'),globals())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End current play before material installation')
fluid=json.loads((ROOT/'Authored/fluids.json').read_text());fall=fluid['falltime']
def make(name):
    global mat
    path=BASE+'/Materials/'+name;mat=u.load_asset(path)
    if mat:
        save(mat)
        return False
    mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT);mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);mat.set_editor_property('tangent_space_normal',False);mat.set_editor_property('two_sided',True);mat.set_editor_property('screen_space_reflections',True)
    return True
def finish():
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat)
if make('M_PusConvergingSheet'):
    inputs={'UV':node('TextureCoordinate'),'T':node('Time')};shared=(ROOT/'Scripts/sheet_shape.hlsl').read_text()
    out(custom(shared+'return (shape.animated(UV,T)-shape.base(UV))*float3(1,-1,1);',inputs),'WORLD_POSITION_OFFSET')
    normal=custom(shared+'''float2 q=clamp(UV,float2(.001,.001),float2(.999,.999));
float3 du=shape.animated(q+float2(.001,0),T)-shape.animated(q-float2(.001,0),T);
float3 dv=shape.animated(q+float2(0,.001),T)-shape.animated(q-float2(0,.001),T);
float3 n=normalize(cross(dv,du));
// Subtle flowing ridges follow the convergence instead of three cylindrical highlights.
n.y+=sin(UV.x*48+UV.y*6-T*1.6)*.023;
return normalize(n)*float3(1,-1,1);''',inputs)
    out(normal,'NORMAL');out(custom('return lerp(float3(.075,.17,.023),float3(.13,.25,.044),UV.y*.45);',inputs),'BASE_COLOR')
    out(scalar('Roughness',.16),'ROUGHNESS');out(scalar('Specular',.47),'SPECULAR')
    out(custom('float edge=smoothstep(0,.045,UV.x)*(1-smoothstep(.955,1.,UV.x));return (.56+UV.y*.17)*edge;',inputs,1),'OPACITY');finish()
if make('M_PusConvergedDrops'):
    inputs={'UV':node('TextureCoordinate'),'Meta':node('VertexColor'),'T':node('Time'),'Fall':scalar('FallSeconds',fall)}
    shared='''struct Drop {
float3 position(float2 uv,float age,float size,float fall,float T) {
 float t=clamp(age-1.48,0,fall);float phase=uv.y*3.14159265;float phi=uv.x*6.2831853;
 float gather=.22+.78*smoothstep(.08,1.48,age);
 float r=.87*size*(age<1.48?gather:1);
 float radial=r*sin(phase)*(1-.16*cos(phase));
 float3 center=float3(.2+8.3*t/fall,.22*sin((T-t)*1.35),-11.2-r*.35-250*t*t);
 return center+float3(radial*cos(phi),radial*sin(phi),r*cos(phase)*(1.1+.45*t/fall));
}
float3 base(float2 uv){float a=uv.x*6.2831853;float b=uv.y*3.14159265;return float3(sin(b)*cos(a),sin(b)*sin(a),cos(b));}
};
Drop shape;float age=frac(T/2.35+Meta.r)*2.35;
'''
    out(custom(shared+'return (shape.position(UV,age,Meta.g,Fall,T)-shape.base(UV))*float3(1,-1,1);',inputs),'WORLD_POSITION_OFFSET')
    out(custom(shared+'''float2 q=float2(UV.x,clamp(UV.y,.002,.998));
float3 du=shape.position(q+float2(.001,0),age,Meta.g,Fall,T)-shape.position(q-float2(.001,0),age,Meta.g,Fall,T);
float3 dv=shape.position(q+float2(0,.001),age,Meta.g,Fall,T)-shape.position(q-float2(0,.001),age,Meta.g,Fall,T);
return normalize(cross(dv,du))*float3(1,-1,1);''',inputs),'NORMAL')
    out(custom('return float3(.095,.22,.036);',{}),'BASE_COLOR');out(scalar('Roughness',.13),'ROUGHNESS');out(scalar('Specular',.50),'SPECULAR')
    out(custom('float age=frac(T/2.35+Meta.r)*2.35;return (Meta.g>.9?1:step(1.48,age))*(1-step(1.48+Fall,age))*.80;',inputs,1),'OPACITY');finish()
path=BASE+'/Materials/M_PusSingleImpact';parent=u.load_asset(path)
if not parent:
    parent=E.duplicate_asset('/Game/Dungeons/CombatExpansionV3_20260922/Materials/M_PusRadialSurface',path)
parent.modify()
for e in L.get_material_expressions(parent):
    if not isinstance(e,u.MaterialExpressionCustom):continue
    code=e.get_editor_property('code')
    if 'float p1=dot(UV' not in code:continue
    code=code.replace('i<3','i<2').replace('i==0?0:(i==1?.37:.73)','i==0?0:.98').replace('float2 center=float2(0,i==0?0:(i==1?.035:-.028));','float2 center=float2(0,0);').replace('float hh=.20*env*Impact;','float hh=.20*env*Impact*(i==0?1:.25);')
    # Keep the existing radial puddle mesh. Its original exported V is world-local Y;
    # undo UE's FBX V flip in the wave formula to place impacts at the actual centre.
    if 'UV.y=1-UV.y;' not in code:code='UV.y=1-UV.y;\n'+code
    e.set_editor_property('code',code)
import sys
sys.path.insert(0,str(Path(u.Paths.project_dir())/'Tools/Fluids'))
from author_impact_smoke_corrosion import pool_surface
pool_surface(parent)
errors=L.recompile_material(parent)
if errors:raise RuntimeError(str(errors))
save(parent)
path=BASE+'/Materials/MI_PusPuddleSingleImpact';mi=u.load_asset(path) or E.duplicate_asset('/Game/Dungeons/CombatExpansionV3_20260922/Materials/MI_PusPuddleRadial',path)
mi.modify();L.set_material_instance_parent(mi,parent);L.set_material_instance_scalar_parameter_value(mi,'DropFallSeconds',fall);L.update_material_instance(mi);save(mi)
(ROOT/'Receipts/materials.json').write_text(json.dumps(dict(saved=saved,tests_run=False),indent=2));print('CONVERGING_MATERIALS_SAVED',len(saved))
