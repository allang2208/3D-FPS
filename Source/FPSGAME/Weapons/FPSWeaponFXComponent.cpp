#include "FPSWeaponFXComponent.h"
#include "TimerManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Super90WeaponAssets.h"
#include "TubeShotgunAssets.h"
#include "Saiga12KWeaponAssets.h"
#include "M24WeaponAssets.h"
#include "ShotgunBirdcageAssets.h"
#include "FPSImpactFXSubsystem.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "AKMSovietCalibration.h"
#include "A762WeaponAssets.h"
#include "LMG201WeaponAssets.h"
#include "PKMLowpolyWeaponAssets.h"
#include "ASH12WeaponAssets.h"
#include "CasingPortCalibration.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"

#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"
#include "HAL/IConsoleManager.h"

#include "WeaponFXPrivate.h"
using namespace WeaponFXRuntime;
namespace WeaponFXRuntime
{

// Optic firing presentation (LPVO 1-6x only). At high magnification the world
// muzzle flash leaves the narrow frustum almost completely, so the world layer is
// compensated with a damped, capped factor and a small forward offset instead of
// being made brighter. Presentation only: the muzzle socket, the shot direction
// and the trace are untouched.
TAutoConsoleVariable<float> ScopeWorldScaleExponent(TEXT("fps.Scope.WorldScaleExponent"),0.f,
    TEXT("Damped magnification exponent for the world muzzle flash (0 = off)."));
TAutoConsoleVariable<float> ScopeWorldScaleMax(TEXT("fps.Scope.WorldScaleMax"),2.5f,
    TEXT("Hard cap for the world muzzle flash compensation."));
TAutoConsoleVariable<float> ScopeWorldForwardCM(TEXT("fps.Scope.WorldForwardCM"),12.f,
    TEXT("Centimetres to push the world flash along the barrel at full compensation."));

TAutoConsoleVariable<float> SmokeIntensity(TEXT("fps.Smoke.Intensity"),1.f,
    TEXT("Muzzle smoke opacity multiplier for shot, continuous plume and heat tail (0-2)."));

// Tracer presentation knob (Docs/Weapons/ballistic-feel-options-20260921.md). Presentation
// only: the trace, the damage and the falloff are untouched.
TAutoConsoleVariable<float> TracerLengthScale(TEXT("fps.Tracer.LengthScale"),1.f,
    TEXT("Multiplier on the tracer streak window (1 = built-in 600/1400 cm rifle window)."));
// Fast rounds cross a room in a few frames, so a streak that vanishes the instant the round
// lands is hard to see at all. It now holds its last position and fades out instead.
TAutoConsoleVariable<float> TracerLingerSeconds(TEXT("fps.Tracer.LingerSeconds"),.12f,
    TEXT("Seconds a finished tracer streak stays visible and fades out (0 = vanish at once)."));
// Width and colour are the two knobs behind "too thin / not vivid"; both apply live, including
// to streaks already in flight (ApplyTracerTransform re-applies them every frame).
TAutoConsoleVariable<float> TracerWidthPixels(TEXT("fps.Tracer.PixelWidth"),4.f,
    TEXT("Tracer screen width in pixels at 1080p reference (higher = thicker beam)."));
TAutoConsoleVariable<float> TracerEmissionScale(TEXT("fps.Tracer.Emission"),2.6f,
    TEXT("Additive emission of the tracer. Very high values clip every channel and read white."));
TAutoConsoleVariable<FString> TracerTintSetting(TEXT("fps.Tracer.Tint"),TEXT("1.0,0.30,0.03"),
    TEXT("Tracer colour as R,G,B (linear, 0-1). Saturated red/orange stays vivid at low emission."));
bool ParseTracerTint(const FString& Text,FLinearColor& Out)
{
    TArray<FString> Parts;Text.ParseIntoArray(Parts,TEXT(","),true);
    if(Parts.Num()<3)return false;
    Out=FLinearColor(FCString::Atof(*Parts[0]),FCString::Atof(*Parts[1]),FCString::Atof(*Parts[2]),1.f);
    return true;
}
// "Strengthen the streak" tier: a wider dim halo pass around the core, and a real light that
// travels with the newest rounds so the beam spills onto the world around it.
TAutoConsoleVariable<float> TracerHaloWidth(TEXT("fps.Tracer.HaloWidth"),2.8f,
    TEXT("Width multiplier of the soft halo pass around the core (<=1 hides it)."));
TAutoConsoleVariable<float> TracerHaloEmission(TEXT("fps.Tracer.HaloEmission"),.55f,
    TEXT("Additive emission of the halo pass; keep well below fps.Tracer.Emission."));
TAutoConsoleVariable<float> TracerLightLumens(TEXT("fps.Tracer.LightLumens"),220.f,
    TEXT("Lumens of the travelling tracer light; 0 disables world lighting."));
TAutoConsoleVariable<float> TracerLightRadiusCM(TEXT("fps.Tracer.LightRadiusCM"),220.f,
    TEXT("Attenuation radius of the travelling tracer light in centimetres."));
// 汇聚附魔（整匣聚合弹）的专属表现：加粗、纯白、螺旋环绕。只走 bConverged 的段，
// 普通曳光一个字节都不变；全部参数实时可调，便于不改代码定观感。
TAutoConsoleVariable<float> TracerConvergedWidth(TEXT("fps.Tracer.Converged.Width"),2.f,
    TEXT("Core width multiplier of a convergence round (also scales the min and world caps)."));
TAutoConsoleVariable<FString> TracerConvergedTint(TEXT("fps.Tracer.Converged.Tint"),TEXT("1.0,1.0,1.0"),
    TEXT("Colour of a convergence round as R,G,B (linear). Default is pure white."));
TAutoConsoleVariable<float> TracerConvergedEmission(TEXT("fps.Tracer.Converged.Emission"),1.8f,
    TEXT("Additive emission of a convergence round; lower than the orange tracer so white does not clip."));
TAutoConsoleVariable<float> TracerConvergedHaloScale(TEXT("fps.Tracer.Converged.HaloScale"),1.f,
    TEXT("Extra halo width multiplier for a convergence round."));
TAutoConsoleVariable<int32> TracerConvergedSpiral(TEXT("fps.Tracer.Converged.Spiral"),1,
    TEXT("Draw the helical tube wrapped around a convergence round (0 = off)."));
TAutoConsoleVariable<float> TracerConvergedSpiralTurns(TEXT("fps.Tracer.Converged.SpiralTurns"),20.f,
    TEXT("Helix turns across the maximum streak length. Fixed pitch; only parameter changes rebuild geometry."));
TAutoConsoleVariable<float> TracerConvergedSpiralRadiusCM(TEXT("fps.Tracer.Converged.SpiralRadiusCM"),12.f,
    TEXT("World radius of the helix around the trajectory, in centimetres."));
TAutoConsoleVariable<float> TracerConvergedSpiralThicknessCM(TEXT("fps.Tracer.Converged.SpiralThicknessCM"),3.f,
    TEXT("World thickness of the helix tube itself, in centimetres."));
TAutoConsoleVariable<float> TracerConvergedSpiralEmission(TEXT("fps.Tracer.Converged.SpiralEmission"),2.f,
    TEXT("Additive emission of the helix tube (it shares the convergence tint)."));
TAutoConsoleVariable<float> TracerConvergedSpiralSpin(TEXT("fps.Tracer.Converged.SpiralSpinDeg"),540.f,
    TEXT("Helix spin around the trajectory in degrees per second (0 = static coil)."));
TAutoConsoleVariable<float> TracerConvergedLightScale(TEXT("fps.Tracer.Converged.LightScale"),1.3f,
    TEXT("Extra lumens for the travelling light of a convergence round (it also turns white)."));
TAutoConsoleVariable<float> TracerConvergedMaxWidthCM(TEXT("fps.Tracer.Converged.MaxWidthCM"),14.f,
    TEXT("Convergence core diameter cap; also limited to leave clearance inside the helix."));
// 白色光柱拖尾：汇聚弹从出膛点到弹头的整条弹道都发光，命中后原地停住再淡出。
// 默认做"宽而暗"：光柱靠宽度和低自发光读成柔和的光带，而不是一根硬管（线条感太强就不自然了）。
TAutoConsoleVariable<int32> TracerTrailOn(TEXT("fps.Tracer.Trail"),1,
    TEXT("Draw the lingering light column along a convergence round's travelled path (0 = off)."));
TAutoConsoleVariable<float> TracerTrailLingerSeconds(TEXT("fps.Tracer.Trail.LingerSeconds"),.5f,
    TEXT("Seconds the column holds after impact, followed by Trail.FadeSeconds."));
TAutoConsoleVariable<float> TracerTrailFadeSeconds(TEXT("fps.Tracer.Trail.FadeSeconds"),.35f,
    TEXT("Seconds for the column to fade after its post-impact hold."));
TAutoConsoleVariable<float> TracerTrailNearFadeCM(TEXT("fps.Tracer.Trail.NearFadeCM"),65.f,
    TEXT("World-space soft emergence distance from the muzzle, independent of total path length."));
TAutoConsoleVariable<float> TracerTrailWidth(TEXT("fps.Tracer.Trail.Width"),2.8f,
    TEXT("Light column width multiplier; wider + dimmer reads softer than a thin bright rod."));
TAutoConsoleVariable<float> TracerTrailEmission(TEXT("fps.Tracer.Trail.Emission"),.55f,
    TEXT("Additive emission of the light column; keep below fps.Tracer.Converged.Emission."));
// 光柱是唯一一条从枪口起就贴着视线轴的元件，宽度必须有世界上限：核心段的像素宽度在远距离
// 会被 28/12 cm 的世界上限接住，再乘宽度倍率就是 1.5 m 粗的管子——那已经不是"光柱"，
// 而是一个糊在玩家眼前的白色大盘子。
TAutoConsoleVariable<float> TracerTrailMaxWidthCM(TEXT("fps.Tracer.Trail.MaxWidthCM"),24.f,
    TEXT("Hard world cap on the light column width in centimetres (keeps it a beam, not a wall)."));
TAutoConsoleVariable<float> TracerTrailMaxLengthCM(TEXT("fps.Tracer.Trail.MaxLengthCM"),0.f,
    TEXT("Optional cap on the light column length in centimetres (0 = the whole trajectory)."));
TAutoConsoleVariable<float> TracerTrailFadePower(TEXT("fps.Tracer.Trail.FadePower"),1.5f,
    TEXT("Fade exponent of the light column: above 1 it dims early and leaves a long faint tail."));
// 排查用：每次汇聚射击打一到两行日志（开段 / 收段），普通曳光不打。
// 汇聚射击很稀（一次打空弹匣 + 4.6 s 换弹），所以默认开着的噪音可以忽略。
TAutoConsoleVariable<int32> TracerDiag(TEXT("fps.Tracer.Diag"),1,
    TEXT("Log one line per convergence tracer open/close so the trail path can be verified in the log."));

}
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
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Convergence(
        TEXT("/Game/Weapons/GunplayFX/M_ConvergenceBeamV2.M_ConvergenceBeamV2"));
    ConvergedMaterial = Convergence.Object;
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EpicMuzzle(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10.NS_FPS_MuzzleFlashV10"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> EpicSmoke(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV15.NS_FPS_MuzzleSmokeStreamV15"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> SmokeImpulse(TEXT("/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15.NS_FPS_MuzzleSmokeShotV15"));
    EpicMuzzleSystem=EpicMuzzle.Object;EpicSmokeSystem=EpicSmoke.Object;
    SmokeImpulseSystem=SmokeImpulse.Object;
}

