"""
Tagging utilities - from user tag input parsing to tag cloud
calculation.
"""
import re
import math
import types

from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

RE_TAG_PART_TOKEN = re.compile(r"^(%s)(.*)$" % r'[:=]|"[^"]*"|[^,\s:="]+')
RE_SPACE_TOKEN = re.compile(r"^(%s)(.*)$" % r"\s+")
RE_COMMA_TOKEN = re.compile(r"^(%s)(.*)$" % r"\s*,\s*")
RE_CHAR_TOKEN = re.compile(r"^(%s)(.*)$" % r"[:=]|[^,\s:=]+")

RE_STRING_TOKEN = re.compile(r'^(%s)(.*)$' % r'"[^"]*"')

def parse_tag_input(input):
    """
    Parses tag input, with multiple word input being activated and
    delineated by commas and double quotes. Quotes take precedence, so
    they may contain commas.

    Returns a sorted list of unique tag names.
    """
    if not input:
        return []

    input = force_unicode(input)

    # Special case - if there are no commas, colons or double quotes in the
    # input, we don't *do* a recall... I mean, we know we only need to
    # split on spaces.
    if u',' not in input and u'"' not in input and \
        ':' not in input and '=' not in input:
        words = list(set(split_strip(input, u' ')))
        words.sort()
        return words

    token_list = []
    token_definition = (
        (RE_TAG_PART_TOKEN, 'part'),
        (RE_SPACE_TOKEN, 'space'),
        (RE_COMMA_TOKEN, 'comma'),
        (RE_CHAR_TOKEN, 'char'),
    )
    saw_loose_comma = False
    while input:
        for token, name in token_definition:
            m = token.match(input)
            if m:
                content, input = m.groups()
                token_list.append((name, content))
                if name == 'comma':
                    saw_loose_comma = True
                break

    if saw_loose_comma:
        delimiter = 'comma'
    else:
        delimiter = 'space'
    words = set()
    word = []
    for token, content in token_list:
        if token == delimiter:
            word = build_tag(word)
            if word:
                words.add(word)
            word = []
        else:
            word.append(content)
    word = build_tag(word)
    if word:
        words.add(word)
    words = list(words)
    words.sort()
    return words

def build_tag(tokens):
    """
    Gets a list of strings and chars and builds a tag with correctly quoted
    namespace, name and values. If there is no namespace or value the part will
    be ignored.
    """
    left, lms, middle, mrs, right = [], None, [], None, []
    if ':' not in tokens and '=' not in tokens:
        return normalize_tag_part(''.join(tokens))
    for token in tokens:
        if lms is None:
            if token == ':':
                lms = ':'
            elif token == '=':
                if left:
                    lms = '='
            else:
                left.append(token)
        elif lms == ':':
            if mrs is None:
                if token == '=':
                    if middle:
                        mrs = '='
                else:
                    middle.append(token)
            else:
                right.append(token)
        elif lms == '=':
            middle.append(token)
    if lms == '=':
        namespace, name, value = [], left, middle
    else:
        if middle:
            namespace, name, value = left, middle, right
        else:
            namespace, name, value = [], left, []
    namespace = normalize_tag_part(''.join(namespace))
    name = normalize_tag_part(''.join(name))
    value = normalize_tag_part(''.join(value))
    if namespace:
        name = "%s:%s" % (namespace, name)
    if value:
        name = "%s=%s" % (name, value)
    return name

def normalize_tag_part(input, stop_chars=':='):
    """
    Takes a namespace, name or value and removes trailing colons and equals.
    Adds quotes around each part that contains a colon or equals sign.
    """
    input = input.replace('"', '')
    if not input:
        return ''
    for char in stop_chars:
        if char in input:
            return '"%s"' % input
    return input

def split_strip(input, delimiter=u','):
    """
    Splits ``input`` on ``delimiter``, stripping each resulting string
    and returning a list of non-empty strings.
    """
    if not input:
        return []

    words = [w.strip() for w in input.split(delimiter)]
    return [w for w in words if w]

