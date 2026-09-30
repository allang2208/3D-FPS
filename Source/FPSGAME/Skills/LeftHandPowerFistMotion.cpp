#include "LeftHandPowerFistMotion.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

FLeftHandPowerFistMotion::FLeftHandPowerFistMotion()
    : Duration(1.f),LiftStart(.035f),ClenchStart(.17f),ClenchEnd(.26f),SettleEnd(.33f),RecoverStart(.52f),
      Wrist(34,-24,-21),Shoulder(-2,-20.5,-20),ElbowPole(9,-36,-37),
      Anticipation(-.3,-.3,-.35),LiftDepart(-1,-4,1.5),LiftApproach(.7,0,6),
      RecoveryDepart(-3,-2,-3),RecoveryApproach(-3,-5,-3),
      PalmForward(.5853,.22,.7804),PalmNormal(-.8,0,.6),BrakeOffset(-.15,-.05,.3)
{
    Digits.Add(TEXT("index"),{{65.75,158.75,216.75},{-.75,-3.75,-6.75},.003f});
    Digits.Add(TEXT("middle"),{{65.75,163.75,227.75},{-2.25,6,9.75},0.f});
    Digits.Add(TEXT("ring"),{{70.75,166.75,229.75},{-2.75,.25,3.25},-.004f});
    Digits.Add(TEXT("pinky"),{{70,168.75,230.75},{-2,1,-.5},-.008f});
    Digits.Add(TEXT("thumb"),{{48,25.75,13},{-11,60,87},.008f});
}

void FLeftHandPowerFistMotion::Load()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/Skills/left_hand_power_fist.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root) || !Root.IsValid())return;
    const auto ReadVector=[](const TSharedPtr<FJsonObject>& Object,const TCHAR* Key,FVector& Value)
    {
        const TArray<TSharedPtr<FJsonValue>>* Array=nullptr;
        if(Object->TryGetArrayField(Key,Array)&&Array->Num()==3)
            Value=FVector((*Array)[0]->AsNumber(),(*Array)[1]->AsNumber(),(*Array)[2]->AsNumber());
    };
    const auto ReadFloat=[&](const TCHAR* Key,float& Value)
    {double Number;if(Root->TryGetNumberField(Key,Number))Value=Number;};
    ReadFloat(TEXT("duration"),Duration);ReadFloat(TEXT("lift_start"),LiftStart);
    ReadFloat(TEXT("clench_start"),ClenchStart);ReadFloat(TEXT("clench_end"),ClenchEnd);
    ReadFloat(TEXT("settle_end"),SettleEnd);ReadFloat(TEXT("recover_start"),RecoverStart);
    ReadVector(Root,TEXT("wrist"),Wrist);ReadVector(Root,TEXT("shoulder"),Shoulder);
    ReadVector(Root,TEXT("elbow_pole"),ElbowPole);ReadVector(Root,TEXT("anticipation_offset"),Anticipation);
    ReadVector(Root,TEXT("lift_depart"),LiftDepart);ReadVector(Root,TEXT("lift_approach"),LiftApproach);
    ReadVector(Root,TEXT("recovery_depart"),RecoveryDepart);ReadVector(Root,TEXT("recovery_approach"),RecoveryApproach);
    ReadVector(Root,TEXT("palm_forward"),PalmForward);ReadVector(Root,TEXT("palm_normal"),PalmNormal);
    ReadVector(Root,TEXT("brake_offset"),BrakeOffset);
    const TSharedPtr<FJsonObject>* Fingers=nullptr;
    if(Root->TryGetObjectField(TEXT("fist"),Fingers))for(auto& Digit:Digits)
    {
        const TSharedPtr<FJsonObject>* Object=nullptr;
        if(!(*Fingers)->TryGetObjectField(Digit.Key.ToString(),Object))continue;
        ReadVector(*Object,TEXT("flex"),Digit.Value.Flex);
        double Spread;
        if((*Object)->TryGetNumberField(TEXT("spread"),Spread))Digit.Value.Spread=FVector(Spread);
        else ReadVector(*Object,TEXT("spread"),Digit.Value.Spread);
    }
    const TSharedPtr<FJsonObject>* Delays=nullptr;
    if(Root->TryGetObjectField(TEXT("finger_close_delay"),Delays))for(auto& Digit:Digits)
    {double Delay;if((*Delays)->TryGetNumberField(Digit.Key.ToString(),Delay))Digit.Value.CloseDelay=Delay;}
}

