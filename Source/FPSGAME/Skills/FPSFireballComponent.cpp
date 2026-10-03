#include "FPSFireballComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffChargeFlow.h"
#include "FPSFireballProjectile.h"
#include "FPSMagicPreview.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "FPSIceSpikeComponent.h"
#include "FPSIceWallComponent.h"
#include "FPSBlizzardComponent.h"
#include "FPSLightningComponent.h"
#include "FPSElectricMagicComponent.h"
#include "FPSHolyLightComponent.h"
#include "FPSFireMagicComponent.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "FPSCastingMeshComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSTraversalRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Misc/ScopeExit.h"

UFPSFireballComponent::UFPSFireballComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    CoreAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/NS_FireballSlowBurnCore.NS_FireballSlowBurnCore")));
    TrailAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/NS_FireballVelocityTrail.NS_FireballVelocityTrail")));
    ExplosionAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic.NS_FireballImpactRealistic")));
    ShockwaveAsset=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave")));
    ImpactSoundAsset=TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/S_FireballImpactLayered.S_FireballImpactLayered")));
}
void UFPSFireballComponent::BeginPlay()
{
    Super::BeginPlay();
    AddTickPrerequisiteActor(GetOwner());
    PoseSettings.Load();PowerFistSettings.Load();
    // Load once with the player, before the first input.
    Core=CoreAsset.LoadSynchronous();Trail=TrailAsset.LoadSynchronous();Explosion=ExplosionAsset.LoadSynchronous();
    Shockwave=ShockwaveAsset.LoadSynchronous();ImpactSound=ImpactSoundAsset.LoadSynchronous();
    if(auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>())
    {
        FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("CastingFallbackLeftArm"));
        GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
        FallbackHands->SetRelativeRotation(FRotator(0,90,0));
        FallbackHands->SetSkeletalMesh(GetDefault<UFPSTraversalSettings>()->ArmsMesh.LoadSynchronous());
        FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
        FallbackHands->SetCastShadow(false);FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetVisibility(false);
        FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
        FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    }
}
UColdSteelStatusModel* UFPSFireballComponent::Model() const
{ return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr; }
bool UFPSFireballComponent::IsPrepared() const { return Active.IsValid()&&!Active->IsFlying(); }
bool UFPSFireballComponent::IsFlying() const { return Active.IsValid()&&Active->IsFlying(); }
bool UFPSFireballComponent::HasOtherPreparedSpell(const UActorComponent* Requester) const
{
    if(Requester!=this&&IsPrepared())return true;
    const auto* Owner=GetOwner();if(!Owner)return false;
    if(const auto* Ice=Owner->FindComponentByClass<UFPSIceSpikeComponent>();Ice&&Requester!=Ice&&Ice->IsPrepared())return true;
    if(const auto* Wall=Owner->FindComponentByClass<UFPSIceWallComponent>();Wall&&Requester!=Wall&&Wall->HasUnreleasedCast())return true;
    if(const auto* Blizzard=Owner->FindComponentByClass<UFPSBlizzardComponent>();Blizzard&&Requester!=Blizzard&&Blizzard->HasUnreleasedCast())return true;
    if(const auto* Electric=Owner->FindComponentByClass<UFPSElectricMagicComponent>();Electric&&Requester!=Electric&&Electric->IsCharging())return true;
    return false;
}
void UFPSFireballComponent::SetHandPhase(EFireballHandPhase Phase)
{
    if(Phase==EFireballHandPhase::Recovering)
    {
        CaptureStaffRecovery();
        if(bPowerFistGesture)PowerFistRecoveryStartAge=FMath::Min(PowerFistSourceAge(),PowerFistSettings.RecoverStart);
        RecoveryReleaseAlpha=HandReleaseFraction();
        RecoveryFromPhase=HandPhase;
        // Keep the unclamped release age so cancellation during impact begins
        // recovery at the actual displaced pose, including after the push ends.
        RecoveryFromFraction=HandPhase==EFireballHandPhase::Releasing?
            PhaseAge/GesturePhaseDuration(EFireballHandPhase::Releasing):HandPhaseFraction();
    }
    if(Phase==EFireballHandPhase::Raising||Phase==EFireballHandPhase::ReadyingRelease)BeginStaffGesture();
    HandPhase=Phase;PhaseAge=0.f;
    if(Phase==EFireballHandPhase::None){bPowerFistGesture=false;PowerFistRecoveryStartAge=0.f;bStaffGesture=false;CastingStaff.Reset();}
    if(Phase==EFireballHandPhase::Releasing)
    {
        ReleaseHoldEndAge=0.f;
        ReleaseImpactAges.Reset();
        if(!bPowerFistGesture)ReleaseImpactAges.Add(ReleaseContactAge());
    }
    if(Phase==EFireballHandPhase::Raising || Phase==EFireballHandPhase::ReadyingRelease)
    { ++CastSerial;bHandEntryCaptured=false;bReleaseFromRest=Phase==EFireballHandPhase::ReadyingRelease; }
}
void UFPSFireballComponent::CaptureHandEntry(const FTransform& Hand,const FTransform& Clavicle,const FVector& Shoulder,const FVector& Elbow)
{
    if(bHandEntryCaptured)return;
    EntryHand=Hand;EntryClavicle=Clavicle;EntryShoulder=Shoulder;EntryElbow=Elbow;bHandEntryCaptured=true;
}
float UFPSFireballComponent::HandReleaseFraction() const
{
    if(HandPhase==EFireballHandPhase::Recovering)return RecoveryReleaseAlpha;
    if(bStaffGesture)return HandPhase==EFireballHandPhase::Releasing?FMath::Clamp(PhaseAge/ReleaseContactAge(),0.f,1.f):0.f;
    if(HandPhase==EFireballHandPhase::ReadyingRelease)return .48f;
    if(HandPhase!=EFireballHandPhase::Releasing)return 0.f;
    const float T=PhaseAge*FireballCastMotion::ReleasePushSpeed/FMath::Max(.01f,FMath::Min(LaunchContactTime,ReleaseDuration));
    return FireballCastMotion::ReleasePalm(T,bReleaseFromRest);
}
FFireballArmMotion UFPSFireballComponent::SampleHandMotion(const FQuat& HandCorrection,const FFireballArmMotion& Current) const
{
    FFireballArmMotion Entry;
    Entry.Wrist=EntryHand.GetLocation();Entry.Rotation=EntryHand.GetRotation();
    Entry.Shoulder=EntryShoulder;Entry.Pole=EntryElbow;
    if(bPowerFistGesture)
    {
        const auto From=PowerFistSettings.Sample(Entry,HandCorrection,PowerFistSourceAge());
        return HandPhase==EFireballHandPhase::Recovering?PowerFistSettings.Recover(From,Current,HandPhaseFraction()):From;
    }
    const auto Sample=[&](EFireballHandPhase Phase,float Fraction)
    {
        if(Phase==EFireballHandPhase::Raising)return FireballCastMotion::Gather(PoseSettings,Entry,HandCorrection,Fraction);
        if(Phase==EFireballHandPhase::ReadyingRelease)return FireballCastMotion::Ready(PoseSettings,Entry,HandCorrection,Fraction);
        if(Phase==EFireballHandPhase::Releasing)
        {
            const float PushDuration=FMath::Max(.01f,ReleaseDuration)/FireballCastMotion::ReleasePushSpeed;
            auto Pose=FireballCastMotion::Release(PoseSettings,HandCorrection,
                FMath::Min(Fraction,1.f)*FMath::Max(.01f,ReleaseDuration)/FMath::Max(.01f,FMath::Min(LaunchContactTime,ReleaseDuration)),bReleaseFromRest);
            for(const float Contact:ReleaseImpactAges)
                Pose=FireballCastMotion::WithReleaseImpact(Pose,Fraction*PushDuration-Contact);
            return Pose;
        }
        return Current;
    };
    if(HandPhase==EFireballHandPhase::Recovering)
        return FireballCastMotion::Recover(PoseSettings,Sample(RecoveryFromPhase,RecoveryFromFraction),Current,HandPhaseFraction());
    const float Fraction=HandPhase==EFireballHandPhase::Releasing?
        PhaseAge/(FMath::Max(.01f,ReleaseDuration)/FireballCastMotion::ReleasePushSpeed):HandPhaseFraction();
    return Sample(HandPhase,Fraction);
}
FVector UFPSFireballComponent::HeldOrbPosition() const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return GetOwner()->GetActorLocation();
    if(bStaffOrb)
    {
        FVector Focus=StaffOrbHover;
        if(!GestureOwner.IsValid()&&HandPhase==EFireballHandPhase::Raising&&IsStaffCasting()&&CastingStaff.IsValid())
            Focus=StaffCastMotion::Focus(SampleStaffMotion(CastingStaff->CarryPoseInCamera()));
        return Camera->GetComponentTransform().TransformPosition(Focus);
    }
    // Initial collision/space query uses the same staff focus as the new gather.
    if(!Active.IsValid())
        if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->CanBeginCast())
            return Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Focus(Staff->CarryPoseInCamera()));
    FVector Wrist=PoseSettings.GatherWrist;
    if(!GestureOwner.IsValid() && HandPhase==EFireballHandPhase::Raising && bHandEntryCaptured)
    {
        Wrist=FireballCastMotion::GatherWrist(PoseSettings,EntryHand.GetLocation(),GatherFraction());
    }
    // Once gathered the orb stays at its established hover offset, independently
    // of recovery, weapon handling and the later release gesture.
    const FVector HoldOffset=PoseSettings.PalmFrame(0).RotateVector(PoseSettings.OrbOffset);
    return Camera->GetComponentTransform().TransformPosition(Wrist+HoldOffset);
}
void UFPSFireballComponent::UpdateFallbackHands()
{
    if(!FallbackHands)return;
    bool OtherHandsVisible=false;
    TInlineComponentArray<UFPSCastingMeshComponent*> Meshes(GetOwner());
    for(const auto* Mesh:Meshes)if(Mesh!=FallbackHands && Mesh->GetSkeletalMeshAsset() && Mesh->IsVisible() && !Mesh->bHiddenInGame)
    { OtherHandsVisible=true;break; }
    const bool Show=IsOccupyingLeftHand() && !OtherHandsVisible;
    FallbackHands->SetVisibility(Show);
    if(Show){FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();}
}
float UFPSFireballComponent::HandPhaseFraction() const
{
    if(HandPhase==EFireballHandPhase::None)return 0.f;
    if(HandPhase==EFireballHandPhase::Holding)return 1.f;
    return FMath::Clamp(PhaseAge/GesturePhaseDuration(HandPhase),0.f,1.f);
}
float UFPSFireballComponent::PowerFistSourceAge() const
{
    if(HandPhase==EFireballHandPhase::Recovering)return PowerFistRecoveryStartAge;
    return PhaseAge+(HandPhase==EFireballHandPhase::Releasing?PowerFistSettings.ClenchStart:0.f);
}
float UFPSFireballComponent::GatherFraction() const
{ return !GestureOwner.IsValid()&&HandPhase==EFireballHandPhase::Raising?HandPhaseFraction():1.f; }
void UFPSFireballComponent::Feedback(const FString& Text)
{ LastMessage=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.5; }
void UFPSFireballComponent::RejectHeldLeftHand()
{
    // Nothing is kept waiting for the hand here: a held hand is released by a
    // loadout change, not by time, so the request is dropped with the notice.
    bQueuedCast=bQueuedLaunch=false;
    if(GetWorld())HandNotice.Show(float(GetWorld()->GetTimeSeconds()));
}
bool UFPSFireballComponent::IsHandOccupiedNotice() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(float(GetWorld()->GetTimeSeconds()));
}
float UFPSFireballComponent::HandNoticeAlpha() const
{ return GetWorld()?HandNotice.Alpha(float(GetWorld()->GetTimeSeconds())):0.f; }
float UFPSFireballComponent::HandNoticeRise() const
{ return GetWorld()?HandNotice.Rise(float(GetWorld()->GetTimeSeconds())):0.f; }
FString UFPSFireballComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(bQueuedCast || (bQueuedLaunch && HandPhase==EFireballHandPhase::None))return TEXT("等待施法");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return LastMessage;
    if(!GestureOwner.IsValid())
    {
        if(HandPhase==EFireballHandPhase::Raising)return TEXT("凝聚");
        if(HandPhase==EFireballHandPhase::Releasing || HandPhase==EFireballHandPhase::ReadyingRelease)return TEXT("发射中");
        if(HandPhase==EFireballHandPhase::Recovering)return TEXT("收手");
    }
    if(IsPrepared())return TEXT("发射");
    if(IsFlying())return TEXT("飞行");
    if(auto* P=Model();P&&P->FireballCooldown()>0)return FString::Printf(TEXT("%.1f"),P->FireballCooldown());
    return TEXT("");
}
float UFPSFireballComponent::CooldownFraction() const
{
    auto* P=Model();if(!P||Active.IsValid())return 0;
    const float Duration=P->FireballCooldownDuration();
    return FMath::Clamp(P->FireballCooldown()/FMath::Max(.1f,Duration),0.f,1.f);
}
void UFPSFireballComponent::Trigger()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* P=Model();
    if(!Player||!P||!Player->IsLocallyControlled()||!GetWorld())return;
    // 联机：客人照常走本地手势与门槛，只有"生球/发射"两个世界效果换成服务端权威。
    const ENetMode NM=GetWorld()->GetNetMode();
    if(NM!=NM_Standalone&&NM!=NM_Client)return;
    if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return;
    if(HasOtherPreparedSpell(this)){bQueuedCast=bQueuedLaunch=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>();Sword && Sword->IsGuarding())Sword->ReleaseGuard();
    if(IsFlying()||HandPhase==EFireballHandPhase::Releasing||HandPhase==EFireballHandPhase::ReadyingRelease)return;
    // Only palm casting is blocked by held left-hand equipment; a held staff
    // selects its own right-hand availability for both gather and release.
    if(Player->IsSpellHandHeld()){RejectHeldLeftHand();return;}
    if(IsPrepared()||bNetExpectOrb)
    {
        // A prepared orb is independent from the hand. Keep one release request,
        // including during gather recovery or an ongoing weapon/tool action.
        // 联机：bNetExpectOrb 覆盖"服务端已凝聚、副本还在路上"的窗口。
        bQueuedLaunch=true;
        if(HandPhase==EFireballHandPhase::None)TryBeginQueuedLaunch();
        return;
    }
    if(IsGestureActive())return;
    if(bQueuedCast)return;
    if(P->FireballCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!P->CanSpendMana(P->FireballStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
    if(!Core||!Trail||!Explosion||!Shockwave){Feedback(TEXT("缺素材"));return;}
    // Do not charge MP or interrupt an existing left-hand action while waiting.
    bQueuedCast=true;TryBeginQueuedCast();
}
void UFPSFireballComponent::TryBeginQueuedCast()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* P=Model();
    if(!bQueuedCast||!Player||!P)return;
    if(HasOtherPreparedSpell(this)){bQueuedCast=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(Player->IsSpellHandHeld()){RejectHeldLeftHand();return;}
    if(Player->IsSpellHandBusy())return;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored())return;
    bQueuedCast=false;
    // The profile may have changed while a reload, swing or ADS was finishing.
    if(P->FireballCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!P->CanSpendMana(P->FireballStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
    // 联机客人：不本地生球——手势照常播，权威 orb 由服务端 spawn 后复制回来认领。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        const float BeforeMana=P->Snapshot().Mana;
        if(!P->BeginFireballCast()){Feedback(TEXT("未施放"));return;}
        RecordGesturePayment(BeforeMana,P->Snapshot().Mana);
        GestureSpeed=P->FireballStats().CastSpeed;
        if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
        bQueuedLaunch=bLaunchCommitted=false;
        bNetExpectOrb=true;NetExpectOrbAt=GetWorld()->GetTimeSeconds();
        SendNetCast(0);
        SetHandPhase(EFireballHandPhase::Raising);
        LastMessage.Reset();MessageUntil=0;
        return;
    }
    auto* Camera=Player->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const FVector Eye=Camera->GetComponentLocation();FVector Position=AFPSFireballProjectile::HoverPosition(Player);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballPrepare),false,Player);FHitResult Wall;
    if(GetWorld()->SweepSingleByChannel(Wall,Eye,Position,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query))Position=Wall.Location;
    if(FVector::Distance(Eye,Position)<35){Feedback(TEXT("受阻"));return;}
    FActorSpawnParameters Spawn;Spawn.Owner=Player;Spawn.Instigator=Player;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ball=GetWorld()->SpawnActor<AFPSFireballProjectile>(Position,FRotator::ZeroRotator,Spawn);
    if(!Ball)return;
    const FFireballCast Snapshot=P->FireballStats();
    const float BeforeMana=P->Snapshot().Mana;
    if(!P->BeginFireballCast()){Ball->Destroy();Feedback(TEXT("未施放"));return;}
    RecordGesturePayment(BeforeMana,P->Snapshot().Mana);
    GestureSpeed=Snapshot.CastSpeed;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    Active=Ball;
    bQueuedLaunch=bLaunchCommitted=false;SetHandPhase(EFireballHandPhase::Raising);
    bStaffOrb=IsStaffCasting();
    StaffOrbHover=StaffCastMotion::Focus(bStaffOrb&&CastingStaff.IsValid()?
        StaffChargeFlow::Settled(*CastingStaff.Get()):StaffCastMotion::Raised());
    Ball->Prepare(this,Player,Snapshot,Core,Trail,Explosion,Shockwave,ImpactSound);
    LastMessage.Reset();MessageUntil=0;
}
void UFPSFireballComponent::TryBeginQueuedLaunch()
{
    if(!bQueuedLaunch || HandPhase!=EFireballHandPhase::None)return;
    if(!IsPrepared()&&!bNetExpectOrb){bQueuedLaunch=false;return;}
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player)return;
    if(Player->IsSpellHandHeld()){RejectHeldLeftHand();return;}
    if(Player->IsSpellHandBusy())return;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC || PC->IsLookInputIgnored() || PC->IsMoveInputIgnored())return;
    // Capture the current weapon's hand pose again; it may have changed while
    // the detached orb was hovering. This does not reserve MP or spawn a new orb.
    bQueuedLaunch=false;bLaunchCommitted=false;
    const auto* P=Model();
    GestureSpeed=Active.IsValid()?Active->Snapshot().CastSpeed:P?P->FireballStats().CastSpeed:1.f;
    SetHandPhase(EFireballHandPhase::ReadyingRelease);
    LastMessage.Reset();MessageUntil=0;
}
void UFPSFireballComponent::LaunchAtContact()
{
    if(GestureOwner.IsValid())
    {if(!bLaunchCommitted){bLaunchCommitted=true;GestureContact.ExecuteIfBound();GestureContact.Unbind();}return;}
    if(bLaunchCommitted||(!IsPrepared()&&!bNetExpectOrb))return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Camera=Player?Player->FindComponentByClass<UCameraComponent>():nullptr;
    if(!Camera)return;
    // 联机客人：发射意图上报——服务端权威球按上报瞄准点起飞，本地不驱动弹道。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        SendNetCast(1,FPSMagicPreview::AimPoint(Player,Active.Get()));
        bLaunchCommitted=true;bQueuedLaunch=false;bNetExpectOrb=false;
        return;
    }
    if(!IsPrepared())return;
    Active->Launch();
    bLaunchCommitted=true;bQueuedLaunch=false;
}
void UFPSFireballComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // Also covers empty hands and traversal's short weapon-stow/retract gaps.
    ON_SCOPE_EXIT { UpdateFallbackHands(); };
    if(auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {
        if(!GestureOwner.IsValid())
        {
            if(!bLaunchCommitted&&GesturePaidMana>0.f)
                if(auto* P=Model())P->RefundUnreleasedCast(GesturePaidMana,TEXT("fireball"));
            GesturePaidMana=0.f;
        }
        Cancel();return;
    }
    // 联机：Prepare 已上报但服务端球迟迟未达（丢包/拒绝未回执）——超时本地收尾。
    if(bNetExpectOrb&&!Active.IsValid()&&GetWorld()&&GetWorld()->GetTimeSeconds()-NetExpectOrbAt>2.5)
    {
        bNetExpectOrb=false;
        if(auto* P=Model())P->RefundUnreleasedCast(TakeGesturePayment(),TEXT("fireball"));
        if(!GestureOwner.IsValid()&&HandPhase!=EFireballHandPhase::None&&HandPhase!=EFireballHandPhase::Recovering)
            SetHandPhase(EFireballHandPhase::Recovering);
        Feedback(TEXT("施法超时"));
    }
    if(bQueuedCast){TryBeginQueuedCast();return;}
    if(HandPhase==EFireballHandPhase::None){TryBeginQueuedLaunch();return;}
    PhaseAge+=Delta*GestureSpeed;
    // Carry frame overshoot between phases so the timing is not frame-rate dependent.
    for(int32 Transition=0;Transition<3;++Transition)
    {
        if(HandPhase==EFireballHandPhase::Raising)
        {
            const float Raise=GesturePhaseDuration(EFireballHandPhase::Raising);
            if(PhaseAge<Raise)return;
            const float Remainder=PhaseAge-Raise;
            // Buff spells can apply on the completed palm-up gathering pose.
            // Other gathering clients pass an empty delegate and retain their own logic.
            if(GestureOwner.IsValid()&&GestureContact.IsBound())LaunchAtContact();
            SetHandPhase(!GestureOwner.IsValid()&&bQueuedLaunch?EFireballHandPhase::Releasing:EFireballHandPhase::Recovering);
            PhaseAge=FMath::Max(0.f,Remainder);
        }
        else if(HandPhase==EFireballHandPhase::ReadyingRelease)
        {
            const float EntryDuration=GesturePhaseDuration(EFireballHandPhase::ReadyingRelease);
            if(PhaseAge<EntryDuration)return;
            const float Remainder=PhaseAge-EntryDuration;
            SetHandPhase(EFireballHandPhase::Releasing);PhaseAge=Remainder;
        }
        else if(HandPhase==EFireballHandPhase::Releasing)
        {
            const float ContactAge=ReleaseContactAge();
            if(PhaseAge>=ContactAge)LaunchAtContact();
            // Each gesture uses its own movement/contact clock; endpoint holds
            // retain real duration while the moving stages use casting haste.
            const float ReleaseEnd=ReleaseEndAge();
            if(PhaseAge<ReleaseEnd)return;
            const float Remainder=PhaseAge-ReleaseEnd;
            SetHandPhase(EFireballHandPhase::Recovering);PhaseAge=FMath::Max(0.f,Remainder);
        }
        else if(HandPhase==EFireballHandPhase::Recovering)
        {
            if(PhaseAge>=GesturePhaseDuration(EFireballHandPhase::Recovering))
            {SetHandPhase(EFireballHandPhase::None);GestureOwner.Reset();GestureContact.Unbind();GestureSpeed=1.f;}
            return;
        }
        else return;
    }
}
void UFPSFireballComponent::ProjectileFinished(AFPSFireballProjectile* Projectile)
{
    if(Active.Get()!=Projectile)return;
    if(Projectile&&Projectile->IsFlying())
    {
        const auto& Spell=Projectile->Snapshot();
        const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!Health||!Health->IsDead())
        {auto* Status=UCombatStatusFormula::GetOrAdd(GetOwner());if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
    }
    Active.Reset();bQueuedLaunch=false;bAimPreview=false;bStaffOrb=false;
    // Expiry/cancellation while gathering also gives the hand a recovery phase.
    if(!GestureOwner.IsValid()&&(HandPhase==EFireballHandPhase::Raising || HandPhase==EFireballHandPhase::ReadyingRelease ||
       (HandPhase==EFireballHandPhase::Releasing && !bLaunchCommitted)))SetHandPhase(EFireballHandPhase::Recovering);
    if(auto* P=Model())P->FinishFireballCast();
}
void UFPSFireballComponent::Cancel()
{
    GestureOwner.Reset();GestureContact.Unbind();GestureSpeed=1.f;
    bQueuedCast=bQueuedLaunch=bLaunchCommitted=false;
    bAimPreview=false;bStaffOrb=false;
    ReleaseOrb();SetHandPhase(EFireballHandPhase::None);
    if(FallbackHands)FallbackHands->SetVisibility(false);
}
void UFPSFireballComponent::ReleaseOrb()
{
    // 与单机退款语义一致：凝聚/预备手势期打断退蓝清冷却；已凝聚的悬停球弃置只清占用。
    const uint8 AbortPhase=(HandPhase==EFireballHandPhase::Raising||HandPhase==EFireballHandPhase::ReadyingRelease)?2:3;
    if(Active.IsValid())
    {
        // 服务端权威球：本地 Destroy 只毁副本，真取消要 RPC 到服务端销毁+影子档结算。
        if(Active->HasAuthority())Active->Destroy();else SendNetCast(AbortPhase);
        Active.Reset();
    }
    if(bNetExpectOrb){bNetExpectOrb=false;SendNetCast(2);}
}
void UFPSFireballComponent::EndPlay(const EEndPlayReason::Type Reason)
{ Cancel();Super::EndPlay(Reason); }

