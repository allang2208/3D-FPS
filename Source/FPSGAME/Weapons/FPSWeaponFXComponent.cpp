#include "FPSWeaponFXComponent.h"
#include "FPSImpactFXSubsystem.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "AKMSovietCalibration.h"
#include "A762WeaponAssets.h"
#include "PKMLowpolyWeaponAssets.h"
#include "ASH12WeaponAssets.h"
#include "../FPSGAMECharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"
#include "HAL/IConsoleManager.h"

namespace WeaponFX
{
    enum : uint8 { FlashCore, FlashTongue, Smoke, Spark, Casing, Dust };
    const FLinearColor Flame(1.0f, 0.42f, 0.075f);
    const FLinearColor HotCore(1.0f, 0.76f, 0.27f);
    constexpr double SmokePeriod = 0.16;
    constexpr float SmokeMaxLifetime = 1.25f;
    constexpr float HeatThreshold = 0.10f;
    constexpr float HeatCoolingRate = 0.28f;
    constexpr float SmokeDrag = 1.3f;
    constexpr float StreamMaxLifetime = 1.30f;
    // Tracer streaks (see Docs/Weapons/tracer-upgrade-plan-20260921.md).
    // The visible dash is clamped to a per-class window instead of "one frame of
    // travel", which used to make it frame-rate dependent and full of gaps.
    // Gap-free criterion: the per-frame step (speed * 100 / fps cm) must stay below the
    // max length, otherwise the path turns into dots. At 350 m/s that is 1167 cm at 30 fps,
    // 583 cm at 60 fps and 243 cm at 144 fps, so the rifle window covers every rate; the
    // dash still reads as a beam sweeping past instead of a pellet (Docs/Weapons/
    // ballistic-feel-options-20260921.md).
    constexpr float TracerRifleLengthCM = 800.f;
    constexpr float TracerRifleMaxCM = 1800.f;
    constexpr float TracerPistolLengthCM = 400.f;
    constexpr float TracerPistolMaxCM = 1300.f;  // 30 fps 下 420 m/s 手枪仍差 100 cm 覆盖
    constexpr float TracerMinDiameterCM = 1.6f;
    // World-space caps: they only bind far away (screen width is constant), where the old
    // 5 cm cap crushed a 60 m streak down to under one pixel.
    constexpr float TracerDiameterMaxCM = 28.f;
    constexpr float TracerScopedDiameterMaxCM = 12.f;
    // Emission multiplies an additive colour and the shader pushes the core towards white,
    // so a high value clipped every channel and read as pale: 7.5 is why the streak was not
    // vivid. Lower emission with a saturated tint keeps red high and green/blue low.
    constexpr float TracerEmission = 2.6f;
    constexpr FLinearColor TracerTint = FLinearColor(1.f,.30f,.03f);
    constexpr float TracerFlashSeconds = 0.05f; // 瞬时段（无弹丸飞行）只做短暂淡出
}

// Optic firing presentation (LPVO 1-6x only). At high magnification the world
// muzzle flash leaves the narrow frustum almost completely, so the world layer is
// compensated with a damped, capped factor and a small forward offset instead of
// being made brighter. Presentation only: the muzzle socket, the shot direction
// and the trace are untouched.
static TAutoConsoleVariable<float> ScopeWorldScaleExponent(TEXT("fps.Scope.WorldScaleExponent"),0.f,
    TEXT("Damped magnification exponent for the world muzzle flash (0 = off)."));
static TAutoConsoleVariable<float> ScopeWorldScaleMax(TEXT("fps.Scope.WorldScaleMax"),2.5f,
    TEXT("Hard cap for the world muzzle flash compensation."));
static TAutoConsoleVariable<float> ScopeWorldForwardCM(TEXT("fps.Scope.WorldForwardCM"),12.f,
    TEXT("Centimetres to push the world flash along the barrel at full compensation."));

static TAutoConsoleVariable<float> SmokeIntensity(TEXT("fps.Smoke.Intensity"),1.f,
    TEXT("Muzzle smoke opacity multiplier for shot, continuous plume and heat tail (0-2)."));

// Tracer presentation knob (Docs/Weapons/ballistic-feel-options-20260921.md). Presentation
// only: the trace, the damage and the falloff are untouched.
static TAutoConsoleVariable<float> TracerLengthScale(TEXT("fps.Tracer.LengthScale"),1.f,
    TEXT("Multiplier on the tracer streak window (1 = built-in 600/1400 cm rifle window)."));
// Fast rounds cross a room in a few frames, so a streak that vanishes the instant the round
// lands is hard to see at all. It now holds its last position and fades out instead.
static TAutoConsoleVariable<float> TracerLingerSeconds(TEXT("fps.Tracer.LingerSeconds"),.12f,
    TEXT("Seconds a finished tracer streak stays visible and fades out (0 = vanish at once)."));
// Width and colour are the two knobs behind "too thin / not vivid"; both apply live, including
// to streaks already in flight (ApplyTracerTransform re-applies them every frame).
static TAutoConsoleVariable<float> TracerWidthPixels(TEXT("fps.Tracer.PixelWidth"),4.f,
    TEXT("Tracer screen width in pixels at 1080p reference (higher = thicker beam)."));
static TAutoConsoleVariable<float> TracerEmissionScale(TEXT("fps.Tracer.Emission"),2.6f,
    TEXT("Additive emission of the tracer. Very high values clip every channel and read white."));
static TAutoConsoleVariable<FString> TracerTintSetting(TEXT("fps.Tracer.Tint"),TEXT("1.0,0.30,0.03"),
    TEXT("Tracer colour as R,G,B (linear, 0-1). Saturated red/orange stays vivid at low emission."));
static bool ParseTracerTint(const FString& Text,FLinearColor& Out)
{
    TArray<FString> Parts;Text.ParseIntoArray(Parts,TEXT(","),true);
    if(Parts.Num()<3)return false;
    Out=FLinearColor(FCString::Atof(*Parts[0]),FCString::Atof(*Parts[1]),FCString::Atof(*Parts[2]),1.f);
    return true;
}
// "Strengthen the streak" tier: a wider dim halo pass around the core, and a real light that
// travels with the newest rounds so the beam spills onto the world around it.
static TAutoConsoleVariable<float> TracerHaloWidth(TEXT("fps.Tracer.HaloWidth"),2.8f,
    TEXT("Width multiplier of the soft halo pass around the core (<=1 hides it)."));
static TAutoConsoleVariable<float> TracerHaloEmission(TEXT("fps.Tracer.HaloEmission"),.55f,
    TEXT("Additive emission of the halo pass; keep well below fps.Tracer.Emission."));
static TAutoConsoleVariable<float> TracerLightLumens(TEXT("fps.Tracer.LightLumens"),220.f,
    TEXT("Lumens of the travelling tracer light; 0 disables world lighting."));
static TAutoConsoleVariable<float> TracerLightRadiusCM(TEXT("fps.Tracer.LightRadiusCM"),220.f,
    TEXT("Attenuation radius of the travelling tracer light in centimetres."));

