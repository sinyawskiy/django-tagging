# -*- coding: utf-8 -*-

import os
from django import forms
from django.db.models import Q
from django.test import TestCase
from tagging.forms import TagField
from tagging import settings
from tagging.models import Tag, TaggedItem
from tagging.tests.models import Article, Link, Perch, Parrot, FormTest
from tagging.utils import calculate_cloud, check_tag_length, edit_string_for_tags, get_tag_list, get_tag_parts, get_tag, parse_tag_input, split_strip
from tagging.utils import LINEAR

#############
# Utilities #
#############

class TestParseTagInput(TestCase):
    def test_with_simple_space_delimited_tags(self):
        """ Test with simple space-delimited tags. """
        
        self.assertEquals(parse_tag_input('one'), [u'one'])
        self.assertEquals(parse_tag_input('one two'), [u'one', u'two'])
        self.assertEquals(parse_tag_input('one two three'), [u'one', u'three', u'two'])
        self.assertEquals(parse_tag_input('one one two two'), [u'one', u'two'])
        self.assertEquals(parse_tag_input('first:one'), [u'first:one'])
        self.assertEquals(parse_tag_input('first:one two'), [u'first:one', u'two'])
        self.assertEquals(parse_tag_input('one= second:two :three'),
            [u'one', u'second:two', u'three'])
        self.assertEquals(parse_tag_input(':one= :two= =three:'),
            [u'one', u'three', u'two'])
        self.assertEquals(parse_tag_input('=one=two :three:four'),
            [u'"three:four"', u'one=two'])
        self.assertEquals(parse_tag_input(':=one:two=three=:'),
            [u'"one:two"="three=:"'])
        self.assertEquals(parse_tag_input('second:one first:one'),
            [u'first:one', u'second:one'])
        self.assertEquals(parse_tag_input('first:one first:two'),
            [u'first:one', u'first:two'])
        self.assertEquals(parse_tag_input('first:one first:one second:one'),
            [u'first:one', u'second:one'])
        self.assertEquals(parse_tag_input('one=two'), [u'one=two'])
        self.assertEquals(parse_tag_input('three=four one=two'),
            [u'one=two', u'three=four'])
        self.assertEquals(parse_tag_input('one=two one=three'),
            [u'one=three', u'one=two'])
        self.assertEquals(parse_tag_input('first:one=two'), [u'first:one=two'])
        self.assertEquals(parse_tag_input('second:one=three first:one=two'),
            [u'first:one=two', u'second:one=three'])
        self.assertEquals(parse_tag_input('first:one:two=three:four=five'),
            [u'first:"one:two"="three:four=five"'])
    
    def test_with_comma_delimited_multiple_words(self):
        """ Test with comma-delimited multiple words.
            An unquoted comma in the input will trigger this. """
            
        self.assertEquals(parse_tag_input(',one'), [u'one'])
        self.assertEquals(parse_tag_input(',one two'), [u'one two'])
        self.assertEquals(parse_tag_input('one two,'), [u'one two'])
        self.assertEquals(parse_tag_input(',one two three'), [u'one two three'])
        self.assertEquals(parse_tag_input('one two three,'), [u'one two three'])
        self.assertEquals(parse_tag_input('a-one, a-two and a-three'),
            [u'a-one', u'a-two and a-three'])
        self.assertEquals(parse_tag_input('a:one, a:two and a=three'),
            [u'a:one', u'a:two and a=three'])
        self.assertEquals(parse_tag_input('a:one, a:two and a:three'),
            [u'a:"two and a:three"', u'a:one'])
        self.assertEquals(parse_tag_input('a:one, a:one=two a:one=two'),
            [u'a:one', u'a:one="two a:one=two"'])
    
    def test_with_double_quoted_multiple_words(self):
        """ Test with double-quoted multiple words.
            A completed quote will trigger this.  Unclosed quotes are ignored. """
            
        self.assertEquals(parse_tag_input('"one'), [u'one'])
        self.assertEquals(parse_tag_input('one"'), [u'one'])
        self.assertEquals(parse_tag_input('"one two'), [u'one', u'two'])
        self.assertEquals(parse_tag_input('"one two three'), [u'one', u'three', u'two'])
        self.assertEquals(parse_tag_input('"one two"'), [u'one two'])
        self.assertEquals(parse_tag_input('a-one "a-two and a-three"'),
            [u'a-one', u'a-two and a-three'])
        self.assertEquals(parse_tag_input('"one""two" "three"'), [u'onetwo', u'three'])
        self.assertEquals(parse_tag_input('":one'), [u'one'])
        self.assertEquals(parse_tag_input('one="'), [u'one'])
        self.assertEquals(parse_tag_input('"one:two"'), [u'"one:two"'])
        self.assertEquals(parse_tag_input('one:"two three"'), [u'one:two three'])
        self.assertEquals(parse_tag_input('"one:"two"=three"'), [u'"one:two=three"'])
        self.assertEquals(parse_tag_input('"one:"two"=three'), [u'"one:two"=three'])
        self.assertEquals(parse_tag_input(':"=one":two=three=:'),
            [u'"=one:two"="three=:"'])
    
    def test_with_no_loose_commas(self):
        """ Test with no loose commas -- split on spaces. """
        self.assertEquals(parse_tag_input('one two "thr,ee"'), [u'one', u'thr,ee', u'two'])
        self.assertEquals(parse_tag_input('one two:"thr,ee"'), [u'one', u'two:thr,ee'])
        self.assertEquals(parse_tag_input('one:two three=four'), [u'one:two', u'three=four'])
        
    def test_with_loose_commas(self):
        """ Loose commas - split on commas """
        self.assertEquals(parse_tag_input('"one", two three'), [u'one', u'two three'])
        self.assertEquals(parse_tag_input('"one", two:three four=five'),
            [u'one', u'two:three four=five'])
        
    def test_tags_with_double_quotes_can_contain_commas(self):
        """ Double quotes can contain commas """
        self.assertEquals(parse_tag_input('a-one "a-two, and a-three"'),
            [u'a-one', u'a-two, and a-three'])
        self.assertEquals(parse_tag_input('"two", one, one, two, "one"'),
            [u'one', u'two'])
    
    def test_with_naughty_input(self):
        """ Test with naughty input. """
        
        # Bad users! Naughty users!
        self.assertEquals(parse_tag_input(None), [])
        self.assertEquals(parse_tag_input(''), [])
        self.assertEquals(parse_tag_input('"'), [])
        self.assertEquals(parse_tag_input('""'), [])
        self.assertEquals(parse_tag_input('"' * 7), [])
        self.assertEquals(parse_tag_input(',,,,,,'), [])
        self.assertEquals(parse_tag_input('",",",",",",","'), [u','])
        self.assertEquals(parse_tag_input(':'), [])
        self.assertEquals(parse_tag_input(':::::::'), [u'"::::::"'])
        self.assertEquals(parse_tag_input('='), [])
        self.assertEquals(parse_tag_input('=' * 7), [])
        self.assertEquals(parse_tag_input(':,:,=,=,:,=,:,='), [])
        self.assertEquals(parse_tag_input(':= := =: =: : = = :'), [])
        self.assertEquals(parse_tag_input('":":":":"="="=":"="'), [u'":":"::="="=:="'])
        self.assertEquals(parse_tag_input('a-one "a-two" and "a-three'),
            [u'a-one', u'a-three', u'a-two', u'and'])

