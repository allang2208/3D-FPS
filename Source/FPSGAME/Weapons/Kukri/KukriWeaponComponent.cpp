#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriHeavyRhythm.h"
#include "../MeleeWeaponStats.h"
#include "../MeleeSmallTargetQuery.h"
#include "../RuneSwordRhythm.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Skills/ColdSteelSkillRules.h"
// #include "../../Skills/LightningHasteSpeed.h"  // pending parallel task; committed as 1.f below
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Building/VoxelBuildComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
    const TCHAR* KukriPommelHitPath=TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick");
    const TCHAR* KukriWallPath=TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02");
    const FName KukriIdle(TEXT("Idle")),KukriWalk(TEXT("Walk")),KukriRun(TEXT("Run")),KukriEquip(TEXT("Equip"));
    constexpr float KukriWalkReferenceSpeed=360.f;
}

UKukriWeaponComponent::UKukriWeaponComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    // Character movement and camera have settled; the attached rig is sampled once.
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    // The heavy strike's charge / release receipt RPCs (KukriHeavy.cpp); no replicated properties.
    SetIsReplicatedByDefault(true);
}

bool UKukriWeaponComponent::IsKukri(const FColdSteelItem& Item)
{
    return Item.Definition==TEXT("ue_kukri")||ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("kukri");
}

AFPSGAMECharacter* UKukriWeaponComponent::Pawn() const
{
    return Cast<AFPSGAMECharacter>(GetOwner());
}

void UKukriWeaponComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* P=Pawn();
    if(!P){SetComponentTickEnabled(false);return;}
    SetTickGroup(TG_PostPhysics);
    AddTickPrerequisiteActor(P);
    AddTickPrerequisiteComponent(P->GetCharacterMovement());
    Camera=P->FindComponentByClass<UCameraComponent>();
    if(P->IsLocallyControlled())
        if(auto* GI=GetWorld()?GetWorld()->GetGameInstance():nullptr)RefreshEquipment(GI->GetSubsystem<UColdSteelStatusModel>());
}

void UKukriWeaponComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(bUppercut){bUppercut=false;FinishUppercut(true);}
    if(bHeavyAttack){bHeavyAttack=false;FinishHeavy(true);}
    if(Blade)Blade->DestroyComponent();
    if(RiftVisual)RiftVisual->DestroyComponent();
    if(Viewmodel)Viewmodel->DestroyComponent();
    if(JumpRoot)JumpRoot->DestroyComponent();
    Super::EndPlay(Reason);
}

void UKukriWeaponComponent::InitializePresentation()
{
    auto* P=Pawn();
    if(!P||!Camera)return;
    // Airborne presentation stays on its own parent, outside the authored clips.
    JumpRoot=NewObject<USceneComponent>(P,TEXT("KukriJumpPresentation"));
    P->AddInstanceComponent(JumpRoot);JumpRoot->SetupAttachment(Camera);JumpRoot->RegisterComponent();
    Viewmodel=NewObject<UKukriArmsMeshComponent>(P,TEXT("KukriViewmodel"));
    P->AddInstanceComponent(Viewmodel);Viewmodel->SetupAttachment(JumpRoot);
    // The shared sword rig faces camera forward along mesh -Y.
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Viewmodel->SetCanEverAffectNavigation(false);Viewmodel->SetOnlyOwnerSee(true);
    Viewmodel->SetCastShadow(false);Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent();Viewmodel->SetVisibility(false,true);
    // One clock: this component samples the clip; the mesh never ticks by itself.
    Viewmodel->SetComponentTickEnabled(false);
    Blade=NewObject<UStaticMeshComponent>(P,TEXT("KukriBlade"));
    P->AddInstanceComponent(Blade);Blade->SetupAttachment(Viewmodel,TEXT("WPN_root"));
    Blade->SetMobility(EComponentMobility::Movable);Blade->SetOnlyOwnerSee(true);
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);Blade->SetCanEverAffectNavigation(false);
    Blade->SetCastShadow(false);Blade->bReceivesDecals=false;
    // WPN_root carries the rig's 100x import scale; the mesh is authored in centimetres at the grip.
    Blade->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Blade->RegisterComponent();Blade->SetVisibility(false);
}

