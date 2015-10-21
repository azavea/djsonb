# -*- coding: utf-8 -*-
import json

from django.db.models import Lookup


class FilterTree:
    """This class should properly assemble the pieces necessary to write the WHERE clause of
    a postgres query
    The jsonb_filter_field property of your view should designate the
    name of the column to filter by.
    Manually filtering by way of Django's ORM might look like:
    Something.objects.filter(<jsonb_field>__jsonb=<filter_specification>)

    Check out the tests for some real examples"""

    def __init__(self, tree, field):
        self.field = field
        self.tree = tree
        self.rules = self.get_rules(self.tree)

    def is_rule(self, obj):
        """Check for bottoming out the recursion in `get_rules`"""
        if '_rule_type' in obj:
            if obj['_rule_type'] not in ['intrange', 'containment', 'containment_multiple']:
                return False
            else:
                return True
        else:
            return False

    def get_rules(self, obj, current_path=[]):
        """Recursively crawl a dict looking for filtering rules"""
        # If node isn't a rule or dictionary
        if type(obj) != dict:
            return []

        # If node is a rule return its location and its details
        if self.is_rule(obj):
            return [([self.field] + current_path, obj)]

        rules = []
        for path, val in obj.items():
            rules = rules + self.get_rules(val, current_path + [path])
        return rules

    def sql(self):
        """Produce output that can be compiled into SQL by Django and psycopg2.

        The format of the output should be a tuple of a (template) string followed by a list
        of parameters for compiling that template
        """
        rule_specs = []
        for rule in self.rules:
            # If not a properly registered rule type
            if '_rule_type' not in rule[1]:
                pass
            rule_type = rule[1]['_rule_type']

            if rule_type == 'intrange':
                rule_specs.append(intrange_filter(rule[0], rule[1]))
            if rule_type == 'containment':
                rule_specs.append(containment_filter(rule[0], rule[1]))
            if rule_type == 'containment_multiple':
                rule_specs.append(multiple_containment_filter(rule[0], rule[1]))
        rule_strings = [rule[0] for rule in rule_specs]
        # flatten the rule_paths
        rule_paths_test = [rule[1] for rule in rule_specs]
        rule_paths = [item for sublist in rule_paths_test
                      for item in sublist]
        outcome = (' AND '.join(rule_strings), tuple(rule_paths))
        return outcome


# Utility functions
def traversal_string(path):
    """Construct traversal instructions for Postgres from a list of nodes
    like: '%s->%S->%s->>%s' for {a: {b: {c: value } } }
    """
    fmt_strs = [path[0]] + ['%s' for leaf in path[1:]]
    traversal = '->'.join(fmt_strs[:-1]) + '->>%s'
    return traversal


def reconstruct_object(path):
    """Reconstruct the object from root to leaf, recursively"""
    if len(path) == 0:
        return '%s'
    else:
        # The indexed query on `path` below is the means by which we recurse
        #  Every iteration pushes it closer to a length of 0 and, thus, bottoming out
        return '{{%s: {recons}}}'.format(recons=reconstruct_object(path[1:]))


def reconstruct_object_multiple(path):
    """Reconstruct the object from root to leaf, recursively"""
    if len(path) == 0:
        return '%s'
    elif len(path) == 2:
        return '{{%s: [{recons}]}}'.format(recons=reconstruct_object_multiple(path[1:]))
    else:
        # The indexed query on `path` below is the means by which we recurse
        #  Every iteration pushes it closer to a length of 0 and, thus, bottoming out
        #  This function differs from the singular reconstruction in that the final object
        #  gets wrapped in a list (when length is 2, there should be a key and a value left)
        return '{{%s: {recons}}}'.format(recons=reconstruct_object_multiple(path[1:]))


# Filters
def containment_filter(path, range_rule):
    """Filter for objects that contain the specified value at some location"""
    template = reconstruct_object(path[1:])
    has_containment = 'contains' in range_rule
    abstract_contains_str = path[0] + " @> %s"

    if has_containment:
        all_contained = range_rule.get('contains')

    contains_params = []
    json_path = [json.dumps(x) for x in path[1:]]
    for contained in all_contained:
        interpolants = tuple(json_path + [json.dumps(contained)])
        contains_params.append(template % interpolants)

    contains_str = ' OR '.join([abstract_contains_str] * len(all_contained))

    return ('(' + contains_str + ')', contains_params)


def multiple_containment_filter(path, range_rule):
    """Filter for objects that contain the specified value in any of the objects in a given list"""
    template = reconstruct_object_multiple(path[1:])
    has_containment = 'contains' in range_rule
    abstract_contains_str = path[0] + " @> %s"

    if has_containment:
        all_contained = range_rule.get('contains')

    contains_params = []
    json_path = [json.dumps(x) for x in path[1:]]
    for contained in all_contained:
        interpolants = tuple(json_path + [json.dumps(contained)])
        contains_params.append(template % interpolants)

    contains_str = ' OR '.join([abstract_contains_str] * len(all_contained))

    return ('(' + contains_str + ')', contains_params)


def intrange_filter(path, range_rule):
    """Filter for numbers that match boundaries provided by a rule"""
    travInt = "(" + traversal_string(path) + ")::int"
    has_min = 'min' in range_rule
    has_max = 'max' in range_rule

    if has_min:
        minimum = range_rule['min']
        less_than = ("{traversal_int} <= %s"
                     .format(traversal_int=travInt))

    if has_max:
        maximum = range_rule['max']
        more_than = ("{traversal_int} >= %s"
                     .format(traversal_int=travInt))

    if has_min and not has_max:
        return ('(' + more_than + ')', path + [minimum])
    elif has_max and not has_min:
        return ('(' + less_than + ')', path + [maximum])
    elif has_max and has_min:
        min_and_max = '(' + less_than + ' AND ' + more_than + ')'
        return (min_and_max, path[1:] + [maximum] + path[1:] + [minimum])


class DriverLookup(Lookup):
    lookup_name = 'jsonb'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)

        return FilterTree(rhs_params[0], lhs).sql()
