#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ColdSteelPlayerState.generated.h"

class UColdSteelStatusModel;
class UColdSteelProfileSave;
class APlayerController;
struct FColdSteelSkillShot;
struct FHitResult;

/**
 * 命中上报（客户端→服务端）的权威化口径：
 * 客户端只申报"我开枪了+几何上下文"（原点/命中点/骨骼/方向/武器声明/自报伤害），
 * 伤害构成（精通/暴击/穿透/弹药效果/面板拆项）一律由服务端按影子档案重算，
 * 自报伤害被钳制在服务端武器包络内。命中结论、目标与位置由服务端校验。
 */
USTRUCT()
struct FColdSteelNetHitReport
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    /** 客户端开火瞬间的相机/枪口原点——服务端用于位置容差与将来 rewind。 */
    UPROPERTY() FVector_NetQuantize AimOrigin;
    UPROPERTY() FVector_NetQuantize ImpactPoint;
    UPROPERTY() FVector_NetQuantizeNormal HitNormal;
    UPROPERTY() FName BoneName;
    UPROPERTY() FVector_NetQuantizeNormal Direction;
    UPROPERTY() FString ItemDefinition;
    /** 客户端自报标量伤害：仅作参考，服务端按武器包络钳制。 */
    UPROPERTY() float ClaimedDamage = 0.f;
    /** 汇聚附魔消耗的弹数（0/1=无汇聚）；服务端按影子档案同参数复算倍率。 */
    UPROPERTY() uint8 ConvergenceRounds = 0;
    /** bit0 bMeleeStrike / bit1 bRifle / bit2 bPistol / bit3 bMelee / bit4 bRicochet / bit5 bInheritedCritical / bit6 bFiredRound */
    UPROPERTY() uint8 Flags = 0;
    /** 攻击语义位（与 FColdSteelSkillShot::AttackMeta 同码）：0x0F=连段阶段，0x10=重击，0x20=旋风，0x40=裂斩波。 */
    UPROPERTY() uint8 AttackMeta = 0;
    /** 攻击语义上下文：弓=拉弦比 0-1。服务端据此把伤害完全重算为权威值。 */
    UPROPERTY() float DamageContext = 0.f;
    /** EMonsterAttackForm 的窄化传输；0 表示沿用服务端 Snapshot 推断值。 */
    UPROPERTY() uint8 AttackForm = 0;
    UPROPERTY() double ClientFireTime = 0.0;
};

/**
 * 施法意图上报（客户端→服务端）：A 模式服务端化通道——
 * 客户端只报"放了哪个技能+相位+瞄准上下文"，消耗校验、orb 生成、弹道与伤害结算
 * 全部在服务端按影子档案执行，法术实体以复制 actor 回流到各端。
 * Phase: 0=凝聚(Prepare) 1=发射/释放(Launch/Commit) 2=凝聚期取消(退蓝清CD) 3=弃置悬停体(只清占用)。
 * 各字段按技能取用：AimPoint=瞄准/放置点；AimNormal=放置朝向/坡面法线/弹道方向；
 * Variant=形态位（冰墙 0=高 1=低；圣光 bit0=自我施放）；Target=目标类法术锁定的 actor；
 * Charge=充能类技能的充量比（thunderLance）。
 */
USTRUCT()
struct FColdSteelNetCastRequest
{
    GENERATED_BODY()
    UPROPERTY() FName SkillId;
    UPROPERTY() uint8 Phase = 0;
    UPROPERTY() FVector_NetQuantize AimPoint = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal AimNormal = FVector::UpVector;
    UPROPERTY() FVector_NetQuantizeNormal AimAxis = FVector::ForwardVector; // 暴雪区椭圆长轴
    UPROPERTY() uint8 Variant = 0;
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() float Charge = 0.f;
};

/** 服务端→客户端的命中回执（命中标记/击杀反馈）。 */
USTRUCT()
struct FColdSteelNetHitReceipt
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() float Applied = 0.f;
    UPROPERTY() bool bCritical = false;
    UPROPERTY() bool bKilled = false;
    UPROPERTY() bool bRejected = false;
};

/** 全员可见的玩家公开信息（名牌/HUD/远端表现用的小字段，私有数据走 OwnerOnly）。 */
USTRUCT(BlueprintType)
struct FColdSteelPublicPlayerInfo
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString ActiveWeaponDefinition;
    UPROPERTY(BlueprintReadOnly) int32 Level = 1;
    UPROPERTY(BlueprintReadOnly) int32 Kills = 0;
};

