import os
import sys
import threading

import customtkinter as ctk
import requests
from customtkinter import CTk, CTkButton, CTkCheckBox, CTkEntry, CTkFont, CTkFrame, CTkImage, CTkLabel, CTkProgressBar, CTkToplevel
from io import BytesIO
from PIL import Image
from tkinter import filedialog, messagebox

from downloader import Downloader


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class TkProgressAdapter:
    def __init__(self, progress_bar, progress_label):
        self.progress_bar = progress_bar
        self.progress_label = progress_label

    def __call__(self, progress: float, message: str):
        self.progress_bar.set(min(max(progress, 0), 1))
        self.progress_label.configure(text=message)


class BaixarVideo:
    def __init__(self, root):
        ctk.set_appearance_mode("dark")
        self.root = root
        self.root.title("Youtube Downloader")
        self.root.geometry("1100x440")
        self.destination = "."
        self.formatar_nomes = ctk.BooleanVar(value=False)
        icon_path = resource_path(os.path.join("images", "icon.ico"))
        if os.path.isfile(icon_path):
            self.root.iconbitmap(icon_path)
        my_font = CTkFont(family="Segoe UI", size=14, weight="bold")

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.left_frame = CTkFrame(root, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.left_frame.grid_rowconfigure((0, 1, 2, 3), weight=1)

        self.link_label = CTkLabel(self.left_frame, text="Link do vídeo:", font=my_font)
        self.link_label.grid(row=0, column=0, padx=5, sticky="e")

        self.checkbox_tooltip_label = CTkLabel(self.left_frame, text="*", text_color="#c74066", cursor="hand2")
        self.checkbox_tooltip_label.grid(row=0, column=1, sticky="w", padx=0)
        self.checkbox_tooltip_label.bind(
            "<Enter>",
            lambda e: self.show_tooltip(
                e,
                "Links suportados:\n- URL de um único vídeo.\n- URL de uma playlist completa.",
                x_offset=-120,
                y_offset=30,
            ),
        )
        self.checkbox_tooltip_label.bind("<Leave>", self.hide_tooltip)

        self.link_entry = CTkEntry(self.left_frame, corner_radius=30, width=300, height=40, border_color="#c74066")
        self.link_entry.grid(row=0, column=1, columnspan=2, padx=10, sticky="ew")

        self.info_button = CTkButton(
            self.left_frame,
            text="Info",
            width=110,
            height=40,
            corner_radius=50,
            fg_color="#c74066",
            command=self.show_info,
            font=my_font,
            hover_color="#b03558",
            border_color="#000000",
            border_width=2,
        )
        self.info_button.grid(row=0, column=3, padx=10, sticky="w")

        self.download_mp3_button = CTkButton(
            self.left_frame,
            text="Baixar MP3",
            width=150,
            height=40,
            corner_radius=50,
            fg_color="#c74066",
            command=self.download_mp3,
            font=my_font,
            hover_color="#b03558",
            border_color="#000000",
            border_width=2,
        )
        self.download_mp3_button.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        self.download_mp4_button = CTkButton(
            self.left_frame,
            text="Baixar MP4",
            width=150,
            height=40,
            corner_radius=50,
            fg_color="#c74066",
            command=self.download_mp4,
            font=my_font,
            hover_color="#b03558",
            border_color="#000000",
            border_width=2,
        )
        self.download_mp4_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.checkbox_frame = CTkFrame(self.left_frame, fg_color="transparent")
        self.checkbox_frame.grid(row=2, column=1, columnspan=2, pady=(5, 0), sticky="n")

        self.checkbox = CTkCheckBox(
            self.checkbox_frame,
            text="Formatar nomes automaticamente",
            variable=self.formatar_nomes,
            command=self.toggle_format_names,
            fg_color="#c75979",
            hover_color="#c74066",
            text_color="white",
            checkmark_color="white",
        )
        self.checkbox.grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.tooltip_label = CTkLabel(self.checkbox_frame, text="*", text_color="#c74066", cursor="hand2")
        self.tooltip_label.grid(row=0, column=1, sticky="w", padx=1)
        self.tooltip_label.bind(
            "<Enter>",
            lambda e: self.show_tooltip(
                e,
                "Ativar esta opção irá:\n- Adicionar uma numeração ao nome do arquivo.\n- Remover caracteres especiais automaticamente.",
                x_offset=-180,
                y_offset=30,
            ),
        )
        self.tooltip_label.bind("<Leave>", self.hide_tooltip)

        self.dest_button = CTkButton(
            self.left_frame,
            text="Selecionar Pasta",
            width=150,
            height=40,
            corner_radius=32,
            fg_color="#c74066",
            command=self.select_destination,
            font=my_font,
            hover_color="#b03558",
            border_color="#000000",
            border_width=2,
        )
        self.dest_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="e")

        self.dest_path = CTkLabel(self.left_frame, text="Diretório Indefinido", text_color="white")
        self.dest_path.grid(row=3, column=2, columnspan=2, padx=20, pady=5, sticky="w")

        self.dest_tooltip_label = CTkLabel(self.left_frame, text="*", text_color="#c74066", cursor="hand2")
        self.dest_tooltip_label.grid(row=3, column=2, columnspan=2, sticky="w", padx=10, pady=5)
        self.dest_tooltip_label.bind(
            "<Enter>",
            lambda e: self.show_tooltip(
                e,
                "Ao clicar no botão:\n- Altera o diretório em que o arquivo será baixado\n- Caso não selecione um, irá para o diretório padrão do programa.",
                x_offset=-180,
                y_offset=-70,
            ),
        )
        self.dest_tooltip_label.bind("<Leave>", self.hide_tooltip)

        self.info_frame = CTkFrame(root, corner_radius=10)
        self.info_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.thumbnail_label = CTkLabel(self.info_frame, text="Informações do Vídeo", wraplength=200, font=my_font)
        self.thumbnail_label.pack(pady=10)

        image_path = resource_path(os.path.join("images", "infoimg.png"))
        if os.path.isfile(image_path):
            self.default_image = CTkImage(light_image=Image.open(image_path), size=(320, 180))
        else:
            self.default_image = None

        self.thumbnail_image = CTkLabel(
            self.info_frame,
            image=self.default_image,
            text="" if self.default_image else "Sem preview",
        )
        self.info_details = CTkLabel(self.info_frame, text="", wraplength=350, justify="left", font=my_font)
        self.info_details.pack(pady=10)
        self.thumbnail_image.pack()
        self.tooltip = None

    def show_progress_window(self):
        my_font = CTkFont(family="Segoe UI", size=14, weight="bold")
        self.progress_window = CTkToplevel(self.root)
        self.progress_window.title("Progresso do Download")
        self.progress_window.geometry("650x200")
        self.progress_window.resizable(False, False)
        self.progress_window.attributes("-topmost", True)

        self.progress_label = CTkLabel(self.progress_window, text="Iniciando download...", font=my_font)
        self.progress_label.pack(pady=20)

        self.progress_bar = CTkProgressBar(
            self.progress_window,
            width=300,
            height=30,
            corner_radius=20,
            border_color="#000000",
            border_width=3,
            progress_color="#c74066",
            fg_color="#000000",
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def show_tooltip(self, event, text, x_offset=-120, y_offset=25):
        if self.tooltip is None:
            self.tooltip = CTkLabel(
                self.left_frame,
                text=text,
                text_color="white",
                fg_color="#c74066",
                corner_radius=30,
                justify="center",
                width=350,
                height=55,
            )
            self.tooltip.update_idletasks()
            self.tooltip.place(
                x=event.x_root - self.left_frame.winfo_rootx() - self.tooltip.winfo_width() + x_offset,
                y=event.y_root - self.left_frame.winfo_rooty() + y_offset,
            )
            self.tooltip.lift()

    def hide_tooltip(self, event):
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None

    def toggle_format_names(self):
        if self.formatar_nomes.get():
            print("Formatação de nomes ativada.")
        else:
            print("Formatação de nomes desativada.")

    def select_destination(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.destination = folder_selected
            self.dest_path.configure(text=self.destination)

    def _show_completion(self, final_files: list[str]):
        my_font = CTkFont(family="Segoe UI", size=14, weight="bold")
        for widget in self.progress_window.winfo_children():
            widget.destroy()

        if len(final_files) == 1:
            final_file = final_files[0]
            text = (
                f"Download concluído!\n\nArquivo: {os.path.basename(final_file)}\n"
                f"Local: {os.path.dirname(os.path.abspath(final_file))}"
            )
        else:
            local_path = os.path.dirname(os.path.abspath(final_files[0]))
            text = f"Download concluído!\n\n{len(final_files)} arquivos salvos em:\n{local_path}"

        progress_label = CTkLabel(self.progress_window, text=text, font=my_font, justify="center")
        progress_label.pack(pady=20)

        close_button = CTkButton(
            self.progress_window,
            text="Fechar",
            command=self.progress_window.destroy,
            width=110,
            height=40,
            corner_radius=50,
            fg_color="#c74066",
            font=my_font,
            hover_color="#b03558",
            border_color="#000000",
            border_width=1,
        )
        close_button.pack(pady=10)

    def _run_download(self, fmt: str):
        link = self.link_entry.get().strip()
        if not link:
            messagebox.showwarning("Atenção", "Por favor, insira o link do vídeo.")
            return

        self.show_progress_window()
        downloader = Downloader(link, self.destination, formatar_nomes=self.formatar_nomes.get())
        progress = TkProgressAdapter(self.progress_bar, self.progress_label)

        def task():
            try:
                if fmt == "mp4":
                    files = downloader.download_mp4(on_progress=progress)
                else:
                    files = downloader.download_mp3(on_progress=progress)
                self.root.after(0, lambda: self._show_completion(files))
            except Exception as e:
                self.root.after(0, lambda: self._handle_download_error(e))

        self.run_in_thread(task)

    def _handle_download_error(self, error: Exception):
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror("Erro", f"Ocorreu um erro ao baixar: {error}")

    def download_mp4(self):
        self._run_download("mp4")

    def download_mp3(self):
        self._run_download("mp3")

    def show_info(self):
        def _downloadinfo():
            link = self.link_entry.get().strip()
            if not link:
                messagebox.showwarning("Atenção", "Por favor, insira o link do vídeo.")
                return

            try:
                info = Downloader(link).get_info()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível obter informações do vídeo: {e}")
                return

            minutes = info["duration"] // 60
            seconds = info["duration"] % 60
            self.thumbnail_label.configure(text=info["title"])
            playlist_note = f"\nPlaylist: {info['entry_count']} vídeos" if info.get("is_playlist") else ""
            details = (
                f"Duração: {minutes}:{seconds:02}{playlist_note}\n"
                f"Canal: {info['channel']}\n"
                f"Descrição:\n{info['description'][:70]}..."
            )
            self.info_details.configure(text=details)

            if info["thumbnail"]:
                try:
                    response = requests.get(info["thumbnail"], stream=True, timeout=15)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        thumbnail = CTkImage(light_image=img, size=(320, 180))
                        self.thumbnail_image.configure(image=thumbnail)
                        self.thumbnail_image.image = thumbnail
                    elif self.default_image:
                        self.thumbnail_image.configure(image=self.default_image)
                except Exception:
                    if self.default_image:
                        self.thumbnail_image.configure(image=self.default_image)

        self.run_in_thread(_downloadinfo)


if __name__ == "__main__":
    root = CTk()
    app = BaixarVideo(root)
    root.mainloop()
