#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/WhirlwindTypes.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/IceSpikeTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/ElectricMagicTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/WeaponDamageFalloff.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/HitResult.h"
#include "CollisionQueryParams.h"
#include "Engine/ActorInstanceHandle.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameState.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Net/UnrealNetwork.h"

namespace
{
    // 与 UGameplayStatics::SaveGameToSlot 相同的序列化口径：FObjectAndNameAsStringProxyArchive + ArNoDelta。
    void SaveToBlob(USaveGame* Save, TArray<uint8>& OutBlob)
    {
        OutBlob.Reset();
        FMemoryWriter Writer(OutBlob);
        FObjectAndNameAsStringProxyArchive Ar(Writer, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
    }

    UColdSteelProfileSave* BlobToSave(const TArray<uint8>& Blob)
    {
        UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
            UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
        FMemoryReader Reader(Blob);
        FObjectAndNameAsStringProxyArchive Ar(Reader, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
        return Save;
    }

    // 服务端施法执行器的技能表键：新增技能在这里注册后按分支实现。
    const FName FireballSkillId(TEXT("fireball"));
}

AColdSteelPlayerState::AColdSteelPlayerState()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    NetUpdateFrequency = 10.f;
}

void AColdSteelPlayerState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelPlayerState, PublicInfo);
    DOREPLIFETIME_CONDITION(AColdSteelPlayerState, MirrorBlob, COND_OwnerOnly);
}

void AColdSteelPlayerState::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Standalone) return;

    if (GetLocalRole() == ROLE_Authority)
    {
        // 影子档案要挂在服务端 pawn 上：spawn/重生后重试挂载（AttachPawn+ApplyToPawn 轻量幂等）。
        APlayerController* PC = Cast<APlayerController>(GetOwner());
        AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
        if (ShadowModel && Pawn && ShadowPawn.Get() != Pawn)
        {
            ApplyShadowToServerPawn();
        }
        // 影子档案随服务端时钟走：冷却衰减/法力回复/增益结算不再等客户端 30s 兜底上行。
        if (ShadowModel && Pawn && ShadowPawn.Get() == Pawn)
            ShadowModel->TickRuntime(DeltaSeconds, Pawn);
        // 施法看门狗：凝聚球在外部消亡（悬停超时/世界清理）而 Phase 未落地——回收占用并退款。
        if (PendingCastSkill == FireballSkillId && !PendingCastOrb.IsValid())
        {
            if (ShadowModel) ShadowModel->RefundUnreleasedCast(PendingCastPaidMana, TEXT("fireball"));
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
        }
        TickShadowMirror(DeltaSeconds);
        TickPublicInfo(DeltaSeconds);
        if (bServerDirty)
        {
            ServerSaveTimer -= DeltaSeconds;
            if (ServerSaveTimer <= 0.f)
            {
                ServerSaveTimer = 20.f;
                bServerDirty = false;
                SaveShadowToHostDisk();
            }
        }
    }
    else
    {
        TickUpload(DeltaSeconds);
        TickClientDiagnostics(DeltaSeconds);
    }
}

// ============================================================================
// 客户端测试钩（移植自 UColdSteelNetChannelComponent，冒烟断言依赖）
// ============================================================================

void AColdSteelPlayerState::TickClientDiagnostics(float DeltaSeconds)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !PC->IsLocalController()) return;

    // 惰性读命令行（ctor 时 FCommandLine 可能还没就绪则下一 tick 再读）。
    static const bool bWantAutoWalk = FParse::Param(FCommandLine::Get(), TEXT("MPClientWalk"));
    static const bool bWantSyntheticShot = FParse::Param(FCommandLine::Get(), TEXT("MPClientShot"));
    if (bWantSyntheticShot && SyntheticShotCountdown < 0.f && SyntheticShotAttempts == 0)
        SyntheticShotCountdown = 12.f;

    // M4 取证：客户端自动驾驶（真实输入路径，每 4s 切换冲刺/走路）。
    if (bWantAutoWalk)
    {
        AutoWalkPhase += DeltaSeconds;
        if (AFPSGAMECharacter* LocalChar = Cast<AFPSGAMECharacter>(PC->GetPawn()))
        {
            LocalChar->MPSetAutoInput(true, FMath::Fmod(AutoWalkPhase, 8.f) < 4.f);
            ClientPosProbe += DeltaSeconds;
            if (ClientPosProbe >= 3.f)
            {
                ClientPosProbe = 0.f;
                const FVector L = LocalChar->GetActorLocation();
                UE_LOG(LogTemp, Warning, TEXT("MPTEST client pos: x=%.0f y=%.0f vel=%.0f"),
                    L.X, L.Y, LocalChar->GetVelocity().Size());
            }
        }
    }

    // M3 测试钩：合成命中（找一只非玩家 pawn 当靶，验证客户端→服务端战斗链）。
    if (SyntheticShotCountdown >= 0.f)
    {
        SyntheticShotCountdown -= DeltaSeconds;
        if (SyntheticShotCountdown <= 0.f)
        {
            SyntheticShotCountdown = 3.f;
            if (++SyntheticShotAttempts > 20)
            {
                SyntheticShotCountdown = -1.f;
            }
            else if (AFPSGAMECharacter* LocalChar = Cast<AFPSGAMECharacter>(PC->GetPawn()))
            {
                // 新校验链要求武器定义匹配影子装备、弹道过 rewind——上报按真实口径填满。
                APawn* TargetPawn = nullptr;
                float BestDist = 6000.f;
                for (TActorIterator<APawn> It(GetWorld()); It; ++It)
                {
                    APawn* Candidate = *It;
                    if (Candidate && Candidate != LocalChar && !Candidate->IsPlayerControlled())
                    {
                        const float D = FVector::Dist(Candidate->GetActorLocation(), LocalChar->GetActorLocation());
                        if (D < BestDist) { BestDist = D; TargetPawn = Candidate; }
                    }
                }
                if (TargetPawn)
                {
                    FColdSteelNetHitReport Report;
                    Report.Target = TargetPawn;
                    const FVector Eye = LocalChar->GetActorLocation() + FVector(0.f, 0.f, 60.f);
                    Report.AimOrigin = Eye;
                    Report.ImpactPoint = TargetPawn->GetActorLocation();
                    Report.HitNormal = FVector::UpVector;
                    Report.ClaimedDamage = 25.f;
                    Report.Direction = (TargetPawn->GetActorLocation() - Eye).GetSafeNormal();
                    if (const UGameInstance* GI = GetGameInstance())
                        if (const UColdSteelStatusModel* Model = GI->GetSubsystem<UColdSteelStatusModel>())
                            if (const FColdSteelItem* Eq = Model->Equipped())
                                Report.ItemDefinition = Eq->Definition;
                    if (const AGameStateBase* GS = GetWorld()->GetGameState())
                        Report.ClientFireTime = GS->GetServerWorldTimeSeconds();
                    ServerReportHit(Report);
                    UE_LOG(LogTemp, Warning, TEXT("MPTEST synthetic hit sent -> %s d=%.0f"), *GetNameSafe(TargetPawn), BestDist);
                    SyntheticShotCountdown = -1.f;
                }
            }
        }
    }
}

