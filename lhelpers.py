'''
Convinience functions and classes.
'''

import configparser
import ast


class DotMap(dict):
    """
    Own implementation to convert a python dict into dot notation.
    mydict['city'] --> mydict.city
    There is a package for this but I wanted less dependencies:
    https://github.com/drgrib/dotmap

    Example:
    m = DotMap({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super(DotMap, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v


        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(DotMap, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(DotMap, self).__delitem__(key)
        del self.__dict__[key]


def get_dict_from_click_args(argsList):
    '''
    '''
    argsDict = {}
    for item in argsList:
        if item.startswith("--"):
            lastKey = item.replace("--","")
            argsDict[lastKey] = None
        else:
            # In case one key has two values
            if not argsDict[lastKey]:
                argsDict[lastKey] = [argsDict[lastKey]].append(item)
            argsDict[lastKey] = item
    return argsDict


def get_config_in_dot_notation(templateFilename="default_config.template", configFilename="default_config.txt"):
    '''
    '''
    config = configparser.ConfigParser(allow_no_value=True, strict=False)
    # In order to prevent key to get converted to lower case
    config.optionxform = lambda option: option
    config.read([templateFilename, configFilename])
    dot = DotMap(config._sections)
    #print(dot.__dict__)
    for section in config._sections:
        setattr(dot, section, DotMap(config[section]))
        for key, value in config[section].items():
            try:
                setattr(getattr(dot, section), key, eval(value))
            except:
                # if "input.ms" is eval to Object (because of . ), treat as string
                setattr(getattr(dot, section), key, str(value))
    return dot

