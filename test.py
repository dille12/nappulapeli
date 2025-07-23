import matplotlib.pyplot as plt
import numpy as np



ts = np.linspace(0, 1, 200)
angles = [reload_rotation(t) for t in ts]

plt.plot(ts, angles)
plt.xlabel("Normalized Time (t)")
plt.ylabel("Rotation Angle (degrees)")
plt.title("Weapon Reload Rotation Curve")
plt.grid(True)
plt.show()