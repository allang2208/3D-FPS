"""Bread currently baking, in cm relative to the bakery doorway."""

COUNTER='/Game/WorldGeneration/TemperateHills/VillageBakery/Furnishings/SM_BakeryCounter'
FIREBOX_CENTER=(-245,660,29)


def build_oven_details(place):
    # Natural bases of the existing scanned loaves sit on the firebrick deck.
    # Leave the peel a straight approach from the landing to either batch.
    for x,y,length,twist in [(-266,641,23.,-14),(-237,651,25.,16),(-269,678,21.,29)]:
        place('BakingRoundLoaf',COUNTER+'Bread',(x,y,95.),(length,length*.623,length*.399),twist)
    for x,y,length,twist in [(-222,683,36.,74),(-249,695,33.,84)]:
        place('BakingLongLoaf',COUNTER+'Baguette',(x,y,95.),(length,length*.190,length*.145),twist)
