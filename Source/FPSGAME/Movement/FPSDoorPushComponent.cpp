#include "FPSDoorPushComponent.h"
#include "DoorPushAuthored20261002.h"
#include "DoorPushCameraShake.h"
#include "FPSCharacterMovementComponent.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
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
{PrimaryComponentTick.bCanEverTick=false;SetIsReplicatedByDefault(true);}

void UFPSDoorPushComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
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
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||!Player->IsLocallyControlled())return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->GetViewTarget()!=Player||AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    if(Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||Player->IsSwitchingWeapon()||
        Player->IsLeftHandBusyForCast()||Player->IsCastBlockingLeftHandAction()||Player->IsSpellGestureBlocking())return false;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
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
    Age=0.f;bContactResolved=false;bActive=true;bAwaitingImpact=true;
    ++LocalSequence;ServerBeginPush(LocalSequence,Door.Get());
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
    if(GetOwner()->HasAuthority())AdvanceAuthority(Delta);
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||!Player->IsLocallyControlled()||Delta<=0.f)return;
    if(bActive)
    {
        const auto* PC=Cast<APlayerController>(Player->GetController());
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
        if(!ActiveHands.IsValid()||!PC||PC->GetViewTarget()!=Player||Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||
            (Health&&Health->IsDead())||AFPSGAMEPlayerController::BlocksOngoingActions(PC))
        {Cancel();return;}
        Age+=Delta;
        if(Age>=DoorPushAuthored20261002::ContactSeconds&&!bContactResolved)
        {
            bContactResolved=true;
            ServerContactPush(LocalSequence);
        }
        if(Age>=DoorPushAuthored20261002::DurationSeconds)Cancel(true);
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

void UFPSDoorPushComponent::Cancel(bool bCompleted)
{
    if(!bCompleted)bAwaitingImpact=false;
    if(!bCompleted&&bActive&&GetOwner()&&Cast<APawn>(GetOwner())->IsLocallyControlled())ServerCancelPush(LocalSequence);
    bActive=false;ActiveHands.Reset();Door.Reset();PoseLayer.Reset();
    if(FallbackHands)FallbackHands->SetVisibility(false);
}

void UFPSDoorPushComponent::EndPlay(const EEndPlayReason::Type Reason)
{Cancel();if(Load){Load->CancelHandle();Load.Reset();}Super::EndPlay(Reason);}

// RPCs travel on the owning pawn's component. Door actors remain server-owned.
bool UFPSDoorPushComponent::ServerCanInteract(AActor* Target,bool bSprint) const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player||!Player->HasAuthority()||!IsValid(Target)||Target->GetWorld()!=GetWorld()||
        Target->ActorHasTag(TEXT("VoxelDetached")))return false;
    if(!Cast<AColdSteelDoor>(Target)&&!Cast<AColdSteelWindow>(Target))return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||Player->IsSwitchingWeapon()||
        Player->IsLeftHandBusyForCast()||Player->IsCastBlockingLeftHandAction()||Player->IsSpellGestureBlocking())return false;
    if(Player->BipodDeployment&&Player->BipodDeployment->BlocksMovement())return false;
    if(bSprint)
    {
        const auto* Move=Cast<UFPSCharacterMovementComponent>(Player->GetCharacterMovement());
        if(!IsClosedPushDoor(Target)||!Move||!Move->IsMovingOnGround()||Move->bWantsToSlide||
            !(Player->IsLocallyControlled()?Player->IsSprinting():bool(Move->bWantsToSprint)))return false;
    }
    FVector Eye=Player->GetMeleeAimTransform().GetLocation();FRotator Aim=Player->GetControlRotation();
    if(Player->IsLocallyControlled())ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,Aim);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NetDoorReach),false,Player);
    TArray<FHitResult> Hits;
    GetWorld()->LineTraceMultiByChannel(Hits,Eye,Eye+Aim.Vector()*(bSprint?DoorPushReachCm:250.f),ECC_Visibility,Params);
    for(const auto& Hit:Hits)
    {
        if(const auto* Arrow=Cast<ABowArrow>(Hit.GetActor());Arrow&&Arrow->CanRecover())return false;
        if(!Hit.bBlockingHit)continue;
        return Hit.GetActor()==Target&&(!bSprint||FVector::DotProduct(Hit.ImpactNormal,FRotator(0,Aim.Yaw,0).Vector())<=-.55f);
    }
    return false;
}

