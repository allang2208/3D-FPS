#include "WoodenTorchComponent.h"
#include "FPSImpactFXSubsystem.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "WoodenTorchItem.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Building/VoxelBuildComponent.h"
#include "WoodenTorchArmsComponent.h"
#include "Staff/StaffGripPose.h"
#include "Staff/StaffIlluminationProfile.h"
#include "Staff/StaffWeaponComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

namespace WoodenTorch
{
    const FSoftObjectPath Fire(TEXT("/Game/Weapons/WoodenTorch20261122/WindResponseR10/NS_HearthWrap.NS_HearthWrap"));
    const FSoftObjectPath Volume(TEXT("/Game/Weapons/WoodenTorch20261122/WindResponseR10/SM_HearthFlameVolume.SM_HearthFlameVolume"));
    constexpr float RaiseSeconds = .5f;
    constexpr float BreathSeconds = 2.5f;

    void ApplyCarryMotion(UWoodenTorchArmsComponent& Hand, int32 Side, float Phase, float Weight, float Sprint, float Age)
    {
        // Both hands rise on the same footfall and swing forward on opposite strides.
        const float Mirror = Side == 0 ? 1.f : -1.f;
        const float Lowered = 1.f - FMath::SmoothStep(0.f, RaiseSeconds, Age);
        const float Breath = 1.f - FMath::Cos(2.f * PI * FMath::Max(0.f, Age - RaiseSeconds) / BreathSeconds);
        const FVector Entry = FVector(-5.f, -1.f * Mirror, -43.f) * Lowered
            + FVector(.08f, .05f * Mirror, .13f) * Breath * (1.f - Weight);
        const float Swing = Mirror * FMath::Sin(Phase);
        const float Sway = FMath::Cos(Phase);
        const float Footfall = -FMath::Cos(2.f * Phase);
        const FVector Offset(
            FMath::Lerp(.85f, 2.8f, Sprint) * Swing,
            FMath::Lerp(.48f, .95f, Sprint) * Sway + Mirror * .45f * Sprint,
            FMath::Lerp(.42f, .95f, Sprint) * Footfall - 1.8f * Sprint);
        // A little angular lag lets the head follow the hand around the grip.
        const FRotator Angles(
            Mirror * FMath::Sin(Phase - .30f) * FMath::Lerp(.85f, 2.9f, Sprint) - 2.f * Sprint,
            FMath::Sin(Phase - .18f) * FMath::Lerp(.40f, .95f, Sprint),
            -Sway * FMath::Lerp(.55f, 1.25f, Sprint));
        const FQuat Tilt = (Angles * Weight + FRotator(-15.f * Lowered, 0.f, 0.f)).Quaternion();
        FVector Pivot = StaffGripPose::RestContactInCamera().GetLocation();
        Pivot.Y *= Mirror;
        Hand.SetRelativeLocationAndRotation(Entry + Offset * Weight + Pivot - Tilt.RotateVector(Pivot), Tilt);
    }
}

UWoodenTorchComponent::UWoodenTorchComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UWoodenTorchComponent::RequestAssets()
{
    const bool bLocal = CastChecked<AFPSGAMECharacter>(GetOwner())->IsLocallyControlled();
    if (GetNetMode() == NM_DedicatedServer || (Assets && (!bLocal || bLocalAssetsRequested))) return;
    bLocalAssetsRequested = bLocal;
    TArray<FSoftObjectPath> Paths{WoodenTorch::Fire, WoodenTorch::Volume};
    if (bLocal)
        Paths.Append({FSoftObjectPath(MeshPath), FSoftObjectPath(StaffGripPose::ArmsMeshPath),
            FSoftObjectPath(UStaffWeaponComponent::SwingSoundPath()), FSoftObjectPath(UStaffWeaponComponent::ImpactSoundPath())});
    Assets = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
}

