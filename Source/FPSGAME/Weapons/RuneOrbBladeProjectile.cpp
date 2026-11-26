#include "RuneOrbBladeProjectile.h"
#include "../Combat/FPSAttackQuery.h"
#include "StarfallBladeImpactComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "RuneOrbBladesComponent.h"
#include "RuneOrbBladeDamage.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/MonsterToughnessTypes.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MagicOcclusion.h"
#include "../Skills/IceWallLandingCameraShake.h"
#include "FPSMeleeLightningComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "../Multiplayer/ColdSteelPlayerState.h"

namespace
{
constexpr int32 SpectralImpactLayerCount = 3; // Flash, shockwave, blue corona.
constexpr int32 SpectralImpactMinParticles = 32;
constexpr int32 SpectralImpactMaxParticles = 48;
}

ARuneOrbBlade::ARuneOrbBlade()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(30.f);
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    StarfallImpact=CreateDefaultSubobject<UStarfallBladeImpactComponent>(TEXT("StarfallImpact"));
    Blade = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Blade"));
    Blade->SetupAttachment(Root);
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Blade->SetCanEverAffectNavigation(false);
    Blade->SetCastShadow(false);
    Blade->SetReceivesDecals(false);
    Wake = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpectralWake"));
    Wake->SetupAttachment(Root);
    Wake->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Wake->SetCanEverAffectNavigation(false);
    Wake->SetCastShadow(false);
    Wake->SetReceivesDecals(false);
    Wake->SetVisibility(false);
    ImpactWisps = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("SpectralImpactWisps"));
    ImpactWisps->SetupAttachment(Root);
    ImpactWisps->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ImpactWisps->SetCanEverAffectNavigation(false);
    ImpactWisps->SetCastShadow(false);
    ImpactWisps->SetReceivesDecals(false);
    ImpactWisps->SetVisibility(false);
    ImpactWisps->SetNumCustomDataFloats(2); // Material role and stable random seed.
    Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
    Light->SetupAttachment(Root);
    Light->SetLightColor(FLinearColor(0.06f, 0.25f, 1.f));
    Light->SetIntensity(90.f);
    Light->SetAttenuationRadius(100.f);
    Light->SetCastShadows(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> WakeAsset(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/SM_SpectralWake.SM_SpectralWake"));
    if (WakeAsset.Succeeded()) Wake->SetStaticMesh(WakeAsset.Object);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shard(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/SM_SpectralImpactParticle.SM_SpectralImpactParticle"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> ShardSkin(
        TEXT("/Game/Weapons/RuneSpectralBlade20260927/M_SpectralImpact.M_SpectralImpact"));
    if (Shard.Succeeded()) ShardMesh = Shard.Object;
    if (ShardSkin.Succeeded()) ShardMaterial = ShardSkin.Object;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> StarfallSkin(
        TEXT("/Game/Weapons/AzureRunesword20260913/StarfallGuard20261030/M_StarfallImpact.M_StarfallImpact"));
    if(StarfallSkin.Succeeded())StarfallShardMaterial=StarfallSkin.Object;
    static ConstructorHelpers::FObjectFinder<USoundBase> StarfallSound(
        TEXT("/Game/Weapons/AzureRunesword20260913/StarfallGuard20261030/S_StarfallImpact.S_StarfallImpact"));
    if(StarfallSound.Succeeded())StarfallImpactSound=StarfallSound.Object;
}

void ARuneOrbBlade::Setup(URuneOrbBladesComponent* InSource, APawn* InOwner, float InDamage, UStaticMesh* Mesh)
{
    Source = InSource;
    Shooter = InOwner;
    Damage = InDamage;
    MagicCooldownReduction = InSource->BladeMagicCooldownReduction();
    GuardMagicMultiplier = InSource->BladeGuardMagicMultiplier();
    MaxDistance = FMath::Max(0.f, InSource->BladeRangeCM());
    VulnerabilityStacks = InSource->BladeVulnerabilityStacks();
    if (Mesh) Blade->SetStaticMesh(Mesh);
    NetworkMesh=Mesh;
    NetworkBlastRadius=InSource->BladeBlastRadius();
    if(NetworkBlastRadius>0.f)
    {
        Wake->SetRelativeScale3D(FVector(2.2f));
        Light->SetIntensity(160.f);Light->SetAttenuationRadius(180.f);
    }
    if(GetNetMode()!=NM_Standalone&&GetNetMode()!=NM_Client&&InOwner&&!InOwner->IsLocallyControlled())
    {Blade->SetOwnerNoSee(true);Wake->SetOwnerNoSee(true);ImpactWisps->SetOwnerNoSee(true);}
    if(NetworkBlastRadius>0.f)StarfallImpact->Prepare(Blade,Light);
    // All shader motion stays in the authored local UVs. Independent phases avoid
    // four swords pulsing together; no per-frame material allocation or texture IO.
    const float Phase = FMath::FRandRange(0.f, 20.f);
    Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Phase);
    Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
    Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Phase);
    Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
}