void UKukriWeaponComponent::RefreshEquipment(UColdSteelStatusModel* Profile)
{
    auto* P=Pawn();
    if(!Profile||!P||!P->IsLocallyControlled())return;
    if(!Viewmodel)InitializePresentation();
    if(!Viewmodel)return;
    const auto* Item=Profile->Equipped();
    const FString NewId=Item&&!Profile->ActiveProductionTool()&&IsKukri(*Item)?Item->InstanceId:FString();
    if(NewId==InstanceId)return;
    CancelAction();
    InstanceId=NewId;
    Viewmodel->SetVisibility(false,true);
    Viewmodel->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
    Viewmodel->ClearEntry();
    if(NewId.IsEmpty())return;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh);
    auto* BladeMesh=LoadObject<UStaticMesh>(nullptr,KukriRhythm::BladeMesh);
    Animations.Reset();
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Run"),TEXT("Equip"),TEXT("Attack"),TEXT("Attack2"),TEXT("Attack3")})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip;
        Animations.Add(FName(Clip),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    bool Complete=Mesh&&BladeMesh;
    for(const auto& Pair:Animations)Complete&=Pair.Value!=nullptr;
    if(!Complete)
    {
        UE_LOG(LogTemp,Error,TEXT("Kukri: viewmodel, blade or clips missing under %s; the kukri stays hidden."),KukriRhythm::Folder);
        InstanceId.Reset();return;
    }
    // Optional: the uppercut skill (swordUppercut) reports "动作未就绪" without its clip.
    Animations.Add(TEXT("Uppercut"),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+TEXT("A_Kukri_Uppercut.A_Kukri_Uppercut"))));
    // Optional: without both heavy clips the left button keeps its plain click (no charge).
    for(const FName Clip:{KukriHeavyRhythm::ChargeClip,KukriHeavyRhythm::ReleaseClip})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip.ToString();
        Animations.Add(Clip,LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    PommelHitSound=LoadObject<USoundBase>(nullptr,KukriPommelHitPath);
    WallSound=LoadObject<USoundBase>(nullptr,KukriWallPath);
    StabWhooshSound=LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    StabThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))StabThudSounds.Add(Thud);
    if(Viewmodel->GetSkeletalMeshAsset()!=Mesh)Viewmodel->SetSkeletalMesh(Mesh);
    Blade->SetStaticMesh(BladeMesh);
    // Equipped sleeves/gloves follow this owner-only rig (modular outfit profile by mesh path).
    Viewmodel->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    CurrentClip=NAME_None;
    bEquipping=true;SetClip(KukriEquip,false,0.f);
    Viewmodel->SetVisibility(CanPresent(),true);
}

bool UKukriWeaponComponent::CanPresent() const
{
    const auto* P=Pawn();
    const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    const auto* Health=P?P->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return PC&&!P->IsTraversing()&&(!Health||!Health->IsDead())&&(!Build||!Build->IsBuilding()||Build->IsPanelOpen());
}

bool UKukriWeaponComponent::CanUse() const
{
    const auto* P=Pawn();
    const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return CanPresent()&&!AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&(!Build||!Build->IsBuilding());
}

void UKukriWeaponComponent::SetClip(FName Name,bool bLoop,float Blend)
{
    if(!Viewmodel)return;
    if(Blend>0.f&&!CurrentClip.IsNone()&&Name!=CurrentClip)Viewmodel->CaptureEntry(Blend);
    CurrentClip=Name;CurrentAnimation=Animations.FindRef(Name);Elapsed=0.f;
    if(!CurrentAnimation)return;
    // Manual-sample contract: play once, freeze, then SetPosition each frame.
    Viewmodel->PlayAnimation(CurrentAnimation,bLoop);Viewmodel->SetPlayRate(0.f);
    SamplePose(0.f);
}

void UKukriWeaponComponent::SamplePose(float Time)
{
    if(!Viewmodel||!CurrentAnimation)return;
    Viewmodel->SetPosition(Time,false);Viewmodel->TickAnimation(0.f,false);Viewmodel->RefreshBoneTransforms();
}

