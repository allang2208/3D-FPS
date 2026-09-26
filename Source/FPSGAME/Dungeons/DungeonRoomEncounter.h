#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonSpawnDirector.h"
#include "DungeonRoomEncounter.generated.h"

class ACharacter;
class AController;
class APawn;
class UBoxComponent;
class UMaterialInterface;
class UStaticMeshComponent;
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
 * 封门精英房遭遇：ADungeonBossEncounter 的泛化兄弟（多怪、任意家族、无奖励门），
 * 不改动 Boss 类本身。由 ADungeonSpawnDirector 在开局规划里为每条支线抽中的精英房创建：
 * SpawnActor → Configure(...) → Activate()（与 Boss 同批，导航构建完成之后）。
 *
 * 玩家越过门内侧触发线 → 落下门板封门 → 用导演同款校验闸门在房内落点生成精英组（生成即唤醒态，
 * 不休眠）→ 全员 IsDead 即开门并 MarkRoomCleared。门口参数无效时不封门，只生成精英组。
 * 玩家死亡/离开房间 → 放行开门（怪保留），回到触发线可重新封门，避免把进度锁死。
 */
UCLASS()
class FPSGAME_API ADungeonRoomEncounter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonRoomEncounter();

    /** 门板材质与网格沿用 Boss GateMesh 同款资源；生成器/导演可覆盖。 */
    UPROPERTY(EditAnywhere, Category="Dungeon|RoomEncounter") TObjectPtr<UMaterialInterface> GateMaterial;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") bool bEncounterComplete = false;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") bool bSealed = false;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dungeon|RoomEncounter") int32 RoomNodeId = INDEX_NONE;

    /**
     * 导演/生成器入口。InCandidateGround 为空时自行用导演的确定性落点配方补齐
     * （同 seed + 同节点结果一致）。门口参数无效（EstimateDoorway 失败）→ 不封门。
     */
    void Configure(UDungeonRunSubsystem* InSubsystem, int32 InRoomNodeId, const TArray<FDungeonSpawnMember>& InGroup,
        const FVector& DoorCenter, const FVector& DoorNormal, const TArray<FVector>& InCandidateGround = TArray<FVector>());
    /** 导航构建完成后武装（Boss ActivateEncounter 同款两段式）。 */
    void Activate();
    bool IsCleared() const { return bEncounterComplete; }
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
    void AttemptSpawns();
    int32 AliveCount() const;
    bool HasPending() const;

    UPROPERTY() TObjectPtr<UStaticMeshComponent> Gate;
    UPROPERTY() TObjectPtr<UBoxComponent> TriggerBox;
    UPROPERTY(Transient) TArray<TObjectPtr<AActor>> Owned;
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TArray<FDungeonRoomEncounterSlot> Slots;
    TArray<FVector> Candidates;
    FVector RoomCenter = FVector::ZeroVector;
    FBox RoomVolume = FBox(ForceInit);
    FVector DoorCenter = FVector::ZeroVector;
    FVector DoorNormal = FVector::ZeroVector;
    FVector GateBase = FVector::ZeroVector;
    int32 NextCandidate = 0;
    float GateOpen = 1.f;
    double NextAttemptAt = 0.0;
    bool bDoorValid = false;
    bool bArmed = false;
};
