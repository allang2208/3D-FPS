#include "PotionUseMotion.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void FPotionUseMotion::Load(bool bMana,const TCHAR* Definition)
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/potion_use_motion.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return;
    const auto Vec=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Name,FVector& V)
    {
        const TArray<TSharedPtr<FJsonValue>>* A=nullptr;
        if(O->TryGetArrayField(Name,A)&&A->Num()==3)V=FVector((*A)[0]->AsNumber(),(*A)[1]->AsNumber(),(*A)[2]->AsNumber());
    };
    const auto Family=Root->GetObjectField(Definition?Definition:(bMana?TEXT("mp_potion"):TEXT("hp_potion")));
    const auto Times=Family->HasField(TEXT("times"))?Family->GetObjectField(TEXT("times")):Root->GetObjectField(TEXT("times"));
    Grab=Times->GetNumberField(TEXT("grab"));Uncap=Times->GetNumberField(TEXT("uncap"));
    DrinkStart=Times->GetNumberField(TEXT("drink_start"));DrinkEnd=Times->GetNumberField(TEXT("drink_end"));
    Contact=Times->GetNumberField(TEXT("contact"));Release=Times->GetNumberField(TEXT("release"));
    Recover=Times->GetNumberField(TEXT("recover"));Duration=Times->GetNumberField(TEXT("duration"));
    Vec(Root,TEXT("shoulder"),Shoulder);Vec(Root,TEXT("elbow_pole"),Pole);
    Vec(Family,TEXT("grip_in_palm"),GripInPalm);GripHeight=Family->GetNumberField(TEXT("grip_height"));
    bHasObjectGrip=Family->HasField(TEXT("grip_in_object"));
    ObjectGrip=FVector::ZeroVector;Vec(Family,TEXT("grip_in_object"),ObjectGrip);
    bTwoHanded=false;Family->TryGetBoolField(TEXT("two_handed"),bTwoHanded);
    Vec(Family,TEXT("right_grip_in_object"),RightObjectGrip);Vec(Family,TEXT("right_grip_in_palm"),RightGripInPalm);
    BiteInObject=FVector::ZeroVector;Vec(Family,TEXT("bite_in_object"),BiteInObject);
    FVector ObjectEuler=FVector::ZeroVector;Vec(Family,TEXT("object_rotation"),ObjectEuler);
    ObjectRotation=FRotator(ObjectEuler.X,ObjectEuler.Y,ObjectEuler.Z).Quaternion();
    FVector PalmEuler=FVector::ZeroVector,RightPalmEuler=FVector::ZeroVector;
    Vec(Family,TEXT("palm_rotation"),PalmEuler);Vec(Family,TEXT("right_palm_rotation"),RightPalmEuler);
    PalmRotation=FRotator(PalmEuler.X,PalmEuler.Y,PalmEuler.Z).Quaternion();
    RightPalmRotation=FRotator(RightPalmEuler.X,RightPalmEuler.Y,RightPalmEuler.Z).Quaternion();
    bOpensContainer=true;Family->TryGetBoolField(TEXT("opens_container"),bOpensContainer);
    const auto ReadLocalRotations=[](const TSharedPtr<FJsonObject>& O,FPotionDigitPose& D)
    {
        D.bHasLocalRotations=false;
        const TArray<TSharedPtr<FJsonValue>>* Rotations=nullptr;
        if(!O->TryGetArrayField(TEXT("local_rotations"),Rotations)||Rotations->Num()!=3)return;
        for(int32 I=0;I<3;++I)
        {
            const TArray<TSharedPtr<FJsonValue>>* Q=nullptr;
            if(!(*Rotations)[I]->TryGetArray(Q)||Q->Num()!=4)return;
            D.LocalRotations[I]=FQuat((*Q)[0]->AsNumber(),(*Q)[1]->AsNumber(),(*Q)[2]->AsNumber(),(*Q)[3]->AsNumber()).GetNormalized();
        }
        D.bHasLocalRotations=true;
    };
    Digits.Reset();
    for(const auto& Pair:Family->GetObjectField(TEXT("digits"))->Values)
    {
        FPotionDigitPose D;Vec(Pair.Value->AsObject(),TEXT("spread"),D.Spread);Vec(Pair.Value->AsObject(),TEXT("flex"),D.Flex);
        Pair.Value->AsObject()->TryGetBoolField(TEXT("preserve_native_roll"),D.bPreserveNativeRoll);
        ReadLocalRotations(Pair.Value->AsObject(),D);
        Digits.Add(FName(*Pair.Key),D);
    }
    RightDigits.Reset();
    const TSharedPtr<FJsonObject>* RightDigitData=nullptr;
    if(Family->TryGetObjectField(TEXT("right_digits"),RightDigitData))
        for(const auto& Pair:(*RightDigitData)->Values)
        {
            FPotionDigitPose D;Vec(Pair.Value->AsObject(),TEXT("spread"),D.Spread);Vec(Pair.Value->AsObject(),TEXT("flex"),D.Flex);
            Pair.Value->AsObject()->TryGetBoolField(TEXT("preserve_native_roll"),D.bPreserveNativeRoll);
            ReadLocalRotations(Pair.Value->AsObject(),D);
            RightDigits.Add(FName(*Pair.Key),D);
        }
    const TSharedPtr<FJsonObject>* RightThumbData=nullptr;
    bHasRightThumb=Family->TryGetObjectField(TEXT("right_thumb"),RightThumbData);
    if(bHasRightThumb)
    {
        RightThumb.bPreserveNativeRoll=false;
        (*RightThumbData)->TryGetBoolField(TEXT("preserve_native_roll"),RightThumb.bPreserveNativeRoll);
        Vec(*RightThumbData,TEXT("spread"),RightThumb.Spread);
        Vec(*RightThumbData,TEXT("flex"),RightThumb.Flex);
        ReadLocalRotations(*RightThumbData,RightThumb);
    }
    Keys.Reset();
    for(const auto& Value:(Family->HasField(TEXT("keys"))?Family->GetArrayField(TEXT("keys")):Root->GetArrayField(TEXT("keys"))))
    {
        const auto O=Value->AsObject();FPotionMotionKey K;FVector Euler;
        K.Time=O->GetNumberField(TEXT("time"));Vec(O,TEXT("grip"),K.Grip);Vec(O,TEXT("rotation"),Euler);
        K.Rotation=FRotator(Euler.X,Euler.Y,Euler.Z).Quaternion();Keys.Add(K);
    }
}

