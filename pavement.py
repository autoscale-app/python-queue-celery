from paver.easy import sh
from paver.tasks import needs, task


@task
@needs(["format", "test"])
def default():
    pass


@task
def lint():
    sh(
        "autoflake --remove-all-unused-imports -r --check . && isort --check . && black --check ."
    )


@task
def format():
    sh("autoflake --remove-all-unused-imports -ri . && isort . && black .")


@task
def test():
    sh("coverage run -m pytest -vv")


@task
def coverage_report():
    sh("coverage report")


@task
def coverage_html():
    sh("coverage html")
    sh("open htmlcov/index.html")
