import os
from sqlalchemy import create_engine

# Do the above in the docker file
construct_table_name = lambda node_id, node_index: f"{node_id}__{node_index}"

connection_string= {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "db"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}



construct_postgre_url = lambda connection_string : (
    f"postgresql+psycopg2://{connection_string['user']}:{connection_string['password']}"
    f"@{connection_string['host']}:{connection_string['port']}/{connection_string['dbname']}"
)

construct_postgre_async_url = lambda connection_string : (
    f"postgresql+asyncpg://{connection_string['user']}:{connection_string['password']}"
    f"@{connection_string['host']}:{connection_string['port']}/{connection_string['dbname']}"
)

postgre_url = construct_postgre_url(connection_string)
postgre_async_url = construct_postgre_async_url(connection_string)

# : Later we can work on connecting to the database only once instead of every tool or every node output connector connecting to the db everytime
postgre_engine = create_engine(postgre_url)

# : Afterwards we can consider using a lighter sql db rather than postgres such as sqlite