UFPSWeaponFXComponent::UFPSWeaponFXComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    SetIsReplicatedByDefault(false);
    // Default object references retain the owned materials/geometry for cooking.
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Card(TEXT("/Engine/BasicShapes/Plane.Plane"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Flash(TEXT("/Game/Weapons/GunplayFX/M_GunFlash_Exposure.M_GunFlash_Exposure"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Smoke(TEXT("/Game/Weapons/GunplayFX/M_GunSmoke.M_GunSmoke"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Brass(TEXT("/Game/Weapons/GunplayFX/M_CasingBrass.M_CasingBrass"));
    CardMesh = Card.Object;
    CylinderMesh = Cylinder.Object;
    FlashMaterial = Flash.Object;
    SmokeMaterial = Smoke.Object;
    BrassMaterial = Brass.Object;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> RifleShell(TEXT("/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/Meshes/SM_BulletShell.SM_BulletShell"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> RifleShellSurface(TEXT("/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/Meshes/MI_BulletShell_FX.MI_BulletShell_FX"));
    RifleCasingMesh = RifleShell.Object;
    RifleCasingMaterial = RifleShellSurface.Object;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Tracer(TEXT("/Game/Weapons/GunplayFX/M_BallisticTracerVisibleV13.M_BallisticTracerVisibleV13"));
    TracerMaterial = Tracer.Object;
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EpicMuzzle(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10.NS_FPS_MuzzleFlashV10"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EpicSmoke(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV15.NS_FPS_MuzzleSmokeStreamV15"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> SmokeImpulse(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15.NS_FPS_MuzzleSmokeShotV15"));
    EpicMuzzleSystem=EpicMuzzle.Object;EpicSmokeSystem=EpicSmoke.Object;
    SmokeImpulseSystem=SmokeImpulse.Object;
}

void UFPSWeaponFXComponent::Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera)
{
    if (WeaponMesh) RemoveTickPrerequisiteComponent(WeaponMesh);
    StopEmission();
    for (FFPSWeaponFXParticle& P : Particles) Release(P);
    for (FFPSWeaponFXTracer& T : Tracers) ReleaseTracer(T);
    WeaponMesh = InWeaponMesh;
    Camera = InCamera;
    bReady = false;
    if (!GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer || !WeaponMesh || !Camera) return;
    AddTickPrerequisiteComponent(WeaponMesh);
    bReady = CardMesh && CylinderMesh && FlashMaterial && SmokeMaterial && BrassMaterial
        && WeaponMesh->DoesSocketExist(MuzzleSocket) && WeaponMesh->DoesSocketExist(EjectSocket);
    if (!bReady)
    {
        UE_LOG(LogTemp, Error, TEXT("GUNPLAY_FX_NOT_READY materials=%d muzzle=%d eject=%d. Run Tools/AssetPipeline/build_gunplay_fx.py."),
            !!(FlashMaterial && SmokeMaterial && BrassMaterial), WeaponMesh->DoesSocketExist(MuzzleSocket), WeaponMesh->DoesSocketExist(EjectSocket));
        return;
    }
    if (!FlashLight)
    {
        FlashLight = NewObject<UPointLightComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(FlashLight);
        FlashLight->SetMobility(EComponentMobility::Movable);
        FlashLight->SetCastShadows(false);
        FlashLight->SetIntensityUnits(ELightUnits::Lumens);
        FlashLight->SetAttenuationRadius(125.0f);
        FlashLight->SetSourceRadius(3.0f);
        FlashLight->SetSoftSourceRadius(5.0f);
        FlashLight->SetSpecularScale(0.35f);
        FlashLight->SetVolumetricScatteringIntensity(0.0f);
        FlashLight->SetIndirectLightingIntensity(0.0f);
        FlashLight->SetLightColor(FLinearColor(1.0f, 0.56f, 0.20f));
        FlashLight->SetVisibility(false);
        FlashLight->RegisterComponent();
    }
    Particles.Reserve(MaxParticles);
    const auto& Ref = WeaponMesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    auto Bone = [&](const TCHAR* Name)
    {
        FTransform Transform = FTransform::Identity;
        for (int32 Index = Ref.FindBoneIndex(Name); Index != INDEX_NONE; Index = Ref.GetParentIndex(Index))
            Transform = Transform * Ref.GetRefBonePose()[Index];
        return Transform;
    };
    const FTransform Root = Bone(TEXT("WPN_root"));
    const FTransform Rear = Bone(TEXT("WPN_RearSight"));
    const FVector Forward = (Bone(TEXT("WPN_FrontSight")).GetLocation() - Rear.GetLocation()).GetSafeNormal();
    // Use the same authored rail normal as the rifle's gunsmith attachments.
    const FVector Up = ((AKMSoviet::Matches(WeaponMesh) || A762WeaponAssets::Matches(WeaponMesh)) ? Root : Rear).GetRotation().GetAxisZ();
    CasingFrameInRoot = Root.GetRotation().Inverse() * FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat();
    PreviousMuzzlePosition = MuzzleLocation();
    PreviousMuzzleForward = MuzzleForward();
    UE_LOG(LogTemp, Display, TEXT("GUNPLAY_FX_READY muzzle=%s eject=%s max_particles=%d"), *MuzzleSocket.ToString(), *EjectSocket.ToString(), MaxParticles);
}

void UFPSWeaponFXComponent::SetIndependentPistol(bool Revolver,bool Suppressed,USceneComponent* Exit)
{
    bIndependentPistol=true;bIndependentRevolver=Revolver;IndependentSuppressed=Suppressed;
    IndependentExit=Exit;bUseCharacterMuzzle=false;
}
FVector UFPSWeaponFXComponent::MuzzleLocation() const
{
    if(IsValid(IndependentExit))return IndependentExit->GetComponentLocation();
    if(bUseCharacterMuzzle)if(const auto* C=Cast<AFPSGAMECharacter>(GetOwner()))return C->GetEffectiveMuzzleLocation();
    return WeaponMesh->GetSocketLocation(MuzzleSocket);
}

FVector UFPSWeaponFXComponent::MuzzleForward() const
{
    if(IsValid(IndependentExit))return IndependentExit->GetForwardVector();
    if(bUseCharacterMuzzle)if(const auto* C=Cast<AFPSGAMECharacter>(GetOwner()))return C->GetEffectiveMuzzleForward();
    if(bIndependentPistol)return (WeaponMesh->GetSocketLocation(TEXT("WPN_FrontSight"))-WeaponMesh->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    // Imported WPN local Y lies along the bore; mirrored source rigs need a sign correction.
    FVector Forward = WeaponMesh->GetSocketQuaternion(MuzzleSocket).GetAxisY();
    if (FVector::DotProduct(Forward, Camera->GetForwardVector()) < 0.0f) Forward *= -1.0f;
    return Forward.GetSafeNormal();
}

FFPSWeaponFXParticle* UFPSWeaponFXComponent::Acquire(uint8 Kind, UStaticMesh* Geometry, UMaterialInterface* BaseMaterial)
{
    FFPSWeaponFXParticle* Result = Particles.FindByPredicate([](const FFPSWeaponFXParticle& P) { return !P.bActive; });
    if (!Result)
    {
        if (Particles.Num() >= MaxParticles) return nullptr;
        Result = &Particles.AddDefaulted_GetRef();
        Result->Mesh = NewObject<UStaticMeshComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Result->Mesh);
        Result->Mesh->SetMobility(EComponentMobility::Movable);
        Result->Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Result->Mesh->SetGenerateOverlapEvents(false);
        Result->Mesh->SetCastShadow(false);
        Result->Mesh->bReceivesDecals = false;
        Result->Mesh->SetCanEverAffectNavigation(false);
        Result->Mesh->RegisterComponent();
    }
    Result->Mesh->SetStaticMesh(Geometry);
    if (!Result->Material || Result->Material->Parent != BaseMaterial)
        Result->Material = UMaterialInstanceDynamic::Create(BaseMaterial, Result->Mesh);
    Result->Mesh->SetMaterial(0, Result->Material);
    Result->Mesh->SetVisibility(true);
    Result->Material->SetScalarParameterValue(TEXT("Opacity"), 1.0f);
    Result->Material->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.0f, 50.0f));
    if (Kind != WeaponFX::Casing)
    {
        Result->Material->SetVectorParameterValue(TEXT("Tint"), WeaponFX::Flame);
        Result->Material->SetScalarParameterValue(TEXT("Emission"), 3.0f);
    }
    Result->Position = FVector::ZeroVector;
    Result->Velocity = FVector::ZeroVector;
    Result->Acceleration = FVector::ZeroVector;
    Result->Rotation = FRotator::ZeroRotator;
    Result->Spin = FRotator::ZeroRotator;
    Result->Size = FVector::OneVector;
    Result->Age = 0.0f;
    Result->BirthFrame = GFrameCounter;
    Result->Lifetime = 1.0f;
    Result->Opacity = 1.0f;
    Result->ForwardOffset = 0.0f;
    Result->Kind = Kind;
    Result->bActive = true;
    Result->bBounced = false;
    SetComponentTickEnabled(true);
    return Result;
}

void UFPSWeaponFXComponent::Release(FFPSWeaponFXParticle& P)
{
    P.bActive = false;
    if (P.Mesh) P.Mesh->SetVisibility(false);
}

void UFPSWeaponFXComponent::OnTracerSegment(const FVector& Start,const FVector& End)
{
    if(!bReady||!TracerMaterial)return;
    const FVector Travel=End-Start;
    const float Distance=static_cast<float>(Travel.Size());
    if(Distance<.1f)return;
    auto* T=AcquireTracer(INDEX_NONE);
    if(!T)return;
    ++TracerSegments;LastTracerEnd=End;
    // Instantaneous path (no flying round): a short dash at the impact end that fades
    // over TracerFlashSeconds instead of vanishing inside a single frame.
    T->bFlash=true;T->FlashAge=0.f;
    T->Direction=Travel/Distance;
    T->Length=FMath::Min(FMath::Clamp(Distance,TracerBaseLengthCM(),TracerMaxLengthCM()),Distance);
    T->Head=End;
    T->TraveledCM=Distance;
    T->LastUpdateFrame=GFrameCounter;
    ApplyTracerTransform(*T);
}

void UFPSWeaponFXComponent::OnTracerSegment(int32 RoundId,const FVector& Start,const FVector& End)
{
    if(!bReady||!TracerMaterial)return;
    const FVector Travel=End-Start;
    const float Distance=static_cast<float>(Travel.Size());
    if(Distance<.1f)return;
    auto* T=AcquireTracer(RoundId);
    if(!T)return;
    ++TracerSegments;LastTracerEnd=End;
    T->bFlash=false;T->FlashAge=0.f;T->LingerAge=0.f;
    T->RoundId=RoundId;
    T->Direction=Travel/Distance;
    T->Head=End;
    T->TraveledCM+=Distance;
    // The dash trails the round by its class length and is never shorter than this
    // frame's travel, so consecutive frames overlap at any frame rate (no dotted path).
    // It also may not reach behind the muzzle: the streak grows out of the barrel.
    T->Length=FMath::Min(FMath::Clamp(Distance,TracerBaseLengthCM(),TracerMaxLengthCM()),T->TraveledCM);
    T->LastUpdateFrame=GFrameCounter;
    ApplyTracerTransform(*T);
}

FFPSWeaponFXTracer* UFPSWeaponFXComponent::AcquireTracer(int32 RoundId)
{
    if(RoundId!=INDEX_NONE)
        for(FFPSWeaponFXTracer& T:Tracers)
            if(T.bActive&&!T.bFlash&&T.RoundId==RoundId)return &T;
    FFPSWeaponFXTracer* Result=Tracers.FindByPredicate([](const FFPSWeaponFXTracer& T){return !T.bActive;});
    if(!Result)
    {
        if(Tracers.Num()>=MaxTracers)
        {
            // Pool exhausted (very fast rounds with long flight times): recycle the streak
            // that has gone longest without an update so no live round is left without one.
            Result=&Tracers[0];
            for(FFPSWeaponFXTracer& T:Tracers)if(T.LastUpdateFrame<Result->LastUpdateFrame)Result=&T;
            ReleaseTracer(*Result);
        }
        else
        {
            Result=&Tracers.AddDefaulted_GetRef();
            Result->Mesh=NewObject<UStaticMeshComponent>(GetOwner());
            GetOwner()->AddInstanceComponent(Result->Mesh);
            Result->Mesh->SetMobility(EComponentMobility::Movable);
            Result->Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Result->Mesh->SetGenerateOverlapEvents(false);
            Result->Mesh->SetCastShadow(false);
            Result->Mesh->bReceivesDecals=false;
            Result->Mesh->SetCanEverAffectNavigation(false);
            Result->Mesh->RegisterComponent();
            Result->Mesh->SetStaticMesh(CylinderMesh);
            Result->Material=UMaterialInstanceDynamic::Create(TracerMaterial,Result->Mesh);
            Result->Mesh->SetMaterial(0,Result->Material);
            Result->HaloMesh=NewObject<UStaticMeshComponent>(GetOwner());
            GetOwner()->AddInstanceComponent(Result->HaloMesh);
            Result->HaloMesh->SetMobility(EComponentMobility::Movable);
            Result->HaloMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Result->HaloMesh->SetGenerateOverlapEvents(false);
            Result->HaloMesh->SetCastShadow(false);
            Result->HaloMesh->bReceivesDecals=false;
            Result->HaloMesh->SetCanEverAffectNavigation(false);
            Result->HaloMesh->RegisterComponent();
            Result->HaloMesh->SetStaticMesh(CylinderMesh);
            Result->HaloMaterial=UMaterialInstanceDynamic::Create(TracerMaterial,Result->HaloMesh);
            Result->HaloMesh->SetMaterial(0,Result->HaloMaterial);
        }
    }
    Result->bActive=true;
    Result->RoundId=RoundId;
    Result->TraveledCM=0.f;
    Result->FlashAge=0.f;
    Result->LingerAge=0.f;
    Result->Head=FVector::ZeroVector;
    Result->Mesh->SetStaticMesh(CylinderMesh);
    if(!Result->Material)Result->Material=UMaterialInstanceDynamic::Create(TracerMaterial,Result->Mesh);
    Result->Mesh->SetMaterial(0,Result->Material);
    Result->Mesh->SetVisibility(true);
    Result->Material->SetVectorParameterValue(TEXT("Tint"),WeaponFX::TracerTint);
    Result->Material->SetScalarParameterValue(TEXT("Emission"),WeaponFX::TracerEmission);
    Result->Material->SetScalarParameterValue(TEXT("Opacity"),1.f);
    if(Result->HaloMesh)
    {
        Result->HaloMesh->SetStaticMesh(CylinderMesh);
        if(!Result->HaloMaterial)Result->HaloMaterial=UMaterialInstanceDynamic::Create(TracerMaterial,Result->HaloMesh);
        Result->HaloMesh->SetMaterial(0,Result->HaloMaterial);
        Result->HaloMesh->SetVisibility(true);
        Result->HaloMaterial->SetVectorParameterValue(TEXT("Tint"),WeaponFX::TracerTint);
        Result->HaloMaterial->SetScalarParameterValue(TEXT("Emission"),TracerHaloEmission.GetValueOnGameThread());
        Result->HaloMaterial->SetScalarParameterValue(TEXT("Opacity"),1.f);
    }
    SetComponentTickEnabled(true);
    return Result;
}

void UFPSWeaponFXComponent::ReleaseTracer(FFPSWeaponFXTracer& T)
{
    T.bActive=false;
    T.bFlash=false;
    T.LingerAge=0.f;
    T.RoundId=INDEX_NONE;
    if(T.Mesh)T.Mesh->SetVisibility(false);
    if(T.HaloMesh)T.HaloMesh->SetVisibility(false);
}

void UFPSWeaponFXComponent::ApplyTracerTransform(FFPSWeaponFXTracer& T)
{
    if(!T.Mesh||!Camera)return;
    // Head on the round, tail Length behind it: the dash always covers the most recent
    // stretch of the real path, so it can never leave the bore or pierce a wall behind it.
    const FVector Tail=T.Head-T.Direction*T.Length;
    int32 ViewWidth=1920,ViewHeight=1080;
    if(const auto* Pawn=Cast<APawn>(GetOwner()))
        if(const auto* PC=Cast<APlayerController>(Pawn->GetController()))
            PC->GetViewportSize(ViewWidth,ViewHeight);
    const FVector Center=(T.Head+Tail)*.5f;
    const float ViewDepth=FMath::Max(1.f,static_cast<float>(FVector::DotProduct(
        Center-Camera->GetComponentLocation(),Camera->GetForwardVector())));
    const float PixelWidth=2.f*ViewDepth*FMath::Tan(FMath::DegreesToRadians(
        FMath::Clamp(Camera->FieldOfView,5.f,150.f)*.5f))/FMath::Max(1,ViewWidth);
    const float Diameter=FMath::Clamp(PixelWidth*FMath::Clamp(TracerWidthPixels.GetValueOnGameThread(),.2f,16.f),
        WeaponFX::TracerMinDiameterCM,
        ShouldHideCasings()?WeaponFX::TracerScopedDiameterMaxCM:WeaponFX::TracerDiameterMaxCM);
    T.Mesh->SetWorldLocationAndRotation(Center,FRotationMatrix::MakeFromZ(T.Head-Tail).Rotator());
    T.Mesh->SetWorldScale3D(FVector(Diameter,Diameter,FMath::Max(1.f,T.Length))/100.f);
    // Colour and brightness are re-applied every frame so console changes show up on streaks
    // that are already flying instead of only on the next shot.
    FLinearColor Tint=WeaponFX::TracerTint;
    ParseTracerTint(TracerTintSetting.GetValueOnGameThread(),Tint);
    T.Material->SetVectorParameterValue(TEXT("Tint"),Tint);
    T.Material->SetScalarParameterValue(TEXT("Emission"),
        FMath::Clamp(TracerEmissionScale.GetValueOnGameThread(),0.f,20.f));
    const float Linger=FMath::Clamp(TracerLingerSeconds.GetValueOnGameThread(),0.f,2.f);
    const float Opacity=T.bFlash?FMath::Clamp(1.f-T.FlashAge/WeaponFX::TracerFlashSeconds,0.f,1.f)
        :(T.LingerAge>0.f&&Linger>0.f?FMath::Clamp(1.f-T.LingerAge/Linger,0.f,1.f):1.f);
    T.Material->SetScalarParameterValue(TEXT("Opacity"),Opacity);
    // Halo pass: same material, wider and much dimmer, so the streak gets a soft outer glow
    // instead of staying a hard rod. Width 1 / emission 0 turns it off at no cost.
    if(T.HaloMesh&&T.HaloMaterial)
    {
        const float HaloScale=FMath::Clamp(TracerHaloWidth.GetValueOnGameThread(),0.f,6.f);
        const float HaloEmission=FMath::Clamp(TracerHaloEmission.GetValueOnGameThread(),0.f,20.f);
        const bool bHalo=HaloScale>1.001f&&HaloEmission>0.f;
        T.HaloMesh->SetVisibility(bHalo);
        if(bHalo)
        {
            const float HaloDiameter=Diameter*HaloScale;
            T.HaloMesh->SetWorldLocationAndRotation(Center,FRotationMatrix::MakeFromZ(T.Head-Tail).Rotator());
            T.HaloMesh->SetWorldScale3D(FVector(HaloDiameter,HaloDiameter,FMath::Max(1.f,T.Length))/100.f);
            T.HaloMaterial->SetVectorParameterValue(TEXT("Tint"),Tint);
            T.HaloMaterial->SetScalarParameterValue(TEXT("Emission"),HaloEmission);
            T.HaloMaterial->SetScalarParameterValue(TEXT("Opacity"),Opacity);
        }
    }
}

UPointLightComponent* UFPSWeaponFXComponent::EnsureTracerLight(int32 Index)
{
    while(TracerLights.Num()<=Index)TracerLights.Add(nullptr);
    UPointLightComponent* Light=TracerLights[Index];
    if(!Light)
    {
        Light=NewObject<UPointLightComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(Light);
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetCastShadows(false);
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetSourceRadius(2.f);
        Light->SetSoftSourceRadius(4.f);
        Light->SetSpecularScale(.5f);
        Light->SetVolumetricScatteringIntensity(0.f);
        Light->SetIndirectLightingIntensity(0.f);
        Light->SetVisibility(false);
        Light->RegisterComponent();
        TracerLights[Index]=Light;
    }
    return Light;
}

void UFPSWeaponFXComponent::UpdateTracerLights()
{
    const float Lumens=FMath::Clamp(TracerLightLumens.GetValueOnGameThread(),0.f,20000.f);
    const float Radius=FMath::Clamp(TracerLightRadiusCM.GetValueOnGameThread(),20.f,3000.f);
    constexpr int32 Slots=2;
    int32 Pick[Slots]={INDEX_NONE,INDEX_NONE};
    float PickDistance[Slots]={FLT_MAX,FLT_MAX};
    if(Lumens>0.f)
    {
        // The two streaks closest to the muzzle are the shots the player just fired, so the
        // moving light always sits where the eye already is. Fixed slot count keeps the cost
        // independent of the fire rate.
        const FVector Muzzle=MuzzleLocation();
        for(int32 I=0;I<Tracers.Num();++I)
        {
            const FFPSWeaponFXTracer& T=Tracers[I];
            if(!T.bActive||T.bFlash||T.LingerAge>0.f)continue;
            const float Distance=static_cast<float>(FVector::DistSquared(T.Head,Muzzle));
            if(Distance<PickDistance[0]){PickDistance[1]=PickDistance[0];Pick[1]=Pick[0];PickDistance[0]=Distance;Pick[0]=I;}
            else if(Distance<PickDistance[1]){PickDistance[1]=Distance;Pick[1]=I;}
        }
    }
    FLinearColor LightColor=WeaponFX::TracerTint;
    ParseTracerTint(TracerTintSetting.GetValueOnGameThread(),LightColor);
    for(int32 Slot=0;Slot<Slots;++Slot)
    {
        if(Pick[Slot]==INDEX_NONE)
        {
            // Park the slot without creating components for a weapon that is not firing.
            if(Slot<TracerLights.Num()&&TracerLights[Slot]!=nullptr)TracerLights[Slot]->SetVisibility(false);
            continue;
        }
        UPointLightComponent* Light=EnsureTracerLight(Slot);
        const FFPSWeaponFXTracer& T=Tracers[Pick[Slot]];
        Light->SetWorldLocation(T.Head-T.Direction*(T.Length*.35f));
        Light->SetAttenuationRadius(Radius);
        Light->SetIntensity(Lumens);
        Light->SetLightColor(LightColor);
        Light->SetVisibility(true);
    }
}

float UFPSWeaponFXComponent::TracerBaseLengthCM() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const float Scale=FMath::Clamp(TracerLengthScale.GetValueOnGameThread(),.1f,5.f);
    return Scale*((bIndependentPistol||(Character&&Character->IsPistolWeapon()))
        ?WeaponFX::TracerPistolLengthCM:WeaponFX::TracerRifleLengthCM);
}

float UFPSWeaponFXComponent::TracerMaxLengthCM() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const float Scale=FMath::Clamp(TracerLengthScale.GetValueOnGameThread(),.1f,5.f);
    return Scale*((bIndependentPistol||(Character&&Character->IsPistolWeapon()))
        ?WeaponFX::TracerPistolMaxCM:WeaponFX::TracerRifleMaxCM);
}

bool UFPSWeaponFXComponent::SpawnEpicFX(FVector Position,FVector Forward,float Scale)
{
    UNiagaraSystem* System=EpicMuzzleSystem.Get();
    if(!System)return false;
    UNiagaraComponent* FX=nullptr;
    for(const auto& Candidate:EpicFXPool)if(Candidate->GetAsset()==System&&!Candidate->IsActive()){FX=Candidate;break;}
    if(!FX&&EpicFXPool.Num()<24){
        FX=NewObject<UNiagaraComponent>(GetOwner());FX->SetAutoActivate(false);FX->SetAutoDestroy(false);
        FX->SetAsset(System);FX->SetCastShadow(false);FX->RegisterComponent();EpicFXPool.Add(FX);
    }
    if(!FX)return true;
    const bool bScope = ShouldHideCasings(); // The same LPVO 1-6x presentation contract.
    if(bScope)
    {
        const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
        const float Magnification=Character?FMath::Max(1.f,Character->GetOpticMagnification()):1.f;
        const float Compensation=FMath::Clamp(FMath::Pow(Magnification,
            FMath::Clamp(ScopeWorldScaleExponent.GetValueOnGameThread(),0.f,1.f)),1.f,
            FMath::Max(1.f,ScopeWorldScaleMax.GetValueOnGameThread()));
        Scale*=Compensation;
        Position+=Forward*FMath::Max(0.f,ScopeWorldForwardCM.GetValueOnGameThread())*(Compensation-1.f);
    }
    FX->SetWorldLocationAndRotation(Position,Forward.Rotation());
    FX->SetVariableFloat(TEXT("User.Global Scale"),Scale);
    FX->SetVariableFloat(TEXT("User.Length Randomness"), FMath::FRandRange(.50f, .85f));
    // Randomize the actual side-lobe geometry, not the muzzle origin or firing direction.
    FX->SetVariableFloat(TEXT("User.Side Flash Angle"), FMath::FRandRange(0.f, 360.f));
    FX->SetVariableFloat(TEXT("User.Side Flash Probability"), bScope
        ? FMath::FRandRange(.45f, .75f) : FMath::FRandRange(.70f, 1.f));
    const FLinearColor SourceFlash=System->GetExposedParameters().GetParameterValue<FLinearColor>(
        FNiagaraVariable(FNiagaraTypeDefinition::GetColorDef(),TEXT("User.Flash Base Color")));
    const auto* FlashOwner = Cast<AFPSGAMECharacter>(GetOwner());
    const bool bAiming = FlashOwner && FlashOwner->IsAiming();
    const float FlashGain = (bScope ? .35f : bAiming ? .42f : .55f) * FMath::FRandRange(.92f, 1.08f);
    FX->SetVariableLinearColor(TEXT("User.Flash Base Color"),FLinearColor(
        SourceFlash.R*FlashGain,SourceFlash.G*FlashGain,SourceFlash.B*FlashGain,SourceFlash.A));
    if(EpicMuzzleBursts==0)UE_LOG(LogTemp,Display,TEXT("EPIC_GUN_FX source_flash=%s"),*SourceFlash.ToString());
    FX->SetVariableBool(TEXT("User.Use Bullet Shell"),false);
    FX->SetVariableBool(TEXT("User.Use Smoke"),false);
    FX->SetVariableBool(TEXT("User.Use Sparks"),false);
    FX->SetVariableBool(TEXT("User.Use Flash Side"),LastSuppression>.5f);
    FX->Activate(true);
    ++EpicMuzzleBursts;
    return true;
}

void UFPSWeaponFXComponent::SpawnSmokeImpulse(bool bADS)
{
    if (!SmokeImpulseSystem) return;
    // Reuse the existing capped cosmetic pool, with the same stop/end-play cleanup.
    UNiagaraComponent* FX = nullptr;
    for (const auto& Candidate : EpicFXPool)
        if (Candidate->GetAsset() == SmokeImpulseSystem && !Candidate->IsActive())
        {
            FX = Candidate;
            break;
        }
    if (!FX && EpicFXPool.Num() < 24)
    {
        FX = NewObject<UNiagaraComponent>(GetOwner());
        FX->SetAutoActivate(false);
        FX->SetAutoDestroy(false);
        FX->SetAsset(SmokeImpulseSystem);
        FX->SetCastShadow(false);
        FX->RegisterComponent();
        EpicFXPool.Add(FX);
    }
    if (!FX) return;

    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    const bool bPistol = bIndependentPistol || (Character && Character->IsPistolWeapon());
    const bool bScope = ShouldHideCasings();
    const bool bSuppressed = LastSuppression < .5f;
    const float Size = .26f * (bPistol ? .8f : 1.f) * LastADSMultiplier
        * (bSuppressed ? .8f : 1.f) * FMath::FRandRange(.92f, 1.08f);
    const float Opacity = FMath::Clamp(SmokeOpacity, 0.f, 1.f)
        * FMath::Clamp(SmokeIntensity.GetValueOnGameThread(), 0.f, 2.f)
        * (bScope ? .34f : bADS ? .38f : .44f) * (bSuppressed ? .65f : 1.f);
    FX->SetWorldLocationAndRotation(MuzzleLocation(), MuzzleForward().Rotation());
    FX->SetVariableFloat(TEXT("User.SpawnRate"), 0.f);
    FX->SetVariableFloat(TEXT("User.SmokeScale"), Size);
    FX->SetVariableFloat(TEXT("User.SmokeForwardSpeed"), bSuppressed ? 180.f : bPistol ? 210.f : 280.f);
    FX->SetVariableFloat(TEXT("User.SmokeSpreadScale"), 1.f);
    FX->SetVariableFloat(TEXT("User.SmokeTailBlend"), 0.f);
    FX->SetVariableFloat(TEXT("User.SightProtection"), bScope ? .82f : bADS ? .68f : .28f);
    FX->SetVariableVec3(TEXT("User.SmokeDrift"), FVector(3.f, -2.f, 4.f));
    FX->SetVariableLinearColor(TEXT("User.Smoke Color"), FLinearColor(.78f, .80f, .82f, Opacity));
    FX->Activate(true); // Three short-lived sprites once per shot, independent of stream heat.
}

void UFPSWeaponFXComponent::UpdateSmokeStream(float DeltaTime)
{
    if (!EpicSmokeSystem) return;
    const double Now = GetWorld()->GetTimeSeconds();
    const float Heat = FMath::Clamp(BarrelHeat + PendingHeat, 0.f, 1.f);
    // Ease the pressurized plume into a sparse, slow barrel wisp. New shots extend
    // both windows without restarting particles already drifting in world space.
    const float TailBlendT = FMath::Clamp(static_cast<float>((Now - SmokeFeedUntil + .10) / .10), 0.f, 1.f);
    const float TailBlend = TailBlendT * TailBlendT * (3.f - 2.f * TailBlendT);
    const float TailAge = FMath::Clamp(static_cast<float>((Now - SmokeFeedUntil)
        / FMath::Max(.01, SmokeTailUntil - SmokeFeedUntil)), 0.f, 1.f);
    const float TailFade = 1.f - TailAge * TailAge * (3.f - 2.f * TailAge);
    const float TailRate = FMath::Lerp(4.f, 11.f, SmokeHeatAtLastShot) * TailFade;
    const float TargetRate = Now < SmokeTailUntil
        ? FMath::Lerp(FMath::Lerp(26.f, 36.f, Heat), TailRate, TailBlend) : 0.f;
    if (!SmokeStream && TargetRate <= 0.f) return;
    if (!SmokeStream)
    {
        SmokeStream = NewObject<UNiagaraComponent>(GetOwner());
        SmokeStream->SetAutoActivate(false);
        SmokeStream->SetAutoDestroy(false);
        SmokeStream->SetAsset(EpicSmokeSystem);
        SmokeStream->SetCastShadow(false);
        SmokeStream->RegisterComponent();
    }
    if (!SmokeStream->IsActive() && TargetRate > 0.f) SmokeEmissionRate = TargetRate;
    else if (DeltaTime > 0.f) SmokeEmissionRate = FMath::Lerp(SmokeEmissionRate, TargetRate, 1.f - FMath::Exp(-DeltaTime * 14.f));
    if (SmokeEmissionRate < .05f) SmokeEmissionRate = 0.f;
    // Only the emission origin follows the muzzle. All born particles remain in world space.
    SmokeStream->SetWorldLocationAndRotation(MuzzleLocation(), MuzzleForward().Rotation());
    SmokeStream->SetVariableFloat(TEXT("User.SpawnRate"), SmokeEmissionRate);
    // Size, speed and color are sampled at birth; the tail cannot shrink or
    // recolor the larger shot smoke that is still dissipating above the barrel.
    SmokeStream->SetVariableFloat(TEXT("User.SmokeScale"), FMath::Lerp(.34f, .14f, TailBlend) * LastADSMultiplier);
    SmokeStream->SetVariableFloat(TEXT("User.SmokeForwardSpeed"), FMath::Lerp(65.f, 6.f, TailBlend));
    SmokeStream->SetVariableFloat(TEXT("User.SmokeSpreadScale"), FMath::Clamp(SmokeSpreadScale, 1.f, 2.5f));
    SmokeStream->SetVariableFloat(TEXT("User.SmokeTailBlend"), TailBlend);
    // World-space breeze avoids forcing every plume towards camera-right.
    SmokeStream->SetVariableVec3(TEXT("User.SmokeDrift"), FVector(3.f, -2.f, 4.f));
    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    const bool bAiming = Character && Character->IsAiming();
    const bool bScope = ShouldHideCasings();
    const float ViewOpacity = bScope ? .25f : (bAiming ? .28f : .32f);
    const float LayerOpacity = FMath::Clamp(SmokeOpacity, 0.f, 1.f)
        * FMath::Clamp(SmokeIntensity.GetValueOnGameThread(), 0.f, 2.f)
        * ViewOpacity * FMath::Lerp(1.f, .85f, Heat)
        * FMath::Lerp(1.f, .55f, TailBlend);
    SmokeStream->SetVariableFloat(TEXT("User.SightProtection"), bScope ? .82f : bAiming ? .68f : .28f);
    SmokeStream->SetVariableLinearColor(TEXT("User.Smoke Color"), FLinearColor(.78f, .80f, .82f, LayerOpacity));
    if (TargetRate > 0.f && !SmokeStream->IsActive())
    {
        SmokeStream->Activate(true);
        ++EpicSmokeBursts; // Counts complete continuous plumes, not individual shots.
    }
    if (SmokeEmissionRate > 0.f) LastSmokeFeedTime = Now;
    else if (Now - LastSmokeFeedTime > WeaponFX::StreamMaxLifetime + .15f)
        SmokeStream->Deactivate(); // Only after the final world-space smoke has dissipated.
}

void UFPSWeaponFXComponent::OnShot(bool bADS)
{
    if (!bReady) return;
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const float Suppression=(bIndependentPistol?IndependentSuppressed:(Character&&Character->IsMuzzleSuppressed()))?.12f:1.f;
    LastSuppression=Suppression;
    LastADSMultiplier = bADS ? 0.78f : 1.0f;
    LastWeaponFlashMultiplier = bIndependentPistol || (Character && Character->IsPistolWeapon()) ? FMath::Clamp(PistolFlashScale, 0.f, 1.f) : 1.f;
    const float Scale = FMath::Clamp(FlashScale, 0.0f, 2.0f) * LastADSMultiplier * LastWeaponFlashMultiplier;
    LastFXShotTime=GetWorld()->GetTimeSeconds();
    const bool bScope = ShouldHideCasings();
    const float ShotVariation=FMath::FRandRange(bScope ? .76f : .86f,1.18f);
    const bool Epic=SpawnEpicFX(MuzzleLocation(),MuzzleForward(),
        Scale*ShotVariation*(Suppression<1.f?.085f:(bScope?.25f:.27f)));
    for (int32 Layer = 0; !Epic && Layer < 2; ++Layer)
    {
        if (FFPSWeaponFXParticle* P = Acquire(Layer == 0 ? WeaponFX::FlashCore : WeaponFX::FlashTongue, CardMesh, FlashMaterial))
        {
            P->Lifetime = Layer == 0 ? 0.045f : 0.065f;
            P->ForwardOffset = Layer == 0 ? 1.2f : 5.0f;
            // The bore is below the sight line: let a short outer lobe clear
            // the sight housing, while keeping its center translucent in ADS.
            P->Size = FVector(Layer == 0 ? 6.0f : 21.0f) * Scale;
            P->Rotation.Roll = FMath::FRandRange(-180.0f, 180.0f);
            P->Material->SetVectorParameterValue(TEXT("Tint"), Layer == 0 ? WeaponFX::HotCore : WeaponFX::Flame);
            P->Material->SetScalarParameterValue(TEXT("Emission"), Layer == 0 ? 5.0f : 3.0f);
            P->Opacity = (Layer == 0 ? 0.8f : 0.42f)*Suppression;
            P->Position = MuzzleLocation() + MuzzleForward() * P->ForwardOffset;
            ApplyParticleTransform(*P);
        }
    }
    for (int32 I = 0; I < (Epic||Suppression<1.f?0:2); ++I)
    {
        if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Spark, CardMesh, FlashMaterial))
        {
            P->Position = MuzzleLocation();
            P->Velocity = MuzzleForward() * FMath::FRandRange(270.0f, 480.0f) + FMath::VRand() * 75.0f;
            P->Acceleration = FVector(0.0f, 0.0f, -340.0f);
            P->Lifetime = FMath::FRandRange(0.075f, 0.13f);
            P->Size = FVector(0.30f, 1.6f, 1.0f) * LastADSMultiplier;
            ApplyParticleTransform(*P);
        }
    }
    if (const auto* OwnerCharacter = Cast<AFPSGAMECharacter>(GetOwner()); bIndependentPistol?!bIndependentRevolver:(!OwnerCharacter || !OwnerCharacter->bUseDanWesson715)) SpawnCasing();
    PendingHeat = FMath::Min(1.0f, PendingHeat + 0.18f);
    SmokeHeatAtLastShot = FMath::Min(1.f, BarrelHeat + PendingHeat);
    SmokeFeedUntil = LastFXShotTime + FMath::Lerp(.14f, .20f, SmokeHeatAtLastShot);
    SmokeTailUntil = SmokeFeedUntil + FMath::Lerp(.30f, 1.60f, SmokeHeatAtLastShot);
    if (EpicSmokeSystem)
    {
        SpawnSmokeImpulse(bADS);
        UpdateSmokeStream(0.f);
    }
    else SpawnSmoke(true, 0.0f, MuzzleLocation(), MuzzleForward(), FMath::Min(1.0f, BarrelHeat + PendingHeat));
    FlashTime = Epic?0.f:0.045f;
    FlashBirthFrame = GFrameCounter;
    FlashLight->SetWorldLocation(MuzzleLocation() + MuzzleForward() * 2.0f);
    FlashLight->SetIntensity(350.0f * Scale * LastSuppression);
    FlashLight->SetVisibility(!Epic && Scale > 0.0f);
    SetComponentTickEnabled(true);
}

bool UFPSWeaponFXComponent::ShouldHideCasings() const
{
    if(bIndependentPistol)return false;
    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    // LPVO at 1x is still scope mode. Cover both aim-in and the remaining scope fade-out.
    return Character && (Character->GetGunsmithOpticVariant() == TEXT("lpvo_1_6x") || Character->HasPSO1Scope())
        && (Character->IsAiming() || Character->GetScopePresentationAlpha() > 0.0f);
}

void UFPSWeaponFXComponent::SpawnCasing()
{
    if (ShouldHideCasings()) return;
    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    const bool bRifle = !bIndependentPistol && Character && !Character->IsPistolWeapon();
    const bool bUseRifleMesh = bRifle && RifleCasingMesh && RifleCasingMaterial;
    UStaticMesh* Geometry = bUseRifleMesh ? RifleCasingMesh.Get() : CylinderMesh.Get();
    UMaterialInterface* Surface = bUseRifleMesh ? RifleCasingMaterial.Get() : BrassMaterial.Get();
    if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Casing, Geometry, Surface))
    {
        // Sample the physical port once. A free casing never remains attached to the gun/camera.
        P->Position = WeaponMesh->GetSocketTransform(EjectSocket, RTS_World).GetLocation();
        if (bRifle)
        {
            const FQuat Frame = WeaponMesh->GetSocketQuaternion(TEXT("WPN_root")) * CasingFrameInRoot;
            P->Velocity = Frame.RotateVector(FVector(FMath::FRandRange(-70.0f, -35.0f),
                FMath::FRandRange(185.0f, 260.0f), FMath::FRandRange(70.0f, 125.0f)))
                + GetOwner()->GetVelocity();
            P->Acceleration = FVector(0.0f, 0.0f, GetWorld()->GetGravityZ());
            const float LengthCM = PKMLowpolyWeaponAssets::Matches(WeaponMesh) ? 5.4f : Character->bUseASH12 ? ASH12WeaponAssets::TracerLengthCM
                : Character->bUseQBZ191 ? 4.2f : (AKMSoviet::Matches(WeaponMesh) || A762WeaponAssets::Matches(WeaponMesh)) ? 3.9f : 4.5f;
            const FVector Extent = Geometry->GetBounds().BoxExtent;
            const int32 LongAxis = Extent.X > Extent.Y ? (Extent.X > Extent.Z ? 0 : 2) : (Extent.Y > Extent.Z ? 1 : 2);
            FVector MeshAxis = FVector::ZeroVector;
            MeshAxis[LongAxis] = 1.0f;
            P->Rotation = (Frame * FQuat::FindBetweenNormals(MeshAxis, FVector::ForwardVector)).Rotator();
            // The owned shell is not a 100 cm engine primitive. Preserve its proportions.
            P->Size = bUseRifleMesh ? FVector(100.0f * LengthCM / FMath::Max(0.01f, float(Extent[LongAxis] * 2.0)))
                : FVector(0.95f, 0.95f, LengthCM);
            P->Spin = FRotator(FMath::FRandRange(650.0f, 1150.0f),
                FMath::FRandRange(-950.0f, 950.0f), FMath::FRandRange(350.0f, 850.0f));
        }
        else
        {
            P->Velocity = Camera->GetRightVector() * FMath::FRandRange(140.0f, 215.0f)
                + Camera->GetUpVector() * FMath::FRandRange(75.0f, 125.0f) - MuzzleForward() * 30.0f;
            P->Acceleration = FVector(0.0f, 0.0f, -650.0f);
            P->Size = FVector(0.80f, 0.80f, 2.6f);
            P->Spin = FRotator(400.0f, 650.0f, 100.0f);
        }
        P->Lifetime = 1.25f;
        if (!bUseRifleMesh)
            P->Material->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.25f, 0.075f));
        ApplyParticleTransform(*P);
    }
}

