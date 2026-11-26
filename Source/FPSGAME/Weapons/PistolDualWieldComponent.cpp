#include "PistolDualWieldComponent.h"
#include "PistolDualEquipmentPrivate.h"
using namespace DualPistolEquipment;
#include "WeaponShotNoise.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "DualPistolReloadTiming.h"
#include "FullAutoTrigger.h"
#include "TacticalDeviceVariants.h"
#include "G18WeaponAssets.h"
#include "PitViper2011WeaponAssets.h"
#include "LonePistolTwoHandAssets.h"
#include "PitViper2011SICompensator.h"
#include "Staff/StaffCatalog.h"
#include "Kukri/KukriWeaponComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelPickupStudio.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "FPSWeaponFXComponent.h"
#include "FPSBallisticsComponent.h"
#include "WeaponStatEvaluation.h"
#include "ColdSteelEnchantmentCombat.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "DanWesson715WeaponAssets.h"
#include "RSH12WeaponAssets.h"
#include "RSH12OpticAssets.h"
#include "RSH12HeavyGrip.h"
#include "ASH12WeaponAssets.h"
#include "DanWesson715FittedParts.h"
#include "M1911MagazineVisual.h"
#include "M1911WeaponAssets.h"
#include "PistolAudioAssets.h"
#include "WeaponReloadStages.h"
#include "TacticalDeviceComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "QuickCombatRecovery.h"
#include "DualPistolQuickCombatMotion.h"
#include "../Skills/QuickCombatPistolMotion.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

UPistolDualWieldComponent::UPistolDualWieldComponent()
{
    PrimaryComponentTick.bCanEverTick=false;
    Hands.SetNum(2);
}

bool UPistolDualWieldComponent::HandBusy(int32 Index) const
{
    if(!bActive||Index<FirstHand()||!Hands.IsValidIndex(Index))return false;
    const auto& H=Hands[Index];
    return H.Reloading||H.Action||H.Held||H.Pending;
}
bool UPistolDualWieldComponent::LeftBusy() const {return HandBusy(1);}

bool UPistolDualWieldComponent::InputAvailable() const
{
    if(!Player || !bActive || Player->IsTraversing() || IsQuickCombatActive())return false;
    if(UFPSPotionUseComponent::BlocksWeaponAttack(Player))return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}

void UPistolDualWieldComponent::StartAction(int32 Index,const FString& Name,float Rate)
{
    if(Index==1){MeleeReleaseClip=nullptr;MeleeReleaseGrip=nullptr;}
    auto& H=Hands[Index];H.Action=H.Clips.FindRef(Name);H.ActionTime=0;H.ActionRate=Rate;H.ActionStarted=GetWorld()->GetTimeSeconds();H.PlayedCues.Empty();
    if(Name==TEXT("equip")||Name==TEXT("equip_empty"))H.ActionRate*=static_cast<float>(H.Stats.EquipRate())*LightningHaste::ActionSpeed(GetOwner());
    H.ActionBlendStarted=H.ActionStarted;
    H.ActionPoseProfile=PistolPoseFamily(Name);
    if(Player->IsLoneLeftHandRig() && Name!=TEXT("fire") && Name!=TEXT("fire_last"))
        Player->SetAimingState(false);
}
bool UPistolDualWieldComponent::IsSingleActionCocking() const
{
    // Retained API for existing callers; all current revolvers use double action.
    return false;
}
void UPistolDualWieldComponent::StopAction(int32 Index,bool NetworkCancel)
{
    auto& H=Hands[Index];
    if(NetworkCancel)CaptureMeleeReleasePose(Index);
    if(NetworkCancel&&H.Reloading&&GetNetMode()==NM_Client)
        if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>())PS->CancelPistolReload(H.Item.InstanceId);
    if(H.Reloading||!H.Voices.IsEmpty())if(auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>())Body->ReportGunMechanicalStop(Index);
    H.Action=nullptr;H.Reloading=H.ReloadQueued=false;H.PendingAmmoType.Reset();
    for(auto& Voice:H.Voices)if(IsValid(Voice))Voice->Stop();H.Voices.Empty();
}
void UPistolDualWieldComponent::CancelInputs()
{
    for(auto& H:Hands)H.Held=H.Pending=false;
}

void UPistolDualWieldComponent::InterruptReloads()
{
    for(int32 Side=0;Side<Hands.Num();++Side)if(Hands[Side].Reloading)StopAction(Side);
}