class TestSplitStrip(TestCase):
    def test_with_empty_input(self):
        self.assertEquals(split_strip(' foo '), [u'foo'])
        self.assertEquals(split_strip(' foo , bar '), [u'foo', u'bar'])
        self.assertEquals(split_strip(', foo , bar ,'), [u'foo', u'bar'])
        self.assertEquals(split_strip(None), [])
    
    def test_with_different_whitespace(self):
        self.assertEquals(split_strip(' foo\t,\nbar '), [u'foo', u'bar'])

    def test_with_athor_delimiter(self):
        self.assertEquals(split_strip(' foo bar ', ' '), [u'foo', u'bar'])
    
    def test_non_empty_input(self):
        self.assertEquals(split_strip(''), [])
        self.assertEquals(split_strip(None), [])

class TestNormalisedTagListInput(TestCase):
    def setUp(self):
        self.cheese = Tag.objects.create(name='cheese')
        self.toast = Tag.objects.create(name='toast')
        self.spam_egg = Tag.objects.create(namespace='spam', name='egg')
    
    def test_single_tag_object_as_input(self):
        self.assertEquals(get_tag_list(self.cheese), [self.cheese])
    
    def test_single_string_as_input(self):
        ret = get_tag_list('cheese')
        self.assertEquals(len(ret), 1)
        self.failUnless(self.cheese in ret)
        ret = get_tag_list('spam:egg')
        self.assertEquals(len(ret), 1)
        self.failUnless(self.spam_egg in ret)
    
    def test_space_delimeted_string_as_input(self):
        ret = get_tag_list('cheese toast')
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_comma_delimeted_string_as_input(self):
        ret = get_tag_list('cheese,toast')
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_namespaced_string_as_input(self):
        ret = get_tag_list('cheese spam:egg')
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.spam_egg in ret)
    
    def test_invalid_string_as_input(self):
        ret = get_tag_list('=')
        self.assertEquals(len(ret), 0)
        ret = get_tag_list(':')
        self.assertEquals(len(ret), 0)
        ret = get_tag_list('"":""=""')
        self.assertEquals(len(ret), 0)
    
    def test_list_of_invalid_string_as_input(self):
        ret = get_tag_list([''])
        self.assertEquals(len(ret), 0)
        ret = get_tag_list(['='])
        self.assertEquals(len(ret), 0)
        ret = get_tag_list([':'])
        self.assertEquals(len(ret), 0)
        ret = get_tag_list(['"":""=""'])
        self.assertEquals(len(ret), 0)
    
    def test_with_empty_list(self):
        self.assertEquals(get_tag_list([]), [])

    def test_with_single_tag_instance(self):
        ret = get_tag_list(self.cheese)
        self.assertEquals(len(ret), 1)
        self.failUnless(self.cheese in ret)
    
    def test_list_of_two_strings(self):
        ret = get_tag_list(['cheese', 'toast'])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
        ret = get_tag_list(['cheese', 'spam:egg'])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.spam_egg in ret)
    
    def test_list_of_tag_primary_keys(self):
        ret = get_tag_list([self.cheese.id, self.toast.id])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_list_of_strings_with_strange_nontag_string(self):
        ret = get_tag_list(['cheese', 'toast', 'ŠĐĆŽćžšđ'])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_list_of_tag_instances(self):
        ret = get_tag_list([self.cheese, self.toast])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_tuple_of_instances(self):
        ret = get_tag_list((self.cheese, self.toast))
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_with_tag_filter(self):
        ret = get_tag_list(Tag.objects.filter(name__in=['cheese', 'toast']))
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
        
    def test_with_invalid_input_mix_of_string_and_instance(self):
        try:
            get_tag_list(['cheese', self.toast])
        except ValueError, ve:
            self.assertEquals(str(ve),
                'If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')
    
    def test_with_invalid_input(self):
        try:
            get_tag_list(29)
        except ValueError, ve:
            self.assertEquals(str(ve), 'The tag input given was invalid.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')

    def test_with_tag_instance(self):
        self.assertEquals(get_tag(self.cheese), self.cheese)
        self.assertEquals(get_tag(self.cheese), self.cheese)
    
    def test_with_string(self):
        self.assertEquals(get_tag('cheese'), self.cheese)
    
    def test_with_primary_key(self):
        self.assertEquals(get_tag(self.cheese.id), self.cheese)
    
    def test_nonexistent_tag(self):
        self.assertEquals(get_tag('mouse'), None)