void AColdSteelPlayerState::OnRep_PublicInfo()
{
    UE_LOG(LogTemp, Verbose, TEXT("MPTEST ps public: %s weapon=%s lv=%d kills=%d"),
        *GetPlayerName(), *PublicInfo.ActiveWeaponDefinition, PublicInfo.Level, PublicInfo.Kills);
}

// ============================================================================
// 服务端：客人初始化 / 影子档案
// ============================================================================

void AColdSteelPlayerState::InitializeGuest(const FString& InSlotName)
{
    if (bGuestInitialized) return;
    bGuestInitialized = true;
    SlotName = InSlotName;
    // 客人档案的载回兜底：上传因故没到，也能用主机磁盘里的旧档开局（单机档案文件名制）。
    if (USaveGame* Loaded = UGameplayStatics::LoadGameFromSlot(SlotName, 0))
    {
        if (UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(Loaded))
        {
            UE_LOG(LogTemp, Warning, TEXT("MPTEST guest slot found on host disk: %s"), *SlotName);
            ApplyGuestProfile(Save->Profile);
        }
    }
}

void AColdSteelPlayerState::ApplyGuestProfile(const FColdSteelProfile& GuestProfile)
{
    UGameInstance* GI = GetGameInstance();
    UColdSteelStatusModel* HostModel = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!HostModel) return;

    if (!ShadowModel)
    {
        ShadowModel = HostModel->CreateShadowModel(GuestProfile);
        ServerPointsBaseline = GuestProfile.Points; // 差分基线对齐首个采纳值
        UE_LOG(LogTemp, Warning, TEXT("MPTEST shadow profile created: %s items=%d hp=%.0f"),
            *SlotName, GuestProfile.Items.Num(), GuestProfile.Health);
    }
    else
    {
        // 双写收口：库存/装备客户端权威；修行字段两边都可能合法增长
        // （服务端击杀/训练授予 vs 客户端装填经验等本地结算）——取单调 max 合并，
        // 任一侧的增量都不会被对方旧快照回滚。
        const FColdSteelProfile Prev = ShadowModel->Snapshot();
        FColdSteelProfile Adopted = GuestProfile;
        // Ongoing survival is server-owned; inventory uploads must not refill or rewind it.
        Adopted.Survival=Prev.Survival;
        if(const auto* Character=Cast<AFPSGAMECharacter>(GetPawn()))
            if(const auto* Survival=Character->FindComponentByClass<UFPSSurvivalComponent>())Adopted.Survival=Survival->GetState();
        Adopted.Level      = FMath::Max(Adopted.Level, Prev.Level);
        Adopted.Experience = FMath::Max(Adopted.Experience, Prev.Experience);
        Adopted.Kills      = FMath::Max(Adopted.Kills, Prev.Kills);
        // Points 有双向合法写：服务端升级授予(+)与客户端属性花费(-)。
        // 基线差分：只把"自上次采纳以来服务端授予的增量"加回客户端申报值——
        // 既不丢服务端授予，也不回滚客户端花费（纯 max 会把花费回滚成免费加点）。
        const int32 ServerGranted = FMath::Max(0, Prev.Points - ServerPointsBaseline);
        Adopted.Points = FMath::Max(0, Adopted.Points + ServerGranted);
        ServerPointsBaseline = Adopted.Points;
        for (const auto& Pair : Prev.Skills)
        {
            FColdSteelSkillProgress& S = Adopted.Skills.FindOrAdd(Pair.Key);
            S.Level = FMath::Max(S.Level, Pair.Value.Level);
            S.Experience = FMath::Max(S.Experience, Pair.Value.Experience);
        }
        ShadowModel->AdoptNetMirror(Adopted);
    }
    ApplyShadowToServerPawn();
    bServerDirty = true;
    ServerSaveTimer = 20.f;
}

void AColdSteelPlayerState::ApplyShadowToServerPawn()
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Character = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!Character || !ShadowModel) return;
    Character->NetShadowProfile = ShadowModel;
    // 影子档绑定服务端 pawn：TickRuntime（冷却/回复）据此承认该 pawn，
    // ApplyToPawn 内部幂等（装备比对不重复换装）。
    ShadowModel->AttachPawn(Character);
    Character->ApplyColdSteelProfile(ShadowModel);
    ShadowPawn = Character;
    UE_LOG(LogTemp, Log, TEXT("MPTEST shadow applied to server pawn: %s"), *GetNameSafe(Character));
}

