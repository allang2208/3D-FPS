#include "OffhandKukriComponent.h"
#include "OffhandKukriAuthoredPose.h"
#include "OffhandKukriAuthoredUppercut.h"
#include "KukriRhythm.h"
#include "../MeleeSmallTargetQuery.h"
#include "../MeleeWeaponStats.h"
#include "../RuneSwordUppercutMotion.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Skills/SwordUppercutTuning.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/BoundCongregateCaptureComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"

// Uppercut (active skill swordUppercut) for the pistol + offhand kukri pair: the main-hand kukri's
// slide uppercut (KukriUppercut.cpp, BV1CeYUeSE7b #9 106.2-107.3 s) mirrored onto the left hand.
// author_upper.py conjugates the Uppercut clip across the camera's left-right plane: the clip's
// right hand becomes the left swing hand and its left balance hand becomes the gun hand's evade
// path (出手时右手避让), baked into the same key record (OffhandKukriAuthoredUppercut.h).  The skill
// contract is the sword uppercut's unchanged: CommitSwordUppercutRelease pays stamina and starts
// the cooldown when the cut starts, damage is the uppercut multiplier of the heavy formula
// (SwordUppercut::HeavyDamageScale), AttackMeta SwordUppercut::AttackMeta (shared forced launch and
// the 0x14 server receipt on the declared OFF-HAND item), single target, one training tier per cast.
// Martial clock: Lightning Haste x KukriRhythm::UpperTempo (stage 3).  The camera is the stage-3
// reference curve mirrored (yaw/roll negated); the rift is the mirrored crescent (camera space).
// The forward stride rides the shared melee-lunge movement like the main-hand version (120 cm).

namespace
{
constexpr float LungeStart=.24f,LungeEnd=.37f,LungeCM=120.f;   // author s; <= the 150 cm server budget
const TCHAR* OffhandUpperWallPath=TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02");

UE::Geometry::FDynamicMesh3 BuildUpperRift()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    constexpr int32 N=OffhandKukriUpper::RiftStations;
    for(int32 S=0;S<N;++S)
        for(int32 E=0;E<2;++E)
        {
            const float* P=OffhandKukriUpper::Rift[S][E];
            Mesh.AppendVertex(FVector3d(P[0],P[1],P[2]));
            UV->AppendElement(FVector2f(float(S)/(N-1),float(E)));
            Normals->AppendElement(FVector3f(0.f,0.f,1.f));   // unlit two-sided material: the normal is unused
        }
    for(int32 S=0;S<N-1;++S)
    {
        const int32 A=S*2;
        for(const FIndex3i T:{FIndex3i(A,A+2,A+1),FIndex3i(A+1,A+2,A+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    return Mesh;
}
}

FString UOffhandKukriComponent::UppercutStatusText() const
{
    if(!bEquipped)return TEXT("需要持刀");
    if(bUppercut)return TEXT("上挑中");
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!Model.IsValid()||!bPair)return TEXT("暂不可用");
    if(Model->SwordUppercutCooldown()>0.f)return TEXT("冷却中");
    if(!Model->CanSpendStamina(Model->SwordUppercutStaminaCost()))return TEXT("体力不足");
    if(bQuickCombat||P->IsWeaponBusy())return TEXT("动作中");
    if(P->IsCastBlockingLeftHandAction()||P->IsDodging()||P->IsSpellGestureBlocking()||P->IsSprinting()||P->IsAiming())
        return TEXT("动作占用");
    if(!OwnsLeftHand())return TEXT("动作占用");
    return FString();
}

bool UOffhandKukriComponent::BeginUppercut()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||UBoundCongregateCaptureComponent::IsCaptured(P)||!UppercutStatusText().IsEmpty())return false;
    auto* Profile=Model.Get();
    const auto State=Profile?Profile->Snapshot():FColdSteelProfile();
    const auto* Item=Profile?Profile->Equipped(State.ActiveWeaponSlot==6?8:11):nullptr;
    if(!Item||!IsOffhandKukri(*Item)||Profile->ActiveProductionTool())return false;
    // Snapshot at the start: damage, reach and skill tier stay fixed for this cast (the cost is paid at the release).
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    const auto Effect=Profile->MasteryEffect(TEXT("swordUppercut"));
    UpperDamage=float(Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers));
    UpperReach=float((Stats.BaseReach>0.?Stats.BaseReach:KukriRhythm::DefaultReachCM)*Effect.UppercutReachMultiplier*Stats.Modifiers.MartialRange);
    UpperShot=ColdSteelSkills::Snapshot(P,Item);
    UpperShot.bRifle=false;UpperShot.bPistol=false;UpperShot.WeakpointPercent=0;UpperShot.bMelee=true;UpperShot.bMeleeStrike=true;
    UpperShot.AttackForm=KukriRhythm::Form;
    UpperShot.AttackMeta=SwordUppercut::AttackMeta;   // heavy formula family + the shared forced launch
    UpperShot.ToughnessDamageMultiplier*=float(Stats.Modifiers.HeavyToughness);
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    WallSound=LoadObject<USoundBase>(nullptr,OffhandUpperWallPath);
    WhooshSound=LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    ThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))ThudSounds.Add(Thud);
    bUppercut=true;bUppercutReleased=bUppercutTrainingPending=false;bUppercutLungeStarted=bUppercutLungeBlocked=false;
    UppercutDirection=FVector::ZeroVector;
    bUpperSwingPlayed=bUpperImpactConfirmed=bUpperWallHit=false;
    UppercutElapsed=0.f;UppercutHitStop=0.f;UppercutImpactAge=-1.f;UppercutStrikeAge=-1.f;UppercutImpactKick=0.f;
    ResetUpperStrike();UpperHitActors.Reset();
    UpperPreviousBlade=UpperBladeFrame(0.f);bHaveUpperPreviousBlade=true;
    StopUpperRift();bUpperRiftStarted=false;
    return true;
}

