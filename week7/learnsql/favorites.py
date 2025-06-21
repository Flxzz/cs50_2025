from cs50 import SQL

db = SQL("sqlite:///favorites.db")

favorite = input("Favorite: ")

db.execute("BEGIN TRANSACTION")
rows = db.execute("SELECT COUNT(*) AS n FROM favorites WHERE language = ?", favorite)

if len(rows) != 0:
    row = rows[0]
    print(row["n"])

db.execute("COMMIT")