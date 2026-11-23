#pragma once
#include "CoreMinimal.h"
#include "ReferenceSkeleton.h"

namespace SpellbookHandMirror
{
    inline FQuat ReflectY(const FQuat& Q) {return FQuat(-Q.X,Q.Y,-Q.Z,Q.W);}
    inline FQuat ReflectX(const FQuat& Q) {return FQuat(Q.X,-Q.Y,-Q.Z,Q.W);}
    struct FBone
    {
        int32 Left,Right;
        FQuat BindCorrection;
    };
    inline TArray<FBone> Build(const FReferenceSkeleton& Ref,const TArray<FTransform>& Bind)
    {
        TArray<FBone> Pairs;
        const int32 Root=Ref.FindBoneIndex(TEXT("clavicle_r"));
        for(int32 R=0;R<Bind.Num();++R)
        {
            if(Root==INDEX_NONE||(R!=Root&&!Ref.BoneIsChildOf(R,Root)))continue;
            const FString Name=Ref.GetBoneName(R).ToString();
            if(!Name.EndsWith(TEXT("_r")))continue;
            const int32 L=Ref.FindBoneIndex(FName(*(Name.LeftChop(2)+TEXT("_l"))));
            if(L!=INDEX_NONE)Pairs.Add({L,R,ReflectX(Bind[L].GetRotation()).Inverse()*Bind[R].GetRotation()});
        }
        return Pairs;
    }

    // The native skeleton reflects across X, and the first-person camera reflects across Y.
    inline FTransform CameraBone(const FTransform& Left,const FBone& Pair)
    {
        const FVector P=Left.GetTranslation();
        return FTransform((ReflectY(Left.GetRotation())*FQuat(FVector::UpVector,PI)*Pair.BindCorrection).GetNormalized(),
            FVector(P.X,-P.Y,P.Z),Left.GetScale3D());
    }
    inline FTransform RightGrip(const FTransform& LeftGrip,const FBone& Wrist)
    {
        const FVector P=LeftGrip.GetTranslation();
        const FQuat Axes=FQuat(FVector::UpVector,PI)*Wrist.BindCorrection;
        return FTransform((Axes.Inverse()*ReflectY(LeftGrip.GetRotation())).GetNormalized(),
            Axes.UnrotateVector(FVector(P.X,-P.Y,P.Z)),LeftGrip.GetScale3D());
    }
}
