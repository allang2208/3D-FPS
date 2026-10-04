#include "M09CeilingRoute.h"
#include "HangingBellM09.h"
#include "Components/SceneComponent.h"
#include "Components/PrimitiveComponent.h"
#include "GameFramework/Volume.h"
#include "Engine/World.h"
#include "EngineUtils.h"
AM09CeilingRoute::AM09CeilingRoute()
{
 PrimaryActorTick.bCanEverTick=false;
 SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("CeilingGraph")));
}
FVector AM09CeilingRoute::Point(int32 I) const{return GetActorTransform().TransformPosition(GripCenters[I]);}
namespace
{
constexpr float SurfaceSearchHeight=180.f;
bool TraceM09Ceiling(UWorld* World,FVector From,FVector To,const AActor* Ignore,FVector& Contact,FVector* Normal=nullptr,const float* PreferredHeight=nullptr)
{
 if(!World)return false;
 FCollisionQueryParams Query(SCENE_QUERY_STAT(M09CeilingSurface),true,Ignore);
 FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
 TArray<FHitResult> Hits;World->LineTraceMultiByObjectType(Hits,From,To,Objects,Query);
 // Collision-only volumes must neither stop travel nor masquerade as a roof.
 // Multi object traces can find a real underside behind such a volume.
 bool Found=false;float Best=FLT_MAX;
 for(const FHitResult& Hit:Hits)
 {
  const auto* Actor=Hit.GetActor();const auto* Component=Hit.GetComponent();
  if(Hit.bStartPenetrating||Hit.ImpactNormal.Z>-.45f||!Actor||!Component||Actor->IsA<APawn>()||Actor->IsA<AVolume>())continue;
  if(Component->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block)continue;
  const float Score=PreferredHeight?FMath::Abs(Hit.ImpactPoint.Z-*PreferredHeight):Hit.Distance;
  if(Score>=Best)continue;
  Best=Score;Contact=Hit.ImpactPoint;if(Normal)*Normal=Hit.ImpactNormal;Found=true;
 }
 return Found;
}
}
bool AM09CeilingRoute::FindSupport(UWorld* W,FVector Near,const AActor* Ignore,FVector& Contact,FVector* Normal)
{
 const float Height=Near.Z;
 return TraceM09Ceiling(W,Near-FVector(0,0,SurfaceSearchHeight),Near+FVector(0,0,SurfaceSearchHeight),Ignore,Contact,Normal,&Height);
}
bool AM09CeilingRoute::Supported(UWorld* W,FVector P,const AActor* Ignore)
{
 // A planted hand still needs actual contact; the wider travel projection is
 // not permission to keep supporting a hand after its roof has disappeared.
 FVector Contact;return TraceM09Ceiling(W,P-FVector(0,0,25),P+FVector(0,0,25),Ignore,Contact);
}
bool AM09CeilingRoute::ClearBody(UWorld* W,FVector P,const AActor* Ignore)
{
 FCollisionQueryParams Q(SCENE_QUERY_STAT(M09Clearance),false,Ignore);
 // Match the actual collision body without an additional exclusion margin.
 return Supported(W,P,Ignore)&&!W->OverlapBlockingTestByChannel(P-FVector(0,0,143),FQuat::Identity,ECC_Pawn,
  FCollisionShape::MakeCapsule(85,137),Q);
}
bool AM09CeilingRoute::ClearSegment(UWorld* W,FVector A,FVector B,const AActor* Ignore)
{
 // Hanging travel ignores the body's terrain volume. Only continuity of the
 // overhead surface constrains the route, including beams and roof steps.
 const int32 N=FMath::Clamp(FMath::CeilToInt(FVector::Distance(A,B)/35.f),1,16);
 FVector Contact;
 for(int32 I=0;I<=N;++I)if(!FindSupport(W,FMath::Lerp(A,B,float(I)/N),Ignore,Contact))return false;
 return true;
}
AM09CeilingRoute* AM09CeilingRoute::FindRoute(UWorld* W,FVector Ceiling)
{
 AM09CeilingRoute* BestRoute=nullptr;float Best=FMath::Square(350.f);
 for(TActorIterator<AM09CeilingRoute> It(W);It;++It)
  for(int32 I=0;I<FMath::Min(It->GripCenters.Num(),256);++I)
  {
   const FVector P=It->Point(I);const float D=FVector::DistSquared2D(P,Ceiling);
   if(D<Best&&FMath::Abs(P.Z-Ceiling.Z)<SurfaceSearchHeight){Best=D;BestRoute=*It;}
  }
 return BestRoute;
}
bool AM09CeilingRoute::FindPlacement(UWorld* W,FVector Near,const AActor* Ignore,FVector& Center,AM09CeilingRoute*& OptionalRoute)
{
 OptionalRoute=nullptr;
 // No authored tag, grip node, ground navigation or 3-7 m height band is required.
 // The trace reach is a search budget; real body clearance decides the minimum height.
 if(!TraceM09Ceiling(W,Near+FVector(0,0,2),Near+FVector(0,0,10000),Ignore,Center))return false;
 const AActor* ClearanceIgnore=Cast<AHangingBellM09>(Ignore)?Ignore:nullptr;
 if(!ClearBody(W,Center,ClearanceIgnore))return false;
 OptionalRoute=FindRoute(W,Center);return true;
}
bool AM09CeilingRoute::FindLocalPath(const AHangingBellM09* M,FVector Destination,TArray<FVector>& Out)
{
 Out.Reset();if(!M)return false;
 const FVector Start=M->CeilingCenter(),Delta=(Destination-Start)*FVector(1,1,0);
 if(Delta.SizeSquared()<FMath::Square(8.f))return false;
 const FVector Near=Start+Delta.GetClampedToMaxSize(150.f);FVector End;
 if(!FindSupport(M->GetWorld(),Near,M,End)||!ClearSegment(M->GetWorld(),Start,End,M))return false;
 Out.Add(End);return true;
}
bool AM09CeilingRoute::FindPath(const AHangingBellM09* M,FVector Destination,TArray<FVector>& Out) const
{
 Out.Reset();if(!M)return false;const int32 N=FMath::Min(GripCenters.Num(),256);if(!N)return false;
 const FVector Start=M->CeilingCenter();int32 First=INDEX_NONE;float Best=FLT_MAX;
 for(int32 I=0;I<N;++I)
 {
  const FVector P=Point(I);const float D=FVector::DistSquared(P,Start);
  if(D<Best&&FMath::Abs(P.Z-Start.Z)<SurfaceSearchHeight&&ClearSegment(GetWorld(),Start,P,M)){Best=D;First=I;}
 }
 if(First==INDEX_NONE)return false;
 TArray<int32> Parent,Queue;Parent.Init(INDEX_NONE,N);Parent[First]=First;Queue.Add(First);
 int32 Goal=First;Best=FVector::DistSquared2D(Point(First),Destination);
 for(int32 Head=0;Head<Queue.Num();++Head)
 {
  const int32 At=Queue[Head];const float D=FVector::DistSquared2D(Point(At),Destination);
  if(D<Best){Best=D;Goal=At;}
  for(const FIntPoint E:Links)
  {
   const int32 Next=E.X==At?E.Y:E.Y==At?E.X:INDEX_NONE;
   if(Next<0||Next>=N||Parent[Next]!=INDEX_NONE)continue;
   if(!ClearSegment(GetWorld(),Point(At),Point(Next),M))continue;
   Parent[Next]=At;Queue.Add(Next);
  }
 }
 for(int32 I=Goal;;I=Parent[I]){Out.Insert(Point(I),0);if(I==First)break;}
 while(!Out.IsEmpty()&&FVector::DistSquared(Out[0],Start)<FMath::Square(8.f))Out.RemoveAt(0);
 return !Out.IsEmpty();
}
