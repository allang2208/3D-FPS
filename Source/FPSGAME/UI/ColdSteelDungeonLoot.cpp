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

TArray<FColdSteelDungeonLootPreview> FColdSteelDungeonLoot::PreviewItems()
{
    const auto& Table=LootTable();
    TArray<FColdSteelDungeonLootPreview> Result;
    for(int32 I=0;I<Table.Tiers.Num();++I)
        for(const auto& Entry:Table.Tiers[I].Entries)
        {
            if(Entry.Weight<=0)continue;
            auto* Existing=Result.FindByPredicate([&](const auto& Row){return Row.Definition==Entry.Id;});
            if(!Existing)
            {
                Result.Add({Entry.Id,Table.Tiers[I].MinDepth,false});
                Existing=&Result.Last();
            }
            Existing->bInFinalTier|=I==Table.Tiers.Num()-1;
        }
    return Result;
}

double FColdSteelDungeonLoot::FinalQuantityMultiplier(){return LootTable().FinalMultiplier;}

namespace
{
    /** 宝箱上下文：房间节点（Tags 前缀精确匹配优先，就近查询兜底）、深度、最终箱标记、领取键。
     *  DungeonTreasure.HubTest 标签＝主神空间测试箱：无运行上下文也可 roll（固定种子，Depth 0 档）。 */
    struct FChestLootContext
    {
        FString ClaimId;
        bool bFinalTreasure=false;
        bool bHubTest=false;
        int32 Depth=0;
        const FDungeonRunNode* Node=nullptr;
        UDungeonRunSubsystem* Run=nullptr;
    };

    bool ResolveChestContext(AActor* Chest,FChestLootContext& Out)
    {
        UWorld* World=Chest?Chest->GetWorld():nullptr;
        if(!World||!World->IsGameWorld())return false;
        Out.Run=UDungeonRunSubsystem::Get(World);
        Out.bHubTest=Chest->ActorHasTag(TEXT("DungeonTreasure.HubTest"));
        if(!Out.Run||(!Out.Run->IsRunActive()&&!Out.bHubTest))return false;

        int32 NodeId=INDEX_NONE;
        static const FString ModulePrefix(TEXT("DungeonModule."));
        for (const FName& Tag : Chest->Tags)
        {
            const FString TagText = Tag.ToString();
            if (!TagText.StartsWith(ModulePrefix)) continue;
            FString IdText, ModuleId;
            if (!TagText.RightChop(ModulePrefix.Len()).Split(TEXT("."), &IdText, &ModuleId)) continue;
            if (!IdText.IsNumeric()) continue;
            const int32 Candidate = FCString::Atoi(*IdText);
            if (Out.Run->NodeById(Candidate)) { NodeId = Candidate; break; }
        }
        if (NodeId == INDEX_NONE) NodeId = Out.Run->NodeNearPosition(Chest->GetActorLocation());
        if (NodeId == INDEX_NONE&&!Out.bHubTest)
            UE_LOG(LogTemp, Warning, TEXT("[DungeonLoot] 宝箱 %s 无法解析房间节点，按 Depth=0 档发放。"), *Chest->GetName());

        Out.Node=Out.Run->NodeById(NodeId);
        Out.Depth=Out.Node?Out.Node->ProgressionDepth:0;
        for (const FName& Tag : Chest->Tags)
            if (Tag.ToString().Equals(TEXT("DungeonFinalTreasure"), ESearchCase::IgnoreCase)) { Out.bFinalTreasure = true; break; }
        Out.ClaimId=Out.Node&&!Out.Node->MissionId.IsEmpty()?Out.Node->MissionId:FString::Printf(TEXT("Node%d"),NodeId);
        Out.ClaimId+=Out.bFinalTreasure?TEXT(".final_chest"):TEXT(".chest");
        for(FName Tag:Chest->Tags)if(Tag.ToString().StartsWith(TEXT("DungeonChestClaim.")))
        {Out.ClaimId=Tag.ToString().RightChop(18);break;}
        return true;
    }
}

