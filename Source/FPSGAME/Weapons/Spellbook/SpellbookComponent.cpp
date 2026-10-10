#include "SpellbookComponent.h"
#include "SpellbookAuthoredGrip.h"
#include "SpellbookCarryTuning.h"
#include "SpellbookAuthoredStrike.h"
#include "SpellbookFocusMotion.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../Staff/StaffWeaponComponent.h"
#include "../Staff/StaffCatalog.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Movement/FPSFootstepAudioComponent.h"
#include "../../Movement/FPSDoorPushComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Characters/FPSModularOutfitComponent.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
const FSoftObjectPath ArmsPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
const FSoftObjectPath BookPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Meshes/SM_Spellbook_Alchemy_Closed.SM_Spellbook_Alchemy_Closed"));
const FSoftObjectPath FocusBookPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Meshes/SK_Spellbook_Alchemy.SK_Spellbook_Alchemy"));
const FSoftObjectPath OpenPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Animations/A_Spellbook_Open.A_Spellbook_Open"));
const FSoftObjectPath FlipPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Animations/A_Spellbook_FlipPages.A_Spellbook_FlipPages"));
const FSoftObjectPath GoldPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Effects/M_Spellbook_GoldOrbit.M_Spellbook_GoldOrbit"));
}

void USpellbookArmsMeshComponent::CachePose()
{
    auto* Mesh=GetSkeletalMeshAsset();if(!Mesh||CachedMesh.Get()==Mesh)return;
    CachedMesh=Mesh;FocusKeys.Reset();FocusEntry.Reset();ReturnKeys.Reset();ReturnEntry.Reset();
    const auto& Ref=Mesh->GetRefSkeleton();Reference=Ref.GetRefBonePose();
    for(int32 I=0;I<Reference.Num();++I)if(Ref.GetParentIndex(I)>=0)Reference[I]=Reference[I]*Reference[Ref.GetParentIndex(I)];
    namespace Grip=SpellbookAuthoredGrip;
    LeftBones.Reset();RightBones.Reset();
    for(const auto* Name:Grip::ArmNames)LeftBones.Add(Ref.FindBoneIndex(Name));
    const int32 Right=Ref.FindBoneIndex(TEXT("clavicle_r"));
    for(int32 I=0;I<Reference.Num();++I)if(Right>=0&&(I==Right||Ref.BoneIsChildOf(I,Right)))RightBones.Add(I);
    for(int32 K=0;K<Grip::PoseCount;++K)
    {
        CarryKeys[K]=Ref.GetRefBonePose();
        for(int32 B=0;B<Grip::BoneCount;++B)if(const int32 I=LeftBones[B];I>=0)
        {
            const int32 Parent=Ref.GetParentIndex(I);
            const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            CarryKeys[K][I].SetLocation(Grip::Poses[K][B].Position/Scale);
            CarryKeys[K][I].SetRotation(Grip::Poses[K][B].Rotation.GetNormalized());
        }
    }
    StrikeKeys.SetNum(SpellbookAuthoredStrike::KeyCount);StrikeEntry.Reset();
    for(int32 K=0;K<StrikeKeys.Num();++K)
    {
        StrikeKeys[K]=Ref.GetRefBonePose();
        for(int32 B=0;B<Grip::BoneCount;++B)if(const int32 I=LeftBones[B];I>=0)
        {
            const int32 Parent=Ref.GetParentIndex(I);
            const FVector Scale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            const auto& Key=SpellbookAuthoredStrike::Poses[K][B];
            StrikeKeys[K][I].SetLocation(Key.Position/Scale);
            StrikeKeys[K][I].SetRotation(Key.Rotation.GetNormalized());
        }
    }
}

