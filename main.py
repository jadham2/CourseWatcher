from twilio.rest import Client
from dotenv import load_dotenv
import datetime
import hashlib
import sqlite3
import urllib3
import requests
import os
import re

PURDUE_API_URL = "https://api.purdue.io/odata/"


def connectToDB(db_path: str):
    # Connect to the database and turn on foreign keys
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    return con, cur


def closeDB(con):
    # commit our changes and close the connection
    con.commit()
    con.close()


def register() -> str:
    username = ""
    while not username:
        username = input("\nEnter a new username: ")

        con, cur = connectToDB('app.db')
        cur.execute("SELECT * FROM Users WHERE username=?", (username,))
        rows = cur.fetchall()
        if rows:
            print("Username already exists. Please try another one.")
            username = ""

    password = input("Enter a new password: ")
    pass_hash = hashlib.sha256(password.encode()).hexdigest()

    cur.execute("INSERT INTO Users VALUES (?, ?)", (username, pass_hash,))

    closeDB(con)

    return username


def login() -> str:
    username = ""
    username = input("Enter username: ")

    con, cur = connectToDB('app.db')
    cur.execute("SELECT * FROM Users WHERE username=?", (username,))
    rows = cur.fetchall()
    closeDB(con)

    if not rows:
        print("Username does not exist.")
        return ""

    password = input("Enter password: ")
    password = hashlib.sha256(password.encode()).hexdigest()

    if password != rows[0][1]:
        print("Incorrect password.")
        return ""

    print("Login succesful.")

    return username


def handle_user() -> str:
    print("Are you a new user or an existing user?")
    print("1. New User\n2. Existing User")
    user_status = 0

    while user_status != '1' and user_status != '2' and user_status != 'done':
        user_status = input().lower()
        if user_status != '1' and user_status != '2' and user_status != 'done':
            print("Error! Invalid input. Please try again or type 'done' to quit.")

    if user_status == '1':
        username = register()
    elif user_status == '2':
        username = login()

    if user_status == 'done' or not username:
        return ""

    return username


def send_text_twilio(body: str, target_phone_num: str) -> bool:
    twilio_account_sid = os.environ['TWILIO_ACCOUNT_SID']
    twilio_auth_token = os.environ['TWILIO_AUTH_TOKEN']
    twilio_phone_num = os.environ['TWILIO_PHONE_NUM']
    twilio_client = Client(twilio_account_sid, twilio_auth_token)
    message = twilio_client.messages.create(
                        body=body,
                        from_=twilio_phone_num,
                        to=target_phone_num
                    )

    return message.sid


def getCourseTerm() -> str:
    course_term = ""
    while not course_term:
        print("What term are you looking at?")
        print("Type F for fall, Sp for Spring, and Sm for Summer; then the last 2 digits of the year.")
        print("For example, F21 for Fall 2021, Sp20 for Spring 2020, and Sm22 for Summer 2022.")
        print("Or, type 'quit' to quit.")
        print("-------------------------------------------")

        course_term = input().lower()
        sem_map = {'f': '10', 'sp': '20', 'sm': '30'}

        if course_term == 'quit':
            return ""

        if len(course_term) == 3:
            if course_term[0] != 'f':
                print("Invalid term. Please try again.")
                course_term = ""
                continue
            if not course_term[1:].isdigit():
                print("Invalid term. Please try again.")
                course_term = ""
                continue
            course_term = f"20{course_term[1:]}{sem_map[course_term[0]]}"
        elif len(course_term) == 4:
            if course_term[0:2] != 'sp' and course_term[0:2] != 'sm':
                print("Invalid term. Please try again.")
                course_term = ""
                continue
            if not course_term[2:].isdigit():
                print("Invalid term. Please try again.")
                course_term = ""
                continue
            course_term = f"20{course_term[2:]}{sem_map[course_term[0:2]]}"
        else:
            print("Invalid term. Please try again.")
            course_term = ""
            continue

    return course_term


def getCourseSubject() -> str:
    course_subject = ""
    while not course_subject:
        print("\nEnter course subject (e.g. ECE, CS, CGT) or 'quit' to quit.")
        print("-------------------------------------------")

        course_subject = input().lower()

        if course_subject == 'quit':
            return ""

        course_subject = course_subject.strip().upper()
        purdue_course_query = f"Subjects?$filter=Abbreviation eq '{course_subject}'"
        subject_response = requests.get(
            PURDUE_API_URL + purdue_course_query, verify=False
            ).json()

        if not subject_response['value']:
            print("Error! Invalid subject. Please make sure you typed the abbreviation.")
            course_subject = ""

    return course_subject


