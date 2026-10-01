#include "DungeonSpawnDirector.h"
#include "DungeonRoomEncounter.h"
#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/FleshHandMonster.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterDamageAlert.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Engine.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "TimerManager.h"

namespace
{
    // 节点混合常量（黄金比）：与编成/落点域常量异或后派生每房独立流，
    // 保证同一 seed + 同一域 + 同一节点逐位可复现，且与布局/dressing/水渍流互不干扰。
    constexpr float PatrolSeconds = .25f;         // 休眠管理 + 房间状态巡检
    constexpr float RoomRetrySeconds = 10.f;      // 落点失败的房间重试（村庄 spawner 口径）
    constexpr int32 SpawnDirectorMaxSlotAttempts = 3; // 同槽最多 3 次，仍失败则放弃该槽
    constexpr int32 MaxCountPerRoom = 12;
    constexpr float MinPlayerDistance = 1500.f;   // 落点与玩家的最小距离
    constexpr float PlayerEyeOffset = 60.f;
    constexpr float MinGroundNormalZ = .94f;      // 坡度闸门（村庄 spawner 口径）
    constexpr int32 ScatterSamples = 24;          // 散点兜底的采样次数
    constexpr int32 ScatterKeep = 8;              // 散点兜底最多保留的候选
    constexpr double ScatterMargin = 150.0;       // 散点距房间体积边界的最小内缩
    constexpr float AlertSeconds = 12.f;          // 相邻房临时唤醒窗口（对齐 AI 记忆 MemorySeconds）
    constexpr int32 EliteLevelBonus = 2;
    constexpr int32 MaxDepthLevelBonus = 4;

    TAutoConsoleVariable<int32> DungeonSpawnGlobalCap(TEXT("fps.Dungeon.Spawn.GlobalCap"), 12,
        TEXT("地牢刷怪导演的全局存活怪上限。达到上限只延后生成，绝不销毁已生成的怪。"));

    UWorld* ContextWorld(const UObject* WorldContext)
    {
        return GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    }

    EMonsterRank RankFromJson(const FString& Value)
    {
        const FString V = Value.TrimStartAndEnd().ToLower();
        if (V == TEXT("elite")) return EMonsterRank::Elite;
        if (V == TEXT("lord")) return EMonsterRank::Lord;
        if (V == TEXT("boss")) return EMonsterRank::Boss;
        if (V == TEXT("minor")) return EMonsterRank::Minor;
        return EMonsterRank::Normal;
    }

    /** 目录 spawn.pool 的一条候选（.cpp 局部，不进反射）。 */
    struct FPoolEntry
    {
        FString Id;
        FString ClassPath;
        double Weight = 1.0;
        int32 Level = 0;
        EMonsterRank Rank = EMonsterRank::Normal;
        bool bRank = false;
    };

    // 普通池基类约束：四家族基类（护士系/狼系/手脑/毒蛆，胖子·突变体·巫婆走护士系，
    // 感染犬走狼系）+ 共用战斗组件。CDO 的 OwnedComponents 不一定齐备，因此按家族公开字段判定。
    bool HasMonsterCombat(const AActor* Actor)
    {
        if (const auto* N = Cast<ANurseZombie>(Actor)) return N->Combat != nullptr;
        if (const auto* W = Cast<AWolfMonster>(Actor)) return W->Combat != nullptr;
        if (const auto* F = Cast<AFleshHandMonster>(Actor)) return F->Combat != nullptr;
        if (const auto* H = Cast<AHandBrainMonster>(Actor)) return H->Combat != nullptr;
        if (const auto* M = Cast<APoisonMaggotMonster>(Actor)) return M->Combat != nullptr;
        return false;
    }
}

ADungeonSpawnDirector::ADungeonSpawnDirector()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SpawnDirectorRoot"));
    // 全定时器驱动：0.25s 巡检 + 每房 10s 落点重试，绝不逐帧 Tick。
    PrimaryActorTick.bCanEverTick = false;
    Tags.Add(TEXT("DungeonSpawnDirector"));
}

void ADungeonSpawnDirector::Configure(AAuthoredDungeonGenerator* InGenerator)
{
    Generator = InGenerator;
    Run = UDungeonRunSubsystem::Get(GetWorld());
    if (!Run.IsValid())
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] Configure 时世界尚无 UDungeonRunSubsystem，Activate 会再取一次。"));
}

void ADungeonSpawnDirector::Activate()
{
    UWorld* World = GetWorld();
    // 与 Boss 遭遇同款两段式守卫：只在 authority 的游戏世界武装，编辑器预览生成一律不刷怪。
    if (!World || !World->IsGameWorld() || !HasAuthority() || bArmed) return;
    if (!Run.IsValid()) Run = UDungeonRunSubsystem::Get(World);
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!Sub || !Sub->IsRunActive())
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 运行服务未绑定或本局未激活，导演不武装。"));
        return;
    }
    bArmed = true;
    if (!bPlanned) { PlanOpening(); bPlanned = true; }
    GetWorldTimerManager().SetTimer(PatrolTimer, this, &ADungeonSpawnDirector::Patrol, PatrolSeconds, true);
    int32 Rooms = 0, Members = 0, Elites = 0;
    for (const FDungeonRoomSpawnPlan& Plan : Plans)
    {
        ++Rooms; Members += Plan.Slots.Num(); if (Plan.bElite) ++Elites;
    }
    UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 武装：房间计划 %d 间 / 编成 %d 只 / 精英房 %d 间（Seed=%d RunId=%s 生成器=%s）"),
        Rooms, Members, Elites, Sub->RunSeed(), *Sub->RunId(),
        Generator.IsValid() ? *Generator->GetPathName() : TEXT("<none>"));
}

