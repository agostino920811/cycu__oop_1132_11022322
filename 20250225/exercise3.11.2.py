def print_right(text):
    # Calculate the number of leading spaces required
    spaces = ' ' * (40 - len(text))
    # Concatenate spaces and the text, then print
    print(spaces + text)

print_right("Monty")
print_right("Python's")
print_right("Flying Circus")