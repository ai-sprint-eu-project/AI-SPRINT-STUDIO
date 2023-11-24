import os
import numpy as np
import yaml

from alibi_detect.cd import KSDrift, CVMDrift, FETDrift, ChiSquareDrift 
from influxdb_client import InfluxDBClient
import boto3


def init_test(statistical_test, x_ref, test_threshold):
    
    if statistical_test == 'kolmogorov-smirnov':
        cd_test = KSDrift(x_ref, p_val=test_threshold)
    elif statistical_test == 'cramer-von-mises':
        cd_test = CVMDrift(x_ref, p_val=test_threshold)
    elif statistical_test == 'fisher-exact-test':
        cd_test = FETDrift(x_ref, p_val=test_threshold)
    elif statistical_test == 'chi-squared':
        cd_test = ChiSquareDrift(x_ref, p_val=test_threshold)
    
    return cd_test

def run_drift_test(test, metric_values):
    preds = test.predict(metric_values, return_p_val=True, return_distance=True)
    drifted = preds['data']['is_drift']
    return drifted 

def get_influxdb_client():
    client = InfluxDBClient(
        url=os.getenv('DRIFT_DETECTOR_INFLUXDB_URL'),
        token=os.getenv('DRIFT_DETECTOR_INFLUXDB_TOKEN'),
        org='ai-sprint')
    return client

def get_minio_client():
    client = boto3.client(
        's3', 
        endpoint_url=os.getenv('DRIFT_DETECTOR_MINIO_URL'),
        region_name='us-east-1',
        verify=False,
        aws_access_key_id=os.getenv('DRIFT_DETECTOR_MINIO_AK'),
        aws_secret_access_key=os.getenv('DRIFT_DETECTOR_MINIO_SK')) 
    return client

def get_metric_values(client, time_range, metric, field, logger=None):

    # Convert from hours to minutes
    minutes = int(np.ceil(time_range * 60))
    
    query = (
        'from (bucket: bucket)'
        ' |> range(start: ' + '-' +str(minutes) + 'm' + ')'
        ' |> filter(fn: (r) => r._measurement == metric and r._field == field)'
        ' |> keep (columns: ["_time", "_value"])'
        ' |> group()'
        ' |> sort(columns: ["_time"])'
    )
    params = {'bucket': os.getenv('BUCKET_NAME'),
              'metric': metric,
              'field': field}

    api = client.query_api()
    results = api.query(query=query, params=params)

    if not results:
        print('No metrics found on InfluxDB yet.')
        if logger:
            logger.log('No metrics found on InfluxDB yet')
        return None

    # there should be exactly 0 or 1 result tables
    assert(len(results) == 1)
    results = results[0]
    metric_values = []
    for i, result in enumerate(results):
        # time = result.get_time()
        value = result.get_value()
        metric_values.append(value)
    
    return np.reshape(np.array(metric_values), [-1, 1]) 

def update_metric_drift_state(minio_client, drift_state_dict):
    with open('drift_state.yaml', 'w') as f:
        yaml.dump(drift_state_dict, f)
    minio_client.upload_file(
        'drift_state.yaml', 
        os.getenv('DRIFT_DETECTOR_MINIO_BUCKET'), 
        'drift_state.yaml')

class DriftDetectorLogger:
    def __init__(self, minio_client):
        self.minio_client = minio_client
    def log(self, txt):
        print(txt)
        f = open('drift_detector_log.txt', 'a')
        f.write(txt + '\n')
        f.close()
        self.minio_client.upload_file(
            'drift_detector_log.txt', 
            os.getenv('DRIFT_DETECTOR_MINIO_BUCKET'), 
            'drift_detector_log.txt')
