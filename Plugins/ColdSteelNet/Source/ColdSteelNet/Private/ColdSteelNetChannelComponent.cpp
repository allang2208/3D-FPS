#include "ColdSteelNetChannelComponent.h"
#include "ColdSteelNetLog.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/ActorInstanceHandle.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Crc.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"

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
}

UColdSteelNetChannelComponent::UColdSteelNetChannelComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

void UColdSteelNetChannelComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UColdSteelNetChannelComponent, MirrorBlob);
}

void UColdSteelNetChannelComponent::BeginPlay()
{
    Super::BeginPlay();
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (PC && PC->IsLocalController() && GetOwnerRole() != ROLE_Authority)
    {
        // 客户端：本机档案就绪即发首帧，之后 0.8s 心跳。
        ClientHeartbeat = 0.f;
        UE_LOG(LogColdSteelNet, Log, TEXT("Channel ready on owning client"));
        // M3 测试钩：合成命中（自动化验证客户端→服务端战斗链）。
        if (FParse::Param(FCommandLine::Get(), TEXT("MPClientShot")))
        {
            SyntheticShotCountdown = 12.f;
        }
    }
}

void UColdSteelNetChannelComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC)
    {
        return;
    }

    if (GetOwnerRole() != ROLE_Authority)
    {
        // M3 测试钩：合成命中（找一只非玩家 pawn 当靶）。
        if (SyntheticShotCountdown >= 0.f)
        {
            SyntheticShotCountdown -= DeltaTime;
            if (SyntheticShotCountdown <= 0.f)
            {
                SyntheticShotCountdown = 3.f;
                if (++SyntheticShotAttempts > 20)
                {
                    SyntheticShotCountdown = -1.f;
                }
                else if (AFPSGAMECharacter* LocalChar = Cast<AFPSGAMECharacter>(PC->GetPawn()))
                {
                    APawn* TargetPawn = nullptr;
                    for (TActorIterator<APawn> It(GetWorld()); It; ++It)
                    {
                        APawn* Candidate = *It;
                        if (Candidate && Candidate != LocalChar && !Candidate->IsPlayerControlled())
                        {
                            TargetPawn = Candidate;
                            break;
                        }
                    }
                    if (TargetPawn)
                    {
                        FColdSteelNetHitReport Report;
                        Report.Target = TargetPawn;
                        Report.HitLocation = TargetPawn->GetActorLocation();
                        Report.HitNormal = FVector::UpVector;
                        Report.Damage = 25.f;
                        Report.Direction = (TargetPawn->GetActorLocation() - LocalChar->GetActorLocation()).GetSafeNormal();
                        ServerReportHit(Report);
                        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST synthetic hit sent -> %s"), *GetNameSafe(TargetPawn));
                        SyntheticShotCountdown = -1.f;
                    }
                }
            }
        }

        // 变更检测：每 2s 对比一次快照，无变化零流量（perf：闲时上行=0）。
        HeartbeatTimer -= DeltaTime;
        if (HeartbeatTimer <= 0.f)
        {
            HeartbeatTimer = 2.f;
            const UGameInstance* GI = PC ? PC->GetGameInstance() : nullptr;
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
                const TArray<uint8>& Reference = PendingUpload.Num() > 0 ? PendingUpload : LastSentBlob;
                if (!bHasLastSent || Reference != Blob)
                {
                    PendingUpload = MoveTemp(Blob);
                    PendingUploadId = ++UploadCounter;
                    NextChunkIndex = 0;
                    PendingTotalChunks = FMath::Max(1, FMath::DivideAndRoundUp(PendingUpload.Num(), ProfileChunkSize));
                    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST profile upload started: %d bytes / %d chunks"),
                        PendingUpload.Num(), PendingTotalChunks);
                }
            }
        }
        // 限速分片上行：每 tick ≤2 片（1KB），避免灌爆 reliable 窗口（实测 11×8KB 连发即溢出丢包）。
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
                bHasLastSent = true;
                PendingUpload.Reset();
            }
        }
        return;
    }

    // 服务端：脏档案 20s 节流落盘到主机。
    if (bServerDirty)
    {
        ServerSaveTimer -= DeltaTime;
        if (ServerSaveTimer <= 0.f)
        {
            ServerSaveTimer = 20.f;
            bServerDirty = false;
            SaveShadowToHostDisk();
        }
    }
}

