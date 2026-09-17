#include "FPSFireballProjectile.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TerrainDestruction.h"
#include "../Monsters/FPSCombatHealthComponent.h"
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
    Body=CreateDefaultSubobject<USphereComponent>(TEXT("Body"));SetRootComponent(Body);Body->InitSphereRadius(14);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Core=CreateDefaultSubobject<UNiagaraComponent>(TEXT("Core"));Core->SetupAttachment(Body);Core->SetAutoActivate(false);
    Trail=CreateDefaultSubobject<UNiagaraComponent>(TEXT("Trail"));Trail->SetupAttachment(Body);Trail->SetAutoActivate(false);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("FireLight"));Light->SetupAttachment(Body);Light->SetCastShadows(false);Light->SetLightColor(FLinearColor(1,.23f,.035f));Light->SetAttenuationRadius(240);Light->SetIntensity(0);
}
void AFPSFireballProjectile::Prepare(UFPSFireballComponent* Ability,APawn* Caster,const FFireballCast& Snapshot,UNiagaraSystem* CoreFX,UNiagaraSystem* TrailFX,UNiagaraSystem* ImpactFX,UMaterialInterface* WaveMaterial,USoundBase* HitSound)
{
    Source=Ability;Shooter=Caster;Cast=Snapshot;Explosion=ImpactFX;Wave=WaveMaterial;ImpactSound=HitSound;
    Core->SetAsset(CoreFX);Core->SetVariableFloat(TEXT("User.Flight"),0.f);Core->SetVariableFloat(TEXT("User.FlightAge"),0.f);
    Core->SetRelativeScale3D(FVector(.01f));Core->Activate(true);Trail->SetAsset(TrailFX);
    Core->AddTickPrerequisiteActor(this);Trail->AddTickPrerequisiteActor(this);
    AddTickPrerequisiteActor(Caster);
    AddTickPrerequisiteComponent(Ability);
}
FVector AFPSFireballProjectile::HoverPosition(APawn* Caster)
{
    if(const auto* Ability=Caster->FindComponentByClass<UFPSFireballComponent>())return Ability->HeldOrbPosition();
    const auto* Camera=Caster->FindComponentByClass<UCameraComponent>();
    if(!Camera)return Caster->GetActorLocation()+Caster->GetActorForwardVector()*100;
    return Camera->GetComponentLocation()+Camera->GetForwardVector()*95-Camera->GetRightVector()*40-Camera->GetUpVector()*22;
}
void AFPSFireballProjectile::Launch(const FVector& AimPoint)
{
    if(bFlying||bFinished)return;
    // Launch from the actual hovering position, including any wall clearance;
    // the remote hand gesture does not pull or teleport the orb toward the hand.
    bFlying=true;FlightAge=0.f;Velocity=(AimPoint-GetActorLocation()).GetSafeNormal()*Cast.Speed;
    if(Velocity.IsNearlyZero())Velocity=Shooter->GetActorForwardVector()*Cast.Speed;
    Core->SetVariableFloat(TEXT("User.Flight"),1.f);
    UpdateFlightFX(GetActorLocation());Trail->Activate(true);
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
    if(bFinished)
    {
        ImpactAge+=Delta;
        const float Fade=FMath::Exp(-ImpactAge*18.f)*FMath::Clamp((.24f-ImpactAge)/.06f,0.f,1.f);
        Light->SetIntensity(ImpactLightPeak*Fade);
        if(ImpactAge>=.24f){Light->SetIntensity(0);SetActorTickEnabled(false);}
        return;
    }
    if(!Shooter.IsValid()||!Source.IsValid()){Destroy();return;}
    if(const auto* Health=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Destroy();return;}
    Age+=Delta;
    const float T=bFlying?1.f:Source->GatherFraction(),Grow=T*T*(3-2*T);
    Core->SetRelativeScale3D(FVector(FMath::Max(.01f,Grow)));
    // Small, slow variations support the roiling flame instead of rapid flicker.
    const float Glow=.97f+.02f*FMath::Sin(Age*2.3f)+.01f*FMath::Sin(Age*3.7f+1.1f);
    Light->SetIntensity(1250*Grow*Glow);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballMove),false,Shooter.Get());Query.AddIgnoredActor(this);
    FHitResult Hit;
    if(!bFlying)
    {
        if(Age>=Cast.HoverDuration){Destroy();return;}
        const FVector Desired=HoverPosition(Shooter.Get());
        // The authored hand trajectory already eases; a second interpolator would
        // leave the ball behind the fast release gesture.
        const FVector End=Desired;
        const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,GetActorLocation(),End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query);
        SetActorLocation(Blocked?Hit.Location:End);
        // World geometry remains in front of the effect; near-camera retreat fades it out.
        if(const auto* Camera=Shooter->FindComponentByClass<UCameraComponent>())Core->SetVisibility(FVector::Distance(Camera->GetComponentLocation(),GetActorLocation())>30);
        return;
    }
    Core->SetVisibility(true);FlightAge+=Delta;
    const FVector PreviousPosition=GetActorLocation();
    const float Step=FMath::Min(Cast.Speed*Delta,FMath::Max(0.f,Cast.Range-Distance));
    const FVector End=GetActorLocation()+Velocity.GetSafeNormal()*Step;
    const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,GetActorLocation(),End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query);
    SetActorLocation(Blocked?Hit.Location:End);Distance+=Step;
    UpdateFlightFX(PreviousPosition);
    if(Blocked)Explode(&Hit);else if(Distance>=Cast.Range-UE_KINDA_SMALL_NUMBER)Explode(nullptr);
}
void AFPSFireballProjectile::Explode(const FHitResult* Hit)
{
    if(bFinished)return;bFinished=true;ImpactAge=0;
    Core->DeactivateImmediate();Light->SetIntensity(0);Trail->Deactivate();
    const FVector Center=GetActorLocation();
    const FVector Normal=Hit?FVector(Hit->ImpactNormal):-Velocity.GetSafeNormal();
    const FVector Contact=Hit?FVector(Hit->ImpactPoint):Center;
    const FRotator ImpactRotation=FRotationMatrix::MakeFromZ(Normal).Rotator();
    // Terrain damage: the hills heightfield gets a stamped crater. The hub arena is a
    // static floor and stays unchanged.
    TerrainDestruction::CarveCrater(this,Contact,Normal,Cast.Radius);
    const float EffectScale=Cast.Radius/FireballImpactVisuals::BaselineRadius;
    // Set the hit contract before activation, including when taking a pooled component.
    // The local-space transform scales spread; Niagara sprite sizes are world
    // units, so the same growth must also be applied explicitly in the system.
    if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,Explosion,Contact+Normal*8,ImpactRotation,FVector(EffectScale*FireballImpactVisuals::BaselineCombustionScale),true,false,ENCPoolMethod::AutoRelease))
    {
        FX->SetVariableFloat(TEXT("User.SurfaceHit"),Hit?1.f:0.f);
        FX->SetVariableVec3(TEXT("User.LocalUp"),ImpactRotation.UnrotateVector(FVector::UpVector));
        FX->SetVariableFloat(TEXT("User.ImpactGrowth"),EffectScale-1.f);
        FX->Activate(true);
    }
    const FVector WaveOrigin=Contact+(Hit?Normal*4:FVector::ZeroVector);
    if(Wave)if(auto* Ring=GetWorld()->SpawnActor<AFireballShockwave>(WaveOrigin,ImpactRotation))Ring->Setup(Wave,Cast.Radius,Hit!=nullptr);
    // One short, shadowed warm flash lights the actual contact environment.
    Light->SetWorldLocation(Contact+Normal*22);
    Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetCastShadows(true);
    Light->SetLightColor(FLinearColor(1.f,.48f,.13f));
    Light->SetAttenuationRadius(FireballImpactVisuals::BaselineLightRadius*EffectScale);
    ImpactLightPeak=FireballImpactVisuals::BaselineLightPeak*EffectScale;
    Light->SetIntensity(ImpactLightPeak);
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Contact,.72f,FMath::FRandRange(.96f,1.04f));
    UAISense_Hearing::ReportNoiseEvent(this,Center,1.f,Shooter.Get(),1600,TEXT("Fireball"));
    // Keep the collision bone for direct-hit weakpoints; airbursts have no hit.
    if(auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())P->ApplyFireballExplosion(Shooter.Get(),WaveOrigin,Cast,Hit);
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
