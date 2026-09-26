#include "WitchProjectile.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../WorldGeneration/GrassDeform/GrassDeformSubsystem.h"
#include "WitchMonster.h"
#include "PoisonMaggotVenomFX.h"
#include "FPSCombatHealthComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AWitchProjectile::AWitchProjectile()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SpellRoot"));
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpellVisual"));
    Visual->SetupAttachment(RootComponent);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetGenerateOverlapEvents(false); Visual->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Liquid(TEXT("/Game/Fluids/VenomProjectiles20260924/M_VenomBody.M_VenomBody"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Core(TEXT("/Game/Fluids/VenomProjectiles20260924/M_VenomCore.M_VenomCore"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Pool(TEXT("/Game/Fluids/VenomProjectiles20260924/M_WitchPoisonPool.M_WitchPoisonPool"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> BottleLiquid(TEXT("/Game/Fluids/VenomProjectiles20260924/M_WitchBottleLiquid.M_WitchBottleLiquid"));
    PoolMaterial = Pool.Object; BottleLiquidMaterial = BottleLiquid.Object;
    Visual->SetStaticMesh(Sphere.Object); Visual->SetMaterial(0, Liquid.Object);
    Visual->SetRelativeScale3D(FVector(.14f,.105f,.105f)); Visual->SetCastShadow(false);
    Visual->bReceivesDecals = false; Visual->bAffectDistanceFieldLighting = false;
    Visual->SetBoundsScale(1.6f);
    LiquidCore = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VenomOpaqueCore"));
    LiquidCore->SetupAttachment(Visual);
    LiquidCore->SetStaticMesh(Sphere.Object); LiquidCore->SetMaterial(0, Core.Object);
    LiquidCore->SetRelativeScale3D(FVector(.8f,.78f,.78f));
    LiquidCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LiquidCore->SetGenerateOverlapEvents(false); LiquidCore->SetCanEverAffectNavigation(false);
    LiquidCore->SetCastShadow(false); LiquidCore->bReceivesDecals = false;
    LiquidCore->bAffectDistanceFieldLighting = false;
    LiquidCore->SetBoundsScale(1.6f);
    LiquidCore->SetVisibility(false);
}

void AWitchProjectile::Launch(AWitchMonster* Source, bool Bottle, FVector Destination, float Speed, float Damage, float Radius)
{
    Shooter = Source; bBottle = Bottle; Origin = GetActorLocation(); Goal = Destination;
    HitDamage = Damage; PoolRadius = Radius;
    FRandomStream CosmeticRandom{int32(GetUniqueID())};
    LiquidPhase = CosmeticRandom.FRand()*2.f*PI;
    Visual->SetCustomPrimitiveDataFloat(0,LiquidPhase/(2.f*PI));
    LiquidCore->SetCustomPrimitiveDataFloat(0,LiquidPhase/(2.f*PI));
    if (Source->ActorHasTag(TEXT("DevelopmentSpawned"))) Tags.Add(TEXT("DevelopmentSpawned"));
    if (bBottle)
    {
        FHitResult Ground; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchBottleLanding), false, Source);
        if (auto* Target = UGameplayStatics::GetPlayerPawn(this, 0)) Query.AddIgnoredActor(Target);
        if (GetWorld()->LineTraceSingleByChannel(Ground, Goal + FVector(0,0,100), Goal - FVector(0,0,500), ECC_Visibility, Query)) Goal = Ground.ImpactPoint;
        if (Source->Bottle->GetStaticMesh())
        {
            const FTransform Held = Source->Bottle->GetComponentTransform();
            const FVector Center = Source->Bottle->GetStaticMesh()->GetBounds().Origin;
            Origin = Held.TransformPosition(Center);
            BottleReleaseRotation = Held.GetRotation();
            SetActorTransform(FTransform(BottleReleaseRotation, Origin));
            Visual->SetStaticMesh(Source->Bottle->GetStaticMesh());
            // The actor sweeps around the bottle's center. Its visible mesh retains
            // exactly the held transform, including the authored bottom pivot/scale.
            Visual->SetRelativeTransform(FTransform(FQuat::Identity,
                -Center * Held.GetScale3D(), Held.GetScale3D()));
            const auto& Slots = Source->Bottle->GetStaticMesh()->GetStaticMaterials();
            for (int32 Index = 0; Index < Source->Bottle->GetNumMaterials(); ++Index)
            {
                const bool bLiquidSlot = Slots.IsValidIndex(Index) &&
                    Slots[Index].MaterialSlotName.ToString().Contains(TEXT("BottleLiquid"));
                Visual->SetMaterial(Index,bLiquidSlot && BottleLiquidMaterial ? BottleLiquidMaterial.Get() : Source->Bottle->GetMaterial(Index));
            }
        }
        const FVector Direction = (Goal - Origin).GetSafeNormal2D();
        BottleSpinAxis = Direction.IsNearlyZero() ? Source->GetActorRightVector()
            : FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
        SetLifeSpan(8.f);
    }
    else
    {
        Velocity = (Goal - Origin).GetSafeNormal() * Speed;
        // Cosmetic phase does not consume the combat spread/poison random stream.
        LiquidCore->SetVisibility(true);
        SetActorRotation(Velocity.Rotation());
        SetLifeSpan(1000.f / FMath::Max(1.f, Speed));
    }
}

void AWitchProjectile::UpdateLiquidVisual(float DeltaTime, const FVector& Start, const FVector& End)
{
    const float PreviousAge = LiquidAge;
    LiquidAge += DeltaTime;
    const float Stretch = 1.f + .09f * FMath::Sin(LiquidAge * 17.f + LiquidPhase);
    const float Width = 1.f / FMath::Sqrt(Stretch);
    Visual->SetRelativeScale3D(FVector(.14f * Stretch, .105f * Width, .105f * Width));
    FRotator Direction = Velocity.Rotation();
    Direction.Roll = FMath::RadiansToDegrees(LiquidPhase) + LiquidAge * 48.f;
    SetActorRotation(Direction);
    LiquidCore->SetRelativeScale3D(FVector(.8f, .78f + .025f * FMath::Sin(LiquidAge * 11.f + LiquidPhase), .78f));
    auto* FX = GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>();
    if (!FX) return;
    // Share the maggot's bounded fragment pool. Sample the traveled segment so
    // a slow frame does not stack droplets at the endpoint or beyond a hit.
    int32 Emitted = 0;
    while (NextTrail <= LiquidAge && Emitted < 4)
    {
        const float Alpha = DeltaTime > UE_SMALL_NUMBER ? FMath::Clamp((NextTrail - PreviousAge) / DeltaTime, 0.f, 1.f) : 1.f;
        FX->AddTrail(FMath::Lerp(Start, End, Alpha), Velocity, (TrailCount++ % 3) == 0);
        NextTrail += .065f;
        ++Emitted;
    }
    if (NextTrail <= LiquidAge) NextTrail = LiquidAge + .065f;
}

void AWitchProjectile::Land(const FHitResult& Contact, const FVector& IncomingVelocity)
{
    const FVector Position = Contact.ImpactPoint;
    const FVector Normal = Contact.ImpactNormal.GetSafeNormal();
    if (auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>()) FX->AddBottleImpact(Position,Normal,IncomingVelocity,PoolRadius);
    // One bottle, one flatten: stamped before the steep-ground reject below, because the glass
    // really did hit here even when no pool forms, and a second stamp on the eventually flat
    // ground would double the event. PoolRadius is the pool's own outward limit, so the two
    // footprints line up; this is a splash rather than a blast, hence the softer tuning.
    if(auto* GrassDeform=GetWorld()->GetSubsystem<UGrassDeformSubsystem>())
        GrassDeform->AddImpulse(Position,PoolRadius*GrassDeformTuning::WitchRadiusMultiplier,
            GrassDeformTuning::WitchImpulseStrength,GrassDeformTuning::WitchImpulseWaveSpeed);
    if (Normal.Z < .65f) { Destroy(); return; }
    Visual->SetVisibility(false,true);
    bPool = true; Age = 0.f; NextPulse = .5f; NextPoolVapor = .35f;
    SetActorLocation(Position + Normal * 2.f); SetActorRotation(FRotationMatrix::MakeFromZ(Normal).Rotator());
    PoolSlope=Normal;BuildPoolFootprint();
    PoolSurface = NewObject<UDecalComponent>(this,TEXT("PoisonPoolSurface"));
    PoolSurface->SetupAttachment(RootComponent);
    PoolSurface->SetDecalMaterial(PoolMaterial);
    PoolSurface->DecalSize = FVector(50.f/Normal.Z,PoolRadius/Normal.Z,PoolRadius/Normal.Z);
    PoolSurface->SetWorldLocation(Position+Normal*2.f);
    PoolSurface->SetWorldRotation((-Normal).Rotation());
    PoolSurface->SetFadeScreenSize(.0001f);
    PoolSurface->RegisterComponent();
    if (auto* Material=PoolSurface->CreateDynamicMaterialInstance())
    {
        const FVector Center = GetActorLocation();
        Material->SetVectorParameterValue(TEXT("PoolCenter"),FLinearColor(Center.X,Center.Y,Center.Z));
        Material->SetVectorParameterValue(TEXT("PoolNormal"),FLinearColor(Normal.X,Normal.Y,Normal.Z));
        Material->SetScalarParameterValue(TEXT("PoolRadius"),PoolRadius);
        Material->SetScalarParameterValue(TEXT("PoolStartTime"),GetWorld()->GetTimeSeconds());
        Material->SetScalarParameterValue(TEXT("PoolSeed"),LiquidPhase/(2.f*PI));
        for(int32 I=0;I<4;++I)
            Material->SetVectorParameterValue(FName(*FString::Printf(TEXT("PoolReach%d"),I)),
                FLinearColor(PoolReach[I*4],PoolReach[I*4+1],PoolReach[I*4+2],PoolReach[I*4+3]));
    }
    // Six seconds of damage, then a cosmetic-only drying tail.
    SetLifeSpan(6.65f);
}

void AWitchProjectile::BuildPoolFootprint()
{
    for(int32 I=0;I<16;++I)PoolReach[I]=SamplePoolSector(I);
    FootprintCursor=0;NextFootprintUpdate=.08f+.06f*LiquidPhase/(2.f*PI);
}

float AWitchProjectile::SamplePoolSector(int32 Index) const
{
    const FVector Center=GetActorLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchPoolFootprint),false,this);
    Query.AddIgnoredActor(Shooter.Get());
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->GetPawn())Query.AddIgnoredActor(It->Get()->GetPawn());
    const float Angle=Index*2.f*PI/16.f;
    const FVector Direction(FMath::Cos(Angle),FMath::Sin(Angle),0);
    float Reach=0;FVector End=Center;
    for(int32 Step=1;Step<=3;++Step)
    {
        const FVector Sample=Center+Direction*(PoolRadius*Step/3.f);
        FHitResult Floor;
        if(!GetWorld()->LineTraceSingleByChannel(Floor,Sample+FVector(0,0,50),Sample-FVector(0,0,50),ECC_Visibility,Query)
            ||Floor.ImpactNormal.Z<.65f)break;
        Reach=float(Step)/3.f;End=Floor.ImpactPoint;
    }
    if(Reach>0)
    {
        FHitResult Wall;
        if(GetWorld()->LineTraceSingleByChannel(Wall,Center+FVector(0,0,15),End+FVector(0,0,15),ECC_Visibility,Query))
            Reach=FMath::Max(0.f,float(FVector::Dist2D(Center,Wall.ImpactPoint)-5.f)/FMath::Max(1.f,PoolRadius));
    }
    return Reach;
}

