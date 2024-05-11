_rules = []
if True:
    _rules.append('{{"field":"title", "operator":"contains", "value":"{query}"}}')
if True:
    _rules.append('{{"field":"originaltitle", "operator":"contains", "value":"{query}"}}')
if True:
    _rules.append('{{"field":"tag", "operator":"contains", "value":"{query}"}}')

search = "abc"

cat = {
    'rule':'"filter":{{{{"or":[{}]}}}}'.format(', '.join(_rules)),
}
print(cat['rule'])
print(cat['rule'].format(query = search))