FTransform UOffhandKukriComponent::UpperBladeFrame(float T) const
{
    // The authored left-hand frame at author time T (the visible mesh is a tick behind), in world space.
    if(!Camera.IsValid())return FTransform::Identity;
    FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Framing;
    OffhandKukriUpper::SamplePose(T,Wrist,Hand,Shoulder,Pole,Framing);
    const FVector HandPos=Arms?Arms->RightHandInCamera:FVector::ZeroVector;
    const FTransform HandFrame(Hand,HandPos+Wrist);
    const bool ForwardGrip=T>=OffhandKukriUpper::DigitsAt&&T<=OffhandKukriUpper::DigitsEnd;
    // FTransform composes left to right (A*B applies A first): blade -> hand (camera space) -> world.
    return (ForwardGrip?OffhandKukriUpper::KukriInHand:OffhandKukriPose::KukriInHand)*HandFrame*Camera->GetComponentTransform();
}

void UOffhandKukriComponent::AdvanceUppercutLunge(float From,float To)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!P->IsLocallyControlled()||bUppercutLungeBlocked||To<=LungeStart||From>=LungeEnd)return;
    const float Distance=LungeCM*(FMath::SmoothStep(LungeStart,LungeEnd,To)-FMath::SmoothStep(LungeStart,LungeEnd,From));
    if(Distance<=0.f)return;
    auto* Move=Cast<UFPSCharacterMovementComponent>(P->GetCharacterMovement());
    if(!Move||!Move->IsMovingOnGround()||P->IsSliding()||P->IsTraversing()||Move->IsDodging()){bUppercutLungeBlocked=true;return;}
    if(!bUppercutLungeStarted)
    {
        bUppercutLungeStarted=true;
        UppercutDirection=P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Uppercut,UppercutDirection);
    }
    if(Move->IsMeleeLungeRejected()){bUppercutLungeBlocked=true;return;}
    const FVector Moved=Move->ApplyMeleeLungeStep(UppercutDirection,Distance);
    const float Actual=FMath::Max(0.f,float(FVector::DotProduct(Moved,UppercutDirection)));
    Move->RecordMeleeLungeStep(Actual);
    // The rift crescent rides along with the stride (it is frozen in world space at its start).
    if(bUpperRiftActive)UpperRiftOrigin.AddToTranslation(Moved);
    if(Actual+.01f<Distance)bUppercutLungeBlocked=true;
}

