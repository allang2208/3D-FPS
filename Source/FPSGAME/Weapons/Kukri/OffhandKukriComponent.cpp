#include "OffhandKukriComponent.h"
#include "OffhandKukriAuthoredPose.h"
#include "OffhandKukriAuthoredStrike.h"
#include "OffhandKukriAuthoredUppercut.h"
#include "../Spellbook/SpellbookPistolArmSolver.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Characters/FPSModularOutfitComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
// Same native V9 off-hand arm as the spellbook; the accepted kukri mesh.
const FSoftObjectPath ArmsPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
const FSoftObjectPath KukriPath(TEXT("/Game/Weapons/Kukri20261020/SM_Kukri.SM_Kukri"));
// Lowering arc (camera cm, added to the stance wrist): the fist first pulls back toward the body, then drops out
// of view below the frame; quadratic Bezier stance -> control -> end. The hand turns the blade down meanwhile.
const FVector LowerArcControl(-6.f,-7.f,-10.f);
const FVector LowerArcEnd(-8.f,-6.f,-34.f);
const FQuat LowerHandTurn(FVector::RightVector,FMath::DegreesToRadians(55.f));
// Draw entry: the knife hand rises into the hold while the pistol is drawn (or whenever the pair re-presents).
constexpr float EntryDelaySeconds=.06f,EntryRiseSeconds=.42f;
// The native support hand starts the reload clip on the grip: bring it in from below instead of popping it there.
const FVector NativeReloadEntryOffset(-7.f,-3.f,-42.f);
constexpr float NativeReloadEntrySeconds=.28f;
float Smooth(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
}

void UOffhandKukriArmsMeshComponent::CacheRig()
{
    auto* Mesh=GetSkeletalMeshAsset();if(!Mesh||CachedMesh.Get()==Mesh)return;
    CachedMesh=Mesh;
    const auto& Ref=Mesh->GetRefSkeleton();
    Reference=Ref.GetRefBonePose();
    for(int32 I=0;I<Reference.Num();++I)if(const int32 P=Ref.GetParentIndex(I);P>=0)Reference[I]*=Reference[P];
    Clavicle=Ref.FindBoneIndex(TEXT("clavicle_l"));Upper=Ref.FindBoneIndex(TEXT("upperarm_l"));
    Lower=Ref.FindBoneIndex(TEXT("lowerarm_l"));Hand=Ref.FindBoneIndex(TEXT("hand_l"));
    Twist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_l"));Twist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_l"));
    LeftBones.Reset();RightBones.Reset();
    const int32 Right=Ref.FindBoneIndex(TEXT("clavicle_r"));
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        if(Clavicle>=0&&(I==Clavicle||Ref.BoneIsChildOf(I,Clavicle)))LeftBones.Add(I);
        if(Right>=0&&(I==Right||Ref.BoneIsChildOf(I,Right)))RightBones.Add(I);
    }
    // Contact-fitted fist: native bind translations, authored digit rotations.
    Source=Reference;
    TMap<FName,FQuat> Digits;
    for(const auto& D:OffhandKukriPose::Digits)Digits.Add(FName(D.Name),D.LocalRotation);
    for(const int32 I:LeftBones)
    {
        const int32 P=Ref.GetParentIndex(I);
        const FQuat* Rotation=Digits.Find(Ref.GetBoneName(I));
        if(P<0||!Rotation)continue;
        FTransform Local=Reference[I].GetRelativeTransform(Reference[P]);
        Local.SetRotation(Rotation->GetNormalized());
        Source[I]=Local*Source[P];
    }
    // Mirrored uppercut: the clip's forward grip, swapped in inside its digits window.
    SourceUpper=Reference;
    TMap<FName,FQuat> UpperDigits;
    for(const auto& D:OffhandKukriUpper::Digits)UpperDigits.Add(FName(D.Name),D.LocalRotation);
    for(const int32 I:LeftBones)
    {
        const int32 P=Ref.GetParentIndex(I);
        const FQuat* Rotation=UpperDigits.Find(Ref.GetBoneName(I));
        if(P<0||!Rotation)continue;
        FTransform Local=Reference[I].GetRelativeTransform(Reference[P]);
        Local.SetRotation(Rotation->GetNormalized());
        SourceUpper[I]=Local*SourceUpper[P];
    }
    Target=Source;
}

