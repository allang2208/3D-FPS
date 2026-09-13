#include "ProductionHarvestSubsystem.h"
#include "ProductionHarvestAssets.h"
#include "ProductionBreakEffect.h"
#include "ProductionResource.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"

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
    if(!Handle||!Handle->HasLoadCompleted())return false;
    if(Wood)
        for(const auto& Path:ProductionHarvestAssets::LoadSet(true))if(!Path.ResolveObject())return false;
    return ProductionHarvestAssets::PickupMesh(Wood?TEXT("wood"):TEXT("stone")).ResolveObject()!=nullptr;
}
void UProductionHarvestSubsystem::PrepareFall(const FProductionResource& Resource)
{
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    if(Variant==INDEX_NONE)return;
    Prepare(true);
    if(!FallLoads[Variant])FallLoads[Variant]=UAssetManager::GetStreamableManager().RequestAsyncLoad(ProductionHarvestAssets::FallingMesh(Variant));
}
bool UProductionHarvestSubsystem::ReadyFall(const FProductionResource& Resource) const
{
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    return Variant!=INDEX_NONE&&FallLoads[Variant]&&FallLoads[Variant]->HasLoadCompleted()&&
        ProductionHarvestAssets::FallingMesh(Variant).ResolveObject()!=nullptr;
}
void UProductionHarvestSubsystem::ReleasePreparedFall(const FProductionResource& Resource)
{
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    if(Variant!=INDEX_NONE&&FallLoads[Variant])
    {FallLoads[Variant]->ReleaseHandle();FallLoads[Variant].Reset();}
}
void UProductionHarvestSubsystem::ShowStumpAtCut(const FProductionResource& Resource)
{
    Hills=Resource.World;bStumpsDirty=true;
    const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    // Run before removing the standing tree and spawning the upper section,
    // in the same game-thread operation instead of waiting for the stream tick.
    UpdateStumps(Pawn?Pawn->GetActorLocation():Resource.Transform.GetLocation(),GetWorld()->GetTimeSeconds());
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
    UpdateStumps(Eye,Now);
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
    for(auto& Component:Stumps)if(Component)Component->DestroyComponent();Stumps.Empty();
    if(WoodLoad)WoodLoad->CancelHandle();if(StoneLoad)StoneLoad->CancelHandle();
    WoodLoad.Reset();StoneLoad.Reset();
    for(auto& Handle:FallLoads){if(Handle)Handle->CancelHandle();Handle.Reset();}
    Super::Deinitialize();
}

void UProductionHarvestSubsystem::UpdateStumps(const FVector& Eye,double Now)
{
    if(Now<NextStumpRefresh&&!bStumpsDirty)return;
    NextStumpRefresh=Now+1;
    const FIntPoint Cell(FMath::FloorToInt(Eye.X/800),FMath::FloorToInt(Eye.Y/800));
    if(!bStumpsDirty&&Cell==StumpCell&&Stumps.Num()==4)return;
    Prepare(true);
    // Four small meshes cut from the four source trees. No hidden full-tree mesh.
    for(int32 Variant=0;Variant<4;++Variant)
        if(!ProductionHarvestAssets::Stump(Variant).ResolveObject())return;
    if(Stumps.IsEmpty())
    {
        for(int32 Variant=0;Variant<4;++Variant)
        {
            auto* Component=NewObject<UInstancedStaticMeshComponent>(Hills.Get(),FName(*FString::Printf(TEXT("OriginalStumps_%d"),Variant)));
            Hills->AddInstanceComponent(Component);
            Component->SetStaticMesh(Cast<UStaticMesh>(ProductionHarvestAssets::Stump(Variant).ResolveObject()));
            Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Component->SetCanEverAffectNavigation(false);Component->SetCullDistances(5200,6400);
            Component->SetMobility(EComponentMobility::Movable);Component->RegisterComponent();Stumps.Add(Component);
        }
    }
    TArray<FTemperatePlacement> Places;Hills->GetHarvestedStumps(FBox(Eye-FVector(6400,6400,50000),Eye+FVector(6400,6400,50000)),Places);
    Places.RemoveAll([&](const auto& P){return ProductionHarvestAssets::TreeVariant(P.Mesh)==INDEX_NONE||FVector::DistSquared2D(P.Transform.GetLocation(),Eye)>FMath::Square(6400.f);});
    Places.Sort([&](const auto& A,const auto& B){return FVector::DistSquared2D(A.Transform.GetLocation(),Eye)<FVector::DistSquared2D(B.Transform.GetLocation(),Eye);});
    if(Places.Num()>64)Places.SetNum(64);
    TArray<FTransform> Groups[4];
    for(const auto& Place:Places)Groups[ProductionHarvestAssets::TreeVariant(Place.Mesh)].Add(Place.Transform);
    for(int32 Variant=0;Variant<4;++Variant)
    {Stumps[Variant]->ClearInstances();Stumps[Variant]->AddInstances(Groups[Variant],false,true,false);}
    StumpCell=Cell;bStumpsDirty=false;
}