class TestCalculateCloud(TestCase):
    def setUp(self):
        self.tags = []
        for line in open(os.path.join(os.path.dirname(__file__), 'tags.txt')).readlines():
            parts, count = line.rstrip().split()
            tag = Tag(**get_tag_parts(parts))
            tag.count = int(count)
            self.tags.append(tag)
    
    def test_default_distribution(self):
        sizes = {}
        for tag in calculate_cloud(self.tags, steps=5):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1
        
        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEquals(sizes[1], 48)
        self.assertEquals(sizes[2], 30)
        self.assertEquals(sizes[3], 19)
        self.assertEquals(sizes[4], 15)
        self.assertEquals(sizes[5], 10)
    
    def test_linear_distribution(self):
        sizes = {}
        for tag in calculate_cloud(self.tags, steps=5, distribution=LINEAR):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1
        
        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEquals(sizes[1], 97)
        self.assertEquals(sizes[2], 12)
        self.assertEquals(sizes[3], 7)
        self.assertEquals(sizes[4], 2)
        self.assertEquals(sizes[5], 4)
    
    def test_invalid_distribution(self):
        try:
            calculate_cloud(self.tags, steps=5, distribution='cheese')
        except ValueError, ve:
            self.assertEquals(str(ve), 'Invalid distribution algorithm specified: cheese.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')

class TestGetTag(TestCase):
    def setUp(self):
        self.foo_tag = Tag.objects.create(name='foo')
        self.foobar_tag = Tag.objects.create(name='foo:bar')
        self.barbaz_tag = Tag.objects.create(name='bar=baz')
        self.bar_baz_tag = Tag.objects.create(name='bar', value='baz')
        self.foo_bar_tag = Tag.objects.create(name='bar', namespace='foo')
        self.foo_bar_baz_tag = Tag.objects.create(name='bar', namespace='foo', value='baz')
        self.one_tag = Tag.objects.create(name='two three', namespace='one', value='four')
        self.sign_tag = Tag.objects.create(name=':=', namespace=':=', value=':=')
        
    def test_simple_tags(self):
        self.failUnless(get_tag('foo'), self.foo_tag)
        self.failUnless(get_tag('"foo:bar"'), self.foobar_tag)
        self.failUnless(get_tag('foo:bar'), self.foo_bar_tag)
        self.failUnless(get_tag('"bar=baz"'), self.barbaz_tag)
        self.failUnless(get_tag('bar=baz'), self.bar_baz_tag)
        self.failUnless(get_tag('foo:bar=baz'), self.bar_baz_tag)
        self.failUnless(get_tag('"foo":"bar"="baz"'), self.bar_baz_tag)
        self.failUnless(get_tag('one:"two three"=four'), self.one_tag)
        self.failUnless(get_tag('":=":":="=":="'), self.sign_tag)

