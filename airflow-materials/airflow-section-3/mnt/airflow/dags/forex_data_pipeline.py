from airflow import DAG
from datetime import datetime, timedelta
from airflow.sensors.http_sensor import HttpSensor
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.hive_operator import HiveOperator
from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.operators.email_operator import EmailOperator
from airflow.operators.slack_operator import SlackAPIPostOperator
import json
import csv
import requests

default_args = {
	"owner" : "airflow",
	"start_date":  datetime(2021, 3, 26),
	"depends_on_past": False,
	"email_on_failure": False,
	"email_on_retry": False,
	"email": "youremail@host.com",
	"retries": 1,
	"retry_delay": timedelta(minutes=2)
}


def download_rates():
    with open('/usr/local/airflow/dags/files/forex_currencies.csv') as forex_currencies:
        reader = csv.DictReader(forex_currencies, delimiter=';')
        for row in reader:
            base = row['base']
            with_pairs = row['with_pairs'].split(' ')
            indata = requests.get('https://api.exchangeratesapi.io/latest?base=' + base).json()
            outdata = {'base': base, 'rates': {}, 'last_update': indata['date']}
            for pair in with_pairs:
                outdata['rates'][pair] = indata['rates'][pair]
            with open('/usr/local/airflow/dags/files/forex_rates.json', 'a') as outfile:
                json.dump(outdata, outfile)
                outfile.write('\n')


with DAG(dag_id="forex_data_pipeline", schedule_interval="@daily", default_args=default_args, catchup=False) as dag:
	is_forex_rates_available = HttpSensor(
		task_id="is_forex_rates_available",
		method='GET',
		http_conn_id='forex_api',
		endpoint='latest',
		response_check=lambda response: "rates" in response.text,
		poke_interval=5,
		timeout=20,
	)

	is_forex_file_available = FileSensor(
		task_id="is_forex_file_available",
		fs_conn_id='forex_path',
		filepath="forex_currencies.csv",
		poke_interval=5,
		timeout=20,
	)

	downloading_rates = PythonOperator(
		task_id='forex_downloading_rates',
		python_callable=download_rates,
	)

	saving_rates = BashOperator(
		task_id="saving_rates",
		bash_command="""
			hdfs dfs -mkdir -p /forex && \
				hdfs dfs -put -f $AIRFLOW_HOME/dags/files/forex_rates.json /forex
		"""
	)

	creating_forex_rates_table = HiveOperator(
		task_id="creating_forex_rates_table",
		hive_cli_conn_id="hive_conn",
		hql="""
	            CREATE EXTERNAL TABLE IF NOT EXISTS forex_rates(
	                base STRING,
	                last_update DATE,
	                eur DOUBLE,
	                usd DOUBLE,
	                nzd DOUBLE,
	                gbp DOUBLE,
	                jpy DOUBLE,
	                cad DOUBLE
	                )
	            ROW FORMAT DELIMITED
	            FIELDS TERMINATED BY ','
	            STORED AS TEXTFILE
	        """
	)

	forex_processing = SparkSubmitOperator(
		task_id="forex_processing",
		conn_id="spark_conn",
		application="/usr/local/airflow/dags/scripts/forex_processing.py",
		verbose=False,
	)

	sending_email_notification = EmailOperator(
		to="Jwan622@yopmail.com",
		task_id="sending_email",
		subject="forex_data_pipeline_subject",
		html_content="<h3> some content forex data pipeline </h3>"
	)

	sending_slack_notification = SlackAPIPostOperator(
		task_id="sending_slack",
		token="xoxb-1858294503888-1902170231477-FvCA58i8jN0DDwzdt3iOYgCJ",
		username="airflow-bot",
		text="DAG TEST",
		channel="#flash-dance"
	)

	is_forex_rates_available >> is_forex_file_available >> downloading_rates >> saving_rates >> creating_forex_rates_table >> forex_processing >> sending_email_notification >> sending_slack_notification