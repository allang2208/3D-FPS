#include "BellowSacProjectile.h"
#include "FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Sound/SoundAttenuation.h"
#include "ExplosiveWarningSubsystem.h"
#include "BellowSacCameraShake.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "../Skills/EnemyAttackDamage.h"

ABellowSacProjectile::ABellowSacProjectile()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true; SetReplicateMovement(true);
    SetNetUpdateFrequency(30.f);
    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MembraneCapsule"));
    RootComponent = Body;
    WarningRing = CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("RuptureSurface"));
    WarningRing->SetupAttachment(Body);
    // The warning belongs to the scene, never to the tumbling/pulsing capsule.
    WarningRing->SetAbsolute(true, true, true);
    WarningRing->SetVisibleInRayTracing(false);
    WarningRing->bAffectDistanceFieldLighting = false;
    Fragments = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("MembraneFragments"));
    Fragments->SetupAttachment(Body);
    PressureAudio=CreateDefaultSubobject<UAudioComponent>(TEXT("SacPressureAudio"));
    PressureAudio->SetupAttachment(Body); PressureAudio->SetAutoActivate(false);
    PressureAudio->bAutoDestroy=false; PressureAudio->bOverrideAttenuation=true;
    FSoundAttenuationSettings AudioRange;
    AudioRange.bAttenuate=true; AudioRange.bSpatialize=true;
    AudioRange.DistanceAlgorithm=EAttenuationDistanceModel::Linear;
    AudioRange.AttenuationShapeExtents=FVector(180.f); AudioRange.FalloffDistance=1200.f;
    AudioRange.bEnableOcclusion=true; AudioRange.OcclusionVolumeAttenuation=.45f;
    AudioRange.OcclusionLowPassFilterFrequency=1800.f;
    PressureAudio->SetAttenuationOverrides(AudioRange);
    for (UPrimitiveComponent* Part : {static_cast<UPrimitiveComponent*>(Body.Get()),
        static_cast<UPrimitiveComponent*>(WarningRing.Get()), static_cast<UPrimitiveComponent*>(Fragments.Get())})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false); Part->SetCastShadow(false);
        Part->bReceivesDecals = false;
    }
    WarningRing->SetVisibility(false);
}
void ABellowSacProjectile::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->GetSubsystem<UExplosiveWarningSubsystem>()->Register(this);
}
void ABellowSacProjectile::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* Registry=GetWorld()->GetSubsystem<UExplosiveWarningSubsystem>()) Registry->Unregister(this);
    PressureAudio->Stop(); Super::EndPlay(Reason);
}
float ABellowSacProjectile::FuseRemaining() const
{ return IsArmed()?FMath::Max(0.f,FuseSeconds-float(Clock()-ContactAt)):FuseSeconds; }
float ABellowSacProjectile::FuseProgress() const
{ return IsArmed()?FMath::Clamp(1.f-FuseRemaining()/FMath::Max(.01f,FuseSeconds),0.f,1.f):0.f; }
bool ABellowSacProjectile::ExposureTo(APawn* Player,float& Distance) const
{
    if (!Player) { Distance=BIG_NUMBER; return false; }
    FVector Closest=Player->GetActorLocation();
    if (auto* Shape=Cast<UPrimitiveComponent>(Player->GetRootComponent()))
        Shape->GetClosestPointOnCollision(GetActorLocation(),Closest);
    Distance=FVector::Dist(GetActorLocation(),Closest);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BellowSacExposure),false,this);
    Query.AddIgnoredActor(Player);
    return !GetWorld()->LineTraceTestByChannel(GetActorLocation(),Closest,ECC_Visibility,Query);
}
double ABellowSacProjectile::Clock() const
{
    const auto* GS = GetWorld()->GetGameState();
    return GS ? GS->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
}
void ABellowSacProjectile::Launch(APawn* Source, FVector LaunchVelocity, float Damage, float Radius,
    float Fuse, UStaticMesh* SacMesh, UStaticMesh* RingMesh, UMaterialInterface* Material, UMaterialInterface* RingMaterial)
{
    SetOwner(Source); SetInstigator(Source); DamageSource = Source;
    DamageController = Source ? Source->GetController() : nullptr;
    Velocity = LaunchVelocity; BlastDamage = Damage; BlastRadius = Radius; FuseSeconds = Fuse;
    CapsuleMesh = SacMesh; TelegraphMesh = RingMesh; CapsuleMaterial = Material; TelegraphMaterial = RingMaterial;
    BornAt = Clock(); OnRep_Visuals(); SetLifeSpan(6.f); ForceNetUpdate();
}
void ABellowSacProjectile::OnRep_Visuals()
{
    Body->SetStaticMesh(CapsuleMesh); Body->SetMaterial(0, CapsuleMaterial);
    WarningRing->SetMaterial(0, TelegraphMaterial);
    Fragments->SetStaticMesh(CapsuleMesh); Fragments->SetMaterial(0, CapsuleMaterial);
}
bool ABellowSacProjectile::Sweep(UWorld* World, const AActor* Ignore, const AActor* Shooter,
    const FVector& Start, const FVector& End, float Radius, FHitResult& Hit, const AActor* IntendedTarget)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BellowSacFlight), false, Ignore);
    if (Shooter) Query.AddIgnoredActor(Shooter);
    if (IntendedTarget) Query.AddIgnoredActor(IntendedTarget);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_Pawn); Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    TArray<FHitResult> Contacts;
    World->SweepMultiByObjectType(Contacts, Start, End, FQuat::Identity, Objects, FCollisionShape::MakeSphere(Radius), Query);
    bool Found = false;
    for (const FHitResult& Contact : Contacts)
    {
        const auto* Component = Contact.GetComponent();
        const auto* Pawn = Cast<APawn>(Contact.GetActor());
        const bool PlayerBody = Pawn && Pawn->IsPlayerControlled() && Component == Pawn->GetRootComponent();
        if (!Component || (!PlayerBody && Component->GetCollisionResponseToChannel(ECC_Visibility) != ECR_Block)) continue;
        if (!Found || Contact.Time < Hit.Time) { Hit = Contact; Found = true; }
    }
    return Found;
}
void ABellowSacProjectile::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (HasAuthority() && BurstAt < 0.)
    {
        // Swept ballistic substeps retain the whole elapsed interval and stop at the first contact.
        float Remaining = FMath::Max(DeltaSeconds, 0.f);
        while (Remaining > UE_SMALL_NUMBER && ContactAt < 0.)
        {
            const float Dt = FMath::Min(Remaining, 1.f / 60.f); Remaining -= Dt;
            const FVector Gravity(0, 0, GetWorld()->GetGravityZ());
            const FVector Start = GetActorLocation(), End = Start + Velocity * Dt + Gravity * (.5f * Dt * Dt);
            FHitResult Hit;
            if (Sweep(GetWorld(), this, DamageSource.Get(), Start, End, CollisionRadius, Hit))
            {
                SetActorLocation(Hit.Location + Hit.ImpactNormal * .5f);
                SurfaceNormal = Hit.ImpactNormal; Velocity = FVector::ZeroVector;
                ContactPoint = Hit.ImpactPoint; bSceneContact = IsWarningSceneSurface(Hit);
                // Start on receipt of contact, keeping the full visible fuse after a hitch.
                ContactAt = Clock(); ForceNetUpdate();
            }
            else { SetActorLocation(End); Velocity += Gravity * Dt; }
        }
        if (ContactAt >= 0. && Clock() - ContactAt >= FuseSeconds) Rupture();
    }
    Present();
}
void ABellowSacProjectile::Rupture()
{
    if (BurstAt >= 0.) return;
    BurstAt = Clock(); ForceNetUpdate(); SetLifeSpan(1.f);
    // One receipt per player; direct contact never adds a second damage event.
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->Get() ? It->Get()->GetPawn() : nullptr;
        const auto* Health = Player ? Player->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
        if (!Health || Health->IsDead()) continue;
        float Distance=0.f;
        if (!ExposureTo(Player,Distance) || Distance>BlastRadius) continue;
        const float Falloff = FMath::Lerp(1.f, .3f, FMath::Clamp(Distance / BlastRadius, 0.f, 1.f));
        UGameplayStatics::ApplyDamage(Player, BlastDamage * Falloff, DamageController.Get(),
            DamageSource.IsValid() ? DamageSource.Get() : this, UEnemyRangedDamage::StaticClass());
    }
}
void ABellowSacProjectile::Present()
{
    if (GetNetMode()==NM_DedicatedServer) return;
    const double Now = Clock();
    auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>();
    if (BurstAt >= 0.)
    {
        Body->SetVisibility(false, false); WarningRing->SetVisibility(false);
        if (!bBurstPresented)
        {
            bBurstPresented=true; PressureAudio->Stop();
            // A late replicated corpse never replays an old explosion.
            if (Now-BurstAt<.45)
            {
                FX->PlaySacImpact(GetActorLocation(),true);
                bool Spawned=false;
                for (FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator(); It; ++It)
                {
                    auto* PC=It->Get(); APawn* Player=PC?PC->GetPawn():nullptr;
                    if (!PC || !PC->IsLocalController() || !Player) continue;
                    if (!Spawned)
                        if (auto* Camera=Player->FindComponentByClass<UCameraComponent>())
                        { FX->SpawnSacRupture(GetActorLocation()-SurfaceNormal*6.f,SurfaceNormal,BlastRadius,Camera); Spawned=true; }
                    float Distance=0.f;
                    if (ExposureTo(Player,Distance) && Distance<450.f && PC->PlayerCameraManager)
                        PC->PlayerCameraManager->StartCameraShake(UBellowSacCameraShake::StaticClass(),
                            .80f*FMath::Square(1.f-Distance/450.f));
                }
            }
        }
        if (!bFragmentsCreated)
        {
            for (int32 I = 0; I < 16; ++I) Fragments->AddInstance(FTransform(FVector::ZeroVector));
            bFragmentsCreated = true;
        }
        const float T = FMath::Clamp(float(Now - BurstAt), 0.f, 1.f);
        FVector Tangent,Bitangent; SurfaceNormal.FindBestAxisVectors(Tangent,Bitangent);
        for (int32 I = 0; I < 16; ++I)
        {
            const float Angle=I*PI*.125f;
            const FVector V=(Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle))*(180.f+(I%4)*65.f)
                +SurfaceNormal*(105.f+(I%3)*45.f);
            const FVector Offset=V*T+FVector(0,0,-350.f*T*T);
            const float Fade=FVector::DotProduct(Offset,SurfaceNormal)<-5.f?0.f:1.f-FMath::SmoothStep(.45f,.9f,T);
            Fragments->UpdateInstanceTransform(I,FTransform(FRotator(T*480.f,I*45.f,T*210.f),
                GetActorLocation()+Offset,FVector(.22f,.08f,.15f)*Fade),true,I==15,true);
        }
        return;
    }
    if (ContactAt >= 0.)
    {
        if (!bContactPresented)
        {
            bContactPresented=true; PressureAudio->Stop();
            if (Now-ContactAt<.20) FX->PlaySacImpact(GetActorLocation(),false);
            // Silent fuse: retain contact and rupture, but no cartoon pressure cue.
        }
        const float Alpha = FMath::Clamp(float(Now - ContactAt) / FuseSeconds, 0.f, 1.f);
        const float Pulse = FMath::Sin(Alpha * PI * 6.f) * .045f + Alpha * .23f;
        Body->SetWorldScale3D(FVector(1.f + Pulse, 1.f + Pulse, 1.f - Pulse * .4f));
        if (!bWarningSurfaceBuilt && TelegraphMaterial) BuildWarningSurface();
    }
    else
    {
        if (!bFlightSoundStarted && FX->SacFlightCue())
        {
            bFlightSoundStarted=true; PressureAudio->SetSound(FX->SacFlightCue());
            PressureAudio->SetVolumeMultiplier(FX->SacAudioGain()*.45f); PressureAudio->Play();
        }
        const float Age = float(Now - BornAt);
        Body->SetRelativeRotation(FRotator(Age * 95.f, Age * 130.f, Age * 70.f));
    }
}
void ABellowSacProjectile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ABellowSacProjectile, CapsuleMesh); DOREPLIFETIME(ABellowSacProjectile, TelegraphMesh);
    DOREPLIFETIME(ABellowSacProjectile, CapsuleMaterial); DOREPLIFETIME(ABellowSacProjectile, TelegraphMaterial);
    DOREPLIFETIME(ABellowSacProjectile, BlastRadius); DOREPLIFETIME(ABellowSacProjectile, FuseSeconds);
    DOREPLIFETIME(ABellowSacProjectile, SurfaceNormal); DOREPLIFETIME(ABellowSacProjectile, ContactAt);
    DOREPLIFETIME(ABellowSacProjectile, ContactPoint); DOREPLIFETIME(ABellowSacProjectile, bSceneContact);
    DOREPLIFETIME(ABellowSacProjectile, BurstAt);
    DOREPLIFETIME(ABellowSacProjectile, BornAt);
}
