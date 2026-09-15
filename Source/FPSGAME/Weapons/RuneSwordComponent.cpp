#include "RuneSwordComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "RuneSwordCombatTuning.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "ColdSteelEnchantmentCombat.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

URuneSwordComponent::URuneSwordComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

bool URuneSwordComponent::TriggerHeavySkill()
{
    if(!IsEquipped()||IsBusy()||!CanUse())return false;
    BeginHeavyCharge();
    bAutoHeavyRelease=bCharging;
    return bCharging;
}

void URuneSwordComponent::FinishHeavyTraining()
{
    if(!bHeavyTrainingPending)return;
    bHeavyTrainingPending=false;
    if(GetWorld()&&GetWorld()->GetGameInstance())
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Profile->TrainHeavyStrike(HeavyTrainingHits,HeavyTrainingKills);
}

void URuneSwordComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    auto* World=GetWorld();
    auto* GameInstance=World?World->GetGameInstance():nullptr;
    // IsGameWorld includes GamePreview; visual rigs must not access inventory.
    if(!Pawn || !GameInstance || (World->WorldType!=EWorldType::Game && World->WorldType!=EWorldType::PIE) || Pawn->GetNetMode()!=NM_Standalone)
    {SetComponentTickEnabled(false);return;}
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    if(!Camera){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(Pawn);
    Viewmodel=NewObject<UFPSCastingMeshComponent>(Pawn,TEXT("RuneSwordViewmodel"));
    Pawn->AddInstanceComponent(Viewmodel);Viewmodel->SetupAttachment(Camera);
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Viewmodel->SetCanEverAffectNavigation(false);Viewmodel->SetOnlyOwnerSee(true);
    Viewmodel->SetCastShadow(false);Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent();Viewmodel->SetVisibility(false);
    // A single animation clock supplies pose, hit window, and audio timing.
    Viewmodel->SetComponentTickEnabled(false);
    RiftVisual=NewObject<UStaticMeshComponent>(Pawn,TEXT("RuneSwordRift"));
    Pawn->AddInstanceComponent(RiftVisual);
    RiftVisual->SetMobility(EComponentMobility::Movable);
    RiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RiftVisual->SetCanEverAffectNavigation(false);RiftVisual->SetOnlyOwnerSee(true);
    RiftVisual->SetCastShadow(false);RiftVisual->bReceivesDecals=false;
    RiftVisual->RegisterComponent();RiftVisual->SetVisibility(false);
    RiftVisual->SetComponentTickEnabled(false);
    RefreshEquipment(GameInstance->GetSubsystem<UColdSteelStatusModel>());
}

void URuneSwordComponent::RefreshEquipment(UColdSteelStatusModel* Profile)
{
    if(!Profile || !Viewmodel)return;
    const auto* Item=Profile->Equipped();
    const FString NewId=Item && !Profile->ActiveProductionTool() && Item->Definition==TEXT("ue_rune_sword") ? Item->InstanceId : FString();
    if(!NewId.IsEmpty())
    {
        Damage=ColdSteelInventory::Number(*Item,TEXT("melee_damage"),55);
        if(auto* E=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            Damage=E->ProcessedDamage(*Item,Damage,Profile->Derived(TEXT("atk")));
            AttackRate=Profile->Derived(TEXT("aspd"))/FMath::Max(.1f,float(E->Effect(*Item,TEXT("attackIntervalMul"),1)));
        }
        else {Damage+=Profile->Derived(TEXT("atk"));AttackRate=Profile->Derived(TEXT("aspd"));}
        AttackRate/=1-Profile->MasteryEffect(TEXT("swordMastery")).CooldownReduction;
        AttackRate=FMath::Clamp(AttackRate,.2f,4.f);
        Reach=ColdSteelInventory::Number(*Item,TEXT("melee_reach_cm"),180);
        // Timing belongs to the installed animation revision. Existing saved
        // instances can still contain earlier contact-window metadata.
    }
    if(NewId==InstanceId)return;
    CancelAction();InstanceId=NewId;NextSlash=0;
    Viewmodel->SetVisibility(false);
    if(NewId.IsEmpty())return;
    const FString Folder=ColdSteelInventory::Text(*Item,TEXT("animation_folder"));
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("viewmodel_mesh")));
    Viewmodel->SetSkeletalMesh(Mesh);Animations.Reset();
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Inspect"),TEXT("Slash1"),TEXT("Slash2"),TEXT("Thrust"),TEXT("HeavyCharge"),TEXT("HeavyRelease"),TEXT("Guard"),TEXT("GuardHit"),TEXT("GuardBreak")})
        Animations.Add(FName(Clip),LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("/A_RuneSword_")+Clip)));
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    AttackLayerSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/SwordAttack20260914/S_Sword_Attack.S_Sword_Attack"));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    BlockSound=LoadObject<USoundBase>(nullptr,*(Folder+TEXT("/S_RuneSword_Block")));
    ParrySound=LoadObject<USoundBase>(nullptr,*(Folder+TEXT("/S_RuneSword_Parry")));
    if(!RiftMaterial)
    {
        const FString FXFolder=TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/");
        auto* Material=LoadObject<UMaterialInterface>(nullptr,*(FXFolder+TEXT("M_RuneRift")));
        if(Material){RiftMaterial=UMaterialInstanceDynamic::Create(Material,this);RiftVisual->SetMaterial(0,RiftMaterial);}
        RiftMeshes.Reset();
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Slash1"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Slash2"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Heavy"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Thrust"))));
    }
    if(!Mesh || !Animations.FindRef(TEXT("Idle")) || !Animations.FindRef(TEXT("Slash1")) || !Animations.FindRef(TEXT("Slash2")) || !Animations.FindRef(TEXT("Thrust")))
    {UE_LOG(LogTemp,Error,TEXT("Rune sword assets are missing; import RuneSword20260913 assets."));return;}
    bEquipping=true;SetClip(TEXT("Equip"),false);
    if(!CurrentAnimation){bEquipping=false;SetClip(TEXT("Idle"),true);}
    Viewmodel->SetVisibility(CanUse());
}

