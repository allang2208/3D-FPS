#include "WeaponEquipWireAudit.h"
#include "GunsmithSystem.h"
#include "M249Attachments.h"
#include "M249OpticAssets.h"
#include "WeaponBipodDeploymentComponent.h"
#include "M249Bipod.h"
#include "M249WeaponAssets.h"
#include "LMGStabilityGrip.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Serialization/JsonSerializer.h"

namespace EquipWire {void Network(UWorld* World);}
namespace
{
struct FPartChoice { const TCHAR* Slot; const TCHAR* Fitted; };
constexpr FPartChoice Choices[]={{TEXT("bipod"),TEXT("m249_no_bipod")},{TEXT("underbarrel"),LMGStabilityGrip::Id},
    {TEXT("reargrip"),TEXT("balanced_reargrip")},{TEXT("stock"),TEXT("skeleton")},{TEXT("muzzle"),TEXT("brake")},{TEXT("optic"),TEXT("holographic")}};

bool PartsMatch(const FColdSteelItem* Item,const UGunsmithSystem& Guns,const FString& Instance,bool Fitted)
{
    if(!Item||Item->InstanceId!=Instance||Item->Definition!=M249WeaponAssets::Definition)return false;
    const auto Parts=Guns.Installed(*Item);
    for(const auto& Choice:Choices)
        if(Parts.FindRef(Choice.Slot)!=(Fitted?FString(Choice.Fitted):FString()))return false;
    return true;
}

bool BodyMatches(const TArray<FFPSBodyWeapon>& Weapons,bool Fitted,const FString& Instance=FString())
{
    if(Weapons.Num()!=1)return false;
    const auto& W=Weapons[0];
    if(W.GunDefinition!=FName(M249WeaponAssets::Definition)||(!Instance.IsEmpty()&&W.ItemInstance!=Instance))return false;
    const auto* Mesh=W.Mesh.Get();if(!Mesh)return false;
    for(const TCHAR* Name:{TEXT("M249_Bipod"),TEXT("M249_Factory_Foregrip"),TEXT("M249_Factory_RearGrip"),
        TEXT("M249_Factory_Stock"),TEXT("M249_Factory_Muzzle"),TEXT("M249_OpticalHousing"),TEXT("M249_MagnifierGlass"),TEXT("M249_MagnifierReticle")})
    {
        const FName Slot(Name);
        const int32 Index=Mesh->GetMaterials().IndexOfByPredicate([Slot](const FSkeletalMaterial& Material){return Material.MaterialSlotName==Slot;});
        const bool Hidden=Fitted||Slot==TEXT("M249_Bipod")||Slot==TEXT("M249_Factory_Foregrip");
        if(Index==INDEX_NONE||W.HiddenMaterials.Contains(Index)!=Hidden)return false;
    }
    for(const TCHAR* Path:{M249Bipod::Base,M249Bipod::LegA,M249Bipod::LegB})
    {
        int32 Count=0;
        for(const auto& Part:W.Parts)if(Part.bVisible&&Part.Mesh.ToSoftObjectPath().GetLongPackageName()==Path)++Count;
        if(Count!=(Fitted?0:1))return false;
    }
    for(const FString& Path:{M249Attachments::MeshPath(LMGStabilityGrip::Id),M249Attachments::MeshPath(TEXT("balanced_reargrip")),
        M249Attachments::MeshPath(TEXT("skeleton")),M249Attachments::MeshPath(TEXT("brake")),M249OpticAssets::MeshPath(TEXT("holographic"))})
    {
        int32 Count=0;
        for(const auto& Part:W.Parts)if(Part.bVisible&&Part.Mesh.ToSoftObjectPath().GetLongPackageName()==Path)++Count;
        if(Count!=(Fitted?1:0))return false;
    }
    return true;
}
}