void UOffhandKukriArmsMeshComponent::FinalizeBoneTransform()
{
    CacheRig();
    const auto* Camera=GetOwner()?GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(Camera&&GetSkeletalMeshAsset()&&Pose.Num()==Reference.Num()&&Clavicle>=0&&Upper>=0&&Lower>=0&&Hand>=0)
    {
        namespace K=OffhandKukriPose;
        const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
        FVector Offset,Shoulder,Pole;FQuat HandRotation;
        bool ForwardGrip=false;
        float ClavicleShare=0.f;
        if(StrikeTime>=0.f)
        {
            // The quick-melee flourish: its key table replaces the stance lerp outright.
            FTransform Framing;
            OffhandKukriStrike::SamplePose(StrikeTime,Offset,HandRotation,Shoulder,Pole,Framing);
            ClavicleShare=OffhandKukriStrike::SampleClavicle(StrikeTime);
        }
        else if(UppercutTime>=0.f)
        {
            // The mirrored uppercut: same key-table sampling; the forward grip only
            // exists inside its window (entry and exit hold the reversed grip).
            FTransform Framing;
            OffhandKukriUpper::SamplePose(UppercutTime,Offset,HandRotation,Shoulder,Pole,Framing);
            ForwardGrip=UppercutTime>=OffhandKukriUpper::DigitsAt&&UppercutTime<=OffhandKukriUpper::DigitsEnd;
            ClavicleShare=OffhandKukriUpper::SampleClavicle(UppercutTime);
        }
        else
        {
            const float A=K::Ease(AimWeight);
            // The left wrist rides on this frame's pistol hand; on the way in and out
            // of ADS the fist dips under the right wrist before settling.
            Offset=FMath::Lerp(K::Hip.LeftWristFromRightHand,K::Aim.LeftWristFromRightHand,A);
            Offset.Z-=K::TransferDipCm*FMath::Sin(PI*A);
            HandRotation=FQuat::Slerp(K::Hip.LeftHand,K::Aim.LeftHand,A).GetNormalized();
            Shoulder=FMath::Lerp(K::Hip.LeftShoulder,K::Aim.LeftShoulder,A);
            Pole=FMath::Lerp(K::Hip.LeftPole,K::Aim.LeftPole,A);
            if(LowerWeight>0.f)
            {
                const float S=FMath::Clamp(LowerWeight,0.f,1.f);
                Offset+=2.f*(1.f-S)*S*LowerArcControl+S*S*LowerArcEnd;
                HandRotation=(FQuat::Slerp(FQuat::Identity,LowerHandTurn,S)*HandRotation).GetNormalized();
            }
        }
        const SpellbookPistolArm::FJoints J{Clavicle,Upper,Lower,Hand,Twist01,Twist02};
        SpellbookPistolArm::Solve(Ref,Reference,ForwardGrip?SourceUpper:Source,LeftBones,J,Shoulder,
            RightHandInCamera+Offset,Pole,HandRotation,0.f,1.f,Target);
        if(ClavicleShare>0.f)
        {
            // The bind clavicle points back along camera -X; a raised upper arm pinches the shoulder skin
            // against it, so the clavicle turns with a share of the upper arm about the shoulder joint.
            const FQuat Bind=Reference[Clavicle].GetRotation();
            const FVector UpperInClavicle=Bind.UnrotateVector(Reference[Upper].GetLocation()-Reference[Clavicle].GetLocation());
            const FQuat Deform=Target[Upper].GetRotation()*Reference[Upper].GetRotation().Inverse();
            const FQuat Turned=(FQuat::Slerp(FQuat::Identity,Deform,ClavicleShare)*Bind).GetNormalized();
            Target[Clavicle].SetRotation(Turned);
            Target[Clavicle].SetLocation(Target[Upper].GetLocation()-Turned.RotateVector(UpperInClavicle));
        }
        const FTransform ToMesh=Camera->GetComponentTransform().GetRelativeTransform(GetComponentTransform());
        Pose=Reference;
        for(const int32 I:LeftBones)
        {
            // Keep each bone's native scale.
            Pose[I].SetLocation(ToMesh.TransformPosition(Target[I].GetLocation()));
            Pose[I].SetRotation((ToMesh.GetRotation()*Target[I].GetRotation()).GetNormalized());
        }
        const FTransform Hidden(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector);
        for(const int32 I:RightBones)Pose[I]=Hidden;
    }
    // Consumable lower/use/raise overlays still write after the carry, as on the spellbook rig.
    Super::FinalizeBoneTransform();
}