void UFPSDoorPushComponent::ServerBeginPush_Implementation(uint16 Sequence,AActor* Target)
{
    const double Now=GetWorld()->GetTimeSeconds();
    if(ServerDoor.IsValid()||(LastServerRequest>=0.&&Now-LastServerRequest<.2)||!ServerCanInteract(Target,true))
    {ClientPushResult(Sequence,false);return;}
    LastServerRequest=Now;ServerSequence=Sequence;ServerDoor=Target;ServerAge=0.f;bServerContact=false;
}

void UFPSDoorPushComponent::ServerContactPush_Implementation(uint16 Sequence)
{
    if(Sequence==ServerSequence&&ServerDoor.IsValid())
    {bServerContact=true;AdvanceAuthority(0.f);}
}

void UFPSDoorPushComponent::ServerCancelPush_Implementation(uint16 Sequence)
{
    if(Sequence==ServerSequence){ServerDoor.Reset();bServerContact=false;}
}

void UFPSDoorPushComponent::AdvanceAuthority(float DeltaSeconds)
{
    if(!ServerDoor.IsValid())return;
    ServerAge+=DeltaSeconds;
    if(ServerAge>DoorPushAuthored20261002::DurationSeconds+.5f)
    {ServerDoor.Reset();ClientPushResult(ServerSequence,false);return;}
    if(!bServerContact||ServerAge<DoorPushAuthored20261002::ContactSeconds)return;
    AActor* Target=ServerDoor.Get();ServerDoor.Reset();bServerContact=false;
    if(!ServerCanInteract(Target,true)){ClientPushResult(ServerSequence,false);return;}
    const auto* Player=Cast<APawn>(GetOwner());
    if(auto* Single=Cast<AColdSteelDoor>(Target))Single->OpenDoorFrom(Player);
    else if(auto* Double=Cast<AColdSteelDoubleDoor>(Target))Double->OpenWindowFrom(Player);
    ClientPushResult(ServerSequence,true);
    MulticastPushImpact(Target->GetActorLocation()+FVector(0,0,100));
}

void UFPSDoorPushComponent::ClientPushResult_Implementation(uint16 Sequence,bool bOpened)
{
    if(Sequence!=LocalSequence||!bAwaitingImpact)return;
    bAwaitingImpact=false;
    if(!bOpened){Cancel();return;}
    PlayImpact();
}

void UFPSDoorPushComponent::PlayImpact()
{
    auto* Player=Cast<APawn>(GetOwner());if(!Player||!Player->IsLocallyControlled())return;
    if(auto* Sound=Cast<USoundBase>(DoorPushImpactPath.ResolveObject()))UGameplayStatics::PlaySound2D(this,Sound,.85f);
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(PC&&PC->PlayerCameraManager)
    {
        const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
        const float Scale=Setting?FMath::Max(0.f,Setting->GetFloat()):1.f;
        if(Scale>0.f)PC->PlayerCameraManager->StartCameraShake(UDoorPushCameraShake::StaticClass(),Scale,ECameraShakePlaySpace::CameraLocal);
    }
}

void UFPSDoorPushComponent::MulticastPushImpact_Implementation(FVector_NetQuantize Location)
{
    const auto* Player=Cast<APawn>(GetOwner());
    if(GetNetMode()==NM_DedicatedServer||!Player||Player->IsLocallyControlled())return;
    if(auto* Sound=Cast<USoundBase>(DoorPushImpactPath.ResolveObject()))UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,.85f);
}

bool UFPSDoorPushComponent::RequestDoorInteraction(AActor* Target)
{
    if(!IsValid(Target)||(!Cast<AColdSteelDoor>(Target)&&!Cast<AColdSteelWindow>(Target)))return false;
    Cancel();ServerToggleDoor(Target);return true;
}

void UFPSDoorPushComponent::ServerToggleDoor_Implementation(AActor* Target)
{
    const double Now=GetWorld()->GetTimeSeconds();
    if((LastServerRequest>=0.&&Now-LastServerRequest<.15)||!ServerCanInteract(Target,false))return;
    LastServerRequest=Now;ServerDoor.Reset();bServerContact=false;
    if(auto* Single=Cast<AColdSteelDoor>(Target))Single->ToggleDoorFrom(Cast<APawn>(GetOwner()));
    else if(auto* Window=Cast<AColdSteelWindow>(Target))Window->ToggleWindowFrom(Cast<APawn>(GetOwner()));
}
