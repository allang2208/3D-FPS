#include "OffhandKukriComponent.h"
#include "KukriWeaponComponent.h"
#include "KukriDecisiveComponent.h"
#include "OffhandKukriAuthoredPose.h"
#include "OffhandKukriAuthoredStrike.h"
#include "OffhandKukriAuthoredUppercut.h"
#include "OffhandShadowStepMotion.h"
#include "OffhandAxeQuickMotion.h"
#include "OffhandQuickClearance.h"
#include "OffhandKukriThrust.h"
#include "KukriRhythm.h"
#include "KukriQuickRhythm.h"
#include "../Staff/StaffOffhandMeleeComponent.h"
#include "../Staff/StaffOffhandQuickMotion.h"
#include "../FPSImpactFXSubsystem.h"
#include "../ModularSwordVisual.h"
#include "../MeleeSmallTargetQuery.h"
#include "../MeleeWeaponStats.h"
#include "../../Combat/CombatStatusFormula.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Skills/QuickCombatPistolMotion.h"
#include "../../Skills/QuickCombatImpactShake.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "Sound/SoundBase.h"

// Quick melee (F) for mixed pistol/staff + offhand blade pairs. Hatchets sample the native
// left hand of PairAttack3KH; other blades retain one left-hand thrust (BV1hQnh6hEio file
// 40.33-41.00 s: the hold swings out, the left arm drives the reversed blade into the screen centre,
// the pistol comes back up; authored pose/camera keys in OffhandKukriAuthoredStrike.h).
// Same skill contract as the other quick-melee weapons (KukriQuickCombat.cpp): CommitQuickCombatCast
// pays the skill stamina once and reserves F, one deterministic query per contact frame, the camera
// impulse also on a miss, use and kill experience.  Per-hit damage is 200 % of the offhand weapon's
// physical panel; the server recomputes the same number from the declared offhand item.  Each target
// is hit once per action, matching the shared quick-melee dedup on dedicated servers.  Martial clock:
// only Lightning Haste scales it.  Hit feel constants are the pommel strike's (KukriQuickRhythm).
// The background-only blur rides the reference's camera-speed envelope (blur curve, stencil 231).

namespace
{
constexpr int32 OffhandStrikeFocusStencil=231;
const TCHAR* OffhandStrikeWallPath=TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02");
// The thrust hits harder than the pommel strike whose constants it shares (user: more impact and force):
// a bigger reference camera swing, a stronger contact nod/push/widen and quick-melee impulse, a longer
// flesh hit-stop and a heavier miss jolt.  KukriQuickRhythm itself stays the main-hand kukri's.
constexpr float ThrustCameraScale=1.3f, ThrustAccentScale=1.7f, ThrustImpulseScale=.6f;
constexpr float ThrustHitStopScale=1.6f, ThrustImpactScale=1.3f, ThrustMissKick=.9f, ThrustMissStop=.045f;
}

bool UOffhandKukriComponent::CanQuickCombat() const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Pair=P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    if(Pair&&Pair->IsEquipped())
        return Pair->CanQuickCombat()&&!bQuickCombat&&!bUppercut&&!bShadowStep&&P->CanStartQuickCombatPriority();
    // Presentation is allowed to yield to reload, inspection and consumables.
    // F first interrupts those actions; ADS, sprint and a fading stance cannot
    // choose a different weapon or require the knife hand to be visible already.
    return bEquipped&&P&&P->HasInventoryWeapon()&&P->IsPistolWeapon()&&!P->HasOffhandPistol()&&
        Arms&&Arms->GetSkeletalMeshAsset()&&Blade&&Blade->GetStaticMesh()&&
        (!bDrawHatchet||UsesNativeAxe())&&!bQuickCombat&&!bUppercut&&!bShadowStep&&P->CanStartQuickCombatPriority();
}

float UOffhandKukriComponent::GetQuickCombatLength() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;}

float UOffhandKukriComponent::GetQuickCombatContact() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::ContactAt:OffhandKukriStrike::Contacts[0];}

float UOffhandKukriComponent::GetQuickCombatRelease() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::ReleaseAt:.32f;}

