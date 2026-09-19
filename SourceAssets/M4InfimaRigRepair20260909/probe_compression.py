import unreal
s=unreal.load_asset('/ACLPlugin/ACLAnimBoneCompressionSettings')
for c in s.get_editor_property('codecs'):
    unreal.log('CODEC '+str(c)+' '+str(dir(c)))
    for p in ['ErrorThreshold','error_threshold','OptimizationTargets','DefaultVirtualVertexDistance','Precision']:
        try:unreal.log('PROPERTY '+p+' '+str(c.get_editor_property(p)))
        except Exception as e:unreal.log('PROPERTY_FAIL '+p+' '+str(e))
for n in ['AnimCompress_BitwiseCompressOnly','AnimBoneCompressionCodec_ACL','AnimBoneCompressionCodec_ACLSafe','AnimBoneCompressionCodec_UniformlySampled','AnimCompressionType']:
    cls=getattr(unreal,n,None);unreal.log('CLASS '+n+' '+str(cls)+' '+str(cls.__doc__ if cls else ''))
