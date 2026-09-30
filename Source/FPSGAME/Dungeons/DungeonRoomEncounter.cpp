#include "DungeonRoomEncounter.h"
#include "DungeonRunSubsystem.h"
#include "DungeonRoomGate.h"
#include "DungeonRoomGateDimensions.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"

namespace
{
    constexpr float GateTickSeconds = .05f;      // 与 Boss 遭遇同款 armed tick
    constexpr double TriggerDepth = 200.0;       // 触发盒进深
    constexpr double TriggerWidth = 400.0;       // 触发盒横向
    constexpr double TriggerHeight = 320.0;      // 触发盒高度
    constexpr double TriggerInset = 150.0;       // 触发盒中心在门内侧的距离
    constexpr double RoomContainMargin = 250.0;  // 判定"玩家还在房内"的体积外扩
    constexpr double RetrySeconds = 10.0;        // 落点失败重试（村庄 spawner 口径）
    constexpr int32 MaxSlotAttempts = 3;
}

ADungeonRoomEncounter::ADungeonRoomEncounter()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("RoomEncounterRoot"));
    TriggerBox = CreateDefaultSubobject<UBoxComponent>(TEXT("RoomDoorTrigger"));
    TriggerBox->SetupAttachment(RootComponent);
    TriggerBox->SetMobility(EComponentMobility::Movable);
    // 判定走几何包含（Boss Contains 同款），不产 overlap 事件，也不参与导航。
    TriggerBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TriggerBox->SetGenerateOverlapEvents(false);
    TriggerBox->SetCanEverAffectNavigation(false);
    TriggerBox->SetHiddenInGame(true);
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    PrimaryActorTick.TickInterval = GateTickSeconds;
    Tags.Add(TEXT("DungeonRoomEncounter"));
}

void ADungeonRoomEncounter::BeginPlay()
{
    Super::BeginPlay();
    // 存档/预览实例绝不自行开战（Boss 同款）：只有导演 Configure+Activate 之后才武装。
    GateOpen = 1.f;
    SetActorTickEnabled(false);
    UpdateGate();
}

