import getopt
import sys
import os

from DeTrusty import get_logger
from DeTrusty.Molecule.MTManager import ConfigFile
from DeTrusty.flaskr import run_query

logger = get_logger(__name__)


def get_options():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:q:o:c:r:a:e:s:i:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    query_file = None
    sparql_one_dot_one = False
    config_file = "./Config/rdfmts.json"
    print_result = True
    api_config = None
    api_endpoint = "http://valsparql_shacl_api:5000/multiprocessing"
    schema_path = None
    query_id = "Q"
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-q":
            query_file = arg
        elif opt == "-o":
            sparql_one_dot_one = eval(arg)
        elif opt == "-c":
            config_file = arg
        elif opt == "-r":
            print_result = eval(arg)
        elif opt == "-a":
            api_config = arg
        elif opt == "-e":
            api_endpoint = arg
        elif opt == "-s":
            schema_path = arg
        elif opt == "-i":
            query_id = arg

    if not query_file or (api_config and not schema_path):
        usage()
        sys.exit(1)

    val_config = None
    if api_config:
        val_config = {"api_config": api_config,
                      "api_endpoint": api_endpoint,
                      "schema_path": schema_path,
                      "test_id": query_id,
                      "output_directory": os.path.join(os.sep, "ShaclAPI", "output")}

    return query_file, sparql_one_dot_one, config_file, print_result, val_config, query_id


def usage():
    usage_str = "Usage: {program} -q <query_file> -c <config_file> -o <sparql1.1> -r <print_result> " \
                "-a <api_config> -e <api_endpoint> -s <schema_path> -i <query_id>" \
                "\nwhere \n" \
                "<query_file> path to the file containing the query to be executed\n" \
                "<config_file> path to the config file containing information about the federation of endpoints\n" \
                "<sparql1.1> is one in [True, False] (default False), when True, no decomposition is needed\n" \
                "<print_result> is one in [True, False] (default True), when False, only metadata is returned\n" \
                "<api_config> path to config file for the SHACL API; omit when no SHACL shapes are to be validated\n" \
                "<api_endpoint> URL of the SHACL API endpoint\n" \
                "<schema_path> path to the SHACL shape schema to validate the data against\n" \
                "<query_id> ID used to identify the given query in the logs"
    print(usage_str.format(program=sys.argv[0]), )


def main():
    query_file, sparql_one_dot_one, config_file, print_result, val_config, query_id = get_options()

    try:
        query = open(query_file, "r", encoding="utf8").read()
        config = ConfigFile(config_file)
        run_query(query, sparql_one_dot_one, config, print_result, val_config, query_id)
        sys.exit()
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