void ADungeonSpawnDirector::PlanOpening()
{
    UWorld* World = GetWorld();
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!World || !Sub || !Sub->IsRunActive()) return;
    Plans.Reset();

    // 目录 spawn 段的每房配方（.cpp 局部）：数量区间 + 加权池。
    struct FRoomRecipe { int32 PlanIndex = INDEX_NONE; int32 NodeId = INDEX_NONE; int32 MinCount = 2; int32 MaxCount = 4; TArray<FPoolEntry> Pool; double TotalWeight = 0.0; };
    TArray<FRoomRecipe> Recipes;

    // 1) 候选房：战斗房、非 Boss 区、未清除、有 spawn 配置且能求出落点。
    //    无 spawn 配置的房 = 安静房，按契约跳过且不视为错误。
    TArray<int32> Eligible;
    for (const FDungeonRunNode& Node : Sub->AllNodes())
    {
        if (Node.Id == INDEX_NONE || Node.bConnector || !Node.bCombatRoom || Node.bBossArea) continue;
        if (Sub->IsRoomCleared(Node.Id)) continue;
        const TSharedPtr<FJsonObject>* ConfigPtr = Sub->SpawnConfigForModule(Node.Module);
        if (!ConfigPtr || !ConfigPtr->IsValid()) continue;
        const TSharedPtr<FJsonObject>& Config = *ConfigPtr;

        FRoomRecipe Recipe;
        Recipe.NodeId = Node.Id;
        const TArray<TSharedPtr<FJsonValue>>* CountArray = nullptr;
        if (Config->TryGetArrayField(TEXT("count"), CountArray) && CountArray && CountArray->Num() >= 2)
        {
            Recipe.MinCount = FMath::Clamp((int32)((*CountArray)[0]->AsNumber()), 0, MaxCountPerRoom);
            Recipe.MaxCount = FMath::Clamp((int32)((*CountArray)[1]->AsNumber()), Recipe.MinCount, MaxCountPerRoom);
        }
        const TArray<TSharedPtr<FJsonValue>>* PoolArray = nullptr;
        if (Config->TryGetArrayField(TEXT("pool"), PoolArray) && PoolArray)
        {
            for (const TSharedPtr<FJsonValue>& Value : *PoolArray)
            {
                const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
                if (!Entry.IsValid()) continue;
                FPoolEntry Pool;
                Entry->TryGetStringField(TEXT("id"), Pool.Id);
                if (!Entry->TryGetStringField(TEXT("class"), Pool.ClassPath) || Pool.ClassPath.IsEmpty()) continue;
                double Weight = 1.0;
                Entry->TryGetNumberField(TEXT("weight"), Weight);
                Pool.Weight = Weight > 0.0 ? Weight : 0.0;
                double Level = 0.0;
                if (Entry->TryGetNumberField(TEXT("level"), Level)) Pool.Level = FMath::Max(1, (int32)Level);
                FString Rank;
                if (Entry->TryGetStringField(TEXT("rank"), Rank)) { Pool.Rank = RankFromJson(Rank); Pool.bRank = true; }
                Recipe.TotalWeight += Pool.Weight;
                Recipe.Pool.Add(MoveTemp(Pool));
            }
        }
        if (Recipe.Pool.IsEmpty() || Recipe.TotalWeight <= 0.0)
        {
            UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 房 %d（%s）的 spawn 配置没有可用池，跳过该房。"), Node.Id, *Node.Module);
            continue;
        }

        // Every configured room owns an entry encounter. Empty candidate sets
        // are resolved by its bounded spawn-failure policy, not silently skipped.
        TArray<FString> AnchorRoles;
        const TArray<TSharedPtr<FJsonValue>>* Roles = nullptr;
        if (Config->TryGetArrayField(TEXT("anchor_roles"), Roles) && Roles)
            for (const TSharedPtr<FJsonValue>& Value : *Roles)
                if (Value.IsValid() && Value->Type == EJson::String) AnchorRoles.Add(Value->AsString());
        if (AnchorRoles.IsEmpty()) AnchorRoles.Add(TEXT("encounter"));

        FDungeonRoomSpawnPlan Plan;
        Plan.NodeId = Node.Id;
        Plan.Module = Node.Module;
        Plan.Route = Node.Route;
        Plan.Depth = Node.ProgressionDepth;
        Plan.Center = Node.Volume.IsValid ? Node.Volume.GetCenter() : Node.Origin;
        BuildRoomCandidates(this, Sub, Node.Id, AnchorRoles, Plan.Candidates);
        Recipe.PlanIndex = Plans.Add(MoveTemp(Plan));
        Eligible.Add(Node.Id);
        Recipes.Add(MoveTemp(Recipe));
    }

    // 2) 精英房：每条支线抽 1 间（深度较深者优先），整组交给封门遭遇。
    TArray<int32> EliteNodes;
    SelectEliteRooms(Eligible, EliteNodes);

    // 3) 逐房编成（独立流，与房序无关）+ 精英房的封门遭遇。
    for (const FRoomRecipe& Recipe : Recipes)
    {
        if (!Plans.IsValidIndex(Recipe.PlanIndex)) continue;
        FDungeonRoomSpawnPlan& Plan = Plans[Recipe.PlanIndex];
        const FDungeonRunNode* Node = Sub->NodeById(Recipe.NodeId);
        if (!Node) continue;
        Plan.bElite = EliteNodes.Contains(Recipe.NodeId);

        FRandomStream Composition = Sub->GameplayStream(DungeonRunDomains::SpawnComposition ^ Sub->NodeRandomSalt(Recipe.NodeId));
        const int32 Count = FMath::Min(MaxCountPerRoom,Composition.RandRange(Recipe.MinCount, Recipe.MaxCount) + (Plan.bElite ? 1 : 0));
        if (Count <= 0)
        {
            Plan.bCleared = true;
            Sub->MarkRoomCleared(Recipe.NodeId);
            UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 房 %d 配置为零怪，保持开放并登记清除。"), Recipe.NodeId);
            continue;
        }
        // 深度加成 +1 级 / 每 4 深度，封顶 +4；精英房再 +2 并整组 Elite 品阶。
        const int32 DepthBonus = FMath::Clamp(Node->ProgressionDepth / 4, 0, MaxDepthLevelBonus);
        for (int32 Index = 0; Index < Count; ++Index)
        {
            // 加权抽取：只消费本房的编成流，同一 seed 必须可复现。
            double Roll = (double)Composition.FRand() * Recipe.TotalWeight;
            const FPoolEntry* Chosen = &Recipe.Pool.Last();
            for (const FPoolEntry& Entry : Recipe.Pool)
            {
                Roll -= Entry.Weight;
                if (Roll <= 0.0) { Chosen = &Entry; break; }
            }
            FDungeonSpawnSlot Slot;
            Slot.Member.Id = Chosen->Id;
            Slot.Member.ClassPath = Chosen->ClassPath;
            Slot.Member.Level = Chosen->Level;
            Slot.Member.LevelBonus = DepthBonus + Node->ThreatBonus + (Plan.bElite ? EliteLevelBonus : 0);
            Slot.Member.bOverrideRank = Plan.bElite || Chosen->bRank;
            Slot.Member.Rank = Plan.bElite ? EMonsterRank::Elite : Chosen->Rank;
            Plan.Slots.Add(MoveTemp(Slot));
        }
        if (Plan.Slots.IsEmpty()) continue;

        // Ordinary, transition and authored progression rooms all seal during
        // their wave. Their original progression shutters retain their own rules.
        FVector DoorCenter = FVector::ZeroVector, DoorNormal = FVector::ZeroVector;
        const int32 Entry = Sub->EntryConnectorFor(Recipe.NodeId);
        const bool bDoor = Entry != INDEX_NONE && Sub->EstimateDoorway(Recipe.NodeId, Entry, DoorCenter, DoorNormal);
        if (!bDoor)
            UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 遭遇房 %d 主入口估算失败：使用房间体积触发，按真实连接门封闸。"), Recipe.NodeId);
        const FRotator Facing = bDoor ? FRotator(0, DoorNormal.Rotation().Yaw, 0) : FRotator::ZeroRotator;
        const FTransform At(Facing, bDoor ? DoorCenter : Plan.Center);
        FActorSpawnParameters Params;
        Params.Owner = this;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Encounter = World->SpawnActor<ADungeonRoomEncounter>(ADungeonRoomEncounter::StaticClass(), At, Params);
        if (!Encounter)
        {
            UE_LOG(LogTemp, Error, TEXT("[DungeonSpawn] 遭遇房 %d 的封门遭遇创建失败，退化为普通房刷怪。"), Recipe.NodeId);
            Plan.bElite = false;
            continue;
        }
        Owned.Add(Encounter);
        TArray<FDungeonSpawnMember> Group;
        for (const FDungeonSpawnSlot& Slot : Plan.Slots) Group.Add(Slot.Member);
        Encounter->Configure(Sub, Recipe.NodeId, Group, DoorCenter, DoorNormal, Plan.Candidates, true);
        Encounter->Activate();
        Plan.Encounter = Encounter;
        Plan.bHandledByEncounter = true;
        UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 遭遇房 %d（%s，深度 %d）：编成 %d 只，进房封闭全部连接门，清除后开门。"),
            Recipe.NodeId, *Plan.Module, Plan.Depth, Group.Num());
    }
}

