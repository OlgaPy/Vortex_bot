# Bot
Set up your config in .env or prod.env and run

### Env file
```env
# Telegram vars
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHANNEL_ID=-100id
TELEGRAM_POPULAR_CHANNEL_ID=-100id
TELEGRAM_COMMENTS_GROUP_ID=-100id
TELEGRAM_COMMENTS_GROUP_TAG=@mygroup

# Logging
LOG_FILE=./logfile.log

# Postgres vars
POSTGRES_DB=main
POSTGRES_PASSWORD=postgres

# DB config
DB_NAME = main
DB_USER = postgres
DB_PASSWORD = postgres
DB_HOST = db
DB_PORT = 5432
```

### Run
`docker-compose up --build`