void UOffhandKukriComponent::AdvanceUppercut(float Delta)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Profile=Model.Get();
    const auto State=Profile?Profile->Snapshot():FColdSteelProfile();
    const auto* Item=Profile?Profile->Equipped(State.ActiveWeaponSlot==6?8:11):nullptr;
    if(!P||!Item||!IsOffhandKukri(*Item)){CancelUppercut();return;}
    const auto& S=KukriRhythm::Swings[KukriRhythm::UppercutStage];
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    // The impact rattle and the contact accent are real time; the hit-stop freezes the author clock.
    if(UppercutImpactAge>=0.f)UppercutImpactAge+=Delta;
    if(UppercutStrikeAge>=0.f)UppercutStrikeAge+=Delta;
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bUppercut&&++Guard<64)
    {
        if(UppercutHitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,UppercutHitStop);
            UppercutHitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float StageRate=Rate*KukriRhythm::StageTempo(KukriRhythm::UppercutStage,UppercutElapsed);
        float Step=FMath::Min(Remaining*StageRate,1.f/120.f);
        const float StrikeAt=KukriRhythm::Strikes[KukriRhythm::UppercutStage].At;
        const float RiftAt=KukriRhythm::Rifts[KukriRhythm::UppercutStage].Start;
        for(const float Boundary:{S.SwingSound,S.ContactStart,S.ContactEnd,StrikeAt,RiftAt,OffhandKukriUpper::Length})
            if(UppercutElapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-UppercutElapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=UppercutElapsed;
        UppercutElapsed=FMath::Min(OffhandKukriUpper::Length,UppercutElapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(UppercutElapsed-Before)/StageRate);
        // Release: stamina and cooldown are committed when the cut starts (as for the sword); a refused
        // payment (cooldown, stamina, a server rejection) cancels the cast before anything lands.
        if(!bUppercutReleased&&UppercutElapsed>=S.ContactStart-UE_KINDA_SMALL_NUMBER)
        {
            if(!Profile->CommitSwordUppercutRelease()){CancelUppercut();return;}
            bUppercutReleased=bUppercutTrainingPending=true;
        }
        AdvanceUppercutLunge(Before,UppercutElapsed);
        const FTransform Now=UpperBladeFrame(UppercutElapsed);
        if(!bUpperSwingPlayed&&UppercutElapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bUpperSwingPlayed=true;
            const bool bWhoosh=KukriRhythm::Strikes[KukriRhythm::UppercutStage].bWhoosh&&WhooshSound;
            if(USoundBase* Cue=bWhoosh?WhooshSound.Get():SwingSound.Get())
                UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume:.6f,S.SwingPitch);
            if(bWhoosh&&SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.45f,S.SwingPitch*.9f);
        }
        if(bUppercutReleased&&bHaveUpperPreviousBlade&&Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd)
            UppercutTrace(UpperPreviousBlade,Now);
        UpperPreviousBlade=Now;bHaveUpperPreviousBlade=true;
        if(StrikeAt>0.f&&!bUpperStrikeDone&&UppercutElapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveUpperStrike();
        if(!bUpperRiftStarted&&UppercutElapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bUpperRiftStarted=true;StartUpperRift();}
        if(bUppercutTrainingPending&&UppercutElapsed>=S.ContactEnd-UE_KINDA_SMALL_NUMBER)FinishUppercut(true);
        if(UppercutElapsed>=OffhandKukriUpper::Length-UE_KINDA_SMALL_NUMBER)
        {
            bUppercut=false;UpperHitActors.Reset();
            FinishUppercut(true);
        }
    }
}