UOffhandKukriComponent::UOffhandKukriComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostPhysics;}

bool UOffhandKukriComponent::IsOffhandKukri(const FColdSteelItem& Item) {return Item.Definition==TEXT("ue_kukri");}

bool UOffhandKukriComponent::IsEquippedOn(const AActor* Owner)
{
    const auto* Kukri=Owner?Owner->FindComponentByClass<UOffhandKukriComponent>():nullptr;
    return Kukri&&Kukri->IsEquipped();
}

bool UOffhandKukriComponent::PresentsLeftHand(const AActor* Owner)
{
    const auto* Kukri=Owner?Owner->FindComponentByClass<UOffhandKukriComponent>():nullptr;
    return Kukri&&Kukri->OwnsLeftHand();
}

void UOffhandKukriComponent::BeginPlay()
{
    Super::BeginPlay();auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer){SetComponentTickEnabled(false);return;}
    Camera=Pawn->FindComponentByClass<UCameraComponent>();if(!Camera.IsValid()){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(Pawn);AddTickPrerequisiteComponent(Pawn->GetCharacterMovement());
    // Read the pistol hand after its animation, ADS, recoil and framing for this frame.
    if(Pawn->AKMViewmodel)AddTickPrerequisiteComponent(Pawn->AKMViewmodel);
    if(auto* Outfit=Pawn->FindComponentByClass<UFPSModularOutfitComponent>())Outfit->AddTickPrerequisiteComponent(this);
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->AddTickPrerequisiteComponent(this);
    if(auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>())Potion->AddTickPrerequisiteComponent(this);
    Arms=NewObject<UOffhandKukriArmsMeshComponent>(Pawn,TEXT("OffhandKukriV9LeftArm"));
    Pawn->AddInstanceComponent(Arms);Arms->SetupAttachment(Camera.Get());
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCanEverAffectNavigation(false);
    Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->bReceivesDecals=false;
    Arms->SetVisibility(false);Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->SetBoundsScale(2.f);
    Blade=NewObject<UStaticMeshComponent>(Pawn,TEXT("OffhandKukriBlade"));
    Pawn->AddInstanceComponent(Blade);Blade->SetupAttachment(Camera.Get());
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);Blade->SetCanEverAffectNavigation(false);
    Blade->SetOnlyOwnerSee(true);Blade->SetCastShadow(false);Blade->bReceivesDecals=false;
    Blade->SetVisibility(false);Blade->RegisterComponent();
    if(Pawn->GetGameInstance())Model=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model.IsValid())EquipmentChanged=Model->OnChanged.AddUObject(this,&UOffhandKukriComponent::RefreshEquipment);
    RefreshEquipment();
}

