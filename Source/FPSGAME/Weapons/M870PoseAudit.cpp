// Explicit M870 visual evidence run. No hook or state changes without the flag.
#include "../FPSGAMECharacter.h"
#include "FPSGunplayAnimInstance.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace M870PoseAudit
{
struct FRun
{
    int32 Phase=0,Wardrobe=0,Frame=0;
    double PhaseStart=0,NextCapture=0;
    bool Done=false;
    FString Directory;
} Run;
TArray<TSharedPtr<FJsonValue>> V(const FVector& P)
{
    return {MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};
}
void Write(const TSharedRef<FJsonObject>& Row,const FString& File,bool Append=false)
{
    FString Text;FJsonSerializer::Serialize(Row,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text+TEXT("\n"),*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),Append?FILEWRITE_Append:0);
}
void End(bool Success,const FString& Reason)
{
    Run.Done=true;auto Row=MakeShared<FJsonObject>();Row->SetBoolField(TEXT("completed"),Success);Row->SetStringField(TEXT("reason"),Reason);
    Row->SetNumberField(TEXT("requested_frames"),Run.Frame);Write(Row,Run.Directory/TEXT("completion.json"));
    UE_LOG(LogTemp,Display,TEXT("M870_POSE_AUDIT_COMPLETE success=%d frames=%d reason=%s"),Success,Run.Frame,*Reason);
    FPlatformMisc::RequestExitWithStatus(false,Success?0:1);
}
bool Fixture(UColdSteelStatusModel* Profile,int32 Magazine)
{
    auto State=Profile->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);State.ActiveWeaponSlot=6;
    auto Gun=Profile->CreateItem(TEXT("ue_m870"));Gun.Place=1;Gun.Cell=6;Gun.Magazine=Magazine;State.Items.Add(Gun);
    if(Run.Wardrobe){auto Shirt=Profile->CreateItem(TEXT("ue_chainmail_shirt"));Shirt.Place=1;Shirt.Cell=7;State.Items.Add(Shirt);}
    Profile->AddAmmoToState(State,TEXT("ammo_12g"),42);
    return Profile->CommitState(State);
}
void Tick(UWorld* World,ELevelTick,float)
{
    if(Run.Done||!World)return;
    auto* PC=World->GetFirstPlayerController();auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    static int32 DiagnosticTicks=0;
    if(DiagnosticTicks++<3)UE_LOG(LogTemp,Display,TEXT("M870_POSE_WORLD type=%d world=%s pawn=%s time=%.3f"),int32(World->WorldType),*GetNameSafe(World),*GetNameSafe(PC?PC->GetPawn():nullptr),World->GetTimeSeconds());
    if(World->WorldType!=EWorldType::Game)return;
    if(!C||World->GetTimeSeconds()<3.f)return;
    auto* Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    static bool ProfileReported=false;
    if(!ProfileReported){ProfileReported=true;UE_LOG(LogTemp,Display,TEXT("M870_POSE_PROFILE object=%s audit=%d slot=%s"),*GetNameSafe(Profile),Profile&&Profile->IsAudit(),Profile?*Profile->ProfileSlot():TEXT("none"));}
    if(!Profile||!Profile->IsAudit()||!Profile->ProfileSlot().Contains(TEXT("M870PoseAudit")))return;
    const double Now=World->GetTimeSeconds();
    if(Run.Directory.IsEmpty())
    {
        FString Label;FParse::Value(FCommandLine::Get(),TEXT("GunplayLabel="),Label);
        Run.Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("M870PoseAudit")/FPaths::MakeValidFileName(Label));
        IFileManager::Get().MakeDirectory(*(Run.Directory/TEXT("Frames")),true);
    }
    if(Now>100){End(false,TEXT("Stage timeout"));return;}
    const auto Key=[&](const FKey& K,EInputEvent Event){PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Event,Event==IE_Released?0.f:1.f));};
    const auto Next=[&](int32 Phase){Run.Phase=Phase;Run.PhaseStart=Now;Run.NextCapture=Now;};
    const double T=Now-Run.PhaseStart;
    switch(Run.Phase)
    {
    case 0: if(!Fixture(Profile,3)){End(false,TEXT("Initial fixture rejected"));return;}Next(1);break;
    case 1: if(T>5&&!C->IsReloading())Next(2);break;
    case 2: if(T>2){Key(EKeys::RightMouseButton,IE_Pressed);Next(3);}break;
    case 3: if(T>2){Key(EKeys::RightMouseButton,IE_Released);Next(4);}break;
    case 4: if(T>1){Key(EKeys::R,IE_Pressed);Key(EKeys::R,IE_Released);Next(5);}break;
    case 5: if(T>7&&!C->IsReloading())
        {if(!Fixture(Profile,0)){End(false,TEXT("Empty fixture rejected"));return;}Next(6);}break;
    case 6: if(T>2){Key(EKeys::R,IE_Pressed);Key(EKeys::R,IE_Released);Next(7);}break;
    case 7: if(T>9&&!C->IsReloading()){Key(EKeys::RightMouseButton,IE_Pressed);Next(8);}break;
    case 8: if(T>2){Key(EKeys::RightMouseButton,IE_Released);Next(9);}break;
    case 9: if(T>1){if(Run.Wardrobe==0){Run.Wardrobe=1;Next(0);}else{End(true,TEXT("Captured bare and chainmail hip, ADS and both reloads"));return;}}break;
    }
    if(Run.Phase!=2&&Run.Phase!=3&&Run.Phase!=5&&Run.Phase!=7&&Run.Phase!=8)return;
    if(Now<Run.NextCapture||FScreenshotRequest::IsScreenshotRequested())return;
    USkeletalMeshComponent* Mesh=nullptr;TArray<USkeletalMeshComponent*> Components;C->GetComponents(Components);
    for(auto* Part:Components)if(Part->GetFName()==TEXT("AKMViewmodel"))Mesh=Part;
    if(!Mesh||!GetPathNameSafe(Mesh->GetSkeletalMeshAsset()).Contains(TEXT("SK_M870"))){End(false,TEXT("M870 viewmodel not active"));return;}
    auto* Camera=C->FindComponentByClass<UCameraComponent>();auto* Anim=Cast<UFPSGunplayAnimInstance>(Mesh->GetAnimInstance());
    if(!Camera||!Anim){End(false,TEXT("Camera or native anim instance missing"));return;}
    Run.NextCapture=Now+1./20.;
    const FString Stage=Run.Phase==2?TEXT("hip"):Run.Phase==3?TEXT("ads"):Run.Phase==5?TEXT("reload_normal"):Run.Phase==7?TEXT("reload_empty"):TEXT("ads_return");
    const FString Image=FString::Printf(TEXT("%s_%s_%05d.png"),Run.Wardrobe?TEXT("chainmail"):TEXT("bare"),*Stage,Run.Frame++);
    FScreenshotRequest::RequestScreenshot(Run.Directory/TEXT("Frames")/Image,false,false);
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),Image);Row->SetStringField(TEXT("stage"),Stage);
    Row->SetStringField(TEXT("wardrobe"),Run.Wardrobe?TEXT("chainmail"):TEXT("bare"));Row->SetNumberField(TEXT("time"),Now);
    Row->SetNumberField(TEXT("stage_time"),Now-Run.PhaseStart);Row->SetNumberField(TEXT("ammo"),C->GetMagazineAmmo());
    Row->SetNumberField(TEXT("weapon_state"),int32(C->GetWeaponState()));Row->SetNumberField(TEXT("aim_alpha"),Anim->AimAlpha);
    Row->SetNumberField(TEXT("action_alpha"),Anim->ActionAlpha);Row->SetNumberField(TEXT("action_time"),Anim->ActionTime);
    Row->SetStringField(TEXT("action"),GetPathNameSafe(Anim->ActionClip));Row->SetStringField(TEXT("idle"),GetPathNameSafe(Anim->IdleClip));
    Row->SetStringField(TEXT("mesh"),GetPathNameSafe(Mesh->GetSkeletalMeshAsset()));
    Row->SetArrayField(TEXT("camera"),V(Camera->GetComponentLocation()));Row->SetArrayField(TEXT("camera_rotation"),V(Camera->GetComponentRotation().Euler()));
    Row->SetNumberField(TEXT("fov"),Camera->FieldOfView);
    auto Bones=MakeShared<FJsonObject>();
    for(const FName Name:{FName("upperarm_l"),FName("lowerarm_l"),FName("hand_l"),FName("WPN_RearSight"),FName("WPN_FrontSight")})
    {
        const FVector Point=Mesh->GetSocketLocation(Name);auto B=MakeShared<FJsonObject>();B->SetArrayField(TEXT("world"),V(Point));
        FVector2D Pixel;if(PC->ProjectWorldLocationToScreen(Point,Pixel))B->SetArrayField(TEXT("pixel"),V(FVector(Pixel.X,Pixel.Y,0)));
        Bones->SetObjectField(Name.ToString(),B);
    }
    Row->SetObjectField(TEXT("bones"),Bones);
    TArray<TSharedPtr<FJsonValue>> Parts;
    for(auto* Part:Components)if(Part->IsVisible()&&Part->GetSkeletalMeshAsset())
    {
        auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("name"),Part->GetName());Item->SetStringField(TEXT("asset"),Part->GetSkeletalMeshAsset()->GetPathName());
        Parts.Add(MakeShared<FJsonValueObject>(Item));
    }
    Row->SetArrayField(TEXT("visible_components"),Parts);Write(Row,Run.Directory/TEXT("frames.jsonl"),true);
}
struct FRegister
{
    FRegister()
    {
        FCoreDelegates::OnPostEngineInit.AddLambda([]()
        {
            if(FParse::Param(FCommandLine::Get(),TEXT("M870PoseAudit")))
            {
                UE_LOG(LogTemp,Display,TEXT("M870_POSE_AUDIT_REGISTERED"));
                FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);
            }
        });
    }
} Register;
}
