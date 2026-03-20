import csv
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime

# webscrape the html page from Schedule Builder
html_doc = open("Schedule Builder.html")
soup = BeautifulSoup(html_doc, 'html.parser')
courses = soup.find_all(class_='classTitle')

# courses_info initially contains header row
courses_info = []

# put course info from Schedule Builder into a list
for course in courses:
    class_title = course.text.split(' - ')
    class_next = course.find_next('div').find(class_='meeting-times')
    if class_next:
        class_divs = class_next.find_all(class_='clearfix')
        for class_ in class_divs:
            info_divs = class_.find_all('div')
            class_info = [class_title[0], class_title[1]]
            for div in info_divs:
                class_info.append(div.text)
            courses_info.append(class_info)

# figure out the exact dates of courses from the days of the week and add them to a pandas df
starting_date = date(2026, 3, 26)
weekdays = ['M','T','W','R','F','Sat','Sun']

# modify courses_info to match Google Calendar csv requirements
modified_courses_info = []
for row in courses_info:
    # instead of letter days, write actual dates
    row_dates = []
    for a_day in row[4]:
        idx = weekdays.index(a_day)
        date = starting_date
        while date.weekday() != idx:
            date = date + timedelta(1)
        row_dates.append(date.strftime("%m/%d/%Y"))
        row[4] = row_dates

    # instead of writing both the class title and type, include the class type in the title
    title = row[0] + ' (' + row[2] + ')'
    row[0] = title
    del row[2]

    # split out the start time & end time
    times = row[2].split(' - ')
    row[2] = times[0]
    row.insert(3, times[1])

    # make a row for each date
    for day in row[4]:
        new_row = [day if row.index(item) == 4 else item for item in row]
        modified_courses_info.append(new_row)

# change the order of columns to match Google Calendar
for a_row in modified_courses_info:
    subject = a_row[0]
    description = a_row[1]
    start_time = a_row[2]
    end_time = a_row[3]
    start_date = a_row[4]
    end_date = a_row[4]
    location = a_row[5]
    modified_row = [subject, start_date, start_time, end_date, end_time, description, location]
    row_idx = modified_courses_info.index(a_row)
    modified_courses_info[row_idx] = modified_row

modified_courses_info.insert(0,['Subject','Start date','Start time', 'End date','End time','Description','Location'])


# create a csv out of the list from webscraping Schedule Builder
with open('output_list.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(modified_courses_info)