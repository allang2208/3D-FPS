"""Install changed segment geometry while reusing unchanged surface textures."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921/Scripts/import_natural_segment.py',
    init_globals={'NATURAL_SKIP_TEXTURE_IMPORT':True},run_name='__main__')
