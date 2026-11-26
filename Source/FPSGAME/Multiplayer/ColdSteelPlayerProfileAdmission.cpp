#include "ColdSteelPlayerState.h"
#include "../Movement/StableHorseAffixes.h"
#include "../UI/ColdSteelWarehouseRules.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../Tasks/CarpenterApprenticeship.h"
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
#include "../Weapons/WoodenTorchItem.h"
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


using ColdSteelProfileTransfer::SaveToBlob;
using ColdSteelProfileTransfer::BlobToSave;

bool AColdSteelPlayerState::ApplyGuestProfile(const FColdSteelProfile& GuestProfile,bool bFromNetwork)
{
    FColdSteelProfile Sanitized;
    const FColdSteelProfile* Source=&GuestProfile;
    if(bFromNetwork)
    {
        Sanitized=GuestProfile;
        FString SanitizeReason;
        if(!SanitizeGuestProfile(Sanitized,SanitizeReason))
        {
            UE_LOG(LogTemp,Warning,TEXT("MPTEST guest profile rejected: %s"),*SanitizeReason);
            ClientProfileSyncRejected(SanitizeReason);
            return false;
        }
        Source=&Sanitized;
    }
    const FColdSteelProfile& Guest=*Source;
    if(Guest.NetworkProfileId.IsValid())
    {
        if(BoundProfileId.IsValid()&&BoundProfileId!=Guest.NetworkProfileId)return false;
        if(!BoundProfileId.IsValid())
        {
            // One live player per durable profile. Otherwise two shadow models overwrite one save slot.
            for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
            {
                if(*It==this||It->IsActorBeingDestroyed())continue;
                const auto* OtherPC=Cast<APlayerController>(It->GetOwner());
                if(!OtherPC||OtherPC->PlayerState!=*It)continue;
                FGuid OtherId=It->BoundProfileId;
                if(OtherPC->IsLocalController())
                    if(const auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())OtherId=Host->Snapshot().NetworkProfileId;
                if(OtherId==Guest.NetworkProfileId)
                {ClientProfileSyncRejected(TEXT("此角色档案已被房间内另一名玩家使用，请切换档案后重新加入"));return false;}
            }
            BoundProfileId=Guest.NetworkProfileId;
            if(const auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())
                for(FName Key:Session->RestoreGuestKeys(BoundProfileId))SessionDoorKeys.AddUnique(Key);
            SlotName=TEXT("ColdSteelMP_Profile_")+BoundProfileId.ToString(EGuidFormats::Digits);
            // Null-subsystem PIE player names change on reconnect. Bind durable
            // receipts to the isolated saved profile, never that temporary name.
            if(ShadowModel&&ShadowModel->Snapshot().NetworkProfileId!=BoundProfileId)ShadowModel=nullptr;
            auto* Session=GetGameInstance()->GetSubsystem<UColdSteelNetSessionSubsystem>();
            if(auto* Cached=Session?Session->RestoreGuestProfile(GetWorld(),BoundProfileId):nullptr)
            {
                // Never discard the last live state merely because logout could not write it.
                if(Cached->HasUnconfirmedTransactionSave())
                {BoundProfileId.Invalidate();ClientProfileSyncRejected(TEXT("此档案的交易保存结果待恢复，请主机保留存档并重启后再加入"));return false;}
                ShadowModel=Cached;bRestoreGuestAmmo=true;
                // Restore the saved resources before the upload merge reads the new pawn's components.
                ApplyShadowToServerPawn();
            }
            else if(UGameplayStatics::DoesSaveGameExist(SlotName,0))
            {
                auto* Stored=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(SlotName,0));
                if(!Stored||Stored->Profile.NetworkProfileId!=BoundProfileId)
                {
                    // An existing unreadable/mismatched host slot is evidence, not a new guest.
                    BoundProfileId.Invalidate();ClientProfileSyncRejected(TEXT("主机已有客机档案无法读取或身份不符，已保留文件，未用上传档案覆盖"));return false;
                }
                if(!ApplyGuestProfile(Stored->Profile)){BoundProfileId.Invalidate();return false;}
                bRestoreGuestAmmo=ShadowModel!=nullptr;
            }
        }
    }
    // Settle against the authority clock before comparing upload receipts. An
    // upload captured before expiry must not resurrect the consumed raw item.
    if(ShadowModel&&ShadowModel->RuntimePawn()&&ShadowModel->RuntimePawn()->HasAuthority())
        ShadowModel->SettleFoodSpoilage(true);
    if(ShadowModel&&ShadowModel->HasUnconfirmedTransactionSave())
    {ClientProfileSyncRejected(TEXT("交易保存结果待恢复，已停止覆盖主机档案"));return false;}
    UGameInstance* GI = GetGameInstance();
    UColdSteelStatusModel* HostModel = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!HostModel) return false;

    if (!ShadowModel)
    {
        auto FoodMigrated=Guest;
        if(bFromNetwork)
        {
            BlacksmithApprenticeship::NormalizeImportedProfile(FoodMigrated);
            CarpenterApprenticeship::NormalizeImportedProfile(FoodMigrated);
        }
        ColdSteelFood::RebaseProfile(FoodMigrated,ColdSteelFood::Clock(this));
        ShadowModel = HostModel->CreateShadowModel(FoodMigrated);
        if(!ShadowModel){ClientProfileSyncRejected(HostModel->ResultMessage());return false;}
        UE_LOG(LogTemp, Warning, TEXT("MPTEST shadow profile created: %s items=%d hp=%.0f"),
            *SlotName, Guest.Items.Num(), Guest.Health);
    }
    else
    {
        // Preserve server transactions; merge progression as coherent level/XP
        // pairs and cumulative attribute entitlement. Repeated uploads are idempotent.
        const FColdSteelProfile Prev = ShadowModel->Snapshot();
        FColdSteelProfile Adopted = Guest;
        Adopted.MountRoster=Prev.MountRoster;
        // If a guest upload carries items in a mount.<HorseId> bag whose horse is no longer present in the
        // server-authoritative MountRoster (e.g., stale client snapshot after a host-side release/roster race),
        // fall back to the authoritative inventory instead of rejecting the entire profile sync.
        bool bStaleMountBagUpload=false;
        if(Adopted.CampfireInventoryRevision==Prev.CampfireInventoryRevision)
        {
            for(const auto& Item:Adopted.Items)
            {
                FGuid BagMountId;
                if(Item.Place==ColdSteelWarehouse::Place && StableHorseAffixes::TryParseBagContainer(Item.Container,BagMountId))
                {
                    const auto* Horse=Adopted.MountRoster.Find(BagMountId);
                    if(!Horse || Horse->BagRows()<=0)
                    {
                        bStaleMountBagUpload=true;
                        break;
                    }
                }
            }
        }
        const auto FoodClock=ColdSteelFood::Clock(this);
        ColdSteelFood::RebaseProfile(Adopted,FoodClock);
        Adopted.Health=Prev.Health;
        // Uploads carry inventory intent, not authority health. An old upload
        // must neither heal a wounded pawn nor revive a pawn awaiting respawn.
        if(const auto* Pawn=GetPawn())
            if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>())Adopted.Health=Health->Health;
        const bool KeepServerPouch=bRestoreGuestAmmo||Adopted.CampfireInventoryRevision!=Prev.CampfireInventoryRevision;
        // Same-revision owner uploads can predate continuous bow upkeep. Keep
        // authority resources while prepared, then rely on the end checkpoint.
        const auto* UpkeepPawn=GetPawn();
        const auto* HeldSword=ShadowModel->Equipped();
        const auto* Offhand=ShadowModel->Equipped(ShadowModel->ActiveOffhandSlot());
        const bool HoldingTorch=(HeldSword&&ColdSteelInventory::IsWoodenTorch(*HeldSword))||
            (Offhand&&ColdSteelInventory::IsWoodenTorch(*Offhand));
        if(HoldingTorch&&(HasGenericMeleeBusy(UpkeepPawn)||IsQuickCombatExecuting(UpkeepPawn)))
        {
            Adopted.Stamina=Prev.Stamina;
            Adopted.StaminaRecoveryDelay=Prev.StaminaRecoveryDelay;
            Adopted.bSprintExhausted=Prev.bSprintExhausted;
        }
        if(UpkeepPawn&&HeldSword&&HeldSword->Definition==TEXT("ue_forged_steel_greatsword"))
        {
            const auto* Sword=UpkeepPawn->FindComponentByClass<URuneSwordComponent>();
            if(HasGenericMeleeBusy(UpkeepPawn)||(Sword&&(Sword->IsHeavyCharging()||Sword->IsNetworkHeavyReleaseWindowOpen(HeldSword->InstanceId))))
            {
                // A profile captured before a paid swing or during the windup can arrive later.
                Adopted.Stamina=Prev.Stamina;
                Adopted.StaminaRecoveryDelay=Prev.StaminaRecoveryDelay;
                Adopted.bSprintExhausted=Prev.bSprintExhausted;
            }
        }
        const auto* ElementHold=UpkeepPawn?UpkeepPawn->FindComponentByClass<UFPSElementalArrowComponent>():nullptr;
        const auto* RainHold=UpkeepPawn?UpkeepPawn->FindComponentByClass<UFPSMagicArrowRainComponent>():nullptr;
        const auto* ThunderHold=UpkeepPawn?UpkeepPawn->FindComponentByClass<UProductionToolComponent>():nullptr;
        if((ElementHold&&ElementHold->OwnsHoldResources())||(RainHold&&RainHold->HasPreparedArrow())||(ThunderHold&&ThunderHold->OwnsThunderCallResources()))
        {
            Adopted.Mana=Prev.Mana;Adopted.StarMarrowManaSpent=Prev.StarMarrowManaSpent;Adopted.MagicCrystalManaRestored=Prev.MagicCrystalManaRestored;Adopted.Stamina=Prev.Stamina;Adopted.StaminaRecoveryDelay=Prev.StaminaRecoveryDelay;Adopted.bSprintExhausted=Prev.bSprintExhausted;
            Adopted.SpellbookFocusManaLoss=Prev.SpellbookFocusManaLoss;Adopted.UppercutStaminaSpent=Prev.UppercutStaminaSpent;
            Adopted.OathStaminaRestored=Prev.OathStaminaRestored;
        }
        if(Adopted.CampfireInventoryRevision!=Prev.CampfireInventoryRevision || bStaleMountBagUpload)
        {
            // A profile sent before a host-committed wall repair still contains
            // the pre-purchase balance. Replaying it must not refund the fee.
            for(const auto& Receipt:Prev.CampfireWorldReceipts)
            {
                if(Receipt.Value>Adopted.CampfireInventoryRevision&&Receipt.Key.StartsWith(TEXT("VillageDefenses_")))
                {
                    Adopted.Souls=Prev.Souls;
                    break;
                }
            }
            Adopted.Items=Prev.Items;
            // Capacity and layout belong to the same authoritative inventory,
            // including extra pages allocated by an earlier footprint migration.
            Adopted.WarehousePages=Prev.WarehousePages;
            Adopted.WarehouseLayoutVersion=Prev.WarehouseLayoutVersion;
            Adopted.StoragePages=Prev.StoragePages;
            Adopted.ActiveWeaponSlot=Prev.ActiveWeaponSlot;Adopted.ActiveProductionTool=Prev.ActiveProductionTool;
            Adopted.AmmoPouch=Prev.AmmoPouch;
            Adopted.Mana=Prev.Mana;Adopted.StarMarrowManaSpent=Prev.StarMarrowManaSpent;Adopted.MagicCrystalManaRestored=Prev.MagicCrystalManaRestored;Adopted.Stamina=Prev.Stamina;
            Adopted.UppercutStaminaSpent=Prev.UppercutStaminaSpent;
            Adopted.OathStaminaRestored=Prev.OathStaminaRestored;
            Adopted.CampfireInventoryRevision=Prev.CampfireInventoryRevision;
        }
        ColdSteelProfileRecovery::NetworkSpells(Adopted,Prev);
        ColdSteelProfileRecovery::MartialCooldowns(Adopted,Prev);
        // Uppercut now commits on authority. A delayed owner profile cannot
        // shorten/reset its server cooldown or undo a confirmed release.
        Adopted.SwordUppercutCooldown=Prev.SwordUppercutCooldown;
        Adopted.SwordUppercutCooldownDuration=Prev.SwordUppercutCooldownDuration;
        Adopted.ChainSlashCooldown=Prev.ChainSlashCooldown;Adopted.ChainSlashCooldownDuration=Prev.ChainSlashCooldownDuration;
        Adopted.LeapStrikeCooldown=Prev.LeapStrikeCooldown;Adopted.LeapStrikeCooldownDuration=Prev.LeapStrikeCooldownDuration;
        Adopted.ShadowStepCooldown=Prev.ShadowStepCooldown;Adopted.ShadowStepCooldownDuration=Prev.ShadowStepCooldownDuration;
        Adopted.WhirlwindCooldown=Prev.WhirlwindCooldown;
        Adopted.WhirlwindCooldownDuration=Prev.WhirlwindCooldownDuration;
        Adopted.CampfireWorldReceipts=Prev.CampfireWorldReceipts;
        Adopted.BlacksmithApprenticeshipStage=Prev.BlacksmithApprenticeshipStage;
        Adopted.CarpenterApprenticeshipStage=Prev.CarpenterApprenticeshipStage;
        Adopted.ForgeJob=Prev.ForgeJob;Adopted.GunAssemblyJob=Prev.GunAssemblyJob;Adopted.WoodworkingJob=Prev.WoodworkingJob;Adopted.AlchemyJob=Prev.AlchemyJob;Adopted.EnhancementItem=Prev.EnhancementItem;
        // Uploads may move ordinary inventory, never duplicate or modify escrow.
        if(!Prev.EnhancementItem.InstanceId.IsEmpty())
            Adopted.Items.RemoveAll([&](const auto& Item){return Item.InstanceId==Prev.EnhancementItem.InstanceId;});
        Adopted.DungeonRun=Prev.DungeonRun;
        ColdSteelWoodQuality::PreserveAuthoritative(Adopted.Items,Prev.Items);
        ColdSteelForgeQuality::PreserveAuthoritative(Adopted.Items,Prev.Items);
        UColdSteelEnhancementSystem::PreserveAuthoritative(Adopted.Items,Prev.Items);
        ColdSteelAssemblyQuality::PreserveAuthoritative(Adopted.Items,Prev.Items);
        // Preserve age even when the inventory receipt is equal (moves/splits
        // can upload independently of the periodic authority settlement).
        for(auto& Item:Adopted.Items)
        {
            const auto* Previous=Prev.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;});
            if(Previous&&ColdSteelInventory::IsWoodenTorch(*Previous))
            {
                if(Item.Definition!=Previous->Definition){Item=*Previous;continue;}
                Item.TorchBurnedSeconds=Previous->TorchBurnedSeconds;
            }
            if(!Previous||ColdSteelFood::LifetimeDays(*Previous)<=0.)continue;
            if(Item.Definition!=Previous->Definition){Item=*Previous;continue;}
            // Food definitions have no client-authored processing fields. Keep
            // the server lifetime contract as well as its accumulated age.
            Item.Data=Previous->Data;
            if(FoodClock.Id.IsValid())
            {
                const double UploadedAge=ColdSteelFood::AgeDays(Item,FoodClock);
                if(UploadedAge<=ColdSteelFood::AgeDays(*Previous,FoodClock))
                {
                    // Preserve the exact birth representation of the existing
                    // batch instead of repeatedly rounding it through Stamp.
                    Item.FoodVersion=Previous->FoodVersion;Item.FoodClockId=Previous->FoodClockId;
                    Item.FoodSampleDay=Previous->FoodSampleDay;Item.FoodAgeDays=Previous->FoodAgeDays;
                }
                else ColdSteelFood::Stamp(Item,FoodClock,UploadedAge);
            }
        }
        if(!RebaseSuper90Upload(Adopted,Prev,KeepServerPouch)){SendSuper90Ammo(true);return false;}
        EnsurePistolAmmoIds();
        if(!RebasePistolUpload(Adopted,Prev,KeepServerPouch)){SendPistolAmmo();return false;}
        // A profile upload may have been captured before the focus-break RPC.
        if(Adopted.MagicCrystalManaRestored<Prev.MagicCrystalManaRestored)
            MagicCrystalMana::Merge(Adopted,Prev.MagicCrystalManaRestored,float(UColdSteelStatusModel::ResourceMaximum(Adopted,true)));
        Adopted.StarMarrowManaSpent=FMath::Clamp(Adopted.StarMarrowManaSpent,0.,Prev.StarMarrowManaSpent);
        Adopted.MergeStarMarrowSpend(Prev.StarMarrowManaSpent);
        SpellbookFocusMana::Merge(Adopted,Prev.SpellbookFocusManaLoss);
        UppercutStaminaReceipt::Merge(Adopted,Prev.UppercutStaminaSpent);
        Adopted.OathStaminaRestored=FMath::IsFinite(Adopted.OathStaminaRestored)?FMath::Clamp(Adopted.OathStaminaRestored,0.,Prev.OathStaminaRestored):0.;
        Adopted.MergeOathStamina(Prev.OathStaminaRestored,UColdSteelStatusModel::StaminaMaximum(Adopted,ShadowModel->StaminaSettings()));
        bool CurrencyChanged=false;FString CurrencyReason;
        // Server-side grant/debit watermarks are not client state. Overwriting
        // them here also prevents a forged watermark from suppressing rewards.
        Adopted.ServerSoulCredits=Prev.ServerSoulCredits;
        Adopted.ServerSoulDebits=Prev.ServerSoulDebits;
        if(!ColdSteelCurrency::Normalize(Adopted,CurrencyChanged,CurrencyReason) || !ColdSteelCurrency::MergeServerCredits(Adopted,Prev))return false;
        Adopted.Souls=FMath::Clamp<int64>(Adopted.Souls,0,1000000000ll);
        const double MaxHealth=UColdSteelStatusModel::ResourceMaximum(Adopted,false);
        const double MaxMana=UColdSteelStatusModel::ResourceMaximum(Adopted,true);
        const double MaxStamina=UColdSteelStatusModel::StaminaMaximum(Adopted,ShadowModel->StaminaSettings());
        Adopted.Health=FMath::Clamp(double(Adopted.Health),0.,MaxHealth);
        Adopted.Mana=FMath::Clamp(double(Adopted.Mana),0.,MaxMana);
        Adopted.Stamina=FMath::Clamp(double(Adopted.Stamina),0.,MaxStamina);
        // Ongoing survival is server-owned; inventory uploads must not refill or rewind it.
        Adopted.Infection=Prev.Infection;
        if(const auto* Pawn=GetPawn())if(const auto* I=Pawn->FindComponentByClass<UProgressiveInfectionComponent>())Adopted.Infection=I->GetState();
        Adopted.Survival=Prev.Survival;
        if(const auto* Character=Cast<AFPSGAMECharacter>(GetPawn()))
            if(const auto* Survival=Character->FindComponentByClass<UFPSSurvivalComponent>())Adopted.Survival=Survival->GetState();
        ColdSteelProfileMerge::Progression(Adopted,Prev);
        ColdSteelProfileMerge::OfferingUsage(Adopted,Prev);
        if(const auto* Pawn=GetPawn())
            if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>())
            {
                const float Maximum=float(UColdSteelStatusModel::ResourceMaximum(Adopted,false));
                // Equipment/attribute growth preserves missing HP, exactly as
                // local PersistState does, without trusting uploaded health.
                Adopted.Health=Health->IsDead()?0.f:FMath::Clamp(Health->Health+Maximum-Health->MaxHealth,0.f,Maximum);
            }
        // A respawn/revive replaces the pawn and refills the magazine client-side;
        // drop the old shot ledger so the first post-respawn shot is not billed
        // against the rounds the player died with.
        if(Prev.Health<=0.f&&Adopted.Health>0.f)
        {
            ServerGunLedgers.Reset();RegisteredPistolShots.Reset();M24Launches.Reset();LastM24LaunchSequence=0;
        GenericLaunches.Reset();LastGenericLaunchSequence=0;GenericLaunchPawn.Reset();GenericLaunchReadyAt=0.;GenericLaunchTokenAt=0.;GenericLaunchTokens=6.f;
        GenericMeleeReceipts.Reset();GenericMeleePawn.Reset();LastGenericMeleeSequence=0;GenericMeleeReadyAt=0.;
        AuthorityShotRecoveryPawn.Reset();AuthorityShotRecoveryUntil=0.;
            StopPistolAuthority();
            ServerComboStage=0;ServerComboSwingAt=-100.;ServerComboWeapon.Reset();
        }
        // Covers reconnect caches and the retained host inventory after revision
        // reconciliation. NetView projections must not perform this migration.
        bool FootprintChanged=false;FString FootprintReason;
        if(!ColdSteelInventory::MigrateAuthoredGridFootprints(Adopted,FootprintChanged,FootprintReason))
        {ClientProfileSyncRejected(FootprintReason);return false;}
        const bool TubeCapacityChanged=Adopted.CampfireInventoryRevision!=Prev.CampfireInventoryRevision;
        auto* ThunderTool=GetPawn()?GetPawn()->FindComponentByClass<UProductionToolComponent>():nullptr;
        FString ThunderReason;
        if(ThunderTool&&!ThunderTool->ValidateThunderEquipmentChange(Prev,Adopted,ThunderReason))
        {ClientProfileSyncRejected(ThunderReason);return false;}
        ShadowModel->AdoptNetMirror(Adopted);
        if(ThunderTool)ThunderTool->CommitThunderEquipmentChange(Adopted);
        if(TubeCapacityChanged)
        {
            RecordSuper90PouchChange(Prev,Adopted);
            RecordPistolPouchChange(Prev.AmmoPouch);
            for(auto& Pair:PistolReloads)Pair.Value.Active=false;
            // A magazine resize ends the old reload plan. The receipt waits for
            // this inventory revision on the owner before interrupting its pose.
            if(Super90Reload.Active){Super90Reload.Active=false;SendSuper90Ammo(true);}
        }
    }
    bRestoreGuestAmmo=false;
    ApplyShadowToServerPawn();
    ShadowModel->SettleFoodSpoilage(true);
    if(ShadowModel->HasUnconfirmedTransactionSave())
    {ClientProfileSyncRejected(TEXT("食物腐败保存未确认，保留服务器物品等待恢复"));return false;}
    SendSuper90Ammo();
    SendPistolAmmo();
    if(bFromNetwork&&GuestProfile.BlacksmithApprenticeshipStage!=ShadowModel->ProfileView().BlacksmithApprenticeshipStage)
        ClientBlacksmithLesson(BoundProfileId,ShadowModel->ProfileView().BlacksmithApprenticeshipStage);
    if(bFromNetwork&&GuestProfile.CarpenterApprenticeshipStage!=ShadowModel->ProfileView().CarpenterApprenticeshipStage)
        ClientCarpenterLesson(BoundProfileId,ShadowModel->ProfileView().CarpenterApprenticeshipStage);
    bServerDirty = true;
    ServerSaveTimer = 20.f;
    return true;
}

