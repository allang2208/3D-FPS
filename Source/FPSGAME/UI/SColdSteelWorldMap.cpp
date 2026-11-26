#include "SColdSteelWorldMap.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelWorldMapData.h"
#include "ColdSteelUIStyle.h"
#include "SColdSteelMapMarkerEditor.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace ColdSteelCartography
{
    class SMapCanvas final : public SLeafWidget
    {
    public:
        SLATE_BEGIN_ARGS(SMapCanvas) {}
            SLATE_EVENT(FColdSteelMapMarkerPicked,OnPickMarker)
        SLATE_END_ARGS()

        void Construct(const FArguments& Args, APlayerController* InPlayer, TSharedRef<FColdSteelWorldMapSession> InSession, FSimpleDelegate InClose)
        {
            Player=InPlayer;
            Session=InSession;
            Close=InClose;
            OnPickMarker=Args._OnPickMarker;
            SetCanTick(true);
            SetClipping(EWidgetClipping::ClipToBounds);
            Font=ColdSteelUI::TextFont(14*.75f,true);
            Number=ColdSteelUI::NumberFont(12*.75f);
            Reload();
            ObservedWorld=InPlayer->GetWorld();
            SpawnHandle=ObservedWorld->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateSP(this,&SMapCanvas::OnActorSpawned));
            FWorldDelegates::LevelAddedToWorld.AddSP(this,&SMapCanvas::OnLevelAdded);
            FWorldDelegates::LevelRemovedFromWorld.AddSP(this,&SMapCanvas::OnLevelRemoved);
        }

        virtual ~SMapCanvas() override
        {
            if (UWorld* World=ObservedWorld.Get()) World->RemoveOnActorSpawnedHandler(SpawnHandle);
            FWorldDelegates::LevelAddedToWorld.RemoveAll(this);
            FWorldDelegates::LevelRemovedFromWorld.RemoveAll(this);
        }

        void Locate()
        {
            if (Data.IsLoadingHubPhoto()) return;
            Center=PlayerXY;
            Floor=PlayerFloor;
            bFollowPlayerFloor=true;
            bFollowPosition=true;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
        void SelectFloor(int32 SelectedFloor)
        {
            const auto& Map=Session->DungeonMap;
            const auto Floors=KnownFloors();
            if (!Data.bDungeon || Data.bWaitingForDungeon || !Floors.Contains(SelectedFloor)) return;
            Floor=SelectedFloor;
            bFollowPlayerFloor=false;
            bFollowPosition=false;
            if(Floor==PlayerFloor)Center=PlayerXY;
            else if(Map.DiscoveredFloors.Contains(Floor))FitView();
            else for(const auto& Marker:Session->Markers.All())
                if(Marker.Region==Data.RegionKey&&Marker.Floor==Floor){Center=FVector2D(Marker.Position);break;}
            Invalidate(EInvalidateWidgetReason::Paint);
        }
        FText Title() const
        {
            const auto& Map=Session->DungeonMap;
            if (Data.bDungeon && !Data.bWaitingForDungeon && Floor==PlayerFloor && !Map.PlayerArea.IsEmpty())
                return FText::FromString(Data.Title+TEXT(" · ")+Map.PlayerArea);
            if (Data.bDungeon && !Data.bWaitingForDungeon && Floor!=PlayerFloor)
                return FText::FromString(Data.Title+TEXT(" · 你在")+FColdSteelDungeonMap::FloorName(PlayerFloor));
            return FText::FromString(Data.Title);
        }
        FText FloorLabel() const
        {
            return FText::FromString(TEXT("查看：")+FColdSteelDungeonMap::FloorName(Floor));
        }
        TArray<int32> KnownFloors() const
        {
            auto Floors=Session->DungeonMap.DiscoveredFloors;
            // A shared pin may locate an unexplored floor; it does not discover its geometry.
            for(const auto& Marker:Session->Markers.All())
                if(Marker.bDungeon&&Marker.Region==Data.RegionKey)Floors.AddUnique(Marker.Floor);
            Floors.Sort();return Floors;
        }
        int32 ViewedFloor() const { return Floor; }
        int32 CurrentFloor() const { return PlayerFloor; }
        bool IsFloorExplored(int32 Value) const { return Session->DungeonMap.DiscoveredFloors.Contains(Value); }
        FText ViewStatus() const
        {
            FString State=bFollowPosition?TEXT("跟随玩家"):TEXT("自由浏览");
            if(Data.bDungeon)
                State=TEXT("所在：")+FColdSteelDungeonMap::FloorName(PlayerFloor)+TEXT(" · ")+State+TEXT(" · 未探索区域隐藏");
            else State+=TEXT(" · 角色可继续移动");
            return FText::FromString(State);
        }
        FText ZoomLabel() const { return FText::FromString(FString::Printf(TEXT("%.0f%%"),Zoom*100.)); }
        void ZoomStep(double Step)
        {
            const FVector2D Size=GetCachedGeometry().GetLocalSize();
            if(!Data.IsLoadingHubPhoto() && Size.GetMin()>1.) ZoomAt(Size*.5,Size,Step);
        }
        void FitView()
        {
            if(Data.IsLoadingHubPhoto() || Data.bWaitingForDungeon) return;
            const FBox2D Bounds=ViewBounds();
            Center=Bounds.GetCenter();
            const FVector2D Size=GetCachedGeometry().GetLocalSize(),Extent=Bounds.GetSize();
            const double BaseScale=Scale(Size)/Zoom;
            Zoom=FMath::Clamp(FMath::Min(FMath::Max(1.,Size.X-52)/FMath::Max(100.,Extent.Y),
                FMath::Max(1.,Size.Y-52)/FMath::Max(100.,Extent.X))/BaseScale,.01,24.);
            bFollowPosition=false;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
        EVisibility FloorVisibility() const
        {
            return Data.bDungeon && !Data.bWaitingForDungeon && !KnownFloors().IsEmpty()
                ? EVisibility::Visible : EVisibility::Collapsed;
        }
        void FocusMarker(const FColdSteelMapMarker& Marker)
        {
            if (!Marker.Id.IsValid() || Marker.Region!=Data.RegionKey) return;
            Center=FVector2D(Marker.Position); Floor=Marker.Floor;
            bFollowPosition=false; bFollowPlayerFloor=false;
            Invalidate(EInvalidateWidgetReason::Paint);
        }
        FText Status() const { return FText::FromString(PickError); }

    private:
        static constexpr double DungeonViewSize=4800.;
        TWeakObjectPtr<APlayerController> Player;
        TWeakObjectPtr<APawn> MapPawn;
        TSharedPtr<FColdSteelWorldMapSession> Session;
        TWeakObjectPtr<UWorld> ObservedWorld;
        FDelegateHandle SpawnHandle;
        FSimpleDelegate Close;
        FColdSteelMapMarkerPicked OnPickMarker;
        FColdSteelWorldMapData Data;
        FSlateBrush MapBrush, ReliefBrush;
        FSlateFontInfo Font, Number;
        FVector2D Center=FVector2D::ZeroVector, PlayerXY=FVector2D::ZeroVector, LastMouse=FVector2D::ZeroVector;
        double Zoom=1., Heading=0., NextUpdate=0.,PickErrorUntil=0.;
        int32 Floor=0, PlayerFloor=0;
        uint32 MapRevision=0, MapLayout=0;
        bool bFollowPosition=false;
        uint32 MarkerRevision=MAX_uint32,MarkerUIRevision=MAX_uint32;
        FVector2D DownMouse=FVector2D::ZeroVector;
        bool bDragging=false;
        FString PickError;
        bool bFollowPlayerFloor=true;

        void OnActorSpawned(AActor* Actor)
        {
            if (Data.TrackLandmark(Actor)) Invalidate(EInvalidateWidgetReason::Paint);
        }

        void OnLevelAdded(ULevel* Level,UWorld* World)
        {
            if (!Level || World!=ObservedWorld.Get()) return;
            Data.NotifyStreamChanged();
            bool bChanged=false;
            for (AActor* Actor:Level->Actors)
                bChanged|=Data.TrackLandmark(Actor);
            if (bChanged) Invalidate(EInvalidateWidgetReason::Paint);
        }

        void OnLevelRemoved(ULevel* Level,UWorld* World)
        {
            if(!Level || World!=ObservedWorld.Get()) return;
            Data.NotifyStreamChanged();
            if (Data.RemoveLevelLandmarks(Level))
                Invalidate(EInvalidateWidgetReason::Paint);
        }

        void BindMapTextures()
        {
            MapBrush.DrawAs=ReliefBrush.DrawAs=ESlateBrushDrawType::Image;
            MapBrush.SetResourceObject(Data.Surface.Get());
            ReliefBrush.SetResourceObject(Data.ReliefOverlay.Get());
        }

        void Reload()
        {
            APawn* Pawn=Player->GetPawn();
            MapPawn=Pawn;
            Data.Open(Pawn,Session->SurfaceCache,Session->DungeonMap);
            BindMapTextures();
            PlayerXY=FVector2D(Pawn->GetActorLocation());
            Heading=Player->GetControlRotation().Yaw;
            PlayerFloor=Data.bDungeon && !Data.bWaitingForDungeon?Session->DungeonMap.PlayerFloor:0;
            MapRevision=Session->DungeonMap.Revision;
            MapLayout=Session->DungeonMap.LayoutSerial;
            Floor=PlayerFloor;
            bFollowPlayerFloor=true;
            bFollowPosition=Data.bDungeon;
            Center=Data.bDungeon?PlayerXY:Data.Bounds.GetCenter();
            Zoom=1.;
            Invalidate(EInvalidateWidgetReason::Paint);
        }

        virtual void Tick(const FGeometry&, double Now, float) override
        {
            auto* PC=Player.Get();
            APawn* Pawn=PC?PC->GetPawn():nullptr;
            if (!Pawn || Pawn!=MapPawn.Get()) { Close.ExecuteIfBound(); return; }
            const FVector At=Pawn->GetActorLocation();
            if(!PickError.IsEmpty() && Now>PickErrorUntil) { PickError.Reset(); Invalidate(EInvalidateWidgetReason::Paint); }
            if (Now>=NextUpdate || (Data.bDungeon && MapLayout!=Session->DungeonMap.LayoutSerial))
            {
                NextUpdate=Now+.2;
                const auto* Run=Data.bDungeon?UDungeonRunSubsystem::Get(PC->GetWorld()):nullptr;
                const bool bRunReady=Run && Session->DungeonMap.Update(PC);
                const bool bHasLayout=Data.bDungeon && !Data.bWaitingForDungeon;
                if (Data.ForestIdentityChanged(Pawn) || Data.bDungeon!=UDungeonRoomSubsystem::IsDungeonPawn(Pawn) || bRunReady!=bHasLayout ||
                    (bRunReady && !Data.RegionKey.EndsWith(TEXT("/")+Run->RunId())) ||
                    (Data.bDungeon && MapLayout!=Session->DungeonMap.LayoutSerial))
                    Reload();
                if (Data.RefreshLandmarks()) Invalidate(EInvalidateWidgetReason::Paint);
                if (!Data.IsSampling() && Data.RefreshTerrainIfChanged(Pawn,Session->SurfaceCache) && !Data.IsSampling())
                {
                    BindMapTextures();
                    Invalidate(EInvalidateWidgetReason::Paint);
                }
            }
            if (MarkerRevision!=Session->Markers.Revision() || MarkerUIRevision!=Session->MarkerUIRevision)
            {
                MarkerRevision=Session->Markers.Revision(); MarkerUIRevision=Session->MarkerUIRevision;
                Invalidate(EInvalidateWidgetReason::Paint);
            }
            const auto& Map=Session->DungeonMap;
            if (Data.bDungeon && !Data.bWaitingForDungeon && (MapRevision!=Map.Revision || PlayerFloor!=Map.PlayerFloor))
            {
                PlayerFloor=Map.PlayerFloor;
                if (bFollowPlayerFloor) Floor=PlayerFloor;
                MapRevision=Map.Revision;
                Invalidate(EInvalidateWidgetReason::Paint);
            }
            const FVector2D CurrentXY(At);
            const double Facing=PC->GetControlRotation().Yaw;
            if (PlayerXY!=CurrentXY || Heading!=Facing)
            {
                PlayerXY=CurrentXY;
                if (bFollowPosition) Center=PlayerXY;
                Heading=Facing;
                Invalidate(EInvalidateWidgetReason::Paint);
            }
            if (Data.IsLoadingHubPhoto() && Data.FinishLoadingHubPhoto(Pawn,Session->SurfaceCache))
            {
                Center=Data.Bounds.GetCenter();
                BindMapTextures();
                Invalidate(EInvalidateWidgetReason::Paint);
            }
            if (Data.IsSampling())
            {
                Data.SampleSurface(Pawn,Session->SurfaceCache);
                if (!Data.IsSampling())
                {
                    BindMapTextures();
                    Invalidate(EInvalidateWidgetReason::Paint);
                }
            }
        }

        virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(100,100); }
        double Scale(FVector2D Size) const
        {
            const FVector2D Extent=Data.bDungeon?FVector2D(DungeonViewSize):Data.Bounds.GetSize();
            return Zoom*FMath::Min(FMath::Max(1.,Size.X-52)/FMath::Max(100.,Extent.Y),
                                   FMath::Max(1.,Size.Y-52)/FMath::Max(100.,Extent.X));
        }
        FVector2D Project(FVector2D XY,FVector2D Size) const
        {
            const FVector2D Delta=XY-Center;
            return Size*.5+FVector2D(Delta.Y,-Delta.X)*Scale(Size);
        }
        FVector2D AtScreen(FVector2D Local,FVector2D Size) const
        {
            const FVector2D Delta=(Local-Size*.5)/Scale(Size);
            return Center+FVector2D(-Delta.Y,Delta.X);
        }
        FBox2D ViewBounds() const
        {
            if(!Data.bDungeon||Data.bWaitingForDungeon)return Data.Bounds;
            FBox2D Bounds(ForceInit);
            if(const auto* Layer=Session->DungeonMap.Layers.Find(Floor);Layer&&Layer->Bounds.bIsValid)Bounds=Layer->Bounds;
            for(const auto& Marker:Session->Markers.All())if(Marker.Region==Data.RegionKey&&Marker.Floor==Floor)
            {
                Bounds+=FVector2D(Marker.Position)-FVector2D(200.);
                Bounds+=FVector2D(Marker.Position)+FVector2D(200.);
            }
            return Bounds.bIsValid?Bounds:Data.Bounds;
        }
        void ClampCenter()
        {
            const FBox2D Bounds=ViewBounds();
            Center.X=FMath::Clamp(Center.X,Bounds.Min.X,Bounds.Max.X);
            Center.Y=FMath::Clamp(Center.Y,Bounds.Min.Y,Bounds.Max.Y);
        }

        void ZoomAt(FVector2D Local,FVector2D Size,double Step)
        {
            const FVector2D Anchor=AtScreen(Local,Size);
            const auto* Layer=Data.bDungeon && !Data.bWaitingForDungeon?Session->DungeonMap.Layers.Find(Floor):nullptr;
            const double MinZoom=Layer?FMath::Min(.75,DungeonViewSize/FMath::Max(1.,Layer->Bounds.GetSize().GetMax())):.75;
            Zoom=FMath::Clamp(Zoom*FMath::Pow(1.35,Step),FMath::Min(MinZoom,Zoom),24.);
            bFollowPosition=false;
            Center+=Anchor-AtScreen(Local,Size);
            ClampCenter();
            Invalidate(EInvalidateWidgetReason::Paint);
        }
        virtual FReply OnMouseWheel(const FGeometry& G,const FPointerEvent& E) override
        {
            if (Data.IsLoadingHubPhoto()) return FReply::Handled();
            ZoomAt(G.AbsoluteToLocal(E.GetScreenSpacePosition()),G.GetLocalSize(),double(E.GetWheelDelta()));
            return FReply::Handled();
        }
        virtual FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& E) override
        {
            if (Data.IsLoadingHubPhoto()) return FReply::Handled();
            const FVector2D Local=G.AbsoluteToLocal(E.GetScreenSpacePosition());
            if (E.GetEffectingButton()==EKeys::LeftMouseButton)
            {
                LastMouse=DownMouse=Local; bDragging=false;
                return FReply::Handled().CaptureMouse(AsShared());
            }
            if (E.GetEffectingButton()==EKeys::RightMouseButton && !Data.bWaitingForDungeon)
            {
                PickMarker(Local,G.GetLocalSize());
            }
            return FReply::Handled();
        }
        virtual FReply OnMouseMove(const FGeometry& G,const FPointerEvent& E) override
        {
            if (!HasMouseCapture()) return FReply::Unhandled();
            const FVector2D Local=G.AbsoluteToLocal(E.GetScreenSpacePosition());
            if (!bDragging && FVector2D::Distance(Local,DownMouse)<5.) return FReply::Handled();
            bDragging=true;
            bFollowPosition=false;
            Center+=AtScreen(LastMouse,G.GetLocalSize())-AtScreen(Local,G.GetLocalSize());
            LastMouse=Local;
            ClampCenter();
            Invalidate(EInvalidateWidgetReason::Paint);
            return FReply::Handled();
        }
        virtual FReply OnMouseButtonUp(const FGeometry& G,const FPointerEvent& E) override
        {
            if (HasMouseCapture() && E.GetEffectingButton()==EKeys::LeftMouseButton)
            {
                if (!bDragging) PickMarker(G.AbsoluteToLocal(E.GetScreenSpacePosition()),G.GetLocalSize());
                return FReply::Handled().ReleaseMouseCapture();
            }
            return FReply::Handled();
        }

        void PickMarker(FVector2D Local,FVector2D Size)
        {
            if (Data.bWaitingForDungeon || Data.IsLoadingHubPhoto()) return;
            PickError.Reset();
            const FColdSteelMapMarker* Nearest=nullptr;
            double Distance=14.;
            for (const auto& Marker:Session->Markers.All())
                if (Marker.Region==Data.RegionKey && Marker.Floor==Floor)
                {
                    const double D=FVector2D::Distance(Local,Project(FVector2D(Marker.Position),Size));
                    if (D<Distance) { Distance=D; Nearest=&Marker; }
                }
            if (Nearest) { OnPickMarker.ExecuteIfBound(*Nearest); return; }
            FColdSteelMapMarker Marker;
            Marker.Region=Data.RegionKey; Marker.Area=Data.Title; Marker.Floor=Floor; Marker.bDungeon=Data.bDungeon;
            Marker.LayoutSerial=Session->DungeonMap.LayoutSerial;
            if (Data.MarkerGround(MapPawn.Get(),AtScreen(Local,Size),Floor,Marker.Position))
                OnPickMarker.ExecuteIfBound(Marker);
            else
            {
                PickError=Data.bDungeon?TEXT("请在本层已探索的地面上选点"):TEXT("此处没有可标记的地面");
                PickErrorUntil=FSlateApplication::Get().GetCurrentTime()+4.;
            }
            Invalidate(EInvalidateWidgetReason::Paint);
        }

        virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,
            int32 L,const FWidgetStyle&,bool) const override
        {
            const FVector2D Size=G.GetLocalSize();
            const FBox2D View(FVector2D::ZeroVector,Size);
            const auto* White=FCoreStyle::Get().GetBrush("WhiteBrush");
            auto Box=[&](int32 Layer,FVector2D At,FVector2D Span,const FLinearColor& Tint,const FSlateBrush* Brush)
            {
                FSlateDrawElement::MakeBox(Out,L+Layer,G.ToPaintGeometry(Span,FSlateLayoutTransform(At)),Brush,ESlateDrawEffect::None,Tint);
            };
            auto Line=[&](int32 Layer,const TArray<FVector2D>& P,const FLinearColor& Tint,float Width=1.f)
            {
                FSlateDrawElement::MakeLines(Out,L+Layer,G.ToPaintGeometry(),P,ESlateDrawEffect::None,Tint,true,Width);
            };
            auto Text=[&](FVector2D At,const FString& Value,const FSlateFontInfo& Face,const FLinearColor& Tint)
            {
                const auto Paint=G.ToPaintGeometry(FSlateLayoutTransform(At));
                FSlateDrawElement::MakeText(Out,L+8,Paint,Value,Face,ESlateDrawEffect::None,Tint);
            };
            Box(0,{0,0},Size,ColdSteelUI::Content,White);
            if (Data.IsLoadingHubPhoto())
            {
                Text({12,8},TEXT("正在载入主神空间地图"),Font,ColdSteelUI::TextSecondary);
                return L+8;
            }
            if (Data.Surface.IsValid())
            {
                const auto NW=Project({Data.Bounds.Max.X,Data.Bounds.Min.Y},Size);
                const auto SE=Project({Data.Bounds.Min.X,Data.Bounds.Max.Y},Size);
                const auto Rect=G.ToPaintGeometry(SE-NW,FSlateLayoutTransform(NW));
                // UE writes zero alpha for SCS_BaseColor. Only the overlay uses transparency.
                FSlateDrawElement::MakeBox(Out,L+1,Rect,&MapBrush,ESlateDrawEffect::IgnoreTextureAlpha,FLinearColor::White);
                if (Data.ReliefOverlay.IsValid())
                    FSlateDrawElement::MakeBox(Out,L+2,Rect,&ReliefBrush,ESlateDrawEffect::None,FLinearColor::White);
            }
            const auto& DungeonMap=Session->DungeonMap;
            const auto* Layer=Data.bDungeon && !Data.bWaitingForDungeon?DungeonMap.Layers.Find(Floor):nullptr;
            if (Layer)
            {
                FBox2D WorldView(ForceInit);
                WorldView+=AtScreen(FVector2D::ZeroVector,Size);
                WorldView+=AtScreen(Size,Size);
                Layer->ForEachVisiblePatch(WorldView,[&](const FColdSteelDungeonPatch& Area)
                {
                    const auto NW=Project({Area.Bounds.Max.X,Area.Bounds.Min.Y},Size);
                    const auto SE=Project({Area.Bounds.Min.X,Area.Bounds.Max.Y},Size);
                    Box(1,NW,SE-NW,Area.bPassage?ColdSteelUI::Gray(68):ColdSteelUI::Gray(87),White);
                });
            }

            // Choose a 1/2/5 metric interval, with origin-anchored grid lines at all zooms.
            const double CmPerBar=96./Scale(Size);
            const double Decade=FMath::Pow(10.,FMath::FloorToDouble(FMath::LogX(10.,CmPerBar)));
            const double Unit=CmPerBar/Decade;
            const double Interval=Decade*(Unit>=5.?5.:Unit>=2.?2.:1.);
            const double Spacing=Interval*Scale(Size);
            const auto Origin=Project(FVector2D::ZeroVector,Size);
            for (double X=FMath::Fmod(Origin.X,Spacing);X<Size.X;X+=Spacing)
                Line(2,{{X,0},{X,Size.Y}},ColdSteelUI::AttributeRow);
            for (double Y=FMath::Fmod(Origin.Y,Spacing);Y<Size.Y;Y+=Spacing)
                Line(2,{{0,Y},{Size.X,Y}},ColdSteelUI::AttributeRow);

            TArray<FBox2D,TInlineAllocator<32>> Labels;
            const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
            auto Mark=[&](FVector2D At,const FString& Label,const FLinearColor& Color)
            {
                if (!View.IsInsideOrOn(At)) return;
                const TArray<FVector2D> Diamond={At+FVector2D(0,-5),At+FVector2D(5,0),At+FVector2D(0,5),At+FVector2D(-5,0),At+FVector2D(0,-5)};
                Line(5,Diamond,ColdSteelUI::GlassFallback,5.f);
                Line(5,Diamond,Color,2.f);
                const FVector2D Span=FVector2D(Measure->Measure(Label,Font))+FVector2D(10,4);
                FVector2D Pos=At+FVector2D(8,-Span.Y*.5);
                if (Pos.X+Span.X>Size.X) Pos.X=At.X-Span.X-8;
                const FBox2D Rect(Pos,Pos+Span);
                if (!View.IsInsideOrOn(Rect.Min) || !View.IsInsideOrOn(Rect.Max) ||
                    Labels.ContainsByPredicate([&](const FBox2D& Used){return Used.Intersect(Rect);})) return;
                Labels.Add(Rect.ExpandBy(2.));
                Box(6,Pos,Span,ColdSteelUI::GlassTint,White);
                Text(Pos+FVector2D(5,2),Label,Font,Color);
            };
            auto UserMark=[&](const FColdSteelMapMarker& M,bool bDraft)
            {
                if (M.Region!=Data.RegionKey || M.Floor!=Floor) return;
                const auto At=Project(FVector2D(M.Position),Size);
                const auto Color=FColdSteelMapMarkers::Color(M.ColorIndex);
                if ((bDraft || M.Id==Session->SelectedMarker) && View.IsInsideOrOn(At))
                    Line(5,{At+FVector2D(-8,-8),At+FVector2D(8,-8),At+FVector2D(8,8),At+FVector2D(-8,8),At+FVector2D(-8,-8)},Color,1.f);
                const FString Caption=M.Label+(M.bReadOnly?TEXT(" · ")+M.OwnerName:FString());
                Mark(At,bDraft?(M.Label.IsEmpty()?TEXT("新标记"):FColdSteelMapMarkers::CleanLabel(M.Label)):Caption,Color);
            };
            if (Session->MarkerDraft.IsSet()) UserMark(Session->MarkerDraft.GetValue(),true);
            for (const auto& M:Session->Markers.All())
                if (!Session->MarkerDraft.IsSet() || !M.Id.IsValid() || M.Id!=Session->MarkerDraft.GetValue().Id) UserMark(M,false);
            for (const auto& Poi : Data.Landmarks)
                if (Poi.Floor==Floor && !Poi.Label.IsEmpty() &&
                    (!Data.bDungeon || (Layer && DungeonMap.IsLandmarkKnown(FVector(Poi.Point,Poi.ActorZ),Floor))))
                    Mark(Project(Poi.Point,Size),Poi.Label,Poi.bSmithLesson?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextPrimary);
            if (Layer) for (const auto& Label : Layer->Labels)
            {
                FString Caption=Label.Text;
                if (Label.Destination.IsSet())
                {
                    const auto* Other=DungeonMap.Layers.Find(Label.Destination.GetValue());
                    if (Other && Other->Labels.ContainsByPredicate([&](const auto& L){return L.RampNode==Label.RampNode;}))
                        Caption+=TEXT("至")+FColdSteelDungeonMap::FloorName(Label.Destination.GetValue());
                }
                Mark(Project(Label.Point,Size),Caption,ColdSteelUI::TextPrimary);
            }

            if (PlayerFloor==Floor)
            {
                const auto At=Project(PlayerXY,Size);
                const double Rad=FMath::DegreesToRadians(Heading);
                const FVector2D Forward(FMath::Sin(Rad),-FMath::Cos(Rad)),Side(-Forward.Y,Forward.X);
                TArray<FVector2D> Arrow={At+Forward*11,At-Forward*7+Side*7,At-Forward*3,At-Forward*7-Side*7,At+Forward*11};
                Line(9,Arrow,ColdSteelUI::GlassTint,5.f);
                Line(10,Arrow,ColdSteelUI::HUDGoldLight,2.5f);
            }
            Box(7,{8,8},{58,28},ColdSteelUI::GlassTint,White);
            Text({16,12},TEXT("北 N"),Number,ColdSteelUI::TextPrimary);
            const double Y=Size.Y-16;
            Box(7,{8,Y-26},{Spacing+20,36},ColdSteelUI::GlassTint,White);
            Line(7,{{16,Y-4},{16,Y},{16+Spacing,Y},{16+Spacing,Y-4}},ColdSteelUI::TextPrimary);
            Text({16,Y-22},FString::Printf(TEXT("%g m"),Interval*.01),Number,ColdSteelUI::TextPrimary);
            if (Data.bWaitingForForest || Data.bWaitingForDungeon || Data.IsSampling())
                Text({78,12},Data.bWaitingForDungeon?TEXT("正在获取地牢布局"):TEXT("正在绘制地表"),Font,ColdSteelUI::TextSecondary);
            else if (Data.bSurfaceUnavailable)
                Text({78,12},TEXT("丘陵底图暂不可用"),Font,ColdSteelUI::TextSecondary);
            return L+10;
        }
    };

    class SMapPanel final : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SMapPanel) {}
        SLATE_END_ARGS()
        void Construct(const FArguments&,APlayerController* Player,TSharedRef<FColdSteelWorldMapSession> Session,FSimpleDelegate Close)
        {
            Panel=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius);
            Notice=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::CardRadius);
            Style=ColdSteelUI::ButtonStyle();
            auto Editor=SNew(SColdSteelMapMarkerEditor,Player,Session)
                .OnSelected_Lambda([this](const FColdSteelMapMarker& Marker){if(Canvas) Canvas->FocusMarker(Marker);});
            SAssignNew(Canvas,SMapCanvas,Player,Session,Close)
                .OnPickMarker(Editor,&SColdSteelMapMarkerEditor::Begin);
            Editor->SetMapContent(SNew(SOverlay)
                + SOverlay::Slot()[Canvas.ToSharedRef()]
                + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(FMargin(12,46,12,0))
                    [SNew(SBorder).BorderImage(&Notice).Padding(FMargin(10,8))
                        .Visibility_Lambda([this](){return Canvas->Status().IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})
                        [SNew(STextBlock).Text(Canvas.ToSharedRef(),&SMapCanvas::Status).Font(ColdSteelUI::TextFont(14*.75f))
                            .ColorAndOpacity(ColdSteelUI::Warning)]]);
            auto Action=[&](TAttribute<FText> Caption,FSimpleDelegate Click)
            {
                return SNew(SBox).MinDesiredWidth(88).HeightOverride(ColdSteelUI::ActionHeight)
                    [SNew(SButton).ButtonStyle(&Style).IsFocusable(false).HAlign(HAlign_Center).VAlign(VAlign_Center)
                        .OnClicked_Lambda([Click](){Click.ExecuteIfBound();return FReply::Handled();})
                        [SNew(STextBlock).Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary).Text(Caption)]];
            };
            auto Help=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(18,4));
            for (const TCHAR* Hint : {TEXT("WASD 移动角色"),TEXT("单击选点"),TEXT("拖动浏览"),TEXT("滚轮缩放"),TEXT("Delete 删除所选"),TEXT("M / Esc 关闭")})
                Help->AddSlot()[SNew(STextBlock).Text(FText::FromString(Hint)).Font(ColdSteelUI::TextFont(12*.75f)).ColorAndOpacity(ColdSteelUI::TextSecondary)];
            auto Toolbar=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8,6))
                .IsEnabled_Lambda([Session](){return !Session->bEditingMarker;});
            Toolbar->AddSlot()
                [SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight)
                    .Visibility(TAttribute<EVisibility>::CreateSP(Canvas.Get(),&SMapCanvas::FloorVisibility))
                    [SAssignNew(FloorMenu,SComboButton).ButtonStyle(&Style).IsFocusable(false)
                        .ContentPadding(FMargin(12,0)).VAlign(VAlign_Center)
                        .IsEnabled_Lambda([this](){return Canvas->KnownFloors().Num()>1;})
                        .ToolTip(ColdSteelToolTip::Make(FText::FromString(TEXT("已探索楼层及共享标记所在层；共享标记不会揭开迷雾"))))
                        .OnGetMenuContent_Lambda([this]() -> TSharedRef<SWidget>
                        {
                            auto Choices=SNew(SVerticalBox);
                            for(int32 Floor:Canvas->KnownFloors())
                            {
                                const FString Caption=FColdSteelDungeonMap::FloorName(Floor)+(Floor==Canvas->CurrentFloor()?TEXT(" · 当前所在"):
                                    Canvas->IsFloorExplored(Floor)?TEXT(" · 已探索"):TEXT(" · 共享标记"));
                                Choices->AddSlot().AutoHeight().Padding(0,2)
                                    [SNew(SBox).MinDesiredWidth(188).HeightOverride(ColdSteelUI::ActionHeight)
                                        [SNew(SButton).ButtonStyle(&Style).IsFocusable(false)
                                            .OnClicked_Lambda([this,Floor](){Canvas->SelectFloor(Floor);FloorMenu->SetIsOpen(false);return FReply::Handled();})
                                            [SNew(STextBlock).Text(FText::FromString(Caption))
                                                .Font(ColdSteelUI::TextFont(14*.75f,Floor==Canvas->ViewedFloor()))
                                                .ColorAndOpacity(Floor==Canvas->ViewedFloor()?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary)]]];
                            }
                            return SNew(SBorder).BorderImage(&Notice).Padding(6)
                                [SNew(SBox).MaxDesiredHeight(240)
                                    [SNew(SScrollBox)+SScrollBox::Slot()[Choices]]];
                        })
                        .ButtonContent()[SNew(STextBlock).Text(Canvas.ToSharedRef(),&SMapCanvas::FloorLabel)
                            .Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]];
            Toolbar->AddSlot()[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()[Action(FText::FromString(TEXT("缩小")),FSimpleDelegate::CreateLambda([this](){Canvas->ZoomStep(-1.);}))]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SNew(SBox).WidthOverride(64).HAlign(HAlign_Center)
                        [SNew(STextBlock).Text(Canvas.ToSharedRef(),&SMapCanvas::ZoomLabel).Font(ColdSteelUI::NumberFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary)]]
                + SHorizontalBox::Slot().AutoWidth()[Action(FText::FromString(TEXT("放大")),FSimpleDelegate::CreateLambda([this](){Canvas->ZoomStep(1.);}))]];
            Toolbar->AddSlot()[Action(FText::FromString(TEXT("查看全图")),FSimpleDelegate::CreateSP(Canvas.ToSharedRef(),&SMapCanvas::FitView))];
            Toolbar->AddSlot()[Action(FText::FromString(TEXT("定位自己")),FSimpleDelegate::CreateSP(Canvas.ToSharedRef(),&SMapCanvas::Locate))];
            ChildSlot
            [SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius)
                .CornerRadius(FVector4(ColdSteelUI::PanelRadius)).Padding(0)
                [SNew(SBorder).BorderImage(&Panel).Padding(12)
                    [SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)
                        [SNew(SHorizontalBox)
                            + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [SNew(SVerticalBox)
                                + SVerticalBox::Slot().AutoHeight()
                                    [SNew(STextBlock).Text(Canvas.ToSharedRef(),&SMapCanvas::Title).ToolTip(ColdSteelToolTip::Make(TAttribute<FText>(Canvas.ToSharedRef(),&SMapCanvas::Title)))
                                        .Font(ColdSteelUI::TextFont(20*.75f,true)).OverflowPolicy(ETextOverflowPolicy::Ellipsis).ColorAndOpacity(ColdSteelUI::TextPrimary)]
                                + SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)
                                    [SNew(STextBlock).Text_Lambda([this,Session](){return Session->bEditingMarker?FText::FromString(TEXT("编辑标记 · 暂停角色移动")):Canvas->ViewStatus();})
                                        .Font(ColdSteelUI::TextFont(12*.75f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis).ColorAndOpacity(ColdSteelUI::TextSecondary)]]
                            + SHorizontalBox::Slot().AutoWidth()[Action(FText::FromString(TEXT("关闭  M")),Close)]]
                        + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[Toolbar]
                        + SVerticalBox::Slot().FillHeight(1)[Editor]
                        + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Help]
                    ]
                ]
            ];
        }
    private:
        FSlateBrush Panel,Notice;
        FButtonStyle Style;
        TSharedPtr<SMapCanvas> Canvas;
        TSharedPtr<SComboButton> FloorMenu;
    };
}

TSharedRef<SWidget> MakeColdSteelWorldMap(APlayerController* Player,TSharedRef<FColdSteelWorldMapSession> Session,FSimpleDelegate Close)
{
    return SNew(ColdSteelCartography::SMapPanel,Player,Session,Close);
}
