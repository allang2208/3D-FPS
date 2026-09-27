#include "PotionUseMotion.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void FPotionUseMotion::Load(bool bMana)
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/potion_use_motion.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return;
    const auto Vec=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Name,FVector& V)
    {
        const TArray<TSharedPtr<FJsonValue>>* A=nullptr;
        if(O->TryGetArrayField(Name,A)&&A->Num()==3)V=FVector((*A)[0]->AsNumber(),(*A)[1]->AsNumber(),(*A)[2]->AsNumber());
    };
    const auto Times=Root->GetObjectField(TEXT("times"));
    Grab=Times->GetNumberField(TEXT("grab"));Uncap=Times->GetNumberField(TEXT("uncap"));
    DrinkStart=Times->GetNumberField(TEXT("drink_start"));DrinkEnd=Times->GetNumberField(TEXT("drink_end"));
    Contact=Times->GetNumberField(TEXT("contact"));Release=Times->GetNumberField(TEXT("release"));
    Recover=Times->GetNumberField(TEXT("recover"));Duration=Times->GetNumberField(TEXT("duration"));
    Vec(Root,TEXT("shoulder"),Shoulder);Vec(Root,TEXT("elbow_pole"),Pole);
    const auto Family=Root->GetObjectField(bMana?TEXT("mp_potion"):TEXT("hp_potion"));
    Vec(Family,TEXT("grip_in_palm"),GripInPalm);GripHeight=Family->GetNumberField(TEXT("grip_height"));
    Digits.Reset();
    for(const auto& Pair:Family->GetObjectField(TEXT("digits"))->Values)
    {
        FPotionDigitPose D;Vec(Pair.Value->AsObject(),TEXT("spread"),D.Spread);Vec(Pair.Value->AsObject(),TEXT("flex"),D.Flex);
        Digits.Add(FName(*Pair.Key),D);
    }
    Keys.Reset();
    for(const auto& Value:Root->GetArrayField(TEXT("keys")))
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
    return FTransform(G.GetRotation(),G.TransformPosition(FVector(0,0,-GripHeight)));
}
FTransform FPotionUseMotion::PalmAt(float Age) const
{
    const FTransform G=GripAt(Age);
    const FQuat Palm=G.GetRotation()*FRotationMatrix::MakeFromXZ(FVector::ForwardVector,FVector::RightVector).ToQuat();
    return FTransform(Palm,G.GetLocation()-Palm.RotateVector(GripInPalm));
}
float FPotionUseMotion::Layer(float Age) const
{
    return Ease(Age/Grab)*(1.f-Ease((Age-Recover)/(Duration-Recover)));
}
float FPotionUseMotion::FingerClosure(float Age) const
{
    return Ease((Age-Grab*.42f)/(Grab*.58f))*(1.f-Ease((Age-(Release-.025f))/.08f));
}
