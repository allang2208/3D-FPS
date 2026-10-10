#include "FPSPlayerBodyComponent.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

#include "HAL/IConsoleManager.h"

namespace FPSPlayerBodyDiagnostics
{
/** Runtime switch for the world-space player body. 0 hides the third-person body
 *  mesh, the world weapon copies, the attachment copies and the outfit meshes, so the
 *  cost of the feature can be measured in a live session without a rebuild. Read at
 *  use sites rather than mirrored into a member, because a console variable set from
 *  the command line lands after the world has already been initialised. */
static int32 GWorldBodyVisible = 1;
static void OnWorldBodyVisibleChanged(IConsoleVariable* /*Variable*/);
static FAutoConsoleVariableRef CVarWorldBodyVisible(
    TEXT("fps.body.WorldBody"),
    GWorldBodyVisible,
    TEXT("1 = draw the third-person player body and its world equipment copies (default).\n")
    TEXT("0 = hide them. Runtime switch for measuring the feature's frame cost; the\n")
    TEXT("body mesh stays resident so toggling back is instant."),
    ECVF_Default);
static void OnWorldBodyVisibleChanged(IConsoleVariable*)
{
    // Apply at once instead of waiting for the 0.2 s visibility refresh, so the effect
    // of toggling in a live session is immediate.
    if(!GEngine)return;
    for(const FWorldContext& Context:GEngine->GetWorldContexts())
        if(UWorld* World=Context.World())
            for(TActorIterator<AFPSGAMECharacter> It(World);It;++It)
                if(auto* Body=It->FindComponentByClass<UFPSPlayerBodyComponent>())
                    Body->ApplyWorldBodyVisibility();
}

/** Diagnostic isolation for hitch captures: hides the body for the whole session.
 *  Distinct from GWorldBodyVisible, which is a live toggle. */
static int32 GWorldBodySuppress = 0;
static FAutoConsoleVariableRef CVarWorldBodySuppress(
    TEXT("fps.body.WorldBodySuppress"),
    GWorldBodySuppress,
    TEXT("1 = never build the world body at all, for isolation captures. Default 0.\n")
    TEXT("Must be set on the command line, since it is read once during initialisation."),
    ECVF_Default);
/** 阴影开关。第一人称下可见的身体与世界装备副本都带 OwnerNoSee + bCastHiddenShadow，
 *  也就是「看不见但仍然渲染阴影深度」。这几个网格 LOD0 加起来近 40 万三角面，
 *  每帧都要为 VSM/CSM 再走一遍深度 pass。此开关用于把这部分成本单独摘出来量。 */
static int32 GWorldBodyShadow = 1;
static void OnWorldBodyShadowChanged(IConsoleVariable* /*Variable*/);
static FAutoConsoleVariableRef CVarWorldBodyShadow(
    TEXT("fps.body.WorldBodyShadow"),
    GWorldBodyShadow,
    TEXT("1 = the player body and its world equipment copies cast shadows (default).\n")
    TEXT("0 = stop them casting. They are already invisible in first person, so this\n")
    TEXT("only removes their shadow-map depth pass. Runtime switch for A/B measurement."),
    ECVF_Default);
static void OnWorldBodyShadowChanged(IConsoleVariable*)
{
    if(!GEngine)return;
    for(const FWorldContext& Context:GEngine->GetWorldContexts())
        if(UWorld* World=Context.World())
            for(TActorIterator<AFPSGAMECharacter> It(World);It;++It)
                if(auto* Body=It->FindComponentByClass<UFPSPlayerBodyComponent>())
                    Body->ApplyWorldBodyShadow();
}
}

bool FPSPlayerBodyWorldBodySuppressed()
{
    return FPSPlayerBodyDiagnostics::GWorldBodySuppress != 0;
}

bool FPSPlayerBodyWorldBodyHidden()
{
    return FPSPlayerBodyDiagnostics::GWorldBodyVisible == 0;
}

bool FPSPlayerBodyWorldBodyShadowEnabled()
{
    return FPSPlayerBodyDiagnostics::GWorldBodyShadow != 0;
}

bool UFPSPlayerBodyComponent::ShouldWorldBodyCastShadow() const
{
    // The diagnostic shadow switch controls the local first-person body only.
    const bool FirstPersonOwner=Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled();
    return !FPSPlayerBodyWorldBodyHidden()&&(!FirstPersonOwner||FPSPlayerBodyWorldBodyShadowEnabled());
}