void UWoodenTorchComponent::RefreshEquipment(const UColdSteelStatusModel& Profile,int32 ActiveMainSlot)
{
    const bool bLocal = GetNetMode()!=NM_DedicatedServer && CastChecked<AFPSGAMECharacter>(GetOwner())->IsLocallyControlled();
    if(auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())AddTickPrerequisiteComponent(Staff);
    if(bLocal)if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())Body->AddTickPrerequisiteComponent(this);
    if (bLocal && GetComponentTickInterval()>0.f) SetComponentTickInterval(0.f);
    const auto* Main = Profile.Equipped(ActiveMainSlot);
    const auto* Left = Profile.Equipped(ActiveMainSlot == 6 ? 8 : 11);
    const bool bTool = Profile.ActiveProductionTool() != nullptr;
    bPistolMain = Main && ColdSteelInventory::IsDualPistol(*Main);
    const auto* StrikingTorch = bTool ? nullptr : ColdSteelInventory::QuickTorch(Main, Left);
    const int32 NextHand = StrikingTorch ? (StrikingTorch==Main ? 0 : 1) : INDEX_NONE;
    const bool ChangedMain=Main?Main->InstanceId!=QuickMainInstance:!QuickMainInstance.IsEmpty();
    const bool ChangedLeft=Left?Left->InstanceId!=QuickOffInstance:!QuickOffInstance.IsEmpty();
    if(bLocal&&UsesQuickAttack()&&(QuickHand!=NextHand||ChangedMain||ChangedLeft))
        if(auto* Quick=GetOwner()->FindComponentByClass<UFPSQuickCombatComponent>();Quick&&Quick->GetStyle()==EQuickCombatStyle::TorchStrike&&Quick->IsOccupyingLeftHand())
            Quick->Cancel();
    QuickHand=NextHand;
    if(StrikingTorch&&Main)QuickMainInstance=Main->InstanceId;else QuickMainInstance.Reset();
    if(StrikingTorch&&Left)QuickOffInstance=Left->InstanceId;else QuickOffInstance.Reset();
    for (int32 Side = 0; Side < 2; ++Side)
    {
        const auto* Item = Side ? Left : Main;
        const FString Id = !bTool && Item && ColdSteelInventory::IsWoodenTorch(*Item) ? Item->InstanceId : FString();
        if (Id == Instances[Side] && (!bLocal || Id.IsEmpty() || bLocalAssetsRequested)) continue;
        Instances[Side] = Id;
        if (!bLocal) continue;
        bPresented[Side] = false;
        RaiseAge[Side] = 0.f;
        GaitWeight[Side] = 0.f;
        SetFire(Side,nullptr);
        if (Arms[Side])
        {
            Arms[Side]->SetVisibility(false);
            Props[Side]->SetVisibility(false);
            Arms[Side]->SetComponentTickEnabled(false);
            Arms[Side]->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
        }
        if (!Id.IsEmpty()) RequestAssets();
        SetComponentTickEnabled(true);
    }
}

void UWoodenTorchComponent::SetWorldProp(int32 Side,UStaticMeshComponent* Prop)
{
    if (GetNetMode() == NM_DedicatedServer) return;
    WorldProps[Side] = Prop;
    if (!CastChecked<AFPSGAMECharacter>(GetOwner())->IsLocallyControlled()) SetComponentTickInterval(.12f);
    RequestAssets();
    SetComponentTickEnabled(true);
}