void UPistolDualWieldComponent::TryCowboyReload()
{
    if(!bActive || !Profile)return;
    // Main then offhand share one pouch. Each successful transaction refreshes
    // both hand counters before the next hand calculates its remaining reserve.
    for(int32 Side=FirstHand();Side<Hands.Num();++Side)
    {
        const FString WeaponId=Hands[Side].Item.InstanceId;
        if(Profile->ReloadCowboyPistol(WeaponId,Hands[Side].Stats.Capacity)<=0)continue;
        if(Hands[Side].Reloading)StopAction(Side);
        auto& H=Hands[Side];
        H.ReloadQueued=false;
        H.PendingAmmoType.Reset();
        if(auto* Sound=H.Sounds.FindRef(H.Revolver?TEXT("SingleOpen"):TEXT("MagInsert")).Get())
        {
            UGameplayStatics::PlaySound2D(this,Sound,.8f);
            if(auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>())Body->ReportGunMechanical(Side,Sound,.8f);
        }
    }
}

bool UPistolDualWieldComponent::IsEquipping() const
{
    if(!bActive)return false;
    for(int32 Side=FirstHand();Side<2;++Side)
        if(Hands[Side].Action && (Hands[Side].Action==Hands[Side].Clips.FindRef(TEXT("equip"))
            || Hands[Side].Action==Hands[Side].Clips.FindRef(TEXT("equip_empty"))))return true;
    return false;
}

void UPistolDualWieldComponent::InterruptActions()
{
    CancelInputs();
    for(int32 Side=0;Side<Hands.Num();++Side)StopAction(Side);
}

void UPistolDualWieldComponent::PrepareSingleInspect()
{
    // Single-weapon setup runs again after leaving dual wield (LoadHand clears
    // the old clip map). Keep this small variant alive without loading on L.
    const auto* OwnerPlayer=Cast<AFPSGAMECharacter>(GetOwner());
    Hands[0].Clips.Add(TEXT("single_inspect_empty"),LoadObject<UAnimSequence>(nullptr,*(OwnerPlayer && OwnerPlayer->IsPitViperWeapon() ? PitViper2011WeaponAssets::AnimationPath(TEXT("inspect_empty")) : OwnerPlayer && OwnerPlayer->IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("inspect_empty")) : M1911WeaponAssets::AnimationPath(TEXT("inspect_empty")))));
}

UAnimSequence* UPistolDualWieldComponent::SingleEmptyInspect() const
{
    return Hands[0].Clips.FindRef(TEXT("single_inspect_empty"));
}

bool UPistolDualWieldComponent::IsQuickCombatActive() const
{
    return bActive && Player && Player->QuickCombatPistol
        && Player->QuickCombatPistol->GetStyle()==(bOffhandOnly?EQuickCombatStyle::StaffOffhandPistol:EQuickCombatStyle::DualPistol)
        && Player->QuickCombatPistol->IsOccupyingLeftHand();
}

bool UPistolDualWieldComponent::IsQuickCombatClip(int32 Index) const
{
    const auto& H=Hands[Index];
    if(!H.Action)return false;
    for(const auto& Clip:H.Clips)
        if(Clip.Key.StartsWith(TEXT("quickcombat")) && H.Action==Clip.Value)return true;
    return false;
}

FString UPistolDualWieldComponent::QuickCombatClipKind(int32 Side,bool LeftStrike) const
{
    const auto& H=Hands[Side];
    FString Kind=LeftStrike?TEXT("quickcombat_left"):TEXT("quickcombat");
    const auto* Instance=Player?Player->GetGameInstance():nullptr;
    const auto* Gunsmith=Instance?Instance->GetSubsystem<UGunsmithSystem>():nullptr;
    if(Gunsmith)
    {
        const auto Parts=Gunsmith->Installed(H.Item);
        const FString Optic=Parts.FindRef(TEXT("optic")),Muzzle=Parts.FindRef(TEXT("muzzle")),Tactical=Parts.FindRef(TEXT("tactical"));
        // Every profile retains the full recovery revolution. Long cans use
        // the most canted axis, including when an optic/tactical is also fitted.
        if(Muzzle==TEXT("true") || Muzzle==TEXT("tactical_suppressor") || Muzzle==TEXT("multi_caliber_suppressor") ||
           (H.Item.Definition==RSH12WeaponAssets::Definition && Muzzle==TEXT("rsh12_heavy_suppressor")))Kind+=TEXT("_long");
        else if(Optic==TEXT("holographic") || Optic==TEXT("panoramic_red_dot") || Optic==TEXT("eoth_holographic") || Optic==TEXT("thermal_scope")
            || (H.Item.Definition==RSH12WeaponAssets::Definition && RSH12OpticAssets::IsSquare(Optic))
            || TacticalDeviceVariants::IsLaser(Tactical) || Tactical==TEXT("flashlight"))Kind+=TEXT("_fitted");
    }
    if(!H.Revolver && H.Rounds==0)Kind+=TEXT("_empty");
    return Kind;
}

