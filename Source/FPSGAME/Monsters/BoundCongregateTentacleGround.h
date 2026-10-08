#pragma once
#include "BoundCongregate.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

/** Game-thread terrain samples, consumed by both passive and attacking poses. */
struct FCongregateTentacleGround
{
    struct FContact { FVector Position,Normal; bool Valid=false; };
    static constexpr int32 Count=57,SampleCount=15;
    FContact Contacts[SampleCount];
    FTransform Frame;
    float Age=1.f;
    bool Enabled=false;
    void Prepare(const ABoundCongregate* M,float Dt)
    {
        Frame=M->GetMesh()->GetComponentTransform();Enabled=!M->Dead();
        if(!Enabled)return;
        Age+=Dt;if(Age<(M->TentacleActive()?1.f/30.f:1.f/15.f))return;Age=0;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CongregateTentacleGround),false,M);
        if(IsValid(M->NetState.CapturedTarget.Get()))Query.AddIgnoredActor(M->NetState.CapturedTarget.Get());
        FCollisionObjectQueryParams Objects;
        Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
        for(int32 S=0;S<SampleCount;++S)
        {
            const FVector P=S<13?M->GetMesh()->GetSocketLocation(FName(FString::Printf(TEXT("attack_tentacle_%02d"),8+S*4))):
                S==13?M->GetActorLocation():M->TentacleActive()?FVector(M->NetState.TentacleAim):M->GetActorLocation();
            FHitResult Hit;auto& C=Contacts[S];
            C.Valid=M->GetWorld()->LineTraceSingleByObjectType(Hit,FVector(P.X,P.Y,FMath::Max(P.Z+40.,Frame.GetLocation().Z+100.)),
                FVector(P.X,P.Y,Frame.GetLocation().Z-240.),Objects,Query)&&Hit.ImpactNormal.Z>=M->GetCharacterMovement()->GetWalkableFloorZ()&&
                Hit.GetComponent()&&Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
            if(C.Valid){C.Position=Hit.ImpactPoint;C.Normal=Hit.ImpactNormal;}
        }
    }
    const FContact* Nearest(const FVector& P) const
    {
        const FContact* Best=nullptr;double Distance=FMath::Square(120.);
        for(const auto& C:Contacts)if(C.Valid)
        {const double D=FVector::DistSquared2D(P,C.Position);if(D<Distance){Distance=D;Best=&C;}}
        return Best;
    }
    static float Radius(int32 I)
    {
        // Conservative envelope of the authored flesh, in centimetres.
        if(I<14)return FMath::Lerp(29.f,9.f,float(I)/14.f);
        if(I<40)return 6.5f;
        return FMath::Lerp(6.5f,3.5f,float(I-40)/16.f);
    }
    void Constrain(FTransform (&Pose)[Count],int32 Anchor) const
    {
        if(!Enabled)return;
        FVector Original[Count],P[Count];float Lift[Count]={},Length[Count]={};
        for(int32 I=0;I<Count;++I)
        {
            Original[I]=P[I]=Frame.TransformPosition(Pose[I].GetLocation());
            if(I)Length[I]=FVector::Distance(P[I],P[I-1]);
            if(I>Anchor)if(const auto* C=Nearest(P[I]))
                Lift[I]=FMath::Max(0.f,(Radius(I)+2.5f-float(FVector::DotProduct(P[I]-C->Position,C->Normal)))/float(C->Normal.Z));
        }
        // Share contact lift along the flesh before projecting segment lengths:
        // a tip touching the floor forms a broad bend instead of a sharp hinge.
        for(int32 I=Anchor+1;I<Count;++I)
        {
            float L=0;
            for(int32 J=FMath::Max(Anchor+1,I-8);J<FMath::Min(Count,I+9);++J)
                L=FMath::Max(L,Lift[J]*FMath::Exp(-FMath::Square(float(I-J))/24.f));
            P[I].Z+=L*FMath::SmoothStep(0.f,5.f,float(I-Anchor));
        }
        for(int32 I=Anchor+1;I<Count;++I)
        {
            FVector Direction=(P[I]-P[I-1]).GetSafeNormal();
            P[I]=P[I-1]+Direction*Length[I];
            if(const auto* C=Nearest(P[I]))
            {
                const float Required=FMath::Clamp((Radius(I)+2.5f-float(FVector::DotProduct(P[I-1]-C->Position,C->Normal)))/FMath::Max(.001f,Length[I]),-1.f,1.f);
                if(FVector::DotProduct(Direction,C->Normal)<Required)
                {
                    FVector Tangent=FVector::VectorPlaneProject(Direction,C->Normal).GetSafeNormal();
                    if(Tangent.IsNearlyZero())Tangent=FVector::VectorPlaneProject(Frame.GetUnitAxis(EAxis::X),C->Normal).GetSafeNormal();
                    Direction=Tangent*FMath::Sqrt(FMath::Max(0.f,1.f-Required*Required))+C->Normal*Required;
                    P[I]=P[I-1]+Direction*Length[I];
                }
            }
        }
        FQuat Transport=FQuat::Identity;
        for(int32 I=Anchor;I<Count;++I)
        {
            const int32 A=I==Count-1?I-1:I,B=A+1;
            const FVector Before=Frame.InverseTransformVectorNoScale(Original[B]-Original[A]).GetSafeNormal();
            const FVector After=Frame.InverseTransformVectorNoScale(P[B]-P[A]).GetSafeNormal();
            Transport=(FQuat::FindBetweenNormals(Transport.RotateVector(Before),After)*Transport).GetNormalized();
            Pose[I].SetLocation(Frame.InverseTransformPosition(P[I]));
            Pose[I].SetRotation((Transport*Pose[I].GetRotation()).GetNormalized());
        }
    }
};