void UFPSWeaponFXComponent::SetBigBlindEnabled(bool Enabled)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_DedicatedServer)Enabled=false;
    if(bBigBlindEnabled==Enabled)return;
    bBigBlindEnabled=Enabled;
    if(!Enabled)
    {
        if(BigBlindLoad){BigBlindLoad->CancelHandle();BigBlindLoad.Reset();}
        if(BigBlindGlow)BigBlindGlow->SetVisibility(false);
        if(BigBlindLight)BigBlindLight->SetVisibility(false);
        return;
    }
    if(BigBlindMID){SetComponentTickEnabled(true);UpdateBigBlindGlow();return;}
    if(auto* Material=BigBlindMaterial.Get()){CreateBigBlindGlow(Material);return;}
    BigBlindLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(BigBlindMaterial.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this]()
        {
            if(bBigBlindEnabled)CreateBigBlindGlow(BigBlindMaterial.Get());
            BigBlindLoad.Reset();
        }));
}
void UFPSWeaponFXComponent::CreateBigBlindGlow(UMaterialInterface* Material)
{
    if(!Material||!CardMesh||!bBigBlindEnabled||!IsValid(WeaponMesh)||!IsValid(Camera))return;
    if(!BigBlindGlow)
    {
        BigBlindGlow=NewObject<UStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(BigBlindGlow);
        BigBlindGlow->SetMobility(EComponentMobility::Movable);
        BigBlindGlow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        BigBlindGlow->SetGenerateOverlapEvents(false);BigBlindGlow->SetCastShadow(false);
        BigBlindGlow->SetOnlyOwnerSee(true);
        BigBlindGlow->SetFirstPersonPrimitiveType(WeaponMesh->FirstPersonPrimitiveType);
        BigBlindGlow->SetCanEverAffectNavigation(false);BigBlindGlow->bReceivesDecals=false;
        BigBlindGlow->SetStaticMesh(CardMesh);BigBlindGlow->SetupAttachment(WeaponMesh);
        BigBlindGlow->RegisterComponent();
        BigBlindMID=UMaterialInstanceDynamic::Create(Material,BigBlindGlow);BigBlindGlow->SetMaterial(0,BigBlindMID);
        BigBlindLight=NewObject<UPointLightComponent>(GetOwner());GetOwner()->AddInstanceComponent(BigBlindLight);
        BigBlindLight->SetMobility(EComponentMobility::Movable);BigBlindLight->SetupAttachment(WeaponMesh);
        BigBlindLight->SetCastShadows(false);BigBlindLight->SetLightColor(FLinearColor(1.f,.55f,.06f));
        BigBlindLight->SetIntensityUnits(ELightUnits::Lumens);BigBlindLight->SetAttenuationRadius(32.f);
        BigBlindLight->SetSourceRadius(2.f);BigBlindLight->SetSpecularScale(.15f);
        BigBlindLight->SetVolumetricScatteringIntensity(0.f);BigBlindLight->RegisterComponent();
    }
    SetComponentTickEnabled(true);UpdateBigBlindGlow();
}
void UFPSWeaponFXComponent::UpdateBigBlindGlow()
{
    if(!BigBlindGlow||!BigBlindLight||!BigBlindMID)return;
    const bool Visible=bBigBlindEnabled&&IsValid(WeaponMesh)&&IsValid(Camera)
        &&WeaponMesh->IsVisible()&&!GetOwner()->IsHidden();
    BigBlindGlow->SetVisibility(Visible);BigBlindLight->SetVisibility(Visible);
    if(!Visible)return;
    // 直接使用已有枪口接口：包含消音器/左手配件出口，检视与换弹仍逐帧跟随。
    const FVector Position=MuzzleLocation()+MuzzleForward()*1.2f;
    const float Phase=FMath::Fmod(GetWorld()->GetTimeSeconds()/1.4f,1.f);
    const float Pulse=.5f-.5f*FMath::Cos(Phase*2.f*PI);
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const float AimDim=Character&&Character->IsAiming()?.35f:1.f;
    BigBlindGlow->SetWorldLocationAndRotation(Position,FRotationMatrix::MakeFromZ(Camera->GetComponentLocation()-Position).Rotator());
    BigBlindGlow->SetWorldScale3D(FVector(.08f,.08f,.08f));
    BigBlindMID->SetScalarParameterValue(TEXT("Phase"),Phase);
    BigBlindMID->SetScalarParameterValue(TEXT("Strength"),AimDim);
    BigBlindLight->SetWorldLocation(Position);BigBlindLight->SetIntensity((1.f+5.f*Pulse)*AimDim);
}
void UFPSWeaponFXComponent::InitializeWorldTracers()
{
    bWorldGun=true;
    bTracersOnly=true;
    WorldViewCamera=UGameplayStatics::GetPlayerCameraManager(this,0);
    bReady=GetNetMode()!=NM_DedicatedServer && CylinderMesh && TracerMaterial;
}