void ARuneOrbBlade::Launch(const FVector& TargetPoint)
{
    if (!CanLaunch()) return;
    if(const auto* Pawn=Shooter.Get())
    {
        const auto* Camera=Pawn->FindComponentByClass<UCameraComponent>();
        const FVector Eye=Pawn->IsLocallyControlled()&&Camera?Camera->GetComponentLocation():Pawn->GetPawnViewLocation();
        const FVector ToTarget=TargetPoint-Eye;
        const FVector Direction=ToTarget.GetSafeNormal();
        const FVector Offset=GetActorLocation()-Eye;
        const double ForwardDepth=FVector::DotProduct(Offset,Direction);
        const float Radius=CollisionRadiusCM();
        const double SafeDepth=FMath::Max(0.0,ToTarget.Length()-Radius);
        if(ForwardDepth>SafeDepth&&ForwardDepth>UE_SMALL_NUMBER)
        {
            // A close target can be behind the hovering row, especially the
            // 144 cm giant-sword slot. Retract along its existing eye-to-slot
            // segment before release so the blade does not launch backwards.
            FVector Release=Eye+Offset*(SafeDepth/ForwardDepth);
            FHitResult Cover;
            FFPSAttackQuery Query(SCENE_QUERY_STAT(RuneBladeNearRelease),false,Pawn);
            Query.AddIgnoredActor(this);
            if(RangedAttackQuery::SweepSingle(GetWorld(),Pawn,Cover,Eye,Release,FQuat::Identity,
                ECC_Visibility,FCollisionShape::MakeSphere(Radius),Query))Release=Cover.Location;
            SetActorLocation(Release);
        }
    }
    EnchantmentShot=ColdSteelSkills::Snapshot(Shooter.Get());
    bFlying = true;
    NetworkPhase=1;ForceNetUpdate();
    Velocity = (TargetPoint - GetActorLocation()).GetSafeNormal(UE_SMALL_NUMBER, GetActorForwardVector()) * Speed;
    SetActorRotation(Velocity.Rotation());
    Wake->SetVisibility(true);
}

void ARuneOrbBlade::StartFade()
{
    if (bFinished || FadeAge >= 0.f) return;
    FadeAge = 0.f;
    NetworkPhase=2;ForceNetUpdate();
    Light->SetIntensity(0.f);
}

