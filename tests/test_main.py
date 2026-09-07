from main import parse_args


def test_parse_args_uses_interactive_defaults():
    args = parse_args([])

    assert args.yes is False
    assert args.dry_run is False


def test_parse_args_enables_automatic_confirmation():
    args = parse_args(["--yes"])

    assert args.yes is True
    assert args.dry_run is False


def test_parse_args_enables_dry_run():
    args = parse_args(["--dry-run"])

    assert args.yes is False
    assert args.dry_run is True


def test_parse_args_accepts_yes_with_dry_run():
    args = parse_args(["--yes", "--dry-run"])

    assert args.yes is True
    assert args.dry_run is True