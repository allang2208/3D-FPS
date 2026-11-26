#include "OffhandKukriComponent.h"
#include "OffhandKukriAuthoredPose.h"
#include "OffhandBladeDraw.h"
#include "PistolKukriDrawWrist.h"
#include "KukriDrawRhythm.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "Sound/SoundBase.h"
#include "OffhandKukriAuthoredStrike.h"
#include "OffhandKukriAuthoredUppercut.h"
#include "OffhandShadowStepMotion.h"
#include "OffhandAxeQuickMotion.h"
#include "OffhandQuickClearance.h"
#include "PistolHatchetCarry.h"
#include "PistolHatchetDrawMotion.h"
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
// The reversed kukri tips down as the fist drops below the frame.
const FQuat LowerHandTurn(FVector::RightVector,FMath::DegreesToRadians(55.f));
// Draw entry: the knife hand rises into the hold while the pistol is drawn (or whenever the pair re-presents).
constexpr float EntryDelaySeconds=.06f,EntryRiseSeconds=.42f;
// The native support hand starts the reload clip on the grip: bring it in from below instead of popping it there.
const FVector NativeReloadEntryOffset(-7.f,-3.f,-42.f);
constexpr float NativeReloadEntrySeconds=.28f;
FQuat KukriDrawWristRotation(float Time)
{
    const auto& Keys=PistolKukriDraw::WristRotation;
    const int32 Last=UE_ARRAY_COUNT(Keys)-1;
    const float Frame=FMath::Clamp(Time*60.f,0.f,float(Last));
    const int32 Start=FMath::Min(int32(Frame),Last-1);
    const auto Key=[&](int32 Index){const auto& Q=Keys[Index];return FQuat(Q[0],Q[1],Q[2],Q[3]);};
    return FQuat::Slerp(Key(Start),Key(Start+1),Frame-Start).GetNormalized();
}

float Smooth(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}

FVector PistolLeftWristOffset(float A)
{
    namespace K=OffhandKukriPose;
    FVector WristOffset=FMath::Lerp(K::Hip.LeftWristFromRightHand,K::Aim.LeftWristFromRightHand,A);
    WristOffset.Z-=K::TransferDipCm*FMath::Sin(PI*A);
    return WristOffset;
}
}

void UPistolHatchetArmsMeshComponent::ConfigureCarry()
{
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    CarryHandInCamera=PistolHatchetCarry::PalmInView(KukriOffhandDraw::Grip().GetRotation());
    Clavicle=Ref.FindBoneIndex(TEXT("clavicle_l"));Upper=Ref.FindBoneIndex(TEXT("upperarm_l"));
    Lower=Ref.FindBoneIndex(TEXT("lowerarm_l"));Hand=Ref.FindBoneIndex(TEXT("hand_l"));
    Twist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_l"));Twist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_l"));
    CarryBones.Reset();
    if(Hand>=0&&Clavicle>=0&&Upper>=0&&Lower>=0)
        for(int32 I=Clavicle;I<Ref.GetNum();++I)
            if(I==Clavicle||Ref.BoneIsChildOf(I,Clavicle))CarryBones.Add(I);
}

