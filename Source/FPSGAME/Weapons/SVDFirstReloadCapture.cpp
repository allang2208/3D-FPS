#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "FPSGunplayAnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace
{
TSharedRef<FJsonObject> TransformJSON(const FTransform& T)
{
    auto J=MakeShared<FJsonObject>();
    const FVector P=T.GetLocation(),S=T.GetScale3D();const FQuat Q=T.GetRotation();
    auto Values=[](std::initializer_list<double> Numbers){TArray<TSharedPtr<FJsonValue>> A;for(double N:Numbers)A.Add(MakeShared<FJsonValueNumber>(N));return A;};
    J->SetArrayField(TEXT("p"),Values({P.X,P.Y,P.Z}));J->SetArrayField(TEXT("q"),Values({Q.X,Q.Y,Q.Z,Q.W}));J->SetArrayField(TEXT("s"),Values({S.X,S.Y,S.Z}));return J;
}
void SaveJSON(const FString& Path,const TSharedRef<FJsonObject>& J)
{
    FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
struct FCapture
{
    FString Dir;float Age=0.f,Next=0.f;int32 Stage=0,Attempt=0,Frame=0;bool SawReload=false;
    FDelegateHandle Handle;
};
}

// Opt-in diagnostic only. A fresh isolated profile is required; no normal
// inventory, animation, render setting or asset is modified by this recorder.
void AFPSGAMECharacter::RunSVDFirstReloadCapture(float DeltaSeconds)
{
    static FCapture State;
    State.Age+=DeltaSeconds;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!Model->IsAudit()||!Model->ProfileSlot().Contains(TEXT("SVDFirstReload")))
    {UE_LOG(LogTemp,Error,TEXT("SVD_FIRST_RELOAD isolated profile required"));FPlatformMisc::RequestExitWithStatus(false,1);return;}
    if(State.Stage==0)
    {
        FString Label=Model->ProfileSlot();
        State.Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("SVDFirstReload")/Label);
        IFileManager::Get().MakeDirectory(*State.Dir,true);
        TWeakObjectPtr<AFPSGAMECharacter> Weak(this);
        State.Handle=FWorldDelegates::OnWorldPostActorTick.AddLambda([Weak](UWorld* World,ELevelTick,float)
        {
            auto* Self=Weak.Get();if(!Self||Self->GetWorld()!=World||State.Stage==5||!Self->AKMViewmodel)return;
            auto* Source=Self->AKMViewmodel.Get();auto J=MakeShared<FJsonObject>();
            const FString Stem=FString::Printf(TEXT("frame_%04d"),State.Frame++);
            J->SetNumberField(TEXT("age"),State.Age);J->SetNumberField(TEXT("attempt"),State.Attempt);
            J->SetBoolField(TEXT("reloading"),Self->IsReloading());J->SetNumberField(TEXT("ammo"),Self->MagazineAmmo);
            J->SetNumberField(TEXT("state"),int32(Self->WeaponState));J->SetNumberField(TEXT("elapsed"),Self->WeaponStateElapsed);
            J->SetObjectField(TEXT("camera"),TransformJSON(Self->FirstPersonCamera->GetComponentTransform()));
            J->SetObjectField(TEXT("source"),TransformJSON(Source->GetComponentTransform()));
            J->SetNumberField(TEXT("shader_platform"),World->Scene?int32(World->Scene->GetShaderPlatform()):-1);
            J->SetNumberField(TEXT("rhi_shader_platform"),int32(GMaxRHIShaderPlatform));
            if(auto* Anim=Self->GunplayAnimation.Get())
            {J->SetStringField(TEXT("clip"),GetPathNameSafe(Anim->ActionClip));J->SetNumberField(TEXT("time"),Anim->ActionTime);J->SetNumberField(TEXT("alpha"),Anim->ActionAlpha);}
            auto Bones=MakeShared<FJsonObject>();
            if(auto* Mesh=Source->GetSkeletalMeshAsset())
            {const auto& Ref=Mesh->GetRefSkeleton();const auto& Pose=Source->GetComponentSpaceTransforms();for(int32 I=0;I<Pose.Num();++I)Bones->SetObjectField(Ref.GetBoneName(I).ToString(),TransformJSON(Pose[I]));}
            J->SetObjectField(TEXT("bones"),Bones);
            TArray<USkeletalMeshComponent*> Components;Self->GetComponents(Components);TArray<TSharedPtr<FJsonValue>> Parts;
            for(auto* Part:Components)
            {
                if(!Part->GetSkeletalMeshAsset())continue;
                auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("name"),Part->GetName());P->SetStringField(TEXT("mesh"),Part->GetSkeletalMeshAsset()->GetPathName());
                P->SetBoolField(TEXT("visible"),Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOwnerNoSee);
                P->SetNumberField(TEXT("predicted_lod"),Part->GetPredictedLODLevel());
                P->SetObjectField(TEXT("transform"),TransformJSON(Part->GetComponentTransform()));
                TArray<TSharedPtr<FJsonValue>> Materials;
                for(int32 I=0;I<Part->GetNumMaterials();++I)
                {
                    auto M=MakeShared<FJsonObject>();M->SetStringField(TEXT("material"),GetPathNameSafe(Part->GetMaterial(I)));
                    M->SetBoolField(TEXT("shown"),Part->IsMaterialSectionShown(I,Part->GetPredictedLODLevel()));
                    const auto* Resource=Part->GetMaterial(I)&&World->Scene?Part->GetMaterial(I)->GetMaterialResource(World->Scene->GetShaderPlatform()):nullptr;
                    M->SetBoolField(TEXT("shader_ready"),Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete());
                    M->SetBoolField(TEXT("has_resource"),Resource!=nullptr);
                    M->SetBoolField(TEXT("has_shader_map"),Resource&&Resource->GetGameThreadShaderMap());
                    if(auto* MID=Cast<UMaterialInstanceDynamic>(Part->GetMaterial(I)))
                    {
                        float Enabled=0;MID->GetScalarParameterValue(TEXT("OutfitCameraFadeEnabled"),Enabled);M->SetNumberField(TEXT("fade"),Enabled);
                        FLinearColor C;MID->GetVectorParameterValue(TEXT("OutfitFadeShoulderLeft"),C);M->SetStringField(TEXT("shoulder_l"),C.ToString());
                    }
                    Materials.Add(MakeShared<FJsonValueObject>(M));
                }
                P->SetArrayField(TEXT("materials"),Materials);Parts.Add(MakeShared<FJsonValueObject>(P));
            }
            J->SetArrayField(TEXT("parts"),Parts);SaveJSON(State.Dir/(Stem+TEXT(".json")),J);
            // Record every rendered frame through the reported opening. Later
            // contacts need only sparse context frames in this narrow capture.
            if((Self->IsReloading()&&Self->WeaponStateElapsed<1.6f)||State.Frame%6==0)
                FScreenshotRequest::RequestScreenshot(State.Dir/(Stem+TEXT(".png")),false,false);
        });
        auto Profile=Model->Snapshot();Profile.Items.Reset();Profile.ActiveWeaponSlot=6;
        const bool ColdEquip=FParse::Param(FCommandLine::Get(),TEXT("SVDFirstReloadColdEquip"));
        if(ColdEquip)
        {
            LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/ChainmailCameraClearance20260929/SVD/SK_SVD_Chainmail"));
            LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/WristCoverage20260929/SVD/SK_SVD_d9b5ee5f40_WristCoverage"));
            for(const TCHAR* Name:{TEXT("M_Chainmail_CameraFade"),TEXT("M_CuffSteel_CameraFade"),TEXT("M_Lining_CameraFade")})
                LoadObject<UMaterialInterface>(nullptr,*FString::Printf(TEXT("/Game/Characters/ModularOutfit20260924/ChainmailCameraFade20260930/Materials/%s"),Name));
        }
        auto Gun=Model->CreateItem(TEXT("ue_svd"));Gun.Place=1;Gun.Cell=6;Gun.Magazine=ColdEquip?0:1;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Attachments=MakeShared<FJsonObject>();
        Attachments->SetStringField(TEXT("underbarrel"),TEXT("canted_foregrip"));
        Attachments->SetStringField(TEXT("optic"),TEXT("lpvo_1_6x"));
        Attachments->SetStringField(TEXT("magazine"),TEXT("ext_mag"));
        Attachments->SetStringField(TEXT("stock"),TEXT("qr_performance"));
        Attachments->SetStringField(TEXT("muzzle"),TEXT("titanium_brake"));
        Attachments->SetStringField(TEXT("tactical"),TEXT("laser"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Attachments);
        Gun.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));
        auto Shirt=Model->CreateItem(TEXT("ue_chainmail_shirt"));Shirt.Place=1;Shirt.Cell=7;
        Profile.Items.Add(Gun);Profile.Items.Add(Shirt);Model->AddAmmoToState(Profile,TEXT("ammo_pkm_762x54r"),100);
        if(!Model->CommitState(Profile)){UE_LOG(LogTemp,Error,TEXT("SVD_FIRST_RELOAD fixture rejected: %s"),*Model->ResultMessage());FPlatformMisc::RequestExitWithStatus(false,1);return;}
        GetCharacterMovement()->SetMovementMode(MOVE_Flying);GetCharacterMovement()->StopMovementImmediately();
        SetActorLocation(FVector(0,0,120));if(auto* PC=Cast<APlayerController>(Controller))PC->SetControlRotation(FRotator::ZeroRotator);
        State.Stage=ColdEquip?1:6;State.Attempt=1;State.Next=State.Age+3.f;
        UE_LOG(LogTemp,Display,TEXT("SVD_FIRST_RELOAD recording %s"),*State.Dir);
    }
    if(State.Stage==6&&State.Age>=State.Next&&!IsWeaponBusy())
    {
        if(FParse::Param(FCommandLine::Get(),TEXT("SVDFirstReloadFromADS")))SetAimingState(true);
        TArray<USkeletalMeshComponent*> Parts;GetComponents(Parts);
        const bool Ready=Parts.ContainsByPredicate([this](const auto* Part){return Part->GetAttachParent()==AKMViewmodel&&Part->IsVisible()&&Part->GetSkeletalMeshAsset()&&Part->GetSkeletalMeshAsset()->GetName().Contains(TEXT("Chainmail"));});
        if(Ready)
        {
            MagazineAmmo=0;Model->SyncRuntime();State.Stage=1;State.Next=State.Age;
        }
    }
    if(State.Stage==1||State.Stage==3)
    {
        if(IsReloading())State.SawReload=true;
        else if(State.SawReload){State.Stage++;State.Next=State.Age+.75f;State.SawReload=false;}
        else if(State.Age>=State.Next&&!IsWeaponBusy())
        {ReloadPressed();State.Next=State.Age+1.f;UE_LOG(LogTemp,Display,TEXT("SVD_FIRST_RELOAD begin attempt=%d ammo=%d"),State.Attempt,MagazineAmmo);}
    }
    if(State.Stage==2&&State.Age>=State.Next)
    {
        MagazineAmmo=0;Model->SyncRuntime();State.Stage=3;State.Attempt=2;State.Next=State.Age;
    }
    if((State.Stage==4&&State.Age>=State.Next)||State.Age>25.f)
    {
        const bool Complete=State.Stage==4;State.Stage=5;FWorldDelegates::OnWorldPostActorTick.Remove(State.Handle);
        auto Receipt=MakeShared<FJsonObject>();Receipt->SetBoolField(TEXT("capture_complete"),Complete);
        Receipt->SetNumberField(TEXT("frames"),State.Frame);Receipt->SetNumberField(TEXT("attempts"),State.Attempt);
        Receipt->SetStringField(TEXT("profile"),Model->ProfileSlot());SaveJSON(State.Dir/TEXT("capture.json"),Receipt);
        UE_LOG(LogTemp,Display,TEXT("SVD_FIRST_RELOAD capture_complete=%d frames=%d"),Complete,State.Frame);
        FPlatformMisc::RequestExitWithStatus(false,Complete?0:1);
    }
}