void AColdSteelPlayerState::SaveShadowToHostDisk()
{
    if (!ShadowModel || SlotName.IsEmpty()) return;
    UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
    Save->Profile = ShadowModel->Snapshot();
    if (UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
    {
        UE_LOG(LogTemp, Warning, TEXT("MPTEST guest profile saved to host disk: %s items=%d hp=%.0f"),
            *SlotName, Save->Profile.Items.Num(), Save->Profile.Health);
    }
}

void AColdSteelPlayerState::TickShadowMirror(float DeltaSeconds)
{
    if (!ShadowModel) return;
    ShadowMirrorTimer += DeltaSeconds;
    if (ShadowMirrorTimer < 3.f) return;
    ShadowMirrorTimer = 0.f;
    UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
    Save->Profile = ShadowModel->Snapshot();
    TArray<uint8> Blob;
    SaveToBlob(Save, Blob);
    // 服务端没写过影子（与客人上行一致）或镜像没变 → 不重复下发。
    if (Blob == LastAppliedBlob || Blob == LastMirrorBlob) return;
    LastMirrorBlob = Blob;
    MirrorBlob = Blob;
}

void AColdSteelPlayerState::TickPublicInfo(float DeltaSeconds)
{
    if (!ShadowModel) return;
    // 展示字段（武器/等级/击杀）1Hz 足够——原来每 tick 全量 Snapshot()，
    // ~84KB 深拷贝×帧率×远端玩家数纯属浪费。
    PublicInfoTimer += DeltaSeconds;
    if (PublicInfoTimer < 1.f) return;
    PublicInfoTimer = 0.f;
    const FColdSteelItem* Eq = ShadowModel->Equipped();
    PublicInfo.ActiveWeaponDefinition = Eq ? Eq->Definition : TEXT("");
    const FColdSteelProfile P = ShadowModel->Snapshot();
    PublicInfo.Level = P.Level;
    PublicInfo.Kills = P.Kills;
}

// ============================================================================
// 客户端：档案快照分块上行（从 UColdSteelNetChannelComponent 移植，口径不变）
// ============================================================================

/** 结构判脏归一：生命体征/冷却/游戏时钟等持续漂移字段置零后再比对——
 *  否则 Snapshot 每 2s 都变，字节去重形同虚设（84KB 全量事实上仍在心跳）。 */
static void NormalizeProfileForCompare(FColdSteelProfile& P)
{
    P.Health = P.Mana = P.Stamina = P.StaminaRecoveryDelay = 0.f;
    P.bSprintExhausted = false;
    P.FireballCooldown = P.FireballCooldownDuration = 0.f;
    P.IceSpikeCooldown = P.IceSpikeCooldownDuration = 0.f;
    P.LightningCooldown = P.LightningCooldownDuration = 0.f;
    P.HolyLightCooldown = P.HolyLightCooldownDuration = 0.f;
    P.WhirlwindCooldown = P.WhirlwindCooldownDuration = 0.f;
    P.SwordUppercutCooldown = P.SwordUppercutCooldownDuration = 0.f;
    P.QuickCombatCooldown = P.QuickCombatCooldownDuration = 0.f;
    P.MeteorCooldown = P.MeteorCooldownDuration = 0.f;
    P.FlameArmorCooldown = P.FlameArmorCooldownDuration = 0.f;
    P.IceWallCooldown = P.IceWallCooldownDuration = 0.f;
    P.IceWallReservedMana = 0.f;
    P.TreeGrowthDay = 0.0;
    P.Infection = FInfectionState();
    P.DungeonRun = FDungeonRunState();
    // 弹药经济随每次开火/装填漂移（SyncRuntime 把 MagazineAmmo 回写进 item），
    // 归一后交 30s 兜底上行——否则持续开火期间每 2s 一次"结构"全量。
    for (auto& I : P.Items) { I.Magazine = I.Reserve = I.VirtualMagazineAmmo = 0; }
    P.AmmoPouch.Empty();
}

void AColdSteelPlayerState::TickUpload(float DeltaSeconds)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !PC->IsLocalController()) return;

    // 调试豁免：双进程回归时 -MPNoHeartbeat 只传首包不重传。
    static const bool bNoHeartbeat = FParse::Param(FCommandLine::Get(), TEXT("MPNoHeartbeat"));
    if (bNoHeartbeat && bHasLastSent) { HeartbeatTimer = 60.f; }

    HeartbeatTimer -= DeltaSeconds;
    if (HeartbeatTimer <= 0.f)
    {
        HeartbeatTimer = 2.f;
        const UGameInstance* GI = GetGameInstance();
        if (const UColdSteelStatusModel* Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr)
        {
            if (!ScratchSave)
            {
                ScratchSave = Cast<UColdSteelProfileSave>(
                    UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
            }
            ScratchSave->Profile = Model->Snapshot();
            TArray<uint8> Blob;
            SaveToBlob(ScratchSave, Blob);
            FColdSteelProfile NormProfile = ScratchSave->Profile;
            NormalizeProfileForCompare(NormProfile);
            ScratchSave->Profile = NormProfile;
            TArray<uint8> NormBlob;
            SaveToBlob(ScratchSave, NormBlob);
            ScratchSave->Profile = Model->Snapshot(); // 复位供别处复用
            const double Now = GetWorld()->GetTimeSeconds();
            // 两级判脏：结构字段变了立刻上行；结构没变但超 30s → 兜底把漂移的生命体征带上去。
            const bool bStructural = !bHasLastSent
                || NormBlob != (PendingUpload.Num() > 0 ? PendingNormBlob : LastSentNormBlob);
            const bool bVitalFlush = bHasLastSent && (Now - LastUploadAt >= VitalFlushInterval)
                && Blob != LastSentBlob;
            if ((bStructural || bVitalFlush) && PendingUpload.Num() == 0)
            {
                PendingUpload = MoveTemp(Blob);
                PendingNormBlob = MoveTemp(NormBlob);
                PendingUploadId = ++UploadCounter;
                NextChunkIndex = 0;
                PendingTotalChunks = FMath::Max(1, FMath::DivideAndRoundUp(PendingUpload.Num(), ProfileChunkSize));
                UE_LOG(LogTemp, Warning, TEXT("MPTEST profile upload started: %d bytes / %d chunks (%s)"),
                    PendingUpload.Num(), PendingTotalChunks, bStructural ? TEXT("structural") : TEXT("vital-flush"));
            }
        }
    }
    // 限速分片上行：每 tick ≤2 片（1KB），避免灌爆 reliable 窗口。
    if (PendingUpload.Num() > 0)
    {
        int32 SentThisTick = 0;
        while (NextChunkIndex < PendingTotalChunks && SentThisTick < 2)
        {
            const int32 Start = NextChunkIndex * ProfileChunkSize;
            const int32 Count = FMath::Min(ProfileChunkSize, PendingUpload.Num() - Start);
            TArray<uint8> Chunk;
            Chunk.Append(PendingUpload.GetData() + Start, Count);
            ServerSubmitProfileChunk(PendingUploadId, NextChunkIndex, PendingTotalChunks, Chunk);
            ++NextChunkIndex;
            ++SentThisTick;
        }
        if (NextChunkIndex >= PendingTotalChunks)
        {
            LastSentBlob = MoveTemp(PendingUpload);
            LastSentNormBlob = MoveTemp(PendingNormBlob);
            bHasLastSent = true;
            LastUploadAt = GetWorld()->GetTimeSeconds();
            PendingUpload.Reset();
        }
    }
}

void AColdSteelPlayerState::OnRep_MirrorBlob()
{
    // 仅拥有者收到：服务端权威档案回写（下行通道——原组件里预留未实现的回程）。
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !PC->IsLocalController()) return;
    UGameInstance* GI = GetGameInstance();
    UColdSteelStatusModel* Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    UColdSteelProfileSave* Save = Model && MirrorBlob.Num() > 0 ? BlobToSave(MirrorBlob) : nullptr;
    if (!Model || !Save) return;

    // 冲突消解：本机在上次上行后未改 → 全量镜像；有本地变更 → 只并入服务端口径的修行字段。
    bool bLocalClean = false;
    if (bHasLastSent)
    {
        if (!ScratchSave)
        {
            ScratchSave = Cast<UColdSteelProfileSave>(
                UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
        }
        ScratchSave->Profile = Model->Snapshot();
        TArray<uint8> CurrentBlob;
        SaveToBlob(ScratchSave, CurrentBlob);
        bLocalClean = (CurrentBlob == LastSentBlob);
    }
    if (bLocalClean)
    {
        Model->AdoptNetMirror(Save->Profile);
    }
    else
    {
        FColdSteelProfile Merged = Model->Snapshot();
        Merged.Survival=Save->Profile.Survival;
        Merged.Level = Save->Profile.Level;
        Merged.Experience = Save->Profile.Experience;
        Merged.Points = Save->Profile.Points;
        Merged.Kills = Save->Profile.Kills;
        Merged.Skills = Save->Profile.Skills;
        Model->AdoptNetMirror(Merged);
    }
    UE_LOG(LogTemp, Warning, TEXT("MPTEST mirror applied: %dB lv=%d"), MirrorBlob.Num(), Save->Profile.Level);
}

