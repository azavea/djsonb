# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import
from django.test import TestCase

from .models import JsonBModel

from djsonb.lookups import (FilterTree,
                            traversal_string,
                            containment_filter,
                            intrange_filter)

class JsonBFilterTests(TestCase):
    def setUp(self):
        self.mock_rule = {'_rule_type': 'sort of a cheat'}
        self.mock_int_rule = {'_rule_type': 'intrange', 'min': 1, 'max': 5}
        self.mock_contains_rule = {'_rule_type': 'containment', 'contains': ['test1', 'a thing']}

        self.two_rules = {'testing': self.mock_int_rule,
                          'alpha': {'beta': {'gamma': {'delta': self.mock_rule},
                                    'distraction': []}}}
        self.two_rule_tree = FilterTree(self.two_rules, 'data')

        self.containment_object = {'a': {'b': {'c': self.mock_contains_rule}}}
        self.containment_tree = FilterTree(self.containment_object, 'data')

        self.distraction = {'alpha': {'beta': {'gamma': {'delta': self.mock_int_rule}, 'distraction': []}}}
        self.distraction_tree = FilterTree(self.distraction, 'data')

    def test_traversal_string_creation(self):
        self.assertEqual(traversal_string(['a', 'b', 'c']), u"a->%s->>%s")

    def test_intrange_rules(self):
        self.assertEqual(self.two_rule_tree.rules, [(['data', 'testing'], self.mock_int_rule)])
        self.assertEqual(self.distraction_tree.rules,
                         [(['data', 'alpha', 'beta', 'gamma', 'delta'], self.mock_int_rule)])

    def test_containment_rules(self):
        self.assertEqual(self.containment_tree.rules,
                         [(['data', 'a', 'b', 'c'], self.mock_contains_rule)])

    def test_intrange_sql(self):
        self.assertEqual(self.two_rule_tree.sql(),
                         (u'((data->>%s)::int <= %s AND (data->>%s)::int >= %s)', ('testing', 5, 'testing', 1)))
        self.assertEqual(self.distraction_tree.sql(),
                         ('((data->%s->%s->%s->>%s)::int <= %s AND (data->%s->%s->%s->>%s)::int >= %s)', ('alpha', 'beta', 'gamma', 'delta', 5, 'alpha', 'beta', 'gamma', 'delta', 1)))

    def test_containment_sql(self):
        self.assertEqual(self.containment_tree.sql(),
                         ("(data @> %s OR data @> %s)",
                          ('{"a": {"b": {"c": "test1"}}}', '{"a": {"b": {"c": "a thing"}}}')))

    def test_containment_output(self):
        self.assertEqual(containment_filter(['a', 'b'], self.mock_contains_rule),
                         ('(a @> %s OR a @> %s)',
                          ['{"b": "test1"}', '{"b": "a thing"}']))


    def test_containment_query(self):
        JsonBModel.objects.create(data={'a': {'b': {'c': 1}}})
        JsonBModel.objects.create(data={'a': {'b': {'c': 2000}}})

        filt = {'a': {'b': {'c': {'_rule_type': 'containment', 'contains': [1, 2, 3]}}}}
        query = JsonBModel.objects.filter(data__jsonb=filt)
        self.assertEqual(query.count(), 1)

        filt2 = {'a': {'b': {'c': {'_rule_type': 'containment', 'contains': [1, 2000, 3]}}}}
        query2 = JsonBModel.objects.filter(data__jsonb=filt2)
        self.assertEqual(query2.count(), 2)

    def test_intrange_query(self):
        JsonBModel.objects.create(data={'a': {'b': {'c': 1}}})
        JsonBModel.objects.create(data={'a': {'b': {'c': 2000}}})

        filt = {'a': {'b': {'c': {'_rule_type': 'intrange', 'min': 1, 'max': 5}}}}
        query = JsonBModel.objects.filter(data__jsonb=filt)
        self.assertEqual(query.count(), 1)

        filt2 = {'a': {'b': {'c': {'_rule_type': 'intrange', 'min': 1, 'max': 2005}}}}
        query2 = JsonBModel.objects.filter(data__jsonb=filt2)
        self.assertEqual(query2.count(), 2)

    def test_multiple_filters(self):
        """This test depends on all of the logic for containment and intrange and uses both in
        the same query
        """
        JsonBModel.objects.create(data={'a': {'b': {'c': 1, 'd': 25}}})
        JsonBModel.objects.create(data={'a': {'b': {'c': 2000, 'd': 9000}}})

        filt1 = {'a': {'b': {'c': {'_rule_type': 'intrange',
                                   'min': 1, 'max': 5},
                             'd': {'_rule_type': 'containment',
                                   'contains': [0, 25, 92, 23, 44, 123, 21, 32,
                                                12, 32, 42, 12, 23123, 213, 23,
                                                421, 123, 12]}}}}
        query1 = JsonBModel.objects.filter(data__jsonb=filt1)
        self.assertEqual(query1.count(), 1)

        filt2 = filt1.copy()
        filt2['a']['b']['d']['contains'].append(9000)
        query2 = JsonBModel.objects.filter(data__jsonb=filt2)
        self.assertEqual(query2.count(), 1)

        filt3 = filt2.copy()
        filt3['a']['b']['c']['max'] = 9000
        query3 = JsonBModel.objects.filter(data__jsonb=filt3)
        self.assertEqual(query3.count(), 2)

    def test_multiple_containment_filters(self):
        JsonBModel.objects.create(data={'a': {'b': {'c': "zog", 'd': "zog"}}})
        JsonBModel.objects.create(data={'a': {'b': {'c': "zog", 'd': 9000}}})

        filt1 = {'a': {'b': {'c': {'_rule_type': 'containment',
                                   'contains': ['zog']},
                             'd': {'_rule_type': 'containment',
                                   'contains': ['zog']}}}}

        query1 = JsonBModel.objects.filter(data__jsonb=filt1)
        self.assertEqual(query1.count(), 1)

        filt2 = filt1.copy()
        del filt2['a']['b']['d']
        query2 = JsonBModel.objects.filter(data__jsonb=filt2)
        self.assertEqual(query2.count(), 2)

    def test_multiple_containment_multiple_filters(self):
        """Test for filters on data which has a list of objects to check"""
        JsonBModel.objects.create(data={'a': {'b': [{'c': "zog"}, {'c': "dog"}]}})
        JsonBModel.objects.create(data={'a': {'b': [{'c': "zog"}, {'c': 9000}]}})

        filt1 = {'a': {'b': {'c': {'_rule_type': 'containment_multiple',
                                   'contains': ['dog']}}}}

        query1 = JsonBModel.objects.filter(data__jsonb=filt1)
        self.assertEqual(query1.count(), 1)

        filt2 = {'a': {'b': {'c': {'_rule_type': 'containment_multiple',
                                   'contains': ['zog', 'dog']}}}}
        query2 = JsonBModel.objects.filter(data__jsonb=filt2)
        self.assertEqual(query2.count(), 2)

    def test_intrange_filter_missing_numbers(self):
        """Test to ensure that missing min and max doesn't add filters"""
        self.assertEqual(intrange_filter(['a', 'b', 'c'], {'_rule_type': 'intrange', 'min': None}),
                         ('', []))
        self.assertEqual(intrange_filter(['a', 'b', 'c'], {'_rule_type': 'intrange', 'min': 1}),
                         (u'((a->%s->>%s)::int >= %s)', [u'a', u'b', u'c', 1]))
        self.assertEqual(intrange_filter(['a', 'b', 'c'], {'_rule_type': 'intrange', 'max': 1}),
                         (u'((a->%s->>%s)::int <= %s)', [u'a', u'b', u'c', 1]))
        self.assertEqual(intrange_filter(['a', 'b', 'c'], {'_rule_type': 'intrange', 'max': 1, 'min': None}),
                         (u'((a->%s->>%s)::int <= %s)', [u'a', u'b', u'c', 1]))

