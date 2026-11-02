"""Сборка GIF из кадров через внешний ffmpeg."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from loguru import logger

FFMPEG: str = "ffmpeg"


def ffmpeg_available() -> bool:
    """Есть ли ffmpeg в PATH."""
    return shutil.which(FFMPEG) is not None


def _command(frames_dir: Path, output: Path, fps: int) -> list[str]:
    return [
        FFMPEG,
        "-y",
        "-framerate",
        str(max(1, int(fps))),
        "-i",
        str(frames_dir / "%05d.png"),
        "-loop",
        "0",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        str(output),
    ]


async def _run(command: list[str]) -> int:
    """Запустить ffmpeg и вернуть код возврата."""
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    return await process.wait()


async def frames_to_gif_async(
    frames_dir: Path, output: Path, fps: int = 2
) -> Path | None:
    """Собрать GIF асинхронно; None — ffmpeg недоступен или упал."""
    if not ffmpeg_available():
        logger.warning("gif: ffmpeg не найден в PATH")
        return None
    try:
        code = await _run(_command(frames_dir, output, fps))
    except (FileNotFoundError, OSError) as exc:
        logger.warning("gif: ffmpeg не запустился: {}", exc)
        return None
    if code != 0 or not output.exists():
        logger.warning("gif: ffmpeg вернул код {}", code)
        return None
    return output


def frames_to_gif(frames_dir: Path, output: Path, fps: int = 2) -> Path | None:
    """Синхронная обёртка: запускает отдельный цикл событий.

    Не вызывать изнутри работающего event loop — используйте
    :func:`frames_to_gif_async`.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(frames_to_gif_async(frames_dir, output, fps))
    logger.warning("gif: frames_to_gif вызван внутри event loop, нужен async-вариант")
    return None