bool UOffhandKukriComponent::BeginQuickCombat()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!CanQuickCombat())return false;
    auto* StaffPair=P->FindComponentByClass<UStaffOffhandMeleeComponent>();
    if(StaffPair&&!StaffPair->IsEquipped())StaffPair=nullptr;
    if(StaffPair)StaffPair->CaptureActionEntry();
    // Equipment stows, casts and the pistol's own actions yield to F (priority interrupt).
    P->InterruptActionsForPriority(false);
    if(StaffPair?!StaffPair->OwnsLeftHand():!OwnsLeftHand())return false;
    auto* Profile=Model.Get();
    const auto State=Profile?Profile->Snapshot():FColdSteelProfile();
    const auto* Item=Profile?Profile->Equipped(State.ActiveWeaponSlot==6?8:11):nullptr;
    if(!Item||!(StaffPair?ColdSteelInventory::IsOneHandedBlade(*Item):IsOffhandKukri(*Item))||Profile->ActiveProductionTool())return false;
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    const bool Hatchet=ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("hatchet");
    if(Hatchet&&!(StaffPair?StaffPair->HasNativeChop():UsesNativeAxe()))return false;
    const float Length=Hatchet?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;
    const bool SwitchStaffRig=StaffPair&&!Hatchet;
    const float Total=Length+(SwitchStaffRig?StaffOffhandQuickMotion::Entry+StaffOffhandQuickMotion::Return:0.f);
    // The skill cost is paid once; F stays reserved through the selected action's recovery.
    if(!Profile->CommitQuickCombatCast(Total/Rate))return false;
    QuickActionRate=Rate;
    QuickCast=Profile->QuickCombatStats();
    // 200 % of the blade's physical panel plus the quick-melee skill's own damage; the authority
    // recomputes the same number from the declared off-hand item (OffhandKukriThrust.h).
    StrikeDamage=OffhandKukriThrust::Damage(*Item,Profile);
    QuickShot=ColdSteelSkills::Snapshot(P,Item);
    CaptureContactEdge(*Item);
    QuickShot.bRifle=false;QuickShot.bPistol=false;QuickShot.WeakpointPercent=0;
    // A blade thrust: blade toughness conversion (the authority uses the same form for this pair).
    QuickShot.AttackForm=EMonsterAttackForm::Blade;QuickShot.bMeleeStrike=true;
    QuickShot.AttackMeta|=0x80;
    QuickShot.ToughnessDamageMultiplier=QuickCast.ToughnessMultiplier;
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    // A downward chop uses the equipped axe swing, without the thrust-only stab layer.
    WhooshSound=Hatchet?nullptr:LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    ThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))ThudSounds.Add(Thud);
    bQuickCombat=true;bImpactConfirmed=bWallHit=bQuickKillPending=false;
    bStaffQuickCombat=StaffPair!=nullptr;
    bHatchetQuickCombat=Hatchet;
    if(Hatchet){StopUpperRift();bUpperRiftStarted=false;PrepareQuickRift();}
    QuickEndTime=Length+(SwitchStaffRig?StaffOffhandQuickMotion::Return:0.f);
    QuickTotalDuration=Total;
    if(auto* Pendant=P->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginLocal(QuickShot,true);
    // The accepted strike owns the hands immediately, including the first frame
    // after reload, consumable stow or draw recovery. Discard the interrupted
    // stance-entry and native reload-arm transitions before sampling either rig.
    EntryAge=-1.f;bWasPresenting=true;NativeReloadEnteredAt=-1.;
    if(Hatchet){DrawTime=-1.f;PendingDraw=EDrawEntry::None;}
    RightWeight=1.f;AimWeight=0.f;bHold=false;
    if(!StaffPair&&Arms)
        QuickNativePistolHand=OffhandKukriPose::HipFraming.InverseTransformPosition(Arms->RightHandInCamera);
    QuickElapsed=SwitchStaffRig?-StaffOffhandQuickMotion::Entry:0.f;
    if(Hatchet&&!StaffPair)
    {
        AxeArms->CaptureLeftEntry(OffhandAxeQuickMotion::Entry,-OffhandAxeQuickMotion::EntryLead/OffhandAxeQuickMotion::Entry);
        AxeArms->SetRelativeLocation(FVector::ZeroVector);
        AxeIdleAge=0.f;
    }
    if(StaffPair)StaffPair->BeginActionPresentation(false,Hatchet);
    QuickHitStop=0.f;QuickImpactAge=-1.f;QuickStrikeAge=-1.f;QuickImpactKick=0.f;
    QuickSwingsPlayed=QuickContactsDone=QuickMasteryHits=0;QuickHitActors.Reset();
    P->ExitSprintForWeapon();
    // The interrupt clears ADS/fire input and returns the gun state to Idle.
    // Release the previous reload/fire/inspect clip for SingleNode rigs too.
    P->ResumeWeaponPose();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    BeginStrikeFocus();
    return true;
}

