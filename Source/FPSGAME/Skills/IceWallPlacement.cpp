#include "IceWallPlacement.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/Pawn.h"
#include "NiagaraComponent.h"

namespace IceWallPlacement
{
namespace
{
constexpr float MinNormalZ=.5735764f; // 55 degrees, also checked against the sampled patch.
constexpr float Embed=14.f;
constexpr int32 MaxSections=31;
AActor* MonsterOwner(AActor* Actor)
{
    for(int32 I=0;Actor&&I<4;++I,Actor=Actor->GetOwner())
        if(Actor->FindComponentByClass<UMonsterCombatComponent>())return Actor;
    return nullptr;
}
bool Creature(AActor* Actor) { return Actor&&(Cast<APawn>(Actor)||MonsterOwner(Actor)); }
bool ClearColumn(UWorld* World,const FIceWallPlacement& P,const FIceWallCast& C,const FIceWallSection& S,FString& Reason)
{
    // The lower part is a foundation embedded in the sampled terrain. Only the
    // exposed air volume must be clear; never ignore a whole floor/building actor.
    const float Bottom=S.MaxGround+4,Top=S.Top-.5f;
    if(Top<=Bottom){Reason=TEXT("高度空间不足");return false;}
    const FVector Extent(C.Thickness*.5f-.5f,(S.MaxAlong-S.MinAlong)*.5f-.25f,(Top-Bottom)*.5f);
    const FVector Center=P.Location+P.Rotation.RotateVector(FVector(0,S.Center(),(Bottom+Top)*.5f));
    TArray<FOverlapResult> Hits;FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallColumn),false);
    World->OverlapMultiByChannel(Hits,Center,P.Rotation.Quaternion(),ECC_Pawn,FCollisionShape::MakeBox(Extent),Query);
    for(const auto& H:Hits)
    {
        auto* A=H.GetActor();auto* Primitive=H.GetComponent();
        if(!Primitive||Primitive->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)continue;
        if(MonsterOwner(A))continue; // Dead, friendly and hostile monsters never veto formation.
        Reason=Cast<APawn>(A)?TEXT("玩家占位"):TEXT("实体障碍");return false;
    }
    return true;
}
bool Sample(UWorld* World,const FIceWallPlacement& P,const FIceWallCast& C,
    float Along,float Span,float Reference,FIceWallSection& S,FString& Reason)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallSupport),false);
    FHitResult Center;
    const FVector At=P.Location+P.Rotation.RotateVector(FVector(0,Along,Reference));
    if(!TraceWithoutCreatures(World,At+FVector(0,0,60),At-FVector(0,0,100),Query,Center))
    {Reason=TEXT("地面断层");return false;}
    if(Center.ImpactNormal.Z<MinNormalZ||Center.bStartPenetrating
        ||(Center.GetActor()&&Center.GetActor()->ActorHasTag(TEXT("IceWall")))
        ||!Center.GetComponent()||Center.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)
    {Reason=TEXT("坡面过陡或障碍");return false;}
    S.MinAlong=Along-Span*.5f;S.MaxAlong=Along+Span*.5f;
    S.Ground=float(Center.ImpactPoint.Z-P.Location.Z);S.MinGround=S.MaxGround=S.Ground;
    const FVector Normal=P.Rotation.UnrotateVector(Center.ImpactNormal);
    S.SlopeAcross=float(-Normal.X/Normal.Z);S.SlopeAlong=float(-Normal.Y/Normal.Z);
    for(float X:{-C.Thickness*.5f+1,C.Thickness*.5f-1})
        for(float Y:{S.MinAlong+1,S.MaxAlong-1})
        {
            const float Predicted=S.Floor(X,Y);
            const FVector Point=P.Location+P.Rotation.RotateVector(FVector(X,Y,Predicted));FHitResult Floor;
            if(!TraceWithoutCreatures(World,Point+FVector(0,0,48),Point-FVector(0,0,96),Query,Floor)
                ||Floor.ImpactNormal.Z<MinNormalZ||Floor.bStartPenetrating
                ||FMath::Abs(float(Floor.ImpactPoint.Z-P.Location.Z)-Predicted)>35.f)
            {Reason=TEXT("地面断层或起伏过大");return false;}
            const float Z=float(Floor.ImpactPoint.Z-P.Location.Z);
            S.MinGround=FMath::Min(S.MinGround,Z);S.MaxGround=FMath::Max(S.MaxGround,Z);
        }
    S.Bottom=S.MinGround-Embed;
    S.Top=FMath::Max(S.Ground+C.Height(P.Shape),S.MaxGround+(P.Shape==EIceWallShape::Low?60.f:180.f));
    return ClearColumn(World,P,C,S,Reason);
}
struct FBody
{
    FVector Offset=FVector::ZeroVector;
    float Radius=35,HalfHeight=90;
};
FBody Body(const AActor* A)
{
    FBody B;
    if(const auto* Capsule=A->FindComponentByClass<UCapsuleComponent>())
    {B.Radius=Capsule->GetScaledCapsuleRadius();B.HalfHeight=Capsule->GetScaledCapsuleHalfHeight();B.Offset=Capsule->GetComponentLocation()-A->GetActorLocation();}
    else if(const auto* Root=Cast<UPrimitiveComponent>(A->GetRootComponent()))
    {B.Radius=float(FMath::Max(Root->Bounds.BoxExtent.X,Root->Bounds.BoxExtent.Y));B.HalfHeight=float(Root->Bounds.BoxExtent.Z);B.Offset=Root->Bounds.Origin-A->GetActorLocation();}
    B.Radius=FMath::Max(1.f,B.Radius);B.HalfHeight=FMath::Max(B.Radius,B.HalfHeight);return B;
}
}
bool TraceWithoutCreatures(UWorld* World,const FVector& Start,const FVector& End,const FCollisionQueryParams& Initial,FHitResult& Hit)
{
    FCollisionQueryParams Query=Initial;
    for(int32 I=0;I<32;++I)
    {
        if(!World->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query))return false;
        if(!Creature(Hit.GetActor()))return true;
        Query.AddIgnoredActor(Hit.GetActor());
        if(auto* Owner=MonsterOwner(Hit.GetActor()))Query.AddIgnoredActor(Owner);
    }
    return false;
}
bool Build(UWorld* World,FIceWallPlacement& P,const FIceWallCast& C,FString& Reason)
{
    P.Sections.Reset();P.bTrimmed=false;
    const int32 Count=FMath::Clamp(FMath::CeilToInt(C.Width()/72.f)|1,1,MaxSections);
    const float Span=C.Width()/Count;
    FIceWallSection Center;
    if(!Sample(World,P,C,0,Span,0,Center,Reason))return false;
    P.Sections.Add(Center);
    for(int32 Direction:{-1,1})
    {
        FIceWallSection Last=Center;
        for(int32 I=1;I<=Count/2;++I)
        {
            const float Along=Direction*I*Span;
            const float Reference=Last.Ground+Last.SlopeAlong*(Along-Last.Center());
            FIceWallSection Next;FString EndReason;
            if(!Sample(World,P,C,Along,Span,Reference,Next,EndReason)) { P.bTrimmed=true;break; }
            if(Direction<0)P.Sections.Insert(Next,0);else P.Sections.Add(Next);
            Last=Next;
        }
    }
    Reason.Reset();return true;
}
bool Validate(UWorld* World,const FIceWallPlacement& P,const FIceWallCast& C,FString& Reason)
{
    if(P.Sections.IsEmpty()){Reason=TEXT("无可用墙段");return false;}
    for(const auto& S:P.Sections)
    {
        FIceWallSection Current;
        if(!Sample(World,P,C,S.Center(),S.MaxAlong-S.MinAlong,S.Ground,Current,Reason))return false;
        if(FMath::Abs(Current.Ground-S.Ground)>12.f||Current.MinGround<S.Bottom+2.f||Current.MaxGround>S.Top-30.f)
        {Reason=TEXT("落点地形已改变");return false;}
    }
    Reason.Reset();return true;
}
float GroundAt(const FIceWallPlacement& P,float X,float Y)
{
    if(P.Sections.IsEmpty())return 0;
    for(const auto& S:P.Sections)if(Y<=S.MaxAlong)return S.Floor(X,Y);
    return P.Sections.Last().Floor(X,Y);
}
TSet<AActor*> Monsters(UWorld* World,const FIceWallPlacement& P,const FIceWallCast& C,float Margin)
{
    TSet<AActor*> Targets;FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallMonsters),false);
    for(const auto& S:P.Sections)
    {
        TArray<FOverlapResult> Hits;
        const FVector Center=P.Location+P.Rotation.RotateVector(FVector(0,S.Center(),(S.Bottom+S.Top)*.5f));
        const FVector Extent(C.Thickness*.5f+Margin,(S.MaxAlong-S.MinAlong)*.5f+Margin,(S.Top-S.Bottom)*.5f);
        World->OverlapMultiByObjectType(Hits,Center,P.Rotation.Quaternion(),FCollisionObjectQueryParams::AllDynamicObjects,FCollisionShape::MakeBox(Extent),Query);
        for(const auto& H:Hits)if(auto* A=MonsterOwner(H.GetActor()))Targets.Add(A);
    }
    return Targets;
}
bool Occupies(const AActor* A,const FIceWallPlacement& P,const FIceWallCast& C)
{
    const auto B=Body(A);const FVector At=P.Rotation.UnrotateVector(A->GetActorLocation()+B.Offset-P.Location);
    if(FMath::Abs(At.X)>C.Thickness*.5f+B.Radius+2)return false;
    for(const auto& S:P.Sections)
        if(At.Y+B.Radius>S.MinAlong&&At.Y-B.Radius<S.MaxAlong&&At.Z+B.HalfHeight>S.Bottom&&At.Z-B.HalfHeight<S.Top)return true;
    return false;
}
bool Displace(UWorld* World,AActor* Target,AActor* Wall,const FIceWallPlacement& P,const FIceWallCast& C,
    const TSet<AActor*>& Occupants,TArray<FVector4>& Reserved)
{
    const auto B=Body(Target);const FVector Start=Target->GetActorLocation()+B.Offset;
    if(!Occupies(Target,P,C)){Reserved.Add(FVector4(Start,B.Radius));return true;}
    const FVector Local=P.Rotation.UnrotateVector(Start-P.Location);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallExtrusion),false,Target);Query.AddIgnoredActor(Wall);
    for(auto* A:Occupants)Query.AddIgnoredActor(A);
    const float Preferred=Local.X>=0?1.f:-1.f;
    const float Face=C.Thickness*.5f+B.Radius+12;
    TArray<FVector> Candidates;
    for(float Side:{Preferred,-Preferred})
        for(float AlongOffset:{0.f,2*B.Radius+12,-2*B.Radius-12})
        {
            const float Clearance=FMath::Max(0.f,Face-Side*float(Local.X));
            const float End=FMath::Max(Face,Side*float(Local.X)+Clearance*FMath::Max(1.f,C.PushDistanceMultiplier)+C.Knockback);
            Candidates.Add(FVector(Side*End,Local.Y+AlongOffset,0));
            Candidates.Add(FVector(Side*Face,Local.Y+AlongOffset,0));
        }
    for(float End:{P.MinAlong()-B.Radius-12,P.MaxAlong()+B.Radius+12})
        Candidates.Add(FVector(Local.X,End,0));
    for(const auto& At:Candidates)
    {
        FVector Ground=P.Location+P.Rotation.RotateVector(FVector(At.X,At.Y,GroundAt(P,At.X,At.Y)));
        FHitResult Floor;
        if(!TraceWithoutCreatures(World,Ground+FVector(0,0,64),Ground-FVector(0,0,140),Query,Floor)
            ||Floor.bStartPenetrating||Floor.ImpactNormal.Z<MinNormalZ)continue;
        const FVector End=FVector(Ground.X,Ground.Y,Floor.ImpactPoint.Z+B.HalfHeight+B.Radius*(1.f/float(Floor.ImpactNormal.Z)-1.f)+3);
        bool Taken=false;
        for(const auto& Other:Reserved)if(FVector::DistSquared2D(FVector(Other.X,Other.Y,Other.Z),End)<FMath::Square(B.Radius+float(Other.W)+10)){Taken=true;break;}
        if(Taken)continue;
        const auto Shape=FCollisionShape::MakeCapsule(B.Radius,B.HalfHeight);
        if(World->OverlapBlockingTestByChannel(End,FQuat::Identity,ECC_Pawn,Shape,Query))continue;
        FHitResult Path;
        if(World->SweepSingleByChannel(Path,Start,End,FQuat::Identity,ECC_Pawn,Shape,Query))continue;
        // The entire route and endpoint are clear of geometry and players. Ignore
        // the simultaneously squeezed crowd, then reserve separated endpoints.
        const FVector Previous=Target->GetActorLocation();
        Target->SetActorLocation(End-B.Offset,false,nullptr,ETeleportType::TeleportPhysics);
        const FVector Pushed=Target->GetActorLocation()-Previous;
        if(auto* BodyPose=Target->FindComponentByClass<UFPSPlayerBodyComponent>())
            BodyPose->RecordKnockback(Pushed,Pushed.Size(),.08f);
        if(!Occupies(Target,P,C)){Reserved.Add(FVector4(End,B.Radius));return true;}
    }
    return false;
}
void SetEffectProfile(UNiagaraComponent* Effect,const FIceWallPlacement& P)
{
    if(P.Sections.IsEmpty())return;
    Effect->SetVariableFloat(TEXT("User.GroundCount"),P.Sections.Num());
    Effect->SetVariableFloat(TEXT("User.WallCenter"),P.CenterAlong());
    for(int32 I=0;I<32;++I)
    {
        const auto& S=P.Sections[FMath::Min(I,P.Sections.Num()-1)];
        Effect->SetVariableVec4(FName(*FString::Printf(TEXT("User.Ground%02d"),I)),FVector4(S.Center(),S.Ground,S.SlopeAcross,S.SlopeAlong));
    }
}
}