void USpellbookArmsMeshComponent::CaptureQuickCombatEntry(uint32 Serial)
{
    CachePose();const auto* Mesh=GetSkeletalMeshAsset();
    const auto* View=GetOwner()?GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    const auto& Pose=GetComponentSpaceTransforms();
    if(!Mesh||!View||Pose.Num()!=Reference.Num())return;
    auto InCamera=Reference;const auto& Ref=Mesh->GetRefSkeleton();
    const FVector Offset=FVector(0,0,-SpellbookCarryTuning::LowerCm)+CarryOffset;
    for(const int32 I:LeftBones)if(I>=0)
    {
        InCamera[I]=(Pose[I]*GetComponentTransform()).GetRelativeTransform(View->GetComponentTransform());
        InCamera[I].AddToTranslation(-Offset);
    }
    StrikeEntry=CarryKeys[0];
    for(const int32 I:LeftBones)if(I>=0)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        const auto Local=Parent>=0?InCamera[I].GetRelativeTransform(InCamera[Parent]):InCamera[I];
        StrikeEntry[I].SetLocation(Local.GetLocation());
        StrikeEntry[I].SetRotation(Local.GetRotation().GetNormalized());
    }
    StrikeSerial=Serial;
}

void USpellbookArmsMeshComponent::ApplyQuickCombat(TArray<FTransform>& LocalPose)
{
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    if(!Quick||Quick->GetStyle()!=EQuickCombatStyle::SpellbookPush||!Quick->IsOccupyingLeftHand()||StrikeKeys.IsEmpty())return;
    namespace Strike=SpellbookAuthoredStrike;
    if(StrikeSerial!=Quick->GetActionSerial()||StrikeEntry.Num()!=LocalPose.Num())
    {StrikeSerial=Quick->GetActionSerial();StrikeEntry=LocalPose;}
    const float Age=Quick->GetActionAge();int32 A=0;
    while(A<Strike::KeyCount-2&&Age>=Strike::Times[A+1])++A;
    const float Alpha=FMath::Clamp((Age-Strike::Times[A])/(Strike::Times[A+1]-Strike::Times[A]),0.f,1.f);
    const float EntryWeight=1.f-FMath::SmoothStep(0.f,Strike::Cock,Age);
    const float Return=FMath::SmoothStep(Strike::Recover,Strike::Length,Age);
    for(const int32 I:LeftBones)if(I>=0)
    {
        FTransform Target,Mixed;Target.Blend(StrikeKeys[A][I],StrikeKeys[A+1][I],Alpha);
        // Remove the live gait offset gradually; never snap into a frozen idle key.
        const FQuat Delta=StrikeEntry[I].GetRotation()*StrikeKeys[0][I].GetRotation().Inverse();
        Target.SetRotation((FQuat::Slerp(FQuat::Identity,Delta,EntryWeight)*Target.GetRotation()).GetNormalized());
        Target.AddToTranslation((StrikeEntry[I].GetLocation()-StrikeKeys[0][I].GetLocation())*EntryWeight);
        Mixed.Blend(Target,LocalPose[I],Return);LocalPose[I]=Mixed;
    }
}