class TestGetTagParts(TestCase):
    def test_simple_cases(self):
        self.assertEquals(get_tag_parts('bar'),
            {'namespace': None, 'name': 'bar', 'value': None})
        self.assertEquals(get_tag_parts('foo:bar'),
            {'namespace': 'foo', 'name': 'bar', 'value': None})
        self.assertEquals(get_tag_parts('bar=baz'),
            {'namespace': None, 'name': 'bar', 'value': 'baz'})
        self.assertEquals(get_tag_parts('foo:bar=baz'),
            {'namespace': 'foo', 'name': 'bar', 'value': 'baz'})
        self.assertEquals(get_tag_parts(' foo: bar =baz '),
            {'namespace': ' foo', 'name': ' bar ', 'value': 'baz '})

    def test_with_quotes(self):
        self.assertEquals(get_tag_parts('"bar="'),
            {'namespace': None, 'name': 'bar=', 'value': None})
        self.assertEquals(get_tag_parts('":="'),
            {'namespace': None, 'name': ':=', 'value': None})
        self.assertEquals(get_tag_parts('":=":":="=":="'),
            {'namespace': ':=', 'name': ':=', 'value': ':='})

class TestCheckTagLength(TestCase):
    def setUp(self):
        self.original_max_tag_length = settings.MAX_TAG_LENGTH
        self.original_max_tag_name_length = settings.MAX_TAG_NAME_LENGTH
        self.original_max_tag_namespace_length = settings.MAX_TAG_NAMESPACE_LENGTH
        self.original_max_tag_value_length = settings.MAX_TAG_VALUE_LENGTH
    
    def tearDown(self):
        settings.MAX_TAG_LENGTH = self.original_max_tag_length
        settings.MAX_TAG_NAME_LENGTH = self.original_max_tag_name_length
        settings.MAX_TAG_NAMESPACE_LENGTH = self.original_max_tag_namespace_length
        settings.MAX_TAG_VALUE_LENGTH = self.original_max_tag_value_length
    
    def test_total_tag_length(self):
        settings.MAX_TAG_LENGTH = 50
        settings.MAX_TAG_NAME_LENGTH = 40
        settings.MAX_TAG_NAMESPACE_LENGTH = 10
        settings.MAX_TAG_VALUE_LENGTH = 10
        try:
            check_tag_length({'namespace': None, 'name': 'a' * 40, 'value': None})
        except Exception, e:
            self.fail(e)
        try:
            check_tag_length({'namespace': None, 'name': 'a' * 41, 'value': None})
            self.fail()
        except ValueError, ve:
            self.assertEquals(ve.args[1], 'name')
        try:
            check_tag_length({'namespace': 'a' * 10, 'name': 'a', 'value': None})
        except Exception, e:
            self.fail(e)
        try:
            check_tag_length({'namespace': 'a' * 11, 'name': 'a', 'value': None})
            self.fail()
        except ValueError, ve:
            self.assertEquals(ve.args[1], 'namespace')
        try:
            check_tag_length({'namespace': None, 'name': 'a', 'value': 'a' * 10})
        except Exception, e:
            self.fail(e)
        try:
            check_tag_length({'namespace': None, 'name': 'a', 'value': 'a' * 11})
            self.fail()
        except ValueError, ve:
            self.assertEquals(ve.args[1], 'value')
        try:
            check_tag_length({'namespace': 'a' * 10, 'name': 'a' * 30, 'value': 'a' * 10})
        except Exception, e:
            self.fail(e)
        try:
            check_tag_length({'namespace': 'a' * 10, 'name': 'a' * 30, 'value': 'a' * 11})
            self.fail()
        except ValueError, ve:
            self.assertEquals(ve.args[1], 'tag')

#########
# Model #
#########

class TestTagModel(TestCase):
    def test_unicode_behaviour(self):
        self.assertEqual(unicode(Tag(name='foo')), u'foo')
        self.assertEqual(unicode(Tag(namespace='foo', name='bar')), u'foo:bar')
        self.assertEqual(unicode(Tag(name='foo', value='bar')), u'foo=bar')
        self.assertEqual(unicode(Tag(namespace='foo', name='bar', value='baz')), u'foo:bar=baz')
        self.assertEqual(unicode(Tag(name='foo:bar')), u'"foo:bar"')
        self.assertEqual(unicode(Tag(name='foo:bar=baz')), u'"foo:bar=baz"')
        self.assertEqual(unicode(Tag(namespace='spam', name='foo:bar=baz')), u'spam:"foo:bar=baz"')
        self.assertEqual(unicode(Tag(namespace='spam', name='foo:bar=baz', value='egg')), u'spam:"foo:bar=baz"=egg')
        self.assertEqual(unicode(Tag(namespace='spam:egg', name='foo:bar=baz')), u'"spam:egg":"foo:bar=baz"')
        self.assertEqual(unicode(Tag(name='foo:bar=baz', value='spam:egg')), u'"foo:bar=baz"="spam:egg"')
        self.assertEqual(unicode(Tag(namespace=':', name=':=', value='=')), u'":":":="="="')

###########
# Tagging #
###########