void UFPSPlayerBodyComponent::ApplyWorldBodyShadow()
{
    if(!Character.IsValid())return;
    const bool bCast=ShouldWorldBodyCastShadow();
    FPSBodyEquipment::ApplyShadowFlags(GetBodyMesh(),bCast);
    for(const TObjectPtr<USkeletalMeshComponent>& Outfit:OutfitMeshes)
        FPSBodyEquipment::ApplyShadowFlags(Outfit,bCast);
    for(const TObjectPtr<UStaticMeshComponent>& Outfit:OutfitStaticMeshes)
        FPSBodyEquipment::ApplyShadowFlags(Outfit,bCast);
    // Weapons use the same policy plus traversal / per-hand occupancy.
    UpdateWorldWeaponPresentation();
    UpdateAppearanceVisibility();
}

void UFPSPlayerBodyComponent::ApplyWorldBodyVisibility()
{
    // Equipment is handled separately with its hand-occupancy rules; never briefly
    // unhide a stowed weapon here before hiding it again later in the same frame.
    const bool bHidden=FPSPlayerBodyWorldBodyHidden();
    TArray<UPrimitiveComponent*> Targets;
    if(auto* Body=GetBodyMesh())Targets.Add(Body);
    // These arrays hold TObjectPtr, so the element type must be spelled out rather than
    // deduced with auto*.
    for(const TObjectPtr<USkeletalMeshComponent>& Outfit:OutfitMeshes)if(Outfit)Targets.Add(Outfit.Get());
    for(const TObjectPtr<UStaticMeshComponent>& Outfit:OutfitStaticMeshes)if(Outfit)Targets.Add(Outfit.Get());

    for(UPrimitiveComponent* Target:Targets)
    {
        if(Target->IsVisible()==bHidden)Target->SetVisibility(!bHidden);
        if(Target->bHiddenInGame!=bHidden)Target->SetHiddenInGame(bHidden);
    }
    // Other players and hidden-shadow passes still consume bone transforms.
    // Only a body excluded from both rendering and shadows can skip the refresh.
    if(auto* Body=GetBodyMesh())
    {
        const bool bDrawn=!bHidden&&Character.IsValid()&&(!Character->IsLocallyControlled()||IsThirdPersonViewEnabled()
            ||ShouldWorldBodyCastShadow()||(FirstPersonLowerBody&&ShouldShowFirstPersonLowerBody()));
        const auto Wanted=bDrawn?EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones
                                :EVisibilityBasedAnimTickOption::AlwaysTickPose;
        if(Body->VisibilityBasedAnimTickOption!=Wanted)Body->VisibilityBasedAnimTickOption=Wanted;
    }
    // Apply each primitive's final shadow state, including stowed equipment.
    ApplyWorldBodyShadow();
    UpdateFirstPersonLowerBodyVisibility();
}