void UFPSWeaponFXComponent::Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera)
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(PumpEjectTimer);
    if(InWeaponMesh&&InWeaponMesh->GetSkeletalMeshAsset()&&(TubeShotgunAssets::MatchesMesh(InWeaponMesh->GetSkeletalMeshAsset()->GetPathName())||Saiga12KWeaponAssets::Matches(InWeaponMesh))&&!Super90CasingMesh)
    {
        Super90CasingMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/Super90/Cransh20261006/Parts/SM_Super90_Casing"));
        Super90CasingMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/Super90/Cransh20261006/Materials/M_S90_12gauge"));
    }

    if (WeaponMesh) RemoveTickPrerequisiteComponent(WeaponMesh);
    StopEmission();
    for (FFPSWeaponFXParticle& P : Particles) Release(P);
    for (FFPSWeaponFXTracer& T : Tracers) ReleaseTracer(T);
    WeaponMesh = InWeaponMesh;
    Camera = InCamera;
    WorldViewCamera=bWorldGun?UGameplayStatics::GetPlayerCameraManager(this,0):nullptr;
    bReady = false;
    if (!GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer || !WeaponMesh || !Camera) return;
    AddTickPrerequisiteComponent(WeaponMesh);
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        AddTickPrerequisiteComponent(Body);
        if(auto* Mesh=Body->GetBodyMesh())AddTickPrerequisiteComponent(Mesh);
    }
    // M24 retains its authored port bone instead of the shared socket alias.
    // Resolve per mesh so switching away never changes another gun's settings.
    const bool bM24=WeaponMesh->GetSkeletalMeshAsset()
        &&WeaponMesh->GetSkeletalMeshAsset()->GetPathName()==M24WeaponAssets::MeshPath;
    const FName ResolvedEjectSocket=bM24?FName(TEXT("WPN_Eject")):EjectSocket;
    bReady = CardMesh && CylinderMesh && FlashMaterial && SmokeMaterial && BrassMaterial
        && WeaponMesh->DoesSocketExist(MuzzleSocket) && WeaponMesh->DoesSocketExist(ResolvedEjectSocket);
    if (!bReady)
    {
        UE_LOG(LogTemp, Error, TEXT("GUNPLAY_FX_NOT_READY materials=%d muzzle=%d eject=%d. Run Tools/AssetPipeline/build_gunplay_fx.py."),
            !!(FlashMaterial && SmokeMaterial && BrassMaterial), WeaponMesh->DoesSocketExist(MuzzleSocket), WeaponMesh->DoesSocketExist(ResolvedEjectSocket));
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
    // Sight bone rotations are not a universal rail normal: on the pistols and
    // Super90 they can point along the bore. Build a fixed frame from positions
    // in the mesh bind pose, never from the camera or animated folding sights.
    const FVector Up = Rear.GetLocation() - Bone(TEXT("WPN_SOCKET_Muzzle")).GetLocation();
    CasingFrameInRoot = Root.GetRotation().Inverse() * FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat();
    CasingAnchorSocket = ResolvedEjectSocket;
    CasingPortInAnchor = FVector::ZeroVector;
    CasingOutwardSide = 1.0f;
    if (const auto* Port = CasingPortCalibration::Find(WeaponMesh->GetSkeletalMeshAsset()->GetPathName()))
    {
        CasingAnchorSocket = Port->Anchor;
        // Native WPN_root is scaled 100x. Convert measured cm to its local units,
        // then to the receiver/slide anchor so the opening follows its own part.
        CasingPortInAnchor = Bone(Port->Anchor).InverseTransformPosition(
            Root.TransformPosition(Port->RootCentimetres * .01f));
        CasingOutwardSide = Port->OutwardSide;
    }
    PreviousMuzzlePosition = MuzzleLocation();
    PreviousMuzzleForward = MuzzleForward();
    UE_LOG(LogTemp, Display, TEXT("GUNPLAY_FX_READY muzzle=%s eject=%s max_particles=%d"), *MuzzleSocket.ToString(), *CasingAnchorSocket.ToString(), MaxParticles);
    PrewarmShotFX();
}

