#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelPlayerState.h"
#include "ColdSteelAuthorityContext.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../Building/VoxelBuildWorld.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "UObject/UObjectIterator.h"

namespace
{
// The same two-centimetre tolerance as the authority instance match. Index XY because
// the standing trunk proxy and its tree can have different pivot heights.
struct FRemovalPoints
{
    TMultiMap<FIntPoint,FVector> Cells;
    static FIntPoint Cell(double X,double Y)
    {
        return {FMath::FloorToInt32(X/256.),FMath::FloorToInt32(Y/256.)};
    }
    void Add(const FVector& P)
    {
        const auto Min=Cell(P.X-2.,P.Y-2.),Max=Cell(P.X+2.,P.Y+2.);
        for(int32 X=Min.X;X<=Max.X;++X)
            for(int32 Y=Min.Y;Y<=Max.Y;++Y)Cells.Add({X,Y},P);
    }
    bool Matches(const FVector& P,bool bCheckHeight) const
    {
        for(auto It=Cells.CreateConstKeyIterator(Cell(P.X,P.Y));It;++It)
            if((bCheckHeight?FVector::DistSquared(P,It.Value()):FVector::DistSquared2D(P,It.Value()))<4.)return true;
        return false;
    }
};
}

void UColdSteelSharedInventorySubsystem::CopyHarvest(const FColdSteelProfile& From,FColdSteelProfile& To)
{
    To.HarvestProgress=From.HarvestProgress;To.TreeHealth=From.TreeHealth;To.RockHealth=From.RockHealth;
    To.TreeGrowth=From.TreeGrowth;To.TreeGrowthVersion=From.TreeGrowthVersion;To.TreeGrowthDay=From.TreeGrowthDay;
}
UColdSteelStatusModel* UColdSteelSharedInventorySubsystem::HarvestModel(const UObject* Context)
{
    auto* W=Context?Context->GetWorld():nullptr;if(!W||!W->GetGameInstance())return nullptr;
    auto* Local=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(W->GetNetMode()==NM_Standalone)return Local;
    auto* Shared=W->GetSubsystem<UColdSteelSharedInventorySubsystem>();if(!Shared||!Local)return nullptr;
    if(W->GetNetMode()!=NM_Client&&!Shared->InitializeAuthority())return nullptr;
    if(!Shared->SharedHarvestModel)
    {
        if(!Shared->Current.bHarvestSeeded&&W->GetNetMode()!=NM_Client)
        {CopyHarvest(Local->Snapshot(),Shared->Current.Harvest);Shared->Current.bHarvestSeeded=true;}
        // Shared storage carries only harvest fields, not a complete player profile.
        // CreateShadowModel validates a full profile; provide a neutral valid shell
        // rather than cloning the host's inventory or relaxing guest validation.
        FColdSteelProfile HarvestProfile;
        HarvestProfile.Hotbar.Init(FString(),4);
        HarvestProfile.HotbarDefinitions.Init(FString(),4);
        for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})
            HarvestProfile.Attributes.Add(Key,0);
        CopyHarvest(Shared->Current.Harvest,HarvestProfile);
        Shared->Current.Harvest=MoveTemp(HarvestProfile);
        Shared->SharedHarvestModel=Local->CreateShadowModel(Shared->Current.Harvest);
    }
    return Shared->SharedHarvestModel;
}
void UColdSteelSharedInventorySubsystem::AdvanceHarvest(float Delta)
{
    if(GetWorld()->GetNetMode()==NM_Client)return;
    HarvestClockAccum+=Delta;if(HarvestClockAccum<1.f)return;
    if(auto* M=HarvestModel(this))
    {
        const int32 PreviousVersion=M->ProfileView().TreeGrowthVersion;
        M->TickTreeGrowthClock(HarvestClockAccum);
        const auto& Profile=M->ProfileView();
        if(PreviousVersion!=Profile.TreeGrowthVersion) CopyHarvest(Profile,Current.Harvest);
        else Current.Harvest.TreeGrowthDay=Profile.TreeGrowthDay;
        for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
            if(It->IsForestVillage())
            {
                if(It->ForestGrowthDay<0. || !Profile.TreeGrowth.IsEmpty()) It->ForestGrowthDay=Profile.TreeGrowthDay;
                break;
            }
        if(!Current.Drops.IsEmpty() || !DropActors.IsEmpty()) RefreshDropActors();
    }
    HarvestClockAccum=0.f;
}
void UColdSteelSharedInventorySubsystem::ApplyForestGrowthDay(double Day)
{
    if (GetWorld()->GetNetMode()!=NM_Client || Day<0.) return;
    Current.Harvest.TreeGrowthDay=Day;
    if (SharedHarvestModel) SharedHarvestModel->SetMirroredTreeGrowthDay(Day);
}

