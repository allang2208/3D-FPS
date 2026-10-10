#include "StaffWeaponComponent.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "StaffArmsMeshComponent.h"
#include "StaffAssembly.h"
#include "StaffCatalog.h"
#include "StaffGripPose.h"
#include "StaffPrimaryAttackMotion.h"
#include "StaffQuickCombatPose.h"
#include "StaffQuickCombatMotion.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../../Skills/QuickCombatPistolMotion.h"
#include "../MeleeSmallTargetQuery.h"
#include "../WeaponStatEvaluation.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../FPSGAMECharacter.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Movement/FPSFootstepAudioComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
    const TCHAR* ArmsPath=TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7");
    const TCHAR* StaffSwingPath=TEXT("/Game/Items/ProductionTools/GripMotion20260913/S_Harvest_Swing.S_Harvest_Swing");
    const TCHAR* StaffImpactPath=TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick");
}
UStaffWeaponComponent::UStaffWeaponComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostPhysics;}
void UStaffWeaponComponent::BeginPlay()
{
    Super::BeginPlay();auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn){SetComponentTickEnabled(false);return;}
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    AddTickPrerequisiteComponent(Pawn->GetCharacterMovement());
    if(auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>())AddTickPrerequisiteComponent(Magic);
    Footsteps=Pawn->FindComponentByClass<UFPSFootstepAudioComponent>();
    if(Footsteps.IsValid())AddTickPrerequisiteComponent(Footsteps.Get());
    Camera=Pawn->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    Staff=NewObject<UStaticMeshComponent>(Pawn,TEXT("StaffAssembly"));Pawn->AddInstanceComponent(Staff);Staff->SetupAttachment(Camera);
    Staff->SetCollisionEnabled(ECollisionEnabled::NoCollision);Staff->SetOnlyOwnerSee(true);Staff->SetCastShadow(false);Staff->RegisterComponent();Staff->SetVisibility(false,true);
    Arms=NewObject<UStaffArmsMeshComponent>(Pawn,TEXT("StaffV7Arms"));Pawn->AddInstanceComponent(Arms);Arms->SetupAttachment(Camera);
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->RegisterComponent();Arms->SetVisibility(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Arms->SetComponentTickEnabled(false);
    AddTickPrerequisiteActor(Pawn);RefreshEquipment(GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
}
void UStaffWeaponComponent::EndPlay(const EEndPlayReason::Type Reason){ResetIllumination();if(Load)Load->CancelHandle();Super::EndPlay(Reason);}
USkeletalMeshComponent* UStaffWeaponComponent::ArmsMesh()const{return Arms;}
void UStaffWeaponComponent::RefreshEquipment(UColdSteelStatusModel* P)
{
    if(!Staff||!Arms||!P)return;const auto* I=P->Equipped();const bool Active=I&&ColdSteelStaff::IsStaff(*I)&&!P->ActiveProductionTool();
    if(!Active)
    {
        Instance.Reset();Recipe.Reset();CancelAction();ResetIllumination();Locomotion.Reset();
        if(Load){Load->CancelHandle();Load.Reset();}
        Staff->SetVisibility(false,true);Arms->SetVisibility(false);Arms->SetComponentTickEnabled(false);
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        return;
    }
    // Keep the equipped staff's sleeves/gloves resident through traversal's
    // temporary render gate. Unequipping releases this retention above.
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    const auto Resolved=ColdSteelStaff::Resolve(*I);
    TArray<FSoftObjectPath> Paths;ColdSteelStaffAssembly::Gather(Resolved,Paths);Paths.AddUnique(FSoftObjectPath(ArmsPath));
    // Presentation depends on the installed meshes, not every inventory field.
    // Offhand/stat refreshes must not hide and reload an unchanged main hand.
    FString Key=I->InstanceId+TEXT("|")+I->Definition;
    for(const auto& Path:Paths)Key+=TEXT("|")+Path.ToString();
    if(Key==Recipe)return;
    ResetIllumination();
    const bool NewInstance=Instance!=I->InstanceId;
    if(NewInstance)
    {
        CancelAction();EquipAge=0;Locomotion.Reset();
        Staff->SetVisibility(false,true);Arms->SetVisibility(false);
    }
    // Keep the current assembly visible during a same-staff part replacement;
    // Apply swaps the complete recipe only after all of its meshes are ready.
    Instance=I->InstanceId;Recipe=Key;
    if(Load){Load->CancelHandle();Load.Reset();}
    Paths.AddUnique(FSoftObjectPath(StaffSwingPath));Paths.AddUnique(FSoftObjectPath(StaffImpactPath));
    auto Ready=FStreamableDelegate::CreateWeakLambda(this,[this,Key,Resolved,NewInstance]()
    {
        if(Recipe!=Key||!Staff||!Arms)return;
        auto* Skin=Cast<USkeletalMesh>(FSoftObjectPath(ArmsPath).ResolveObject());if(!Skin)return;
        if(!ColdSteelStaffAssembly::Apply(Staff,Resolved))return;
        AuthoredGripVariant=StaffGripPose::VariantForMesh(ColdSteelInventory::Text(Resolved,TEXT("staff_part_grip_lining_mesh")));
        SwingSound=Cast<USoundBase>(FSoftObjectPath(StaffSwingPath).ResolveObject());
        ImpactSound=Cast<USoundBase>(FSoftObjectPath(StaffImpactPath).ResolveObject());
        if(Arms->GetSkeletalMeshAsset()!=Skin)Arms->SetSkeletalMesh(Skin);
        // The native V7 M4 derivation also contains weapon sections: expose its skin only.
        if(const auto* Render=Skin->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                const FString N=Skin->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
                const bool Hand=!N.Contains(TEXT("handguard"))&&(N.Contains(TEXT("skin"))||N.Contains(TEXT("manny"))||N.Contains(TEXT("bare"))||N.Contains(TEXT("glove"))||N.Contains(TEXT("sleeve"))||N==TEXT("hand")||N==TEXT("hands")||N.EndsWith(TEXT("_hands")));
                Arms->ShowMaterialSection(M,S,Hand,L);
            }
        // Sample the arm pose after the staff clock/transform, before camera caching.
        // An independent skeletal tick used the previous frame's contact transform.
        if(NewInstance)EquipAge=0;
        Staff->SetRelativeTransform(GripInCamera());
        Arms->SetVisibility(true);Arms->SetComponentTickEnabled(false);Staff->SetVisibility(true,true);
        ConfigureIllumination(Resolved);
    });
    // Even resident assets otherwise wait for the streamable delegate's next
    // tick, while the independently loaded offhand pistol is already visible.
    const bool Resident=!Paths.ContainsByPredicate([](const FSoftObjectPath& Path)
    {
        const auto* Object=Path.ResolveObject();
        return !Object||Object->HasAnyFlags(RF_NeedLoad|RF_NeedPostLoad);
    });
    if(Resident)Ready.Execute();
    else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,MoveTemp(Ready),FStreamableManager::AsyncLoadHighPriority);
}
bool UStaffWeaponComponent::CanBeginCast() const
{
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    return (!Potion||!Potion->IsActive())&&IsEquipped()&&!IsBusy()&&Staff&&Staff->IsVisible()&&Arms&&Arms->IsVisible();
}
FStaffCastPose UStaffWeaponComponent::CarryPoseInCamera() const
{
    // Pos is the hand's contact point, not the centre of the 160 cm mesh.
    // Lean the head forward and slightly inward to frame the upper shaft/head.
    FVector Pos=FVector(44,19,-21)+StaffCastMotion::PresentationOffset()+Locomotion.Offset;
    const FQuat RestRotation=FRotationMatrix::MakeFromZX(FVector(.22,-.12,.968).GetSafeNormal(),FVector::ForwardVector).ToQuat();
    const float Equip=FMath::Clamp(EquipAge/.35f,0.f,1.f);Pos.Z-=35*(1-Equip)*(1-Equip);
    FStaffCastPose Pose;Pose.Contact=FTransform(Locomotion.Rotation*RestRotation,Pos);
    // Carry/run weights feed the complete authored local arm poses. The contact
    // trajectory and these weights enter the same casting/recovery snapshots.
    Pose.ArmWeights[5]=Locomotion.RunWeight();Pose.ArmWeights[0]=1.f-Pose.ArmWeights[5];
    Pose.Shoulder+=StaffCastMotion::PresentationOffset()+Locomotion.RightShoulder;
    Pose.Elbow+=StaffCastMotion::PresentationOffset()+Locomotion.RightElbow;
    // The activation gesture completes once; sustained light does not hold the arm.
    return SampleIlluminationGesture(Pose);
}
FStaffCastPose UStaffWeaponComponent::CastingPoseInCamera() const
{
    const auto Carry=CarryPoseInCamera();
    if(const auto* Magic=GetOwner()->FindComponentByClass<UFPSFireballComponent>();Magic&&Magic->IsStaffCasting())
        return Magic->SampleStaffMotion(Carry);
    return Carry;
}
FStaffCastPose UStaffWeaponComponent::SamplePrimaryPose()const
{
    const auto Carry=CarryPoseInCamera();
    const float Recovery=bBlocked?StaffCastMotion::Ease((Age-BlockedAge)/FMath::Max(.01f,Duration-BlockedAge)):0.f;
    auto Pose=bBlocked
        ?StaffCastMotion::Blend(BlockedPose,Carry,Recovery)
        :StaffPrimaryAttackMotion::Sample(AttackEntry,Carry,Age/Duration);
    if(Arms)
    {
        // Shoulder and elbow FK determine the hand and shaft, including between
        // keys. Do not independently lerp a hand pivot and rotate the arm to it.
        Pose.Contact=Arms->AuthoredContactInCamera(Pose,AuthoredGripVariant);
        const auto& From=bBlocked?BlockedPose:Age<Duration*.4f?AttackEntry:Carry;
        const FTransform Base=Arms->AuthoredContactInCamera(From,AuthoredGripVariant);
        const FTransform Delta=Base.Inverse()*From.Contact;
        float Weight=0.f;
        for(int32 I=0;I<6;++I)Weight+=Pose.ArmWeights[I];
        FTransform Correction;
        Correction.Blend(FTransform::Identity,Delta,bBlocked?1.f-Recovery:Weight);
        Pose.Contact=Pose.Contact*Correction;
        if(bBlocked)
        {
            const FTransform CarryBase=Arms->AuthoredContactInCamera(Carry,AuthoredGripVariant);
            Correction.Blend(FTransform::Identity,CarryBase.Inverse()*Carry.Contact,Recovery);
            Pose.Contact=Pose.Contact*Correction;
        }
    }
    return Pose;
}
FStaffCastPose UStaffWeaponComponent::ActionPoseInCamera() const
{
    if(Age<0.f)return CastingPoseInCamera();
    return StaffPrimaryAttackMotion::Recoil(SamplePrimaryPose(),ImpactAge,ImpactStrength);
}
FTransform UStaffWeaponComponent::AttackRootInCamera(bool bFeedback)const
{
    const auto Pose=bFeedback?ActionPoseInCamera():SamplePrimaryPose();
    const FQuat Rotation=Pose.Contact.GetRotation();
    return FTransform(Rotation,Pose.Contact.GetLocation()-Rotation.RotateVector(StaffGripPose::HoldPoint()));
}
FTransform UStaffWeaponComponent::GripInCamera() const
{
    return AttackRootInCamera(true);
}
void UStaffWeaponComponent::GetCameraMotion(FVector& Location,FRotator& Rotation)const
{
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;if(!IsEquipped())return;
    // A wall contact returns from its actual pose; do not keep pitching down
    // with the part of the swing that was stopped by the wall.
    const float CameraT=bBlocked?BlockedAge/Duration:Age>=0.f?Age/Duration:-1.f;
    StaffPrimaryAttackMotion::Camera(CameraT,-1.f,0.f,Location,Rotation);
    if(bBlocked)
    {
        const float Weight=1.f-StaffCastMotion::Ease((Age-BlockedAge)/FMath::Max(.01f,Duration-BlockedAge));
        Location*=Weight;Rotation*=Weight;
    }
    FVector Kick;FRotator Turn;
    StaffPrimaryAttackMotion::Camera(-1.f,ImpactAge,ImpactStrength,Kick,Turn);
    Location+=Kick;Rotation+=Turn;
}
void UStaffWeaponComponent::BeginPrimaryAttack()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!IsEquipped()||IsBusy()||!Pawn||!Staff||!Staff->IsVisible()||Pawn->IsSpellGestureBlocking()||Pawn->IsCastBlockingLeftHandAction())return;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    auto* P=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P->Equipped();if(!I||I->InstanceId!=Instance)return;
    Damage=ColdSteelWeaponStats::Damage(*I,P,3);Duration=FMath::Max(.1,double(ColdSteelWeaponStats::Interval(I,P,.5)));
    Shot=ColdSteelSkills::Snapshot(Pawn,I);Shot.bRifle=false;Shot.bPistol=false;Shot.WeakpointPercent=0;Shot.AttackForm=EMonsterAttackForm::Blunt;Shot.bMeleeStrike=true;
    const auto Entry=CarryPoseInCamera();CancelAction();AttackEntry=Entry;Age=0;
    Previous=AttackRootInCamera(false)*Pawn->GetMeleeAimTransform();
}
void UStaffWeaponComponent::CancelAction()
{
    if(IsQuickCombatActive())
        if(auto* Quick=GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>())Quick->Cancel();
    IlluminationGestureAge=-1.f;
    Age=-1;HitActors.Reset();bBlocked=false;HitStopRemaining=0;ImpactAge=-1;ImpactStrength=0;
    bSwingSoundPlayed=false;bAirImpulse=false;bImpactConfirmed=false;
}
void UStaffWeaponComponent::ConfirmImpact(const FHitResult& Hit,bool bWorld)
{
    if(bWorld)
    {
        BlockedPose=SamplePrimaryPose();
        BlockedAge=Age;bBlocked=true;
    }
    // Only the first accepted contact pauses and punches. Multiple targets
    // still receive their one damage receipt without stacking camera impulses.
    if(bImpactConfirmed)return;
    bImpactConfirmed=true;ImpactAge=0;ImpactStrength=bWorld?1.15f:1.f;
    HitStopRemaining=bWorld?StaffPrimaryAttackMotion::WallStopSeconds:StaffPrimaryAttackMotion::FleshStopSeconds;
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,bWorld?.8f:.95f,bWorld?.78f:.86f);
}
void UStaffWeaponComponent::TraceSwing(const FTransform& From,const FTransform& To)
{
    if(bBlocked)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    // QuickCombatStats copies this cached definition's range unchanged. Read
    // the range alone, without recomputing damage/modifiers for every substep.
    const float Reach=Profile?Profile->QuickCombatDefinition().QuickCombat.RangeCM:FQuickCombatTuning{}.RangeCM;
    const float Radius=Pawn->HasOffhandPistol()?QuickCombatPistolMotion::QueryRadiusCM:StaffQuickCombatMotion::QueryRadiusCM;
    const FVector Start=To.TransformPosition(StaffGripPose::HoldPoint());
    FCollisionQueryParams Q(SCENE_QUERY_STAT(StaffSwing),false,GetOwner());
    for(const auto& Actor:HitActors)if(Actor.IsValid())Q.AddIgnoredActor(Actor.Get());
    TArray<FHitResult,TInlineAllocator<8>> Contacts;
    // Use quick melee's forward sphere and low-target coverage, while retaining
    // the ordinary swing's per-target cleave. A rear windup is not a strike.
    if(FVector::DotProduct(Start-Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X))>=0.f)
        Contacts.Append(MeleeSmallTargets::QueryQuickAreaContacts(GetWorld(),Pawn,Aim,Start,Reach,Radius));
    // Keep actual shaft/tip contact with scenery and its blocked recovery.
    // Monster damage now comes exclusively from the shared range query above.
    for(int32 Segment=0;Segment<=6;++Segment)
    {
        const FVector Local(0,0,32.f+Segment*8.f),A=From.TransformPosition(Local),B=To.TransformPosition(Local);
        FHitResult Hit;
        if(GetWorld()->SweepSingleByChannel(Hit,A,B,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(Segment==6?6.f:4.5f),Q))
            if(const auto* Actor=Hit.GetActor();Actor&&!Actor->FindComponentByClass<UMonsterCombatComponent>())Contacts.Add(Hit);
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const auto& Hit:Contacts)
    {
        auto* Actor=Hit.GetActor();if(!Actor||Actor->ActorHasTag(TEXT("Friendly")))continue;
        if(HitActors.Contains(Actor))continue;
        auto* Combat=Actor->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)
        {
            UWardBreakableGlass::BreakHit(Hit,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal());
            ConfirmImpact(Hit,true);return;
        }
        HitActors.Add(Actor);
        if(Combat->IsDead())continue;
        FWeaponDamageResult Receipt;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,Damage,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),Shot,&Receipt);
        if(Applied>0.f||Combat->IsDead())
        {
            ConfirmImpact(Hit,false);
            Pawn->NotifyConfirmedWeaponHit(Actor,Applied,&Receipt,false);
        }
    }
}
void UStaffWeaponComponent::AdvanceActionBeforeCamera(float Delta)
{
    if(!IsEquipped()||Delta<=0.f)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead()){bIlluminationOn=false;IlluminationBlend=0.f;}
    UpdateIllumination(Delta);
    if((PC&&PC->bShowMouseCursor)||(Health&&Health->IsDead())){CancelAction();return;}
    if(auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();Quick&&Quick->GetStyle()==EQuickCombatStyle::StaffPunch)
        Quick->AdvanceAction(Delta);
    float Remaining=Delta;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    while(Remaining>UE_SMALL_NUMBER&&Age>=0.f)
    {
        if(HitStopRemaining>0.f)
        {
            const float Pause=FMath::Min(Remaining,HitStopRemaining);
            HitStopRemaining-=Pause;Remaining-=Pause;ImpactAge+=Pause;
            Previous=AttackRootInCamera(false)*Aim;
            continue;
        }
        const float Before=Age;
        float End=FMath::Min(Duration,Age+FMath::Min(Remaining,Duration/90.f));
        // Land exactly on the phase boundaries, so slow/fast frames neither
        // trace backwards during the lift nor omit the first descending segment.
        for(const float Boundary:{StaffPrimaryAttackMotion::StrikeStart,StaffPrimaryAttackMotion::ContactTime,StaffPrimaryAttackMotion::StrikeEnd})
            if(Age<Duration*Boundary)End=FMath::Min(End,Duration*Boundary);
        const float Step=End-Age;if(Step<=0.f)break;
        Age=End;Remaining=FMath::Max(0.f,Remaining-Step);
        if(ImpactAge>=0.f)ImpactAge+=Step;
        if(!bSwingSoundPlayed&&Age>=Duration*StaffPrimaryAttackMotion::StrikeStart)
        {
            bSwingSoundPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.48f,FMath::Clamp(.5f/Duration*.82f,.68f,1.35f));
        }
        const FTransform Now=AttackRootInCamera(false)*Aim;
        if(Before>=Duration*StaffPrimaryAttackMotion::StrikeStart&&Before<Duration*StaffPrimaryAttackMotion::StrikeEnd)TraceSwing(Previous,Now);
        Previous=Now;
        if(!bAirImpulse&&Age>=Duration*StaffPrimaryAttackMotion::ContactTime)
        {
            bAirImpulse=true;
            if(!bImpactConfirmed){ImpactAge=0;ImpactStrength=.22f;}
        }
        if(Age>=Duration)
        {
            Age=-1;HitActors.Reset();bBlocked=false;HitStopRemaining=0;
        }
    }
    if(ImpactAge>=0.f)
    {
        ImpactAge+=Remaining;
        if(ImpactAge>=StaffPrimaryAttackMotion::ImpactSeconds){ImpactAge=-1;ImpactStrength=0;}
    }
}
void UStaffWeaponComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);if(!IsEquipped()||!Staff||!Camera)return;
    EquipAge+=Delta;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if((PC&&PC->bShowMouseCursor)||(Health&&Health->IsDead()))CancelAction();
    const auto* Magic=GetOwner()->FindComponentByClass<UFPSFireballComponent>();
    if(Pawn)Locomotion.Update(*Pawn,Footsteps.Get(),Delta,IsBusy()||IlluminationGestureAge>=0.f||(Magic&&Magic->IsGestureActive())
        ||Pawn->IsSpellGestureBlocking()||(PC&&PC->bShowMouseCursor)||(Health&&Health->IsDead()));
    // Character::UpdateCamera already advanced the one action clock and sampled
    // its feedback this frame. Only publish the matching staff/arm pose here.
    Staff->SetRelativeTransform(GripInCamera());
    PublishIllumination();
    if(Arms&&Arms->IsVisible()&&!Arms->bHiddenInGame)
    {
        Arms->TickAnimation(0.f,false);
        Arms->RefreshBoneTransforms();
    }
}
