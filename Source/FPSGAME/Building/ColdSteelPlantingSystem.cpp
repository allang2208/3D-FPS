#include "ColdSteelPlantingSystem.h"
#include "ColdSteelPlantingLayout.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    bool PlantingReadJson(const TCHAR* File,TSharedPtr<FJsonObject>& Out)
    {
        FString Text;
        return FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File))
            &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Out)&&Out.IsValid();
    }
    bool PlantingMaterialPlace(const FColdSteelItem& Item)
    {return Item.Place==0||Item.Place==ColdSteelInventory::ColdSteelCompartment::Place||(Item.Place==4&&Item.Container.IsEmpty());}
    bool PlantingTakeInputs(FColdSteelProfile& State,const FString& Definition,int64 Count)
    {
        int64 Have=0;
        for(const auto& Item:State.Items)if(Item.Definition==Definition&&PlantingMaterialPlace(Item))Have+=Item.Count;
        if(Have<Count)return false;
        for(int32 Place:{0,5,4})for(int32 Index=State.Items.Num()-1;Index>=0&&Count>0;--Index)
        {
            auto& Item=State.Items[Index];
            if(Item.Place!=Place||Item.Definition!=Definition||!PlantingMaterialPlace(Item))continue;
            const int64 Used=FMath::Min(Count,Item.Count);Item.Count-=Used;Count-=Used;
            if(Item.Count<=0)State.Items.RemoveAt(Index);
        }
        return Count==0;
    }
}

void UColdSteelPlantingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    if(!LoadCatalog())return;
    TArray<FSoftObjectPath> Paths;
    for(const auto& Rule:Rules)for(const auto& Variant:Rule.Variants)for(const auto& Path:Variant.Value)Paths.AddUnique(Path);
    // Exactly 36 catalog meshes; no synchronous asset load from HUD or plant ticks.
    AssetRequest=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths]()
    {
        MeshCache.Reset();
        for(const auto& Path:Paths)if(auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject()))MeshCache.Add(Mesh);
        bAssetsReady=MeshCache.Num()==36;bVisualDirty=true;++ChangeSerial;
        if(!bAssetsReady)UE_LOG(LogTemp,Error,TEXT("Planting: V3 mesh catalog loaded %d/36 meshes"),MeshCache.Num());
    }));
}
void UColdSteelPlantingSystem::Deinitialize()
{
    ClearPresentation();EndNetworkContext();Mirror={};MirrorWorld.Reset();AssetRequest.Reset();MeshCache.Reset();Super::Deinitialize();
}
bool UColdSteelPlantingSystem::LoadCatalog()
{
    Rules.Reset();SlotsCm.Reset();
    TSharedPtr<FJsonObject> Config,Models;
    if(!PlantingReadJson(TEXT("planting_rules.json"),Config)||!PlantingReadJson(TEXT("crop_models_v3.json"),Models))return false;
    if(Models->GetStringField(TEXT("model_version"))!=TEXT("V3"))return false;
    MaxPlants=FMath::Clamp(Config->GetIntegerField(TEXT("max_plants")),16,4096);
    const auto& Range=Config->GetArrayField(TEXT("scale_range"));
    if(Range.Num()!=2)return false;
    ScaleMin=float(Range[0]->AsNumber());ScaleMax=float(Range[1]->AsNumber());
    if(ScaleMin<=0||ScaleMax<ScaleMin||ScaleMax>1.1f)return false;
    for(const auto& Value:Config->GetArrayField(TEXT("slots_cm")))
    {
        const auto& V=Value->AsArray();if(V.Num()!=3)return false;
        SlotsCm.Add(FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber()));
    }
    if(SlotsCm.Num()!=16)return false;
    const auto& ModelCrops=Models->GetObjectField(TEXT("crops"));
    for(const auto& Value:Config->GetArrayField(TEXT("crops")))
    {
        const auto& O=Value->AsObject();if(!O)return false;
        FColdSteelCropRule R;R.Id=FName(*O->GetStringField(TEXT("id")));R.Name=O->GetStringField(TEXT("name"));
        R.InputItem=O->GetStringField(TEXT("input_item"));R.OutputItem=O->GetStringField(TEXT("output_item"));
        R.InputCount=O->GetIntegerField(TEXT("input_count"));R.OutputCount=O->GetIntegerField(TEXT("output_count"));
        R.GrowthSeconds=O->GetNumberField(TEXT("growth_seconds"));
        const auto& Size=O->GetArrayField(TEXT("footprint"));if(Size.Num()!=2)return false;
        R.Footprint=FIntPoint(int32(Size[0]->AsNumber()),int32(Size[1]->AsNumber()));
        if(Find(R.Id)||R.GrowthSeconds<1.||!FMath::IsFinite(R.GrowthSeconds)||R.InputCount<1||R.OutputCount<1
            ||!FColdSteelCropPlant::Fits(0,R.Footprint))return false;
        const auto& Variants=ModelCrops->GetObjectField(R.Id.ToString())->GetObjectField(TEXT("variants"));
        for(const TCHAR* Variant:{TEXT("A"),TEXT("B"),TEXT("C")})
        {
            const auto& Stages=Variants->GetObjectField(Variant)->GetObjectField(TEXT("stages"));
            auto& Out=R.Variants.Add(FName(Variant));
            for(int32 Stage=1;Stage<=3;++Stage)
            {
                FSoftObjectPath Path(Stages->GetStringField(FString::FromInt(Stage)));
                if(!Path.IsValid()||!Path.GetAssetPathString().StartsWith(TEXT("/Game/Props/Crops/V3/")))return false;
                Out.Add(Path);
            }
        }
        Rules.Add(MoveTemp(R));
    }
    return Rules.Num()==4;
}
const FColdSteelCropRule* UColdSteelPlantingSystem::Find(FName Crop) const
{return Rules.FindByPredicate([Crop](const auto& Rule){return Rule.Id==Crop;});}
UColdSteelStatusModel* UColdSteelPlantingSystem::Model() const
{return GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
AVoxelBuildPrefabActor* UColdSteelPlantingSystem::Bed(const AVoxelBuildWorld* World,FIntVector Cell) const
{
    auto* Actor=World?Cast<AVoxelBuildPrefabActor>(World->PrefabActorAt(Cell)):nullptr;
    return Actor&&!Actor->IsFalling()&&Actor->PrefabId()==BedPrefabId()&&World->HasPrefabAt(Cell)?Actor:nullptr;
}
const FColdSteelCropPlant* UColdSteelPlantingSystem::Occupant(const AVoxelBuildWorld* World,FIntVector Cell,int32 Slot) const
{
    auto* M=Model();if(!World||!M||!Bed(World,Cell))return nullptr;
    const FGuid Id=World->PrefabInstanceIdentity(Cell);
    return Plants(World).FindByPredicate([&](const auto& Plant)
    {return Plant.WorldKey==World->BuildingWorldKey()&&Plant.BedId==Id&&Plant.Occupies(Slot);});
}
bool UColdSteelPlantingSystem::Prepare(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FColdSteelProfile& Proposed,FString& Reason,bool Preview,
    UColdSteelStatusModel* Operator,TArray<FColdSteelCropPlant>* SharedAfter,const FColdSteelProfile* BaseProfile) const
{
    Reason.Reset();auto* M=Operator?Operator:Model();auto* Piece=Bed(World,Cell);
    if(!World){Reason=TEXT("种植地尚未就绪");return false;}
    if(World->GetNetMode()!=NM_Standalone)
    {
        if(World->GetNetMode()==NM_Client)
        {
            if(!Preview){Reason=TEXT("客户端不能提交种植世界");return false;}
            if(MirrorWorld.Get()!=World->GetWorld()||Mirror.WorldKey!=World->BuildingWorldKey()||!Mirror.bReady)
            {Reason=TEXT("正在同步服务端种植地…");return false;}
            if(Mirror.bSaveBlocked){Reason=TEXT("服务端世界保存待恢复，暂不能操作");return false;}
        }
        else
        {
            auto* Shared=World->GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
            if(!Shared||!Shared->EnsurePlantingWorld(World,Reason)||Shared->IsPlantingSaveBlocked())
            {if(Reason.IsEmpty())Reason=TEXT("共享种植世界尚未就绪");return false;}
            if(!Preview&&!SharedAfter){Reason=TEXT("多人种植必须通过服务端共享事务");return false;}
        }
        if(Preview&&bNetworkPending){Reason=TEXT("正在等待服务端种植结果…");return false;}
    }
    if(!M||!Piece||!World->PrefabInstanceIdentity(Cell).IsValid()){Reason=TEXT("种植地不可用，请重新交互");return false;}
    const auto* PC=World->GetWorld()->GetFirstPlayerController();
    const APawn* Pawn=Operator?Operator->RuntimePawn():(PC?PC->GetPawn():nullptr);
    if(!Pawn||Pawn->GetWorld()!=World->GetWorld()||FVector::DistSquared(Pawn->GetActorLocation(),Piece->GetActorLocation())>FMath::Square(350.f))
    {Reason=TEXT("已离开种植地");return false;}
    if(Slot<0||Slot>=16){Reason=TEXT("请先选择地块");return false;}
    const auto StagedOccupant=[&](int32 At)->const FColdSteelCropPlant*
    {
        if(!SharedAfter)return Occupant(World,Cell,At);
        const FGuid Id=World->PrefabInstanceIdentity(Cell);
        return SharedAfter->FindByPredicate([&](const auto& P){return P.WorldKey==World->BuildingWorldKey()&&P.BedId==Id&&P.Occupies(At);});
    };
    const auto* Existing=StagedOccupant(Slot);
    if(Existing)
    {
        if(Existing->Stage(NowTicks(World))<3){Reason=TEXT("植株仍在生长，成熟后可收获");return false;}
        Proposed=BaseProfile?*BaseProfile:M->Snapshot();
        const auto Product=M->CreateItem(Existing->OutputItem,Existing->OutputCount);
        if(Product.Data.IsEmpty()||!ColdSteelInventory::Insert(Proposed.Items,Product)){Reason=TEXT("背包放不下，植株保持待收获");return false;}
        const FGuid PlantId=Existing->PlantId;
        auto& Crops=SharedAfter?*SharedAfter:Proposed.PlantingCrops;
        Crops.RemoveAll([PlantId](const auto& P){return P.PlantId==PlantId;});return true;
    }
    const auto* Rule=Find(Crop);
    if(!Rule){Reason=TEXT("请选择种植作物");return false;}
    // Harvest above remains valid at every legacy anchor. New planting uses
    // only four fixed positions, including direct/old-client network requests.
    if(!ColdSteelPlantingLayout::IsAnchor(Slot))
    {Reason=TEXT("请选择 2×2 布局中的种植位");return false;}
    const FGuid BedId=World->PrefabInstanceIdentity(Cell);
    int32 BedCount=0;
    for(const auto& Plant:(SharedAfter?*SharedAfter:Plants(World)))
        if(Plant.WorldKey==World->BuildingWorldKey()&&Plant.BedId==BedId)++BedCount;
    if(BedCount>=ColdSteelPlantingLayout::PlotCount)
    {Reason=TEXT("每块种植地最多 4 株，请先收获已有植株");return false;}
    for(int32 Offset:{0,1,4,5})if(StagedOccupant(Slot+Offset))
    {Reason=TEXT("该种植位已有植株，请先收获");return false;}
    if(!bAssetsReady&&World->GetNetMode()!=NM_DedicatedServer){Reason=TEXT("正在准备作物模型");return false;}
    if(!FColdSteelCropPlant::Fits(Slot,Rule->Footprint)){Reason=TEXT("所选地块放不下该作物，请选择左上方空位");return false;}
    for(int32 X=0;X<Rule->Footprint.X;++X)for(int32 Y=0;Y<Rule->Footprint.Y;++Y)
        if(StagedOccupant(Slot+X*4+Y)){Reason=TEXT("种植范围已有植株");return false;}
    if((SharedAfter?SharedAfter->Num():Plants(World).Num())>=MaxPlants){Reason=TEXT("已达当前种植数量上限");return false;}
    if(M->CreateItem(Rule->InputItem).Data.IsEmpty()||M->CreateItem(Rule->OutputItem).Data.IsEmpty())
    {Reason=TEXT("种植材料或产物不在当前物品目录");return false;}
    const bool Free=UDevelopmentTuningSubsystem::IsFreePlanting(M);
    if(Preview)
    {
        if(!Free&&M->CountMaterial(Rule->InputItem)<Rule->InputCount){Reason=TEXT("种植材料不足（背包、夹层与主仓库）");return false;}
        return true;
    }
    Proposed=BaseProfile?*BaseProfile:M->Snapshot();
    if(!Free&&!PlantingTakeInputs(Proposed,Rule->InputItem,Rule->InputCount)){Reason=TEXT("种植材料不足（背包、夹层与主仓库）");return false;}
    FColdSteelCropPlant Plant;Plant.PlantId=FGuid::NewGuid();Plant.WorldKey=World->BuildingWorldKey();
    Plant.BedId=World->PrefabInstanceIdentity(Cell);Plant.BedCell=Cell;Plant.Slot=Slot;Plant.Footprint=Rule->Footprint;
    Plant.Crop=Rule->Id;Plant.GrowthSeconds=Rule->GrowthSeconds;Plant.OutputItem=Rule->OutputItem;Plant.OutputCount=Rule->OutputCount;
    FRandomStream Random(GetTypeHash(Plant.PlantId));
    Plant.Variant=FName(*FString::Chr(TCHAR('A'+Random.RandRange(0,2))));
    Plant.YawDegrees=Random.FRandRange(0.f,360.f);Plant.UniformScale=Random.FRandRange(ScaleMin,ScaleMax);
    for(int32 X=0;X<Rule->Footprint.X;++X)for(int32 Y=0;Y<Rule->Footprint.Y;++Y)Plant.LocalRootCm+=SlotsCm[Slot+X*4+Y];
    Plant.LocalRootCm/=double(Rule->Footprint.X*Rule->Footprint.Y);Plant.PlantedUtcTicks=FDateTime::UtcNow().GetTicks();
    (SharedAfter?*SharedAfter:Proposed.PlantingCrops).Add(MoveTemp(Plant));return true;
}
bool UColdSteelPlantingSystem::CanAct(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FString& Reason) const
{FColdSteelProfile Proposed;return Prepare(World,Cell,Slot,Crop,Proposed,Reason,true);}
bool UColdSteelPlantingSystem::Act(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FString& Reason,const FGuid& ExpectedPlantId)
{
    if(World&&World->GetNetMode()!=NM_Standalone)return RequestNetwork(World,Cell,Slot,Crop,ExpectedPlantId,Reason);
    auto* M=Model();if(!M)return false;M->SyncRuntime();
    const auto* Existing=Occupant(World,Cell,Slot);
    if(ExpectedPlantId.IsValid()?(!Existing||Existing->PlantId!=ExpectedPlantId):Existing!=nullptr)
    {Reason=TEXT("植株状态已变化，请重新选择地块");return false;}
    FColdSteelProfile Proposed;if(!Prepare(World,Cell,Slot,Crop,Proposed,Reason))return false;
    if(!M->CommitState(MoveTemp(Proposed))){Reason=M->ResultMessage();return false;}
    bVisualDirty=true;++ChangeSerial;Accum=1.;UpdateWorld(World,0.f);return true;
}
void UColdSteelPlantingSystem::ClearPresentation()
{for(auto& Group:MeshGroups)if(IsValid(Group.Value))Group.Value->DestroyComponent();MeshGroups.Reset();}
void UColdSteelPlantingSystem::UpdateWorld(AVoxelBuildWorld* World,float Delta)
{
    if(!World)return;
    if(bNetworkPending)
    {
        const auto* PC=World->GetWorld()->GetFirstPlayerController();
        if(RequestWorld.Get()!=World->GetWorld()||!RequestPawn.IsValid()||!PC||PC->GetPawn()!=RequestPawn.Get())EndNetworkContext();
    }
    Accum+=Delta;if(Accum<1.)return;Accum=0.;
    if(ActiveWorld!=World){ClearPresentation();ActiveWorld=World;bVisualDirty=true;}
    auto* M=Model();if(!M)return;
    const bool Client=World->GetNetMode()==NM_Client;
    auto* Shared=World->GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    if(World->GetNetMode()!=NM_Standalone&&!Client)
    {FString Reason;if(!Shared||!Shared->EnsurePlantingWorld(World,Reason))return;}
    TSet<FGuid> Orphans;
    uint32 Signature=uint32(Plants(World).Num());const int64 Now=NowTicks(World);bool Unresolved=false;
    for(const auto& Plant:Plants(World))if(Plant.WorldKey==World->BuildingWorldKey())
    {
        auto* Piece=Bed(World,Plant.BedCell);
        if(!Piece||World->PrefabInstanceIdentity(Plant.BedCell)!=Plant.BedId)
        {if(Client)Unresolved=true;else Orphans.Add(Plant.PlantId);continue;}
        Signature=HashCombine(Signature,HashCombine(GetTypeHash(Plant.PlantId),uint32(Plant.Stage(Now))));
    }
    if(!Orphans.IsEmpty())
    {
        if(World->GetNetMode()==NM_Standalone)
        {
            auto Proposed=M->Snapshot();Proposed.PlantingCrops.RemoveAll([&](const auto& Plant){return Orphans.Contains(Plant.PlantId);});
            if(M->CommitState(MoveTemp(Proposed))){bVisualDirty=true;++ChangeSerial;}
        }
        else {FString Reason;if(Shared->PrunePlanting(World,Orphans,Reason)){bVisualDirty=true;++ChangeSerial;}}
    }
    if(World->GetNetMode()==NM_DedicatedServer)return;
    if(Signature!=VisualSignature)++ChangeSerial;
    if(!bAssetsReady||(!bVisualDirty&&Signature==VisualSignature))return;
    VisualSignature=Signature;bVisualDirty=Unresolved;
    for(auto& Group:MeshGroups)Group.Value->ClearInstances();
    for(const auto& Plant:Plants(World))if(Plant.WorldKey==World->BuildingWorldKey()&&!Orphans.Contains(Plant.PlantId))
    {
        auto* Piece=Bed(World,Plant.BedCell);const auto* Rule=Find(Plant.Crop);
        if(!Piece||World->PrefabInstanceIdentity(Plant.BedCell)!=Plant.BedId||!Rule)continue;
        const auto* Stages=Rule->Variants.Find(Plant.Variant);if(!Stages||Stages->Num()!=3)continue;
        const auto& Path=(*Stages)[Plant.Stage(Now)-1];auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject());if(!Mesh)continue;
        const FString Key=Path.ToString();auto& Component=MeshGroups.FindOrAdd(Key);
        if(!Component)
        {
            Component=NewObject<UInstancedStaticMeshComponent>(World);World->AddInstanceComponent(Component);
            Component->SetStaticMesh(Mesh);Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Component->SetCanEverAffectNavigation(false);Component->SetMobility(EComponentMobility::Movable);
            Component->SetCullDistances(0,12000);Component->RegisterComponent();
        }
        const FTransform Local(FRotator(0,Plant.YawDegrees,0),Plant.LocalRootCm,FVector(Plant.UniformScale));
        Component->AddInstance(Local*Piece->GetActorTransform(),true);
    }
}