FName UKukriWeaponComponent::LocomotionClip() const
{
    const auto* P=Pawn();
    if(!P)return KukriIdle;
    const auto* Move=P->GetCharacterMovement();
    const bool Ground=!Move||Move->IsMovingOnGround();
    const float Speed=P->GetVelocity().Size2D();
    if(Ground&&P->IsSprinting()&&Speed>300.f)return KukriRun;
    if(Ground&&Speed>40.f)return KukriWalk;
    return KukriIdle;
}

FTransform UKukriWeaponComponent::BladeFrame() const
{
    // The bone frame without its import scale: the grip frame of SM_Kukri in world space.
    if(!Viewmodel)return FTransform::Identity;
    const FTransform Bone=Viewmodel->GetSocketTransform(TEXT("WPN_root"),RTS_World);
    return FTransform(Bone.GetRotation(),Bone.GetLocation());
}

FRotator UKukriWeaponComponent::ViewmodelKick() const
{
    if(bHeavyCharging&&bHeavyFull&&GetWorld())
    {
        // Full heavy charge: a fine tension tremble of the loaded arm until the release.
        const float T=float(GetWorld()->GetTimeSeconds())*2.f*PI*KukriHeavyRhythm::TrembleHz;
        const float A=KukriHeavyRhythm::TrembleDegrees;
        return FRotator(FMath::Sin(T)*A,FMath::Sin(T*1.37f+1.f)*A*.6f,FMath::Sin(T*.71f+2.f)*A*.5f);
    }
    if(ImpactAge<0.f)return FRotator::ZeroRotator;
    const float E=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick;
    // The contact pushes the arm back against its travel: right/down for the first sweep, left/up for the
    // down-right diagonal, left/down for the stab from the lower left (KukriRhythm::FSwing::KickYaw/KickPitch).
    const auto& S=KukriRhythm::Swings[Stage];
    const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
    return FRotator(E*.6f*S.KickPitch+Shake*.5f,E*.8f*S.KickYaw,(-E*.5f+Shake*.8f)*S.KickYaw);
}

void UKukriWeaponComponent::GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;FovDelta=0.f;
    if(!IsEquipped())return;
    // Heavy charge: the raise and the slow load on the charge clip's clock (KukriHeavyRhythm).
    if(bHeavyCharging)KukriHeavyRhythm::ChargeCamera(Elapsed,Rotation,FovDelta);
    if(bAttacking||bUppercut||bHeavyAttack)
    {
        // Same author clock as the clip: contact holds freeze the camera curve with the arm (the uppercut too).
        // The stab (stage 3) also pushes the camera forward along the view.
        KukriRhythm::SwingCamera(Stage,Elapsed,Rotation,FovDelta,&Location);
    }
    if(CameraCarryAge>=0.f)
    {
        // A chained stage starts from the previous stage's camera offset and eases into its own curve.
        const float Keep=1.f-FMath::SmoothStep(0.f,1.f,CameraCarryAge/KukriRhythm::CameraCarrySeconds);
        Rotation+=CameraCarry*Keep;FovDelta+=CameraCarryFov*Keep;
    }
    if(ImpactAge>=0.f)
    {
        // Confirmed hit: short damped shake on top of the swing curve (real time).  The stab rattles its roll
        // harder, like the reference's contact frames (FSwing::HitRoll).
        const float Shake=KukriRhythm::HitShake(ImpactAge)*ImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriRhythm::Swings[Stage].HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        // Contact punch: the view widens for a beat with the hit-stop (V4).
        FovDelta+=KukriRhythm::ImpactEnvelope(ImpactAge)*ImpactKick*1.4f;
    }
    if(StrikeAge>=0.f)
    {
        // Impact-moment accent (hit or miss, real time): the view is carried along the strike for a beat
        // (stab: forward and wider; slashes: with the blade) -- KukriRhythm::Strikes.
        const auto& K=KukriRhythm::Strikes[Stage];
        const float E=KukriRhythm::StrikeEnvelope(StrikeAge);
        FovDelta+=K.AccentFov*E;Location.X+=K.AccentPushCM*E;
        Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw+=K.AccentYaw*E;
    }
}

