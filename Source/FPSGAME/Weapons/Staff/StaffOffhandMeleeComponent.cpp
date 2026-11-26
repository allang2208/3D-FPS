#include "StaffOffhandMeleeComponent.h"
#include "../WoodenTorchItem.h"
#include "StaffWeaponComponent.h"
#include "StaffCatalog.h"
#include "StaffOffhandQuickMotion.h"
#include "../Kukri/OffhandKukriComponent.h"
#include "../Kukri/KukriWeaponComponent.h"
#include "../Kukri/KukriArmsMeshComponent.h"
#include "../Kukri/KukriRhythm.h"
#include "../Kukri/HatchetPairRhythm.h"
#include "../Kukri/KukriDrawRhythm.h"
#include "../Kukri/KukriOffhandDraw.h"
#include "../Kukri/OffhandBladeDraw.h"
#include "../ModularSwordVisual.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Characters/FPSModularOutfitComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
    const FSoftObjectPath IdlePath(TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle.A_Kukri_DualIdle"));
    const FSoftObjectPath EquipPath(TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualEquip.A_Kukri_DualEquip"));
    const FSoftObjectPath WhirlwindPath(TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_Whirlwind.A_Kukri_Whirlwind"));
    const FSoftObjectPath StrikeArmsPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
    // Camera centimetres. Keep both arms/contacts rigid within their existing authored rigs.
    const FVector LeftFraming(2.f,-4.f,-1.f),RightFraming(2.f,4.f,-1.f);
    constexpr float PairBlendSeconds=.18f;
}

UStaffOffhandMeleeComponent::UStaffOffhandMeleeComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
}

bool UStaffOffhandMeleeComponent::IsEquippedOn(const AActor* Owner)
{
    const auto* Pair=Owner?Owner->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    return Pair&&Pair->IsEquipped();
}
bool UStaffOffhandMeleeComponent::PresentsLeftHand(const AActor* Owner)
{
    const auto* Pair=Owner?Owner->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    return Pair&&Pair->OwnsLeftHand();
}
USkeletalMeshComponent* UStaffOffhandMeleeComponent::ArmsMesh() const {return UsesStrikeRig()?static_cast<USkeletalMeshComponent*>(StrikeArms):Arms.Get();}

void UStaffOffhandMeleeComponent::BeginPlay()
{
    Super::BeginPlay();
    InitializeLocalPresentation();
}

void UStaffOffhandMeleeComponent::InitializeLocalPresentation()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Arms||!Pawn||!Pawn->IsLocallyControlled())return;
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    if(!Camera.IsValid())return;
    AddTickPrerequisiteActor(Pawn);
    if(auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>())
    {
        AddTickPrerequisiteComponent(Staff);
        // The shared spin controller composes its final camera before either staff or blade publishes a pose.
        if(auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>())Staff->AddTickPrerequisiteComponent(Kukri);
    }
    Arms=NewObject<UKukriArmsMeshComponent>(Pawn,TEXT("StaffOffhandBladeArms"));
    Pawn->AddInstanceComponent(Arms);Arms->SetupAttachment(Camera.Get());
    Arms->SetRelativeTransform(FTransform(FRotator(0,90,0),LeftFraming));
    Arms->bLeftHandOnly=true;
    Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->bReceivesDecals=false;
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCanEverAffectNavigation(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->SetVisibility(false);Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    StrikeArms=NewObject<UOffhandKukriArmsMeshComponent>(Pawn,TEXT("StaffOffhandQuickMeleeArms"));
    Pawn->AddInstanceComponent(StrikeArms);StrikeArms->SetupAttachment(Camera.Get());
    StrikeArms->SetOnlyOwnerSee(true);StrikeArms->SetCastShadow(false);StrikeArms->bReceivesDecals=false;
    StrikeArms->SetCollisionEnabled(ECollisionEnabled::NoCollision);StrikeArms->SetCanEverAffectNavigation(false);
    StrikeArms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    StrikeArms->SetVisibility(false);StrikeArms->RegisterComponent();StrikeArms->SetComponentTickEnabled(false);
    Blade=NewObject<UStaticMeshComponent>(Pawn,TEXT("StaffOffhandBlade"));
    Pawn->AddInstanceComponent(Blade);Blade->SetupAttachment(Arms);
    Blade->SetOnlyOwnerSee(true);Blade->SetCastShadow(false);Blade->bReceivesDecals=false;
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);Blade->SetCanEverAffectNavigation(false);
    Blade->SetVisibility(false);Blade->RegisterComponent();
    if(auto* Outfit=Pawn->FindComponentByClass<UFPSModularOutfitComponent>())Outfit->AddTickPrerequisiteComponent(this);
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->AddTickPrerequisiteComponent(this);
    if(auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>())Potion->AddTickPrerequisiteComponent(this);
    if(Pawn->GetGameInstance())Model=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model.IsValid())EquipmentChanged=Model->OnChanged.AddUObject(this,&UStaffOffhandMeleeComponent::RefreshEquipment);
    SetComponentTickEnabled(true);
    RefreshEquipment();
}

