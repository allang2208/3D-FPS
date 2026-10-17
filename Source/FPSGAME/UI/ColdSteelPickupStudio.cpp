#include "ColdSteelPickupStudio.h"
#include "FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"

void UColdSteelPickupStudio::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    IdleTicker=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateWeakLambda(this,[this](float)
    { ReleaseIdleRigs(); return true; }),1.f);
}

void UColdSteelPickupStudio::ReleaseIdleRigs(bool bEnteringDungeon)
{
    const double Now=FPlatformTime::Seconds();
    for(int32 Index=RigUseOrder.Num()-1;Index>=0;--Index)
    {
        const FString Key=RigUseOrder[Index];
        if(!bEnteringDungeon && Now-LastUseSeconds.FindRef(Key)<5.)continue;
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Pickup_ReleaseIdleRig);
        if(auto* Rig=Rigs.Find(Key);Rig&&IsValid(*Rig))(*Rig)->Destroy();
        Rigs.Remove(Key);LastUseSeconds.Remove(Key);RigUseOrder.RemoveAt(Index);
        // At most one retirement per idle tick. Keep the empty world shell:
        // FPreviewScene destruction forces a full GC in this engine.
        if(!bEnteringDungeon)break;
    }
    if(Rigs.IsEmpty()&&Studio)Studio->SuspendRendering();
}

FString UColdSteelPickupStudio::Key(const FColdSteelItem& Item) const
{
    const auto Parts=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(Item);
    TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();FString Result=Item.Definition;
    for(const auto& Name:Names)Result+=TEXT("|")+Name+TEXT("=")+Parts[Name];return Result;
}
AFPSGAMECharacter* UColdSteelPickupStudio::Acquire(const FString& Definition,bool& Created)
{
    Created=false;
    LastUseSeconds.Add(Definition,FPlatformTime::Seconds());
    if(auto* Existing=Rigs.Find(Definition);Existing&&IsValid(*Existing))
    {
        RigUseOrder.Remove(Definition);RigUseOrder.Add(Definition);
        return *Existing;
    }
    Rigs.Remove(Definition);RigUseOrder.Remove(Definition);
    while(RigUseOrder.Num()>=2)
    {
        const FString Retired=RigUseOrder[0];RigUseOrder.RemoveAt(0);
        if(auto* Old=Rigs.Find(Retired);Old&&IsValid(*Old))(*Old)->Destroy();
        Rigs.Remove(Retired);
        LastUseSeconds.Remove(Retired);
    }
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Pickup_CreateRig);
    FFPSPerformanceScope RigScope(GetGameInstance(),TEXT("Pickup.CreateRig"));
    if(!Studio)Studio=MakeUnique<FColdSteelPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetCreateDefaultLighting(false).SetForceMipsResident(false).AllowAudioPlayback(false));
    Studio->ResumeRendering();
    FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
    // SpawnActor can inherit another world's BeginPlay call depth. Mark the rig
    // before spawning so neither the character nor its components begin play.
    Spawn.bTemporaryEditorActor=true;
#endif
    auto* Rig=Studio->GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
    if(Rig){Rig->SetActorTickEnabled(false);Rig->SetActorEnableCollision(false);Rigs.Add(Definition,Rig);RigUseOrder.Add(Definition);Created=true;}return Rig;
}
void UColdSteelPickupStudio::Warm(const FColdSteelItem& Item, const FBox* PreparedBounds)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Pickup_Warm);
    FFPSPerformanceScope WarmScope(GetGameInstance(),TEXT("Pickup.Warm"));
    if(Item.Definition!=TEXT("ue_super90")&&Item.Definition!=TEXT("ue_m870")&&Item.Definition!=TEXT("ue_m4a1")&&Item.Definition!=TEXT("ue_hk416")&&Item.Definition!=TEXT("ue_akm")&&Item.Definition!=TEXT("ue_a762")&&Item.Definition!=TEXT("ue_lmg201")&&Item.Definition!=TEXT("ue_svd")&&Item.Definition!=TEXT("ue_pkm_lowpoly")&&Item.Definition!=TEXT("ue_qbz191")&&Item.Definition!=TEXT("ue_ash12")&&Item.Definition!=TEXT("ue_m16a2")&&Item.Definition!=TEXT("ue_m1911")&&Item.Definition!=TEXT("ue_g18")&&Item.Definition!=TEXT("ue_pit_viper2011")&&(Item.Definition!=TEXT("ue_dan_wesson715")&&Item.Definition!=TEXT("ue_rsh12")))return;
    if(Bounds.Contains(Key(Item)))return;
    // Icon assembly can supply the exact same visible-vertex bounds in pickup axes.
    // Keep rig/model prewarming, but avoid a second CPU skinning traversal.
    if(PreparedBounds && PreparedBounds->IsValid){
        if(Bounds.Num()>=64)Bounds.Empty();
        Bounds.Add(Key(Item),*PreparedBounds);
    }
    // The icon studio has already loaded this recipe. Prepare collision bounds before mouse release.
    // Acquire/build must initialize a new rig together, so only create the world here.
    if(!Studio)Studio=MakeUnique<FColdSteelPreviewScene>(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetCreateDefaultLighting(false).SetForceMipsResident(false).AllowAudioPlayback(false));
    Studio->ResumeRendering();
    FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;
#if WITH_EDITOR
    Spawn.bTemporaryEditorActor=true;
#endif
    auto* Preview=Studio->GetWorld()->SpawnActor<AColdSteelPickup>(Spawn);
    if(Preview){Preview->SetActorTickEnabled(false);Preview->BuildWeapon(Item,GetGameInstance());Preview->Destroy();}
}
void UColdSteelPickupStudio::Deinitialize()
{
    FTSTicker::GetCoreTicker().RemoveTicker(IdleTicker);
    for(auto& Pair:Rigs)if(IsValid(Pair.Value))Pair.Value->Destroy();
    Rigs.Empty();RigUseOrder.Empty();LastUseSeconds.Empty();Bounds.Empty();Studio.Reset();Super::Deinitialize();
}
