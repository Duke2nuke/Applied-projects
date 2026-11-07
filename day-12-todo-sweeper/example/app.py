"""A tiny example module with a few planted markers (synthetic demo data)."""


def load_users(path):
    # TODO: support pagination for large user lists
    with open(path) as fh:
        return [line.strip() for line in fh]


def calculate_total(items):
    # FIXME: rounding error when prices have more than 2 decimals
    return round(sum(items), 2)


def legacy_export(data):
    # HACK: the old API expects a trailing comma, remove after migration
    return ",".join(data) + ","
