import sys
from pathlib import Path

# Добавляем корень проекта, чтобы `import main` работал при запуске pytest.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
