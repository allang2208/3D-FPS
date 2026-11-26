#include "ColdSteelPlayerState.h"
#include "ColdSteelMapMarkerSharing.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/StarMarrowComponent.h"
#include "ColdSteelPreparedHit.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ConicalHammerSeat.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/RootCrownHitComponent.h"
#include "../Monsters/HeQueMonster.h"
#include "../Monsters/HumanoidHitVolumeData.h"
#include "../Combat/RangedAttackQuery.h"
#include "ColdSteelNetWorldSubsystem.h"
#include "ColdSteelNetSessionSubsystem.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "ColdSteelProfileTransfer.h"
#include "Serialization/JsonSerializer.h"
#include "ColdSteelProfileMerge.h"
#include "UppercutStaminaReceipt.h"
#include "../Building/WoodworkingQuality.h"
#include "../Building/ForgingQuality.h"
#include "../Building/GunAssemblyQuality.h"
#include "../Items/FoodSpoilage.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/BoundCongregate.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/SwordUppercutWeapon.h"
#include "../Skills/WhirlwindTypes.h"
#include "../Skills/MagicOcclusion.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/MeteorGround.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/IceSpikeTypes.h"
#include "../Skills/IceWallTypes.h"
#include "../Skills/BlizzardTypes.h"
#include "../Skills/HolyLightTypes.h"
#include "../Skills/LightningTypes.h"
#include "../Skills/FireMagicTypes.h"
#include "../Skills/ElectricMagicTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelCurrency.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/AzureDragonReach.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "../Weapons/Kukri/OffhandKukriThrust.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/LMGStabilityGrip.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Kukri/SwiftFalconHeavy.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookFocusMana.h"
#include "../Weapons/MagicCrystalMana.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/SniperSuppressorAssets.h"
#include "../Weapons/WeaponShotNoise.h"
#include "../Weapons/WeaponDamageFalloff.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/NetConnection.h"
#include "Engine/HitResult.h"
#include "CollisionQueryParams.h"
#include "Engine/ActorInstanceHandle.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameState.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

namespace
{
    using ColdSteelProfileTransfer::SaveToBlob;
    using ColdSteelProfileTransfer::BlobToSave;

    // 服务端施法执行器的技能表键：新增技能在这里注册后按分支实现。
    const FName FireballSkillId(TEXT("fireball"));
}

AColdSteelPlayerState::AColdSteelPlayerState()
{
    CreateDefaultSubobject<UColdSteelMapMarkerSharing>(TEXT("MapMarkerSharing"));
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    NetUpdateFrequency = 10.f;
}