void AColdSteelPlayerState::ServerSubmitProfileChunk_Implementation(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk)
{
    if (GetLocalRole() != ROLE_Authority || TotalChunks <= 0 || TotalChunks > 512 ||
        ChunkIndex < 0 || ChunkIndex >= TotalChunks || Chunk.Num() <= 0 || Chunk.Num() > ProfileChunkSize)
    {
        return;
    }
    if (UploadId != IncomingUploadId)
    {
        IncomingUploadId = UploadId;
        IncomingBlob.Reset();
        IncomingReceived = 0;
        IncomingTotal = TotalChunks;
    }
    // reliable 同 actor 通道保序：按到达顺序尾接即可，偏移不符说明丢包/重放，丢弃该包。
    if (ChunkIndex * ProfileChunkSize != IncomingBlob.Num())
    {
        return;
    }
    IncomingBlob.Append(Chunk);
    ++IncomingReceived;
    if (IncomingReceived >= IncomingTotal)
    {
        TArray<uint8> Completed = MoveTemp(IncomingBlob);
        IncomingUploadId = INDEX_NONE;
        IncomingReceived = 0;
        IncomingTotal = 0;
        if (Completed == LastAppliedBlob) return;
        LastAppliedBlob = Completed;
        if (UColdSteelProfileSave* Save = BlobToSave(Completed))
        {
            UE_LOG(LogTemp, Warning, TEXT("MPTEST profile upload complete: %d bytes"), Completed.Num());
            ApplyGuestProfile(Save->Profile);
        }
    }
}

// ============================================================================
// 命中权威：服务端校验 + 影子档案复算（替代原"客户端报数值照单全收"）
// ============================================================================

bool AColdSteelPlayerState::ValidateHitReport(const FColdSteelNetHitReport& Report, AFPSGAMECharacter* Shooter,
    FString& OutReason, const FColdSteelItem*& OutDeclaredItem)
{
    OutDeclaredItem = nullptr;
    if (!ShadowModel) { OutReason = TEXT("no shadow"); return false; }
    if (!Shooter) { OutReason = TEXT("no pawn"); return false; }
    if (UFPSCombatHealthComponent* HP = Shooter->FindComponentByClass<UFPSCombatHealthComponent>())
        if (HP->IsDead()) { OutReason = TEXT("shooter dead"); return false; }

    // 武器声明必须匹配服务端影子的持握武器——主手或双持副手任一同型号槽位。
    // Quick combat allows an empty declaration; ordinary punches require both active hands empty.
    const bool bUnarmed=Report.AttackMeta==UnarmedPunch::AttackMeta&&Report.ItemDefinition.IsEmpty();
    if(bUnarmed)
    {
        const int32 Primary=ShadowModel->Snapshot().ActiveWeaponSlot;
        const int32 Offhand=Primary==6?8:11;
        if(ShadowModel->Equipped(Primary)||ShadowModel->Equipped(Offhand)||ShadowModel->ActiveProductionTool())
        {OutReason=TEXT("unarmed equipment mismatch");return false;}
    }
    const FColdSteelItem* Equipped = ShadowModel->Equipped();
    if (Equipped && Equipped->Definition == Report.ItemDefinition) OutDeclaredItem = Equipped;
    if (!OutDeclaredItem)
        for (const FColdSteelItem& I : ShadowModel->Items())
            if (I.Place == 1 && I.Definition == Report.ItemDefinition) { OutDeclaredItem = &I; break; }
    if (!OutDeclaredItem && !bUnarmed && !((Report.AttackMeta & 0x80) && Report.ItemDefinition.IsEmpty()))
    { OutReason = TEXT("weapon mismatch"); return false; }

    // 射速限流：令牌桶按服务端 EffectiveFireInterval 充能，上限容纳一次性补射连发。
    const double Now = GetWorld()->GetTimeSeconds();
    const double Interval = bUnarmed?double(StaffQuickCombatMotion::Length):FMath::Max(0.05, Shooter->EffectiveFireInterval());
    FireTokenBucket = FMath::Min(6.f, FireTokenBucket + static_cast<float>((Now - LastFireTokenRefillAt) / Interval));
    LastFireTokenRefillAt = Now;
    if (FireTokenBucket < 1.f) { OutReason = TEXT("rate"); return false; }

    // 几何合理性（抗明显伪造）。投射物（箭/法杖弹/裂斩波/弹道弹）的 TraceStart 是
    // 弹体飞行末段位置、远离射手属正常——只对直线类命中保留 600cm 原点漂移检查；
    // 统一改为"命中点距服务端射手 ≤ 射程"的主口径。
    UGameInstance* GI = GetGameInstance();
    const UGunsmithSystem* Gunsmith = GI ? GI->GetSubsystem<UGunsmithSystem>() : nullptr;
    const bool bProjectile = !bUnarmed&&((Report.AttackMeta & 0x40) != 0
        || (OutDeclaredItem && (ColdSteelInventory::IsBow(*OutDeclaredItem)
            || (Gunsmith && Gunsmith->IsStaff(OutDeclaredItem->Definition))))
        || Shooter->ProjectileSpeedCM > 0.f);
    if (!bProjectile)
    {
        const float OriginDrift = FVector::Dist(Shooter->GetActorLocation(), FVector(Report.AimOrigin));
        if (OriginDrift > 600.f) { OutReason = TEXT("origin drift"); return false; }
    }
    float MaxRange = bUnarmed?UnarmedPunch::ReachCM+120.f:Shooter->TraceDistance*1.25f;
    if(Report.AttackMeta==SwordUppercut::AttackMeta&&OutDeclaredItem&&ColdSteelInventory::IsTwoHandedSword(*OutDeclaredItem))
        MaxRange=static_cast<float>(ColdSteelMelee::UppercutReachCM(ShadowModel))*1.25f;
    if (FVector::Dist(Shooter->GetActorLocation(), FVector(Report.ImpactPoint)) > MaxRange)
    { OutReason = TEXT("range"); return false; }
    const float Range = FVector::Dist(FVector(Report.AimOrigin), FVector(Report.ImpactPoint));
    if (Range > MaxRange) { OutReason = TEXT("range"); return false; }

    // 服务端 LOS：直线类命中（hitscan/近战/裂斩波）检查眼位→命中点的世界静态遮挡，
    // 堵"申报墙后原点穿墙打"的伪报；弹道抛射物有重力弧线，跳过（rewind 校验仍兜底）。
    if (!bProjectile || (Report.AttackMeta & 0x40))
    {
        FCollisionQueryParams LOSParams(SCENE_QUERY_STAT(NetHitLOS), true);
        LOSParams.AddIgnoredActor(Shooter);
        if (Report.Target) LOSParams.AddIgnoredActor(Report.Target.Get());
        FHitResult LOSHit;
        if (GetWorld()->LineTraceSingleByChannel(LOSHit, Shooter->GetPawnViewLocation(),
            FVector(Report.ImpactPoint), ECC_Visibility, LOSParams))
        { OutReason = TEXT("los blocked"); return false; }
    }

    if (!Report.Target) { OutReason = TEXT("no target"); return false; }
    UFPSCombatHealthComponent* TargetHealth = Report.Target->FindComponentByClass<UFPSCombatHealthComponent>();
    if (TargetHealth && TargetHealth->IsDead()) { OutReason = TEXT("target dead"); return false; }

    // rewind 时间戳：客户端上报的是它估计的服务端世界钟（GameState->GetServerWorldTimeSeconds）。
    // 超出历史窗口的报数直接拒（过期重放/伪时间戳）。
    const double ServerNow = GetWorld()->GetGameState()
        ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
        : GetWorld()->GetTimeSeconds();
    const double ShotAge = Report.ClientFireTime > 0.0 ? ServerNow - Report.ClientFireTime : 0.0;
    if (Report.ClientFireTime > 0.0 && (ShotAge < -0.10 || ShotAge > 0.9))
    { OutReason = TEXT("stale timestamp"); return false; }

    // rewind 几何校验：把目标胶囊轴插值回射击时刻的位姿，检验弹道线段确实穿过它。
    // 容差=胶囊半径 + 60cm 采样间位移余量（25Hz 录制 + 冲刺/闪避高速目标）。
    if (TargetHealth)
    {
        FVector RewoundCenter, RewoundTop;
        const UCapsuleComponent* Capsule = Report.Target->FindComponentByClass<UCapsuleComponent>();
        const double PoseTime = Report.ClientFireTime > 0.0 ? Report.ClientFireTime : ServerNow;
        if (Capsule && TargetHealth->GetLagPose(PoseTime, RewoundCenter, RewoundTop))
        {
            const FVector CapBottom = RewoundCenter + (RewoundCenter - RewoundTop);
            FVector OnShot, OnAxis;
            FMath::SegmentDistToSegmentSafe(FVector(Report.AimOrigin), FVector(Report.ImpactPoint),
                CapBottom, RewoundTop, OnShot, OnAxis);
            const float MissDist = FVector::Dist(OnShot, OnAxis);
            if (MissDist > Capsule->GetScaledCapsuleRadius() + 60.f)
            { OutReason = FString::Printf(TEXT("rewind miss %.0fcm"), MissDist); return false; }
        }
    }

    FireTokenBucket -= 1.f;
    return true;
}

