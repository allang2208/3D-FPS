#include "ProductionAxeImpactMotion.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<float> AxeImpactCameraScale(TEXT("fps.Tool.AxeCamera"),1.f,
    TEXT("Axe windup, impact, pry and extraction camera strength. 0 disables the layer."));

namespace ProductionAxeCamera
{
    FVector ReadVector(const TSharedPtr<FJsonObject>& Object,const TCHAR* Key)
    {
        const auto& Values=Object->GetArrayField(Key);
        return FVector(Values[0]->AsNumber(),Values[1]->AsNumber(),Values[2]->AsNumber());
    }

    FProductionAxeCameraKey Curve(const TArray<FProductionAxeCameraKey>& Keys,float Time)
    {
        if(Keys.IsEmpty())return {};
        if(Time<=Keys[0].Time)return Keys[0];
        for(int32 I=1;I<Keys.Num();++I)
            if(Time<=Keys[I].Time)
            {
                const float U=FMath::SmoothStep(Keys[I-1].Time,Keys[I].Time,Time);
                return {Time,FMath::Lerp(Keys[I-1].Angles,Keys[I].Angles,U),
                    FMath::Lerp(Keys[I-1].Position,Keys[I].Position,U)};
            }
        return Keys.Last();
    }

    float Pry(const TArray<FVector2D>& Keys,float Time)
    {
        if(Keys.IsEmpty()||Time<Keys[0].X||Time>Keys.Last().X)return 0.f;
        for(int32 I=1;I<Keys.Num();++I)
            if(Time<=Keys[I].X)
            {
                const float U=FMath::Clamp((Time-Keys[I-1].X)/(Keys[I].X-Keys[I-1].X),0.,1.);
                const float Ease=U*U*U*(10.f-15.f*U+6.f*U*U);
                return FMath::Lerp(Keys[I-1].Y,Keys[I].Y,Ease);
            }
        return 0.f;
    }
}

void FProductionAxeImpactMotion::Load()
{
    FString Text;
    TSharedPtr<FJsonObject> Root;
    const FString Path=FPaths::ProjectContentDir()/TEXT("ColdSteelData/axe_impact_motion.json");
    if(!FFileHelper::LoadFileToString(Text,*Path)||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))
    {
        UE_LOG(LogTemp,Warning,TEXT("[ProductionAxe] Cannot load motion/camera profile: %s"),*Path);
        return;
    }
    SwingSeconds=Root->GetNumberField(TEXT("swing_seconds"));
    ContactSeconds=Root->GetNumberField(TEXT("contact_seconds"));
    SwingSoundSeconds=Root->GetNumberField(TEXT("swing_sound_seconds"));
    HitRecoverSeconds=Root->GetNumberField(TEXT("hit_recover_seconds"));
    PryEndSeconds=Root->GetNumberField(TEXT("pry_end_seconds"));
    PryCameraPitch=Root->GetNumberField(TEXT("pry_camera_pitch_per_degree"));
    PryCameraUp=Root->GetNumberField(TEXT("pry_camera_up_cm_per_degree"));
    auto ReadKeys=[&](const TCHAR* Name,TArray<FProductionAxeCameraKey>& Keys)
    {
        Keys.Reset();
        for(const auto& Value:Root->GetArrayField(Name))
        {
            const auto Object=Value->AsObject();
            Keys.Add({float(Object->GetNumberField(TEXT("t"))),
                ProductionAxeCamera::ReadVector(Object,TEXT("angles")),
                ProductionAxeCamera::ReadVector(Object,TEXT("position_cm"))});
        }
    };
    ReadKeys(TEXT("swing_camera"),SwingCamera);
    ReadKeys(TEXT("hit_camera"),HitCamera);
    ReadKeys(TEXT("impact_camera"),ImpactCamera);
    ReadKeys(TEXT("extract_camera"),ExtractCamera);
    PryKeys.Reset();
    for(const auto& Value:Root->GetArrayField(TEXT("pry_keys")))
    {
        const auto Object=Value->AsObject();
        PryKeys.Add(FVector2D(Object->GetNumberField(TEXT("t")),Object->GetNumberField(TEXT("angle"))));
    }
}

void FProductionAxeImpactMotion::Sample(float Seconds,bool bHit,FVector& Location,FRotator& Rotation) const
{
    auto Pose=ProductionAxeCamera::Curve(bHit?HitCamera:SwingCamera,bHit?Seconds-ContactSeconds:Seconds);
    if(bHit)
    {
        const float Age=Seconds-ContactSeconds;
        const auto Impact=ProductionAxeCamera::Curve(ImpactCamera,Age);
        const auto Extract=ProductionAxeCamera::Curve(ExtractCamera,Age-PryEndSeconds);
        Pose.Angles+=Impact.Angles+Extract.Angles;
        Pose.Position+=Impact.Position+Extract.Position;
        const float Rock=ProductionAxeCamera::Pry(PryKeys,Age);
        Pose.Angles.X+=Rock*PryCameraPitch;
        Pose.Position.Z+=Rock*PryCameraUp;
    }
    const float Strength=FMath::Max(0.f,AxeImpactCameraScale.GetValueOnGameThread());
    Location=Pose.Position*Strength;
    Rotation=FRotator(Pose.Angles.X,Pose.Angles.Y,Pose.Angles.Z)*Strength;
}
