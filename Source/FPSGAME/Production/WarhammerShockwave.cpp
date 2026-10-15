#include "WarhammerShockwave.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerCombat.h"
#include "WarhammerSlamFXSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MagicOcclusion.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"
#include "Net/UnrealNetwork.h"

AWarhammerShockwave::AWarhammerShockwave()
{
    bReplicates=true;SetReplicateMovement(true);PrimaryActorTick.bCanEverTick=true;
    Ring=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GroundRing"));SetRootComponent(Ring);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    static ConstructorHelpers::FObjectFinder<USoundBase> GroundImpact(TEXT("/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact.S_Warhammer_GroundImpact"));
    ImpactSound=GroundImpact.Object;
    Ring->SetStaticMesh(Plane.Object);Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ring->SetCastShadow(false);Ring->SetReceivesDecals(false);Ring->SetCanEverAffectNavigation(false);
    NetUpdateFrequency=30.f;InitialLifeSpan=1.f;
}
double AWarhammerShockwave::Clock() const
{
    if(const auto* State=GetWorld()->GetGameState())return State->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void AWarhammerShockwave::Setup(const FColdSteelSkillShot& InShot,float Radius,float StunSeconds)
{
    Shot=InShot;MaxRadius=Radius;HeavyStunSeconds=StunSeconds;StartedAt=Clock();bConfigured=true;ForceNetUpdate();
}
void AWarhammerShockwave::BeginPlay()
{
    Super::BeginPlay();
    Ring->SetRelativeScale3D(FVector(.001));
    if(GetNetMode()!=NM_DedicatedServer)
        Material=Ring->CreateDynamicMaterialInstance(0,LoadObject<UMaterialInterface>(nullptr,
            TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV1/M_WarhammerGroundWave.M_WarhammerGroundWave")));
}
void AWarhammerShockwave::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AWarhammerShockwave,MaxRadius);DOREPLIFETIME(AWarhammerShockwave,StartedAt);
}
void AWarhammerShockwave::ApplyWave(float Radius)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);ColdSteelAuthority::FScope Scope(Profile);
    const FVector Origin=GetActorLocation();
    TArray<FOverlapResult> Overlaps;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(WarhammerWave),false,Pawn);
    GetWorld()->OverlapMultiByObjectType(Overlaps,Origin+FVector(0,0,65),FQuat::Identity,
        FCollisionObjectQueryParams::AllDynamicObjects,FCollisionShape::MakeBox(FVector(Radius,Radius,110)),Q);
    for(const auto& Overlap:Overlaps)if(auto* Body=Cast<APawn>(Overlap.GetActor()))Q.AddIgnoredActor(Body);
    for(const auto& Overlap:Overlaps)
    {
        auto* Target=Overlap.GetActor();auto* Shape=Overlap.GetComponent();
        auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Shape||!Combat||Combat->IsDead()||Target==Pawn||HitActors.Contains(Target)||!Target->CanBeDamaged()
            ||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Player")))continue;
        if(const auto* Body=Cast<APawn>(Target);Body&&Body->IsPlayerControlled())continue;
        const auto Bounds=Shape->Bounds;
        if(FMath::Abs(Bounds.Origin.Z-Bounds.BoxExtent.Z-Origin.Z)>70.f)continue;
        FVector Point;
        if(Shape->GetClosestPointOnCollision(Origin+FVector(0,0,30),Point)<0.f)Point=Bounds.GetBox().GetClosestPointTo(Origin+FVector(0,0,30));
        const FVector Normal=GetActorUpVector(),ToPoint=Point-Origin;
        const FVector PlaneOffset=ToPoint-Normal*FVector::DotProduct(ToPoint,Normal);
        if(PlaneOffset.SizeSquared()>FMath::Square(Radius))continue;
        const FVector ToBounds=Bounds.Origin-Origin;
        const float FarEdge=(ToBounds-Normal*FVector::DotProduct(ToBounds,Normal)).Size()+Bounds.BoxExtent.Size2D();
        if(FarEdge<PreviousRadius-16.f)continue;
        // The expanding band reaches every target once, even across a late frame.
        // Feet/height and solid-cover checks prevent cross-floor/wall damage.
        FHitResult Cover;
        if(MagicOcclusion::TraceBlocker(GetWorld(),Origin+FVector(0,0,12),Point,Q,Cover)&&Cover.GetActor()!=Target)continue;
        HitActors.Add(Target);
        FHitResult Hit(Target,Shape,Point,(Origin-Point).GetSafeNormal());Hit.TraceStart=Origin;Hit.TraceEnd=Point;
        FWeaponDamageResult Result;
        const float Damage=ColdSteelSkills::ApplyHit(Pawn,Hit,Shot.DamagePanel.Total(),(Point-Origin).GetSafeNormal(),Shot,&Result);
        if(Damage>0.f||Combat->IsDead())Pawn->NotifyConfirmedWeaponHit(Target,Damage,&Result);
        if(Damage>0.f)WarhammerCombat::ApplyHeavyStun(Target,HeavyStunSeconds);
    }
}
void AWarhammerShockwave::Tick(float Delta)
{
    Super::Tick(Delta);
    if(StartedAt<=0.||(HasAuthority()&&!bConfigured))return;
    const float T=FMath::Clamp(float((Clock()-StartedAt)/WarhammerHeavy::WaveSeconds),0.f,1.f);
    const float Radius=FMath::Lerp(12.f,MaxRadius,T);
    if(HasAuthority()){ApplyWave(Radius);PreviousRadius=Radius;}
    // Scale only the visual component; replication owns the impact transform.
    Ring->SetRelativeScale3D(FVector(Radius/50.f,Radius/50.f,1.f));
    if(Material)Material->SetScalarParameterValue(TEXT("Opacity"),FMath::Pow(1.f-T,1.15f));
    if(!bSoundPlayed&&GetNetMode()!=NM_DedicatedServer)
    {
        bSoundPlayed=true;
        if(auto* FX=GetWorld()->GetSubsystem<UWarhammerSlamFXSubsystem>())
            FX->Emit(GetActorLocation()-GetActorUpVector()*2.f,GetActorQuat(),MaxRadius,float(Clock()-StartedAt));
        // Heavy and sprint attacks spawn this same replicated wave at contact.
        // Keep the supplied impact's pitch and cache it before the impact tick.
        if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,GetActorLocation(),1.f,1.f);
    }
    if(T>=1.f&&HasAuthority())Destroy();
}
