#include "StaffGunsmithAuditCommandlet.h"
#include "StaffCatalog.h"
#include "StaffAssembly.h"
#include "../GunsmithSystem.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 UStaffGunsmithAuditCommandlet::Main(const FString& Params)
{
    FString Report;int32 Checks=0,Failures=0;
    auto Note=[&](const FString& Line){Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("STAFF_GUNSMITH %s"),*Line);};
    auto Check=[&](bool OK,const FString& Name){++Checks;if(!OK)++Failures;Note((OK?TEXT("PASS "):TEXT("FAIL "))+Name);return OK;};
    // Override any caller profile before the subsystem can load or publish a save.
    const FString OriginalCommand=FCommandLine::Get();
    const FString ProfileName=TEXT("StaffGunsmithAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("StaffGunsmithAudit -ColdSteelProfile=")+ProfileName));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("StaffGunsmithAuditWorld"));
    auto* World=GI->GetWorld();auto* P=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!P||!G||!World)return 2;
    Check(P->IsAudit()&&P->ProfileSlot()==TEXT("ColdSteel_")+ProfileName,TEXT("isolated profile selected"));
    auto State=P->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    auto Staff=P->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;State.ActiveWeaponSlot=6;State.Items.Add(Staff);
    auto Other=P->CreateItem(TEXT("ue_apprentice_staff"));Other.Place=1;Other.Cell=9;State.Items.Add(Other);
    Check(P->CommitState(State),TEXT("seed two independent staff instances: ")+P->ResultMessage());
    Check(G->Begin(Staff.InstanceId),TEXT("open equipped staff"));
    const auto Catalog=ColdSteelStaff::Catalog();FGunsmithParts Expected;
    for(const auto& V:Catalog->GetArrayField(TEXT("columns")))
    {
        const auto C=V->AsObject();const FString Slot=C->GetStringField(TEXT("key"));
        const FString Id=C->GetArrayField(TEXT("options"))[0]->AsObject()->GetStringField(TEXT("id"));
        Expected.Add(Slot,Id);Check(G->Select(Slot,Id),TEXT("select ")+Slot);
    }
    Check(G->Pending()==6&&ColdSteelStaff::Installed(*P->Equipped()).IsEmpty(),TEXT("six previews do not mutate installed staff"));
    FString Reason;Check(G->CanApply(Reason),TEXT("zero materials and zero tickets can apply"));
    P->AuditFailNextSave=true;
    Check(!G->Apply()&&ColdSteelStaff::Installed(*P->Equipped()).IsEmpty(),TEXT("save failure rolls back all six slots"));
    const bool Applied=G->Apply();Check(Applied,TEXT("apply all six slots through real save transaction: ")+G->Message());
    Check(ColdSteelStaff::Installed(*P->Equipped()).OrderIndependentCompareEqual(Expected)&&P->Snapshot().Items.Num()==2,TEXT("all six slots committed without inventory cost"));
    Check(ColdSteelStaff::Installed(*P->FindItem(Other.InstanceId)).IsEmpty(),TEXT("other staff remains factory"));
    G->Close();Check(P->ReloadProfile(),TEXT("reload saved profile"));
    Check(ColdSteelStaff::Installed(*P->Equipped()).OrderIndependentCompareEqual(Expected),TEXT("all six slots survive reload"));
    State=P->Snapshot();State.ActiveWeaponSlot=9;Check(P->CommitState(State)&&P->Equipped()->InstanceId==Other.InstanceId,TEXT("equip other staff"));
    State=P->Snapshot();State.ActiveWeaponSlot=6;Check(P->CommitState(State)&&ColdSteelStaff::Installed(*P->Equipped()).OrderIndependentCompareEqual(Expected),TEXT("re-equipping restores installed six-slot recipe"));
    const auto SavedStaff=*P->Equipped();const auto Resolved=ColdSteelStaff::Resolve(SavedStaff);
    TSharedPtr<FJsonObject> SavedData,ResolvedData;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(SavedStaff.Data),SavedData);
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Resolved.Data),ResolvedData);
    FString EffectsA,EffectsB;
    FJsonSerializer::Serialize(SavedData->GetObjectField(TEXT("_craftEffects")).ToSharedRef(),TJsonWriterFactory<>::Create(&EffectsA));
    FJsonSerializer::Serialize(ResolvedData->GetObjectField(TEXT("_craftEffects")).ToSharedRef(),TJsonWriterFactory<>::Create(&EffectsB));
    Check(EffectsA==EffectsB&&!SavedData->GetObjectField(TEXT("_craftEffects"))->Values.IsEmpty(),TEXT("saved gameplay effects match installed parts"));
    TArray<FSoftObjectPath> Paths;ColdSteelStaffAssembly::Gather(SavedStaff,Paths);for(const auto& Path:Paths)Path.TryLoad();
    auto* Actor=World->SpawnActor<AActor>();auto* Mesh=NewObject<UStaticMeshComponent>(Actor);Actor->SetRootComponent(Mesh);Mesh->RegisterComponent();
    Check(ColdSteelStaffAssembly::Apply(Mesh,SavedStaff),TEXT("build actual assembly from committed item"));
    for(const auto& V:Catalog->GetArrayField(TEXT("columns")))
    {
        const FString Slot=V->AsObject()->GetStringField(TEXT("key"));const FString Path=ColdSteelInventory::Text(SavedStaff,*(TEXT("staff_part_")+Slot+TEXT("_mesh")));
        bool Found=false;for(USceneComponent* Child:Mesh->GetAttachChildren())if(auto* Part=Cast<UStaticMeshComponent>(Child))Found|=Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName()==Path;
        Check(Found,TEXT("committed assembly mounts ")+Slot);
    }
    G->Begin(Staff.InstanceId);
    const FString Replacement=Catalog->GetArrayField(TEXT("columns"))[0]->AsObject()->GetArrayField(TEXT("options"))[1]->AsObject()->GetStringField(TEXT("id"));
    Check(G->Select(TEXT("head_crystal"),Replacement)&&G->Apply(),TEXT("replace head without tickets"));
    G->Select(TEXT("head_crystal"),TEXT("false"));Check(G->Apply(),TEXT("restore factory head without tickets"));
    Check(!ColdSteelStaff::Installed(*P->Equipped()).Contains(TEXT("head_crystal"))&&P->Snapshot().Items.Num()==2,TEXT("factory restoration saved without cost"));
    const auto Installed=ColdSteelStaff::Installed(*P->Equipped());G->Select(TEXT("head_crystal"),Replacement);G->Close();
    Check(ColdSteelStaff::Installed(*P->Equipped()).OrderIndependentCompareEqual(Installed),TEXT("closing preview does not install"));
    Note(FString::Printf(TEXT("RESULT checks=%d failures=%d profile=%s"),Checks,Failures,*P->ProfileSlot()));
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("StaffGunsmith");IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(Report,*(Directory/TEXT("transaction-report.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    Actor->Destroy();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*OriginalCommand);
    return Failures?1:0;
}
