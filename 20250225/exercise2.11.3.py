import math

# Part 1: Volume of a sphere
radius = 5  # radius in centimeters
volume = (4/3) * math.pi * radius**3  # volume in cubic centimeters
print(f"Volume of the sphere: {volume} cubic centimeters")  # Displaying the result

# Part 2: Trigonometric identity (sin²(x) + cos²(x) = 1)
x = 42  # angle in radians

# Calculate sine and cosine
sin_x = math.sin(x)
cos_x = math.cos(x)

# Compute the sum of their squares
result = sin_x**2 + cos_x**2
print(f"sin²(x) + cos²(x) = {result}")  # Display the result, should be close to 1

# Part 3: Exponentiation with e
e = math.e  # Get the value of e

# Method 1: Using the exponentiation operator
exp1 = e**2

# Method 2: Using math.pow
exp2 = math.pow(e, 2)

# Method 3: Using math.exp (exponentiation of the argument)
exp3 = math.exp(2)

print(f"Using ** operator: e^2 = {exp1}")
print(f"Using math.pow: e^2 = {exp2}")
print(f"Using math.exp: e^2 = {exp3}")