void UOffhandKukriComponent::AdvanceQuickCombat(float Delta)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    auto* StaffPair=bStaffQuickCombat&&P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    if(bStaffQuickCombat&&(!StaffPair||!StaffPair->OwnsLeftHand()||
        AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(P->GetController()))))
    {CancelQuickCombat();return;}
    // Keep the accepted action clock through haste expiry and recovery. The
    // authority window and third-person timeline use this same committed rate.
    const float Rate=QuickActionRate;
    const float SwingAt=bHatchetQuickCombat?OffhandAxeQuickMotion::SwingAt:OffhandKukriStrike::Swings[0];
    const float ContactAt=GetQuickCombatContact();
    // The impact rattle and the contact accent are real time; the hit-stop freezes the author clock.
    if(QuickImpactAge>=0.f)QuickImpactAge+=Delta;
    if(QuickStrikeAge>=0.f)QuickStrikeAge+=Delta;
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bQuickCombat&&++Guard<64)
    {
        if(QuickHitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,QuickHitStop);
            QuickHitStop-=Pause;Remaining-=Pause;
            continue;
        }
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        if(QuickSwingsPlayed<OffhandKukriStrike::SlashCount&&
            QuickElapsed<SwingAt-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,SwingAt-QuickElapsed);
        if(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed<ContactAt-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,ContactAt-QuickElapsed);
        if(QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,QuickEndTime-QuickElapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=QuickElapsed;
        QuickElapsed=FMath::Min(QuickEndTime,QuickElapsed+Step);
        if(StaffPair)StaffPair->SetActionTime(QuickElapsed);
        Remaining=FMath::Max(0.f,Remaining-(QuickElapsed-Before)/Rate);
        while(QuickSwingsPlayed<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=SwingAt-UE_KINDA_SMALL_NUMBER)
        {
            // The stab whoosh under the swing: the drive-in is the fastest move of the action.
            if(WhooshSound)UGameplayStatics::PlaySound2D(this,WhooshSound,KukriRhythm::StabWhooshVolume,1.05f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,
                KukriQuickRhythm::SwingVolume,bHatchetQuickCombat?HatchetChopRhythm::Swing.SwingPitch:
                    KukriQuickRhythm::SwingPitch*(1.f+.06f*QuickSwingsPlayed));
            ++QuickSwingsPlayed;
        }
        while(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=ContactAt-UE_KINDA_SMALL_NUMBER)
        {
            ++QuickContactsDone;bImpactConfirmed=false;bWallHit=false;
            QuickContact();
        }
        if(QuickElapsed>=QuickEndTime-UE_KINDA_SMALL_NUMBER)
        {
            bQuickCombat=false;QuickHitActors.Reset();
            FinishQuickCombat();
        }
    }
    if(!bQuickCombat)return;
    if(Model.IsValid())
        Model->UpdateQuickCombatAction((QuickEndTime-QuickElapsed)/Rate+QuickHitStop,QuickTotalDuration/Rate);
    UpdateStrikeFocus(bHatchetQuickCombat?.75f*FMath::SmoothStep(.30f,.35f,QuickElapsed)*(1.f-FMath::SmoothStep(.40f,.59f,QuickElapsed)):
        OffhandKukriStrike::SampleCurve(OffhandKukriStrike::CameraBlur,QuickElapsed));
}