FTransform FPotionUseMotion::GripAt(float Age) const
{
    if(Keys.IsEmpty())return FTransform::Identity;
    for(int32 I=1;I<Keys.Num();++I)if(Age<=Keys[I].Time)
    {
        const auto& A=Keys[I-1];const auto& B=Keys[I];
        const float T=FMath::Clamp((Age-A.Time)/FMath::Max(.001f,B.Time-A.Time),0.f,1.f);
        // Hermite tangents carry the bottle through the lift and throw. The
        // drinking plateau has stationary keys, so the rim stays by the mouth.
        const auto Tangent=[&](int32 J)
        {
            if(J==0||J==Keys.Num()-1)return FVector::ZeroVector;
            if(Keys[J].Grip.Equals(Keys[J-1].Grip,.01)||Keys[J].Grip.Equals(Keys[J+1].Grip,.01))return FVector::ZeroVector;
            return (Keys[J+1].Grip-Keys[J-1].Grip)/(Keys[J+1].Time-Keys[J-1].Time);
        };
        const FVector P=FMath::CubicInterp(A.Grip,Tangent(I-1)*(B.Time-A.Time),B.Grip,Tangent(I)*(B.Time-A.Time),T);
        return FTransform(FQuat::Slerp(A.Rotation,B.Rotation,Ease(T)).GetNormalized(),P);
    }
    return FTransform(Keys.Last().Rotation,Keys.Last().Grip);
}
FTransform FPotionUseMotion::BottleAt(float Age) const
{
    const FTransform G=GripAt(Age);
    const FQuat Rotation=G.GetRotation()*ObjectRotation;
    return FTransform(Rotation,G.GetLocation()-Rotation.RotateVector(ObjectGripPoint()));
}
FQuat FPotionUseMotion::PalmBasis(bool bRight) const
{
    return FRotationMatrix::MakeFromXZ(FVector::ForwardVector,bRight?-FVector::RightVector:FVector::RightVector).ToQuat()*
        (bRight?RightPalmRotation:PalmRotation);
}
FTransform FPotionUseMotion::PalmAt(float Age) const
{
    const FTransform G=GripAt(Age);
    const FQuat Palm=G.GetRotation()*PalmBasis();
    return FTransform(Palm,G.GetLocation()-Palm.RotateVector(GripInPalm));
}
float FPotionUseMotion::Layer(float Age) const
{
    return Ease(Age/Grab)*(1.f-Ease((Age-Recover)/(Duration-Recover)));
}
float FPotionUseMotion::FingerClosure(float Age) const
{
    // A two-hand food stays grasped until its visibility window has ended.
    const float OpenAt=bTwoHanded?Release:Release-.025f;
    return Ease((Age-Grab*.42f)/(Grab*.58f))*(1.f-Ease((Age-OpenAt)/.08f));
}