class TestBasicTagging(TestCase):
    def setUp(self):
        self.dead_parrot = Parrot.objects.create(state='dead')
    
    def test_update_tags(self):
        Tag.objects.update_tags(self.dead_parrot, 'foo,bar,"ter"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('ter') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, '"foo" bar "baz"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, '"foo":bar "baz"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 2)
        self.failUnless(get_tag('foo:bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, '"foo":bar="baz"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.failUnless(get_tag('foo:bar=baz') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, 'bar="baz"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.failUnless(get_tag('bar=baz') in tags)
    
    def test_add_tag(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        # try to add a tag that already exists
        Tag.objects.add_tag(self.dead_parrot, 'foo')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        # now add a tag that doesn't already exist
        Tag.objects.add_tag(self.dead_parrot, 'zip')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 4)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)

        # try to add a tag that has the same name of an existing but a
        # different namespace and a tag that looks the same but quoted
        Tag.objects.add_tag(self.dead_parrot, 'foo:bar')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 5)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('foo:bar') in tags)
        
        # try to add a tag that looks like an already existent namespaced tag
        # but is quoted
        Tag.objects.add_tag(self.dead_parrot, '"foo:bar"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 6)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('foo:bar') in tags)
        self.failUnless(get_tag('"foo:bar"') in tags)
        
        # now add a tag with namespace that already exists
        Tag.objects.add_tag(self.dead_parrot, 'foo:bar')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 6)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('foo:bar') in tags)
        self.failUnless(get_tag('"foo:bar"') in tags)
        
        # add a tag with namespace and value
        Tag.objects.add_tag(self.dead_parrot, 'foo:bar=baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 7)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('foo:bar') in tags)
        self.failUnless(get_tag('"foo:bar"') in tags)
        self.failUnless(get_tag('"foo":"bar"="baz"') in tags)
    
    def test_add_tag_invalid_input_no_tags_specified(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        invalid_input = ['     ', ':', '=', ':=']
        for input in invalid_input:
            try:
                Tag.objects.add_tag(self.dead_parrot, input)
            except AttributeError, ae:
                self.assertEquals(str(ae), 'No tags were given: "%s".' % input)
            except Exception, e:
                raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                    (str(type(e)), str(e)))
            else:
                raise self.failureException('an AttributeError exception was supposed to be raised!')
        
    def test_add_tag_invalid_input_multiple_tags_specified(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        try:
            Tag.objects.add_tag(self.dead_parrot, 'one two')
        except AttributeError, ae:
            self.assertEquals(str(ae), 'Multiple tags were given: "one two".')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('an AttributeError exception was supposed to be raised!')
    
    def test_update_tags_exotic_characters(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, u'ŠĐĆŽćžšđ')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0].name, u'ŠĐĆŽćžšđ')
        
        Tag.objects.update_tags(self.dead_parrot, u'你好')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0].name, u'你好')
    
    def test_update_tags_with_none(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, None)
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 0)

class TestModelTagField(TestCase):
    """ Test the 'tags' field on models. """
    
    def test_create_with_tags_specified(self):
        f1 = FormTest.objects.create(tags=u'test3 test2 test1 one:"two three"=four')
        tags = Tag.objects.get_for_object(f1)
        test1_tag = get_tag('test1')
        test2_tag = get_tag('test2')
        test3_tag = get_tag('test3')
        one_tag = get_tag('one:"two three"=four')
        self.failUnless(None not in (test1_tag, test2_tag, test3_tag, one_tag))
        self.assertEquals(len(tags), 4)
        self.failUnless(test1_tag in tags)
        self.failUnless(test2_tag in tags)
        self.failUnless(test3_tag in tags)
        self.failUnless(one_tag in tags)
    
    def test_update_via_tags_field(self):
        f1 = FormTest.objects.create(tags=u'test3 test2 test1')
        tags = Tag.objects.get_for_object(f1)
        test1_tag = get_tag('test1')
        test2_tag = get_tag('test2')
        test3_tag = get_tag('test3')
        self.failUnless(None not in (test1_tag, test2_tag, test3_tag))
        self.assertEquals(len(tags), 3)
        self.failUnless(test1_tag in tags)
        self.failUnless(test2_tag in tags)
        self.failUnless(test3_tag in tags)
        
        f1.tags = u'test4'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        test4_tag = get_tag('test4')
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0], test4_tag)
        
        f1.tags = u'foo:bar'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        foo_bar_tag = get_tag('foo:bar')
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0], foo_bar_tag)
        
        f1.tags = ''
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        self.assertEquals(len(tags), 0)
        
