import os
import re
import shutil
import subprocess
import zipfile
from typing import Callable, Optional

from yt_dlp import YoutubeDL

ProgressCallback = Callable[[float, str], None]


def resolve_ffmpeg_path() -> Optional[str]:
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        return env_path
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return os.path.dirname(ffmpeg)
    if os.name == "nt":
        default = r"C:\ffmpeg\bin"
        if os.path.isfile(os.path.join(default, "ffmpeg.exe")):
            return default
    return None


def _ffmpeg_binary(ffmpeg_path: Optional[str]) -> str:
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    if ffmpeg_path:
        return os.path.join(ffmpeg_path, name)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        "FFmpeg não encontrado. Instale FFmpeg ou defina FFMPEG_PATH."
    )


class Downloader:
    def __init__(self, link: str, destination: str = ".", formatar_nomes: bool = False):
        self.link = link
        self.destination = destination
        self.formatar_nomes = formatar_nomes
        self.ffmpeg_path = resolve_ffmpeg_path()

    def get_info(self) -> dict:
        with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(self.link, download=False)

        is_playlist = isinstance(info, dict) and "entries" in info
        if is_playlist:
            entries = [e for e in info.get("entries", []) if e]
            first = entries[0] if entries else info
            return {
                "title": info.get("title", "Playlist"),
                "thumbnail": first.get("thumbnail", "") if first else "",
                "duration": sum(e.get("duration") or 0 for e in entries),
                "channel": info.get("uploader", info.get("channel", "Canal não encontrado")),
                "description": info.get("description", "Descrição não encontrada"),
                "is_playlist": True,
                "entry_count": len(entries),
            }

        return {
            "title": info.get("title", "Título não encontrado"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "channel": info.get("channel", "Canal não encontrado"),
            "description": info.get("description", "Descrição não encontrada"),
            "is_playlist": False,
            "entry_count": 1,
        }

    def download_mp4(self, on_progress: Optional[ProgressCallback] = None) -> list[str]:
        return self._download("mp4", on_progress)

    def download_mp3(self, on_progress: Optional[ProgressCallback] = None) -> list[str]:
        return self._download("mp3", on_progress)

    def _download(self, fmt: str, on_progress: Optional[ProgressCallback] = None) -> list[str]:
        os.makedirs(self.destination, exist_ok=True)
        files: list[str] = []

        def progress_hook(d):
            if not on_progress:
                return
            if d["status"] == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                progress = downloaded / total if total else 0
                on_progress(progress, f"Baixando... {int(progress * 100)}%")
            elif d["status"] == "finished":
                on_progress(1.0, "Download concluído, processando...")

        if fmt == "mp4":
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "outtmpl": os.path.join(self.destination, "%(title)s.%(ext)s"),
                "progress_hooks": [progress_hook],
            }
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(self.destination, "%(title)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "progress_hooks": [progress_hook],
            }

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.link, download=True)

            if isinstance(info_dict, dict) and "entries" in info_dict:
                total_videos = len(info_dict["entries"])
                for idx, entry in enumerate(info_dict["entries"], start=1):
                    try:
                        final_file = self._process_entry(ydl, entry, fmt, on_progress, idx, total_videos)
                        if final_file:
                            files.append(final_file)
                    except ValueError as ve:
                        print(f"Erro: {ve} - Ignorando entrada.")
                    except Exception as e:
                        print(f"Erro ao processar vídeo da playlist: {e}")
            else:
                self._validate_video(info_dict)
                final_file = self._process_single(ydl, info_dict, fmt, on_progress)
                files.append(final_file)

        if not files:
            raise FileNotFoundError("Nenhum arquivo foi gerado.")

        return files

    def _validate_video(self, info_dict: dict) -> None:
        if (
            info_dict is None
            or "title" not in info_dict
            or info_dict.get("is_private")
            or info_dict.get("was_live")
            or info_dict.get("uploader") is None
        ):
            raise ValueError("Vídeo indisponível ou não encontrado.")

    def _process_entry(
        self,
        ydl: YoutubeDL,
        entry: dict,
        fmt: str,
        on_progress: Optional[ProgressCallback],
        idx: int,
        total: int,
    ) -> Optional[str]:
        if entry is None or "title" not in entry:
            raise ValueError("Vídeo indisponível na playlist.")

        if on_progress:
            on_progress(idx / total, f"Baixando... [{idx}/{total}]")

        downloaded_file = ydl.prepare_filename(entry)
        return self._finalize_file(downloaded_file, fmt, on_progress)

    def _process_single(
        self,
        ydl: YoutubeDL,
        info_dict: dict,
        fmt: str,
        on_progress: Optional[ProgressCallback],
    ) -> str:
        downloaded_file = ydl.prepare_filename(info_dict)
        return self._finalize_file(downloaded_file, fmt, on_progress)

    def _finalize_file(
        self,
        downloaded_file: str,
        fmt: str,
        on_progress: Optional[ProgressCallback],
    ) -> str:
        if fmt == "mp4" and downloaded_file.endswith(".webm"):
            self.convert_to_mp4(downloaded_file, on_progress)
            os.remove(downloaded_file)
            final_file = downloaded_file.replace(".webm", ".mp4")
        elif fmt == "mp3":
            final_file = downloaded_file.replace(".webm", ".mp3")
        else:
            final_file = downloaded_file

        if not os.path.exists(final_file):
            raise FileNotFoundError(f"O arquivo final {final_file} não foi gerado.")

        if self.formatar_nomes:
            ext = ".mp4" if fmt == "mp4" else ".mp3"
            novo_nome = self.formatar_nome(os.path.splitext(os.path.basename(final_file))[0], ext)
            novo_caminho = os.path.join(self.destination, novo_nome)
            os.rename(final_file, novo_caminho)
            final_file = novo_caminho

        return final_file

    def convert_to_mp4(self, input_file: str, on_progress: Optional[ProgressCallback] = None) -> str:
        output_file = input_file.replace(".webm", ".mp4")
        if on_progress:
            on_progress(0, "Convertendo vídeo...")

        command = [
            _ffmpeg_binary(self.ffmpeg_path), "-y", "-i", input_file,
            "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", output_file,
        ]

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        progress_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        for line in process.stderr:
            match = progress_pattern.search(line)
            if match and on_progress:
                hours, minutes, seconds = map(float, match.groups())
                total_seconds = hours * 3600 + minutes * 60 + seconds
                progress = min(1, total_seconds / 300)
                on_progress(progress, f"Convertendo... {int(progress * 100)}%")

        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Houve um problema durante a conversão do vídeo.")

        if on_progress:
            on_progress(1.0, "Conversão concluída!")
        return output_file

    def formatar_nome(self, nome_original: str, extensao: str = ".mp3") -> str:
        nome_formatado = "".join(
            c for c in nome_original if c.isalnum() or c in (" ", "-")
        ).strip()

        arquivos_existentes = os.listdir(self.destination)
        maior_numero = 0
        padrao = re.compile(r"^(\d{2})-")

        for arquivo in arquivos_existentes:
            match = padrao.match(arquivo)
            if match:
                maior_numero = max(maior_numero, int(match.group(1)))

        novo_numero = maior_numero + 1
        while True:
            nome_completo = f"{novo_numero:02d}-{nome_formatado}{extensao}"
            if not os.path.exists(os.path.join(self.destination, nome_completo)):
                return nome_completo
            novo_numero += 1

    @staticmethod
    def create_zip(files: list[str], zip_path: str) -> str:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                zf.write(file_path, arcname=os.path.basename(file_path))
        return zip_path
