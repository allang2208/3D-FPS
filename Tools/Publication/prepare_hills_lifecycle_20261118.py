"""Publish owned implementations and additive integration hunks, not shared hosts."""
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Docs/Publication/HillsVillageLifecycle20261118'
records = []

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8-sig')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def copy_owned(rel, text=None):
    # Git stores these text artifacts with LF; hash the same bytes as a checkout.
    raw = (read(rel) if text is None else text).encode('utf-8')
    dest = OUT / 'Implementation' / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    records.append(dict(kind='implementation', target=rel, artifact=dest.relative_to(OUT).as_posix(), sha256=sha(raw)))

def between(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a)]

def patch(rel, removals):
    after = read(rel)
    before = after
    for part in removals:
        if not part or before.count(part) != 1:
            raise ValueError(f'Non-unique owned hunk: {rel}: {part[:100]!r}')
        before = before.replace(part, '', 1)
    body = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='a/'+rel, tofile='b/'+rel, n=0))
    dest = OUT / 'Integration' / (rel.replace('/', '__') + '.patch')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body.encode('utf-8'))
    records.append(dict(kind='additive_patch', target=rel, artifact=dest.relative_to(OUT).as_posix(),
        base_kind='current shared context with ONLY these additions removed; not a historical commit',
        base_sha256=sha(before.encode()), result_sha256=sha(after.encode()), sha256=sha(body.encode())))

