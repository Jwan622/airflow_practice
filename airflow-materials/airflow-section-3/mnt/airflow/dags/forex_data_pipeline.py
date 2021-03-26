from airflow import DAG
from datetime import datetime, timedelta
from airflow.sensors.http_sensor import HttpSensor
from airflow.contrib.sensors.file_sensor import FileSensor

default_args = {
	"owner" : "airflow",
	"start_date":  datetime(2021, 3, 21),
	"depends_on_past": False,
	"email_on_failure": False,
	"email_on_retry": False,
	"email": "youremail@host.com",
	"retries": 1,
	"retry_delay": timedelta(minutes=5)
}

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