void UPistolHatchetArmsMeshComponent::FinalizeBoneTransform()
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto* Mesh=GetSkeletalMeshAsset();
    if(bCrossedCarry&&Mesh&&!CarryBones.IsEmpty()&&Pose.Num()==Mesh->GetRefSkeleton().GetNum())
    {
        namespace K=OffhandKukriPose;
        const float A=K::Ease(AimWeight);
        // Keep the accepted crossed-arm shoulder and elbow. A small wrist dip
        // leaves clearance for the newly rotated axe fist beneath the gun hand.
        const FVector Wrist=CarryAnchorInCamera+PistolLeftWristOffset(A)+FVector(0.,0.,-FMath::Lerp(5.f,2.f,A));
        const FVector Shoulder=FMath::Lerp(K::Hip.LeftShoulder,K::Aim.LeftShoulder,A);
        const FVector Pole=FMath::Lerp(K::Hip.LeftPole,K::Aim.LeftPole,A);
        const FQuat ToMesh=GetRelativeRotation().Quaternion().Inverse();
        const FVector TargetWrist=FMath::Lerp(Pose[Hand].GetLocation(),ToMesh.RotateVector(Wrist),CarryWeight);
        const FVector TargetShoulder=FMath::Lerp(Pose[Upper].GetLocation(),ToMesh.RotateVector(Shoulder),CarryWeight);
        const FVector TargetPole=FMath::Lerp(Pose[Lower].GetLocation(),ToMesh.RotateVector(Pole),CarryWeight);
        const FQuat TargetHand=FQuat::Slerp(Pose[Hand].GetRotation(),ToMesh*CarryHandInCamera,CarryWeight).GetNormalized();
        const SpellbookPistolArm::FJoints J{Clavicle,Upper,Lower,Hand,Twist01,Twist02};
        // Keep the fitted fist closed as the elbow follows the wrist into the crossed hold.
        SpellbookPistolArm::Solve(Mesh->GetRefSkeleton(),Pose,Pose,CarryBones,J,
            TargetShoulder,TargetWrist,TargetPole,TargetHand,0.f,CarryWeight,CarryPose);
        PistolHatchetCarry::FitFingers(Mesh->GetRefSkeleton(),CarryPose,CarryWeight);
        for(const int32 I:CarryBones)Pose[I]=CarryPose[I];
    }
    Super::FinalizeBoneTransform();
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
    // Mirrored ShadowStepSlash: forward grip digits baked from ShadowStep Stage 1.
    SourceShadowStep=Reference;
    TMap<FName,FQuat> ShadowDigits;
    for(const auto& D:OffhandShadowStepMotion::Digits)ShadowDigits.Add(FName(D.Name),D.LocalRotation);
    for(const int32 I:LeftBones)
    {
        const int32 P=Ref.GetParentIndex(I);
        const FQuat* Rotation=ShadowDigits.Find(Ref.GetBoneName(I));
        if(P<0||!Rotation)continue;
        FTransform Local=Reference[I].GetRelativeTransform(Reference[P]);
        Local.SetRotation(Rotation->GetNormalized());
        SourceShadowStep[I]=Local*SourceShadowStep[P];
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
        const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
        FVector Offset,Shoulder,Pole;FQuat HandRotation;
        bool ForwardGrip=false;
        bool UseShadowDigits=false;
        float ClavicleShare=0.f;
        if(StrikeTime>=0.f)
        {
            // The quick-melee flourish: its key table replaces the stance lerp outright.
            FTransform Framing;
            OffhandKukriStrike::SamplePose(StrikeTime,Offset,HandRotation,Shoulder,Pole,Framing);
            ClavicleShare=OffhandKukriStrike::SampleClavicle(StrikeTime);
        }
        else if(ShadowStepTime>=0.f)
        {
            FTransform Framing;
            OffhandShadowStepMotion::SamplePose(bShadowStepStage2,ShadowStepTime,Offset,HandRotation,Shoulder,Pole,Framing);
            ForwardGrip=OffhandShadowStepMotion::UsesForwardGrip(bShadowStepStage2,ShadowStepTime);
            UseShadowDigits=ForwardGrip;
            ClavicleShare=OffhandShadowStepMotion::SampleClavicle(bShadowStepStage2,ShadowStepTime);
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
            namespace K=OffhandKukriPose;
            const float A=K::Ease(AimWeight);
            Offset=PistolLeftWristOffset(A);
            Shoulder=FMath::Lerp(K::Hip.LeftShoulder,K::Aim.LeftShoulder,A);
            Pole=FMath::Lerp(K::Hip.LeftPole,K::Aim.LeftPole,A);
            HandRotation=FQuat::Slerp(K::Hip.LeftHand,K::Aim.LeftHand,A).GetNormalized();
            if(DrawTime>=0.f)
            {
                Offset+=OffhandBladeDraw::WristOffset(false,DrawTime);
                HandRotation=(KukriDrawWristRotation(DrawTime)*HandRotation).GetNormalized();
            }
            if(LowerWeight>0.f)
            {
                const float S=FMath::Clamp(LowerWeight,0.f,1.f);
                Offset+=PistolOffhandRaise::WristOffset(S);
                HandRotation=(FQuat::Slerp(FQuat::Identity,LowerHandTurn,S)*HandRotation).GetNormalized();
            }
        }
        const SpellbookPistolArm::FJoints J{Clavicle,Upper,Lower,Hand,Twist01,Twist02};
        SpellbookPistolArm::Solve(Ref,Reference,UseShadowDigits?SourceShadowStep:(ForwardGrip?SourceUpper:Source),LeftBones,J,Shoulder,
            RightHandInCamera+Offset,Pole,HandRotation,0.f,1.f,Target);
        if(DrawTime>=0.f&&StrikeTime<0.f&&UppercutTime<0.f&&ShadowStepTime<0.f)
        {
            const float Open=OffhandBladeDraw::OpenHand(false,DrawTime);
            for(const int32 I:LeftBones)if(Ref.BoneIsChildOf(I,Hand))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                FTransform Local=Source[I].GetRelativeTransform(Source[Parent]);
                Local.SetRotation(FQuat::Slerp(Local.GetRotation(),Ref.GetRefBonePose()[I].GetRotation(),Open).GetNormalized());
                Target[I]=Local*Target[Parent];
            }
        }
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
            Pose[I].SetLocation(ToMesh.TransformPosition(Target[I].GetLocation()+PresentationOffset));
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

