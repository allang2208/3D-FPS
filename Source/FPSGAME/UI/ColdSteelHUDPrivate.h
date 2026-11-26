#pragma once
#include "../FPSWeatherManager.h"
#include "Components/CanvasPanelSlot.h"
#include "Styling/SlateTypes.h"

namespace ColdSteelHUDPrivate
{
extern const int32 InventoryColumns;
extern const int32 InventoryRows;
extern const int32 WeatherSegmentsPerDay;
extern const float TimelineHorizonDays;
extern const FLinearColor DrawerHeader, DrawerDeep, SlotDark, SlotEquipped, GridLine;
extern const FLinearColor TimelineWeatherColor, TimelineCriticalColor, StatusCard, AttributeRow, TooltipSurface;
FProgressBarStyle StatusBarStyle();
void FillSlot(UCanvasPanelSlot* Slot, const FAnchors& Anchors, const FMargin& Offsets = FMargin(0.0f), int32 ZOrder = 0);
bool IsWetWeather(EFPSWeatherState State);
FString WeatherRegionName(const UWorld* World);
FString WeatherName(EFPSWeatherState State);
FString WeatherIconFile(EFPSWeatherState State);
FString FormatTimelineAbsolute(float AbsoluteSeconds, float DaySeconds);
}