void ADungeonRoomEncounter::Configure(UDungeonRunSubsystem* InSubsystem, int32 InRoomNodeId, const TArray<FDungeonSpawnMember>& InGroup,
    const FVector& DoorCenterIn, const FVector& DoorNormalIn, const TArray<FVector>& InCandidateGround)
{
    Run = InSubsystem;
    RoomNodeId = InRoomNodeId;
    Slots.Reset();
    for (const FDungeonSpawnMember& Member : InGroup)
    {
        FDungeonRoomEncounterSlot Slot;
        Slot.Member = Member;
        Slots.Add(MoveTemp(Slot));
    }
    Candidates = InCandidateGround;
    if (Candidates.IsEmpty())
    {
        // 生成器直接挂接时可以不给落点：用导演同款确定性配方自行补齐（同 seed + 同节点结果一致）。
        TArray<FString> Roles;
        Roles.Add(TEXT("encounter"));
        ADungeonSpawnDirector::BuildRoomCandidates(this, InSubsystem, InRoomNodeId, Roles, Candidates);
    }
    if (const FDungeonRunNode* Node = InSubsystem ? InSubsystem->NodeById(InRoomNodeId) : nullptr)
    {
        RoomVolume = Node->Volume;
        RoomCenter = Node->Volume.IsValid ? Node->Volume.GetCenter() : Node->Origin;
    }
    DoorCenter = DoorCenterIn;
    DoorNormal = DoorNormalIn.GetSafeNormal();
    bDoorValid = !DoorNormal.IsNearlyZero() && !DoorCenter.ContainsNaN();
    if (!bDoorValid)
        UE_LOG(LogTemp, Warning, TEXT("[RoomEncounter] 房 %d 门口参数无效：不封门，只生成精英组。"), InRoomNodeId);

    // Every real connected port gets the same kit, fitted in its own door frame.
    // The authored room frame remains intact; rails mount on the room-facing side.
    const FRotator Facing = bDoorValid ? FRotator(0, DoorNormal.Rotation().Yaw, 0) : FRotator::ZeroRotator;
    for (ADungeonRoomGate* Previous : Gates) if (IsValid(Previous)) Previous->Destroy();
    Gates.Reset();
    if(bDoorValid)if(const auto* Node=InSubsystem?InSubsystem->NodeById(InRoomNodeId):nullptr)
        for(const FDungeonRunDoor& Door:Node->Doors)
        {
            FActorSpawnParameters Params;
            Params.Owner = this;
            Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Assembly = GetWorld()->SpawnActor<ADungeonRoomGate>(ADungeonRoomGate::StaticClass(), FTransform::Identity, Params);
            if (!Assembly || !Assembly->Configure(Door))
            {
                if (Assembly) Assembly->Destroy();
                bDoorValid = false;
                break;
            }
            Gates.Add(Assembly);
        }
    if (Gates.IsEmpty()) bDoorValid = false;
    if (!bDoorValid)
    {
        for (ADungeonRoomGate* Assembly : Gates) if (IsValid(Assembly)) Assembly->Destroy();
        Gates.Reset();
        UE_LOG(LogTemp, Warning, TEXT("[RoomEncounter] 房 %d 闸门资源或门洞不完整：保留开放战斗。"), RoomNodeId);
    }
    TriggerBox->SetWorldLocationAndRotation(bDoorValid ? DoorCenter + DoorNormal * TriggerInset : FVector::ZeroVector, Facing);
    TriggerBox->SetBoxExtent(FVector(TriggerDepth, TriggerWidth, TriggerHeight) * .5);
    GateOpen = 1.f;
    bSealed = false;
    bEncounterStarted=false;
    bEncounterComplete = Slots.IsEmpty();
    NextAttemptAt = 0.0;
    NextCandidate = 0;
    UpdateGate();
    Tags.AddUnique(TEXT("DungeonRoom.Encounter"));
    if (bEncounterComplete)
        UE_LOG(LogTemp, Warning, TEXT("[RoomEncounter] 房 %d 的精英组为空，遭遇直接判完成。"), InRoomNodeId);
}

void ADungeonRoomEncounter::Activate()
{
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld() || !HasAuthority() || bArmed) return;
    bArmed = true;
    SetActorTickEnabled(true);
    // Even encounters without a usable doorway wait for the player to enter.
    UE_LOG(LogTemp, Display, TEXT("[RoomEncounter] 武装：房 %d 精英组 %d 只 封门=%s 落点=%d"),
        RoomNodeId, Slots.Num(), bDoorValid ? TEXT("是") : TEXT("否"), Candidates.Num());
}

void ADungeonRoomEncounter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bArmed || !HasAuthority()) return;
    if (!bEncounterComplete)
    {
        const bool Inside=CombatantInside();
        if (bSealed && (!Inside || (GateOpen > 0.f && IsGateSweepOccupied()))) OpenGate();
        if(Inside)
        {
            bEncounterStarted=true;
            AttemptSpawns();
            // Complete the spawn wave before sealing; cap/nav failures leave an exit.
            if(bDoorValid&&!HasPending()&&AliveCount()>0)SealGate();
        }
        if(bEncounterStarted&&AliveCount()==0&&!HasPending())Complete();
    }
    const float TargetOpen = (bSealed && !bEncounterComplete) ? 0.f : 1.f;
    GateOpen = FMath::FInterpConstantTo(GateOpen, TargetOpen, DeltaSeconds, float(1. / DungeonRoomGateDimensions::TravelSeconds));
    UpdateGate();
    // Smooth door motion uses frame ticks only while travelling; encounter polling stays at 20 Hz.
    SetActorTickInterval(GateOpen == TargetOpen ? GateTickSeconds : 0.f);
    if (bEncounterComplete && GateOpen >= 1.f) SetActorTickEnabled(false);
}

void ADungeonRoomEncounter::SealGate()
{
    if (bSealed || bEncounterComplete || !bDoorValid) return;
    // Use the actual four-track sweep on the room side, including the whole capsule.
    if (IsGateSweepOccupied()) return;
    bSealed = true;
    SetActorTickInterval(0.f);
    Tags.AddUnique(TEXT("DungeonRoom.Sealed"));
    UE_LOG(LogTemp, Display, TEXT("[RoomEncounter] 房 %d 精英组落地完成，封闭全部连接门。"), RoomNodeId);
}

