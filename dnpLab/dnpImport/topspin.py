import numpy as _np
import re as _re

from .. import dnpdata as _dnpdata

import os as _os

_dspfvs_table_10 = {
        2   : 44.7500,
        3   : 33.5000,
        4   : 66.6250,
        6   : 59.0833,
        8   : 68.5625,
        12  : 60.3750,
        16  : 69.5313,
        24  : 61.0208,
        32  : 70.0156,
        48  : 61.3438,
        64  : 70.2578,
        96  : 61.5052,
        128 : 70.3789,
        192 : 61.5859,
        256 : 70.4395,
        384 : 61.6263,
        512 : 70.4697,
        1024: 70.4849,
        1536: 61.6566,
        2048: 70.4924,
        }

_dspfvs_table_11 = {
        2   : 46.0000,
        3   : 36.5000,
        4   : 48.0000,
        6   : 50.1667,
        8   : 53.2500,
        12  : 69.5000,
        16  : 72.2500,
        24  : 70.1667,
        32  : 72.7500,
        48  : 70.5000,
        64  : 73.0000,
        96  : 70.6667,
        128 : 72.5000,
        192 : 71.3333,
        256 : 72.2500,
        384 : 71.6667,
        512 : 72.1250,
        1024: 72.0625,
        1536: 71.9167,
        2048: 72.0313,
        }

_dspfvs_table_12 = {
        2   : 46.311,
        3   : 36.530,
        4   : 47.870,
        6   : 50.229,
        8   : 53.289,
        12  : 69.551,
        16  : 71.600,
        24  : 70.184,
        32  : 72.138,
        48  : 70.528,
        64  : 72.348,
        96  : 70.700,
        128 : 72.524,
        192 : 71.3333,
        256 : 72.2500,
        384 : 71.6667,
        512 : 72.1250,
        1024: 72.0625,
        1536: 71.9167,
        2048: 72.0313,
        }

_dspfvs_table_13 = {
        2   : 2.750,
        3   : 2.833,
        4   : 2.875,
        6   : 2.917,
        8   : 2.938,
        12  : 2.958,
        16  : 2.969,
        24  : 2.979,
        32  : 2.984,
        48  : 2.989,
        64  : 2.992,
        96  : 2.995,
        }

def find_group_delay(decim,dspfvs):
    '''
    '''
    group_delay = 0
    if decim == 1:
        group_delay = 0
    else:
        if dspfvs == 10:
            group_delay = _dspfvs_table_10[int(decim)]
        elif dspfvs == 11:
            group_delay = _dspfvs_table_11[int(decim)]
        elif dspfvs == 12:
            group_delay = _dspfvs_table_12[int(decim)]
        elif dspfvs == 13:
            group_delay = _dspfvs_table_13[int(decim)]
        else:
            print('dspfvs not defined')

    return group_delay

def load_title(path, expNum = 1, titlePath = 'pdata/1',titleFilename = 'title'):
    '''
    Import Topspin Experiment Title File
    '''

    pathFilename = _os.path.join(path,str(expNum),titlePath,titleFilename) 

    with open(pathFilename,'r') as f:
        rawTitle = f.read()
    title = rawTitle.rstrip()

    return title

def load_acqu(path, expNum = 1, paramFilename = 'acqus'):
    '''
    JCAMPDX file
    return dictionary of parameters
    '''

    pathFilename = path + str(expNum) + '/' + paramFilename

    # Import parameters
    with open(pathFilename,'r') as f:
        rawParams = f.read()

    # Split parameters by line
    lines = rawParams.strip('\n').split('\n')
    attrsDict = {}

    # Parse Parameters
    for line in lines:
        if line[0:3] == '##$':
            lineSplit = line[3:].split('= ')
            try:
                attrsDict[lineSplit[0]] = float(lineSplit[1])
            except:
                attrsDict[lineSplit[0]] = lineSplit[1]

    return attrsDict

def load_proc(path, expNum = 1, procNum = 1, paramFilename = 'procs'):
    '''
    '''

    pathFilename = path + str(expNum)  + '/pdata/' + str(procNum) + '/' + paramFilename

    # Import parameters
    with open(pathFilename,'r') as f:
        rawParams = f.read()

    # Split parameters by line
    lines = rawParams.strip('\n').split('\n')
    attrsDict = {}

    # Parse Parameters
    for line in lines:
        if line[0:3] == '##$':
            lineSplit = line[3:].split('= ')
            try:
                attrsDict[lineSplit[0]] = float(lineSplit[1])
            except:
                attrsDict[lineSplit[0]] = lineSplit[1]

    return attrsDict