const TCHAR* UPistolDualWieldComponent::QuickCombatBlockReason() const
{
    if(!bActive || !Player || !Player->QuickCombatPistol)return TEXT("双持/副手控制器未就绪");
    if(IsSingleActionCocking())return TEXT("RSH-12正在拨回击锤");
    if(!Player->CanStartQuickCombatPriority())return TEXT("切换武器或输入不可用");
    const bool LeftStrike=bOffhandOnly||DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial()+1u)==1;
    UAnimSequence* Clips[2]={nullptr,nullptr};
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        const auto& H=Hands[Side];
        if(!H.Mesh || !H.Anim)return TEXT("单手视模/动画实例缺失");
        const FString Kind=QuickCombatClipKind(Side,LeftStrike);
        Clips[Side]=H.Clips.FindRef(Kind);
        if(!Clips[Side])return TEXT("当前出手侧/空仓近战动画缺失");
    }
    if(!bOffhandOnly&&!FMath::IsNearlyEqual(Clips[0]->GetPlayLength(),Clips[1]->GetPlayLength(),.001f))return TEXT("左右近战动画时长不一致");
    return nullptr;
}

bool UPistolDualWieldComponent::BeginQuickCombat()
{
    if(const TCHAR* Reason=QuickCombatBlockReason())
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombatDual] 拒绝=%s 单持状态=%d 右=%s/%.3f/换弹%d 左=%s/%.3f/换弹%d"),
            Reason,Player?int32(Player->GetWeaponState()):-1,
            *GetNameSafe(Hands[0].Action),Hands[0].ActionTime,Hands[0].Reloading,
            *GetNameSafe(Hands[1].Action),Hands[1].ActionTime,Hands[1].Reloading);
        return false;
    }
    FString Kinds[2];
    UAnimSequence* Clips[2]={nullptr,nullptr};
    const bool LeftStrike=bOffhandOnly||DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial()+1u)==1;
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        const auto& H=Hands[Side];
        Kinds[Side]=QuickCombatClipKind(Side,LeftStrike);
        Clips[Side]=H.Clips.FindRef(Kinds[Side]);
    }
    Player->InterruptActionsForPriority(false);
    Player->ExitSprintForWeapon();
    if(bOffhandOnly)Player->QuickCombatPistol->ConfigureForStaffOffhandPistol(Clips[1]->GetPlayLength());
    else Player->QuickCombatPistol->ConfigureForClipLength(Clips[0]->GetPlayLength(),true);
    if(!Player->QuickCombatPistol->BeginAction())return false;
    const double Started=GetWorld()->GetTimeSeconds();
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        // Pending mechanical reload state lives on the item and is resumed
        // after melee; the interrupted exchange itself is never queued again.
        const bool Queued=Hands[Side].ReloadQueued;
        StopAction(Side);Hands[Side].ReloadQueued=Queued;
        StartAction(Side,Kinds[Side]);
        Hands[Side].ActionStarted=Started;
        Pose(Side,0.f);
    }
    UE_LOG(LogTemp,Log,TEXT("[QuickCombatDual] 开始 主攻=%s 右=%s 左=%s"),
        LeftStrike?TEXT("左"):TEXT("右"),*GetNameSafe(Clips[0]),*GetNameSafe(Clips[1]));
    return true;
}

