import psycopg2
import os

# Establish connection to the PostgreSQL database using environment variables
conn = psycopg2.connect(
    host=os.environ.get('PGHOST'),
    database=os.environ.get('PGDATABASE'),
    user=os.environ.get('PGUSER'),
    password=os.environ.get('PGPASSWORD'),
    port=os.environ.get('PGPORT', 5432)
)

# Enable autocommit mode for the connection
conn.autocommit = True
cursor = conn.cursor()

# Execute the schema.sql file to create the necessary tables
with open('schema.sql', 'r') as f:
    cursor.execute(f.read())

# Close the cursor and the connection
cursor.close()
conn.close()

print("Database initialized successfully!")
