#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/ElectricMagicTypes.h"
#include "Super90NetworkTypes.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "ColdSteelStationNetwork.h"
#include "../Building/ColdSteelDoorNetState.h"
#include "ColdSteelPlayerState.generated.h"

class UColdSteelStatusModel;
class UColdSteelProfileSave;
class APlayerController;
class AFPSGAMECharacter;
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
    UPROPERTY() FName HitComponent;
    UPROPERTY() FVector_NetQuantizeNormal Direction;
    UPROPERTY() FString ItemDefinition;
    /** 客户端自报标量伤害：仅作参考，服务端按武器包络钳制。 */
    UPROPERTY() float ClaimedDamage = 0.f;
    /** 汇聚附魔消耗的弹数（0/1=无汇聚）；服务端按影子档案同参数复算倍率。 */
    UPROPERTY() uint8 ConvergenceRounds = 0;
    /** bit0 bMeleeStrike / bit1 bRifle / bit2 bPistol / bit3 bMelee / bit4 bRicochet / bit5 bInheritedCritical / bit6 bFiredRound / bit7 Azure Dragon active */
    UPROPERTY() uint8 Flags = 0;
    /** 攻击语义位（与 FColdSteelSkillShot::AttackMeta 同码）：0x0F=连段阶段，0x10=重击，0x20=旋风，0x40=裂斩波。 */
    UPROPERTY() uint8 AttackMeta = 0;
    /** 攻击语义上下文：弓=拉弦比 0-1。服务端据此把伤害完全重算为权威值。 */
    UPROPERTY() float DamageContext = 0.f;
    /** EMonsterAttackForm 的窄化传输；0 表示沿用服务端 Snapshot 推断值。 */
    UPROPERTY() uint8 AttackForm = 0;
    UPROPERTY() double ClientFireTime = 0.0;
    /** Groups targets from one blade swing; carries no client-provided buff values. */
    UPROPERTY() uint32 GuardAttackSerial = 0;
    UPROPERTY() uint32 QuickCombatSerial = 0;
};

/**
 * 施法意图上报（客户端→服务端）：A 模式服务端化通道——
 * 客户端只报"放了哪个技能+相位+瞄准上下文"，消耗校验、orb 生成、弹道与伤害结算
 * 全部在服务端按影子档案执行，法术实体以复制 actor 回流到各端。
 * Phase: 0=凝聚 1=释放 2=未释放取消 3=弃置 4=龙息按 CastId 停止／取消。
 * 各字段按技能取用：AimPoint=瞄准/放置点（龙息为眼部瞄准空间的杖尖偏移）；AimNormal=放置朝向/坡面法线/弹道方向；
 * Variant=形态位（冰墙 0=高 1=低；圣光 bit0=自我施放）；Target=目标类法术锁定的 actor；
 * Charge=充能类技能的充量比（thunderLance）。
 */
USTRUCT()
struct FColdSteelNetCastRequest
{
    GENERATED_BODY()
    UPROPERTY() FName SkillId;
    UPROPERTY() TObjectPtr<APawn> SourcePawn=nullptr;
    UPROPERTY() uint32 Sequence=0;
    UPROPERTY() uint32 CastId=0; // Dragon/Storm prepare sequence; stable through release/cancellation.
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
    UPROPERTY() bool bFirearm = false;
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
 * - 私有数据（服务端权威档案回写 MirrorBlob）仅通过分片 Client RPC 发给拥有者。
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
    friend class UBowSkillTrainingAuditCommandlet;

public:
    UFUNCTION(Client,Reliable) void ClientGlassBroken(const FString& ActorName,FVector_NetQuantize Point,FVector_NetQuantizeNormal Direction);
    UFUNCTION(Client,Reliable) void ClientGeneratedDoorSwing(const FString& ActorName,const FColdSteelDoorNetState& State);
    UFUNCTION(Client,Reliable) void ClientGeneratedContainerOpened(const FString& ActorName);
    AColdSteelPlayerState();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void Tick(float DeltaSeconds) override;

    /** 服务端：客人档案位名登记 + 尝试从主机磁盘载回旧档（NetWorldSubsystem 轮询调）。 */
    void InitializeGuest(const FString& InSlotName);
    void InitializeHostSession();
    bool IsGuestInitialized() const { return bGuestInitialized; }

