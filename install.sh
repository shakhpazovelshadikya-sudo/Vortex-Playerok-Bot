#!/usr/bin/env bash
# ==========================================================
# ==========================================================
#   🌀 Playerok Vortex — Linux инсталлер / менеджер
#   Поддержка мультиаккинга: каждый аккаунт = свой инстанс
#   со своим config.yaml, БД и логом, но общим кодом/venv.
#   Канал: @Vortexplayrock | Юз: @Iucdip
# ==========================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCES_DIR="$PROJECT_DIR/instances"
VENV_DIR="$PROJECT_DIR/.venv"
PID_DIR="$PROJECT_DIR/.pids"

mkdir -p "$INSTANCES_DIR" "$PID_DIR" "$PROJECT_DIR/logs" "$PROJECT_DIR/data"

C_RESET="\033[0m"; C_G="\033[1;32m"; C_Y="\033[1;33m"; C_R="\033[1;31m"; C_C="\033[1;36m"

banner() {
cat << "EOF"

   ⚡〜〜〜〜〜〜〜〜〜〜〜〜〜〜⚡
         .:::.
       .::   ::.
      ::   🌀   ::        P L A Y E R O K   V O R T E X
       ::.   .::             Linux Installer & Manager
         '::::'

     📢 Канал: @Vortexplayrock
     👤 Юз:    @Iucdip
   ⚡〜〜〜〜〜〜〜〜〜〜〜〜〜〜⚡

EOF
}

ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${C_C}Создаю виртуальное окружение...${C_RESET}"
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"
}

install_deps() {
    ensure_venv
    echo -e "${C_C}Устанавливаю зависимости...${C_RESET}"
    pip install --upgrade pip -q
    pip install -q -r "$PROJECT_DIR/requirements.txt"
    echo -e "${C_G}✅ Зависимости установлены.${C_RESET}"
}

list_instances() {
    if [ -z "$(ls -A "$INSTANCES_DIR" 2>/dev/null)" ]; then
        echo -e "${C_Y}Пока нет ни одного аккаунта/инстанса.${C_RESET}"
        return 1
    fi
    echo -e "${C_C}Аккаунты:${C_RESET}"
    local i=1
    for d in "$INSTANCES_DIR"/*/; do
        name="$(basename "$d")"
        if is_running "$name"; then
            status="${C_G}● запущен${C_RESET}"
        else
            status="${C_R}○ остановлен${C_RESET}"
        fi
        echo -e "  $i) $name — $status"
        i=$((i + 1))
    done
}

pid_file() { echo "$PID_DIR/$1.pid"; }

is_running() {
    local name="$1"
    local pf; pf="$(pid_file "$name")"
    [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null
}

create_instance() {
    read -rp "Имя нового аккаунта/инстанса (латиницей, без пробелов): " name
    if [ -z "$name" ]; then echo -e "${C_R}Имя не может быть пустым.${C_RESET}"; return; fi
    local dir="$INSTANCES_DIR/$name"
    if [ -d "$dir" ]; then echo -e "${C_R}Такой инстанс уже существует.${C_RESET}"; return; fi
    mkdir -p "$dir"
    cp "$PROJECT_DIR/config.example.yaml" "$dir/config.yaml"
    sed -i "s/instance_name: \".*\"/instance_name: \"$name\"/" "$dir/config.yaml"
    echo -e "${C_G}✅ Инстанс '$name' создан.${C_RESET}"
    echo -e "${C_Y}Отредактируй файл: $dir/config.yaml${C_RESET} (укажи токены Telegram и Playerok), затем запусти его."
    read -rp "Открыть в nano прямо сейчас? [y/N]: " ans
    if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
        ${EDITOR:-nano} "$dir/config.yaml"
    fi
}

start_instance() {
    local name="$1"
    local dir="$INSTANCES_DIR/$name"
    if [ ! -d "$dir" ]; then echo -e "${C_R}Инстанс не найден.${C_RESET}"; return; fi
    if is_running "$name"; then echo -e "${C_Y}Уже запущен.${C_RESET}"; return; fi
    ensure_venv
    cd "$PROJECT_DIR"
    nohup "$VENV_DIR/bin/python" main.py "$dir/config.yaml" \
        > "$PROJECT_DIR/logs/$name.out.log" 2>&1 &
    echo $! > "$(pid_file "$name")"
    sleep 1
    if is_running "$name"; then
        echo -e "${C_G}✅ '$name' запущен (PID $(cat "$(pid_file "$name")")).${C_RESET}"
    else
        echo -e "${C_R}❌ Не удалось запустить. Смотри logs/$name.out.log${C_RESET}"
    fi
}

stop_instance() {
    local name="$1"
    local pf; pf="$(pid_file "$name")"
    if ! is_running "$name"; then echo -e "${C_Y}Не запущен.${C_RESET}"; return; fi
    kill "$(cat "$pf")" 2>/dev/null || true
    rm -f "$pf"
    echo -e "${C_G}✅ '$name' остановлен.${C_RESET}"
}

restart_instance() {
    stop_instance "$1"
    sleep 1
    start_instance "$1"
}

start_all() {
    for d in "$INSTANCES_DIR"/*/; do
        start_instance "$(basename "$d")"
    done
}

