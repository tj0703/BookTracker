from click.testing import CliRunner

from app_cli.cli import main


def test_hello_default():
    runner = CliRunner()
    result = runner.invoke(main, ["hello"])
    assert result.exit_code == 0
    assert "Hello, world!" in result.output


def test_hello_name():
    runner = CliRunner()
    result = runner.invoke(main, ["hello", "Tanvi"])
    assert result.exit_code == 0
    assert "Hello, Tanvi!" in result.output
