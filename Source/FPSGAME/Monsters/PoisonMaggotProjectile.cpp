#include "PoisonMaggotProjectile.h"
#include "PoisonMaggotMonster.h"
#include "PoisonMaggotVenomFX.h"
#include "FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "../UI/StatusEffectsComponent.h"
APoisonMaggotProjectile::APoisonMaggotProjectile()
{
 PrimaryActorTick.bCanEverTick=true;
 Visual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VenomDroplet"));RootComponent=Visual;
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> Liquid(TEXT("/Game/Fluids/VenomProjectiles20260924/M_VenomBody.M_VenomBody"));
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> Core(TEXT("/Game/Fluids/VenomProjectiles20260924/M_VenomCore.M_VenomCore"));
 if(Sphere.Succeeded())Visual->SetStaticMesh(Sphere.Object);
 Visual->SetMaterial(0,Liquid.Object);
 Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetCastShadow(false);Visual->SetRelativeScale3D(FVector(.125,.095,.095));
 Visual->SetCanEverAffectNavigation(false);Visual->bReceivesDecals=false;Visual->bAffectDistanceFieldLighting=false;
 Visual->SetBoundsScale(1.6f);
 LiquidCore=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VenomOpaqueCore"));LiquidCore->SetupAttachment(Visual);
 LiquidCore->SetStaticMesh(Sphere.Object);LiquidCore->SetMaterial(0,Core.Object);
 LiquidCore->SetRelativeScale3D(FVector(.80,.78,.78));
 LiquidCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);LiquidCore->SetCastShadow(false);
 LiquidCore->SetCanEverAffectNavigation(false);LiquidCore->bReceivesDecals=false;LiquidCore->bAffectDistanceFieldLighting=false;
 LiquidCore->SetBoundsScale(1.6f);
}
void APoisonMaggotProjectile::Launch(APoisonMaggotMonster* Source,FVector Dir,float Speed,float Range,float Damage,float Chance)
{
 Shooter=Source;Velocity=Dir.GetSafeNormal()*Speed;Remaining=Range;HitDamage=Damage;PoisonChance=Chance;
 // Cosmetics use their own random stream, never consuming combat poison/spread RNG.
 VisualRandom.Initialize(int32(GetUniqueID()));VisualPhase=VisualRandom.FRand()*2.f*PI;
 Visual->SetCustomPrimitiveDataFloat(0,VisualPhase/(2.f*PI));
 LiquidCore->SetCustomPrimitiveDataFloat(0,VisualPhase/(2.f*PI));
 SetActorRotation(Dir.Rotation());SetLifeSpan(Range/FMath::Max(1.f,Speed)+.1f);
}
void APoisonMaggotProjectile::UpdateLiquidVisual(float Dt,const FVector& Start,const FVector& End)
{
 const float PreviousAge=VisualAge;VisualAge+=Dt;
 const float Stretch=1.f+.09f*FMath::Sin(VisualAge*17.f+VisualPhase);
 const float Width=1.f/FMath::Sqrt(Stretch);
 Visual->SetRelativeScale3D(FVector(.125f*Stretch,.095f*Width,.095f*Width));
 FRotator Direction=Velocity.Rotation();Direction.Roll=FMath::RadiansToDegrees(VisualPhase)+VisualAge*48.f;
 SetActorRotation(Direction);
 LiquidCore->SetRelativeScale3D(FVector(.8f,.78f+.025f*FMath::Sin(VisualAge*11.f+VisualPhase),.78f));
 auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>();
 if(!FX)return;
 // Emit along the traveled segment, not as a cluster at the current endpoint.
 int32 Emitted=0;
 while(NextTrail<=VisualAge&&Emitted<4)
 {
  const float Alpha=Dt>UE_SMALL_NUMBER?FMath::Clamp((NextTrail-PreviousAge)/Dt,0.f,1.f):1.f;
  FX->AddTrail(FMath::Lerp(Start,End,Alpha),Velocity,(TrailCount++%3)==0);
  NextTrail+=.065f;++Emitted;
 }
 if(NextTrail<=VisualAge)NextTrail=VisualAge+.065f;
}
void APoisonMaggotProjectile::Tick(float Dt)
{
 Super::Tick(Dt);if(!HasAuthority())return;
 if(!Shooter.IsValid()||Shooter->Dead()){Destroy();return;}
 const float Step=FMath::Min(Remaining,Velocity.Size()*Dt);const FVector Start=GetActorLocation(),End=Start+Velocity.GetSafeNormal()*Step;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotVenom),false,this);Q.AddIgnoredActor(Shooter.Get());FHitResult Hit;
 // The FPS capsule ignores Visibility to avoid blocking its own weapon traces.
 FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_Pawn);
 // Object queries include overlap-only fog/trigger boxes. Gather all contacts so
 // an overlap volume cannot hide a real blocking surface or the player capsule.
 TArray<FHitResult> Contacts;GetWorld()->SweepMultiByObjectType(Contacts,Start,End,FQuat::Identity,Objects,FCollisionShape::MakeSphere(4.75f),Q);
 bool Blocking=false;
 for(const auto& Contact:Contacts)
 {
  const auto* Component=Contact.GetComponent();const auto* Pawn=Cast<APawn>(Contact.GetActor());
  const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Component&&Component==Pawn->GetRootComponent();
  if(!Component||(!PlayerBody&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block))continue;
  if(!Blocking||Contact.Time<Hit.Time){Hit=Contact;Blocking=true;}
 }
 if(Blocking)
 {
  UpdateLiquidVisual(Dt*Hit.Time,Start,Hit.Location);
  if(auto* FX=GetWorld()->GetSubsystem<UPoisonMaggotVenomFX>())FX->AddImpact(Hit,Velocity);
  if(FParse::Param(FCommandLine::Get(),TEXT("MonsterFeedbackProbe")))UE_LOG(LogTemp,Display,TEXT("MAGGOT_IMPACT_PROBE actor=%s component=%s profile=%s visibility=%d pawn=%d initial=%d"),*GetPathNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),Hit.GetComponent()?*Hit.GetComponent()->GetCollisionProfileName().ToString():TEXT("none"),Hit.GetComponent()?int32(Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Visibility)):-1,Hit.GetComponent()?int32(Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)):-1,Hit.bStartPenetrating);
  if(auto* P=Cast<APawn>(Hit.GetActor()))if(P->IsPlayerControlled())
  {
   auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();
   if(H&&!H->IsDead())
   {
    const float Applied=UGameplayStatics::ApplyDamage(P,HitDamage,Shooter->GetController(),Shooter.Get(),UMaggotVenomDamage::StaticClass());++Shooter->ProjectileHits;
    if(Applied>0.f&&!H->IsDead()&&FMath::FRand()<PoisonChance){auto* Poison=P->FindComponentByClass<UMaggotPoisonComponent>();if(!Poison){Poison=NewObject<UMaggotPoisonComponent>(P);P->AddInstanceComponent(Poison);Poison->RegisterComponent();}Poison->AddStack(Shooter.Get());}
   }
  }
  Destroy();return;
 }
 SetActorLocation(End);UpdateLiquidVisual(Dt,Start,End);Remaining-=Step;if(Remaining<=0)Destroy();
}
UMaggotPoisonComponent::UMaggotPoisonComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UMaggotPoisonComponent::AddStack(APoisonMaggotMonster* Source)
{
 if(!GetOwner()->HasAuthority()||!IsValid(Source))return;
 auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();if(!H||H->IsDead()||H->IsInvulnerable())return;
 if(Stacks==0)NextTick=1;Stacks=FMath::Min(20,Stacks+1);DecayLeft=5;DamageSource=Source;DamageInstigator=Source->GetController();SetComponentTickEnabled(true);
 UStatusEffectsComponent::Notify(GetOwner());
}
void UMaggotPoisonComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
 Super::TickComponent(Dt,Type,Tick);if(!GetOwner()->HasAuthority())return;
 const int32 Before=Stacks;auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();if(!H||H->IsDead()){Stacks=0;SetComponentTickEnabled(false);if(Before)UStatusEffectsComponent::Notify(GetOwner());return;}
 // Process tick/decay events in temporal order even when a frame crosses both.
 while(Dt>0&&Stacks>0&&!H->IsDead())
 {
  const float Step=FMath::Min(Dt,FMath::Min(NextTick,DecayLeft));Dt-=Step;NextTick-=Step;DecayLeft-=Step;
  if(NextTick<=UE_KINDA_SMALL_NUMBER){UGameplayStatics::ApplyDamage(GetOwner(),Stacks,DamageInstigator.Get(),DamageSource.Get(),UMaggotPoisonDamage::StaticClass());++TicksApplied;NextTick=1;}
  if(DecayLeft<=UE_KINDA_SMALL_NUMBER){--Stacks;DecayLeft=5;}
 }
 if(H->IsDead())Stacks=0;if(Stacks==0)SetComponentTickEnabled(false);
 if(Stacks!=Before)UStatusEffectsComponent::Notify(GetOwner());
}