void USpellbookArmsMeshComponent::FinalizeBoneTransform()
{
    CachePose();auto* Mesh=GetSkeletalMeshAsset();
    const auto* Camera=GetOwner()?GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(Mesh&&Camera&&Pose.Num()==Reference.Num())
    {
        const auto& Ref=Mesh->GetRefSkeleton();
        namespace Grip=SpellbookAuthoredGrip;
        Pose=CarryKeys[0];
        // Keep the shared unarmed/offhand stride clock, but settle the book
        // around the photo grip with a smaller whole-arm gait envelope.
        const float Sample=FMath::Fmod(StridePhase/(2.f*PI)*Grip::Samples+Grip::Samples,float(Grip::Samples));
        const int32 A=FMath::FloorToInt(Sample),B=(A+1)%Grip::Samples;
        const float Alpha=Sample-A;
        const float Variation=.972f+.018f*FMath::Sin(MotionTime*.71f)+.010f*FMath::Sin(MotionTime*1.13f+.8f);
        const float CarryWeight=MoveWeight*Variation*FMath::Lerp(SpellbookCarryTuning::WalkScale,SpellbookCarryTuning::RunScale,RunWeight);
        for(const int32 I:LeftBones)if(I>=0)
        {
            FTransform Walk,Run,Gait,Mixed;
            Walk.Blend(CarryKeys[1+A][I],CarryKeys[1+B][I],Alpha);
            Run.Blend(CarryKeys[1+Grip::Samples+A][I],CarryKeys[1+Grip::Samples+B][I],Alpha);
            Gait.Blend(Walk,Run,RunWeight);Mixed.Blend(Pose[I],Gait,CarryWeight);Pose[I]=Mixed;
        }
        ApplyFocusPose(Pose);ApplyQuickCombat(Pose);
        for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
        const FTransform ToMesh=Camera->GetComponentTransform().GetRelativeTransform(GetComponentTransform());
        const FVector LowCarry(0,0,-SpellbookCarryTuning::LowerCm);
        const auto* Spellbook=GetOwner()->FindComponentByClass<USpellbookComponent>();
        const FVector CatchOffset=Spellbook?Spellbook->FocusCatchOffset():FVector::ZeroVector;
        for(const int32 I:LeftBones)if(I>=0)
        {
            Pose[I].SetLocation(ToMesh.TransformPosition(Pose[I].GetLocation()+LowCarry+CarryOffset+CatchOffset));
            Pose[I].SetRotation((ToMesh.GetRotation()*Pose[I].GetRotation()).GetNormalized());
        }
        const FTransform Hidden(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector);
        for(const int32 I:RightBones)Pose[I]=Hidden;
    }
    // This rig also owns the existing lower/use/raise consumable transition.
    Super::FinalizeBoneTransform();
}

USpellbookComponent::USpellbookComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostPhysics;}

void USpellbookComponent::BeginPlay()
{
    Super::BeginPlay();auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer)
    {SetComponentTickEnabled(false);return;}
    Camera=Pawn->FindComponentByClass<UCameraComponent>();if(!Camera.IsValid())return;
    AddTickPrerequisiteActor(Pawn);AddTickPrerequisiteComponent(Pawn->GetCharacterMovement());
    Footsteps=Pawn->FindComponentByClass<UFPSFootstepAudioComponent>();
    if(Footsteps.IsValid())AddTickPrerequisiteComponent(Footsteps.Get());
    if(auto* Outfit=Pawn->FindComponentByClass<UFPSModularOutfitComponent>())Outfit->AddTickPrerequisiteComponent(this);
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->AddTickPrerequisiteComponent(this);
    if(auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>())Potion->AddTickPrerequisiteComponent(this);
    Arms=NewObject<USpellbookArmsMeshComponent>(Pawn,TEXT("SpellbookV7LeftArm"));
    Pawn->AddInstanceComponent(Arms);Arms->SetupAttachment(Camera.Get());
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCanEverAffectNavigation(false);
    Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->bReceivesDecals=false;
    Arms->SetVisibility(false);Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->SetBoundsScale(2.f);
    Book=NewObject<UStaticMeshComponent>(Pawn,TEXT("OffhandAlchemySpellbook"));
    Pawn->AddInstanceComponent(Book);Book->SetupAttachment(Camera.Get());
    Book->SetCollisionEnabled(ECollisionEnabled::NoCollision);Book->SetCanEverAffectNavigation(false);
    Book->SetOnlyOwnerSee(true);Book->SetCastShadow(false);Book->bReceivesDecals=false;
    Book->SetVisibility(false);Book->RegisterComponent();
    if(Pawn->GetGameInstance())Model=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model.IsValid())EquipmentChanged=Model->OnChanged.AddUObject(this,&USpellbookComponent::RefreshEquipment);
    RefreshEquipment();
}

