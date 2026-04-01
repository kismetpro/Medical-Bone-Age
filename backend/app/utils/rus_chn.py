import math

# RUS-CHN Scoring Standard
SCORE_TABLE = {
    'female': {
        'Radius': [0, 10, 15, 22, 25, 40, 59, 91, 125, 138, 178, 192, 199, 203, 210],
        'Ulna': [0, 27, 31, 36, 50, 73, 95, 120, 157, 168, 176, 182, 189],
        'MCPFirst': [0, 5, 7, 10, 16, 23, 28, 34, 41, 47, 53, 66],
        'MCPThird': [0, 3, 5, 6, 9, 14, 21, 32, 40, 47, 51],
        'MCPFifth': [0, 4, 5, 7, 10, 15, 22, 33, 43, 47, 51],
        'PIPFirst': [0, 6, 7, 8, 11, 17, 26, 32, 38, 45, 53, 60, 67],
        'PIPThird': [0, 3, 5, 7, 9, 15, 20, 25, 29, 35, 41, 46, 51],
        'PIPFifth': [0, 4, 5, 7, 11, 18, 21, 25, 29, 34, 40, 45, 50],
        'MIPThird': [0, 4, 5, 7, 10, 16, 21, 25, 29, 35, 43, 46, 51],
        'MIPFifth': [0, 3, 5, 7, 12, 19, 23, 27, 32, 35, 39, 43, 49],
        'DIPFirst': [0, 5, 6, 8, 10, 20, 31, 38, 44, 45, 52, 67],
        'DIPThird': [0, 3, 5, 7, 10, 16, 24, 30, 33, 36, 39, 49],
        'DIPFifth': [0, 5, 6, 7, 11, 18, 25, 29, 33, 35, 39, 49]
    },
    'male': {
        'Radius': [0, 8, 11, 15, 18, 31, 46, 76, 118, 135, 171, 188, 197, 201, 209],
        'Ulna': [0, 25, 30, 35, 43, 61, 80, 116, 157, 168, 180, 187, 194],
        'MCPFirst': [0, 4, 5, 8, 16, 22, 26, 34, 39, 45, 52, 66],
        'MCPThird': [0, 3, 4, 5, 8, 13, 19, 30, 38, 44, 51],
        'MCPFifth': [0, 3, 4, 6, 9, 14, 19, 31, 41, 46, 50],
        'PIPFirst': [0, 4, 5, 7, 11, 17, 23, 29, 36, 44, 52, 59, 66],
        'PIPThird': [0, 3, 4, 5, 8, 14, 19, 23, 28, 34, 40, 45, 50],
        'PIPFifth': [0, 3, 4, 6, 10, 16, 19, 24, 28, 33, 40, 44, 50],
        'MIPThird': [0, 3, 4, 5, 9, 14, 18, 23, 28, 35, 42, 45, 50],
        'MIPFifth': [0, 3, 4, 6, 11, 17, 21, 26, 31, 36, 40, 43, 49],
        'DIPFirst': [0, 4, 5, 6, 9, 19, 28, 36, 43, 46, 51, 67],
        'DIPThird': [0, 3, 4, 5, 9, 15, 23, 29, 33, 37, 40, 49],
        'DIPFifth': [0, 3, 4, 6, 11, 17, 23, 29, 32, 36, 40, 49]
    }
}

BONE_NAMES_CN = {
    'Radius': '桡骨 (Radius)',
    'Ulna': '尺骨 (Ulna)',
    'MCPFirst': '第一掌骨 (MCP1)',
    'MCPThird': '第三掌骨 (MCP3)',
    'MCPFifth': '第五掌骨 (MCP5)',
    'PIPFirst': '第一近节 (PIP1)',
    'PIPThird': '第三近节 (PIP3)',
    'PIPFifth': '第五近节 (PIP5)',
    'MIPThird': '第三中节 (MIP3)',
    'MIPFifth': '第五中节 (MIP5)',
    'DIPFirst': '第一远节 (DIP1)',
    'DIPThird': '第三远节 (DIP3)',
    'DIPFifth': '第五远节 (DIP5)'
}