void UFPSWeaponFXComponent::ResolveCasingAsset(bool bRifle, bool bSuper90, UStaticMesh*& OutMesh, UMaterialInterface*& OutMaterial) const
{
    const bool bUseSuper90Mesh = bSuper90 && Super90CasingMesh && Super90CasingMaterial;
    const bool bUseRifleMesh = bRifle && RifleCasingMesh && RifleCasingMaterial;
    OutMesh = bUseSuper90Mesh ? Super90CasingMesh.Get() : bUseRifleMesh ? RifleCasingMesh.Get() : CylinderMesh.Get();
    OutMaterial = bUseSuper90Mesh ? Super90CasingMaterial.Get() : bUseRifleMesh ? RifleCasingMaterial.Get() : BrassMaterial.Get();
}

void UFPSWeaponFXComponent::PrewarmShotFX()
{
    if (!bReady || !GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer) return;
    // The Niagara instances were previously created inside the first shot: SetAsset and
    // registration issue the async system compile, and the first Activate waited on it.
    // Doing it at equip hides the compile inside the already-blocking weapon swap.
    // Activate+DeactivateImmediate forces the instance build; deactivated before any
    // tick it emits nothing.
    const auto WarmSystem = [this](UNiagaraSystem* System) -> UNiagaraComponent*
    {
        UNiagaraComponent* FX = NewObject<UNiagaraComponent>(GetOwner());
        FX->SetAutoActivate(false);
        FX->SetAutoDestroy(false);
        FX->SetTickBehavior(ENiagaraTickBehavior::ForceTickLast);
        FX->SetAsset(System);
        FX->SetCastShadow(false);
        FX->RegisterComponent();
        FX->Activate(false);
        FX->DeactivateImmediate();
        return FX;
    };
    const auto WarmIntoPool = [this,&WarmSystem](UNiagaraSystem* System)
    {
        if (!System || EpicFXPool.ContainsByPredicate([System](const UNiagaraComponent* FX) { return FX->GetAsset() == System; })) return;
        EpicFXPool.Add(WarmSystem(System));
    };
    WarmIntoPool(EpicMuzzleSystem.Get());
    WarmIntoPool(SmokeImpulseSystem.Get());
    if (!SmokeStream && EpicSmokeSystem.Get()) SmokeStream = WarmSystem(EpicSmokeSystem.Get());

    // The first casing and tracer also allocate their mesh components and dynamic
    // materials inside the shot path; build and release one entry each now.
    if (!ShouldHideCasings())
    {
        const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
        const bool bRifle = bWorldGun?!bWorldPistol:(!bIndependentPistol && Character && !Character->IsPistolWeapon());
        const bool bSuper90 = bRifle && WeaponMesh && WeaponMesh->GetSkeletalMeshAsset()
            &&(TubeShotgunAssets::MatchesMesh(WeaponMesh->GetSkeletalMeshAsset()->GetPathName())||Saiga12KWeaponAssets::Matches(WeaponMesh));
        UStaticMesh* Geometry = nullptr;
        UMaterialInterface* Surface = nullptr;
        ResolveCasingAsset(bRifle, bSuper90, Geometry, Surface);
        if (Geometry && Surface)
            if (FFPSWeaponFXParticle* P = Acquire(WeaponFX::Casing, Geometry, Surface)) Release(*P);
    }
    if (TracerMaterial && CylinderMesh)
        if (FFPSWeaponFXTracer* T = AcquireTracer(INDEX_NONE)) ReleaseTracer(*T);
}

