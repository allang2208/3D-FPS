#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Monsters/MonsterCoreStats.h"
#include "DungeonSpawnDirector.generated.h"

class AAuthoredDungeonGenerator;
class ADungeonRoomEncounter;
class ACharacter;
class AController;
class APawn;
class UDamageType;
class UDungeonRunSubsystem;

/**
 * 一只怪的编成结果（配置条目 + 深度/精英加成）。
 * Level=0 表示保留类默认等级；LevelBonus 恒叠加到最终实例值上。
 */
struct FDungeonSpawnMember
{
    FString Id;
    FString ClassPath;
    int32 Level = 0;
    int32 LevelBonus = 0;
    EMonsterRank Rank = EMonsterRank::Normal;
    bool bOverrideRank = false;
};

/** 一间房的一个刷怪槽位。bFilled/bGivenUp 一起构成"已解决"，避免尸体销毁后被当成未生成而重生。 */
struct FDungeonSpawnSlot
{
    FDungeonSpawnMember Member;
    int32 Attempts = 0;
    bool bGivenUp = false;
    bool bFilled = false;
    bool bAwake = false;
    TWeakObjectPtr<ACharacter> Monster;
};

/** 一间战斗房的刷怪计划：编成、确定性落点候选、存活登记与重试定时器。 */
struct FDungeonRoomSpawnPlan
{
    int32 NodeId = INDEX_NONE;
    FString Module;
    FString Route;
    int32 Depth = 0;
    FVector Center = FVector::ZeroVector;
    bool bElite = false;
    /** 精英房整组交给 ADungeonRoomEncounter 生成，导演不再自行落怪（只负责清房登记）。 */
    bool bHandledByEncounter = false;
    bool bCleared = false;
    bool bAlarmed = false;
    bool bExplored = false;
    int32 NextCandidate = 0;
    TArray<FDungeonSpawnSlot> Slots;
    TArray<FVector> Candidates;
    TWeakObjectPtr<ADungeonRoomEncounter> Encounter;
    FTimerHandle RetryTimer;
};

/**
 * 地牢刷怪导演：一次运行绑定一间已装配地牢，负责开局编成规划、落点校验闸门、
 * 远房休眠/唤醒、警报传播与清房登记。全定时器驱动（bCanEverTick=false）：
 * 0.25s 巡检 + 每房 10s 落点重试（村庄 spawner 口径）。
 *
 * 生成器挂接（主会话）：在 FinishAssembly 收尾批（DungeonAssembly.Ready、导航构建完成、
 * 仅 State->bRuntime）SpawnActor 本类并 OwnGenerated，然后 Configure(Generator) → Activate()，
 * 与 ADungeonBossEncounter::ActivateEncounter 同批。布局重生成时随生成器一起销毁，EndPlay 清场。
 */
UCLASS()
class FPSGAME_API ADungeonSpawnDirector : public AActor
{
    GENERATED_BODY()
public:
    ADungeonSpawnDirector();

    /** 生成器入口：缓存生成器弱引用并从世界取 UDungeonRunSubsystem。 */
    void Configure(AAuthoredDungeonGenerator* InGenerator);
    /** 导航构建完成后武装：一次性开局规划 + 启动 0.25s 巡检。非游戏世界/无 authority 直接返回。 */
    void Activate();

    // ── 与 ADungeonRoomEncounter 共用的静态闸门（普通池基类约束 = ACharacter + MonsterCombatComponent）──
    /** 类路径解析 + CDO 校验（照抄 SpawnBoss 的口径，泛化到四家族）。失败返回 nullptr。 */
    static UClass* ResolveMonsterClass(const FString& ClassPath);
    /**
     * 完整生成闸门：nav 严格投影（agent 匹配、|ΔZ|≤55、2D≤150）→ SpawnDeferred（写槽位标签与
     * 实例 Level/Rank，绝不动 CDO）→ FinishSpawning → 校验 tick/物理资产/控制器/行为树。
     * 任一环节失败立即销毁并返回 nullptr（落点失败由调用方重试）。bAwake=false 时按休眠配方落地。
     */
    static ACharacter* SpawnMonsterAtGround(UObject* WorldContext, AActor* Owner, const FDungeonSpawnMember& Member,
        const FVector& Ground, const FRotator& Facing, bool bAwake, FName SlotTag);
    /** 玩家闸门：与玩家距离 ≥MinDistance 且无视线连通才允许落点（无玩家视为通过）。 */
    static bool PlayerGateAllows(const UObject* WorldContext, const FVector& Candidate, float MinDistance);
    /** 房间落点候选：anchor_roles 锚点（确定性打乱）优先，房间体积内地面 trace 散点兜底。 */
    static void BuildRoomCandidates(UObject* WorldContext, UDungeonRunSubsystem* Subsystem, int32 NodeId,
        const TArray<FString>& AnchorRoles, TArray<FVector>& OutCandidates);
    static void WriteLevelRank(ACharacter* Monster, const FDungeonSpawnMember& Member);
    /** 唤醒配方（顺序严格）：SetActorTickEnabled(true) → SetDecisionEnabled(true)。 */
    static void WakeMonster(ACharacter* Monster);
    /** 休眠配方（顺序严格）：SetDecisionEnabled(false) → SetActorTickEnabled(false)。死亡/交战中返回 false（跳过）。 */
    static bool SleepMonster(ACharacter* Monster);
    static bool IsMonsterDead(const ACharacter* Monster);
    /** FirstPlayerController 的 Pawn（无则 nullptr）。 */
    static APawn* PlayerPawn(const UObject* WorldContext);
    static FRotator YawToward(const FVector& From, const FVector& Toward);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    /** 任一族受击 → 该房进入警报集（本 run 不再休眠）+ 相邻房（共享 connector 邻居，1 跳）临时唤醒。 */
    UFUNCTION() void OnMonsterDamaged(AActor* DamagedActor, float Damage, const UDamageType* DamageType, AController* InstigatedBy, AActor* DamageCauser);
    UFUNCTION() void OnMonsterDestroyed(AActor* DestroyedActor);

    void Patrol();
    void PlanOpening();
    void SelectEliteRooms(const TArray<int32>& Eligible, TArray<int32>& OutEliteNodes);
    void AttemptRoomSpawns(int32 RoomIndex);
    void CheckRoomCleared(int32 RoomIndex);
    void WakeRoom(int32 RoomIndex);
    int32 PlanIndexOfRoom(int32 NodeId) const;
    int32 PlanIndexOfMonster(const AActor* Monster) const;
    int32 AliveCount() const;
    static bool HasPending(const FDungeonRoomSpawnPlan& Plan);

    /** 自有怪与自有 encounter 的硬引用（生成器 GeneratedActors 同款），EndPlay 遍历销毁。 */
    UPROPERTY(Transient) TArray<TObjectPtr<AActor>> Owned;
    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TArray<FDungeonRoomSpawnPlan> Plans;
    /** 警报传播的临时唤醒窗口：NodeId → 到期世界秒。 */
    TMap<int32, double> AlertUntil;
    FTimerHandle PatrolTimer;
    bool bArmed = false;
    bool bPlanned = false;
};
