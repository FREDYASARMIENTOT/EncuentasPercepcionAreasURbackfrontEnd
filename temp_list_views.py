import sys
sys.path.insert(0, r'F:\ETL_DITIC\EncuestasPercepciónAzure\backend')
from database import get_pyodbc_connection

conn = get_pyodbc_connection()
cur = conn.cursor()
cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='VIEW' AND TABLE_NAME LIKE '%Encuesta%' ORDER BY TABLE_NAME")
print(cur.fetchall())
conn.close()
