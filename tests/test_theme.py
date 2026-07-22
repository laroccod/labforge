"""
Theme unit tests

Pure-Python checks on the colour table and the process-wide selection: that an
unknown name fails loudly at open() rather than silently falling back, and that
selecting a theme moves the plot palette and equation ink with the chrome —
the drift this module exists to prevent.
"""

import pytest

from labforge import palette, themes
from labforge import theme as theme_module


@pytest.fixture(autouse=True)
def restore_default_theme():
    """
    Reset the process-wide theme after each test.

    The active theme is module state, so a test that selects one would otherwise
    leak its palette into every test that runs after it.
    """
    yield
    theme_module.use(theme_module.DEFAULT)


def test_names_lists_every_registered_theme():
    listed = themes()
    assert listed["instrument"]
    assert set(listed) == set(theme_module.THEMES)
    # Every theme is listed with a note; names() is what open()'s docstring points at.
    assert all(note for note in listed.values())


def test_use_rejects_an_unknown_theme():
    with pytest.raises(ValueError, match="theme must be one of"):
        theme_module.use("gruvbox")


def test_use_switches_the_active_palette():
    # Which theme is default is config; that use() moves the palette is the contract.
    assert theme_module.active().name == theme_module.DEFAULT
    theme_module.use("retro_green")
    assert theme_module.active().name == "retro_green"
    assert theme_module.active().accent == "#08CB00"


def test_palette_follows_the_active_theme():
    # An author's figure reads palette() at draw time, so it must track use().
    assert palette().data == theme_module.THEMES[theme_module.DEFAULT].data
    theme_module.use("neon_violet")
    assert palette().data == "#FF5FCF"


def test_every_theme_defines_every_colour():
    # A missing hex would surface as a Flet render error, not a Python one.
    for name, theme in theme_module.THEMES.items():
        assert theme.mode in ("dark", "light"), f"{name}.mode = {theme.mode!r}"
        for field, value in vars(theme).items():
            if field in ("name", "note", "mode"):
                continue
            assert value.startswith("#") and len(value) == 7, f"{name}.{field} = {value!r}"


def test_theme_name_matches_its_key():
    for key, theme in theme_module.THEMES.items():
        assert theme.name == key