    /** 服务端影子档案（权威数值源）。 */
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> ShadowModel;
    UColdSteelStatusModel* GetShadowModel() const { return ShadowModel; }

    /** 公开信息（全员复制）。 */
    UPROPERTY(ReplicatedUsing=OnRep_PublicInfo)
    FColdSteelPublicPlayerInfo PublicInfo;
    UFUNCTION() void OnRep_PublicInfo();
    void GrantSessionDoorKey(FName Key);
    bool HasSessionDoorKey(FName Key) const {return SessionDoorKeys.Contains(Key);}
private:
    // Session state survives pawn replacement and seamless travel, never disk saves.
    UPROPERTY(Replicated) TArray<FName> SessionDoorKeys;
public:

    /** 私有镜像由拥有者按分片组装；整块字节数组不能作为复制属性发送。 */
    UPROPERTY(Transient)
    TArray<uint8> MirrorBlob;
    UFUNCTION() void OnRep_MirrorBlob();
    UFUNCTION(Client, Reliable)
    void ClientReceiveProfileChunk(uint32 TransferId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk,APawn* SourcePawn,uint32 CastSequence,double CapturedAt);

    /** 档案快照分块上行（客户端→服务端）。TMap 不能直接 RPC，序列化成字节流按 1KB 分片。 */
    UFUNCTION(Server, Reliable)
    void ServerSubmitProfileChunk(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk,uint32 AmmoRevision,APawn* SourcePawn);
    UFUNCTION(Client,Reliable) void ClientRetryProfileUpload(int32 UploadId);