void ADungeonRoomEncounter::OpenGate()
{
    if (!bSealed) return;   // 幂等：导演巡检也会催一次
    bSealed = false;
    SetActorTickInterval(0.f);
    Tags.Remove(TEXT("DungeonRoom.Sealed"));
    UE_LOG(LogTemp, Display, TEXT("[RoomEncounter] 房 %d 开门。"), RoomNodeId);
}

void ADungeonRoomEncounter::Complete()
{
    if (bEncounterComplete) return;
    bEncounterComplete = true;
    const bool bWasSealed = bSealed;
    OpenGate();
    Tags.AddUnique(TEXT("DungeonRoom.Cleared"));
    if (Run.IsValid()) Run->MarkRoomCleared(RoomNodeId);
    UE_LOG(LogTemp, Display, TEXT("[RoomEncounter] 房 %d 精英组清空%s，开门并登记清除。"),
        RoomNodeId, bWasSealed ? TEXT("（封门战）") : TEXT("（无门口战）"));
}

void ADungeonRoomEncounter::UpdateGate()
{
    if (!bDoorValid) return;
    for (ADungeonRoomGate* Assembly : Gates) if (IsValid(Assembly)) Assembly->SetOpenFraction(GateOpen);
}

bool ADungeonRoomEncounter::IsGateSweepOccupied() const
{
    const APawn* Player = LivePlayer();
    for (const ADungeonRoomGate* Assembly : Gates)
        if (IsValid(Assembly) && Assembly->IsSweepOccupied(Player)) return true;
    return false;
}

void ADungeonRoomEncounter::AttemptSpawns()
{
    UWorld* World = GetWorld();
    if (!World || !bArmed || !bEncounterStarted || !CombatantInside() || !HasPending()) return;
    const double Now = World->GetTimeSeconds();
    if (Now < NextAttemptAt) return;
    NextAttemptAt = Now + RetrySeconds;
    if (Candidates.IsEmpty())
    {
        // 没有可用落点：整组放弃，Tick 据此判完成并开门，绝不把玩家锁在房里。
        for (FDungeonRoomEncounterSlot& Slot : Slots) if (!Slot.bFilled) Slot.bGivenUp = true;
        UE_LOG(LogTemp, Warning, TEXT("[RoomEncounter] 房 %d 没有可用落点，精英组放弃生成。"), RoomNodeId);
        return;
    }
    UDungeonRunSubsystem* Sub = Run.Get();
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        FDungeonRoomEncounterSlot& Slot = Slots[Index];
        if (Slot.bGivenUp || Slot.bFilled) continue;
        if(const auto* Director=Cast<ADungeonSpawnDirector>(GetOwner());Director&&!Director->CanSpawnMember())
        {NextAttemptAt=Now+.25;return;}
        ACharacter* Monster = nullptr;
        for (int32 Try = 0; Try < Candidates.Num(); ++Try)
        {
            const FVector Ground = Candidates[NextCandidate % Candidates.Num()];
            ++NextCandidate;
            // 房内落怪不做玩家距离/视线闸门（玩家已进房触发封门）；nav/资产/碰撞闸门与导演完全一致。
            Monster = ADungeonSpawnDirector::SpawnMonsterAtGround(this, this, Slot.Member, Ground,
                ADungeonSpawnDirector::YawToward(Ground, RoomCenter), true,
                Sub ? Sub->EnemySlotTag(RoomNodeId, Index) : NAME_None,Sub?Sub->NodeById(RoomNodeId):nullptr);
            if (Monster) break;
        }
        if (Monster)
        {
            Slot.Monster = Monster;
            Slot.bFilled = true;
            Owned.Add(Monster);
            Monster->OnDestroyed.AddDynamic(this, &ADungeonRoomEncounter::OnMonsterDestroyed);
            UE_LOG(LogTemp, Display, TEXT("[RoomEncounter] 房 %d 槽 %d 精英 %s 落地 @ %s"),
                RoomNodeId, Index, *Slot.Member.ClassPath, *Monster->GetActorLocation().ToString());
        }
        else
        {
            ++Slot.Attempts;
            if (Slot.Attempts >= MaxSlotAttempts)
            {
                Slot.bGivenUp = true;
                UE_LOG(LogTemp, Warning, TEXT("[RoomEncounter] 房 %d 槽 %d 连续 %d 次落点失败，放弃该槽：%s"),
                    RoomNodeId, Index, Slot.Attempts, *Slot.Member.ClassPath);
            }
        }
    }
}