void ATemperateHillsWorld::OnRep_ForestGrowthDay()
{
    if (auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>()) Shared->ApplyForestGrowthDay(ForestGrowthDay);
}

void UColdSteelSharedInventorySubsystem::ApplyHarvestMirror(const FColdSteelProfile& State,const TArray<FColdSteelHarvestRemoval>& Removals)
{
    CopyHarvest(State,Current.Harvest);
    if(auto* M=HarvestModel(this))M->AdoptNetMirror(Current.Harvest);
    // Remove matching streamed instances too; changing the persistence map alone
    // only affects future PCG cells and leaves nearby colliders standing.
    TSet<FString> Seen;
    Seen.Reserve(Current.HarvestRemovals.Num());
    for(const auto& Old:Current.HarvestRemovals)Seen.Add(Old.Id);
    TMap<FSoftObjectPath,FRemovalPoints> Rocks,Trees;
    FRemovalPoints Trunks;
    for(const auto& R:Removals)
    {
        bool AlreadySeen=false;
        Seen.Add(R.Id,&AlreadySeen);
        if(AlreadySeen)continue;
        if(R.Layer==1)Rocks.FindOrAdd(R.Mesh).Add(R.Location);
        else if(R.Layer==0)
        {
            Trunks.Add(R.Location);
            Trees.FindOrAdd(R.Mesh).Add(R.Location);
        }
    }
    if(!Rocks.IsEmpty()||!Trunks.Cells.IsEmpty())
        for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        {
            auto* C=*It;
            if(C->GetWorld()!=GetWorld()||!C->GetStaticMesh())continue;
            const auto* Points=Rocks.Find(FSoftObjectPath(C->GetStaticMesh()));
            const bool CheckTrunk=!Trunks.Cells.IsEmpty()&&C->ComponentHasTag(TEXT("HillsStandingTrunk"));
            if(!Points&&!CheckTrunk)continue;
            TArray<int32> Erased;
            for(int32 I=C->GetInstanceCount()-1;I>=0;--I)
            {
                FTransform Pose;
                if(!C->GetInstanceTransform(I,Pose,true))continue;
                const auto P=Pose.GetLocation();
                if((Points&&Points->Matches(P,false))||(CheckTrunk&&Trunks.Matches(P,false)))Erased.Add(I);
            }
            if(!Erased.IsEmpty())C->RemoveInstances(Erased,true);
        }
    if(!Trees.IsEmpty())
        for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
        {
            auto* C=*It;
            if(C->GetWorld()!=GetWorld()||C->ComponentHasTag(TEXT("HarvestRegrowth"))||!C->GetSkinnedAsset())continue;
            const auto* Points=Trees.Find(FSoftObjectPath(C->GetSkinnedAsset()));
            if(!Points)continue;
            TArray<FPrimitiveInstanceId> Erased;
            for(int32 I=0;I<C->GetInstanceCount();++I)
            {
                const auto Id=C->GetInstanceId(I);
                FTransform Pose;
                if(C->GetInstanceTransform(Id,Pose,true)&&Points->Matches(Pose.GetLocation(),true))Erased.Add(Id);
            }
            if(!Erased.IsEmpty())C->RemoveInstances(Erased);
        }
    Current.HarvestRemovals=Removals;
}