void UOffhandKukriComponent::UppercutTrace(const FTransform& From,const FTransform& To)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    UWorld* World=GetWorld();
    if(!P||!World)return;
    const FTransform Aim=P->GetMeleeAimTransform();
    const FVector Probe=To.TransformPosition(KukriRhythm::BladeMid);
    TArray<FHitResult,TInlineAllocator<8>> Contacts;
    // Targets: forward area from the blade's current position (cleave, low targets, cover).
    const float Forward=FVector::DotProduct(Probe-Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X));
    if(Forward>=0.f)
        Contacts.Append(MeleeSmallTargets::QueryQuickAreaContacts(World,P,Aim,Probe,FMath::Max(40.f,UpperReach-Forward),KukriRhythm::QueryRadiusCM));
    // Scenery: the real edge from root to tip, swept between substeps.  The follow-through carries the blade up past
    // the head, so the player's own attached gear and anything at the eye are not scenery (no block clang there).
    FCollisionQueryParams Q(SCENE_QUERY_STAT(OffhandKukriUppercut),false,GetOwner());
    TArray<AActor*> OwnGear;GetOwner()->GetAttachedActors(OwnGear,true,true);Q.AddIgnoredActors(OwnGear);
    for(const auto& Actor:UpperHitActors)if(Actor.IsValid())Q.AddIgnoredActor(Actor.Get());
    for(int32 Segment=0;Segment<=3;++Segment)
    {
        const FVector Local=FMath::Lerp(KukriRhythm::BladeRoot,KukriRhythm::BladeTip,Segment/3.f);
        FHitResult Hit;
        if(World->SweepSingleByChannel(Hit,From.TransformPosition(Local),To.TransformPosition(Local),FQuat::Identity,
            ECC_Visibility,FCollisionShape::MakeSphere(2.5f),Q))
            if(const auto* Actor=Hit.GetActor();Actor&&!Actor->FindComponentByClass<UMonsterCombatComponent>()&&Actor->GetOwner()!=GetOwner()
                &&FVector::DotProduct(Hit.ImpactPoint-Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X))>=20.f)
                Contacts.Add(Hit);
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const auto& Hit:Contacts)
    {
        auto* Actor=Hit.GetActor();
        if(!Actor||Actor->ActorHasTag(TEXT("Friendly"))||UpperHitActors.Contains(Actor))continue;
        const FVector Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
        auto* Combat=Actor->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)
        {
            UWardBreakableGlass::BreakHit(Hit,Direction);
            // Scenery comes back on every substep while the blade rests against it: one cue and one burst per swing.
            const bool bFirstWall=!bUpperWallHit&&!bUpperImpactConfirmed&&!bUpperPendingWall;
            ConfirmUpperImpact(Hit,true);
            if(bFirstWall)QueueUpperFX(Hit,true);
            continue;
        }
        // Single target, like the sword and hammer uppercuts.
        if(!UpperHitActors.IsEmpty())break;
        UpperHitActors.Add(Actor);
        if(Combat->IsDead())continue;
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,UpperDamage,Direction,UpperShot,&Receipt);
        if(Applied>0.f||Combat->IsDead())
        {
            ConfirmUpperImpact(Hit,false);
            QueueUpperFX(Hit,false);
            P->NotifyConfirmedWeaponHit(Actor,Applied,&Receipt,false);
        }
    }
}

