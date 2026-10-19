"""Deploy approved-master ImageGen icons; keep common option artwork shared."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
ARCHIVE=ROOT/'trash/zhanmadao-icons-v1-20261018';ARCHIVE.mkdir(parents=True,exist_ok=True)
def retain(path):
    if not path.exists():return
    rel=path.resolve().relative_to(ROOT.resolve());dst=ARCHIVE/rel
    if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)
    return {'old_path':str(path),'archive':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}
def deploy():
    jobs=[];retired=[]
    for slot in ['blade_1','guard','grip','pommel']:
        source=P/'Icons'/(slot+'_factory_framed_v2.png')
        if not source.exists():raise RuntimeError('Missing generated icon: '+str(source))
        # This source location is also consumed by the original asset importer.
        retained=retain(P.parent/'Icons'/(slot+'.png'))
        if retained:retired.append(retained)
        shutil.copy2(source,P.parent/'Icons'/(slot+'.png'))
        for key in ['ue_zhanmadao_'+slot+'_false','ue_zhanmadao_category_'+slot]:
            target=D/(key+'.png')
            for path in [target,target.with_suffix('.uasset')]:
                retained=retain(path)
                if retained:retired.append(retained)
            shutil.copy2(source,target)
            jobs.append({'key':key,'source':str(source),'file':str(target),'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+key})
    # The empty rune option is a shared neutral removal symbol. It has no
    # physical original module and must not fall back to an unrelated sword.
    source=D/'rune_false.png';target=D/'blade_2_false.png'
    if not target.exists():shutil.copy2(source,target)
    jobs.append({'key':'blade_2_false','source':str(source),'file':str(target),'asset':'/Game/ColdSteelData/AttachmentIcons20260913/blade_2_false'})
    (P/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ARCHIVE/'retirement_manifest.json').write_text(json.dumps({'replacement_root':str(P/'Icons'),'files':retired},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return jobs
if __name__=='__main__':deploy()