/**
 * 联机玩家数据归属（重构自 UColdSteelNetChannelComponent 的档案/命中通路）：
 * - 公开数据（武器/等级/击杀）复制到全员——远端玩家的名牌与 UI 数据源。
 * - 私有数据（服务端权威档案回写 MirrorBlob）仅复制给拥有者（COND_OwnerOnly）。
 * - 服务端在这里持有每个远端玩家的影子档案（UColdSteelStatusModel::CreateShadowModel），
 *   命中校验、死亡结算、身体表现都从这里读权威状态。
 * - 客户端侧把本机档案快照分块上行给服务端（ServerSubmitProfileChunk）。
 * PlayerState 本身随 AGameModeBase::PlayerStateClass 落到每张图——
 * AFPSGAMEGameMode（单机 GameMode 基类）与其派生（含 NetGameMode、丘陵）统一挂载，
 * 不再依赖地图是否恰好使用 NetGameMode。
 */
UCLASS()
class FPSGAME_API AColdSteelPlayerState : public APlayerState
{
    GENERATED_BODY()

public:
    AColdSteelPlayerState();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void Tick(float DeltaSeconds) override;

    /** 服务端：客人档案位名登记 + 尝试从主机磁盘载回旧档（NetWorldSubsystem 轮询调）。 */
    void InitializeGuest(const FString& InSlotName);
    bool IsGuestInitialized() const { return bGuestInitialized; }

    /** 服务端影子档案（权威数值源）。 */
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> ShadowModel;
    UColdSteelStatusModel* GetShadowModel() const { return ShadowModel; }

    /** 公开信息（全员复制）。 */
    UPROPERTY(ReplicatedUsing=OnRep_PublicInfo)
    FColdSteelPublicPlayerInfo PublicInfo;
    UFUNCTION() void OnRep_PublicInfo();

    /** 私有镜像（COND_OwnerOnly）：服务端权威档案回写，仅拥有者可见。 */
    UPROPERTY(ReplicatedUsing=OnRep_MirrorBlob)
    TArray<uint8> MirrorBlob;
    UFUNCTION() void OnRep_MirrorBlob();

    /** 档案快照分块上行（客户端→服务端）。TMap 不能直接 RPC，序列化成字节流按 1KB 分片。 */
    UFUNCTION(Server, Reliable)
    void ServerSubmitProfileChunk(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk);

    /** 客户端命中上报：只报开火几何与武器声明，数值由服务端按影子档案重算。 */
    UFUNCTION(Server, Reliable)
    void ServerReportHit(const FColdSteelNetHitReport& Report);

    /** 服务端命中回执。 */
    UFUNCTION(Client, Reliable)
    void ClientConfirmHit(const FColdSteelNetHitReceipt& Receipt);

    /** 远端身体表现：客户端上报离散动作开始（换弹/检视/施法等），服务端写进身体复制态。 */
    UFUNCTION(Server, Unreliable)
    void ServerReportBodyAction(uint8 Action, FName Variant, float Duration);

    /** 远端身体表现：客户端开火时刻戳（枪响姿势用）。 */
    UFUNCTION(Server, Unreliable)
    void ServerReportShotStamp();

    /** 施法意图上报：见 FColdSteelNetCastRequest。 */
    UFUNCTION(Server, Reliable)
    void ServerCastSpell(const FColdSteelNetCastRequest& Request);

    /** 施法回执：Code 0=受理；其余为拒因，Phase 回传以便本地收尾。 */
    UFUNCTION(Client, Reliable)
    void ClientCastResult(FName SkillId, uint8 Phase, uint8 Code);

    /** 服务端最近一次已接受的合法命中时刻（服务端时钟域）——远端身体开火表现读它。 */
    double LastValidatedShotAt = -100.0;

    /** ColdSteelSkills::ApplyHit 的转发器实现：从射手 Pawn 找本 PlayerState 再发 ServerReportHit。
     *  ColdSteelNet 模块启动时注册到 NetHitForward()。 */
    static bool ForwardHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);

public:
    /** 服务端：影子档案落盘到主机磁盘（玩家离开时由 NetWorldSubsystem 调用）。 */
    void SaveShadowToHostDisk();

