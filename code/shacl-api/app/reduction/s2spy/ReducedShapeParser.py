import sys
from s2spy.validation.ShapeParser import ShapeParser
import pathlib

PACKAGE_S2SPY_VALIDATION_PATH = str(pathlib.Path(__file__).parent.parent.parent.parent.joinpath('s2spy/validation').resolve())
sys.path.append(PACKAGE_S2SPY_VALIDATION_PATH)
import validation.sparql.SPARQLPrefixHandler as SPARQLPrefixHandler
sys.path.remove(PACKAGE_S2SPY_VALIDATION_PATH)
from app.query import Query

import logging
logger = logging.getLogger(__name__)

# Note the internal structure of ShapeParser:
# parse_shapes_from_dir --> calls for each shape: parse_constraints (--> parse_constraint), shape_references; Afterwards we call computeReducedEdges to find the involvedShapeIDs.
class ReducedShapeParser(ShapeParser):
    def __init__(self, query, targetShape, graph_traversal, remove_constraints):
        super().__init__()
        self.query = query
        self.targetShape = targetShape
        self.currentShape = None
        self.removed_constraints = {}
        self.involvedShapeIDs = []
        self.graph_traversal = graph_traversal
        self.remove_constraints = remove_constraints

    """
    Shapes are only relevant, if they (partially) occur in the query. Other shapes can be removed.
    """

    def parseShapesFromDir(self, path, shapeFormat, useSelectiveQueries, maxSplitSize, ORDERBYinQueries, replace_target_query=True, merge_old_target_query=True, prune_shape_network=True):
        shapes = super().parseShapesFromDir(path, shapeFormat,
                                               useSelectiveQueries, maxSplitSize, ORDERBYinQueries)
        if prune_shape_network:
            self.involvedShapeIDs = self.graph_traversal.traverse_graph(
                *self.computeReducedEdges(shapes), self.targetShape)            
            logger.debug("Involved Shapes:" + str(self.involvedShapeIDs))
            shapes = [s for s in shapes if s.getId() in self.involvedShapeIDs]
        else:
            logger.warn("Shape Network is not pruned!")

        logger.debug("Removed Constraints:" + str(self.removed_constraints))
        # Replacing old targetQuery with new one
        if replace_target_query:
            logger.info("Using Shape Schema WITH replaced target query!")
            for s in shapes:
                if s.getId() == self.targetShape:
                    # The Shape already has a target query
                    logger.debug("Starshaped Query:\n" + self.query.query_string)
                    if s.targetQuery and merge_old_target_query:
                        logger.debug("Old TargetDef: \n" + s.targetQuery)
                        oldTargetQuery = Query(s.targetQuery)
                        targetQuery = self.query.merge_as_target_query(
                            oldTargetQuery)
                    else:
                        if not '?x' in self.query.query_string:
                            new_query_string = self.query.query_string.replace(self.query.target_var, '?x')
                            targetQuery = Query(new_query_string).as_target_query()
                        else:
                            targetQuery = self.query.query_string
                    s.targetQuery = SPARQLPrefixHandler.getPrefixString() + targetQuery
                    logger.debug("New TargetDef:\n" + targetQuery)
        else:
            logger.warn("Using Shape Schema WITHOUT replaced target query!")
        return shapes

    """
    parseConstraint can return None, which need to be filtered.
    """
    def parseConstraints(self,shapeName, array, targetDef, constraintsId):
        self.currentShape = constraintsId[:-3]
        self.removed_constraints[self.currentShape] = []
        return [c for c in super().parseConstraints(shapeName, array, targetDef, constraintsId) if c]

    """
    Constraints are only relevant if:
        - subject and object do both NOT belong to the targetShape
        OR
        - subject or object belong to the targetShape AND the predicate is part of the query
            (-> inverted paths can be treated equally to normal paths)
    Other constraints are not relevant and result in a None.
    """

    def parseConstraint(self, varGenerator, obj, id, targetDef):
        if self.remove_constraints and (self.targetShape == self.currentShape or self.targetShape == obj.get('shape')):
            path = obj['path'][obj['path'].startswith('^'):]
            if path in self.query.get_predicates(replace_prefixes=False):
                return super().parseConstraint(varGenerator, obj, id, targetDef)
            else:
                self.removed_constraints[self.currentShape] += [obj.get('path')]
                return None
        return super().parseConstraint(varGenerator, obj, id, targetDef)

    """
    constraints and references are parsed independently based on the json. 
    Constraints that are removed in parse_constraint() should not appear in the references.
    self.removed_constraints keeps track of the removed constraints
    """

    def shapeReferences(self, constraints):
        '''
        shape_references is used to get the references in self.currentShape to other shapes. 
        It then returns ONE path of a constraint referencing to that shape (The other ones are ignored?!)
        '''
        return {c.get("shape"): c.get("path") for c in constraints
                if c.get("shape") and c.get("path") not in self.removed_constraints[self.currentShape]}

    """
    Returns unidirectional dependencies with a single exception: Reversed dependencies are included, if they aim at the targetShape.
    """

    def computeReducedEdges(self, shapes):
        """Computes the edges in the network."""
        dependencies = {s.getId(): [] for s in shapes}
        reverse_dependencies = {s.getId(): [] for s in shapes}
        for s in shapes:
            refs = s.getShapeRefs()
            if refs:
                name = s.getId()
                dependencies[name] = refs
                # Reverse Dependencies are needed if we have local semantics, in that case
                # there might be an inverse path in the query pointing to a shape which isn't reachable otherwise.
                # So we have to include all inverse dependencies from the target shape. (TODO: Is that really the case? Find example)
                if self.remove_constraints:
                    for ref in refs:
                        if ref == self.targetShape:
                            reverse_dependencies[ref].append(name)
        return dependencies, reverse_dependencies