void UKukriWeaponComponent::BeginPrimaryAttack()
{
    auto* P=Pawn();
    if(!IsEquipped()||!P||!Viewmodel||!CanUse()||bEquipping||bUppercut||bHeavyCharging||bHeavyAttack||P->IsSpellGestureBlocking())return;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(bAttacking)
    {
        // Two-handed cadence (V11): one click buffered after this stage's contact; the next stage starts when
        // this one is back on the stance, so every stage keeps its full recovery as the attack interval.
        if(Elapsed>=KukriRhythm::Swings[Stage].BufferOpen)bQueued=true;
        return;
    }
    // Heavy strike learned: the press starts the charge and the release decides (KukriHeavy.cpp ReleasePrimaryAttack).
    if(CanBeginHeavyCharge()){BeginHeavyCharge();return;}
    StartComboClick();
}

void UKukriWeaponComponent::StartComboClick()
{
    // Shortly after a swing the combo continues; after a pause it starts over (RuneSword NextSlash rule).
    const bool bContinue=LastAttackEnd>=0.&&GetWorld()&&GetWorld()->GetTimeSeconds()-LastAttackEnd<=KukriRhythm::ComboResetSeconds;
    StartAttack(bContinue?NextStage:0);
}

void UKukriWeaponComponent::StartAttack(int32 NewStage)
{
    auto* P=Pawn();
    auto* Profile=GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const auto* Item=Profile?Profile->Equipped():nullptr;
    bQueued=false;
    if(!P||!Item||Item->InstanceId!=InstanceId)return;
    NewStage=FMath::Clamp(NewStage,0,KukriRhythm::SwingCount-1);
    // Camera continuity if a stage is ever entered mid-swing: carry the outgoing offset and blend it out.
    // (V11 stages hand over on the stance, where every swing curve is back at zero.)
    FRotator OldCamera=FRotator::ZeroRotator;float OldFov=0.f;
    const bool bChain=bAttacking;
    if(bChain)KukriRhythm::SwingCamera(Stage,Elapsed,OldCamera,OldFov);
    // Debit once on swing entry, including misses; failed payment changes nothing.
    if(!Profile->SpendStamina(ColdSteelMelee::AttackStamina(Item,Profile)))return;
    if(bChain)
    {
        FRotator NewCamera;float NewFov=0.f;
        KukriRhythm::SwingCamera(NewStage,0.f,NewCamera,NewFov);
        const float OldKeep=CameraCarryAge>=0.f?1.f-FMath::SmoothStep(0.f,1.f,CameraCarryAge/KukriRhythm::CameraCarrySeconds):0.f;
        CameraCarry=OldCamera+CameraCarry*OldKeep-NewCamera;CameraCarryFov=OldFov+CameraCarryFov*OldKeep-NewFov;CameraCarryAge=0.f;
    }
    Stage=NewStage;
    // Snapshot at swing start: damage, speed and reach stay fixed for this swing.
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    SwingDamage=Stats.Damage;
    // AttackRate is normalised to the sword's 1.775 s clip.  The item's attack_seconds is 1.5625x this clip's
    // authored length (V9 -25 %, V10 another -25 %: "still too fast"), so the base product is 0.64 and
    // aspd/mastery/haste scale from there.
    PlayRate=FMath::Clamp(float(Stats.AttackRate)*KukriRhythm::AttackSeconds/RuneSwordRhythm::AttackEnd,.3f,3.f);
    Reach=Stats.BaseReach>0.?float(Stats.BaseReach):KukriRhythm::DefaultReachCM;
    Shot=ColdSteelSkills::Snapshot(P,Item);
    Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;
    Shot.AttackForm=KukriRhythm::Form;Shot.bMeleeStrike=true;
    bAttacking=true;bSwingPlayed=false;bImpactConfirmed=false;bWallHit=false;
    HitActors.Reset();HitStop=0.f;
    // V11: every stage starts and ends on the stance; the short local-space entry blend absorbs the idle/walk
    // offset when a swing starts from locomotion (a stage-to-stage hand-over is stance to stance).
    SetClip(FName(KukriRhythm::Swings[Stage].Clip),false,KukriRhythm::EntryBlendSeconds);
    PreviousBlade=BladeFrame();bHavePreviousBlade=true;
    ResetStrike();
}

