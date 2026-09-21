#include "FPSWeaponFXComponent.h"
#include "FPSImpactFXSubsystem.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "AKMSovietCalibration.h"
#include "A762WeaponAssets.h"
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
    constexpr float StreamMaxLifetime = 1.1f;
    // Tracer streaks (see Docs/Weapons/tracer-upgrade-plan-20260921.md).
    // The visible dash is clamped to a per-class window instead of "one frame of
    // travel", which used to make it frame-rate dependent and full of gaps.
    constexpr float TracerRifleLengthCM = 250.f;
    constexpr float TracerRifleMaxCM = 350.f;   // 30 fps 下 9.5 m/s 级长枪仍不断线
    constexpr float TracerPistolLengthCM = 150.f;
    constexpr float TracerPistolMaxCM = 300.f;  // 高速手枪弹单段无法同时做到不断线又不成光柱
    constexpr float TracerPixelWidth = 1.7f;    // 原 1.1 像素过细，细亮线在 TSR 下闪且容易被 bloom 抹开
    constexpr float TracerMinDiameterCM = 0.9f;
    constexpr float TracerEmission = 7.5f;      // 原 14：亮度直接决定残影强度与过曝
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
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EpicSmoke(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV12.NS_FPS_MuzzleSmokeStreamV12"));
    EpicMuzzleSystem=EpicMuzzle.Object;EpicSmokeSystem=EpicSmoke.Object;
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
    T->bFlash=false;T->FlashAge=0.f;
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
        }
    }
    Result->bActive=true;
    Result->RoundId=RoundId;
    Result->TraveledCM=0.f;
    Result->FlashAge=0.f;
    Result->Head=FVector::ZeroVector;
    Result->Mesh->SetStaticMesh(CylinderMesh);
    if(!Result->Material)Result->Material=UMaterialInstanceDynamic::Create(TracerMaterial,Result->Mesh);
    Result->Mesh->SetMaterial(0,Result->Material);
    Result->Mesh->SetVisibility(true);
    Result->Material->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.63f,.18f));
    Result->Material->SetScalarParameterValue(TEXT("Emission"),WeaponFX::TracerEmission);
    Result->Material->SetScalarParameterValue(TEXT("Opacity"),1.f);
    SetComponentTickEnabled(true);
    return Result;
}

void UFPSWeaponFXComponent::ReleaseTracer(FFPSWeaponFXTracer& T)
{
    T.bActive=false;
    T.bFlash=false;
    T.RoundId=INDEX_NONE;
    if(T.Mesh)T.Mesh->SetVisibility(false);
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
    const float Diameter=FMath::Clamp(PixelWidth*WeaponFX::TracerPixelWidth,
        WeaponFX::TracerMinDiameterCM,ShouldHideCasings()?2.5f:5.f);
    T.Mesh->SetWorldLocationAndRotation(Center,FRotationMatrix::MakeFromZ(T.Head-Tail).Rotator());
    T.Mesh->SetWorldScale3D(FVector(Diameter,Diameter,FMath::Max(1.f,T.Length))/100.f);
    T.Material->SetScalarParameterValue(TEXT("Opacity"),
        T.bFlash?FMath::Clamp(1.f-T.FlashAge/WeaponFX::TracerFlashSeconds,0.f,1.f):1.f);
}

float UFPSWeaponFXComponent::TracerBaseLengthCM() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    return (bIndependentPistol||(Character&&Character->IsPistolWeapon()))
        ?WeaponFX::TracerPistolLengthCM:WeaponFX::TracerRifleLengthCM;
}

float UFPSWeaponFXComponent::TracerMaxLengthCM() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    return (bIndependentPistol||(Character&&Character->IsPistolWeapon()))
        ?WeaponFX::TracerPistolMaxCM:WeaponFX::TracerRifleMaxCM;
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
    const float TailRate = FMath::Lerp(10.f, 14.f, SmokeHeatAtLastShot) * TailFade;
    const float TargetRate = Now < SmokeTailUntil
        ? FMath::Lerp(FMath::Lerp(44.f, 48.f, Heat), TailRate, TailBlend) : 0.f;
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
    SmokeStream->SetVariableFloat(TEXT("User.SmokeScale"), FMath::Lerp(.28f, .13f, TailBlend) * LastADSMultiplier);
    SmokeStream->SetVariableFloat(TEXT("User.SmokeForwardSpeed"), FMath::Lerp(95.f, 22.f, TailBlend));
    SmokeStream->SetVariableFloat(TEXT("User.SmokeSpreadScale"), FMath::Clamp(SmokeSpreadScale, 1.f, 2.5f));
    SmokeStream->SetVariableFloat(TEXT("User.SmokeTailBlend"), TailBlend);
    // A gentle outward drift is sampled only at birth, so even a stationary
    // shooter leaves a thin trail beside the bore instead of stacking a curtain.
    SmokeStream->SetVariableVec3(TEXT("User.SmokeDrift"),
        Camera->GetRightVector() * FMath::Lerp(12.f, 7.f, TailBlend) + FVector::UpVector * 3.f);
    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    const bool bAiming = Character && Character->IsAiming();
    const float ViewOpacity = ShouldHideCasings() ? .17f : (bAiming ? .20f : .24f);
    const float LayerOpacity = FMath::Clamp(SmokeOpacity, 0.f, 1.f)
        * ViewOpacity * FMath::Lerp(1.f, .85f, Heat)
        * FMath::Lerp(1.f, .55f, TailBlend);
    SmokeStream->SetVariableLinearColor(TEXT("User.Smoke Color"), FLinearColor(.92f, .94f, .96f, LayerOpacity));
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
    SmokeFeedUntil = LastFXShotTime + FMath::Lerp(.18f, .24f, SmokeHeatAtLastShot);
    SmokeTailUntil = SmokeFeedUntil + FMath::Lerp(.45f, .80f, SmokeHeatAtLastShot);
    if (EpicSmokeSystem) UpdateSmokeStream(0.f);
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
    return Character && Character->GetGunsmithOpticVariant() == TEXT("lpvo_1_6x")
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
            const float LengthCM = Character->bUseASH12 ? ASH12WeaponAssets::TracerLengthCM
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
    // ballistics tick earlier this frame. A streak that was not refreshed is a round
    // that ended (or impacted), so it is retired immediately - no history pile-up.
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
        { ReleaseTracer(T); ++ExpiredTracerSegments; continue; }
        ApplyTracerTransform(T);
    }

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