void UWoodenTorchComponent::PrepareHand(int32 Side)
{
    auto* Pawn = CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* Rig = Cast<USkeletalMesh>(FSoftObjectPath(StaffGripPose::ArmsMeshPath).ResolveObject());
    auto* Mesh = Cast<UStaticMesh>(FSoftObjectPath(MeshPath).ResolveObject());
    if (!Rig || !Mesh || !Pawn->FirstPersonCamera) return;
    auto* Hand = NewObject<UWoodenTorchArmsComponent>(Pawn);
    Pawn->AddInstanceComponent(Hand);
    Hand->SetupAttachment(Pawn->FirstPersonCamera);
    Hand->SetOnlyOwnerSee(true);
    Hand->SetCastShadow(false);
    Hand->SetCanEverAffectNavigation(false);
    Hand->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    const FTransform GripInHand = Hand->ConfigureCarry(*Rig, Side);
    Hand->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Hand->SetVisibility(false);
    Hand->RegisterComponent();
    Hand->SetComponentTickEnabled(false);
    Hand->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    auto* Prop = NewObject<UStaticMeshComponent>(Pawn);
    Pawn->AddInstanceComponent(Prop);
    Prop->SetStaticMesh(Mesh);
    Prop->SetupAttachment(Hand, Side ? TEXT("hand_l") : TEXT("hand_r"));
    const FTransform MeshInGrip = Prop->GetSocketTransform(TEXT("Grip"), RTS_Component).Inverse();
    Prop->SetRelativeTransform(MeshInGrip * GripInHand);
    Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prop->SetCanEverAffectNavigation(false);
    Prop->SetOnlyOwnerSee(true);
    Prop->SetCastShadow(false);
    Prop->SetVisibility(false);
    Prop->RegisterComponent();
    Arms[Side] = Hand;
    Props[Side] = Prop;
}

USkeletalMeshComponent* UWoodenTorchComponent::HandForMotion(int32 Side) const
{
    if(!bPresented[Side])return nullptr;
    const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
    return Staff&&Staff->PrimaryTorchHand()==Side?Staff->ArmsMesh():Arms[Side].Get();
}

UStaticMeshComponent* UWoodenTorchComponent::ReadyPairedOffhand() const
{
    const float DrawTime = WoodenTorch::RaiseSeconds + (HoldsRight() ? .07f : 0.f);
    return HoldsLeft() && bPresented[1] && RaiseAge[1] >= DrawTime ? Props[1].Get() : nullptr;
}

bool UWoodenTorchComponent::ShowsLeft(const USceneComponent* Except) const
{
    auto* Hand=HandForMotion(1);
    return Hand&&Hand!=Except;
}