float AColdSteelPlayerState::ComputeServerDamage(AFPSGAMECharacter* Shooter,
    const FColdSteelNetHitReport& Report, const FColdSteelSkillShot& Shot,
    const FColdSteelItem* Item, float ConvergenceScale) const
{
    // 全部走服务端可信输入：影子档案装备/修炼 + 已校验几何 + 申报语义上下文。
    // 客户端不可再决定伤害数值，只决定"用了哪种攻击"。Item=已校验的申报武器。
    const float Panel = Shot.DamagePanel.Total();
    UGameInstance* GI = GetGameInstance();
    UGunsmithSystem* G = GI ? GI->GetSubsystem<UGunsmithSystem>() : nullptr;

    if(Report.AttackMeta==UnarmedPunch::AttackMeta&&Report.ItemDefinition.IsEmpty())
        return UnarmedPunch::Damage(ShadowModel);

    // 技能语义覆盖优先：旋风/快速近战是技能面板，与武器面板无关。
    if (Report.AttackMeta & 0x20)
        return ShadowModel ? ShadowModel->WhirlwindStats().Damage : Panel;
    if (Report.AttackMeta & 0x80)
        return ShadowModel ? ShadowModel->QuickCombatStats().Damage : Panel;

    if (Item && ColdSteelInventory::IsBow(*Item))
    {
        // 弓：面板 × 拉弦倍率(0.5-1.5，申报比钳 [0,1]) × 箭种倍率（服务端影子同参）。
        const float Draw = ColdSteelBow::DrawDamageMultiplier(FMath::Clamp(Report.DamageContext, 0.f, 1.f));
        return Panel * Draw * ShadowModel->AmmoDamageMultiplier(*Item);
    }

    if (Item && ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        // 剑挥砍：面板 × 轻重击/连段倍率——倍率函数与客户端同一套（MeleeModifiers 服务端可算）。
        const auto Melee = ColdSteelMelee::Evaluate(*Item, ShadowModel);
        // Uppercut uses its own level while retaining the complete heavy formula.
        if(Report.AttackMeta==0x14)
            return Melee.Damage*ColdSteelMelee::UppercutMultiplier(ShadowModel,Melee.Modifiers);
        const int32 Stage = Report.AttackMeta & 0x0F;
        const double Mult = (Report.AttackMeta & 0x10)
            ? Melee.Modifiers.HeavyMultiplier(ShadowModel->MasteryEffect(TEXT("heavyStrike")).HeavyMultiplier)
            : Melee.Modifiers.ComboMultiplier(Stage);
        double Damage = Panel * Mult;
        if (Report.AttackMeta & 0x40) // 裂斩波 = 挥砍伤害 × 附魔缩放（服务端同参）
            if (const auto* E = GI ? GI->GetSubsystem<UColdSteelEnhancementSystem>() : nullptr)
                Damage *= E->Effect(*Item, TEXT("riftSlashDamageScale"));
        return float(Damage);
    }

    if (Item && G && G->IsStaff(Item->Definition))
        return float(ColdSteelWeaponStats::Damage(*Item, ShadowModel, 3.0));

    if (Item && G && G->IsTool(Item->Definition))
        return Panel; // 斧头等生产工具：面板即伤害（AxeStrike.DamagePanel.Total() 同口径）

    // 枪械 hitscan 与弹道投射物：面板 × 汇聚(已按弹匣容量钳) × 服务端距离衰减。
    const float Distance = FVector::Dist(FVector(Report.AimOrigin), FVector(Report.ImpactPoint));
    return Panel * ConvergenceScale
        * WeaponDamageFalloff::Multiplier(Distance, Shooter->EffectiveWeaponRangeCM);
}

