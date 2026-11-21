"""
Assistente Virtual por Voz - com avatar (imagem) na tela
----------------------------------------------------------
Bibliotecas necessárias:
    pip install SpeechRecognition pyttsx3 pyaudio pillow

No Windows, se pyaudio der erro na instalação, use:
    pip install pipwin
    pipwin install pyaudio

tkinter já vem com o Python, não precisa instalar.

IMAGEM DO AVATAR:
    Coloque um arquivo chamado "avatar.png" (ou "avatar.jpg") na mesma
    pasta deste script (ex: Área de Trabalho). Se não encontrar,
    o assistente volta a desenhar um rosto simples como reserva.

Palavra de ativação: diga "assistente" antes do comando.
Exemplos: "assistente, que horas são", "assistente, abrir spotify"

Uma janelinha flutuante com sua imagem aparece no canto da tela. Enquanto o
assistente fala, uma boca simples abre e fecha sobre o avatar. O anel colorido
ao redor também muda conforme o estado:
- Cinza: parado, esperando a palavra de ativação
- Verde (pulsando): ouvindo o comando
- Azul (pulsando mais rápido): falando a resposta

Você pode arrastar a janela clicando e segurando nela.
Clique com o botão direito nela para fechar o assistente.
"""

import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import sys
import threading
import tkinter as tk
import base64
import subprocess
import time

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_DISPONIVEL = True
except ImportError:
    PIL_DISPONIVEL = False

PALAVRA_ATIVACAO = "assistente"

# Nome dos possíveis arquivos de imagem do avatar (procurados na pasta do script)
NOMES_AVATAR = ["avatar.png", "avatar.jpg", "avatar.jpeg"]

# Ajuste fino do enquadramento vertical em fotos de retrato (verticais).
# 0.0 = recorte começa bem no topo da imagem (mostra mais da cabeça/cabelo)
# 0.5 = recorte centralizado (padrão "meio da imagem")
# Aumente um pouco se ainda cortar a testa/cabelo; diminua se cortar o queixo.
AVATAR_RECORTE_TOPO = 0.08

# Posição da boca no avatar, em proporção à imagem circular.
# Estes valores foram ajustados para a imagem atual do Goku. Se trocar a
# imagem, aumente/diminua os números para mover a boca na horizontal/vertical.
BOCA_X = 0.52
BOCA_Y = 0.735

# ---------- Estado compartilhado entre a thread de voz e a interface gráfica ----------
estado_lock = threading.Lock()
estado_atual = "idle"  # idle | ouvindo | falando


def set_estado(novo_estado: str):
    global estado_atual
    with estado_lock:
        estado_atual = novo_estado


def get_estado() -> str:
    with estado_lock:
        return estado_atual


# ---------- Configuração da voz (texto -> fala) ----------
def _falar_com_daniel(texto: str):
    """Usa a voz Microsoft Daniel pela interface nativa do Windows."""
    texto_powershell = texto.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Speech
