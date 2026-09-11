#include "PoisonMaggotProjectile.h"
#include "PoisonMaggotMonster.h"
#include "FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
APoisonMaggotProjectile::APoisonMaggotProjectile()
{
 PrimaryActorTick.bCanEverTick=true;
 Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VenomDroplet"));RootComponent=Visual;
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
 if(Sphere.Succeeded())Visual->SetStaticMesh(Sphere.Object);
 Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetCastShadow(false);Visual->SetRelativeScale3D(FVector(.15,.095,.095));
}
void APoisonMaggotProjectile::Launch(APoisonMaggotMonster* Source,FVector Dir,float Speed,float Range,float Damage,float Chance)
{
 Shooter=Source;Velocity=Dir.GetSafeNormal()*Speed;Remaining=Range;HitDamage=Damage;PoisonChance=Chance;
 SetActorRotation(Dir.Rotation());if(Source->VenomMaterial)Visual->SetMaterial(0,Source->VenomMaterial);SetLifeSpan(Range/FMath::Max(1.f,Speed)+.1f);
}
void APoisonMaggotProjectile::Tick(float Dt)
{
 Super::Tick(Dt);if(!HasAuthority())return;
 if(!Shooter.IsValid()||Shooter->Dead()){Destroy();return;}
 const float Step=FMath::Min(Remaining,Velocity.Size()*Dt);const FVector Start=GetActorLocation(),End=Start+Velocity.GetSafeNormal()*Step;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotVenom),false,this);Q.AddIgnoredActor(Shooter.Get());FHitResult Hit;
 // The FPS capsule ignores Visibility to avoid blocking its own weapon traces.
 FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_Pawn);
 if(GetWorld()->SweepSingleByObjectType(Hit,Start,End,FQuat::Identity,Objects,FCollisionShape::MakeSphere(4.75f),Q))
 {
  if(auto* P=Cast<APawn>(Hit.GetActor()))if(P->IsPlayerControlled())
  {
   auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();
   if(H&&!H->IsDead())
   {
    UGameplayStatics::ApplyDamage(P,HitDamage,Shooter->GetController(),Shooter.Get(),UMaggotVenomDamage::StaticClass());++Shooter->ProjectileHits;
    if(!H->IsDead()&&FMath::FRand()<PoisonChance){auto* Poison=P->FindComponentByClass<UMaggotPoisonComponent>();if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(P);P->AddInstanceComponent(Poison);Poison->RegisterComponent();}Poison->AddStack(Shooter.Get());}
   }
  }
  Destroy();return;
 }
 SetActorLocation(End);Remaining-=Step;if(Remaining<=0)Destroy();
}
UMaggotPoisonComponent::UMaggotPoisonComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UMaggotPoisonComponent::AddStack(APoisonMaggotMonster* Source)
{
 if(!GetOwner()->HasAuthority()||!IsValid(Source))return;
 auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();if(!H||H->IsDead())return;
 if(Stacks==0)NextTick=1;Stacks=FMath::Min(20,Stacks+1);DecayLeft=5;DamageSource=Source;DamageInstigator=Source->GetController();SetComponentTickEnabled(true);
}
void UMaggotPoisonComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);if(!GetOwner()->HasAuthority())return;
 auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();if(!H||H->IsDead()){Stacks=0;SetComponentTickEnabled(false);return;}
 // Process tick/decay events in temporal order even when a frame crosses both.
 while(Dt>0&&Stacks>0&&!H->IsDead())
 {
  const float Step=FMath::Min(Dt,FMath::Min(NextTick,DecayLeft));Dt-=Step;NextTick-=Step;DecayLeft-=Step;
  if(NextTick<=UE_KINDA_SMALL_NUMBER){UGameplayStatics::ApplyDamage(GetOwner(),Stacks,DamageInstigator.Get(),DamageSource.Get(),UMaggotPoisonDamage::StaticClass());++TicksApplied;NextTick=1;}
  if(DecayLeft<=UE_KINDA_SMALL_NUMBER){--Stacks;DecayLeft=5;}
 }
 if(H->IsDead())Stacks=0;if(Stacks==0)SetComponentTickEnabled(false);
}
