# Growth Standards and Height Prediction Utilities
# Data approximated from Chinese Children Growth Standards and TW3/BP methods

def get_percent_adult_height(bone_age, gender):
    """
    Returns the approximate percentage of adult height reached at a given BONE AGE.
    Based on Bayley-Pinneau tables (simplified curve fitting).
    """
    # Simple polynomial approximation for percentages
    # Age range: 6 - 18
    ba = max(6, min(bone_age, 18))
    
    if gender == 'male':
        # Boys curve approximation
        # Age 6: ~68%, Age 10: ~78%, Age 13: ~87%, Age 15: ~96%, Age 17: 99%
        if ba < 10:
             return 0.68 + (ba - 6) * 0.025
        elif ba < 13:
             return 0.78 + (ba - 10) * 0.03
        elif ba < 15:
             return 0.87 + (ba - 13) * 0.045
        elif ba < 17:
             return 0.96 + (ba - 15) * 0.015
        else:
             return 0.99 + (ba - 17) * 0.005
             
    else: # female
        # Girls curve approximation (earlier maturity)
        # Age 6: ~70%, Age 9: ~80%, Age 11: ~88%, Age 13: ~96%, Age 15: 99%
        if ba < 9:
             return 0.70 + (ba - 6) * 0.033
        elif ba < 11:
             return 0.80 + (ba - 9) * 0.04
        elif ba < 13:
             return 0.88 + (ba - 11) * 0.04
        elif ba < 15:
             return 0.96 + (ba - 13) * 0.015
        else:
             return 0.99 + (ba - 15) * 0.005

def predict_adult_height(current_height_cm, bone_age_years, gender):
    """
    Predict adult height based on current height and bone age.
    Formula: Predicted = Current / %_completed_at_bone_age
    """
    if not current_height_cm or current_height_cm <= 0:
        return None
        
    percent_completed = get_percent_adult_height(bone_age_years, gender)
    
    predicted_height = current_height_cm / percent_completed
    
    # Sanity limits
    predicted_height = min(max(predicted_height, 140), 220)
    
    return round(predicted_height, 1)

def get_chn_standard_height(age, gender):
    """
    Get standard height (50th percentile) for CHRONOLOGICAL age (Chinese Standard).
    Used for comparison.
    """
    # Very rough linear approx for demo 
    # Boys: 75cm at 1y, 172cm at 18y
    # Girls: 74cm at 1y, 160cm at 18y
    
    age = max(1, min(age, 18))
    
    if gender == 'male':
        # Simplistic curve
        if age <= 2: return 75 + (age-1)*10
        if age <= 12: return 85 + (age-2)*6.5
        return 150 + (age-12)*4 # spurt
    else:
        if age <= 2: return 74 + (age-1)*10
        if age <= 10: return 84 + (age-2)*6.5
        return 136 + (age-10)*2.5 # slower end
        