def edit_string_for_tags(tags):
    """
    Given list of ``Tag`` instances, creates a string representation of
    the list suitable for editing by the user, such that submitting the
    given string representation back without changing it will give the
    same list of tags.

    Parts of tags which contain commas will be double quoted.

    If any tag name which isn't being quoted contains whitespace, the
    resulting string of tag names will be comma-delimited, otherwise
    it will be space-delimited.
    """
    quote_chars = ',:='
    fields = {'namespace': '', 'name': '', 'value': ''}
    names = []
    use_commas = False
    for tag in tags:
        for field in fields:
            fields[field] = getattr(tag, field) or ''
            quoted = False
            for char in quote_chars:
                if char in fields[field]:
                    fields[field] = '"%s"' % fields[field]
                    quoted = True
                    break
            if not quoted and ' ' in fields[field]:
                use_commas = True
        name = fields['name']
        if fields['namespace']:
            name = '%s:%s' % (fields['namespace'], name)
        if fields['value']:
            name = '%s=%s' % (name, fields['value'])
        names.append(name)
    if use_commas:
        glue = u', '
    else:
        glue = u' '
    return glue.join(names)

def get_queryset_and_model(queryset_or_model):
    """
    Given a ``QuerySet`` or a ``Model``, returns a two-tuple of
    (queryset, model).

    If a ``Model`` is given, the ``QuerySet`` returned will be created
    using its default manager.
    """
    try:
        return queryset_or_model, queryset_or_model.model
    except AttributeError:
        return queryset_or_model._default_manager.all(), queryset_or_model

def get_tag_list(tags):
    """
    Utility function for accepting tag input in a flexible manner.

    If a ``Tag`` object is given, it will be returned in a list as
    its single occupant.

    If given, the tag names in the following will be used to create a
    ``Tag`` ``QuerySet``:

       * A string, which may contain multiple tag names.
       * A list or tuple of strings corresponding to tag names.
       * A list or tuple of integers corresponding to tag ids.

    If given, the following will be returned as-is:

       * A list or tuple of ``Tag`` objects.
       * A ``Tag`` ``QuerySet``.

    """
    from tagging.models import Tag
    if isinstance(tags, Tag):
        return [tags]
    elif isinstance(tags, QuerySet) and tags.model is Tag:
        return tags
    elif isinstance(tags, types.StringTypes):
        q = get_tag_filter_lookup(tags)
        if q is None:
            return []
        return Tag.objects.filter(q)
    elif isinstance(tags, (types.ListType, types.TupleType)):
        if len(tags) == 0:
            return tags
        contents = set()
        for item in tags:
            if isinstance(item, types.StringTypes):
                contents.add('string')
            elif isinstance(item, Tag):
                contents.add('tag')
            elif isinstance(item, (types.IntType, types.LongType)):
                contents.add('int')
        if len(contents) == 1:
            if 'string' in contents:
                q = get_tag_filter_lookup([force_unicode(tag) for tag in tags])
                if q is None:
                    return []
                return Tag.objects.filter(q)
            elif 'tag' in contents:
                return tags
            elif 'int' in contents:
                return Tag.objects.filter(id__in=tags)
        else:
            raise ValueError(_('If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.'))
    else:
        raise ValueError(_('The tag input given was invalid.'))

def get_tag_filter_lookup(tags):
    """
    Takes a user entered string or an iteratable of strings and returns a
    a ``Q`` object that matches all given tags.

    Returns ``None`` if no valid tag name is found in the strings.
    """
    if isinstance(tags, types.StringTypes):
        tags = parse_tag_input(tags)
    else:
        tag_parsed = set()
        for tag in tags:
            tag_parsed.update(parse_tag_input(tag))
        tags = tag_parsed
    tags = [get_tag_parts(tag) for tag in tags]
    tag_names, tag_parts = [], []
    for tag in tags:
        if not tag['namespace'] and not tag['value']:
            tag_names.append(tag['name'])
        else:
            tag_parts.append(tag)
    q = None
    if len(tag_names):
        q = Q(name__in=tag_names, namespace=None, value=None)
    for tag in tag_parts:
        if q is None:
            q = Q(**tag)
        else:
            q = q | Q(**tag)
    return q

