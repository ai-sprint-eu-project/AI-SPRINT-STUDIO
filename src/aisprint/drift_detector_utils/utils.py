import os
import numpy as np
import yaml

import boto3


def get_metric_drift_state(metric, field):
    minio_client = boto3.client(
        's3', 
        endpoint_url=os.getenv('DRIFT_DETECTOR_MINIO_URL'),
        region_name='us-east-1',
        verify=False,
        aws_access_key_id=os.getenv('DRIFT_DETECTOR_MINIO_AK'),
        aws_secret_access_key=os.getenv('DRIFT_DETECTOR_MINIO_SK')) 

    try:
        minio_client.download_file(
            os.getenv('DRIFT_DETECTOR_MINIO_BUCKET'), 
            'drift_state.yaml', 'drift_state.yaml')
    except:
        print("Metric {} - Field {} - DRIFT STATE = 0".format(metric, field))
        return 0

    with open('drift_state.yaml', 'r') as f:
        drift_dict = yaml.load(f, Loader=yaml.Loader)
    
    print("Metric {} - Field {} - DRIFT STATE = {}".format(metric, field, drift_dict[metric][field]))
    return drift_dict[metric][field] 

def get_drift_state():
    minio_client = boto3.client(
        's3', 
        endpoint_url=os.getenv('DRIFT_DETECTOR_MINIO_URL'),
        region_name='us-east-1',
        verify=False,
        aws_access_key_id=os.getenv('DRIFT_DETECTOR_MINIO_AK'),
        aws_secret_access_key=os.getenv('DRIFT_DETECTOR_MINIO_SK')) 

    minio_client.download_file(
        os.getenv('DRIFT_DETECTOR_MINIO_BUCKET'), 
        'drift_state.yaml', 'drift_state.yaml')

    with open('drift_state.yaml', 'r') as f:
        drift_dict = yaml.load(f, Loader=yaml.Loader)

    for metric in drift_dict.keys():
        for field in drift_dict[metric].keys():
            if drift_dict[metric][field] == 2:  # data-collection end
                return 2 
    
    for metric in drift_dict.keys():
        for field in drift_dict[metric].keys():
            if drift_dict[metric][field] == 1:  # drift 
                return 1 
    
    return 0