void AWitchProjectile::PushPoolFootprint()
{
    if(auto* Material=PoolSurface?Cast<UMaterialInstanceDynamic>(PoolSurface->GetDecalMaterial()):nullptr)
        for(int32 I=0;I<4;++I)
            Material->SetVectorParameterValue(FName(*FString::Printf(TEXT("PoolReach%d"),I)),
                FLinearColor(PoolReach[I*4],PoolReach[I*4+1],PoolReach[I*4+2],PoolReach[I*4+3]));
}

void AWitchProjectile::RefreshPoolFootprint()
{
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    bool Changed=false;
    for(int32 I=0;I<2;++I)
    {
        if(Budget&&!Budget->ReserveGeometryQueries(4,true))break;
        const int32 Sector=FootprintCursor++%16;
        const float Reach=SamplePoolSector(Sector);
        Changed|=!FMath::IsNearlyEqual(Reach,PoolReach[Sector],.001f);
        PoolReach[Sector]=Reach;
    }
    if(Changed)PushPoolFootprint(); // Publish the same values damage uses, in the same frame.
    NextFootprintUpdate=Age+.10f+.02f*FMath::Frac(LiquidPhase+FootprintCursor*.618f);
}

float AWitchProjectile::PoolBoundary(const FVector& Position) const
{
    const FVector Offset=Position-GetActorLocation();
    float Sector=FMath::Atan2(Offset.Y,Offset.X)*(16.f/(2.f*PI));if(Sector<0)Sector+=16;
    const int32 I=FMath::FloorToInt(Sector)%16;
    // The same smooth spoke interpolation is used by the decal shader and damage mask.
    return FMath::Lerp(PoolReach[I],PoolReach[(I+1)%16],FMath::Frac(Sector));
}