stop_all() {
    for d in "$INSTANCES_DIR"/*/; do
        stop_instance "$(basename "$d")"
    done
}

tail_logs() {
    read -rp "Имя инстанса для просмотра логов: " name
    tail -n 100 -f "$PROJECT_DIR/logs/$name.out.log" 2>/dev/null || echo -e "${C_R}Лог не найден.${C_RESET}"
}

remove_instance() {
    read -rp "Имя инстанса для удаления (данные и конфиг будут удалены!): " name
    stop_instance "$name"
    rm -rf "${INSTANCES_DIR:?}/$name"
    rm -f "$PROJECT_DIR/data/$name.db"
    echo -e "${C_G}✅ Инстанс '$name' удалён.${C_RESET}"
}

update_from_git() {
    cd "$PROJECT_DIR"
    if [ -d ".git" ]; then
        git pull
        install_deps
        echo -e "${C_G}✅ Обновлено. Перезапусти нужные инстансы.${C_RESET}"
    else
        echo -e "${C_R}Это не git-репозиторий.${C_RESET}"
    fi
}

menu() {
    while true; do
        clear
        banner
        list_instances || true
        echo ""
        echo "  1) Установить/обновить зависимости"
        echo "  2) ➕ Создать новый аккаунт (инстанс)"
        echo "  3) ▶️  Запустить инстанс"
        echo "  4) ⏹  Остановить инстанс"
        echo "  5) 🔄 Перезапустить инстанс"
        echo "  6) ▶️▶️ Запустить ВСЕ инстансы"
        echo "  7) ⏹⏹ Остановить ВСЕ инстансы"
        echo "  8) 📄 Смотреть логи инстанса"
        echo "  9) 🗑  Удалить инстанс"
        echo " 10) ⬆️  Обновить бота (git pull)"
        echo "  0) Выход"
        echo ""
        read -rp "Выбери действие: " choice
        case "$choice" in
            1) install_deps; read -rp "Enter..." _;;
            2) create_instance; read -rp "Enter..." _;;
            3) read -rp "Имя инстанса: " n; start_instance "$n"; read -rp "Enter..." _;;
            4) read -rp "Имя инстанса: " n; stop_instance "$n"; read -rp "Enter..." _;;
            5) read -rp "Имя инстанса: " n; restart_instance "$n"; read -rp "Enter..." _;;
            6) start_all; read -rp "Enter..." _;;
            7) stop_all; read -rp "Enter..." _;;
            8) tail_logs;;
            9) remove_instance; read -rp "Enter..." _;;
            10) update_from_git; read -rp "Enter..." _;;
            0) exit 0;;
            *) echo -e "${C_R}Неверный выбор${C_RESET}"; sleep 1;;
        esac
    done
}

# Поддержка non-interactive вызова: ./install.sh start <name>, stop <name>, install и т.д.
case "$1" in
    install) install_deps ;;
    create) create_instance ;;
    start) start_instance "$2" ;;
    stop) stop_instance "$2" ;;
    restart) restart_instance "$2" ;;
    start-all) start_all ;;
    stop-all) stop_all ;;
    list) list_instances ;;
    update) update_from_git ;;
    "") menu ;;
    *) echo "Использование: $0 [install|create|start <name>|stop <name>|restart <name>|start-all|stop-all|list|update]" ;;
esac
