LESSON_PROGRESS = [
    (1, ("f", "j"), "Left index finger, right index finger", "Home Row Beacons", "Practice F and J by defending your training pod."),
    (2, ("d", "k", "space"), "Left middle finger, right middle finger, thumbs", "Middle Finger Control", "Add D, K, and ␣ while keeping F and J ready."),
    (3, ("s", "l"), "Left ring finger, right ring finger", "Ring Finger Control", "Add S and L to your home row formation."),
    (4, ("a", ";"), "Left pinky finger, right pinky finger", "Pinky Home Row", "Add A and semicolon with steady pinky control."),
    (5, ("g", "h"), "Left index finger, right index finger", "Inner Home Row", "Reach inward for G and H, then return to F and J."),
    (6, ("r", "u"), "Left index finger, right index finger", "Top Row Index Reach", "Add R and U from the top row."),
    (7, ("e", "i"), "Left middle finger, right middle finger", "Top Row Middle Reach", "Add E and I with your middle fingers."),
    (8, ("w", "o"), "Left ring finger, right ring finger", "Top Row Ring Reach", "Add W and O with your ring fingers."),
    (9, ("q", "p"), "Left pinky finger, right pinky finger", "Top Row Pinky Reach", "Add Q and P with your pinkies."),
    (10, ("t", "y"), "Left index finger, right index finger", "Top Row Center Reach", "Add T and Y with index finger control."),
    (11, ("v", "m"), "Left index finger, right index finger", "Bottom Row Index Reach", "Add V and M from the bottom row."),
    (12, ("c", ","), "Left middle finger, right middle finger", "Bottom Row Middle Reach", "Add C and comma with your middle fingers."),
    (13, ("x", "."), "Left ring finger, right ring finger", "Bottom Row Ring Reach", "Add X and period with your ring fingers."),
    (14, ("z", "/"), "Left pinky finger, right pinky finger", "Bottom Row Pinky Reach", "Add Z and slash with your pinkies."),
    (15, ("b", "n"), "Left index finger, right index finger", "Bottom Row Center Reach", "Add B and N with index finger control."),
    (16, ("enter",), "Right pinky finger", "Enter Control", "Add Enter to your typing controls."),
    (17, ("shift", "backspace"), "Pinkies, right pinky finger", "Correction Controls", "Add Shift and Backspace control."),
    (18, ("tab", "caps lock"), "Left pinky finger", "Left Edge Controls", "Add Tab and Caps Lock with the left pinky finger."),
    (19, ("'", "-"), "Right pinky finger", "Punctuation Reach One", "Add apostrophe and hyphen."),
    (20, ("[", "]"), "Right pinky finger", "Bracket Reach", "Add left and right brackets."),
    (21, ("\\", "="), "Right pinky finger", "Right Edge Symbols", "Add backslash and equals."),
    (22, ("1", "0"), "Pinkies", "Number Row Edges", "Add 1 and 0 from the number row."),
    (23, ("2", "9"), "Ring fingers", "Number Row Ring Reach", "Add 2 and 9 from the number row."),
    (24, ("3", "8"), "Middle fingers", "Number Row Middle Reach", "Add 3 and 8 from the number row."),
    (25, ("4", "7"), "Index fingers", "Number Row Index Reach", "Add 4 and 7 from the number row."),
    (26, ("5", "6"), "Index fingers", "Number Row Center Reach", "Add 5 and 6 from the number row."),
    (27, ("!", ")"), "Shift + 1, Shift + 0", "Shifted Number Edges", "Add exclamation mark and right parenthesis."),
    (28, ("@", "("), "Shift + 2, Shift + 9", "Shifted Ring Numbers", "Add at sign and left parenthesis."),
    (29, ("#", "*"), "Shift + 3, Shift + 8", "Shifted Middle Numbers", "Add hash and asterisk."),
    (30, ("$", "&"), "Shift + 4, Shift + 7", "Shifted Index Numbers", "Add dollar sign and ampersand."),
    (31, ("%", "^"), "Shift + 5, Shift + 6", "Shifted Center Numbers", "Add percent and caret."),
    (32, (":", '"'), "Shift + ;, Shift + '", "Shifted Home Punctuation", "Add colon and quotation mark."),
    (33, ("<", ">"), "Shift + comma, Shift + period", "Shifted Bottom Punctuation", "Add less-than and greater-than."),
    (34, ("?", "_"), "Shift + slash, Shift + hyphen", "Question And Underscore", "Add question mark and underscore."),
    (35, ("{", "}"), "Shift + [, Shift + ]", "Shifted Brackets", "Add left and right braces."),
    (36, ("|", "+"), "Shift + backslash, Shift + equals", "Final Symbol Controls", "Add pipe and plus."),
]


LESSONS_BY_NUMBER = {number: item for number, *item in LESSON_PROGRESS}


def learned_keys_through(lesson_number):
    keys = []
    for number, lesson_keys, *_ in LESSON_PROGRESS:
        if number > lesson_number:
            break
        keys.extend(lesson_keys)
    return tuple(keys)


def lesson_title(lesson_number):
    _, _, title, _ = LESSONS_BY_NUMBER[lesson_number]
    return title


def lesson_new_keys(lesson_number):
    keys, _, _, _ = LESSONS_BY_NUMBER[lesson_number]
    return keys


def lesson_fingers(lesson_number):
    _, fingers, _, _ = LESSONS_BY_NUMBER[lesson_number]
    return fingers
