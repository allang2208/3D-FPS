#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"

bool UProductionToolComponent::HasReadyPresentation() const
{
    if(!bUsesArms)return ToolMesh && ToolMesh->GetStaticMesh();
    if(!Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return false;
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
        if(!Motions.FindRef(FName(Clip)))return false;
    return true;
}

void UProductionToolComponent::SampleMotion(FName Clip,float Seconds)
{
    UAnimSequence* Motion=Motions.FindRef(Clip);
    if(!Motion || !Viewmodel)return;
    if(CurrentMotion!=Motion)
    {
        CurrentMotion=Motion;
        Viewmodel->PlayAnimation(Motion,false);
        Viewmodel->SetPlayRate(0.f);
    }
    Viewmodel->SetPosition(FMath::Clamp(Seconds,0.f,Motion->GetPlayLength()),false);
    Viewmodel->TickAnimation(0.f,false);
    Viewmodel->RefreshBoneTransforms();
}

void UProductionToolComponent::UpdateHandPresentation(float Delta)
{
    VisualTime+=Delta;
    const float Speed=Character->GetVelocity().Size2D();
    const float SprintTarget=Elapsed<0 && Speed>650.f?1.f:0.f;
    // Exponential settling depends on elapsed time, including when frame rate changes.
    SprintBlend=FMath::Lerp(SprintBlend,SprintTarget,1.f-FMath::Exp(-14.f*Delta));
    Viewmodel->SetRelativeLocation(FVector(-3,0,-6)*SprintBlend);
    if(Elapsed>=0)
    {
        // Pose, whoosh and the one authoritative contact share the same clock.
        // Only a committed resource hit chooses the braced recovery; misses follow through.
        if(bHitConfirmed)
            SampleMotion(TEXT("HitRecover"),.44f*(Elapsed-ContactSeconds)/(SwingSeconds-ContactSeconds));
        else
            SampleMotion(TEXT("Swing"),Elapsed<ContactSeconds?
                .24f*Elapsed/ContactSeconds:.24f+.44f*(Elapsed-ContactSeconds)/(SwingSeconds-ContactSeconds));
    }
    else if(EquipElapsed>=0)
    {
        EquipElapsed+=Delta;
        SampleMotion(TEXT("Equip"),EquipElapsed);
        if(EquipElapsed>=Motions.FindRef(TEXT("Equip"))->GetPlayLength())EquipElapsed=-1.f;
    }
    else
    {
        const FName Clip=Speed>20.f?TEXT("Walk"):TEXT("Idle");
        const float Duration=Motions.FindRef(Clip)->GetPlayLength();
        SampleMotion(Clip,FMath::Fmod(VisualTime,Duration));
    }
}