void AColdSteelPlayerState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelPlayerState, PublicInfo);
    DOREPLIFETIME(AColdSteelPlayerState,bInDungeonRoom);
    DOREPLIFETIME_CONDITION(AColdSteelPlayerState,bClaimedFinalDungeonTreasure,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(AColdSteelPlayerState,SessionDoorKeys,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(AColdSteelPlayerState,FoodClockState,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(AColdSteelPlayerState,PlantingUtcTicks,COND_OwnerOnly);
}

void AColdSteelPlayerState::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Standalone) return;
    if(const auto* PC=Cast<APlayerController>(GetOwner());PC&&PC->IsLocalController())bWasLocalOwner=true;
    TickSuper90Recovery();
    TickPistolRecovery();
    TickContainerRefresh();
    TickTeamTravel();
    TickRoomEntry();
    TickWorldNetwork(DeltaSeconds);
    TickStations(DeltaSeconds);
    TickWoodNetwork();

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
        TickBowDrawAuthority();
        if (ShadowModel && Pawn && ShadowPawn.Get() == Pawn)
            ShadowModel->TickRuntime(DeltaSeconds, Pawn);
        TickSuper90Authority(DeltaSeconds);
        TickPistolAuthority();
        TickSwordUppercut();
        TickShadowStep();
        TickSwordWhirlwind(DeltaSeconds);
        TickKukriAuthority(DeltaSeconds);
        if(!PendingCastSkill.IsNone())
        {
            const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
            const bool MissingOrb=(PendingCastSkill==FireballSkillId||PendingCastSkill==TEXT("iceSpike"))&&!PendingCastOrb.IsValid();
            if(!Pawn||PendingCastPawn.Get()!=Pawn||(Health&&Health->IsDead())||MissingOrb)
            {const FName Cancelled=PendingCastSkill;const uint32 CastId=PendingIdentifiedCastId;auto* CastPawn=PendingCastPawn.Get();CancelPendingNetworkCast();ClientCastResult(Cancelled,1,5,CastPawn,ProcessedCastSequence,CastId);}
        }
        if (PendingCastSkill == TEXT("blizzard"))
        {
            const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
            const auto* Hands=Pawn?Pawn->FindComponentByClass<UFPSFireballComponent>():nullptr;
            const double Lifetime=35.0+(Hands?Hands->RaiseDuration+Hands->ReleaseEntryDuration+Hands->ReleaseDuration:1.55f)/FMath::Max(.1f,PendingBlizzardStats.CastSpeed);
            if(!Pawn||(Health&&Health->IsDead())||World->GetTimeSeconds()-PendingCastAt>Lifetime)
            {
                if(ShadowModel)ShadowModel->RefundUnreleasedCast(PendingCastPaidMana,TEXT("blizzard"));
                PendingCastSkill=NAME_None;PendingCastPaidMana=0.f;
                ClientCastResult(TEXT("blizzard"),1,5,PendingCastPawn.Get(),ProcessedCastSequence);
            }
        }
        TickInventoryReply();
        if(PendingCastSkill==TEXT("dragonBreath")||PendingCastSkill==TEXT("stormDomain")||PendingCastSkill==TEXT("flameArmor")||PendingCastSkill==TEXT("iceArmor")||PendingCastSkill==TEXT("lightningHaste")||PendingCastSkill==TEXT("meteor"))
        {
            const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
            const double Limit=PendingCastSkill==TEXT("stormDomain")?35.:10.;
            const bool MissingStaff=PendingCastSkill!=TEXT("flameArmor")&&PendingCastSkill!=TEXT("iceArmor")&&PendingCastSkill!=TEXT("lightningHaste")&&ShadowModel&&!ShadowModel->HasEquippedStaff();
            if(!Pawn||(Health&&Health->IsDead())||!ShadowModel||MissingStaff||World->GetTimeSeconds()-PendingCastAt>Limit)
            {
                const FName Skill=PendingCastSkill;
                const uint32 CastId=PendingIdentifiedCastId;auto* CastPawn=PendingCastPawn.Get();
                CancelPendingNetworkCast();ClientCastResult(Skill,1,5,CastPawn,ProcessedCastSequence,CastId);
            }
        }
        if(InventoryReplyOutgoing.IsEmpty())TickShadowMirror(DeltaSeconds);
        TickPublicInfo(DeltaSeconds);
        if (bServerDirty)
        {
            ServerSaveTimer -= DeltaSeconds;
            if (ServerSaveTimer <= 0.f)
            {
                ServerSaveTimer = 20.f;
                bServerDirty = !SaveShadowToHostDisk();
            }
        }
    }
    else
    {
        if(bMirrorReady)OnRep_MirrorBlob();
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

void AColdSteelPlayerState::InitializeHostSession()
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!HasAuthority()||!PC||!PC->IsLocalController())return;
    if(const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())BoundProfileId=Model->Snapshot().NetworkProfileId;
    if(const auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())
        for(FName Key:Session->RestoreGuestKeys(BoundProfileId))SessionDoorKeys.AddUnique(Key);
    ForceNetUpdate();
}

void AColdSteelPlayerState::InitializeGuest(const FString& InSlotName)
{
    if (bGuestInitialized) return;
    bGuestInitialized = true;
    SlotName = InSlotName;
    // Wait for the saved profile identity before loading a host-side guest slot.
    // PIE display names are temporary and can otherwise bind another client's save.
}

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
    if(const auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());Pawn&&Pawn->IsTubeShotgunWeapon())return;
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

