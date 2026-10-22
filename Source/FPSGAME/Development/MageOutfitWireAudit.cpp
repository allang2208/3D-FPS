#include "MageOutfitWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSHeadEquipmentMeshComponent.h"
#include "../Characters/FPSOutfitRobeAnimInstance.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "LeatherBootsWireChecks.h"

namespace MageOutfitWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("MageOutfitWireAudit"));}
const TCHAR* Names[]={TEXT("hat"),TEXT("robe"),TEXT("gloves"),TEXT("pants"),TEXT("boots")};
const int32 Slots[]={1,7,3,15,13};
const int32 Masks[]={31,30,29,15,31,0,31};
// Divergent outfits catch accidental use of the host's singleton for a guest.
const int32 HostMasks[]={31,15,0,29,30,31,31};
FString Id(int32 I){return FString(TEXT("MageAudit_"))+Names[I];}
FString Definition(int32 I){return LeatherBootsWire::Enabled()&&I>=3?(I==3?TEXT("ue_leather_pants"):TEXT("ue_leather_boots")):FString(TEXT("ue_blue_mage_"))+Names[I];}
void Freeze(AFPSGAMECharacter* Pawn,bool Host)
{
    if(!Pawn)return;
    Pawn->SetActorLocation(FVector(0,Host?1000:0,500));
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
bool Seed(UColdSteelStatusModel* Model,AFPSGAMECharacter* Pawn)
{
    if(!Model||!Model->IsAudit()||!Pawn)return false;
    if(!Model->FindItem(Id(0)))
    {
        auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
        for(int32 I=0;I<5;++I){auto Item=Model->CreateItem(Definition(I));Item.InstanceId=Id(I);Item.Place=1;Item.Cell=Slots[I];State.Items.Add(Item);}
        if(LeatherBootsWire::Enabled()){auto Item=Model->CreateItem(TEXT("ue_field_sweater"));Item.InstanceId=TEXT("LeatherAudit_Shirt");Item.Place=0;Item.Cell=0;State.Items.Add(Item);}
        FString Reason;if(!ColdSteelInventory::Validate(State,Reason)){UE_LOG(LogTemp,Error,TEXT("MAGE_WIRE_SEED_REJECTED %s"),*Reason);return false;}
        Model->AdoptNetMirror(State);
    }
    Model->AttachPawn(Pawn);Model->NotifyChanged();return true;
}
int32 InventoryMask(UColdSteelStatusModel* Model)
{
    int32 Mask=0;if(!Model)return -1;
    for(int32 I=0;I<5;++I)if(const auto* Item=Model->Equipped(Slots[I]);Item&&Item->Definition==Definition(I))Mask|=1<<I;
    return Mask;
}
bool Wear(UColdSteelStatusModel* Model,int32 Mask)
{
    bool OK=true;
    const bool FieldShirt=LeatherBootsWire::Enabled()&&Mask!=0&&!(Mask&2);
    if(LeatherBootsWire::Enabled()&&!FieldShirt)if(const auto* Shirt=Model->FindItem(TEXT("LeatherAudit_Shirt"));Shirt&&Shirt->Place==1)OK=Model->MoveItem(Shirt->InstanceId,0,-1)&&OK;
    for(int32 I=0;I<5;++I)
    {
        const auto* Item=Model->FindItem(Id(I));if(!Item){OK=false;continue;}
        const bool Wearing=(Mask&(1<<I))!=0;
        if((Item->Place==1)!=Wearing)OK=Model->MoveItem(Id(I),Wearing?1:0,Wearing?Slots[I]:-1)&&OK;
    }
    if(FieldShirt)if(const auto* Shirt=Model->FindItem(TEXT("LeatherAudit_Shirt"));Shirt&&Shirt->Place!=1)OK=Model->MoveItem(Shirt->InstanceId,1,7)&&OK;
    return OK&&InventoryMask(Model)==Mask;
}
int32 ReplicatedMask(UFPSPlayerBodyComponent* Body)
{
    const auto* Property=FindFProperty<FArrayProperty>(UFPSPlayerBodyComponent::StaticClass(),TEXT("ReplicatedOutfit"));
    if(!Body||!Property)return -1;
    const auto& Values=*Property->ContainerPtrToValuePtr<TArray<FFPSBodyOutfitSlot>>(Body);int32 Mask=0;
    for(const auto& V:Values)for(int32 I=0;I<5;++I)if(V.Slot==Slots[I]&&V.Definition==FName(*Definition(I)))Mask|=1<<I;
    return Mask;
}
bool Presentation(AFPSGAMECharacter* Pawn,int32 Mask,FString& Details)
{
    if(!Pawn)return false;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();auto* Source=Body?Body->GetBodyMesh():nullptr;if(!Source)return false;
    int32 Counts[5]={},Shirts=0;bool Binding=true,PantsFit=true,Cloth=true;TArray<USkinnedMeshComponent*> Meshes;Pawn->GetComponents(Meshes);
    for(auto* Part:Meshes)
    {
        if(!Part||!Part->IsVisible()||Part->bHiddenInGame||Part->bOnlyOwnerSee||!Part->GetSkinnedAsset())continue;
        const FString Path=Part->GetSkinnedAsset()->GetPathName();
        if(LeatherBootsWire::Enabled()&&LeatherBootsWire::IsShirt(Path)){++Shirts;PantsFit&=Path==LeatherBootsWire::Shirt(Mask);Binding&=Part->LeaderPoseComponent.Get()==Source;}
        for(int32 I=0;I<5;++I)
        {
            const FString Token=I==0?TEXT("BlueMageHat"):I==1?TEXT("BlueMageRobe"):I==2?TEXT("BlueMageGloves"):I==3?TEXT("BlueMagePants"):TEXT("BlueMageBoots");
            // Robe-owned calf/base replacements also contain BlueMageRobe in
            // their package names; only the drape component is the actual robe.
            const bool Matches=LeatherBootsWire::Enabled()&&I>=3?(I==3?LeatherBootsWire::IsPants(Path):LeatherBootsWire::IsBoots(Path)):(I==1?Part->ComponentHasTag(TEXT("OutfitRobeDrape")):Path.Contains(Token));
            if(!Matches)continue;
            ++Counts[I];
            if(I==0)Binding&=Part->GetAttachParent()==Source&&Part->GetAttachSocketName()==TEXT("head");
            else if(I==1)
            {
                const auto* Mesh=Cast<USkeletalMeshComponent>(Part);Cloth&=Mesh&&Mesh->GetAnimInstance()&&Mesh->GetAnimInstance()->IsA<UFPSOutfitRobeAnimInstance>()&&!Mesh->LeaderPoseComponent.IsValid();
            }
            else Binding&=Part->LeaderPoseComponent.Get()==Source;
            if(LeatherBootsWire::Enabled()&&I>=3)PantsFit&=Path==(I==3?LeatherBootsWire::Pants(Mask):LeatherBootsWire::Boots(Mask));
            else if(I==3)PantsFit&=Path.Contains(TEXT("RobeInner"))==bool(Mask&2)&&Path.Contains(TEXT("HighBootsFit"))==bool(Mask&16);
        }
    }
    bool CountsOK=true;for(int32 I=0;I<5;++I)CountsOK&=Counts[I]==((Mask&(1<<I))?1:0);
    if(LeatherBootsWire::Enabled())CountsOK&=Shirts==(LeatherBootsWire::Shirt(Mask).IsEmpty()?0:1);
    Details=FString::Printf(TEXT("mask=%d replicas=%d counts=%d,%d,%d,%d,%d shirt=%d bind=%d fit=%d cloth=%d"),Mask,ReplicatedMask(Body),Counts[0],Counts[1],Counts[2],Counts[3],Counts[4],Shirts,Binding,PantsFit,Cloth);
    return CountsOK&&Binding&&PantsFit&&Cloth;
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role)
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("passed"),Pass);Root->SetStringField(TEXT("role"),Role);Root->SetArrayField(TEXT("cases"),Rows);Root->SetBoolField(TEXT("rendered"),false);
    FString Json,Path;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("MageOutfitWireOutput="),Path)){IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("MAGE_WIRE_RESULT %s"),*Json);
}
}

