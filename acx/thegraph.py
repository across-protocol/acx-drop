import json
import time

import requests

from acx.utils import createSessionWithRetries


THEGRAPHURL = "https://api.thegraph.com/"


def add_line(text, level=0):
    return "  "*level + text + "\n"


def _unpack_variable(variable, indent_level=1):
    "Unpacks a single variable or a dict variable"
    # If a string, simply return the string
    if isinstance(variable, str):
        return add_line(variable, level=indent_level)

    # If the variable isn't a string then it must be a dict with a
    # single element
    assert isinstance(variable, dict)
    assert len(variable.keys()) == 1

    out = ""
    for variable, subvariables in variable.items():
        # Make sure they gave you a list for the subvariables
        assert isinstance(subvariables, list)

        out += add_line(f"{variable} {{", level=indent_level)
        out += _unpack_variables(subvariables, indent_level+1)
    out += add_line("}", level=indent_level)

    return out


def _unpack_variables(variables, indent_level=0):
    "Takes a list of variables and unpacks them into a string"
    # Start an empty string to fill
    var_str = add_line("{", level=indent_level)
    for v in variables:
        var_str += _unpack_variable(v, indent_level=indent_level+1)
    var_str += add_line("}", level=indent_level)

    return  var_str


def _unpack_arguments(first=None, orderBy=None, orderDirection=None, where=None):
    "Unpacks query arguments"
    # Check whether each arg is None
    fin = first is None
    obin = orderBy is None
    odin = orderDirection is None
    win = where is None

    # If each argument is None, return nothing
    if fin and obin and odin and win:
        return ""

    out = add_line("(", level=0)
    if not fin:
        out += add_line(f"first: {first}", level=1)
    if not (obin or odin):
        out += add_line(f"orderBy: {orderBy}", level=1)
        out += add_line(f"orderDirection: {orderDirection}", level=1)
    if not win:
        if isinstance(where, str):
            out += add_line(f"where: {where}", level=1)
        elif isinstance(where, list):
            out += add_line("where: {", level=1)
            for w in where:
                out += add_line(f"{w}", level=2)
            out += add_line("}", level=1)
        elif isinstance(where, dict):
            out += add_line("where: {", level=1)
            for k, v in where.items():
                out += add_line(f"{k}: {v}", level=2)
            out += add_line("}", level=1)

    out += add_line(")", level=0)

    return out


def build_query(table, variables, arguments={"first": 5}):
    """
    Helper to construct a graph query from strings and lists of strings

    Parameters
    ----------
    table : string
        Which table to collect data from
    variables : list(dict or string)
        The variables to collect from the table. If these are nested
        variables then you should input a dict with the variable and
        subvariable
    arguments : dict, optional
        The arguments to the query for things like filtering and
        ordering.
    """
    query = "{"

    # First, add table name and open curly brackets
    query += add_line(table, level=0)

    # Next, add arguments
    query += _unpack_arguments(**arguments)

    # Finally, add variables and end line
    query += _unpack_variables(variables, indent_level=0)
    query += "}"

    return query


def submit_single_query(table, variables, arguments, organization, subgraph):
    """
    Submits a single query to `organization/subgraph` for `variables`
    from `table` with `arguments`.

    Parameters
    ----------
    table : string
        Which table to collect data from
    variables : list(dict or string)
        The variables to collect from the table. If these are nested
        variables then you should input a dict with the variable and
        subvariable
    arguments : dict, optional
        The arguments to the query for things like filtering and
        ordering.
    organization : str
        The organization the subgraph belongs to
    subgraph : str
        The subgraph the table belongs to
    """
    # Requests session with retries
    session = createSessionWithRetries(nRetries=5, backoffFactor=1.0)

    # Build query
    query = build_query(table, variables, arguments)

    # Set the query url using org/subgraph info
    queryable_url = (
        THEGRAPHURL +
        "subgraphs/name/{organization}/{subgraph}"
    ).format(organization=organization, subgraph=subgraph)

    # Build the query
    query_json = {
        "query": query,
    }

    # Make the request
    res = session.post(queryable_url, json=query_json)

    if "errors" in res.json().keys():
        print(f"""Error\n{queryable_url}\n{query_json["query"]}\n{res}""")
        raise ValueError("Failed to get data")

    return res


def submit_query_iterate(
        table, variables, arguments, organization, subgraph,
        npages=1, verbose=False
    ):
    """
    Submits a multiple queries to `organization/subgraph` for `variables`
    from `table` with `arguments` by iterating over a column called `id`.

    Parameters
    ----------
    table : string
        Which table to collect data from
    variables : list(dict or string)
        The variables to collect from the table. If these are nested
        variables then you should input a dict with the variable and
        subvariable
    arguments : dict, optional
        The arguments to the query for things like filtering and
        ordering.
    organization : str
        The organization the subgraph belongs to
    subgraph : str
        The subgraph the table belongs to
    """
    # Grab first argument or set it to 1,000
    limit = arguments.get("first", 1_000)

    # Order ascending by id
    if "id" not in variables:
        variables.append("id")
    arguments.update({"orderBy": "id", "orderDirection": "asc"})

    # Iterate until done iterating through pages
    last_id = ''
    page = 0
    out = []
    while True:
        # Update where argument
        where_arg = arguments.get("where", {})
        where_arg.update({"id_gt": f'"{last_id}"'})
        arguments.update({"where": where_arg})

        if verbose:
            print(arguments)
            print(limit)
            print(page, npages)
            print(last_id)
            print(f"Retrieving {limit*page + 1} to {limit*(page+1)}")

        res = submit_single_query(
            table, variables, arguments, organization, subgraph
        )
        _out = res.json()["data"][table]
        if len(_out) > 0:
            last_id = _out[-1]["id"]

        # Add new value to list of all output
        out.extend(_out)

        page += 1
        nout = len(_out)

        if (nout < limit) or (page >= npages):
            break

    return out