class TestSettings(TestCase):
    def setUp(self):
        self.original_force_lower_case_tags = settings.FORCE_LOWERCASE_TAGS
        self.dead_parrot = Parrot.objects.create(state='dead')
    
    def tearDown(self):
        settings.FORCE_LOWERCASE_TAGS = self.original_force_lower_case_tags
    
    def test_force_lowercase_tags(self):
        """ Test forcing tags to lowercase. """
        
        settings.FORCE_LOWERCASE_TAGS = True
        
        Tag.objects.update_tags(self.dead_parrot, 'foO bAr Ter')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        foo_tag = get_tag('foo')
        bar_tag = get_tag('bar')
        ter_tag = get_tag('ter')
        self.failUnless(foo_tag in tags)
        self.failUnless(bar_tag in tags)
        self.failUnless(ter_tag in tags)
        
        Tag.objects.update_tags(self.dead_parrot, 'foO bAr baZ')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        baz_tag = get_tag('baz')
        self.assertEquals(len(tags), 3)
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        
        Tag.objects.add_tag(self.dead_parrot, 'FOO')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        
        Tag.objects.add_tag(self.dead_parrot, 'Zip')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 4)
        zip_tag = get_tag('zip')
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        self.failUnless(zip_tag in tags)
        
        Tag.objects.add_tag(self.dead_parrot, 'Foo:bAr=ziP')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 5)
        foo_bar_zip_tag = get_tag('foo:bar=zip')
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        self.failUnless(zip_tag in tags)
        self.failUnless(foo_bar_zip_tag in tags)
        
        f1 = FormTest.objects.create()
        f1.tags = u'TEST5'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        test5_tag = get_tag('test5')
        self.assertEquals(len(tags), 1)
        self.failUnless(test5_tag in tags)
        self.assertEquals(f1.tags, u'test5')
        
        f1.tags = u'TEST5 FOO:BAR=TAR'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        foo_bar_tar_tag = get_tag('foo:bar=tar')
        self.assertEquals(len(tags), 2)
        self.failUnless(test5_tag in tags)
        self.failUnless(foo_bar_tar_tag in tags)
        self.assertEquals(f1.tags, u'test5 foo:bar=tar')

class TestTagUsageForModelBaseCase(TestCase):
    def test_tag_usage_for_model_empty(self):
        self.assertEquals(Tag.objects.usage_for_model(Parrot), [])

class TestTagUsageForModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar foo:bar=egg'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter foo:bar=egg'),
            ('late',                  2, False, 'bar ter foo:bar'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
    
    def test_tag_usage_for_model(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 6)
        self.failUnless((u'bar', 3) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 3) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 2) in relevant_attribute_list)
        self.failUnless((u'foo:bar', 1) in relevant_attribute_list)
    
    def test_tag_usage_for_model_with_min_count(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, min_count = 2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 3) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 3) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 2) in relevant_attribute_list)
    
    def test_tag_usage_with_filter_on_model_objects(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state='no more'))
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state__startswith='p'))
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__size__gt=4))
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__smelly=True))
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, min_count=2, filters=dict(perch__smelly=True))
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=4))
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        self.failUnless((u'foo:bar=egg', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=99))
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 0)

class TestTagsRelatedForModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar spam:egg=ham'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter spam:egg=ham'),
            ('late',                  2, False, 'bar ter spam:foo'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
            
    def test_related_for_model_with_tag_query_sets_as_input(self):
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, min_count=2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=False)
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'count')) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', False) in relevant_attribute_list)
        self.failUnless((u'spam:foo', False) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter', 'baz']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['foo']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)

        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['foo'], namespace=None), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 2) in relevant_attribute_list)

        related_tags = Tag.objects.related_for_model(Tag.objects.filter(namespace__in=['spam']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)

        related_tags = Tag.objects.related_for_model(Tag.objects.filter(value__in=['ham']), Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)

    def test_related_for_model_with_tag_strings_as_input(self):
        # Once again, with feeling (strings)
        related_tags = Tag.objects.related_for_model('bar', Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model('spam:egg=ham', Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model('bar', Parrot, min_count=2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model('bar', Parrot, counts=False)
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'count')) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', False) in relevant_attribute_list)
        self.failUnless((u'spam:foo', False) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(['bar', 'ter'], Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(['bar', 'ter', 'baz'], Parrot, counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)
        
class TestGetTaggedObjectsByModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar spam:egg=ham'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter spam:egg=ham'),
            ('late',                  2, False, 'bar ter spam:foo'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
            
        self.foo = Tag.objects.get(namespace=None, name='foo', value=None)
        self.bar = Tag.objects.get(namespace=None, name='bar', value=None)
        self.baz = Tag.objects.get(namespace=None, name='baz', value=None)
        self.ter = Tag.objects.get(namespace=None, name='ter', value=None)
        self.spameggham = Tag.objects.get(namespace='spam', name='egg', value='ham')
        self.spamfoo = Tag.objects.get(namespace='spam', name='foo', value=None)
        
        self.pining_for_the_fjords_parrot = Parrot.objects.get(state='pining for the fjords')
        self.passed_on_parrot = Parrot.objects.get(state='passed on')
        self.no_more_parrot = Parrot.objects.get(state='no more')
        self.late_parrot = Parrot.objects.get(state='late')
        
    def test_get_by_model_simple(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, self.foo)
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.no_more_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, self.bar)
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
    
    def test_get_by_model_intersection(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.foo, self.baz])
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.foo, self.bar])
        self.assertEquals(len(parrots), 1)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.bar, self.ter])
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        
        # Issue 114 - Intersection with non-existant tags
        parrots = TaggedItem.objects.get_intersection_by_model(Parrot, [])
        self.assertEquals(len(parrots), 0)
    
    def test_get_by_model_with_tag_querysets_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'baz']))
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar']))
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.late_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar', 'ter']))
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
    
    def test_get_by_model_with_strings_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, 'foo baz')
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, 'bar')
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.late_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, 'bar ter')
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        
    def test_get_by_model_with_lists_of_strings_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, ['foo', 'baz'])
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, ['bar'])
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.late_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, ['bar', 'ter'])
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
    
    def test_get_by_nonexistent_tag(self):
        # Issue 50 - Get by non-existent tag
        parrots = TaggedItem.objects.get_by_model(Parrot, 'argatrons')
        self.assertEquals(len(parrots), 0)
    
    def test_get_union_by_model(self):
        parrots = TaggedItem.objects.get_union_by_model(Parrot, ['foo', 'ter'])
        self.assertEquals(len(parrots), 4)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.no_more_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_union_by_model(Parrot, ['bar', 'baz'])
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_union_by_model(Parrot, ['spam:foo', 'baz'])
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.late_parrot in parrots)
        
        # Issue 114 - Union with non-existant tags
        parrots = TaggedItem.objects.get_union_by_model(Parrot, [])
        self.assertEquals(len(parrots), 0)