def getCourseNum(course_term: str, course_subject: str) -> str:
    course_num = ""
    while not course_num:
        print("\nChoose a course number from the following courses")
        print("-------------------------------------------")

        purdue_course_query = f"Courses?$expand=Classes($filter=Term/Code eq '{course_term}'; \
                                $expand=Sections($expand=Meetings)) \
                                &$filter=Subject/Abbreviation eq '{course_subject}' \
                                &$orderby=Number asc"
        courses_response = requests.get(
            PURDUE_API_URL + purdue_course_query, verify=False
        ).json()
        sem_map = {'10': 'Fall', '20': 'Spring', '30': 'Summer'}

        print(f"Courses in {sem_map[course_term[4:]]} {course_term[0:4]}:")

        for course in courses_response['value']:
            if course['Classes']:
                print(f"{course_subject} {course['Number']}: {course['Title']}")

        course_num_list = [course['Number'] for course in courses_response['value']]
        course_num = -1

        print("-------------------------------------------")

        while course_num not in course_num_list:
            course_num = input("Enter course number here: ").lower()
            if course_num == 'quit':
                return ""
            if course_num not in course_num_list:
                print("Error! Course number is not in the given list. Please try again or type 'quit' to quit. Make sure you type number exactly as it appears.")
                continue

    return course_num


def getCourseSection(course_term: str, course_subject: str, course_num: str) -> str:
    purdue_course_query = f"Courses?$expand=Classes($filter=Term/Code eq '{course_term}'; \
                        $expand=Sections($expand=Meetings)) \
                        &$filter=Subject/Abbreviation eq '{course_subject}' \
                        and Number eq '{course_num}'"
    courses_response = requests.get(
        PURDUE_API_URL + purdue_course_query, verify=False
    ).json()

    print("\nSelect a course")
    print("-------------------------------------------")

    for i, course in enumerate(courses_response['value']):
        print(f"{i+1}. {course['Title']}, {course['CreditHours']} credits")

    print("-------------------------------------------")

    course_ind = ""
    while not course_ind:
        course_ind = input("Enter choice here (or type 'quit' to quit): ")
        if course_ind == 'quit':
            return ""
        if not course_ind.isdigit() or int(course_ind) < 1 or int(course_ind) > len(courses_response['value']):
            print("\nError! Invalid choice. Please try again or type 'quit' to quit.")
            course_ind = ""
    course_ind = int(course_ind) - 1

    course_section = ""
    while course_section == "":
        print("\nPlease choose a section from the following\n------------------")

        for i, section in enumerate(courses_response['value'][course_ind]['Classes']):
            section = section['Sections'][0]
            meeting = section['Meetings'][0]

            start_time = meeting['StartTime']
            duration = meeting['Duration']

            start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%Sz")
            duration = re.match(r'^PT(?:(?P<hour>\d+)H)?(?:(?P<minute>\d+)M)?(?:(?P<second>\d+)S)?$', duration)
            duration = duration.groupdict(default=0)
            duration = datetime.timedelta(hours=int(duration['hour']), minutes=int(duration['minute']), seconds=int(duration['second']))

            end_time = start_time + duration
            time_fstring = "%I:%M %p"
            start_time = start_time.strftime(time_fstring)
            end_time = end_time.strftime(time_fstring)

            print(f"Section {i+1}")
            print(f"CRN: {section['Crn']}")
            print(f"Type: {section['Meetings'][0]['Type']}")
            print(f"Meeting Days: {section['Meetings'][0]['DaysOfWeek']}")
            print(f"Timeslot: {start_time} - {end_time}")
            print(f"Remaining spots: {section['RemainingSpace']}\n")

        course_section = input("Enter section number here: ")

        if course_section == 'quit':
            return ""
        if not course_section.isdigit() or int(course_section) < 1 or int(course_section) > len(courses_response['value'][course_ind]['Classes']):
            print("\nError! Invalid section. Please try again or type 'quit' to quit.")
            course_section = ""

    return course_section


def main():
    # username = handle_user()

    course_term = getCourseTerm()
    if not course_term:
        return

    course_subject = getCourseSubject()
    if not course_subject:
        return

    course_num = getCourseNum(course_term, course_subject)
    if not course_num:
        return

    course_section = getCourseSection(course_term, course_subject, course_num)
    if not course_section:
        return


if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    load_dotenv()
    main()