void UStaffOffhandMeleeComponent::RefreshEquipment()
{
    if(!Model.IsValid()||!Arms||!Blade)return;
    const auto* Main=Model->Equipped();
    const int32 Slot=Model->Snapshot().ActiveWeaponSlot;
    const auto* Item=Model->Equipped(Slot==6?8:11);
    const bool Active=Main&&ColdSteelInventory::UsesStaffMelee(*Main)&&Item&&ColdSteelInventory::IsOneHandedBlade(*Item)
        &&!Model->ActiveProductionTool();
    if(!Active)
    {
        if(auto* Kukri=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();Kukri&&bWhirlwindPresentation)Kukri->CancelAction();
        if(auto* Quick=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();Quick&&bActionPresentation)
        {Quick->CancelQuickCombat();Quick->CancelUppercut();Quick->CancelShadowStep();}
        bActionPresentation=false;ActionReturnAge=-1.f;
        if(Load){Load->CancelHandle();Load.Reset();}
        ColdSteelModularSword::Clear(Blade);Instance.Reset();Recipe.Reset();
        bReady=bDrawing=bWasPresenting=false;
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        StrikeArms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        UpdateVisibility();return;
    }
    FString MeshPath=ColdSteelInventory::Text(*Item,TEXT("offhand_melee_mesh"));
    if(MeshPath.IsEmpty()&&(Item->Definition==TEXT("ue_kukri")||ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("kukri")))
        MeshPath=KukriRhythm::BladeMesh;
    // Other swords/knives opt in with their real grip-space mesh; never show a kukri as a missing sword.
    const FString Key=Main->InstanceId+TEXT("|")+Item->InstanceId+TEXT("|")+Item->Data;
    if(Key==Recipe)return;
    const bool NewInstance=Instance!=Item->InstanceId||!Recipe.StartsWith(Main->InstanceId+TEXT("|"));
    if(NewInstance)
    {
        if(auto* Kukri=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();Kukri&&bWhirlwindPresentation)Kukri->CancelAction();
        if(auto* Quick=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();Quick&&bActionPresentation)
        {Quick->CancelQuickCombat();Quick->CancelUppercut();Quick->CancelShadowStep();}
        bActionPresentation=false;ActionReturnAge=-1.f;
    }
    if(Load){Load->CancelHandle();Load.Reset();}
    Instance=Item->InstanceId;Recipe=Key;
    if(NewInstance){bReady=bDrawing=bWasPresenting=false;Arms->ClearEntry();UpdateVisibility();}
    if(MeshPath.IsEmpty())
    {
        Instance.Reset();bReady=false;
        Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));UpdateVisibility();
        UE_LOG(LogTemp,Warning,TEXT("Staff offhand blade %s needs offhand_melee_mesh."),*Item->Definition);
        return;
    }
    Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    const FSoftObjectPath BladePath(MeshPath);
    const bool Axe=ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("hatchet");
    const FSoftObjectPath DrawPath=ColdSteelInventory::UsesKukriMoveset(*Item)?FSoftObjectPath(OffhandBladeDraw::Asset(Axe)):EquipPath;
    TArray<FSoftObjectPath> Paths{FSoftObjectPath(KukriRhythm::ArmsMesh),StrikeArmsPath,IdlePath,DrawPath,WhirlwindPath,BladePath,
        FSoftObjectPath(KukriDrawRhythm::TossSound),FSoftObjectPath(KukriDrawRhythm::CatchSound)};
    ColdSteelModularSword::GatherVisualResources(*Item,Paths);
    if(Axe)
    {
        Paths.Add(FSoftObjectPath(HatchetPairRhythm::Attack3KHClip));
        Paths.Add(FSoftObjectPath(KukriRhythm::RiftMaterial));
    }
    const auto Ready=FStreamableDelegate::CreateWeakLambda(this,[this,Key,Snapshot=*Item,BladePath,NewInstance]()
        {ApplyAssets(Key,Snapshot,BladePath,NewInstance);});
    if(Paths.ContainsByPredicate([](const FSoftObjectPath& Path)
    {
        const auto* Object=Path.ResolveObject();
        return !Object||Object->HasAnyFlags(RF_NeedLoad|RF_NeedPostLoad);
    }))
        Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,Ready);
    else Ready.Execute();
}

