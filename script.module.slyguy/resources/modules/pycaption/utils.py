def is_leaf(element):
    """
    Return True if the element is a leaf, False otherwise. The element is
    considered a leaf if it is either NavigableString or the "br" tag
    :param element: A BeautifulSoup tag or NavigableString
    """
    name = getattr(element, 'name', None)
    if not name or name == 'br':
        return True
    return False
