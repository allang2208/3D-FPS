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
    // Only the shovel overrides the selected weapon from the backpack. Axe and
    // pickaxe are held through the active main-hand equipment slot.
    const auto* Override = FindItem(Current.ActiveProductionTool);
    if(Override && !ColdSteelInventory::IsEquippedProductionTool(*Override) && Override->Place==0 &&
        ColdSteelInventory::Text(*Override,TEXT("category"))==TEXT("tool"))return Override;
    const auto* Item=Equipped();
    return Item && ColdSteelInventory::IsEquippedProductionTool(*Item) ? Item : nullptr;
}

void UColdSteelStatusModel::NormalizeProductionState(FColdSteelProfile& P) const
{
    for(auto& I:P.Items)if(I.Place!=2)I.HarvestWorldId.Invalidate();
    // Refresh presentation, equipment, combat tuning and both tools' phase clocks; saved identity,
    // placement and harvesting progress stay intact.
    for(auto& I:P.Items)
    {
        if(I.Definition!=TEXT("tool_axe")&&I.Definition!=TEXT("tool_pickaxe"))continue;
        const FString* Definition=Definitions.Find(I.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> SavedData,VisualData;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),SavedData)||
           !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),VisualData))continue;
        bool Changed=false;
        for(const TCHAR* Key:{TEXT("tool_mesh"),TEXT("tool_scale"),TEXT("mount_pitch"),TEXT("mount_yaw"),TEXT("mount_roll"),
            TEXT("tool_viewmodel"),TEXT("tool_animation_prefix"),TEXT("tool_swing_sound"),
            TEXT("swing_seconds"),TEXT("contact_seconds"),TEXT("desc"),TEXT("melee_damage"),
            TEXT("combat_reach_cm"),TEXT("combat_sweep_radius_cm"),TEXT("harvest_reach_cm"),TEXT("harvest_sweep_radius_cm"),
            TEXT("grid_w"),TEXT("grid_h"),TEXT("ue_icon"),TEXT("weaponType"),TEXT("weaponTypeTag"),TEXT("equipSlot"),TEXT("isTwoHanded")})
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
            // 2x3 -> 1x3 only shrinks in either orientation. Keep the saved cell and
            // explicit player rotation; new items use the upright default.
            if(I.Definition==TEXT("tool_axe"))ColdSteelInventory::ApplyOrientation(I,-1);
        }
        I.Magazine=0;I.Reserve=0;
    }
    const auto* Item = P.Items.FindByPredicate([&](const auto& I){return I.InstanceId == P.ActiveProductionTool && I.Place == 0;});
    // Discard legacy backpack selections without relocating either tool.
    if (!Item || ColdSteelInventory::IsEquippedProductionTool(*Item) || ColdSteelInventory::Text(*Item,TEXT("category")) != TEXT("tool")) P.ActiveProductionTool.Reset();
}

bool UColdSteelStatusModel::GrantProductionTools()
{
    if (Current.ProductionSupplyVersion >= 1) return true;
    SyncRuntime(); auto P = Snapshot();
    for (const FString& Id : {FString(TEXT("tool_axe")), FString(TEXT("tool_pickaxe")), FString(TEXT("tool_shovel"))})
    {
        if (P.Items.ContainsByPredicate([&](const auto& I){return I.Definition == Id && (I.Place == 0 || I.Place == 1 || I.Place == 4);})) continue;
        auto Item = CreateItem(Id);
        if (Item.Data.IsEmpty()) { Message=TEXT("生产工具目录未加载"); return false; }
        if (!ColdSteelInventory::Insert(P.Items, Item))
        {
            if (!ColdSteelWarehouse::Insert(P.Items,Item,WarehouseCapacity()))
            { Message=TEXT("背包和仓库空间不足，腾出空间后按 8 领取工具；伐木斧与矿镐需在背包装备"); return false; }
        }
    }
    P.ProductionSupplyVersion = 1;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::ToggleProductionTool(const FString& InstanceId)
{
    const auto* Item=FindItem(InstanceId);
    if(Item && ColdSteelInventory::IsEquippedProductionTool(*Item))
    {
        if(Item->Place!=1 || (Item->Cell!=6 && Item->Cell!=9))
        {Message=TEXT("请先在背包右键装备此工具，或将它拖入主手武器槽");return false;}
        return MoveItem(InstanceId,1,Item->Cell);
    }
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
    if(Definition==TEXT("tool_axe") || Definition==TEXT("tool_pickaxe"))
    {
        const auto* EquippedTool=Current.Items.FindByPredicate([&](const auto& I){return I.Definition==Definition && I.Place==1 && (I.Cell==6 || I.Cell==9);});
        if(!EquippedTool){Message=TEXT("请先在背包右键装备此工具，再用 G 或滚轮切换武器");return ReportFailure();}
        return ToggleProductionTool(EquippedTool->InstanceId) || ReportFailure();
    }
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

bool UColdSteelStatusModel::ResetHarvestProgress(const FString& Id)
{
    // Topsoil excavation digs one 20 cm layer per completed cycle, so the cell has to
    // become harvestable again; trees and rocks keep their single-depletion rule.
    if (Id.IsEmpty() || !Current.HarvestProgress.Contains(Id)) return false;
    SyncRuntime(); auto P=Snapshot();
    P.HarvestProgress.Remove(Id);
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::CommitHarvestStrike(const FProductionResource& Target, bool& Depleted)
{
    Depleted=false;
    const auto* Tool=ActiveProductionTool();
    if (!Target.World.IsValid() || Target.Id.IsEmpty() || !Tool) return false;
    if (ColdSteelInventory::Text(*Tool,TEXT("tool_kind")) != Target.RequiredTool)
    { Message=TEXT("工具类型不匹配"); return false; }
    const int32 Before=HarvestProgress(Target.Id);
    const int32 Needed=Target.HitsNeeded();
    if (Before >= Needed) { Message=TEXT("此处资源已经采尽"); return false; }
    SyncRuntime(); auto P=Snapshot();
    const int32 After=Before+1;
    TArray<FString> Drops;
    if (After == Needed)
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
    Depleted=After == Needed;
    if(!Drops.IsEmpty())GetWorld()->GetSubsystem<UProductionHarvestSubsystem>()->DelayDrops(Drops,
        Target.Layer==0?FProductionTreeFallPlan::Make(Target).ReleaseSeconds():.25f);
    Message=Depleted ? (Target.Layer==0?TEXT("树木正在倒下，落地后对准木材按 E 拾取"):
        Target.Layer==1?TEXT("岩石已破碎，对准石材或矿石按 E 拾取"):TEXT("表土已采集，材料收入背包")) :
        FString::Printf(TEXT("%s  %d / %d"),*Target.Name,After,Needed);
    return true;
}
