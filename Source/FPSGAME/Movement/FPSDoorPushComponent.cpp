#include "FPSDoorPushComponent.h"
#include "DoorPushAuthored20261002.h"
#include "DoorPushCameraShake.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/ColdSteelDoor.h"
#include "../Building/ColdSteelDoubleDoor.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Sound/SoundBase.h"

namespace
{
const FSoftObjectPath DoorPushArmsPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
const FSoftObjectPath DoorPushImpactPath(TEXT("/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact.S_DoorPushImpact"));
constexpr float DoorPushReachCm=210.f;
bool IsClosedPushDoor(const AActor* Target)
{
    if(!IsValid(Target)||Target->ActorHasTag(TEXT("VoxelDetached")))return false;
    if(const auto* Single=Cast<AColdSteelDoor>(Target))return !Single->IsDoorOpen();
    if(const auto* Double=Cast<AColdSteelDoubleDoor>(Target))return !Double->IsWindowOpen();
    return false;
}
}

UFPSDoorPushComponent::UFPSDoorPushComponent()
{PrimaryComponentTick.bCanEverTick=false;}

void UFPSDoorPushComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()!=NM_Standalone)return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("DoorPushFallbackLeftArm"));
    GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
    FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
    FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetCastShadow(false);FallbackHands->bReceivesDecals=false;
    FallbackHands->SetVisibility(false);FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
    FallbackHands->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    FallbackHands->SetBoundsScale(2.f);
    FallbackHands->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    if(DoorPushArmsPath.ResolveObject())ApplyLoadedHands();
    // Keep both assets pinned for this component's lifetime, even if the arms
    // already arrived through an outfit preloader. Contact never loads from disk.
    const TArray<FSoftObjectPath> PreloadPaths{DoorPushArmsPath,DoorPushImpactPath};
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(PreloadPaths,
        FStreamableDelegate::CreateUObject(this,&UFPSDoorPushComponent::ApplyLoadedHands));
}

void UFPSDoorPushComponent::ApplyLoadedHands()
{
    auto* Asset=Cast<USkeletalMesh>(DoorPushArmsPath.ResolveObject());if(!Asset||!FallbackHands)return;
    FallbackHands->SetSkeletalMesh(Asset);
    if(const auto* Render=Asset->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            const bool Arm=!Name.Contains(TEXT("handguard"))&&(Name.Contains(TEXT("skin"))||Name.Contains(TEXT("manny"))||
                Name.Contains(TEXT("bare"))||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||
                Name==TEXT("hand")||Name==TEXT("hands")||Name.EndsWith(TEXT("_hands")));
            FallbackHands->ShowMaterialSection(M,S,Arm,L);
        }
    FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    FallbackHands->HideBoneByName(TEXT("WPN_root"),EPhysBodyOp::PBO_None);
}

bool UFPSDoorPushComponent::CanStart() const
{
    if(!FallbackHands||!FallbackHands->GetSkeletalMeshAsset())return false;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||GetNetMode()!=NM_Standalone||!Player->IsLocallyControlled())return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->GetViewTarget()!=Player||AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    if(Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||Player->IsSwitchingWeapon()||
        Player->IsLeftHandBusyForCast()||Player->IsCastBlockingLeftHandAction()||Player->IsSpellGestureBlocking())return false;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();Body&&Body->IsThirdPersonViewEnabled())return false;
    if(const auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();Bow&&Bow->IsEquipped()&&Bow->IsBusy())return false;
    return true;
}

bool UFPSDoorPushComponent::Probe(FHitResult& Hit) const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC=Player?Cast<APlayerController>(Player->GetController()):nullptr;if(!PC)return false;
    FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SprintDoorPush),false,Player);
    // Use the same first visible blocker and recoverable-arrow priority as E.
    TArray<FHitResult> TraceHits;
    GetWorld()->LineTraceMultiByChannel(TraceHits,Eye,Eye+View.Vector()*DoorPushReachCm,ECC_Visibility,Query);
    for(const auto& Result:TraceHits)
    {
        if(const auto* Arrow=Cast<ABowArrow>(Result.GetActor());Arrow&&Arrow->CanRecover())return false;
        if(Result.bBlockingHit){Hit=Result;return IsClosedPushDoor(Hit.GetActor());}
    }
    return false;
}

bool UFPSDoorPushComponent::BeginPush(const FHitResult& Hit)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player)return false;
    ActiveHands.Reset();USkeletalMeshComponent* Source=nullptr;
    const auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    if(!Bow||!Bow->IsEquipped())
    {
        TInlineComponentArray<UFPSCastingMeshComponent*> Meshes(Player);
        for(auto* Mesh:Meshes)if(Mesh!=FallbackHands&&Mesh->bApplyLeftHandCast&&Mesh->GetSkeletalMeshAsset()&&
            Mesh->IsVisible()&&!Mesh->bHiddenInGame&&Mesh->GetBoneIndex(TEXT("hand_l"))>=0)
        {ActiveHands=Mesh;Source=Mesh;break;}
    }
    else
    {
        TInlineComponentArray<USkeletalMeshComponent*> Meshes(Player);
        for(auto* Mesh:Meshes)if(Mesh!=FallbackHands&&Mesh->IsVisible()&&!Mesh->bHiddenInGame&&
            Mesh->GetName().Contains(TEXT("Bow"))&&Mesh->GetBoneIndex(TEXT("hand_l"))>=0)
        {Source=Mesh;break;}
        if(FallbackHands&&FallbackHands->GetSkeletalMeshAsset())ActiveHands=FallbackHands;
    }
    // Static tools have no native hand viewmodel. Enter/recover below the view
    // using the same canonical closed-fist idle example as the authored take.
    if(!Source&&FallbackHands&&FallbackHands->GetSkeletalMeshAsset())
    {
        ActiveHands=FallbackHands;Source=FallbackHands;
        FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();
    }
    if(!ActiveHands.IsValid()||!Source||!FallbackHands||!FallbackHands->GetSkeletalMeshAsset()||
        !PoseLayer.Capture(*ActiveHands.Get(),*Source,*FallbackHands->GetSkeletalMeshAsset(),
            Source==FallbackHands.Get()))return false;
    Door=LastDoor=Hit.GetActor();
    Age=0.f;bContactResolved=false;bActive=true;
    return true;
}

