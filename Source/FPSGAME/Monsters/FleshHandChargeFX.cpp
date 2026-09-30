#include "FleshHandChargeFX.h"
#include "FleshHandMonster.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

bool UFleshHandChargeFX::DoesSupportWorldType(EWorldType::Type T) const {return T==EWorldType::Game||T==EWorldType::PIE;}
TStatId UFleshHandChargeFX::GetStatId() const {RETURN_QUICK_DECLARE_CYCLE_STAT(FleshHandChargeFX,STATGROUP_Tickables);}
float UFleshHandChargeFX::ViewDistance(const FVector& At) const
{
 if(auto* PC=GetWorld()->GetFirstPlayerController()){FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);return FVector::Distance(Eye,At);}
 return TNumericLimits<float>::Max();
}
FVector UFleshHandChargeFX::Ground(AFleshHandMonster* H) const
{
 const auto& Floor=H->GetCharacterMovement()->CurrentFloor;
 return Floor.IsWalkableFloor()?FVector(Floor.HitResult.ImpactPoint):H->GetActorLocation()-FVector(0,0,H->GetSimpleCollisionHalfHeight());
}
bool UFleshHandChargeFX::Prepare(AFleshHandMonster* H)
{
 if(bReady)return true;
 if(GetWorld()->GetNetMode()==NM_DedicatedServer||!H->ChargeDustMaterial||!H->ChargeAirMaterial||!H->ChargeSkinMaterial||!H->ChargeChipMaterial||!H->ChargeFXPlane||!H->ChargeFXCube)return false;
 Plane=H->ChargeFXPlane;Cube=H->ChargeFXCube;
 for(int32 G=0;G<3;++G)
 {
  auto* R=NewObject<UInstancedStaticMeshComponent>(this);R->SetMobility(EComponentMobility::Movable);
  R->SetStaticMesh(G==2?Cube:Plane);R->SetMaterial(0,G==0?H->ChargeDustMaterial:G==1?H->ChargeAirMaterial:H->ChargeChipMaterial);
  R->SetCollisionEnabled(ECollisionEnabled::NoCollision);R->SetGenerateOverlapEvents(false);R->SetCanEverAffectNavigation(false);
  R->SetCastShadow(false);R->bReceivesDecals=false;R->bAffectDistanceFieldLighting=false;
  R->SetNumCustomDataFloats(4);R->SetCullDistances(2800,3500);
  const int32 Count=SlotCount*(G==0?DustPerSlot:G==1?AirPerSlot:ChipsPerSlot);
  Transforms[G].Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),Count);
  R->PreAllocateInstancesMemory(Count);R->AddInstances(Transforms[G],false,false,false);R->RegisterComponentWithWorld(GetWorld());Renderers.Add(R);
 }
 PreviousSkin.SetNum(SlotCount);
 for(int32 I=0;I<SlotCount;++I)
 {
  Skin.Add(UMaterialInstanceDynamic::Create(H->ChargeSkinMaterial,this));
  auto* A=NewObject<UAudioComponent>(this);A->bAutoActivate=false;A->bAutoDestroy=false;
  A->bOverrideAttenuation=true;A->AttenuationOverrides.bAttenuate=true;A->AttenuationOverrides.bSpatialize=true;
  A->AttenuationOverrides.AttenuationShapeExtents=FVector(180);A->AttenuationOverrides.FalloffDistance=2600;
  A->RegisterComponentWithWorld(GetWorld());Audio.Add(A);
 }
 bReady=true;return true;
}
int32 UFleshHandChargeFX::Find(AFleshHandMonster* H) const
{for(int32 I=0;I<SlotCount;++I)if(Slots[I].Used&&!Slots[I].Released&&Slots[I].Hand.Get()==H)return I;return INDEX_NONE;}
void UFleshHandChargeFX::Hide(int32 G,int32 I)
{Transforms[G][I].SetScale3D(FVector::ZeroVector);Renderers[G]->SetCustomDataValue(I,0,0,false);}
void UFleshHandChargeFX::Release(int32 I)
{
 auto& S=Slots[I];if(S.Released)return;
 if(auto* H=S.Hand.Get())if(H->GetMesh()->GetOverlayMaterial()==Skin[I])H->GetMesh()->SetOverlayMaterial(PreviousSkin[I]);
 PreviousSkin[I]=nullptr;Audio[I]->Stop();S.Released=true;S.ReleaseAge=0;
 for(int32 N=0;N<2;++N)Hide(1,I*AirPerSlot+N);
}
void UFleshHandChargeFX::Cancel(AFleshHandMonster* H){const int32 I=Find(H);if(I!=INDEX_NONE)Release(I);}
void UFleshHandChargeFX::Dust(int32 I,const FVector& At,const FVector& Direction,int32 Count,float Strength)
{
 const float Distance=ViewDistance(At);if(Distance>3500)return;
 if(Distance>1800)Count=FMath::Min(Count,2);
 auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();if(!Budget)return;
 Count=Budget->AllocateDetail(At,Count,true);
 const FVector Wind=Count?Budget->WindAt(At)*.12f:FVector::ZeroVector;
 auto& S=Slots[I];
 for(int32 N=0;N<Count;++N)
 {
  auto& P=S.Dust[S.Cursor++%DustPerSlot];const FVector Side=FVector::CrossProduct(Direction,FVector::UpVector);
  P.Position=At+Side*Random.FRandRange(-24,24)+FVector(0,0,14);P.FloorZ=At.Z+3;
  P.Velocity=Direction*Random.FRandRange(45,105)*Strength+Side*Random.FRandRange(-42,42)+FVector(0,0,Random.FRandRange(15,30))+Wind;
  P.Age=0;P.Life=Random.FRandRange(.38f,.68f);P.Size=Random.FRandRange(42,70)*Strength;P.Seed=Random.FRand();
 }
}
void UFleshHandChargeFX::Arc(int32 I,const FVector& At,const FVector& Normal,float Size,float Life)
{auto& S=Slots[I];S.ArcPosition=At;S.ArcNormal=Normal.GetSafeNormal();S.ArcSize=Size;S.ArcLife=Life;S.ArcAge=0;}
void UFleshHandChargeFX::Transition(AFleshHandMonster* H,EFleshHandState Previous)
{
 if(!H||H->bMinion||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
 int32 I=Find(H);
 if(H->State==EFleshHandState::ChargeWindup)
 {
  if(I!=INDEX_NONE||ViewDistance(H->GetActorLocation())>3500||!Prepare(H))return;
  for(int32 N=0;N<SlotCount;++N)if(!Slots[N].Used){I=N;break;}
  if(I==INDEX_NONE)return;
  Slots[I]=FSlot{};auto& S=Slots[I];S.Used=true;S.Hand=H;++ActiveSlots;
  PreviousSkin[I]=H->GetMesh()->GetOverlayMaterial();Skin[I]->SetScalarParameterValue(TEXT("Tension"),0);
  H->GetMesh()->SetOverlayMaterial(Skin[I]);Audio[I]->SetWorldLocation(H->GetActorLocation());
  Audio[I]->SetSound(H->ChargeWindupSound);Audio[I]->SetPitchMultiplier(1.2f/FMath::Max(.1f,H->ChargeWindupSeconds));Audio[I]->SetVolumeMultiplier(.65f);
  if(H->ChargeWindupSound)Audio[I]->Play();return;
 }
 if(I==INDEX_NONE)return;
 if(H->State==EFleshHandState::ChargeRush)
 {
  Dust(I,Ground(H),-H->GetActorForwardVector(),5,1.f);
  Arc(I,H->GetMesh()->GetSocketLocation(TEXT("middle_01"))+H->GetActorForwardVector()*22,H->GetActorForwardVector(),120,.16f);
  Audio[I]->Stop();Audio[I]->SetSound(H->ChargeRushSound);Audio[I]->SetPitchMultiplier(1);Audio[I]->SetVolumeMultiplier(.8f);
  if(H->ChargeRushSound)Audio[I]->Play();return;
 }
 if(H->State==EFleshHandState::ChargeRecover)
 {
  if(Previous==EFleshHandState::ChargeRush&&!Slots[I].Impacted)Dust(I,Ground(H),H->GetActorForwardVector(),4,.85f);
  Release(I);return;
 }
 Release(I);
}
void UFleshHandChargeFX::Impact(AFleshHandMonster* H,const FHitResult& Hit,bool bDamagedPlayer)
{
 const int32 I=Find(H);if(I==INDEX_NONE)return;auto& S=Slots[I];if(S.Impacted)return;S.Impacted=true;
 const bool Body=Cast<APawn>(Hit.GetActor())!=nullptr;
 if(!Body||bDamagedPlayer)Arc(I,Hit.ImpactPoint+Hit.ImpactNormal*5,Hit.ImpactNormal,Body?85:120,.23f);
 Dust(I,Ground(H),-H->GetActorForwardVector(),Body?2:5,Body?.65f:1.f);
 if(!Body&&ViewDistance(Hit.ImpactPoint)<1800)
 {
  auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();const int32 Count=Budget?Budget->AllocateDetail(Hit.ImpactPoint,ChipsPerSlot,true):0;
  for(int32 N=0;N<Count;++N){auto& P=S.Chips[N];P.Position=Hit.ImpactPoint+Hit.ImpactNormal*6;P.FloorZ=Ground(H).Z+2;
   P.Velocity=Hit.ImpactNormal*90+Random.VRand()*65+FVector(0,0,110);P.Age=0;P.Life=.42f;P.Size=Random.FRandRange(1.5f,3.5f);P.Seed=Random.FRand();}
 }
}
void UFleshHandChargeFX::Tick(float Delta)
{
 auto* PC=GetWorld()->GetFirstPlayerController();FVector Eye=FVector::ZeroVector;FRotator R;if(PC)PC->GetPlayerViewPoint(Eye,R);
 for(int32 I=0;I<SlotCount;++I)
 {
  auto& S=Slots[I];if(!S.Used)continue;auto* H=S.Hand.Get();
  if(!S.Released&&(!H||H->Dead()||ViewDistance(H->GetActorLocation())>3800))Release(I);
  if(!S.Released&&H)
  {
   const float T=FMath::Clamp(H->StateSeconds/FMath::Max(.1f,H->ChargeWindupSeconds),0.f,1.f);
   Skin[I]->SetScalarParameterValue(TEXT("Tension"),H->State==EFleshHandState::ChargeWindup?T*.75f:.35f);
   Audio[I]->SetWorldLocation(H->GetActorLocation());
   if(H->State==EFleshHandState::ChargeRush)
   {
    const FVector V=H->GetVelocity(),F=H->GetActorForwardVector(),Side=H->GetActorRightVector();
    const float Speed=V.Size2D(),Length=FMath::Clamp(Speed*.16f,40.f,180.f);
    const FVector Center=FMath::Lerp(H->GetMesh()->GetSocketLocation(TEXT("palm")),H->GetMesh()->GetSocketLocation(TEXT("middle_01")),.6f);
    for(int32 N=0;N<2;++N)
    {
     const int32 J=I*AirPerSlot+N;const FVector At=Center-F*Length*.5f+Side*(N?32.f:-32.f);
     const FQuat Q=FRotationMatrix::MakeFromXZ(F,Eye-At).ToQuat();
     Transforms[1][J]=FTransform(Q,At,FVector(Length*.01f,.32f,1));
     Renderers[1]->SetCustomDataValue(J,0,FMath::Clamp(Speed/1100.f,0.f,1.f)*.28f,false);
     Renderers[1]->SetCustomDataValue(J,1,H->StateSeconds,false);Renderers[1]->SetCustomDataValue(J,2,0,false);
    }
    S.TrailClock+=Delta;if(S.TrailClock>=.12f&&Speed>100){S.TrailClock=0;Dust(I,Ground(H),-F,1,.55f);}
   }
  }
  for(int32 N=0;N<DustPerSlot;++N)
  {
   auto& P=S.Dust[N];const int32 J=I*DustPerSlot+N;
   if(P.Life<=0){Hide(0,J);continue;}P.Age+=Delta;
   if(P.Age>=P.Life){P.Life=0;Hide(0,J);continue;}
   P.Position+=P.Velocity*Delta;P.Position.Z=FMath::Max(P.FloorZ,P.Position.Z);P.Velocity*=FMath::Exp(-2.f*Delta);
   const float T=P.Age/P.Life,Size=P.Size*(.65f+T*.85f);
   const FQuat Q=FRotationMatrix::MakeFromZ(Eye-P.Position).ToQuat()*FQuat(FVector::UpVector,P.Seed*2*PI);
   Transforms[0][J]=FTransform(Q,P.Position,FVector(Size*.01f));
   Renderers[0]->SetCustomDataValue(J,0,FMath::Min(1.f,T*12)*(1-T)*.48f,false);
   Renderers[0]->SetCustomDataValue(J,1,P.Seed,false);Renderers[0]->SetCustomDataValue(J,2,T,false);
  }
  const int32 A=I*AirPerSlot+2;S.ArcAge+=Delta;
  if(S.ArcLife>0&&S.ArcAge<S.ArcLife)
  {
   const float T=S.ArcAge/S.ArcLife;const float Size=S.ArcSize*(.45f+.55f*T);
   Transforms[1][A]=FTransform(FRotationMatrix::MakeFromZ(S.ArcNormal).ToQuat(),S.ArcPosition,FVector(Size*.01f));
   Renderers[1]->SetCustomDataValue(A,0,(1-T)*.55f,false);Renderers[1]->SetCustomDataValue(A,1,T,false);Renderers[1]->SetCustomDataValue(A,2,1,false);
  }else Hide(1,A);
  for(int32 N=0;N<ChipsPerSlot;++N)
  {
   auto& P=S.Chips[N];const int32 J=I*ChipsPerSlot+N;P.Age+=Delta;
   if(P.Life<=0||P.Age>=P.Life||P.Position.Z<P.FloorZ){P.Life=0;Hide(2,J);continue;}
   P.Position+=P.Velocity*Delta;P.Velocity.Z-=600*Delta;
   Transforms[2][J]=FTransform(FRotator(P.Age*370,P.Seed*360,P.Age*240),P.Position,FVector(P.Size*.01f*(1-P.Age/P.Life)));
  }
  if(S.Released){S.ReleaseAge+=Delta;if(S.ReleaseAge>.8f){S.Used=false;S.Hand.Reset();--ActiveSlots;}}
 }
 for(int32 G=0;G<3;++G)Renderers[G]->BatchUpdateInstancesTransforms(0,Transforms[G],true,true,true);
}
void UFleshHandChargeFX::Deinitialize()
{
 for(int32 I=0;I<SlotCount;++I)if(Slots[I].Used&&!Slots[I].Released)Release(I);
 for(const auto& A:Audio)if(A)A->DestroyComponent();for(const auto& R:Renderers)if(R)R->DestroyComponent();
 Audio.Empty();Renderers.Empty();Skin.Empty();PreviousSkin.Empty();bReady=false;ActiveSlots=0;Super::Deinitialize();
}
