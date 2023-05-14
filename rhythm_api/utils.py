def merge(a: dict, b: dict) -> dict:
    """
    "merges b into a"

    a = {
        1: {"a":"A"},
        2: {"b":"B"},
        3: [1,2,3],
        4: {'a': {'b': 2}}
    }

    b = {
        2: {"c":"C"},
        3: {"d":"D"},
        4: {'c': {'b': 3}, 'a': [1,2,{'b':2}]}
    }

    merge(a,b)
    {
        1: {'a': 'A'},
        2: {'b': 'B', 'c': 'C'},
        3: {'d': 'D'},
        4: {'a': [1, 2, {'b': 2}], 'c': {'b': 3}}
    }
    """

    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a