bool UOffhandKukriComponent::IsOffhandKukri(const FColdSteelItem& Item) {return ColdSteelInventory::UsesKukriMoveset(Item);}

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

void UOffhandKukriComponent::OnPistolEquipStarted()
{
    // The firearm and the offhand listen to the same inventory change in either order.
    RefreshEquipment();
    if(!bEquipped)return;
    PendingDraw=EDrawEntry::Raise;
    EntryAge=DrawTime=-1.f;
}

void UOffhandKukriComponent::RefreshEquipment()
{
    bool Active=false;bEquipmentResolved=false;const FColdSteelItem* Knife=nullptr;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Model.IsValid()&&Pawn&&Pawn->IsLocallyControlled())
    {
        // The inventory always accepts the kukri in the off-hand slot; it only
        // presents beside a dual-capable pistol of the same weapon set.
        const auto State=Model->Snapshot();
        const auto* Item=Model->Equipped(State.ActiveWeaponSlot==6?8:11);
        const auto* Primary=Model->Equipped(State.ActiveWeaponSlot);
        Active=Item&&IsOffhandKukri(*Item)&&Primary&&ColdSteelInventory::IsDualPistol(*Primary)&&!Model->ActiveProductionTool();
        if(Active)Knife=Item;
        bEquipmentResolved=true;
    }
    const FString Next=Knife?Knife->InstanceId:FString();
    if(Active==bEquipped&&BladeInstance==Next){if(Active&&bAssetsReady&&Blade)Modules.Refresh(Blade,Knife);return;}
    if(Load){Load->CancelHandle();Load.Reset();}
    BladeInstance=Next;bAssetsReady=false;DrawTime=EntryAge=-1.f;
    bDrawHatchet=Knife&&ColdSteelInventory::Text(*Knife,TEXT("weaponType"))==TEXT("hatchet");
    PendingDraw=!Active?EDrawEntry::None:(bDrawHatchet?EDrawEntry::Raise:EDrawEntry::KukriToss);
    if(AxeArms)
    {
        AxeArms->SetVisibility(false);
        AxeArms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
    }
    AxeChop=nullptr;AxeIdle=nullptr;AxeIdleAge=0.f;
    if(bQuickCombat)CancelQuickCombat();
    if(bUppercut)CancelUppercut();
    if(bShadowStep)CancelShadowStep();
    bEquipped=Active;RightWeight=AimWeight=0.f;bPair=bHold=false;
    if(!Arms||!Blade)return;
    if(!Active)
    {
        Modules.Clear(Blade);
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        if(Load){Load->CancelHandle();Load.Reset();}UpdateVisibility();return;
    }
    UpdateVisibility();
    // Gloves and sleeves follow this arm exactly like the spellbook arm.
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    TArray<FSoftObjectPath> Paths{ArmsPath,KukriPath};
    if(bDrawHatchet)
    {
        Paths.Add(FSoftObjectPath(KukriRhythm::ArmsMesh));
        Paths.Add(FSoftObjectPath(HatchetPairRhythm::Attack3KHClip));
        Paths.Add(FSoftObjectPath(OffhandAxeQuickMotion::IdlePath));
        Paths.Add(FSoftObjectPath(KukriRhythm::RiftMaterial));
    }
    else
    {
        Paths.Add(FSoftObjectPath(KukriDrawRhythm::TossSound));
        Paths.Add(FSoftObjectPath(KukriDrawRhythm::CatchSound));
    }
    if(!Paths.ContainsByPredicate([](const FSoftObjectPath& Path){return !Path.ResolveObject();}))ApplyAssets();
    else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateUObject(this,&UOffhandKukriComponent::ApplyAssets));
}