void ARuneOrbBlade::DamageTarget(const FHitResult& Hit,bool bDirectHit)
{
    if (auto* Target = Hit.GetActor();Target&&GetNetMode()!=NM_Client)
    {
        auto* Combat = Target->FindComponentByClass<UMonsterCombatComponent>();
        if (Combat && !Combat->IsDead() && !RangedAttackQuery::IsFriendlyUnit(Shooter.Get(),Target))
        {
            const bool bBerserkEnemy=UFPSMeleeLightningComponent::IsEnemy(Target,Shooter.Get());
            bool bCritical = false;
            double CritChance = 0, CritBonus = 0, Pen = 0, DmgBonus = 0;
            if (Shooter.IsValid() && Shooter->GetGameInstance())
                if (auto* Profile = Cast<AFPSGAMECharacter>(Shooter.Get())&&CastChecked<AFPSGAMECharacter>(Shooter.Get())->GetNetShadowProfile()
                    ?CastChecked<AFPSGAMECharacter>(Shooter.Get())->GetNetShadowProfile():Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
                {
                    CritChance = Profile->Derived(TEXT("crit"));
                    CritBonus = Profile->CriticalStrikeEffect().CriticalDamageBonus;
                    Pen = Profile->SetEffect(TEXT("magicPenetration"));
                    DmgBonus = Profile->SetEffect(TEXT("magicDamage"));
                }
            DmgBonus=(1.+DmgBonus)*GuardMagicMultiplier-1.;
            const CombatFormulaRuntime::MagicHit Magic{CritChance, CritBonus, Pen, DmgBonus, &bCritical, bDirectHit&&ColdSteelSkills::IsCriticalHit(Hit)};
            const TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(
                CombatFormulaRuntime::ActiveMagicHit, &Magic);
            // The concentrated explosion uses impact toughness; ordinary blades stay sharp.
            const MonsterToughness::FScopedForm FormScope(NetworkBlastRadius>0.f?EMonsterAttackForm::Impact:EMonsterAttackForm::Blade);
            const float Applied = UGameplayStatics::ApplyPointDamage(
                Target, Damage, Velocity.GetSafeNormal(), Hit, Shooter.IsValid() ? Shooter->GetController() : nullptr, Shooter.Get(),
                URuneOrbBladeDamage::StaticClass());
            if(bBerserkEnemy&&Damage>0.f)ColdSteelSkills::GrantBerserkOnWeaponHit(Shooter.Get(),EnchantmentShot);
            if (Applied > 0)
                if (auto* Player = Cast<AFPSGAMECharacter>(Shooter.Get()))
                {
                    FWeaponDamageResult HitResult;
                    HitResult.bResolved=true;
                    HitResult.bCritical=bCritical;
                    HitResult.bKilled=Combat->IsDead();
                    HitResult.Applied.BaseMagic=Applied;
                    Player->NotifyConfirmedWeaponHit(Target, Applied,&HitResult,false,false);
                    if(!Player->IsLocallyControlled())if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>())
                    {FColdSteelNetHitReceipt Receipt;Receipt.Target=Target;Receipt.Applied=Applied;Receipt.MagicApplied=Applied;Receipt.bCritical=bCritical;Receipt.bKilled=Combat->IsDead();PS->ClientConfirmHit(Receipt);}
                }
            // 毁灭符文 (2D magicVulnerabilityOnHit): the blade stacks the target's
            // magic vulnerability so follow-up magic lands harder.
            if (VulnerabilityStacks > 0 && Applied > 0 && !Combat->IsDead())
                UCombatStatusFormula::GetOrAdd(Target)->AddMagicVulnerability(VulnerabilityStacks);
            if (Source.IsValid() && Applied > 0) Source->NotifyBladeResult(Combat->IsDead(),MagicCooldownReduction);
        }
    }
}