def get_tag(tag):
    """
    Utility function for accepting single tag input in a flexible
    manner.

    If a ``Tag`` object is given it will be returned as-is; if a
    string or integer are given, they will be used to lookup the
    appropriate ``Tag``.

    If no matching tag can be found, ``None`` will be returned.
    """
    from tagging.models import Tag
    if isinstance(tag, Tag):
        return tag

    try:
        if isinstance(tag, types.StringTypes):
            return Tag.objects.get(**get_tag_parts(tag))
        elif isinstance(tag, (types.IntType, types.LongType)):
            return Tag.objects.get(id=tag)
    except Tag.DoesNotExist:
        pass

    return None

RE_TAG_PARTS = re.compile(
    r'(?:(?P<namespace>"[^"]+"|[^:="]+):)?'
    r'(?P<name>"[^"]+"|[^="]+)'
    r'(?:=(?P<value>"[^"]+"|[^"]+))?'
)

def get_tag_parts(tag):
    """
    Utility function for accepting single tag string representation that are
    returned from the ``parse_tag_input`` function.

    It returns a dictionary with the keys ``namespace``, ``name`` and
    ``value``. The values have no quotes.
    """
    parts = RE_TAG_PARTS.match(tag).groupdict()
    for key, value in parts.items():
        if value and value[0] == value[-1] == '"':
            parts[key] = value[1:-1]
    return parts

# Font size distribution algorithms
LOGARITHMIC, LINEAR = 1, 2

def _calculate_thresholds(min_weight, max_weight, steps):
    delta = (max_weight - min_weight) / float(steps)
    return [min_weight + i * delta for i in range(1, steps + 1)]

def _calculate_tag_weight(weight, max_weight, distribution):
    """
    Logarithmic tag weight calculation is based on code from the
    `Tag Cloud`_ plugin for Mephisto, by Sven Fuchs.

    .. _`Tag Cloud`: http://www.artweb-design.de/projects/mephisto-plugin-tag-cloud
    """
    if distribution == LINEAR or max_weight == 1:
        return weight
    elif distribution == LOGARITHMIC:
        return math.log(weight) * max_weight / math.log(max_weight)
    raise ValueError(_('Invalid distribution algorithm specified: %s.') % distribution)

def calculate_cloud(tags, steps=4, distribution=LOGARITHMIC):
    """
    Add a ``font_size`` attribute to each tag according to the
    frequency of its use, as indicated by its ``count``
    attribute.

    ``steps`` defines the range of font sizes - ``font_size`` will
    be an integer between 1 and ``steps`` (inclusive).

    ``distribution`` defines the type of font size distribution
    algorithm which will be used - logarithmic or linear. It must be
    one of ``tagging.utils.LOGARITHMIC`` or ``tagging.utils.LINEAR``.
    """
    if len(tags) > 0:
        counts = [tag.count for tag in tags]
        min_weight = float(min(counts))
        max_weight = float(max(counts))
        thresholds = _calculate_thresholds(min_weight, max_weight, steps)
        for tag in tags:
            font_set = False
            tag_weight = _calculate_tag_weight(tag.count, max_weight, distribution)
            for i in range(steps):
                if not font_set and tag_weight <= thresholds[i]:
                    tag.font_size = i + 1
                    font_set = True
    return tags

def check_tag_length(tag_parts):
    """
    Checks the length of the tag parts according to the settings. The lengths
    are checked for each single part and the sum of the lengths of all parts.
    The delimiters for namespace and value (':' and '=') are not counted. They
    are not part of the tag.
    """
    from tagging import settings
    namespace_len = len(tag_parts['namespace'] or '')
    name_len = len(tag_parts['name'] or '')
    value_len = len(tag_parts['value'] or '')
    tag_len = name_len + namespace_len + value_len
    if tag_len > settings.MAX_TAG_LENGTH:
        raise ValueError("Tag is too long.", 'tag', settings.MAX_TAG_LENGTH)
    if name_len > settings.MAX_TAG_NAME_LENGTH:
        raise ValueError("Tag's name part is too long.", 'name', settings.MAX_TAG_NAME_LENGTH)
    if namespace_len > settings.MAX_TAG_NAMESPACE_LENGTH:
        raise ValueError("Tag's namespace part is too long.", 'namespace', settings.MAX_TAG_NAMESPACE_LENGTH)
    if value_len > settings.MAX_TAG_VALUE_LENGTH:
        raise ValueError("Tag's value part is too long.", 'value', settings.MAX_TAG_VALUE_LENGTH)