void UOffhandKukriComponent::ApplyAssets()
{
    if(!bEquipped||!Arms||!Blade)return;
    auto* Skin=Cast<USkeletalMesh>(ArmsPath.ResolveObject());auto* Mesh=Cast<UStaticMesh>(KukriPath.ResolveObject());
    if(!Skin||!Mesh)return;
    Arms->SetSkeletalMesh(Skin);Blade->SetStaticMesh(Mesh);
    DrawTossSound=bDrawHatchet?nullptr:Cast<USoundBase>(FSoftObjectPath(KukriDrawRhythm::TossSound).ResolveObject());
    DrawCatchSound=bDrawHatchet?nullptr:Cast<USoundBase>(FSoftObjectPath(KukriDrawRhythm::CatchSound).ResolveObject());
    Modules.Clear(Blade);
    if(Model.IsValid())Modules.Refresh(Blade,Model->Equipped(Model->Snapshot().ActiveWeaponSlot==6?8:11));
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
    if(bDrawHatchet)InstallAxeArms();
    bAssetsReady=true;
    UpdateVisibility();
}

void UOffhandKukriComponent::InstallAxeArms()
{
    auto* Skin=Cast<USkeletalMesh>(FSoftObjectPath(KukriRhythm::ArmsMesh).ResolveObject());
    AxeChop=Cast<UAnimSequence>(FSoftObjectPath(HatchetPairRhythm::Attack3KHClip).ResolveObject());
    AxeIdle=Cast<UAnimSequence>(FSoftObjectPath(OffhandAxeQuickMotion::IdlePath).ResolveObject());
    if(!Skin||!AxeIdle||!AxeChop)return;
    if(!AxeArms)
    {
        AxeArms=NewObject<UPistolHatchetArmsMeshComponent>(GetOwner(),TEXT("PistolOffhandHatchetArms"));
        GetOwner()->AddInstanceComponent(AxeArms);
        AxeArms->SetupAttachment(Camera.Get());
        AxeArms->SetRelativeRotation(FRotator(0,90,0));
        AxeArms->bLeftHandOnly=true;
        AxeArms->SetOnlyOwnerSee(true);AxeArms->SetCastShadow(false);
        AxeArms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        AxeArms->SetCanEverAffectNavigation(false);AxeArms->bReceivesDecals=false;
        AxeArms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        AxeArms->SetVisibility(false);AxeArms->RegisterComponent();
        AxeArms->SetComponentTickEnabled(false);
    }
    AxeArms->SetSkeletalMesh(Skin);
    AxeArms->ConfigureCarry();
    PrepareQuickRift();
    AxeArms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
}