bool UPistolDualWieldComponent::GetQuickCombatStrikeProbe(FVector& OutOrigin,float ContactTime)
{
    if(!IsQuickCombatActive())return false;
    // Resolve both meshes at the shared contact frame before tracing, even if
    // this frame crossed 0.18 s. Only the current striking hand supplies a hit.
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        auto& H=Hands[Side];
        if(!IsQuickCombatClip(Side) || !H.Mesh || !H.Anim)return false;
        H.ActionTime=ContactTime;
        Pose(Side,0.f);
        H.Mesh->TickAnimation(0.f,false);
        H.Mesh->RefreshBoneTransforms();
    }
    const int32 Strike=bOffhandOnly?1:DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial());
    const auto* Mesh=Hands[Strike].Mesh.Get();
    if(bTwoHandedLone&&Mesh)
    {
        // This source is the single-pistol downward grip bash, with exchanged
        // hand roles, not the akimbo fist strike's transverse contact.
        OutOrigin=Mesh->GetSocketLocation(TEXT("hand_l"))
            +Player->FirstPersonCamera->GetComponentQuat().RotateVector(QuickCombatPistolMotion::GripPointOffset());
        return true;
    }
    const FName ContactBone=Strike?TEXT("middle_01_l"):TEXT("middle_01_r");
    // This transverse whip contacts with the gun-holding fist. Sample the
    // anatomical knuckle instead of the old downward bash's camera-Z offset.
    if(!Mesh || Mesh->GetBoneIndex(ContactBone)==INDEX_NONE)return false;
    OutOrigin=Mesh->GetSocketLocation(ContactBone);
    return true;
}
void UPistolDualWieldComponent::Trigger(int32 Index,bool Pressed)
{
    if(!bActive || Index<FirstHand() || Index>=2)return;
    auto& H=Hands[Index];
    if(!Pressed){H.Held=H.Pending=false;return;}
    if(!InputAvailable() || (IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition && H.Item.Definition!=PitViper2011WeaponAssets::Definition) || (Index==1 && Player->IsCastBlockingLeftHandAction()))return;
    if(!H.Held)H.Pending=true;H.Held=true;
    if(Index==1&&IsMeleePairBlocked())return;
    Player->ExitSprintForWeapon();
    if(H.Action==H.Clips.FindRef(TEXT("equip")))StopAction(Index);
    TryFire(Index);
}
int32 UPistolDualWieldComponent::Reserve(int32 Index) const
{
    return Profile?Profile->AmmoCountFor(Hands[Index].Item):0;
}
bool UPistolDualWieldComponent::InfiniteReserve(int32 Index) const
{return Player&&Profile&&Player->HasInfiniteReserveAmmoFor(Profile->AmmoDefinitionFor(Hands[Index].Item));}
void UPistolDualWieldComponent::SyncInventory(TArray<FColdSteelItem>& Items) const
{
    if(!bActive)return;
    for(int32 Side=FirstHand();Side<2;++Side)for(auto& I:Items)if(I.InstanceId==Hands[Side].Item.InstanceId)
    {
        const auto& H=Hands[Side];
        I.VirtualMagazineAmmo=FMath::Clamp(I.VirtualMagazineAmmo-FMath::Max(0,I.Magazine-H.Rounds),0,H.Rounds);
        I.Magazine=H.Rounds;
        if(H.Revolver)
        {
            TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O);
            if(O){O->SetNumberField(TEXT("revolver_case_count"),H.Cases);I.Data.Reset();FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));}
        }
    }
}

float UPistolDualWieldComponent::SampleActionTime(int32 Index) const
{
    const auto& H=Hands[Index];
    if(!H.Action)return H.ActionTime;
    float Time=FMath::Max(0.f,float(GetWorld()->GetTimeSeconds()-H.ActionStarted)*H.ActionRate);
    if(H.Reloading && H.SourceLength>0.f && !bTwoHandedLone)
    {
        const float Length=FMath::Max(.001f,H.Action->GetPlayLength());
        Time=DualPistolReloadTiming::SourceTime(Time/Length*H.SourceLength,H.Revolver,H.ReloadSpeedloader)
            /H.SourceLength*Length;
    }
    return FMath::Max(H.ActionTime,Time);
}

