#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../Production/ProductionTreeFallPlan.h"
#include "../FPSGAMECharacter.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::LoadProductionDefinitions()
{
    FString Json; TSharedPtr<FJsonObject> Root;
    if (FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/production_tools.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))
        for (const auto& Pair : Root->Values)
        {
            FString Data;
            FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(), TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));
            Definitions.Add(FString(*Pair.Key), Data);
        }
}

const FColdSteelItem* UColdSteelStatusModel::ActiveProductionTool() const
{
    const auto* Item = FindItem(Current.ActiveProductionTool);
    return Item && Item->Place == 0 && ColdSteelInventory::Text(*Item,TEXT("category")) == TEXT("tool") ? Item : nullptr;
}

void UColdSteelStatusModel::NormalizeProductionState(FColdSteelProfile& P) const
{
    for(auto& I:P.Items)if(I.Place!=2)I.HarvestWorldId.Invalidate();
    // Refresh only presentation fields; saved identity, placement and harvesting data stay intact.
    for(auto& I:P.Items)
    {
        if(I.Definition!=TEXT("tool_axe")&&I.Definition!=TEXT("tool_pickaxe"))continue;
        const FString* Definition=Definitions.Find(I.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> SavedData,VisualData;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),SavedData)||
           !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),VisualData))continue;
        bool Changed=false;
        for(const TCHAR* Key:{TEXT("tool_mesh"),TEXT("tool_scale"),TEXT("mount_pitch"),TEXT("mount_yaw"),TEXT("mount_roll")})
        {
            const auto* Value=VisualData->Values.Find(Key);if(!Value)continue;
            const auto* OldValue=SavedData->Values.Find(Key);
            if(OldValue&&FJsonValue::CompareEqual(**OldValue,**Value))continue;
            SavedData->SetField(Key,*Value);Changed=true;
        }
        if(Changed)
        {
            I.Data.Reset();
            FJsonSerializer::Serialize(SavedData.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
        }
    }
    const auto* Item = P.Items.FindByPredicate([&](const auto& I){return I.InstanceId == P.ActiveProductionTool && I.Place == 0;});
    if (!Item || ColdSteelInventory::Text(*Item,TEXT("category")) != TEXT("tool")) P.ActiveProductionTool.Reset();
}

bool UColdSteelStatusModel::GrantProductionTools()
{
    if (Current.ProductionSupplyVersion >= 1) return true;
    SyncRuntime(); auto P = Snapshot();
    for (const FString& Id : {FString(TEXT("tool_axe")), FString(TEXT("tool_pickaxe")), FString(TEXT("tool_shovel"))})
    {
        if (P.Items.ContainsByPredicate([&](const auto& I){return I.Definition == Id && (I.Place == 0 || I.Place == 4);})) continue;
        auto Item = CreateItem(Id);
        if (Item.Data.IsEmpty()) { Message=TEXT("生产工具目录未加载"); return false; }
        if (!ColdSteelInventory::Insert(P.Items, Item))
        {
            if (!ColdSteelWarehouse::Insert(P.Items,Item,P.WarehousePages*ColdSteelWarehouse::CellsPerPage))
            { Message=TEXT("背包和仓库空间不足，腾出空间后按 6 / 7 / 8 领取工具"); return false; }
        }
    }
    P.ProductionSupplyVersion = 1;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::ToggleProductionTool(const FString& InstanceId)
{
    const auto* Item=FindItem(InstanceId);
    if (!Item || Item->Place != 0 || ColdSteelInventory::Text(*Item,TEXT("category")) != TEXT("tool")) return false;
    SyncRuntime(); auto P=Snapshot();
    P.ActiveProductionTool = P.ActiveProductionTool == InstanceId ? FString() : InstanceId;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::SelectProductionTool(const FString& Definition)
{
    auto ReportFailure=[this]()
    {
        if(CurrentPawn.IsValid())if(auto* Tools=CurrentPawn->FindComponentByClass<UProductionToolComponent>())Tools->ShowFeedback(Message);
        return false;
    };
    if (!GrantProductionTools()) return ReportFailure();
    const auto* Item=Current.Items.FindByPredicate([&](const auto& I){return I.Definition==Definition && I.Place==0;});
    if (!Item) { Message=TEXT("请先从仓库取出工具放入背包"); return ReportFailure(); }
    if(!ToggleProductionTool(Item->InstanceId))return ReportFailure();
    return true;
}

bool UColdSteelStatusModel::StowProductionTool()
{
    if (Current.ActiveProductionTool.IsEmpty()) return false;
    SyncRuntime(); auto P=Snapshot(); P.ActiveProductionTool.Reset();
    return CommitState(MoveTemp(P));
}

int32 UColdSteelStatusModel::HarvestProgress(const FString& Id) const
{
    return Current.HarvestProgress.FindRef(Id);
}

bool UColdSteelStatusModel::CommitHarvestStrike(const FProductionResource& Target, bool& Depleted)
{
    Depleted=false;
    const auto* Tool=ActiveProductionTool();
    if (!Target.World.IsValid() || Target.Id.IsEmpty() || !Tool) return false;
    if (ColdSteelInventory::Text(*Tool,TEXT("tool_kind")) != Target.RequiredTool)
    { Message=TEXT("工具类型不匹配"); return false; }
    const int32 Before=HarvestProgress(Target.Id);
    if (Before >= FProductionResource::RequiredHits) { Message=TEXT("此处资源已经采尽"); return false; }
    SyncRuntime(); auto P=Snapshot();
    const int32 After=Before+1;
    TArray<FString> Drops;
    if (After == FProductionResource::RequiredHits)
    {
        if(Target.Layer<2)
        {
            auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();
            if(!Harvest){Message=TEXT("当前世界无法生成采集物");return false;}
            Harvest->Prepare(Target.Layer==0);
            if(Target.Layer==0)
            {
                Harvest->PrepareFall(Target);
                if(!Harvest->ReadyFall(Target)){Message=TEXT("正在准备倒树模型，稍后再挥动一次");return false;}
            }
            if(!Harvest->Ready(Target.Layer==0)){Message=TEXT("正在准备采集物模型，稍后再挥动一次");return false;}
            if(!StageProductionDrops(P,Target,Drops))return false;
        }
        else
        for (const auto& Reward : Target.Rewards)
        {
            const auto Item=CreateItem(Reward.Key,Reward.Value);
            if (Item.Data.IsEmpty() || !ColdSteelInventory::Insert(P.Items,Item))
            { Message=TEXT("背包空间不足，资源保留；整理后继续采集"); return false; }
        }
    }
    P.HarvestProgress.Add(Target.Id,After);
    // Depletion and every ground pickup are one profile transaction, before visuals.
    if (!CommitState(MoveTemp(P))) return false;
    Depleted=After == FProductionResource::RequiredHits;
    if(!Drops.IsEmpty())GetWorld()->GetSubsystem<UProductionHarvestSubsystem>()->DelayDrops(Drops,
        Target.Layer==0?FProductionTreeFallPlan::Make(Target).ReleaseSeconds():.25f);
    Message=Depleted ? (Target.Layer==0?TEXT("树木正在倒下，落地后对准木材按 E 拾取"):
        Target.Layer==1?TEXT("岩石已破碎，对准石材或矿石按 E 拾取"):TEXT("表土已采集，材料收入背包")) :
        FString::Printf(TEXT("%s  %d / %d"),*Target.Name,After,FProductionResource::RequiredHits);
    return true;
}
