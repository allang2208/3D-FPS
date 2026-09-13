#include "ProductionHarvestSubsystem.h"
#include "ProductionHarvestAssets.h"
#include "ProductionBreakEffect.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"

bool UProductionHarvestSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    const auto* World=Cast<UWorld>(Outer);
    return Super::ShouldCreateSubsystem(Outer)&&World&&(World->WorldType==EWorldType::Game||World->WorldType==EWorldType::PIE);
}
TStatId UProductionHarvestSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UProductionHarvestSubsystem,STATGROUP_Tickables); }
void UProductionHarvestSubsystem::Prepare(bool Wood)
{
    auto& Handle=Wood?WoodLoad:StoneLoad;
    if (!Handle) Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(ProductionHarvestAssets::LoadSet(Wood));
}
bool UProductionHarvestSubsystem::Ready(bool Wood) const
{
    const auto& Handle=Wood?WoodLoad:StoneLoad;
    return Handle&&Handle->HasLoadCompleted()&&ProductionHarvestAssets::PickupMesh(Wood?TEXT("wood"):TEXT("stone")).ResolveObject();
}
void UProductionHarvestSubsystem::DelayDrops(const TArray<FString>& Ids,float Delay)
{
    const double Time=GetWorld()->GetTimeSeconds()+Delay;
    for(const auto& Id:Ids) VisibleAfter.Add(Id,Time);
    ScanCountdown=0;
}
void UProductionHarvestSubsystem::Burst(bool Wood,const FVector& At,uint32 Seed,bool Landing)
{
    Effects.RemoveAll([](const auto& E){return !E.IsValid();});
    if(Effects.Num()>=2)return; // At most two effects and twelve cosmetic rigid bodies.
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Effect=GetWorld()->SpawnActor<AProductionBreakEffect>(At,FRotator::ZeroRotator,Spawn))
    { Effect->Start(Wood,Seed,Landing);Effects.Add(Effect); }
}
void UProductionHarvestSubsystem::Tick(float Delta)
{
    if(GetWorld()->GetNetMode()!=NM_Standalone)return;
    ScanCountdown-=Delta;if(ScanCountdown>0)return;ScanCountdown=.2f;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    if(!Profile||!Pawn)return;
    if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    if(!Hills.IsValid()||!Hills->bReady)return;
    const auto WorldId=Hills->WorldId;
    const FVector Eye=Pawn->GetActorLocation();
    const double Now=GetWorld()->GetTimeSeconds();
    for(auto It=VisibleAfter.CreateIterator();It;++It)if(It.Value()<=Now)It.RemoveCurrent();
    struct FCandidate {FString Id;double Distance;};
    TArray<FCandidate> Candidates;
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    for(const auto& Item:Profile->Items())
    {
        if(Item.Place!=2||Item.HarvestWorldId!=WorldId||Item.Map!=Map||VisibleAfter.Contains(Item.InstanceId))continue;
        const double Distance=FVector::DistSquared(Eye,Item.Position);
        if(Distance<FMath::Square(6400.))Candidates.Add({Item.InstanceId,Distance});
    }
    Candidates.Sort([](const auto& A,const auto& B){return A.Distance<B.Distance;});
    if(Candidates.Num()>40)Candidates.SetNum(40);
    TSet<FString> Wanted;for(const auto& C:Candidates)Wanted.Add(C.Id);
    int32 Removed=0;bool Synced=false;
    for(auto It=Pickups.CreateIterator();It;++It)
    {
        if(It.Value().IsValid()&&Wanted.Contains(It.Key()))continue;
        if(!Synced){Profile->SyncRuntime();Synced=true;}
        if(auto* Pickup=It.Value().Get())Pickup->Destroy();
        It.RemoveCurrent();if(++Removed>=2)break;
    }
    if(Pickups.Num()>=40)return;
    // At most one component/physics assembly per 0.2 s, nearest items first.
    for(const auto& Candidate:Candidates)
    {
        if(Pickups.Contains(Candidate.Id))continue;
        const auto* Item=Profile->FindItem(Candidate.Id);if(!Item)continue;
        const bool Wood=Item->Definition==TEXT("wood");Prepare(Wood);if(!Ready(Wood))continue;
        FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Pickup=GetWorld()->SpawnActor<AColdSteelPickup>(Item->Position,Item->WorldRotation,Spawn))
        {Pickup->InitializeItem(*Item);Pickups.Add(Candidate.Id,Pickup);}
        break;
    }
}
void UProductionHarvestSubsystem::Deinitialize()
{
    if(GetWorld()&&GetWorld()->GetGameInstance())
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->SyncRuntime();
    for(auto& Pair:Pickups)if(auto* Pickup=Pair.Value.Get())Pickup->Destroy();
    Pickups.Empty();VisibleAfter.Empty();Effects.Empty();
    if(WoodLoad)WoodLoad->CancelHandle();if(StoneLoad)StoneLoad->CancelHandle();
    WoodLoad.Reset();StoneLoad.Reset();
    Super::Deinitialize();
}
