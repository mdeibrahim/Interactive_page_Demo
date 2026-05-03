import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()
HTML_TAG_RE = re.compile(r'</?[a-zA-Z][^>]*>')


@register.filter
def render_stored_content(value):
    if value is None:
        return ''

    text = str(value)
    if not text:
        return ''

    if HTML_TAG_RE.search(text):
        return mark_safe(text)

    return mark_safe(escape(text).replace('\n', '<br>'))