void UOffhandKukriComponent::QuickContact()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    UWorld* World=GetWorld();
    auto* Profile=Model.Get();
    if(!P||!World||!Profile||!Camera.IsValid())return;
    if(auto* Capture=P->FindComponentByClass<UBoundCongregateCaptureComponent>();Capture&&Capture->HitRestraintWithQuickMelee())
    {
        QuickImpactAge=0.f;QuickStrikeAge=0.f;QuickImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale;
        P->RefreshQuickCombatCamera();
        if(HitSound)UGameplayStatics::PlaySound2D(this,HitSound,1.f,1.f);
        return;
    }
    const FTransform Aim=P->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    // The blade lane is read from this contact key frame directly (the visible mesh is a tick behind).
    auto* StaffPair=bStaffQuickCombat?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    FTransform BladeFrame;
    if(bHatchetQuickCombat)
        BladeFrame=StaffPair?StaffPair->SampleHatchetBlade(QuickElapsed):SampleAxeBlade(QuickElapsed,true);
    else if(StaffPair)
        BladeFrame=StaffPair->ActionBladeInCamera(QuickElapsed)*Camera->GetComponentTransform();
    else
    {
        FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Framing;
        OffhandKukriStrike::SamplePose(QuickElapsed,Wrist,Hand,Shoulder,Pole,Framing);
        const FTransform HandFrame(Hand,Framing.TransformPosition(QuickNativePistolHand)+Wrist);
        BladeFrame=OffhandKukriPose::KukriInHand*HandFrame*Camera->GetComponentTransform();
    }
    const FVector BladePoint=BladeFrame.TransformPosition(bHatchetQuickCombat?(ContactBase+ContactTip)*.5f:KukriRhythm::BladeMid);
    const FVector Origin=BladePoint-Direction*FMath::Max(0.f,FVector::DotProduct(BladePoint-Aim.GetLocation(),Direction));
    // Targets use the skill's rangeCM like every F; scenery only answers where the blade really reaches.
    const float TipDepth=FVector::DotProduct(BladeFrame.TransformPosition(ContactTip)-Aim.GetLocation(),Direction);
    const float Radius=QuickCombatPistolMotion::QueryRadiusCM*float(ColdSteelMelee::EquippedModifiers(Profile).MartialRange);
    TArray<FHitResult> Hits;
    if(QuickCast.bAreaHit)Hits=MeleeSmallTargets::QueryQuickAreaContacts(World,P,Aim,Origin,QuickCast.RangeCM,Radius);
    else
    {
        FHitResult Hit;
        if(MeleeSmallTargets::QueryQuickContact(World,P,Aim,Origin,QuickCast.RangeCM,Radius,Hit))Hits.Add(Hit);
    }
    // The contact accent plays on the thrust's contact frame, hit or miss (lighter on a miss); the
    // hit-stop and the hit cue need a confirmed damage contact.
    QuickImpactAge=0.f;QuickStrikeAge=0.f;
    QuickImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*ThrustImpactScale*ThrustMissKick;
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=%s 第%d记 起点=%s 方向=%s 距离=%.0f AOE=%d 接触数=%d"),
        bHatchetQuickCombat?TEXT("副手斧头下劈"):TEXT("副手弯刀"),QuickContactsDone,*Origin.ToCompactString(),*Direction.ToCompactString(),QuickCast.RangeCM,
        QuickCast.bAreaHit?1:0,Hits.Num());
    for(const FHitResult& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!IsValid(Target)||Target->ActorHasTag(TEXT("Friendly"))||QuickHitActors.Contains(Target))continue;
        QuickHitActors.Add(Target);
        if(UWardBreakableGlass::BreakHit(Hit,Direction)){ConfirmQuickImpact(Hit,true);continue;}
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)
        {
            // A wall or prop in the blade's reach stops the thrust: wall stop, block cue and sparks.
            if(Hit.bBlockingHit&&!Target->IsA<APawn>()&&Target->GetOwner()!=P&&!Target->IsAttachedTo(P)
                &&FVector::DotProduct(Hit.ImpactPoint-Aim.GetLocation(),Direction)<=TipDepth+8.f)
                ConfirmQuickImpact(Hit,true);
            continue;
        }
        if(Combat->IsDead())continue;
        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(P,Target);
        auto HitShot=QuickShot;
        HitShot.MeleeDamagePhase=uint8(FMath::Max(0,QuickContactsDone-1));
        HitShot.ExtraMasteryExperience=Eligible&&QuickMasteryHits==1?Profile->MasteryDefinition(QuickShot.MasteryId).MultiHitExperience:0;
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(P,Hit,StrikeDamage,Direction,HitShot,&Receipt);
        const bool bKilled=Combat->IsDead();
        if(Applied<=0.f&&!bKilled)continue;
        if(Eligible)++QuickMasteryHits;
        ConfirmQuickImpact(Hit,false);
        if(P->HasAuthority())SpawnContactFX(Hit,false);
        P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
        // Pure push after the damage, no stun reaction (the skill's knockback).
        Combat->ReceiveMeleeKnockback(P,QuickCast.KnockbackCM);
        if(P->HasAuthority()&&!bKilled&&QuickCast.BleedChance>0.f&&FMath::FRand()<QuickCast.BleedChance)
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddBleeding(P,1);
        if(Eligible&&bKilled)bQuickKillPending=true;
    }
    if(QuickCast.bAreaHit&&!bWallHit)
    {
        FHitResult Surface;
        if(MeleeSmallTargets::BladeScenery(World,P,Origin,BladeFrame.TransformPosition(ContactTip),Surface))
            SpawnContactFX(Surface,true);
    }
    if(!bImpactConfirmed&&!bWallHit)QuickHitStop=FMath::Max(QuickHitStop,ThrustMissStop);
    // Resample the camera now so the impulse shows on this frame even after the character's update.
    P->RefreshQuickCombatCamera();
}

