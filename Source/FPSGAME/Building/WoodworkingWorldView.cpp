#include "WoodworkingWorldView.h"
#include "WoodworkingStockGeometry.h"
#include "WoodworkingSystem.h"
#include "Async/Async.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "HAL/PlatformTime.h"
#include "Materials/MaterialInterface.h"

struct FWoodworkingWorldMesh
{
    UE::Geometry::FDynamicMesh3 Stock,Marks;
    uint64 Epoch=0;
    int32 Revision=0;
    bool Valid=false;
};

namespace
{
constexpr double StockBottom=ColdSteelWoodworking::FDeviceGeometry::StockBottom,StockThickness=ColdSteelWoodworking::FDeviceGeometry::StockThickness,BladeRadius=ColdSteelWoodworking::FDeviceGeometry::BladeRadius;
using FMesh=UE::Geometry::FDynamicMesh3;
const FSoftObjectPath WoodworkingCutGuidePath(TEXT("/Game/Building/WoodworkingSawHighlight20261013/M_SawCutGuide.M_SawCutGuide"));
void PrepareMesh(FMesh& Mesh){Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();}
void Quad(FMesh& Mesh,FVector3d A,FVector3d B,FVector3d C,FVector3d D,FVector3f Normal,FVector4f Color,double UVScale)
{
    // Match UE front-face winding (clockwise), as in VoxelSurfaceMesher::Emit.
    if(FVector3d::DotProduct(FVector3d::CrossProduct(B-A,C-A),FVector3d(Normal))>0)Swap(B,D);
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();auto* Colors=Mesh.Attributes()->PrimaryColors();
    const int32 Start=Mesh.VertexCount();
    for(const FVector3d P:{A,B,C,D})
    {
        Mesh.AppendVertex(P);Normals->AppendElement(Normal);UVs->AppendElement(FVector2f(float(P.X/UVScale),float(P.Y/UVScale)));Colors->AppendElement(Color);
    }
    for(const auto Indices:{UE::Geometry::FIndex3i(Start,Start+1,Start+2),UE::Geometry::FIndex3i(Start,Start+2,Start+3)})
    {
        const int32 ID=Mesh.AppendTriangle(Indices);Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
    }
}
TSharedPtr<FWoodworkingWorldMesh,ESPMode::ThreadSafe> BuildStock(TArray<uint8> Wood,TArray<uint8> Target,TArray<uint8> Damage,int32 W,int32 H,double Units,uint64 Epoch,int32 Revision,bool Review=false)
{
    auto Result=MakeShared<FWoodworkingWorldMesh,ESPMode::ThreadSafe>();Result->Epoch=Epoch;Result->Revision=Revision;
    const auto Plan=WoodworkingStockGeometry::Plan(Wood.GetData(),Wood.Num(),W,H);
    const auto Guide=WoodworkingStockGeometry::Plan(Target.GetData(),Target.Num(),W,H);
    const auto Hurt=WoodworkingStockGeometry::Plan(Damage.GetData(),Damage.Num(),W,H);
    TArray<uint8> Remaining;Remaining.Init(0,W*H);
    if(Review)for(int32 I=0;I<Remaining.Num();++I)Remaining[I]=Wood[I]&&!Target[I];
    const auto Excess=WoodworkingStockGeometry::Plan(Remaining.GetData(),Remaining.Num(),W,H);
    if(!Plan.Valid||!Guide.Valid||!Hurt.Valid||Plan.Faces.size()*2+Plan.Edges.size()+Guide.Edges.size()+Hurt.Faces.size()+Excess.Faces.size()>WoodworkingStockGeometry::MaximumQuads)return Result;
    PrepareMesh(Result->Stock);PrepareMesh(Result->Marks);
    auto P=[&](double X,double Y,double Z){return FVector3d((X-W*.5)*Units,-(Y-H*.5)*Units,Z);};
    const FVector4f Face(.48f,.28f,.125f,1),Cut(.64f,.40f,.21f,1),Ink(.84f,.88f,.85f,.9f),Red(.72f,.075f,.045f,.32f);
    auto FaceRect=[&](FMesh& Mesh,double X0,double Y0,double X1,double Y1,double Z,FVector3f N,FVector4f Color)
    {Quad(Mesh,P(X0,Y0,Z),P(X1,Y0,Z),P(X1,Y1,Z),P(X0,Y1,Z),N,Color,40);};
    for(const auto& R:Plan.Faces)
    {
        FaceRect(Result->Stock,R.X0,R.Y0,R.X1,R.Y1,StockThickness,FVector3f(0,0,1),Face);
        FaceRect(Result->Stock,R.X0,R.Y0,R.X1,R.Y1,0,FVector3f(0,0,-1),Face);
    }
    for(const auto& E:Plan.Edges)
        Quad(Result->Stock,P(E.X0,E.Y0,0),P(E.X1,E.Y1,0),P(E.X1,E.Y1,StockThickness),P(E.X0,E.Y0,StockThickness),FVector3f(float(E.NX),float(-E.NY),0),Cut,40);
    // Board-local chalk outline uses the same authoritative target cells as scoring.
    for(const auto& E:Guide.Edges)
    {
        const double DX=E.X1-E.X0,DY=E.Y1-E.Y0,Length=FMath::Sqrt(DX*DX+DY*DY),NX=-DY/Length*.4,NY=DX/Length*.4;
        Quad(Result->Marks,P(E.X0+NX,E.Y0+NY,StockThickness+.035),P(E.X1+NX,E.Y1+NY,StockThickness+.035),P(E.X1-NX,E.Y1-NY,StockThickness+.035),P(E.X0-NX,E.Y0-NY,StockThickness+.035),FVector3f(0,0,1),Ink,40);
    }
    // Damage is a translucent location marker over missing target cells, not replacement wood.
    for(const auto& R:Hurt.Faces)FaceRect(Result->Marks,R.X0,R.Y0,R.X1,R.Y1,StockThickness+.02,FVector3f(0,0,1),Red);
    for(const auto& R:Excess.Faces)FaceRect(Result->Marks,R.X0,R.Y0,R.X1,R.Y1,StockThickness+.025,FVector3f(0,0,1),FVector4f(.85f,.53f,.12f,.35f));
    Result->Valid=true;return Result;
}
}

