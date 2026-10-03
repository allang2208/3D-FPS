#include "FPSFireballProjectile.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "FPSMagicPreview.h"
#include "Components/LineBatchComponent.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/TerrainDestruction.h"
#include "../WorldGeneration/GrassDeform/GrassDeformSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/SphereComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Perception/AISense_Hearing.h"
#include "UObject/ConstructorHelpers.h"
#include "Net/UnrealNetwork.h"

namespace FireballImpactVisuals
{
    // Fixed asset calibration at the accepted level-one size, not another gameplay
    // growth formula. All spatial impact effects scale from the cast's actual radius.
    constexpr float BaselineRadius=210.375f;
    constexpr float BaselineCombustionScale=.765f;
    constexpr float BaselineLightRadius=360.f;
    constexpr float BaselineLightPeak=14000.f*(127.5f/180.f);
    constexpr float HeatStrength=.06f;
    constexpr float HeatDuration=.36f;
    constexpr float HeatFadeExponent=1.35f;
}

AFPSFireballProjectile::AFPSFireballProjectile()
{
    PrimaryActorTick.bCanEverTick=true;
    // 联机：服务端生成并驱动弹道，远端副本靠复制变换+相位字段演同款表现。
    bReplicates=true;SetReplicateMovement(true);
    Body=CreateDefaultSubobject<USphereComponent>(TEXT("Body"));SetRootComponent(Body);Body->InitSphereRadius(14);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Core=CreateDefaultSubobject<UNiagaraComponent>(TEXT("Core"));Core->SetupAttachment(Body);Core->SetAutoActivate(false);
    Trail=CreateDefaultSubobject<UNiagaraComponent>(TEXT("Trail"));Trail->SetupAttachment(Body);Trail->SetAutoActivate(false);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("FireLight"));Light->SetupAttachment(Body);Light->SetCastShadows(false);Light->SetLightColor(FLinearColor(1,.23f,.035f));Light->SetAttenuationRadius(240);Light->SetIntensity(0);
}
void AFPSFireballProjectile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSFireballProjectile,Shooter);
    DOREPLIFETIME(AFPSFireballProjectile,NetHoverDuration);
    DOREPLIFETIME(AFPSFireballProjectile,NetGravity);
    DOREPLIFETIME(AFPSFireballProjectile,NetRange);
    DOREPLIFETIME(AFPSFireballProjectile,NetRadius);
    DOREPLIFETIME(AFPSFireballProjectile,NetExplodePoint);
    DOREPLIFETIME(AFPSFireballProjectile,NetExplodeNormal);
    DOREPLIFETIME(AFPSFireballProjectile,bNetSurfaceHit);
    DOREPLIFETIME(AFPSFireballProjectile,bFlying);
    DOREPLIFETIME(AFPSFireballProjectile,bFinished);
}
void AFPSFireballProjectile::Prepare(UFPSFireballComponent* Ability,APawn* Caster,const FFireballCast& Snapshot,UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound)
{
    Source=Ability;Shooter=Caster;Cast=Snapshot;Explosion=ImpactFX;Wave=WaveMaterial;ImpactSound=HitSound;
    NetHoverDuration=Snapshot.HoverDuration;NetGravity=Snapshot.Gravity;NetRange=Snapshot.Range;NetRadius=Snapshot.Radius;
    Core->SetAsset(CoreFX);Core->SetVariableFloat(TEXT("User.Flight"),0.f);Core->SetVariableFloat(TEXT("User.FlightAge"),0.f);
    Core->SetRelativeScale3D(FVector(.01f));Core->Activate(true);Trail->SetAsset(TrailFX);
    Core->AddTickPrerequisiteActor(this);Trail->AddTickPrerequisiteActor(this);
    AddTickPrerequisiteActor(Caster);
    if(Ability)AddTickPrerequisiteComponent(Ability);
}
FVector AFPSFireballProjectile::HoverPosition(APawn* Caster)
{
    if(const auto* Ability=Caster->FindComponentByClass<UFPSFireballComponent>())return Ability->HeldOrbPosition();
    const auto* Camera=Caster->FindComponentByClass<UCameraComponent>();
    if(!Camera)return Caster->GetActorLocation()+Caster->GetActorForwardVector()*100;
    return Camera->GetComponentLocation()+Camera->GetForwardVector()*95-Camera->GetRightVector()*40-Camera->GetUpVector()*22;
}
void AFPSFireballProjectile::SetPresentationAssets(UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound)
{
    Explosion=ImpactFX;Wave=WaveMaterial;ImpactSound=HitSound;bAssetsAttached=1;
    if(CoreFX){Core->SetAsset(CoreFX);Core->SetVariableFloat(TEXT("User.Flight"),0.f);Core->SetVariableFloat(TEXT("User.FlightAge"),0.f);Core->Activate(true);}
    if(TrailFX)Trail->SetAsset(TrailFX);
}
void AFPSFireballProjectile::ResolveNetState()
{
    Cast.HoverDuration=NetHoverDuration;Cast.Gravity=NetGravity;Cast.Range=NetRange;Cast.Radius=NetRadius;
    if(!Shooter)return;
    if(!Source.IsValid())Source=Shooter->FindComponentByClass<UFPSFireballComponent>();
    if(!Source.IsValid())return;
    if(!bAssetsAttached)Source->AttachPresentationAssets(this);
    // 施法者本机：把复制到达的服务端球认领成本地表现态（手势收尾/发射队列/取消都读 Active）。
    if(Shooter->IsLocallyControlled())Source->AdoptNetOrb(this);
}
void AFPSFireballProjectile::LaunchAt(const FVector& AimPoint)
{
    if(bFlying||bFinished||!Shooter)return;
    PreviewAimPoint=AimPoint;bPreviewLaunchLocked=true;Launch();
}
void AFPSFireballProjectile::Launch()
{
    if(bFlying||bFinished||!Shooter)return;
    // Contact is evaluated before this projectile's tick. Catch up to the
    // player's current pose before detaching, including wall clearance.
    UpdateHover();
    const bool bUsePreview=bPreviewLaunchLocked;
    const FVector AimPoint=bUsePreview?PreviewAimPoint:FPSMagicPreview::AimPoint(Shooter.Get(),this);
    SetAimPreviewActive(false);
    // Launch from the actual hovering position, including any wall clearance;
    // the remote hand gesture does not pull or teleport the orb toward the hand.
    bFlying=true;FlightAge=0.f;
    LaunchPosition=GetActorLocation();
    LaunchVelocity=FPSMagicPreview::LaunchVelocity(LaunchPosition,AimPoint,Cast.Speed,Shooter->GetActorForwardVector());
    Velocity=LaunchVelocity;
    Core->SetVariableFloat(TEXT("User.Flight"),1.f);
    UpdateFlightFX(GetActorLocation());Trail->Activate(true);
}
void AFPSFireballProjectile::SetAimPreviewActive(bool bActive)
{
    bAimPreview=bActive;
    bPreviewLaunchLocked=false;
    if(bActive)PreviewPoints.Reset();
    // Segments carry a short lifetime, so stopping the refresh is enough to clear them.
    if(!bActive)FPSMagicPreview::Clear(AimPreviewLines);
}
void AFPSFireballProjectile::CommitAimPreview()
{
    if(!bAimPreview||bFlying||bFinished||!IsValid(Shooter.Get()))return;
    // Quick taps can precede the first preview tick. Otherwise preserve the
    // last displayed aim target while the launch origin keeps following.
    if(PreviewPoints.IsEmpty())RefreshAimPreview();
    SetAimPreviewActive(false);
    bPreviewLaunchLocked=true;
}
void AFPSFireballProjectile::RefreshAimPreview()
{
    if(!IsValid(Shooter.Get()))return;
    // One frame of segments only: the previous frame is dropped here so a fast camera pan
    // cannot leave a trail of stale lines behind the orb.
    FPSMagicPreview::BeginRefresh(AimPreviewLines,this);
    // Same arc Launch() builds: from the hovering orb toward the camera ray's first hit, then
    // dropping under the cast's gravity, so the preview shows where the orb will really land.
    const FVector AimPoint=FPSMagicPreview::AimPoint(Shooter.Get(),this);
    PreviewAimPoint=AimPoint;
    const FVector Start=GetActorLocation();
    LaunchPosition=Start;
    LaunchVelocity=FPSMagicPreview::LaunchVelocity(Start,AimPoint,Cast.Speed,Shooter->GetActorForwardVector());
    FPSMagicPreview::SamplePath(Shooter.Get(),this,Start,LaunchVelocity,Cast.Gravity,
        Cast.Range,14.f,PreviewPoints,false);
    FPSMagicPreview::DrawPath(AimPreviewLines,PreviewPoints);
}
void AFPSFireballProjectile::UpdateHover()
{
    if(!IsValid(Shooter.Get()))return;
    const FVector Desired=HoverPosition(Shooter.Get());
    // The authored trajectory already eases. Continue following through the
    // windup, without a second interpolator or freezing at input release.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballMove),false,Shooter.Get());Query.AddIgnoredActor(this);
    FHitResult Hit;
    const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,GetActorLocation(),Desired,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query);
    SetActorLocation(Blocked?Hit.Location:Desired);
    if(const auto* Camera=Shooter->FindComponentByClass<UCameraComponent>())Core->SetVisibility(FVector::Distance(Camera->GetComponentLocation(),GetActorLocation())>30);
}
void AFPSFireballProjectile::UpdateFlightFX(const FVector& PreviousPosition)
{
    // Core flames use local -X; trail particles keep their world-space birth
    // direction and position, so later actor/camera movement cannot lift them.
    SetActorRotation(Velocity.Rotation());
    Core->SetVariableFloat(TEXT("User.FlightAge"),FlightAge);
    Trail->SetVariableVec3(TEXT("User.FlightDirection"),Velocity.GetSafeNormal());
    Trail->SetVariableFloat(TEXT("User.FlightSpeed"),Velocity.Size());
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"),PreviousPosition);
    Trail->SetVariablePosition(TEXT("User.CurrentPosition"),GetActorLocation());
}
void AFPSFireballProjectile::Tick(float Delta)
{
    Super::Tick(Delta);
    // 客户副本：变换由复制驱动，本地只演 FX——不跑弹道模拟，不与复制位置打架。
    if(!HasAuthority())
    {
        ResolveNetState();
        if(bFinished)
        {
            ImpactAge+=Delta;
            const float Fade=FMath::Exp(-ImpactAge*18.f)*FMath::Clamp((.24f-ImpactAge)/.06f,0.f,1.f);
            Light->SetIntensity(ImpactLightPeak*Fade);
            if(ImpactAge>=.24f){Light->SetIntensity(0);SetActorTickEnabled(false);}
            return;
        }
        Age+=Delta;
        // 凝聚成长用本机时钟近似（~0.95s 抬手），复制延迟下比跟随远端手势状态更稳。
        const float GrowT=bFlying?1.f:FMath::Clamp(Age/.95f,0.f,1.f),Grow=GrowT*GrowT*(3-2*GrowT);
        Core->SetRelativeScale3D(FVector(FMath::Max(.01f,Grow)));
        const float Glow=.97f+.02f*FMath::Sin(Age*2.3f)+.01f*FMath::Sin(Age*3.7f+1.1f);
        Light->SetIntensity(1250*Grow*Glow);
        if(bFlying)
        {
            FlightAge+=Delta;
            if(ClientPrevPos.IsNearlyZero())ClientPrevPos=GetActorLocation();
            Velocity=(GetActorLocation()-ClientPrevPos)/FMath::Max(Delta,1e-4f);
            UpdateFlightFX(ClientPrevPos);
            ClientPrevPos=GetActorLocation();
        }
        return;
    }
    if(bFinished)
    {
        ImpactAge+=Delta;
        const float Fade=FMath::Exp(-ImpactAge*18.f)*FMath::Clamp((.24f-ImpactAge)/.06f,0.f,1.f);
        Light->SetIntensity(ImpactLightPeak*Fade);
        if(ImpactAge>=.24f){Light->SetIntensity(0);SetActorTickEnabled(false);}
        return;
    }
    if(!IsValid(Shooter.Get())||!Source.IsValid()){Destroy();return;}
    if(const auto* Health=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Destroy();return;}
    Age+=Delta;
    const float T=bFlying?1.f:Source->GatherFraction(),Grow=T*T*(3-2*T);
    Core->SetRelativeScale3D(FVector(FMath::Max(.01f,Grow)));
    // Small, slow variations support the roiling flame instead of rapid flicker.
    const float Glow=.97f+.02f*FMath::Sin(Age*2.3f)+.01f*FMath::Sin(Age*3.7f+1.1f);
    Light->SetIntensity(1250*Grow*Glow);
    if(!bFlying)
    {
        if(Age>=Cast.HoverDuration){Destroy();return;}
        UpdateHover();
        if(bAimPreview)RefreshAimPreview();
        return;
    }
    Core->SetVisibility(true);FlightAge+=Delta;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballMove),false,Shooter.Get());Query.AddIgnoredActor(this);
    FHitResult Hit;
    const FVector PreviousPosition=GetActorLocation();
    // Ballistic flight: the analytic position keeps the drop frame-rate independent, so the
    // preview line can reproduce the same arc with the same integration.
    const FVector Gravity(0,0,-Cast.Gravity);
    const FVector NextPosition=FPSMagicPreview::LimitStep(PreviousPosition,
        LaunchPosition+LaunchVelocity*FlightAge+.5f*Gravity*FlightAge*FlightAge,Cast.Range-Distance);
    Velocity=LaunchVelocity+Gravity*FlightAge;
    const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,PreviousPosition,NextPosition,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query);
    SetActorLocation(Blocked?Hit.Location:NextPosition);
    if(!bWaterContact)
        if(auto* Water=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
            bWaterContact=Water->TryFireCrossing(PreviousPosition,Blocked?FVector(Hit.ImpactPoint):NextPosition,Cast.Radius,false);
    Distance+=FVector::Distance(PreviousPosition,GetActorLocation());
    UpdateFlightFX(PreviousPosition);
    if(Blocked)Explode(&Hit);else if(Distance>=Cast.Range-UE_KINDA_SMALL_NUMBER)Explode(nullptr);
}
void AFPSFireballProjectile::PresentExplosion(const FVector& Contact,const FVector& Normal,bool bSurfaceHit)
{
    Core->DeactivateImmediate();Light->SetIntensity(0);Trail->Deactivate();
    const FRotator ImpactRotation=FRotationMatrix::MakeFromZ(Normal).Rotator();
    const float EffectScale=Cast.Radius/FireballImpactVisuals::BaselineRadius;
    // Same event, same foot: the grass flatten is stamped on the contact the crater used, so
    // the flattened tufts and the bowl stay concentric. Cast.Radius is the single radius this
    // cast shares between damage and impact presentation, hence a 1.0 multiplier.
    if(auto* GrassDeform=GetWorld()->GetSubsystem<UGrassDeformSubsystem>())
        GrassDeform->AddImpulse(Contact,Cast.Radius*GrassDeformTuning::FireballRadiusMultiplier,
            GrassDeformTuning::FireballImpulseStrength,GrassDeformTuning::FireballImpulseWaveSpeed);
    // Set the hit contract before activation, including when taking a pooled component.
    // The local-space transform scales spread; Niagara sprite sizes are world
    // units, so the same growth must also be applied explicitly in the system.
    if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,Explosion,Contact+Normal*8,ImpactRotation,FVector(EffectScale*FireballImpactVisuals::BaselineCombustionScale),true,false,ENCPoolMethod::AutoRelease))
    {
        FX->SetVariableFloat(TEXT("User.SurfaceHit"),bSurfaceHit?1.f:0.f);
        FX->SetVariableVec3(TEXT("User.LocalUp"),ImpactRotation.UnrotateVector(FVector::UpVector));
        FX->SetVariableFloat(TEXT("User.ImpactGrowth"),EffectScale-1.f);
        if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Budget->ConfigureSmoke(FX,9,bWaterContact);
        FX->Activate(true);
    }
    const FVector WaveOrigin=Contact+(bSurfaceHit?Normal*4:FVector::ZeroVector);
    if(Wave)if(auto* Ring=GetWorld()->SpawnActor<AFireballShockwave>(WaveOrigin,ImpactRotation))Ring->Setup(Wave,Cast.Radius,bSurfaceHit);
    // One short, shadowed warm flash lights the actual contact environment.
    Light->SetWorldLocation(Contact+Normal*22);
    Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetCastShadows(true);
    Light->SetLightColor(FLinearColor(1.f,.48f,.13f));
    Light->SetAttenuationRadius(FireballImpactVisuals::BaselineLightRadius*EffectScale);
    ImpactLightPeak=FireballImpactVisuals::BaselineLightPeak*EffectScale;
    Light->SetIntensity(ImpactLightPeak);
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Contact,.72f,FMath::FRandRange(.96f,1.04f));
}
void AFPSFireballProjectile::OnRep_Finished()
{
    if(!bFinished||bExplosionPresented)return;
    bExplosionPresented=1;
    PresentExplosion(NetExplodePoint,NetExplodeNormal,bNetSurfaceHit!=0);
}
void AFPSFireballProjectile::Explode(const FHitResult* Hit)
{
    if(bFinished)return;bFinished=true;ImpactAge=0;
    const FVector Center=GetActorLocation();
    const FVector Normal=Hit?FVector(Hit->ImpactNormal):-Velocity.GetSafeNormal();
    const FVector Contact=Hit?FVector(Hit->ImpactPoint):Center;
    // 复制契约：远端副本靠这组字段在 OnRep_Finished 播同款爆炸表现。
    NetExplodePoint=Contact;NetExplodeNormal=Normal;bNetSurfaceHit=Hit!=nullptr;
    if(!bExplosionPresented){bExplosionPresented=1;PresentExplosion(Contact,Normal,Hit!=nullptr);}
    if(HasAuthority())
    {
        // Terrain damage: the hills heightfield gets a stamped crater. The hub arena is a
        // static floor and stays unchanged. 权威侧刻痕经 NetEdits 确定性下发，远端不重复刻。
        TerrainDestruction::CarveCrater(this,Contact,Normal,Cast.Radius);
        UAISense_Hearing::ReportNoiseEvent(this,Center,1.f,Shooter.Get(),1600,TEXT("Fireball"));
        // Keep the collision bone for direct-hit weakpoints; airbursts have no hit.
        // 联机：客人的球结算到自己的影子档案；主机玩家的球回落本机单例。
        UColdSteelStatusModel* P=nullptr;
        if(const auto* Char=::Cast<AFPSGAMECharacter>(Shooter.Get()))P=Char->GetNetShadowProfile();
        if(!P)P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const FVector WaveOrigin=Contact+(Hit?Normal*4:FVector::ZeroVector);
        if(P)P->ApplyFireballExplosion(Shooter.Get(),WaveOrigin,Cast,Hit);
    }
    if(Source.IsValid())Source->ProjectileFinished(this);Source.Reset();
    SetLifeSpan(1.2f); // Let the world-space trail finish its existing particles.
}
void AFPSFireballProjectile::EndPlay(const EEndPlayReason::Type Reason)
{ if(Source.IsValid())Source->ProjectileFinished(this);Source.Reset();Super::EndPlay(Reason); }

