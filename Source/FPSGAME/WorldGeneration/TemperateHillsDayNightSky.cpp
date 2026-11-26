#include "TemperateHillsWorld.h"
#include "../FPSWeatherManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"

// The authored 50 km HDR day/night backdrop was retired with the UDS migration:
// Ultra Dynamic Sky now presents the sky, sun, moon and stars for the hills world
// through the weather manager's UDS bridge. These hooks remain so the streaming
// and teardown paths stay intact; the component itself is no longer created.

void ATemperateHillsWorld::ActivateDayNightSky()
{
}

void ATemperateHillsWorld::TickDayNightSky()
{
}

void ATemperateHillsWorld::EndDayNightSky()
{
    if(DayNightSky){RemoveInstanceComponent(DayNightSky);DayNightSky->DestroyComponent();DayNightSky=nullptr;}
    DayNightSkyMID=nullptr;SkyWeather.Reset();
}