void UOffhandKukriComponent::ConfirmUpperImpact(const FHitResult& Hit,bool bWorld)
{
    const auto& K=KukriRhythm::Strikes[KukriRhythm::UppercutStage];
    if(K.At>0.f&&!bUpperStrikeDone)
    {
        // Found before the impact moment -- the cue waits for it (ArriveUpperStrike); damage already applied.
        if(bWorld){if(!bUpperPendingWall){bUpperPendingWall=true;UpperPendingWallHit=Hit;}}
        else if(!bUpperPendingFlesh){bUpperPendingFlesh=true;UpperPendingFleshHit=Hit;}
        return;
    }
    if(bWorld)
    {
        if(bUpperWallHit||bUpperImpactConfirmed)return;
        bUpperWallHit=true;UppercutHitStop=KukriRhythm::WallStopSeconds;UppercutImpactAge=0.f;UppercutImpactKick=.7f;
        if(WallSound)UGameplayStatics::PlaySoundAtLocation(this,WallSound,Hit.ImpactPoint,.55f,1.15f);
        return;
    }
    // One confirmed-hit cue per swing; every target still gets its own damage receipt.
    if(bUpperImpactConfirmed)return;
    bUpperImpactConfirmed=true;
    UppercutHitStop=KukriRhythm::FleshStopSeconds*KukriRhythm::Swings[KukriRhythm::UppercutStage].HitStopScale;
    UppercutImpactAge=0.f;
    UppercutImpactKick=KukriRhythm::ImpactKick*KukriRhythm::Swings[KukriRhythm::UppercutStage].ImpactScale;
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.95f,1.04f);
    if(ThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,ThudSounds[FMath::RandRange(0,ThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch);
}

void UOffhandKukriComponent::ResetUpperStrike()
{
    bUpperStrikeDone=false;bUpperPendingFlesh=false;bUpperPendingWall=false;bUpperRiftStarted=false;
    UpperPendingFX.Reset();
}

void UOffhandKukriComponent::ArriveUpperStrike()
{
    bUpperStrikeDone=true;
    // The arrival accent is real time: it keeps going through the hit-stop that freezes the author clock.
    UppercutStrikeAge=0.f;
    if(bUpperPendingFlesh){bUpperPendingFlesh=false;ConfirmUpperImpact(UpperPendingFleshHit,false);}
    else if(bUpperPendingWall){bUpperPendingWall=false;ConfirmUpperImpact(UpperPendingWallHit,true);}
    else if(!bUpperImpactConfirmed&&!bUpperWallHit)
    {
        // A miss still stops dead: a short freeze and a light jolt instead of the flesh hit-stop.
        UppercutHitStop=FMath::Max(UppercutHitStop,KukriRhythm::Strikes[KukriRhythm::UppercutStage].MissStop);
        UppercutImpactAge=0.f;UppercutImpactKick=KukriRhythm::StrikeKick;
    }
    for(const auto& Pending:UpperPendingFX)SpawnContactFX(Pending.Hit,Pending.bWorld);
    UpperPendingFX.Reset();
}

void UOffhandKukriComponent::QueueUpperFX(const FHitResult& Hit,bool bWorld)
{
    if(KukriRhythm::Strikes[KukriRhythm::UppercutStage].At>0.f&&!bUpperStrikeDone){UpperPendingFX.Add({Hit,bWorld});return;}
    SpawnContactFX(Hit,bWorld);
}

void UOffhandKukriComponent::FinishUppercut(bool bTrain)
{
    // One training tier per released cast (use / hit / kill), also when it is cancelled after the release.
    if(!bUppercutTrainingPending)return;
    bUppercutTrainingPending=false;
    if(!bTrain)return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Profile=Model.Get();
    if(!P||!Profile)return;
    if(GetNetMode()==NM_Client)
    {
        // The server counted the reported hits of this release (ServerSwordUppercut / SettleSwordUppercut).
        if(auto* PS=P->GetPlayerState<AColdSteelPlayerState>())PS->FinishSwordUppercut();
        return;
    }
    int32 Hits=0,Kills=0;
    for(const auto& Actor:UpperHitActors)
    {
        AActor* Target=Actor.Get();
        const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||!ColdSteelSkills::IsMasteryTrainingTarget(P,Target))continue;
        Hits=1;if(Combat->IsDead())Kills=1;
    }
    Profile->TrainSwordUppercut(Hits,Kills);
}

