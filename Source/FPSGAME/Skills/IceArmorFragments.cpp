#include "FPSIceArmorComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "Materials/MaterialInterface.h"

void UFPSIceArmorComponent::EmitChips(const FVector& Direction,int32 Count)
{
    if(GetNetMode()==NM_DedicatedServer||!ChipMesh||!ChipMaterial||VisualDetail<=0)return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());if(!P)return;
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();const bool First=P->IsLocallyControlled()&&(!Body||!Body->IsThirdPersonViewEnabled());
    if(!Chips)
    {
        Chips=NewObject<UInstancedStaticMeshComponent>(P,NAME_None,RF_Transient);P->AddInstanceComponent(Chips);Chips->SetupAttachment(P->GetRootComponent());
        Chips->SetAbsolute(true,true,true);Chips->SetWorldTransform(FTransform::Identity);Chips->SetStaticMesh(ChipMesh);Chips->SetMaterial(0,ChipMaterial);
        Chips->NumCustomDataFloats=1;Chips->SetCollisionEnabled(ECollisionEnabled::NoCollision);Chips->SetGenerateOverlapEvents(false);
        Chips->SetCastShadow(false);Chips->SetVisibleInRayTracing(false);Chips->SetCanEverAffectNavigation(false);Chips->RegisterComponent();
        ChipParticles.SetNum(12);for(int32 I=0;I<12;++I)Chips->AddInstance(FTransform(FQuat::Identity,P->GetActorLocation(),FVector::ZeroVector));
    }
    bLastFirstPerson=First;Chips->SetOnlyOwnerSee(First);
    FVector Origin=(Body&&Body->GetBodyMesh()?Body->GetBodyMesh()->GetSocketLocation(TEXT("spine_05")):P->GetActorLocation()+FVector(0,0,35))+Direction*22;
    FVector Push=Direction;
    if(First&&P->FirstPersonCamera)
    {
        const auto* Camera=P->FirstPersonCamera.Get();const float Side=FVector::DotProduct(Direction,Camera->GetRightVector())>=0?1.f:-1.f;
        const float Width=42*FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5f);
        Origin=Camera->GetComponentLocation()+Camera->GetForwardVector()*42+Camera->GetRightVector()*Width*.91f*Side-Camera->GetUpVector()*8;
        Push=Camera->GetRightVector()*Side;
    }
    FRandomStream Random(Impact.Serial*733+uint32(VisualStartedAt*100));
    const int32 N=FMath::Clamp(FMath::CeilToInt(Count*VisualDetail),1,12);
    for(int32 I=0;I<N;++I)
    {
        auto& C=ChipParticles[ChipCursor++%12];C.At=Clock();C.Start=Origin+Random.VRand()*2;
        FVector FragmentPush=Push;
        if(Count>=12)
        {
            if(First&&P->FirstPersonCamera)
            {
                const auto* Camera=P->FirstPersonCamera.Get();const float Side=I%2?1.f:-1.f;
                const float Width=42*FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5f);
                C.Start=Camera->GetComponentLocation()+Camera->GetForwardVector()*42+Camera->GetRightVector()*Width*.91*Side+Camera->GetUpVector()*Random.FRandRange(-14,14);
                FragmentPush=Camera->GetRightVector()*Side;
            }
            else
            {
                const float A=Random.FRandRange(0,2*PI);FragmentPush=FVector(FMath::Cos(A),FMath::Sin(A),0);
                C.Start=P->GetActorLocation()+FragmentPush*23+FVector(0,0,Random.FRandRange(-45,38));
            }
        }
        C.Velocity=FragmentPush*Random.FRandRange(14,27)+Random.VRand()*8+FVector(0,0,12);
        C.Rotation=FRotator(Random.FRandRange(-180,180),Random.FRandRange(-180,180),Random.FRandRange(-180,180));
        C.Spin=FRotator(Random.FRandRange(-160,160),Random.FRandRange(-200,200),Random.FRandRange(-160,160));C.Size=Random.FRandRange(.4f,1.05f);
    }
}
void UFPSIceArmorComponent::UpdateChips()
{
    if(!Chips)return;
    const double Now=Clock();
    if(!ChipParticles.ContainsByPredicate([Now](const FChip& C){return Now-C.At<.55;}))
    {if(Chips->IsVisible())Chips->SetVisibility(false);return;}
    bool Any=false;
    for(int32 I=0;I<ChipParticles.Num();++I)
    {
        const auto& C=ChipParticles[I];const float Age=Now-C.At,Alpha=FMath::Clamp(1.f-Age/.55f,0.f,1.f);Any|=Alpha>0;
        const FVector Position=C.Start+C.Velocity*Age+FVector(0,0,-75*Age*Age);
        Chips->UpdateInstanceTransform(I,FTransform((C.Rotation+C.Spin*FMath::Max(0.f,Age)).Quaternion(),Alpha>0?Position:GetOwner()->GetActorLocation(),FVector(Alpha>0?C.Size:0)),false,false,true);
        Chips->SetCustomDataValue(I,0,Alpha*Alpha,false);
    }
    Chips->SetVisibility(Any);Chips->MarkRenderStateDirty();
}
