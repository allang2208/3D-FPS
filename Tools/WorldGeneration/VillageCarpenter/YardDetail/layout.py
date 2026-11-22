"""Repair assembly placements in centimetres in the plot 04 house frame."""
PACKAGE = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_Carpenter'
LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
TAG = 'VillageCarpenter.YardDetail'
# Area centers are stable model pivots, including the two patches fitted to the deck.
PLACEMENTS = {
    'BenchCurls': ((281, -230, 0), 0, False),
    'SawSlivers': ((126, 145, 0), 0, False),
    'HewingChips': ((-245, -561, -4), 0, False),
    'SeasoningBoards': ((520, -150, -4), 87, True),
    'OffcutCrib': ((520, -352, -4), 6, True),
    'YardFlitches': ((-234, -703, -4), 9, True),
}

def place_detail(house, add):
    from author_shop import pose
    for key,(point,yaw,solid) in PLACEMENTS.items():
        add('Repaired',PACKAGE+key,pose(house,*point,yaw),
            profile='BlockAll' if solid else 'NoCollision',extra=(TAG,))