void UFPSWeaponFXComponent::SpawnSmoke(bool bImmediate, float InitialAge, const FVector& BirthPosition,
    const FVector& BirthForward, float HeatAtBirth)
{
    const float Lifetime = FMath::FRandRange(0.80f, WeaponFX::SmokeMaxLifetime);
    if (InitialAge >= Lifetime) return; // Do not occupy the pool with already expired catch-up particles.
    if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Smoke, CardMesh, SmokeMaterial))
    {
        P->Position = BirthPosition + BirthForward * 2.0f;
        P->Velocity = BirthForward * (bImmediate ? 36.0f : 10.0f) + FVector(3.5f, -2.0f, 22.0f);
        P->Acceleration = FVector(0.8f, 0.0f, 7.0f);
        P->Lifetime = Lifetime;
        P->Size = FVector(bImmediate ? 9.0f : 7.0f);
        P->Rotation.Roll = FMath::FRandRange(-180.0f, 180.0f);
        P->Spin.Roll = FMath::FRandRange(-25.0f, 25.0f);
        P->Opacity = FMath::Clamp(SmokeOpacity, 0.0f, 1.0f) * FMath::Lerp(0.32f, 1.0f, HeatAtBirth) * LastADSMultiplier;
        P->Material->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.92f, 0.94f, 0.96f));
        P->Material->SetScalarParameterValue(TEXT("Emission"), 0.12f);
        AdvanceParticle(*P, InitialAge);
        ApplyParticleTransform(*P);
    }
}