float UFPSDoorPushComponent::GetPresentationWeight() const
{
    if(!bActive)return 0.f;
    namespace Motion=DoorPushAuthored20261002;
    if(Age>=Motion::RecoverStartSeconds)
        return 1.f-Motion::Ease((Age-Motion::RecoverStartSeconds)/Motion::RecoverySeconds);
    return Motion::Ease(Age/Motion::PrepareSeconds);
}

void UFPSDoorPushComponent::Advance(float Delta)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||!Player->IsLocallyControlled()||Delta<=0.f)return;
    if(bActive)
    {
        const auto* PC=Cast<APlayerController>(Player->GetController());
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
        if(!ActiveHands.IsValid()||!PC||PC->GetViewTarget()!=Player||Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||
            (Body&&Body->IsThirdPersonViewEnabled())||
            (Health&&Health->IsDead())||AFPSGAMEPlayerController::BlocksOngoingActions(PC))
        {Cancel();return;}
        Age+=Delta;
        if(Age>=DoorPushAuthored20261002::ContactSeconds&&!bContactResolved)
        {
            bContactResolved=true;FHitResult Hit;
            if(Player->IsSprinting()&&IsClosedPushDoor(Door.Get())&&Probe(Hit)&&Hit.GetActor()==Door.Get())
            {
                bool bOpened=false;
                if(auto* Single=Cast<AColdSteelDoor>(Door.Get()))
                {Single->OpenDoor();bOpened=Single->IsDoorOpen();}
                else if(auto* Double=Cast<AColdSteelDoubleDoor>(Door.Get()))
                {Double->OpenWindow();bOpened=Double->IsWindowOpen();}
                if(bOpened)
                {
                    if(auto* Impact=Cast<USoundBase>(DoorPushImpactPath.ResolveObject()))
                        UGameplayStatics::PlaySound2D(this,Impact,.85f,1.f,0.f,nullptr,Player,false);
                }
                if(bOpened&&PC->PlayerCameraManager)
                {
                    const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
                    const float Scale=Setting?FMath::Max(0.f,Setting->GetFloat()):1.f;
                    if(Scale>0.f)PC->PlayerCameraManager->StartCameraShake(UDoorPushCameraShake::StaticClass(),
                        Scale,ECameraShakePlaySpace::CameraLocal);
                }
            }
        }
        if(Age>=DoorPushAuthored20261002::DurationSeconds)Cancel();
        return;
    }
    const auto* Movement=Player->GetCharacterMovement();
    // IsSprinting is refreshed from held Shift and forward input, not velocity.
    // A closed door can stop movement while the player still intends to sprint.
    const bool Sprint=Player->IsSprinting()&&Movement&&Movement->IsMovingOnGround();
    if(!Sprint){SprintAge=ProbeAge=0.f;LastDoor.Reset();return;}
    SprintAge+=Delta;ProbeAge+=Delta;
    // The Shift tap remains a dodge. A sustained sprint alone can own this gesture.
    if(SprintAge<.21f||ProbeAge<1.f/30.f||!CanStart())return;
    ProbeAge=0.f;FHitResult Hit;
    if(!Probe(Hit)){LastDoor.Reset();return;}
    if(Hit.GetActor()==LastDoor.Get())return;
    const FVector Forward=FRotator(0,Player->GetControlRotation().Yaw,0).Vector();
    if(FVector::DotProduct(Hit.ImpactNormal,Forward)>-.55f)return;
    BeginPush(Hit);
}

void UFPSDoorPushComponent::ApplyHandPose(UFPSCastingMeshComponent& Mesh)
{
    if(!bActive||ActiveHands.Get()!=&Mesh)return;
    PoseLayer.Apply(Mesh,Age);
}

void UFPSDoorPushComponent::UpdatePresentation()
{
    if(!FallbackHands)return;
    const bool Show=bActive&&ActiveHands.Get()==FallbackHands.Get();FallbackHands->SetVisibility(Show);
    if(Show){FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();}
}

void UFPSDoorPushComponent::Cancel()
{
    bActive=false;ActiveHands.Reset();Door.Reset();PoseLayer.Reset();
    if(FallbackHands)FallbackHands->SetVisibility(false);
}

void UFPSDoorPushComponent::EndPlay(const EEndPlayReason::Type Reason)
{Cancel();if(Load){Load->CancelHandle();Load.Reset();}Super::EndPlay(Reason);}
