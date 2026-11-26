#include "UnknownGunRosterAuditCommandlet.h"
#include "../Monsters/UnknownHumanoid.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../UI/ColdSteelPickupStudio.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/StreamableManager.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderingThread.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    // Compare scene depth with and without the held assembly. This counts pixels of the gun
    // actually in front of body/clothes, not the gun's projected bounding rectangle.
    int32 VisibleGunPixels(ASceneCapture2D& Camera,UTextureRenderTarget2D& RT,AUnknownHumanoid& Monster,UPoseableMeshComponent& Gun)
    {
        auto* Capture=Camera.GetCaptureComponent2D();
        const FVector Focus=Monster.GetMesh()->GetSocketLocation(TEXT("hand_r"));
        const FVector Offset=Monster.GetActorTransform().TransformVectorNoScale(FVector(125,210,75));
        Camera.SetActorLocationAndRotation(Focus+Offset,(-Offset).Rotation());
        Capture->ClearShowOnlyComponents();
        Capture->ShowOnlyActorComponents(&Monster);
        Monster.GetWorld()->SendAllEndOfFrameUpdates();
        auto Read=[&](TArray<FFloat16Color>& Depth)
        {
            Capture->CaptureScene();
            FlushRenderingCommands();
            return RT.GameThread_GetRenderTargetResource()->ReadFloat16Pixels(Depth);
        };
        TArray<FFloat16Color> Whole,Without;
        if(!Read(Whole))return -1;
        Capture->RemoveShowOnlyComponent(&Gun);
        TArray<USceneComponent*> Children;Gun.GetChildrenComponents(true,Children);
        for(auto* Child:Children)if(auto* Primitive=Cast<UPrimitiveComponent>(Child))Capture->RemoveShowOnlyComponent(Primitive);
        if(!Read(Without)||Whole.Num()!=RT.SizeX*RT.SizeY||Whole.Num()!=Without.Num())return -1;
        int32 Pixels=0;
        for(int32 I=0;I<Whole.Num();++I)
        {
            const float Near=Whole[I].R.GetFloat(),Far=Without[I].R.GetFloat();
            if(Near>1 && Near<500 && (Far==0 || Far>Near+.25f))++Pixels;
        }
        return Pixels;
    }
}