def calc_bone_age_from_score(score, gender):
    """
    Calculate bone age (years) from total RUS-CHN score.
    Ref: Pyqt5-and-BoneAge-main/utils.py
    """
    if score is None or math.isnan(score):
        return 0.0

    # Formula is valid for score roughly 0-1000
    if gender == 'male':
        boneAge = 2.01790023656577 + (-0.0931820870747269)*score + math.pow(score,2)*0.00334709095418796 +\
        math.pow(score,3)*(-3.32988302362153E-05) + math.pow(score,4)*(1.75712910819776E-07) +\
        math.pow(score,5)*(-5.59998691223273E-10) + math.pow(score,6)*(1.1296711294933E-12) +\
        math.pow(score,7)* (-1.45218037113138e-15) +math.pow(score,8)* (1.15333377080353e-18) +\
        math.pow(score,9)*(-5.15887481551927e-22) +math.pow(score,10)* (9.94098428102335e-26)
    else:  # female
        boneAge = 5.81191794824917 + (-0.271546561737745)*score + \
        math.pow(score,2)*0.00526301486340724 + math.pow(score,3)*(-4.37797717401925E-05) +\
        math.pow(score,4)*(2.0858722025667E-07) +math.pow(score,5)*(-6.21879866563429E-10) + \
        math.pow(score,6)*(1.19909931745368E-12) +math.pow(score,7)* (-1.49462900826936E-15) +\
        math.pow(score,8)* (1.162435538672E-18) +math.pow(score,9)*(-5.12713017846218E-22) +\
        math.pow(score,10)* (9.78989966891478E-26)
    
    if math.isnan(boneAge) or math.isinf(boneAge):
        return 0.0
    return max(0, boneAge)

def find_score_for_age(target_age, gender):
    """
    Reverse lookup: find the total score that yields the closest bone age.
    """
    best_score = 0
    min_diff = float('inf')
    
    # RUS-CHN scores typically range 0-1000
    for s in range(0, 1001):
        age = calc_bone_age_from_score(s, gender)
        diff = abs(age - target_age)
        if diff < min_diff:
            min_diff = diff
            best_score = s
            
    return best_score

def generate_bone_report(predicted_age, gender):
    """
    Generate a detailed report with individual bone scores.
    Since the deep model predicts age directly, we infer the likely score distribution
    that would result in this age, assuming balanced development.
    """
    target_score = find_score_for_age(predicted_age, gender)
    
    # Get score table for gender
    table = SCORE_TABLE[gender]
    bones = list(table.keys())
    
    # Initialize all bones to stage 0
    current_stages = {b: 0 for b in bones}
    current_scores = {b: table[b][0] for b in bones}
    current_total = sum(current_scores.values())
    
    # Greedy algorithm to match target score
    # We iteratively upgrade the bone that is "furthest behind" (percentage wise)
    # or just simple round-robin for simplicity as development is usually synchronous.
    
    while current_total < target_score:
        best_upgrade_bone = None
        min_stage = float('inf')
        
        # Find bones that can still be upgraded
        candidates = []
        for b in bones:
            stage = current_stages[b]
            max_stage = len(table[b]) - 1
            if stage < max_stage:
                candidates.append(b)
                if stage < min_stage:
                    min_stage = stage
        
        if not candidates:
            break # Maxed out
            
        # Strategy: Prefer upgrading bones with lower stages to keep development balanced
        # Filter candidates to only those with min_stage
        best_candidates = [b for b in candidates if current_stages[b] == min_stage]
        
        # If multiple, pick one (e.g., Radius/Ulna first as they are major)
        # Or Just pick the first one
        upgrade_bone = best_candidates[0]
        
        # Perform upgrade
        old_score = current_scores[upgrade_bone]
        new_stage = current_stages[upgrade_bone] + 1
        new_score = table[upgrade_bone][new_stage]
        
        diff = new_score - old_score
        
        # Check if upgrading overshoots too much
        # If (current + diff) is closer to target than current, we do it.
        # But since we are strictly increasing, we just check if we are below target roughly.
        if abs(current_total + diff - target_score) > abs(current_total - target_score) and current_total > target_score * 0.95:
             # If we are already close and adding makes it worse (overshoot), stop?
             # Usually we want to get as close as possible.
             if (current_total + diff - target_score) > (target_score - current_total):
                 break
        
        current_stages[upgrade_bone] = new_stage
        current_scores[upgrade_bone] = new_score
        current_total += diff
        
    # Format result
    details = []
    for b in bones:
        details.append({
            'name': BONE_NAMES_CN[b],
            'stage': current_stages[b],
            'score': current_scores[b]
        })
        
    return {
        'total_score': current_total,
        'details': details,
        'target_score_lookup': target_score
    }
