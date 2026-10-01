#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonSpawnDirector.h"
#include "DungeonRoomEncounter.generated.h"

class ACharacter;
class AController;
class APawn;
class UBoxComponent;
class ADungeonRoomGate;
class UDungeonRunSubsystem;

/** 封门精英战的一个槽位（成员编成来自导演的开局规划）。 */
struct FDungeonRoomEncounterSlot
{
    FDungeonSpawnMember Member;
    int32 Attempts = 0;
    bool bGivenUp = false;
    bool bFilled = false;
    TWeakObjectPtr<ACharacter> Monster;
};

/**
 * 房间封门遭遇：普通房、过渡房、主题房与精英房统一使用，Boss 仍由独立遭遇持有。
 * 由 ADungeonSpawnDirector 在开局规划里为所有有刷怪编成的房间创建：
 * SpawnActor → Configure(...) → Activate()（与 Boss 同批，导航构建完成之后）。
 *
 * 玩家完整进房且离开门扇扫掠区 → 锁定全部连接门并生成编成，待生成槽位也属于战斗。
 * 全员 IsDead 且无待生成槽位才开门并 MarkRoomCleared；离开体积不解锁。
 * 玩家死亡 → 放行重试（怪保留、不登记清除），重新进入后再次锁定。
 */
UCLASS()
class FPSGAME_API ADungeonRoomEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonRoomEncounter();

    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") bool bEncounterComplete = false;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") bool bSealed = false;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") int32 RoomNodeId = INDEX_NONE;

    /**
     * 导演/生成器入口。InCandidateGround 为空时自行用导演的确定性落点配方补齐
     * （同 seed + 同节点结果一致）。主入口估算失败时按房间体积触发，闸门取真实 Doors。
     * bSealConnectedDoors=false 仅保留给显式开放遭遇调用方；地牢导演统一传 true。
     */
    void Configure(UDungeonRunSubsystem* InSubsystem, int32 InRoomNodeId, const TArray<FDungeonSpawnMember>& InGroup,
        const FVector& DoorCenter, const FVector& DoorNormal, const TArray<FVector>& InCandidateGround = TArray<FVector>(),
        bool bSealConnectedDoors = true);
    /** 导航构建完成后武装（Boss ActivateEncounter 同款两段式）。 */
    void Activate();
    bool IsCleared() const { return bEncounterComplete; }
    int32 AliveCount()const;
    int32 PendingCount()const;
    /** 幂等开门：导演巡检到房间清空时也会调用。 */
    void OpenGate();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    UFUNCTION() void OnMonsterDestroyed(AActor* DestroyedActor);

    bool TriggerContains(const APawn* Pawn) const;
    bool RoomContains(const APawn* Pawn) const;
    /** 房内是否还有活着的玩家（死亡玩家视为不在房内，Boss 同款判定）。 */
    bool CombatantInside() const;
    APawn* LivePlayer() const;
    void SealGate();
    void Complete();
    void UpdateGate();
    bool IsGateSweepOccupied() const;
    void AttemptSpawns();
    bool HasPending() const;

    UPROPERTY() TObjectPtr<UBoxComponent> TriggerBox;
    UPROPERTY(Transient) TArray<TObjectPtr<AActor>> Owned;
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TArray<FDungeonRoomEncounterSlot> Slots;
    TArray<FVector> Candidates;
    FVector RoomCenter = FVector::ZeroVector;
    FBox RoomVolume = FBox(ForceInit);
    FVector DoorCenter = FVector::ZeroVector;
    FVector DoorNormal = FVector::ZeroVector;
    int32 NextCandidate = 0;
    float GateOpen = 1.f;
    double NextAttemptAt = 0.0;
    bool bDoorValid = false;
    bool bArmed = false;
    bool bEncounterStarted=false;
    UPROPERTY(Transient) TArray<TObjectPtr<ADungeonRoomGate>> Gates;
};
