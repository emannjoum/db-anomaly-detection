import pandas as pd
import mysql.connector
from mysql.connector import Error
from sklearn.ensemble import IsolationForest
from faker import Faker
import random
import time
import matplotlib.pyplot as plt

db_config = { 
    'host': 'xxx',
    'user': 'xxxx',
    'password': 'xxxxx',
    'database': 'xxxxx'
}

class DBSentinel:
    def __init__(self, config):
        self.config = config
        self.model = IsolationForest(contamination=0.01, random_state=42) 
        # you can tune contamination depending on whether you want a higher precision or recall
        # here i care more about precision and thus lowered contamination (dont want false pos)
        # for example if you use 0.05 you will have MORE queries flagged as anomaly and vice versa
        # you can check the generated db_analysis.png to visualize your results
        self.fake = Faker()
        self.last_id = 0

    def connect(self):
        return mysql.connector.connect(**self.config)

    def setup_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS transaction_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            query_type VARCHAR(20),
            execution_time_ms FLOAT,
            rows_changed INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # the speeds and number of rows used below arent strict, i chose them subjectively 
        data = []
        for _ in range(1000): # 1000 normal rows
            data.append((
                random.randint(1, 100),
                random.choice(['SELECT', 'UPDATE']),
                random.uniform(5.0, 45.0), # normal speed
                random.randint(1, 5)        # few rows
            ))
        
        for _ in range(30): # 30 anomalies
            data.append((
                random.randint(1, 100),
                'DELETE',
                random.uniform(500.0, 2000.0), # very slow
                random.randint(500, 1000)      # mass changes
            ))

        insert_query = "INSERT INTO transaction_logs (user_id, query_type, execution_time_ms, rows_changed) VALUES (%s, %s, %s, %s)"
        cursor.executemany(insert_query, data)
        conn.commit()
        cursor.close()
        conn.close()

    def train_detector(self):
        conn = self.connect()
        df = pd.read_sql("SELECT execution_time_ms, rows_changed FROM transaction_logs", conn)
        conn.close()

        print(f"Training on {len(df)} records...")
        self.model.fit(df)
        return df

    def monitor_live(self):
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM transaction_logs WHERE id > %s ORDER BY id ASC" # all new queries since the last time we checked
        cursor.execute(query, (self.last_id,))
        new_entries = cursor.fetchall()
        cursor.close()
        conn.close()

        for record in new_entries:
            features = pd.DataFrame([[record['execution_time_ms'], record['rows_changed']]], 
                                    columns=['execution_time_ms', 'rows_changed'])
            
            prediction = self.model.predict(features)
            status = "ANOMALY" if prediction[0] == -1 else "NORMAL"
            
            print(f"[LIVE] ID: {record['id']} | Type: {record['query_type']} | Status: {status}")
            
            self.last_id = record['id']

    def generate_report(self):
        conn = self.connect()
        df = pd.read_sql("SELECT execution_time_ms, rows_changed FROM transaction_logs", conn)
        conn.close()

        df['prediction'] = self.model.predict(df)
        
        plt.figure(figsize=(10, 6))

        normal = df[df['prediction'] == 1]
        plt.scatter(normal['execution_time_ms'], normal['rows_changed'], 
                    c='skyblue', label='Normal', alpha=0.5)
        
        anomalies = df[df['prediction'] == -1]
        plt.scatter(anomalies['execution_time_ms'], anomalies['rows_changed'], 
                    c='red', label='Anomaly', marker='x')

        plt.title('Database Activity Fingerprinting (Isolation Forest)')
        plt.xlabel('Execution Time (ms)')
        plt.ylabel('Rows Affected')
        plt.legend()
        plt.savefig('db_analysis.png')
        print("Graph generated: db_analysis.png")


if __name__ == "__main__":
    sentinel = DBSentinel(db_config)
    sentinel.setup_db()
    sentinel.train_detector()
    print("\nstarted watching db")
    for _ in range(30): 
        sentinel.monitor_live()
        time.sleep(5)
    sentinel.generate_report()