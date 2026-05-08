###  About the Project

A FastAPI CRUD blog project with features:
  - Register, login and change profile pictures(uses AWS S3)
  - Create new posts, edit and delete(postgres database).
  - A Home page with All page, user-specific post page.
  - Supports pagination

**Built With:**  

[![uv](https://img.shields.io/badge/uv-%2324292e.svg?style=for-the-badge&logo=python&logoColor=white)](#)  [![FastAPI](https://img.shields.io/badge/FastAPI-%23009485.svg?style=for-the-badge&logo=fastapi&logoColor=white)](#)  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](#)  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-%23D71F00.svg?style=for-the-badge&logo=sqlalchemy&logoColor=white)](#)  [![Alembic](https://img.shields.io/badge/Alembic-%236BA81E.svg?style=for-the-badge&logo=alembic&logoColor=white)](#)  [![Pydantic](https://img.shields.io/badge/Pydantic-%23E92064.svg?style=for-the-badge&logo=pydantic&logoColor=white)](#)

### Architecture

- At the heart of the architecture are two containers running in an EC2 instance.
  - WatchTower is a monitoring application "for automating Docker container image updates". On interval, it checks the registry, docker hub in this case, and pulls the image if it has been updated. Then it stops and re-creates the _webapp_ container with the new image i.e. the new code/feature.
  - blog-webapp runs the code in the 'live' branch  of this repo. `docker run` exposes the uv  port to the host machines's port 80. After allowing traffic through _Security Groups_, it is now  Live at [https://blog.mahin.uk](https://blog.mahin.uk). DNS and SSL is maintained by Cloudflare.

**Workflow:**
1. On pushing a commit from local development to the 'live' branch, a _Github Action Runner_ is started to build  the new image  and push to Docker Hub registry.
2. WatchTower  polls the registry and finds that  the current  running container's image hash is different than that of the registry. Pulls the new image and re-creates the webapp container.
  - The webapp listens to 8080 port and docker forwards traffic from host's port 80 (`docker run ... -p 80:8080 ...`). _AWS Security Group_ allows outside traffic to port 80 and thus access to the webapp.
3. User profile pictures are stored/updated using _AWS S3 Bucket_ with _Standard Tier_. All other data incl. posts are stored in a remote postgres database(Supabase). Note that the main branch connect to neither S3 nor remote Postgres. It is a locally deploy-able version of the blog-webapp.
   

<img width="799" height="453" alt="blog-webapp-architecture-2" src="https://github.com/user-attachments/assets/ee8eca94-e323-4e4e-b6d3-5e44a15dc4bb" />


### Installation(local)

1. download the main branch
2. Install postgres
3. Create an .env file with two variables: DATABASE_URL(`=postgresql+psycopg://bloguser:bloguser@localhost:5432/blog` ) and SECRET_KEY( to form JWT access token, `python -c "import secrets; print(secrets.token_hex(32))"`)
4. install python3 and uv
5. while inside project root, run: `uv sync`. It will use the project.toml file.
6. run `uv run fastapi dev main.py`

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
