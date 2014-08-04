#!/usr/bin/env python3

import pprint
import struct
import sys

class FormatError(Exception):
    pass

def parse(filename):
    p = {}
    with open(filename, 'rb') as inp:
        header(p, inp)
        pprint.pprint(p)

def header(p, inp):
    magic(p, inp)
    numrecs(p, inp)
    dim_list(p, inp)
    gatt_list(p, inp)
    var_list(p, inp)

def magic(p, inp):
    magic = inp.read(4)
    if not magic.startswith(b'CDF'):
        raise FormatError("Wrong magic number")
    version = magic[3]
    if version not in (1,2):
        raise FormatError("VERSION byte {:#x} is not acceptable".format(magic[3]))
    p['version'] = version

def numrecs(p, inp):
    b = inp.read(4)
    (numrecs,) = struct.unpack('>i', b)
    if numrecs < -1:
        raise FormatError("numrecs field is {%d} which is invalid".format(numrecs))
    if numrecs == -1:
        p.numrecs = 'streaming'
        return
    assert numrecs >= 0
    p['numrecs'] = numrecs

def dim_list(p, inp):
    dimension = inp.read(4)
    if dimension == b'\x00\x00\x00\x00':
        # ABSENT case
        n = inp.read(4)
        if n != b'\x00\x00\x00\x00':
            raise FormatError("expected ABSENT for dim_list, but found {!r}".format(n))
        p['dim_list'] = 'absent'
        return
    if dimension != b'\x00\x00\x00\x0a':
        raise FormatError("expected NC_DIMENSON for dim_list, but found {!r}".format(dimension))

    n = nelems(inp)
    p['dim_list'] = [dim(inp) for i in range(n)]

def dim(inp):
    return (name(inp), dim_length(inp))

def gatt_list(p, inp):
    p['gatt_list'] = att_list(inp)

def att_list(inp):
    attribute = inp.read(4)
    if attribute == b'\x00\x00\x00\x00':
        # ABSENT case
        n = inp.read(4)
        if n != b'\x00\x00\x00\x00':
            raise FormatError("expected ABSENT for att_list, but found {!r}".format(n))
        p['gatt_list'] = 'absent'
        return
    if attribute != b'\x00\x00\x00\x0c':
        raise FormatError("expected NC_ATTRIBUTE for att_list, but found {!r}".format(attribute))
    n = nelems(inp)
    return [attr(inp) for i in range(n)]

def attr(inp):
    attr_name = name(inp)
    type = nc_type(inp)
    n = nelems(inp)
    vs = values(inp, type, n)
    return (attr_name, vs)

def var_list(p,inp):
    b = inp.read(4)
    if b == b'\x00\x00\x00\x00':
        # ABSENT case
        n = inp.read(4)
        if n != b'\x00\x00\x00\x00':
            raise FormatError("expected ABSENT for var_list, but found {!r}".format(n))
        p['var_list'] = 'absent'
        return
    if b != b'\x00\x00\x00\x0b':
        raise FormatError("expected NC_VARIABLE for var_list, but found {!r}".format(attribute))
    n = nelems(inp)
    print("{} vars at {}".format(n, inp.tell()))
    p['var_list'] = [var(inp) for i in range(n)]

def var(inp):
    var_name = name(inp)
    n = nelems(inp)
    dimensions = [non_neg(inp) for i in range(n)]
    var_attr = att_list(inp)
    type = nc_type(inp)
    vsize = non_neg(inp)
    # For classic format; would be 64-bit for 64-bit offset format.
    begin = non_neg(inp)
    return (var_name, var_attr, vsize, begin)

def nelems(inp):
    return non_neg(inp)

def non_neg(inp):
    b = inp.read(4)
    (n,) = struct.unpack('>i', b)
    if n < 0:
        raise FormatError("expected NON NEG, but found {!r}".format(n))
    return n


def nc_type(inp):
    b = inp.read(4)
    (x,) = struct.unpack('>i', b)
    if x not in (1, 2, 3, 4, 5, 6):
        raise FormatError("invalid nc_type code {!r}".format(x))
    if x == 1:
        return 'byte'
    if x == 2:
        return 'char'
    if x == 3:
        return 'short'
    if x == 4:
        return 'int'
    if x == 5:
        return 'float'
    if x == 6:
        return 'double'

def values(inp, type, nelems):
    if type == 'byte':
        l = 1
        f = 'b'
    if type == 'char':
        l = 1
        f = 's'
    if type == 'short':
        l = 2
        f = 'h'
    if type == 'int':
        l = 4
        f = 'i'
    if type == 'float':
        l = 4
        f = 'f'
    if type == 'double':
        l = 8
        f = 'd'

    length = nelems * l
    padded_length  = 4 * ((length + 3) // 4)
    n = padded_length // l
    b = inp.read(padded_length)
    vs = struct.unpack('>{}{}'.format(n, f), b)
    if type == 'char':
        (vs,) = vs
    return vs[:nelems]

def name(inp):
    b = inp.read(4)
    (nelems,) = struct.unpack('>i', b)
    if nelems < 0:
        raise FormatError("expected name nelems, but found {!r}".format(nelems))
    padded = 4 * ((nelems + 3) // 4)
    padded_name = inp.read(padded)
    name = str(padded_name[:nelems], 'utf-8')
    padding = padded_name[nelems:]
    if padding != b'\x00' * len(padding):
        raise FormatError("wrong padding in name")
    return name

def dim_length(inp):
    b = inp.read(4)
    (dim_length,) = struct.unpack('>i', b)
    if dim_length < 0:
        raise FormatError("invalid dim_length {!r}".format(dim_length))
    return dim_length

def main(argv=None):
    if argv is None:
        argv = sys.argv

    arg = argv[1:]
    parse(arg[0])

if __name__ == '__main__':
    main()
