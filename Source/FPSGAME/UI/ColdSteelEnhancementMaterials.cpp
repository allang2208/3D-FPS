#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "Serialization/JsonSerializer.h"

bool UColdSteelStatusModel::GrantEnhancementMaterials()
{
    if(Current.EnhancementSupplyVersion>=1)return true;
    SyncRuntime();auto Next=Snapshot();
    for(const TCHAR* Definition:{TEXT("enhancement_stone"),TEXT("magic_dust")})
    {
        const auto Template=CreateItem(Definition);
        if(Template.Data.IsEmpty()||Template.StackMax!=99999)return false;
        int64 Stored=0;
        for(auto& Item:Next.Items)if(Item.Definition==Definition)
        {
            // Update only definition-owned presentation/stack fields; preserve identity and instance metadata.
            TSharedPtr<FJsonObject> Data,Base;
            if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Template.Data),Base))return false;
            for(const TCHAR* Key:{TEXT("category"),TEXT("type"),TEXT("icon"),TEXT("ue_icon"),TEXT("stack_max")})Data->SetField(Key,Base->TryGetField(Key));
            Data->SetNumberField(TEXT("maxStack"),99999);Item.StackMax=99999;
            Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));
            if(Item.Place==4)Stored+=Item.Count;
        }
        // One-time top-up. Existing excess is preserved; consumed materials are never regenerated on reopening.
        if(Stored<99999&&!ColdSteelWarehouse::Insert(Next.Items,CreateItem(Definition,99999-Stored),WarehouseCapacity()))
        {Message=TEXT("仓库空间不足，强化材料尚未发放");return false;}
    }
    Next.EnhancementSupplyVersion=1;
    return CommitState(Next);
}