void ADungeonSpawnDirector::SelectEliteRooms(const TArray<int32>& Eligible, TArray<int32>& OutEliteNodes)
{
    OutEliteNodes.Reset();
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!Sub || Eligible.IsEmpty()) return;
    // Mission roles own elite intent; route names are only a legacy fallback.
    bool HasMission=false;
    for(int32 Id:Eligible)if(const auto* Node=Sub->NodeById(Id);Node&&!Node->EncounterRole.IsEmpty())
    {HasMission=true;if(Node->EncounterRole==TEXT("risk_elite"))OutEliteNodes.Add(Id);}
    if(HasMission)return;
    FRandomStream Stream = Sub->GameplayStream(DungeonRunDomains::EliteSelection);
    TArray<FString> Routes;
    for(int32 Id:Eligible)if(const auto* Node=Sub->NodeById(Id);Node&&Node->Route!=TEXT("Approach"))Routes.AddUnique(Node->Route);
    Routes.Sort();
    for (const FString& Prefix : Routes)
    {
        TArray<int32> Group;
        for (int32 NodeId : Eligible)
        {
            const FDungeonRunNode* Node = Sub->NodeById(NodeId);
            if (Node && Node->Route==Prefix) Group.Add(NodeId);
        }
        if (Group.IsEmpty()) continue;
        // 深度较深者优先：稳定排序（深度、节点号）后取后半再随机。
        Group.StableSort([Sub](const int32 A, const int32 B)
        {
            const FDungeonRunNode* NA = Sub->NodeById(A);
            const FDungeonRunNode* NB = Sub->NodeById(B);
            const int32 DA = NA ? NA->ProgressionDepth : 0;
            const int32 DB = NB ? NB->ProgressionDepth : 0;
            return DA != DB ? DA < DB : A < B;
        });
        OutEliteNodes.Add(Group[Stream.RandRange(Group.Num() / 2, Group.Num() - 1)]);
    }
}