bool UOffhandKukriComponent::UsesNativeAxe() const
{
    return bEquipped&&bDrawHatchet&&!bUppercut&&!bShadowStep&&AxeArms&&AxeIdle&&AxeChop;
}

USkeletalMeshComponent* UOffhandKukriComponent::ArmsMesh() const
{
    return UsesNativeAxe()?static_cast<USkeletalMeshComponent*>(AxeArms.Get()):Arms.Get();
}

FTransform UOffhandKukriComponent::SampleAxeBlade(float Time,bool Striking,float EntryLower)
{
    auto* Clip=Striking?AxeChop.Get():AxeIdle.Get();
    AxeArms->CarryWeight=Striking?OffhandAxeQuickMotion::Carry(Time):1.f;
    AxeArms->bCrossedCarry=AxeArms->CarryWeight>0.f;
    if(AxeArms->bCrossedCarry)
    {
        AxeArms->CarryAnchorInCamera=Arms->RightHandInCamera+PistolOffhandRaise::WristOffset(EntryLower);
        AxeArms->AimWeight=AimWeight;
    }
    const float ClipTime=Striking?Time*OffhandAxeQuickMotion::ClipRate:AxeIdleAge;
    OffhandAxeQuickMotion::Sample(*AxeArms,Clip,ClipTime);
    return OffhandAxeQuickMotion::BladeWorld(*AxeArms);
}

bool UOffhandKukriComponent::OwnsLeftHand() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!bEquipped||!bAssetsReady||!Pawn||!Pawn->IsLocallyControlled()||!Arms||!Arms->GetSkeletalMeshAsset()||!Blade||!Blade->GetStaticMesh())return false;
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
    if(!Arms||!Blade)return;const bool Show=OwnsLeftHand()&&PendingDraw==EDrawEntry::None;
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const bool ShowBlade=Show&&(!Potion||!Potion->IsOffhandWeaponHidden())&&!Cast<AFPSGAMECharacter>(GetOwner())->IsDoorPushActive();
    const bool Native=UsesNativeAxe();
    if(Arms->IsVisible()!=(Show&&!Native))Arms->SetVisibility(Show&&!Native);
    if(AxeArms&&AxeArms->IsVisible()!=(Show&&Native))AxeArms->SetVisibility(Show&&Native);
    if(Blade->IsVisible()!=ShowBlade)Blade->SetVisibility(ShowBlade,true);
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
    if(bShadowStep)
    {
        if(!Pawn||Pawn->IsDodging()||Pawn->IsTraversing()||Pawn->IsSwitchingWeapon()||
            (!bStaffShadowStep&&Pawn->GetWeaponState()!=EAKMWeaponState::Idle))CancelShadowStep();
        else AdvanceShadowStep(Delta);
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
    const auto* Potion=Pawn?Pawn->FindComponentByClass<UFPSPotionUseComponent>():nullptr;
    const bool CanDraw=Presenting&&!Pawn->IsOffhandReloadActive()&&!Pawn->IsDoorPushActive()&&
        !(Potion&&Potion->IsActive())&&!bQuickCombat&&!bUppercut&&!bShadowStep;
    if(EntryAge>=0.f){EntryAge+=Delta;if(EntryAge>=EntryDelaySeconds+EntryRiseSeconds)EntryAge=-1.f;}
    if(PendingDraw!=EDrawEntry::None&&CanDraw)
    {
        // Only a kukri fitted to an already presented pistol uses the toss clock.
        const bool Toss=PendingDraw==EDrawEntry::KukriToss&&!Drawing;
        EntryAge=Toss?-1.f:0.f;
        DrawTime=Toss?0.f:-1.f;
        if(bDrawHatchet&&AxeArms)AxeArms->ClearEntry();
        PendingDraw=EDrawEntry::None;
    }
    else if(DrawTime>=0.f)
    {
        if(CanDraw)
        {
            const float Before=DrawTime;
            DrawTime+=Delta*LightningHaste::ActionSpeed(Pawn);
            OffhandBladeDraw::PlayCues(this,false,Before,DrawTime,DrawTossSound,DrawCatchSound);
            if(DrawTime>=OffhandBladeDraw::Length(false))DrawTime=-1.f;
        }
        else DrawTime=-1.f;
    }
    else if(Presenting&&!bWasPresenting&&!Pawn->IsOffhandReloadActive())EntryAge=0.f;
    bWasPresenting=Presenting;
    if(!bPair){RightWeight=AimWeight=0.f;bHold=false;EntryAge=-1.f;return;}
    const auto Phase=Pawn->GetOffhandReloadPhase();
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
    if(Drawing||(Ready&&EntryAge>=0.f))
        RightWeight=Presenting?1.f-EntryLowerWeight():0.f;
    else if(Pawn->IsOffhandReloadActive())RightWeight=1.f-Pawn->GetOffhandReloadLowerWeight();
    if(bHold)return;
    const bool Aim=Ready&&Pawn->IsAiming();
    AimWeight=FMath::FInterpConstantTo(AimWeight,Aim?1.f:0.f,Delta,1.f/(Aim?K::AimInSeconds:K::AimOutSeconds));
    // The flourish, uppercut and shadow step hold the authored gun framing for their whole clock.
    if(bQuickCombat||bUppercut||bShadowStep){RightWeight=1.f;AimWeight=0.f;}
}

void UOffhandKukriComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Pawn->IsLocallyControlled())return;
    // Freeze the trail after this frame's camera update, including staff pairs
    // whose presentation is owned by their separate off-hand component.
    if(bQuickCombat&&bHatchetQuickCombat&&!bUpperRiftStarted&&QuickElapsed>=OffhandAxeQuickMotion::RiftStart)
    {bUpperRiftStarted=true;StartQuickRift();}
    if(!bEquipmentResolved)RefreshEquipment();
    if(!bEquipped)return;
    UpdateVisibility();if(!ArmsMesh()||!ArmsMesh()->IsVisible())return;
    const auto* Gun=Pawn->AKMViewmodel.Get();
    if(Gun&&Gun->GetSkeletalMeshAsset()&&Camera.IsValid())
        if(const int32 Index=Gun->GetBoneIndex(TEXT("hand_r"));Index!=INDEX_NONE)
        {
            Arms->RightHandInCamera=Camera->GetComponentTransform().InverseTransformPosition(Gun->GetBoneTransform(Index).GetLocation());
            if(bQuickCombat&&!bStaffQuickCombat)
            {
                const FTransform Presented=OffhandQuickClearance::PistolFrame(OffhandKukriPose::HipFraming,
                    QuickElapsed/GetQuickCombatLength(),bHatchetQuickCombat);
                QuickNativePistolHand=Presented.InverseTransformPosition(Arms->RightHandInCamera);
                FTransform BladeReference=OffhandKukriPose::HipFraming;
                if(!bHatchetQuickCombat)
                {
                    FVector Wrist,Shoulder,Pole;FQuat Hand;
                    OffhandKukriStrike::SamplePose(QuickElapsed,Wrist,Hand,Shoulder,Pole,BladeReference);
                }
                // The left blade retains its authored lane while the right
                // gun uses a smaller independent arc. Axe carry stays at idle.
                Arms->RightHandInCamera=BladeReference.TransformPosition(QuickNativePistolHand);
            }
        }
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const float Stow=FMath::Max(Pawn->GetOffhandReloadLowerWeight(),Potion&&Potion->IsStowingOffhand()?Potion->OffhandLowerWeight():0.f);
    if(UsesNativeAxe())
    {
        const bool Striking=IsHatchetQuickCombat();
        // Reload and consumables lower the whole rig. During equip the shoulder
        // stays in place and the wrist covers the remainder of the below-frame arc.
        const float EntryLower=Striking?0.f:FMath::Max(0.f,EntryLowerWeight()-Stow);
        AxeArms->SetRelativeLocation(PistolOffhandRaise::LowerEnd*(Striking?0.f:Stow));
        if(!bQuickCombat||QuickHitStop<=0.f)AxeArms->AdvanceEntry(Delta*LightningHaste::ActionSpeed(Pawn));
        if(!Striking)AxeIdleAge=FMath::Fmod(AxeIdleAge+Delta,FMath::Max(.01f,AxeIdle->GetPlayLength()));
        Blade->SetWorldTransform(SampleAxeBlade(QuickElapsed,Striking,EntryLower));
        return;
    }
    Arms->LowerWeight=FMath::Max(Stow,EntryLowerWeight());Arms->AimWeight=AimWeight;
    Arms->DrawTime=DrawTime;
    Arms->StrikeTime=bQuickCombat?QuickElapsed:-1.f;
    Arms->UppercutTime=bUppercut?UppercutElapsed:-1.f;
    Arms->ShadowStepTime=bShadowStep?FMath::Clamp(ShadowStepElapsed,0.f,bShadowStepStage2?OffhandShadowStepMotion::Stage2Length:OffhandShadowStepMotion::Stage1Length):-1.f;
    Arms->bShadowStepStage2=bShadowStepStage2;
    Arms->PresentationOffset=bShadowStep?ShadowStepPressOffset():FVector::ZeroVector;
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    // Same-frame rigid contact; the native hand carries a scale-100 import.
    FTransform HandFrame=Arms->GetSocketTransform(TEXT("hand_l"));HandFrame.SetScale3D(FVector::OneVector);
    const bool ForwardShadow=bShadowStep&&OffhandShadowStepMotion::UsesForwardGrip(bShadowStepStage2,Arms->ShadowStepTime);
    const bool ForwardGrip=bUppercut&&UppercutElapsed>=OffhandKukriUpper::DigitsAt&&UppercutElapsed<=OffhandKukriUpper::DigitsEnd;
    const FTransform Grip=ForwardShadow?OffhandShadowStepMotion::KukriInHand:(ForwardGrip?OffhandKukriUpper::KukriInHand:OffhandKukriPose::KukriInHand);
    const FTransform Flight=DrawTime>=0.f&&!bQuickCombat&&!bUppercut&&!bShadowStep?OffhandBladeDraw::FlightDelta(false,DrawTime):FTransform::Identity;
    Blade->SetWorldTransform(Flight*Grip*HandFrame);
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
    FVector Shoulder=FMath::Lerp(RightSource[RightUpper].GetLocation(),FMath::Lerp(K::Hip.RightShoulder,K::Aim.RightShoulder,A),Weight);
    FVector Pole=FMath::Lerp(RightSource[RightLower].GetLocation(),FMath::Lerp(K::Hip.RightPole,K::Aim.RightPole,A),Weight);
    if(bQuickCombat&&!bStaffQuickCombat)
    {
        const auto Clearance=OffhandQuickClearance::Sample(QuickElapsed/GetQuickCombatLength(),bHatchetQuickCombat);
        const float Support=FMath::Clamp(float(Clearance.Offset.Y)/22.f,0.f,1.f);
        Shoulder+=Clearance.Offset*.12;
        Pole+=Clearance.Offset*.45+FVector(-1,1,-2)*Support;
    }
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
    Modules.Clear(Blade);
    CancelQuickCombat();CancelUppercut();CancelShadowStep();
    StopUpperRift();
    if(Model.IsValid()&&EquipmentChanged.IsValid())Model->OnChanged.Remove(EquipmentChanged);
    if(Load)Load->CancelHandle();Super::EndPlay(Reason);
}