void UOffhandKukriComponent::RefreshEquipment()
{
    bool Active=false;bEquipmentResolved=false;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Model.IsValid()&&Pawn&&Pawn->IsLocallyControlled())
    {
        // The inventory always accepts the kukri in the off-hand slot; it only
        // presents beside a dual-capable pistol of the same weapon set.
        const auto State=Model->Snapshot();
        const auto* Item=Model->Equipped(State.ActiveWeaponSlot==6?8:11);
        const auto* Primary=Model->Equipped(State.ActiveWeaponSlot);
        Active=Item&&IsOffhandKukri(*Item)&&Primary&&ColdSteelInventory::IsDualPistol(*Primary)&&!Model->ActiveProductionTool();
        bEquipmentResolved=true;
    }
    if(Active==bEquipped)return;
    if(!Active&&bQuickCombat)CancelQuickCombat();
    if(!Active&&bUppercut)CancelUppercut();
    bEquipped=Active;RightWeight=AimWeight=0.f;bPair=bHold=false;
    if(!Arms||!Blade)return;
    if(!Active)
    {
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        if(Load){Load->CancelHandle();Load.Reset();}UpdateVisibility();return;
    }
    // Gloves and sleeves follow this arm exactly like the spellbook arm.
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    if(ArmsPath.ResolveObject()&&KukriPath.ResolveObject())ApplyAssets();
    else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{ArmsPath,KukriPath},
        FStreamableDelegate::CreateUObject(this,&UOffhandKukriComponent::ApplyAssets));
}

void UOffhandKukriComponent::ApplyAssets()
{
    if(!bEquipped||!Arms||!Blade)return;
    auto* Skin=Cast<USkeletalMesh>(ArmsPath.ResolveObject());auto* Mesh=Cast<UStaticMesh>(KukriPath.ResolveObject());
    if(!Skin||!Mesh)return;
    Arms->SetSkeletalMesh(Skin);Blade->SetStaticMesh(Mesh);
    if(const auto* Render=Skin->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString N=Skin->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            const bool HandSection=!N.Contains(TEXT("handguard"))&&(N.Contains(TEXT("skin"))||N.Contains(TEXT("manny"))||
                N.Contains(TEXT("bare"))||N.Contains(TEXT("glove"))||N.Contains(TEXT("sleeve"))||N==TEXT("hand")||N==TEXT("hands")||N.EndsWith(TEXT("_hands")));
            Arms->ShowMaterialSection(M,S,HandSection,L);
        }
    Arms->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    UpdateVisibility();
}

bool UOffhandKukriComponent::OwnsLeftHand() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!bEquipped||!Pawn||!Pawn->IsLocallyControlled()||!Arms||!Arms->GetSkeletalMeshAsset()||!Blade||!Blade->GetStaticMesh())return false;
    if(!Pawn->HasInventoryWeapon()||!Pawn->IsPistolWeapon()||Pawn->HasOffhandPistol())return false;
    // The pistol draw keeps the knife hand: it rises into the hold with the gun (draw entry).
    const bool Drawing=Pawn->GetWeaponState()==EAKMWeaponState::Equipping;
    if(!Cast<APlayerController>(Pawn->GetController())||Pawn->IsTraversing()||(Pawn->IsSwitchingWeapon()&&!Drawing))return false;
    // The shared off-hand reload contract: lower, reload with the native support arm, raise.
    if(Pawn->GetOffhandReloadPhase()==EOffhandReloadPhase::Reload||Pawn->IsOffhandReloadArmExiting())return false;
    // Reload, inspection and the pistol bash need the native support arm;
    // the equipment identity stays unchanged while the presentation yields.
    if((Pawn->IsReloading()&&Pawn->GetOffhandReloadPhase()!=EOffhandReloadPhase::Raise)||
        Pawn->GetWeaponState()==EAKMWeaponState::Inspecting||Pawn->GetWeaponState()==EAKMWeaponState::QuickCombat)return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    return true;
}

void UOffhandKukriComponent::UpdateVisibility()
{
    if(!Arms||!Blade)return;const bool Show=OwnsLeftHand();
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const bool ShowBlade=Show&&(!Potion||!Potion->IsOffhandWeaponHidden())&&!Cast<AFPSGAMECharacter>(GetOwner())->IsDoorPushActive();
    if(Arms->IsVisible()!=Show)Arms->SetVisibility(Show);
    if(Blade->IsVisible()!=ShowBlade)Blade->SetVisibility(ShowBlade);
}

