#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "StarMarrowComponent.h"
#include "StarMarrowChargeMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
// V7 deliberately repositions the right wrist around the hilt. Compare the compressed clip to
// its authored trajectory in centimeters, including the rig scale, instead of assuming a fixed wrist.
TArray<float> AuthoredGripDistances(const FString& Variant)
{
    const FString File=FPaths::ProjectDir()/TEXT("SourceAssets/StarMarrowChargeMotion20261103/DirectRecoverV7")/Variant/TEXT("poses.json");
    FString Source;TSharedPtr<FJsonObject> Pose;
    if(!FFileHelper::LoadFileToString(Source,*File)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Source),Pose))return {};
    const auto& Names=Pose->GetArrayField(TEXT("names"));
    const auto BoneIndex=[&Names](const TCHAR* Name){return Names.IndexOfByPredicate([Name](const auto& Entry){return Entry->AsString()==Name;});};
    const int32 Hand=BoneIndex(TEXT("hand_r")),Weapon=BoneIndex(TEXT("WPN_root"));
    if(Hand==INDEX_NONE||Weapon==INDEX_NONE)return {};
    const auto Column=[](const auto& Matrix,int32 C)
    {return FVector(Matrix[0]->AsArray()[C]->AsNumber(),Matrix[1]->AsArray()[C]->AsNumber(),Matrix[2]->AsArray()[C]->AsNumber());};
    TArray<float> Result;FVector InitialGrip=FVector::ZeroVector;
    for(const auto& Frame:Pose->GetArrayField(TEXT("poses")))
    {
        const auto& Bones=Frame->AsArray();
        const auto& W=Bones[Weapon]->AsArray();
        const FVector Delta=Column(Bones[Hand]->AsArray(),3)-Column(W,3);
        const FVector Grip=FVector::DotProduct(Column(W,0).GetSafeNormal(),Delta)*FVector::ForwardVector+
            FVector::DotProduct(Column(W,1).GetSafeNormal(),Delta)*FVector::RightVector+
            FVector::DotProduct(Column(W,2).GetSafeNormal(),Delta)*FVector::UpVector;
        if(Result.IsEmpty())InitialGrip=Grip;
        Result.Add(float(FVector::Distance(Grip,InitialGrip)*100.));
    }
    return Result;
}
}