UFPSPlayerBodyComponent::UFPSPlayerBodyComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetIsReplicatedByDefault(true);
}
void UFPSPlayerBodyComponent::BeginPlay()
{
    Super::BeginPlay();Character=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Character.IsValid()||!GetWorld()->IsGameWorld()||GetWorld()->WorldType==EWorldType::GamePreview)
    {SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(Character.Get());
    if(auto* Sword=Character->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    if(auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>())AddTickPrerequisiteComponent(Bow);
    if(auto* Staff=Character->FindComponentByClass<UStaffWeaponComponent>())AddTickPrerequisiteComponent(Staff);
    if(auto* Tool=Character->FindComponentByClass<UProductionToolComponent>())AddTickPrerequisiteComponent(Tool);
    if(auto* Dual=Character->DualPistols.Get())AddTickPrerequisiteComponent(Dual);
    if(auto* Potion=Character->FindComponentByClass<UFPSPotionUseComponent>())AddTickPrerequisiteComponent(Potion);
    if(auto* Hands=Character->FindComponentByClass<UFPSUnarmedIdleComponent>())AddTickPrerequisiteComponent(Hands);
    if(auto* Bipod=Character->FindComponentByClass<UWeaponBipodDeploymentComponent>())AddTickPrerequisiteComponent(Bipod);
    FString Json;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))))
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Configuration);
    if(!Configuration.IsValid())
    {UE_LOG(LogTemp,Error,TEXT("PlayerBody: missing Content/ColdSteelData/player_body.json"));SetComponentTickEnabled(false);return;}
    if(GetNetMode()!=NM_DedicatedServer)InitializeBody();
    if(Character->GetGameInstance())if(auto* Profile=Character->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        ProfileChanged=Profile->OnChanged.AddUObject(this,&UFPSPlayerBodyComponent::RefreshEquipment);
}
void UFPSPlayerBodyComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(FirstPersonLowerBody){FirstPersonLowerBody->DestroyComponent();FirstPersonLowerBody=nullptr;}
    ClearBow();
    ClearMotion();
    ++AppearanceRequest;
    if(AppearanceLoad){AppearanceLoad->CancelHandle();AppearanceLoad.Reset();}
    if(Character.IsValid()&&Character->GetGameInstance())if(auto* Profile=Character->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->OnChanged.Remove(ProfileChanged);
    Super::EndPlay(Reason);
}
void UFPSPlayerBodyComponent::InitializeBody()
{
    auto* Body=GetBodyMesh();if(!Body)return;
    if(FPSPlayerBodyWorldBodySuppressed())
    {
        UE_LOG(LogTemp,Display,TEXT("PlayerBody: world body suppressed by fps.body.WorldBodySuppress 1 (capture isolation)"));
        SetComponentTickEnabled(false);return;
    }
    const FString MeshPath=Configuration->GetStringField(TEXT("body_mesh"));
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*MeshPath);
    if(!Mesh){UE_LOG(LogTemp,Error,TEXT("PlayerBody: cannot load %s"),*MeshPath);return;}
    Body->SetSkeletalMeshAsset(Mesh);
    // World weapon rigs were authored for Manny's hand axes. Retargeting the
    // body does not change those rigs; convert their mounts to the new bind axes.
    FString ReferencePath;
    if(Configuration->TryGetStringField(TEXT("weapon_pose_reference_mesh"),ReferencePath))
        if(const auto* Reference=LoadObject<USkeletalMesh>(nullptr,*ReferencePath))
        {
            const auto Bind=[](const USkeletalMesh* Asset,FName Bone)
            {
                FTransform Result=FTransform::Identity;const auto& Ref=Asset->GetRefSkeleton();
                for(int32 I=Ref.FindBoneIndex(Bone);I!=INDEX_NONE;I=Ref.GetParentIndex(I))Result=Result*Ref.GetRefBonePose()[I];
                return Result.GetRotation();
            };
            for(int32 I=0;I<2;++I)
            {
                const FName Bone=I==0?TEXT("hand_r"):TEXT("hand_l");
                HandRigOffsets[I]=FTransform(Bind(Mesh,Bone).Inverse()*Bind(Reference,Bone));
            }
        }
    Body->SetRelativeLocation(FVector(0,0,-Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()));
    Body->SetRelativeRotation(FRotator(0,-90,0));
    Character->CacheInitialMeshOffset(Body->GetRelativeLocation(),Body->GetRelativeRotation());
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetGenerateOverlapEvents(false);
    Body->SetOnlyOwnerSee(false);Body->SetOwnerNoSee(true);
    Body->SetCastShadow(true);Body->bCastHiddenShadow=true;
    Body->SetVisibility(true);Body->SetHiddenInGame(false);
    Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
    BodyAnimation=Cast<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());
    if(BodyAnimation)
    {
        const TArray<TSharedPtr<FJsonValue>>* Scale=nullptr;
        if(Configuration->TryGetArrayField(TEXT("pose_scale"),Scale)&&Scale->Num()==3)
            BodyAnimation->PoseScale=FVector((*Scale)[0]->AsNumber(),(*Scale)[1]->AsNumber(),(*Scale)[2]->AsNumber());
        const TArray<TSharedPtr<FJsonValue>>* Mouth=nullptr;
        if(Configuration->TryGetArrayField(TEXT("consume_mouth_in_head"),Mouth)&&Mouth->Num()==3)
            BodyAnimation->ConsumeMouthInHead=FVector((*Mouth)[0]->AsNumber(),(*Mouth)[1]->AsNumber(),(*Mouth)[2]->AsNumber());
        const TSharedPtr<FJsonObject>* Clips=nullptr;
        if(Configuration->TryGetObjectField(TEXT("clips"),Clips))for(const auto& Pair:(*Clips)->Values)
            if(auto* Sequence=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))BodyAnimation->Clips.Add(FName(*Pair.Key),Sequence);
    }
    Body->AddTickPrerequisiteComponent(this);
    BodyPoseFinalizedHandle=Body->RegisterOnBoneTransformsFinalizedDelegate(FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this,&ThisClass::OnBodyPoseFinalized));
    if(!Character->IsLocallyControlled()&&GetNetMode()!=NM_Standalone)
    {RebuildWeapons(ReplicatedWeapons);ApplyOutfit(ReplicatedOutfit);}
    ApplyAppearance(ReplicatedAppearance);
    InitializeFirstPersonLowerBody();
    ApplyWorldBodyVisibility();
    UpdateOwnerVisibility();
}
USkeletalMeshComponent* UFPSPlayerBodyComponent::GetBodyMesh() const
{return Character.IsValid()?Character->GetMesh():nullptr;}
float UFPSPlayerBodyComponent::ServerClock() const
{
    const auto* World=GetWorld();
    if(const auto* State=World?World->GetGameState():nullptr)return State->GetServerWorldTimeSeconds();
    return World?World->GetTimeSeconds():0.f;
}
void UFPSPlayerBodyComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSPlayerBodyComponent,ReplicatedState);
    DOREPLIFETIME(UFPSPlayerBodyComponent,ReplicatedWeapons);
    DOREPLIFETIME(UFPSPlayerBodyComponent,ReplicatedOutfit);
    DOREPLIFETIME(UFPSPlayerBodyComponent,ReplicatedAppearance);
    DOREPLIFETIME(UFPSPlayerBodyComponent,Reactions);
}
void UFPSPlayerBodyComponent::SetAuthoritativeState(const FFPSBodyState& State)
{
    if(!GetOwner()->HasAuthority())return;
    bExternalAuthorityState=true;ReplicatedState=State;DisplayState=State;
}
void UFPSPlayerBodyComponent::OnRep_BodyState()
{if(Character.IsValid()&&!Character->IsLocallyControlled())DisplayState=ReplicatedState;}
void UFPSPlayerBodyComponent::SetAuthoritativeEquipment(const TArray<FFPSBodyWeapon>& Weapons,const TArray<FFPSBodyOutfitSlot>& Outfit)
{
    if(!GetOwner()->HasAuthority())return;
    ReplicatedWeapons=Weapons;ReplicatedOutfit=Outfit;
    if(GetNetMode()!=NM_DedicatedServer){RebuildWeapons(Weapons);ApplyOutfit(Outfit);}
    GetOwner()->ForceNetUpdate();
}
void UFPSPlayerBodyComponent::OnRep_Equipment()
{if(GetNetMode()!=NM_DedicatedServer&&Character.IsValid()&&!Character->IsLocallyControlled())RebuildWeapons(ReplicatedWeapons);}
void UFPSPlayerBodyComponent::OnRep_Outfit()
{if(GetNetMode()!=NM_DedicatedServer&&Character.IsValid()&&!Character->IsLocallyControlled())ApplyOutfit(ReplicatedOutfit);}
void UFPSPlayerBodyComponent::RefreshEquipment(){bEquipmentDirty=true;bOutfitDirty=true;}

