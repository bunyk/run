from lxml import etree

def pprint(filepath):
    tree = etree.parse(filepath)
    root = tree.getroot()

    print(etree.tostring(root, pretty_print=True).decode('utf-8'))



