from pathlib import Path
import runpy
O=Path(__file__).parent
runpy.run_path(str(O.parent/'Checks/check_saved_assets.py'),init_globals={
    'ASSET_ROOT':'/Game/Weapons/SVCH/Refined20261018/R5','MESH_NAME':'SK_SVCH_Refined_R5',
    'MODEL_RECEIPT':O/'model_receipt_r5.json','REPORT_PATH':O/'saved_assets.json'})
