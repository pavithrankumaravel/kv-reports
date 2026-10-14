from django import template
register = template.Library()

@register.filter
def get_items(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return ''

@register.filter
def dict_get(d, key):
    """Get a dictionary item by key safely."""
    if d is None:
        return ""
    return d.get(key, "")

@register.filter
def dict_get_indi1(d, key):
    """Safely get value from dict in template"""
    try:
        return d.get(int(key)) if d else None
    except (ValueError, AttributeError):
        return None
    
@register.filter
def dict_get_indi2(d, key):
    return d.get(key, 0)

@register.filter
def get_item_indi(dictionary, key):
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)