void UFPSWeaponFXComponent::OnImpact(const FHitResult& Hit)
{
    if (!GetWorld() || !Hit.bBlockingHit || !IsValid(Camera)) return;
    if (const auto* Pawn=Cast<APawn>(GetOwner()); Pawn && !Pawn->IsLocallyControlled()) return;
    if (auto* Impacts=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>()) Impacts->SpawnImpact(Hit,Camera);
}

void UFPSWeaponFXComponent::ApplyParticleTransform(FFPSWeaponFXParticle& P)
{
    const float Life = FMath::Clamp(P.Age / P.Lifetime, 0.0f, 1.0f);
    FVector Size = P.Size;
    float Alpha = P.Opacity * (1.0f - Life);
    FRotator Rotation = P.Rotation;
    if (P.Kind != WeaponFX::Casing)
    {
        Rotation = FRotationMatrix::MakeFromZ(Camera->GetComponentLocation() - P.Position).Rotator();
        const FQuat Billboard = Rotation.Quaternion() * FQuat(FVector::UpVector, FMath::DegreesToRadians(P.Rotation.Roll));
        Rotation = Billboard.Rotator();
        if (P.Kind == WeaponFX::Smoke || P.Kind == WeaponFX::Dust)
        {
            Size *= 0.6f + Life * 2.4f;
            Alpha *= FMath::Min(1.0f, Life * 9.0f);
        }
        else Alpha *= 1.0f - Life;
        P.Material->SetScalarParameterValue(TEXT("Opacity"), Alpha);
    }
    // Keep the physical center on the port/flight path even when the shell asset has an end pivot.
    const FVector PivotOffset = P.Kind == WeaponFX::Casing
        ? Rotation.RotateVector(P.Mesh->GetStaticMesh()->GetBounds().Origin * (Size / 100.0f)) : FVector::ZeroVector;
    P.Mesh->SetWorldLocationAndRotation(P.Position - PivotOffset, Rotation);
    P.Mesh->SetWorldScale3D(Size / 100.0f);
}

