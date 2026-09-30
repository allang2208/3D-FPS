"""Retire only the 201 box feed; preserve PKM and other weapon branches."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parents[3];O=Path(__file__).parent
def edit(relative,fn):
 p=P/relative;t=p.read_text(encoding='utf-8-sig');new=fn(t)
 if new==t:return
 b=O/'BeforeCode'/relative;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():shutil.copy2(p,b)
 p.write_text(new,encoding='utf8')
def header(t):
 t=t.replace('inline constexpr const TCHAR* AmmoBoxId=TEXT("lmg201_ammo_box");\n','')
 a=t.index('    // Reload11');b=t.index('    return FString::Printf',t.index('Clip,Clip);',a))
 t=t[:a]+t[b:]
 a=t.index('// The accepted PKM donor');b=t.index('inline FString PartPath',a)
 t=t[:a]+'''// The 201 now uses only its factory magazine. Retired feed props stay hidden
// in game, inventory and gunsmith previews, including legacy saved loadouts.
inline void SetMagazineSections(USkeletalMeshComponent* Mesh,int32& CachedVisibility)
{
    if(!Matches(Mesh)||CachedVisibility==1)return;
    const auto* Asset=Mesh->GetSkeletalMeshAsset();
    const auto* Render=Asset->GetResourceForRendering();
    if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString();
            if(Name.StartsWith(TEXT("M_LMG201_Magazine")))Mesh->ShowMaterialSection(M,S,true,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Feed__")))Mesh->ShowMaterialSection(M,S,false,L);
        }
    CachedVisibility=1;
}
'''+t[b:];return t
edit('Source/FPSGAME/Weapons/LMG201WeaponAssets.h',header)
def character(t):
 t=t.replace('    bLMG201BeltVisual=bLMG201BeltInstalled=false;\n','').replace('    BeltReloadAnimation=BeltReloadEmptyAnimation=nullptr;\n','')
 t=t.replace('    if(LMG201WeaponAssets::Matches(AKMViewmodel))\n    {\n        BeltReloadAnimation=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::AnimationPath(TEXT("reload_belt")));\n        BeltReloadEmptyAnimation=LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::AnimationPath(TEXT("reload_belt_empty")));\n    }\n','')
 t=t.replace('    if(bLMG201BeltInstalled)Animation=bPendingEmptyReload?BeltReloadEmptyAnimation:BeltReloadAnimation;\n','')
 t=t.replace('LMG201WeaponAssets::SetFeedSections(AKMViewmodel,false,false,false,0.f,30,LMG201FeedVisibility);','LMG201WeaponAssets::SetMagazineSections(AKMViewmodel,LMG201FeedVisibility);')
 t=t.replace('LMG201WeaponAssets::SetFeedSections(AKMViewmodel,bLMG201BeltVisual,IsReloading(),bPendingEmptyReload,\n        IsReloading()?ReloadSourceTime(WeaponStateElapsed):0.f,bGunsmithInspection?100:MagazineAmmo,LMG201FeedVisibility);','LMG201WeaponAssets::SetMagazineSections(AKMViewmodel,LMG201FeedVisibility);')
 t=t.replace('    // Keep the PKM-derived 201 reload intact; move the complete gun/arms assembly\n    // farther from the camera and lower it through the existing action framing.\n    const FVector ActionLocation = M4ActionViewmodelLocation\n        + ((bLMG201BeltInstalled && IsReloading()) ? FVector(18.f, 0.f, -12.f) : FVector::ZeroVector);','    const FVector ActionLocation = M4ActionViewmodelLocation;')
 t=t.replace(' || (bLMG201BeltInstalled && IsReloading())','').replace(' || bLMG201BeltInstalled','')
 return t
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda t:'\n'.join(l for l in t.split('\n') if not any(k in l for k in ['bLMG201BeltVisual','bLMG201BeltInstalled','BeltReloadAnimation','BeltReloadEmptyAnimation'])))
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp',lambda t:t.replace('        bLMG201BeltInstalled=bInventoryWeaponReady && Definition==LMG201WeaponAssets::Definition\n            && Parts.FindRef(TEXT("magazine"))==LMG201WeaponAssets::AmmoBoxId;\n',''))
def reload(t):
 a=t.index('    if(bLMG201BeltInstalled)');b=t.index('    bReloadCycleOnly=',a);t=t[:a]+t[b:]
 return t.replace(' && !bLMG201BeltInstalled','').replace('||bLMG201BeltInstalled','').replace(' || bLMG201BeltInstalled','')
edit('Source/FPSGAME/FPSGAMECharacterReload.cpp',reload)
edit('Source/FPSGAME/Weapons/M4DrumVisual.cpp',lambda t:t.replace('        bLMG201BeltVisual=bInventoryWeaponReady && Id==LMG201WeaponAssets::AmmoBoxId;\n        MagazineAttachmentId=bLMG201BeltVisual?Id:FString();','        MagazineAttachmentId.Reset();').replace('LMG201WeaponAssets::SetFeedSections(AKMViewmodel,bLMG201BeltVisual,false,false,0.f,100,LMG201FeedVisibility);','LMG201WeaponAssets::SetMagazineSections(AKMViewmodel,LMG201FeedVisibility);'))
edit('Source/FPSGAME/Weapons/LMG201Attachments.h',lambda t:t.replace('// Both feed systems retain their own source clocks and mechanical tracks.','// Factory magazine only; retired belt animations are never loaded.').replace(',TEXT("reload_belt"),TEXT("reload_belt_empty")',''))
def catalog(t):
 pos=t.index('"id": "ue_lmg201"');start=t.rfind('{',0,pos);w,length=json.JSONDecoder().raw_decode(t[start:]);indent=t[t.rfind('\n',0,start)+1:start]
 w['allowed']=[k for k in w['allowed'] if k!='magazine'];w['options'].pop('magazine',None)
 for trait in w.get('traits',[]):
  if '100发弹药箱' in trait.get('text',''):trait['text']='全自动射击，使用5.8毫米弹药；配备原厂30发弹匣。'
 return t[:start]+json.dumps(w,ensure_ascii=False,indent=2).replace('\n','\n'+indent)+t[start+length:]
edit('Content/ColdSteelData/gunsmith.json',catalog)
print('201 box feed removed from catalog, presentation and runtime routing')