void UWoodenTorchComponent::SetFire(int32 Side,UStaticMeshComponent* Parent,bool bInHand)
{
    if (!Parent)
    {
        HandAir[Side] = {};
        NextShedAt[Side]=0.;
        if (IsValid(Flames[Side]))
        {
            if (Flames[Side]->IsActive()) Flames[Side]->DeactivateImmediate();
            if (Flames[Side]->GetAttachParent()) Flames[Side]->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        }
        if (FlameVolumes[Side] && FlameVolumes[Side]->IsVisible()) FlameVolumes[Side]->SetVisibility(false);
        if (Lights[Side] && Lights[Side]->IsVisible()) Lights[Side]->SetVisibility(false);
        return;
    }
    if (!IsValid(Flames[Side]))
    {
        auto* System = Cast<UNiagaraSystem>(WoodenTorch::Fire.ResolveObject());
        auto* VolumeMesh = Cast<UStaticMesh>(WoodenTorch::Volume.ResolveObject());
        if (!System || !VolumeMesh) return;
        auto* Flame = NewObject<UNiagaraComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Flame);
        Flame->SetAutoActivate(false);
        Flame->SetAsset(System);
        Flame->SetCastShadow(false);
        Flame->SetCanEverAffectNavigation(false);
        Flame->SetupAttachment(Parent,TEXT("Flame"));
        // The fuel and all effect layers share this unscaled socket frame.
        Flame->SetAbsolute(false,false,true);
        Flame->RegisterComponent();
        Flames[Side] = Flame;
        LastSlope[Side] = FVector2D::ZeroVector;
        // Close up, the volume supplies the whole flame. Fire is the inexpensive distant replacement.
        Flame->SetEmitterEnable(TEXT("Fire"), false);
        Flame->SetEmitterEnable(TEXT("Sparks"), false); // shed in world space at the moving cloth head
        auto* Volume = NewObject<UStaticMeshComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Volume);
        Volume->SetupAttachment(Flame);
        Volume->SetStaticMesh(VolumeMesh);
        Volume->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Volume->SetGenerateOverlapEvents(false);
        Volume->SetCastShadow(false);
        Volume->SetReceivesDecals(false);
        Volume->SetVisibleInRayTracing(false);
        Volume->SetCanEverAffectNavigation(false);
        Volume->SetCustomPrimitiveDataFloat(0, FMath::Fmod(float(GetOwner()->GetUniqueID() % 1024) * .71f + Side * 2.37f, 17.f));
        Volume->SetVisibility(false);
        Volume->RegisterComponent();
        FlameVolumes[Side] = Volume;
        bFullFire[Side] = true;
        NextViewAt[Side] = 0.;
        auto* Glow = NewObject<UPointLightComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Glow);
        Glow->SetupAttachment(Flame);
        Glow->SetRelativeLocation(FVector(0.f,0.f,23.f));
        Glow->SetMobility(EComponentMobility::Movable);
        Glow->SetCastShadows(false);
        Glow->SetIntensityUnits(ELightUnits::Lumens);
        Glow->SetIntensity(130.f);
        Glow->SetLightColor(FLinearColor(1.f,.51f,.21f));
        Glow->SetAttenuationRadius(UStaffIlluminationProfile::RadiusCm);
        Glow->SetSourceRadius(6.5f);
        Glow->SetSpecularScale(.22f);
        Glow->SetVolumetricScatteringIntensity(.08f);
        Glow->SetMaxDrawDistance(3600.f);
        Glow->RegisterComponent();
        Lights[Side] = Glow;
    }
    if (Flames[Side]->GetAttachParent() != Parent)
    {
        Flames[Side]->AttachToComponent(Parent,FAttachmentTransformRules::SnapToTargetNotIncludingScale,TEXT("Flame"));
    }
    auto* Flame = Flames[Side].Get();
    auto* World = GetWorld();
    if (bInHand || World->GetTimeSeconds() >= NextViewAt[Side])
    {
        NextViewAt[Side] = World->GetTimeSeconds() + .10;
        auto* Views = bInHand ? nullptr : World->GetSubsystem<UFluidPresentationSubsystem>();
        // Smoke and embers are intermittent. A visible fire volume keeps the full-detail tier alive.
        const bool bVolumeOnScreen = Views && bFullFire[Side] && FlameVolumes[Side]->IsVisible()
            && World->GetTimeSeconds() - FlameVolumes[Side]->GetLastRenderTimeOnScreen() < .25;
        const auto Detail = Views ? Views->FireViews.Classify(*World, Flame->GetComponentLocation(), 65.f, 12.f,
            1500.f, 3600.f, bVolumeOnScreen ? nullptr : Flame, bFullFire[Side]) : EFireParticleDetail::Full;
        bFlameInView[Side] = Detail != EFireParticleDetail::Off;
        if (bFlameInView[Side] && bFullFire[Side] != (Detail == EFireParticleDetail::Full))
        {
            bFullFire[Side] = Detail == EFireParticleDetail::Full;
            Flame->SetEmitterEnable(TEXT("Fire"),!bFullFire[Side]);
            Flame->SetEmitterEnable(TEXT("Smoke"),bFullFire[Side]);

        }
    }
    const bool bShowVolume = bFlameInView[Side] && bFullFire[Side];
    if (FlameVolumes[Side]->IsVisible() != bShowVolume) FlameVolumes[Side]->SetVisibility(bShowVolume);
    if (bFlameInView[Side] && !Flame->IsActive()) Flame->Activate();
    else if (!bFlameInView[Side] && Flame->IsActive()) Flame->DeactivateImmediate();
    if (!Lights[Side]->IsVisible()) Lights[Side]->SetVisibility(true);
}