void AWeaponEquipWireController::TickM249Parts()
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* Body=Subject?Subject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Body||!Guns||bFinished)return;
    if(!IsLocalController())
    {
        if(PendingCase<0)return;
        auto* Host=Cast<AWeaponEquipWireController>(GetWorld()->GetFirstPlayerController());
        if(!Host||!Host->IsLocalController()||Host->CaseIndex!=PendingCase||Host->Stage!=1)return;
        const auto* PS=GetPlayerState<AColdSteelPlayerState>();
        const auto* Shadow=PS&&PS->ShadowModel?PS->ShadowModel->ActiveFirearm():nullptr;
        const bool Fitted=PendingCase==1;
        const bool ShadowOK=PartsMatch(Shadow,*Guns,PendingExpected,Fitted);
        const bool RemoteOK=BodyMatches(Body->ReplicatedWeapons,Fitted,PendingExpected);
        const bool DeployAllowed=Subject->BipodDeployment&&Subject->BipodDeployment->AuthorityEligible();
        if(!(ShadowOK&&RemoteOK&&(DeployAllowed!=Fitted))&&Now-PendingAt<12.)return;
        TSharedPtr<FJsonObject> Row;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PendingJson),Row);
        if(!Row)Row=MakeShared<FJsonObject>();
        const bool Passed=Row->HasField(TEXT("passed"))&&Row->GetBoolField(TEXT("passed"))&&Host->bCasePassed&&ShadowOK&&RemoteOK&&(DeployAllowed!=Fitted);
        Row->SetBoolField(TEXT("server_deploy_eligible"),DeployAllowed);
        Row->SetBoolField(TEXT("host_save_reload"),Host->bCasePassed);
        Row->SetBoolField(TEXT("server_shadow"),ShadowOK);Row->SetBoolField(TEXT("guest_seen_by_host"),RemoteOK);
        Row->SetBoolField(TEXT("passed"),Passed);Results.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("M249_PARTS case=%d host=%d shadow=%d remote=%d pass=%d"),PendingCase,Host->bCasePassed,ShadowOK,RemoteOK,Passed);
        bPassed&=Passed;
        Host->ClientCaseAck_Implementation(PendingCase,Passed);ClientCaseAck(PendingCase,Passed);
        bFinished=PendingCase==2;PendingCase=-1;return;
    }
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!Model->IsAudit()||bWaiting)return;
    if(StageAt<0){StageAt=Now;EquipWire::Network(GetWorld());}
    const bool Fitted=CaseIndex==1;
    if(Stage==0)
    {
        if(Now-StageAt<3.)return;
        if(CaseIndex==0)
        {
            auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();
            auto Item=Model->CreateItem(M249WeaponAssets::Definition);Item.Place=1;Item.Cell=6;Item.Magazine=100;S.Items.Add(Item);
            ExpectedInstance=Item.InstanceId;bCasePassed=Model->CommitState(S);Model->AttachPawn(Subject);
        }
        else
        {
            bCasePassed=Guns->Begin(ExpectedInstance);
            for(const auto& Choice:Choices)bCasePassed&=Guns->Select(Choice.Slot,Fitted?Choice.Fitted:TEXT("false"));
            bCasePassed&=Guns->Apply();Guns->Close();
        }
        bCasePassed&=Model->SaveNow()&&Model->ReloadProfile();
        bCasePassed&=PartsMatch(Model->ActiveFirearm(),*Guns,ExpectedInstance,Fitted);
        Stage=1;StageAt=Now;return;
    }
    if(HasAuthority())return; // Hold the host configuration until the guest sees its simulated proxy.
    const bool OwnerOK=BodyMatches(Body->LocalWeapons,Fitted,ExpectedInstance);
    bool ObserverOK=false;
    for(TActorIterator<AFPSGAMECharacter> It(GetWorld());It;++It)
        if(*It!=Subject&&It->GetLocalRole()==ROLE_SimulatedProxy)
            if(auto* Other=It->FindComponentByClass<UFPSPlayerBodyComponent>())ObserverOK|=BodyMatches(Other->ReplicatedWeapons,Fitted);
    const bool Grounded=Subject->GetCharacterMovement()->IsMovingOnGround();
    if(!(OwnerOK&&ObserverOK&&Grounded)&&Now-StageAt<18.)return;
    if(Fitted&&Stage==1)
    {
        if(Now-StageAt<2.)return;
        SwitchCount=Subject->ShotsFired;Subject->FirePressed();Stage=2;StageAt=Now;return;
    }
    const double BurstAtLastShot=Subject->TriggerFirstShotWorldTime>=0.
        ?Subject->LastShotWorldTime-Subject->TriggerFirstShotWorldTime:0.;
    if(Fitted&&BurstAtLastShot<LMGStabilityGrip::FullBonusSeconds&&Now-StageAt<10.)return;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),CaseIndex);
    Row->SetBoolField(TEXT("guest_save_reload"),bCasePassed);
    if(Fitted)
    {
        const float Alpha=Subject->StabilityGripFireAlpha(GetWorld()->GetTimeSeconds());
        const float Recoil=Subject->LastShotGripRecoilMultiplier;
        const int32 Shots=Subject->ShotsFired-SwitchCount;
        Subject->FireReleased();
        const float Released=Subject->StabilityGripFireAlpha(GetWorld()->GetTimeSeconds());
        Row->SetNumberField(TEXT("burst_shots"),Shots);Row->SetNumberField(TEXT("peak_fire_alpha"),Alpha);
        Row->SetNumberField(TEXT("last_shot_grip_recoil_factor"),Recoil);Row->SetNumberField(TEXT("released_fire_alpha"),Released);
        Row->SetNumberField(TEXT("burst_at_last_shot_seconds"),BurstAtLastShot);
        bCasePassed&=Shots>1&&BurstAtLastShot>=LMGStabilityGrip::FullBonusSeconds&&Alpha==1.f&&Released==0.f
            &&FMath::IsNearlyEqual(Recoil,LMGStabilityGrip::AdditionalRecoilMultiplier(1.f));
    }
    Row->SetStringField(TEXT("guest_instance"),ExpectedInstance);
    Row->SetBoolField(TEXT("guest_local_body"),OwnerOK);Row->SetBoolField(TEXT("host_seen_by_guest"),ObserverOK);
    Row->SetBoolField(TEXT("guest_on_shared_floor"),Grounded);
    Row->SetBoolField(TEXT("passed"),bCasePassed&&OwnerOK&&ObserverOK&&Grounded);
    Results.Add(MakeShared<FJsonValueObject>(Row));
    FString Json;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Json));
    bWaiting=true;ServerCaseReport(CaseIndex,ExpectedInstance,Json);
}