bool UFPSFireballComponent::TryBeginSpellGesture(UActorComponent* Spell,bool bRelease,float Speed,const FSimpleDelegate& Contact,bool bPowerFist)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Spell||!Player||HasOtherPreparedSpell(Spell)||BlocksNewLeftHandAction()||Player->IsSpellHandBusy())return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored())return false;
    GestureOwner=Spell;GestureContact=Contact;GestureSpeed=FMath::Max(.1f,Speed);bLaunchCommitted=false;
    GesturePaidMana=0.f;bDirectCastWindup=false;
    bPowerFistGesture=bPowerFist&&bRelease;PowerFistRecoveryStartAge=0.f;
    SetHandPhase(bRelease?EFireballHandPhase::ReadyingRelease:EFireballHandPhase::Raising);return true;
}

void UFPSFireballComponent::RecordGesturePayment(float BeforeMana,float AfterMana,bool bDirectCast)
{
    GesturePaidMana=FMath::Max(0.f,BeforeMana-AfterMana);
    bDirectCastWindup=bDirectCast;
}

void UFPSFireballComponent::InterruptForPriority()
{
    UActorComponent* Spell=GestureOwner.Get();
    const EFireballHandPhase Phase=HandPhase;
    // A one-step spell's ready pose is its gathering windup. For an already
    // hovering projectile the same pose begins release, so its cost is retained.
    const bool Gathering=Phase==EFireballHandPhase::Raising ||
        (bDirectCastWindup && Phase==EFireballHandPhase::ReadyingRelease);
    const bool PendingContact=Gathering || Phase==EFireballHandPhase::ReadyingRelease ||
        (Phase==EFireballHandPhase::Releasing && !bLaunchCommitted);
    const float Refund=Gathering&&!bLaunchCommitted?GesturePaidMana:0.f;
    GesturePaidMana=0.f;bDirectCastWindup=false;
    FName Unreleased=NAME_None;
    if(auto* Electric=GetOwner()->FindComponentByClass<UFPSElectricMagicComponent>();Electric&&!Electric->UnreleasedSkill().IsNone())Unreleased=Electric->UnreleasedSkill();
    else if(auto* Holy=GetOwner()->FindComponentByClass<UFPSHolyLightComponent>();Holy&&Holy->HasUnreleasedCast())Unreleased=TEXT("holyLight");
    else if(auto* Lightning=GetOwner()->FindComponentByClass<UFPSLightningComponent>();Lightning&&Lightning->HasUnreleasedCast())Unreleased=TEXT("lightning");
    else if(auto* FireMagic=GetOwner()->FindComponentByClass<UFPSFireMagicComponent>();FireMagic&&!FireMagic->UnreleasedSkill().IsNone())Unreleased=FireMagic->UnreleasedSkill();
    else if(Refund>0.f&&!Spell)Unreleased=TEXT("fireball");
    // Unbind BEFORE destroying a prepared entity. Its EndPlay callback must
    // never advance a stale release or restore a hand recovery over the winner.
    GestureContact.Unbind();GestureOwner.Reset();GestureSpeed=1.f;
    bQueuedCast=bQueuedLaunch=false;SetAimPreview(false);
    SetHandPhase(EFireballHandPhase::None);
    if(auto* Ice=GetOwner()->FindComponentByClass<UFPSIceSpikeComponent>())Ice->InterruptPending(Spell==Ice&&PendingContact);
    if(auto* IceWall=GetOwner()->FindComponentByClass<UFPSIceWallComponent>())IceWall->InterruptPending(Spell==IceWall&&PendingContact);
    if(auto* Lightning=GetOwner()->FindComponentByClass<UFPSLightningComponent>())Lightning->InterruptPending();
    if(auto* Electric=GetOwner()->FindComponentByClass<UFPSElectricMagicComponent>())Electric->CancelPending(false);
    if(auto* HolyLight=GetOwner()->FindComponentByClass<UFPSHolyLightComponent>())HolyLight->InterruptPending();
    if(auto* FireMagic=GetOwner()->FindComponentByClass<UFPSFireMagicComponent>())FireMagic->CancelPending();
    if(auto* Blizzard=GetOwner()->FindComponentByClass<UFPSBlizzardComponent>())Blizzard->InterruptPending(Spell==Blizzard&&PendingContact);
    if(auto* Blades=GetOwner()->FindComponentByClass<URuneOrbBladesComponent>())Blades->InterruptPending(Spell==Blades&&Gathering);
    if(!Spell && PendingContact && (IsPrepared()||bNetExpectOrb)){ReleaseOrb();Feedback(TEXT("施法中断"));}
    bLaunchCommitted=false;
    if(FallbackHands)FallbackHands->SetVisibility(false);
    if(auto* P=Model();P&&(Refund>0.f||!Unreleased.IsNone()))P->RefundUnreleasedCast(Refund,Unreleased);
}
// ============================================================================
// 联机：施法意图通道（A 模式打样——意图上报、服务端执行、表现靠 actor 复制回流）
// ============================================================================
AColdSteelPlayerState* UFPSFireballComponent::NetPlayerState() const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    return P?P->GetPlayerState<AColdSteelPlayerState>():nullptr;
}
void UFPSFireballComponent::SendNetCast(uint8 Phase,const FVector& AimPoint)
{
    if(!GetWorld()||GetWorld()->GetNetMode()!=NM_Client)return;
    if(auto* PS=NetPlayerState())
    {
        FColdSteelNetCastRequest R;
        R.SkillId=TEXT("fireball");R.Phase=Phase;R.AimPoint=AimPoint;
        PS->ServerCastSpell(R);
    }
}
AFPSFireballProjectile* UFPSFireballComponent::SpawnOrbForCast(APawn* Caster,const FFireballCast& Stats)
{
    if(!Caster||!GetWorld()||!Core||!Trail||!Explosion||!Shockwave)return nullptr;
    FActorSpawnParameters Spawn;Spawn.Owner=Caster;Spawn.Instigator=Caster;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ball=GetWorld()->SpawnActor<AFPSFireballProjectile>(AFPSFireballProjectile::HoverPosition(Caster),FRotator::ZeroRotator,Spawn);
    if(Ball)Ball->Prepare(this,Caster,Stats,Core,Trail,Explosion,Shockwave,ImpactSound);
    return Ball;
}
void UFPSFireballComponent::AttachPresentationAssets(AFPSFireballProjectile* Ball) const
{
    if(Ball)Ball->SetPresentationAssets(Core,Trail,Explosion,Shockwave,ImpactSound);
}
void UFPSFireballComponent::AdoptNetOrb(AFPSFireballProjectile* Ball)
{
    if(!Ball||Active.Get()==Ball)return;
    Active=Ball;bNetExpectOrb=false;
}
void UFPSFireballComponent::NetCastRejected(uint8 Phase,uint8 /*Code*/)
{
    if(Phase!=0)return; // 发射/取消被拒只记日志；未凝聚才需要本地收尾。
    bNetExpectOrb=false;
    if(auto* P=Model())P->RefundUnreleasedCast(TakeGesturePayment(),TEXT("fireball"));
    if(!GestureOwner.IsValid()&&HandPhase!=EFireballHandPhase::None&&HandPhase!=EFireballHandPhase::Recovering)
        SetHandPhase(EFireballHandPhase::Recovering);
    Feedback(TEXT("未施放"));
}
void UFPSFireballComponent::NetCastCancelled(uint8 Phase)
{
    // 与服务端同口径：凝聚期取消退蓝清冷却；已凝聚弃球只清占用、冷却照跑。
    if(auto* P=Model())
    {
        if(Phase==2)P->RefundUnreleasedCast(TakeGesturePayment(),TEXT("fireball"));
        else P->FinishFireballCast();
    }
    bNetExpectOrb=false;
}
void UFPSFireballComponent::CancelSpellGesture(UActorComponent* Spell)
{
    if(GestureOwner.Get()!=Spell)return;
    GestureContact.Unbind();
    if(HandPhase!=EFireballHandPhase::Recovering)SetHandPhase(EFireballHandPhase::Recovering);
}
bool UFPSFireballComponent::ContinueSpellRelease(UActorComponent* Spell,float HoldSeconds,bool bAddImpact)
{
    if(!Spell||GestureOwner.Get()!=Spell||bPowerFistGesture||HandPhase!=EFireballHandPhase::Releasing||!bLaunchCommitted)return false;
    ReleaseHoldEndAge=FMath::Max(ReleaseHoldEndAge,PhaseAge+FMath::Max(0.f,HoldSeconds)*GestureSpeed);
    if(bAddImpact)
    {
        // Superpose impulses: resetting the first impulse mid-recoil would pop the wrist.
        ReleaseImpactAges.RemoveAll([this](float Age){return PhaseAge-Age>=FireballCastMotion::ImpactDuration;});
        ReleaseImpactAges.Add(PhaseAge);
    }
    return true;
}
void UFPSFireballComponent::SetAimPreview(bool bActive)
{
    // Only a hovering orb previews; during the gather the press keeps its old meaning
    // (queue the launch), so a second press while charging is never swallowed.
    if(bActive&&(!IsPrepared()||bQueuedLaunch||HandPhase==EFireballHandPhase::Raising
        ||HandPhase==EFireballHandPhase::ReadyingRelease||HandPhase==EFireballHandPhase::Releasing))return;
    bAimPreview=bActive;
    if(auto* Ball=Active.Get())Ball->SetAimPreviewActive(bAimPreview);
}
void UFPSFireballComponent::ReleaseAimPreview()
{
    if(!bAimPreview||!IsPrepared())return;
    Active->CommitAimPreview();bAimPreview=false;
    Trigger();
    // A rejected request releases the snapshot; menus/cancellation use
    // SetAimPreview(false), which must never commit a cast by itself.
    if(!bQueuedLaunch&&HandPhase!=EFireballHandPhase::ReadyingRelease)
        if(auto* Ball=Active.Get())Ball->SetAimPreviewActive(false);
}