AFireballShockwave::AFireballShockwave()
{
    PrimaryActorTick.bCanEverTick=true;Mesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ring"));SetRootComponent(Mesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));Mesh->SetStaticMesh(Plane.Object);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));AirShell=Sphere.Object;
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetReceivesDecals(false);
}
void AFireballShockwave::Setup(UMaterialInterface* Material,float Radius,bool bSurfaceHit)
{
    MaxRadius=Radius;
    if(!bSurfaceHit)Mesh->SetStaticMesh(AirShell);
    Dynamic=Mesh->CreateDynamicMaterialInstance(0,Material);
    if(Dynamic)
    {
        Dynamic->SetScalarParameterValue(TEXT("SurfaceHit"),bSurfaceHit?1.f:0.f);
        Dynamic->SetScalarParameterValue(TEXT("Opacity"),1.f);
        Dynamic->SetScalarParameterValue(TEXT("HeatStrength"),FireballImpactVisuals::HeatStrength);
    }
    SetActorScale3D(FVector(FMath::Max(.01f,MaxRadius*.08f/50.f)));
    SetLifeSpan(FireballImpactVisuals::HeatDuration+.04f);
}
void AFireballShockwave::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;const float T=FMath::Clamp(Age/FireballImpactVisuals::HeatDuration,0.f,1.f);
    const float Expansion=.08f+.92f*(1-FMath::Pow(1-T,3.f));
    SetActorScale3D(FVector(FMath::Max(.01f,MaxRadius*2/100*Expansion)));
    if(Dynamic)Dynamic->SetScalarParameterValue(TEXT("Opacity"),FMath::Pow(1-T,FireballImpactVisuals::HeatFadeExponent));
}
