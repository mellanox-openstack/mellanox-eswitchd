#!/usr/bin/python

import sys
from eswitchd.cli import conn_utils
from eswitchd.cli import exceptions
#from eswitchd.common import constants

action = sys.argv[1]
client = conn_utils.ConnUtil()

def pprint_table(out,table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """
    
    def get_max_width(table, index):
        """Get the maximum width of the given column index"""
        return max([len(str(row[index])) for row in table])

    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print >> out, row[0].ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = str(row[i]).rjust(col_paddings[i] + 2)
            print >> out, col,
        print >> out
   
    
def main():
    if action == 'get-tables':
        fabric = sys.argv[2]
        try:
            result = client.get_tables(fabric)
            for fabric, tables in result.items():
                print "FABRIC = %s" % fabric
                print"========================"
                for table, data in tables.items():
                    print "TABLE: %s" % table
                    pprint_table(sys.stdout, data)
                    print"========================"
        except exceptions.MlxException as e:
            sys.stderr.write("Error in get-tables command")
            sys.stderr.write(e.message)
            sys.exit(1)
        # sys.stdout.write(str(result))
        sys.exit(0)
        
if __name__ == '__main__':
    main()