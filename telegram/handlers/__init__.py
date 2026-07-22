from . import (
    main_menu,
    deals,
    chats,
    autodelivery,
    templates_ui,
    autoresponses,
    blacklist_ui,
    stats_ui,
    settings_ui,
    plugins_ui,
    store,
    inputs,  # ВАЖНО: должен подключаться последним, т.к. ловит "сырые" текст/медиа
)


def setup_all(app):
    main_menu.setup(app)
    deals.setup(app)
    chats.setup(app)
    autodelivery.setup(app)
    templates_ui.setup(app)
    autoresponses.setup(app)
    blacklist_ui.setup(app)
    stats_ui.setup(app)
    settings_ui.setup(app)
    plugins_ui.setup(app)
    store.setup(app)
    inputs.setup(app)  # последним