void ARuneOrbBlade::ApplyBlast(const FHitResult& DirectHit)
{
    if(GetNetMode()==NM_Client)return;
    const FVector Center=DirectHit.ImpactPoint+DirectHit.ImpactNormal.GetSafeNormal()*2.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(StarfallBlast),true,Shooter.Get());
    Query.AddIgnoredActor(this);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Center,FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(NetworkBlastRadius),Query);
    TSet<AActor*> Targets;
    auto AddTarget=[&](AActor* Target)
    {
        auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(Combat&&!Combat->IsDead()&&Target!=Shooter.Get()&&!RangedAttackQuery::IsFriendlyUnit(Shooter.Get(),Target))Targets.Add(Target);
    };
    for(const auto& Overlap:Overlaps)AddTarget(Overlap.GetActor());
    AddTarget(DirectHit.GetActor());
    for(AActor* Target:Targets)Query.AddIgnoredActor(Target);
    for(AActor* Target:Targets)
    {
        if(Target==DirectHit.GetActor()){DamageTarget(DirectHit,true);continue;}
        MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Center,Samples);
        auto* Body=Cast<UPrimitiveComponent>(Target->GetRootComponent());
        FVector Closest=Target->GetActorLocation();
        if(Body&&Body->GetClosestPointOnCollision(Center,Closest)>=0.f)Samples.Add(Closest);
        for(const FVector& Point:Samples)
        {
            if(FVector::DistSquared(Center,Point)>FMath::Square(NetworkBlastRadius))continue;
            FHitResult Blocker;
            if(MagicOcclusion::TraceBlocker(GetWorld(),Center,Point,Query,Blocker,Shooter.Get()))continue;
            FHitResult Splash(Target,Body,Point,(Point-Center).GetSafeNormal());
            DamageTarget(Splash,false);
            break; // Each actor receives exactly one damage receipt, even with many overlapping bodies.
        }
    }
}

