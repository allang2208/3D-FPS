#include "ColdSteelPlantingSystem.h"
#include "ColdSteelPlantingLayout.h"
#include "VoxelBuildWorld.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Development/DevelopmentTuningSubsystem.h"

bool UColdSteelPlantingSystem::SelectionAnchors(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,
    TArray<int32>& Anchors,FString& Reason) const
{
    Anchors.Reset();Reason.Reset();
    const auto* Rule=Find(Crop);
    if(!Rule){Reason=TEXT("请选择种植作物");return false;}
    if(!World||!Bed(World,Cell)||Slots.IsEmpty()||Slots.Num()>16){Reason=TEXT("请先选择空地");return false;}
    uint32 Remaining=0;
    for(const int32 Slot:Slots)
    {
        if(Slot<0||Slot>=16||(Remaining&(1u<<Slot))){Reason=TEXT("所选地块无效，请重新选择");return false;}
        if(Occupant(World,Cell,Slot)){Reason=TEXT("所选地块已有植株，请重新选择空地");return false;}
        Remaining|=1u<<Slot;
    }
    // The wire still carries physical cells. Accept only complete user-facing
    // positions and return exactly one anchor per position, for every crop.
    for(int32 Plot=0;Plot<ColdSteelPlantingLayout::PlotCount;++Plot)
    {
        const uint32 Mask=ColdSteelPlantingLayout::Mask(Plot);
        if(!(Remaining&Mask))continue;
        if((Remaining&Mask)!=Mask)
        {Anchors.Reset();Reason=TEXT("请选择完整种植位，每个位置种植一株");return false;}
        Anchors.Add(ColdSteelPlantingLayout::Anchor(Plot));Remaining&=~Mask;
    }
    return !Anchors.IsEmpty();
}

bool UColdSteelPlantingSystem::CanPlantSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,
    int32& Count,FString& Reason) const
{
    Count=0;TArray<int32> Anchors;
    if(!SelectionAnchors(World,Cell,Slots,Crop,Anchors,Reason))return false;
    Count=Anchors.Num();
    // Reuse all existing context, world-save, distance, readiness and per-footprint gates.
    for(const int32 Anchor:Anchors)if(!CanAct(World,Cell,Anchor,Crop,Reason))return false;
    const FGuid BedId=World->PrefabInstanceIdentity(Cell);
    int32 BedCount=0;
    for(const auto& Plant:Plants(World))if(Plant.WorldKey==World->BuildingWorldKey()&&Plant.BedId==BedId)++BedCount;
    if(BedCount+Count>ColdSteelPlantingLayout::PlotCount)
    {Reason=TEXT("每块种植地最多 4 株，请先收获已有植株");return false;}
    if(Plants(World).Num()+Count>MaxPlants){Reason=TEXT("本次播种会超过种植数量上限");return false;}
    const auto* Rule=Find(Crop);const auto* M=Model();
    if(!Rule||!M)return false;
    if(!UDevelopmentTuningSubsystem::IsFreePlanting(M)&&M->CountMaterial(Rule->InputItem)/Rule->InputCount<Count)
    {Reason=FString::Printf(TEXT("本次需 %lld 份种植材料，当前材料不足"),Rule->InputCount*Count);return false;}
    return true;
}

bool UColdSteelPlantingSystem::PrepareSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,
    UColdSteelStatusModel* Operator,FColdSteelProfile& Profile,TArray<FColdSteelCropPlant>& After,FString& Reason) const
{
    TArray<int32> Anchors;
    if(!Operator||!SelectionAnchors(World,Cell,Slots,Crop,Anchors,Reason))return false;
    // These are transaction-local copies. Any failed footprint discards the entire batch.
    auto Proposed=Profile;auto Staged=After;
    for(const int32 Anchor:Anchors)
    {
        FColdSteelProfile Next;
        if(!Prepare(World,Cell,Anchor,Crop,Next,Reason,false,Operator,&Staged,&Proposed))return false;
        Proposed=MoveTemp(Next);
    }
    Profile=MoveTemp(Proposed);After=MoveTemp(Staged);return true;
}

bool UColdSteelPlantingSystem::PlantSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,FString& Reason)
{
    int32 Count=0;
    if(!CanPlantSelection(World,Cell,Slots,Crop,Count,Reason))return false;
    if(World->GetNetMode()!=NM_Standalone)return RequestNetwork(World,Cell,Slots[0],Crop,FGuid(),Reason,Slots);
    auto* M=Model();if(!M)return false;M->SyncRuntime();
    auto Profile=M->Snapshot();auto After=Plants(World);
    if(!PrepareSelection(World,Cell,Slots,Crop,M,Profile,After,Reason))return false;
    Profile.PlantingCrops=MoveTemp(After);
    if(!M->CommitState(MoveTemp(Profile))){Reason=M->ResultMessage();return false;}
    bVisualDirty=true;++ChangeSerial;Accum=1.;UpdateWorld(World,0.f);return true;
}