class TestGetRelatedTaggedItems(TestCase):
    def setUp(self):
        self.l1 = Link.objects.create(name='link 1')
        Tag.objects.update_tags(self.l1, 'tag1 tag2 tag3 tag4 tag5')
        self.l2 = Link.objects.create(name='link 2')
        Tag.objects.update_tags(self.l2, 'tag1 tag2 tag3')
        self.l3 = Link.objects.create(name='link 3')
        Tag.objects.update_tags(self.l3, 'tag1')
        self.l4 = Link.objects.create(name='link 4')
        
        self.a1 = Article.objects.create(name='article 1')
        Tag.objects.update_tags(self.a1, 'tag1 tag2 tag3 tag4')
    
    def test_get_related_objects_of_same_model(self):
        related_objects = TaggedItem.objects.get_related(self.l1, Link)
        self.assertEquals(len(related_objects), 2)
        self.failUnless(self.l2 in related_objects)
        self.failUnless(self.l3 in related_objects)
        
        related_objects = TaggedItem.objects.get_related(self.l4, Link)
        self.assertEquals(len(related_objects), 0)
    
    def test_get_related_objects_of_same_model_limited_number_of_results(self):
        # This fails on Oracle because it has no support for a 'LIMIT' clause.
        # See http://asktom.oracle.com/pls/asktom/f?p=100:11:0::::P11_QUESTION_ID:127412348064
        
        # ask for no more than 1 result
        related_objects = TaggedItem.objects.get_related(self.l1, Link, num=1)
        self.assertEquals(len(related_objects), 1)
        self.failUnless(self.l2 in related_objects)
        
    def test_get_related_objects_of_same_model_limit_related_items(self):
        related_objects = TaggedItem.objects.get_related(self.l1, Link.objects.exclude(name='link 3'))
        self.assertEquals(len(related_objects), 1)
        self.failUnless(self.l2 in related_objects)
    
    def test_get_related_objects_of_different_model(self):
        related_objects = TaggedItem.objects.get_related(self.a1, Link)
        self.assertEquals(len(related_objects), 3)
        self.failUnless(self.l1 in related_objects)
        self.failUnless(self.l2 in related_objects)
        self.failUnless(self.l3 in related_objects)
            
        Tag.objects.update_tags(self.a1, 'tag6')
        related_objects = TaggedItem.objects.get_related(self.a1, Link)
        self.assertEquals(len(related_objects), 0)
        