void UStaffOffhandMeleeComponent::ApplyAssets(const FString& Key,const FColdSteelItem& Item,const FSoftObjectPath& BladePath,bool NewInstance)
{
    if(Key!=Recipe||!Arms||!Blade)return;
    auto* Skin=Cast<USkeletalMesh>(FSoftObjectPath(KukriRhythm::ArmsMesh).ResolveObject());
    auto* Mesh=Cast<UStaticMesh>(BladePath.ResolveObject());
    auto* IdleClip=Cast<UAnimSequence>(IdlePath.ResolveObject());
    const bool Axe=ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("hatchet");
    const FSoftObjectPath DrawPath=ColdSteelInventory::UsesKukriMoveset(Item)?FSoftObjectPath(OffhandBladeDraw::Asset(Axe)):EquipPath;
    auto* EquipClip=Cast<UAnimSequence>(DrawPath.ResolveObject());
    if(!Skin||!Mesh||!IdleClip||!EquipClip)
    {
        // A failed new draw must not leave the main staff permanently busy.
        // A failed same-item part replacement keeps the already installed presentation.
        if(!bReady){Instance.Reset();Recipe.Reset();Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));UpdateVisibility();}
        UE_LOG(LogTemp,Warning,TEXT("Staff offhand blade assets are incomplete for %s."),*Item.Definition);return;
    }
    Idle=IdleClip;Equip=EquipClip;bDrawHatchet=Axe;
    HatchetChop=Axe?Cast<UAnimSequence>(FSoftObjectPath(HatchetPairRhythm::Attack3KHClip).ResolveObject()):nullptr;
    if(Axe)if(auto* Quick=GetOwner()->FindComponentByClass<UOffhandKukriComponent>())Quick->PrepareQuickRift();
    Whirlwind=Cast<UAnimSequence>(WhirlwindPath.ResolveObject());
    if(auto* StrikeSkin=Cast<USkeletalMesh>(StrikeArmsPath.ResolveObject()))
    {
        if(StrikeArms->GetSkeletalMeshAsset()!=StrikeSkin)StrikeArms->SetSkeletalMesh(StrikeSkin);
        if(const auto* Render=StrikeSkin->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                const FString N=StrikeSkin->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
                const bool HandSection=!N.Contains(TEXT("handguard"))&&(N.Contains(TEXT("skin"))||N.Contains(TEXT("manny"))||
                    N.Contains(TEXT("bare"))||N.Contains(TEXT("glove"))||N.Contains(TEXT("sleeve"))||N==TEXT("hand")||N==TEXT("hands")||N.EndsWith(TEXT("_hands")));
                StrikeArms->ShowMaterialSection(M,S,HandSection,L);
            }
        StrikeArms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    }
    TossSound=Cast<USoundBase>(FSoftObjectPath(KukriDrawRhythm::TossSound).ResolveObject());
    CatchSound=Cast<USoundBase>(FSoftObjectPath(KukriDrawRhythm::CatchSound).ResolveObject());
    if(Arms->GetSkeletalMeshAsset()!=Skin)Arms->SetSkeletalMesh(Skin);
    if(Blade->GetAttachSocketName()!=TEXT("hand_l"))
        Blade->AttachToComponent(Arms,FAttachmentTransformRules::KeepRelativeTransform,TEXT("hand_l"));
    ColdSteelModularSword::Clear(Blade);Blade->SetStaticMesh(Mesh);
    if(ColdSteelModularSword::Supports(Item))ColdSteelModularSword::Apply(Blade,Item);
    BladeFit=FTransform(FRotator(ColdSteelInventory::Number(Item,TEXT("offhand_melee_pitch")),
        ColdSteelInventory::Number(Item,TEXT("offhand_melee_yaw")),ColdSteelInventory::Number(Item,TEXT("offhand_melee_roll"))),
        FVector(ColdSteelInventory::Number(Item,TEXT("offhand_melee_x")),ColdSteelInventory::Number(Item,TEXT("offhand_melee_y")),
            ColdSteelInventory::Number(Item,TEXT("offhand_melee_z"))));
    bReady=true;
    if(NewInstance)bWasPresenting=false;
    // Visibility/clock start together on the next pre-camera step, after the staff is resident too.
}

bool UStaffOffhandMeleeComponent::OwnsLeftHand() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!IsEquipped()||!bReady||!Pawn||!Pawn->IsLocallyControlled()||Pawn->IsTraversing())return false;
    const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
    const bool MainPresented=Staff&&Staff->HasMeleeMoveset()&&Staff->ArmsMesh()&&Staff->ArmsMesh()->GetSkeletalMeshAsset()&&Staff->ArmsMesh()->IsVisible();
    if(!MainPresented)return false;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    return PC&&(!Health||!Health->IsDead())&&(!Build||!Build->IsBuilding()||Build->IsPanelOpen())
        &&!(Potion&&Potion->IsTwoHanded());
}

