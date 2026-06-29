# Type Fighter Achievements

Achievements are checked when the mission list loads, after a mission ends, and after leaving the upgrades menu. Each achievement can reward a player only once.

## Rank Achievements

Ranks are based on the highest continuous mission progress unlocked for the player.

| Achievement | Requirement | Credits | Score | Image |
| --- | --- | ---: | ---: | --- |
| Private | Reach Private rank. Private begins when mission 5 is unlocked. | 500 | 500 | `rank_private_achievement.png` |
| Lieutenant | Reach Lieutenant rank. Lieutenant begins when mission 10 is unlocked. | 750 | 750 | `rank_lieutenant_achievement.png` |
| Captain | Reach Captain rank. Captain begins when mission 20 is unlocked. | 1,000 | 1,000 | `rank_captain_achievement.png` |
| Major | Reach Major rank. Major begins when mission 30 is unlocked. | 2,000 | 2,000 | `rank_major_achievement.png` |

Major also enables support for a third defense drone.

## Perfect Mission Achievements

A perfect mission requires all of the following:

- The mission was won.
- No damage was taken.
- No inaccurate keys were pressed.
- Final accuracy was 100%.

Perfect missions are stored per player and shown with the gold `P` marker in the mission list.

| Achievement | Requirement | Credits | Score | Image |
| --- | --- | ---: | ---: | --- |
| Seeking Perfection | Complete 5 missions perfectly. | 300 | 500 | `seeking_perfection_achievement.png` |
| Nearing Perfection | Complete 20 missions perfectly. | 300 | 1,000 | `nearing_perfection_achievement.png` |
| Total Perfection | Complete all 36 main missions perfectly. | 300 | 2,000 | `total_perfection_achievement.png` |

## Resource And Upgrade Achievements

| Achievement | Requirement | Credits | Score | Image |
| --- | --- | ---: | ---: | --- |
| Living Forever | Reach the maximum life count of 99. | 300 | 750 | `living_forever_achievement.png` |
| Fully Upgraded | Purchase every upgrade at least once. Extra lives and shield charges count if the player has more than the starting/default amount. | 0 | 1,500 | `fully_upgraded_achievement.png` |
| Quartermaster | Sell at least 50 lives and at least 50 shield charges. | 300 | 1,000 | `quartermaster_achievement.png` |

Fully Upgraded unlocks the sixth shield slot.

## Completion Achievement

| Achievement | Requirement | Credits | Score | Image |
| --- | --- | ---: | ---: | --- |
| Typing Master | Complete all 36 main missions. | 10,000 | 5,000 | `typing_master_achievement.png` |

## Shield Achievement

| Achievement | Requirement | Credits | Score | Image |
| --- | --- | ---: | ---: | --- |
| Shields Up | Start a mission with 6 shield charges, use all 6 charges during that mission, win, and finish without taking damage. | 300 | 300 | `shields_up_achievement.png` |

## Disabled Images

When an achievement has not been earned yet, the achievements modal looks for a disabled version of the image by adding `_disabled` before the extension.

Examples:

- `living_forever_achievement_disabled.png`
- `total_perfection_achievement_disabled.png`
- `shields_up_achievement_disabled.png`
