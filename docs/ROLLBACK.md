# Rollback to stable reports

## Code
git fetch --all --tags
git checkout reports-stable-20250930

## (Optional) DB
# Choose the needed backup:
#   .\backups\db-YYYYMMDD-HHMMSS.sqlite3
# Replace the live DB:
#   Stop the Django server first, then:
#   copy /Y .\backups\db-YYYYMMDD-HHMMSS.sqlite3 .\db.sqlite3
