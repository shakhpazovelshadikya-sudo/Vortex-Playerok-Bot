from __future__ import annotations

import os
import subprocess
import sys


class UpdateError(Exception):
    pass


class Updater:
    """
    Обновление бота из GitHub-репозитория через `git pull`.

    Данные пользователя (config.yaml, папка data/, logs/, instances/*/config.yaml)
    в git не отслеживаются (см. .gitignore) — при обновлении кода они не трогаются
    и не перезаписываются. Обновляется только сам код бота.
    """

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = os.path.abspath(repo_dir)

    def _run(self, args: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                args, cwd=self.repo_dir, capture_output=True, text=True, timeout=120
            )
        except FileNotFoundError:
            raise UpdateError("Команда 'git' не найдена. Установи git на сервере (apt install git).")
        except subprocess.TimeoutExpired:
            raise UpdateError("Команда выполнялась слишком долго и была прервана.")
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output.strip()

    def is_git_repo(self) -> bool:
        return os.path.isdir(os.path.join(self.repo_dir, ".git"))

    def has_remote(self) -> bool:
        code, out = self._run(["git", "remote"])
        return code == 0 and bool(out.strip())

    def current_commit(self) -> str:
        code, out = self._run(["git", "rev-parse", "--short", "HEAD"])
        return out if code == 0 else "?"

    def check_for_updates(self) -> tuple[bool, str, str]:
        """
        Возвращает (есть_обновление, локальный_коммит, удалённый_коммит).
        Не изменяет рабочую копию — делает только git fetch.
        """
        if not self.is_git_repo():
            raise UpdateError(
                "Это не git-репозиторий (нет папки .git). "
                "Обновление доступно только если бот был склонирован/распакован вместе с .git."
            )
        if not self.has_remote():
            raise UpdateError(
                "К репозиторию не подключён удалённый источник (origin).\n"
                "Подключи его один раз на сервере:\n"
                "git remote add origin https://github.com/ТВОЙ_АККАУНТ/ТВОЙ_РЕПО.git"
            )

        code, out = self._run(["git", "fetch", "--quiet"])
        if code != 0:
            raise UpdateError(f"Не удалось получить обновления (git fetch):\n{out}")

        local = self.current_commit()
        code, remote = self._run(["git", "rev-parse", "--short", "@{u}"])
        if code != 0:
            raise UpdateError(
                "Не удалось определить удалённую ветку для отслеживания.\n"
                "Убедись, что сделан 'git push -u origin main' хотя бы раз."
            )
        return local != remote, local, remote

    def pull_and_upgrade(self, python_exe: str | None = None) -> str:
        """
        Выполняет git pull + переустановку зависимостей.
        При ошибке пытается откатиться на предыдущий коммит и поднимает UpdateError.
        Данные (config.yaml/data/logs) не отслеживаются git'ом и не затрагиваются.
        """
        before = self.current_commit()
        log_lines = [f"📌 Текущая версия: {before}"]

        code, out = self._run(["git", "pull", "--ff-only"])
        log_lines.append("— git pull —\n" + out)
        if code != 0:
            raise UpdateError(
                "Не удалось выполнить git pull (возможно, есть локальные правки кода, "
                "конфликтующие с обновлением):\n\n" + out
            )

        after = self.current_commit()
        log_lines.append(f"📌 Новая версия: {after}")

        python_exe = python_exe or sys.executable
        req_path = os.path.join(self.repo_dir, "requirements.txt")
        if os.path.exists(req_path):
            pip_cmd = [python_exe, "-m", "pip", "install", "-q", "-U", "-r", req_path]
            code, out = self._run(pip_cmd)
            if code != 0 and "externally-managed-environment" in out:
                # Некоторые хостинги (в т.ч. типовые Pterodactyl-образы Python) защищают
                # системный Python (PEP 668) — повторяем с явным разрешением.
                code, out = self._run(pip_cmd + ["--break-system-packages"])
            log_lines.append("— pip install -r requirements.txt —\n" + (out or "(без вывода)"))
            if code != 0:
                # откатываем код обратно, чтобы не остаться в сломанном состоянии
                self._run(["git", "reset", "--hard", before])
                raise UpdateError(
                    "Обновление кода прошло, но не удалось поставить новые зависимости — "
                    "откатил код обратно на предыдущую версию:\n\n" + out
                )

        return "\n\n".join(log_lines)

    def restart_process(self):
        """Перезапускает текущий процесс тем же интерпретатором и теми же аргументами."""
        python_exe = sys.executable
        os.execv(python_exe, [python_exe] + sys.argv)