void USpellbookComponent::RefreshEquipment()
{
    bool Active=false;bEquipmentResolved=false;bFocusPair=false;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Model.IsValid()&&Pawn&&Pawn->IsLocallyControlled())
    {
        const auto State=Model->Snapshot();const auto* Item=Model->Equipped(State.ActiveWeaponSlot==6?8:11);
        Active=Item&&Item->Definition==TEXT("ue_alchemy_spellbook")&&!Model->ActiveProductionTool();
        const auto* Primary=Model->Equipped(State.ActiveWeaponSlot);
        bFocusPair=Active&&Primary&&ColdSteelStaff::IsStaff(*Primary);
        bEquipmentResolved=true;
    }
    if(!bFocusPair)CancelFocus();
    if(Active==bEquipped)return;
    bEquipped=Active;Locomotion.Reset();
    if(!Arms||!Book)return;
    if(!Active)
    {
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        if(Load){Load->CancelHandle();Load.Reset();}UpdateVisibility();return;
    }
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    if(ArmsPath.ResolveObject()&&BookPath.ResolveObject()&&FocusBookPath.ResolveObject()&&OpenPath.ResolveObject()&&FlipPath.ResolveObject()&&GoldPath.ResolveObject())ApplyAssets();
    else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{ArmsPath,BookPath,FocusBookPath,OpenPath,FlipPath,GoldPath},
        FStreamableDelegate::CreateUObject(this,&USpellbookComponent::ApplyAssets));
}

void USpellbookComponent::ApplyAssets()
{
    if(!bEquipped||!Arms||!Book)return;
    auto* Skin=Cast<USkeletalMesh>(ArmsPath.ResolveObject());auto* Mesh=Cast<UStaticMesh>(BookPath.ResolveObject());
    if(!Skin||!Mesh)return;
    Arms->SetSkeletalMesh(Skin);Book->SetStaticMesh(Mesh);
    if(!FocusBook)CreateFocusMeshes();
    CreateFocusGold(Cast<UMaterialInterface>(GoldPath.ResolveObject()));
    OpenClip=Cast<UAnimSequence>(OpenPath.ResolveObject());FlipClip=Cast<UAnimSequence>(FlipPath.ResolveObject());
    if(FocusBook&&FocusWorldBook)if(auto* Animated=Cast<USkeletalMesh>(FocusBookPath.ResolveObject()))
    {
        FocusBook->SetSkeletalMesh(Animated);FocusBook->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        FocusWorldBook->SetSkeletalMesh(Animated);FocusWorldBook->SetLeaderPoseComponent(FocusBook);
    }
    if(const auto* Render=Skin->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString N=Skin->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            const bool Hand=!N.Contains(TEXT("handguard"))&&(N.Contains(TEXT("skin"))||N.Contains(TEXT("manny"))||
                N.Contains(TEXT("bare"))||N.Contains(TEXT("glove"))||N.Contains(TEXT("sleeve"))||N==TEXT("hand")||N==TEXT("hands")||N.EndsWith(TEXT("_hands")));
            Arms->ShowMaterialSection(M,S,Hand,L);
        }
    Arms->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"));Hand.SetScale3D(FVector::OneVector);
    Book->SetWorldTransform(SpellbookAuthoredGrip::BookInHand*Hand);
    UpdateVisibility();
}

bool USpellbookComponent::OwnsLeftHand() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!bEquipped||!Pawn||!Pawn->IsLocallyControlled()||!Arms||!Arms->GetSkeletalMeshAsset()||!Book||!Book->GetStaticMesh())return false;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    // UI input ownership must not give the equipped book's arm back to another rig.
    // Quick combat keeps its separate CanStartQuickCombatPriority input gate.
    if(!PC||Pawn->IsTraversing()||Pawn->IsSwitchingWeapon())return false;
    // Main-hand reload/inspection/melee temporarily needs its native support
    // arm. The equipment identity remains unchanged while presentation yields.
    if(Pawn->HasInventoryWeapon()&&(Pawn->IsReloading()||Pawn->WeaponState==EAKMWeaponState::Equipping||Pawn->WeaponState==EAKMWeaponState::Inspecting||Pawn->WeaponState==EAKMWeaponState::QuickCombat))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    return true;
}