void AColdSteelPlayerState::ServerReportHit_Implementation(const FColdSteelNetHitReport& Report)
{
    if (GetLocalRole() != ROLE_Authority) return;
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Shooter = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;

    FString Reject;
    const FColdSteelItem* Declared = nullptr;
    if (!ValidateHitReport(Report, Shooter, Reject, Declared))
    {
        UE_LOG(LogTemp, Warning, TEXT("MPTEST hit rejected: %s (%s)"), *Reject, *GetPlayerName());
        return;
    }
    // 远端身体开火表现与身体组件 ServerClock 同域（GameState 服务端世界钟）。
    LastValidatedShotAt = GetWorld()->GetGameState()
        ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
        : GetWorld()->GetTimeSeconds();

    // 服务端按影子档案复算 Shot——客户端不再上报伤害构成，只报几何 + 语义 flag。
    // Snapshot 经 GetNetShadowProfile 自动取到影子（对主机玩家回退单例）。
    const bool bFiredRound = (Report.Flags & (1 << 6)) != 0;
    // 用客户端声明（且已校验属于持握集合）的那件武器建 Shot——双持副手命中拿到副手面板。
    FColdSteelSkillShot Shot = ColdSteelSkills::Snapshot(Shooter,
        Declared ? Declared : ShadowModel->Equipped(), bFiredRound);
    Shot.bMeleeStrike = (Report.Flags & (1 << 0)) != 0;
    Shot.bRifle = (Report.Flags & (1 << 1)) != 0;
    Shot.bPistol = (Report.Flags & (1 << 2)) != 0;
    Shot.bMelee = (Report.Flags & (1 << 3)) != 0;
    Shot.bRicochet = (Report.Flags & (1 << 4)) != 0;
    Shot.bInheritedCritical = (Report.Flags & (1 << 5)) != 0;
    Shot.AttackMeta = Report.AttackMeta;
    if (Report.AttackForm != 0) Shot.AttackForm = static_cast<EMonsterAttackForm>(Report.AttackForm);

    // 自报伤害钳制在服务端武器包络内：汇聚倍率服务端复算，
    // 消耗弹数按影子装备弹匣容量上界（客户端申报的 Rounds 本身不可信——无界会放大 cap）。
    float ConvergenceScale = 1.f;
    if (Report.ConvergenceRounds > 1)
    {
        const FColdSteelConvergence Conv = ColdSteelCombat::Convergence(
            GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>() : nullptr,
            ShadowModel->Equipped());
        const int32 Rounds = FMath::Clamp<int32>(Report.ConvergenceRounds, 0, FMath::Max(1, Shooter->GetMagazineCapacity()));
        ConvergenceScale = static_cast<float>(ColdSteelCombat::ConvergenceShotScale(Conv, Rounds));
    }
    // 权威伤害由服务端按武器族全量复算；ClaimedDamage 只进对账日志（偏差大即伪报特征）。
    const float Damage = ComputeServerDamage(Shooter, Report, Shot, Declared, ConvergenceScale);
    if (Report.ClaimedDamage > 0.f && FMath::Abs(Report.ClaimedDamage - Damage) > FMath::Max(1.f, Damage * 0.25f))
        UE_LOG(LogTemp, Warning, TEXT("MPTEST dmg recon: claimed=%.1f computed=%.1f shooter=%s"),
            Report.ClaimedDamage, Damage, *GetPlayerName());

    FHitResult Hit(FVector(Report.ImpactPoint), FVector(Report.HitNormal));
    Hit.BoneName = Report.BoneName;
    Hit.HitObjectHandle = FActorInstanceHandle(Report.Target.Get());
    Hit.bBlockingHit = true;

    UColdSteelStatusModel* Model = ShadowModel;
    if (!Model)
    {
        const UGameInstance* GI = GetGameInstance();
        Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    }
    if (!Model) return;

    FWeaponDamageResult Receipt;
    const float Applied = Model->ApplySkillWeaponHit(Shooter, Hit, Damage, FVector(Report.Direction), Shot, &Receipt);
    UE_LOG(LogTemp, Warning, TEXT("MPTEST hit applied: shooter=%s target=%s dmg=%.1f crit=%d killed=%d"),
        *GetNameSafe(Shooter), *GetNameSafe(Report.Target), Applied, Receipt.bCritical ? 1 : 0, Receipt.bKilled ? 1 : 0);
    bServerDirty = true;
    ServerSaveTimer = 20.f;

    FColdSteelNetHitReceipt Out;
    Out.Target = Report.Target;
    Out.Applied = Applied;
    Out.bCritical = Receipt.bCritical;
    Out.bKilled = Receipt.bKilled;
    ClientConfirmHit(Out);
}

void AColdSteelPlayerState::ClientConfirmHit_Implementation(const FColdSteelNetHitReceipt& Receipt)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* LocalChar = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!LocalChar || !Receipt.Target) return;
    FWeaponDamageResult Result;
    Result.bResolved = true;
    Result.bCritical = Receipt.bCritical;
    Result.bKilled = Receipt.bKilled;
    LocalChar->NotifyConfirmedWeaponHit(Receipt.Target, Receipt.Applied, &Result, true);
    UE_LOG(LogTemp, Warning, TEXT("MPTEST hit confirmed on client: target=%s applied=%.1f"),
        *GetNameSafe(Receipt.Target), Receipt.Applied);
}

// ============================================================================
// 远端身体表现（离散动作 + 开火戳）
// ============================================================================

void AColdSteelPlayerState::ServerReportBodyAction_Implementation(uint8 Action, FName Variant, float Duration)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    UFPSPlayerBodyComponent* Body = Pawn ? Pawn->FindComponentByClass<UFPSPlayerBodyComponent>() : nullptr;
    if (!Body) return;
    Body->ServerRecordAction(static_cast<EFPSBodyAction>(Action), Variant, Duration);
}

void AColdSteelPlayerState::ServerReportShotStamp_Implementation()
{
    const double Now = GetWorld()->GetGameState()
        ? GetWorld()->GetGameState()->GetServerWorldTimeSeconds()
        : GetWorld()->GetTimeSeconds();
    // 防抖：合法射速上限约 33Hz；只影响远端开火姿势，不拦截实际命中校验（那条走令牌桶）。
    if (Now - LastShotStampAt < 0.03) return;
    LastShotStampAt = Now;
    LastValidatedShotAt = Now;
}

