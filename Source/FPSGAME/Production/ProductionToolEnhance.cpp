#include "ProductionToolEnhance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

/**
 * 采集工具强化目录（`ColdSteelData/tool-enhance.json`）。
 *
 * 惰性加载一次：首次调用时读盘，之后只读缓存，不依赖 GameInstance、不依赖 UI，
 * 因此在没有世界的离线入口（commandlet、自检）里也能调用。
 *
 * 目录里的 `cost`／`stats` 本次恒为空对象：这里刻意**不解析也不暴露**，避免任何
 * 假数值从加载器漏出去。素材（阶段 2）未到位时材质路径指向不存在的资产，本文件
 * 只返回路径字符串，不做加载——解析失败的降级由 `ProductionToolAppearance` 负责。
 */

namespace
{
    struct FToolEnhanceCatalog
    {
        TArray<FToolEnhanceLevel> Levels;
        FString MetalSlot=TEXT("Metal");
        FString WoodSlot=TEXT("Wood");
    };

    FToolEnhanceCatalog& Catalog()
    {
        static FToolEnhanceCatalog Loaded=[]()
        {
            FToolEnhanceCatalog Result;
            FString Text;TSharedPtr<FJsonObject> Root;
            if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tool-enhance.json")))
                ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)
            {UE_LOG(LogTemp,Warning,TEXT("Tool enhance catalog unavailable"));return Result;}
            Root->TryGetStringField(TEXT("metal_slot"),Result.MetalSlot);
            Root->TryGetStringField(TEXT("wood_slot"),Result.WoodSlot);
            const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
            if(!Root->TryGetArrayField(TEXT("levels"),Entries)||!Entries)
            {UE_LOG(LogTemp,Warning,TEXT("Tool enhance catalog has no levels"));return Result;}
            for(const auto& Value:*Entries)
            {
                const auto Entry=Value->AsObject();
                if(!Entry)continue;
                FToolEnhanceLevel Row;
                Entry->TryGetNumberField(TEXT("level"),Row.Level);
                if(Row.Level<=0)continue;
                Entry->TryGetStringField(TEXT("id"),Row.Id);
                Entry->TryGetStringField(TEXT("name"),Row.Name);
                Entry->TryGetStringField(TEXT("description"),Row.Description);
                const TSharedPtr<FJsonObject>* Materials=nullptr;
                // materials 按工具分开写：斧与镐的金属区面积、磨损方向不同，允许各自指向不同 MI。
                if(Entry->TryGetObjectField(TEXT("materials"),Materials)&&Materials)
                    for(const auto& Pair:(*Materials)->Values)
                        if(Pair.Value.IsValid())Row.Materials.Add(FString(Pair.Key),Pair.Value->AsString());   // 5.8 JSON SharedString 键需显式转 FString（C2665）
                Result.Levels.Add(MoveTemp(Row));
            }
            Result.Levels.Sort([](const FToolEnhanceLevel& A,const FToolEnhanceLevel& B){return A.Level<B.Level;});
            return Result;
        }();
        return Loaded;
    }
}

const TArray<FToolEnhanceLevel>& ColdSteelToolEnhance::Levels()
{
    return Catalog().Levels;
}

int32 ColdSteelToolEnhance::MaxLevel()
{
    // 目录缺失时按 1 级：与物品缺字段的缺省一致，UI 不会拿到 0 级。
    return FMath::Max(1,Levels().Num());
}

FString ColdSteelToolEnhance::MetalSlotName()
{
    return Catalog().MetalSlot;
}

const FToolEnhanceLevel* ColdSteelToolEnhance::Find(int32 Level)
{
    return Levels().FindByPredicate([Level](const FToolEnhanceLevel& Row){return Row.Level==Level;});
}

int32 ColdSteelToolEnhance::Level(const FColdSteelItem& Item)
{
    // 走工程既有 helper 读物品 Data，不自己解析 JSON 字符串。
    return FMath::Clamp(int32(ColdSteelInventory::Number(Item,TEXT("tool_enhance_level"),1)),1,MaxLevel());
}

bool ColdSteelToolEnhance::CanEnhance(const FColdSteelItem& Item,int32& OutNextLevel)
{
    const int32 Current=Level(Item);
    OutNextLevel=Current+1;
    return Current<MaxLevel();
}

FString ColdSteelToolEnhance::MetalMaterialPath(const FColdSteelItem& Item,int32 LevelOverride)
{
    const int32 Wanted=LevelOverride>0?FMath::Clamp(LevelOverride,1,MaxLevel()):Level(Item);
    const FToolEnhanceLevel* Row=Find(Wanted);
    if(!Row)return FString();
    // 未登记的工具（铁铲）没有 materials 键，返回空串即保持现有材质。
    const FString* Path=Row->Materials.Find(Item.Definition);
    return Path?*Path:FString();
}

FString ColdSteelToolEnhance::LevelName(int32 Level)
{
    const FToolEnhanceLevel* Row=Find(Level);
    return Row?Row->Name:FString();
}