void UKukriWeaponComponent::CancelAction()
{
    const bool WasActive=bAttacking||bEquipping||bUppercut||bHeavyCharging||bHeavyAttack;
    // A cancelled charge bills nothing more (its camera eases out); a cancelled release keeps its paid stamina and trains once.
    const bool bWasCharging=bHeavyCharging;
    if(bWasCharging)KukriHeavyRhythm::ChargeCamera(Elapsed,CameraCarry,CameraCarryFov);
    SetHeavyCharging(false,false);bHeavyAuto=bHeavyFull=false;
    if(bHeavyAttack){bHeavyAttack=false;FinishHeavy(true);}
    // A cancelled uppercut keeps its paid release and still trains once (the sword's rule).
    if(bUppercut){bUppercut=false;FinishUppercut(true);}
    bAttacking=false;bEquipping=false;bQueued=false;Stage=0;NextStage=0;LastAttackEnd=-1.;CameraCarryAge=bWasCharging?0.f:-1.f;
    HitStop=0.f;HitActors.Reset();bHavePreviousBlade=false;
    ResetStrike();StrikeAge=-1.f;StopRift();
    if(WasActive&&IsEquipped()&&Viewmodel&&Animations.Num())
        SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
}

void UKukriWeaponComponent::ConfirmImpact(const FHitResult& Hit,bool bWorld)
{
    const auto& K=KukriRhythm::Strikes[Stage];
    if(K.At>0.f&&!bStrikeDone)
    {
        // Found before the impact moment (stab: during the drive; slashes: before the blade crosses the centre) --
        // the cue waits for it (ArriveStrike); damage has already been applied.
        if(bWorld){if(!bPendingWall){bPendingWall=true;PendingWallHit=Hit;}}
        else if(!bPendingFlesh){bPendingFlesh=true;PendingFleshHit=Hit;}
        return;
    }
    if(bWorld)
    {
        if(bWallHit||bImpactConfirmed)return;
        bWallHit=true;HitStop=KukriRhythm::WallStopSeconds;ImpactAge=0.f;ImpactKick=.7f;
        if(WallSound)UGameplayStatics::PlaySoundAtLocation(this,WallSound,Hit.ImpactPoint,.55f,1.15f);
        return;
    }
    // One confirmed-hit cue per swing; every target still gets its own damage receipt.
    if(bImpactConfirmed)return;
    bImpactConfirmed=true;HitStop=KukriRhythm::FleshStopSeconds*KukriRhythm::Swings[Stage].HitStopScale;ImpactAge=0.f;
    ImpactKick=KukriRhythm::ImpactKick*KukriRhythm::Swings[Stage].ImpactScale;
    if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.95f,1.04f);
    if(StabThudSounds.Num())
        UGameplayStatics::PlaySoundAtLocation(this,StabThudSounds[FMath::RandRange(0,StabThudSounds.Num()-1)],Hit.ImpactPoint,
            KukriRhythm::StabThudVolume,KukriRhythm::StabThudPitch);
    bPressIn=K.PressX!=0.f||K.PressY!=0.f||K.PressZ!=0.f;PressStop=HitStop;
}