bool AColdSteelPlayerState::SanitizeGuestProfile(FColdSteelProfile& Profile,FString& OutReason) const
{
    UGameInstance* GI=GetGameInstance();
    UColdSteelStatusModel* Host=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Host){OutReason=TEXT("主机档案目录不可用");return false;}

    // Bound progression before structural validation. The host never accepts a
    // client's raw attribute/currency watermark as authority.
    if(Profile.Items.Num()>10000)
    {
        Profile.Items.SetNum(10000);
        UE_LOG(LogTemp,Warning,TEXT("MPTEST guest profile item cap trimmed upload"));
    }
    Profile.Level=FMath::Clamp(Profile.Level,1,10000);
    const int64 LevelNeed=(20ll+int64(Profile.Level)*20ll+int64(Profile.Level)*Profile.Level*12ll)*8ll;
    Profile.Experience=FMath::Clamp<int64>(Profile.Experience,0,FMath::Max<int64>(0,LevelNeed-1));
    const int64 PointCap=3ll*Profile.Level+100ll;
    Profile.Points=FMath::Clamp<int32>(Profile.Points,0,int32(FMath::Min<int64>(PointCap,1000000)));
    int64 AttributeTotal=0;
    for(auto& Pair:Profile.Attributes)
    {
        Pair.Value=FMath::Clamp(Pair.Value,0,999);
        AttributeTotal+=Pair.Value;
    }
    if(AttributeTotal>PointCap&&Profile.Attributes.Num()>0)
    {
        const int32 PerAttribute=int32(PointCap/Profile.Attributes.Num());
        for(auto& Pair:Profile.Attributes)Pair.Value=FMath::Clamp(Pair.Value,0,PerAttribute);
    }
    Profile.Souls=FMath::Clamp<int64>(Profile.Souls,0,1000000000ll);
    // Server grant/debit watermarks are never client state. Starting from zero
    // also stops a fresh upload from suppressing future server rewards.
    Profile.ServerSoulCredits=0;
    Profile.ServerSoulDebits=0;
    if(!FMath::IsFinite(Profile.Stamina))Profile.Stamina=0.f;
    if(!FMath::IsFinite(Profile.Mana))Profile.Mana=0.f;
    if(!FMath::IsFinite(Profile.StarMarrowManaSpent)||Profile.StarMarrowManaSpent<0.||Profile.StarMarrowManaSpent>1.e12)Profile.StarMarrowManaSpent=0.;
    if(!FMath::IsFinite(Profile.Health))Profile.Health=0.f;
    Profile.Stamina=FMath::Clamp(Profile.Stamina,0.f,
        float(Host->StaminaMaximum(Profile,Host->StaminaSettings())));
    Profile.Mana=FMath::Clamp(Profile.Mana,0.f,
        float(Host->ResourceMaximum(Profile,true)));
    if(!ShadowModel)Profile.CampfireInventoryRevision=0;

    // Fresh profiles can bring legitimate personal escrow from another world.
    // Existing authority profiles replace uploads below; normalize new seeds just
    // like ordinary items, without granting an extra copy in inventory.
    if(ShadowModel)Profile.EnhancementItem=ShadowModel->Snapshot().EnhancementItem;
    if(!Profile.EnhancementItem.InstanceId.IsEmpty())
    {
        const auto* Enhancement=GI->GetSubsystem<UColdSteelEnhancementSystem>();
        if(!Host->SanitizeNetworkItem(Profile.EnhancementItem)||!Enhancement||!Enhancement->Supports(Profile.EnhancementItem))
        {OutReason=TEXT("工作台暂存武器无效，请恢复原档案后重试");return false;}
        Profile.Items.RemoveAll([&](const auto& Item){return Item.InstanceId==Profile.EnhancementItem.InstanceId;});
    }
    TSet<FString> KeptIds;
    int32 Dropped=0;
    for(int32 Index=Profile.Items.Num()-1;Index>=0;--Index)
    {
        FColdSteelItem& Item=Profile.Items[Index];
        if(!Host->SanitizeNetworkItem(Item)||KeptIds.Contains(Item.InstanceId))
        {
            Profile.Items.RemoveAt(Index);
            ++Dropped;
            continue;
        }
        KeptIds.Add(Item.InstanceId);
    }
    if(Dropped>0)
        UE_LOG(LogTemp,Warning,TEXT("MPTEST guest profile dropped %d invalid item instances"),Dropped);

    // Legacy currency items are normalized into Souls. Bound their contribution
    // so a forged stack cannot bypass the balance cap during Normalize.
    int64 CurrencyBudget=FMath::Max<int64>(0,1000000000ll-Profile.Souls);
    for(int32 Index=Profile.Items.Num()-1;Index>=0;--Index)
    {
        FColdSteelItem& Item=Profile.Items[Index];
        if(!ColdSteelCurrency::IsCurrency(Item.Definition))continue;
        if(CurrencyBudget<=0)
        {
            KeptIds.Remove(Item.InstanceId);
            Profile.Items.RemoveAt(Index);
            continue;
        }
        Item.Count=FMath::Min<int64>(Item.Count,CurrencyBudget);
        Item.StackMax=FMath::Max(Item.StackMax,Item.Count);
        CurrencyBudget-=Item.Count;
    }
    for(FString& Id:Profile.Hotbar)
        if(!Id.IsEmpty()&&!KeptIds.Contains(Id))Id.Reset();
    // Resources are bounded by the same server-side stat formula the pawn uses.
    // Uploaded Health/Mana must not start a first-join shadow above its maximum.
    Profile.Health=FMath::Clamp(Profile.Health,0.f,float(Host->ResourceMaximum(Profile,false)));
    Profile.Mana=FMath::Clamp(Profile.Mana,0.f,float(Host->ResourceMaximum(Profile,true)));
    // Preserve the saved row stride until layout migration. Validating an old
    // 6x8 expedition compartment as 8x6 first can reject a legitimate guest
    // before CreateShadowProfile gets a chance to migrate it. Items above are
    // already sanitized; the shared migration validates both layouts atomically.
    // Skill tree (2026-11-15): learned skills and specialization ranks must obey the tree rules.
    ColdSteelSkillTree::Sanitize(Profile);
    bool LayoutChanged=false;
    return ColdSteelInventory::MigrateAuthoredGridFootprints(Profile,LayoutChanged,OutReason);
}

void AColdSteelPlayerState::GrantSessionDoorKey(FName Key)
{
    if(!HasAuthority()||Key.IsNone())return;
    SessionDoorKeys.AddUnique(Key);ForceNetUpdate();
    if(auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())Session->RememberGuestKeys(BoundProfileId,SessionDoorKeys);
}
void AColdSteelPlayerState::ClientProfileSyncRejected_Implementation(const FString& Reason)
{
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->PostNotice(TEXT("角色档案未接入"),Reason);
}