private:
    void ApplyGuestProfile(const FColdSteelProfile& Profile);
    void ApplyShadowToServerPawn();
    void TickUpload(float DeltaSeconds);
    void TickShadowMirror(float DeltaSeconds);
    void TickPublicInfo(float DeltaSeconds);
    bool ValidateHitReport(const FColdSteelNetHitReport& Report, class AFPSGAMECharacter* Shooter, FString& OutReason,
        const struct FColdSteelItem*& OutDeclaredItem);
    /** 服务端权威伤害：按武器族从影子档案同参复算，客户端 ClaimedDamage 只作对账参考。 */
    float ComputeServerDamage(class AFPSGAMECharacter* Shooter, const FColdSteelNetHitReport& Report,
        const struct FColdSteelSkillShot& Shot, const struct FColdSteelItem* DeclaredItem, float ConvergenceScale) const;

    /** 服务端已把影子档案挂载到的 pawn——pawn 重生后要重新挂。 */
    TWeakObjectPtr<AFPSGAMECharacter> ShadowPawn;

    FString SlotName;
    bool bGuestInitialized = false;
    bool bServerDirty = false;
    float ServerSaveTimer = 0.f;
    float ShadowMirrorTimer = 0.f;
    float PublicInfoTimer = 0.f;
    /** 修行点数采纳基线：ApplyGuestProfile 差分出服务端授予增量（升级奖励），
     *  叠回客户端申报值——客户端花费与服务端授予两个写者互不覆盖。 */
    int32 ServerPointsBaseline = 0;
    /** 表现层 RPC 防抖：远端开火戳/离散动作上报的最小到达间隔。 */
    double LastShotStampAt = -100.0;
    double LastBodyActionAt = -100.0;

    /** 服务端施法执行器：按 SkillId 分派到各族实现（当前仅 fireball）。 */
    void ExecuteCastRequest(const FColdSteelNetCastRequest& Request);
    /** 服务端已凝聚未发射的权威 orb：发射/取消/看门狗清理共用。 */
    TWeakObjectPtr<AActor> PendingCastOrb;
    FName PendingCastSkill = NAME_None;
    double PendingCastAt = -100.0;
    float PendingCastPaidMana = 0.f;
    double LastCastRequestAt = -100.0;

    /** 上传节流载体（复用对象，避免每 2s 新建）。 */
    UPROPERTY(Transient)
    TObjectPtr<UColdSteelProfileSave> ScratchSave;

    static constexpr int32 ProfileChunkSize = 1024;
    int32 UploadCounter = 0;
    TArray<uint8> LastSentBlob;
    /** 最近一次上行 blob 的"结构归一"版本（生命体征/冷却/游戏时钟置零后序列化）——
     *  判脏用它，HP/体力/冷却的帧间漂移不再每 2s 触发 84KB 全量重传。 */
    TArray<uint8> LastSentNormBlob;
    /** 在途上传对应的归一 blob，完成时迁入 LastSentNormBlob。 */
    TArray<uint8> PendingNormBlob;
    bool bHasLastSent = false;
    /** 上次整块实际完成上行的时间（世界秒）：结构不变时 30s 兜底把生命体征漂移带上去。 */
    double LastUploadAt = 0.0;
    static constexpr double VitalFlushInterval = 30.0;
    TArray<uint8> PendingUpload;
    int32 PendingUploadId = 0;
    int32 NextChunkIndex = 0;
    int32 PendingTotalChunks = 0;
    float HeartbeatTimer = 2.f;
    int32 IncomingUploadId = INDEX_NONE;
    int32 IncomingReceived = 0;
    int32 IncomingTotal = 0;
    TArray<uint8> IncomingBlob;
    /** 最近一次已应用的上传整块：字节级相同的新快照直接跳过应用。 */
    TArray<uint8> LastAppliedBlob;
    /** 最近一次下发给拥有者的镜像整块：无服务端侧变更则不重复写 MirrorBlob。 */
    TArray<uint8> LastMirrorBlob;

    /** 服务端命中限流：按影子档案的射速发令牌，容忍批量补射（最大连补数）。 */
    float FireTokenBucket = 4.f;
    double LastFireTokenRefillAt = 0.0;

    /** 测试钩：-MPClientWalk 客户端自动驾驶（真实输入路径）/ -MPClientShot 合成命中。
     *  移植自 UColdSteelNetChannelComponent，双进程冒烟断言依赖这两个探针。 */
    bool bClientAutoWalk = false;
    float AutoWalkPhase = 0.f;
    float ClientPosProbe = 0.f;
    float SyntheticShotCountdown = -1.f;
    int32 SyntheticShotAttempts = 0;
    void TickClientDiagnostics(float DeltaSeconds);
};