int32 UUnknownGunRosterAuditCommandlet::Main(const FString& Params)
{
    const FString Profile=TEXT("UnknownGunAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();
    GI->InitializeStandalone(TEXT("UnknownGunRosterAuditWorld"));
    FCommandLine::Set(*Original);
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    auto* Guns=GI->GetSubsystem<UGunsmithSystem>();
    auto* Rules=GI->GetSubsystem<UColdSteelEnhancementSystem>();
    if(!World||!Model||!Guns||!Rules||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 Was=Delay?Delay->GetInt():1;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    ON_SCOPE_EXIT {if(Delay)Delay->Set(Was,ECVF_SetByCode);};
    auto* Camera=World->SpawnActor<ASceneCapture2D>();if(!Camera)return 2;
    auto* Capture=Camera->GetCaptureComponent2D();
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->CaptureSource=SCS_SceneDepth;Capture->FOVAngle=46;
    auto* RT=NewObject<UTextureRenderTarget2D>(Camera);
    RT->RenderTargetFormat=RTF_RGBA16f;RT->InitAutoFormat(320,320);RT->UpdateResourceImmediate(true);Capture->TextureTarget=RT;

    TArray<FString> Ids;
    for(const auto& Entry:Model->ItemDefinitions())if(Guns->Weapon(Entry.Key))Ids.Add(Entry.Key);
    Ids.Sort();
    TArray<TSharedPtr<FJsonValue>> Rows;TSet<FString> MaleMeshes;int32 Failures=0;
    const TSet<FString> Singles={TEXT("ue_m1911"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12"),
        TEXT("ue_m24"),TEXT("ue_svd"),TEXT("ue_svch"),TEXT("ue_m870"),TEXT("ue_super90")};
    for(const FString& Id:Ids)for(FName BodyId:{FName(TEXT("jason")),FName(TEXT("kaitlin"))})
    {
        auto Row=MakeShared<FJsonObject>();Rows.Add(MakeShared<FJsonValueObject>(Row));
        Row->SetStringField(TEXT("weapon"),Id);Row->SetStringField(TEXT("body"),BodyId.ToString());
        TArray<TSharedPtr<FJsonValue>> Errors;
        auto Check=[&](bool Ok,const TCHAR* Label){if(!Ok)Errors.Add(MakeShared<FJsonValueString>(Label));return Ok;};
        FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Monster=World->SpawnActor<AUnknownHumanoid>(Spawn);
        if(Check(Monster && Monster->EquipLoadout(*Model,*Rules,EUnknownRole::Gun,20,BodyId,Id),TEXT("loadout")))
        {
            Monster->DispatchBeginPlay();
            if(Monster->AppearanceLoad)Monster->AppearanceLoad->WaitUntilComplete(60.f);
            FlushAsyncLoading();
            auto* Body=Monster->GetMesh();auto* Gun=Monster->HeldGun.Get();
            Check(Monster->Sheet->Equipped() && Monster->Sheet->Equipped()->Definition==Id,TEXT("equipped definition"));
            Row->SetNumberField(TEXT("accuracy_percent"),Monster->ShotAccuracyPercent);
            Check(Monster->ShotAccuracyPercent==(Singles.Contains(Id)?33:20),TEXT("accuracy group"));
            if(Check(Body->GetSkeletalMeshAsset() && Gun && Gun->GetSkinnedAsset(),TEXT("held mesh")))
            {
                Body->TickAnimation(.01f,false);Body->RefreshBoneTransforms();Body->UpdateChildTransforms();
                auto* Asset=CastChecked<USkeletalMesh>(Gun->GetSkinnedAsset());const FString MeshPath=Asset->GetPathName();
                Row->SetStringField(TEXT("mesh"),MeshPath);
                Check(!MeshPath.Contains(TEXT("/AKM/SK_AKM_Viewmodel")),TEXT("generic fallback mesh"));
                if(BodyId==TEXT("jason")){Check(!MaleMeshes.Contains(MeshPath),TEXT("duplicate factory gun mesh"));MaleMeshes.Add(MeshPath);}
                Check(Gun->IsRegistered()&&Gun->IsVisible()&&!Gun->bHiddenInGame&&Gun->GetOwner()==Monster&&
                    Gun->GetAttachParent()==Body&&Gun->GetAttachSocketName()==TEXT("hand_r")&&Body->DoesSocketExist(TEXT("hand_r")),TEXT("body attachment"));
                Check(Gun->DoesSocketExist(TEXT("hand_r"))&&Gun->DoesSocketExist(TEXT("WPN_SOCKET_Muzzle")),TEXT("hand / muzzle socket"));
                const FVector Palm=Body->GetSocketLocation(TEXT("hand_r"));
                const double Gap=FVector::Dist(Palm,Gun->GetSocketLocation(TEXT("hand_r")));
                const double Barrel=FVector::Dist(Palm,Gun->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle")));
                Row->SetNumberField(TEXT("palm_gap_cm"),Gap);Row->SetNumberField(TEXT("hand_to_muzzle_cm"),Barrel);
                Check(Gap<15 && Barrel>4 && Barrel<180,TEXT("grip / barrel placement"));

                bool Created=false;
                auto* Rig=GI->GetSubsystem<UColdSteelPickupStudio>()->Acquire(Id,Created);
                auto* Source=Rig&&!Created?Rig->AKMViewmodel.Get():nullptr;
                TArray<FString> Expected,Actual;
                auto Parts=[&](USceneComponent& Parent,TArray<FString>& Names,bool InspectTransform)
                {
                    TArray<USceneComponent*> Children;Parent.GetChildrenComponents(true,Children);
                    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh())
                    {
                        Names.Add(Part->GetStaticMesh()->GetPathName());
                        if(InspectTransform)Check(Part->IsRegistered()&&Part->GetOwner()==Monster&&Part->GetAttachParent()==Gun&&
                            !Part->GetComponentTransform().ContainsNaN(),TEXT("attachment transform"));
                    }
                    Names.Sort();
                };
                if(Check(Source!=nullptr,TEXT("source rig")))Parts(*Source,Expected,false);
                Parts(*Gun,Actual,true);Check(Expected==Actual,TEXT("factory parts differ from source"));
                TArray<TSharedPtr<FJsonValue>> PartNames;
                for(const FString& Name:Actual)PartNames.Add(MakeShared<FJsonValueString>(Name));
                Row->SetArrayField(TEXT("static_parts"),PartNames);
                const int32 Pixels=VisibleGunPixels(*Camera,*RT,*Monster,*Gun);
                Row->SetNumberField(TEXT("visible_gun_pixels"),Pixels);
                Check(Pixels>10,TEXT("no distinct gun silhouette in held pose"));
            }
        }
        Row->SetArrayField(TEXT("errors"),Errors);Failures+=!Errors.IsEmpty();
        UE_LOG(LogTemp,Display,TEXT("UNKNOWN_GUN_CASE %s %s accuracy=%d pixels=%.0f errors=%d"),*Id,*BodyId.ToString(),
            Monster?Monster->ShotAccuracyPercent:0,Row->HasField(TEXT("visible_gun_pixels"))?Row->GetNumberField(TEXT("visible_gun_pixels")):0.,Errors.Num());
        Capture->ClearShowOnlyComponents();
        if(Monster)Monster->Destroy();
        if(Rows.Num()%6==0){FlushAsyncLoading();CollectGarbage(RF_NoFlags);}
    }
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("gun_count"),Ids.Num());Result->SetNumberField(TEXT("failures"),Failures);
    Result->SetArrayField(TEXT("cases"),Rows);
    const auto Directory=FPaths::ProjectSavedDir()/TEXT("UnknownGunRosterAudit");
    IFileManager::Get().MakeDirectory(*Directory,true);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    if(!FFileHelper::SaveStringToFile(Json,*(Directory/TEXT("report.json"))))return 2;
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_GUN_COMPLETE guns=%d cases=%d failures=%d"),Ids.Num(),Rows.Num(),Failures);
    return Ids.IsEmpty()||Failures?1:0;
}