void AWitchProjectile::Pulse()
{
    if (!Shooter.IsValid()) return;
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->IsValid() ? It->Get()->GetPawn() : nullptr;
        auto* Health = Player ? Player->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
        if (!Health || Health->IsDead() || Health->IsInvulnerable()) continue;
        const FVector Feet = Player->GetActorLocation() - FVector(0,0,Player->GetSimpleCollisionHalfHeight());
        const float Boundary=PoolBoundary(Feet);
        if (Boundary<=.001f || FVector::DistSquared2D(Feet, GetActorLocation()) > FMath::Square(PoolRadius*Boundary)
            || FMath::Abs(Feet.Z - GetActorLocation().Z) > 50.f) continue;
        FHitResult Wall; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchPoisonOcclusion), false, this);
        Query.AddIgnoredActor(Shooter.Get()); Query.AddIgnoredActor(Player);
        if (GetWorld()->LineTraceSingleByChannel(Wall, GetActorLocation() + FVector(0,0,15), Feet + FVector(0,0,15), ECC_Visibility, Query)) continue;
        const float Applied = UGameplayStatics::ApplyDamage(Player, HitDamage, Shooter->GetController(), Shooter.Get(), UWitchMagicDamage::StaticClass());
        if (Applied > 0 && !Health->IsDead())
        {
            auto* Poison = Player->FindComponentByClass<UColdSteelPoisonComponent>();
            if (!Poison) { Poison = NewObject<UColdSteelPoisonComponent>(Player); Player->AddInstanceComponent(Poison); Poison->RegisterComponent(); }
            Poison->AddStacks(Shooter.Get(), 1);
        }
    }
}

