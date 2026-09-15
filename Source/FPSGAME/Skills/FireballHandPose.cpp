#include "FireballHandPose.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void FFireballHandPose::Load()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/Skills/fireball_hand_pose.json"))) ||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return;
    const auto Read=[](const TSharedPtr<FJsonObject>& Object,const TCHAR* Key,FVector& Value)
    {
        const TArray<TSharedPtr<FJsonValue>>* Array=nullptr;
        if(Object->TryGetArrayField(Key,Array) && Array->Num()==3)
            Value=FVector((*Array)[0]->AsNumber(),(*Array)[1]->AsNumber(),(*Array)[2]->AsNumber());
    };
    Read(Root,TEXT("shoulder"),Shoulder);Read(Root,TEXT("elbow_pole"),ElbowPole);
    Read(Root,TEXT("gather_wrist"),GatherWrist);Read(Root,TEXT("release_wrist"),ReleaseWrist);Read(Root,TEXT("withdraw_wrist"),WithdrawWrist);
    Read(Root,TEXT("windup_wrist"),WindupWrist);Read(Root,TEXT("release_shoulder"),ReleaseShoulder);Read(Root,TEXT("release_elbow_pole"),ReleaseElbowPole);
    Read(Root,TEXT("gather_depart"),GatherDepart);Read(Root,TEXT("gather_approach"),GatherApproach);
    Read(Root,TEXT("windup_depart"),WindupDepart);Read(Root,TEXT("windup_approach"),WindupApproach);Read(Root,TEXT("recovery_depart"),RecoveryDepart);
    Read(Root,TEXT("gather_forward"),GatherForward);Read(Root,TEXT("gather_normal"),GatherNormal);
    Read(Root,TEXT("release_forward"),ReleaseForward);Read(Root,TEXT("release_normal"),ReleaseNormal);Read(Root,TEXT("release_mid_normal"),ReleaseMidNormal);
    Read(Root,TEXT("orb_offset"),OrbOffset);
    const TSharedPtr<FJsonObject>* Fingers=nullptr;
    if(Root->TryGetObjectField(TEXT("digits"),Fingers))for(const auto& Entry:(*Fingers)->Values)
    {
        FFireballDigitPose Digit;const auto Object=Entry.Value->AsObject();
        Read(Object,TEXT("spread"),Digit.Spread);Read(Object,TEXT("gather_flex"),Digit.GatherFlex);Read(Object,TEXT("release_flex"),Digit.ReleaseFlex);
        Digits.Add(FName(*Entry.Key),Digit);
    }
}
FQuat FFireballHandPose::PalmFrame(float ReleaseAlpha) const
{
    const FQuat Hold=FRotationMatrix::MakeFromXZ(GatherForward,GatherNormal).ToQuat();
    const FQuat Middle=FRotationMatrix::MakeFromXZ(FMath::Lerp(GatherForward,ReleaseForward,.5f),ReleaseMidNormal).ToQuat();
    const FQuat End=FRotationMatrix::MakeFromXZ(ReleaseForward,ReleaseNormal).ToQuat();
    // Continuous angular direction through the sideways palm, without a kink.
    const float T=FMath::Clamp(ReleaseAlpha,0.f,1.f);
    return FQuat::Slerp(FQuat::Slerp(Hold,Middle,T),FQuat::Slerp(Middle,End,T),T).GetNormalized();
}
