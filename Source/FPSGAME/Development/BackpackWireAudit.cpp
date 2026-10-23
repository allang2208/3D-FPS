#include "BackpackWireAudit.h"
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
#include "../Characters/FPSBackpackMotionComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

namespace BackpackWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("BackpackWireAudit"));}
const TCHAR* Names[]={TEXT("pathfinder"),TEXT("expedition"),TEXT("sweater"),TEXT("robe")};
const int32 Slots[]={14,14,7,7};
const int32 Masks[]={5,10,4,9,6,0,9};
const int32 HostMasks[]={10,5,9,6,0,10,5};
FString Id(int32 I){return FString(TEXT("BackpackAudit_"))+Names[I];}
FString Definition(int32 I)
{
    const TCHAR* Values[]={TEXT("ue_pathfinder_backpack"),TEXT("ue_expedition_backpack"),TEXT("ue_field_sweater"),TEXT("ue_blue_mage_robe")};return Values[I];
}
TSharedPtr<FJsonObject> Config()
{
    static TSharedPtr<FJsonObject> Data;
    if(!Data){FString Text;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")));FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);}
    return Data;
}
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
        for(int32 I=0;I<4;++I)
        {
            auto Item=Model->CreateItem(Definition(I));Item.InstanceId=Id(I);Item.Place=0;Item.Cell=INDEX_NONE;
            for(int32 Cell=0;Cell<72;++Cell)if(ColdSteelInventory::Fits(State.Items,Item,Cell)){Item.Cell=Cell;break;}
            if(Item.Cell==INDEX_NONE)return false;State.Items.Add(Item);
        }
        FString Reason;if(!ColdSteelInventory::Validate(State,Reason)){UE_LOG(LogTemp,Error,TEXT("BACKPACK_WIRE_SEED_REJECTED %s"),*Reason);return false;}
        Model->AdoptNetMirror(State);
    }
    Model->AttachPawn(Pawn);Model->NotifyChanged();return true;
}
int32 InventoryMask(UColdSteelStatusModel* Model)
{
    if(!Model)return -1;
    int32 Mask=0;for(int32 I=0;I<4;++I)if(const auto* Item=Model->Equipped(Slots[I]);Item&&Item->Definition==Definition(I))Mask|=1<<I;
    const int32 Rows=(Mask&1)?7:(Mask&2)?6:4;
    const FIntPoint Grid=(Mask&1)?FIntPoint(12,6):(Mask&2)?FIntPoint(8,6):FIntPoint::ZeroValue;
    return ColdSteelInventory::BagRows(Model->Items())==Rows&&ColdSteelInventory::CompartmentGrid(Model->Items())==Grid?Mask:-1;
}
bool Wear(UColdSteelStatusModel* Model,int32 Mask)
{
    bool OK=true;
    // Unequip first: two items share each tested slot. Each MoveItem still
    // travels through the production inventory request/authority path.
    for(int32 I=0;I<4;++I)if(!(Mask&(1<<I)))
        if(const auto* Item=Model->FindItem(Id(I));Item&&Item->Place==1)OK=Model->MoveItem(Id(I),0,-1)&&OK;
    for(int32 I=0;I<4;++I)if(Mask&(1<<I))
        if(const auto* Item=Model->FindItem(Id(I));Item&&Item->Place!=1)OK=Model->MoveItem(Id(I),1,Slots[I])&&OK;
    return OK;
}
int32 ReplicatedMask(UFPSPlayerBodyComponent* Body)
{
    const auto* Property=FindFProperty<FArrayProperty>(UFPSPlayerBodyComponent::StaticClass(),TEXT("ReplicatedOutfit"));
    if(!Body||!Property)return -1;
    const auto& Values=*Property->ContainerPtrToValuePtr<TArray<FFPSBodyOutfitSlot>>(Body);int32 Mask=0;
    for(const auto& V:Values)for(int32 I=0;I<4;++I)if(V.Slot==Slots[I]&&V.Definition==FName(*Definition(I)))Mask|=1<<I;
    return Mask;
}
bool Presentation(AFPSGAMECharacter* Pawn,int32 Mask,FString& Details)
{
    if(!Pawn)return false;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();auto* Source=Body?Body->GetBodyMesh():nullptr;
    if(!Source||!Source->GetSkeletalMeshAsset())return false;
    const bool HasPack=(Mask&3)!=0,Split=(Mask&1)!=0;
    FString Expected,ExpectedRigid;FVector RigidReference=FVector::ZeroVector;
    if(HasPack)
    {
        const auto O=Config()->GetObjectField(TEXT("outfits"))->GetObjectField(Definition(Split?0:1));
        Expected=O->GetStringField(TEXT("world_mesh"));
        const FString Shirt=(Mask&4)?Definition(2):(Mask&8)?Definition(3):FString();
        if(!Shirt.IsEmpty())O->GetObjectField(TEXT("world_mesh_by_shirt"))->TryGetStringField(Shirt,Expected);
        if(Split)
        {
            const auto R=O->GetObjectField(TEXT("rigid_pack"));ExpectedRigid=R->GetStringField(TEXT("mesh"));
            const auto& V=Shirt.IsEmpty()?R->GetArrayField(TEXT("location")):R->GetObjectField(TEXT("location_by_shirt"))->GetArrayField(Shirt);
            RigidReference=FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
        }
    }
    int32 Skinned=0,Rigids=0;bool Binding=true,CorrectAsset=true;USkeletalMeshComponent* Strap=nullptr;UStaticMeshComponent* Rigid=nullptr;
    TArray<USkeletalMeshComponent*> Meshes;Pawn->GetComponents(Meshes);
    for(auto* Part:Meshes)if(Part!=Source&&Part->GetSkeletalMeshAsset()&&Part->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("Backpack")))
    {
        ++Skinned;Strap=Part;CorrectAsset&=Part->GetSkeletalMeshAsset()->GetPathName()==Expected;
        Binding&=Part->LeaderPoseComponent.Get()==Source&&Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOnlyOwnerSee;
    }
    TArray<UStaticMeshComponent*> Statics;Pawn->GetComponents(Statics);
    for(auto* Part:Statics)if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName().Contains(TEXT("Backpack")))
    {
        ++Rigids;Rigid=Part;CorrectAsset&=Part->GetStaticMesh()->GetPathName()==ExpectedRigid;
        Binding&=Part->GetAttachParent()==Source&&Part->GetAttachSocketName()==TEXT("spine_03")&&Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOnlyOwnerSee;
    }
    auto* Motion=Pawn->FindComponentByClass<UFPSBackpackMotionComponent>();
    bool Dynamic=HasPack?Motion&&Motion->IsComponentTickEnabled()&&Strap&&Strap->GetCustomPrimitiveData().Data.Num()==30:!Motion||!Motion->IsComponentTickEnabled();
    double SeamError=0.;
    if(Split&&Rigid&&Strap&&Strap->GetCustomPrimitiveData().Data.Num()==30)
    {
        const auto& Ref=Source->GetSkeletalMeshAsset()->GetRefSkeleton();const int32 Spine=Ref.FindBoneIndex(TEXT("spine_03"));
        FTransform Bind=Ref.GetRefBonePose()[Spine];for(int32 P=Ref.GetParentIndex(Spine);P!=INDEX_NONE;P=Ref.GetParentIndex(P))Bind=Bind*Ref.GetRefBonePose()[P];
        const FVector At=(Bind.Inverse()*Source->GetBoneTransform(Spine)).TransformPosition(RigidReference);
        const auto& D=Strap->GetCustomPrimitiveData().Data;
        const FVector Q=At-FVector(D[0],D[1],D[2]);
        const FVector Shift(FVector::DotProduct(FVector(D[3],D[4],D[5]),Q)+D[12],FVector::DotProduct(FVector(D[6],D[7],D[8]),Q)+D[13],FVector::DotProduct(FVector(D[9],D[10],D[11]),Q)+D[14]);
        SeamError=FVector::Dist(At+Shift,Rigid->GetComponentLocation());Dynamic&=SeamError<.25;
    }
    Details=FString::Printf(TEXT("mask=%d replicas=%d skinned=%d rigid=%d asset=%d bind=%d motion=%d seam_cm=%.5f"),Mask,ReplicatedMask(Body),Skinned,Rigids,CorrectAsset,Binding,Dynamic,SeamError);
    return Skinned==(HasPack?1:0)&&Rigids==(Split?1:0)&&CorrectAsset&&Binding&&Dynamic;
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role)
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("passed"),Pass);Root->SetStringField(TEXT("role"),Role);Root->SetArrayField(TEXT("cases"),Rows);Root->SetBoolField(TEXT("rendered"),false);
    FString Json,Path;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("BackpackWireOutput="),Path)){IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_RESULT %s"),*Json);
}
}

