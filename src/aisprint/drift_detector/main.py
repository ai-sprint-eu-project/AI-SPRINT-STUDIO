import os
import numpy as np
import yaml
import time
import traceback

from utils import (init_test, get_metric_values, get_influxdb_client, 
                   get_minio_client, run_drift_test, update_metric_drift_state, DriftDetectorLogger)


def main(metrics, detection_interval, data_collection_period, 
         minio_client, influxdb_client, logger):
    
    logger.log("Starting Drift Detector algorithm..")
    logger.log("The following metrics will be monitored")
    
    for metric_name in metrics.keys():
        for metric_field in metrics[metric_name].keys():
            logger.log("Metric: {}, Field: {}".format(metric_name, metric_field))
            logger.log(" - Statistical Test: {}".format(metrics[
                metric_name][metric_field]['statistical_test']))
            logger.log(" - Test Threshold: {}".format(metrics[
                metric_name][metric_field]['test_threshold']))
            logger.log(" - Monitoring Period: {}".format(metrics[
                metric_name][metric_field]['monitoring_period']))

    is_first_period = {}   # This allows to identify the first period
    for metric_name, metric_dict in metrics.items():
        is_first_period[metric_name] = {}
        for metric_field, field_dict in metric_dict.items():
            is_first_period[metric_name][metric_field] = True

    at_least_one_drifted = False

    drift_state_dict = {}

    while(not at_least_one_drifted):
        # Run the detection algorithm each detection_interval hours
        time.sleep(detection_interval * 3600)

        for metric_name, metric_dict in metrics.items():
            if not metric_name in drift_state_dict:
                drift_state_dict[metric_name] = {}
            for metric_field, field_dict in metric_dict.items():
                if not metric_field in drift_state_dict[metric_name]:
                    drift_state_dict[metric_name][metric_field] = 0 
                if is_first_period[metric_name][metric_field]:
                    # Get x_ref and initialize the test
                    # x_ref -> 1 x N
                    logger.log("Initializing x_ref for metric: {}".format(metric_name))
                    x_ref = get_metric_values(
                        influxdb_client, field_dict['monitoring_period'], metric_name, metric_field)
                    logger.log("Done!")

                    if x_ref is None:
                        continue

                    # Init test
                    logger.log("Initializing statistical test for metric: {}, field: {}".format(
                        metric_name, metric_field))
                    test_obj = init_test(
                        field_dict['statistical_test'], x_ref, field_dict['test_threshold'])
                    logger.log("Done!")

                    metrics[metric_name][metric_field]['test'] = test_obj  

                    # Initilize metric state
                    drift_state_dict[metric_name][metric_field] = 0
                    update_metric_drift_state(minio_client, drift_state_dict) 

                    is_first_period[metric_name][metric_field] = False

                else:
                    # Get the metric values over the user-defined monitoring period
                    logger.log("Running statistical test for metric: {}, field: {}".format(
                        metric_name, metric_field))
                    metric_values = get_metric_values(
                        influxdb_client, field_dict['monitoring_period'], metric_name, metric_field)
                    # Run the statistical test
                    drift_state = run_drift_test(metrics[metric_name][metric_field]['test'], metric_values) 
                    logger.log("Drift state: {}".format(drift_state))

                    # Drift result
                    if drift_state == 1: # DRIFTED!
                        logger.log("Drift detected!")
                        at_least_one_drifted = True
                        # Save metric drift state
                        drift_state_dict[metric_name][metric_field] = drift_state
                        update_metric_drift_state(minio_client, drift_state_dict)

        if at_least_one_drifted:
            logger.log("Starting data collection period..")
            time.sleep(data_collection_period * 3600)
            
            # Update metric drift state 
            drift_state = 2  # DATA COLLECTION PERIOD END
            for metric_name in drift_state_dict.keys():
                for metric_field in drift_state_dict[metric_name].keys():
                    if drift_state_dict[metric_name][metric_field] == 1:
                        drift_state_dict[metric_name][metric_field] = drift_state
            update_metric_drift_state(minio_client, drift_state_dict)

            logger.log("Done! Collected data is available.")
            logger.log("Ending drift detector..Done!") 
            return
                
if __name__ == '__main__':
    
    # Load Drift Detector config 
    with open('./drift_detector_config.yaml', 'r') as f:
        drift_detector_config = yaml.safe_load(f)

    metrics = drift_detector_config['metrics']
    detection_interval = drift_detector_config['detection_interval']
    data_collection_period = drift_detector_config['data_collection_period']
    
    influxdb_client = get_influxdb_client() 
    minio_client = get_minio_client()

    logger = DriftDetectorLogger(minio_client)

    try:
        main(metrics, detection_interval, data_collection_period, 
             minio_client, influxdb_client, logger)
    except:
        exception = traceback.format_exc() 
        exception = exception.split('\n')
        for line in exception:
            logger.log(line)