void UOffhandKukriComponent::ConfirmQuickImpact(const FHitResult& Hit,bool bWorld)
{
    // One cue per slash; every target still gets its own damage receipt.
    if(bImpactConfirmed||(bWorld&&bWallHit))return;
    if(bWorld)
    {
        bWallHit=true;QuickHitStop=KukriRhythm::WallStopSeconds;QuickImpactAge=0.f;
        QuickImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*.6f;
        if(auto* Sound=LoadObject<USoundBase>(nullptr,OffhandStrikeWallPath))
            UGameplayStatics::PlaySoundAtLocation(this,Sound,Hit.ImpactPoint,.55f,1.15f);
        SpawnContactFX(Hit,true);
        return;
    }
    bImpactConfirmed=true;QuickImpactAge=0.f;
    QuickHitStop=KukriRhythm::FleshStopSeconds*(bHatchetQuickCombat?HatchetChopRhythm::Swing.HitStopScale:ThrustHitStopScale);
    QuickImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*ThrustImpactScale;
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,1.f,.9f);
    if(ThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,ThudSounds[FMath::RandRange(0,ThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch*KukriQuickRhythm::ThudPitchScale);
}

void UOffhandKukriComponent::CaptureContactEdge(const FColdSteelItem& Item)
{
    const bool Modular=ColdSteelModularSword::Supports(Item);
    ContactBase=Modular?ColdSteelModularSword::BladePoint(Item,false):KukriRhythm::BladeRoot;
    ContactTip=Modular?ColdSteelModularSword::BladePoint(Item,true):KukriRhythm::BladeTip;
}

void UOffhandKukriComponent::SpawnContactFX(const FHitResult& Hit,bool bWorld) const
{
    auto* FX=GetWorld()?GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>():nullptr;
    if(FX)FX->SpawnBladeContact(Hit,Camera.Get(),bWorld);
    if(bWorld)if(auto* BladeFX=GetOwner()->FindComponentByClass<UKukriWeaponComponent>())BladeFX->PresentBladeScenery(Hit);
}

void UOffhandKukriComponent::FinishQuickCombat()
{
    if(bStaffQuickCombat)
        if(auto* Pair=GetOwner()->FindComponentByClass<UStaffOffhandMeleeComponent>())
            Pair->EndActionPresentation(QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER);
    if(bHatchetQuickCombat)
    {
        const bool Interrupted=QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER;
        if(!bStaffQuickCombat&&AxeArms)
        {
            if(Interrupted)AxeArms->CaptureLeftEntry(.12f);
            else AxeArms->ClearEntry();
        }
        if(Interrupted)StopUpperRift();
    }
    bStaffQuickCombat=false;bHatchetQuickCombat=false;
    auto* Profile=Model.Get();
    if(Profile)
    {
        Profile->FinishQuickCombatCast();
        if(bQuickKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bQuickKillPending=false;
    EndStrikeFocus();
    UpdateStrikeFocus(0.f);
    if(Arms)Arms->StrikeTime=-1.f;
}

void UOffhandKukriComponent::CancelQuickCombat()
{
    if(!bQuickCombat)return;
    bQuickCombat=false;QuickHitActors.Reset();
    FinishQuickCombat();
}

bool UOffhandKukriComponent::GetStrikeFraming(FTransform& Out) const
{
    FVector Wrist,Shoulder,Pole;FQuat Hand;
    if(bQuickCombat)
    {
        Out=OffhandQuickClearance::PistolFrame(OffhandKukriPose::HipFraming,
            QuickElapsed/GetQuickCombatLength(),bHatchetQuickCombat);
        return true;
    }
    if(bUppercut)
    {
        OffhandKukriUpper::SamplePose(UppercutElapsed,Wrist,Hand,Shoulder,Pole,Out);
        return true;
    }
    if(bShadowStep)
    {
        const float MaxT=bShadowStepStage2?OffhandShadowStepMotion::Stage2Length:OffhandShadowStepMotion::Stage1Length;
        OffhandShadowStepMotion::SamplePose(bShadowStepStage2,FMath::Clamp(ShadowStepElapsed,0.f,MaxT),Wrist,Hand,Shoulder,Pole,Out);
        return true;
    }
    return false;
}

void UOffhandKukriComponent::GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    if(bShadowStep){GetShadowStepCameraMotion(Location,Rotation,FovDelta);return;}
    if(bUppercut)
    {
        // The stage-3 reference curve mirrored: a left-hand cut carries the view the other way (its wind-up gather too).
        KukriRhythm::SwingCamera(KukriRhythm::UppercutStage,UppercutElapsed,Rotation,FovDelta,&Location);
        Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;Location.Y=-Location.Y;
        if(UppercutImpactAge>=0.f)
        {
            const float Shake=KukriRhythm::HitShake(UppercutImpactAge)*UppercutImpactKick;
            Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*-KukriRhythm::Swings[KukriRhythm::UppercutStage].HitRoll);
            Location+=FVector(0.f,Shake*.25f,Shake*.15f);
            FovDelta+=KukriRhythm::ImpactEnvelope(UppercutImpactAge)*UppercutImpactKick*1.4f;
        }
        if(UppercutStrikeAge>=0.f)
        {
            // Real-time contact accent at the impact moment, mirrored with the cut.
            const auto& K=KukriRhythm::Strikes[KukriRhythm::UppercutStage];
            const float E=KukriRhythm::StrikeEnvelope(UppercutStrikeAge);
            Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw-=K.AccentYaw*E;
            Location.X+=K.AccentPushCM*E;FovDelta+=K.AccentFov*E;
        }
        return;
    }
    if(!bQuickCombat)return;
    // Same author clock as the arm keys: the hit-stop freezes the curve with the pose.
    float BlurStrength=0.f;
    if(bHatchetQuickCombat)
    {
        HatchetDualChopRhythm::Camera(QuickElapsed*OffhandAxeQuickMotion::ClipRate,Rotation,FovDelta,&Location);
    }
    else
    {
        OffhandKukriStrike::Camera(QuickElapsed,Rotation,FovDelta,BlurStrength);
        Rotation*=ThrustCameraScale;FovDelta*=ThrustCameraScale;
        Location=FVector::ZeroVector;
    }
    if(QuickImpactAge>=0.f)
    {
        const float Shake=KukriRhythm::HitShake(QuickImpactAge)*QuickImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriQuickRhythm::HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        FovDelta+=KukriRhythm::ImpactEnvelope(QuickImpactAge)*QuickImpactKick*KukriQuickRhythm::HitFov;
    }
    if(QuickStrikeAge>=0.f)
    {
        if(bHatchetQuickCombat)
        {
            const auto& K=HatchetChopRhythm::Strike;
            const float E=KukriRhythm::StrikeEnvelope(QuickStrikeAge);
            Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw-=K.AccentYaw*E;
            Location.X+=K.AccentPushCM*E;FovDelta+=K.AccentFov*E;
            return;
        }
        // Real-time contact accent on the contact frame: the view nods into the thrust, pushes forward
        // and widens, plus a share of the shared quick-melee impulse.
        const float E=KukriRhythm::StrikeEnvelope(QuickStrikeAge)*ThrustAccentScale;
        Rotation.Pitch+=KukriQuickRhythm::AccentPitch*E;Location.X+=KukriQuickRhythm::AccentPushCM*E;
        FovDelta+=KukriQuickRhythm::AccentFov*E;
        FVector ImpulseLocation=FVector::ZeroVector;FRotator ImpulseRotation=FRotator::ZeroRotator;
        QuickCombatImpactShake::Add(QuickStrikeAge,ImpulseLocation,ImpulseRotation);
        Location+=ImpulseLocation*ThrustImpulseScale;
        Rotation+=ImpulseRotation*ThrustImpulseScale;
    }
}

void UOffhandKukriComponent::BeginStrikeFocus()
{
    // Background-only blur (the whirlwind material): the pistol viewmodel, the kukri arm and the
    // blade write stencil 231 and stay sharp; engine motion blur is off for the strike.
    if(!Camera.IsValid())return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    bFocusActive=true;
    auto& PP=Camera->PostProcessSettings;
    FocusSavedBlur=PP.MotionBlurAmount;bFocusSavedBlurOverride=PP.bOverride_MotionBlurAmount;
    PP.bOverride_MotionBlurAmount=true;PP.MotionBlurAmount=0.f;
    if(!FocusMaterial)
        if(auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus")).TryLoad()))
            FocusMaterial=UMaterialInstanceDynamic::Create(Material,this);
    TArray<USceneComponent*> Parts;
    if(P&&P->AKMViewmodel){P->AKMViewmodel->GetChildrenComponents(true,Parts);Parts.Add(P->AKMViewmodel);}
    if(bStaffQuickCombat)
    {
        // Both native arm sources, staff modules, blade and outfit followers stay sharp through the handoff.
        TArray<USceneComponent*> StaffParts;Camera->GetChildrenComponents(true,StaffParts);
        for(auto* Part:StaffParts)Parts.AddUnique(Part);
    }
    if(Arms)Parts.AddUnique(Arms);
    if(bHatchetQuickCombat&&AxeArms)Parts.AddUnique(AxeArms);
    if(Blade)Parts.AddUnique(Blade);
    for(auto* Part:Parts)
        if(auto* Primitive=Cast<UPrimitiveComponent>(Part))
        {
            FocusDepth.Add({Primitive,bool(Primitive->bRenderCustomDepth),Primitive->CustomDepthStencilValue,uint8(Primitive->CustomDepthStencilWriteMask)});
            Primitive->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
            Primitive->SetCustomDepthStencilValue(OffhandStrikeFocusStencil);Primitive->SetRenderCustomDepth(true);
        }
}

void UOffhandKukriComponent::UpdateStrikeFocus(float Strength)
{
    if(!Camera.IsValid()||!bFocusActive)return;
    if(FocusMaterial)
    {
        FocusMaterial->SetScalarParameterValue(TEXT("Strength"),Strength);
        const auto* Resource=GetWorld()&&GetWorld()->Scene?FocusMaterial->GetMaterialResource(GetWorld()->Scene->GetShaderPlatform()):nullptr;
        // Only with a complete shader map: the fallback post-process material draws a coloured border.
        if(Strength>UE_SMALL_NUMBER&&Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete())
            Camera->PostProcessSettings.AddBlendable(FocusMaterial,1.f);
        else Camera->PostProcessSettings.RemoveBlendable(FocusMaterial);
    }
}

void UOffhandKukriComponent::EndStrikeFocus()
{
    if(!bFocusActive)return;
    bFocusActive=false;
    if(Camera.IsValid())
    {
        if(FocusMaterial)Camera->PostProcessSettings.RemoveBlendable(FocusMaterial);
        Camera->PostProcessSettings.MotionBlurAmount=FocusSavedBlur;
        Camera->PostProcessSettings.bOverride_MotionBlurAmount=bFocusSavedBlurOverride;
    }
    for(const auto& Saved:FocusDepth)
        if(auto* Part=Saved.Part.Get())
        {
            Part->SetRenderCustomDepth(Saved.bEnabled);Part->SetCustomDepthStencilValue(Saved.Stencil);
            Part->SetCustomDepthStencilWriteMask(ERendererStencilMask(Saved.WriteMask));
        }
    FocusDepth.Reset();
}