void UOffhandKukriComponent::AdvanceActionBeforeCamera(float Delta)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(bQuickCombat)
    {
        if(!Pawn||Pawn->IsDodging()||Pawn->IsTraversing()||Pawn->IsSwitchingWeapon()||
            Pawn->GetWeaponState()!=EAKMWeaponState::Idle)CancelQuickCombat();
        else AdvanceQuickCombat(Delta);
    }
    if(bUppercut)
    {
        if(!Pawn||Pawn->IsDodging()||Pawn->IsTraversing()||Pawn->IsSwitchingWeapon()||
            Pawn->GetWeaponState()!=EAKMWeaponState::Idle)CancelUppercut();
        else AdvanceUppercut(Delta);
    }
    if(bUpperRiftActive)TickUpperRift(Delta);
    const auto* Gun=Pawn?Pawn->AKMViewmodel.Get():nullptr;
    const auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    const bool Drawing=Pawn&&Pawn->GetWeaponState()==EAKMWeaponState::Equipping;
    bPair=bEquipped&&Arms&&Arms->GetSkeletalMeshAsset()&&Pawn&&Pawn->IsLocallyControlled()&&Pawn->HasInventoryWeapon()&&
        Pawn->IsPistolWeapon()&&!Pawn->HasOffhandPistol()&&(!Pawn->IsSwitchingWeapon()||Drawing)&&!Pawn->IsTraversing()&&
        Gun&&Gun->GetSkeletalMeshAsset()&&!(Body&&Body->IsThirdPersonViewEnabled());
    if(bEquipped&&Pawn&&Pawn->GetOffhandReloadPhase()==EOffhandReloadPhase::Reload&&GetWorld())
    {if(NativeReloadEnteredAt<0.)NativeReloadEnteredAt=GetWorld()->GetTimeSeconds();}
    else NativeReloadEnteredAt=-1.;
    // The draw entry starts each time the knife hand takes the left hand over outside the reload's own raise.
    const bool Presenting=bPair&&OwnsLeftHand();
    if(Presenting&&!bWasPresenting&&!Pawn->IsOffhandReloadActive())EntryAge=0.f;
    bWasPresenting=Presenting;
    if(EntryAge>=0.f){EntryAge+=Delta;if(EntryAge>=EntryDelaySeconds+EntryRiseSeconds)EntryAge=-1.f;}
    if(!bPair){RightWeight=AimWeight=0.f;bHold=false;EntryAge=-1.f;return;}
    const auto Phase=Pawn->GetOffhandReloadPhase();
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    bHold=Phase==EOffhandReloadPhase::Lower||Phase==EOffhandReloadPhase::Reload||
        (Potion&&Potion->IsStowingOffhand()&&!Potion->IsOffhandWeaponHidden())||
        (Pawn->GetWeaponState()!=EAKMWeaponState::Idle&&Phase!=EOffhandReloadPhase::Raise&&!Drawing);
    const bool Ready=Pawn->GetWeaponState()==EAKMWeaponState::Idle&&!Pawn->IsSprinting()&&
        !Pawn->IsOffhandReloadActive()&&!(Potion&&Potion->IsActive())&&!Pawn->IsDoorPushActive();
    namespace K=OffhandKukriPose;
    // One clock before the viewmodel and both mesh evaluations; actions fade the
    // framing back to the native pistol anchor and keep their own hands.
    RightWeight=FMath::FInterpConstantTo(RightWeight,Ready?1.f:0.f,Delta,1.f/K::ContactReturnSeconds);
    // The gun centres and cants together with the knife hand instead of in a second move: during the draw it
    // follows the entry, around a reload it unwinds as the knife drops and returns as it rises.
    if(Drawing)RightWeight=Presenting?1.f-EntryLowerWeight():0.f;   // arm assets still streaming: native draw
    else if(Pawn->IsOffhandReloadActive())RightWeight=1.f-Pawn->GetOffhandReloadLowerWeight();
    if(bHold)return;
    const bool Aim=Ready&&Pawn->IsAiming();
    AimWeight=FMath::FInterpConstantTo(AimWeight,Aim?1.f:0.f,Delta,1.f/(Aim?K::AimInSeconds:K::AimOutSeconds));
    // The flourish and the uppercut hold the authored gun framing for their whole clock.
    if(bQuickCombat||bUppercut){RightWeight=1.f;AimWeight=0.f;}
}

void UOffhandKukriComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Pawn->IsLocallyControlled())return;
    if(!bEquipmentResolved)RefreshEquipment();
    if(!bEquipped)return;
    UpdateVisibility();if(!Arms||!Arms->IsVisible())return;
    const auto* Gun=Pawn->AKMViewmodel.Get();
    if(Gun&&Gun->GetSkeletalMeshAsset()&&Camera.IsValid())
        if(const int32 Index=Gun->GetBoneIndex(TEXT("hand_r"));Index!=INDEX_NONE)
            Arms->RightHandInCamera=Camera->GetComponentTransform().InverseTransformPosition(Gun->GetBoneTransform(Index).GetLocation());
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const float Stow=FMath::Max(Pawn->GetOffhandReloadLowerWeight(),Potion&&Potion->IsStowingOffhand()?Potion->OffhandLowerWeight():0.f);
    Arms->LowerWeight=FMath::Max(Stow,EntryLowerWeight());Arms->AimWeight=AimWeight;
    Arms->StrikeTime=bQuickCombat?QuickElapsed:-1.f;
    Arms->UppercutTime=bUppercut?UppercutElapsed:-1.f;
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    // Same-frame rigid contact; the native hand carries a scale-100 import.
    FTransform HandFrame=Arms->GetSocketTransform(TEXT("hand_l"));HandFrame.SetScale3D(FVector::OneVector);
    const bool ForwardGrip=bUppercut&&UppercutElapsed>=OffhandKukriUpper::DigitsAt&&UppercutElapsed<=OffhandKukriUpper::DigitsEnd;
    Blade->SetWorldTransform((ForwardGrip?OffhandKukriUpper::KukriInHand:OffhandKukriPose::KukriInHand)*HandFrame);
    UpdateVisibility();
}

void UOffhandKukriComponent::CacheGun(const USkeletalMeshComponent& Gun)
{
    GunMesh=Gun.GetSkeletalMeshAsset();
    const auto& Ref=GunMesh->GetRefSkeleton();
    RightClavicle=Ref.FindBoneIndex(TEXT("clavicle_r"));RightUpper=Ref.FindBoneIndex(TEXT("upperarm_r"));
    RightLower=Ref.FindBoneIndex(TEXT("lowerarm_r"));RightHand=Ref.FindBoneIndex(TEXT("hand_r"));
    RightTwist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_r"));RightTwist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_r"));
    RightReference=Ref.GetRefBonePose();RightBones.Reset();GunLeftBones.Reset();
    const int32 LeftClavicle=Ref.FindBoneIndex(TEXT("clavicle_l"));
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        if(const int32 P=Ref.GetParentIndex(I);P>=0)RightReference[I]*=RightReference[P];
        if(RightClavicle>=0&&(I==RightClavicle||Ref.BoneIsChildOf(I,RightClavicle)))RightBones.Add(I);
        if(LeftClavicle>=0&&(I==LeftClavicle||Ref.BoneIsChildOf(I,LeftClavicle)))GunLeftBones.Add(I);
    }
    RightSource=RightReference;RightTarget=RightReference;
}

float UOffhandKukriComponent::EntryLowerWeight() const
{
    if(EntryAge<0.f)return 0.f;
    // Ease-out rise: quick off the bottom of the frame, settling into the hold.
    const float U=FMath::Clamp((EntryAge-EntryDelaySeconds)/EntryRiseSeconds,0.f,1.f);
    return FMath::Cube(1.f-U);
}

