__author__ = "Philipp D. Rohde"

import os
import re
import time
from multiprocessing import Queue

from DeTrusty import get_logger
from DeTrusty.Decomposer.Decomposer import Decomposer
from DeTrusty.Decomposer.Planner import Planner
from DeTrusty.Molecule.MTManager import ConfigFile
from DeTrusty.Molecule.MoleculeCollector import collect_molecules
from DeTrusty.Wrapper import contact_source
from flask import Flask, Response, request, jsonify, render_template
import pathlib, sys
import logging

# This assumes that the DeTrusty Package is side by to side with the shacl-api package
PACKAGE_SHACL_API = str(pathlib.Path(__file__).parent.parent.parent.joinpath('shacl-api').resolve())
PACKAGE_TRAVSHACL = str(pathlib.Path(__file__).parent.parent.parent.joinpath('shacl-api/Trav-SHACL').resolve())

logger = get_logger(__name__)

app = Flask(__name__)
app.config['VERSION'] = os.environ.get("VERSION")
app.config['JSON_AS_ASCII'] = False
app.config['CONFIG'] = ConfigFile('/code/query-engine/Config/rdfmts.json')
app.config['OUTPUT_DIR'] = os.path.join(os.sep, "DeTrusty", "output")
app.config['SHACL_API_OUTPUT_DIR'] = os.path.join(os.sep, "ShaclAPI", "output")

re_https = re.compile("https?://")


@app.route('/version', methods=['POST'])
def version():
    """Returns the version of DeTrusty that is being run."""
    return Response('DeTrusty v' + app.config['VERSION'] + "\n", mimetype='text/plain')


def run_query(query: str, sparql_one_dot_one: bool = False, config: ConfigFile = app.config['CONFIG'], print_result: bool = True, val_config: dict = None, query_id: str = "Q"):
    trace = []
    test_name = val_config['test_id'] if val_config else query_id
    approach_name = os.path.basename(val_config['api_config']) if val_config else "no_shacl"
    
    if val_config:
        sys.path.append(PACKAGE_SHACL_API)
        import app.api as speed_up_execution_by_one_seconde

    start_time = time.time()
    decomposer = Decomposer(query, config, sparql_one_dot_one=sparql_one_dot_one)
    decomposed_query = decomposer.decompose()

    if decomposed_query is None:
        return {"results": {}, "error": "The query cannot be answered by the endpoints in the federation."}

    planner = Planner(decomposed_query, True, contact_source, 'RDF', config, val_config)
    plan = planner.createPlan()

    output = Queue()
    plan.execute(output)

    result = []
    r = output.get()
    card = 0
    while r != 'EOF':
        card += 1
        trace.append({"test": test_name, "approach": approach_name, "answer": card, "time": time.time() - start_time})
        if print_result:
            res = {}
            for key, value in r.items():
                res[key] = {"value": value, "type": "uri" if re_https.match(value) else "literal"}
            res['__val__'] = r.val_report if hasattr(r, 'val_report') else None

            result.append(res)
        r = output.get()
    end_time = time.time()

    return {"head": {"vars": decomposed_query.variables()},
                    "cardinality": card,
                    "results": {"bindings": result} if print_result else "printing results was disabled",
                    "execution_time": end_time - start_time,
                    "output_version": "2.0"}