void ARuneOrbBlade::ApplyHit(const FHitResult& Hit)
{
    if(bFinished)return;
    bFinished = true;
    if(GetNetMode()!=NM_Client)UWardBreakableGlass::BreakHit(Hit,Velocity.GetSafeNormal());
    if(NetworkBlastRadius>0.f)ApplyBlast(Hit);
    else DamageTarget(Hit,true);
    if(NetworkBlastRadius>0.f && GetNetMode()!=NM_DedicatedServer)
    {
        StarfallImpact->Prepare(Blade,Light);
        if(StarfallImpact->PlayImpact(Hit,Velocity,NetworkBlastRadius))
        {
            Wake->SetVisibility(false);
            SetLifeSpan(UStarfallBladeImpactComponent::Lifetime+.05f);
            if(GetNetMode()!=NM_Client){NetworkPhase=3;ForceNetUpdate();MulticastImpact(Hit);}
            return;
        }
    }
    // Flash, expanding shockwave and corona share the same bounded ISM as sparks.
    // Damage has already resolved once above; these layers only present the contact.
    Blade->SetVisibility(false);
    Wake->SetVisibility(false);
    if (ShardMesh && ShardMaterial)
    {
        // Sample once per contact. Tick only advances the captured burst, so its
        // random shape is continuous rather than changing chaotically each frame.
        FRandomStream Random(FMath::Rand());
        ImpactLifetime = Random.FRandRange(.85f, 1.15f);
        ImpactDrag = Random.FRandRange(2.6f, 3.8f);
        ImpactLightPeak = Random.FRandRange(3600.f, 5000.f);
        ImpactFlashSeconds = Random.FRandRange(.19f, .29f);
        const float BurstScale = Random.FRandRange(.85f, 1.15f);
        const float StreakChance = Random.FRandRange(.18f, .38f);
        const bool bStarfall=NetworkBlastRadius>0.f;
        const int32 ParticleCount = bStarfall?72:Random.RandRange(SpectralImpactMinParticles, SpectralImpactMaxParticles);
        if(bStarfall){ImpactLifetime=1.35f;ImpactDrag=2.8f;ImpactLightPeak=14500.f;ImpactFlashSeconds=.32f;}
        const FVector SurfaceNormal = Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, -Velocity.GetSafeNormal());
        auto OutwardDirection = [&Random, SurfaceNormal]()
        {
            FVector Direction = Random.VRand();
            if (FVector::DotProduct(Direction, SurfaceNormal) < 0.f) Direction *= -1.f;
            return (Direction + SurfaceNormal * .15f).GetSafeNormal();
        };
        const FVector Jets[] = { OutwardDirection(), OutwardDirection(), OutwardDirection() };
        ImpactAge = 0.f;
        ImpactWisps->SetStaticMesh(ShardMesh);
        ImpactWisps->SetMaterial(0, bStarfall&&StarfallShardMaterial?StarfallShardMaterial:ShardMaterial);
        const FVector BurstOrigin = Hit.ImpactPoint + SurfaceNormal * 6.f;
        ImpactWisps->SetWorldLocationAndRotation(BurstOrigin, FRotator::ZeroRotator);
        ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), 1.f);
        ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralPhase"), Random.FRandRange(0.f, 100.f));
        WispTransforms.Reserve(SpectralImpactLayerCount + ParticleCount);
        WispVelocities.Reserve(SpectralImpactLayerCount + ParticleCount);
        ImpactLayers.Reserve(SpectralImpactLayerCount);
        for (int32 I = 0; I < SpectralImpactLayerCount; ++I)
        {
            const float Radius = (I == 0 ? 18.f : I == 1 ? 12.f : 24.f) * BurstScale;
            FImpactLayerMotion Motion;
            Motion.BaseScale = FVector(Random.FRandRange(.75f, 1.25f), Random.FRandRange(.75f, 1.25f), Random.FRandRange(.75f, 1.25f)) * Radius;
            Motion.SpinPerSecond = FRotator(Random.FRandRange(-65.f, 65.f), Random.FRandRange(-100.f, 100.f), Random.FRandRange(-65.f, 65.f));
            Motion.Growth = (I == 0 ? 1.55f : I == 1 ? 8.58f : 2.33f) * Random.FRandRange(.85f, 1.15f);
            Motion.ExpansionRate = (I == 0 ? 16.f : I == 1 ? 5.f : 6.f) * Random.FRandRange(.8f, 1.2f);
            if(bStarfall)
            {
                Motion.BaseScale=FVector(NetworkBlastRadius*(I==0?.12f:I==1?.05f:.20f));
                Motion.Growth=I==0?2.f:I==1?19.f:2.2f;
                Motion.ExpansionRate=I==1?8.f:12.f;
                if(I==1)Motion.SpinPerSecond=FRotator::ZeroRotator;
            }
            ImpactLayers.Add(Motion);
            const FRotator Rotation=bStarfall&&I==1?FRotator::ZeroRotator:FRotator(Random.FRandRange(-180.f, 180.f), Random.FRandRange(-180.f, 180.f), Random.FRandRange(-180.f, 180.f));
            const FTransform Transform(Rotation, bStarfall&&I==1?FVector::ZeroVector:OutwardDirection() * Random.FRandRange(0.f, 6.f), Motion.BaseScale);
            const int32 Index = ImpactWisps->AddInstance(Transform);
            ImpactWisps->SetCustomDataValue(Index, 0, float(I + 1), false);
            ImpactWisps->SetCustomDataValue(Index, 1, Random.FRand(), false);
            WispTransforms.Add(Transform);
            WispVelocities.Add(bStarfall&&I==1?FVector::ZeroVector:OutwardDirection() * Random.FRandRange(6.f, 22.f));
        }
        for (int32 I = 0; I < ParticleCount; ++I)
        {
            const FVector Direction = (OutwardDirection() + Jets[Random.RandRange(0, 2)] * Random.FRandRange(0.f, 1.8f)).GetSafeNormal();
            const bool bStreak = Random.FRand() < StreakChance;
            const float Width = Random.FRandRange(.9f, 1.6f);
            const FVector Scale = (bStreak ? FVector(Random.FRandRange(8.f, 18.f), Width, Width)
                : FVector(Random.FRandRange(2.3f, 5.6f))) * BurstScale * (bStarfall?1.6f:1.f);
            FRotator Rotation = Direction.Rotation(); Rotation.Roll = Random.FRandRange(-180.f, 180.f);
            const FTransform Transform(Rotation, Direction * Random.FRandRange(3.f, 14.f), Scale);
            const int32 Index = ImpactWisps->AddInstance(Transform);
            ImpactWisps->SetCustomDataValue(Index, 0, 0.f, false);
            ImpactWisps->SetCustomDataValue(Index, 1, Random.FRand(), I == ParticleCount - 1);
            WispTransforms.Add(Transform);
            WispVelocities.Add(Direction * Random.FRandRange(240.f, 500.f) * BurstScale * (bStarfall?1.7f:1.f));
        }
        ImpactWisps->SetVisibility(true);
        // Reuse the flight light for a brief surface flash, with no extra light.
        Light->SetWorldLocation(BurstOrigin + SurfaceNormal * 12.f);
        Light->SetLightColor(FLinearColor(.025f, .20f, 1.f));
        Light->SetAttenuationRadius(bStarfall?NetworkBlastRadius*1.6f:220.f * BurstScale);
        Light->SetIntensity(ImpactLightPeak);
    }
    else Light->SetIntensity(0.f);
    if(NetworkBlastRadius>0.f&&GetNetMode()!=NM_DedicatedServer)
    {
        if(StarfallImpactSound)UGameplayStatics::PlaySoundAtLocation(this,StarfallImpactSound,Hit.ImpactPoint,.8f);
        UGameplayStatics::PlayWorldCameraShake(this,UIceWallLandingCameraShake::StaticClass(),Hit.ImpactPoint,0.f,NetworkBlastRadius*2.f,1.5f,false);
    }
    SetLifeSpan(ImpactLifetime + .05f);
    if(GetNetMode()!=NM_Client){NetworkPhase=3;ForceNetUpdate();MulticastImpact(Hit);}
}