void UFPSWeaponFXComponent::SetIndependentPistol(bool Revolver,bool Suppressed,USceneComponent* Exit)
{
    bIndependentPistol=true;bIndependentRevolver=Revolver;IndependentSuppressed=Suppressed;
    IndependentExit=Exit;bUseCharacterMuzzle=false;
}
FTransform UFPSWeaponFXComponent::PresentationFrame(const FTransform& NativeFrame,const USceneComponent* Anchor) const
{
    if(bWorldGun)return NativeFrame;
    if(const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();Body&&Body->IsThirdPersonViewEnabled())
    {
        FTransform WorldFrame;
        if(Body->ResolveWorldWeaponFrame(WeaponMesh,Anchor,NativeFrame,WorldFrame))return WorldFrame;
    }
    return NativeFrame;
}
void UFPSWeaponFXComponent::SetWorldMuzzle(UStaticMeshComponent* Part,FVector Tip,FVector Axis)
{WorldMuzzlePart=Part;WorldMuzzleTip=Tip;WorldMuzzleAxis=Axis;}
FTransform UFPSWeaponFXComponent::MuzzleTransform() const
{
    if(bUseMuzzleSnapshot)return MuzzleSnapshot;
    if(bWorldGun&&WorldMuzzlePart.IsValid())
        return FTransform(WorldMuzzlePart->GetComponentQuat().RotateVector(WorldMuzzleAxis).Rotation(),
            WorldMuzzlePart->GetComponentTransform().TransformPosition(WorldMuzzleTip));
    if(bWorldGun)return IsValid(WeaponMesh)?WorldMuzzleInRoot*WeaponMesh->GetSocketTransform(TEXT("WPN_root")):MuzzleSnapshot;
    if(IsValid(IndependentExit))return PresentationFrame(IndependentExit->GetComponentTransform(),IndependentExit);
    if(bUseCharacterMuzzle)if(const auto* C=Cast<AFPSGAMECharacter>(GetOwner()))return C->GetEffectiveMuzzleTransform();
    if(!IsValid(WeaponMesh))return MuzzleSnapshot;
    // Imported WPN local Y lies along the bore; mirrored source rigs need a sign correction.
    FVector Forward;
    if(bWorldGun||bIndependentPistol)Forward=(WeaponMesh->GetSocketLocation(TEXT("WPN_FrontSight"))-WeaponMesh->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    else
    {
        Forward=WeaponMesh->GetSocketQuaternion(MuzzleSocket).GetAxisY();
        const auto* Pawn=Cast<APawn>(GetOwner());
        const FVector Aim=bWorldGun&&Pawn?Pawn->GetBaseAimRotation().Vector():Camera->GetForwardVector();
        if(FVector::DotProduct(Forward,Aim)<0.f)Forward=-Forward;
    }
    return PresentationFrame(FTransform(Forward.Rotation(),WeaponMesh->GetSocketLocation(MuzzleSocket)));
}
FVector UFPSWeaponFXComponent::MuzzleLocation() const
{return MuzzleTransform().GetLocation();}
FVector UFPSWeaponFXComponent::MuzzleForward() const
{return MuzzleTransform().GetRotation().GetAxisX();}

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
    Result->Mesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);
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
    Result->bReloadDrop = false;
    Result->bSettled = false;
    SetComponentTickEnabled(true);
    return Result;
}

