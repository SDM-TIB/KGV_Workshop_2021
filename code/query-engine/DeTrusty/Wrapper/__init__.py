from DeTrusty.Wrapper.RDFWrapper import contact_source as contact_rdf_source
from DeTrusty.Wrapper.valWrapper import contact_val_source


def contact_source(server, query, queue, val_config=None, target_shape=None, buffersize=16384, limit=-1):
    try:
        if val_config:
            contact_val_source(server, query, queue, val_config, target_shape, buffersize=buffersize, limit=limit)
        else:
            contact_rdf_source(server, query, queue, buffersize=buffersize, limit=limit)
    except Exception as e:
        queue.put("EOF")
        print("EXCEPTION in contact source:", str(e))
        import sys
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        emsg = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(emsg)
