from aiogram.fsm.state import State, StatesGroup


class CollectionStates(StatesGroup):
    waiting_add_address = State()
    waiting_remove_address = State()


class ChatStates(StatesGroup):
    waiting_unbind_confirm = State()


class ConfigStates(StatesGroup):
    waiting_import_file = State()


class SettingsStates(StatesGroup):
    waiting_min_price = State()
    waiting_cooldown = State()
    waiting_whale_threshold = State()
    waiting_copy_from_chat_id = State()
    waiting_reset_collections_confirm = State()
    waiting_quiet_hours = State()
    waiting_batch_window = State()
    waiting_template = State()