void UFPSWeaponFXComponent::Release(FFPSWeaponFXParticle& P)
{
    P.bActive = false;
    if (P.Mesh) P.Mesh->SetVisibility(false);
}

float UFPSWeaponFXComponent::MuzzleFlashVisualScale() const
{
    if(bWorldGun)
    {
        const auto* Part=WorldMuzzlePart.Get();
        const UStaticMesh* Mesh=Part?Part->GetStaticMesh():nullptr;
        return Mesh&&(Mesh->GetPathName()==ShotgunBirdcageAssets::MeshObjectPath
            ||Mesh->GetPathName()==TEXT("/Game/Weapons/Saiga12K/Detail20261018/Attachments/SM_Saiga12K_shotgun_birdcage_flash_hider.SM_Saiga12K_shotgun_birdcage_flash_hider"))
            ?ShotgunBirdcageAssets::FlashVisualScale:1.f;
    }
    if(bIndependentPistol)return 1.f;
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    return Character&&(Character->IsSuper90Weapon()||Character->IsSaiga12KWeapon())&&Character->GetGunsmithMuzzle()==ShotgunBirdcageAssets::Part
        ?ShotgunBirdcageAssets::FlashVisualScale:1.f;
}

void UFPSWeaponFXComponent::ApplyParticleTransform(FFPSWeaponFXParticle& P)
{
    const float Life = FMath::Clamp(P.Age / P.Lifetime, 0.0f, 1.0f);
    FVector Size = P.Size;
    float Alpha = P.Opacity * (1.0f - Life);
    FRotator Rotation = P.Rotation;
    if (P.Kind != WeaponFX::Casing)
    {
        Rotation = FRotationMatrix::MakeFromZ((bWorldGun&&WorldViewCamera.IsValid()?WorldViewCamera->GetCameraLocation():Camera->GetComponentLocation()) - P.Position).Rotator();
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
    // Only casings need swept collision substeps. Their finite lifetime bounds
    // this loop; even the capped case consumes the entire interval, never discarding time.
    const int32 Steps = P.Kind == WeaponFX::Casing
        ? FMath::Clamp(FMath::CeilToInt(DeltaTime / 0.025f), 1, 64) : 1;
    const float Step = DeltaTime / Steps;
    for (int32 I = 0; I < Steps; ++I)
    {
        if (P.Age + Step >= P.Lifetime) { Release(P); return; }
        P.Age += Step;
        if(P.bSettled)continue;
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
        if (P.Kind == WeaponFX::Casing && (!P.bBounced || P.bReloadDrop))
        {
            FHitResult Bounce;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(WeaponCasing), false, GetOwner());
            if (GetWorld()->LineTraceSingleByChannel(Bounce, OldPosition, P.Position, ECC_Visibility, Params))
            {
                const float AfterHit = Step * (1.0f - FMath::Clamp(Bounce.Time, 0.0f, 1.0f));
                P.Position = Bounce.ImpactPoint + Bounce.ImpactNormal * 0.8f;
                const FVector HitVelocity = P.Velocity - P.Acceleration * AfterHit;
                if(P.bReloadDrop && (P.bBounced || HitVelocity.SizeSquared()<FMath::Square(35.f)))
                {
                    P.Velocity=P.Acceleration=FVector::ZeroVector;
                    P.Spin=FRotator::ZeroRotator;P.bSettled=true;
                    continue;
                }
                P.Velocity = FMath::GetReflectionVector(HitVelocity, Bounce.ImpactNormal) * 0.24f;
                // Consume the post-impact part of this substep as well.
                P.Position += P.Velocity * AfterHit + P.Acceleration * (0.5f * AfterHit * AfterHit);
                P.Velocity += P.Acceleration * AfterHit;
                P.Rotation -= P.Spin * (AfterHit * 0.70f);
                P.Spin *= 0.30f;
                P.bBounced = true;
                if(!P.bReloadDrop)P.Lifetime = FMath::Min(P.Lifetime, P.Age - AfterHit + 0.25f);
                if (P.Age >= P.Lifetime) { Release(P); return; }
            }
        }
    }
}

void UFPSWeaponFXComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if(bTracersOnly)
    {
        TickTracers(DeltaTime);
        SetComponentTickEnabled(GetActiveTracerCount()>0);
        return;
    }
    if (!IsValid(WeaponMesh) || !IsValid(Camera))
    {
        StopEmission();
        for (FFPSWeaponFXParticle& P : Particles) Release(P);
        for (FFPSWeaponFXTracer& T : Tracers) ReleaseTracer(T);
        SetComponentTickEnabled(false);
        return;
    }
    // All gun-attached effects consume the same completed body pose this tick.
    // Emitted smoke/tracers remain in world space after their birth.
    const FTransform Frame=MuzzleTransform();
    TGuardValue<FTransform> FrameGuard(MuzzleSnapshot,Frame);
    TGuardValue<bool> SnapshotGuard(bUseMuzzleSnapshot,true);
    UpdateBigBlindGlow();
    if(!bReady){if(!bBigBlindEnabled)SetComponentTickEnabled(false);return;}
    for(const auto& FX:EpicFXPool)if(FX->IsActive()&&FX->GetAsset()==EpicMuzzleSystem)
        FX->SetWorldLocationAndRotation(MuzzleLocation(),MuzzleForward().Rotation());
    DeltaTime = FMath::Max(0.0f, DeltaTime);
    if (FlashBirthFrame != GFrameCounter) FlashTime = FMath::Max(0.0f, FlashTime - DeltaTime);
    if (FlashLight)
    {
        if (FlashTime > 0.0f)
        {
            FlashLight->SetWorldLocation(MuzzleLocation() + MuzzleForward() * 2.0f);
            FlashLight->SetIntensity(350.0f * FMath::Clamp(FlashScale, 0.0f, 2.0f) * LastADSMultiplier * LastWeaponFlashMultiplier * LastSuppression * FMath::Square(FlashTime / 0.045f));
        }
        else FlashLight->SetVisibility(false);
    }
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
    TickTracers(DeltaTime);
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
        && GetActiveTracerCount() == 0 && (!SmokeStream || !SmokeStream->IsActive()) && !bBigBlindEnabled)
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
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(PumpEjectTimer);
    SetBigBlindEnabled(false);
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
    for (FFPSWeaponFXTracer& T : Tracers)
    {
        if(T.Mesh)T.Mesh->DestroyComponent();
        if(T.HaloMesh)T.HaloMesh->DestroyComponent();
        if(T.SpiralMesh)T.SpiralMesh->DestroyComponent();
        if(T.TrailMesh)T.TrailMesh->DestroyComponent();
    }
    Tracers.Reset();
    for(auto Light:TracerLights)if(Light)Light->DestroyComponent();
    TracerLights.Reset();
    for(const auto& FX:EpicFXPool)if(FX)FX->DestroyComponent();
    EpicFXPool.Reset();
    if (SmokeStream) SmokeStream->DestroyComponent();
    if (FlashLight) FlashLight->DestroyComponent();
    if (BigBlindGlow) BigBlindGlow->DestroyComponent();
    if (BigBlindLight) BigBlindLight->DestroyComponent();
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
