#include "HillsNightRaidSubsystem.h"
#include "HillsNightPortal.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/HumanoidKnockdownComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/NetDriver.h"
#include "Engine/PackageMapClient.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"

namespace HillsRaidAssets
{
const TCHAR* NurseClass=TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C");
void Paths(TArray<FSoftObjectPath>& Out)
{
    AHillsNightPortal::AddAssetPaths(Out);Out.Emplace(NurseClass);
    // FatZombie's native CDO and BeginPlay use these hard references. Include
    // them in the shared request, before accessing defaults or spawning a wave.
    Out.Emplace(TEXT("/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.SK_FatZombie_Meshy"));
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Attack"),TEXT("Death"),TEXT("Stagger")})
        Out.Emplace(FString::Printf(TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_%s.A_FatZombie_%s"),Clip,Clip));
    Out.Emplace(TEXT("/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C"));
    // These component defaults are runtime soft loads, not dependencies of the
    // monster Blueprint. Include the same manifests used by BeginPlay so both
    // first spawn and an existing-wave join avoid synchronous animation loads.
    for(const TCHAR* Role:{TEXT("Nurse"),TEXT("FatZombie")})
    {
        Out.Append(UHumanoidKnockdownComponent::DefaultAnimationPaths(Role));
        Out.Add(UMonsterCombatComponent::DefaultStunAnimationPath(Role));
    }
}
}

void UHillsNightRaidSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if(!bEnabled)return;
    // LoadMap attaches the listen/pending driver before world BeginPlay and
    // before its first actor replication tick. Both endpoints must opt in: the
    // server exports MustBeMapped GUIDs, the client queues those actor bunches
    // while packages load. This closes the existing-wave late-join race.
    if(auto* Driver=InWorld.GetNetDriver();Driver&&Driver->GuidCache.IsValid())
    {
        PreparedNetCache=Driver->GuidCache;PreviousNetLoadMode=uint8(Driver->GuidCache->AsyncLoadMode);
        Driver->GuidCache->SetAsyncLoadMode(FNetGUIDCache::EAsyncLoadMode::ForceEnable);
        UE_LOG(LogTemp,Display,TEXT("HILLS_RAID async network loading enabled mode=%d"),int32(InWorld.GetNetMode()));
    }
    PrepareAssets();
}

void UHillsNightRaidSubsystem::ReleaseNetworkLoadingPolicy()
{
    // Do not change the process-wide CVar or overwrite a later owner's policy.
    if(auto Cache=PreparedNetCache.Pin();Cache&&Cache->AsyncLoadMode==FNetGUIDCache::EAsyncLoadMode::ForceEnable)
        Cache->SetAsyncLoadMode(FNetGUIDCache::EAsyncLoadMode(PreviousNetLoadMode));
    PreparedNetCache.Reset();
}

void UHillsNightRaidSubsystem::PrepareAssets()
{
    if(bAssetsReady||bAssetPreparationFailed)return;
    if(Preload&&!Preload->WasCanceled())
    {
        // Package completion is not skeletal compilation completion.
        // Poll the existing request; never flush async work or reload it per tick.
        if(Preload->HasLoadCompleted())AssetsReady();
        return;
    }
    const double Now=GetWorld()->GetTimeSeconds();if(Now<NextAssetAttempt)return;
    NextAssetAttempt=Now+30.;Preload.Reset();
    TArray<FSoftObjectPath> Requested;HillsRaidAssets::Paths(Requested);
    Preload=UAssetManager::GetStreamableManager().RequestAsyncLoad(Requested,
        FStreamableDelegate::CreateUObject(this,&UHillsNightRaidSubsystem::AssetsReady));
}

void UHillsNightRaidSubsystem::AssetsReady()
{
    if(bAssetsReady||bAssetPreparationFailed)return;
    auto Failed=[this](const FString& Asset)
    {
        ++AssetLoadFailures;Preload.Reset();bAssetPreparationFailed=AssetLoadFailures>=3;
        UE_LOG(LogTemp,Error,TEXT("HILLS_RAID resource preparation failed asset=%s attempt=%d"),*Asset,AssetLoadFailures);
    };
    TArray<FSoftObjectPath> Requested;HillsRaidAssets::Paths(Requested);
    for(const auto& Path:Requested)if(!Path.ResolveObject()){Failed(Path.ToString());return;}
    UClass* Nurse=Cast<UClass>(FSoftObjectPath(HillsRaidAssets::NurseClass).ResolveObject());
    if(!Nurse||!Nurse->IsChildOf(ANurseZombie::StaticClass())){Failed(HillsRaidAssets::NurseClass);return;}
    for(UClass* Type:{Nurse,AFatZombie::StaticClass()})
    {
        const auto* Defaults=Type->GetDefaultObject<ANurseZombie>();
        const auto* Mesh=Defaults?(Defaults->VisualMesh?Defaults->VisualMesh.Get():Defaults->GetMesh()->GetSkeletalMeshAsset()):nullptr;
        if(!Mesh||!Defaults->IdleClip||!Defaults->WalkClip||!Defaults->AttackClip)
        {Failed(Type->GetPathName());return;}
        if(Mesh->IsCompiling())return;
    }
    MonsterClasses={Nurse,AFatZombie::StaticClass()};bAssetsReady=true;
    // Retain the successful handle for the entire hills session, not just until
    // entry. GC must not turn a later sunset into another cold network load.
    UE_LOG(LogTemp,Display,TEXT("HILLS_RAID resources ready mode=%d"),int32(GetWorld()->GetNetMode()));
}