void UKukriWeaponComponent::TraceBlade(const FTransform& From,const FTransform& To)
{
    auto* P=Pawn();
    UWorld* World=GetWorld();
    if(!P||!World)return;
    const FTransform Aim=P->GetMeleeAimTransform();
    const FVector Probe=To.TransformPosition(KukriRhythm::BladeMid);
    TArray<FHitResult,TInlineAllocator<8>> Contacts;
    // Targets: forward area from the blade's current position (cleave, low targets, cover).
    const float Forward=FVector::DotProduct(Probe-Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X));
    if(Forward>=0.f)
        Contacts.Append(MeleeSmallTargets::QueryQuickAreaContacts(World,P,Aim,Probe,FMath::Max(40.f,Reach-Forward),KukriRhythm::QueryRadiusCM));
    // Scenery: the real edge from root to tip, swept between substeps.
    FCollisionQueryParams Q(SCENE_QUERY_STAT(KukriSwing),false,GetOwner());
    for(const auto& Actor:HitActors)if(Actor.IsValid())Q.AddIgnoredActor(Actor.Get());
    for(int32 Segment=0;Segment<=3;++Segment)
    {
        const FVector Local=FMath::Lerp(KukriRhythm::BladeRoot,KukriRhythm::BladeTip,Segment/3.f);
        FHitResult Hit;
        if(World->SweepSingleByChannel(Hit,From.TransformPosition(Local),To.TransformPosition(Local),FQuat::Identity,
            ECC_Visibility,FCollisionShape::MakeSphere(2.5f),Q))
            if(const auto* Actor=Hit.GetActor();Actor&&!Actor->FindComponentByClass<UMonsterCombatComponent>())Contacts.Add(Hit);
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const auto& Hit:Contacts)
    {
        auto* Actor=Hit.GetActor();
        if(!Actor||Actor->ActorHasTag(TEXT("Friendly"))||HitActors.Contains(Actor))continue;
        const FVector Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
        auto* Combat=Actor->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)
        {
            UWardBreakableGlass::BreakHit(Hit,Direction);
            // Scenery comes back on every substep while the blade rests against it: one cue and one burst per swing.
            const bool bFirstWall=!bWallHit&&!bImpactConfirmed&&!bPendingWall;
            ConfirmImpact(Hit,true);
            if(bFirstWall)QueueContactFX(Hit,true);
            continue;
        }
        // The uppercut is single-target, like the sword and hammer uppercuts.
        if(bUppercut&&!HitActors.IsEmpty())break;
        HitActors.Add(Actor);
        if(Combat->IsDead())continue;
        const bool bHeavyVictim=bHeavyAttack&&bHeavyTrainingPending&&ColdSteelSkills::IsMasteryTrainingTarget(P,Actor);
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,SwingDamage,Direction,Shot,&Receipt);
        // Hit cue: damage was dealt, or this hit killed the target.
        if(Applied>0.f||Combat->IsDead())
        {
            ConfirmImpact(Hit,false);
            QueueContactFX(Hit,false);
            P->NotifyConfirmedWeaponHit(Actor,Applied,&Receipt,false);
            if(bHeavyVictim){++HeavyHits;if(Combat->IsDead())++HeavyKills;}
        }
    }
}

void UKukriWeaponComponent::AdvanceAttack(float Delta)
{
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bAttacking&&++Guard<64)
    {
        if(HitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStop);
            HitStop-=Pause;Remaining-=Pause;
            continue;
        }
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriRhythm::AttackSeconds;
        // Author-time substeps (<= 1/120 s) that land exactly on every phase boundary.
        const KukriRhythm::FSwing& S=KukriRhythm::Swings[Stage];
        // V12b: the stab slows its visible phases on a smooth tempo curve (KukriRhythm::StageTempo); substeps are
        // <= 1/120 author s, so the rate is sampled finely enough for the SmoothStep blends between knots.
        const float Rate=PlayRate*KukriRhythm::StageTempo(Stage,Elapsed);
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        const float StrikeAt=KukriRhythm::Strikes[Stage].At, RiftAt=KukriRhythm::Rifts[Stage].Start;
        for(const float Boundary:{S.SwingSound,S.ContactStart,S.ContactEnd,StrikeAt,RiftAt,Length})
            if(Elapsed<Boundary-UE_KINDA_SMALL_NUMBER)Step=FMath::Min(Step,Boundary-Elapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=Elapsed;
        Elapsed=FMath::Min(Length,Elapsed+Step);
        Remaining=FMath::Max(0.f,Remaining-(Elapsed-Before)/Rate);
        SamplePose(Elapsed);
        const FTransform Now=BladeFrame();
        if(!bSwingPlayed&&Elapsed>=S.SwingSound-UE_KINDA_SMALL_NUMBER)
        {
            bSwingPlayed=true;
            // The stab plays a short sharp whoosh on its drive instead of the item swing sound.
            const bool bWhoosh=KukriRhythm::Strikes[Stage].bWhoosh&&StabWhooshSound;
            USoundBase* Cue=bWhoosh?StabWhooshSound.Get():SwingSound.Get();
            if(Cue)UGameplayStatics::PlaySound2D(this,Cue,bWhoosh?KukriRhythm::StabWhooshVolume:.55f,
                S.SwingPitch*FMath::Clamp(PlayRate,.85f,1.3f));
        }
        if(bHavePreviousBlade&&Before>=S.ContactStart-UE_KINDA_SMALL_NUMBER&&Before<S.ContactEnd)TraceBlade(PreviousBlade,Now);
        if(StrikeAt>0.f&&!bStrikeDone&&Elapsed>=StrikeAt-UE_KINDA_SMALL_NUMBER)ArriveStrike();
        if(!bRiftStarted&&Elapsed>=RiftAt-UE_KINDA_SMALL_NUMBER){bRiftStarted=true;StartRift();}
        PreviousBlade=Now;bHavePreviousBlade=true;
        if(Elapsed>=Length-UE_KINDA_SMALL_NUMBER)
        {
            // Back on the stance: the full recovery was this stage's attack interval.  A buffered click starts
            // the next stage now (3 -> 1); otherwise the next click within ComboResetSeconds still continues.
            const bool bNext=bQueued;
            bAttacking=false;HitActors.Reset();
            NextStage=(Stage+1)%KukriRhythm::SwingCount;
            LastAttackEnd=GetWorld()?GetWorld()->GetTimeSeconds():0.;
            if(bNext){StartAttack(NextStage);if(bAttacking)continue;}
            SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);
        }
    }
}

void UKukriWeaponComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // Authority of a remote owner: keep its heavy charge honest (the stamina bill stops with the charge).
    if(bServerHeavyCharging&&GetOwner()&&GetOwner()->HasAuthority())TickServerHeavyCharge();
    auto* P=Pawn();
    if(!P||!Viewmodel||!IsEquipped()||!P->IsLocallyControlled())return;
    if(ImpactAge>=0.f){ImpactAge+=Delta;if(ImpactAge>.6f)ImpactAge=-1.f;}
    if(StrikeAge>=0.f){StrikeAge+=Delta;if(StrikeAge>.4f)StrikeAge=-1.f;}
    TickRift(Delta);
    if(CameraCarryAge>=0.f){CameraCarryAge+=Delta*PlayRate;if(CameraCarryAge>KukriRhythm::CameraCarrySeconds)CameraCarryAge=-1.f;}
    if(JumpRoot)
    {
        // Impact kick is a camera-aligned rotation of the presentation parent only.
        const FTransform Kick(ViewmodelKick(),StrikeViewmodelOffset());
        JumpRoot->SetRelativeTransform(Kick*P->GetWeaponJumpTransform(EFirstPersonJumpRig::Sword));
    }
    const bool Present=CanPresent();
    Viewmodel->SetVisibility(Present&&Viewmodel->GetSkeletalMeshAsset(),true);
    if(!Present){if(IsBusy())CancelAction();return;}
    Viewmodel->AdvanceEntry(Delta);
    if((bAttacking||bUppercut||bHeavyCharging||bHeavyAttack)&&!CanUse())CancelAction();
    if(bUppercut){AdvanceUppercut(Delta);return;}
    if(bHeavyCharging){AdvanceHeavyCharge(Delta);return;}
    if(bHeavyAttack){AdvanceHeavy(Delta);return;}
    const float Speed=1.f;// TODO(lightning-haste): restore LightningHaste::ActionSpeed(P) when Skills/LightningHasteSpeed.h lands
    if(bEquipping)
    {
        Elapsed+=Delta*Speed;
        const float Length=CurrentAnimation?CurrentAnimation->GetPlayLength():KukriRhythm::EquipSeconds;
        if(Elapsed>=Length){bEquipping=false;SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);}
        else SamplePose(Elapsed);
        return;
    }
    if(bAttacking){AdvanceAttack(Delta);return;}
    const FName Want=LocomotionClip();
    if(Want!=CurrentClip)
        SetClip(Want,true,(Want==KukriRun||CurrentClip==KukriRun)?KukriRhythm::SprintBlendSeconds:KukriRhythm::EntryBlendSeconds);
    if(!CurrentAnimation)return;
    float Rate=1.f;
    if(CurrentClip==KukriWalk)Rate=FMath::Clamp(P->GetVelocity().Size2D()/KukriWalkReferenceSpeed,.6f,1.4f);
    Elapsed=FMath::Fmod(Elapsed+Delta*Rate,FMath::Max(.01f,CurrentAnimation->GetPlayLength()));
    SamplePose(Elapsed);
}