void ADungeonSpawnDirector::Patrol()
{
    UWorld* World = GetWorld();
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!World || !bArmed || !Sub || !Sub->IsRunActive()) return;

    // 相邻房的临时唤醒窗口到期即收回（警报房本身本 run 不再休眠）。
    const double Now = World->GetTimeSeconds();
    for (auto It = AlertUntil.CreateIterator(); It; ++It) if (It.Value() < Now) It.RemoveCurrent();

    APawn* Player = PlayerPawn(this);
    const FVector PlayerAt = Player ? Player->GetActorLocation() : Sub->EntryPosition();
    TArray<int32> Active;
    if (Player) Sub->CollectActiveRooms(PlayerAt, Active);

    for (int32 Index = 0; Index < Plans.Num(); ++Index)
    {
        FDungeonRoomSpawnPlan& Plan = Plans[Index];
        const auto* RoomNode=Sub->NodeById(Plan.NodeId);
        if (Player&&RoomNode&&RoomNode->DistanceSquared(PlayerAt)<=FMath::Square(100.) && !Plan.bExplored)
        {
            Plan.bExplored = true;
            Sub->MarkRoomExplored(Plan.NodeId);
        }
        // 精英组由封门遭遇持有：生成即唤醒态，导演不做休眠，只负责清房登记。
        if (Plan.bHandledByEncounter) { CheckRoomCleared(Index); continue; }
        const bool bWantAwake = Plan.bAlarmed || Active.Contains(Plan.NodeId) || AlertUntil.Contains(Plan.NodeId);
        for (FDungeonSpawnSlot& Slot : Plan.Slots)
        {
            ACharacter* Monster = Slot.Monster.Get();
            if (!Slot.bFilled || !IsValid(Monster)) continue;
            if (bWantAwake)
            {
                if (!Slot.bAwake) { WakeMonster(Monster); Slot.bAwake = true; }
            }
            // 死亡/交战中的怪本轮跳过（SleepMonster 返回 false），下个巡检再试，不打断攻击。
            else if (Slot.bAwake && SleepMonster(Monster)) Slot.bAwake = false;
        }
        CheckRoomCleared(Index);
    }

    // 生成摊帧 + 就近优先：每 tick 最多推进一间房。全局上限满或整房在玩家闸门内时，
    // 本轮什么都不做，下个巡检（0.25s）自然再试——绝不销毁已生成的怪。
    if (AliveCount() >= OrdinarySpawnLimit()) return;
    int32 Best = INDEX_NONE;
    double BestDistance = TNumericLimits<double>::Max();
    for (int32 Index = 0; Index < Plans.Num(); ++Index)
    {
        const FDungeonRoomSpawnPlan& Plan = Plans[Index];
        if (Plan.bCleared || Plan.bHandledByEncounter || !HasPending(Plan)) continue;
        if (GetWorldTimerManager().IsTimerActive(Plan.RetryTimer)) continue;   // 10s 重试窗口内不打断
        const double Distance = FVector::DistSquared(PlayerAt, Plan.Center);
        if (Distance < FMath::Square((double)MinPlayerDistance)) continue;    // 不消耗槽位尝试次数
        if (Distance < BestDistance) { BestDistance = Distance; Best = Index; }
    }
    if (Best != INDEX_NONE) AttemptRoomSpawns(Best);
}

void ADungeonSpawnDirector::AttemptRoomSpawns(int32 RoomIndex)
{
    UWorld* World = GetWorld();
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!World || !Sub || !bArmed || !Plans.IsValidIndex(RoomIndex)) return;
    FDungeonRoomSpawnPlan& Plan = Plans[RoomIndex];
    GetWorldTimerManager().ClearTimer(Plan.RetryTimer);
    if (Plan.bCleared || Plan.bHandledByEncounter || Plan.Candidates.IsEmpty() || !HasPending(Plan)) return;

    const int32 Cap = OrdinarySpawnLimit();
    int32 Alive = AliveCount();
    APawn* Player = PlayerPawn(this);
    TArray<int32> Active;
    if (Player) Sub->CollectActiveRooms(Player->GetActorLocation(), Active);
    // 落地即醒只给警报房/活动房；其余按休眠配方落地，等玩家靠近再唤醒。
    const bool bAwake = Plan.bAlarmed || Active.Contains(Plan.NodeId) || AlertUntil.Contains(Plan.NodeId);
    bool bCapBlocked = false, bPlayerBlocked = false, bPlacementFailed = false;

    for (int32 Index = 0; Index < Plan.Slots.Num(); ++Index)
    {
        FDungeonSpawnSlot& Slot = Plan.Slots[Index];
        if (Slot.bGivenUp || Slot.bFilled) continue;
        if (Alive >= Cap) { bCapBlocked = true; break; }
        if (!ResolveMonsterClass(Slot.Member.ClassPath))
        {
            // 类不可解析/资产不齐：重试没有意义，直接放弃该槽。
            Slot.bGivenUp = true;
            UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 房 %d 槽 %d 的怪物类不可用，放弃：%s"), Plan.NodeId, Index, *Slot.Member.ClassPath);
            continue;
        }
        ACharacter* Monster = nullptr;
        bool bSlotPlayerBlocked=false,bSlotPlacementFailed=false;
        for (int32 Try = 0; Try < Plan.Candidates.Num(); ++Try)
        {
            const FVector Ground = Plan.Candidates[Plan.NextCandidate % Plan.Candidates.Num()];
            ++Plan.NextCandidate;
            if (!PlayerGateAllows(World, Ground, MinPlayerDistance)) { bSlotPlayerBlocked = true; continue; }
            Monster = SpawnMonsterAtGround(World, this, Slot.Member, Ground, YawToward(Ground, Plan.Center), bAwake,
                Sub->EnemySlotTag(Plan.NodeId, Index),Sub->NodeById(Plan.NodeId));
            if (Monster) break;
            bSlotPlacementFailed = true;
        }
        if (Monster)
        {
            Slot.Monster = Monster;
            Slot.bFilled = true;
            Slot.bAwake = bAwake;
            ++Alive;
            Owned.Add(Monster);
            Monster->OnDestroyed.AddDynamic(this, &ADungeonSpawnDirector::OnMonsterDestroyed);
            Monster->OnTakeAnyDamage.AddDynamic(this, &ADungeonSpawnDirector::OnMonsterDamaged);
            UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 房 %d 槽 %d 生成 %s%s @ %s"), Plan.NodeId, Index,
                *Slot.Member.ClassPath, bAwake ? TEXT("（醒）") : TEXT("（休眠）"), *Monster->GetActorLocation().ToString());
        }
        else if (bSlotPlacementFailed && !bSlotPlayerBlocked && !bCapBlocked)
        {
            ++Slot.Attempts;
            if (Slot.Attempts >= SpawnDirectorMaxSlotAttempts)
            {
                Slot.bGivenUp = true;
                UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 房 %d 槽 %d 连续 %d 次落点/资产校验失败，放弃该槽：%s"),
                    Plan.NodeId, Index, Slot.Attempts, *Slot.Member.ClassPath);
            }
        }
        bPlacementFailed|=!Monster&&bSlotPlacementFailed;
        bPlayerBlocked|=!Monster&&bSlotPlayerBlocked;
        if (bPlayerBlocked || bCapBlocked) break;
    }

    // 玩家闸门/全局上限造成的延后交给 0.25s 巡检；真正的落点失败走每房 10s 重试定时器。
    if (bPlacementFailed && !bCapBlocked && !bPlayerBlocked && !Plan.bCleared && HasPending(Plan))
        GetWorldTimerManager().SetTimer(Plan.RetryTimer,
            FTimerDelegate::CreateUObject(this, &ADungeonSpawnDirector::AttemptRoomSpawns, RoomIndex), RoomRetrySeconds, false);
    CheckRoomCleared(RoomIndex);
}