void UOffhandKukriComponent::ApplyNativeReloadEntry(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(NativeReloadEnteredAt<0.||!Pawn||Pawn->AKMViewmodel.Get()!=&Gun||!Pawn->FirstPersonCamera||!GetWorld()||!Gun.GetSkeletalMeshAsset())return;
    const float Fade=1.f-Smooth(float(GetWorld()->GetTimeSeconds()-NativeReloadEnteredAt)/NativeReloadEntrySeconds);
    if(Fade<=0.f)return;
    if(GunMesh.Get()!=Gun.GetSkeletalMeshAsset())CacheGun(Gun);
    // The clip's support hand dives for the magazine within ~0.2 s anyway; it now arrives from where the knife
    // hand left instead of appearing on the grip.
    const FTransform CameraTransform=Pawn->FirstPersonCamera->GetComponentTransform();
    const FTransform ToCamera=Gun.GetComponentTransform().GetRelativeTransform(CameraTransform);
    const FTransform ToMesh=CameraTransform.GetRelativeTransform(Gun.GetComponentTransform());
    for(const int32 I:GunLeftBones)
        if(Pose.IsValidIndex(I)){FTransform Bone=Pose[I]*ToCamera;Bone.AddToTranslation(NativeReloadEntryOffset*Fade);Pose[I]=Bone*ToMesh;}
}

void UOffhandKukriComponent::ApplyPistolRightArm(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose)
{
    ApplyNativeReloadEntry(Gun,Pose);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const float Weight=PistolFramingWeight();
    if(!bPair||Weight<=UE_SMALL_NUMBER||!Pawn||Pawn->AKMViewmodel.Get()!=&Gun||!Pawn->FirstPersonCamera||!Gun.GetSkeletalMeshAsset())return;
    if(GunMesh.Get()!=Gun.GetSkeletalMeshAsset())CacheGun(Gun);
    if(RightClavicle<0||RightUpper<0||RightLower<0||RightHand<0||Pose.Num()!=RightReference.Num())return;
    const FTransform ToCamera=Gun.GetComponentTransform().GetRelativeTransform(Pawn->FirstPersonCamera->GetComponentTransform());
    const FTransform ToMesh=Pawn->FirstPersonCamera->GetComponentTransform().GetRelativeTransform(Gun.GetComponentTransform());
    for(int32 I=0;I<Pose.Num();++I)RightSource[I]=Pose[I]*ToCamera;
    namespace K=OffhandKukriPose;
    const float A=K::Ease(AimWeight);
    const FVector Shoulder=FMath::Lerp(RightSource[RightUpper].GetLocation(),FMath::Lerp(K::Hip.RightShoulder,K::Aim.RightShoulder,A),Weight);
    const FVector Pole=FMath::Lerp(RightSource[RightLower].GetLocation(),FMath::Lerp(K::Hip.RightPole,K::Aim.RightPole,A),Weight);
    const auto& Ref=Gun.GetSkeletalMeshAsset()->GetRefSkeleton();
    const SpellbookPistolArm::FJoints J{RightClavicle,RightUpper,RightLower,RightHand,RightTwist01,RightTwist02};
    SpellbookPistolArm::Solve(Ref,RightReference,RightSource,RightBones,J,Shoulder,RightSource[RightHand].GetLocation(),Pole,
        RightSource[RightHand].GetRotation(),0.f,Weight,RightTarget);
    for(const int32 I:RightBones)
    {
        // The pistol grip, fingers and gun stay exactly as animated; only the
        // shoulder, elbow and arm helpers follow the crossed stance.
        if(I==RightHand||Ref.BoneIsChildOf(I,RightHand))continue;
        Pose[I]=RightTarget[I]*ToMesh;
    }
}

void UOffhandKukriComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelQuickCombat();CancelUppercut();
    if(Model.IsValid()&&EquipmentChanged.IsValid())Model->OnChanged.Remove(EquipmentChanged);
    if(Load)Load->CancelHandle();Super::EndPlay(Reason);
}
