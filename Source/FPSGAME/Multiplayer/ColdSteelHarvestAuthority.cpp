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
        Shared->SharedHarvestModel=Local->CreateShadowModel(Shared->Current.Harvest);
    }
    return Shared->SharedHarvestModel;
}
void UColdSteelSharedInventorySubsystem::AdvanceHarvest(float Delta)
{
    if(GetWorld()->GetNetMode()==NM_Client)return;
    HarvestClockAccum+=Delta;if(HarvestClockAccum<1.f)return;
    if(auto* M=HarvestModel(this)){M->TickTreeGrowthClock(HarvestClockAccum);CopyHarvest(M->Snapshot(),Current.Harvest);RefreshDropActors();}
    HarvestClockAccum=0.f;
}
void UColdSteelSharedInventorySubsystem::ApplyHarvestMirror(const FColdSteelProfile& State,const TArray<FColdSteelHarvestRemoval>& Removals)
{
    CopyHarvest(State,Current.Harvest);
    if(auto* M=HarvestModel(this))M->AdoptNetMirror(Current.Harvest);
    // Remove matching streamed instances too; changing the persistence map alone
    // only affects future PCG cells and leaves nearby colliders standing.
    for(const auto& R:Removals)
    {
        if(Current.HarvestRemovals.ContainsByPredicate([&](const auto& Old){return Old.Id==R.Id;}))continue;
        for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        {
            auto* C=*It;if(C->GetWorld()!=GetWorld()||!C->GetStaticMesh())continue;
            const bool Rock=R.Layer==1&&C->GetStaticMesh()->GetPathName()==R.Mesh.ToString();
            const bool Trunk=R.Layer==0&&C->GetOwner()->IsA<ATemperateHillsWorld>()&&!C->ComponentHasTag(TEXT("HarvestStump"));
            if(!Rock&&!Trunk)continue;
            for(int32 I=C->GetInstanceCount()-1;I>=0;--I)
            {FTransform T;if(C->GetInstanceTransform(I,T,true)&&FVector::DistSquared2D(T.GetLocation(),R.Location)<4.)C->RemoveInstance(I);}
        }
        for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
        {
            auto* C=*It;if(R.Layer!=0||C->GetWorld()!=GetWorld()||!C->GetSkinnedAsset()||C->GetSkinnedAsset()->GetPathName()!=R.Mesh.ToString())continue;
            for(int32 I=C->GetInstanceCount()-1;I>=0;--I)
            {const auto Id=C->GetInstanceId(I);FTransform T;if(C->GetInstanceTransform(Id,T,true)&&FVector::DistSquared(T.GetLocation(),R.Location)<4.)C->RemoveInstance(Id);}
        }
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
    {
        TGuardValue<bool> Stage(M->bStagingNetworkContainer,true);
        if(R.Action==EColdSteelInventoryAction::Building)
        {
            for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady()){Building=*It;break;}
            if(Building&&Building->MakeNetworkSnapshot(BuildingBefore))Success=Building->ExecuteNetworkEdit(R,M,Reason);
            if(Success)Building->MakeNetworkSnapshot(After.Building);
        }
        else if(R.Action==EColdSteelInventoryAction::Workstation)
        {
            // Alchemy mutates a personal batch and a transient lease, never building geometry.
            // Do not rebuild every prefab from an old world snapshot when its payment fails.
            if(!R.Mode.StartsWith(TEXT("alchemy.")))
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
                if(Found)for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
                {
                    if(R.Action==EColdSteelInventoryAction::SoilRefill)
                    {
                        if(ColdSteelInventory::Text(*Tool,TEXT("tool_kind"))==TEXT("shovel")&&It->ResolveProductionResource(Hit,Resource,Reason)&&Resource.Layer==2)
                            Success=It->ApplySoilRefill(Hit.ImpactPoint,Reason);
                    }
                    else if(It->ResolveProductionResource(Hit,Resource,Reason))
                    {
                        Resource.Direction=R.Direction;
                        if(M->SpendStamina(float(Stats.StaminaCost)))Success=M->CommitHarvestStrike(Resource,Depleted);
                        Reason=M->ResultMessage();
                        if(Success&&Depleted&&Resource.Layer==2)It->CompleteProductionHarvest(Resource,Hit,R.Direction);
                    }
                    if(!Resource.Id.IsEmpty())break;
                }
            }
        }
        Staged=M->Snapshot();
    }
    M->AdoptNetMirror(Before);
    if(!Success)
    {if(Building&&!BuildingBefore.IsEmpty())Building->ApplyNetworkSnapshot(BuildingBefore);return false;}
    CopyHarvest(Staged,After.Harvest);After.bHarvestSeeded=true;
    // Transfer newly spawned production/overflow items into the shared world journal.
    for(int32 I=Staged.Items.Num()-1;I>=0;--I)
    {
        const auto& Item=Staged.Items[I];
        if(Item.Place==2&&!Before.Items.ContainsByPredicate([&](const auto& Old){return Old.InstanceId==Item.InstanceId;}))
        {auto Drop=Item;Drop.HarvestWorldId.Invalidate();After.Drops.Add(MoveTemp(Drop));Staged.Items.RemoveAt(I);}
    }
    if(Depleted&&Resource.Layer<2&&!Resource.bStump)
    {FColdSteelHarvestRemoval Removal;Removal.Id=Resource.Id;Removal.Mesh=Resource.Mesh;Removal.Location=Resource.Transform.GetLocation();Removal.Layer=Resource.Layer;After.HarvestRemovals.Add(Removal);}
    if(Building)After.bBuildingPending=true;
    if(!Commit(M,Guest,MoveTemp(Staged),MoveTemp(After),Reason))
    {if(Building&&!BuildingBefore.IsEmpty())Building->ApplyNetworkSnapshot(BuildingBefore);return false;}
    HarvestState->AdoptNetMirror(Current.Harvest);
    if(Depleted&&Resource.Layer<2&&Resource.World.IsValid())Resource.World->CompleteProductionHarvest(Resource,Hit,R.Direction);
    if(Building)CompleteBuildingCommit(Building);
    return true;
}

bool UColdSteelSharedInventorySubsystem::CompleteBuildingCommit(AVoxelBuildWorld* W)
{
    if(!W||!W->FlushCampfirePersistence())return false;
    Current.bBuildingPending=false;return SaveWorld(Current);
}
bool UColdSteelSharedInventorySubsystem::RestoreBuilding(AVoxelBuildWorld* W)
{
    if(!InitializeAuthority()||!Current.bBuildingPending)return true;
    if(!W||!W->ApplyNetworkSnapshot(Current.Building))return false;
    return CompleteBuildingCommit(W);
}