def main():
    owned = [
        'Characters/FPSBodySpawnResources.cpp', 'Building/VoxelBuildPreparation.cpp',
        'Diagnostics/FPSGameSceneLifecycle.cpp', 'Diagnostics/FPSGameSceneLifecycle.h',
        'WorldGeneration/HillsNightAssets.cpp', 'WorldGeneration/HillsNightPersistence.cpp',
        'WorldGeneration/HillsNightRaidSave.h', 'WorldGeneration/HillsNightReplicationGate.cpp',
        'WorldGeneration/HillsNightReplicationGate.h',
        'Development/HillsNetLoadAudit.cpp', 'Development/HillsNetLoadAudit.h',
        'Development/HillsContinuityAudit.cpp', 'Development/HillsContinuityAudit.h',
        'Development/HillsContinuityHost.cpp', 'Development/HillsContinuitySupport.cpp',
        'Development/HillsContinuitySupport.h', 'Development/HillsVillageInteractionAudit.cpp',
        'Development/HillsVillageInteractionAudit.h',
    ]
    for rel in owned:
        copy_owned('Source/FPSGAME/'+rel)
    for rel in [
        'Plugins/FPSStandaloneRuntime/FPSStandaloneRuntime.uplugin',
        'Plugins/FPSStandaloneRuntime/Source/FPSStandaloneRuntime/FPSStandaloneRuntime.Build.cs',
        'Plugins/FPSStandaloneRuntime/Source/FPSStandaloneRuntime/Private/FPSStandaloneRuntime.cpp',
    ]:
        copy_owned(rel)

    rel='Source/FPSGAME/WorldGeneration/VillagePlantingDisplay.cpp'
    text=read(rel)
    # A parallel village foliage change is outside this publication.
    extra=between(text, '                // Thousands of ankle-high plants', '                AddInstanceComponent')
    copy_owned(rel,text.replace(extra,''))
    records[-1]['excluded_parallel_change']='Additional pass-2 shadow/distance-field policy'
    copy_owned('Source/FPSGAME/WorldGeneration/VillagePlantingDisplay.h')

    rel='Source/FPSGAME/Characters/FPSBodyAssetPreloader.h';s=read(rel)
    patch(rel,[between(s,'    /** Keep the actual native pawn bootstrap','    /** Diagnostics:'),
        '    UPROPERTY() TArray<TObjectPtr<UObject>> SpawnAssets;\n',
        '    TSet<TWeakObjectPtr<UClass>> CapturedSpawnClasses;\n'])
    patch('Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp',['    SpawnAssets.Reset(); CapturedSpawnClasses.Reset();\n'])
    patch('Source/FPSGAME/FPSGAMECharacter.cpp',[
        '#include "Characters/FPSBodyAssetPreloader.h"\n',
        '    if (auto* Resources = GetGameInstance()->GetSubsystem<UFPSBodyAssetPreloader>())\n        Resources->RetainSpawnAssets(this);\n'])
    patch('Source/FPSGAME/FPSGAME.cpp',[
        '#include "Diagnostics/FPSGameSceneLifecycle.h"\n',
        '        FFPSGameSceneLifecycle::Startup();\n','        FFPSGameSceneLifecycle::Shutdown();\n'])
    patch('Source/FPSGAME/Building/VoxelBuildComponent.h',[
        '    bool PreparePreviewAssets();\n','    TSharedPtr<struct FStreamableHandle> PreviewAssetHandle;\n',
        '    TSharedPtr<struct FStreamableHandle> SurfaceAssetHandle;\n','    bool bSurfaceAssetsRequested=false;\n'])
    patch('Source/FPSGAME/Building/VoxelBuildComponent.cpp',[
        '    if(!PreparePreviewAssets())return;\n',
        '    if(PreviewAssetHandle)PreviewAssetHandle->CancelHandle();\n    PreviewAssetHandle.Reset();\n    if(SurfaceAssetHandle)SurfaceAssetHandle->CancelHandle();\n    SurfaceAssetHandle.Reset();\n'])
    rel='Source/FPSGAME/Skills/PlayerSkillRenderPreparation.cpp';s=read(rel)
    patch(rel,['#include "RHIGlobals.h"\n',between(s,'    // Headless worlds still load assets','    if(CurrentAsset.Get()!=Asset)')])
    rel='Source/FPSGAME/WorldGeneration/HillsNavigationSystem.cpp';s=read(rel)
    patch(rel,[between(s,'    // Geometry gathering / completed-tile installation','\n}\n\nvoid UHillsNavigationSystem::RegisterInvoker')])
    rel='Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformRendering.cpp';s=read(rel)
    patch(rel,['#include "MaterialShared.h"\n','#include "RHIGlobals.h"\n',
        between(s,'bool UGrassDeformSubsystem::ArePassShadersReady() const','UTextureRenderTarget2D* UGrassDeformSubsystem::GetReadTarget'),
        between(s,'    // Canvas otherwise finishes pending shader maps synchronously','    UWorld* World = GetWorld();'),
        '    if (!ArePassShadersReady()) return;\n'])
    patch('Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformSubsystem.h',['    bool ArePassShadersReady() const;\n'])
    rel='Source/FPSGAME/Monsters/WildlifeSubsystem.cpp';s=read(rel)
    patch(rel,['#include "HillsWildlifeAudio.h"\n',
        between(s,'            // The native audio component\'s soft paths','            if(GetWorld()->GetNetMode()!=NM_Client)'),
        '    AmbientAudioLoads.Reset();\n',
        '    if(const auto* Audio=AmbientAudioLoads.Find(Row.Id);Audio&&*Audio&&!(*Audio)->HasLoadCompleted())return false;\n'])
    patch('Source/FPSGAME/Monsters/WildlifeSubsystem.h',['    TMap<FString,TSharedPtr<FStreamableHandle>> AmbientAudioLoads;\n'])
    rel='Source/FPSGAME/Monsters/HillsWildlifeAudio.cpp';s=read(rel)
    dest=OUT/'Integration/HillsWildlifeAudioManifest.fragment.cpp'
    dest.write_text(between(s,'    void AppendTakes(', '    USoundWave* Choose(')+'\n'+
        between(s,'TArray<FSoftObjectPath> UHillsWildlifeAudio::AssetPaths','UHillsWildlifeAudio::UHillsWildlifeAudio()').rstrip()+'\n',encoding='utf-8',newline='\n')
    records.append(dict(kind='method_replacement',target=rel,artifact=dest.relative_to(OUT).as_posix(),sha256=sha(dest.read_bytes()),
        instructions='Place AppendTakes/LoadTakes in existing anonymous namespace; add AssetPaths static declaration to HillsWildlifeAudio.h. Preserve existing playback/RPC methods.'))
    patch('Source/FPSGAME/NPC/VillageBlacksmithResident.h',['    FTimerHandle AppearanceRetryTimer;\n'])
    rel='Source/FPSGAME/NPC/VillageBlacksmithResident.cpp';s=read(rel)
    patch(rel,[between(s,'    // Package completion is earlier than skeletal compilation','    VillageBlacksmithAssets::Appearance.Dress('),
        '    GetWorldTimerManager().ClearTimer(AppearanceRetryTimer);\n'])
    patch('Source/FPSGAME/WorldGeneration/TemperateHillsStreamingPrivate.h',[
        '    TSharedPtr<FStreamableHandle> SmithAppearance;\n','    bool EntryCleanupRequested=false;\n','    double EntryCleanupGCTime=0;\n'])
    rel='Source/FPSGAME/WorldGeneration/TemperateHillsStreamingPreparation.cpp';s=read(rel)
    patch(rel,[
        '    if(bVillageBlacksmithRepaired && !S.SmithAppearance)\n        S.SmithAppearance=UAssetManager::GetStreamableManager().RequestAsyncLoad(AVillageBlacksmithResident::AppearancePaths());\n',
        '    if(bVillageBlacksmithRepaired && !ResidentReady(S.SmithAppearance, AVillageBlacksmithResident::AppearancePaths,\n        AVillageBlacksmithResident::IsAppearanceCompilationPending)) return;\n',
        between(s,'    // Discard initial load/assembly transients','    bReady=true;S.NextVegetationFrontierTime=0;')])
    # Preserve the shared helper's contract as a fragment, without the other NPC's use.
    dest=OUT/'Integration/SmithReadiness.fragment.cpp'
    dest.write_text(between(s,'    const auto ResidentReady =','    if(bVillageBlacksmithRepaired && !ResidentReady'),encoding='utf-8',newline='\n')
    records.append(dict(kind='shared_helper_contract',target=rel,artifact=dest.relative_to(OUT).as_posix(),sha256=sha(dest.read_bytes())))
    patch('Source/FPSGAME/Monsters/NurseZombie.h',[
        '    virtual bool IsNetRelevantFor(const AActor* RealViewer,const AActor* ViewTarget,const FVector& SrcLocation) const override;\n'])
    patch('Source/FPSGAME/Monsters/MonsterCombatComponent.h',[
        ' static FSoftObjectPath DefaultStunAnimationPath(const FString& Role);\n'])
    s=read('Source/FPSGAME/Monsters/MonsterStunPresentation.cpp')
    dest=OUT/'Integration/MonsterStunSharedManifest.fragment.cpp'
    dest.write_text(between(s,'FSoftObjectPath UMonsterCombatComponent::DefaultStunAnimationPath',
        'void UMonsterCombatComponent::LoadHumanoidStun()')+'\n// Replace only the existing !DizzyClip branch inside LoadHumanoidStun.\n'+
        between(s,'    if(!DizzyClip)\n','    if(DizzyClip &&'),encoding='utf-8',newline='\n')
    records.append(dict(kind='method_replacement',target='Source/FPSGAME/Monsters/MonsterStunPresentation.cpp',artifact=dest.relative_to(OUT).as_posix(),sha256=sha(dest.read_bytes())))
    s=read('Source/FPSGAME/WorldGeneration/HillsNightPortal.cpp')
    dest=OUT/'Integration/PortalAssetManifest.fragment.cpp'
    dest.write_text(between(s,'void AHillsNightPortal::AddAssetPaths','double AHillsNightPortal::ServerTime')+
        '\n// BeginPlay requests this manifest; keep the existing callback and visual setup.\n'+
        'TArray<FSoftObjectPath> Paths;AddAssetPaths(Paths);\n',encoding='utf-8',newline='\n')
    records.append(dict(kind='method_replacement',target='Source/FPSGAME/WorldGeneration/HillsNightPortal.cpp',artifact=dest.relative_to(OUT).as_posix(),sha256=sha(dest.read_bytes())))
    patch('Source/FPSGAME/WorldGeneration/HillsNightPortal.h',['    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);\n'])
    (OUT/'integration-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print('Prepared',len(records),'owned implementation / integration artifacts')

if __name__=='__main__':
    main()