void ADungeonSpawnDirector::CheckRoomCleared(int32 RoomIndex)
{
    if (!Plans.IsValidIndex(RoomIndex)) return;
    FDungeonRoomSpawnPlan& Plan = Plans[RoomIndex];
    if (Plan.bCleared) return;
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!Sub) return;

    if (Plan.bHandledByEncounter)
    {
        // 精英房的清房判定由封门遭遇持有；这里只补登记，并幂等地催一次开门。
        auto* Encounter = Plan.Encounter.Get();
        if (!IsValid(Encounter) || !Encounter->IsCleared()) return;
        Plan.bCleared = true;
        Sub->MarkRoomCleared(Plan.NodeId);
        Encounter->OpenGate();
        return;
    }
    if (Plan.Slots.IsEmpty() || HasPending(Plan)) return;
    for (const FDungeonSpawnSlot& Slot : Plan.Slots)
        if (Slot.bFilled && !IsMonsterDead(Slot.Monster.Get())) return;

    // 全员 Combat->IsDead()（尸体销毁即视为死亡，不等 15s 回收）→ 本 run 不重生。
    Plan.bCleared = true;
    GetWorldTimerManager().ClearTimer(Plan.RetryTimer);
    int32 Spawned = 0;
    for (FDungeonSpawnSlot& Slot : Plan.Slots)
    {
        if (Slot.bFilled) ++Spawned;
        else Slot.bGivenUp = true;   // 停止该房后续重试
    }
    if (Spawned == 0)
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 房 %d 没有任何怪成功落地即判清空。"), Plan.NodeId);
    Sub->MarkRoomCleared(Plan.NodeId);
    UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 房 %d 清空（%d 只）。"), Plan.NodeId, Spawned);
}

void ADungeonSpawnDirector::OnMonsterDamaged(AActor* DamagedActor, float /*Damage*/, const UDamageType* /*DamageType*/, AController* /*InstigatedBy*/, AActor* /*DamageCauser*/)
{
    if (!bArmed || !IsValid(DamagedActor)) return;
    const TWeakObjectPtr<ADungeonSpawnDirector> Director(this);
    const TWeakObjectPtr<AActor> Victim(DamagedActor);
    if (MonsterDamageAlert::FScopedSilentShot::DeferGroupAlert(DamagedActor, [Director, Victim]()
        {
            if (Director.IsValid() && Victim.IsValid()) Director->RaiseDamageAlarm(Victim.Get());
        })) return;
    RaiseDamageAlarm(DamagedActor);
}

void ADungeonSpawnDirector::RaiseDamageAlarm(AActor* DamagedActor)
{
    if (!bArmed || !IsValid(DamagedActor)) return;
    const int32 RoomIndex = PlanIndexOfMonster(DamagedActor);
    if (RoomIndex == INDEX_NONE) return;
    FDungeonRoomSpawnPlan& Plan = Plans[RoomIndex];
    UDungeonRunSubsystem* Sub = Run.Get();
    if (!Plan.bAlarmed)
    {
        Plan.bAlarmed = true;   // 本 run 不再休眠
        WakeRoom(RoomIndex);
        UE_LOG(LogTemp, Display, TEXT("[DungeonSpawn] 警报：房 %d 进入警报集（本 run 不再休眠）。"), Plan.NodeId);
    }
    if (!Sub) return;
    const FDungeonRunNode* Node = Sub->NodeById(Plan.NodeId);
    UWorld* World = GetWorld();
    if (!Node || !World) return;
    // 沿连续通道找到相邻房，到房即停；不向相邻怪注入玩家目标：
    // 受击者自身已由 ReceiveHit 自动 RememberDamage。
    const double Until = World->GetTimeSeconds() + AlertSeconds;
    TArray<int32> Neighbors;Sub->CollectNeighborRooms(Plan.NodeId,Neighbors);
    for (int32 NextId : Neighbors)
    {
        AlertUntil.FindOrAdd(NextId) = Until;
        const int32 Other = PlanIndexOfRoom(NextId);
        if (Other != INDEX_NONE) WakeRoom(Other);
    }
}

void ADungeonSpawnDirector::OnMonsterDestroyed(AActor* DestroyedActor)
{
    if (!IsValid(DestroyedActor)) return;
    const int32 RoomIndex = PlanIndexOfMonster(DestroyedActor);
    if (RoomIndex == INDEX_NONE) return;
    for (FDungeonSpawnSlot& Slot : Plans[RoomIndex].Slots)
        if (Slot.Monster.Get() == DestroyedActor) Slot.Monster.Reset();
    // bFilled 保持 true：尸体销毁只意味着死亡既成事实，绝不触发同槽重生。
    CheckRoomCleared(RoomIndex);
}

