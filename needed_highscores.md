# Needed High Scores

The **High Scorer** badge for a level is earned when your end-of-mission **Points** meet or exceed the goal below.

Goal formula (per issue #15, as specified): `drone_target*100 + power_ups*100 + 1000 + final_boss_value + semi_bosses*200 + 2000`
- `power_ups` = 4 (MAX_LIFE_POWER_UPS_PER_MISSION)
- `final_boss_value` = 1000 when the level has a final boss (lessons 5+), else 0
- `semi_bosses` = scheduled mini-bosses for the level

> These are computed defaults. Tune by editing the formula/inputs in `src/lessons/mission_engine.py` (`high_score_goal`).

| Lesson | Title | Drone target | Semi-bosses | Final boss | **High score needed** |
|-------:|-------|-------------:|------------:|-----------:|----------------------:|
| 1 | Home Row Beacons | 30 | 0 | no | **6400** |
| 2 | Middle Finger Control | 30 | 0 | no | **6400** |
| 3 | Ring Finger Control | 40 | 4 | no | **8200** |
| 4 | Pinky Home Row | 40 | 4 | no | **8200** |
| 5 | Inner Home Row | 51 | 5 | yes | **10500** |
| 6 | Top Row Index Reach | 52 | 5 | yes | **10600** |
| 7 | Top Row Middle Reach | 53 | 5 | yes | **10700** |
| 8 | Top Row Ring Reach | 54 | 5 | yes | **10800** |
| 9 | Top Row Pinky Reach | 55 | 5 | yes | **10900** |
| 10 | Top Row Center Reach | 56 | 5 | yes | **11000** |
| 11 | Bottom Row Index Reach | 57 | 5 | yes | **11100** |
| 12 | Bottom Row Middle Reach | 58 | 5 | yes | **11200** |
| 13 | Bottom Row Ring Reach | 59 | 5 | yes | **11300** |
| 14 | Bottom Row Pinky Reach | 60 | 6 | yes | **11600** |
| 15 | Bottom Row Center Reach | 61 | 6 | yes | **11700** |
| 16 | Enter Control | 62 | 6 | yes | **11800** |
| 17 | Correction Controls | 63 | 6 | yes | **11900** |
| 18 | Left Edge Controls | 64 | 6 | yes | **12000** |
| 19 | Punctuation Reach One | 65 | 6 | yes | **12100** |
| 20 | Bracket Reach | 66 | 6 | yes | **12200** |
| 21 | Right Edge Symbols | 67 | 6 | yes | **12300** |
| 22 | Number Row Edges | 68 | 6 | yes | **12400** |
| 23 | Number Row Ring Reach | 69 | 6 | yes | **12500** |
| 24 | Number Row Middle Reach | 70 | 7 | yes | **12800** |
| 25 | Number Row Index Reach | 71 | 7 | yes | **12900** |
| 26 | Number Row Center Reach | 72 | 7 | yes | **13000** |
| 27 | Shifted Number Edges | 73 | 7 | yes | **13100** |
| 28 | Shifted Ring Numbers | 74 | 7 | yes | **13200** |
| 29 | Shifted Middle Numbers | 75 | 7 | yes | **13300** |
| 30 | Shifted Index Numbers | 76 | 7 | yes | **13400** |
| 31 | Shifted Center Numbers | 77 | 7 | yes | **13500** |
| 32 | Shifted Home Punctuation | 78 | 7 | yes | **13600** |
| 33 | Shifted Bottom Punctuation | 79 | 7 | yes | **13700** |
| 34 | Question And Underscore | 80 | 8 | yes | **14000** |
| 35 | Shifted Brackets | 81 | 8 | yes | **14100** |
| 36 | Final Symbol Controls | 82 | 8 | yes | **14200** |