void UColdSteelNetChannelComponent::ServerSubmitProfileChunk_Implementation(int32 UploadId, int32 ChunkIndex, int32 TotalChunks, const TArray<uint8>& Chunk)
{
    if (GetOwnerRole() != ROLE_Authority || TotalChunks <= 0 || ChunkIndex < 0 || ChunkIndex >= TotalChunks)
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
    constexpr int32 ChunkSize = UColdSteelNetChannelComponent::ProfileChunkSize;
    if (ChunkIndex * ChunkSize != IncomingBlob.Num() || Chunk.Num() > ChunkSize)
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
        if (Completed == LastAppliedBlob)
        {
            return; // 字节级相同：档案无实质变化，跳过应用（多人时消除 2s 一次的重放卡顿）
        }
        LastAppliedBlob = Completed;
        if (UColdSteelProfileSave* Save = BlobToSave(Completed))
        {
            UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST profile upload complete: %d bytes"), Completed.Num());
            ApplyGuestProfile(Save->Profile);
        }
    }
}

void UColdSteelNetChannelComponent::ApplyGuestProfile(const FColdSteelProfile& Profile)
{
    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    const UGameInstance* GI = PC ? PC->GetGameInstance() : nullptr;
    UColdSteelStatusModel* HostModel = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!HostModel)
    {
        return;
    }

    if (!ShadowModel)
    {
        ShadowModel = HostModel->CreateShadowModel(Profile);
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST shadow profile created: %s items=%d hp=%.0f"),
            *SlotName, Profile.Items.Num(), Profile.Health);
    }
    else
    {
        ShadowModel->AdoptNetMirror(Profile);
    }

    ApplyShadowToServerPawn();
    bServerDirty = true;
    ServerSaveTimer = 20.f;
}

void UColdSteelNetChannelComponent::ApplyShadowToServerPawn()
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !ShadowModel)
    {
        return;
    }
    if (AFPSGAMECharacter* Character = Cast<AFPSGAMECharacter>(PC->GetPawn()))
    {
        Character->NetShadowProfile = ShadowModel;
        Character->ApplyColdSteelProfile(ShadowModel);
        UE_LOG(LogColdSteelNet, Log, TEXT("MPTEST shadow applied to server pawn: %s"), *GetNameSafe(Character));
    }
}

void UColdSteelNetChannelComponent::OnRep_MirrorBlob()
{
    // 预留的权威回程入口（M3 伤害/服务端改档）。透传阶段服务端不写 MirrorBlob。
    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !PC->IsLocalController())
    {
        return;
    }
    const UGameInstance* GI = PC->GetGameInstance();
    if (UColdSteelStatusModel* Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr)
    {
        if (UColdSteelProfileSave* Save = BlobToSave(MirrorBlob))
        {
            Model->AdoptNetMirror(Save->Profile);
            UE_LOG(LogColdSteelNet, Log, TEXT("MPTEST mirror adopted (client)"));
        }
    }
}

void UColdSteelNetChannelComponent::InitializeGuest(const FString& InSlotName)
{
    SlotName = InSlotName;
    if (USaveGame* Loaded = UGameplayStatics::LoadGameFromSlot(SlotName, 0))
    {
        if (UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(Loaded))
        {
            UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST guest slot found on host disk: %s"), *SlotName);
            ApplyGuestProfile(Save->Profile);
        }
    }
}

void UColdSteelNetChannelComponent::SaveShadowToHostDisk()
{
    if (!ShadowModel || SlotName.IsEmpty())
    {
        return;
    }
    UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
    Save->Profile = ShadowModel->Snapshot();
    if (UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
    {
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST guest profile saved to host disk: %s items=%d hp=%.0f"),
            *SlotName, Save->Profile.Items.Num(), Save->Profile.Health);
    }
}

bool UColdSteelNetChannelComponent::ForwardHitStatic(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot)
{
    const APawn* Pawn = Cast<APawn>(Shooter);
    AController* Controller = Pawn ? Pawn->GetController() : nullptr;
    UColdSteelNetChannelComponent* Channel = Controller ? Controller->FindComponentByClass<UColdSteelNetChannelComponent>() : nullptr;
    if (!Channel)
    {
        return false;
    }

    FColdSteelNetHitReport Report;
    Report.Target = Hit.GetActor();
    Report.HitLocation = Hit.ImpactPoint;
    Report.HitNormal = Hit.ImpactNormal;
    Report.BoneName = Hit.BoneName;
    Report.Damage = Damage;
    Report.Direction = Direction;
    Report.AttackForm = static_cast<uint8>(Shot.AttackForm);
    Report.MasteryId = Shot.MasteryId;
    Report.ItemDefinition = Shot.ItemDefinition;
    Report.ExtraMasteryExperience = Shot.ExtraMasteryExperience;
    Report.AmmoPoisonStacks = Shot.AmmoPoisonStacks;
    Report.AmmoBleedStacks = Shot.AmmoBleedStacks;
    Report.ArmorPenetration = Shot.ArmorPenetration;
    Report.ToughnessDamageMultiplier = Shot.ToughnessDamageMultiplier;
    Report.MagicPenetration = Shot.MagicPenetration;
    Report.CriticalChance = Shot.CriticalChance;
    Report.WeakpointPercent = Shot.WeakpointPercent;
    Report.CriticalDamageBonus = Shot.CriticalDamageBonus;
    if (Shot.bMeleeStrike) Report.Flags |= 1 << 0;
    if (Shot.bRifle) Report.Flags |= 1 << 1;
    if (Shot.bPistol) Report.Flags |= 1 << 2;
    if (Shot.bMelee) Report.Flags |= 1 << 3;
    if (Shot.bRicochet) Report.Flags |= 1 << 4;
    if (Shot.bInheritedCritical) Report.Flags |= 1 << 5;
    Channel->ServerReportHit(Report);
    return true;
}

