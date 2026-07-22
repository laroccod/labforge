"""
The colour table — chrome, plot palette and equation ink — and the one
process-wide selection of it.

Holding all three in one frozen value is what keeps them from drifting apart.
Pure hexes, no Flet import: shell.py owns the mapping onto ColorScheme slots, so
figures.py and mathtext.py read the palette without pulling in the UI layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """
    Every colour the app draws, chrome and plots together.

    Parameters
    ----------
    name: str
        The key open(theme=...) selects this theme by.
    note: str
        One-line description, shown by names().
    mode: str
        "dark" or "light"; drives the Flet ThemeMode so widget defaults the
        scheme does not name (shadows, ripples, error tones) match the surfaces.
    accent: str
        The single electric colour reserved for interactive and live things.
    on_accent: str
        Ink drawn on top of accent fills; carries the accent's contrast burden.
    accent_dim: str
        Muted accent fill for selected-but-not-active chrome (the rail indicator).
    on_accent_dim: str
        Ink on accent_dim.
    surface: str
        The page background.
    surface_lowest: str
        Recessed chrome — the top bar and rail.
    surface_low: str
        The lowest raised container step.
    surface_container: str
        The standard card fill.
    surface_high: str
        A raised card step.
    surface_highest: str
        The most raised step; input fills.
    on_surface: str
        Body ink.
    on_surface_variant: str
        Secondary ink — labels, readouts, anything factual but not primary.
    outline: str
        Borders that must read as a boundary.
    outline_variant: str
        Hairline dividers that must not.
    data: str
        Plot colour for the worker's data — matches accent, so a figure reads as
        part of the app.
    model: str
        Plot colour for a model or comparison curve; contrasts with data.
    highlight: str
        Third plot colour, for an emphasised subset.
    ink: str
        Plot and equation ink. Sits on a transparent PNG over surface, so it
        tracks on_surface rather than being pure white.
    grid: str
        Plot grid and spines.
    """

    name: str
    note: str
    mode: str
    accent: str
    on_accent: str
    accent_dim: str
    on_accent_dim: str
    surface: str
    surface_lowest: str
    surface_low: str
    surface_container: str
    surface_high: str
    surface_highest: str
    on_surface: str
    on_surface_variant: str
    outline: str
    outline_variant: str
    data: str
    model: str
    highlight: str
    ink: str
    grid: str


THEMES = {
    "instrument": Theme(
        name="instrument",
        note="Near-black teal-tinted surfaces, one electric accent.",
        mode="dark",
        accent="#2BE4C8",
        on_accent="#04211C",
        accent_dim="#123B33",
        on_accent_dim="#7FEFD9",
        surface="#0B0F10",
        surface_lowest="#080C0D",
        surface_low="#11181A",
        surface_container="#141C1E",
        surface_high="#182123",
        surface_highest="#1C2628",
        on_surface="#E4EBEA",
        on_surface_variant="#8CA0A0",
        outline="#3C4C4E",
        outline_variant="#233032",
        data="#2BE4C8",
        model="#FF4D9E",
        highlight="#7FEFD9",
        ink="#D9E2E0",
        grid="#3A4649",
    ),
    "neon_violet": Theme(
        name="neon_violet",
        mode="dark",
        note="Violet chrome with hot-pink data on black.",
        accent="#9929EA",
        on_accent="#FFFFFF",
        accent_dim="#2E1147",
        on_accent_dim="#D9A6FF",
        surface="#000000",
        surface_lowest="#0A0410",
        surface_low="#120818",
        surface_container="#170A22",
        surface_high="#1E0E2C",
        surface_highest="#251236",
        on_surface="#F3EAFB",
        on_surface_variant="#A98BC4",
        outline="#3B1B57",
        outline_variant="#26113A",
        data="#FF5FCF",
        model="#FAEB92",
        highlight="#9929EA",
        ink="#F3EAFB",
        grid="#3B1B57",
    ),
    "neon_gold": Theme(
        name="neon_gold",
        mode="dark",
        note="The violet palette with pale gold as the accent instead.",
        accent="#FAEB92",
        on_accent="#1A0B26",
        accent_dim="#3E3418",
        on_accent_dim="#FAEB92",
        surface="#000000",
        surface_lowest="#0C0610",
        surface_low="#150823",
        surface_container="#1A0B26",
        surface_high="#221030",
        surface_highest="#29143A",
        on_surface="#F6EEFC",
        on_surface_variant="#AE90C8",
        outline="#43205F",
        outline_variant="#2B1440",
        data="#FF5FCF",
        model="#9929EA",
        highlight="#FAEB92",
        ink="#F6EEFC",
        grid="#43205F",
    ),
    "retro_green": Theme(
        name="retro_green",
        mode="dark",
        note="Matrix mood with a calmer green and a legible olive card.",
        accent="#08CB00",
        on_accent="#00230A",
        accent_dim="#12400A",
        on_accent_dim="#7CFF77",
        surface="#000000",
        surface_lowest="#050805",
        surface_low="#1B2A00",
        surface_container="#253900",
        surface_high="#2E4600",
        surface_highest="#375300",
        on_surface="#EEEEEE",
        on_surface_variant="#8FA07A",
        outline="#3A5410",
        outline_variant="#223300",
        data="#08CB00",
        model="#EEEEEE",
        highlight="#7CFF77",
        ink="#EEEEEE",
        grid="#3A5410",
    ),
    "paper": Theme(
        name="paper",
        note="Warm paper surfaces, graphite ink and a vermilion accent.",
        mode="light",
        accent="#C14B2E",
        on_accent="#FFF6F1",
        accent_dim="#F2D9CE",
        on_accent_dim="#8A2F1B",
        surface="#FAF6EF",
        surface_lowest="#F1EAD9",
        surface_low="#FFFFFF",
        surface_container="#FFFDF8",
        surface_high="#FFFFFF",
        surface_highest="#FFFFFF",
        on_surface="#33302A",
        on_surface_variant="#7A7264",
        outline="#C9BFA9",
        outline_variant="#E5DECC",
        data="#C14B2E",
        model="#2E6F8E",
        highlight="#E0A458",
        ink="#33302A",
        grid="#C9BFA9",
    ),
    "mint": Theme(
        name="mint",
        note="Light mint greens on white, colorhunt's fresh-green family.",
        mode="light",
        accent="#3E8E5A",
        on_accent="#F2FBF4",
        accent_dim="#D8F0DC",
        on_accent_dim="#2C6E44",
        surface="#F4FAEF",
        surface_lowest="#E4F3DA",
        surface_low="#FFFFFF",
        surface_container="#FBFEF8",
        surface_high="#FFFFFF",
        surface_highest="#FFFFFF",
        on_surface="#24312A",
        on_surface_variant="#6D8072",
        outline="#B9CDB9",
        outline_variant="#DCE9D8",
        data="#3E8E5A",
        model="#B85B9E",
        highlight="#7FBF6C",
        ink="#24312A",
        grid="#B9CDB9",
    ),
    "glacier": Theme(
        name="glacier",
        note="Pale glacier blues with a deep slate accent.",
        mode="light",
        accent="#4A628A",
        on_accent="#F2F7FF",
        accent_dim="#D5E4EE",
        on_accent_dim="#35577D",
        surface="#F2F8FA",
        surface_lowest="#E0EEF2",
        surface_low="#FFFFFF",
        surface_container="#FAFDFE",
        surface_high="#FFFFFF",
        surface_highest="#FFFFFF",
        on_surface="#22303B",
        on_surface_variant="#64798A",
        outline="#B4C8D4",
        outline_variant="#DCE8EE",
        data="#3D7EA6",
        model="#C96A4A",
        highlight="#4A628A",
        ink="#22303B",
        grid="#B4C8D4",
    ),
    "lavender": Theme(
        name="lavender",
        note="Soft lavender neutrals with a deep violet accent.",
        mode="light",
        accent="#7C6BD6",
        on_accent="#F8F6FF",
        accent_dim="#E3DBF7",
        on_accent_dim="#5A4BB0",
        surface="#F7F4FC",
        surface_lowest="#EDE6F7",
        surface_low="#FFFFFF",
        surface_container="#FCFAFF",
        surface_high="#FFFFFF",
        surface_highest="#FFFFFF",
        on_surface="#2C2838",
        on_surface_variant="#756E88",
        outline="#C4BBDA",
        outline_variant="#E4DEF1",
        data="#7C6BD6",
        model="#D66B8F",
        highlight="#A594F9",
        ink="#2C2838",
        grid="#C4BBDA",
    ),
}

DEFAULT = "paper"

# The process-wide selection, rebound only by use() before the app serves. This
# is the one piece of module state the per-session rule tolerates: Flet calls
# main(page) per browser connection, but every session resolves the same theme,
# so it is config rather than shared mutable state.
ACTIVE = THEMES[DEFAULT]


def names():
    """The registered themes as {name: note}, in registration order."""
    return {name: theme.note for name, theme in THEMES.items()}


def use(name):
    """
    Select the process-wide theme by name and return it.

    Called once from shell.build_main before the app serves; see ACTIVE on why
    process-wide state is safe here.
    """
    global ACTIVE
    if name not in THEMES:
        raise ValueError(f"theme must be one of {sorted(THEMES)}, got {name!r}.")
    ACTIVE = THEMES[name]
    return ACTIVE


def active():
    """
    The active Theme: the palette figures and equations render with.

    Read at draw time, never bound at import, so a figure follows whichever
    theme open(theme=...) selected.
    """
    return ACTIVE