AWoodworkingWorldView::AWoodworkingWorldView()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("WorkFrame"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("WorkCamera"));Camera->SetupAttachment(RootComponent);Camera->FieldOfView=53;
    Stock=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("CutStock"));Stock->SetupAttachment(RootComponent);
    Markings=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("ChalkAndDamage"));Markings->SetupAttachment(Stock);
    Effects=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("CutChips"));Effects->SetupAttachment(RootComponent);
    Waste=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("DetachedWaste"));Waste->SetupAttachment(RootComponent);
    SawGuide=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("SawEdgeGuide"));SawGuide->SetupAttachment(RootComponent);
    for(auto* Mesh:{Stock.Get(),Markings.Get(),Effects.Get(),Waste.Get(),SawGuide.Get()})
    {
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);Mesh->SetCanEverAffectNavigation(false);
        Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetVisibility(false);
        Mesh->SetTransientDeferCollisionUpdates(true);
    }
    Markings->SetCastShadow(false);
    SawGuide->SetCastShadow(false);
    Effects->SetCastShadow(false);Chips.Reserve(32);
    StockMaterial=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Building/WoodworkingWorld20261009/M_WoodworkingStock.M_WoodworkingStock")));
    MarkMaterial=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Building/WoodworkingWorld20261009/M_WoodworkingMarks.M_WoodworkingMarks")));
}
bool AWoodworkingWorldView::Prepare(APlayerController* Player,UStaticMeshComponent* Station,UWoodworkingSystem* InSystem)
{
    if(!Player||!Player->IsLocalController()||!Station||!InSystem||!Station->DoesSocketExist(TEXT("WoodworkingSawPivot")))return false;
    PC=Player;Workbench=Station;System=InSystem;SetOwner(Player);
    SetActorTransform(Station->GetComponentTransform());AttachToComponent(Station,FAttachmentTransformRules::KeepWorldTransform);
    SawOrigin=Station->GetSocketTransform(TEXT("WoodworkingSawPivot"),RTS_Component).GetLocation();
    // Share the actual blade's socket and local axes, without a separate screen-space projection.
    SawGuide->AttachToComponent(Station,FAttachmentTransformRules::SnapToTargetIncludingScale,TEXT("WoodworkingSawPivot"));
    const double Height=StockBottom+StockThickness-SawOrigin.Z;
    if(Height<=0||Height>=BladeRadius||InSystem->SawSettings().ContactLength<=0)return false;
    // Match the finite gameplay contact line to the visible blade chord at stock top.
    UnitsPerPixel=InSystem->SawSettings().CentimetersPerPixel;
    Notice=TEXT("正在准备实景木板…");UpdateCamera();SetActorTickEnabled(true);
    TArray<FSoftObjectPath> Paths={StockMaterial.ToSoftObjectPath(),MarkMaterial.ToSoftObjectPath(),WoodworkingCutGuidePath};
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateUObject(this,&ThisClass::MaterialsReady));
    if(!MaterialLoad){bFailed=true;Notice=TEXT("木板材质加载失败，请关闭后重试");}
    return !bFailed;
}
void AWoodworkingWorldView::MaterialsReady()
{
    auto* GuideMaterial=Cast<UMaterialInterface>(WoodworkingCutGuidePath.ResolveObject());
    bMaterialsReady=StockMaterial.IsValid()&&MarkMaterial.IsValid()&&GuideMaterial;
    if(!bMaterialsReady){bFailed=true;Notice=TEXT("缺少实景木板材质，请关闭面板");return;}
    Stock->SetMaterial(0,StockMaterial.Get());Markings->SetMaterial(0,MarkMaterial.Get());
    Effects->SetMaterial(0,StockMaterial.Get());Waste->SetMaterial(0,StockMaterial.Get());
    // Dedicated opaque unlit ink: no translucent sorting or chalk opacity on the cutting guide.
    SawGuide->SetMaterial(0,GuideMaterial);
}
void AWoodworkingWorldView::Enter()
{
    auto* Player=PC.Get();if(!Player||bEntered)return;
    WorkingPawn=Player->GetPawn();PreviousView=Player->GetViewTarget();bEntered=true;
    if(WorkingPawn.IsValid()&&!Player->HiddenActors.Contains(WorkingPawn.Get()))
    {Player->HiddenActors.Add(WorkingPawn.Get());bHiddenPawn=true;}
    // Immediate entry keeps pointer deprojection and the visible plane identical from first input.
    Player->SetViewTarget(this);UpdateStock();
}
bool AWoodworkingWorldView::Healthy() const
{return !IsActorBeingDestroyed()&&bEntered&&PC.IsValid()&&WorkingPawn.IsValid()&&PC->GetPawn()==WorkingPawn.Get()&&Workbench.IsValid()&&!Workbench->IsSimulatingPhysics()&&System.IsValid();}
bool AWoodworkingWorldView::Prepared() const{return PC.IsValid()&&Workbench.IsValid()&&System.IsValid()&&bMaterialsReady&&bStockReady&&!bFailed;}
bool AWoodworkingWorldView::Ready() const{return Healthy()&&Prepared();}
void AWoodworkingWorldView::RestorePlayer()
{
    if(!bEntered)return;bEntered=false;
    if(auto* Player=PC.Get())
    {
        if(bHiddenPawn)Player->HiddenActors.Remove(WorkingPawn.Get());
        if(Player->GetViewTarget()==this||(Player->PlayerCameraManager&&Player->PlayerCameraManager->PendingViewTarget.Target==this))
        {
            AActor* Return=PreviousView.IsValid()?PreviousView.Get():Player->GetPawn();if(Return)Player->SetViewTarget(Return);
        }
    }
    bHiddenPawn=false;
}
void AWoodworkingWorldView::Leave()
{
    RestorePlayer();SetActorTickEnabled(false);Stock->SetVisibility(false);Markings->SetVisibility(false);Effects->SetVisibility(false);Waste->SetVisibility(false);SawGuide->SetVisibility(false);Chips.Reset();
    if(MaterialLoad){MaterialLoad->CancelHandle();MaterialLoad.Reset();}
    SetLifeSpan(.01f); // Camera restore is synchronous; widget cleanup may destroy this actor immediately.
}
void AWoodworkingWorldView::EndPlay(const EEndPlayReason::Type Reason)
{RestorePlayer();if(MaterialLoad)MaterialLoad->CancelHandle();Super::EndPlay(Reason);}
void AWoodworkingWorldView::UpdateCamera()
{
    if(!PC.IsValid()||!System.IsValid())return;int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);if(Width<1||Height<1)return;
    LastViewport=FVector2D(Width,Height);const auto* S=System.Get();TArray<FVector> Points;
    for(const FVector2D P:{FVector2D(0,0),FVector2D(S->Settings().Width,0),FVector2D(0,S->Settings().Height),FVector2D(S->Settings().Width,S->Settings().Height)})
    {const auto Work=S->BoardToWork(P);Points.Add(FVector(SawOrigin.X+Work.X*UnitsPerPixel,SawOrigin.Y-Work.Y*UnitsPerPixel,StockBottom+StockThickness));}
    Points.Add(SawOrigin+FVector(0,-25,BladeRadius));Points.Add(SawOrigin+FVector(0,25,BladeRadius));
    FBox Bounds(ForceInit);for(const FVector& P:Points)Bounds+=P;const FVector Focus=Bounds.GetCenter();
    // Face the front edge squarely, with the stock axes aligned to the screen.
    const FRotator Rotation=(-FVector(0,-160,280)).Rotation();const FRotationMatrix Basis(Rotation);
    const FVector Forward=Basis.GetScaledAxis(EAxis::X),Right=Basis.GetScaledAxis(EAxis::Y),Up=Basis.GetScaledAxis(EAxis::Z);
    const double TanX=FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView*.5)),TanY=TanX*Height/Width;
    const double UsableX=FMath::Max(.2,1.0-(ScreenInsets.Left+ScreenInsets.Right)/Width)*.9;
    const double UsableY=FMath::Max(.2,1.0-(ScreenInsets.Top+ScreenInsets.Bottom)/Height)*.9;
    double Distance=120;
    for(const FVector& P:Points)
    {
        const FVector D=P-Focus;const double Depth=FVector::DotProduct(D,Forward);
        Distance=FMath::Max(Distance,FMath::Abs(FVector::DotProduct(D,Right))/(TanX*UsableX)-Depth);
        Distance=FMath::Max(Distance,FMath::Abs(FVector::DotProduct(D,Up))/(TanY*UsableY)-Depth);
    }
    Distance*=ZoomFactor;
    const double CX=(ScreenInsets.Left-ScreenInsets.Right)/Width,CY=(ScreenInsets.Bottom-ScreenInsets.Top)/Height;
    Camera->SetRelativeLocation(Focus-Forward*Distance-Right*(Distance*TanX*CX)-Up*(Distance*TanY*CY));Camera->SetRelativeRotation(Rotation);
}
void AWoodworkingWorldView::SetScreenInsets(FMargin Insets)
{if(ScreenInsets!=Insets){ScreenInsets=Insets;UpdateCamera();}}
void AWoodworkingWorldView::SetReview(bool Enabled)
{if(bReview!=Enabled){bReview=Enabled;++Epoch;AppliedRevision=QueuedRevision=-1;}}
void AWoodworkingWorldView::Zoom(float Steps){ZoomFactor=FMath::Clamp(ZoomFactor*FMath::Pow(1.12,-double(Steps)),.65,1.8);UpdateCamera();}
void AWoodworkingWorldView::ResetCamera(){ZoomFactor=1;UpdateCamera();}
void AWoodworkingWorldView::UpdateSawGuide()
{
    const auto* S=System.Get();
    if(!Ready()||!S||(!S->IsAdjusting()&&!S->MotorRunning())){SawGuide->SetVisibility(false);return;}
    const int8 State=S->IsAdjusting()?0:1;
    if(State!=SawGuideState)
    {
        FMesh Mesh;PrepareMesh(Mesh);
        const double Height=StockBottom+StockThickness-SawOrigin.Z+.08;
        const double Half=S->SawSettings().ContactLength*.5*UnitsPerPixel;
        const double HalfKerf=S->SawSettings().Kerf*.5*UnitsPerPixel;
        const FVector4f Red(.95f,.008f,.004f,1),Dark(.008f,.004f,.003f,1);
        auto Stripe=[&](double A,double B)
        {
            // Both layers are in blade-socket space, exactly over the gameplay contact chord.
            // The dark border is presentation only; the red center keeps the actual kerf width.
            for(int32 Layer=0;Layer<2;++Layer)
            {
                const double Width=HalfKerf+(Layer==0?.22:0),Z=Height+Layer*.035;
                Quad(Mesh,FVector3d(-Width,A,Z),FVector3d(Width,A,Z),FVector3d(Width,B,Z),FVector3d(-Width,B,Z),FVector3f(0,0,1),Layer==0?Dark:Red,40);
            }
        };
        if(State==0)
        {
            for(int32 I=0;I<10;++I)Stripe(-Half+2*Half*I/10,-Half+2*Half*(I+.68)/10);
        }
        else Stripe(-Half,Half);
        SawGuide->SetMesh(MoveTemp(Mesh));SawGuideState=State;
    }
    SawGuide->SetVisibility(true);
}
bool AWoodworkingWorldView::CursorToWork(FVector2D Pixel,FVector2D& Work) const
{
    if(!Ready())return false;FVector Origin,Direction;
    if(!PC->DeprojectScreenPositionToWorld(float(Pixel.X),float(Pixel.Y),Origin,Direction))return false;
    Origin=GetActorTransform().InverseTransformPosition(Origin);Direction=GetActorTransform().InverseTransformVector(Direction);
    if(FMath::Abs(Direction.Z)<.00001)return false;
    const double Distance=(StockBottom+StockThickness-Origin.Z)/Direction.Z;if(Distance<0)return false;
    const FVector At=Origin+Direction*Distance;
    Work=FVector2D((At.X-SawOrigin.X)/UnitsPerPixel,-(At.Y-SawOrigin.Y)/UnitsPerPixel);
    return FMath::IsFinite(Work.X)&&FMath::IsFinite(Work.Y);
}
void AWoodworkingWorldView::InvalidateBoard()
{
    ++Epoch;AppliedRevision=QueuedRevision=-1;bStockReady=false;Stock->SetVisibility(false);Markings->SetVisibility(false);
    Chips.Reset();Effects->SetVisibility(false);Waste->SetVisibility(false);WasteAge=2;
    if(System.IsValid()){LastCut=System->Mask().CutSerial();LastPeel=System->Mask().PeelSerial();}
}
void AWoodworkingWorldView::UpdateStock()
{
    const auto* S=System.Get();if(!S||bFailed)return;
    const auto* Pattern=S->Pattern();const FName Id=Pattern?Pattern->Id:NAME_None;
    if(Id!=ObservedPattern||S->Mask().Revision()<AppliedRevision){ObservedPattern=Id;InvalidateBoard();}
    const auto& Pose=S->Pose();
    Stock->SetRelativeLocation(FVector(SawOrigin.X+Pose.Offset.X*UnitsPerPixel,SawOrigin.Y-Pose.Offset.Y*UnitsPerPixel,StockBottom));
    Stock->SetRelativeRotation(FRotator(0,-FMath::RadiansToDegrees(Pose.Angle),0));
    if(Pending.IsValid()&&Pending.IsReady())
    {
        auto Result=Pending.Get();Pending=decltype(Pending)();
        if(Result&&Result->Epoch==Epoch)
        {
            if(!Result->Valid)
            {
                bFailed=bMeshBudgetFailure=true;Notice=TEXT("切口实景显示暂不可用，准备切换平面台面");Stock->SetVisibility(false);Markings->SetVisibility(false);
                if(auto* Active=System.Get()){Active->EndStroke();if(Active->MotorRunning())Active->ToggleMotor();}return;
            }
            Stock->SetMesh(MoveTemp(Result->Stock));Markings->SetMesh(MoveTemp(Result->Marks));
            AppliedRevision=Result->Revision;bStockReady=true;Notice.Reset();
        }
    }
    Stock->SetVisibility(bEntered&&bMaterialsReady&&bStockReady);Markings->SetVisibility(bEntered&&bMaterialsReady&&bStockReady);
    const double Now=FPlatformTime::Seconds();
    if(Pending.IsValid()||!Pattern||Now<NextMesh||AppliedRevision==S->Mask().Revision())return;
    NextMesh=Now+1.0/15.0;QueuedRevision=S->Mask().Revision();
    // One immutable snapshot / one worker at a time. No UObjects or GPU readback in the worker.
    TArray<uint8> Wood=S->Mask().Wood(),Target=S->Mask().Target(),Damage=S->Mask().Damage();
    const int32 W=S->Settings().Width,H=S->Settings().Height,Revision=QueuedRevision;const uint64 Generation=Epoch;const double Units=UnitsPerPixel;
    const bool Review=bReview;
    Pending=Async(EAsyncExecution::ThreadPool,[Wood=MoveTemp(Wood),Target=MoveTemp(Target),Damage=MoveTemp(Damage),W,H,Units,Generation,Revision,Review]() mutable
    {return BuildStock(MoveTemp(Wood),MoveTemp(Target),MoveTemp(Damage),W,H,Units,Generation,Revision,Review);});
}
void AWoodworkingWorldView::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);UpdateStock();UpdateSawGuide();if(bEntered)UpdateEffects(DeltaSeconds);
    if(PC.IsValid()){int32 W,H;PC->GetViewportSize(W,H);if(LastViewport!=FVector2D(W,H))UpdateCamera();}
}
void AWoodworkingWorldView::UpdateEffects(float DeltaSeconds)
{
    auto* S=System.Get();if(!S||!bMaterialsReady)return;
    const auto& Mask=S->Mask();const float Step=FMath::Min(DeltaSeconds,.05f);
    if(LastCut!=Mask.CutSerial())
    {
        LastCut=Mask.CutSerial();const auto& Hit=Mask.LastCut();
        for(int32 I=0;I<FMath::Min(6,Hit.Samples.Num())&&Chips.Num()<32;++I)
        {
            const auto Work=S->BoardToWork(Hit.Samples[I]);const float Side=(I%2)?1.f:-1.f;
            Chips.Add({FVector(SawOrigin.X+Work.X*UnitsPerPixel,SawOrigin.Y-Work.Y*UnitsPerPixel,StockBottom+StockThickness+.2),FVector(Side*(16+I*3),22+I*3,25+I*2),0});
        }
    }
    if(LastPeel!=Mask.PeelSerial())
    {
        LastPeel=Mask.PeelSerial();TArray<uint8> Empty;Empty.Init(0,Mask.Wood().Num());
        auto Mesh=BuildStock(Mask.DetachedWaste(),Empty,Empty,S->Settings().Width,S->Settings().Height,UnitsPerPixel,Epoch,Mask.Revision(),false);
        if(Mesh->Valid)
        {
            Waste->SetMesh(MoveTemp(Mesh->Stock));Waste->SetRelativeScale3D(FVector::OneVector);WasteStart=Stock->GetRelativeLocation();WasteRotation=Stock->GetRelativeRotation();WasteAge=0;Waste->SetVisibility(true);
        }
    }
    if(WasteAge<.65f)
    {
        WasteAge+=Step;const float T=WasteAge/.65f;
        // A bounded detached display chunk, never a second source of collision or score.
        Waste->SetRelativeLocation(WasteStart+FVector(14*T,10*T,-12*T*T));Waste->SetRelativeRotation(WasteRotation+FRotator(7*T,0,4*T));
        Waste->SetRelativeScale3D(FVector(FMath::Max(.01f,1.f-FMath::Max(0.f,(T-.7f)/.3f))));
        if(WasteAge>=.65f)Waste->SetVisibility(false);
    }
    else Waste->SetRelativeScale3D(FVector::OneVector);
    for(auto& Chip:Chips){Chip.Age+=Step;Chip.Velocity.Z-=180*Step;Chip.Position+=Chip.Velocity*Step;}
    Chips.RemoveAll([](const FChip& Chip){return Chip.Age>.5f;});
    if(Chips.IsEmpty()){Effects->SetVisibility(false);return;}
    FMesh Mesh;PrepareMesh(Mesh);
    for(const auto& Chip:Chips)
    {
        const FVector3d P(Chip.Position);const double Size=FMath::Clamp((.5-Chip.Age)*3,0.05,0.6);
        Quad(Mesh,P+FVector3d(-Size,-.18,0),P+FVector3d(Size,-.18,0),P+FVector3d(Size,.18,.12),P+FVector3d(-Size,.18,.12),FVector3f(0,0,1),FVector4f(.72f,.46f,.23f,1),40);
    }
    Effects->SetMesh(MoveTemp(Mesh));Effects->SetVisibility(true);
}