void UColdSteelNetChannelComponent::ServerReportHit_Implementation(const FColdSteelNetHitReport& Report)
{
    if (GetOwnerRole() != ROLE_Authority || !Report.Target)
    {
        return;
    }
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* Shooter = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!Shooter)
    {
        return;
    }
    UColdSteelStatusModel* Model = Shooter->GetNetShadowProfile();
    if (!Model)
    {
        const UGameInstance* GI = PC->GetGameInstance();
        Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    }
    if (!Model)
    {
        return;
    }

    FHitResult Hit(Report.HitLocation, Report.HitNormal);
    Hit.BoneName = Report.BoneName;
    Hit.HitObjectHandle = FActorInstanceHandle(Report.Target.Get());
    Hit.bBlockingHit = true;

    FColdSteelSkillShot Shot;
    Shot.MasteryId = Report.MasteryId;
    Shot.ItemDefinition = Report.ItemDefinition;
    Shot.AttackForm = static_cast<EMonsterAttackForm>(Report.AttackForm);
    Shot.ExtraMasteryExperience = Report.ExtraMasteryExperience;
    Shot.ArmorPenetration = Report.ArmorPenetration;
    Shot.ToughnessDamageMultiplier = Report.ToughnessDamageMultiplier;
    Shot.MagicPenetration = Report.MagicPenetration;
    Shot.CriticalChance = Report.CriticalChance;
    Shot.WeakpointPercent = Report.WeakpointPercent;
    Shot.CriticalDamageBonus = Report.CriticalDamageBonus;
    Shot.AmmoPoisonStacks = Report.AmmoPoisonStacks;
    Shot.AmmoBleedStacks = Report.AmmoBleedStacks;
    Shot.bMeleeStrike = (Report.Flags & (1 << 0)) != 0;
    Shot.bRifle = (Report.Flags & (1 << 1)) != 0;
    Shot.bPistol = (Report.Flags & (1 << 2)) != 0;
    Shot.bMelee = (Report.Flags & (1 << 3)) != 0;
    Shot.bRicochet = (Report.Flags & (1 << 4)) != 0;
    Shot.bInheritedCritical = (Report.Flags & (1 << 5)) != 0;

    FWeaponDamageResult Receipt;
    const float Applied = Model->ApplySkillWeaponHit(Shooter, Hit, Report.Damage, Report.Direction, Shot, &Receipt);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST hit applied: shooter=%s target=%s dmg=%.1f crit=%d killed=%d"),
        *GetNameSafe(Shooter), *GetNameSafe(Report.Target), Applied, Receipt.bCritical ? 1 : 0, Receipt.bKilled ? 1 : 0);

    FColdSteelNetHitReceipt Out;
    Out.Target = Report.Target;
    Out.Applied = Applied;
    Out.bCritical = Receipt.bCritical;
    Out.bKilled = Receipt.bKilled;
    ClientConfirmHit(Out);
}

void UColdSteelNetChannelComponent::ClientConfirmHit_Implementation(const FColdSteelNetHitReceipt& Receipt)
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    AFPSGAMECharacter* LocalChar = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
    if (!LocalChar || !Receipt.Target)
    {
        return;
    }
    FWeaponDamageResult Result;
    Result.bResolved = true;
    Result.bCritical = Receipt.bCritical;
    Result.bKilled = Receipt.bKilled;
    LocalChar->NotifyConfirmedWeaponHit(Receipt.Target, Receipt.Applied, &Result, true);
    UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST hit confirmed on client: target=%s applied=%.1f"), *GetNameSafe(Receipt.Target), Receipt.Applied);
}
