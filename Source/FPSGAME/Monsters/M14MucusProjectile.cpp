#include "M14MucusProjectile.h"
#include "SpiralPillarM14.h"
#include "PoisonMaggotVenomFX.h"
#include "FPSCombatHealthComponent.h"
#include "PoisonMaggotProjectile.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

AM14MucusProjectile::AM14MucusProjectile()
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(30.f);
    Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MucusShell"));RootComponent=Visual;
    LiquidCore=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MucusCore"));LiquidCore->SetupAttachment(Visual);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    for(UStaticMeshComponent* Part:{Visual.Get(),LiquidCore.Get()})
    {
        if(Sphere.Succeeded())Part->SetStaticMesh(Sphere.Object);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->SetCanEverAffectNavigation(false);Part->bReceivesDecals=false;Part->bAffectDistanceFieldLighting=false;
        Part->SetBoundsScale(3.f); // Includes the longer shader-deformed trailing neck.
    }
    Visual->SetRelativeScale3D(FVector(.25f,.19f,.19f));LiquidCore->SetRelativeScale3D(FVector(.8f,.78f,.78f));
}

void AM14MucusProjectile::BeginPlay()
{
    Super::BeginPlay();PreviousVisualPosition=GetActorLocation();OnRep_Materials();
    // Cosmetic only: never draw from combat's random sequence or allocate a MID.
    const FVector P=GetActorLocation();
    const float Seed=FMath::Frac(FMath::Abs(FMath::Sin(float(P.X*.017+P.Y*.029+P.Z*.043))*43758.5453f));
    for(auto* Part:{Visual.Get(),LiquidCore.Get()})Part->SetCustomPrimitiveDataFloat(0,Seed);
}

void AM14MucusProjectile::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AM14MucusProjectile,ShellMaterial);DOREPLIFETIME(AM14MucusProjectile,CoreMaterial);
}

void AM14MucusProjectile::OnRep_Materials()
{
    if(ShellMaterial)Visual->SetMaterial(0,ShellMaterial);
    if(CoreMaterial)LiquidCore->SetMaterial(0,CoreMaterial);
}

void AM14MucusProjectile::Launch(ASpiralPillarM14* Source,const FVector& Direction,float Speed,float Range,float Damage,
    float SlowPercent,float SlowSeconds,UMaterialInterface* Shell,UMaterialInterface* Core)
{
    Shooter=Source;Velocity=Direction.GetSafeNormal()*Speed;Remaining=Range;HitDamage=Damage;
    SlowAmount=SlowPercent;SlowDuration=SlowSeconds;ShellMaterial=Shell;CoreMaterial=Core;OnRep_Materials();
    SetActorRotation(Direction.Rotation());SetLifeSpan(Range/FMath::Max(1.f,Speed)+.15f);ForceNetUpdate();
}

void AM14MucusProjectile::UpdateLiquidVisual(float Dt,const FVector& Start,const FVector& End)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    VisualAge+=Dt;
    const float Release=FMath::Clamp(VisualAge/.12f,0.f,1.f);
    const float Stretch=1.f+.08f*FMath::Sin(VisualAge*13.f)+.14f*(1.f-Release);
    const float Width=1.f/FMath::Sqrt(Stretch);
    Visual->SetRelativeScale3D(FVector(.25f*Stretch,.19f*Width,.19f*Width));
    for(auto* Part:{Visual.Get(),LiquidCore.Get()})Part->SetCustomPrimitiveDataFloat(1,VisualAge);
    auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>();if(!FX)return;
    const FVector TravelVelocity=Dt>UE_SMALL_NUMBER?(End-Start)/Dt:Velocity;
    if(!bMuzzleShown&&!TravelVelocity.IsNearlyZero())
    {
        FX->AddM14Muzzle(Start,TravelVelocity);bMuzzleShown=true;
    }
    // Distance sampling stays connected across frame rates and replicated steps.
    // Bound catch-up on a hitch; no unbounded particle emission backlog.
    constexpr float Spacing=53.f; // Covers the full 33 m shot inside the existing 64-sample budget.
    const float Distance=FVector::Distance(Start,End);
    float Along=Spacing-TrailRemainder;
    int32 Emitted=0;
    while(Along<=Distance&&Emitted<4&&TrailSamples<64)
    {
        FX->AddM14Trail(FMath::Lerp(Start,End,Along/FMath::Max(Distance,UE_SMALL_NUMBER)),TravelVelocity,TrailSamples++);
        Along+=Spacing;++Emitted;
    }
    TrailRemainder=FMath::Fmod(TrailRemainder+Distance,Spacing);
}