@app.route('/sparql', methods=['POST'])
def sparql():
    """Retrieves a SPARQL query and returns the result."""
    try:
        query = request.values.get("query", None)
        query = query.replace('\r', '')
        logger.info("Received query: " + str(query))
        if query is None:
            return jsonify({"result": [], "error": "No query passed."})

        config_path = request.values.get("config", "/code/query-engine/Config/rdfmts.json")
        config = ConfigFile(config_path)
        if request.values.get("validate", False):
            api_config = "/inputs/api_configs/valsparql.json"
            schema_path = "/inputs/shapes/lubm/"
            test_id = "Q"

            val_config = {"api_config": api_config,
                          "api_endpoint": None,
                          "schema_path": schema_path,
                          "test_id": test_id,
                          "output_directory": app.config['SHACL_API_OUTPUT_DIR']}
        else:
            val_config = None

        sparql1_1 = request.values.get("sparql1_1", False)

        result = run_query(query, sparql_one_dot_one=sparql1_1, val_config=val_config, config=config)
        if request.values.get("table", False):
            logger.exception(str(result))
            validation_information = True if val_config is not None else False
            result_html = dict_to_html_table(result, validation_information)
            return render_template("result.html", html=result_html)
        else:
            return jsonify(result)
    except Exception as e:
        logger.exception(e)
        import sys
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        emsg = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        return jsonify({"result": [], "error": str(emsg)})


def dict_to_html_table(dict_, val_info: bool):
    html = '<div>The query returned ' + str(dict_['cardinality']) + ' results in ' + str(dict_['execution_time']) + ' seconds.<br><table border="1px">'

    order = []
    html += "<tr>"
    for var in dict_['head']['vars']:
        order.append(var)
        html += "<th>" + var + "</th>"
    if val_info:
        html += "<th>__val__</th>"
    html += "</tr>"

    for res in dict_['results']['bindings']:
        html += "<tr>"
        for var in order:
            if res[var]['type'] == 'uri':
                html += '<td><a href="' + res[var]['value'] + '">' + res[var]['value'] + "</a></td>"
            else:
                html += "<td>" + res[var]['value'] + "</td>"
        if val_info:
            html += "<td>" + str(res['__val__']).replace('<','').replace('>','') + "</td>"
        html += "</tr>"

    html += "</table></div>"
    return html


@app.route('/sparql', methods=['GET'])
def sparql_get():
    query = request.args.get("query", None)
    if query is None:
        return render_template('sparql.html')


@app.route('/validate', methods=['POST', 'GET'])
def validate():
    if request.method == 'GET':
        return render_template('validate.html')
    sys.path.append(PACKAGE_TRAVSHACL)
    sys.path.append(PACKAGE_SHACL_API)
    from app.config import Config
    from app.reduction.travshacl.ReducedShapeSchema import ReturnShapeSchema
    config = Config.from_request_form(request.form)
    schema = ReturnShapeSchema.from_config(config)
    start = time.time()
    result = schema.validate()
    stop = time.time()
    result_html = travshacl_to_html_table(result, stop - start)
    return render_template("result.html", html=result_html) 

def travshacl_to_html_table(trav_result, time_used):
    parsed_result = []

    for shape, validation_dict in trav_result.items():
        for validation_result, instances in validation_dict.items():
            for instance in instances:
                parsed_result.append({'shape': instance[0], 'finished@shape': shape, 'validation result': validation_result.replace('_instances',''), 'instance': instance[1]})

    html = '<div>Trav-SHACL returned ' + str(len(parsed_result)) + ' validation results in ' + str(time_used) + ' seconds.<br><table border="1px">'

    order = []
    html += "<tr>"
    for item in ['instance', 'shape', 'validation result', 'finished@shape']:
        order.append(item)
        html += "<th>" + item + "</th>"
    html += "</tr>"

    for res in parsed_result:
        html += "<tr>"
        for item in order:
            if res[item]:
                html += "<td>" + str(res[item]) + "</td>"
        html += "</tr>"

    html += "</table></div>"
    return html

@app.route('/configure', methods=['GET', 'POST'])
def serve_configure():
    if request.method == 'POST':
        success = False
        try:
            endpoint_url = request.values.get("endpoint_url", None)
            logger.info("Received the following URL: " + str(endpoint_url))
            if endpoint_url:
                collect_molecules([endpoint_url])
                success = True
        finally:
            return render_template('configure.html', success=success)
    return render_template('configure.html', success=None)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
