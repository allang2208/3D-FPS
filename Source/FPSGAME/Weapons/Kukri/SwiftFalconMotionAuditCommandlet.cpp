#include "SwiftFalconMotionAuditCommandlet.h"
#include "SwiftFalconHeavy.h"
#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

int32 USwiftFalconMotionAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(TEXT("FalconMotion -ColdSteelProfile=SkillNetworkAudit_FalconMotion_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("FalconMotionCheck"));
    FCommandLine::Set(*Original);
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    if(!World||!Model||!Model->IsAudit())return 2;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
    auto* K=Pawn?Pawn->FindComponentByClass<UKukriWeaponComponent>():nullptr;if(!K)return 3;
    auto* Arms=NewObject<UKukriArmsMeshComponent>(Pawn);Pawn->AddInstanceComponent(Arms);
    Arms->SetSkeletalMeshAsset(LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh));Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    K->Viewmodel=Arms;K->SetComponentTickEnabled(false);
    FString Report;int32 Failures=0,Checks=0;
    const auto Check=[&](bool OK,const FString& Name){++Checks;Failures+=!OK;Report+=FString::Printf(TEXT("%s %s\n"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);};
    for(bool Dual:{false,true})
    {
        auto Profile=Model->Snapshot();Profile.Items.Reset();Profile.ActiveWeaponSlot=6;Profile.ActiveProductionTool.Reset();
        auto Main=Model->CreateItem(TEXT("ue_tactical_hatchet"));Main.Place=1;Main.Cell=6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Main.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("hatchet_falcon_edge"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Main.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Main.Data));Profile.Items.Add(Main);
        auto Off=Model->CreateItem(TEXT("ue_tactical_hatchet"));Off.Place=1;Off.Cell=8;Off.Data=Main.Data;if(Dual)Profile.Items.Add(Off);
        Model->AdoptNetMirror(Profile);
        K->InstanceId=Main.InstanceId;K->HeavyOffhandWeapon=Dual?Off.InstanceId:FString();K->OffhandInstanceId=K->HeavyOffhandWeapon;
        K->bDual=Dual;K->bDualHeavy=Dual;K->bFalconHeavy=K->bHeavyAttack=true;K->bHeavyTrainingPending=false;K->FalconReleaseRate=.85f;
        const FName Role=Dual?SwiftFalconHeavy::DualRelease:SwiftFalconHeavy::Release;
        const FString Name=TEXT("A_")+Role.ToString();
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Weapons/TacticalHatchet20261101/SwiftFalconHeavy/Arms/")+Name+TEXT(".")+Name));
        if(!Clip)return 4;K->Animations.Add(Role,Clip);K->SetClip(Role,false,0.f);
        for(uint8 Phase:{uint8(0),uint8(1)})for(int32 Kind=0;Kind<3;++Kind)
        {
            const FString Label=FString::Printf(TEXT("%s phase%d %s"),Dual?TEXT("dual"):TEXT("single"),Phase,Kind==0?TEXT("miss"):Kind==1?TEXT("flesh"):TEXT("wall"));
            K->Shot.MeleeDamagePhase=K->OffhandShot.MeleeDamagePhase=Phase;K->ResetStrike();
            K->bImpactConfirmed=K->bWallHit=false;K->HitStop=0.f;K->ImpactAge=K->StrikeAge=-1.f;
            K->Elapsed=(Phase?SwiftFalconHeavy::PullAt:SwiftFalconHeavy::ChopAt)-.01f;
            if(Kind)K->ConfirmImpact(FHitResult(),Kind==2);
            Check(K->HitStop==0.f,Label+TEXT(" queues before strike"));
            K->Elapsed+=.01f;K->SamplePose(K->Elapsed);K->ArriveStrike();
            const float Expected=Kind==0?K->StrikeProfile().MissStop:Kind==1?SwiftFalconHeavy::FleshStop(Phase==1,Dual):Phase?.065f:.085f;
            Check(FMath::IsNearlyEqual(K->HitStop,Expected,.00001f),Label+FString::Printf(TEXT(" stop=%.3fs"),K->HitStop));
            const float Before=K->Elapsed;const FTransform Pose=K->BladeFrame();
            K->bSwingPlayed=K->bRiftStarted=true;K->bHavePreviousBlade=false;
            K->AdvanceHeavy(Expected*.5f);
            Check(FMath::IsNearlyEqual(Before,K->Elapsed,.000001f)&&Pose.Equals(K->BladeFrame(),.00001f),Label+TEXT(" real action clock and pose frozen"));
            K->AdvanceHeavy(K->HitStop+.001f);
            Check(K->Elapsed>Before&&K->HitStop<=UE_SMALL_NUMBER,Label+TEXT(" resumes after real-time hold"));
        }
        K->Shot.MeleeDamagePhase=0;K->HitStop=0.f;K->Elapsed=SwiftFalconHeavy::Hook-.001f;
        K->bImpactConfirmed=true;K->bWallHit=true;K->bSwingPlayed=K->bRiftStarted=true;
        K->AdvanceHeavy(.006f);
        Check(K->Shot.MeleeDamagePhase==1&&!K->bImpactConfirmed&&!K->bWallHit,TEXT("hook resets contact guard for second strike"));
        if(Dual)
        {
            Profile.Items[1].Data=Model->CreateItem(TEXT("ue_tactical_hatchet")).Data;
            Model->AdoptNetMirror(Profile);
            Check(!SwiftFalconHeavy::Eligible(Model->ActiveKukriWeapon(),Model,true),TEXT("one factory blade disables paired Falcon"));
            K->AdvanceHeavy(.01f);
            Check(!K->bHeavyAttack&&!K->bFalconHeavy,TEXT("changing the offhand head cancels an in-flight Falcon release"));
        }
    }
    Report+=FString::Printf(TEXT("checks=%d failures=%d\nNo BeginPlay, game input, target collision or network session was run.\n"),Checks,Failures);
    FString Out=FPaths::ProjectSavedDir()/TEXT("SwiftFalconMotionInspection/runtime-clock.txt");FParse::Value(*Params,TEXT("Out="),Out);
    FFileHelper::SaveStringToFile(Report,*Out);UE_LOG(LogTemp,Display,TEXT("FALCON_MOTION %s"),*Report);
    return Failures?1:0;
}