int32 URuneSwordAuditCommandlet::AuditStarMarrowMotion(const FString& Params)
{
    FString Output;if(!FParse::Value(*Params,TEXT("Report="),Output))return 2;
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Charge_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("StarMarrowMotionAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("StarMarrowMotionAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    World->InitializeActorsForPlay(FURL());
    FString Report;int32 Checks=0,Failures=0;
    const auto Check=[&](bool OK,const FString& Name)
    {
        ++Checks;Failures+=!OK;const FString Line=FString::Printf(TEXT("CHARGE_AUDIT %s %s\n"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
        Report+=Line;UE_LOG(LogTemp,Display,TEXT("%s"),*Line);
    };
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();
    State.Mana=100;State.Stamina=100;State.bSprintExhausted=false;State.DungeonRun={};
    for(auto& Skill:State.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Item=Model->CreateItem(TEXT("ue_frost_crystal_sword"));Item.InstanceId=TEXT("charge-audit-sword");Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    if(!Data)Data=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("star_marrow"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));State.Items={Item};Model->AdoptNetMirror(State);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->bShowMouseCursor=false;PC->Possess(Pawn);
    Pawn->SetActorTickEnabled(false);for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();auto* Core=Pawn->FindComponentByClass<UStarMarrowComponent>();
    Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();Sword->InstanceId=Item.InstanceId;
    Sword->Viewmodel=NewObject<USkeletalMeshComponent>(Pawn);Pawn->AddInstanceComponent(Sword->Viewmodel);
    Sword->Viewmodel->SetupAttachment(Sword->Camera.Get());Sword->Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Sword->Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sword->Viewmodel->RegisterComponent();
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny"));
    Sword->Viewmodel->SetSkeletalMesh(Mesh);
    Check(Pawn->IsLocallyControlled()&&Sword->CanUse(),TEXT("isolated fixture has local control and usable action context"));
    for(const FString Variant:{FString(TEXT("Standard")),FString(TEXT("LongGrip"))})
    {
        const FString Folder=Variant==TEXT("Standard")?TEXT("/Game/Weapons/AzureRunesword20260913/"):TEXT("/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/");
        auto* Idle=LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("A_RuneSword_Idle")));
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103/")+Variant+TEXT("/A_StarMarrow_Charge")));
        Check(Mesh&&Idle&&Clip,Variant+TEXT(" saved rig, idle and charge load"));if(!Mesh||!Idle||!Clip)continue;
        Sword->Animations.Add(TEXT("Idle"),Idle);Sword->Animations.Add(TEXT("StarMarrowCharge"),Clip);
        Sword->CancelAction();Sword->SetClip(TEXT("Idle"),true);Sword->SamplePose(0);
        const auto Bone=[&](const TCHAR* Name){return Sword->Viewmodel->GetSocketTransform(FName(Name),RTS_Component);};
        const FTransform IdleWpn=Bone(TEXT("WPN_root")),IdleR=Bone(TEXT("hand_r")),IdleL=Bone(TEXT("hand_l"));
        const FTransform Grip=IdleR.GetRelativeTransform(IdleWpn);
        const float UpperR=FVector::Distance(Bone(TEXT("upperarm_r")).GetLocation(),Bone(TEXT("lowerarm_r")).GetLocation());
        const float LowerR=FVector::Distance(Bone(TEXT("lowerarm_r")).GetLocation(),IdleR.GetLocation());
        float MaxGrip=0,MaxGripError=0,MaxLength=0;bool Finite=true;
        const auto Reference=AuthoredGripDistances(Variant);
        Sword->SetClip(TEXT("StarMarrowCharge"),false);
        const int32 LastFrame=FMath::RoundToInt(StarMarrowChargeMotion::Duration*120.f);
        for(int32 F=0;F<=LastFrame;++F)
        {
            Sword->SamplePose(F/120.f);const FTransform R=Bone(TEXT("hand_r")),W=Bone(TEXT("WPN_root"));
            Finite&=!R.ContainsNaN()&&!W.ContainsNaN()&&!Bone(TEXT("hand_l")).ContainsNaN();
            const float Travel=float(W.TransformVector(R.GetRelativeTransform(W).GetLocation()-Grip.GetLocation()).Size());
            MaxGrip=FMath::Max(MaxGrip,Travel);
            if(Reference.IsValidIndex(F))MaxGripError=FMath::Max(MaxGripError,FMath::Abs(Travel-Reference[F]));
            MaxLength=FMath::Max(MaxLength,FMath::Abs(float(FVector::Distance(Bone(TEXT("upperarm_r")).GetLocation(),Bone(TEXT("lowerarm_r")).GetLocation()))-UpperR));
            MaxLength=FMath::Max(MaxLength,FMath::Abs(float(FVector::Distance(Bone(TEXT("lowerarm_r")).GetLocation(),R.GetLocation()))-LowerR));
        }
        Check(FMath::IsNearlyEqual(Clip->GetPlayLength(),StarMarrowChargeMotion::Duration,.001f),Variant+TEXT(" duration matches charge motion"));
        Check(Finite&&Reference.Num()==LastFrame+1&&MaxGripError<.1f&&MaxLength<.05f,FString::Printf(TEXT("%s compressed poses: authored wrist travel %.4f cm, error %.4f cm, bone length error %.4f cm"),*Variant,MaxGrip,MaxGripError,MaxLength));
        Check(Bone(TEXT("WPN_root")).Equals(IdleWpn,.005f)&&Bone(TEXT("hand_r")).Equals(IdleR,.005f)&&Bone(TEXT("hand_l")).Equals(IdleL,.005f),Variant+TEXT(" final pose matches installed idle"));
        Sword->CancelAction();Check(Sword->BeginStarMarrowChargeMotion(),Variant+TEXT(" native motion starts"));
        Check(Sword->IsBusy()&&!Sword->CanReleaseSupportHand(),TEXT("motion owns both hands"));
        Sword->TickComponent(.4f,LEVELTICK_All,nullptr);const float Progress=Sword->Elapsed;
        Sword->BeginStarMarrowChargeMotion();Check(FMath::IsNearlyEqual(Sword->Elapsed,Progress),TEXT("confirm during playback does not rewind"));
        Sword->CancelStarMarrowChargeMotion();Check(!Sword->IsBusy()&&Sword->CanReleaseSupportHand(),TEXT("cancel releases action ownership"));
        Check(!Sword->BeginStarMarrowChargeMotion(StarMarrowChargeMotion::Duration+.1f),TEXT("stale motion is skipped"));
        for(float Hz:{30.f,60.f,144.f})
        {
            Sword->CancelAction();Sword->BeginStarMarrowChargeMotion();int32 Frames=0;
            while(Sword->IsStarMarrowChargeMotionPlaying()&&Frames<500){Sword->TickComponent(1.f/Hz,LEVELTICK_All,nullptr);++Frames;}
            Check(!Sword->IsBusy()&&FMath::Abs(Frames/Hz-StarMarrowChargeMotion::Duration)<=1.01f/Hz,FString::Printf(TEXT("%s completes and returns idle at %.0f FPS"),*Variant,Hz));
        }
    }
    Core->Configure(Model);Sword->CancelAction();
    const float Mana=Model->Mana(),Cost=float(Model->Derived(TEXT("maxMp")))*.2f;
    Core->Trigger();
    Check(Core->Remaining()>29.9f&&Sword->IsStarMarrowChargeMotionPlaying(),TEXT("G ability entry starts charge and native motion"));
    Check(FMath::IsNearlyEqual(Mana-Model->Mana(),Cost,.01f),TEXT("activation spends 20 percent maximum mana once"));
    const float PaidMana=Model->Mana();Core->Trigger();Check(Model->Mana()==PaidMana,TEXT("repeat activation does not pay again"));
    Sword->CancelStarMarrowChargeMotion();Core->OnRep_State();
    Check(!Sword->IsStarMarrowChargeMotionPlaying(),TEXT("duplicate state after interruption does not restart"));
    Core->PresentedChargeUntil=0.;Core->bPredictedChargeMotion=true;Core->OnRep_State();
    Check(!Sword->IsStarMarrowChargeMotionPlaying()&&!Core->bPredictedChargeMotion,TEXT("late confirmation consumes interrupted prediction without replay"));
    Core->PresentedChargeUntil=0.;Core->OnRep_State();Check(Sword->IsStarMarrowChargeMotionPlaying(),TEXT("fresh unpredicted confirmation starts motion"));
    Sword->CancelStarMarrowChargeMotion();
    auto* Loaded=Cast<UAnimSequence>(Sword->Animations.FindRef(TEXT("StarMarrowCharge")).Get());
    Sword->Animations.Remove(TEXT("StarMarrowCharge"));Core->PresentedChargeUntil=0.;Core->OnRep_State();
    Check(!Sword->IsStarMarrowChargeMotionPlaying()&&Core->PresentedChargeUntil!=Core->ChargedUntil,TEXT("confirmed state waits for delayed clip"));
    Sword->Animations.Add(TEXT("StarMarrowCharge"),Loaded);Core->TickComponent(.016f,LEVELTICK_All,nullptr);
    Check(Sword->IsStarMarrowChargeMotionPlaying()&&Core->PresentedChargeUntil==Core->ChargedUntil,TEXT("late clip presents once at authoritative age"));
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const float BeforeDeath=Health->Health;Health->Health=0.f;Core->TickComponent(.016f,LEVELTICK_All,nullptr);Health->Health=BeforeDeath;
    Check(!Sword->IsStarMarrowChargeMotionPlaying()&&Core->ChargedUntil==0.&&Core->Remaining()==0,TEXT("death cancels charge and revival does not resume it"));
    auto Old=State;Old.Mana=Mana;Old.StarMarrowManaSpent=0.;
    Old.MergeStarMarrowSpend(Cost);Old.MergeStarMarrowSpend(Cost);Old.MergeStarMarrowSpend(0.);
    Check(FMath::IsNearlyEqual(Old.Mana,PaidMana,.01f),TEXT("duplicate and older spend receipts debit exactly once"));
    State.Mana=0;Model->AdoptNetMirror(State);Core->Configure(Model);Core->Trigger();
    Check(Core->Remaining()==0&&!Sword->IsStarMarrowChargeMotionPlaying(),TEXT("insufficient mana starts neither charge nor motion"));
    FVector Location=FVector::ZeroVector;FRotator Rotation=FRotator::ZeroRotator;
    StarMarrowChargeMotion::Camera(StarMarrowChargeMotion::Duration,Location,Rotation);
    Check(Location.IsNearlyZero(.0001f)&&Rotation.IsNearlyZero(.0001f),TEXT("camera envelope returns exactly to zero"));
    const FRotator Control=PC->GetControlRotation();Sword->BeginStarMarrowChargeMotion(.76f);Pawn->RefreshQuickCombatCamera();
    Check(PC->GetControlRotation().Equals(Control,.0001f),TEXT("presentation shake leaves control rotation unchanged"));Sword->CancelAction();
    Report+=FString::Printf(TEXT("RESULT checks=%d failures=%d; isolated native world; no live network or gameplay render; profile=%s\n"),Checks,Failures,*Model->ProfileSlot());
    FFileHelper::SaveStringToFile(Report,*Output);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