void ARuneOrbBlade::Tick(float Delta)
{
    Super::Tick(Delta);
    if (bFinished)
    {
        if (ImpactAge >= 0.f)
        {
            ImpactAge += Delta;
            const float Alpha = FMath::Clamp(1.f - ImpactAge / ImpactLifetime, 0.f, 1.f);
            ImpactWisps->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha);
            const float Flash = FMath::Clamp(1.f - ImpactAge / ImpactFlashSeconds, 0.f, 1.f);
            Light->SetIntensity(ImpactLightPeak * Flash * Flash);
            for (int32 I = 0; I < WispTransforms.Num(); ++I)
            {
                if (I < SpectralImpactLayerCount)
                {
                    const FImpactLayerMotion& Motion = ImpactLayers[I];
                    WispTransforms[I].SetScale3D(Motion.BaseScale * (1.f + Motion.Growth * (1.f - FMath::Exp(-Motion.ExpansionRate * ImpactAge))));
                    if(NetworkBlastRadius>0.f&&I==1)
                    {
                        // The private shockwave shader's contour is at UV radius .85.
                        // Reach precisely the 3 m damage boundary, then fade in place.
                        const float T=FMath::Clamp(ImpactAge/.32f,0.f,1.f);
                        const float Radius=NetworkBlastRadius*FMath::InterpEaseOut(.05f,1.f,T,2.f);
                        WispTransforms[I].SetScale3D(FVector(Radius/.85f));
                    }
                    WispTransforms[I].SetRotation((Motion.SpinPerSecond * Delta).Quaternion() * WispTransforms[I].GetRotation());
                    WispTransforms[I].AddToTranslation(WispVelocities[I] * Delta);
                }
                else
                {
                    // Integrate drag analytically so burst reach is stable across frame rates.
                    const float Drag = FMath::Exp(-ImpactDrag * Delta);
                    WispTransforms[I].AddToTranslation(WispVelocities[I] * ((1.f - Drag) / ImpactDrag));
                    WispVelocities[I] *= Drag;
                }
                ImpactWisps->UpdateInstanceTransform(I, WispTransforms[I], false, I == WispTransforms.Num() - 1, true);
            }
            if (Alpha <= 0.f) Destroy();
        }
        return;
    }
    if(GetNetMode()==NM_Client&&GetLocalRole()!=ROLE_Authority)return;
    if (!Shooter.IsValid() || !Source.IsValid()) { Destroy(); return; }
    if (FadeAge >= 0.f)
    {
        FadeAge += Delta;
        const float Alpha = FMath::Clamp(1.f - FadeAge / FadeSeconds, 0.f, 1.f);
        Blade->SetVisibility(Alpha > 0.f);
        Blade->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha * Alpha);
        Wake->SetScalarParameterValueOnMaterials(TEXT("SpectralFade"), Alpha * Alpha);
        if (FadeAge >= FadeSeconds) { bFinished = true; Destroy(); }
        return;
    }
    if (!bFlying) return;
    const FVector Previous = GetActorLocation();
    const float Travel = FMath::Min(Speed * Delta, FMath::Max(0.f, MaxDistance - Distance));
    const FVector Next = Previous + Velocity.GetSafeNormal() * Travel;
    FFPSAttackQuery Query(SCENE_QUERY_STAT(RuneBladeMove), false, Shooter.Get());
    Query.AddIgnoredActor(this);
    FHitResult Hit;
    bool Blocked = false;
    // Match ice-spike bursts: an earlier blade's corpse does not eat later blades.
    for (int32 Pass = 0; Pass < 8; ++Pass)
    {
        Blocked = RangedAttackQuery::SweepSingle(GetWorld(), Shooter.Get(), Hit, Previous, Next, FQuat::Identity,
            ECC_Visibility, FCollisionShape::MakeSphere(CollisionRadiusCM()), Query);
        if (!Blocked) break;
        const auto* Combat = IsValid(Hit.GetActor()) ? Hit.GetActor()->FindComponentByClass<UMonsterCombatComponent>() : nullptr;
        if (!Combat || !Combat->IsDead()) break;
        Query.AddIgnoredActor(Hit.GetActor());
    }
    if (Blocked) { SetActorLocation(Hit.Location); ApplyHit(Hit); return; }
    SetActorLocation(Next);
    Distance += Travel;
    if (Distance >= MaxDistance) StartFade();
}
void ARuneOrbBlade::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(ARuneOrbBlade,NetworkMesh,COND_InitialOnly);
    DOREPLIFETIME(ARuneOrbBlade,NetworkPhase);
    DOREPLIFETIME_CONDITION(ARuneOrbBlade,NetworkBlastRadius,COND_InitialOnly);
}
void ARuneOrbBlade::OnRep_Visual()
{
    if(NetworkMesh)Blade->SetStaticMesh(NetworkMesh);
    if(NetworkBlastRadius>0.f)Wake->SetRelativeScale3D(FVector(2.2f));
    // The owning client already has immediate gesture-driven cosmetic blades.
    Blade->SetOwnerNoSee(true);Wake->SetOwnerNoSee(true);ImpactWisps->SetOwnerNoSee(true);
    if(NetworkBlastRadius>0.f)StarfallImpact->Prepare(Blade,Light);
    if(GetInstigator()&&GetInstigator()->IsLocallyControlled())Light->SetVisibility(false);
    if(NetworkPhase==1)Wake->SetVisibility(true);
    else if(NetworkPhase>=2 && !(NetworkBlastRadius>0.f&&bFinished))
    {Blade->SetVisibility(false);Wake->SetVisibility(false);Light->SetIntensity(0.f);}
}
void ARuneOrbBlade::MulticastImpact_Implementation(const FHitResult& Hit)
{
    if(GetNetMode()==NM_Client&&GetLocalRole()!=ROLE_Authority)
    {
        // The owner's predicted blade already presents the same contact.
        if(GetInstigator()&&GetInstigator()->IsLocallyControlled()){bFinished=true;SetLifeSpan(.1f);return;}
        ApplyHit(Hit);
    }
}