void AM14MucusProjectile::ShowImpact_Implementation(const FHitResult& Hit,FVector IncomingVelocity)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>())
    {
        FX->AddM14Impact(Hit,IncomingVelocity);
    }
}

void AM14MucusProjectile::Tick(float Dt)
{
    Super::Tick(Dt);
    if(!HasAuthority())
    {
        const FVector Here=GetActorLocation();UpdateLiquidVisual(Dt,PreviousVisualPosition,Here);PreviousVisualPosition=Here;return;
    }
    if(!Shooter.IsValid()||Shooter->Dead()){Destroy();return;}
    const float Step=FMath::Min(Remaining,Velocity.Size()*Dt);
    const FVector Start=GetActorLocation(),End=Start+Velocity.GetSafeNormal()*Step;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14Mucus),false,this);Query.AddIgnoredActor(Shooter.Get());
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Contacts;
    GetWorld()->SweepMultiByObjectType(Contacts,Start,End,FQuat::Identity,Objects,FCollisionShape::MakeSphere(9.5f),Query);
    const FHitResult* First=nullptr;
    for(const auto& Contact:Contacts)
    {
        const auto* Component=Contact.GetComponent();const auto* Pawn=Cast<APawn>(Contact.GetActor());
        const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Component==Pawn->GetRootComponent();
        if(!Component||(!PlayerBody&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block))continue;
        if(!First||Contact.Time<First->Time)First=&Contact;
    }
    if(First)
    {
        UpdateLiquidVisual(Dt*First->Time,Start,First->Location);
        const auto* HitPawn=Cast<APawn>(First->GetActor());
        ShowImpact(*First,Velocity);
        AActor* HitActor=First->GetActor();
        if(HitPawn&&HitPawn->IsPlayerControlled())
        {
            auto* Vitals=HitActor->FindComponentByClass<UFPSCombatHealthComponent>();
            if(Vitals&&!Vitals->IsDead())
            {
                const float Before=Vitals->Health;
                UGameplayStatics::ApplyPointDamage(HitActor,HitDamage,Velocity.GetSafeNormal(),*First,
                    Shooter->GetController(),Shooter.Get(),UEnemyRangedDamage::StaticClass());
                // The damage return value can be positive even when a health
                // callback rejects the hit. Add exactly one layer after HP loss.
                if(Vitals->Health<Before&&!Vitals->IsDead()&&!Vitals->IsInvulnerable())
                {
                    if(auto* Status=UCombatStatusFormula::GetOrAdd(HitActor))Status->AddSlow(SlowDuration,SlowAmount);
                    auto* Poison=HitActor->FindComponentByClass<UMaggotPoisonComponent>();
                    if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(HitActor);HitActor->AddInstanceComponent(Poison);Poison->RegisterComponent();}
                    Poison->AddStack(Shooter.Get());
                }
            }
        }
        else if(HitActor&&HitActor->IsA<AFPSIceWall>())
            UGameplayStatics::ApplyPointDamage(HitActor,HitDamage,Velocity.GetSafeNormal(),*First,
                Shooter->GetController(),Shooter.Get(),UEnemyRangedDamage::StaticClass());
        Destroy();return;
    }
    SetActorLocation(End);UpdateLiquidVisual(Dt,Start,End);Remaining-=Step;
    if(Remaining<=0.f)Destroy();
}