void UPistolDualWieldComponent::Advance(float Delta)
{
    AdvanceMeleePair(Delta);
    if(!bActive)return;
    Clock+=Delta;
    UpdateAimTarget(Delta);
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();FHitResult Wall;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DualPistolNearWall),false,Player);
    const bool Close=GetWorld()->LineTraceSingleByChannel(Wall,Eye,Eye+Player->FirstPersonCamera->GetForwardVector()*80.f,ECC_Visibility,Query);
    const float WallTarget=Close?1.f-FMath::Clamp((Wall.Distance-25.f)/55.f,0.f,1.f):0.f;
    Player->NearWallAlpha=FMath::FInterpTo(Player->NearWallAlpha,WallTarget,Delta,12.f);
    // The character retains the last grounded phase through slide/jump. Reading
    // the audio clock here would pick up its airborne partial-step reset.
    Phase=Player->M4SprintPhase;
    // Hold the last running stroke during recovery. The footstep clock resets
    // its partial step when stationary; that reset must not flip the raised guns.
    if(Player->IsSprinting() && !Player->bWeaponJumpAirborne && Player->GetCharacterMovement()->IsMovingOnGround() && Player->HorizontalSpeed()>15.f)
        SprintPhase=Phase;
    if(!InputAvailable())
    {
        CancelInputs();
        // Menu entry interrupts reload presentation through SuspendWeaponForMenu.
        // Traversal and death also release these per-hand action clocks.
        if(Player->IsTraversing())for(int32 Side=0;Side<2;++Side)StopAction(Side);
        if(const auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H && H->IsDead())for(int32 Side=0;Side<2;++Side)StopAction(Side);
    }
    auto* Bash=Player->QuickCombatPistol.Get();
    if(bActive && Bash && Bash->GetStyle()==(bOffhandOnly?EQuickCombatStyle::StaffOffhandPistol:EQuickCombatStyle::DualPistol))
    {
        if(IsQuickCombatActive() && ((!bOffhandOnly&&!IsQuickCombatClip(0)) || !IsQuickCombatClip(1)))Bash->Cancel();
        const float SinceStart=float(FMath::Max(0.0,GetWorld()->GetTimeSeconds()-Hands[FirstHand()].ActionStarted));
        Bash->AdvanceAction(IsQuickCombatActive()?FMath::Min(Delta,SinceStart):Delta);
        Player->RefreshQuickCombatCamera();
    }
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        // Bloom follows the single-weapon contract: rise per shot, recover only
        // after the hand actually stops firing. The old continuous 0.028/s decay
        // outran the 0.003 rise at both pistol cadences (0.18 s and 0.32 s), so
        // sustained fire could never open the cone and the reticle only blipped
        // per shot. The hold scales with this hand's own cadence, so a fast pistol
        // and a slow revolver both reach full bloom in a few seconds of fire.
        auto& H=Hands[Side];
        if(Side==1 && H.Reloading && Player->IsCastBlockingLeftHandAction())StopAction(Side);
        const float Hold=Player->IsLoneLeftHandRig()?.18f:FMath::Max(.12f,float(H.Stats.Interval)*DualPistolSpread::BloomHold);
        const float Recovery=FMath::Clamp(float(GetWorld()->GetTimeSeconds()-H.LastShot-Hold),0.f,Delta);
        H.Bloom=FMath::Max(0.f,H.Bloom-Recovery*DualPistolSpread::BloomRecovery);
        if(IsQuickCombatClip(Side))
        {
            if(IsQuickCombatActive())H.ActionTime=Bash->GetActionAge();
            else
            {
                const bool Queued=H.ReloadQueued;StopAction(Side);H.ReloadQueued=Queued;
            }
        }
        else if(H.Action)
        {
            const float Previous=H.ActionTime/FMath::Max(.001f,H.Action->GetPlayLength())*H.SourceLength;
            H.ActionTime=SampleActionTime(Side);
            if(H.Reloading)AdvanceReload(Side,Previous);
            if(H.Action && H.ActionTime>=H.Action->GetPlayLength())
            {
                const bool Queued=H.ReloadQueued;StopAction(Side,false);H.ReloadQueued=Queued;
            }
        }
        if(InputAvailable() && !Player->IsChoosingAmmo() && !H.Action && (H.ReloadQueued || WeaponReloadStages::NeedsCycle(H.Item)
            || (H.Rounds==0 && (InfiniteReserve(Side)||Reserve(Side)>0))))BeginReload(Side);
        if(H.Automatic)
        {
            // Preserve this hand's cadence across variable frame times, with
            // bounded catch-up. Action gates remain owned by TryFire.
            for(int32 Shot=0;Shot<4;++Shot)
            {
                const double Before=H.NextShot;TryFire(Side);
                if(H.NextShot==Before || !H.Held || H.Reloading)break;
            }
        }
        else TryFire(Side);
        if(Side==1 && Player->IsLoneLeftHandRig())
        {
            const bool Fire=H.Action && (H.Action==H.Clips.FindRef(TEXT("fire")) || H.Action==H.Clips.FindRef(TEXT("fire_last")));
            Player->SetAimingState(Player->bAimHeld && (!H.Action || Fire) && InputAvailable()
                && !Player->IsSprinting() && !Player->IsWeaponBusyForAim());
        }
        Pose(Side,Delta);
    }
    if(!bOffhandOnly || Player->IsLoneLeftHandRig())
    {
        const int32 Side=bOffhandOnly?1:0;
        Player->MagazineAmmo=Hands[Side].Rounds;Player->RevolverCaseCount=Hands[Side].Cases;Player->ReserveAmmo=Reserve(Side);
    }
}