def dir_data_type(path,expNum):
    '''
    '''
    fullPath = path + '/' + str(expNum)

    dirList = _os.listdir(fullPath)

    if 'fid' in dirList:
        return 'fid'
    elif 'ser' in dirList: 
        if 'vdlist' in dirList:
            return 'ser'
        else:
            return 'serPhaseCycle'
    else:
        return ''

def import_topspin(path,expNum,paramFilename = 'acqus'):
    '''
    '''
    dirType = dir_data_type(path,expNum)

    if expNum is not None:
        fullPath = path + '/' + str(expNum)
    else:
        fullPath = path

    if dirType == 'fid':
        data = topspin_fid(path,expNum,paramFilename)
        return data
    elif dirType == 'ser':
        data = import_ser(path,expNum,paramFilename)
        return data
    elif dirType == 'serPhaseCycle':
        data = topspin_ser_phase_cycle(path,expNum,paramFilename)
        return data
    else:
        raise ValueError
        Print('Could Not Identify Data Type in File')


def topspin_fid(path,expNum,paramFilename = 'acqus'):
    '''
    '''
    attrsDict = load_acqu(path, expNum, paramFilename)

    sw_h = attrsDict['SW_h'] # Spectral Width in Hz

    rg = attrsDict['RG'] # reciever gain
    decim = attrsDict['DECIM'] # Decimation factor of the digital filter
    dspfvs = attrsDict['DSPFVS'] # Digital signal processor firmware version
    bytorda = attrsDict['BYTORDA'] # 1 for big endian, 0 for little endian
    td = int(attrsDict['TD'])# points in time axes


    if bytorda == 0:
        endian = '<'
    else:
        endian = '>'

    raw = _np.fromfile(path + str(expNum) + '/fid',dtype = endian + 'i4')
    data = raw[0::2] + 1j * raw[1::2] # convert to complex

    group_delay = find_group_delay(decim,dspfvs)
    group_delay = int(_np.ceil(group_delay))

    t = 1./sw_h * _np.arange(0,int(td/2)-group_delay)

    data = data[group_delay:int(td/2)]

    data = data / rg

    importantParamsDict = {}
    importantParamsDict['nmr_frequency'] = attrsDict['SFO1'] * 1e6
    output = _dnpdata(data,[t],['t2'],importantParamsDict)

    return output

def topspin_jcamp_dx(path):
    '''Return the contents of

    Args:
        path: Path to file

    Returns:
        dict: Dictionary of JCAMP-DX file
    '''

    attrs = {}

    with open(path, 'r') as f:
        for line in f:
            line = line.rstrip()

            if line[0:3] == '##$':
                key, value = tuple(line[3:].split('= ', 1))

                # Test for array
                if value[0] == '(':
                    x = _re.findall('\([0-9]+\.\.[0-9]+\)', value)

                    start, end = tuple(x[0][1:-1].split('..',1))

                    array_size = int(end) + 1

                    same_line_array = value.split(')', 1)[-1]

                    array = []
                    if same_line_array != '':
                        same_line_array = same_line_array.split(' ')
                        same_line_array = [float(x) if '.' in x else int(x) for x in same_line_array]

                        array += same_line_array

                    while len(array) < array_size:
                        array_line = f.readline().rstrip().split(' ')

                        array_line = [float(x) if '.' in x else int(x) for x in array_line]

                        array += array_line

                    
                    array = _np.array(array)

                    attrs[key] = array

                elif value[0] == '<':
                    value = value[1:-1]
                    if '.' in value:
                        try:
                            value = float(value)
                        except:
                            pass
                    else:
                        try:
                            value = int(value)
                        except:
                            pass

                    attrs[key] = value
                else:
                    if '.' in value:
                        try:
                            value = float(value)
                        except:
                            pass
                    else:
                        try:
                            value = int(value)
                        except:
                            pass

                    attrs[key] = value



            elif line[0:2] == '##':
                try:
                    key, value = tuple(line[2:].split('= ', 1))
                except:
                    pass

    return attrs


