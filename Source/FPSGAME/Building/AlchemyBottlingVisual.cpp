#include "PotionWorkbenchVisualComponent.h"
#include "AlchemyBottlingMotion.h"
#include "AlchemyWorkbenchLayout.h"
#include "Components/StaticMeshComponent.h"

void UPotionWorkbenchVisualComponent::AnimateBottling(float T,float SurfaceZ,bool Active)
{
    using namespace AlchemyBottling;
    auto Blend=[](const FTransform& A,const FTransform& B,float Fraction,float Lift)
    {
        const float S=AlchemyInteraction::Smooth(Fraction);
        return FTransform(FQuat::Slerp(A.GetRotation(),B.GetRotation(),S),
            FMath::Lerp(A.GetLocation(),B.GetLocation(),S)+FVector(0,0,Lift*FMath::Sin(PI*S)));
    };
    const FTransform BottleRest(AlchemyLayout::DoseRest),BottleWork(BottlePosition);
    const FTransform LadleRest(AlchemyLayout::ToolRestRotation,AlchemyLayout::LadleRest);
    FTransform Bottle=BottleRest,Ladle=LadleRest;
    if(Active)
    {
        Bottle=T<ReturnAt?Blend(BottleRest,BottleWork,T/.9f,8):Blend(BottleWork,BottleRest,(T-ReturnAt)/(RestAt-ReturnAt),8);
        // Scoop while upright. The bowl is below the liquid; only after it has
        // cleared the rolled lip does the hand move over the waiting bottle.
        const FTransform Dip(FQuat::Identity,FVector(225,-106,SurfaceZ+19.3));
        const FTransform Hover(FQuat::Identity,PourPoint-Spout);
        if(T<DipAt)Ladle=Blend(LadleRest,Dip,T/DipAt,20);
        else if(T<LiftAt)Ladle=Dip;
        else if(T<AlignedAt)Ladle=Blend(Dip,Hover,(T-LiftAt)/(AlignedAt-LiftAt),10);
        else if(T<ReturnAt)
        {
            const FQuat Q=FRotator(65* Tilt(T),0,0).Quaternion();
            // Pivot around the actual lowest lip, so tipping never moves the
            // outlet off the bottle mouth.
            Ladle=FTransform(Q,PourPoint-Q.RotateVector(Spout));
        }
        else Ladle=Blend(Hover,LadleRest,(T-ReturnAt)/(RestAt-ReturnAt),20);
        if(T>=FlowStart&&BottleSoundSerial!=State.ActionSerial)
        {
            BottleSoundSerial=State.ActionSerial;
            if(T<FlowStart+.3f)Sound(TEXT("Bottle"),BottlePosition+Mouth);
        }
    }
    Part(TEXT("Dose"))->SetRelativeTransform(Bottle);
    Part(TEXT("Ladle"))->SetRelativeTransform(Ladle);
}
