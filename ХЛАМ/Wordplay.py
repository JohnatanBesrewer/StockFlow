class Wordplay:
    def __init__(self, words=None):
        self.words = [word for word in words] if words else []

    def add_word(self, word):
        self.words.append(word) if word not in self.words else None

    def words_with_length(self, n):
        return list(filter(lambda x: len(x) == n, self.words))

    def only(self, *args):
        return [word for word in self.words if all(ch in args for ch in word)]

    def avoid(self, *args):
        return [word for word in self.words if all(ch not in args for ch in word)]


# INPUT DATA:

# TEST_1:
wordplay = Wordplay()

print(wordplay.words_with_length(1))
print(wordplay.only("a", "b", "c"))
print(wordplay.avoid("a", "b", "c"))
print()

# TEST_2:
wordplay = Wordplay()

print(wordplay.words)
wordplay.add_word("bee")
wordplay.add_word("geek")
print(wordplay.words)
print()

# TEST_3:
wordplay = Wordplay(["bee", "geek", "cool", "stepik"])

wordplay.add_word("python")
print(wordplay.words_with_length(4))
print()

# TEST_4:
wordplay = Wordplay(["o", "to", "otto", "top", "t"])

print(wordplay.only("o", "t"))
print()

# TEST_5:
wordplay = Wordplay(["a", "arthur", "timur", "bee", "geek", "python", "stepik"])

print(wordplay.avoid("a", "b", "c"))
print()

# TEST_6:
wordplay = Wordplay()
print(wordplay.words)
print()

# TEST_7:
wordplay = Wordplay(
    ["Тьюринг", "Торвальдс", "Россум", "Гейтс", "Гамильтон", "Бэкус", "Кнут"]
)
print()

print(wordplay.words_with_length(6))
print(wordplay.avoid("ь"))
print()

# TEST_8:
words = ["Лейбниц", "Бэббидж", "Нейман", "Джобс", "да_Винчи", "Касперский"]
wordplay = Wordplay(words)

words.extend(["Гуев", "Харисов", "Светкин"])
print(words)
print(wordplay.words)
print()

# TEST_9:
wordplay = Wordplay(["a", "arthur", "timur", "bee", "geek", "python", "stepik"])

print(wordplay.words)
wordplay.add_word("stepik")
wordplay.add_word("bee")
wordplay.add_word("geek")
print(wordplay.words)
print()
