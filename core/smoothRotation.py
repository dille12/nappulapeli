import math


def smoothRotationFactorORG(angleVel, gainFactor, diff):
    dir = 1 if diff > 0 else -1
    decelarationTicks = abs(angleVel/gainFactor)
    distanceDecelerating = angleVel*decelarationTicks-0.5*dir*gainFactor*decelarationTicks**2
    acceleratingMod = 1 if distanceDecelerating < diff else -1
    return acceleratingMod * gainFactor

def smoothRotationFactor(angleVel, gainFactor, diff):
    """
    Improved version of your original physics-based approach
    Calculates exact stopping distance and decelerates only when needed
    """
    dir = 1 if diff > 0 else -1
    gainFactor *= min(1, abs(diff) * 3)

    # Your original calculation - time needed to decelerate to zero
    if abs(angleVel) < 1e-6:  # Avoid division by zero
        decelarationTicks = 0
    else:
        decelarationTicks = abs(angleVel / gainFactor)
    # Your original calculation - distance covered while decelerating
    distanceDecelerating = angleVel * decelarationTicks - 0.5 * dir * gainFactor * decelarationTicks**2
    
    acceleratingMod = 1 if distanceDecelerating < diff else -1
    
    return acceleratingMod * gainFactor



import random
# Test both versions
if __name__ == "__main__":

    # Test the improved version
    angle_vel = 0
    gain_factor = 0.2
    angle = 300
    angle_target = 0
    hits = 0
    print("Improved physics-based rotation:")
    for tick in range(1000):
        diff = angle_target - angle
        if abs(diff) < 0.01:
            print(f"Reached target at tick {tick}")
            print("Diff:", diff)
            angle_target = random.randint(0, 360)
            hits += 1
            
        torque = smoothRotationFactor(angle_vel, gain_factor, diff)
        angle_vel += torque
        angle += angle_vel
        
        if tick % 30 == 0:
            print(f"Tick {tick}: angle={angle:.2f}, vel={angle_vel:.3f}, diff={diff:.2f}, torque={torque:.3f}")
        
            
    
    print(f"Final: angle={angle:.2f}, target={angle_target}, error={abs(angle_target-angle):.3f}")
    print("HITS:", hits)