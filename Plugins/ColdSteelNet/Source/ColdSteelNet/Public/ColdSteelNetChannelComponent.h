#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "UI/ColdSteelInventoryTypes.h"
#include "Skills/ColdSteelSkillTypes.h"
#include "Combat/WeaponDamageTypes.h"
#include "Combat/MonsterToughnessTypes.h"
#include "ColdSteelNetChannelComponent.generated.h"

class UColdSteelStatusModel;
class APlayerController;

/** M3 战斗权威化：客户端→服务端的命中上报（FColdSteelSkillShot 的 RPC 安全镜像，不含弱指针与表现字段）。 */
USTRUCT()
struct FColdSteelNetHitReport
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() FVector_NetQuantize HitLocation;
    UPROPERTY() FVector_NetQuantizeNormal HitNormal;
    UPROPERTY() FName BoneName;
    UPROPERTY() float Damage = 0.f;
    UPROPERTY() FVector_NetQuantize Direction;
    /** EMonsterAttackForm 的 uint8 传输形。 */
    UPROPERTY() uint8 AttackForm = 0;
    UPROPERTY() FName MasteryId;
    UPROPERTY() FString ItemDefinition;
    UPROPERTY() int32 ExtraMasteryExperience = 0;
    UPROPERTY() int32 AmmoPoisonStacks = 0;
    UPROPERTY() int32 AmmoBleedStacks = 0;
    UPROPERTY() float ArmorPenetration = 0.f;
    UPROPERTY() float ToughnessDamageMultiplier = 1.f;
    UPROPERTY() float MagicPenetration = 0.f;
    UPROPERTY() float CriticalChance = 0.f;
    UPROPERTY() float WeakpointPercent = 0.f;
    UPROPERTY() float CriticalDamageBonus = 0.f;
    /** bit0 bMeleeStrike / bit1 bRifle / bit2 bPistol / bit3 bMelee / bit4 bRicochet / bit5 bInheritedCritical */
    UPROPERTY() uint8 Flags = 0;
};

/** M3：服务端→客户端的命中回执（命中反馈/击杀提示）。 */
USTRUCT()
struct FColdSteelNetHitReceipt
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() float Applied = 0.f;
    UPROPERTY() bool bCritical = false;
    UPROPERTY() bool bKilled = false;
};

/**
 * M2 档案桥：挂在 PlayerController 上（NetGameMode 在 PostLogin 为远端玩家装配）。
 *
 * 客户端（本机控制器）：每 0.8s 心跳上行本机档案快照（ServerSubmitProfile）——
 *   玩家在背包/装备/喝药等所有既有 UI 路径上的改动全部由此同步到服务端。
 * 服务端（权威）：为远端玩家维护影子档案（UColdSteelStatusModel::CreateShadowModel，
 *   目录状态复制自主机单例），应用到服务端 pawn（ApplyColdSteelProfile 全链路生效）；
 *   镜像 MirrorProfile 仅在服务端主动改档时下发（M3 伤害回程等），当前透传模式不回声；
 *   脏档案 20s 节流落盘主机（ColdSteelMP_<玩家键> 槽）。
 */
UCLASS(ClassGroup=(ColdSteelNet))
class COLDSTEELNET_API UColdSteelNetChannelComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UColdSteelNetChannelComponent();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    /** 客户端→服务端：档案快照分块上行（FColdSteelProfile 含 TMap 不能直接进 RPC；
     *  且整块字节数会超 RPC 载荷上限被静默丢弃，固定 8KB 分片、reliable 保序、UploadId 防串包）。 */
    UFUNCTION(Server, Reliable)
    void ServerSubmitProfileChunk(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk);

    /** 服务端→客户端：权威镜像（预留 M3 伤害/权威更正回程；透传模式不写）。 */
    UPROPERTY(ReplicatedUsing=OnRep_MirrorBlob)
    TArray<uint8> MirrorBlob;

    UFUNCTION()
    void OnRep_MirrorBlob();

    /** M3：客户端命中上报（游戏模块 ApplyHit 经 ColdSteelSkills::NetHitForward 转发到这）。 */
    UFUNCTION(Server, Reliable)
    void ServerReportHit(const FColdSteelNetHitReport& Report);

    /** M3：服务端命中回执（客户端命中标记/击杀反馈）。 */
    UFUNCTION(Client, Reliable)
    void ClientConfirmHit(const FColdSteelNetHitReceipt& Receipt);

    /** M3：游戏模块转发钩子的静态入口（模块启动时注册）。 */
    static bool ForwardHitStatic(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);

    /** 服务端：影子档案（应用到服务端 pawn 的数据源；主机单例之外每远端玩家一份）。 */
    UPROPERTY(Transient)
    TObjectPtr<UColdSteelStatusModel> ShadowModel;

    /** 服务端：服务端初始化（PostLogin 时机调用）——登记槽名并尝试从主机磁盘载回老档案。 */
    void InitializeGuest(const FString& InSlotName);

private:
    /** 服务端：接收一份客人档案（上行 RPC 与磁盘载回共用）。 */
    void ApplyGuestProfile(const FColdSteelProfile& Profile);
    void ApplyShadowToServerPawn();
    void SaveShadowToHostDisk();

    FString SlotName;
    float ClientHeartbeat = 0.f;
    float ServerSaveTimer = 0.f;
    bool bServerDirty = false;
    /** 复用的序列化载体，避免每次心跳新建对象。 */
    UPROPERTY(Transient)
    TObjectPtr<UColdSteelProfileSave> ScratchSave;
    /** M3 测试钩：-MPClientShot 启动参数，客户端入图 12s 后向最近怪物发一发合成命中（自动化验证战斗链）。 */
    float SyntheticShotCountdown = -1.f;
    int32 SyntheticShotAttempts = 0;
    /** 分块上传状态：客户端侧计数器 / 服务端侧攒包。 */
    int32 UploadCounter = 0;
    /** 变更检测+限速上行：与上次成功上传的整块比对，无变化零流量；1KB 分片、每 tick ≤2 片。 */
    static constexpr int32 ProfileChunkSize = 1024;
    TArray<uint8> LastSentBlob;
    bool bHasLastSent = false;
    TArray<uint8> PendingUpload;
    int32 PendingUploadId = 0;
    int32 NextChunkIndex = 0;
    int32 PendingTotalChunks = 0;
    float HeartbeatTimer = 2.f;
    int32 IncomingUploadId = INDEX_NONE;
    int32 IncomingReceived = 0;
    int32 IncomingTotal = 0;
    TArray<uint8> IncomingBlob;
    /** 最近一次已应用的上传整块：字节级相同的新快照直接跳过（perf：HP/计时漂移导致的 2s 重传不再重复触发 ApplyColdSteelProfile）。 */
    TArray<uint8> LastAppliedBlob;
};
