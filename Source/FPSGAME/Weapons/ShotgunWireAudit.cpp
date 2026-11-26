#include "ShotgunWireAudit.h"
#include "SniperZhimingWire.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "FPSBallisticsComponent.h"
#include "GunsmithSystem.h"
#include "ShotgunDuckbillAssets.h"
#include "Super90TubeMagazineAssets.h"
#include "M870TubeMagazineAssets.h"
#include "M870WeaponAssets.h"
#include "WeaponPresentationMaterials.h"
#include "Engine/SkeletalMesh.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace ShotgunWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("ShotgunWireAudit"));}
bool M870(){return FParse::Param(FCommandLine::Get(),TEXT("M870"));}
const TCHAR* Definition(){return M870()?M870WeaponAssets::Definition:TEXT("ue_super90");}
const TCHAR* TubePart(){return M870()?M870TubeMagazineAssets::Part:Super90TubeMagazineAssets::Part;}
const TCHAR* TubeMesh(){return M870()?M870TubeMagazineAssets::MeshPath:Super90TubeMagazineAssets::MeshPath;}
bool Tube(int32 Case){return Case!=0&&(!M870()||Case!=4);}
bool Aim(int32 Case){return Case!=0&&Case!=5;}
const TCHAR* Muzzle(int32 Case){return M870()?TEXT("false"):Case==3?TEXT("false"):Case==4?TEXT("shotgun_choke"):ShotgunDuckbillAssets::Part;}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role)
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("passed"),Pass);Root->SetStringField(TEXT("role"),Role);Root->SetArrayField(TEXT("cases"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));FString Path;
    if(FParse::Value(FCommandLine::Get(),TEXT("ShotgunWireOutput="),Path))
    {IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_RESULT %s"),*Json);
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,int32 Case)
{
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
    State.AmmoPouch.Add(TEXT("ammo_12g"),100);State.AmmoPouch.Add(TEXT("ammo_12g_slug"),100);State.CampfireInventoryRevision=0;
    auto Item=Model->CreateItem(Definition());Item.InstanceId=Id;Item.Place=1;Item.Cell=6;
    Item.Magazine=Tube(Case)?10:7;Item.VirtualMagazineAmmo=0;Item.LoadedAmmoType=Case==2?TEXT("ammo_12g_slug"):TEXT("ammo_12g");
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("muzzle"),Muzzle(Case));
    if(Tube(Case))Parts->SetStringField(TEXT("magazine"),TubePart());
    if(M870()&&Case>=3)Parts->SetStringField(TEXT("trigger"),TEXT("m870_lightweight_trigger_kit"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    State.Items={Item};return State;
}
}
void AShotgunWireAuditController::ClientSetup_Implementation(int32 Case,const FString& Id,AFPSGAMECharacter* Host)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("MealReceiptWire"))){SetupMealReceipt(Case,Id);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire"))){SetupPistolAmmo(Case,Id,Host);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolPresentationWire"))){SetupPistolPresentation(Case,Id,Host);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("BowSparrowWire"))){SetupSparrowPresentation(Case,Id,Host);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("M870PresentationWire"))){SetupM870Presentation(Case,Id,Host);return;}
    if(!ShotgunWire::Enabled()||HasAuthority()||Case==Current||!Host)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* PS=GetPlayerState<AColdSteelPlayerState>();
    if(!AuditPawn||!Model||!Model->IsAudit()||!PS||PS->GetPawn()!=AuditPawn)return;
    // The fixture disables movement simulation; an autonomous proxy therefore
    // cannot consume normal movement corrections for the server's test teleport.
    UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_FIXTURE_POSITION case=%d before=%s authority=(0,0,500)"),Case,*AuditPawn->GetActorLocation().ToString());
    AuditPawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);SetControlRotation(FRotator::ZeroRotator);
    Model->Current=ShotgunWire::Seed(Model,Id,Case);Model->CurrentPawn=AuditPawn;AuditPawn->ApplyColdSteelProfile(Model);
    AuditPawn->SetActorTickEnabled(false);AuditPawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    AuditPawn->GetCharacterMovement()->DisableMovement();AuditPawn->GetCharacterMovement()->StopMovementImmediately();
    AuditPawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AuditPawn->Ballistics->SetComponentTickEnabled(false);AuditPawn->Ballistics->PrimaryComponentTick.bCanEverTick=false;AuditPawn->Ballistics->Rounds.Reset();
    AuditPawn->CurrentSpread=AuditPawn->MoveSpread=AuditPawn->AirSpread=0;AuditPawn->WeaponState=EAKMWeaponState::Idle;
    AuditPawn->bIsAiming=ShotgunWire::Aim(Case);AuditPawn->WeaponADSFactor=AuditPawn->bIsAiming?1.f:0.f;
    AuditPawn->NextAllowedShotTime=0;AuditPawn->SprintFireUnlockTime=0;AuditPawn->bIsSprinting=false;
    Host->Ballistics->SetComponentTickEnabled(false);Host->Ballistics->PrimaryComponentTick.bCanEverTick=false;Host->Ballistics->Rounds.Reset();
    PS->Super90ServerWeapons.Reset();PS->bSuper90ReloadPending=false;PS->Super90PredictedShots.Reset();
    ObserverSubject=Host;Weapon=Id;Current=Case;Started=GetWorld()->GetRealTimeSeconds();bSent=bReported=false;Prediction.Reset();
    ServerReady(Case);
}
void AShotgunWireAuditController::ServerReady_Implementation(int32 Case)
{
    if(SniperZhimingWire::Enabled()){ProbeSniperZhiming(Case);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolPresentationWire"))){ReadyPistolPresentation(Case);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("M870PresentationWire")))return;
    if(!ShotgunWire::Enabled()||Case!=Expected)return;
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(PS)PS->SendSuper90Ammo();
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())if(auto* Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn()))
        {Host->WeaponState=EAKMWeaponState::Idle;Host->NextAllowedShotTime=0;Host->bIsAiming=true;Host->WeaponADSFactor=1;Host->FireShot();
        UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_HOST_FIRE case=%d rounds=%d ammo=%d ready=%d busy=%d cycle=%d"),Case,Host->Ballistics->ActiveCount(),Host->MagazineAmmo,Host->bInventoryWeaponReady,Host->IsWeaponBusy(),Host->NeedsReloadCycle());}
}
void AShotgunWireAuditController::Tick(float Delta)
{
    if(TickMealReceipt(Delta))return;
    if(TickPistolAmmo(Delta))return;
    if(TickPistolPresentation(Delta))return;
    if(TickSparrowPresentation(Delta))return;
    if(TickM870Presentation(Delta))return;
    Super::Tick(Delta);if(!ShotgunWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Current<0||bReported)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!AuditPawn||!PS||!Model)return;
    if(!bSent&&PS->IsSuper90ServerReady(Weapon)&&Now-Started>(Current==0?6.:.5))
    {
        ServerProbeShot(Current,AuditPawn->FirstPersonCamera->GetComponentLocation(),AuditPawn->GetEffectiveMuzzleLocation(),
            AuditPawn->ComputeWeaponAimDirection(),GetWorld()->GetGameState()->GetServerWorldTimeSeconds());
        AuditPawn->WeaponState=EAKMWeaponState::Idle;AuditPawn->FireShot();
        UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_OWNER_FIRE case=%d rounds=%d ammo=%d ready=%d busy=%d cycle=%d sequence=%u"),Current,AuditPawn->Ballistics->ActiveCount(),AuditPawn->MagazineAmmo,AuditPawn->bInventoryWeaponReady,AuditPawn->IsWeaponBusy(),AuditPawn->NeedsReloadCycle(),PS->Super90LocalSequence);
        for(const auto& R:AuditPawn->Ballistics->Rounds)Prediction.Add(R.Direction);
        // Replay the same sequence through the actual reliable RPC channel.
        const FVector Eye=AuditPawn->FirstPersonCamera->GetComponentLocation();const FVector Muzzle=AuditPawn->GetEffectiveMuzzleLocation();
        const double Fired=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        PS->ServerSuper90Shot(PS->Super90LocalSequence,Weapon,Eye,Muzzle,AuditPawn->ComputeWeaponAimDirection(),ShotgunWire::Aim(Current),Fired,AuditPawn);
        bSent=true;SentAt=Now;
    }
    const auto* Item=Model->FindItem(Weapon);
    if((bSent&&Item&&Item->Magazine==(ShotgunWire::Tube(Current)?9:6)&&Now-SentAt>2.)||Now-Started>25.)
    {
        const int32 ExpectedCount=Current==2?1:8;
        const float BaseSpread=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(ShotgunWire::Definition())->Base.Spread;
        const bool OwnerOK=bSent&&Prediction.Num()==ExpectedCount&&Item&&Item->Magazine==(ShotgunWire::Tube(Current)?9:6)
            &&FMath::IsNearlyEqual(AuditPawn->HipSpreadMultiplier,BaseSpread*((ShotgunWire::M870()||Current==3||Current==4)?1.f:.75f));
        bool RemoteMesh=false,RemoteTube=false;const auto* Body=ObserverSubject?ObserverSubject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
        if(Body)for(const auto& W:Body->ReplicatedWeapons)
        {
            if(ShotgunWire::M870())if(const auto* Mesh=W.Mesh.Get())
            {
                bool Clean=Mesh->GetPathName()==M870WeaponAssets::MeshPath;
                for(int32 M=0;M<Mesh->GetMaterials().Num();++M)
                    if(WeaponPresentationMaterials::IsArmSection(Mesh->GetMaterials()[M])||Mesh->GetMaterials()[M].MaterialSlotName==TEXT("M870_FactoryTubeCap"))
                        Clean&=W.HiddenMaterials.Contains(M);
                RemoteMesh|=Clean;
            }
            for(const auto& Part:W.Parts)
            {if(!ShotgunWire::M870())RemoteMesh|=Part.Mesh.ToSoftObjectPath().GetLongPackageName()==ShotgunDuckbillAssets::MeshPath;
             RemoteTube|=Part.Mesh.ToSoftObjectPath().GetLongPackageName()==ShotgunWire::TubeMesh()&&Part.bVisible;}
        }
        bool RemoteCosmetic=ObserverSubject&&ObserverSubject->Ballistics->ActiveCount()==8;
        if(ObserverSubject)for(const auto& R:ObserverSubject->Ballistics->Rounds)RemoteCosmetic&=R.bCosmeticOnly;
        const bool RemoteOK=RemoteMesh&&RemoteTube&&RemoteCosmetic;
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Current);Row->SetBoolField(TEXT("owner_ammo_prediction"),OwnerOK);
        Row->SetBoolField(TEXT("remote_mesh"),RemoteMesh);Row->SetBoolField(TEXT("remote_tube"),RemoteTube);Row->SetBoolField(TEXT("remote_cosmetic_rounds"),RemoteCosmetic);
        Row->SetBoolField(TEXT("fire_attempted"),bSent);Row->SetBoolField(TEXT("server_ready"),PS->IsSuper90ServerReady(Weapon));
        Row->SetNumberField(TEXT("predicted_rounds"),Prediction.Num());Row->SetNumberField(TEXT("magazine"),Item?Item->Magazine:-1);
        Row->SetNumberField(TEXT("pawn_magazine"),AuditPawn->MagazineAmmo);Row->SetNumberField(TEXT("hip_spread"),AuditPawn->HipSpreadMultiplier);
        Row->SetNumberField(TEXT("remote_round_count"),ObserverSubject?ObserverSubject->Ballistics->ActiveCount():-1);
        Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=OwnerOK&&RemoteOK;bReported=true;
        ShotgunWire::Save(Results,bAllPassed,TEXT("client"));ServerCaseResult(Current,OwnerOK,RemoteOK,Prediction);
    }
}
void AShotgunWireAuditController::ServerProbeShot_Implementation(int32 Case,FVector Eye,FVector Muzzle,FVector Aim,double FiredAt)
{
    if(!ShotgunWire::Enabled()||Case!=Expected)return;
    const auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());if(!AuditPawn)return;
    UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_INPUT case=%d eye_distance=%.3f muzzle_distance=%.3f aim_dot=%.8f age=%.4f pawn=%s eye=%s"),
        Case,FVector::Distance(Eye,AuditPawn->GetPawnViewLocation()),FVector::Distance(Eye,Muzzle),
        FVector::DotProduct(Aim.GetSafeNormal(),AuditPawn->GetBaseAimRotation().Vector()),GetWorld()->GetGameState()->GetServerWorldTimeSeconds()-FiredAt,
        *AuditPawn->GetActorLocation().ToString(),*Eye.ToString());
}
void AShotgunWireAuditController::ServerCaseResult_Implementation(int32 Case,bool OwnerOK,bool RemoteOK,const TArray<FVector_NetQuantizeNormal>& Predicted)
{
    if(!ShotgunWire::Enabled()||Case!=Expected||Finished!=Case)return;
    auto* AuditPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();
    const auto* Item=PS&&PS->ShadowModel?PS->ShadowModel->Equipped():nullptr;
    const int32 Count=Case==2?1:8;
    bool Directions=AuditPawn&&AuditPawn->Ballistics->Rounds.Num()==Count&&Predicted.Num()==Count;float Damage=0;
    if(AuditPawn)for(int32 I=0;I<AuditPawn->Ballistics->Rounds.Num();++I)
    {
        const auto& R=AuditPawn->Ballistics->Rounds[I];Damage+=R.Damage;
        // NetQuantizeNormal quantizes components; normalize before comparing
        // the angle so quantization length error is not counted as divergence.
        Directions&=Predicted.IsValidIndex(I)&&FVector::DotProduct(R.Direction,FVector(Predicted[I]).GetSafeNormal())>.99999&&!R.bCosmeticOnly;
    }
    const bool Ammo=Item&&Item->Magazine==(ShotgunWire::Tube(Case)?9:6);
    const bool Budget=AuditPawn&&FMath::IsNearlyEqual(Damage,AuditPawn->DamagePerShot,.01f);
    const bool Recipe=AuditPawn&&(ShotgunWire::M870()?(!AuditPawn->HasShotgunDuckbill()&&FMath::IsNearlyEqual(AuditPawn->EffectiveFireInterval(),Case>=3?.675:.9,1.e-5)):AuditPawn->HasShotgunDuckbill()==(Case!=3&&Case!=4));
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Case);Row->SetBoolField(TEXT("prediction_matches_authority"),Directions);
    Row->SetBoolField(TEXT("ammo_once_despite_duplicate_rpc"),Ammo);Row->SetBoolField(TEXT("damage_budget"),Budget);Row->SetBoolField(TEXT("committed_recipe"),Recipe);
    Row->SetBoolField(TEXT("owner_ok"),OwnerOK);Row->SetBoolField(TEXT("remote_ok"),RemoteOK);Results.Add(MakeShared<FJsonValueObject>(Row));
    Row->SetNumberField(TEXT("authority_rounds"),AuditPawn?AuditPawn->Ballistics->ActiveCount():-1);Row->SetNumberField(TEXT("authority_magazine"),Item?Item->Magazine:-1);
    Row->SetNumberField(TEXT("processed_sequence"),PS?PS->Super90ProcessedSequence:0);
    bAllPassed&=Directions&&Ammo&&Budget&&Recipe&&OwnerOK&&RemoteOK;++Finished;
}
void AShotgunWireAuditController::ClientFinish_Implementation(bool Passed)
{if(ShotgunWire::Enabled()){bAllPassed&=Passed;ShotgunWire::Save(Results,bAllPassed,TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}}
AShotgunWireAuditGameMode::AShotgunWireAuditGameMode()
{PlayerControllerClass=AShotgunWireAuditController::StaticClass();PlayerStateClass=AShotgunWireAuditPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void AShotgunWireAuditGameMode::BeginPlay()
{Super::BeginPlay();if(ShotgunWire::Enabled())UE_LOG(LogTemp,Display,TEXT("SHOTGUN_WIRE_HOST_READY"));}
void AShotgunWireAuditGameMode::PostLogin(APlayerController* Player)
{Super::PostLogin(Player);if(ShotgunWire::Enabled()&&!Player->IsLocalController()){Guest=Cast<AShotgunWireAuditController>(Player);Joined=GetWorld()->GetRealTimeSeconds();}}
void AShotgunWireAuditGameMode::Tick(float Delta)
{
    if(TickMealReceipt(Delta))return;
    if(TickPistolAmmo(Delta))return;
    if(TickPistolPresentation(Delta))return;
    if(TickSparrowPresentation(Delta))return;
    if(TickM870Presentation(Delta))return;
    Super::Tick(Delta);if(!ShotgunWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Pawn||!PS||!Host||!Host->IsAudit())return;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())HostPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    if(!HostPawn)return;
    if(Guest->Finished>=6||Now-Joined>220.)
    {
        const bool Passed=Guest->Finished==6&&Guest->bAllPassed;ShotgunWire::Save(Guest->Results,Passed,TEXT("listen_host"));
        Guest->ClientFinish(Passed);ExitAt=Now+3.;return;
    }
    if(Prepared!=Guest->Finished)
    {
        Prepared=Guest->Finished;Weapon=FGuid::NewGuid().ToString();Guest->Expected=Prepared;
        const auto Seed=ShotgunWire::Seed(Host,Weapon,Prepared);
        if(!PS->ShadowModel)PS->ShadowModel=Host->CreateShadowModel(Seed);else PS->ShadowModel->Current=Seed;
        PS->ShadowModel->CurrentPawn=Pawn;Pawn->NetShadowProfile=PS->ShadowModel;Pawn->ApplyColdSteelProfile(PS->ShadowModel);
        PS->Super90NextFireTime=0;PS->Super90Reload.Active=false;PS->Super90Revision=0;PS->Super90PouchDelta={0,0,0};
        Host->Current=ShotgunWire::Seed(Host,TEXT("ShotgunAuditHost"),ShotgunWire::M870()?3:1);Host->CurrentPawn=HostPawn;HostPawn->ApplyColdSteelProfile(Host);
        for(auto* C:{Pawn,HostPawn.Get()})
        {
            C->SetActorTickEnabled(false);C->GetCharacterMovement()->SetComponentTickEnabled(false);C->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            // The empty map has no floor. ServerMove can still simulate even
            // with component ticking disabled while client setup is in flight.
            C->GetCharacterMovement()->DisableMovement();C->GetCharacterMovement()->StopMovementImmediately();
            C->Ballistics->SetComponentTickEnabled(false);C->Ballistics->PrimaryComponentTick.bCanEverTick=false;C->Ballistics->Rounds.Reset();C->CurrentSpread=C->MoveSpread=C->AirSpread=0;
            C->WeaponState=EAKMWeaponState::Idle;C->bIsSprinting=false;C->NextAllowedShotTime=0;C->SprintFireUnlockTime=0;
            if(auto* Body=C->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RefreshEquipment();
        }
        Pawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);Guest->SetControlRotation(FRotator::ZeroRotator);
        HostPawn->SetActorLocationAndRotation(FVector(0,1000,500),FRotator::ZeroRotator);Pawn->ForceNetUpdate();HostPawn->ForceNetUpdate();LastSetup=-10;
    }
    if(Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,HostPawn);}
}