void UFPSWeaponFXComponent::AdvanceParticle(FFPSWeaponFXParticle& P, float DeltaTime)
{
    if (DeltaTime <= 0.0f) return;
    if (P.Age + DeltaTime >= P.Lifetime) { Release(P); return; }
    // Only casings need swept collision substeps. Their <=1.25 s lifetime bounds
    // this loop; even the capped case consumes the entire interval, never discarding time.
    const int32 Steps = P.Kind == WeaponFX::Casing
        ? FMath::Clamp(FMath::CeilToInt(DeltaTime / 0.025f), 1, 64) : 1;
    const float Step = DeltaTime / Steps;
    for (int32 I = 0; I < Steps; ++I)
    {
        if (P.Age + Step >= P.Lifetime) { Release(P); return; }
        P.Age += Step;
        const FVector OldPosition = P.Position;
        if (P.Kind == WeaponFX::Smoke || P.Kind == WeaponFX::Dust)
        {
            // Exact solution of dv/dt = Acceleration - Drag * Velocity.
            const float Decay = FMath::Exp(-WeaponFX::SmokeDrag * Step);
            const float Travel = (1.0f - Decay) / WeaponFX::SmokeDrag;
            P.Position += P.Velocity * Travel + P.Acceleration / WeaponFX::SmokeDrag * (Step - Travel);
            P.Velocity = P.Velocity * Decay + P.Acceleration * Travel;
        }
        else if (P.Kind != WeaponFX::FlashCore && P.Kind != WeaponFX::FlashTongue)
        {
            P.Position += P.Velocity * Step + P.Acceleration * (0.5f * Step * Step);
            P.Velocity += P.Acceleration * Step;
        }
        P.Rotation += P.Spin * Step;
        if (P.Kind == WeaponFX::Casing && !P.bBounced)
        {
            FHitResult Bounce;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(WeaponCasing), false, GetOwner());
            if (GetWorld()->LineTraceSingleByChannel(Bounce, OldPosition, P.Position, ECC_Visibility, Params))
            {
                const float AfterHit = Step * (1.0f - FMath::Clamp(Bounce.Time, 0.0f, 1.0f));
                P.Position = Bounce.ImpactPoint + Bounce.ImpactNormal * 0.8f;
                const FVector HitVelocity = P.Velocity - P.Acceleration * AfterHit;
                P.Velocity = FMath::GetReflectionVector(HitVelocity, Bounce.ImpactNormal) * 0.24f;
                // Consume the post-impact part of this substep as well.
                P.Position += P.Velocity * AfterHit + P.Acceleration * (0.5f * AfterHit * AfterHit);
                P.Velocity += P.Acceleration * AfterHit;
                P.Rotation -= P.Spin * (AfterHit * 0.70f);
                P.Spin *= 0.30f;
                P.bBounced = true;
                P.Lifetime = FMath::Min(P.Lifetime, P.Age - AfterHit + 0.25f);
                if (P.Age >= P.Lifetime) { Release(P); return; }
            }
        }
    }
}

void UFPSWeaponFXComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!bReady || !IsValid(WeaponMesh) || !IsValid(Camera))
    {
        StopEmission();
        for (FFPSWeaponFXParticle& P : Particles) Release(P);
        for (FFPSWeaponFXTracer& T : Tracers) ReleaseTracer(T);
        SetComponentTickEnabled(false);
        return;
    }
    for(const auto& FX:EpicFXPool)if(FX->IsActive()&&FX->GetAsset()==EpicMuzzleSystem)
        FX->SetWorldLocationAndRotation(MuzzleLocation(),MuzzleForward().Rotation());
    DeltaTime = FMath::Max(0.0f, DeltaTime);
    if (FlashBirthFrame != GFrameCounter) FlashTime = FMath::Max(0.0f, FlashTime - DeltaTime);
    if (FlashTime > 0.0f)
    {
        FlashLight->SetWorldLocation(MuzzleLocation() + MuzzleForward() * 2.0f);
        FlashLight->SetIntensity(350.0f * FMath::Clamp(FlashScale, 0.0f, 2.0f) * LastADSMultiplier * LastWeaponFlashMultiplier * LastSuppression * FMath::Square(FlashTime / 0.045f));
    }
    else FlashLight->SetVisibility(false);
    const bool bHideCasings = ShouldHideCasings();
    for (FFPSWeaponFXParticle& P : Particles)
    {
        if (!P.bActive) continue;
        // Retire pre-ADS shells too, so a hip-fire casing cannot cross the scope after aim-in.
        if (P.Kind == WeaponFX::Casing && bHideCasings) { Release(P); continue; }
        // An OnShot/OnImpact particle was born at this frame's current time.
        // Both its age and motion start next Tick, preserving a zero-age first display.
        if (P.BirthFrame != GFrameCounter) AdvanceParticle(P, DeltaTime);
        if (!P.bActive) continue;
        if (P.Kind == WeaponFX::FlashCore || P.Kind == WeaponFX::FlashTongue)
            P.Position = MuzzleLocation() + MuzzleForward() * P.ForwardOffset;
        ApplyParticleTransform(P);
    }
    // Tracer streaks: every live round owns exactly one, refreshed in place by the
    // ballistics tick earlier this frame. A streak that was not refreshed belongs to a round
    // that ended (impacted or out of range): it keeps its last position, fades out over
    // fps.Tracer.LingerSeconds and is only then pooled again, so nothing piles up.
    for (FFPSWeaponFXTracer& T : Tracers)
    {
        if (!T.bActive) continue;
        if (T.bFlash)
        {
            T.FlashAge += DeltaTime;
            if (T.FlashAge >= WeaponFX::TracerFlashSeconds)
            { ReleaseTracer(T); ++ExpiredTracerSegments; continue; }
        }
        else if (T.LastUpdateFrame != GFrameCounter)
        {
            // A 350 m/s round crosses 20 m in about three frames at 60 fps, so a streak that
            // died with the round was almost invisible. It never moves again after this, so
            // holding it cannot smear (the material refuses TSR history).
            T.LingerAge += DeltaTime;
            if (T.LingerAge >= FMath::Clamp(TracerLingerSeconds.GetValueOnGameThread(),0.f,2.f))
            { ReleaseTracer(T); ++ExpiredTracerSegments; continue; }
        }
        ApplyTracerTransform(T);
    }
    UpdateTracerLights();

    const FVector CurrentMuzzlePosition = MuzzleLocation();
    const FVector CurrentMuzzleForward = MuzzleForward();
    const float HeatAtStart = BarrelHeat;
    const double HotDelta = FMath::Clamp((static_cast<double>(HeatAtStart) - WeaponFX::HeatThreshold)
        / WeaponFX::HeatCoolingRate, 0.0, static_cast<double>(DeltaTime));
    if (!EpicSmokeSystem && HotDelta > 0.0)
    {
        const double Total = SmokeClock + HotDelta;
        const int32 DueCount = FMath::FloorToInt((Total + 1.e-9) / WeaponFX::SmokePeriod);
        const double FirstOffset = WeaponFX::SmokePeriod - SmokeClock;
        // Skip history outside the maximum lifetime before iterating; at most
        // ceil(1.25 / 0.11) + 1 events can need a pool slot, even after a long hitch.
        const double SkippedHistory = FMath::Clamp(
            (DeltaTime - WeaponFX::SmokeMaxLifetime - FirstOffset) / WeaponFX::SmokePeriod, 0.0, static_cast<double>(DueCount));
        const int32 FirstVisible = FMath::CeilToInt(SkippedHistory);
        for (int32 I = FirstVisible; I < DueCount; ++I)
        {
            const double Offset = FirstOffset + I * WeaponFX::SmokePeriod;
            const float Age = FMath::Max(0.0f, DeltaTime - static_cast<float>(Offset));
            const float Fraction = DeltaTime > 0.0f ? FMath::Clamp(static_cast<float>(Offset) / DeltaTime, 0.0f, 1.0f) : 1.0f;
            // Socket history between samples is reconstructed linearly in world space.
            const FVector BirthPosition = FMath::Lerp(PreviousMuzzlePosition, CurrentMuzzlePosition, Fraction);
            FVector BirthForward = FMath::Lerp(PreviousMuzzleForward, CurrentMuzzleForward, Fraction).GetSafeNormal();
            if (BirthForward.IsNearlyZero()) BirthForward = CurrentMuzzleForward;
            const float BirthHeat = FMath::Max(WeaponFX::HeatThreshold,
                HeatAtStart - static_cast<float>(Offset) * WeaponFX::HeatCoolingRate);
            SpawnSmoke(false, Age, BirthPosition, BirthForward, BirthHeat);
        }
        SmokeClock = FMath::Max(0.0, Total - DueCount * WeaponFX::SmokePeriod);
    }
    const float CooledHeat = FMath::Max(0.0f, HeatAtStart - DeltaTime * WeaponFX::HeatCoolingRate);
    if (CooledHeat <= WeaponFX::HeatThreshold) SmokeClock = 0.0;
    // Heat added by this frame's shot is an endpoint event, not heat from the past interval.
    BarrelHeat = FMath::Min(1.0f, CooledHeat + PendingHeat);
    PendingHeat = 0.0f;
    if (EpicSmokeSystem) UpdateSmokeStream(DeltaTime);
    PreviousMuzzlePosition = CurrentMuzzlePosition;
    PreviousMuzzleForward = CurrentMuzzleForward;
    if (BarrelHeat <= WeaponFX::HeatThreshold && FlashTime <= 0.0f && GetActiveParticleCount() == 0
        && GetActiveTracerCount() == 0 && (!SmokeStream || !SmokeStream->IsActive()))
    {
        BarrelHeat = 0.0f;
        SmokeClock = 0.0;
        // The tick stops here, so the travelling tracer lights must be parked explicitly:
        // otherwise the last one would stay lit until the next shot.
        for(const TObjectPtr<UPointLightComponent>& Light : TracerLights)
            if(Light!=nullptr)Light->SetVisibility(false);
        SetComponentTickEnabled(false);
    }
}