void UWoodenTorchComponent::UpdateFlameWind(float DeltaSeconds)
{
    // Sample the existing sheltered, gusting wind field once for both hands.
    // Filter in world space so changing view direction preserves the airflow heading.
    bool bUpdatedFlow = false;
    const auto* Pawn = CastChecked<AFPSGAMECharacter>(GetOwner());
    for (int32 Side = 0; Side < 2; ++Side)
    {
        auto* Flame = Flames[Side].Get();
        auto& Hand = HandAir[Side];
        auto* Mount = Flame ? Cast<UStaticMeshComponent>(Flame->GetAttachParent()) : nullptr;
        if (!Mount || !bFlameInView[Side])
        {
            Hand = {};
            continue;
        }
        if (!bUpdatedFlow)
        {
            auto* World = GetWorld();
            const double Now = World->GetTimeSeconds();
            if (Now >= NextWindSampleAt)
            {
                auto* Fluid = World->GetSubsystem<UFluidPresentationSubsystem>();
                AmbientWind = Fluid ? Fluid->WindWithGustAt(Flame->GetComponentLocation()) : FVector::ZeroVector;
                NextWindSampleAt = Now + .18;
            }
            FVector RelativeAir = AmbientWind - GetOwner()->GetVelocity();
            RelativeAir.Z = 0.;
            // 450 cm/s walking and 700 cm/s sprinting give ~28 and ~40 degrees in still air.
            const FVector Target = (RelativeAir / 840.).GetClampedToMaxSize(.95);
            AirLeanWorld = FMath::Lerp(AirLeanWorld, Target, 1. - FMath::Exp(-double(DeltaSeconds) / .14));
            bUpdatedFlow = true;
        }
        // Remove camera and pawn motion before measuring this hand. Locomotion already contributes above.
        const FTransform Basis = Mount->bOnlyOwnerSee && Pawn->FirstPersonCamera
            ? Pawn->FirstPersonCamera->GetComponentTransform() : Pawn->GetActorTransform();
        const FVector Tip = Basis.InverseTransformPositionNoScale(Flame->GetComponentLocation());
        const FVector Step = Tip - Hand.PreviousTip;
        if (Hand.Mount.Get() == Mount && DeltaSeconds > UE_SMALL_NUMBER && DeltaSeconds < .25f &&
            Step.SizeSquared() < FMath::Square(40. + 1750. * DeltaSeconds))
        {
            const FVector Velocity = Basis.TransformVectorNoScale(Step) / DeltaSeconds;
            const double Speed = Velocity.Size();
            const FVector Drag = -Velocity.GetSafeNormal() * FMath::Clamp((Speed - 12.) / 480., 0., .98);
            const double Response = Drag.SizeSquared() > Hand.DragWorld.SizeSquared() ? .045 : .12;
            Hand.DragWorld = FMath::Lerp(Hand.DragWorld, Drag, 1. - FMath::Exp(-DeltaSeconds / Response));
        }
        else Hand.DragWorld = FVector::ZeroVector;
        Hand.Mount = Mount;
        Hand.PreviousTip = Tip;
        const FQuat Frame = Flame->GetComponentQuat();
        const FVector Up = Frame.UnrotateVector(FVector::UpVector);
        const FVector Air = Frame.UnrotateVector(AirLeanWorld + Hand.DragWorld);
        const double Vertical = FMath::Max(Up.Z, .60);
        // Retain R9 buoyancy on a tilted shaft. Only the part of the plume above the cloth bends.
        const FVector2D Buoyancy(FMath::Clamp(Up.X / Vertical, -.58, .58) * .84,
                                 FMath::Clamp(Up.Y / Vertical, -.58, .58) * .84);
        FVector2D Slope = (Buoyancy + FVector2D(Air.X, Air.Y)) / FMath::Max(.65, 1. + Air.Z);
        Slope = Slope.GetClampedToMaxSize(.98);
        const double Now=GetWorld()->GetTimeSeconds();
        if(bFullFire[Side]&&Now>=NextShedAt[Side])
        {
            if(NextShedAt[Side]>0.)
            {
                auto* View=LocalEmberCamera();
                const FVector Crown=Flame->GetComponentTransform().TransformPositionNoScale(FVector(Slope.X*9.,Slope.Y*9.,9.));
                // Detached coals follow world wind. The short wake comes from this hand's swing.
                if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
                    FX->ShedTorchEmbers(Crown,AmbientWind*.42+Hand.DragWorld*47.,View);
            }
            NextShedAt[Side]=Now+FMath::FRandRange(.14f,.44f);
        }
        if (Slope.Equals(LastSlope[Side], .0025)) continue;
        LastSlope[Side] = Slope;
        FlameVolumes[Side]->SetCustomPrimitiveDataVector2(1, Slope);
        Flame->SetVariableVec3(TEXT("User.PlumeSlope"), FVector(Slope.X, Slope.Y, 0.));
        // The lamp follows the luminous core partway, keeping most light near the burning cloth.
        Lights[Side]->SetRelativeLocation(FVector(9. * Slope.X, 9. * Slope.Y, 23.));
    }
    if (!bUpdatedFlow)
    {
        NextWindSampleAt = 0.;
        AirLeanWorld = FVector::ZeroVector;
    }
}

void UWoodenTorchComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Pawn = CastChecked<AFPSGAMECharacter>(GetOwner());
    const auto* Body = Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Potion = Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const auto* Door = Pawn->FindComponentByClass<UFPSDoorPushComponent>();
    const auto* Controller = Cast<APlayerController>(Pawn->GetController());
    const auto* Build = Controller ? Controller->FindComponentByClass<UVoxelBuildComponent>() : nullptr;
    const bool bLocal = Pawn->IsLocallyControlled();
    const bool bFirstPerson = bLocal && !(Body && Body->IsThirdPersonViewEnabled());
    const bool bCanHold = !(Health && Health->IsDead()) && !Pawn->IsTraversing() &&
        !(Build && Build->IsBuilding() && !Build->IsPanelOpen());
    const bool bRunning = bLocal && bCanHold && Pawn->IsSprinting() && !Pawn->bIsCrouched;
    SprintBlend = FMath::Lerp(SprintBlend, bRunning ? 1.f : 0.f, 1.f - FMath::Exp(-8.f * Delta));
    const float GaitFollow = 1.f - FMath::Exp(-16.f * Delta);
    const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
    bool bNeeded = false;
    for (int32 Side = 0; Side < 2; ++Side)
    {
        const bool bHeld = bLocal && !Instances[Side].IsEmpty();
        bNeeded |= bHeld || WorldProps[Side].IsValid();
        if(bHeld&&Staff&&Staff->PrimaryTorchHand()==Side)
        {
            auto* Held=Staff->AssemblyRoot();
            auto* Rig=Staff->ArmsMesh();
            const bool HideLeft=Side==1&&((Door&&Door->IsActive())||(Potion&&Potion->IsOffhandWeaponHidden()));
            const bool HiddenForMeal=Potion&&Potion->IsTwoHanded()&&Potion->IsOffhandWeaponHidden();
            const bool Show=bCanHold&&!HideLeft&&!HiddenForMeal;
            bPresented[Side]=Rig&&Held&&Held->IsVisible()&&Rig->IsVisible()&&Show;
            if(Held)Held->SetHiddenInGame(!bFirstPerson||!Show);
            if(Rig)Rig->SetHiddenInGame(!bFirstPerson||!bCanHold||HiddenForMeal);
            if(Arms[Side]&&Arms[Side]->IsVisible())Arms[Side]->SetVisibility(false);
            if(Props[Side]&&Props[Side]->IsVisible())Props[Side]->SetVisibility(false);
            auto* WorldProp=WorldProps[Side].Get();
            auto* Visible=bFirstPerson?(bPresented[Side]?Held:nullptr):
                (WorldProp&&WorldProp->IsVisible()&&!WorldProp->bHiddenInGame&&Show?WorldProp:nullptr);
            SetFire(Side,Visible,bFirstPerson);
            continue;
        }
        if (bHeld && !Arms[Side] && Assets && Assets->HasLoadCompleted()) PrepareHand(Side);
        auto* Hand = Arms[Side].Get();
        const bool bDoor = Side && Door && Door->IsActive();
        const bool bPotion = Side && Potion && Potion->IsOffhandWeaponHidden();
        const bool bSupport = Side && (Pawn->IsReloading() || Pawn->GetOffhandReloadPhase()==EOffhandReloadPhase::Reload ||
            Pawn->IsOffhandReloadArmExiting() || Pawn->GetWeaponState() == EAKMWeaponState::Inspecting);
        const bool bYield = bSupport || (bDoor && !Door->UsesHandMesh(Hand)) || (bPotion && !Potion->UsesHandMesh(Hand));
        const bool bPose = bHeld && bCanHold && !bYield && Hand;
        const bool bDrawProp = bPose && !bDoor && !bPotion;
        const bool bWasPresented = bPresented[Side];
        bPresented[Side] = bPose;
        if (Hand && Hand->IsVisible() != (bFirstPerson && bPose)) Hand->SetVisibility(bFirstPerson && bPose);
        if (Props[Side] && Props[Side]->IsVisible() != (bFirstPerson && bDrawProp))
            Props[Side]->SetVisibility(bFirstPerson && bDrawProp);
        if (bPose)
        {
            if (!bWasPresented)
            {
                if (!Pawn->IsOffhandReloadActive() && !(Potion && Potion->IsStowingOffhand())) RaiseAge[Side] = 0.f;
                GaitWeight[Side] = 0.f;
                Hand->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
            }
            const float Delay = Side && !Instances[0].IsEmpty() ? .07f : 0.f;
            RaiseAge[Side] += Delta;
            if (RaiseAge[Side] >= Delay + WoodenTorch::RaiseSeconds + WoodenTorch::BreathSeconds)
                RaiseAge[Side] = Delay + WoodenTorch::RaiseSeconds + FMath::Fmod(RaiseAge[Side]-Delay-WoodenTorch::RaiseSeconds,WoodenTorch::BreathSeconds);
            const float PoseTime = FMath::Max(0.f, RaiseAge[Side] - Delay);
            // The character samples the footstep distance clock for every loadout, including unarmed.
            const float Target = Pawn->GroundLocomotionWeight * (Pawn->bIsCrouched ? .65f : 1.f)
                * FMath::SmoothStep(.18f, WoodenTorch::RaiseSeconds, PoseTime);
            GaitWeight[Side] = bDrawProp ? FMath::Lerp(GaitWeight[Side], Target, GaitFollow) : 0.f;
            WoodenTorch::ApplyCarryMotion(*Hand, Side, Pawn->M4SprintPhase, GaitWeight[Side], SprintBlend, PoseTime);
            if (Side && bDrawProp)
            {
                const float UseLower = Potion && Potion->IsStowingOffhand() && !Potion->IsTwoHanded() ? Potion->OffhandLowerWeight() : 0.f;
                const float Lower = FMath::Max(UseLower, Pawn->GetOffhandReloadLowerWeight());
                if (Lower > 0.f) Hand->AddRelativeLocation(FVector(-10., -3., -58.) * Lower);
            }
            Hand->TickAnimation(0.f,false);
            Hand->RefreshBoneTransforms();
        }
        auto* WorldProp = WorldProps[Side].Get();
        auto* Visible = bFirstPerson ? (bDrawProp ? Props[Side].Get() : nullptr) :
            (WorldProp && WorldProp->IsVisible() && !WorldProp->bHiddenInGame && bCanHold && !bDoor && !bPotion && !bSupport ? WorldProp : nullptr);
        SetFire(Side,Visible,bFirstPerson);
    }
    UpdateFlameWind(Delta);
    if (!bNeeded) SetComponentTickEnabled(false);
}

void UWoodenTorchComponent::EndPlay(EEndPlayReason::Type Reason)
{
    for (int32 I=0; I<2; ++I)
    {
        if (FlameVolumes[I]) FlameVolumes[I]->DestroyComponent();
        if (Flames[I]) Flames[I]->DestroyComponent();
        if (Lights[I]) Lights[I]->DestroyComponent();
        if (Props[I]) Props[I]->DestroyComponent();
        if (Arms[I]) Arms[I]->DestroyComponent();
    }
    Assets.Reset();
    Super::EndPlay(Reason);
}
