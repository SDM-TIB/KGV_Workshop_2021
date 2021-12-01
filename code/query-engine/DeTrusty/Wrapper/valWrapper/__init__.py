from threading import Thread

import requests

from DeTrusty import get_logger
from DeTrusty.Wrapper.valWrapper.Mapping import Mapping

# TODO: Import run_multiprocessing from api, fix all other imports, logging of the api needs to be extended to detrusty/ having multiple loggers

USE_DIRECT_STREAMING = True

logger = get_logger(__name__)


def contact_val_source(server, query, queue, val_config, target_shape, buffersize=16384, limit=-1):
    """
    Contacts the validation api which gives the joined validation results by contacting the external sparql endpoint and asking a backend for validation results.

    server: the external sparql endpoint
    query: the star-shaped query to be executed
    target_shape: the name of the shape which is focused by the star-shaped query
    """
    #print("Contacting endpoint: " + str(server) + "\n Query: " + str(query))

    params = {
        'external_endpoint': server,
        'query': query,
        'targetShape': target_shape,
        'config': val_config['api_config'],
        'schemaDir': val_config['schema_path'],
        'test_identifier': val_config['test_id'],
        'output_directory': val_config['output_directory']
    }

    if USE_DIRECT_STREAMING:
        from app.api import run_multiprocessing, get_result_queue
        in_queue = get_result_queue()
        t_api = Thread(target=run_multiprocessing, args=(params, in_queue))
        t_api.start()
        new_result = in_queue.receiver.get()
        while new_result != 'EOF':
            queue.put(Mapping(new_result))
            new_result = in_queue.receiver.get()
        queue.put('EOF')
        result = True
    else:
        response = requests.post(val_config['api_endpoint'], data=params)
        json_response = response.json()
        for binding_explaination in json_response:
            queue.put(Mapping(binding_explaination))
        queue.put('EOF')
        result = (response.status_code == 200)
    return result
