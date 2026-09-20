import numpy as np
import matplotlib.pyplot as plt

N = np.arange(1, 101)
y = 1 / np.sqrt(N)

plt.plot(N, y)

# Add a marker at N=30
n_marker = 30
y_marker = 1 / np.sqrt(n_marker)
plt.plot(n_marker, y_marker, 'ro')  # 'ro' creates a red circle marker

plt.xlabel('N')
plt.ylabel('$1/\\sqrt{N}$')
plt.title('Plot of $1/\\sqrt{N}$ for N from 1 to 100 with a marker at N=30')
plt.grid(True)
plt.savefig('figures/Chapter3/RootN.png')