void UPistolDualWieldComponent::RefreshNetworkAmmo(UColdSteelStatusModel* Model)
{
    if(!bActive||!Player||!Model)return;
    for(int32 Side=FirstHand();Side<Hands.Num();++Side)
    {
        auto& H=Hands[Side];const auto* Gun=Model->FindItem(H.Item.InstanceId);if(!Gun)continue;
        H.Item=*Gun;H.Rounds=Gun->Magazine;
        H.Cases=H.Revolver?FMath::Clamp(int32(ColdSteelInventory::Number(*Gun,TEXT("revolver_case_count"),H.Rounds)),H.Rounds,H.Stats.Capacity):H.Rounds;
    }
    if(!bOffhandOnly||Player->IsLoneLeftHandRig())
    {
        const int32 Side=bOffhandOnly?1:0;Player->MagazineAmmo=Hands[Side].Rounds;
        Player->RevolverCaseCount=Hands[Side].Cases;Player->ReserveAmmo=Reserve(Side);
    }
}

void UPistolDualWieldComponent::FinishNetworkReload(const FString& Instance)
{
    for(int32 Side=FirstHand();Side<Hands.Num();++Side)
        if(Hands[Side].Item.InstanceId==Instance&&Hands[Side].Reloading)StopAction(Side,false);
}