void UOffhandKukriComponent::CancelUppercut()
{
    if(!bUppercut)return;
    bUppercut=false;
    // A cancelled uppercut keeps its paid release and still trains once (the sword's rule).
    FinishUppercut(true);
    UpperHitActors.Reset();UpperPendingFX.Reset();
    StopUpperRift();
    if(Arms)Arms->UppercutTime=-1.f;
}

void UOffhandKukriComponent::StartUpperRift()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!Camera.IsValid())return;
    if(!UpperRiftVisual)
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        if(!Material)return;
        UpperRiftVisual=NewObject<UDynamicMeshComponent>(P,TEXT("OffhandKukriRift"));
        P->AddInstanceComponent(UpperRiftVisual);
        UpperRiftVisual->SetMobility(EComponentMobility::Movable);
        UpperRiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);UpperRiftVisual->SetGenerateOverlapEvents(false);
        UpperRiftVisual->SetCanEverAffectNavigation(false);UpperRiftVisual->SetCastShadow(false);UpperRiftVisual->SetReceivesDecals(false);
        UpperRiftVisual->SetOnlyOwnerSee(true);UpperRiftVisual->bVisibleInRayTracing=false;UpperRiftVisual->bAffectDistanceFieldLighting=false;
        UpperRiftVisual->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        UpperRiftVisual->RegisterComponent();
        UpperRiftMID=UMaterialInstanceDynamic::Create(Material,this);
    }
    UpperRiftVisual->SetMesh(BuildUpperRift());
    UpperRiftVisual->SetMaterial(0,UpperRiftMID);
    // Freeze the mirrored crescent where the camera is now (the table is camera space), so it
    // stays in the world while the view moves on.
    UpperRiftOrigin=Camera->GetComponentTransform();UpperRiftDirection=Camera->GetForwardVector();
    UpperRiftAge=0.f;UpperRiftFadeAge=-1.f;bUpperRiftActive=true;
    const auto& R=KukriRhythm::Rifts[KukriRhythm::UppercutStage];
    UpperRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),R.Strength);
    UpperRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    UpperRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    UpperRiftVisual->SetWorldTransform(UpperRiftOrigin);
    UpperRiftVisual->SetVisibility(true);
}

void UOffhandKukriComponent::TickUpperRift(float Delta)
{
    if(!bUpperRiftActive||!UpperRiftVisual||!UpperRiftMID)return;
    const auto& R=KukriRhythm::Rifts[KukriRhythm::UppercutStage];
    UpperRiftAge+=Delta;
    // Reveal on the swing's author clock while it plays (frozen through a hit-stop); the fade is real time.
    const float Reveal=bUppercut?FMath::Clamp((UppercutElapsed-R.Start)/FMath::Max(.01f,R.End-R.Start),0.f,1.f):1.f;
    if(Reveal>=1.f&&UpperRiftFadeAge<0.f)UpperRiftFadeAge=0.f;
    else if(UpperRiftFadeAge>=0.f)UpperRiftFadeAge+=Delta;
    const float Recovery=UpperRiftFadeAge<0.f?0.f:FMath::Clamp(UpperRiftFadeAge/R.Dissolve,0.f,1.f);
    if(Recovery>=1.f){StopUpperRift();return;}
    UpperRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),Reveal*1.06f);
    UpperRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f-Recovery*Recovery*(3.f-2.f*Recovery));
    FTransform Pose=UpperRiftOrigin;Pose.AddToTranslation(UpperRiftDirection*(UpperRiftAge*R.DriftCM));
    UpperRiftVisual->SetWorldTransform(Pose);
}

void UOffhandKukriComponent::StopUpperRift()
{
    bUpperRiftActive=false;UpperRiftAge=0.f;UpperRiftFadeAge=-1.f;
    if(UpperRiftVisual)UpperRiftVisual->SetVisibility(false);
}