FString FColdSteelDungeonLoot::ChestStorageKey(AActor* Chest)
{
    FChestLootContext Ctx;
    if(!ResolveChestContext(Chest,Ctx))return FString();
    return TEXT("DungeonChest.")+Ctx.ClaimId;
}

bool FColdSteelDungeonLoot::StoreFromChest(AActor* Chest,FString& OutContainerKey)
{
    OutContainerKey.Empty();
    if(!IsValid(Chest))return false;
    FChestLootContext Ctx;
    if(!ResolveChestContext(Chest,Ctx))return true; // 非运行场景：不发放不开面板，与旧行为一致

    UGameInstance* GameInstance=Chest->GetWorld()->GetGameInstance();
    UColdSteelStatusModel* Model=GameInstance?GameInstance->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model)
    {
        UE_LOG(LogTemp,Warning,TEXT("[DungeonLoot] StatusModel 不可用，宝箱战利品未写入。"));
        return false;
    }
    const FName Claim(*Ctx.ClaimId);
    OutContainerKey=TEXT("DungeonChest.")+Ctx.ClaimId;
    // 重复开箱：领取标记在案即不重 roll——roll 流可复现，但重写会把弹药池条目再发一遍。
    // 测试箱（主神空间）例外：战利品已被取空＝解除标记，这次开箱重新 roll，方便反复实测。
    if(Model->HasDungeonClaim(Claim))
        if(!(Ctx.bHubTest&&Model->ReleaseHubTestClaimIfEmpty(OutContainerKey,Claim)))return true;

    const FDungeonLootTable& Table=LootTable();
    if(Table.Tiers.IsEmpty())return false;
    const FDungeonLootTier* Tier=&Table.Tiers[0];
    for(const FDungeonLootTier& Candidate:Table.Tiers)
        if(Candidate.MinDepth<=Ctx.Depth)Tier=&Candidate;   // 取 min_depth ≤ Depth 的最高档（升序扫描）
    if(Ctx.bFinalTreasure)Tier=&Table.Tiers.Last();

    // 全部随机经运行种子流：同 seed + 同宝箱节点可复现；测试箱无运行上下文，用领取键散列做固定种子。
    FRandomStream Stream=Ctx.Run
        ?Ctx.Run->GameplayStream(DungeonRunDomains::ChestLoot^GetTypeHash(Ctx.ClaimId))
        :FRandomStream(static_cast<int32>(DungeonRunDomains::ChestLoot^GetTypeHash(Ctx.ClaimId)));
    TArray<TPair<FString,int64>> Loot;
    for(int32 Roll=0;Roll<Tier->Rolls;++Roll)
    {
        double TotalWeight=0;
        for(const FDungeonLootEntry& Entry:Tier->Entries)TotalWeight+=Entry.Weight;
        if(TotalWeight<=0)break;
        double Point=Stream.FRandRange(0.f,(float)TotalWeight);
        const FDungeonLootEntry* Picked=nullptr;
        for(const FDungeonLootEntry& Entry:Tier->Entries)
        {
            Point-=Entry.Weight;
            if(Point<0){Picked=&Entry;break;}
        }
        if(!Picked)Picked=&Tier->Entries.Last();
        const int64 Base=Stream.RandRange(Picked->CountMin,Picked->CountMax);
        const double Multiplier=Ctx.bFinalTreasure?Table.FinalMultiplier:(1.0+Ctx.Depth*0.05)*(Ctx.Node?Ctx.Node->RewardMultiplier:1.);
        const int64 Count=FMath::Max<int64>(1,FMath::RoundToInt64(Base*Multiplier));
        // 同一物品多次抽中合并计数（保持首次出现顺序）。
        if(TPair<FString,int64>* Slot=Loot.FindByPredicate([&](const TPair<FString,int64>& P){return P.Key==Picked->Id;}))
            Slot->Value+=Count;
        else
            Loot.Emplace(Picked->Id,Count);
    }
    if(Loot.IsEmpty())return false;
    // 一页仓库面板；不再直接进背包、不再播报——面板与取出交互由仓库规则承担。
    return Model->StoreDungeonChestLoot(Ctx.Run?Ctx.Run->RunId():FString(),Claim,Loot,OutContainerKey,1,Ctx.bHubTest);
}