void ADungeonSpawnDirector::WakeRoom(int32 RoomIndex)
{
    if (!Plans.IsValidIndex(RoomIndex)) return;
    for (FDungeonSpawnSlot& Slot : Plans[RoomIndex].Slots)
    {
        ACharacter* Monster = Slot.Monster.Get();
        if (!Slot.bFilled || Slot.bAwake || !IsValid(Monster)) continue;
        WakeMonster(Monster);
        Slot.bAwake = true;
    }
}

int32 ADungeonSpawnDirector::PlanIndexOfRoom(int32 NodeId) const
{
    for (int32 Index = 0; Index < Plans.Num(); ++Index) if (Plans[Index].NodeId == NodeId) return Index;
    return INDEX_NONE;
}

int32 ADungeonSpawnDirector::PlanIndexOfMonster(const AActor* Monster) const
{
    if (!Monster) return INDEX_NONE;
    for (int32 Index = 0; Index < Plans.Num(); ++Index)
        for (const FDungeonSpawnSlot& Slot : Plans[Index].Slots)
            if (Slot.Monster.Get() == Monster) return Index;
    return INDEX_NONE;
}

int32 ADungeonSpawnDirector::AliveCount() const
{
    int32 Count = 0;
    for (const FDungeonRoomSpawnPlan& Plan : Plans)
    {
        if(Plan.bHandledByEncounter)
        {if(const auto* Encounter=Plan.Encounter.Get())Count+=Encounter->AliveCount();continue;}
        for (const FDungeonSpawnSlot& Slot : Plan.Slots)
            if (Slot.bFilled && !Slot.bGivenUp && !IsMonsterDead(Slot.Monster.Get())) ++Count;
    }
    return Count;
}

bool ADungeonSpawnDirector::CanSpawnMember()const
{
    return bArmed&&AliveCount()<FMath::Max(0,DungeonSpawnGlobalCap.GetValueOnGameThread());
}

int32 ADungeonSpawnDirector::OrdinarySpawnLimit()const
{
    const int32 Cap=FMath::Max(0,DungeonSpawnGlobalCap.GetValueOnGameThread());
    int32 Reserve=0;
    for(const auto& Plan:Plans)if(const auto* Encounter=Plan.Encounter.Get())
        Reserve=FMath::Max(Reserve,Encounter->PendingCount());
    // Reserve one encounter wave without removing any already spawned monster.
    return FMath::Max(0,Cap-FMath::Min(Reserve,FMath::Max(0,Cap-1)));
}

bool ADungeonSpawnDirector::HasPending(const FDungeonRoomSpawnPlan& Plan)
{
    for (const FDungeonSpawnSlot& Slot : Plan.Slots)
        if (!Slot.bFilled && !Slot.bGivenUp) return true;
    return false;
}

UClass* ADungeonSpawnDirector::ResolveMonsterClass(const FString& ClassPath)
{
    if (ClassPath.IsEmpty()) return nullptr;
    UClass* Class = LoadObject<UClass>(nullptr, *ClassPath);
    if (!Class && !ClassPath.Contains(TEXT(".")))
    {
        // 容忍目录只写包路径：补齐蓝图生成类对象名（/Game/.../BP_X → BP_X.BP_X_C）。
        const FString Short = FPackageName::GetShortName(ClassPath);
        Class = LoadObject<UClass>(nullptr, *(ClassPath + TEXT(".") + Short + TEXT("_C")));
    }
    if (!Class || !Class->IsChildOf(ACharacter::StaticClass()) || Class->HasAnyClassFlags(CLASS_Abstract))
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 怪物类无法载入、抽象或不是 ACharacter：%s"), *ClassPath);
        return nullptr;
    }
    // CDO 校验（照抄 SpawnBoss 口径，泛化到四家族）：网格、移动、胶囊、共用战斗组件齐备。
    auto* Defaults = Class->GetDefaultObject<ACharacter>();
    if (!Defaults || !Defaults->GetMesh() || !Defaults->GetCharacterMovement() || !Defaults->GetCapsuleComponent() || !HasMonsterCombat(Defaults))
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 怪物类缺少网格/移动/战斗组件，不入池：%s"), *ClassPath);
        return nullptr;
    }
    return Class;
}

