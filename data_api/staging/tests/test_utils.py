import codecs
import json
import os


def get_api_results_from_file(filename, extract_result=None):
    """
    Loads JSON from the given test file
    """
    handle = codecs.open(os.path.join(os.path.dirname(__file__), 'test_api_results',
                                      '{}.json'.format(filename)))
    contents = handle.read()
    handle.close()

    if extract_result is not None:
        contents = json.dumps(json.loads(contents)['results'][0])

    return contents
