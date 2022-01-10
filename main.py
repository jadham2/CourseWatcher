from twilio.rest import Client
from dotenv import load_dotenv
import hashlib
import sqlite3


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
        username = input("Enter a new username: ")

        con, cur = connectToDB('app.db')
        cur.execute("SELECT * FROM Users WHERE username=?", (username,))
        rows = cur.fetchall()
        if rows:
            print("Username already exists. Please try another one.\n")
            username = ""

    password = input("Enter a new password.")
    pass_hash = hashlib.sha256(password.encode()).hexdigest()

    cur.execute("INSERT INTO Users VALUES (?, ?)", (username, pass_hash,))

    closeDB(con)

    return username


def login() -> str:
    username = ""
    username = input("What is your username? ")

    con, cur = connectToDB('app.db')
    cur.execute("SELECT * FROM Users WHERE username=?", (username,))
    rows = cur.fetchall()
    if not rows:
        print("Username does not exist.\n")
        return ""


def main():
    print("Are you a new user or an existing user?")
    print("1. New User\n2. Existing User")
    user_status = 0

    while user_status != '1' and user_status != '2' and user_status != 'done':
        user_status = input().lower()
        if user_status != '1' and user_status != '2' and user_status != 'done':
            print("Error! Invalid input. Please try again or type 'done' to quit.")

    if user_status == 1:
        username = register()
    elif user_status == 2:
        username = login()
        if not username:
            return
    else:


if __name__ == "__main__":
    load_dotenv()
    main()