// ============================================================================
// 施法意图通道（A 模式：客户端报意图，服务端按影子档案执行，实体经复制回流）
// ============================================================================

void AColdSteelPlayerState::ServerCastSpell_Implementation(const FColdSteelNetCastRequest& Request)
{
    if (GetLocalRole() != ROLE_Authority) return;
    if (GetWorld() && GetWorld()->GetNetMode() == NM_Standalone) return;
    // 防抖：施法相位切换的最小合理间隔远大于 150ms。
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now - LastCastRequestAt < 0.15) return;
    LastCastRequestAt = Now;
    ExecuteCastRequest(Request);
}

namespace
{
// 各技能在服务端落地的最小校验：影子档扣账入口 + 对应组件指针。Phase1 的具体执行在组件侧。
struct FNetCastSkill { FName Id; };
const FNetCastSkill NetCastSkills[] = {
    { TEXT("fireball") }, { TEXT("iceSpike") }, { TEXT("iceWall") }, { TEXT("blizzard") },
    { TEXT("holyLight") }, { TEXT("lightning") }, { TEXT("meteor") }, { TEXT("flameArmor") },
    { TEXT("stormDomain") }, { TEXT("thunderLance") },
};
bool IsNetCastSkill(FName Id)
{
    for (const auto& S : NetCastSkills) if (S.Id == Id) return true;
    return false;
}
}

