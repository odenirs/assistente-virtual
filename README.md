# Assistente Virtual por Voz

Assistente de voz para Windows feito em Python. Ele escuta comandos em português, responde falando e mostra um avatar flutuante na tela que muda de cor conforme o estado (parado, ouvindo ou falando).

## Recursos

- Reconhecimento de voz em português (pt-BR)
- Resposta falada com a voz do Windows (Maria, se estiver instalada)
- Palavra de ativação: diga **"assistente"** antes do comando
- Avatar circular com anel colorido e boca animada enquanto fala
- Janela flutuante: arraste com o botão esquerdo, feche com o botão direito
- Desligar o PC por voz, com confirmação e opção de cancelar

## Requisitos

- Windows
- **Python 3.13 ou anterior**. O PyAudio ainda não tem instalador pronto para o Python 3.14
- Microfone
- Conexão com a internet (o reconhecimento de voz usa o serviço do Google)

## Instalação

```
py -3.13 -m pip install -r requirements.txt
```

Se o `pyaudio` der erro na instalação, tente:

```
py -3.13 -m pip install pipwin
py -3.13 -m pipwin install pyaudio
```

## Como usar

```
py -3.13 assistente_voz.py
```

Diga **"assistente"** seguido do comando. Exemplo: *"assistente, que horas são"*.

## Comandos de voz

| Comando | O que faz |
|---|---|
| que horas são | Diz a hora atual |
| data de hoje / que dia é hoje | Diz a data |
| abrir youtube | Abre o YouTube no navegador |
| abrir google | Abre o Google no navegador |
| abrir spotify / tocar música | Abre o Spotify |
| pesquisar + termo | Pesquisa o termo no Google |
| qual é seu nome | O assistente se apresenta |
| desligar o computador | Pede confirmação ("sim"), avisa e desliga em 15 segundos |
| cancelar desligamento | Cancela o desligamento durante a contagem |
| sair / encerrar assistente / tchau | Encerra o assistente |

## Avatar personalizado

Coloque uma imagem chamada `avatar.png`, `avatar.jpg` ou `avatar.jpeg` na mesma pasta do script. Ela é recortada em círculo. Sem imagem, o assistente usa um rosto simples desenhado.

Ajustes no início do `assistente_voz.py`:

- `AVATAR_RECORTE_TOPO`: sobe ou desce o enquadramento em fotos de retrato
- `BOCA_X` e `BOCA_Y`: posição da boca animada sobre a imagem

## Iniciar com o Windows (opcional)

O arquivo `iniciar_assistente.bat` abre o assistente. Para iniciar junto com o Windows, crie um atalho dele na pasta que abre com `Win + R` e o comando `shell:startup`. O `.bat` espera o projeto na pasta `Desktop\assistentevoz`; se você usar outro lugar, edite o caminho dentro dele.

## Estrutura

```
assistente_voz.py          # código principal
iniciar_assistente.bat     # atalho para iniciar no Windows
requirements.txt           # dependências
avatar.png                 # sua imagem (não vai para o GitHub)
```