bool UColdSteelSharedInventorySubsystem::WorldAction(UColdSteelStatusModel* M,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& R,FString& Reason)
{
    if(!InitializeAuthority()||!M||!M->RuntimePawn())return false;
    auto* HarvestState=HarvestModel(this);if(!HarvestState)return false;
    M->SyncRuntime();const auto Before=M->Snapshot();auto Staged=Before;
    CopyHarvest(HarvestState->Snapshot(),Staged);M->AdoptNetMirror(Staged);
    ColdSteelAuthority::FScope Context(M);
    auto After=Current;bool Success=false,Depleted=false;FProductionResource Resource;FHitResult Hit;
    AVoxelBuildWorld* Building=nullptr;TArray<uint8> BuildingBefore;
    TOptional<FVoxelBuildUndoHistory> UndoBefore;
    const auto RollbackBuilding=[&]()
    {
        if(!Building||BuildingBefore.IsEmpty())return;
        if(Building->ApplyNetworkSnapshot(BuildingBefore)&&UndoBefore.IsSet())
            Building->UndoHistory=MoveTemp(UndoBefore.GetValue());
    };
    {
        TGuardValue<bool> Stage(M->bStagingNetworkContainer,true);
        if(R.Action==EColdSteelInventoryAction::Building)
        {
            for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady()){Building=*It;break;}
            if(Building&&Building->MakeNetworkSnapshot(BuildingBefore))
            {
                UndoBefore.Emplace(Building->UndoHistory);
                TGuardValue<bool> WorldStage(Building->bNetworkTransaction,true);
                Success=Building->ExecuteNetworkEdit(R,M,Reason);
                if(Success&&!Building->MakeNetworkSnapshot(After.Building))
                {Reason=TEXT("建筑状态保存失败");Success=false;}
            }
        }
        else if(R.Action==EColdSteelInventoryAction::Workstation)
        {
            // Personal crafting never changes building geometry. A rejected payment must
            // not recreate the bound gun bench (or unrelated prefabs) from a world snapshot.
            if(!R.Mode.StartsWith(TEXT("alchemy."))&&!R.Mode.StartsWith(TEXT("assembly."))&&!R.Mode.StartsWith(TEXT("wood."))&&R.Mode!=TEXT("craft")&&!R.Mode.StartsWith(TEXT("enhancement.")))
                for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady()){Building=*It;break;}
            if(Building)Building->MakeNetworkSnapshot(BuildingBefore);
            TGuardValue<bool> WorldStage(Building?Building->bNetworkTransaction:bCommitting,true);
            auto* State=M->RuntimePawn()->GetPlayerState<AColdSteelPlayerState>();
            Success=State&&State->ExecuteStation(R,M,Reason);
            if(Success&&Building)Building->MakeNetworkSnapshot(After.Building);
        }
        else
        {
            const auto* Tool=M->ActiveProductionTool();
            if(Tool&&!R.Eye.ContainsNaN()&&!R.Direction.ContainsNaN()&&FVector::DistSquared(R.Eye,M->RuntimePawn()->GetPawnViewLocation())<FMath::Square(180.f))
            {
                const auto Stats=ColdSteelTool::Evaluate(*Tool,M);
                FCollisionQueryParams Q(SCENE_QUERY_STAT(NetworkHarvest),false,M->RuntimePawn());
                const FVector End=FVector(R.Eye)+FVector(R.Direction).GetSafeNormal()*FMath::Clamp(Stats.HarvestReachCM,100.,600.);
                bool Found=GetWorld()->LineTraceSingleByChannel(Hit,R.Eye,End,ECC_Visibility,Q);
                if(!Found&&Stats.HarvestRadiusCM>0)Found=GetWorld()->SweepSingleByChannel(Hit,R.Eye,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(FMath::Min(Stats.HarvestRadiusCM,80.)),Q);
                if(Found && FProductionResource::ResolveHit(GetWorld(),Hit,Resource,Reason))
                {
                    if(R.Action==EColdSteelInventoryAction::SoilRefill)
                    {
                        if(ColdSteelInventory::Text(*Tool,TEXT("tool_kind"))==TEXT("shovel")&&Resource.Layer==2&&Resource.World.IsValid())
                            Success=Resource.World->ApplySoilRefill(Hit.ImpactPoint,Reason);
                    }
                    else
                    {
                        Resource.Direction=R.Direction;
                        if(M->SpendStamina(float(Stats.StaminaCost)))Success=M->CommitHarvestStrike(Resource,Depleted);
                        Reason=M->ResultMessage();
                        if(Success&&Depleted&&Resource.Layer==2)Resource.ApplySuccessfulStrike(Hit,true);
                    }
                }
            }
        }
        Staged=M->Snapshot();
    }
    M->AdoptNetMirror(Before);
    if(!Success)
    {RollbackBuilding();return false;}
    CopyHarvest(Staged,After.Harvest);After.bHarvestSeeded=true;
    // Transfer newly spawned production/overflow items into the shared world journal.
    for(int32 I=Staged.Items.Num()-1;I>=0;--I)
    {
        const auto& Item=Staged.Items[I];
        if(Item.Place==2&&!Before.Items.ContainsByPredicate([&](const auto& Old){return Old.InstanceId==Item.InstanceId;}))
        {auto Drop=Item;Drop.HarvestWorldId.Invalidate();After.Drops.Add(MoveTemp(Drop));Staged.Items.RemoveAt(I);}
    }
    if(Depleted&&Resource.Layer<2&&!Resource.bStump&&!Resource.DevelopmentObject.IsValid()
        &&!After.HarvestRemovals.ContainsByPredicate([&](const auto& Old){return Old.Id==Resource.Id;}))
    {FColdSteelHarvestRemoval Removal;Removal.Id=Resource.Id;Removal.Mesh=Resource.Mesh;Removal.Location=Resource.Transform.GetLocation();Removal.Layer=Resource.Layer;After.HarvestRemovals.Add(Removal);}
    if(Building)After.bBuildingPending=true;
    if(!Commit(M,Guest,MoveTemp(Staged),MoveTemp(After),Reason))
    {RollbackBuilding();return false;}
    HarvestState->AdoptNetMirror(Current.Harvest);
    if(R.Action==EColdSteelInventoryAction::Harvest&&Resource.Layer<2)Resource.ApplySuccessfulStrike(Hit,Depleted);
    if(Building&&!CompleteBuildingCommit(Building))
        Reason=TEXT("物品已记账，建筑保存待恢复；篝火和共享交易已暂停，请重进主机世界");
    return true;
}

bool UColdSteelSharedInventorySubsystem::CompleteBuildingCommit(AVoxelBuildWorld* W)
{
    // Keep the durable redo and its in-memory barrier until BOTH writes succeed.
    // A later campfire credit must never be followed by replay of this old snapshot.
    if(!W||!W->FlushCampfirePersistence()){bBlocked=true;return false;}
    auto Completed=Current;Completed.bBuildingPending=false;
    if(!SaveWorld(Completed)){bBlocked=true;return false;}
    Current=MoveTemp(Completed);return true;
}
bool UColdSteelSharedInventorySubsystem::RestoreBuilding(AVoxelBuildWorld* W)
{
    if(!InitializeAuthority())return false;
    if(!Current.bBuildingPending)return true;
    if(!W||!W->ApplyNetworkSnapshot(Current.Building)){bBlocked=true;return false;}
    return CompleteBuildingCommit(W);
}
