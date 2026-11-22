from pathlib import Path
import json,hashlib,os,tempfile

work=Path(__file__).resolve().parent
project=Path("D:/FPS3D/FPSGAME")
official=project/"Content"
host=work/"Host/Content"
stable=project/"SourceAssets/OneHandAxe20261101/BladeVariants20261102/HistoricalRecovery20261121"
historical=json.loads((work.parent/"NovemberFurtherRecovery/prior-missing.json").read_bytes())
worklist=json.loads((Path.home() / "FPSGAME-Recovery-20261120/NovemberRedevelopmentList/input.json").read_bytes())['rows']
rows={r[9]:r[0] for r in worklist if r[3]=="战术斧三种早期斧刃" and "_R2" in r[4]}
saved=json.loads((work/'r2-saved.json').read_bytes())
if len(rows)!=15 or sorted(p for s in saved.values() for p in s['packages'])!=sorted(rows):
    raise RuntimeError("Save receipts differ from requested R2 package list")
def publish(path,b):
    if path.exists() and path.read_bytes()==b: return
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
        tmp.write(b)
        src=Path(tmp.name)
    try:os.rename(src,path)
    except FileExistsError:
        if path.read_bytes()!=b:raise
    finally:src.unlink(missing_ok=True)
records=[]
pending=[]
for kind,s in saved.items():
    if Path(s['mesh_input']).parents[2]!=stable:raise ValueError('Reimport path is transient')
    inputs={Path(f).stem:f for f in [s['mesh_input'],*s['texture_inputs'].values()]}
    for pkg in s['packages']:
        row=historical[pkg]; rel=Path(row['path'])
        blob=(host/rel).read_bytes();dst=official/rel
        if dst.exists() and dst.read_bytes()!=blob:raise FileExistsError(dst)
        if blob[:4]!=bytes.fromhex("c1832a9e"):raise ValueError(pkg)
        rec=dict(id=rows[pkg],kind=kind,package=pkg,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),preloss_saved_hash=row['signature'],rebuilt_saved_hash=blob[24:44].hex())
        filepath=inputs.get(pkg.rsplit('/',1)[1])
        if filepath:
            rec.update(author_input=str(Path(filepath).relative_to(project)),source_md5=hashlib.md5(Path(filepath).read_bytes()).hexdigest(),preloss_source_md5=row['source_files'][0]['FileMD5'])
        if row['asset_class']=='StaticMesh':
            rec['note']='已照仓库 R2 配方重建网格并保存到旧包路径，FBX 与原导入记录的 MD5 不同。'
        elif row['asset_class']=='Material':
            rec['note']='已用战术斧原模块的材质配方重构，绑定本款 R2 的底色、法线和 ORM 贴图，旧包路径已补齐。'
        else:
            rec['note']='已按'+('旧 R2 烘焙配方' if kind=='SwiftCrescent' else 'R2 重建网格及与归档一致的原厂表面转印配置')+'重建贴图并保存到旧包路径。'
        records.append(rec);pending.append((dst,blob))
for dst,blob in pending:publish(dst,blob)
records.sort(key=lambda r:r['id'])
summary=dict(commit='ec0f9738',production_entries=['BladeVariants20261102/RebuildV2/author.py','OneHandAxe20261101/ModulesV1/import_modules.py','CrescentReferenceR4_20261104/FactoryFinish20261104/transfer_textures.py'],scope='Archived R2 assets, game catalog still selects R4/R5',original_v1='Pending per user. Original asset bodies unavailable. Historical hashes and destinations in Docs/Publication/Hatchet20261104/cleanup-manifest.json.',reconstruction='Geometry rebuilt with the archived R2 author. FoldedArc and HeavyCleaver use stock steel transfer with byte-identical archived transfer_config and surface_source, SwiftCrescent uses the original R2 bake recipe. Current source file hashes differ from historical import records.',source_mapping='Reimport FBX and PNG paths refer to the local project HistoricalRecovery20261121/R2 directory.',runtime_tested=False,packages=records)
payload=(json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode()
publish(stable/'recovery.json',payload)
publish(work/'installed.json',payload)
print('Published',len(records),'R2 packages;',len([r for r in records if r.get('source_md5') and r['source_md5']==r['preloss_source_md5']]),'identical historical input hashes')
