import sys
from lxml import etree

def main():
    tree = etree.parse(sys.stdin)
    root = tree.getroot()

    print(etree.tostring(root, pretty_print=True).decode('utf-8'))

if __name__ == "__main__":
    main()

