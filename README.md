###  About the Project

A FastAPI CRUD blog project with features:
  - Register, login and change profile pictures(uses AWS S3)
  - Create new posts, edit and delete(postgres database).
  - A Home page with All page, user-specific post page.
  - Supports pagination

**Demo:** [https://blog.mahin.uk](https://blog.mahin.uk)

**Built With:**  

[![FastAPI](https://img.shields.io/badge/FastAPI-%23009485.svg?style=for-the-badge&logo=fastapi&logoColor=white)](#) [![uv](https://img.shields.io/badge/uv-%2324292e.svg?style=for-the-badge&logo=python&logoColor=white)](#)  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](#)  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-%23D71F00.svg?style=for-the-badge&logo=sqlalchemy&logoColor=white)](#)  [![Alembic](https://img.shields.io/badge/Alembic-%236BA81E.svg?style=for-the-badge&logo=alembic&logoColor=white)](#)  [![Pydantic](https://img.shields.io/badge/Pydantic-%23E92064.svg?style=for-the-badge&logo=pydantic&logoColor=white)](#)

### Architecture

At the heart of the architecture are two containers running in an EC2 instance: the webapp and WatchTower.
  - blog-webapp runs the code from the 'live' branch of this repo. `docker run` exposes the uv port 8080 to the host machines's port 80. After allowing traffic through _Security Groups_, it is now Live at [https://blog.mahin.uk](https://blog.mahin.uk). DNS and SSL is maintained by Cloudflare.
  - User profile pictures are stored/updated using _AWS S3 Bucket_ with _Standard Tier_. All other data incl. blog posts are stored in a remote postgres database(Supabase).
  - Note that the _main_ branch connect to neither S3 nor remote Postgres. It is a locally deploy-able version of the blog-webapp.

**Continuous Deployment:**
- [WatchTower](https://github.com/nicholas-fedor/watchtower) is a monitoring application "for automating Docker container image updates". On interval, it checks the registry, docker hub in this case, and pulls the image if it has been updated. Then it stops and re-creates the _webapp_ container with the new image i.e. the new code/feature.
- On pushing a commit from local development to the 'live' branch, a _Github Action Runner_ is started to build the new image and push to Docker Hub registry.
- WatchTower polls the registry and finds that the currently running container's image hash is different than that of the registry. Pulls the new image and re-creates the webapp container.
   

<img width="799" height="453" alt="blog-webapp-architecture-2" src="https://github.com/user-attachments/assets/ee8eca94-e323-4e4e-b6d3-5e44a15dc4bb" />


### Installation(Docker Compose, two containers)

1. Download the main branch
2. Create an .env file with two variables: DATABASE_URL(`=postgresql+psycopg://bloguser:bloguser@localhost:5432/blog` ) and SECRET_KEY( to form JWT access token, `python -c "import secrets; print(secrets.token_hex(32))"`)
3. Place the .env file in project root. Do not share/upload it.
4. Fromt the terminal run `docker compose up -d`.
   - Make sure docker is running in your machine.
   - Make sure the file is named `docker-compose.yml`(or `compose.yaml`). It is the default name docker compose command looks for.
 
### Installation(Local, without Docker)

1. Download the main branch
2. Install postgresql. Inside `psql` client: `CREATE USER bloguser WITH PASSWORD'bloguser'; CREATE DATABASE blog OWNER bloguser`
3. Create an .env file with two variables: DATABASE_URL(`=postgresql+psycopg://bloguser:bloguser@localhost:5432/blog` ) and SECRET_KEY( to form JWT access token, `python -c "import secrets; print(secrets.token_hex(32))"`)
4. Install python3 and [uv](https://docs.astral.sh/uv/getting-started/installation/#installation-methods)
5. While inside project root, run: `uv sync`. It will use the project.toml file.
6. `uv run alembic upgrade head` to actually create the tables, otherwise next command will fail.
7. Run `uv run fastapi dev main.py`. 
  - Put the .env file following the path mentioned in auth/config.py
  - The database tables must be present and open to connecttions from FastAPI

### Installation(Cloud)

1. Uses AWS EC2 instance and Supabase free tier.
2. **This part of instructions for the 'cloud-stack' branch only, and relates to the architectural diagram above**
3. EC2 instance security grups **inbound** rules must allow ssh, http and https traffic, and **outbound** rule must allow traffic to internet 0.0.0.0/0 to connect to Supabase.
    <img width="1582" height="903" alt="image" src="https://github.com/user-attachments/assets/d5aeaf2c-1570-4ddc-8c65-0c6f09f22eae" />
4. Enable EIP for EC2 instance to actually ssh to the machine. 1. Right-click > Networking > Manage IP Addresses > Auto-assign public IP. Then click "connect".
5. Inside EC2 instance(amazon linux), you can install docker with `sudo dnf install docker`
6. Build the env file and start the container `sudo docker build -d --restart always ./ && docker run -p 8080:8080 --env-file /path/to/.env fastapi-blog`
7. The .env file will look as below:  

   ```
    SECRET_KEY= ( to form JWT access token, `python -c "import secrets; print(secrets.token_hex(32))"`)
    
    # this is 'session pooler' option from supabase
    # DATABASE_URL=postgresql+psycopg://postgres.project_id:password.vvQd@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
    
    # this is 'transaction pooler' option from supabase
    # DATABASE_URL=postgresql+psycopg://postgres.project_id:password.vvQd@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres  
    # In Supabase default database 'postgres' stays fixed. but we can use 'blogdb' instead of default schema 'public'. 'blogdb' has been used in `database.py` and in alembic migration files. Check "Discussion".
    
    S3_BUCKET_NAME=
    S3_REGION=
    S3_ACCESS_KEY=
    S3_SECRET_ACCESS_KEY=
    ```
8. Setup watchtower to check new image every hour: `docker run -d --name watchtower  -v /var/run/docker.sock:/var/run/docker.sock --restart unless-stopped nickfedor/watchtower --interval 3600 fastapi-blog`

###  Discussion, Troubleshoot Log...

After trying to out sqlite and the async variant of operations, it's time to switch to PostgreSQL.  We will install 1)postgres itself, 2)the python package, and another 3)packageto migrate from sqlite.

- install postgresql in the host machine or in a docker container, make sure it can be connected from the host machine(ie. the docker subnet is allowed in pg_hba.conf)
- `psql postgres -c "CREATE USER bloguser WITH PASSWORD 'bloguser';` then from psql: `createdb blog  -O bloguser;`  (O for owner)
-  Install python package for postgres! replacing 'aiosqlite':  `uv add psycopg[binary]`, supports both sync and async. `[binary]` gives are precompiled binary, hence no need to compile anything locally.
- `uv add alembic`
- `uv run alembic init -t async alembic`: to run alembic using async template(standard alembic is not async). The trailing 'alembic' is the dir. name where migration files will live.
- After changing the database_url in .ini file or dynamically from env.py file, we need to establish a "source truth" that alembic will cross-check with throughtout the migration process: ` uv run alembic revision --autogenerate  -m "initial schema generation"`
  - Posible errors in Windows: `run alembic: connection_async.py", line 107, in connect raise e.InterfaceError(sqlalchemy.exc.InterfaceError: (psycopg.InterfaceError) Psycopg cannot use the 'ProactorEventLoop' to run in async mode. Please use a compatible event loop, for instance by running 'asyncio.run()))'(Background on this error at: https://sqlalche.me/e/20/rvf5)`
    - Add an argument `echo=True` to enable log output  (i.e. more specific error message): `engine = create_async_engine(settings.database_url, echo=True)`
    - Found this new message in the output: `sqlalchemy\engine\url.py", line 922, in _parse_url raise exc.ArgumentError(sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string`
    - Gemini and [stackoverflow](https://stackoverflow.com/questions/71219607/psycopg3-unable-to-connect-async) says to add this line: `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` *Does not work*.  Then inserted it to `database.py` where the first asyncio line is executed; not `main.py` which imports objects from `database.py`.
  - After `alembic revision...` command, If you dont see any tables(only 'pass' keyword instead) in alembicDir/revision...py file, then chances are tables were already created by   'create_all' in main.py lifespan block.Comment that 'create_all' block, delete the tables(login with `psql -U bloguser -d blog` and then `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) and then try the alembic revision command again.
  -  Then to apply the revision: `uv run alembic upgrade head`. head means latest, alembic is indeed git-like. to rollback to previous revision: `uv run   alembic downgrade -1`. More commands: `uv run alembic current|history`
  -  Troubleshoot: running command `uv run alembic revision --autogenerate -m "new changes to the databae new table/colum"` throws error: `Target database is not up to date` after making changes to models.py file to add another column or table. Then check  whether the latest alembic version is indeed the latest database's version `uv run alembic history --indicate`. If you cannot see both 'head' and 'current' then run `uv run alembic stamp head`. Now continue with `alembic revision --autogenerate... ` and `alembic upgrade head`
  -  


 **Git commit issue: Should not push 3 features in 1 commit! commit in chunks with `git add -p`**
 - First dont use `git add`  command yet, keep the staging area clear.
 - then type `git add -p` If you see 'nothing changed' then type `git reset` to unstage files(prevous step)
 - You will be shown changes made to each file! and prompted to confirm to stage or unstage that file. Hence for the first feature(say file upload), only confirm 'y' if the files related to file-upload are shown to you and it will move to staging area, press 'n' for other files that correspond to another feature.
    -  Hunk-by-hunk questioning:
    - y (yes): Stage this hunk for the next commit.

    - n (no): Do not stage this hunk. Keep it in your working directory for later.

    - s (split): If a hunk contains both "Image Upload" and "Pagination" code, s will try to break it into even smaller pieces so you can stage them separately.

    -  q (quit): Stop right here. Don't stage anything else, but keep what you've already "y-ed" so far.
