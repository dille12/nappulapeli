def ease(t):
    return 3*t**2 - 2*t**3

def melee_animation(t):
    # Initialize
    x, y, angle = 0.0, 0.0, 0.0

    if t < 0.15:
        k = ease(t / 0.15)
        x = -10 * k       # pull back
        y = 5 * k
        angle = -20 * k

    elif t < 0.5:
        k = ease((t - 0.15) / 0.35)
        x = -10 + (30 * k)  # forward thrust
        y = 5 - (10 * k)
        angle = -20 + (80 * k)

    else:
        k = ease((t - 0.5) / 0.5)
        x = 20 * (1 - k)  # retract
        y = -5 * (1 - k)
        angle = 60 * (1 - k)

    return x, y, angle
import matplotlib.pyplot as plt
import numpy as np

ts = np.linspace(0, 1, 200)
xs, ys, angles = zip(*[melee_animation(t) for t in ts])

plt.figure(figsize=(12, 4))

plt.subplot(1, 3, 1)
plt.plot(ts, xs)
plt.title("X Offset")

plt.subplot(1, 3, 2)
plt.plot(ts, ys)
plt.title("Y Offset")

plt.subplot(1, 3, 3)
plt.plot(ts, angles)
plt.title("Rotation (degrees)")

plt.tight_layout()
plt.show()