FFireballArmMotion FLeftHandPowerFistMotion::Sample(const FFireballArmMotion& Entry,const FQuat& Correction,float Age) const
{
    using namespace FireballCastMotion;
    FFireballArmMotion R=Entry;
    if(Age<LiftStart)
    {R.Wrist+=Anticipation*Ease(Age/FMath::Max(.001f,LiftStart));R.Layer=Ease(Age/.025f);return R;}
    const FQuat EndRotation=FRotationMatrix::MakeFromXZ(PalmForward,PalmNormal).ToQuat()*Correction;
    // LiftApproach is the raised waypoint relative to the final wrist in V2.
    const FVector PeakWrist=Wrist+LiftApproach;
    const FVector PeakShoulder=Shoulder+LiftApproach*.25f,PeakPole=ElbowPole+LiftApproach*.60f;
    if(Age<ClenchStart)
    {
        const float U=Ease((Age-LiftStart)/FMath::Max(.001f,ClenchStart-LiftStart));
        const FVector Begin=Entry.Wrist+Anticipation;
        R.Wrist=Arc(Begin,Begin+LiftDepart,PeakWrist+LiftDepart*.2f,PeakWrist,U);
        R.Shoulder=FMath::Lerp(Entry.Shoulder,PeakShoulder,U);R.Pole=FMath::Lerp(Entry.Pole,PeakPole,U);
        R.Rotation=FQuat::Slerp(Entry.Rotation,EndRotation,U).GetNormalized();
        return R;
    }
    if(Age<ClenchEnd)
    {
        const float U=Ease((Age-ClenchStart)/FMath::Max(.001f,ClenchEnd-ClenchStart));
        R.Wrist=FMath::Lerp(PeakWrist,Wrist,U);R.Shoulder=FMath::Lerp(PeakShoulder,Shoulder,U);
        R.Pole=FMath::Lerp(PeakPole,ElbowPole,U);R.Rotation=EndRotation;
        return R;
    }
    R.Wrist=Wrist;R.Shoulder=Shoulder;R.Pole=ElbowPole;R.Rotation=EndRotation;
    const float U=(Age-ClenchEnd)/FMath::Max(.001f,SettleEnd-ClenchEnd);
    if(U>0.f&&U<1.f)
    {const FVector Offset=BrakeOffset*FMath::Square(FMath::Sin(PI*U));R.Wrist+=Offset;R.Shoulder+=Offset;R.Pole+=Offset;}
    return R;
}

FFireballArmMotion FLeftHandPowerFistMotion::Recover(const FFireballArmMotion& From,const FFireballArmMotion& Current,float Fraction) const
{
    using namespace FireballCastMotion;
    FFireballArmMotion R=From;const float U=Ease(Fraction);
    R.Wrist=Arc(From.Wrist,From.Wrist+RecoveryDepart,Current.Wrist+RecoveryApproach,Current.Wrist,U);
    R.Shoulder=FMath::Lerp(From.Shoulder,Current.Shoulder,U);R.Pole=FMath::Lerp(From.Pole,Current.Pole,U);
    R.Rotation=FQuat::Slerp(From.Rotation,Current.Rotation,Ease(Fraction/.88f)).GetNormalized();
    R.Layer=From.Layer*(1.f-Ease((Fraction-.6f)/.4f));return R;
}

FVector2D FLeftHandPowerFistMotion::FingerWeights(FName Digit,float Age,float RecoveryFraction) const
{
    using namespace FireballCastMotion;
    const auto* Profile=Digits.Find(Digit);const float Delay=Profile?Profile->CloseDelay:0.f;
    const float Close=Ease((Age-ClenchStart-Delay)/FMath::Max(.001f,ClenchEnd-ClenchStart-Delay));
    const float ReleaseDelay=Digit==TEXT("thumb")?.02f:.13f;
    return FVector2D(Ease(Age/.105f)*(1.f-Ease(RecoveryFraction/.5f)),
        Close*(1.f-Ease((RecoveryFraction-ReleaseDelay)/.65f)));
}

float FLeftHandPowerFistMotion::ArmSupportWeight(float Age,float RecoveryFraction) const
{
    return FireballCastMotion::Ease((Age-LiftStart)/FMath::Max(.001f,ClenchEnd-LiftStart))*(1.f-FireballCastMotion::Ease(RecoveryFraction));
}