    uint32 RequestSuper90Shot(const FString& Weapon,const FVector& Eye,const FVector& Muzzle,const FVector& Aim,bool Aiming,int32 PredictedRounds);
    void RequestSuper90Reload(const FString& Weapon,const FString& Ammo);
    void CancelSuper90Reload(bool Soft);
    bool IsSuper90ReloadPending() const {return bSuper90ReloadPending;}
    bool IsSuper90ServerReady(const FString& Weapon) const {return Super90ServerWeapons.Contains(Weapon);}
    UFUNCTION(Server,Reliable) void ServerSuper90Shot(uint32 Sequence,const FString& Weapon,FVector_NetQuantize Eye,
        FVector_NetQuantize Muzzle,FVector_NetQuantizeNormal Aim,bool Aiming,double FiredAt,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerSuper90Reload(uint32 Sequence,const FString& Weapon,const FString& Ammo,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerSuper90Cancel(uint32 Sequence,bool Soft,APawn* SourcePawn);
    UFUNCTION(Client,Reliable) void ClientSuper90Ammo(const FSuper90NetAmmoState& State);
    UFUNCTION(NetMulticast,Unreliable) void MulticastSuper90Shot(class AFPSGAMECharacter* Shooter,FVector_NetQuantize Muzzle,
        const TArray<FVector_NetQuantizeNormal>& Directions,float Speed,float Range,bool Aiming,bool Suppressed,const FString& Weapon,float FiredAt);

    /** 客户端命中上报：只报开火几何与武器声明，数值由服务端按影子档案重算。 */
    UFUNCTION(Server, Reliable)
    void ServerReportHit(const FColdSteelNetHitReport& Report);
    UFUNCTION(Server,Reliable) void ServerReleaseRiftSlash(uint32 Sequence,const FString& Weapon,FVector_NetQuantize Origin,FVector_NetQuantizeNormal Direction,uint32 GuardSerial,bool bAzureDragon,bool bClovenCounter);
    uint32 LastRiftSequence=0;
    double LastRiftReleasedAt=-100.;
    TWeakObjectPtr<APawn> RiftPawn;

    /** 服务端命中回执。 */
    UFUNCTION(Client, Reliable)
    void ClientConfirmHit(const FColdSteelNetHitReceipt& Receipt);

    /** 远端身体表现：客户端上报离散动作开始（换弹/检视/施法等），服务端写进身体复制态。 */
    UFUNCTION(Server, Reliable)
    void ServerReportBodyAction(uint8 Action, FName Variant, float Duration);

    /** 远端身体表现：客户端开火时刻戳（枪响姿势用）。 */
    UFUNCTION(Server, Unreliable)
    void ServerReportShotStamp();

    /** One reliable start/cancel per draw; no per-frame timing reports. */
    UFUNCTION(Server, Reliable)
    void ServerSetBowDraw(AFPSGAMECharacter* Character,const FString& Weapon,bool bDrawing,float CarriedSeconds);

    /** 施法意图上报：见 FColdSteelNetCastRequest。 */
    UFUNCTION(Server, Reliable)
    void ServerCastSpell(const FColdSteelNetCastRequest& Request);
    uint32 RequestCastSpell(FColdSteelNetCastRequest Request);

    /** 施法回执：Code 0=受理；其余为拒因，Phase 回传以便本地收尾。 */
    UFUNCTION(Client, Reliable)
    void ClientCastResult(FName SkillId, uint8 Phase, uint8 Code,APawn* SourcePawn,uint32 Sequence,uint32 CastId=0);

    /** Focus intent shares the reliable cast channel: 0 cancel, 1 open, 2 close. */
    UFUNCTION(Server, Reliable)
    void ServerSetSpellbookFocus(AFPSGAMECharacter* Character,uint32 Session,uint8 State);
    UFUNCTION(Client, Reliable)
    void ClientSpellbookFocusStopped(AFPSGAMECharacter* Character,uint32 Session,bool Interrupted,double ManaLossTotal);
    void NotifySpellbookFocusStopped(AFPSGAMECharacter* Character,uint32 Session,bool Interrupted);

    /** 服务端最近一次已接受的合法命中时刻（服务端时钟域）——远端身体开火表现读它。 */
    double LastValidatedShotAt = -100.0;

    /** ColdSteelSkills::ApplyHit 的转发器实现：从射手 Pawn 找本 PlayerState 再发 ServerReportHit。
     *  ColdSteelNet 模块启动时注册到 NetHitForward()。 */
    static bool ForwardHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);

public:
    /** 服务端：影子档案落盘到主机磁盘（玩家离开时由 NetWorldSubsystem 调用）。 */
    bool SaveShadowToHostDisk();
    void PrepareForDisconnect();
    const FString& CampfireGuestSlot() const { return SlotName; }
    /** UI sends intents on the owned PlayerState channel, never on a world-owned campfire. */
    bool RequestCampfire(class AColdSteelCampfire* Fire,uint8 Action,FName Recipe=NAME_None,int64 Batch=1);
    bool CampfireRequestPending() const { return bCampfirePending; }
    const FString& CampfireMessage() const { return CampfireResultText; }
    UFUNCTION(Server,Reliable) void ServerCampfireRequest(AColdSteelCampfire* Fire,int32 RequestId,uint8 Action,FName Recipe,int64 Batch,int64 InventoryRevision,APawn* RequestPawn);
    UFUNCTION(Client,Reliable) void ClientCampfireResult(int32 RequestId,int64 InventoryRevision,const FString& Reason);
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool RequestInventoryAction(EColdSteelInventoryAction Action,const FString& Item=FString(),AActor* Target=nullptr);
    bool RequestInventoryAction(FColdSteelInventoryRequest Request);
    void AcknowledgeInventoryProfile();
    void SyncMartialCooldowns(const FColdSteelProfile& Profile,bool Immediate);
    UFUNCTION(Server,Reliable) void ServerMartialCooldowns(APawn* SourcePawn,int64 Revision,float Whirlwind,
        float WhirlwindDuration,float Uppercut,float UppercutDuration,double CapturedAt);
    bool ExecuteWorldAction(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason);
    bool RequestTeamTravel(AActor* Entrance);
    UFUNCTION(Server,Reliable) void ServerTeamTravel(AActor* Entrance);
    UFUNCTION(Client,Reliable) void ClientPrepareTeamTravel(FGuid TravelId);
    UFUNCTION(Server,Reliable) void ServerTeamTravelReady(FGuid TravelId,int32 AcceptedUploadId);
    UFUNCTION(Client,Reliable) void ClientTeamTravelSaveFailed(FGuid TravelId,const FString& Reason);
    void AbortTeamTravel(const FString& Reason);
    void InvalidateTeamTravelReady();
    bool SaveTeamTravelParticipant();
    virtual void CopyProperties(APlayerState* Other) override;
    void TickTeamTravel();
    void TickWorldNetwork(float Delta);
    bool ExecuteStation(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason);
    bool StationReach(FName Kind) const;
    void InitializeStations(UColdSteelStatusModel* M);
    void TickStations(float Delta);
    UFUNCTION(Client,Reliable) void ClientAlchemyState(const FColdSteelAlchemyNetState& State,APawn* SourcePawn);
    UPROPERTY() TObjectPtr<class UColdSteelAlchemySystem> GuestAlchemy;
    uint32 AlchemyInputSerial=0,AlchemyAuthoritySequence=0;
    FString LastAlchemyStateId;
    int64 LastAlchemyStateRevision=-1;
    bool bAlchemyWasActive=false,bAlchemyWasSaving=false;
    bool CloseStationSessions();
    UFUNCTION(Server,Reliable) void ServerStationInput(APawn* InputPawn,const FString& JobId,FName System,uint8 Op,FName Recipe,int32 Index,FVector2D A,FVector2D B,uint32 Sequence);
    void TickWoodNetwork();
    UFUNCTION(Client,Reliable) void ClientWoodChunk(int32 Transfer,uint32 Ack,int32 Index,int32 Total,const TArray<uint8>& Bytes,APawn* SourcePawn);
    uint32 WoodInputSerial=0,WoodAuthoritySequence=0,WoodOutgoingAck=0,WoodIncomingAck=0;
    int32 WoodTransfer=0,WoodChunk=0,WoodReceiving=0,WoodTotal=0;
    TArray<uint8> WoodOutgoing,WoodIncoming;
    TWeakObjectPtr<APawn> WoodOutgoingPawn;
    double WoodSendAt=0.,WoodPublishAt=0.;
    bool bWoodDirty=false;
    UFUNCTION(Client,Reliable) void ClientStationState(const FColdSteelForgeNetState& Forge,const FColdSteelAssemblyNetState& Assembly,APawn* SourcePawn);
    UPROPERTY() TObjectPtr<class UColdSteelForgingSystem> GuestForge;
    UPROPERTY() TObjectPtr<class UGunAssemblySystem> GuestAssembly;
    UPROPERTY() TObjectPtr<class UWoodworkingSystem> GuestWood;
    double StationPublishAt=0,CalibrationAt=0,HarvestAt=0;
    bool bStationDirty=false;
    UFUNCTION(Client,Reliable) void ClientWorldChunk(int32 Serial,int32 Index,int32 Total,const TArray<uint8>& Bytes);
    UPROPERTY() TObjectPtr<class UColdSteelWorldSnapshot> PendingWorldState;
    uint64 LastBuildingSentRevision=0;
    TWeakObjectPtr<class AVoxelBuildWorld> LastBuildingSentWorld;
    TWeakObjectPtr<UWorld> WorldStreamWorld;
    void EnsureWorldStreamContext();
    bool ApplyWorldState();
    TArray<uint8> WorldOutgoing,WorldIncoming,WorldLastSent;
    int32 WorldSerial=0,WorldChunk=0,WorldReceiveSerial=0,WorldReceiveTotal=0;
    double WorldSendAt=0,WorldSnapshotAt=0,WorldApplyAt=0;
    bool bWorldHarvestApplied=false;
    bool bTravelFlush=false,bTravelReady=false,bTravelNeedsFreshUpload=false;
    bool bDisconnectPrepared=false;
    bool bWasLocalOwner=false;
    FGuid TeamTravelId;
    TWeakObjectPtr<UWorld> TeamTravelWorld;
    TWeakObjectPtr<APawn> TeamTravelPawn;
    FString TeamDestination,TeamOptions;
    double TeamTravelStarted=0.;
    bool InventoryRequestPending() const {return bInventoryRequestPending;}
    void RequestQuickCombat(float Duration,float PredictedCost);
    void FinishQuickCombat();
    UFUNCTION(Server,Reliable) void ServerQuickCombat(uint32 Sequence,APawn* Pawn,float Duration,bool Finish);
    UFUNCTION(Client,Reliable) void ClientQuickCombatRejected(uint32 Sequence);
    UFUNCTION(Server,Reliable) void ServerInventoryAction(const FColdSteelInventoryRequest& Request);
    UFUNCTION(Client,Reliable) void ClientInventoryReplyChunk(uint32 Sequence,int32 Index,int32 Total,const TArray<uint8>& Chunk);
    UFUNCTION(Client,Reliable) void ClientInventoryBaseline(const FString& Digest,int64 Souls,int64 Credits,int64 Debits);
    UFUNCTION(Server,Reliable) void ServerWarehouseOpen(class AColdSteelWarehouseChest* Chest,bool Open);
    UFUNCTION(Client,Reliable) void ClientContainerInvalidated(AActor* Target);
    UFUNCTION(NetMulticast,Reliable) void MulticastSharedChestOpened(AActor* Target);

private:
    bool bContainerNeedsRefresh=false;
    friend class UColdSteelAcquisitionAuditCommandlet;
    void TickContainerRefresh();
    uint32 QuickCombatSequence=0,QuickCombatServerSequence=0;
    double QuickCombatUntil=0.;
    TMap<uint32,float> QuickCombatPredictedCosts;
    TWeakObjectPtr<APawn> QuickCombatPawn;
    TSet<TWeakObjectPtr<AActor>> QuickCombatTargets;
    int64 ConfirmedSouls=-1,ConfirmedSoulCredits=-1,ConfirmedSoulDebits=-1;
    bool bInventoryRequestPending=false;
    bool bInventoryWaitingUpload=false;
    UPROPERTY() FColdSteelInventoryRequest PendingInventoryRequest;
    void DispatchInventoryAfterUpload();
    TArray<uint8> AcknowledgedInventoryBaseline;
    static TArray<uint8> InventoryBaseline(const FColdSteelProfile& Profile);
    void SendInventoryBaseline();
    bool ExecuteBowShot(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason);
    double LastBowShotAt=-100.;
    TWeakObjectPtr<APawn> BowDrawPawn;
    FString BowDrawWeapon;
    double BowDrawStartedAt=-1.;
    float BowDrawSeconds=0.f;
    TWeakObjectPtr<APawn> InventoryRequestPawn;
    uint32 InventoryRequestSequence=0,LastInventoryRequestSequence=0,ReplySequence=0;
    TArray<uint8> InventoryReplyOutgoing,InventoryReplyIncoming;
    int32 InventoryReplyChunk=0,InventoryReplyTotal=0;
    double LastInventoryReplyAt=0.;
    void TickInventoryReply();
    void QueueInventoryReply(const FColdSteelInventoryRequest& Request,bool Success,const FString& Reason,
        const FColdSteelProfile& Before,const FColdSteelProfile& After);
    uint32 Super90LocalSequence=0,Super90ProcessedSequence=0,Super90Revision=0,Super90AppliedRevision=0;
    uint32 PendingSuper90Revision=0,IncomingSuper90Revision=0;
    TArray<FSuper90PredictedShot> Super90PredictedShots;
    TSet<FString> Super90ServerWeapons;
    TArray<int64> Super90PouchDelta={0,0,0},Super90AppliedPouchDelta={0,0,0};
    TMap<uint32,TArray<int64>> Super90PouchHistory;
    FSuper90ServerReload Super90Reload;
    bool bSuper90ReloadPending=false,bSuper90SoftCancelSent=false;
    double Super90LastFireTime=-100.,Super90NextFireTime=-100.;
    void TickSuper90Authority(float DeltaSeconds);
    void TickSuper90Recovery();
    TWeakObjectPtr<APawn> Super90ClientPawn;
    UPROPERTY() FSuper90NetAmmoState PendingSuper90State;
    bool bPendingSuper90State=false;
    void SendSuper90Ammo(bool Rejected=false);
    void RecordSuper90PouchChange(const FColdSteelProfile& Before,const FColdSteelProfile& After);
    bool RebaseSuper90Upload(FColdSteelProfile& Incoming,const FColdSteelProfile& Previous,bool KeepServerPouch) const;
    void PreserveSuper90ClientAmmo(FColdSteelProfile& Incoming) const;
    class AFPSGAMECharacter* Super90AuthorityPawn(const FString& Weapon);
    void FinishSuper90AuthorityReload();
    bool bCampfirePending=false,bCampfireWaitingUpload=false;
    int32 CampfireRequestId=0,LastCampfireRequestId=0;
    int64 CampfireResultRevision=-1;
    uint8 PendingCampfireAction=0;
    FName PendingCampfireRecipe;
    int64 PendingCampfireBatch=1;
    TWeakObjectPtr<AColdSteelCampfire> PendingCampfire;
    TWeakObjectPtr<APawn> PendingCampfirePawn;
    FString CampfireResultText;
    double LastCampfireRequestAt=-100;
    void FinishCampfireReceipt();
    void DispatchCampfireAfterUpload();
    bool ApplyGuestProfile(const FColdSteelProfile& Profile);
    UFUNCTION(Client,Reliable) void ClientProfileSyncRejected(const FString& Reason);
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
    bool bRestoreGuestAmmo=false;
    double MartialPublishAt=0.;
    FGuid BoundProfileId;
    bool bServerDirty = false;
    float ServerSaveTimer = 0.f;
    float ShadowMirrorTimer = 0.f;
    float PublicInfoTimer = 0.f;
    /** 表现层 RPC 防抖：远端开火戳/离散动作上报的最小到达间隔。 */
    double LastShotStampAt = -100.0;
    double LastBodyActionAt = -100.0;

    /** 服务端施法执行器：按 SkillId 分派到各族实现（当前仅 fireball）。 */
    void ExecuteCastRequest(const FColdSteelNetCastRequest& Request);
    /** 服务端已凝聚未发射的权威 orb：发射/取消/看门狗清理共用。 */
    void CancelPendingNetworkCast();
    TWeakObjectPtr<APawn> PendingCastPawn;
    TWeakObjectPtr<AActor> PendingCastOrb;
    FName PendingCastSkill = NAME_None;
    double PendingCastAt = -100.0;
    float PendingCastPaidMana = 0.f;
    uint32 PendingIdentifiedCastId=0;
    // Authoritative paid-cast snapshots survive chain consumption until release.
    FIceWallCast PendingIceWallStats;
    FBlizzardCast PendingBlizzardStats;
    FHolyLightCast PendingHolyLightStats;
    FLightningCast PendingLightningStats;
    FFireMagicCast PendingFireMagicStats;
    FElectricMagicCast PendingElectricMagicStats;
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
    /** 最近分片发送的真实时间；整块完成后也作为 30s 生命体征补传的基准。 */
    double LastUploadAt = 0.0;
    static constexpr double VitalFlushInterval = 30.0;
    TArray<uint8> PendingUpload;
    TWeakObjectPtr<APawn> PendingUploadPawn,IncomingUploadPawn;
    int32 PendingUploadId = 0;
    int32 NextChunkIndex = 0;
    int32 PendingTotalChunks = 0;
    float HeartbeatTimer = 2.f;
    int32 IncomingUploadId = INDEX_NONE;
    int32 LastAcceptedUploadId = INDEX_NONE;
    int32 IncomingReceived = 0;
    int32 IncomingTotal = 0;
    TArray<uint8> IncomingBlob;
    /** 最近一次已应用的上传整块：字节级相同的新快照直接跳过应用。 */
    TArray<uint8> LastAppliedBlob;
    /** 最近一次下发给拥有者的镜像整块：无服务端侧变更则不重复写 MirrorBlob。 */
    TArray<uint8> LastMirrorBlob;
    TArray<uint8> PendingMirrorBlob;
    TWeakObjectPtr<APawn> PendingMirrorPawn,ReceivingMirrorPawn;
    bool bMirrorReady=false;
    uint32 LocalCastSequence=0,ProcessedCastSequence=0,PendingMirrorCastSequence=0,ReceivingMirrorCastSequence=0;
    double PendingMirrorCapturedAt=0.,ReceivingMirrorCapturedAt=0.;
    uint32 MirrorTransferId = 0;
    int32 NextMirrorChunk = 0;
    double LastMirrorChunkAt = 0.0;
    uint32 ReceivingMirrorId = 0;
    int32 ReceivingMirrorTotal = 0;

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
