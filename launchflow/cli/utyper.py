import asyncio
import inspect
from functools import wraps

import click
import typer


class UTyper(typer.Typer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("pretty_exceptions_enable", False)
        super().__init__(*args, **kwargs)

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)

        def add_runner(f):
            @wraps(f)
            def runner(*args, **kwargs):
                ctx = click.get_current_context()
                root = ctx
                while root.parent is not None:
                    root = root.parent
                try:
                    if inspect.iscoroutinefunction(f):
                        results = asyncio.run(f(*args, **kwargs))
                    else:
                        results = f(*args, **kwargs)
                    return results
                except Exception:
                    raise

            return decorator(runner)

        return add_runner
