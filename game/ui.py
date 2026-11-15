from ursina import *
from ursina.shaders import unlit_shader

from game.core.modes import MODES

menu_panel = None
settings_panel = None
death_panel = None

mainFont = "assets/font/Minecraft.ttf"

_get_player = lambda: None
_settings   = {
    'volume': 0.7, 
    'sensebilty': 0,
    'fov': 0,
}

def _btn(text, parent, y, on_click, width=0.4):
    return Button(
        text=text,
        parent=parent,
        font=mainFont,
        pixel_perfect=True,
        scale=(width, 0.055),
        origin=(0, 0),
        y=y,
        z=-0.02,
        color=color.rgb(80, 80, 80),
        highlight_color=color.rgb(100, 100, 100),
        pressed_color=color.rgb(55, 55, 55),
        text_color=color.white,
        radius=0.02,
        shader=unlit_shader,
        on_click=on_click,
    )

def _label(text, parent, y):
    return Text(
        text,
        parent=parent,
        font=mainFont,
        pixel_perfect=True,
        scale=0.65,
        origin=(-0.5, 0),
        x=-0.21,
        y=y,
        z=-0.02,
        color=color.rgb(200, 200, 200),
        shader=unlit_shader
    )

def _separator(parent, y):
    Entity(
        parent=parent,
        model='quad',
        color=color.rgba(180, 180, 180, 60),
        scale=(0.5, 0.002),
        y=y,
        z=-0.02,
        shader=unlit_shader
    )

def _slider(parent, y, min_val, max_val, default, step=None):
    s = Slider(
        min=min_val,
        max=max_val,
        default=default,
        step=step,
        dynamic=True,
        parent=parent,
        scale=(0.46, 0.035),
        origin=(0, 0),
        y=y,
        z=-0.02,
    )
    return s

def build_main_menu(start_game):
    global menu_panel, settings_panel

    menu_panel = Entity(parent=camera.ui, enabled=True)

    Text(
        "pythoncraft", 
        parent=menu_panel, 
        font=mainFont,
        pixel_perfect=True,
        scale=3.5, 
        origin=(0,0),
        y=0.2,
        x=0
    )

    Text(
        "by caiothedev", 
        parent=menu_panel, 
        font=mainFont,
        pixel_perfect=True,
        scale=0.8, 
        origin=(0,0),
        y=0.15, 
        x=0,
        color=color.gray
    )

    for i, mode in enumerate(MODES.values()):
        Button(
            f"Jogar {mode.name}", 
            parent=menu_panel, 
            font=mainFont,
            pixel_perfect=True,
            scale=(0.4, 0.06), 
            origin=(0,0),
            y=-0.05 - i * 0.08,
            color=color.rgb32(111, 111, 111),
            highlight_color=color.rgb32(121, 121, 121),
            pressed_color=color.rgb32(86, 86, 86),
            text_color=color.white,
            radius=0.02,
            on_click=Func(start_game, mode.id)
        )

    _btn(
        "Sair",
        menu_panel,
        -0.05 - len(MODES) * 0.08,
        application.quit,
    )

    settings_panel = WindowPanel(
        title="Configurações",
        enabled=False,
        content=(
            Text("Volume: (mock)"),
            Text("Sensibilidade: (mock)")
        ),
        scale=(0.6, 0.6)
    )

    settings_panel.parent = camera.ui
    settings_panel.y = 0

def set_settings_visible(visible: bool):
    if settings_panel:
        settings_panel.enabled = visible

def build_death_screen(respawn_callback, menu_callback):
    global death_panel
    death_panel = Entity(parent=camera.ui, enabled=False)

    Entity(
        parent=death_panel,
        model="quad",
        color=color.rgba32(120, 0, 0, 160),
        scale=(2, 2),
        z=1,
    )

    Text(
        "Você Morreu!",
        parent=death_panel,
        font=mainFont,
        pixel_perfect=True,
        scale=3,
        origin=(0, 0),
        y=0.1,
        color=color.white,
    )

    Button(
        "Respawnar",
        parent=death_panel,
        font=mainFont,
        pixel_perfect=True,
        scale=(0.35, 0.06),
        origin=(0, 0),
        y=-0.05,
        color=color.rgb32(111, 111, 111),
        highlight_color=color.rgb32(121, 121, 121),
        pressed_color=color.rgb32(86, 86, 86),
        text_color=color.white,
        radius=0.02,
        on_click=respawn_callback,
    )

    Button(
        "Menu Principal",
        parent=death_panel,
        font=mainFont,
        pixel_perfect=True,
        scale=(0.35, 0.06),
        origin=(0, 0),
        y=-0.14,
        color=color.rgb32(111, 111, 111),
        highlight_color=color.rgb32(121, 121, 121),
        pressed_color=color.rgb32(86, 86, 86),
        text_color=color.white,
        radius=0.02,
        on_click=menu_callback,
    )

def show_death_screen():
    global death_panel
    if death_panel:
        death_panel.enabled = True

def hide_death_screen():
    global death_panel
    if death_panel:
        death_panel.enabled = False