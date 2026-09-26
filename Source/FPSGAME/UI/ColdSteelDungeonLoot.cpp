#include "ColdSteelDungeonLoot.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Math/RandomStream.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

#include "../Dungeons/DungeonRunSubsystem.h"
#include "ColdSteelStatusModel.h"

namespace
{
    /** dungeon_loot.json 的单条目：物品定义 id + 抽取权重 + 数量区间。 */
    struct FDungeonLootEntry
    {
        FString Id;
        double Weight = 1.0;
        int32 CountMin = 1;
        int32 CountMax = 1;
    };

    /** 单档位：min_depth（含）起生效；开箱 roll 次数 Rolls。 */
    struct FDungeonLootTier
    {
        int32 MinDepth = 0;
        int32 Rolls = 1;
        TArray<FDungeonLootEntry> Entries;
    };

    struct FDungeonLootTable
    {
        double FinalMultiplier = 3.0;
        TArray<FDungeonLootTier> Tiers;   // 按 MinDepth 升序
    };

    /** 一次性读取 Content/ColdSteelData/dungeon_loot.json（static 缓存+已读标志，与 ApplyDungeonEventBuff 同一口径，不做热重载）。 */
    const FDungeonLootTable& LootTable()
    {
        static FDungeonLootTable Table;
        static bool Loaded = false;
        if (Loaded) return Table;
        Loaded = true;

        const FString Path = FPaths::ProjectContentDir() / TEXT("ColdSteelData/dungeon_loot.json");
        FString Text;
        TSharedPtr<FJsonObject> Json;
        if (!FFileHelper::LoadFileToString(Text, *Path)
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Json) || !Json.IsValid())
        {
            UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] 战利品表不可用（缺失或解析失败）：%s"), *Path);
            return Table;
        }
        double Version = 1;
        if (Json->TryGetNumberField(TEXT("version"), Version) && Version != 1)
            UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] 战利品表 version=%g，按 version 1 口径继续解析。"), Version);
        Json->TryGetNumberField(TEXT("final_multiplier"), Table.FinalMultiplier);
        if (!(Table.FinalMultiplier > 0)) Table.FinalMultiplier = 3.0;

        const TArray<TSharedPtr<FJsonValue>>* Tiers = nullptr;
        if (Json->TryGetArrayField(TEXT("tiers"), Tiers))
            for (const TSharedPtr<FJsonValue>& TierValue : *Tiers)
            {
                const TSharedPtr<FJsonObject>* TierObject = nullptr;
                if (!TierValue.IsValid() || !TierValue->TryGetObject(TierObject) || !TierObject->IsValid()) continue;
                FDungeonLootTier Tier;
                double MinDepth = 0, Rolls = 1;
                (*TierObject)->TryGetNumberField(TEXT("min_depth"), MinDepth);
                (*TierObject)->TryGetNumberField(TEXT("rolls"), Rolls);
                Tier.MinDepth = FMath::Max(0, FMath::RoundToInt32(MinDepth));
                Tier.Rolls = FMath::Clamp(FMath::RoundToInt32(Rolls), 1, 16);

                const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
                if ((*TierObject)->TryGetArrayField(TEXT("entries"), Entries))
                    for (const TSharedPtr<FJsonValue>& EntryValue : *Entries)
                    {
                        const TSharedPtr<FJsonObject>* EntryObject = nullptr;
                        if (!EntryValue.IsValid() || !EntryValue->TryGetObject(EntryObject) || !EntryObject->IsValid()) continue;
                        FString Id;
                        if (!(*EntryObject)->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty()) continue;
                        FDungeonLootEntry Entry;
                        Entry.Id = Id;
                        double Weight = 1;
                        (*EntryObject)->TryGetNumberField(TEXT("weight"), Weight);
                        Entry.Weight = FMath::Max(0.0, Weight);
                        const TArray<TSharedPtr<FJsonValue>>* Count = nullptr;
                        if ((*EntryObject)->TryGetArrayField(TEXT("count"), Count) && Count->Num() >= 2
                            && (*Count)[0].IsValid() && (*Count)[1].IsValid())
                        {
                            Entry.CountMin = FMath::Max(1, FMath::RoundToInt32((*Count)[0]->AsNumber()));
                            Entry.CountMax = FMath::Max(Entry.CountMin, FMath::RoundToInt32((*Count)[1]->AsNumber()));
                        }
                        Tier.Entries.Add(MoveTemp(Entry));
                    }
                if (!Tier.Entries.IsEmpty()) Table.Tiers.Add(MoveTemp(Tier));
            }
        Table.Tiers.Sort([](const FDungeonLootTier& A, const FDungeonLootTier& B) { return A.MinDepth < B.MinDepth; });
        return Table;
    }
}

