> Check main branch's readme for more.

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

