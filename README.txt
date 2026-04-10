__Database Sentinel: Anomaly Detection for SQL Transactions__
A real-time monitoring system that integrates MySQL transaction logging with machine learning to identify anomalous database activity.
Uses **Isolation Forest** algorithm to analyze behavioral fingerprints based on execution time and data impact.

__Configuration and Usage__
1. Define database credentials in the `db_config` dictionary
2. you may modify `contamination`, running time, rows + speed + number of normal and anomaly rows
3. Run script to initializes the schema, populates the training set
4. Insert new values to the db to check live monitoring

The system outputs an img titled `db_analysis.png` upon completion which displays the decision boundaries and identified outliers
