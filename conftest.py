import sys

# TODO: add option or in other way allow developer to enable debug logging.
if False:
    import logging
    logging.basicConfig(level=logging.DEBUG)


def pytest_cmdline_preparse(args):
    if sys.version_info[:2] == (3, 5):
        # Disable pylint on Python 3.5, since it's broken:
        # <https://bitbucket.org/logilab/astroid/issues/187/call-object-has-no-attribute-starargs>
        args[:] = (
            ["-p", "no:pylint"] +
            [arg for arg in args if "pylint" not in arg])
