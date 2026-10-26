#include "OffhandKukriComponent.h"
#include "OffhandKukriAuthoredPose.h"
#include "OffhandKukriAuthoredStrike.h"
#include "OffhandKukriAuthoredUppercut.h"
#include "OffhandKukriThrust.h"
#include "KukriRhythm.h"
#include "KukriQuickRhythm.h"
#include "../FPSImpactFXSubsystem.h"
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

// Quick melee (F) for the pistol + offhand kukri pair: one left-hand thrust (BV1hQnh6hEio file
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
    return bEquipped&&P&&OwnsLeftHand()&&RightWeight>.95f&&!P->IsSprinting()&&!P->IsAiming()&&!bQuickCombat&&!bUppercut;
}

bool UOffhandKukriComponent::BeginQuickCombat()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!P->CanStartQuickCombatPriority()||!CanQuickCombat())return false;
    // Equipment stows, casts and the pistol's own actions yield to F (priority interrupt).
    P->InterruptActionsForPriority(false);
    if(!CanQuickCombat())return false;
    auto* Profile=Model.Get();
    const auto State=Profile?Profile->Snapshot():FColdSteelProfile();
    const auto* Item=Profile?Profile->Equipped(State.ActiveWeaponSlot==6?8:11):nullptr;
    if(!Item||!IsOffhandKukri(*Item)||Profile->ActiveProductionTool())return false;
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    // The skill cost is paid once; F stays reserved until the thrust is back on the stance.
    if(!Profile->CommitQuickCombatCast(OffhandKukriStrike::Length/Rate))return false;
    QuickCast=Profile->QuickCombatStats();
    // 200 % of the blade's physical panel plus the quick-melee skill's own damage; the authority
    // recomputes the same number from the declared off-hand item (OffhandKukriThrust.h).
    StrikeDamage=OffhandKukriThrust::Damage(*Item,Profile);
    QuickShot=ColdSteelSkills::Snapshot(P,Item);
    QuickShot.bRifle=false;QuickShot.bPistol=false;QuickShot.WeakpointPercent=0;
    // A blade thrust: blade toughness conversion (the authority uses the same form for this pair).
    QuickShot.AttackForm=EMonsterAttackForm::Blade;QuickShot.bMeleeStrike=true;
    QuickShot.AttackMeta|=0x80;
    QuickShot.ToughnessDamageMultiplier=QuickCast.ToughnessMultiplier;
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    WhooshSound=LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    ThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))ThudSounds.Add(Thud);
    bQuickCombat=true;bImpactConfirmed=bWallHit=bQuickKillPending=false;
    QuickElapsed=0.f;QuickHitStop=0.f;QuickImpactAge=-1.f;QuickStrikeAge=-1.f;QuickImpactKick=0.f;
    QuickSwingsPlayed=QuickContactsDone=QuickMasteryHits=0;QuickHitActors.Reset();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    BeginStrikeFocus();
    return true;
}