void UFPSPlayerBodyComponent::UpdateOwnerVisibility()
{
    UFPSPerformanceMetricsSubsystem::CountVisibilityUpdate(this);
    FFPSPerformanceScope PerformanceScope(this,TEXT("PlayerBody.OwnerVisibility"));
    if(!Character.IsValid()||!Character->FirstPersonCamera)return;
    // A network pawn can become locally controlled after BeginPlay.
    InitializeFirstPersonLowerBody();
    const bool bThirdPerson=IsThirdPersonViewEnabled();
    UpdateWorldOwnerVisibility(!bThirdPerson);
    // Compress only the owning pistol viewmodel's rendered depth. Sleeves,
    // bare skin, gloves, optics and dual-wield parts must use the same space;
    // scaling a sleeve alone would reverse its depth order against the hand.
    const auto ViewmodelType=Character->IsLocallyControlled()&&Character->IsPistolWeapon()
        ?EFirstPersonPrimitiveType::FirstPerson:EFirstPersonPrimitiveType::None;
    const auto ApplyFirstPersonVisibility=[&](USceneComponent* Child,EFirstPersonPrimitiveType PrimitiveType)
    {
        auto* Primitive=Cast<UPrimitiveComponent>(Child);if(!Primitive)return;
        if(Primitive->FirstPersonPrimitiveType!=PrimitiveType)Primitive->SetFirstPersonPrimitiveType(PrimitiveType);
        // Every setter below marks the primitive's render state dirty and
        // re-registers it in the shadow scene, so only touch what actually
        // changed: this runs again on every camera update and every 0.2 s.
        // The scope owns its recorded hide request until it releases it. Clearing
        // it here every 0.2 s exposes the rifle/arms for a frame during scoped ADS.
        const bool bHideFromOwner=bThirdPerson||Character->ScopeHiddenParts.Contains(Primitive);
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(Primitive,/*bOnlyOwnerSee=*/true,/*bOwnerNoSee=*/bHideFromOwner);
        FPSBodyEquipment::ApplyShadowFlags(Primitive,false);
    };
    TArray<USceneComponent*> Children;Character->FirstPersonCamera->GetChildrenComponents(true,Children);
    for(auto* Child:Children)ApplyFirstPersonVisibility(Child,ViewmodelType);
    if(const auto* Traversal=Character->FindComponentByClass<UFPSTraversalComponent>())
    {
        if(auto* Arms=Traversal->GetFirstPersonArms())
        {
            // Traversal anchors FPS hands in world space, so camera descendants
            // alone miss both these arms and their sleeve/glove followers.
            // Keep their render space unchanged even when a pistol is equipped.
            ApplyFirstPersonVisibility(Arms,EFirstPersonPrimitiveType::None);
            Children.Reset();Arms->GetChildrenComponents(true,Children);
            for(auto* Child:Children)ApplyFirstPersonVisibility(Child,EFirstPersonPrimitiveType::None);
        }
    }
    // Reapply visibility and the remote/hidden-shadow bone-update policy.
    // fps.body.WorldBody 0 overrides all of it: the switch has to be re-applied here
    // because the world equipment copies are rebuilt behind this path.
    ApplyWorldBodyVisibility();
}
void UFPSPlayerBodyComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);if(!Character.IsValid())return;
    UpdateReactions();
    const bool Local=GetNetMode()==NM_Standalone||Character->IsLocallyControlled();
    if(Local&&!bExternalAuthorityState)
    {
        DisplayState=SampleLocalState();
        if(DisplayState.Action!=PreviousAction)
        {
            PreviousAction=DisplayState.Action;UnclockedActionStartedAt=ServerClock();

        }
        if(DisplayState.ActionDuration<=0.f)DisplayState.ActionStartedAt=UnclockedActionStartedAt;
        RefreshCountdown-=Delta;
        if(RefreshCountdown<=0.f||bEquipmentDirty)
        {RefreshCountdown=.2f;CaptureEquipment();bEquipmentDirty=false;}
        CaptureMotion(DisplayState);
        SendBodyPresentation(Delta);
        if(GetOwner()->HasAuthority())ReplicatedState=DisplayState;
    }
    else if(GetOwner()->HasAuthority())
    {
        // 联机：服务端为远端玩家 pawn 组装权威身体态——本地输入路径在服务端不成立，
        // 采样服务端可信事实（CMC 意图位/装备）+ 客户端汇报的离散动作。
        RefreshCountdown-=Delta;
        if(RefreshCountdown<=0.f)
        {
            RefreshCountdown=.1f;
            DisplayState=SampleRemoteAuthorityState();
            ReplicatedState=DisplayState;
        }
        RemoteEquipCountdown-=Delta;
        if(RemoteEquipCountdown<=0.f||bEquipmentDirty)
        {RemoteEquipCountdown=1.f;CaptureEquipment();bEquipmentDirty=false;}
    }
    else DisplayState=ReplicatedState;
    if(!Local)
    {
        DisplayState=ReplicatedState;
        AdvanceBodyPresentation(DisplayState,ServerClock());
        PresentRemoteAzureDragon();
    }
    // Keep weapons stowed through the short return from an interrupted hand pose.
    const float Now=ServerClock();
    if(FPSBodyPoses::Traversing(DisplayState.Motion))WorldWeaponsHiddenUntil=Now+.1f;
    if((DisplayState.bDual||DisplayState.bOffhandPistol)&&DisplayState.Action==EFPSBodyAction::Cast&&DisplayState.Contacts.Channel!=TEXT("StaffCast"))OffhandWeaponHiddenUntil=Now+.1f;
    VisibilityCountdown-=Delta;
    if(VisibilityCountdown<=0.f){VisibilityCountdown=.2f;UpdateOwnerVisibility();}
    UpdateFirstPersonLowerBodyVisibility();
    UpdateWorldWeaponPresentation();
    UpdateBow();
    ApplyMotion(Delta);
    if(BodyAnimation)
    {
        BodyAnimation->BodyState=DisplayState;BodyAnimation->Clock=ServerClock();
        BodyAnimation->Reactions=Reactions;
        const FVector LocalVelocity=Character->GetActorQuat().UnrotateVector(Character->GetVelocity());
        BodyAnimation->Speed=LocalVelocity.Size2D();
        if(BodyAnimation->Speed>3.f)BodyAnimation->Direction=FMath::RadiansToDegrees(FMath::Atan2(LocalVelocity.Y,LocalVelocity.X));
        BodyAnimation->VerticalSpeed=LocalVelocity.Z;BodyAnimation->bFalling=Character->GetCharacterMovement()->IsFalling();
    }
}