void USpellbookComponent::UpdateVisibility()
{
    if(!Arms||!Book)return;const bool Show=OwnsLeftHand();
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const bool ShowBook=Show&&(!Potion||!Potion->IsOffhandWeaponHidden())&&!Cast<AFPSGAMECharacter>(GetOwner())->IsDoorPushActive();
    if(Arms->IsVisible()!=Show)Arms->SetVisibility(Show);
    const bool Floating=ShowBook&&IsFocusActive()&&bFocusDetached;
    if(Book->IsVisible()!=(ShowBook&&!Floating))Book->SetVisibility(ShowBook&&!Floating);
    if(FocusBook&&FocusBook->IsVisible()!=Floating)FocusBook->SetVisibility(Floating);
    if(FocusWorldBook&&FocusWorldBook->IsVisible()!=Floating)FocusWorldBook->SetVisibility(Floating);
    ShowFocusGold(Floating&&GoldFade>UE_SMALL_NUMBER);
}

void USpellbookComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Pawn->IsLocallyControlled())return;
    if(!bEquipmentResolved)RefreshEquipment();
    if(!bEquipped)return;
    AdvanceFocus(Delta);
    UpdateVisibility();if(!Arms||!Arms->IsVisible())return;
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const bool Action=IsQuickCombatActive()||IsFocusActive()||(Potion&&Potion->IsActive())||(Staff&&Staff->IsEquipped()&&Staff->IsBusy())||(Magic&&Magic->IsGestureActive())||Pawn->IsDoorPushActive();
    Locomotion.Update(*Pawn,Footsteps.Get(),Delta,Action);
    Arms->StridePhase=Locomotion.StridePhase();Arms->MoveWeight=Locomotion.MoveWeight()*(Pawn->bIsCrouched?.6f:1.f);
    Arms->RunWeight=Locomotion.RunWeight();Arms->MotionTime=Locomotion.MotionTime();
    Arms->CarryOffset=Potion&&Potion->IsStowingOffhand()?FVector(-7,-3,-42)*Potion->OffhandLowerWeight():FVector::ZeroVector;
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    // Same-frame rigid contact, including the native hand's scale-100 import.
    FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"));Hand.SetScale3D(FVector::OneVector);
    Book->SetWorldTransform(SpellbookAuthoredGrip::BookInHand*Hand);
    PresentFocusBook();UpdateVisibility();
}

bool USpellbookComponent::IsQuickCombatActive() const
{
    const auto* Quick=GetOwner()?GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>():nullptr;
    return Quick&&Quick->GetStyle()==EQuickCombatStyle::SpellbookPush&&Quick->IsOccupyingLeftHand();
}

bool USpellbookComponent::BeginQuickCombat()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->CanStartQuickCombatPriority()||!OwnsLeftHand())return false;
    if(IsFocusActive())
    {bFocusDesired=false;bQueuedBookStrike=true;if(!bFocusClosing)BeginCloseFocus();return true;}
    if(!Book->IsVisible())return false;
    auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();if(!Quick)return false;
    Arms->CaptureQuickCombatEntry(Quick->GetActionSerial()+1u);
    Pawn->InterruptActionsForPriority(false);Pawn->ExitSprintForWeapon();
    Quick->ConfigureForSpellbookPush();return Quick->BeginAction();
}

void USpellbookComponent::AdvanceActionBeforeCamera(float Delta)
{
    // Advance the shared clock once, including its impact tail after recovery.
    if(auto* Quick=GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>();Quick&&Quick->GetStyle()==EQuickCombatStyle::SpellbookPush)
        Quick->AdvanceAction(Delta);
}

bool USpellbookComponent::GetQuickCombatStrikeProbe(FVector& Origin)
{
    if(!IsQuickCombatActive()||!OwnsLeftHand())return false;
    // The action clock is held at Contact while resolving this exact authored pose.
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    FTransform Hand=Arms->GetSocketTransform(TEXT("hand_l"));Hand.SetScale3D(FVector::OneVector);
    const FTransform Frame=SpellbookAuthoredGrip::BookInHand*Hand;
    Book->SetWorldTransform(Frame);
    Origin=Frame.TransformPosition(SpellbookAuthoredStrike::ContactPointBookCM);return true;
}

void USpellbookComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelFocus();
    if(Model.IsValid()&&EquipmentChanged.IsValid())Model->OnChanged.Remove(EquipmentChanged);
    if(Load)Load->CancelHandle();Super::EndPlay(Reason);
}