void AColdSteelPlayerState::ExecuteCastRequest(const FColdSteelNetCastRequest& Request)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    const auto Reject = [&](uint8 Code) { ClientCastResult(Request.SkillId, Request.Phase, Code); };
    const auto Accept = [&]() { ClientCastResult(Request.SkillId, Request.Phase, 0); };
    if (!ShadowModel || !Pawn) { Reject(1); return; }
    if (!IsNetCastSkill(Request.SkillId)) { Reject(2); return; }
    const double Now = GetWorld()->GetTimeSeconds();

    // ── Phase 2/3 取消/弃置：通用收尾——销毁在途实体，按技能退蓝/清占用。 ──
    if (Request.Phase == 2 || Request.Phase == 3)
    {
        if (PendingCastOrb.IsValid()) { PendingCastOrb->Destroy(); PendingCastOrb.Reset(); }
        if (PendingCastSkill == Request.SkillId)
        {
            if (Request.Phase == 2) ShadowModel->RefundUnreleasedCast(PendingCastPaidMana, Request.SkillId);
            else
            {
                if (Request.SkillId == TEXT("fireball")) ShadowModel->FinishFireballCast();
                else if (Request.SkillId == TEXT("iceSpike")) ShadowModel->FinishIceSpikeCast(FIceSpikeRewards());
                // iceWall 无独立 Finish：弃置未释放的种子墙只占用手位，CommitIceWallRelease 之前不产生结算。
                else if (Request.SkillId == TEXT("blizzard")) ShadowModel->FinishBlizzardCast(FBlizzardRewards());
                else if (Request.SkillId == TEXT("holyLight")) ShadowModel->FinishHolyLightCast(FHolyLightRewards());
                else if (Request.SkillId == TEXT("lightning")) ShadowModel->FinishLightningCast(FLightningRewards());
                else if (FireMagic::IsSkill(Request.SkillId)) ShadowModel->FinishFireMagicCast(Request.SkillId, FFireMagicRewards());
                else if (ElectricMagic::IsSkill(Request.SkillId)) ShadowModel->FinishElectricMagicCast(Request.SkillId, FElectricMagicRewards());
            }
        }
        PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
        Accept();
        return;
    }

    // ── Phase 1 释放：按技能分派到组件服务端入口（影子档案校验在里面）。 ──
    if (Request.Phase == 1)
    {
        if (Request.SkillId == TEXT("fireball"))
        {
            auto* Ball = Cast<AFPSFireballProjectile>(PendingCastOrb.Get());
            if (PendingCastSkill != TEXT("fireball") || !Ball || Now - PendingCastAt > 35.0) { Reject(3); return; }
            Ball->LaunchAt(Request.AimPoint);
            ShadowModel->FinishFireballCast();
            PendingCastOrb.Reset(); PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("iceSpike"))
        {
            auto* Volley = Cast<AFPSIceSpikeVolley>(PendingCastOrb.Get());
            if (PendingCastSkill != TEXT("iceSpike") || !Volley || Now - PendingCastAt > 35.0) { Reject(3); return; }
            Volley->LaunchAt(Request.AimPoint);
            PendingCastOrb.Reset(); PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("iceWall"))
        {
            if (PendingCastSkill != TEXT("iceWall")) { Reject(3); return; }
            auto* Wall = Pawn->FindComponentByClass<UFPSIceWallComponent>();
            if (!Wall || !Wall->NetCommitWall(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("blizzard"))
        {
            if (PendingCastSkill != TEXT("blizzard")) { Reject(3); return; }
            auto* B = Pawn->FindComponentByClass<UFPSBlizzardComponent>();
            if (!B || !B->NetCommitZone(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("holyLight"))
        {
            if (PendingCastSkill != TEXT("holyLight")) { Reject(3); return; }
            auto* H = Pawn->FindComponentByClass<UFPSHolyLightComponent>();
            if (!H || !H->NetRelease(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (Request.SkillId == TEXT("lightning"))
        {
            if (PendingCastSkill != TEXT("lightning")) { Reject(3); return; }
            auto* L = Pawn->FindComponentByClass<UFPSLightningComponent>();
            if (!L || !L->NetRelease(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (FireMagic::IsSkill(Request.SkillId))
        {
            if (PendingCastSkill != Request.SkillId) { Reject(3); return; }
            auto* F = Pawn->FindComponentByClass<UFPSFireMagicComponent>();
            if (!F || !F->NetRelease(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        if (ElectricMagic::IsSkill(Request.SkillId))
        {
            if (PendingCastSkill != Request.SkillId) { Reject(3); return; }
            auto* E = Pawn->FindComponentByClass<UFPSElectricMagicComponent>();
            if (!E || !E->NetRelease(Pawn, Request, ShadowModel)) { Reject(7); return; }
            PendingCastSkill = NAME_None; PendingCastPaidMana = 0.f;
            Accept(); return;
        }
        Reject(2); return;
    }

    // ── Phase 0 凝聚：影子档校验法耗/冷却并扣账；带悬停体的技能同时生成权威实体。 ──
    if (PendingCastOrb.IsValid() || PendingCastSkill != NAME_None) { Reject(4); return; }
    if (auto* HP = Pawn->FindComponentByClass<UFPSCombatHealthComponent>(); HP && HP->IsDead()) { Reject(5); return; }

    if (Request.SkillId == TEXT("fireball"))
    {
        const FFireballCast Stats = ShadowModel->FireballStats();
        if (!ShadowModel->BeginFireballCast()) { Reject(6); return; }
        auto* Ability = Pawn->FindComponentByClass<UFPSFireballComponent>();
        auto* Ball = Ability ? Ability->SpawnOrbForCast(Pawn, Stats) : nullptr;
        if (!Ball) { ShadowModel->RefundUnreleasedCast(Stats.ManaCost, TEXT("fireball")); Reject(7); return; }
        PendingCastOrb = Ball; PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("iceSpike"))
    {
        const FIceSpikeCast Stats = ShadowModel->IceSpikeStats();
        if (!ShadowModel->BeginIceSpikeCast(Stats)) { Reject(6); return; }
        auto* Ability = Pawn->FindComponentByClass<UFPSIceSpikeComponent>();
        auto* Volley = Ability ? Ability->SpawnVolleyForCast(Pawn, Stats) : nullptr;
        if (!Volley) { ShadowModel->RefundUnreleasedCast(Stats.ManaCost, TEXT("iceSpike")); Reject(7); return; }
        PendingCastOrb = Volley; PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("iceWall"))
    {
        const FIceWallCast Stats = ShadowModel->IceWallStats();
        if (!ShadowModel->BeginIceWallCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("blizzard"))
    {
        const FBlizzardCast Stats = ShadowModel->BlizzardStats();
        if (!ShadowModel->BeginBlizzardCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("holyLight"))
    {
        const FHolyLightCast Stats = ShadowModel->HolyLightStats();
        if (!ShadowModel->BeginHolyLightCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
    }
    else if (Request.SkillId == TEXT("lightning"))
    {
        const FLightningCast Stats = ShadowModel->LightningStats();
        if (!ShadowModel->BeginLightningCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
    }
    else if (FireMagic::IsSkill(Request.SkillId))
    {
        const FFireMagicCast Stats = ShadowModel->FireMagicStats(Request.SkillId);
        if (!ShadowModel->BeginFireMagicCast(Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.ManaCost;
    }
    else if (ElectricMagic::IsSkill(Request.SkillId))
    {
        const FElectricMagicCast Stats = ShadowModel->ElectricMagicStats(Request.SkillId);
        if (!ShadowModel->BeginElectricMagicCast(Request.SkillId, Stats)) { Reject(6); return; }
        PendingCastPaidMana = Stats.Hit.ManaCost;
    }
    PendingCastSkill = Request.SkillId; PendingCastAt = Now;
    Accept();
}

void AColdSteelPlayerState::ClientCastResult_Implementation(FName SkillId, uint8 Phase, uint8 Code)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!Pawn) return;
    // 把回执路由到发起技能的组件；各组件自己决定拒收/取消的本地收尾。
    const auto Receipt = [Phase, Code](auto* C)
    {
        if (!C) return;
        if (Code == 0 && (Phase == 2 || Phase == 3)) C->NetCastCancelled(Phase);
        else if (Code != 0) C->NetCastRejected(Phase, Code);
    };
    if (SkillId == TEXT("fireball")) Receipt(Pawn->FindComponentByClass<UFPSFireballComponent>());
    else if (SkillId == TEXT("iceSpike")) Receipt(Pawn->FindComponentByClass<UFPSIceSpikeComponent>());
    else if (SkillId == TEXT("iceWall")) Receipt(Pawn->FindComponentByClass<UFPSIceWallComponent>());
    else if (SkillId == TEXT("blizzard")) Receipt(Pawn->FindComponentByClass<UFPSBlizzardComponent>());
    else if (SkillId == TEXT("holyLight")) Receipt(Pawn->FindComponentByClass<UFPSHolyLightComponent>());
    else if (SkillId == TEXT("lightning")) Receipt(Pawn->FindComponentByClass<UFPSLightningComponent>());
    else if (FireMagic::IsSkill(SkillId)) Receipt(Pawn->FindComponentByClass<UFPSFireMagicComponent>());
    else if (ElectricMagic::IsSkill(SkillId)) Receipt(Pawn->FindComponentByClass<UFPSElectricMagicComponent>());
}

// ============================================================================
// 命中转发器（ColdSteelNet 模块注册到 ColdSteelSkills::NetHitForward()）
// ============================================================================

bool AColdSteelPlayerState::ForwardHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot)
{
    const APawn* Pawn = Cast<APawn>(Shooter);
    AColdSteelPlayerState* PS = Pawn ? Pawn->GetPlayerState<AColdSteelPlayerState>() : nullptr;
    if (!PS) return false;

    FColdSteelNetHitReport Report;
    Report.Target = Hit.GetActor();
    Report.AimOrigin = Hit.TraceStart;
    Report.ImpactPoint = Hit.ImpactPoint;
    Report.HitNormal = Hit.ImpactNormal;
    Report.BoneName = Hit.BoneName;
    Report.Direction = Direction;
    Report.ItemDefinition = Shot.ItemDefinition;
    Report.ClaimedDamage = Damage;
    Report.AttackMeta = Shot.AttackMeta;
    Report.DamageContext = Shot.DamageContext;
    Report.AttackForm = static_cast<uint8>(Shot.AttackForm);
    if (const AFPSGAMECharacter* Char = Cast<AFPSGAMECharacter>(Shooter))
        Report.ConvergenceRounds = static_cast<uint8>(FMath::Clamp(Char->LastShotConvergenceRounds, 0, 255));
    // 时间戳用客户端估计的服务端世界钟——服务端据此做 rewind 回放与新鲜度检查。
    if (const UWorld* W = Pawn->GetWorld())
    {
        const AGameStateBase* GS = W->GetGameState();
        Report.ClientFireTime = GS ? GS->GetServerWorldTimeSeconds() : W->GetTimeSeconds();
    }
    if (Shot.bMeleeStrike) Report.Flags |= 1 << 0;
    if (Shot.bRifle) Report.Flags |= 1 << 1;
    if (Shot.bPistol) Report.Flags |= 1 << 2;
    if (Shot.bMelee) Report.Flags |= 1 << 3;
    if (Shot.bRicochet) Report.Flags |= 1 << 4;
    if (Shot.bInheritedCritical) Report.Flags |= 1 << 5;
    // bFiredRound：真正消耗弹药的一发（枪/弓），不含近战挥砍与握把砸击。
    if (!Shot.bMelee && !Shot.bMeleeStrike) Report.Flags |= 1 << 6;
    PS->ServerReportHit(Report);
    return true;
}