class TestTagUsageForQuerySet(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar spam:egg=ham'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter spam:egg=ham'),
            ('late',                  2, False, 'bar ter spam:foo'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
    
    def test_tag_usage_for_queryset(self):
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(state='no more'), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(state__startswith='p'), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), min_count=2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4))
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=99))
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 0)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), min_count=2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')))
        relevant_attribute_list = [(unicode(tag), hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', False) in relevant_attribute_list)
        self.failUnless((u'spam:foo', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(state='passed on'), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 5)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 2) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(state__startswith='p'), min_count=2)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(Q(perch__size__gt=6) | Q(perch__smelly=False)), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:egg=ham', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(perch__smelly=True).filter(state__startswith='l'), counts=True)
        relevant_attribute_list = [(unicode(tag), tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        self.failUnless((u'spam:foo', 1) in relevant_attribute_list)
        
################
# Model Fields #
################

class TestTagFieldInForms(TestCase):
    def setUp(self):
        self.original_max_tag_length = settings.MAX_TAG_LENGTH
        self.original_max_tag_name_length = settings.MAX_TAG_NAME_LENGTH
        self.original_max_tag_namespace_length = settings.MAX_TAG_NAMESPACE_LENGTH
        self.original_max_tag_value_length = settings.MAX_TAG_VALUE_LENGTH
    
    def tearDown(self):
        settings.MAX_TAG_LENGTH = self.original_max_tag_length
        settings.MAX_TAG_NAME_LENGTH = self.original_max_tag_name_length
        settings.MAX_TAG_NAMESPACE_LENGTH = self.original_max_tag_namespace_length
        settings.MAX_TAG_VALUE_LENGTH = self.original_max_tag_value_length

    def test_tag_field_in_modelform(self):
        # Ensure that automatically created forms use TagField
        class TestForm(forms.ModelForm):
            class Meta:
                model = FormTest
                
        form = TestForm()
        self.assertEquals(form.fields['tags'].__class__.__name__, 'TagField')
    
    def test_recreation_of_tag_list_string_representations(self):
        plain = Tag.objects.create(name='plain')
        spaces = Tag.objects.create(name='spa ces')
        comma = Tag.objects.create(name='com,ma')
        colon = Tag.objects.create(name='co:lon')
        equal = Tag.objects.create(name='equa=l')
        spaces_namespace = Tag.objects.create(name='foo', namespace='spa ces')
        spaces_value = Tag.objects.create(name='foo', value='spa ces')
        spaces_colon_namespace = Tag.objects.create(name='foo', namespace='spa ces,colon')
        self.assertEquals(edit_string_for_tags([plain]), u'plain')
        self.assertEquals(edit_string_for_tags([plain, spaces]), u'plain, spa ces')
        self.assertEquals(edit_string_for_tags([plain, spaces, comma]), u'plain, spa ces, "com,ma"')
        self.assertEquals(edit_string_for_tags([plain, comma]), u'plain "com,ma"')
        self.assertEquals(edit_string_for_tags([comma, spaces]), u'"com,ma", spa ces')
        self.assertEquals(edit_string_for_tags([plain, colon]), u'plain "co:lon"')
        self.assertEquals(edit_string_for_tags([equal, colon]), u'"equa=l" "co:lon"')
        self.assertEquals(edit_string_for_tags([equal, spaces, colon]), u'"equa=l", spa ces, "co:lon"')
        self.assertEquals(edit_string_for_tags([plain, spaces_namespace]), u'plain, spa ces:foo')
        self.assertEquals(edit_string_for_tags([plain, spaces_value]), u'plain, foo=spa ces')
        self.assertEquals(edit_string_for_tags([plain, spaces_colon_namespace]), u'plain "spa ces,colon":foo')
    
    def test_tag_d_validation(self):
        t = TagField()
        w50 = 'qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb'
        w51 = w50 + 'n'
        w10 = w50[:10]
        w11 = w50[:11]
        settings.MAX_TAG_LENGTH = 150
        settings.MAX_TAG_NAME_LENGTH = 50
        settings.MAX_TAG_NAMESPACE_LENGTH = 50
        settings.MAX_TAG_VALUE_LENGTH = 50
        self.assertEquals(t.clean('foo'), u'foo')
        self.assertEquals(t.clean('foo bar baz'), u'foo bar baz')
        self.assertEquals(t.clean('foo,bar,baz'), u'foo,bar,baz')
        self.assertEquals(t.clean('foo, bar, baz'), u'foo, bar, baz')
        self.assertEquals(t.clean('foo %s bar' % w50),
            u'foo %s bar' % w50)
        self.assertEquals(t.clean('foo %s:%s=%s bar' % (w50, w50, w50)),
            u'foo %s:%s=%s bar' % (w50, w50, w50))
        try:
            t.clean('foo %s bar' % w51)
        except forms.ValidationError, ve:
            self.assertEquals(unicode(list(ve.messages)), u'[u"Each tag\'s name may be no more than 50 characters long."]')
        except Exception, e:
            raise e
        else:
            raise self.failureException('a ValidationError exception was supposed to have been raised.')
        try:
            t.clean('foo %s:%s bar' % (w51, w50))
        except forms.ValidationError, ve:
            self.assertEquals(unicode(list(ve.messages)), u'[u"Each tag\'s namespace may be no more than 50 characters long."]')
        except Exception, e:
            raise e
        else:
            raise self.failureException('a ValidationError exception was supposed to have been raised.')
        try:
            t.clean('foo %s=%s bar' % (w50, w51))
        except forms.ValidationError, ve:
            self.assertEquals(unicode(list(ve.messages)), u'[u"Each tag\'s value may be no more than 50 characters long."]')
        except Exception, e:
            raise e
        else:
            raise self.failureException('a ValidationError exception was supposed to have been raised.')
        settings.MAX_TAG_LENGTH = 149
        try:
            t.clean('foo %s:%s=%s bar' % (w50, w50, w50))
        except forms.ValidationError, ve:
            self.assertEquals(unicode(list(ve.messages)), u"[u'Each tag may be no more than 149 characters long.']")
        except Exception, e:
            raise e
        else:
            raise self.failureException('a ValidationError exception was supposed to have been raised.')