void ABackpackWireAuditController::ClientCase_Implementation(int32 Phase,AFPSGAMECharacter* Subject)
{
    if(!BackpackWire::Enabled()||HasAuthority()||Phase==Current||Phase<0||Phase>=UE_ARRAY_COUNT(BackpackWire::Masks))return;
    auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!BackpackWire::Seed(Model,ControlledPawn))return;
    BackpackWire::Freeze(ControlledPawn,false);Host=Subject;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();LastSent=-10;
    MovesOK=BackpackWire::Wear(Model,BackpackWire::Masks[Phase]);
    if(Phase==4)MovesOK=BackpackWire::Wear(Model,0)&&BackpackWire::Wear(Model,BackpackWire::Masks[Phase])&&MovesOK;
}
void ABackpackWireAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!BackpackWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Current<0||Now-Started<3||Now-LastSent<1)return;
    FString OwnerDetails,Remote;const int32 Mask=BackpackWire::Masks[Current];auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const bool OwnerOK=BackpackWire::Presentation(ControlledPawn,Mask,OwnerDetails),RemoteOK=BackpackWire::Presentation(Host,BackpackWire::HostMasks[Current],Remote);
    const bool OK=OwnerOK&&RemoteOK&&BackpackWire::InventoryMask(Model)==Mask;
    if(OK||Now-Started>45.){ServerResult(Current,OK&&MovesOK,OwnerDetails+TEXT(" | remote: ")+Remote);LastSent=Now;}
}
void ABackpackWireAuditController::ServerResult_Implementation(int32 Phase,bool ClientPassed,const FString& Details)
{
    if(!BackpackWire::Enabled()||Phase!=Finished||Phase>=UE_ARRAY_COUNT(BackpackWire::Masks))return;
    auto* ControlledPawn=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();const int32 Mask=BackpackWire::Masks[Phase];FString Remote;
    const bool Inventory=PS&&BackpackWire::InventoryMask(PS->GetShadowModel())==Mask;
    const bool Replication=ControlledPawn&&BackpackWire::ReplicatedMask(ControlledPawn->FindComponentByClass<UFPSPlayerBodyComponent>())==Mask;
    const bool Visible=BackpackWire::Presentation(ControlledPawn,Mask,Remote);
    if(ClientPassed&&(!Inventory||!Replication||!Visible))return;
    const bool Pass=ClientPassed&&Inventory&&Replication&&Visible;auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);Row->SetBoolField(TEXT("passed"),Pass);Row->SetBoolField(TEXT("authority_inventory"),Inventory);Row->SetBoolField(TEXT("replicated_slots"),Replication);Row->SetStringField(TEXT("client"),Details);Row->SetStringField(TEXT("host_observer"),Remote);Results.Add(MakeShared<FJsonValueObject>(Row));AllPassed&=Pass;++Finished;
    UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_CASE phase=%d pass=%d %s"),Phase,Pass,*Remote);
}
void ABackpackWireAuditController::ClientFinish_Implementation(bool Passed)
{if(BackpackWire::Enabled()){BackpackWire::Save(Results,Passed,TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}}
ABackpackWireAuditGameMode::ABackpackWireAuditGameMode()
{PlayerControllerClass=ABackpackWireAuditController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void ABackpackWireAuditGameMode::PostLogin(APlayerController* Player)
{Super::PostLogin(Player);if(BackpackWire::Enabled()&&!Player->IsLocalController()){Guest=Cast<ABackpackWireAuditController>(Player);Joined=GetWorld()->GetRealTimeSeconds();Prepared=INDEX_NONE;}}
void ABackpackWireAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!BackpackWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Host)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)if(It->IsValid()&&It->Get()->IsLocalController())Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Model)return;
    if(!HostSeeded){if(!BackpackWire::Seed(Model,Host))return;BackpackWire::Freeze(Host,true);HostSeeded=true;UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_HOST_READY"));}
    if(!Guest)return;
    if(Guest->Finished>=UE_ARRAY_COUNT(BackpackWire::Masks)||Now-Joined>360.)
    {
        Passed&=Guest->AllPassed&&Guest->Finished==UE_ARRAY_COUNT(BackpackWire::Masks);History.Append(Guest->Results);Guest->ClientFinish(Passed);++Connections;
        if(Connections==1){Guest=nullptr;Prepared=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_REJOIN_READY"));return;}
        BackpackWire::Save(History,Passed,TEXT("listen_host"));ExitAt=Now+3.;return;
    }
    if(Prepared!=Guest->Finished)
    {
        if(Guest->Finished==3)
        {
            // Recreate the controlled pawn through the normal spawn path;
            // keep PlayerState and its server-owned equipment/profile alive.
            APawn* Previous=Guest->GetPawn();Guest->UnPossess();if(Previous)Previous->Destroy();
            RestartPlayer(Guest);
            UE_LOG(LogTemp,Display,TEXT("BACKPACK_WIRE_RESPAWN connection=%d"),Connections);
        }
        Prepared=Guest->Finished;Passed=BackpackWire::Wear(Model,BackpackWire::HostMasks[Prepared])&&Passed;
        if(Prepared==4)Passed=BackpackWire::Wear(Model,0)&&BackpackWire::Wear(Model,BackpackWire::HostMasks[Prepared])&&Passed;
        LastSetup=-10;
    }
    if(auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn()))BackpackWire::Freeze(Pawn,false);
    if(Now-LastSetup>2){LastSetup=Now;Guest->ClientCase(Prepared,Host);}
}