void UOffhandKukriComponent::AdvanceQuickCombat(float Delta)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
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
            QuickElapsed<OffhandKukriStrike::Swings[QuickSwingsPlayed]-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,OffhandKukriStrike::Swings[QuickSwingsPlayed]-QuickElapsed);
        if(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed<OffhandKukriStrike::Contacts[QuickContactsDone]-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,OffhandKukriStrike::Contacts[QuickContactsDone]-QuickElapsed);
        if(QuickElapsed<OffhandKukriStrike::Length-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,OffhandKukriStrike::Length-QuickElapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=QuickElapsed;
        QuickElapsed=FMath::Min(OffhandKukriStrike::Length,QuickElapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(QuickElapsed-Before)/Rate);
        while(QuickSwingsPlayed<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=OffhandKukriStrike::Swings[QuickSwingsPlayed]-UE_KINDA_SMALL_NUMBER)
        {
            // The stab whoosh under the swing: the drive-in is the fastest move of the action.
            if(WhooshSound)UGameplayStatics::PlaySound2D(this,WhooshSound,KukriRhythm::StabWhooshVolume,1.05f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,
                KukriQuickRhythm::SwingVolume,KukriQuickRhythm::SwingPitch*(1.f+.06f*QuickSwingsPlayed));
            ++QuickSwingsPlayed;
        }
        while(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=OffhandKukriStrike::Contacts[QuickContactsDone]-UE_KINDA_SMALL_NUMBER)
        {
            ++QuickContactsDone;bImpactConfirmed=false;bWallHit=false;
            QuickContact();
        }
        if(QuickElapsed>=OffhandKukriStrike::Length-UE_KINDA_SMALL_NUMBER)
        {
            bQuickCombat=false;QuickHitActors.Reset();
            FinishQuickCombat();
        }
    }
    if(!bQuickCombat)return;
    if(Model.IsValid())
        Model->UpdateQuickCombatAction((OffhandKukriStrike::Length-QuickElapsed)/Rate+QuickHitStop,
            OffhandKukriStrike::Length/Rate);
    UpdateStrikeFocus(OffhandKukriStrike::SampleCurve(OffhandKukriStrike::CameraBlur,QuickElapsed));
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
    FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Framing;
    OffhandKukriStrike::SamplePose(QuickElapsed,Wrist,Hand,Shoulder,Pole,Framing);
    const FVector HandPos=Arms?Arms->RightHandInCamera:FVector::ZeroVector;
    const FTransform HandFrame(Hand,HandPos+Wrist);
    // FTransform composes left to right (A*B applies A first): blade -> hand (camera space) -> world.
    const FTransform BladeFrame=OffhandKukriPose::KukriInHand*HandFrame*Camera->GetComponentTransform();
    const FVector BladePoint=BladeFrame.TransformPosition(KukriRhythm::BladeMid);
    const FVector Origin=BladePoint-Direction*FMath::Max(0.f,FVector::DotProduct(BladePoint-Aim.GetLocation(),Direction));
    // Targets use the skill's rangeCM like every F; scenery only answers where the blade really reaches.
    const float TipDepth=FVector::DotProduct(BladeFrame.TransformPosition(KukriRhythm::BladeTip)-Aim.GetLocation(),Direction);
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
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=副手弯刀 第%d记 起点=%s 方向=%s 距离=%.0f AOE=%d 接触数=%d"),
        QuickContactsDone,*Origin.ToCompactString(),*Direction.ToCompactString(),QuickCast.RangeCM,
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
        HitShot.ExtraMasteryExperience=Eligible&&QuickMasteryHits==1?Profile->MasteryDefinition(QuickShot.MasteryId).MultiHitExperience:0;
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(P,Hit,StrikeDamage,Direction,HitShot,&Receipt);
        const bool bKilled=Combat->IsDead();
        if(Applied<=0.f&&!bKilled)continue;
        if(Eligible)++QuickMasteryHits;
        ConfirmQuickImpact(Hit,false);
        P->NotifyConfirmedWeaponHit(Target,Applied,&Receipt,false);
        // Pure push after the damage, no stun reaction (the skill's knockback).
        Combat->ReceiveMeleeKnockback(P,QuickCast.KnockbackCM);
        if(P->HasAuthority()&&!bKilled&&QuickCast.BleedChance>0.f&&FMath::FRand()<QuickCast.BleedChance)
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddBleeding(P,1);
        if(Eligible&&bKilled)bQuickKillPending=true;
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
    QuickHitStop=KukriRhythm::FleshStopSeconds*ThrustHitStopScale;
    QuickImpactKick=KukriRhythm::ImpactKick*KukriQuickRhythm::ImpactScale*ThrustImpactScale;
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,1.f,.9f);
    if(ThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,ThudSounds[FMath::RandRange(0,ThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch*KukriQuickRhythm::ThudPitchScale);
    SpawnContactFX(Hit,false);
}

void UOffhandKukriComponent::SpawnContactFX(const FHitResult& Hit,bool bWorld) const
{
    auto* FX=GetWorld()?GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>():nullptr;
    if(!FX||!Camera.IsValid())return;
    // Melee query hits are cosmetic input here: the subsystem only draws blocking hits, and the
    // flourish plays its own hit / wall cue, so no bullet impact sound and no bullet-hole decal.
    FHitResult Contact=Hit;Contact.bBlockingHit=true;
    if(Contact.ImpactNormal.IsNearlyZero())
        if(const auto* P=Cast<AFPSGAMECharacter>(GetOwner()))
            Contact.ImpactNormal=-P->GetMeleeAimTransform().GetUnitAxis(EAxis::X);
    FX->SpawnImpact(Contact,Camera.Get(),false,false);
}

void UOffhandKukriComponent::FinishQuickCombat()
{
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
        OffhandKukriStrike::SamplePose(QuickElapsed,Wrist,Hand,Shoulder,Pole,Out);
        return true;
    }
    if(bUppercut)
    {
        OffhandKukriUpper::SamplePose(UppercutElapsed,Wrist,Hand,Shoulder,Pole,Out);
        return true;
    }
    return false;
}

void UOffhandKukriComponent::GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    if(bUppercut)
    {
        // The stage-3 reference curve mirrored: a left-hand cut carries the view the other way.
        KukriRhythm::SwingCamera(KukriRhythm::UppercutStage,UppercutElapsed,Rotation,FovDelta);
        Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;
        Location=FVector::ZeroVector;
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
    OffhandKukriStrike::Camera(QuickElapsed,Rotation,FovDelta,BlurStrength);
    Rotation*=ThrustCameraScale;FovDelta*=ThrustCameraScale;
    Location=FVector::ZeroVector;
    if(QuickImpactAge>=0.f)
    {
        const float Shake=KukriRhythm::HitShake(QuickImpactAge)*QuickImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriQuickRhythm::HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        FovDelta+=KukriRhythm::ImpactEnvelope(QuickImpactAge)*QuickImpactKick*KukriQuickRhythm::HitFov;
    }
    if(QuickStrikeAge>=0.f)
    {
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
    if(Arms)Parts.Add(Arms);
    if(Blade)Parts.Add(Blade);
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
