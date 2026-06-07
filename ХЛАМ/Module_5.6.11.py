from random import randint


class Dice:
    def __init__(self, sides):
        self.sides = sides

    def __call__(self):
        return randint(1, self.sides)


# INPUT DATA:

print()
print("# TEST_1:")
kingdice = Dice(6)

print(kingdice() in [1, 2, 3, 4, 5, 6])
print(kingdice() in [1, 2, 3, 4, 5, 6])
print(kingdice() in [7, 8, 9, 10])

print()
print("# TEST_2:")
kingdice = Dice(2)

print(kingdice() in [1, 2, 3, 4, 5, 6])
print(kingdice() in [3, 4])
print(kingdice() in [7, 8, 9, 10])

print()
print("# TEST_3:")
kingdice = Dice(1)

print(kingdice() == 1)
print(kingdice() in [1, 2])
print(kingdice() in [3, 4])
print(kingdice() in [7, 8, 9, 10])

print()
print("# TEST_4:")
kingdice = Dice(100)

for _ in range(100):
    print(kingdice() in range(1, 101))

print()
print("# TEST_5:")
kingdice = Dice(20)
print(callable(kingdice))
