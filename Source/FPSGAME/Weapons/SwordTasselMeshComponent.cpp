#include "SwordTasselMeshComponent.h"
#include "RuneSwordComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"

USwordTasselMeshComponent::USwordTasselMeshComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetCanEverAffectNavigation(false);
    // The hanging bind-pose mesh can swing around its root in either direction.
    BoundsScale=3.f;
}

void USwordTasselMeshComponent::Configure(const TSharedPtr<FJsonObject>& Spec)
{
    bInitialized=false;Rest.Reset();Capsules.Reset();DynamicMaterials.Reset();
    const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
    if(!Spec||!Spec->TryGetArrayField(TEXT("guides_cm"),Points)||Points->Num()!=8)
    {SetComponentTickEnabled(false);return;}
    for(const auto& Value:*Points)
    {
        const auto& V=Value->AsArray();if(V.Num()!=3){SetComponentTickEnabled(false);return;}
        Rest.Add(FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber()));
    }
    Lengths.Reset();for(int32 I=0;I<7;++I)Lengths.Add(FVector::Dist(Rest[I],Rest[I+1]));
    InverseMass={0.,1.,.30,.30,.65,1.,1.,1.};
    const TArray<TSharedPtr<FJsonValue>>* Shapes=nullptr;
    if(Spec->TryGetArrayField(TEXT("collision_capsules_cm"),Shapes))
        for(const auto& Value:*Shapes)
        {
            const auto& V=Value->AsArray();if(V.Num()!=7)continue;
            Capsules.Add({FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber()),
                FVector(V[3]->AsNumber(),V[4]->AsNumber(),V[5]->AsNumber()),V[6]->AsNumber()});
        }
    for(int32 I=0;I<GetNumMaterials();++I)
        if(auto* MID=CreateDynamicMaterialInstance(I))DynamicMaterials.Add(MID);
    const auto* World=GetWorld();
    const bool Game=World&&(World->WorldType==EWorldType::Game||World->WorldType==EWorldType::PIE)&&World->GetNetMode()!=NM_DedicatedServer;
    for(const auto& M:DynamicMaterials)M->SetScalarParameterValue(TEXT("TasselActive"),Game?1.f:0.f);
    if(auto* Owner=GetOwner())
    {
        AddTickPrerequisiteActor(Owner);
        if(auto* Sword=Owner->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    }
    SetComponentTickEnabled(Game);
}

void USwordTasselMeshComponent::Publish()
{
    const FTransform Frame=GetComponentTransform();
    static const FName PNames[]={TEXT("TasselP0"),TEXT("TasselP1"),TEXT("TasselP2"),TEXT("TasselP3"),TEXT("TasselP4"),TEXT("TasselP5"),TEXT("TasselP6")};
    static const FName QNames[]={TEXT("TasselQ0"),TEXT("TasselQ1"),TEXT("TasselQ2"),TEXT("TasselQ3"),TEXT("TasselQ4"),TEXT("TasselQ5"),TEXT("TasselQ6")};
    for(int32 I=0;I<7;++I)
    {
        const FVector P=Frame.InverseTransformPosition(Position[I]);
        const FVector Direction=Frame.InverseTransformVectorNoScale(Position[I+1]-Position[I]).GetSafeNormal();
        const FQuat Q=FQuat::FindBetweenNormals((Rest[I+1]-Rest[I]).GetSafeNormal(),Direction);
        // Whirlwind swaps in responsive MIDs and later restores the originals.
        // Publish into whichever material is actually displayed this frame.
        for(int32 Slot=0;Slot<GetNumMaterials();++Slot)
            if(auto* M=Cast<UMaterialInstanceDynamic>(GetMaterial(Slot)))
        {
            M->SetScalarParameterValue(TEXT("TasselActive"),1.f);
            M->SetVectorParameterValue(PNames[I],FLinearColor(P.X,P.Y,P.Z,0));
            M->SetVectorParameterValue(QNames[I],FLinearColor(Q.X,Q.Y,Q.Z,Q.W));
        }
    }
}

void USwordTasselMeshComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(Rest.Num()!=8||!IsVisible()||bHiddenInGame||(GetOwner()&&GetOwner()->IsHidden())){bInitialized=false;return;}
    const FTransform Frame=GetComponentTransform();
    if(!bInitialized||Delta>.12f||FVector::DistSquared(Frame.GetLocation(),PreviousFrame.GetLocation())>6400.)
    {
        Position.Reset();for(const FVector& P:Rest)Position.Add(Frame.TransformPosition(P));
        Velocity.Init(FVector::ZeroVector,8);PreviousFrame=Frame;bInitialized=true;Publish();return;
    }
    if(Delta<=UE_SMALL_NUMBER)return;
    // Same fixed-substep / length-constraint principle as PKMSoftBeltDynamics.
    // Only the suspension knot is pinned; jade is a heavier rigid segment.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta*240.f),1,24);
    const double Dt=Delta/Steps;
    const FVector Gravity(0,0,GetWorld()->GetGravityZ());
    const double Scale=Frame.GetScale3D().GetAbsMax();
    for(int32 Step=0;Step<Steps;++Step)
    {
        FTransform Current;Current.Blend(PreviousFrame,Frame,double(Step+1)/Steps);
        const FVector Pin=Current.TransformPosition(Rest[0]);
        FVector Before[8];for(int32 I=0;I<8;++I)Before[I]=Position[I];
        for(int32 I=1;I<8;++I)
        {
            Velocity[I]*=FMath::Exp(-(I==2||I==3?3.8:3.0)*Dt);
            Velocity[I]+=Gravity*Dt;Position[I]+=Velocity[I]*Dt;
        }
        const auto PushOutside=[&](const FVector& P)
        {
            FVector Out=P;
            for(const FCapsule& C:Capsules)
            {
                const FVector A=Current.TransformPosition(C.A),B=Current.TransformPosition(C.B);
                const FVector Nearest=FMath::ClosestPointOnSegment(Out,A,B);
                const FVector D=Out-Nearest;const double R=(C.Radius+.18)*Scale;
                if(D.SizeSquared()<R*R)Out=Nearest+D.GetSafeNormal(UE_SMALL_NUMBER,Current.GetUnitAxis(EAxis::Y))*R;
            }
            return Out;
        };
        for(int32 Iter=0;Iter<20;++Iter)
        {
            Position[0]=Pin;
            for(int32 I=1;I<8;++I)Position[I]=PushOutside(Position[I]);
            for(int32 J=0;J<7;++J)
            {
                const int32 I=Iter%2?6-J:J;const double A=InverseMass[I],B=InverseMass[I+1];
                const FVector D=Position[I+1]-Position[I];const double L=D.Size();
                if(L<=UE_SMALL_NUMBER)continue;
                const FVector Fix=D*((L-Lengths[I]*Scale)/(L*(A+B)));
                Position[I]+=Fix*A;Position[I+1]-=Fix*B;
                // Midpoint exclusion protects links as well as their endpoints.
                const FVector Mid=(Position[I]+Position[I+1])*.5;
                const FVector Offset=PushOutside(Mid)-Mid;
                Position[I]+=Offset*(2*A/(A+B));Position[I+1]+=Offset*(2*B/(A+B));
            }
        }
        Position[0]=Pin;
        for(int32 I=0;I<8;++I)Velocity[I]=((Position[I]-Before[I])/Dt).GetClampedToMaxSize(2200.);
    }
    PreviousFrame=Frame;Publish();
}