void FColdSteelDungeonLoot::GrantFromChest(AActor* Chest)
{
    if (!IsValid(Chest)) return;
    UWorld* World = Chest->GetWorld();
    if (!World || !World->IsGameWorld()) return;
    const UDungeonRunSubsystem* Run = UDungeonRunSubsystem::Get(World);
    if (!Run || !Run->IsRunActive()) return;   // 编辑器摆放的普通宝箱／非运行场景：开启行为完全不变

    // 房间节点：优先解析宝箱 Tags 里的 DungeonModule.<NodeId>.<ModuleId>（前缀精确匹配），失败用就近查询兜底。
    int32 NodeId = INDEX_NONE;
    static const FString ModulePrefix(TEXT("DungeonModule."));
    for (const FName& Tag : Chest->Tags)
    {
        const FString TagText = Tag.ToString();
        if (!TagText.StartsWith(ModulePrefix)) continue;
        FString IdText, ModuleId;
        if (!TagText.RightChop(ModulePrefix.Len()).Split(TEXT("."), &IdText, &ModuleId)) continue;
        if (!IdText.IsNumeric()) continue;
        const int32 Candidate = FCString::Atoi(*IdText);
        if (Run->NodeById(Candidate)) { NodeId = Candidate; break; }
    }
    if (NodeId == INDEX_NONE) NodeId = Run->NodeNearPosition(Chest->GetActorLocation());
    if (NodeId == INDEX_NONE)
        UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] 宝箱 %s 无法解析房间节点，按 Depth=0 档发放。"), *Chest->GetName());

    const FDungeonRunNode* Node = Run->NodeById(NodeId);
    const int32 Depth = Node ? Node->Depth : 0;

    // 最终宝箱：强制最高档且数量乘 final_multiplier（标签大小写不敏感比较）。
    bool bFinalTreasure = false;
    for (const FName& Tag : Chest->Tags)
        if (Tag.ToString().Equals(TEXT("DungeonFinalTreasure"), ESearchCase::IgnoreCase)) { bFinalTreasure = true; break; }

    const FDungeonLootTable& Table = LootTable();
    if (Table.Tiers.IsEmpty()) return;   // 表缺失/全空：加载时已警告，这里静默返回
    const FDungeonLootTier* Tier = &Table.Tiers[0];
    for (const FDungeonLootTier& Candidate : Table.Tiers)
        if (Candidate.MinDepth <= Depth) Tier = &Candidate;   // 取 min_depth ≤ Depth 的最高档（升序扫描）
    if (bFinalTreasure) Tier = &Table.Tiers.Last();

    // 全部随机经运行种子流：同 seed + 同宝箱节点可复现。
    FRandomStream Stream = Run->GameplayStream(DungeonRunDomains::ChestLoot ^ ((uint32)NodeId * 0x9E3779B9u));

    TArray<TPair<FString, int64>> Loot;
    for (int32 Roll = 0; Roll < Tier->Rolls; ++Roll)
    {
        double TotalWeight = 0;
        for (const FDungeonLootEntry& Entry : Tier->Entries) TotalWeight += Entry.Weight;
        if (TotalWeight <= 0) break;
        double Point = Stream.FRandRange(0.f, (float)TotalWeight);
        const FDungeonLootEntry* Picked = nullptr;
        for (const FDungeonLootEntry& Entry : Tier->Entries)
        {
            Point -= Entry.Weight;
            if (Point < 0) { Picked = &Entry; break; }
        }
        if (!Picked) Picked = &Tier->Entries.Last();
        const int64 Base = Stream.RandRange(Picked->CountMin, Picked->CountMax);
        const double Multiplier = bFinalTreasure ? Table.FinalMultiplier : (1.0 + Depth * 0.05);
        const int64 Count = FMath::Max<int64>(1, FMath::RoundToInt64(Base * Multiplier));
        // 同一物品多次抽中合并计数（保持首次出现顺序，播报稳定）。
        if (TPair<FString, int64>* Slot = Loot.FindByPredicate([&](const TPair<FString, int64>& P) { return P.Key == Picked->Id; }))
            Slot->Value += Count;
        else
            Loot.Emplace(Picked->Id, Count);
    }
    if (Loot.IsEmpty()) return;

    UGameInstance* GameInstance = World->GetGameInstance();
    UColdSteelStatusModel* Model = GameInstance ? GameInstance->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!Model)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] StatusModel 不可用，%d 条宝箱战利品未发放。"), Loot.Num());
        return;
    }

    // 展示名：复用档案子系统缓存的物品目录（items.json 首读归纳并缓存），缺失时回退定义 id。
    auto DisplayName = [&](const FString& Id) -> FString
    {
        for (const FColdSteelCatalogEntry& Entry : Model->ItemCatalog())
            if (Entry.Definition == Id && !Entry.Name.IsEmpty()) return Entry.Name;
        return Id;
    };

    TArray<FString> GrantedLines, FailedLines;
    for (const TPair<FString, int64>& Pair : Loot)
    {
        // AddItem 自动提交档案；弹药 id 走弹药袋（不占背包）；失败（背包满等）写 ResultMessage，只记日志不弹窗轰炸。
        if (Model->AddItem(Pair.Key, Pair.Value))
            GrantedLines.Add(FString::Printf(TEXT("%s x%lld"), *DisplayName(Pair.Key), Pair.Value));
        else
        {
            FailedLines.Add(FString::Printf(TEXT("%s x%lld（未发放）"), *DisplayName(Pair.Key), Pair.Value));
            UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] 发放失败 %s x%lld：%s"), *Pair.Key, Pair.Value, *Model->ResultMessage());
        }
    }

    FString Detail;
    for (const FString& Line : GrantedLines) Detail += Detail.IsEmpty() ? Line : TEXT("、") + Line;
    for (const FString& Line : FailedLines) Detail += Detail.IsEmpty() ? Line : TEXT("；") + Line;
    if (!Detail.IsEmpty())
        Model->PostNotice(bFinalTreasure ? TEXT("最终宝箱奖励") : TEXT("宝箱奖励"), Detail, FString(),
            (GrantedLines.Num() + FailedLines.Num()) > 3 ? 4.2f : 3.2f);
}