void ADungeonRoomEncounter::OnMonsterDestroyed(AActor* DestroyedActor)
{
    if (!IsValid(DestroyedActor)) return;
    for (FDungeonRoomEncounterSlot& Slot : Slots)
        if (Slot.Monster.Get() == DestroyedActor) Slot.Monster.Reset();
    // bFilled 保持 true：尸体销毁只是死亡既成事实，绝不触发同槽重生。
}

bool ADungeonRoomEncounter::TriggerContains(const APawn* Pawn) const
{
    if (!IsValid(Pawn) || !bDoorValid) return false;
    // Boss Contains 同款：转到触发盒局部空间做盒判定（盒已按门口法线定向）。
    const FVector Local = TriggerBox->GetComponentTransform().InverseTransformPosition(Pawn->GetActorLocation());
    const FVector Extent = TriggerBox->GetUnscaledBoxExtent();
    return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

bool ADungeonRoomEncounter::RoomContains(const APawn* Pawn) const
{
    if (!IsValid(Pawn) || !RoomVolume.IsValid) return false;
    if(const auto* Sub=Run.Get())if(const auto* Node=Sub->NodeById(RoomNodeId))
        return Node->DistanceSquared(Pawn->GetActorLocation())<=FMath::Square(40.);
    return RoomVolume.ExpandBy(FVector(RoomContainMargin)).IsInsideOrOn(Pawn->GetActorLocation());
}

APawn* ADungeonRoomEncounter::LivePlayer() const
{
    UWorld* World = GetWorld();
    if (!World) return nullptr;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->Get() ? It->Get()->GetPawn() : nullptr;
        if (!Player) continue;
        auto* Health = Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Health && Health->IsDead()) continue;   // 死亡玩家不算在场（Boss 同款判定）
        return Player;
    }
    return nullptr;
}

bool ADungeonRoomEncounter::CombatantInside() const
{
    APawn* Player = LivePlayer();
    return IsValid(Player) && (RoomContains(Player) || TriggerContains(Player));
}

int32 ADungeonRoomEncounter::AliveCount() const
{
    int32 Count = 0;
    for (const FDungeonRoomEncounterSlot& Slot : Slots)
        if (Slot.bFilled && !ADungeonSpawnDirector::IsMonsterDead(Slot.Monster.Get())) ++Count;
    return Count;
}

bool ADungeonRoomEncounter::HasPending() const
{
    for (const FDungeonRoomEncounterSlot& Slot : Slots)
        if (!Slot.bFilled && !Slot.bGivenUp) return true;
    return false;
}

int32 ADungeonRoomEncounter::PendingCount()const
{
    int32 Count=0;for(const auto& Slot:Slots)if(!Slot.bFilled&&!Slot.bGivenUp)++Count;return Count;
}

void ADungeonRoomEncounter::EndPlay(const EEndPlayReason::Type Reason)
{
    // 清场照抄 Boss 遭遇：解绑委托 + 销毁自有精英组，跨布局零残留。
    bArmed = false;
    for (ADungeonRoomGate* Assembly : Gates) if (IsValid(Assembly)) Assembly->Destroy();
    Gates.Reset();
    for (AActor* Actor : Owned)
    {
        if (!IsValid(Actor)) continue;
        Actor->OnDestroyed.RemoveDynamic(this, &ADungeonRoomEncounter::OnMonsterDestroyed);
        Actor->Destroy();
    }
    Owned.Reset();
    Slots.Reset();
    Super::EndPlay(Reason);
}
