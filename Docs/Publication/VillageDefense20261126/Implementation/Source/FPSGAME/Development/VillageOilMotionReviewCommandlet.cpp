#include "VillageOilMotionReviewCommandlet.h"
#if WITH_EDITOR
#include "../WorldGeneration/VillageOilCarry.h"
#include "../WorldGeneration/VillageHotOil.h"
#include "../FPSGAMEPlayerController.h"
#include "../Movement/FurnitureRestAuditCommandlet.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Building/ForgeArmsMeshComponent.h"
#include "../Weapons/WoodenTorchArmsComponent.h"
#include "../Weapons/WeaponPresentationMaterials.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "../WorldGeneration/VillageOilMotion.h"
#include "Components/CapsuleComponent.h"
#include "Serialization/JsonSerializer.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "AssetCompilingManager.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "VillageOilSurfaceReview.inl"
#include "VillageOilSpreadChecks.inl"

namespace
{
template<class T> void Binary(const FString& File,const TArray<T>& Values)
{
    TUniquePtr<FArchive> Writer(IFileManager::Get().CreateFileWriter(*File));
    if(Writer && !Values.IsEmpty())Writer->Serialize(const_cast<T*>(Values.GetData()),Values.Num()*sizeof(T));
}
FString Triple(FVector P){return FString::Printf(TEXT(",%.6f,%.6f,%.6f"),P.X,P.Y,P.Z);}
}
#endif
int32 UVillageOilMotionReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Out;if(!FParse::Value(*Params,TEXT("Output="),Out))return 1;
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Profile=TEXT("OilMotionAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Cmd=FCommandLine::Get();
    FCommandLine::Set(*(Cmd+TEXT(" -ColdSteelProfile=")+Profile));
    TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));GI->InitializeStandalone(TEXT("OilMotionAudit"));
    FCommandLine::Set(*Cmd);
    UWorld* W=GI->GetWorld();
    ON_SCOPE_EXIT{GI->Shutdown();if(W){GEngine->DestroyWorldContext(W);W->DestroyWorld(false);}};
    auto* ProfileModel=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!W || !ProfileModel || !ProfileModel->IsAudit() || ProfileModel->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    W->InitializeActorsForPlay(FURL());
    auto* Floor=W->SpawnActor<AStaticMeshActor>();
    Floor->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorScale3D(FVector(40,40,1));Floor->SetActorLocation(FVector(0,0,-50));
    auto* P=W->SpawnActor<AFurnitureRestAuditPawn>(FVector(0,0,90),FRotator::ZeroRotator);
    auto* PC=W->SpawnActor<AFPSGAMEPlayerController>();
    if(!P||!PC)return 3;
    PC->SetAsLocalPlayerController();PC->Possess(P);PC->SetInitialLocationAndRotation(P->GetPawnViewLocation(),FRotator::ZeroRotator);PC->SetViewTarget(P);PC->bShowMouseCursor=false;
    // The isolated pawn has no equipment startup. Start in the normal post-equip idle state.
    auto* Weapon=FindFProperty<FEnumProperty>(P->GetClass(),TEXT("WeaponState"));
    if(!Weapon)return 4;
    *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Idle;
    auto* K=W->SpawnActor<AVillageOilKettle>();K->GetMasonry()->SetStaticMesh(Cast<UStaticMesh>(AVillageOilKettle::MeshPath().TryLoad()));
    auto* Carry=P->FindComponentByClass<UVillageOilCarry>();
    FString BodyData;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(BodyData,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))) ||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(BodyData),Config))return 11;
    FString BodyId;
    if(FParse::Value(*Params,TEXT("Body="),BodyId) && BodyId!=TEXT("jason"))
        Config=Config->GetObjectField(TEXT("body_variants"))->GetObjectField(BodyId);
    auto* WorldSkin=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    if(!WorldSkin)return 12;
    P->GetMesh()->SetSkeletalMeshAsset(WorldSkin);
    P->GetMesh()->SetRelativeLocationAndRotation(FVector(0,0,-P->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()),FRotator(0,-90,0));
    FAssetCompilingManager::Get().FinishAllCompilation();
    FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    auto PlaceKettle=[&](FVector At){
        K->SetActorLocation(At);K->GetMasonry()->RecreatePhysicsState();
        W->GetPhysicsScene()->EnsureCollisionTreeIsBuilt(W);
    };
    PlaceKettle(Eye+View.Vector()*155.-FVector(0,0,78));
    auto Key=[&](FKey K0,EInputEvent E){FInputKeyEventArgs Ev{};Ev.Key=K0;Ev.Event=E;Ev.AmountDepressed=E==IE_Pressed?1.f:0.f;return static_cast<APlayerController*>(PC)->InputKey(Ev);};
    if(!Carry || ColdSteelWorldInteraction::TraceUseTargets(PC).Target!=K){
        UE_LOG(LogTemp,Error,TEXT("OIL_REVIEW focus eye=%s pawn=%s pos=%s kettle=%s found=%s"),*Eye.ToString(),*GetNameSafe(PC->GetPawn()),*P->GetActorLocation().ToString(),*K->GetActorLocation().ToString(),*GetNameSafe(ColdSteelWorldInteraction::TraceUseTargets(PC).Target));return 5;}
    Key(EKeys::E,IE_Pressed);
    if(!Carry->Occupied()){UE_LOG(LogTemp,Error,TEXT("OIL_REVIEW pickup rejected local=%d busy=%s"),P->IsLocallyControlled(),*P->DescribeLeftHandBusy());return 6;}
    if(FParse::Param(*Params,TEXT("OilCarryOnly")))
    {
        // The controller and viewmodel can both change while the equipped hand items stay put.
        PC->SetIgnoreLookInput(true);
        PC->bShowMouseCursor=true;
        *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Equipping;
        PlaceKettle(Eye-FVector(450,0,50));
        for(int Frame=0;Frame<720 && Carry->Occupied();++Frame)
        {
            W->Tick(LEVELTICK_TimeOnly,1.f/60);
            if(Frame==120)
            {
                PC->SetIgnoreLookInput(false);PC->bShowMouseCursor=false;
                *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Idle;
            }
            if(Frame%60==0)Carry->RefreshEquipment(*ProfileModel);
            Carry->TickComponent(1.f/60,LEVELTICK_All,nullptr);
        }
        const bool Held=Carry->Occupied();
        FInputKeyEventArgs Unbound{};Unbound.Key=EKeys::R;Unbound.Event=IE_Pressed;
        Carry->HandleInput(Unbound);
        const bool IgnoredKey=Carry->Occupied();
        auto Alternate=ProfileModel->Snapshot();
        Alternate.ActiveWeaponSlot=Alternate.ActiveWeaponSlot==6?9:6;
        if(auto* Switched=ProfileModel->CreateEquipmentModel(Alternate))Carry->RefreshEquipment(*Switched);
        const bool ChangedSlots=!Carry->Occupied();
        PlaceKettle(Eye+View.Vector()*155.-FVector(0,0,78));Key(EKeys::E,IE_Pressed);
        const bool Retrieved=Carry->Occupied();
        *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Reloading;
        Carry->TickComponent(1.f/60,LEVELTICK_All,nullptr);
        const bool ReloadCancelled=!Carry->Occupied();
        UE_LOG(LogTemp,Display,TEXT("OIL_CARRY idle_and_input_lock=%d unbound_reload_key=%d equipment_swap=%d retake=%d reload=%d"),
            Held,IgnoredKey,ChangedSlots,Retrieved,ReloadCancelled);
        return Held && IgnoredKey && ChangedSlots && Retrieved && ReloadCancelled?0:14;
    }
    // Turn away from the supply kettle to pour onto the unobstructed floor.
    PlaceKettle(Eye-FVector(450,0,50));PC->SetControlRotation(FRotator::ZeroRotator);
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto* Arms=P->FindComponentByClass<UForgeArmsMeshComponent>();
    auto* Native=Arms?Cast<USkeletalMesh>(Arms->GetSkinnedAsset()):nullptr;
    if(!Native)return 7;
    const auto& LOD=Native->GetResourceForRendering()->LODRenderData[0];
    TArray<uint32> Faces;auto* IB=LOD.MultiSizeIndexContainer.GetIndexBuffer();
    for(const auto& Section:LOD.RenderSections)
        if(WeaponPresentationMaterials::IsArmSection(Native->GetMaterials()[Section.MaterialIndex]))
            for(uint32 I=0;I<Section.NumTriangles*3;++I)Faces.Add(IB->Get(Section.BaseIndex+I));
    Binary(Out/TEXT("arms.idx"),Faces);
    TArray<FTransform> Tmp;FTransform Contacts[2];
    FFPSBodyGripRig BodyRig[2];
    for(int Side=0;Side<2;++Side)
    {
        Contacts[Side]=UWoodenTorchArmsComponent::BuildStaffCarry(*Native,Side,Tmp);
        const FName Hand=Side?TEXT("hand_l"):TEXT("hand_r");
        BodyRig[Side].Initialize(Native->GetRefSkeleton(),WorldSkin->GetRefSkeleton(),Hand,Hand);
        if(!BodyRig[Side].IsValid())return 13;
    }
    UStaticMeshComponent* Pot=nullptr,*Oil=nullptr,*WorldPot=nullptr;
    P->ForEachComponent<UStaticMeshComponent>(false,[&](UStaticMeshComponent* C){
        if(C->GetStaticMesh())
        {if(C->GetStaticMesh()->GetFName()==TEXT("SM_OilHandPot"))(C->bOnlyOwnerSee?Pot:WorldPot)=C;
         if(C->bOnlyOwnerSee && C->GetStaticMesh()->GetFName()==TEXT("SM_OilSurface"))Oil=C;}
    });
    if(!Pot||!Oil||!WorldPot)return 8;
    FString Table=TEXT("frame,t,held,arms,pot,oil,fill_scale,pitch,px,py,pz,oil_pitch,ox,oy,oz,r_err,l_err,fields,stream,lip_dx,lip_dy,lip_dz,body_r_err,body_l_err\n");
    FString Ribbons=TEXT("frame");
    FString Anatomy=TEXT("frame,side,sx,sy,sz,ex,ey,ez,wx,wy,wz,kx,ky,kz\n");
    for(int J=0;J<=10;++J)Ribbons+=FString::Printf(TEXT(",x%d,y%d,z%d"),J,J,J);
    Ribbons+=TEXT("\n");
    auto* Camera=P->FirstPersonCamera.Get();
    FOilReviewCapture Capture;
    if(FParse::Param(*Params,TEXT("OilScreens")))Capture.Start(W,Out);
    if(!K->HasActorBegunPlay())K->DispatchBeginPlay();
    int32 BubbleTransitions=0;TArray<bool> WasLive;WasLive.Init(false,K->Boil.Num());
    auto Step=[&](){
        W->Tick(LEVELTICK_TimeOnly,1.f/60);
        if(Carry->Occupied())Carry->TickComponent(1.f/60,LEVELTICK_All,nullptr);
        K->AdvanceBoil(W->GetTimeSeconds());
        for(int I=0;I<K->Boil.Num();++I){const bool Live=K->Boil[I].Born>=0.;if(WasLive[I]&&!Live)++BubbleTransitions;WasLive[I]=Live;}
        for(TActorIterator<AVillageOilField> It(W);It;++It)
        {if(!It->HasActorBegunPlay())It->DispatchBeginPlay();static_cast<AActor*>(*It)->Tick(1.f/60);}
    };
    constexpr int Click=30;
    int FieldFrames=0,FlowFrames=0;
    double WorstView=0.,WorstBody=0.,WorstLip=0.;bool bDryFlow=false;
    for(int F=0;F<=Click+FMath::CeilToInt(VillageOilMotion::Finish*60.)+4;++F)
    {
        if(F==Click){Key(EKeys::LeftMouseButton,IE_Pressed);Key(EKeys::LeftMouseButton,IE_Released);}
        if(F)Step();
        const auto Pan=Pot->GetRelativeTransform();
        double Error[2]={},BodyError[2]={};
        auto BodyPose=BodyRig[0].TargetBind;Carry->PoseWorldArms(*P->GetMesh(),BodyPose);
        for(int Side=0;Side<2;++Side)
        {
            auto Wrist=Arms->GetSocketTransform(Side?TEXT("hand_l"):TEXT("hand_r"),RTS_Component);
            Wrist.SetScale3D(FVector::OneVector);
            const FVector Palm=(Contacts[Side]*Wrist).GetLocation();
            const auto Bone=[&](const TCHAR* Name){return Arms->GetSocketTransform(FName(*(FString(Name)+(Side?TEXT("_l"):TEXT("_r")))),RTS_Component).GetLocation();};
            Anatomy+=FString::Printf(TEXT("%d,%d"),F,Side)+Triple(Bone(TEXT("upperarm")))+Triple(Bone(TEXT("lowerarm")))+Triple(Wrist.GetLocation())+Triple(Bone(TEXT("middle_01")))+TEXT("\n");
            Error[Side]=FVector::Distance(Palm,Pan.TransformPosition(FVector(0,Side?-18.9:18.9,5.6)));
            FTransform BodyWrist=BodyPose[BodyRig[Side].TargetHand];BodyWrist.SetScale3D(FVector::OneVector);
            const FVector BodyPalm=(Contacts[Side]*BodyRig[Side].Mount*BodyWrist*P->GetMesh()->GetComponentTransform()).GetLocation();
            BodyError[Side]=FVector::Dist(BodyPalm,WorldPot->GetComponentTransform().TransformPosition(FVector(0,Side?-18.9:18.9,5.6)));
        }
        int Fields=0;bool HasStream=false;FVector Offset=FVector::ZeroVector;
        for(TActorIterator<AVillageOilField> It(W);It;++It)
        {
            ++Fields;
            auto* Ribbon=It->FindComponentByClass<USplineMeshComponent>();
            if(Ribbon && Ribbon->IsVisible())
            {
                HasStream=true;
                const FVector Start=Ribbon->GetComponentTransform().TransformPosition(Ribbon->GetStartPosition());
                const FVector Edge=Pot->GetComponentTransform().TransformPosition(VillageOilMotion::Lip);
                Offset=Camera->GetComponentQuat().UnrotateVector(Start-Edge);
                Ribbons+=FString::FromInt(F);
                for(int J=0;J<=10;++J)
                {
                    const FVector V=FMath::CubicInterp(Ribbon->GetStartPosition(),Ribbon->GetStartTangent(),
                        Ribbon->GetEndPosition(),Ribbon->GetEndTangent(),J/10.);
                    Ribbons+=Triple(Camera->GetComponentTransform().InverseTransformPosition(Ribbon->GetComponentTransform().TransformPosition(V)));
                }
                Ribbons+=TEXT("\n");
            }
        }
        if(Capture.Camera)
        {
            if(F%3==0)
                Capture.Shot(*FString::Printf(TEXT("hands-%03d"),F),Camera->GetComponentLocation(),Camera->GetComponentRotation(),90,
                    {Arms,Pot,Oil},Fields?static_cast<AActor*>(*TActorIterator<AVillageOilField>(W)):nullptr);
            if(Fields && F%4==0)
            {
                auto* Field=*TActorIterator<AVillageOilField>(W);
                const FVector Aim=Field->GetActorLocation(),Cam=Aim+FVector(-460,-550,660);
                Capture.Shot(*FString::Printf(TEXT("advance-%03d"),F),Cam,(Aim-Cam).Rotation(),76,{},Field);
            }
            if(F>=24 && F%6==0)
            {
                const FVector Aim=K->GetActorLocation()+FVector(0,0,87),Cam=Aim+FVector(107,-79,88);
                Capture.Shot(*FString::Printf(TEXT("kettle-%03d"),F),Cam,(Aim-Cam).Rotation(),53,{},K);
            }
        }
        if(Fields)++FieldFrames;
        if(Carry->Occupied())
        {
            WorstView=FMath::Max(WorstView,FMath::Max(Error[0],Error[1]));
            WorstBody=FMath::Max(WorstBody,FMath::Max(BodyError[0],BodyError[1]));
        }
        if(HasStream)
        {
            ++FlowFrames;WorstLip=FMath::Max(WorstLip,Offset.Size());
            bDryFlow|=!Oil->IsVisible();
        }
        const FTransform Fluid=Oil->GetRelativeTransform();
        Table+=FString::Printf(TEXT("%d,%.6f,%d,%d,%d,%d,%.6f,%.6f"),F,F/60.,Carry->Occupied(),Arms->IsVisible(),Pot->IsVisible(),Oil->IsVisible(),Fluid.GetScale3D().X,Pan.Rotator().Pitch)
            +Triple(Pan.GetLocation())+FString::Printf(TEXT(",%.6f"),Fluid.Rotator().Pitch)+Triple(Fluid.GetLocation())
            +FString::Printf(TEXT(",%.6f,%.6f,%d,%d"),Error[0],Error[1],Fields,HasStream)+Triple(Offset)
            +FString::Printf(TEXT(",%.6f,%.6f\n"),BodyError[0],BodyError[1]);
        if(Arms->IsVisible() && F%3==0)
        {
            TArray<FMatrix44f> Matrices;Arms->GetCurrentRefToLocalMatrices(Matrices,0);
            TArray<FVector3f> Vertices;
            USkinnedMeshComponent::ComputeSkinnedPositions(Arms,Vertices,Matrices,LOD,*Arms->GetSkinWeightBuffer(0));
            Binary(Out/FString::Printf(TEXT("arms-%03d.bin"),F),Vertices);
        }
    }
    FFileHelper::SaveStringToFile(Table,*(Out/TEXT("motion.csv")));
    FFileHelper::SaveStringToFile(Ribbons,*(Out/TEXT("ribbon.csv")));
    FFileHelper::SaveStringToFile(Anatomy,*(Out/TEXT("hands.csv")));
    const bool Finished=FieldFrames>0 && !Carry->Occupied() && !Pot->IsVisible() && !Arms->IsVisible();
    if(Capture.Camera)
    {
        auto* Field=*TActorIterator<AVillageOilField>(W);
        const FVector Ground=Field->GetActorLocation(),Cam=Ground+FVector(-460,-550,660);
        const FRotator Frame=(Ground-Cam).Rotation();
        Capture.Shot(TEXT("ground-dry"),Cam,Frame,76,{});
        for(int I=0;I<=230;++I)
        {
            if(I%8==0 || I==230)
                Capture.Shot(*FString::Printf(TEXT("ground-%03d"),I),Cam,Frame,76,{},Field);
            Step();
        }
    }
    UE_LOG(LogTemp,Display,TEXT("OIL_BOIL sampled_bursts=%d"),BubbleTransitions);
    for(TActorIterator<AVillageOilField> It(W);It;++It)It->Destroy();
    PlaceKettle(Eye+View.Vector()*155.-FVector(0,0,78));Key(EKeys::E,IE_Pressed);
    if(!Carry->Occupied())return 9;
    Key(EKeys::LeftMouseButton,IE_Pressed);Key(EKeys::LeftMouseButton,IE_Released);
    for(int I=0;I<12;++I)Step();
    P->InterruptActionsForPriority(true);
    for(int I=0;I<65;++I)Step();
    const bool Cancelled=!Carry->Occupied() && !Arms->IsVisible() && !Pot->IsVisible() && !TActorIterator<AVillageOilField>(W);
    auto CancelPour=[&](int32 PourFrames,bool WantField)
    {
        PlaceKettle(Eye+View.Vector()*155.-FVector(0,0,78));Key(EKeys::E,IE_Pressed);
        if(!Carry->Occupied())return false;
        PlaceKettle(Eye-FVector(450,0,50));
        for(int I=0;I<22;++I)Step();
        Key(EKeys::LeftMouseButton,IE_Pressed);Key(EKeys::LeftMouseButton,IE_Released);
        for(int I=0;I<PourFrames;++I)Step();
        *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Reloading;Step();
        *Weapon->ContainerPtrToValuePtr<EAKMWeaponState>(P)=EAKMWeaponState::Idle;
        int Fields=0;
        for(TActorIterator<AVillageOilField> It(W);It;++It)
        {++Fields;if(It->FindComponentByClass<USplineMeshComponent>()->IsVisible())return false;}
        return !Carry->Occupied() && !Pot->IsVisible() && Fields==(WantField?1:0);
    };
    const bool Before=CancelPour(15,false),After=CancelPour(32,true);
    UE_LOG(LogTemp,Display,TEXT("OIL_REVIEW complete=%d cancel_raise=%d cancel_tip=%d cancel_stream=%d"),Finished,Cancelled,Before,After);
    const bool Contact=FlowFrames>0 && !bDryFlow && WorstView<.25 && WorstBody<.25 && WorstLip<.25;
    UE_LOG(LogTemp,Display,TEXT("OIL_REVIEW contact=%d view_cm=%.4f body_cm=%.4f lip_cm=%.4f empty_flow=%d"),Contact,WorstView,WorstBody,WorstLip,bDryFlow);
    const bool FlowOK=CheckVillageOilSpread(*W,Out);
    return Finished && Cancelled && Before && After && Contact && BubbleTransitions>0 && FlowOK?0:10;
#else
    return 1;
#endif
}
