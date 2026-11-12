#include "WeaponEquipWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "M249Attachments.h"
#include "LMGGripReview.h"
#include "GunsmithSystem.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace EquipWire {void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed);void Network(UWorld* World);}
namespace M249WristWire
{
const TCHAR* Variants[]={TEXT("false"),TEXT("vertical_foregrip"),TEXT("tactical_vertical_foregrip"),TEXT("angled_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")};
FString Variant(int32 Case){return LMGGripReview::Enabled()?LMGGripReview::Variant(Case):Variants[Case/2];}
FString Definition(int32 Case){return LMGGripReview::Enabled()?LMGGripReview::Definition(Case):TEXT("ue_m249");}
FString Profile(int32 Case){if(LMGGripReview::Enabled())return LMGGripReview::Profile(Case);return M249Attachments::ProfilePath(FName(M249Attachments::ForegripFamily(Variants[Case/2])));}
bool Recipe(const TArray<FFPSBodyWeapon>& Weapons,int32 Case)
{
    if(Weapons.Num()!=1)return false;
    const auto& W=Weapons[0];const FString V=Variant(Case),D=Definition(Case);
    if(W.GunDefinition!=FName(*D)||W.GripProfile.ToSoftObjectPath().GetLongPackageName()!=Profile(Case))return false;
    const bool Bare=V==TEXT("false");const FString Expected=V==LMGStabilityGrip::Id?LMGStabilityGrip::MeshPath(D):M249Attachments::MeshPath(V);
    int32 Grips=0;bool Found=Bare;
    for(const auto& Part:W.Parts)if(Part.bVisible)
    {
        const FString Path=Part.Mesh.ToSoftObjectPath().GetLongPackageName(),Name=Part.Mesh.ToSoftObjectPath().GetAssetName();
        if(Path.StartsWith(TEXT("/Game/Weapons/LMGStabilityGrip20261111/SM_"))||Name.EndsWith(TEXT("_vertical"))||Name.EndsWith(TEXT("_tactical_vertical"))||Name.EndsWith(TEXT("_angled"))||Name.EndsWith(TEXT("_canted"))||Name.EndsWith(TEXT("_prism")))
        {++Grips;Found|=Path==Expected;}
    }
    if(D==TEXT("ue_m249"))
        if(auto* Mesh=W.Mesh.Get())
            if(!W.HiddenMaterials.Contains(Mesh->GetMaterials().IndexOfByPredicate([](const auto& M){return M.MaterialSlotName==TEXT("M249_Factory_Foregrip");})))return false;
    return Found&&Grips==(Bare?0:1);
}
bool Stats(UGunsmithSystem* G,const FColdSteelItem* Item,int32 Case,TSharedPtr<FJsonObject> J)
{
    if(!LMGGripReview::Enabled())return true;
    if(!G||!Item)return false;
    auto Parts=G->Installed(*Item);auto Bare=Parts;Bare.Remove(TEXT("underbarrel"));
    const auto B=G->Calculate(Item->Definition,Bare),S=G->Calculate(Item->Definition,Parts);
    const bool Equipped=Case>=2;const auto V=Parts.FindRef(TEXT("underbarrel"));
    const bool Id=Equipped?V==LMGStabilityGrip::Id:(V.IsEmpty()||V==TEXT("false"));
    const double Recoil=S.Recoil/B.Recoil,Stability=S.StabilityMultiplier/B.StabilityMultiplier,ADS=S.ADS/B.ADS;
    const FGunsmithWeapon* Gun=G->Weapon(Item->Definition);
    const bool Passed=Id&&Gun&&FMath::IsNearlyEqual(Recoil,Equipped?.85:1.,.00001)&&FMath::IsNearlyEqual(Stability,Equipped?1.15:1.,.00001)
        &&FMath::IsNearlyEqual(S.ADSPercent,B.ADSPercent,.00001)&&FMath::IsNearlyEqual(S.ADS,B.ADS,.00001)
        &&!G->Option(TEXT("ue_akm"),TEXT("underbarrel"),LMGStabilityGrip::Id);
    if(J){J->SetBoolField(TEXT("stats_and_slot_valid"),Passed);J->SetNumberField(TEXT("recoil_ratio"),Recoil);J->SetNumberField(TEXT("stability_ratio"),Stability);J->SetNumberField(TEXT("ads_duration_ratio"),ADS);J->SetNumberField(TEXT("ads_seconds_added"),S.ADS-B.ADS);}
    return Passed;
}

}