$sintetizador = New-Object System.Speech.Synthesis.SpeechSynthesizer
$sintetizador.SelectVoice('Microsoft Daniel')
$sintetizador.Rate = 1
$sintetizador.Speak('{texto_powershell}')
$sintetizador.Dispose()
"""
    comando_codificado = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", comando_codificado],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def falar(texto: str):
    """Converte texto em fala e exibe no console."""
    print(f"Assistente: {texto}")
    set_estado("falando")

    try:
        _falar_com_daniel(texto)
    except (OSError, subprocess.CalledProcessError) as erro:
        print(f"Aviso: não foi possível usar Microsoft Daniel ({erro}). Usando voz de reserva.")
        engine = pyttsx3.init()
        engine.setProperty('rate', 185)
        engine.say(texto)
        engine.runAndWait()
        engine.stop()
    finally:
        set_estado("idle")


# ---------- Reconhecimento de voz (fala -> texto) ----------
def ouvir(timeout=5, phrase_time_limit=6) -> str:
    """Escuta o microfone e retorna o texto reconhecido em minúsculas."""
    set_estado("ouvindo")
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            set_estado("idle")
            return ""

    set_estado("idle")

    try:
        comando = recognizer.recognize_google(audio, language='pt-BR')
        print(f"Você disse: {comando}")
        return comando.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        falar("Estou sem conexão com o serviço de reconhecimento de voz.")
        return ""


# ---------- Ações auxiliares ----------
def abrir_spotify():
    try:
        os.startfile("spotify:")
    except OSError:
        webbrowser.open("https://open.spotify.com")


def confirmar_desligamento() -> bool:
    falar("Tem certeza que deseja desligar o computador? Diga sim para confirmar.")
    time.sleep(1.5)  # evita captar o eco da própria fala no microfone
    resposta = ouvir(timeout=8, phrase_time_limit=4)
    print(f"[debug] Resposta de confirmação entendida: '{resposta}'")
    return "sim" in resposta


def desligar_pc():
    if not confirmar_desligamento():
        falar("Desligamento cancelado.")
        return
    falar("Desligando o computador em quinze segundos. Diga 'cancelar desligamento' para impedir.")
    os.system("shutdown /s /t 15")

    # Pequena pausa para o eco da própria fala do assistente sumir do
    # microfone antes de começar a ouvir. Sem isso, o microfone às vezes
    # capta o som "cancelar desligamento" saindo da caixa de som e cancela
    # sozinho na hora.
    time.sleep(1.5)

    resposta = ouvir(timeout=10, phrase_time_limit=4)
    # Exige a frase completa (não só a palavra solta "cancelar"), para
    # reduzir falsos positivos de reconhecimento.
    if "cancelar desligamento" in resposta or "cancelar o desligamento" in resposta:
        os.system("shutdown /a")
        falar("Desligamento cancelado.")


# ---------- Lógica dos comandos ----------
def processar_comando(comando: str) -> bool:
    if not comando:
        return True

    if "que horas são" in comando or "horas" in comando:
        agora = datetime.datetime.now().strftime("%H:%M")
        falar(f"Agora são {agora}")

    elif "data de hoje" in comando or "que dia é hoje" in comando:
        hoje = datetime.datetime.now().strftime("%d/%m/%Y")
        falar(f"Hoje é {hoje}")

    elif "abrir youtube" in comando:
        falar("Abrindo o YouTube")
        webbrowser.open("https://youtube.com")

    elif "abrir google" in comando:
        falar("Abrindo o Google")
        webbrowser.open("https://google.com")

    elif "abrir spotify" in comando or "tocar música" in comando or "tocar musica" in comando:
        falar("Abrindo o Spotify")
        abrir_spotify()

    elif "pesquisar" in comando:
        termo = comando.replace("pesquisar", "").strip()
        if termo:
            falar(f"Pesquisando por {termo}")
            webbrowser.open(f"https://www.google.com/search?q={termo}")
        else:
            falar("O que você quer que eu pesquise?")

    elif "qual é seu nome" in comando:
        falar("Eu sou goku,seu assistente virtual, criado em Python.")

    elif "desligar o computador" in comando or "desligar o pc" in comando or "desligar pc" in comando:
        desligar_pc()

    elif any(p in comando for p in ["sair", "encerrar assistente", "tchau"]):
        falar("Até logo!")
        return False

    else:
        falar("Ainda não sei fazer isso, mas você pode me ensinar editando o código.")

    return True


# ---------- Loop de voz (roda em thread separada da interface) ----------
def loop_voz():
    falar(f"Assistente iniciado. Diga '{PALAVRA_ATIVACAO}' seguido do comando, ou 'sair' para encerrar.")
    ativo = True
    while ativo:
        frase = ouvir()

        if not frase:
            continue

        if frase.strip() in ("sair", "encerrar assistente", "tchau"):
            ativo = processar_comando(frase)
            continue

        if PALAVRA_ATIVACAO not in frase:
            continue

        comando = frase.split(PALAVRA_ATIVACAO, 1)[-1].strip(" ,.")

        if not comando:
            falar("Diga o comando.")
            comando = ouvir()

        if comando:
            ativo = processar_comando(comando)

    os._exit(0)  # encerra tudo, inclusive a janela


# ---------- Interface gráfica: avatar com anel de estado ----------
class AvatarAssistente:
    CORES = {
        "idle": (120, 120, 120),      # cinza
        "ouvindo": (46, 204, 113),    # verde
        "falando": (52, 152, 219),    # azul
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.tamanho = 220
        self.diametro_avatar = 170
        self.pulso = 0

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.95)
        largura_tela = root.winfo_screenwidth()
        root.geometry(f"{self.tamanho}x{self.tamanho}+{largura_tela - self.tamanho - 30}+30")
        root.config(bg="black")

        self.canvas = tk.Canvas(root, width=self.tamanho, height=self.tamanho,
                                 bg="black", highlightthickness=0)
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>", self._iniciar_arrasto)
        self.canvas.bind("<B1-Motion>", self._arrastar)
        self.canvas.bind("<Button-3>", lambda e: os._exit(0))

        self.imagem_avatar_tk = self._carregar_avatar()

        self._desenhar()
        self._loop_atualizacao()

    def _encontrar_arquivo_avatar(self):
        pasta_script = os.path.dirname(os.path.abspath(__file__))
        for nome in NOMES_AVATAR:
            caminho = os.path.join(pasta_script, nome)
            if os.path.isfile(caminho):
                return caminho
        return None

    def _carregar_avatar(self):
        """Carrega a imagem do avatar e a recorta em círculo."""
        if not PIL_DISPONIVEL:
            print("Aviso: biblioteca 'pillow' não instalada. Rode: py -3.13 -m pip install pillow")
            return None

        caminho = self._encontrar_arquivo_avatar()
        if not caminho:
            print(f"Aviso: nenhum arquivo de avatar encontrado ({', '.join(NOMES_AVATAR)}). Usando rosto padrão.")
            return None

        try:
            img = Image.open(caminho).convert("RGBA")
            lado = min(img.size)

            esquerda = (img.width - lado) // 2
            if img.height > img.width:
                topo = int((img.height - lado) * AVATAR_RECORTE_TOPO)
            else:
                topo = (img.height - lado) // 2

            img = img.crop((esquerda, topo, esquerda + lado, topo + lado))

            img = img.resize((self.diametro_avatar, self.diametro_avatar), Image.LANCZOS)
            mascara = Image.new("L", (self.diametro_avatar, self.diametro_avatar), 0)
            ImageDraw.Draw(mascara).ellipse(
                (0, 0, self.diametro_avatar, self.diametro_avatar), fill=255
            )
            img_circular = Image.new("RGBA", (self.diametro_avatar, self.diametro_avatar))
            img_circular.paste(img, (0, 0), mascara)
            return ImageTk.PhotoImage(img_circular)
        except Exception as erro:
            print(f"Erro ao carregar avatar: {erro}")
            return None

    def _iniciar_arrasto(self, event):
        self._x = event.x
        self._y = event.y

    def _arrastar(self, event):
        x = self.root.winfo_x() + (event.x - self._x)
        y = self.root.winfo_y() + (event.y - self._y)
        self.root.geometry(f"+{x}+{y}")

    def _cor_hex(self, rgb):
        return "#%02x%02x%02x" % rgb

    def _desenhar(self):
        self.canvas.delete("all")
        estado = get_estado()
        cor_rgb = self.CORES.get(estado, self.CORES["idle"])

        c = self.tamanho // 2
        raio_base = self.diametro_avatar // 2 + 8

        if estado in ("ouvindo", "falando"):
            variacao = 6 * abs((self.pulso % 20) - 10) / 10
        else:
            variacao = 0

        raio_anel = raio_base + variacao

        cor_clara = self._cor_hex(tuple(min(255, v + 40) for v in cor_rgb))
        self.canvas.create_oval(c - raio_anel - 4, c - raio_anel - 4,
                                 c + raio_anel + 4, c + raio_anel + 4,
                                 outline=cor_clara, width=2)
        self.canvas.create_oval(c - raio_anel, c - raio_anel,
                                 c + raio_anel, c + raio_anel,
                                 outline=self._cor_hex(cor_rgb), width=5)

        if self.imagem_avatar_tk is not None:
            self.canvas.create_image(c, c, image=self.imagem_avatar_tk)

            if estado == "falando":
                abertura = (3, 6, 10, 6)[(self.pulso // 2) % 4]
                boca_x = c + int((BOCA_X - 0.5) * self.diametro_avatar)
                boca_y = c + int((BOCA_Y - 0.5) * self.diametro_avatar)
                largura_boca = 14
                self.canvas.create_oval(
                    boca_x - largura_boca, boca_y - 2,
                    boca_x + largura_boca, boca_y + abertura,
                    fill="#3a1515", outline="#160606", width=1,
                )
        else:
            r = self.diametro_avatar // 2
            self.canvas.create_oval(c - r, c - r, c + r, c + r, fill="#1e1e1e", outline="")
            self.canvas.create_oval(c - 30 - 8, c - 10 - 8, c - 30 + 8, c - 10 + 8,
                                     fill=self._cor_hex(cor_rgb), outline="")
            self.canvas.create_oval(c + 30 - 8, c - 10 - 8, c + 30 + 8, c - 10 + 8,
                                     fill=self._cor_hex(cor_rgb), outline="")
            if estado == "falando":
                abertura = 4 + (self.pulso % 8)
                self.canvas.create_oval(c - 20, c + 20, c + 20, c + 20 + abertura,
                                        fill=self._cor_hex(cor_rgb), outline="")
            else:
                self.canvas.create_line(c - 20, c + 25, c + 20, c + 25,
                                        fill=self._cor_hex(cor_rgb), width=4)

    def _loop_atualizacao(self):
        self.pulso += 1
        self._desenhar()
        self.root.after(80, self._loop_atualizacao)


def main():
    root = tk.Tk()
    AvatarAssistente(root)

    thread = threading.Thread(target=loop_voz, daemon=True)
    thread.start()

    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
        sys.exit(0)