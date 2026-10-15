#include "M66SlamWave.h"
#include "M66IncineratorMonster.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/MagicOcclusion.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Net/UnrealNetwork.h"

AM66SlamWave::AM66SlamWave()
{
    bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(20.f);
    PrimaryActorTick.bCanEverTick=true;InitialLifeSpan=2.f;
    Origin=CreateDefaultSubobject<USceneComponent>(TEXT("ImpactOrigin"));SetRootComponent(Origin);
    Ring=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GroundWave"));Ring->SetupAttachment(Origin);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    Ring->SetStaticMesh(Plane.Object);Ring->SetRelativeLocation(FVector(0,0,3));Ring->SetRelativeScale3D(FVector(.001f));
    Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ring->SetGenerateOverlapEvents(false);
    Ring->SetCastShadow(false);Ring->SetReceivesDecals(false);Ring->SetCanEverAffectNavigation(false);
    Ring->SetVisibility(false);
}
double AM66SlamWave::Clock() const
{
    if(const auto* State=GetWorld()->GetGameState())return State->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void AM66SlamWave::Setup(float InDamage,float Radius,float Seconds,float Stun,UMaterialInterface* Material,double StartedAt)
{
    Damage=FMath::Max(0.f,InDamage);StunSeconds=FMath::Max(0.f,Stun);
    Wave.Radius=FMath::Max(20.f,Radius);Wave.Seconds=FMath::Max(.1f,Seconds);
    Wave.StartedAt=StartedAt;Wave.Material=Material;Wave.Ready=true;
}
void AM66SlamWave::BeginPlay()
{
    Super::BeginPlay();
    if(HasAuthority())SetLifeSpan(FMath::Max(.35f,Wave.Seconds+.35f-float(Clock()-Wave.StartedAt)));
}
void AM66SlamWave::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AM66SlamWave,Wave);}

void AM66SlamWave::ApplyWave(float Radius)
{
    auto* Source=Cast<AM66IncineratorMonster>(GetOwner());if(!IsValid(Source))return;
    const FVector Point=GetActorLocation(),Normal=GetActorUpVector();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M66SlamWave),false,Source);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Point+FVector(0,0,80),FQuat::Identity,
        FCollisionObjectQueryParams::AllDynamicObjects,FCollisionShape::MakeBox(FVector(Radius,Radius,180)),Query);
    // Bodies do not shield each other from a ground pulse; world cover does.
    for(const auto& Overlap:Overlaps)
        if(AActor* Target=Overlap.GetActor();Target&&(Target->IsA<APawn>()||Target->FindComponentByClass<UMonsterCombatComponent>()))Query.AddIgnoredActor(Target);
    TSet<TWeakObjectPtr<AActor>> Seen;
    for(const auto& Overlap:Overlaps)
    {
        if(!IsValid(Source))return;
        auto* Target=Cast<APawn>(Overlap.GetActor());
        if(!IsValid(Target)||Seen.Contains(Target)||HitActors.Contains(Target)||!Target->CanBeDamaged()
            ||RangedAttackQuery::IsFriendlyUnit(Source,Target))continue;
        Seen.Add(Target);
        auto* Vitals=Target->FindComponentByClass<UFPSCombatHealthComponent>();
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if((!Vitals&&!Combat)||(Vitals&&Vitals->IsDead())||(Combat&&Combat->IsDead()))continue;
        auto* Shape=Cast<UPrimitiveComponent>(Target->GetRootComponent());if(!Shape)continue;
        float BodyRadius=0,Half=0;Target->GetSimpleCollisionCylinder(BodyRadius,Half);
        const FVector Feet=Target->GetActorLocation()-FVector(0,0,Half),Delta=Feet-Point;
        const float Height=FVector::DotProduct(Delta,Normal);
        if(FMath::Abs(Height)>75.f)continue;
        const float Distance=(Delta-Normal*Height).Size();
        if(Distance-BodyRadius>Radius||Distance+BodyRadius<PreviousRadius-45.f)continue;
        const FVector Contact=Feet+FVector(0,0,35);FHitResult Block;
        if(MagicOcclusion::TraceBlocker(GetWorld(),Point+Normal*12.f,Contact,Query,Block))continue;
        // Mark the contact even when dodge/parry prevents damage; the same wave
        // must not retry after invulnerability expires while its band passes.
        HitActors.Add(Target);
        FHitResult Hit(Target,Shape,Contact,(Point-Contact).GetSafeNormal());Hit.TraceStart=Point;Hit.TraceEnd=Contact;
        const float Before=Vitals?Vitals->Health:0.f;
        const float Applied=UGameplayStatics::ApplyPointDamage(Target,Damage,(Contact-Point).GetSafeNormal(),Hit,
            Source->GetController(),Source,UEnemyMeleeDamage::StaticClass());
        if(!IsValid(Target)||Applied<=0.f||(Vitals&&(Vitals->IsDead()||Vitals->Health>=Before))||(Combat&&Combat->IsDead()))continue;
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddStun(StunSeconds);
    }
}
void AM66SlamWave::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);if(!Wave.Ready)return;
    const float Age=FMath::Max(0.f,float(Clock()-Wave.StartedAt));
    const float T=FMath::Clamp(Age/Wave.Seconds,0.f,1.f),Radius=FMath::Lerp(20.f,Wave.Radius,T);
    if(HasAuthority()&&!bDamageFinished)
    {ApplyWave(Radius);PreviousRadius=Radius;bDamageFinished=T>=1.f;}
    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(!Dynamic&&Wave.Material)Dynamic=Ring->CreateDynamicMaterialInstance(0,Wave.Material);
        Ring->SetVisibility(Dynamic&&Age<Wave.Seconds+.18f);
        Ring->SetRelativeScale3D(FVector(Radius/50.f,Radius/50.f,1));
        if(Dynamic)
        {
            Dynamic->SetScalarParameterValue(TEXT("Radius"),Radius);
            Dynamic->SetScalarParameterValue(TEXT("Opacity"),FMath::Clamp(Age/.035f,0.f,1.f)*(1-FMath::SmoothStep(Wave.Seconds-.08f,Wave.Seconds+.18f,Age)));
        }
    }
    if(Age>=Wave.Seconds+.2f&&HasAuthority())Destroy();
}
