# spotgenius-connect

# setup

# Builds docker image and starts backend service
```
# Local Development env
docker-compose -f docker-compose.yml up --build

```
```
# Migrate
alembic -c app/migrations/alembic.ini upgrade head
```
