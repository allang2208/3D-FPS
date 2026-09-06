 # Evaluated in each semantic material, baked in rest-world centimetres.
 rough_output=scalar.outputs[0]
 geo=node(nt,'ShaderNodeNewGeometry','Anatomical rest position')
 def math_node(operation,a,b=None,name='Surface mask'):
  n=node(nt,'ShaderNodeMath',name);n.operation=operation
  if isinstance(a,(int,float)):n.inputs[0].default_value=a
  else:nt.links.new(a,n.inputs[0])
  if b is not None:
   if isinstance(b,(int,float)):n.inputs[1].default_value=b
   else:nt.links.new(b,n.inputs[1])
  return n.outputs[0]
 def patch(center,radius,label):
  sub=node(nt,'ShaderNodeVectorMath',label+' position');sub.operation='SUBTRACT';nt.links.new(geo.outputs['Position'],sub.inputs[0]);sub.inputs[1].default_value=center
  div=node(nt,'ShaderNodeVectorMath',label+' shape');div.operation='DIVIDE';nt.links.new(sub.outputs[0],div.inputs[0]);div.inputs[1].default_value=radius
  length=node(nt,'ShaderNodeVectorMath',label+' distance');length.operation='LENGTH';nt.links.new(div.outputs[0],length.inputs[0])
  edge=noise(nt,geo.outputs['Position'],1.7,label+' irregular edge')
  distance=math_node('ADD',length.outputs['Value'],math_node('MULTIPLY',edge,.23))
  fade=node(nt,'ShaderNodeMapRange',label+' feather');fade.interpolation_type='SMOOTHERSTEP';nt.links.new(distance,fade.inputs['Value'])
  fade.inputs['From Min'].default_value=.62;fade.inputs['From Max'].default_value=1.13;fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=0
  return fade.outputs[0]
 def mix_color(factor,base_color,added,label):
  mix=node(nt,'ShaderNodeMixRGB',label);mix.blend_type='MIX';nt.links.new(factor,mix.inputs[0]);nt.links.new(base_color,mix.inputs[1]);mix.inputs[2].default_value=(*added,1)
  return mix.outputs[0]
 if region=='Skin':
  wound=patch((71,-.5,137),(4,4,1.8),'Hand abrasion')
  if VARIANT=='runner':
   wound=math_node('MAXIMUM',wound,patch((29,-1,137),(5.5,3,4.2),'Exposed shoulder injury'))
   wound=math_node('MAXIMUM',wound,patch((-49,-1.5,136),(5.0,3.5,2.0),'Forearm injury'))
  color=mix_color(wound,color,(.09,.012,.013),'Abraded skin')
  rough_output=math_node('SUBTRACT',rough_output,math_node('MULTIPLY',wound,.18))
  injury_bump=node(nt,'ShaderNodeBump','Shallow wound depression');injury_bump.invert=True;injury_bump.inputs['Distance'].default_value=.07;injury_bump.inputs['Strength'].default_value=.40
  nt.links.new(wound,injury_bump.inputs['Height']);nt.links.new(bump.outputs[0],injury_bump.inputs['Normal']);nt.links.new(injury_bump.outputs[0],bs.inputs['Normal'])
 if region in ['Shirt','Trousers']:
  # Crossed weave has lower relief than clothing folds in the mesh.
  weave=[]
  for axis in ['X','Z']:
   wv=node(nt,'ShaderNodeTexWave','Woven yarn '+axis);wv.wave_type='BANDS';wv.bands_direction=axis;wv.inputs['Scale'].default_value=22;wv.inputs['Distortion'].default_value=1.2;nt.links.new(coord.outputs['Object'],wv.inputs['Vector']);weave.append(wv.outputs['Fac'])
  yarn=math_node('MULTIPLY',weave[0],weave[1])
  weave_bump=node(nt,'ShaderNodeBump','Cloth weave relief');weave_bump.inputs['Distance'].default_value=.018;weave_bump.inputs['Strength'].default_value=.20
  nt.links.new(yarn,weave_bump.inputs['Height']);nt.links.new(bump.outputs[0],weave_bump.inputs['Normal']);nt.links.new(weave_bump.outputs[0],bs.inputs['Normal'])
  dirt=noise(nt,geo.outputs['Position'],.65,'Small irregular grime')
  color=mix_color(math_node('MULTIPLY',dirt,.22),color,(.012,.010,.008),'Embedded dust')
  stains=patch((10,-7,111),(4.5,5,12),'Chest blood stain') if region=='Shirt' else patch((-13,-3,51),(4.4,6,9),'Knee dirt')
  color=mix_color(math_node('MULTIPLY',stains,.75),color,(.065,.012,.009) if region=='Shirt' else (.024,.018,.011),'Irregular cloth staining')
 nt.links.new(color,bs.inputs['Base Color']);nt.links.new(rough_output,bs.inputs['Roughness'])
