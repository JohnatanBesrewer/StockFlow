import re
from datetime import datetime, timedelta
import calendar
from random import randrange, randint
from collections import Counter

file_name: str = "calls.log"
total_lns: int = 1500  # кол-во записей
max_dur: int = 600  # максимальная длительность
year: int = 2023  # год

all_num = Counter()  # уникальные номера
average_call_duration_by_month = Counter()  # средняя длительность звонка по месяцам
most_frequent_call_day = Counter()  # самый частый день звонков
longest_talkers = Counter()  # самые "долгие" абоненты


def gen_dt(yr: int = year) -> datetime:
    """расчёт случайных даты/времени"""
    delta = datetime(yr + 1, 1, 1) - (dt := datetime(yr, 1, 1))
    rnd_sec = randrange(int(delta.total_seconds()) - max_dur)
    return dt + timedelta(seconds=rnd_sec)


def gen_num() -> str:
    """расчёт номера телефона"""
    prefix = ("+7", "8")[randint(0, 1)] + (spr := (" ", "-", "")[randint(0, 2)])
    num = "9" + "".join(str(randint(0, 9)) for _ in range(9))
    num = "(" + num[:3] + ")" + num[3:] if not randint(0, 6) else num
    num = num[:-7] + spr + num[-7:-4] + spr + num[-4:-2] + spr + num[-2:]
    return prefix + num


def gen_file(fn: str = file_name):
    """генерация лог-файла"""
    caller_list = [gen_num() for _ in range(total_lns // 5)]
    callee_list = [gen_num() for _ in range(total_lns // 5)]
    try:
        with open(fn, "x", encoding="UTF8") as f:
            for _ in range(randint(1000, 1501)):
                f.write(
                    f"{gen_dt()} caller:{caller_list[randrange(len(caller_list))]} callee:{callee_list[randrange(len(callee_list))]} duration:{randrange(1, max_dur)}\n"
                )
        return file_name
    except FileExistsError as e:
        return e


def get_call_report(fn: str = file_name):
    """сбор статистики"""

    global all_num  # уникальные номера
    global average_call_duration_by_month  # средняя длительность звонка по месяцам
    global most_frequent_call_day  # самый частый день звонков
    global longest_talkers  # самые "долгие" абоненты

    num_norm = (
        lambda number: "+7" + "".join(c for c in number if c.isdigit())[-10:]
    )  # нормализация номера телефона
    dt_norm = lambda dt_str: datetime.strptime(
        dt_str, "%Y-%m-%d %H:%M:%S"
    )  # нормализация даты/времени

    dt_pattern = r"^\d{4}(-\d\d){2} \d\d(:\d\d){2}"
    num_pattern = r"(\+7|8)[- (]{0,2}\d{3}[- )]{0,2}\d{3}[- ]?\d\d[- ]?\d\d"
    dur_pattern = r"\d{1,3}$"

    try:
        with open(file_name, "r", encoding="UTF8") as f:
            for n, line in enumerate(f):
                if (
                    (dt := re.search(dt_pattern, line))
                    and (caller := re.search(num_pattern, line))
                    and (callee := re.search(num_pattern, line[caller.end() :]))
                    and (dur := re.search(dur_pattern, line))
                ):
                    all_num.update(
                        [num_norm(caller.group()), num_norm(callee.group())]
                    )  #  номер: количество
                    average_call_duration_by_month.update(
                        {
                            dt_norm(dt.group()).strftime("%B"): int(dur.group())
                        }  #  месяц: продолжительность
                    )
                    most_frequent_call_day.update(
                        {dt_norm(dt.group()).strftime("%A"): 1}
                    )  #  день ненели: количество
                    longest_talkers.update(
                        {
                            num_norm(caller.group()): int(dur.group()),
                            num_norm(callee.group()): int(dur.group()),
                        }  #  номер: продолжительность
                    )
                else:
                    continue
    except OSError as e:
        return e


def print_result():
    print(f"Уникальных номеров: {len(all_num)}")
    print()
    print("Топ-10 активных абонентов:")
    for num, cnt in all_num.most_common(10):
        print(f"    {num} — {cnt} зв.")
    print()
    print("Средняя длительность по месяцам:")
    for m in calendar.month_name[1:]:
        print(
            f"{m}: {round(average_call_duration_by_month[m] / calendar.monthrange(year, list(calendar.month_name).index(m))[1])} сек."
        )
    print()
    print(f"Самый звонкий день недели: {most_frequent_call_day.most_common(1)[0][0]}")
    print()
    print("Топ-10 по суммарному времени:")
    for num, dur in longest_talkers.most_common(10):
        print(f"    {num} — {dur} сек.")


gen_file()
get_call_report()
print_result()