bool URuneSwordComponent::CanUse() const
{
    auto* Pawn=Character.Get();const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return PC && !PC->bShowMouseCursor && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored() &&
        !Pawn->IsTraversing() && (!Health || !Health->IsDead()) && (!Build || !Build->IsBuilding());
}

void URuneSwordComponent::SetClip(FName Name,bool bLoop)
{
    CurrentClip=Name;CurrentAnimation=Animations.FindRef(Name);Elapsed=0;
    if(!CurrentAnimation || !Viewmodel)return;
    Viewmodel->PlayAnimation(CurrentAnimation,bLoop);Viewmodel->SetPlayRate(0.f);SamplePose(0.f);
    if(Character.IsValid())PreviousAimFrame=Character->GetMeleeAimTransform();
}

void URuneSwordComponent::SamplePose(float Time)
{
    if(!Viewmodel || !CurrentAnimation)return;
    Viewmodel->SetPosition(Time,false);Viewmodel->TickAnimation(0.f,false);Viewmodel->RefreshBoneTransforms();
}

void URuneSwordComponent::BeginInspect()
{
    if(!IsEquipped() || IsBusy() || bGuardHeld || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(Character->IsCastBlockingLeftHandAction() || !Animations.FindRef(TEXT("Inspect")))return;
    // Cosmetic action: its own real-time clock, no attack rate, stamina or hit window.
    bInspecting=true;bQueuedAttack=false;StopRift();
    SetClip(TEXT("Inspect"),false);
}

void URuneSwordComponent::BeginAttack()
{
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return;
    // Let the current swing finish; only reject a new swing or queued combo.
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction()){bQueuedAttack=false;return;}
    if(!IsEquipped() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(bInspecting)CancelAction();
    if(bCharging || bReturningCharge)return;
    if(bEquipping){bQueuedAttack=true;return;}
    if(bAttacking){if(Elapsed>=ContactEnd)bQueuedAttack=true;return;}
    if(GetWorld()->GetTimeSeconds()-LastAttackEnd>.85)NextSlash=0;
    const FName Clip=NextSlash==0?TEXT("Slash1"):(NextSlash==1?TEXT("Slash2"):TEXT("Thrust"));
    if(StartSwing(Clip,false))NextSlash=(NextSlash+1)%3;
}

void URuneSwordComponent::BeginPrimaryAttack()
{
    if(bInspecting)CancelAction();
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return;
    // Preserve the ordinary equip/recovery click buffer. This press belongs to
    // that combo, so its release must not start a second attack or a charge.
    if(bAttacking || bEquipping){BeginAttack();return;}
    BeginHeavyCharge();
}

void URuneSwordComponent::ReleasePrimaryAttack()
{
    if(!bCharging)return;
    if(!CanUse() || Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    const double HeldSeconds=GetWorld()->GetTimeSeconds()-ChargeStartedAt;
    if(HeldSeconds<=.20)
    {
        // A tap uses the full normal attack and advances the three-part combo.
        // The two-second charge clock always starts at the original press.
        bCharging=false;BeginAttack();
        if(!bAttacking)ReturnFromCharge();
        return;
    }
    ReleaseHeavyCharge();
}

bool URuneSwordComponent::StartSwing(FName Clip,bool Heavy)
{
    if(!Animations.FindRef(Clip))return false;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(!Profile->SpendStamina(Profile->StaminaSettings().MeleeCost)){bQueuedAttack=false;return false;}
    bAttacking=true;bQueuedAttack=bCharging=bReturningCharge=false;bHeavyAttack=Heavy;
    bThrustAttack=Clip==TEXT("Thrust");bLungeStarted=bLungeBlocked=false;
    LungeDirection=FVector::ZeroVector;
    HitActors.Reset();SwingDamage=Damage*(Heavy?ChargedMultiplier:1.f);
    bHeavyTrainingPending=Heavy;HeavyTrainingHits=HeavyTrainingKills=0;bAutoHeavyRelease=false;
    SwingRate=AttackRate;SwingReach=RuneSwordCombatTuning::ScaledReach(Reach,bThrustAttack?RuneSwordThrustRhythm::ReachBonus:0.f);
    ContactStart=Heavy?RuneSwordHeavyRhythm::ContactStart:(bThrustAttack?RuneSwordThrustRhythm::ContactStart:RuneSwordRhythm::ContactStart);
    ContactEnd=Heavy?RuneSwordHeavyRhythm::ContactEnd:(bThrustAttack?RuneSwordThrustRhythm::ContactEnd:RuneSwordRhythm::ContactEnd);
    bImpactFeedbackPlayed=bSwingCuePlayed=false;
    SwingTrainingHits=0;
    SwingPoison=ColdSteelCombat::Snapshot(Character.Get()).Poison;
    SwingSkills=ColdSteelSkills::Snapshot(Character.Get());
    SwingSkills.bRifle=false;SwingSkills.bPistol=false;SwingSkills.WeakpointPercent=0;
    SetClip(Clip,false);return true;
}

FVector URuneSwordComponent::AdvanceThrustLunge(float FromTime,float ToTime)
{
    const float Distance=RuneSwordThrustRhythm::LungeDistance*
        (RuneSwordThrustRhythm::LungeAlpha(ToTime)-RuneSwordThrustRhythm::LungeAlpha(FromTime));
    if(!bThrustAttack || bLungeBlocked || Distance<=0.f)return FVector::ZeroVector;
    auto* Pawn=Character.Get();
    auto* Movement=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    if(!Movement || Pawn->IsSliding() || Pawn->IsTraversing() || !Movement->IsMovingOnGround() || Movement->IsDodging())
    {bLungeBlocked=true;return FVector::ZeroVector;}
    if(!bLungeStarted)
    {
        LungeDirection=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
        bLungeStarted=true;
    }
    const FVector Moved=Movement->ApplyMeleeLungeStep(LungeDirection,Distance);
    if(FVector::DotProduct(Moved,LungeDirection)+.01f<Distance)bLungeBlocked=true;
    return Moved;
}

void URuneSwordComponent::BeginHeavyCharge()
{
    if(bInspecting)CancelAction();
    if(!IsEquipped() || IsBusy() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(Character->IsCastBlockingLeftHandAction())return;
    if(!Animations.FindRef(TEXT("HeavyCharge")) || !Animations.FindRef(TEXT("HeavyRelease")))return;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(!Profile->CanSpendStamina(Profile->StaminaSettings().MeleeCost))return;
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||Profile->MasteryProgress(TEXT("heavyStrike")).Level<1||Profile->ActiveProductionTool())return;
    const auto Skill=Profile->MasteryEffect(TEXT("heavyStrike"));RequiredChargeSeconds=Skill.HeavyChargeSeconds;ChargedMultiplier=Skill.HeavyMultiplier;
    bAutoHeavyRelease=false;
    bCharging=true;bQueuedAttack=false;bHeavyAttack=false;HitActors.Reset();
    ChargeStartedAt=GetWorld()->GetTimeSeconds();
    SetClip(TEXT("HeavyCharge"),false);
}

void URuneSwordComponent::ReleaseHeavyCharge()
{
    if(!bCharging)return;
    if(!CanUse() || Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    // Input is dispatched before the component tick: decide from the input's
    // gameplay timestamp, so an exact two-second hold does not lose one frame.
    const double HeldSeconds=GetWorld()->GetTimeSeconds()-ChargeStartedAt;
    const bool Heavy=HeldSeconds>=RequiredChargeSeconds;
    const float ChargePoseTime=Elapsed;
    // Charging always loads the right shoulder. Continue with Slash1, then
    // allow the existing left-click combo to mirror into Slash2.
    if(StartSwing(Heavy?TEXT("HeavyRelease"):TEXT("Slash1"),Heavy))
    {
        if(!Heavy)
        {
            // HeavyCharge reaches V6's raised pose at .65 s and its ordinary
            // load pose at 1.60 s. Resume the matching point in the V8 windup
            // instead of resetting the hands to idle and lifting a second time.
            const float SourceTime=ChargePoseTime<.65f ? .17f*ChargePoseTime/.65f :
                FMath::Lerp(.17f,.40f,FMath::Clamp((ChargePoseTime-.65f)/.95f,0.f,1.f));
            float Low=0.f,High=RuneSwordRhythm::WindupEnd;
            for(int32 I=0;I<16;++I)
            {
                const float Mid=(Low+High)*.5f;
                if(RuneSwordRhythm::SourceTime(Mid)<SourceTime)Low=Mid;else High=Mid;
            }
            Elapsed=(Low+High)*.5f;SamplePose(Elapsed);
        }
        NextSlash=1;return;
    }
    // A failed stamina/asset gate still returns safely without dealing damage.
    ReturnFromCharge();
}

void URuneSwordComponent::ReturnFromCharge()
{
    bCharging=false;bReturningCharge=true;bQueuedAttack=false;
    CancelChargeFrom=Elapsed;CancelChargeAge=0.f;
    CancelChargeDuration=FMath::Clamp(Elapsed*.25f,.1f,.45f);
}

void URuneSwordComponent::CancelAction()
{
    FinishHeavyTraining();bAutoHeavyRelease=false;
    ClearGuard();
    bAttacking=bEquipping=bInspecting=bQueuedAttack=bCharging=bReturningCharge=bHeavyAttack=false;HitActors.Reset();
    bThrustAttack=bLungeStarted=bLungeBlocked=false;LungeDirection=FVector::ZeroVector;
    ImpactAge=1.f;bImpactFeedbackPlayed=bThrustImpact=false;
    StopRift();
    if(Viewmodel && Animations.FindRef(TEXT("Idle")))SetClip(TEXT("Idle"),true);
}

void URuneSwordComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;
    if(!IsEquipped())return;
    if(GetGuardCameraMotion(Location,Rotation))return;
    if(!CanUse())return;
    if(bCharging || bReturningCharge)
    {
        const float Gather=FMath::SmoothStep(0.f,RuneSwordHeavyRhythm::ChargeSeconds,Elapsed);
        Location=FVector(-13.f,7.8f,3.12f)*Gather;
        Rotation=FRotator(7.8f,9.1f,6.5f)*Gather;
    }
    else if(bAttacking && bThrustAttack)
    {
        const float ExtensionEnd=RuneSwordThrustRhythm::ExtensionEnd;
        const FVector LoadLocation(-8.f,1.5f,1.2f),FollowLocation(13.f,-.6f,-3.5f);
        const FRotator LoadRotation(3.f,1.2f,.8f),FollowRotation(-4.5f,-.7f,-.6f);
        if(Elapsed<=ContactStart)
        {
            const float Gather=FMath::SmoothStep(0.f,RuneSwordThrustRhythm::LoadEnd,Elapsed);
            Location=LoadLocation*Gather;Rotation=LoadRotation*Gather;
        }
        else if(Elapsed<=ExtensionEnd)
        {
            const float U=(Elapsed-ContactStart)/(ExtensionEnd-ContactStart);
            const float Push=FMath::SmoothStep(0.f,1.f,U),Burst=FMath::Square(FMath::Sin(PI*U));
            Location=FMath::Lerp(LoadLocation,FollowLocation,Push);Location.X+=5.f*Burst;
            Rotation=FMath::Lerp(LoadRotation,FollowRotation,Push);
            Rotation.Pitch+=1.8f*Burst*FMath::Sin(U*PI*4.f);
        }
        else
        {
            float Weight;
            if(Elapsed<=RuneSwordThrustRhythm::ArrestEnd)
                Weight=1.f+.08f*FMath::Sin(PI*(Elapsed-ExtensionEnd)/(RuneSwordThrustRhythm::ArrestEnd-ExtensionEnd));
            else if(Elapsed<=RuneSwordThrustRhythm::ReturnCorner)
                Weight=FMath::Lerp(1.f,.18f,FMath::SmoothStep(RuneSwordThrustRhythm::ArrestEnd,RuneSwordThrustRhythm::ReturnCorner,Elapsed));
            else
                Weight=.18f*(1.f-FMath::SmoothStep(RuneSwordThrustRhythm::ReturnCorner,RuneSwordThrustRhythm::AttackEnd,Elapsed));
            Location=FollowLocation*Weight;Rotation=FollowRotation*Weight;
        }
        if(bLungeStarted)
        {
            // One weight shift and one foot plant accompany the real stride.
            // The actor supplies the metre of forward travel; this is local bob.
            const float Step=FMath::Clamp((Elapsed-RuneSwordThrustRhythm::LungeStart)/
                (RuneSwordThrustRhythm::LungeEnd-RuneSwordThrustRhythm::LungeStart),0.f,1.f);
            const float Lower=FMath::Square(FMath::Sin(PI*Step));
            Location.Z-=3.5f*Lower;Rotation.Pitch+=1.2f*Lower;
            const float Landing=FMath::Clamp((Elapsed-RuneSwordThrustRhythm::LungeEnd)/.16f,0.f,1.f);
            const float Plant=FMath::Square(FMath::Sin(PI*Landing))*(1.f-Landing);
            Location.Z-=2.4f*Plant;Rotation.Pitch+=.8f*Plant;
        }
    }
    else if(bAttacking)
    {
        const float Direction=CurrentClip==TEXT("Slash2")?1.f:-1.f;
        const float SourceTime=bHeavyAttack?RuneSwordHeavyRhythm::CameraSourceTime(Elapsed):RuneSwordRhythm::SourceTime(Elapsed);
        // Authored centimeters/degrees: a committed body turn before the
        // character's existing camera presentation scale is applied.
        const float LoadStrength=bHeavyAttack?1.3f:1.f, ReleaseStrength=bHeavyAttack?1.5f:1.f;
        const FVector LoadLocation=FVector(-10.f,-Direction*6.f,2.4f)*LoadStrength;
        const FRotator LoadRotation=FRotator(6.f,-Direction*7.f,-Direction*5.f)*LoadStrength;
        const FVector FollowLocation=FVector(16.f,Direction*11.f,-9.f)*ReleaseStrength;
        const FRotator FollowRotation=FRotator(-9.f,Direction*12.f,Direction*10.f)*ReleaseStrength;
        if(Elapsed<=ContactStart)
        {
            const float Gather=FMath::SmoothStep(0.f,.40f,SourceTime);
            Location=LoadLocation*Gather;Rotation=LoadRotation*Gather;
        }
        else if(Elapsed<=ContactEnd)
        {
            const float U=(Elapsed-ContactStart)/(ContactEnd-ContactStart);
            const float Across=U*U*(2.f-U);
            const float Burst=FMath::Square(FMath::Sin(PI*U));
            Location=FMath::Lerp(LoadLocation,FollowLocation,Across);
            Location.X+=10.f*Burst*ReleaseStrength;
            Rotation=FMath::Lerp(LoadRotation,FollowRotation,Across);
            // A brief directional vibration rides the release; it is silent
            // during the held load pose and vanishes at the phase boundary.
            Rotation.Pitch+=1.7f*Burst*FMath::Sin(U*PI*6.f)*ReleaseStrength;
            Rotation.Roll+=Direction*2.2f*Burst*FMath::Sin(U*PI*4.f)*ReleaseStrength;
        }
        else
        {
            // Follow the cut, arrest its weight, then draw back with the hands.
            // A sign-changing spring here fought the accepted diagonal path.
            float Weight;
            if(SourceTime<=1.115f)
                Weight=1.f+.10f*FMath::SmoothStep(1.015f,1.115f,SourceTime);
            else if(SourceTime<=1.34f)
                Weight=FMath::Lerp(1.10f,.30f,FMath::SmoothStep(1.115f,1.34f,SourceTime));
            else
                Weight=.30f*(1.f-FMath::SmoothStep(1.34f,1.65f,SourceTime));
            Location=FollowLocation*Weight;Rotation=FollowRotation*Weight;
        }
    }
    // Confirmed contact gives one damped impulse per slash. Multi-target
    // sweeps keep their damage but cannot stack camera shake indefinitely.
    if(ImpactAge<.20f)
    {
        const float Envelope=1.f-FMath::SmoothStep(0.f,.20f,ImpactAge);
        const float Kick=FMath::Exp(-17.f*ImpactAge)*FMath::Sin(55.f*ImpactAge)*Envelope;
        Location+=(bThrustImpact?FVector(-12.f,0.f,1.4f):FVector(-8.f,ImpactDirection*3.f,2.f))*Kick*ImpactStrength;
        Rotation+=(bThrustImpact?FRotator(7.f,0.f,.8f):FRotator(6.f,ImpactDirection*2.8f,-ImpactDirection*4.4f))*Kick*ImpactStrength;
    }
    // Scale the sword's directional travel and impact vibration together.
    // Other camera effects keep their own existing amplitude.
    constexpr float SwordCameraStrength=1.5f;
    Location*=SwordCameraStrength;
    Rotation*=SwordCameraStrength;
}

void URuneSwordComponent::StartRift(float SourceAge)
{
    const int32 Index=bThrustAttack?3:(bHeavyAttack?2:(CurrentClip==TEXT("Slash2")?1:0));
    if(!RiftVisual || !RiftMaterial || !RiftMeshes.IsValidIndex(Index) || !RiftMeshes[Index])return;
    RiftVisual->SetStaticMesh(RiftMeshes[Index]);
    // The crescent is authored from the same blade trajectory as the contact
    // animation. Freeze its launch transform in world space so it can drift out.
    RiftOrigin=Viewmodel->GetComponentTransform();RiftDirection=Camera->GetForwardVector();
    RiftFastSeconds=((bThrustAttack?RuneSwordThrustRhythm::ExtensionEnd:ContactEnd)-ContactStart)/SwingRate;
    RiftDissolveSeconds=bThrustAttack?.16f:(bHeavyAttack?.28f:.20f);
    RiftDriftSpeed=bThrustAttack?50.f:(bHeavyAttack?120.f:85.f);
    RiftMaterial->SetScalarParameterValue(TEXT("RiftStrength"),bThrustAttack?.10f:(bHeavyAttack?.14f:.085f));
    RiftAge=FMath::Max(0.f,SourceAge/SwingRate);bRiftActive=true;
    RiftVisual->SetVisibility(true);TickRift(0.f);
}

void URuneSwordComponent::TickRift(float Delta)
{
    if(!bRiftActive || !RiftVisual || !RiftMaterial)return;
    RiftAge+=Delta;
    if(RiftAge>=RiftFastSeconds+RiftDissolveSeconds){StopRift();return;}
    const float Recovery=FMath::Clamp((RiftAge-RiftFastSeconds)/RiftDissolveSeconds,0.f,1.f);
    const float Fade=1.f-Recovery*Recovery*(3.f-2.f*Recovery);
    RiftMaterial->SetScalarParameterValue(TEXT("SweepProgress"),FMath::Clamp(RiftAge/RiftFastSeconds,0.f,1.f)*1.06f);
    RiftMaterial->SetScalarParameterValue(TEXT("RiftFade"),Fade);
    FTransform Pose=RiftOrigin;Pose.AddToTranslation(RiftDirection*(RiftAge*RiftDriftSpeed));
    RiftVisual->SetWorldTransform(Pose);
}

void URuneSwordComponent::StopRift()
{
    bRiftActive=false;RiftAge=0.f;
    if(RiftVisual)RiftVisual->SetVisibility(false);
}

FRuneSwordBladeSample URuneSwordComponent::ReadBlade(const FTransform& AimFrame) const
{
    const FQuat ImportBasis=FRotator(0,90,0).Quaternion();
    const auto Point=[&](FName Bone){return AimFrame.TransformPosition(ImportBasis.RotateVector(
        Viewmodel->GetSocketTransform(Bone,RTS_Component).GetLocation()));};
    return {Point(TEXT("Blade_Base")),Point(TEXT("Blade_Tip")),AimFrame.GetLocation(),AimFrame.GetUnitAxis(EAxis::X)};
}

void URuneSwordComponent::SweepBlade(const FRuneSwordBladeSample& From,const FRuneSwordBladeSample& To)
{
    if(bThrustAttack && !HitActors.IsEmpty())return;
    FRuneSwordTraceSettings Trace;
    Trace.Radius=RuneSwordCombat::BladeRadius*RuneSwordCombatTuning::RangeMultiplier;
    if(bThrustAttack)
    {
        Trace.Radius=RuneSwordThrustRhythm::BladeRadius*RuneSwordCombatTuning::RangeMultiplier;
        Trace.ForwardCorridorRadius=RuneSwordThrustRhythm::CorridorRadius*RuneSwordCombatTuning::RangeMultiplier;
        Trace.bCleavePawns=false;
    }
    auto* Pawn=Character.Get();
    auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,From,To,SwingReach,HitActors,Trace);
    if(RuneSwordCombatTuning::RangeMultiplier>1.f)
    {
        // Extend the tip's distance from the stable eye, retaining the hilt.
        // Keep the original blade pass as well so close contacts are not lost
        // when the expanded segment changes its angle around the hilt.
        auto ExtendedFrom=From,ExtendedTo=To;
        ExtendedFrom.Tip=From.Origin+(From.Tip-From.Origin)*RuneSwordCombatTuning::RangeMultiplier;
        ExtendedTo.Tip=To.Origin+(To.Tip-To.Origin)*RuneSwordCombatTuning::RangeMultiplier;
        Hits.Append(RuneSwordCombat::Query(GetWorld(),Pawn,ExtendedFrom,ExtendedTo,SwingReach,HitActors,Trace));
    }
    if(bThrustAttack && Hits.Num()>1)
    {
        Hits.Sort([&](const FHitResult& A,const FHitResult& B)
        {
            return FVector::DotProduct(A.ImpactPoint-To.Origin,To.Forward)<
                FVector::DotProduct(B.ImpactPoint-To.Origin,To.Forward);
        });
        Hits.SetNum(1);
    }
    for(const FHitResult& Hit:Hits)
    {
            AActor* Target=Hit.GetActor();
            if(!IsValid(Target) || HitActors.Contains(Target))continue;
            HitActors.Add(Target);
            const FVector Direction=((To.Base+To.Tip)-(From.Base+From.Tip)).GetSafeNormal(SMALL_NUMBER,To.Forward);
            auto HitSkills=SwingSkills;
            if(SwingTrainingHits==1)if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())HitSkills.ExtraMasteryExperience=Profile->MasteryDefinition(TEXT("swordMastery")).MultiHitExperience;
            auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            const bool Eligible=Combat&&!Combat->IsDead()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
            const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,SwingDamage,Direction,HitSkills);
            if(Applied>0)
            {
                if(bHeavyTrainingPending&&Eligible){++HeavyTrainingHits;if(!IsValid(Target)||Combat->IsDead())++HeavyTrainingKills;}
                if(!bImpactFeedbackPlayed)
                {
                    bImpactFeedbackPlayed=true;ImpactAge=0.f;
                    bThrustImpact=bThrustAttack;
                    ImpactDirection=CurrentClip==TEXT("Slash2")?1.f:-1.f;
                    ImpactStrength=bHeavyAttack?1.5f:1.f;
                }
                if(Target->FindComponentByClass<UMonsterCombatComponent>()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))++SwingTrainingHits;
                Pawn->NotifyConfirmedWeaponHit(Target,Applied);ColdSteelCombat::OnHit(Target,Pawn,SwingPoison);
                if(HitSound)UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,bHeavyAttack?.90f:.65f,bHeavyAttack?.85f:(bThrustAttack?1.1f:1.f));
            }
    }
}

void URuneSwordComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!Viewmodel || !IsEquipped())return;
    if(TickGuardBreak(Delta))return;
    const bool Usable=CanUse();Viewmodel->SetVisibility(Usable && Viewmodel->GetSkeletalMeshAsset());
    if(!Usable){if(IsBusy())CancelAction();ImpactAge=1.f;StopRift();return;}
    if((bCharging || bReturningCharge || bInspecting) && Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    ImpactAge=FMath::Min(1.f,ImpactAge+Delta);
    TickRift(Delta);
    if(TickGuard(Delta))return;
    if(!CurrentAnimation)return;
    const float End=CurrentAnimation->GetPlayLength();
    if(bAttacking)
    {
        const float Next=FMath::Min(End,Elapsed+Delta*SwingRate);
        const FTransform AimBeforeLunge=Character->GetMeleeAimTransform();
        const FVector LungeMoved=AdvanceThrustLunge(Elapsed,Next);
        const FTransform AimNow=Character->GetMeleeAimTransform();
        if(bThrustAttack && bRiftActive)
        {
            // Carry the narrow rift with the actual step, including collision stops.
            RiftOrigin.AddToTranslation(LungeMoved);TickRift(0.f);
        }
        if(!bSwingCuePlayed && Next>=ContactStart)
        {
            bSwingCuePlayed=true;
            if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,1.f,1.f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,bHeavyAttack?.95f:.72f,FMath::Clamp(SwingRate*(bHeavyAttack?.95f:(bThrustAttack?1.25f:1.1f)),.7f,1.4f));
            StartRift(Next-ContactStart);
        }
        const auto FrameAt=[&](float Time)
        {
            // A hitch may run past the clip end. Aim still spans the full real
            // frame, rather than compressing all player movement into the clip.
            FTransform Frame;Frame.Blend(PreviousAimFrame,AimBeforeLunge,(Time-Elapsed)/FMath::Max(UE_SMALL_NUMBER,Delta*SwingRate));
            // Attribute real capsule displacement to the thrust's phase curve.
            // When blocked, the trace stops travelling with the blocked capsule.
            const float ForwardMoved=FVector::DotProduct(LungeMoved,LungeDirection);
            if(ForwardMoved>UE_SMALL_NUMBER)
            {
                const float Requested=RuneSwordThrustRhythm::LungeDistance*
                    (RuneSwordThrustRhythm::LungeAlpha(Time)-RuneSwordThrustRhythm::LungeAlpha(Elapsed));
                Frame.AddToTranslation(LungeMoved*FMath::Clamp(Requested/ForwardMoved,0.f,1.f));
            }
            return Frame;
        };
        const float HitStart=FMath::Max(Elapsed,ContactStart),HitEnd=FMath::Min(Next,ContactEnd);
        if(HitEnd>HitStart)
        {
            const FTransform StartFrame=FrameAt(HitStart),EndFrame=FrameAt(HitEnd);
            const float AimTravel=FVector::Distance(StartFrame.GetLocation(),EndFrame.GetLocation())+
                SwingReach*StartFrame.GetRotation().AngularDistance(EndFrame.GetRotation());
            const float SampleRate=bThrustAttack?RuneSwordThrustRhythm::SampleRate:(bHeavyAttack?RuneSwordHeavyRhythm::SampleRate:240.f);
            const float TraceRadius=(bThrustAttack?RuneSwordThrustRhythm::BladeRadius:RuneSwordCombat::BladeRadius)*RuneSwordCombatTuning::RangeMultiplier;
            const int32 Steps=FMath::Max(1,FMath::Max(FMath::CeilToInt((HitEnd-HitStart)*SampleRate),FMath::CeilToInt(AimTravel/TraceRadius)));
            SamplePose(HitStart);FRuneSwordBladeSample Previous=ReadBlade(StartFrame);
            for(int32 Step=1;Step<=Steps;++Step)
            {
                const float T=FMath::Lerp(HitStart,HitEnd,float(Step)/Steps);
                SamplePose(T);const auto Current=ReadBlade(FrameAt(T));SweepBlade(Previous,Current);Previous=Current;
            }
        }
        if(bHeavyTrainingPending&&Next>=ContactEnd)FinishHeavyTraining();
        SamplePose(Next);PreviousAimFrame=AimNow;
        Elapsed=Next;
        if(Elapsed>=End)
        {
            const bool Queued=bQueuedAttack;bAttacking=bQueuedAttack=bHeavyAttack=bThrustAttack=false;
            bLungeStarted=bLungeBlocked=false;LastAttackEnd=GetWorld()->GetTimeSeconds();
            SetClip(TEXT("Idle"),true);if(Queued)BeginAttack();
        }
    }
    else if(bCharging)
    {
        Elapsed=FMath::Min(float(GetWorld()->GetTimeSeconds()-ChargeStartedAt)/RequiredChargeSeconds,1.f)*RuneSwordHeavyRhythm::ChargeSeconds;
        SamplePose(Elapsed); // Retiming keeps the authored charge pose synchronized with the skill clock.
        if(bAutoHeavyRelease&&GetWorld()->GetTimeSeconds()-ChargeStartedAt>=RequiredChargeSeconds)ReleaseHeavyCharge();
    }
    else if(bReturningCharge)
    {
        CancelChargeAge=FMath::Min(CancelChargeDuration,CancelChargeAge+Delta);
        Elapsed=CancelChargeFrom*(1.f-FMath::SmoothStep(0.f,CancelChargeDuration,CancelChargeAge));
        SamplePose(Elapsed); // Reverse the same supported two-hand path, without damage.
        if(CancelChargeAge>=CancelChargeDuration){bReturningCharge=false;SetClip(TEXT("Idle"),true);}
    }
    else if(bInspecting)
    {
        Elapsed=FMath::Min(End,Elapsed+Delta);SamplePose(Elapsed);
        if(Elapsed>=End){bInspecting=false;SetClip(TEXT("Idle"),true);}
    }
    else if(bEquipping)
    {
        Elapsed=FMath::Min(End,Elapsed+Delta);SamplePose(Elapsed);
        if(Elapsed>=End){const bool Queued=bQueuedAttack;bEquipping=bQueuedAttack=false;SetClip(TEXT("Idle"),true);if(Queued)BeginAttack();}
    }
    else
    {
        const FName Clip=Character->GetVelocity().SizeSquared2D()>400?TEXT("Walk"):TEXT("Idle");
        if(Clip!=CurrentClip)SetClip(Clip,true);
        if(CurrentAnimation){Elapsed=FMath::Fmod(Elapsed+Delta*(Character->IsSprinting()?1.45f:1.f),FMath::Max(.01f,CurrentAnimation->GetPlayLength()));SamplePose(Elapsed);}
    }
    const bool Sprint=Character->IsSprinting() && !IsBusy();
    Viewmodel->SetRelativeLocation(FMath::VInterpTo(Viewmodel->GetRelativeLocation(),Sprint?FVector(-4,0,-9):FVector::ZeroVector,Delta,9.f));
    Viewmodel->SetRelativeRotation(FMath::RInterpTo(Viewmodel->GetRelativeRotation(),FRotator(0,90,Sprint?22:0),Delta,9.f));
}

void URuneSwordComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    FinishHeavyTraining();
    ClearGuard();
    bAttacking=bEquipping=bInspecting=bQueuedAttack=bCharging=bReturningCharge=bHeavyAttack=false;HitActors.Reset();
    bThrustAttack=bLungeStarted=bLungeBlocked=false;
    ImpactAge=1.f;
    if(Viewmodel)Viewmodel->DestroyComponent();
    if(RiftVisual)RiftVisual->DestroyComponent();
    Super::EndPlay(Reason);
}