void UPistolDualWieldComponent::Pose(int32 Index,float Delta)
{
    auto& H=Hands[Index];if(!H.Mesh || !H.Anim)return;
    H.Anim->GripProfile=bTwoHandedLone?H.PoseProfiles.FindRef(H.LoneGripFamily).Get():
        H.Action?H.PoseProfiles.FindRef(H.ActionPoseProfile).Get():nullptr;
    if(!bTwoHandedLone && !H.Anim->GripProfile && H.Item.Definition==RSH12WeaponAssets::Definition)H.Anim->GripProfile=H.PoseProfiles.FindRef(TEXT("base")).Get();
    // Consumables lower the equipped left rig before hiding its weapon, then
    // return to that same lowered grip before raising it back into view.
    const bool Cast=Player->IsCastingWithLeftHand() && !IsQuickCombatActive();
    const auto* Consumable=Index==1?Player->FindComponentByClass<UFPSPotionUseComponent>():nullptr;
    const bool Stowing=Consumable&&Consumable->IsStowingOffhand();
    const float LowerWeight=Stowing?Consumable->OffhandLowerWeight():0.f;
    const bool HideWeapon=Stowing?Consumable->IsOffhandWeaponHidden():Cast;
    const bool Visible=bActive && !Player->IsTraversing();
    H.Mesh->SetVisibility(Visible);
    if(Index==1)
    {
        if(HideWeapon)H.Mesh->HideBoneByName(TEXT("WPN_root"),EPhysBodyOp::PBO_None);
        else H.Mesh->UnHideBoneByName(TEXT("WPN_root"));
        // The two-hand variant releases its support arm while the left hand
        // casts and the gun is hidden. Consumables keep their own hand overlay.
        if(bTwoHandedLone&&Cast)H.Mesh->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
        else H.Mesh->UnHideBoneByName(TEXT("clavicle_r"));
        for(auto& C:LeftAttachments)if(C)C->SetVisibility(Visible && !HideWeapon);
        if(H.Tactical)H.Tactical->SetPresentationHidden(HideWeapon || !Visible);
    }
    const bool Running=Player->IsSprinting() && !Player->bWeaponJumpAirborne && Player->GetCharacterMovement()->IsMovingOnGround()
        && Player->HorizontalSpeed()>15.f && !Player->IsSliding() && !H.Action && !Cast;
    // Finite ease-in/out: lift over 0.24 s and settle within the existing
    // sprint-to-fire window. An interrupted lift resumes from its current pose.
    const float BlendDuration=Running?.24f:FMath::Max(.01f,FMath::Min(.16f,Player->SprintToFireDuration));
    H.SprintBlend=FMath::FInterpConstantTo(H.SprintBlend,Running?1.f:0.f,Delta,LightningHaste::ActionSpeed(GetOwner())/BlendDuration);
    const float U=H.SprintBlend;
    H.Sprint=U*U*U*(U*(U*6.f-15.f)+10.f);
    const bool Empty=!H.Revolver && (H.Rounds==0 || WeaponReloadStages::NeedsCycle(H.Item));
    H.Anim->IdleClip=H.Clips.FindRef(Empty?TEXT("idle_empty"):TEXT("idle"));H.Anim->AimClip=H.Anim->IdleClip;
    H.Anim->AimAlpha=0;H.Anim->BaseTime=Clock;
    H.Anim->SprintClip=H.Clips.FindRef(Empty?TEXT("sprint_empty"):TEXT("sprint"));
    H.Anim->SprintTime=H.Anim->SprintClip?SprintPhase/(2.f*PI)*H.Anim->SprintClip->GetPlayLength():0.f;
    H.Anim->SprintAlpha=H.Sprint;
    H.Anim->ActionClip=H.Action;H.Anim->ActionTime=H.ActionTime;
    const float BlendAge=float(GetWorld()->GetTimeSeconds()-H.ActionBlendStarted)*H.ActionRate;
    const bool FireAction=H.Action && (H.Action==H.Clips.FindRef(TEXT("fire")) || H.Action==H.Clips.FindRef(TEXT("fire_last")));
    // Match the single-hand fire entrance so the 12 ms slide impulse remains
    // visible while each hand retains its independent aim and recoil clocks.
    const float BlendIn=FireAction && H.Item.Definition==PitViper2011WeaponAssets::Definition?.008f:.025f;
    H.Anim->ActionAlpha=H.Action?FMath::Min(FMath::Clamp(BlendAge/BlendIn,0.f,1.f),FMath::Clamp((H.Action->GetPlayLength()-H.ActionTime)/.035f,0.f,1.f)):0;
    const bool QuickAction=IsQuickCombatClip(Index);
    if(QuickAction)H.Anim->ActionAlpha=FMath::Min(FMath::Clamp(H.ActionTime/.025f,0.f,1.f),
        bTwoHandedLone?FMath::Clamp((H.Action->GetPlayLength()-H.ActionTime)/.025f,0.f,1.f):
        QuickCombatRecovery::RemainingWeight(H.ActionTime,H.Action->GetPlayLength(),DualPistolQuickCombatMotion::IdleHandoffStart));
    ApplyMeleeReleasePose(Index);
    H.Anim->bDualPistolAim=true;H.Anim->DualPistolSide=Index;
    H.Anim->DualPistolAimTargetWorld=AimTargetWorld;
    const float LeftAimWeight=(Index!=1?1.f:(Stowing?1.f-LowerWeight:(Cast?0.f:1.f)))
        *(Index==1&&IsMeleePair()?1.f-MeleeAvoidance:1.f);
    const bool Lone=Index==1 && Player->IsLoneLeftHandRig();
    // A single rigid ADS frame owns arm + weapon. Convergence fades by exactly
    // the same weight; firing retains ADS while reload/equip/strike release it.
    if(Lone && !bLoneSightCalibrated)ConfigureLoneSight();
    const float ActionRelease=H.Action && !FireAction?1.f-H.Anim->ActionAlpha:1.f;
    const float ADS=Lone && bLoneSightCalibrated
        ?FMath::Clamp(Player->WeaponADSFactor,0.f,1.f)*ActionRelease*(1.f-H.Sprint)
            *(1.f-Player->NearWallAlpha)*(1.f-Player->DodgePresentationWeight())*LeftAimWeight:0.f;
    H.Anim->LonePistolADSAlpha=ADS;
    // The two-hand single pistol uses the mirrored primary hip pose. Akimbo
    // shoulder convergence would introduce a different yaw from that pose.
    H.Anim->DualPistolAimAlpha=Visible && !bTwoHandedLone
        ?LeftAimWeight*(1-H.Sprint)*(1-Player->NearWallAlpha)*(1-Player->DodgePresentationWeight())
            *(1.f-ADS)*(FireAction?1.f:1-H.Anim->ActionAlpha):0.f;
    H.Anim->bRevolver=H.Revolver;H.Anim->RevolverLiveRounds=H.Rounds;H.Anim->RevolverCartridges=H.Cases;
    // Ammo switching commits at insertion. Hide the released geometry during
    // that interval without prematurely spending/refunding the old live rounds.
    if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Reloading && H.ReloadCasesReleased && !H.Seated)
    {
        const int32 Retained=H.ReloadSpeedloader || !H.PendingAmmoType.IsEmpty()?0:H.Rounds;
        H.Anim->RevolverLiveRounds=Retained;H.Anim->RevolverCartridges=Retained;
    }
    // Fade the final step out/in with the camera and rifle instead of dropping
    // the arm offset to zero on takeoff or restoring its full value on landing.
    const float Walk=Player->GroundLocomotionWeight*(1-H.Sprint)*(1.f-ADS);
    const float HandPhase=Phase+(Index?PI:0);
    FVector Offset(-Player->NearWallAlpha*12,0,-Player->NearWallAlpha*6);
    Offset+=FVector(-2,0,-6)*Player->DodgePresentationWeight();
    if(!H.Action)Offset+=FVector(.10f*FMath::Sin(2*HandPhase)*Walk,.24f*FMath::Cos(HandPhase)*Walk,.15f*FMath::Sin(Clock*1.9f)*(1-H.Sprint)*(1.f-ADS)-.24f*FMath::Cos(2*HandPhase)*Walk);
    // Shot recoil: one spring set per hand, sampled through the same
    // camera-space conversion as the single-pistol rig and mirrored for the left
    // hand. The authored fire clip and the ballistic pattern stay untouched.
    Player->AdvanceDualWieldHandRecoil(Index,H.Revolver,ColdSteelCombat::ComposureHandling(Player,H.Stats.Handling),Delta);
    FVector KickOffset,KickAngles;Player->GetDualWieldHandRecoil(Index,KickOffset,KickAngles);
    const float SecondaryWeight=QuickAction?1.f-H.Anim->ActionAlpha:1.f;
    Offset*=SecondaryWeight;KickOffset*=SecondaryWeight;KickAngles*=SecondaryWeight;
    if(bTwoHandedLone)
    {
        // Camera X is depth, Y is lateral, Z is height. Keep the primary
        // pistol's current tuning, mirror only Y, and let evaluated ADS own
        // the complete sight frame at full aim. The baked clips share the
        // primary native frame, so this applies equally to both arms/actions.
        const FVector PrimaryHip=H.Revolver?Player->RevolverHipViewmodelLocation:Player->PistolHipViewmodelLocation;
        Offset+=FVector(PrimaryHip.X,-PrimaryHip.Y,PrimaryHip.Z)*(1.f-ADS);
    }
    const float Mirror=Index?-1.f:1.f;
    Offset+=FVector(-KickOffset.Z*100.f,KickOffset.X*100.f*Mirror,KickOffset.Y*100.f);
    // ADS is applied to the evaluated skeleton, where the actual optic bone
    // and source pose are available. This component carries only extra motion.
    FRotator Rotation(0,-90,0);
    Rotation.Pitch+=FMath::RadiansToDegrees(KickAngles.X);
    Rotation.Yaw-=FMath::RadiansToDegrees(KickAngles.Y)*Mirror;
    Rotation.Roll-=FMath::RadiansToDegrees(KickAngles.Z)*Mirror;
    FQuat PoseRotation=Rotation.Quaternion();
    Player->ApplyWeaponCrouchPose(Offset,PoseRotation,true,Index==1);
    const FTransform JumpPose=Player->GetWeaponJumpTransform(EFirstPersonJumpRig::Pistol,Index==1);
    Offset=JumpPose.TransformPosition(Offset);PoseRotation=JumpPose.GetRotation()*PoseRotation;
    if(Stowing)
    {
        // Camera-space rigid motion preserves the pistol/hand contact and all
        // native arm segments. The consumable layer solves above this base.
        Offset+=FVector(-7,-3,-42)*LowerWeight;
        PoseRotation=FRotator(-18.f*LowerWeight,0,0).Quaternion()*PoseRotation;
    }
    ApplyMeleePairPose(Index,Offset,PoseRotation);
    H.Mesh->SetRelativeLocation(Offset);
    H.Mesh->SetRelativeRotation(PoseRotation);
}