int32 UFPSWeaponFXComponent::GetActiveParticleCount() const
{
    int32 Count = 0;
    for (const FFPSWeaponFXParticle& P : Particles) if (P.bActive) ++Count;
    return Count;
}

void UFPSWeaponFXComponent::StopEmission()
{
    for(const auto& FX:EpicFXPool)if(FX)FX->DeactivateImmediate();
    if (SmokeStream) SmokeStream->DeactivateImmediate();
    SmokeEmissionRate = 0.f;
    SmokeFeedUntil = SmokeTailUntil = LastSmokeFeedTime = -10.0;
    SmokeHeatAtLastShot = 0.f;
    BarrelHeat = PendingHeat = FlashTime = 0.0f;
    SmokeClock = 0.0;
    if (FlashLight) FlashLight->SetVisibility(false);
}

void UFPSWeaponFXComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    StopEmission();
    for (FFPSWeaponFXParticle& P : Particles) if (P.Mesh) P.Mesh->DestroyComponent();
    Particles.Reset();
    for (FFPSWeaponFXTracer& T : Tracers) if (T.Mesh) T.Mesh->DestroyComponent();
    Tracers.Reset();
    for(const auto& FX:EpicFXPool)if(FX)FX->DestroyComponent();
    EpicFXPool.Reset();
    if (SmokeStream) SmokeStream->DestroyComponent();
    if (FlashLight) FlashLight->DestroyComponent();
    Super::EndPlay(EndPlayReason);
}

int32 UFPSWeaponFXComponent::GetActiveEpicFXCount() const
{
    int32 Count=SmokeStream && SmokeStream->IsActive() ? 1 : 0;
    for(const auto& FX:EpicFXPool)if(FX&&FX->IsActive())++Count;
    return Count;
}

int32 UFPSWeaponFXComponent::GetActiveTracerCount() const
{
    int32 Count=0;
    for(const FFPSWeaponFXTracer& T:Tracers) if(T.bActive) ++Count;
    return Count;
}