void AMageOutfitWireAuditController::ClientCase_Implementation(int32 Phase,AFPSGAMECharacter* Subject)
{
    if(!MageOutfitWire::Enabled()||HasAuthority()||Phase==Current||Phase<0||Phase>=UE_ARRAY_COUNT(MageOutfitWire::Masks))return;
    auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!MageOutfitWire::Seed(Model,ControlledPawn))return;
    MageOutfitWire::Freeze(ControlledPawn,false);Host=Subject;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();LastSent=-10;
    MovesOK=MageOutfitWire::Wear(Model,MageOutfitWire::Masks[Phase]);
    if(Phase==4)MovesOK=MageOutfitWire::Wear(Model,0)&&MageOutfitWire::Wear(Model,31)&&MovesOK;
}
void AMageOutfitWireAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!MageOutfitWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Current<0||Now-Started<3||Now-LastSent<1)return;
    FString OwnerDetails,Remote;const int32 Mask=MageOutfitWire::Masks[Current];auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());
    FString DropDetails;const bool DropOK=LeatherBootsWire::LegacyDrop(GetWorld(),DropDetails);
    const bool OwnerOK=MageOutfitWire::Presentation(ControlledPawn,Mask,OwnerDetails),RemoteOK=MageOutfitWire::Presentation(Host,MageOutfitWire::HostMasks[Current],Remote);
    const bool OK=OwnerOK&&RemoteOK&&DropOK;
    if(OK||Now-Started>45.){ServerResult(Current,OK&&MovesOK,OwnerDetails+TEXT(" | remote: ")+Remote+TEXT(" | ")+DropDetails);LastSent=Now;}
}
void AMageOutfitWireAuditController::ServerResult_Implementation(int32 Phase,bool ClientPassed,const FString& Details)
{
    if(!MageOutfitWire::Enabled()||Phase!=Finished||Phase>=UE_ARRAY_COUNT(MageOutfitWire::Masks))return;
    auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();const int32 Mask=MageOutfitWire::Masks[Phase];FString Remote;
    const bool Inventory=PS&&MageOutfitWire::InventoryMask(PS->GetShadowModel())==Mask;
    const bool Replication=ControlledPawn&&MageOutfitWire::ReplicatedMask(ControlledPawn->FindComponentByClass<UFPSPlayerBodyComponent>())==Mask;
    const bool Visible=MageOutfitWire::Presentation(ControlledPawn,Mask,Remote);
    if(ClientPassed&&(!Inventory||!Replication||!Visible))return;
    const bool Pass=ClientPassed&&Inventory&&Replication&&Visible;auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);Row->SetBoolField(TEXT("passed"),Pass);Row->SetBoolField(TEXT("authority_inventory"),Inventory);Row->SetBoolField(TEXT("replicated_slots"),Replication);Row->SetStringField(TEXT("client"),Details);Row->SetStringField(TEXT("host_observer"),Remote);Results.Add(MakeShared<FJsonValueObject>(Row));AllPassed&=Pass;++Finished;
    UE_LOG(LogTemp,Display,TEXT("MAGE_WIRE_CASE phase=%d pass=%d %s"),Phase,Pass,*Remote);
}
void AMageOutfitWireAuditController::ClientFinish_Implementation(bool Passed)
{if(MageOutfitWire::Enabled()){MageOutfitWire::Save(Results,Passed,TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}}
AMageOutfitWireAuditGameMode::AMageOutfitWireAuditGameMode()
{PlayerControllerClass=AMageOutfitWireAuditController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void AMageOutfitWireAuditGameMode::PostLogin(APlayerController* Player)
{Super::PostLogin(Player);if(MageOutfitWire::Enabled()&&!Player->IsLocalController()){Guest=Cast<AMageOutfitWireAuditController>(Player);Joined=GetWorld()->GetRealTimeSeconds();Prepared=INDEX_NONE;}}
void AMageOutfitWireAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!MageOutfitWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Host)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)if(It->IsValid()&&It->Get()->IsLocalController())Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Model)return;
    if(!HostSeeded){if(!MageOutfitWire::Seed(Model,Host))return;MageOutfitWire::Freeze(Host,true);LeatherBootsWire::SpawnLegacyDrop(Model,GetWorld());HostSeeded=true;UE_LOG(LogTemp,Display,TEXT("MAGE_WIRE_HOST_READY"));}
    if(!Guest)return;
    if(Guest->Finished>=UE_ARRAY_COUNT(MageOutfitWire::Masks)||Now-Joined>360.)
    {
        Passed&=Guest->AllPassed&&Guest->Finished==UE_ARRAY_COUNT(MageOutfitWire::Masks);History.Append(Guest->Results);Guest->ClientFinish(Passed);++Connections;
        if(Connections==1){Guest=nullptr;Prepared=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("MAGE_WIRE_REJOIN_READY"));return;}
        MageOutfitWire::Save(History,Passed,TEXT("listen_host"));ExitAt=Now+3.;return;
    }
    if(Prepared!=Guest->Finished)
    {
        Prepared=Guest->Finished;Passed=MageOutfitWire::Wear(Model,MageOutfitWire::HostMasks[Prepared])&&Passed;
        if(Prepared==4)Passed=MageOutfitWire::Wear(Model,0)&&MageOutfitWire::Wear(Model,MageOutfitWire::HostMasks[Prepared])&&Passed;
        LastSetup=-10;
    }
    if(auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn()))MageOutfitWire::Freeze(Pawn,false);
    if(Now-LastSetup>2){LastSetup=Now;Guest->ClientCase(Prepared,Host);}
}