ACharacter* ADungeonSpawnDirector::SpawnMonsterAtGround(UObject* WorldContext, AActor* Owner, const FDungeonSpawnMember& Member,
    const FVector& Ground, const FRotator& Facing, bool bAwake, FName SlotTag, const FDungeonRunNode* Room)
{
    UWorld* World = ContextWorld(WorldContext);
    UClass* Class = ResolveMonsterClass(Member.ClassPath);
    if (!World || !Class) return nullptr;
    auto* Defaults = Class->GetDefaultObject<ACharacter>();
    const auto* Movement = Defaults ? Defaults->GetCharacterMovement() : nullptr;
    const auto* Capsule = Defaults ? Defaults->GetCapsuleComponent() : nullptr;
    if (!Defaults || !Movement || !Capsule) return nullptr;

    // nav 投影闸门：照抄 SpawnBoss 的 agent 口径（FromCapsule 分支）与跨房/跨层防线。
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    FNavAgentProperties Agent = Movement->GetNavAgentPropertiesRef();
    const bool FromCapsule = Movement->ShouldUpdateNavAgentWithOwnersCollision();
    Agent.AgentRadius = FromCapsule ? Capsule->GetScaledCapsuleRadius() : FMath::Max(Agent.AgentRadius, Capsule->GetScaledCapsuleRadius());
    Agent.AgentHeight = FromCapsule ? Capsule->GetScaledCapsuleHalfHeight() * 2 : FMath::Max(Agent.AgentHeight, Capsule->GetScaledCapsuleHalfHeight() * 2);
    const auto* NavData = Nav ? Nav->GetNavDataForProps(Agent, Ground) : nullptr;
    FNavLocation Location;
    if (!NavData || !Nav->ProjectPointToNavigation(Ground, Location, FVector(150, 150, 100), NavData)) return nullptr;
    if (NavData->GetConfig().AgentRadius + KINDA_SMALL_NUMBER < Agent.AgentRadius ||
        NavData->GetConfig().AgentHeight + KINDA_SMALL_NUMBER < Agent.AgentHeight) return nullptr;
    // 绝不让投影把怪抬到上层平台或推进隔壁房。
    if (FMath::Abs(Location.Location.Z - Ground.Z) > 55 || (Location.Location - Ground).Size2D() > 150) return nullptr;
    if(Room&&!Room->AllowsSpawn(Location.Location))return nullptr;

    const FVector Position = Location.Location + FVector(0, 0, Capsule->GetScaledCapsuleHalfHeight() + 3);
    const FTransform Transform(FRotator(0, Facing.Yaw, 0), Position);
    ACharacter* Monster = World->SpawnActorDeferred<ACharacter>(Class, Transform, Owner, nullptr,
        ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    if (!Monster) return nullptr;
    // FinishSpawning 之前写好槽位标签与实例等级/品阶：BeginPlay 缓存的 Home 与击杀去重都读得到。
    if (SlotTag != NAME_None) Monster->Tags.Add(SlotTag);
    Monster->Tags.AddUnique(TEXT("DungeonSpawned"));
    WriteLevelRank(Monster, Member);
    Monster->FinishSpawning(Transform);
    if (!IsValid(Monster)) return nullptr;
    // 生成后校验（照抄 SpawnBoss）：tick 可用、物理资产、移动、控制器与行为树齐全，否则立即销毁。
    if (!Monster->IsActorTickEnabled() || !Monster->GetMesh() || !Monster->GetMesh()->GetPhysicsAsset() || !Monster->GetCharacterMovement())
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 生成后校验失败（tick/物理资产/移动）：%s"), *Member.ClassPath);
        Monster->Destroy();
        return nullptr;
    }
    if (!Monster->GetController()) Monster->SpawnDefaultController();
    auto* Controller = Cast<AMonsterAIController>(Monster->GetController());
    if (!Controller || !Controller->Behavior)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonSpawn] 生成后校验失败（MonsterAIController/Behavior）：%s"), *Member.ClassPath);
        Monster->Destroy();
        return nullptr;
    }
    if (!bAwake)
    {
        // 休眠配方顺序严格：先关决策，再关 tick（先例 PoisonMaggotAudit.cpp:201）。
        Controller->SetDecisionEnabled(false);
        Monster->SetActorTickEnabled(false);
    }
    return Monster;
}

bool ADungeonSpawnDirector::PlayerGateAllows(const UObject* WorldContext, const FVector& Candidate, float MinDistance)
{
    UWorld* World = ContextWorld(WorldContext);
    APawn* Player = PlayerPawn(WorldContext);
    if (!World || !Player) return true;   // 无玩家（加载/纯服务器）不拦生成
    if (FVector::Dist(Player->GetActorLocation(), Candidate) < MinDistance) return false;
    // 视线闸门：trace 命中任何东西 = 有遮挡 = 允许；无命中 = 玩家能看见落点 = 禁止凭空出现。
    const FVector Eye = Player->GetActorLocation() + FVector(0, 0, PlayerEyeOffset);
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonSpawnSight), false, Player);
    return World->LineTraceSingleByChannel(Hit, Eye, Candidate + FVector(0, 0, PlayerEyeOffset), ECC_Visibility, Query);
}

void ADungeonSpawnDirector::BuildRoomCandidates(UObject* WorldContext, UDungeonRunSubsystem* Subsystem, int32 NodeId,
    const TArray<FString>& AnchorRoles, TArray<FVector>& OutCandidates)
{
    OutCandidates.Reset();
    UWorld* World = ContextWorld(WorldContext);
    if (!World || !Subsystem || !Subsystem->IsRunActive()) return;
    const FDungeonRunNode* Node = Subsystem->NodeById(NodeId);
    if (!Node || !Node->Volume.IsValid) return;
    // 落点流与编成流同构：只依赖 seed + 节点，重试时序不影响可复现性。
    FRandomStream Placement = Subsystem->GameplayStream(DungeonRunDomains::SpawnPlacement ^ Subsystem->NodeRandomSalt(NodeId));

    // 1) 优先锚点：anchor_roles 前缀合并去重后按流打乱（手写 Fisher-Yates，保证逐位可复现）。
    TArray<ATargetPoint*> Anchors;
    for (const FString& Role : AnchorRoles)
        for (ATargetPoint* Anchor : Subsystem->RoomAnchors(NodeId, *Role))
            if (IsValid(Anchor) && !Anchors.Contains(Anchor)) Anchors.Add(Anchor);
    // Actor iteration order changes across staged assemblies; order by authored position first.
    Anchors.StableSort([](const ATargetPoint& A,const ATargetPoint& B)
    {
        const FVector P=A.GetActorLocation(),Q=B.GetActorLocation();
        if(P.X!=Q.X)return P.X<Q.X;
        if(P.Y!=Q.Y)return P.Y<Q.Y;
        return P.Z<Q.Z;
    });
    for (int32 Index = Anchors.Num() - 1; Index > 0; --Index)
    {
        const int32 Other = Placement.RandRange(0, Index);
        Anchors.Swap(Index, Other);
    }
    for (const ATargetPoint* Anchor : Anchors)
        if(Node->AllowsSpawn(Anchor->GetActorLocation()))OutCandidates.Add(Anchor->GetActorLocation());

    // 2) 兜底散点：房间体积内随机 XY + 地面 trace + 坡度闸门（村庄 spawner 口径）。
    //    起始高度阶梯覆盖"体积底=地板面"与"体积底=楼板底"两种目录口径。
    const FVector Size = Node->Volume.Max - Node->Volume.Min;
    if (Size.X < ScatterMargin * 4 || Size.Y < ScatterMargin * 4) return;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonSpawnGround), false);
    const int32 AnchorCount = OutCandidates.Num();
    const double Heights[4] = { Node->Volume.Min.Z + 300.0, Node->Volume.Min.Z + 600.0,
        (Node->Volume.Min.Z + Node->Volume.Max.Z) * .5, Node->Volume.Max.Z - 100.0 };
    for (int32 Sample = 0; Sample < ScatterSamples && OutCandidates.Num() - AnchorCount < ScatterKeep; ++Sample)
    {
        const double X = Node->Volume.Min.X + ScatterMargin + (double)Placement.FRand() * (Size.X - ScatterMargin * 2);
        const double Y = Node->Volume.Min.Y + ScatterMargin + (double)Placement.FRand() * (Size.Y - ScatterMargin * 2);
        for (double StartZ : Heights)
        {
            FHitResult Hit;
            if (!World->LineTraceSingleByChannel(Hit, FVector(X, Y, StartZ), FVector(X, Y, Node->Volume.Min.Z - 60.0), ECC_WorldStatic, Query)) continue;
            if (Hit.ImpactNormal.Z < MinGroundNormalZ || Hit.ImpactPoint.Z < Node->Volume.Min.Z - 20.0) break;
            if(!Node->AllowsSpawn(Hit.ImpactPoint))continue;
            OutCandidates.Add(Hit.ImpactPoint);
            break;
        }
    }
}

