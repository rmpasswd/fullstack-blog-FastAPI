```
posts: list[dict] = [
    {
        "id": 1,
        "user_id": 1,
        "author": {
            "id": 1,
            "username": "corey_schafer",
            "email": "corey@example.com",
            "image_file": "default.jpg",
            "image_path": "/static/profile_pics/default.jpg"
        },
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "2025-04-20T00:00:00",
    },
    {
        "id": 2,
        "user_id": 2,
        "author": {
            "id": 2,
            "username": "jane_doe",
            "email": "jane@example.com",
            "image_file": "default.jpg",
            "image_path": "/static/profile_pics/default.jpg"
        },
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "2025-04-21T00:00:00",
    },
]
```

###  Discussion, Troubleshoot Log...

After trying to out sqlite and the async variant of operations, it's time to switch to PostgreSQL.  We will  install 1)postgres itself, 2)the python package, and another 3)packageto migrate from sqlite.

- install  postgresql in  the host machine or in  a  docker container, make sure it can be connected from the host  machine(ie. the docker subnet  is allowed  in pg_hba.conf)
- `psql  postgres -c "CREATE USER  bloguser  WITH  PASSWORD 'bloguser';` then from psql: `createdb blog  -O  bloguser;`  (O for owner)
-  Install python package for postgres! replacing 'aiosqlite':  `uv add psycopg[binary]`, supports both sync  and async. `[binary]` gives are precompiled binary, hence  no  need to compile anything locally.
- `uv add alembic`
- `uv  run alembic init -t async alembic`: to run alembic using async template(standard alembic is not async). The trailing 'alembic' is the dir. name where migration files will live.
- After changing the database_url in .ini file or dynamically from env.py file, we  need to establish a "source truth" that alembic will cross-check with throughtout the migration process: ` uv  run  alembic revision --autogenerate  -m "initial schema generation"`
  - Posible errors in Windows: `run alembic: connection_async.py", line 107, in connect raise e.InterfaceError(sqlalchemy.exc.InterfaceError: (psycopg.InterfaceError) Psycopg cannot use the 'ProactorEventLoop' to run in async mode. Please use a compatible event loop, for instance by running 'asyncio.run()))'(Background on this error at: https://sqlalche.me/e/20/rvf5)`
    - Add an argument `echo=True` to enable log output  (i.e. more specific error message): `engine = create_async_engine(settings.database_url, echo=True)`
    - Found this new message in the output: `sqlalchemy\engine\url.py", line 922, in _parse_url raise exc.ArgumentError(sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string`
    - Gemini  and [stackoverflow](https://stackoverflow.com/questions/71219607/psycopg3-unable-to-connect-async) says to add this line: `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` *Does not work*.  Then inserted it to `database.py` where the first asyncio line is executed; not `main.py` which imports objects from `database.py`.
  - After `alembic revision...` command, If you dont see any tables(only 'pass' keyword  instead) in alembicDir/revision...py file, then chances are tables were already created by   'create_all' in main.py  lifespan block.Comment that 'create_all' block, delete the tables(login with `psql -U bloguser -d blog` and then `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) and then try the alembic revision command again.
  -  Then to  apply the revision: `uv run alembic upgrade head`. head means latest, alembic is indeed git-like. to  rollback to  previous revision: `uv run   alembic downgrade -1`. More commands: `uv run alembic current|history`


 **Git commit issue: Should not push 3 features in 1 commit! commit in chunks with `git add -p`**
 - First dont use `git add`  command yet, keep the staging area clear.
 - then type `git add -p` If you see 'nothing  changed' then  type `git reset` to unstage files(prevous  step)
 - You  will be shown changes made to each file! and prompted to confirm to stage or unstage that file. Hence for the first feature(say file upload), only confirm 'y' if the files related to file-upload are shown to you and it will move to staging area, press 'n' for  other files that correspond to another feature.
    -  Hunk-by-hunk questioning:
    - y (yes): Stage this hunk for the next commit.

    - n (no): Do not stage this hunk. Keep it in your working directory for later.

    - s (split): If a hunk contains both "Image Upload" and "Pagination" code, s will try to break it into even smaller pieces so you can stage them separately.

    -  q (quit): Stop right here. Don't stage anything else, but keep what you've already "y-ed" so far.