void AWitchProjectile::Tick(float Delta)
{
    Super::Tick(Delta); if (!HasAuthority()) return;
    if (!Shooter.IsValid()) { Destroy(); return; }
    Age += Delta;
    if (bPool)
    {
        if(Age>=NextFootprintUpdate&&Age<=6.f)RefreshPoolFootprint();
        if (Age>=NextPoolVapor && Age<5.8f)
        {
            const float Angle=Age*2.39996f+LiquidPhase;
            FVector Sample=GetActorLocation()+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*(PoolRadius*.4f);
            const FVector Offset=Sample-GetActorLocation();
            Sample.Z-=FVector::DotProduct(Offset,PoolSlope)/FMath::Max(.65f,float(PoolSlope.Z));
            if(PoolBoundary(Sample)>.45f)
                if(auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>())FX->AddPoolVapor(Sample,GetActorUpVector(),0);
            NextPoolVapor=Age+.70f;
        }
        while (NextPulse <= 6.f && Age >= NextPulse) { Pulse(); NextPulse += .5f; }
        if (Age >= 6.6f) Destroy();
        return;
    }
    if (Shooter->State == ENurseState::Dead) { Destroy(); return; }
    const FVector Start = GetActorLocation();
    constexpr float FlightSeconds = 1.5f, ArcHeight = 100.f;
    const float Phase = FMath::Clamp(Age / FlightSeconds, 0.f, 1.f);
    FVector End = Start + Velocity * Delta;
    if (bBottle)
    {
        End = FMath::Lerp(Origin, Goal, Phase) + FVector(0,0,4.f * ArcHeight * Phase * (1-Phase));
        if (Age > FlightSeconds)
        {
            // Missing/moving ground is not a landing. Continue from the arc's
            // end velocity until a real swept contact or the lifetime expires.
            const float FallSeconds = Age - FlightSeconds;
            const FVector EndVelocity = (Goal - Origin - FVector(0,0,4.f * ArcHeight)) / FlightSeconds;
            End += EndVelocity * FallSeconds + FVector(0,0,.5f * GetWorld()->GetGravityZ() * FMath::Square(FallSeconds));
        }
    }
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchSpellCollision), false, this); Query.AddIgnoredActor(Shooter.Get());
    FCollisionObjectQueryParams Objects; Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Contacts; GetWorld()->SweepMultiByObjectType(Contacts, Start, End, FQuat::Identity, Objects, FCollisionShape::MakeSphere(5.f), Query);
    const FHitResult* First = nullptr;
    for (const auto& Hit : Contacts)
    {
        const auto* Part = Hit.GetComponent(); const auto* Pawn = Cast<APawn>(Hit.GetActor());
        const bool Player = Pawn && Pawn->IsPlayerControlled() && Part == Pawn->GetRootComponent();
        if (Part && (Player || Part->GetCollisionResponseToChannel(ECC_Visibility) == ECR_Block)
            && (!First || Hit.Time < First->Time)) First = &Hit;
    }
    if (First)
    {
        if (bBottle)
        {
            const FVector ImpactVelocity = Delta>UE_SMALL_NUMBER ? (End-Start)/Delta : FVector::ZeroVector;
            if (Cast<APawn>(First->GetActor()))
            {
                FHitResult Ground; auto GroundQuery = Query; GroundQuery.AddIgnoredActor(First->GetActor());
                if (GetWorld()->LineTraceSingleByChannel(Ground, First->ImpactPoint, First->ImpactPoint - FVector(0,0,300), ECC_Visibility, GroundQuery)) Land(Ground,ImpactVelocity);
                else Destroy();
            }
            else Land(*First,ImpactVelocity);
        }
        else
        {
            UpdateLiquidVisual(Delta * First->Time, Start, First->Location);
            if (auto* FX = GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>()) FX->AddImpact(*First, Velocity);
            if (auto* Pawn = Cast<APawn>(First->GetActor())) if (Pawn->IsPlayerControlled())
                UGameplayStatics::ApplyDamage(Pawn, HitDamage, Shooter->GetController(), Shooter.Get(), UWitchMagicDamage::StaticClass());
            Destroy();
        }
        return;
    }
    SetActorLocation(End);
    if (bBottle)
        SetActorRotation(FQuat(BottleSpinAxis, FMath::DegreesToRadians(Age * 360.f)) * BottleReleaseRotation);
    else UpdateLiquidVisual(Delta, Start, End);
}
