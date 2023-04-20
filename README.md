# Python Queue Celery (Autoscale.app)

Produces [Celery] queue metrics for the [Autoscale.app] [Agent].

## Installation

Install the package:

    pip install autoscale-queue-celery

## Usage

Instructions are provided during the autoscaler setup process on [Autoscale.app].

## Development

Prepare environment:

    pip install poetry
    poetry install

Boot the shell:

    poetry shell

See Paver for relevant tasks:

    paver --help

## Release

1. Update `pyproject.toml` and `__init__.py`
2. Create and push a new tag (`v.1.2.3`)

## Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/autoscale-app/python-queue-celery

[Autoscale.app]: https://autoscale.app
[Agent]: https://github.com/autoscale-app/python-agent
[Celery]: https://docs.celeryq.dev/en/stable/