def topspin_vdlist(path, expNum):
    '''
    '''
    fullPath = path + str(expNum) + '/vdlist'

    with open(fullPath,'r') as f:
        raw = f.read()

#    lines = raw.strip('\n').split('\n')
    lines = raw.rstrip().rsplit()

    unitDict = {
            'n' : 1.e-9,
            'u' : 1.e-6,
            'm' : 1.e-3,
            'k' : 1.e3,
            }
    vdList = []
    for line in lines:
        if line[-1] in unitDict:
            value = float(line[0:-1]) * unitDict[line[-1]]
            vdList.append(value)
        else:
            value = float(line)
            vdList.append(value)


    vdList = _np.array(vdList)
    return vdList

def import_ser(path,expNum,paramFilename = 'acqus'):
    '''
    '''
    attrsDict = load_acqu(path, expNum, paramFilename)

    sw_h = attrsDict['SW_h'] # Spectral Width in Hz

    rg = attrsDict['RG'] # reciever gain
    decim = attrsDict['DECIM'] # Decimation factor of the digital filter
    dspfvs = attrsDict['DSPFVS'] # Digital signal processor firmware version
    bytorda = attrsDict['BYTORDA'] # 1 for big endian, 0 for little endian
    td = int(attrsDict['TD'])# points in time axes

    if bytorda == 0:
        endian = '<'
    else:
        endian = '>'

    raw = _np.fromfile(path + str(expNum) + '/ser',dtype = endian + 'i4')
    data = raw[0::2] + 1j * raw[1::2] # convert to complex

    group_delay = find_group_delay(decim,dspfvs)
    group_delay = int(_np.ceil(group_delay))

    t = 1./sw_h * _np.arange(0,int(td/2)-group_delay)

    vdList = topspin_vdlist(path,expNum)

    data = data.reshape(len(vdList),-1).T

    data = data[group_delay:int(td/2),:]

    data = data / rg

    importantParamsDict = {}
    importantParamsDict['nmr_frequency'] = attrsDict['SFO1'] * 1e6
    output = _dnpdata(data,[t,vdList],['t2','t1'],importantParamsDict)

    return output

def topspin_ser_phase_cycle(path,expNum,paramFilename = 'acqus'):
    '''
    '''
    attrsDict = load_acqu(path, expNum, paramFilename)

    sw_h = attrsDict['SW_h'] # Spectral Width in Hz

    rg = attrsDict['RG'] # reciever gain
    decim = attrsDict['DECIM'] # Decimation factor of the digital filter
    dspfvs = attrsDict['DSPFVS'] # Digital signal processor firmware version
    bytorda = attrsDict['BYTORDA'] # 1 for big endian, 0 for little endian
    td = int(attrsDict['TD'])# points in time axes

    if bytorda == 0:
        endian = '<'
    else:
        endian = '>'

    raw = _np.fromfile(path + str(expNum) + '/ser',dtype = endian + 'i4')
    data = raw[0::2] + 1j * raw[1::2] # convert to complex

    group_delay = find_group_delay(decim,dspfvs)
    group_delay = int(_np.ceil(group_delay))

    t = 1./sw_h * _np.arange(0,int(td/2)-group_delay)


    length1d = int((_np.ceil(td/256.)*256)/2)
#    print length1d
    data = data.reshape(-1,int(length1d)).T

    data = data[group_delay:int(td/2),:]

    # Assume phase cycle is 0, 90, 180, 270
    data = data[:,0] + 1j*data[:,1] - data[:,2] - 1j*data[:,3]
    data = data / rg

    importantParamsDict = {}
    importantParamsDict['nmr_frequency'] = attrsDict['SFO1'] * 1e6

    output = _dnpdata(data,[t],['t2'],importantParamsDict)
    return output


def import_topspin_dir(path):
    '''
    '''

    dirFiles = [x for x in _os.listdir(path) if _os.path.isdir(_os.path.join(path,x))]

    dataDict = {}
    for expNum in dirFiles:
        try:
            tempData = import_topspin(path,expNum)
            dataDict[expNum] = tempData
        except:
            pass
#            print('%s is not a valid data directory'%(expNum))
    return dataDict




if __name__ == "__main__":
    pass
