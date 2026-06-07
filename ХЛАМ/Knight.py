class Knight:
    def __init__(self, horizontal, vertical, color):
        self.horizontal = horizontal
        self.vertical = vertical
        self.color = color

    def get_char(self):
        return "N"

    def can_move(self, horizontal, vertical):
        x1 = "abcdefgh".index(self.horizontal)
        y1 = self.vertical - 1
        x2 = "abcdefgh".index(horizontal)
        y2 = vertical - 1
        if (
            abs(x1 - x2) == 1
            and abs(y1 - y2) == 2
            or abs(x1 - x2) == 2
            and abs(y1 - y2) == 1
        ):
            return True
        else:
            return False

    def move_to(self, horizontal, vertical):
        if self.can_move(horizontal, vertical):
            self.horizontal = horizontal
            self.vertical = vertical

    def draw_board(self):
        chessboard = [["." for _ in range(8)] for _ in range(8)]
        x = "abcdefgh".index(self.horizontal)
        y = self.vertical - 1
        chessboard[y][x] = self.get_char()

        for i in range(7, -1, -1):
            for j in range(8):
                if self.can_move("abcdefgh"[j], i + 1):
                    chessboard[i][j] = "*"
                print(chessboard[i][j], end="")
            print()


# INPUT DATA:

print("TEST_1:")
knight = Knight("c", 3, "white")

print(knight.color, knight.get_char())
print(knight.horizontal, knight.vertical)
print()

print("TEST_2:")
knight = Knight("c", 3, "white")

print(knight.horizontal, knight.vertical)
print(knight.can_move("e", 5))
print(knight.can_move("e", 4))

knight.move_to("e", 4)
print(knight.horizontal, knight.vertical)
print()

print("TEST_3:")
knight = Knight("c", 3, "white")

knight.draw_board()
print()

print("TEST_4:")
knight = Knight("e", 5, "black")

knight.draw_board()
knight.move_to("d", 3)
print()
knight.draw_board()
print()

print("TEST_5:")
knight = Knight("a", 1, "white")

knight.draw_board()
knight.move_to("e", 8)
print()
knight.draw_board()
print()

print("TEST_6:")
knight = Knight("g", 7, "black")
knight.draw_board()
print()

print("TEST_7:")
knight = Knight("d", 8, "white")
knight.draw_board()
print()

print("TEST_8:")
knight = Knight("h", 1, "black")
knight.draw_board()
