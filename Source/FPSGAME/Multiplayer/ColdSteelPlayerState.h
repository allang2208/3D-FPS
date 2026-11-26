#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/IceArmorTypes.h"
#include "../Skills/LightningHasteTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/WhirlwindTypes.h"
#include "../Skills/ShadowStepTypes.h"
#include "../Weapons/Kukri/KukriAttackReceipt.h"
#include "../Skills/ElectricMagicTypes.h"
#include "Super90NetworkTypes.h"
#include "PistolNetworkTypes.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "ColdSteelStationNetwork.h"
#include "../Building/ColdSteelDoorNetState.h"
#include "ColdSteelPlayerProtocol.h"
#include "ColdSteelPlayerState.generated.h"

class UColdSteelStatusModel;
class UColdSteelProfileSave;
class APlayerController;
class AFPSGAMECharacter;
struct FColdSteelSkillShot;
struct FKukriPairedHeavyHit;
struct FColdSteelPreparedHit;
struct FHitResult;
struct FFoodClockSample;

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
    friend struct FSharedFoodSpoilageAuditAccess;

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
    void PublishFoodClock(const FFoodClockSample& Sample);
    UPROPERTY(ReplicatedUsing=OnRep_FoodClock) FColdSteelFoodClockState FoodClockState;
    UFUNCTION() void OnRep_FoodClock();
    TArray<uint8> LastMirrorWithoutFoodTime;
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
    void ClientReceiveProfileChunk(uint32 TransferId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk,APawn* SourcePawn,uint32 CastSequence,double CapturedAt,uint32 GunsmithSequence);

    /** 档案快照分块上行（客户端→服务端）。TMap 不能直接 RPC，序列化成字节流按 1KB 分片。 */
    UFUNCTION(Server, Reliable)
    void ServerSubmitProfileChunk(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk,uint32 AmmoRevision,APawn* SourcePawn,uint32 UploadPistolRevision,uint32 PistolIntentSequence,uint32 GunsmithSequence);
    UFUNCTION(Client,Reliable) void ClientRetryProfileUpload(int32 UploadId);
    UFUNCTION(Client,Reliable) void ClientBlacksmithLesson(FGuid ProfileId,uint8 StageValue);
    UFUNCTION(Client,Reliable) void ClientCarpenterLesson(FGuid ProfileId,uint8 StageValue);
    void NotifyGunsmithApplied(const FString& InstanceId,const TSet<FString>& BowSlots);
    UFUNCTION(Client,Reliable) void ClientStarMarrowSpend(AFPSGAMECharacter* Character,double Total);
    void NotifyMagicCrystalMana(AFPSGAMECharacter* Character,double Total);
    UFUNCTION(Client,Reliable) void ClientMagicCrystalMana(AFPSGAMECharacter* Character,double Total);

    UFUNCTION(Server,Reliable) void ServerRememberPistolShot(uint32 Sequence,const FString& Instance,int32 ActiveSlot,int32 Rounds,APawn* SourcePawn);
    void RequestPistolShot(uint32 Sequence,const FString& Instance,int32 ActiveSlot,int32 Rounds);
    bool RequestPistolReload(const FString& Instance,const FString& Ammo);
    void CancelPistolReload(const FString& Instance);
    bool IsPistolReloadPending(const FString& Instance) const {return PistolPendingReloads.Contains(Instance);}
    bool IsPistolServerReady(const FString& Instance) const {return PistolServerWeapons.Contains(Instance);}
    UFUNCTION(Server,Reliable) void ServerPistolReload(uint32 Serial,const FString& Instance,const FString& Ammo,int32 ActiveSlot,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerPistolCancel(uint32 Serial,const FString& Instance,uint32 ReloadSerial,APawn* SourcePawn);
    UFUNCTION(Client,Reliable) void ClientPistolAmmo(const FPistolNetAmmoState& Receipt);
    void PistolCowboyReload();
    uint32 RequestSuper90Shot(const FString& Weapon,const FVector& Eye,const FVector& Muzzle,const FVector& Aim,bool Aiming,int32 PredictedRounds);
    void RequestSuper90Reload(const FString& Weapon,const FString& Ammo);
    void CancelSuper90Reload(bool Soft);
    void RequestM870PumpInterrupt(const FString& Weapon,uint32 ShotSequence);
    bool IsSuper90ReloadPending() const {return bSuper90ReloadPending;}
    bool IsSuper90ServerReady(const FString& Weapon) const {return Super90ServerWeapons.Contains(Weapon);}
    UFUNCTION(Server,Reliable) void ServerSuper90Shot(uint32 Sequence,const FString& Weapon,FVector_NetQuantize Eye,
        FVector_NetQuantize Muzzle,FVector_NetQuantizeNormal Aim,bool Aiming,double FiredAt,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerSuper90Reload(uint32 Sequence,const FString& Weapon,const FString& Ammo,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerSuper90Cancel(uint32 Sequence,bool Soft,APawn* SourcePawn);
    UFUNCTION(Server,Reliable) void ServerM870PumpInterrupt(uint32 Sequence,const FString& Weapon,
        uint32 ShotSequence,double InterruptedAt,APawn* SourcePawn);
    UFUNCTION(Client,Reliable) void ClientSuper90Ammo(const FSuper90NetAmmoState& State);
    UFUNCTION(NetMulticast,Unreliable) void MulticastSuper90Shot(class AFPSGAMECharacter* Shooter,FVector_NetQuantize Muzzle,
        const TArray<FVector_NetQuantizeNormal>& Directions,float Speed,float Range,bool Aiming,bool Suppressed,const FString& Weapon,float FiredAt,float PumpRate);

    /** 客户端命中上报：只报开火几何与武器声明，数值由服务端按影子档案重算。 */
    UFUNCTION(Server, Reliable)
    void ServerReportHit(const FColdSteelNetHitReport& Report);
    UFUNCTION(Server,Reliable) void ServerReportPairedHeavyHit(const FColdSteelNetHitReport& First,const FColdSteelNetHitReport& Second);
    static bool ForwardPairedHeavyHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot,const FKukriPairedHeavyHit& Pair);
    UFUNCTION(Server,Reliable) void ServerReleaseRiftSlash(uint32 Sequence,const FString& Weapon,FVector_NetQuantize Origin,FVector_NetQuantizeNormal Direction,uint32 GuardSerial,bool bAzureDragon,bool bClovenCounter);
    uint32 LastRiftSequence=0;
    double LastRiftReleasedAt=-100.;
    TWeakObjectPtr<APawn> RiftPawn;

    /** 服务端命中回执。 */
    UFUNCTION(Client, Reliable)
    void ClientConfirmHit(const FColdSteelNetHitReceipt& Receipt);
    UFUNCTION(Client,Reliable) void ClientConfirmBladeHit(const FColdSteelNetHitReceipt& Receipt,APawn* Attacker,const FHitResult& Hit,uint32 OwnerSwing,uint8 Phase);
    UFUNCTION(Client,Reliable) void ClientConfirmTorchHit(const FColdSteelNetHitReceipt& Receipt,APawn* Attacker,FVector_NetQuantize10 Point,uint32 StrikeSerial,bool bQuick);

    /** 远端身体表现：客户端上报离散动作开始（换弹/检视/施法等），服务端写进身体复制态。 */
    UFUNCTION(Server, Reliable)
    void ServerReportBodyAction(uint8 Action, FName Variant, float Duration);

    /** 远端身体表现：客户端开火时刻戳（枪响姿势用）。 */
    UFUNCTION(Server, Unreliable)
    void ServerReportShotStamp();
    UFUNCTION(Server,Reliable)
    void ServerRememberM24Launch(APawn* SourcePawn,const FString& Instance,uint32 Sequence,int32 Rounds);

    /** One reliable start/cancel per draw; no per-frame timing reports. */
    UFUNCTION(Server, Reliable)
    void ServerSetBowDraw(AFPSGAMECharacter* Character,const FString& Weapon,bool bDrawing,float CarriedSeconds,FGuid DrawId);

    bool IsBowDrawActive(const AFPSGAMECharacter* Character) const;
    void CancelBowDraw(bool bExhausted=false);
    void ResetBowPerfectSpeedBonus();
    UFUNCTION(Client, Reliable)
    void ClientCancelBowDraw(AFPSGAMECharacter* Character,const FString& Weapon,FGuid DrawId,bool bExhausted);
    UFUNCTION(Client, Reliable)
    void ClientConfirmBowDraw(AFPSGAMECharacter* Character,const FString& Weapon,FGuid DrawId,float FullDrawSeconds,bool PerfectSpeed);

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
    /** 同一发的多弹丸/穿透命中共享一次暴击样本（按上报开火时刻归并，2026-10-19）。 */
    double LastHitCriticalTime = -1.0;
    float LastHitCriticalRoll = -1.f;

    /** ColdSteelSkills::ApplyHit 的转发器实现：从射手 Pawn 找本 PlayerState 再发 ServerReportHit。
     *  ColdSteelNet 模块启动时注册到 NetHitForward()。 */
    static bool ForwardHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);

public:
    /** 服务端：影子档案落盘到主机磁盘（玩家离开时由 NetWorldSubsystem 调用）。 */
    bool SaveShadowToHostDisk();
    void MarkGuestProfileDirty() { bServerDirty=true; }
    void PrepareForDisconnect();
    const FString& CampfireGuestSlot() const { return SlotName; }
    /** UI sends intents on the owned PlayerState channel, never on a world-owned campfire. */
    bool RequestCampfire(class AColdSteelCampfire* Fire,uint8 Action,FName Recipe=NAME_None,int64 Batch=1);
    bool CampfireRequestPending() const { return bCampfirePending; }
    const FString& CampfireMessage() const { return CampfireResultText; }
    bool CampfireResultSucceeded() const { return bCampfireResultSucceeded; }
    UFUNCTION(Server,Reliable) void ServerCampfireRequest(AColdSteelCampfire* Fire,int32 RequestId,uint8 Action,FName Recipe,int64 Batch,int64 InventoryRevision,APawn* RequestPawn);
    UFUNCTION(Client,Reliable) void ClientCampfireResult(int32 RequestId,int64 InventoryRevision,bool Success,const FString& Reason);
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool RequestInventoryAction(EColdSteelInventoryAction Action,const FString& Item=FString(),AActor* Target=nullptr);
    bool RequestInventoryAction(FColdSteelInventoryRequest Request);
    bool RequestArtisanLesson(class AVillageArtisanMerchant* Teacher,uint32 ConversationSession);
    UFUNCTION(Server,Reliable) void ServerBeginConsumableUse(APawn* SourcePawn,FGuid UseId,const FString& Item,FName Definition);
    UFUNCTION(Server,Reliable) void ServerCancelConsumableUse(FGuid UseId);
    bool HasAuthorityConsumableReservation(const APawn* Pawn) const;
    UFUNCTION(Server,Reliable) void ServerRememberGenericLaunch(APawn* SourcePawn,const FString& Instance,uint32 Sequence,int32 Rounds);
    bool IsGenericFirearm(const FColdSteelItem& Item) const;
    double FastestAuthorityFireInterval(const AFPSGAMECharacter* Pawn) const;
    void RecordAuthorityShotRecovery(APawn* Pawn,double Seconds);
    TWeakObjectPtr<APawn> AuthorityShotRecoveryPawn;
    double AuthorityShotRecoveryUntil=0.;
    uint32 RequestGenericMeleeStart(APawn* Pawn,const FString& Instance,uint8 Family,uint8 Meta);
    UFUNCTION(Server,Reliable) void ServerRememberGenericMeleeStart(APawn* SourcePawn,const FString& Instance,uint8 Family,uint8 Meta,uint32 Serial);
    bool RequiresGenericMeleeReceipt(const FColdSteelNetHitReport& Report,const FColdSteelItem* Item) const;
    bool ValidateGenericMeleeReceipt(const FColdSteelNetHitReport& Report,const APawn* Pawn,const FColdSteelItem* Item) const;
    void CommitGenericMeleeReceipt(const FColdSteelNetHitReport& Report,const APawn* Pawn,const FColdSteelItem* Item);
    bool HasGenericMeleeBusy(const APawn* Pawn) const;
    void RequestTorchEmbers(APawn* Pawn,uint32 OrdinarySwingSerial,const FVector& Point,const FVector& Normal);
    UFUNCTION(Server,Unreliable) void ServerTorchEmbers(APawn* Pawn,uint32 Serial,bool bQuick,FVector_NetQuantize10 Point,FVector_NetQuantizeNormal Normal);
    struct FGenericMeleeReceipt
    {
        TWeakObjectPtr<APawn> Pawn;
        FColdSteelItem Item;
        uint32 Serial=0;
        uint8 Family=0,Meta=0;
        bool bTorchSurfaceSent=false;
        double StartedAt=0.,ContactFrom=0.,ContactUntil=0.,BusyUntil=0.,Expires=0.;
        TSet<TWeakObjectPtr<AActor>> Targets;
    };
    TMap<uint32,FGenericMeleeReceipt> GenericMeleeReceipts;
    TWeakObjectPtr<APawn> GenericMeleePawn;
    uint32 GenericMeleeSequence=0,LastGenericMeleeSequence=0;
    double GenericMeleeReadyAt=0.;
    struct FGenericLaunch
    {
        FColdSteelItem Item;
        TWeakObjectPtr<APawn> Pawn;
        uint32 Sequence=0;
        int32 Rounds=1;
        double At=0.,Expires=0.,ReadyAt=0.;
    };
    const FGenericLaunch* FindGenericLaunch(const FColdSteelNetHitReport& Report,const APawn* Pawn) const;
    TMap<uint32,FGenericLaunch> GenericLaunches;
    uint32 LastGenericLaunchSequence=0;
    TWeakObjectPtr<APawn> GenericLaunchPawn;
    double GenericLaunchReadyAt=0.;
    double GenericLaunchTokenAt=0.;
    float GenericLaunchTokens=6.f;
    void AcknowledgeInventoryProfile();
    void SyncMartialCooldowns(const FColdSteelProfile& Profile,bool Immediate);
    UFUNCTION(Server,Reliable) void ServerMartialCooldowns(APawn* SourcePawn,int64 Revision,float Whirlwind,
        float WhirlwindDuration,float Uppercut,float UppercutDuration,double CapturedAt);
    bool ExecuteWorldAction(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason);
    bool RequestTeamTravel(AActor* Entrance,bool bConfirmUnclaimedReward=false);
    /** Runtime region belongs to the connection, not the host's current camera/map. */
    UPROPERTY(Replicated) bool bInDungeonRoom=false;
    UPROPERTY(Replicated) bool bClaimedFinalDungeonTreasure=false;
    FGuid RoomTransferToken,RoomTransferInstance;
    TWeakObjectPtr<APawn> RoomTransferPawn;
    bool bRoomEntryAckSent=false;
    UFUNCTION(Client,Reliable) void ClientBeginRoomEntry(FGuid Token,FGuid Instance,APawn* Pawn);
    UFUNCTION(Server,Reliable) void ServerRoomEntryReady(FGuid Token,FGuid Instance,APawn* Pawn);
    UFUNCTION(Server,Reliable) void ServerCancelRoomEntry(FGuid Token);
    UFUNCTION(Client,Reliable) void ClientFinishRoomEntry(FGuid Token,bool Dungeon,const FString& Reason);
    UFUNCTION(Client,Reliable) void ClientRoomRegionChanged(bool Dungeon);
    UFUNCTION(Client,Reliable) void ClientTeamTravelFinished(FGuid TravelId);
    void TickRoomEntry();
    void FinishTravelBatch(FGuid Id);
    UFUNCTION(Server,Reliable) void ServerTeamTravel(AActor* Entrance,bool bConfirmUnclaimedReward);
    /** Development landmark command; server derives the destination from its world. */
    UFUNCTION(Server,Reliable) void ServerVisitHillsQuarry();
    UFUNCTION(Client,Reliable) void ClientTeamTravelRejected(const FString& Reason);
    UFUNCTION(Client,Reliable) void ClientPrepareTeamTravel(FGuid TravelId);
    UFUNCTION(Server,Reliable) void ServerTeamTravelReady(FGuid TravelId,int32 AcceptedUploadId);
    UFUNCTION(Client,Reliable) void ClientTeamTravelSaveFailed(FGuid TravelId,const FString& Reason);
    void AbortTeamTravel(const FString& Reason);
    void RollbackTeamReturnCompletion();
    void InvalidateTeamTravelReady();
    bool SaveTeamTravelParticipant();
    virtual void CopyProperties(APlayerState* Other) override;
    void TickTeamTravel();
    void TickWorldNetwork(float Delta);
    UPROPERTY(ReplicatedUsing=OnRep_PlantingClock) int64 PlantingUtcTicks=0;
    UFUNCTION() void OnRep_PlantingClock();
    double PlantingClockPublishAt=0.;
    bool ExecuteStation(const FColdSteelInventoryRequest& R,UColdSteelStatusModel* M,FString& Reason);
    bool StationReach(FName Kind,AActor* Target=nullptr) const;
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
    UFUNCTION(Server,Reliable) void ServerOpenWoodworking(APawn* InputPawn,const FString& JobId,AActor* Station,uint32 Sequence);
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
    FString LastDungeonLayoutSentRunId;
    int32 WorldSerial=0,WorldChunk=0,WorldReceiveSerial=0,WorldReceiveTotal=0;
    double WorldSendAt=0,WorldSnapshotAt=0,WorldApplyAt=0;
    bool bWorldHarvestApplied=false;
    bool bTravelFlush=false,bTravelReady=false,bTravelNeedsFreshUpload=false;
    bool bTeamReturnUnclaimedConfirmed=false,bTeamReturnCompletionStaged=false;
    bool bDisconnectPrepared=false;
    bool bWasLocalOwner=false;
    FGuid TeamTravelId;
    TWeakObjectPtr<UWorld> TeamTravelWorld;
    TWeakObjectPtr<APawn> TeamTravelPawn;
    FString TeamDestination,TeamOptions;
    TWeakObjectPtr<AActor> TeamTravelEntrance;
    double TeamTravelStarted=0.;
    bool InventoryRequestPending() const {return bInventoryRequestPending;}
    void RequestQuickCombat(float Duration,float PredictedCost,float PredictedMana=0.f);
    void FinishQuickCombat();
    bool IsQuickCombatExecuting(const APawn* Pawn) const;
    bool RequestSwordUppercutRelease();
    uint32 RequestKukriAttack(const FString& Main,const FString& Offhand,uint8 Stage,bool Dash,const FVector& Direction,uint32 MasterySerial);
    void FinishKukriAttack(uint32 Serial,bool Cancelled);
    bool GetKukriMovement(uint32 Serial,uint8 Kind,FVector& Direction,float& Limit,float& Recovery) const;
    bool IsKukriMovementPending(uint32 Serial) const;
    UFUNCTION(Server,Reliable) void ServerPayGaleSwing(APawn* ActionPawn,const FString& Weapon,uint32 Serial,bool Dash);
    UFUNCTION(Client,Reliable) void ClientGaleSwingCost(double TotalSpent);
    UFUNCTION(Client,Reliable) void ClientGaleCredit(double TotalSpent,double TotalCredit);
    UFUNCTION(Server,Reliable) void ServerBeginRidgeStrike(APawn* ActionPawn,const FString& Weapon,uint32 Serial,uint8 Meta,double ClientStartedAt);
    UFUNCTION(Server,Reliable) void ServerBeginKukriAttack(uint32 Serial,APawn* Pawn,const FString& Main,
        const FString& Offhand,uint8 Stage,bool Dash,FVector_NetQuantizeNormal Direction,uint32 MasterySerial,double ClientStartedAt);
    UFUNCTION(Server,Reliable) void ServerFinishKukriAttack(uint32 Serial,APawn* Pawn,bool Cancelled);
    UFUNCTION(Client,Reliable) void ClientKukriAttackResult(uint32 Serial,APawn* Pawn,bool Accepted,double TotalSpent);
    void FinishSwordUppercut();
    void SettleSwordUppercut();
    bool RequestSwordWhirlwind(bool Zhufeng,const FVector& Direction);
    void FinishSwordWhirlwind();
    void SettleSwordWhirlwind();
    bool IsSwordWhirlwindExecuting(const APawn* Pawn) const;
    bool SwordWhirlwindMove(uint32 MoveSequence,FVector& Direction,float& DistanceLimit) const;
    UFUNCTION(Server,Reliable) void ServerSwordWhirlwind(uint32 Sequence,APawn* Pawn,const FString& Weapon,bool Zhufeng,
        uint32 MoveSequence,FVector_NetQuantizeNormal Direction,bool Finish);
    UFUNCTION(Client,Reliable) void ClientSwordWhirlwindResult(uint32 Sequence,APawn* Pawn,bool Accepted,bool Zhufeng,
        double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt);
    UFUNCTION(Server,Reliable) void ServerSwordUppercut(uint32 Sequence,APawn* Pawn,const FString& Weapon,bool Finish);
    UFUNCTION(Client,Reliable) void ClientSwordUppercutResult(uint32 Sequence,APawn* Pawn,bool Accepted,double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt);
    uint32 RequestShadowStep(const FString& PrimaryWeapon,const FString& SecondaryWeapon,const FVector& Direction);
    bool RequestShadowStepFollowup(uint32 Sequence);
    void FinishShadowStep(uint32 Sequence);
    void SettleShadowStep();
    bool IsShadowStepDashOpen(const APawn* Pawn) const;
    UFUNCTION(Server,Reliable) void ServerShadowStep(uint32 Sequence,APawn* Pawn,const FString& PrimaryWeapon,const FString& SecondaryWeapon,FVector_NetQuantizeNormal Direction,bool Finish);
    UFUNCTION(Server,Reliable) void ServerShadowStepFollowup(uint32 Sequence,APawn* Pawn);
    UFUNCTION(Client,Reliable) void ClientShadowStepResult(uint32 Sequence,APawn* Pawn,bool Accepted,double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt);
    UFUNCTION(Client,Reliable) void ClientShadowStepFollowupWindow(uint32 Sequence,APawn* Pawn,float WindowSeconds);
    UFUNCTION(Client,Reliable) void ClientShadowStepFollowupResult(uint32 Sequence,APawn* Pawn,bool Accepted);
    UFUNCTION(Server,Reliable) void ServerQuickCombat(uint32 Sequence,APawn* Pawn,float Duration,bool Finish,const FString& Equipment);
    UFUNCTION(Client,Reliable) void ClientQuickCombatRejected(uint32 Sequence);
    UFUNCTION(Server,Reliable) void ServerInventoryAction(const FColdSteelInventoryRequest& Request);
    UFUNCTION(Client,Reliable) void ClientInventoryReplyChunk(uint32 Sequence,int32 Index,int32 Total,const TArray<uint8>& Chunk);
    UFUNCTION(Client,Reliable) void ClientInventoryBaseline(const FString& Digest,int64 Souls,int64 Credits,int64 Debits);
    UFUNCTION(Server,Reliable) void ServerWarehouseOpen(class AColdSteelWarehouseChest* Chest,bool Open);
    UFUNCTION(Client,Reliable) void ClientContainerInvalidated(AActor* Target);
    UFUNCTION(Server,Reliable) void ServerCloseContainerSearch(AActor* Target);
    UFUNCTION(NetMulticast,Reliable) void MulticastSharedChestOpened(AActor* Target);

private:
    friend class UFPSConsumableAuditCommandlet;
    friend class URuneSwordAuditCommandlet;
    friend class UKukriNetworkAuditCommandlet;
    friend class UEnhancementEscrowAuditCommandlet;
    friend class AEnhancementEscrowWirePlayerState;
    friend class AEnhancementEscrowWireController;
    friend class AEnhancementEscrowWireGameMode;
    void TickKukriAuthority(float Delta);
    void ClearKukriAttack();
    bool MatchesKukriEquipment() const;
    bool ValidateKukriHit(const FColdSteelNetHitReport& Report,const AFPSGAMECharacter* Pawn,FString& Reason) const;
    void ConfirmKukriHit(const FColdSteelNetHitReport& Report,AFPSGAMECharacter* Pawn,float Applied,bool Killed,bool TrainingEligible);
    FKukriAttackReceipt KukriAttack;
    uint32 KukriSequence=0,KukriReceivedSequence=0,KukriReceiptSequence=0;
    double KukriReadyAt=0.,KukriChainUntil=0.,KukriDashReadyUntil=-1.;
    uint8 KukriNextStage=0;
    float KukriSprintSeconds=0.f;
    FString KukriChainKey,KukriSprintKey;
    TWeakObjectPtr<APawn> KukriSprintPawn;
    bool bContainerNeedsRefresh=false;
    friend class UColdSteelAcquisitionAuditCommandlet;
    friend class USkillNetworkAuditCommandlet;
    friend class UMonsterNetworkHitAuditCommandlet;
    friend class UShotgunAttachmentAuditCommandlet;
    friend class AShotgunWireAuditController;
    friend class AShotgunWireAuditGameMode;
    friend class UWarhammerNetworkAuditCommandlet;
    friend class ASkillWireAuditController;
    friend class ASkillWireAuditGameMode;
    friend struct FUnknownJoinAuditAccess;
    void TickSwordUppercut();
    void TickShadowStep();
    bool ValidateShadowStepHit(const FColdSteelNetHitReport& Report,const AFPSGAMECharacter* Pawn,FString& Reason) const;
    void RecordShadowStepTarget(const FColdSteelNetHitReport& Report);
    void ConfirmShadowStepHit(const FColdSteelNetHitReport& Report,AFPSGAMECharacter* Shooter,float Applied,bool Killed);
    void TickSwordWhirlwind(float Delta);
    bool ValidateSwordWhirlwindHit(const FColdSteelNetHitReport& Report,const AFPSGAMECharacter* Pawn,FString& Reason) const;
    void ConfirmSwordWhirlwindHit(AFPSGAMECharacter* Pawn,AActor* Target,float Applied,bool Killed);
    uint32 WhirlwindSequence=0,WhirlwindReceivedSequence=0,WhirlwindActiveSequence=0,WhirlwindReceiptSequence=0;
    uint32 WhirlwindMoveSequence=0;
    TWeakObjectPtr<APawn> WhirlwindPawn;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> WhirlwindRewardModel;
    FString WhirlwindWeapon,WhirlwindSprintWeapon;
    FWhirlwindCast ServerWhirlwindCast;
    FVector WhirlwindMoveDirection=FVector::ForwardVector;
    double WhirlwindStartedAt=0.,WhirlwindUntil=0.,WhirlwindDashReadyUntil=-1.;
    float WhirlwindReadySeconds=0.f,WhirlwindMoveSeconds=0.f,WhirlwindMoveSpeed=0.f,WhirlwindSprintSeconds=0.f;
    float WhirlwindRuneVulnerability=0.f,WhirlwindRuneSeconds=0.f,WhirlwindCooldownReduction=0.f;
    bool bWhirlwindZhufeng=false,bWhirlwindCooldownReduced=false;
    int32 WhirlwindHits=0,WhirlwindKills=0;
    TSet<TWeakObjectPtr<AActor>> WhirlwindTargets;
    uint32 UppercutSequence=0,UppercutReceivedSequence=0,UppercutActiveSequence=0,UppercutReceiptSequence=0;
    TWeakObjectPtr<APawn> UppercutPawn;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> UppercutRewardModel;
    FString UppercutWeapon;
    double UppercutUntil=0.;
    bool bUppercutContact=false;
    int32 UppercutHits=0,UppercutKills=0;
    uint32 ShadowStepSequence=0,ShadowStepReceivedSequence=0,ShadowStepActiveSequence=0,ShadowStepReceiptSequence=0;
    TWeakObjectPtr<APawn> ShadowStepPawn;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> ShadowStepRewardModel;
    FString ShadowStepPrimaryWeapon,ShadowStepSecondaryWeapon;
    FShadowStepCast ServerShadowStepCast;
    bool bShadowStepDual=false,bShadowStepStage1Hit=false,bShadowStepFollowupStarted=false;
    double ShadowStepUntil=0.,ShadowStepDashUntil=0.,ShadowStepFollowupUntil=0.;
    int32 ShadowStepKills=0;
    TSet<TWeakObjectPtr<AActor>> ShadowStepTargets[2];
    TSet<TWeakObjectPtr<AActor>> ShadowStepFollowTargets[2];
    void TickContainerRefresh();
    uint32 QuickCombatSequence=0,QuickCombatServerSequence=0,QuickCombatRequestSequence=0;
    double QuickCombatUntil=0.;
    TMap<uint32,FVector2f> QuickCombatPredictedCosts;
    TWeakObjectPtr<APawn> QuickCombatPawn;
    FString QuickCombatEquipment;
    FString QuickCombatEquipmentKey() const;
    TSet<TWeakObjectPtr<AActor>> QuickCombatTargets;
    uint32 LastTorchQuickSurface=0;
    uint32 LastRuneCooldownAttackSerial=0;
    TWeakObjectPtr<APawn> RuneCooldownPawn;
    uint32 LastMasteryAttackSerial=0;
    uint32 ResolveKukriRuneAttackSerial(const FColdSteelNetHitReport& Report,uint32 SnapshotSerial);
    TWeakObjectPtr<APawn> KukriRunePawn;
    uint32 KukriRuneSequences[5]={},KukriRuneAttackIds[5]={};
    int32 MeleeMasteryHits=0;
    TWeakObjectPtr<APawn> MeleeMasteryPawn;
    FString MeleeMasteryWeapon;
    TSet<TWeakObjectPtr<AActor>> MeleeMasteryTargets;
    int64 ConfirmedSouls=-1,ConfirmedSoulCredits=-1,ConfirmedSoulDebits=-1;
    bool bInventoryRequestPending=false;
    bool bInventoryWaitingUpload=false;
    UPROPERTY() FColdSteelInventoryRequest PendingInventoryRequest;
    void DispatchInventoryAfterUpload();
    TArray<uint8> AcknowledgedInventoryBaseline;
    static TArray<uint8> InventoryBaseline(const FColdSteelProfile& Profile);
    void SendInventoryBaseline();
    bool ExecuteBowShot(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason);
    void TickBowDrawAuthority();
    double LastBowShotAt=-100.;
    TWeakObjectPtr<APawn> BowDrawPawn;
    FString BowDrawWeapon;
    double BowDrawStartedAt=-1.;
    float BowDrawSeconds=0.f;
    FGuid BowDrawId;
    TWeakObjectPtr<APawn> BowPerfectPawn;
    FString BowPerfectWeapon;
    void RefreshBowPerfectOwner();
    bool bLastBowShotPiercing=false;
    /** Authority-only; the exact release receipt reconciles the owner's prediction. */
    bool bBowPerfectSpeedBonus=false;
    TWeakObjectPtr<APawn> InventoryRequestPawn;
    uint32 InventoryRequestSequence=0,LastInventoryRequestSequence=0,ReplySequence=0;
    TArray<uint8> InventoryReplyOutgoing,InventoryReplyIncoming;
    int32 InventoryReplyChunk=0,InventoryReplyTotal=0;
    double LastInventoryReplyAt=0.;
    void TickInventoryReply();
    void ProcessInventoryAction(const FColdSteelInventoryRequest& Request);
    TWeakObjectPtr<APawn> ConsumablePawn;
    FGuid ConsumableUseId;
    FName ConsumableDefinition;
    FString ConsumableItem;
    double ConsumableContactAt=0.;
    double ConsumableExpiresAt=0.;
    FGuid LastConsumableBeginId;
    bool CanAuthorityBeginConsumable(const APawn* Pawn) const;
    FTimerHandle ConsumableContactTimer;
    void QueueInventoryReply(const FColdSteelInventoryRequest& Request,bool Success,const FString& Reason,
        const FColdSteelProfile& Before,const FColdSteelProfile& After);
    uint32 Super90LocalSequence=0,Super90ProcessedSequence=0,Super90Revision=0,Super90AppliedRevision=0;
    uint32 PendingSuper90Revision=0,IncomingSuper90Revision=0;
    TArray<FSuper90PredictedShot> Super90PredictedShots;
    TMap<FString,uint32> M870PredictedPumpInterrupts;
    TSet<FString> Super90ServerWeapons;
    TArray<int64> Super90PouchDelta={0,0,0},Super90AppliedPouchDelta={0,0,0};
    TMap<uint32,TArray<int64>> Super90PouchHistory;
    FSuper90ServerReload Super90Reload;
    bool bSuper90ReloadPending=false,bSuper90SoftCancelSent=false;
    double Super90LastFireTime=-100.,Super90NextFireTime=-100.;
    uint32 M870AuthorityShotSequence=0;
    FString M870AuthorityShotWeapon;
    TWeakObjectPtr<APawn> M870AuthorityShotPawn;
    double M870AuthorityShotTime=-100.,M870AuthorityPumpClosedTime=-100.;
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
    uint32 PistolControlSequence=0,PistolProcessedControl=0,PistolProcessedShot=0;
    uint32 PistolReceiptRevision=0,PistolAppliedReceipt=0,PistolAmmoRevision=0,PistolAppliedAmmoRevision=0;
    int64 PistolAppliedInventoryRevision=-1;
    uint32 PendingPistolAmmoRevision=0,IncomingPistolAmmoRevision=0,PendingPistolIntent=0,IncomingPistolIntent=0;
    TArray<FString> PistolAmmoIds;
    TMap<FString,int64> PistolPouchDelta,PistolAppliedPouchDelta;
    TMap<uint32,TMap<FString,int64>> PistolPouchHistory;
    TMap<FString,FPistolServerReload> PistolReloads;
    TMap<FString,uint32> PistolPendingReloads;
    TSet<FString> PistolCancelPending;
    TArray<FPistolPredictedShot> PistolPredictedShots;
    TSet<FString> PistolServerWeapons;
    TWeakObjectPtr<APawn> PistolClientPawn;
    UPROPERTY() FPistolNetAmmoState PendingPistolState;
    bool bPendingPistolState=false,bPistolAmmoInitialized=false,bApplyingPistolReceipt=false;
    void TickPistolAuthority();
    void TickPistolRecovery();
    void SendPistolAmmo(bool Cowboy=false);
    void EnsurePistolAmmoIds();
    bool ConsumePistolAmmo(const FColdSteelItem& Item,int32 Rounds,FString& Reason);
    void FinishPistolReload(FPistolServerReload& Reload,bool Rejected=false);
    void RecordPistolPouchChange(const TMap<FString,int64>& Before);
    bool RebasePistolUpload(FColdSteelProfile& Incoming,const FColdSteelProfile& Previous,bool KeepServerPouch) const;
    void PreservePistolClientAmmo(FColdSteelProfile& Incoming) const;
    void RefreshPistolAmmoCounters(class AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,bool AmmoChanged=false);
    void StopPistolAuthority();
    bool bCampfirePending=false,bCampfireWaitingUpload=false;
    bool bCampfireResultSucceeded=false;
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
    bool ApplyGuestProfile(const FColdSteelProfile& Profile,bool bFromNetwork=false);
    /** Host admission check for an uploaded profile; repairs bounded fields and rejects malformed data. */
    bool SanitizeGuestProfile(FColdSteelProfile& Profile,FString& OutReason) const;
    UFUNCTION(Client,Reliable) void ClientProfileSyncRejected(const FString& Reason);
    void ApplyShadowToServerPawn();
    void TickUpload(float DeltaSeconds);
    void TickShadowMirror(float DeltaSeconds);
    void TickPublicInfo(float DeltaSeconds);
    bool ValidateHitReport(const FColdSteelNetHitReport& Report, class AFPSGAMECharacter* Shooter, FString& OutReason,
        const struct FColdSteelItem*& OutDeclaredItem);
    /** Server-side magazine ledger. Client hit reports never grant free rounds. */
    bool ConsumeServerAmmo(const FColdSteelItem* Item,int32 Rounds,double Now,FString& OutReason);
    struct FServerGunLedger
    {
        int32 Magazine=-1;
        double ReloadReadyAt=0.,LastClientTime=-1.,LastServerAt=-1.;
        uint32 LastSequence=0;
        TMap<uint32,float> CriticalRolls;
    };
    TMap<FString,FServerGunLedger> ServerGunLedgers;
    // Short-lived launch context for M24 bullets still in flight after a swap.
    struct FM24Launch
    {
        FColdSteelItem Item;
        TWeakObjectPtr<APawn> Pawn;
        FVector Eye,ViewForward;
        float TraceRange=0.f,EffectiveRange=0.f;
        double At=0.,Expires=0.,Interval=0.;
        int32 Rounds=1,MaxTargets=1;
        TSet<TWeakObjectPtr<AActor>> Targets;
    };
    TMap<uint32,FM24Launch> M24Launches;
    uint32 LastM24LaunchSequence=0;
    const FM24Launch* FindM24Launch(const FColdSteelNetHitReport& Report,const APawn* Shooter) const;
    struct FRegisteredPistolShot
    {
        FColdSteelItem Item;
        TWeakObjectPtr<APawn> Pawn;
        double At=0.;
        int32 Rounds=1;
    };
    TMap<uint32,FRegisteredPistolShot> RegisteredPistolShots;
    TWeakObjectPtr<APawn> GaleSwingPawn;
    uint32 LastGaleSwingSerial=0;
    int32 ServerComboStage=0,ValidatedComboStage=0;
    double ServerComboAt=-100.,ServerComboSwingAt=-100.;
    FString ServerComboWeapon;
    // Begin and hit reports share this actor channel, so a miss still advances
    // the installed blade's combo and one rectangle may hit several distinct targets.
    struct FRidgeStrike
    {
        TWeakObjectPtr<APawn> Pawn;
        FString Weapon;
        uint32 Serial=0;
        uint8 Meta=0,NextStage=1;
        double StartedAt=-1.,NextSwingAt=0.,ChainUntil=0.,HitFrom=0.,HitUntil=0.;
        float Length=0.f;
        FVector DashForward=FVector::ForwardVector;
        TSet<TWeakObjectPtr<AActor>> Targets;
    } RidgeStrike;
    /** 服务端权威伤害：按武器族从影子档案同参复算，客户端 ClaimedDamage 只作对账参考。 */
    bool PrepareHitReport(const FColdSteelNetHitReport& Report,FColdSteelPreparedHit& Prepared);
    void SettleHitReport(FColdSteelPreparedHit& Prepared,FKukriPairedHeavyHit* PairedHeavy=nullptr);
    static FColdSteelNetHitReport MakeHitReport(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot);
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
    FIceArmorCast PendingIceArmorStats;
    FLightningHasteCast PendingLightningHasteStats;
    FLightningCast PendingLightningStats;
    FFireMagicCast PendingFireMagicStats;
    FVector PendingMeteorPoint=FVector::ZeroVector,PendingMeteorNormal=FVector::UpVector;
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
    // Inventory-only receipts do not acknowledge cosmetics. Keep the selection
    // from the last complete upload separate from the rebased inventory blobs.
    FName UploadedHeadId,UploadedHairId,PendingUploadHeadId,PendingUploadHairId;
    bool bHasUploadedAppearance=false;
    // Freeze the customization identity with each upload and mirror. Sending
    // the last chunk is not acknowledgement that a paced mirror contains it.
    uint32 LocalGunsmithSequence=0,ProcessedGunsmithSequence=0,UploadedGunsmithSequence=0;
    uint32 PendingUploadGunsmithSequence=0,IncomingGunsmithSequence=0;
    uint32 PendingMirrorGunsmithSequence=0,ReceivingMirrorGunsmithSequence=0;
    bool bGunsmithReplyPending=false;
    TMap<FString,TSet<FString>> PendingGunsmithInstances;
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
