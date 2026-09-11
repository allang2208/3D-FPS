#include "PoisonMaggotSpawner.h"
#include "PoisonMaggotMonster.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
APoisonMaggotSpawner::APoisonMaggotSpawner(){RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("SpawnPoint"));}
void APoisonMaggotSpawner::BeginPlay()
{
 Super::BeginPlay();
 // Other monster regressions own isolated fixtures; a newly placed enemy must
 // not inject unrelated damage into their tests. Normal village play is unchanged.
 if(FParse::Param(FCommandLine::Get(),TEXT("HandBrainAudit"))||FParse::Param(FCommandLine::Get(),TEXT("NurseAudit"))||FParse::Param(FCommandLine::Get(),TEXT("MonsterAIAudit")))return;
 if(HasAuthority()&&bEnabled)GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::SpawnMonster,1,false);
}
void APoisonMaggotSpawner::SpawnMonster()
{
 if(!HasAuthority()||!bEnabled||IsValid(LiveMonster)||!MonsterClass)return;
 auto Retry=[this](){GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::SpawnMonster,10,false);};
 if(auto* P=UGameplayStatics::GetPlayerPawn(this,0))if(FVector::Dist2D(P->GetActorLocation(),GetActorLocation())<MinimumPlayerDistance){Retry();return;}
 FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotSpawn),false,this);FVector At=GetActorLocation();
 if(!GetWorld()->LineTraceSingleByChannel(Hit,At+FVector(0,0,200),At-FVector(0,0,400),ECC_WorldStatic,Q)||Hit.ImpactNormal.Z<.94f){Retry();return;}
 At=Hit.ImpactPoint+FVector(0,0,72);
 if(GetWorld()->OverlapBlockingTestByChannel(At,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(71,71),Q)){Retry();return;}
 FActorSpawnParameters P;P.Owner=this;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
 LiveMonster=GetWorld()->SpawnActor<APoisonMaggotMonster>(MonsterClass,At,GetActorRotation(),P);
 if(LiveMonster){++SpawnCount;LiveMonster->OnDestroyed.AddDynamic(this,&ThisClass::MonsterDestroyed);}else Retry();
}
void APoisonMaggotSpawner::MonsterDestroyed(AActor*){LiveMonster=nullptr;if(bEnabled&&!IsActorBeingDestroyed())GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::SpawnMonster,FMath::Max(1.f,RespawnSeconds),false);}
void APoisonMaggotSpawner::EndPlay(const EEndPlayReason::Type Reason){GetWorldTimerManager().ClearTimer(Timer);if(IsValid(LiveMonster))LiveMonster->OnDestroyed.RemoveDynamic(this,&ThisClass::MonsterDestroyed);Super::EndPlay(Reason);}
bool APoisonMaggotSpawner::FindVillageSpawn(UObject* Context,FVector Origin,FRotator Facing,FVector& Location)
{
 auto* W=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);if(!W)return false;FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotVillage),false);
 for(float Dist:{2100.f,2500.f,1800.f,1500.f})for(float Angle:{60.f,-60.f,90.f,-90.f,120.f,-120.f,0.f,180.f})
 {
  const FVector Near=Origin+FRotator(0,Facing.Yaw+Angle,0).Vector()*Dist;FHitResult H;
  if(!W->LineTraceSingleByChannel(H,Near+FVector(0,0,400),Near-FVector(0,0,700),ECC_WorldStatic,Q)||H.ImpactNormal.Z<.94f)continue;
  const FVector P=H.ImpactPoint+FVector(0,0,72);if(FMath::Abs(P.Z-Origin.Z)>180)continue;
  if(W->OverlapBlockingTestByChannel(P,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(70,70),Q))continue;
  // Four footprint probes ensure the full elongated body has supported terrain.
  bool Supported=true;for(FVector Offset:{FVector(100,0,0),FVector(-100,0,0),FVector(0,70,0),FVector(0,-70,0)})
  {FHitResult Edge;if(!W->LineTraceSingleByChannel(Edge,P+Offset,P+Offset-FVector(0,0,160),ECC_WorldStatic,Q)||Edge.ImpactNormal.Z<.9f||FMath::Abs(Edge.ImpactPoint.Z-(P.Z-72))>18){Supported=false;break;}}
  if(Supported){Location=P;return true;}
 }return false;
}