void AWeaponEquipWireController::ServerWristBegin_Implementation(int32 Case,const FString& Expected)
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("M249WristWire"))||Case<0||Case>=LMGGripReview::Count())return;
    CaseIndex=Case;ExpectedInstance=Expected;bWristSawAim=bWristSawReload=false;bWristFinite=true;WristSamples=WristBadEquipment=0;
}

void AWeaponEquipWireController::TickM249Wrist(float Dt)
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());if(!Subject||!Subject->HasActorBegunPlay()||bFinished)return;
    auto* Body=Subject->FindComponentByClass<UFPSPlayerBodyComponent>();if(!Body)return;
    if(!IsLocalController())
    {
        const auto State=Body->GetBodyState();
        if(!ExpectedInstance.IsEmpty()&&State.WeaponInstance==ExpectedInstance)
        {
            ++WristSamples;bWristSawAim|=State.bAiming;bWristSawReload|=State.Action==(CaseIndex%2?EFPSBodyAction::ReloadEmpty:EFPSBodyAction::Reload);
            bWristFinite&=State.Contacts.IsSane();
            if(!M249WristWire::Recipe(Body->ReplicatedWeapons,CaseIndex))
            {
                ++WristBadEquipment;
                if(WristBadEquipment==1)
                {
                    const auto& Weapons=Body->ReplicatedWeapons;
                    UE_LOG(LogTemp,Warning,TEXT("WRIST_REMOTE_RECIPE case=%d state=%s weapons=%d"),CaseIndex,*State.WeaponInstance,Weapons.Num());
                    for(const auto& W:Weapons)
                        UE_LOG(LogTemp,Warning,TEXT("WRIST_REMOTE_WEAPON item=%s gun=%s profile=%s hidden=%d"),*W.ItemInstance,*W.GunDefinition.ToString(),*W.GripProfile.ToString(),W.HiddenMaterials.Num());
                }
            }
        }
        if(PendingCase<0)return;
        const auto* PS=GetPlayerState<AColdSteelPlayerState>();const auto* Item=PS&&PS->ShadowModel?PS->ShadowModel->ActiveFirearm():nullptr;
        const bool Synced=Item&&Item->InstanceId==PendingExpected&&State.WeaponInstance==PendingExpected&&State.Action==EFPSBodyAction::None&&M249WristWire::Recipe(Body->ReplicatedWeapons,PendingCase);
        if(!Synced&&Now-PendingAt<8.)return;
        TSharedPtr<FJsonObject> J;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PendingJson),J);if(!J)J=MakeShared<FJsonObject>();
        FTransform Camera;float FOV;Subject->FirstPersonCamera->GetAdditiveOffset(Camera,FOV);
        const bool Stats=M249WristWire::Stats(GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item,PendingCase,nullptr);
        J->SetBoolField(TEXT("authority_stats_match"),Stats);
        const bool Passed=J->GetBoolField(TEXT("passed"))&&Stats&&Synced&&bWristSawAim&&bWristSawReload&&bWristFinite&&WristSamples>0&&WristBadEquipment==0&&Camera.Equals(FTransform::Identity,.0001f);
        J->SetBoolField(TEXT("passed"),Passed);J->SetBoolField(TEXT("authority_settled"),Synced);
        J->SetBoolField(TEXT("remote_saw_aim"),bWristSawAim);J->SetBoolField(TEXT("remote_saw_reload"),bWristSawReload);
        J->SetNumberField(TEXT("remote_samples"),WristSamples);J->SetNumberField(TEXT("remote_wrong_equipment_frames"),WristBadEquipment);
        J->SetBoolField(TEXT("remote_contacts_finite"),bWristFinite);
        Results.Add(MakeShared<FJsonValueObject>(J));bPassed&=Passed;ClientCaseAck(PendingCase,Passed);PendingCase=-1;
        bFinished=Results.Num()==((FParse::Param(FCommandLine::Get(),TEXT("M249WristBaseOnly"))||FParse::Param(FCommandLine::Get(),TEXT("M249WristPrismOnly")))?2:LMGGripReview::Count());ExpectedInstance.Reset();return;
    }
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Model->IsAudit()||bWaiting)return;
    if(StageAt<0){StageAt=Now;EquipWire::Network(GetWorld());if(FParse::Param(FCommandLine::Get(),TEXT("M249WristPrismOnly")))CaseIndex=10;}
    if(Stage==0)
    {
        if((CaseIndex==0||CaseIndex==10)&&FParse::Param(FCommandLine::Get(),TEXT("M249WristCapture")))
        {
            int32 Peers=0;bool Ready=true;
            for(TActorIterator<AFPSGAMECharacter> It(GetWorld());It;++It)if(It->HasActorBegunPlay())
            {
                ++Peers;auto* PeerBody=It->FindComponentByClass<UFPSPlayerBodyComponent>();
                Ready&=PeerBody&&!PeerBody->IsAppearanceLoading();
            }
            if(Peers<2||!Ready){StageAt=Now;return;}
        }
        if(Now-StageAt<1.5)return;
        Subject->bMPAutoInputActive=true;Subject->MoveInput=FVector2D::ZeroVector;Subject->bSprintHeld=false;Subject->AimReleased();
        auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();
        auto W=Model->CreateItem(M249WristWire::Definition(CaseIndex));W.Place=1;W.Cell=6;W.Magazine=CaseIndex%2?0:10;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(W.Data),Data);
        auto Parts=MakeShared<FJsonObject>();
        // The default M249 and an explicitly cleared slot both restore bare.
        if(!LMGGripReview::Enabled()||CaseIndex!=0)Parts->SetStringField(TEXT("underbarrel"),M249WristWire::Variant(CaseIndex));
        Parts->SetStringField(TEXT("magazine"),TEXT("false"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);W.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&W.Data));
        S.Items.Add(W);auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        auto Ammo=Model->CreateItem(Guns->Weapon(W.Definition)->Ammo,200);Ammo.Place=0;Ammo.Cell=0;S.Items.Add(Ammo);
        bCasePassed=Model->CommitState(S);
        if(LMGGripReview::Enabled())
        {
            bWristSaveRestored=Model->SaveNow()&&Model->ReloadProfile();
            const auto* Restored=Model->FindItem(W.InstanceId);
            bWristSaveRestored&=Restored&&Guns->Installed(*Restored).OrderIndependentCompareEqual(Guns->Installed(W));
            bCasePassed&=bWristSaveRestored;
        }
        Model->AttachPawn(Subject);ExpectedInstance=W.InstanceId;
        bWristSawAim=bWristSawReload=false;bWristFinite=true;WristSamples=WristBadEquipment=0;WristBoundary=0;bWristWasReloading=false;
        Stage=1;StageAt=Now;return;
    }
    if(Stage==1)
    {
        if(Now-StageAt<4.)return;
        bCasePassed&=Subject->ActiveInventoryWeapon==ExpectedInstance&&M249WristWire::Recipe(Body->LocalWeapons,CaseIndex);
        if(!HasAuthority())ServerWristBegin(CaseIndex,ExpectedInstance);
        Subject->AimPressed();Stage=2;StageAt=Now;return;
    }
    ++WristSamples;bWristFinite&=Body->GetBodyState().Contacts.IsSane();
    if(!M249WristWire::Recipe(Body->LocalWeapons,CaseIndex)||Subject->ActiveInventoryWeapon!=ExpectedInstance)++WristBadEquipment;
    bWristSawAim|=Subject->WeaponADSFactor>.99f;
    auto* Mesh=Subject->AKMViewmodel.Get();for(const auto& T:Mesh->GetComponentSpaceTransforms())bWristFinite&=!T.ContainsNaN();
    const auto Hand=Mesh->GetSocketTransform(TEXT("hand_l"),RTS_Component).GetLocation();
    if(bWristWasReloading&&!Subject->IsReloading())WristBoundary=FVector::Dist(Hand,WristPrevious);
    bWristWasReloading=Subject->IsReloading();WristPrevious=Hand;
    if(Stage==2&&Now-StageAt>1.5)
    {
        Subject->ReloadPressed();bCasePassed&=Subject->IsReloading()&&Subject->bPendingEmptyReload==bool(CaseIndex%2);
        bWristSawReload=Subject->IsReloading();Stage=3;StageAt=Now;return;
    }
    if(Stage==3)
    {
        if(Subject->IsReloading()&&Now-StageAt<18.)return;
        bCasePassed&=!Subject->IsReloading();Subject->AimReleased();Stage=4;StageAt=Now;return;
    }
    if(Stage==4&&Now-StageAt>1.){Subject->AimPressed();Stage=5;StageAt=Now;return;}
    if(Stage==5&&Now-StageAt>1.){Subject->AimReleased();Stage=6;StageAt=Now;return;}
    if(Stage==6&&Now-StageAt>2.)
    {
        auto* Anim=Subject->GunplayAnimation.Get();const bool Profile=Anim&&Anim->GripProfile&&Anim->GripProfile->GetPathName().StartsWith(M249WristWire::Profile(CaseIndex)+TEXT("."));
        const bool Settled=Subject->WeaponState==EAKMWeaponState::Idle&&Subject->WeaponADSFactor<.001f&&Anim&&Anim->ActionAlpha<.001f;
        const bool Stats=M249WristWire::Stats(GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Model->ActiveFirearm(),CaseIndex,nullptr);
        const bool Passed=bCasePassed&&Stats&&bWristSawAim&&bWristSawReload&&bWristFinite&&WristBadEquipment==0&&Settled&&Profile&&WristBoundary<.5;
        auto J=MakeShared<FJsonObject>();J->SetNumberField(TEXT("case"),CaseIndex);J->SetStringField(TEXT("variant"),M249WristWire::Variant(CaseIndex));
        J->SetStringField(TEXT("definition"),M249WristWire::Definition(CaseIndex));
        M249WristWire::Stats(GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Model->ActiveFirearm(),CaseIndex,J);
        if(LMGGripReview::Enabled())J->SetBoolField(TEXT("profile_save_reload"),bWristSaveRestored);
        J->SetBoolField(TEXT("empty"),bool(CaseIndex%2));J->SetStringField(TEXT("owner"),HasAuthority()?TEXT("listen_host"):TEXT("client"));
        J->SetBoolField(TEXT("passed"),Passed);J->SetBoolField(TEXT("settled"),Settled);J->SetBoolField(TEXT("owner_profile_matches"),Profile);
        J->SetBoolField(TEXT("owner_saw_aim"),bWristSawAim);J->SetBoolField(TEXT("owner_saw_reload"),bWristSawReload);
        J->SetBoolField(TEXT("finite"),bWristFinite);J->SetNumberField(TEXT("wrong_equipment_frames"),WristBadEquipment);J->SetNumberField(TEXT("return_boundary_cm"),WristBoundary);
        UE_LOG(LogTemp,Display,TEXT("M249_WRIST_WIRE case=%d owner=%d pass=%d aim=%d reload=%d settled=%d wrong=%d boundary=%.5f"),CaseIndex,HasAuthority(),Passed,bWristSawAim,bWristSawReload,Settled,WristBadEquipment,WristBoundary);
        if(HasAuthority()){Results.Add(MakeShared<FJsonValueObject>(J));bPassed&=Passed;ClientCaseAck_Implementation(CaseIndex,Passed);}
        else{Results.Add(MakeShared<FJsonValueObject>(J));FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));bWaiting=true;ServerCaseReport(CaseIndex,ExpectedInstance,Text);}
    }
}