void ADungeonSpawnDirector::WriteLevelRank(ACharacter* Monster, const FDungeonSpawnMember& Member)
{
    if (!Monster) return;
    // 只改实例 UPROPERTY，绝不动 CDO。Level=0 表示保留类默认；LevelBonus（深度/精英）恒叠加。
    if (auto* N = Cast<ANurseZombie>(Monster))
    {
        if (Member.Level > 0) N->Level = Member.Level;
        N->Level = FMath::Max(1, N->Level + Member.LevelBonus);
        if (Member.bOverrideRank) N->Rank = Member.Rank;
    }
    else if (auto* W = Cast<AWolfMonster>(Monster))
    {
        if (Member.Level > 0) W->Level = Member.Level;
        W->Level = FMath::Max(1, W->Level + Member.LevelBonus);
        if (Member.bOverrideRank) W->Rank = Member.Rank;
    }
    else if (auto* F = Cast<AFleshHandMonster>(Monster))
    {
        if (Member.Level > 0) F->Level = Member.Level;
        F->Level = FMath::Max(1, F->Level + Member.LevelBonus);
        if (Member.bOverrideRank) F->Rank = Member.Rank;
    }
    else if (auto* H = Cast<AHandBrainMonster>(Monster))
    {
        if (Member.Level > 0) H->Level = Member.Level;
        H->Level = FMath::Max(1, H->Level + Member.LevelBonus);
        if (Member.bOverrideRank) H->Rank = Member.Rank;
    }
    else if (auto* M = Cast<APoisonMaggotMonster>(Monster))
    {
        if (Member.Level > 0) M->Level = Member.Level;
        M->Level = FMath::Max(1, M->Level + Member.LevelBonus);
        if (Member.bOverrideRank) M->Rank = Member.Rank;
    }
}

void ADungeonSpawnDirector::WakeMonster(ACharacter* Monster)
{
    if (!IsValid(Monster)) return;
    // 唤醒配方顺序严格：先恢复 tick，再放开决策。不用 UnPossess，也不用 SetEncounterTarget（Boss 专用锁）。
    Monster->SetActorTickEnabled(true);
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->SetDecisionEnabled(true);
}

bool ADungeonSpawnDirector::SleepMonster(ACharacter* Monster)
{
    if (!IsValid(Monster)) return true;
    auto* Combat = Monster->FindComponentByClass<UMonsterCombatComponent>();
    if (!Combat || Combat->IsDead() || Combat->IsBusy()) return false;   // 死亡/交战中跳过
    // 休眠配方顺序严格：先关决策，再关 tick。不用 StopLogic（仓内无 ResumeLogic 先例）。
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController())) AI->SetDecisionEnabled(false);
    Monster->SetActorTickEnabled(false);
    return true;
}

bool ADungeonSpawnDirector::IsMonsterDead(const ACharacter* Monster)
{
    if (!IsValid(Monster)) return true;
    // 胖子的 PusPool 是独立 Actor，不计入清房判定。
    auto* Combat = Monster->FindComponentByClass<UMonsterCombatComponent>();
    return !Combat || Combat->IsDead();
}

APawn* ADungeonSpawnDirector::PlayerPawn(const UObject* WorldContext)
{
    UWorld* World = ContextWorld(WorldContext);
    APlayerController* Controller = World ? World->GetFirstPlayerController() : nullptr;
    return Controller ? Controller->GetPawn() : nullptr;
}

FRotator ADungeonSpawnDirector::YawToward(const FVector& From, const FVector& Toward)
{
    const FRotator Look = (Toward - From).Rotation();
    return FRotator(0.f, Look.Yaw, 0.f);
}

void ADungeonSpawnDirector::EndPlay(const EEndPlayReason::Type Reason)
{
    // 清场照抄 Boss 遭遇：解绑全部委托 + 销毁全部自有怪与自有 encounter，跨布局零残留。
    if (UWorld* World = GetWorld()) World->GetTimerManager().ClearAllTimersForObject(this);
    bArmed = false;
    for (AActor* Actor : Owned)
    {
        if (!IsValid(Actor)) continue;
        Actor->OnDestroyed.RemoveDynamic(this, &ADungeonSpawnDirector::OnMonsterDestroyed);
        Actor->OnTakeAnyDamage.RemoveDynamic(this, &ADungeonSpawnDirector::OnMonsterDamaged);
        Actor->Destroy();
    }
    Owned.Reset();
    Plans.Reset();
    AlertUntil.Reset();
    Super::EndPlay(Reason);
}
