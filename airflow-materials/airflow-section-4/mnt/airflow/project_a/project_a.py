from airflow import DAG
from airflow.operators.bash_operator import BashOperator

from datetime import datetime, timedelta

default_args = {
    'start_date': datetime(2021, 1, 2),
    'owner': 'Airflow',
    'email': 'owner@test.com',
}

with DAG(dag_id='project_a_dagbag', schedule_interval="0 0 * * *", default_args=default_args, catchup=False) as dag:
    
    # Task 1
    bash_task_1 = BashOperator(task_id='bash_task_1', bash_command="echo 'first task'")
    
    # Task 2
    bash_task_2 = BashOperator(task_id='bash_task_2', bash_command="echo 'second task'")

    bash_task_1 >> bash_task_2