import calendar
import math
import os
from datetime import datetime
from pytz import timezone
tz = timezone('US/Eastern')

from PIL import ImageFont, Image, ImageDraw

import utils

user_calendar = utils.JOpen("cache/calendar.json", "r+")

STRING_MONTHS = {"1": "January", "2": "February", "3": "March", "4": "April", "5": "May", "6": "June", "7": "July",
    "8": "August", "9": "September", "10": "October", "11": "November", "12": "December"}

roboto_path = os.path.join(os.getcwd(), 'assets/Roboto/Roboto-Medium.ttf')
print(roboto_path)
roboto_font = ImageFont.truetype(roboto_path, 40)
activity_font = ImageFont.truetype(roboto_path, 20)
month_path = os.path.join(os.getcwd(), 'assets/Dancing_Script/DancingScript-VariableFont_wght.ttf')
month_font = ImageFont.truetype(month_path, 140)

def schedule(task, date, ctime, user_id):
    user_id = str(user_id)
    ym = str(date.month) + "/" + str(date.year)
    day = str(date.day)
    if ym not in user_calendar:
        user_calendar[ym] = {}
    ydict = user_calendar[ym]
    if day not in ydict:
        ydict[day] = {}
    daydict = ydict[day]
    if user_id not in daydict:
        daydict[user_id] = {}
    current = daydict[user_id]
    if ctime not in current:
        current[ctime] = [task]
    else:
        current[ctime].append(task)
    utils.JOpen("cache/calendar.json", "w+", user_calendar)

def get_plans(month, year, day, ctime):
    ydict = user_calendar.get(f'{month}/{year}', {})
    daydict = ydict.get(str(day), {})
    plans = {}
    [plans.setdefault(user_id, daydict[user_id][ctime]) for user_id in daydict.keys() if ctime in daydict[user_id]]
    return plans

def display(month, year, user_id):

    day = int(datetime.now(tz=tz).day)

    img = Image.open(os.path.join(os.getcwd(), "assets/calendar.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)

    user_id = str(user_id)
    cal = calendar.Calendar()
    xs = 0
    y = 360
    a = 0
    ym = month + "/" + year
    ydict = user_calendar.get(ym, {})
    user_days = [key for key in ydict.keys() if user_id in ydict[key].keys()]

    m = STRING_MONTHS[str(month)]
    shift = 9-len(m)

    draw.text((740+(shift*24), 50), STRING_MONTHS[str(month)], (0, 0, 0), font=month_font)

    for i in (cal.itermonthdays(int(year), int(month))):
        comp_x = 0 if a >= 10 else 12
        date = str(i) if i != 0 else ''
        comp_x = 16 if i >= 6 and i <= 9 else comp_x
        color = (0, 0, 0) if i != day else (255, 87, 51)
        draw.text((188 + xs + comp_x, y), date, color, font=roboto_font)
        color = (14, 218, 14) if i >= day else (164, 0, 0)
        if str(i) in user_days:
            tasks = []
            ttasks = ydict[str(i)][user_id].values()
            for t in ttasks: tasks += t
            draw.text((188 + xs + comp_x, y + 40), "\n".join(tasks), color, font=activity_font)
        a += 1
        xs += 240
        if a % 7 == 0:
            xs = 0
            y += 190
    img.save(os.path.join(os.getcwd(), "assets/temp_calendar.png"))
    return True