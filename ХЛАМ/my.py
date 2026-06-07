from datetime import datetime, timedelta
from random import randrange
from re import search

start = datetime(2023, 1, 1)
end = datetime(2023, 12, 31)

delta = (end - start).days + 1

with open("visits.log", "w", encoding="UTF-8") as f:
    for _ in range(1000):
        f.write(f"{start + timedelta(days=randrange(delta))} user_{randrange(201)}\n")


with open("visits.log", "r", encoding="UTF-8") as f:
    users = {}
    weeks = {}

    for line in f:

        key = search(r"user_\d{1,3}", line).group()
        users[key] = users.get(key, 0) + 1

        key = datetime.strptime(
            search(r"\d{4}(-\d\d){2}", line).group(), "%Y-%m-%d"
        ).strftime("%A")
        weeks[key] = weeks.get(key, 0) + 1

print(f"Самый активный пользователь: {max(users, key=users.get)}")
print(f"Самый посещаемый день недели: {max(weeks, key=weeks.get)}")
