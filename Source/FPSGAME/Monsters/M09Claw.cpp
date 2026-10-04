#include "HangingBellM09.h"
#include "M09ClawParameters.h"
#include "FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

namespace M09ClawGeometry
{
const FName Shoulders[2]={TEXT("small_upperarm_L"),TEXT("small_upperarm_R")};
const FName Elbows[2]={TEXT("small_forearm_L"),TEXT("small_forearm_R")};
const FName Hands[2]={TEXT("small_hand_L"),TEXT("small_hand_R")};
const FName Tips[2]={TEXT("smallfinger_L_03_03"),TEXT("smallfinger_R_03_03")};
const FName PreviousJoints[2]={TEXT("smallfinger_L_03_02"),TEXT("smallfinger_R_03_02")};
FVector Tip(const USkeletalMeshComponent* Mesh,int32 Side)
{
 const FVector Last=Mesh->GetSocketLocation(Tips[Side]);
 // The endpoint is just beyond the final weighted finger joint, not a remote
 // reach extension. The capsule radius covers the neighbouring visible digits.
 return Last+(Last-Mesh->GetSocketLocation(PreviousJoints[Side])).GetSafeNormal()*4.f;
}
}

bool AHangingBellM09::InClawRange(const APawn* Victim) const
{
 return IsValid(Victim)&&FVector::DistSquared2D(GetActorLocation(),Victim->GetActorLocation())<=FMath::Square(M09Claw::TriggerRange);
}

bool AHangingBellM09::CanClawReach(const APawn* Victim) const
{
 if(!InClawRange(Victim)||!Clip(TEXT("Claw")))return false;
 float Radius=0.f,HalfHeight=0.f;Victim->GetSimpleCollisionCylinder(Radius,HalfHeight);
 for(int32 Side=0;Side<2;++Side)
 {
  const FVector Shoulder=GetMesh()->GetSocketLocation(M09ClawGeometry::Shoulders[Side]);
  const FVector Elbow=GetMesh()->GetSocketLocation(M09ClawGeometry::Elbows[Side]);
  const FVector Hand=GetMesh()->GetSocketLocation(M09ClawGeometry::Hands[Side]);
  const float Reach=FVector::Distance(Shoulder,Elbow)+FVector::Distance(Elbow,Hand)+
   FVector::Distance(Hand,M09ClawGeometry::Tip(GetMesh(),Side))+M09Claw::PalmRadius;
  // Choose the attack using the stable near band and vertical reach separately.
  // The old shoulder-to-capsule sphere shrank the near band with ceiling height
  // and rejected targets directly under the forward-offset shoulders.
  const float VerticalGap=FMath::Max(0.f,float(FMath::Abs(Shoulder.Z-Victim->GetActorLocation().Z))-HalfHeight);
  if(VerticalGap<=Reach)return true;
 }
 return false;
}

void AHangingBellM09::SweepClawContact(int32 Side,bool ResetPrevious)
{
 if(!HasAuthority()||Dead()||State!=EM09State::Claw)return;
 const FVector Hand=GetMesh()->GetSocketLocation(M09ClawGeometry::Hands[Side]);
 const FVector Tip=M09ClawGeometry::Tip(GetMesh(),Side),Span=Tip-Hand;
 const FVector Center=(Hand+Tip)*.5f;
 if(ResetPrevious)PreviousContact[Side]=Center;
 const FQuat Rotation=Span.IsNearlyZero()?FQuat::Identity:
  FQuat::FindBetweenNormals(FVector::UpVector,Span.GetSafeNormal());
 FCollisionQueryParams Query(SCENE_QUERY_STAT(M09ClawContact),false,this);
 // Reuse M07's palm-to-claw capsule technique with M09's real small-hand bones.
 TArray<FHitResult> Hits;
 GetWorld()->SweepMultiByObjectType(Hits,PreviousContact[Side],Center,Rotation,
  FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeCapsule(M09Claw::PalmRadius,
  M09Claw::PalmRadius+Span.Size()*.5f),Query);
 PreviousContact[Side]=Center;
 for(const FHitResult& Hit:Hits)
 {
  APawn* Victim=Cast<APawn>(Hit.GetActor());
  if(!IsValid(Victim)||!Victim->IsPlayerControlled()||HitVictims.Contains(Victim))continue;
  if(auto* HealthComponent=Victim->FindComponentByClass<UFPSCombatHealthComponent>();HealthComponent&&HealthComponent->IsDead())continue;
  if(!HasAttackSight(Victim))continue;
  const FVector Point=Hit.bStartPenetrating?Center:Hit.ImpactPoint;
  FHitResult Obstacle;FCollisionQueryParams Cover(SCENE_QUERY_STAT(M09ClawCover),false,this);
  Cover.AddIgnoredActor(Victim);
  if(GetWorld()->LineTraceSingleByChannel(Obstacle,
   GetMesh()->GetSocketLocation(M09ClawGeometry::Shoulders[Side]),Point,ECC_Visibility,Cover))continue;
  HitVictims.Add(Victim);
  Deal(Victim,PhysicalAttack*M09Claw::DamageMultiplier,false,Point);
  // Parry/death can synchronously change state inside the damage callback.
  if(Dead()||State!=EM09State::Claw)return;
 }
}