void UStaffOffhandMeleeComponent::StartDraw()
{
    Age=0.f;bDrawing=true;Arms->ClearEntry();
    Arms->PlayAnimation(Equip,false);Arms->SetPlayRate(0.f);
    SamplePose();
}

void UStaffOffhandMeleeComponent::AdvanceBeforeCamera(float Delta)
{
    if(Arms)Arms->AdvanceEntry(FMath::Max(0.f,Delta)*LightningHaste::ActionSpeed(GetOwner()));
    if(ActionReturnAge>=0.f)
    {
        ActionReturnAge+=FMath::Max(0.f,Delta)*LightningHaste::ActionSpeed(GetOwner());
        if(ActionReturnAge>=StaffOffhandQuickMotion::CancelReturn)ActionReturnAge=-1.f;
    }
    const bool Presenting=OwnsLeftHand();
    PairWeight=FMath::FInterpConstantTo(PairWeight,Presenting?1.f:0.f,FMath::Max(0.f,Delta),1.f/PairBlendSeconds);
    if(!Presenting){bWasPresenting=false;return;}
    if(IsActionPresentationActive())return;
    if(!bWasPresenting){StartDraw();bWasPresenting=true;return;}
    const float Before=Age;
    Age+=FMath::Max(0.f,Delta)*LightningHaste::ActionSpeed(GetOwner());
    if(bDrawing)
    {
        OffhandBladeDraw::PlayCues(this,bDrawHatchet,Before,Age,TossSound,CatchSound);
        if(Age>=Equip->GetPlayLength())
        {
            bDrawing=false;Age=0.f;
            // DualEquip ends at DualIdle frame zero, including the left grip and fingers.
            Arms->PlayAnimation(Idle,true);Arms->SetPlayRate(0.f);
        }
    }
    else Age=FMath::Fmod(Age,FMath::Max(.01f,Idle->GetPlayLength()));
}

FVector UStaffOffhandMeleeComponent::StaffOffset() const
{
    const float Weight=FMath::SmoothStep(0.f,1.f,PairWeight);
    return RightFraming*Weight;
}
void UStaffOffhandMeleeComponent::GetCameraMotion(FRotator& Rotation,float& Fov) const
{
    Rotation=FRotator::ZeroRotator;Fov=0.f;
    if(!bDrawing||!bWasPresenting||!OwnsLeftHand())return;
    if(const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();Body&&Body->IsThirdPersonViewEnabled())return;
    OffhandBladeDraw::Camera(bDrawHatchet,Age,Rotation,Fov);
}
void UStaffOffhandMeleeComponent::SamplePose()
{
    if(!bReady||!Arms)return;
    if(bWhirlwindPresentation){SampleWhirlwindPose();return;}
    if(IsActionPresentationActive()){SampleActionPose();return;}
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const float Lower=Potion&&Potion->IsStowingOffhand()?Potion->OffhandLowerWeight():0.f;
    Arms->SetRelativeLocation(LeftFraming+FVector(-6.f,0.f,-35.f)*Lower);
    Arms->SetPosition(Age,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    Blade->SetRelativeTransform(BladeFit*(bDrawing?OffhandBladeDraw::InHand(bDrawHatchet,Age):KukriOffhandDraw::Grip()));
}
void UStaffOffhandMeleeComponent::UpdateVisibility()
{
    if(!Arms||!Blade)return;
    const bool Show=bWasPresenting&&OwnsLeftHand();
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const bool ShowBlade=Show&&(!Potion||!Potion->IsOffhandWeaponHidden())&&(!Pawn||!Pawn->IsDoorPushActive());
    const bool Strike=Show&&UsesStrikeRig();
    if(Arms->IsVisible()!=(Show&&!Strike))Arms->SetVisibility(Show&&!Strike);
    if(StrikeArms&&StrikeArms->IsVisible()!=Strike)StrikeArms->SetVisibility(Strike);
    if(Blade->IsVisible()!=ShowBlade)Blade->SetVisibility(ShowBlade,true);
}
void UStaffOffhandMeleeComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);UpdateVisibility();
    if(bWasPresenting&&OwnsLeftHand())SamplePose();
}
void UStaffOffhandMeleeComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(auto* Kukri=GetOwner()->FindComponentByClass<UKukriWeaponComponent>();Kukri&&bWhirlwindPresentation)Kukri->CancelAction();
    if(auto* Quick=GetOwner()->FindComponentByClass<UOffhandKukriComponent>();Quick&&bActionPresentation)
    {Quick->CancelQuickCombat();Quick->CancelUppercut();}
    if(Model.IsValid())Model->OnChanged.Remove(EquipmentChanged);
    if(Load)Load->CancelHandle();
    ColdSteelModularSword::Clear(Blade);
    Super::EndPlay(Reason);
}
