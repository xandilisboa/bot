# 🎮 Guia de Teste Completo - Mega MU Trader Bot (macOS M1)

## 📋 Pré-requisitos

- ✅ macOS (M1/M2/M3)
- ✅ Python 3.9+ instalado
- ✅ Mega MU instalado e funcionando
- ✅ Acesso ao banco de dados (credenciais do Manus)

---

## 🚀 Passo 1: Instalação

### 1.1 Baixar arquivos do bot

Baixe a pasta `bot/` do projeto Mega MU Trader para seu Mac.

### 1.2 Abrir Terminal

1. Abra o **Terminal** (Applications → Utilities → Terminal)
2. Navegue até a pasta do bot:
   ```bash
   cd /caminho/para/mega_mu_trader/bot
   ```

### 1.3 Executar instalação

```bash
chmod +x install_macos.sh
./install_macos.sh
```

Este script irá:
- ✅ Verificar Python
- ✅ Instalar Homebrew (se necessário)
- ✅ Instalar Tesseract OCR
- ✅ Criar ambiente virtual Python
- ✅ Instalar todas as dependências
- ✅ Criar arquivo `.env`

### 1.4 Configurar banco de dados

Edite o arquivo `.env`:

```bash
nano .env
```

Cole as credenciais do banco de dados (disponíveis no painel Manus):

```env
DATABASE_URL=mysql://usuario:senha@host:porta/database
```

Salve com `CTRL+O`, `ENTER`, `CTRL+X`

---

## 🎯 Passo 2: Calibração

### 2.1 Preparar o jogo

1. Abra o **Mega MU**
2. Faça login no jogo
3. Pressione **P** para abrir o mercado
4. Deixe a janela do mercado **visível e em primeiro plano**

### 2.2 Ativar ambiente virtual

```bash
source venv/bin/activate
```

### 2.3 Executar calibrador

```bash
python3 calibrate_macos.py
```

### 2.4 Seguir menu de calibração

**Opção 1: Rastrear posição do mouse**
- Escolha opção `1`
- Mova o mouse sobre elementos do jogo
- Anote as coordenadas

**Opção 2: Testar screenshot**
- Escolha opção `2`
- Verifica se capturas de tela funcionam
- Screenshot salvo em `screenshots/`

**Opção 3: Calibrar interface** (PRINCIPAL)
- Escolha opção `3`
- Siga as instruções na tela:
  1. Posicione mouse no botão **→** (próxima página)
  2. Posicione mouse no botão **←** (página anterior)
  3. Posicione mouse na **primeira loja** da lista
  4. Abra uma loja
  5. Posicione mouse no **primeiro slot de item**
  6. Posicione mouse no botão **X** (fechar loja)

**Opção 4: Salvar configuração**
- Escolha opção `4`
- Salva em `config_macos.json`

---

## 🧪 Passo 3: Teste do OCR

### 3.1 Capturar screenshot do mercado

Com o mercado aberto:

```bash
python3 -c "import pyautogui; pyautogui.screenshot('screenshots/test_market.png')"
```

### 3.2 Testar OCR na imagem

```bash
python3 test_ocr.py screenshots/test_market.png
```

Você verá:
- ✅ Texto extraído da imagem
- ✅ Itens detectados
- ✅ Preços identificados

---

## 🤖 Passo 4: Teste de Coleta Manual

### 4.1 Executar coleta seletiva (teste)

```bash
python3 hybrid_collector.py --mode selective --manual
```

O bot irá:
1. Pressionar **P** para abrir mercado
2. Navegar pelas páginas
3. Clicar em lojas
4. Mover mouse sobre itens
5. Capturar tooltips
6. Extrair dados com OCR
7. Salvar no banco de dados

### 4.2 Verificar logs

```bash
tail -f logs/collector.log
```

### 4.3 Verificar dados no banco

Acesse o web app → Página "Mercado" → Verifique se itens apareceram

---

## ⚙️ Passo 5: Teste de Coleta Automática

### 5.1 Executar scheduler

```bash
python3 hybrid_scheduler.py
```

O scheduler irá:
- ✅ Executar coletas nos horários configurados (5h, 10h, 17h, 23h)
- ✅ Salvar logs em `logs/scheduler.log`

### 5.2 Monitorar execução

```bash
tail -f logs/scheduler.log
```

---

## 🐛 Solução de Problemas

### Problema: "Permission denied" ao executar script

**Solução:**
```bash
chmod +x install_macos.sh
chmod +x calibrate_macos.py
```

### Problema: OCR não detecta texto

**Soluções:**
1. Verificar se Tesseract está instalado:
   ```bash
   tesseract --version
   ```
2. Aumentar qualidade do screenshot
3. Ajustar threshold de confiança no código

### Problema: Bot clica em posições erradas

**Soluções:**
1. Recalibrar coordenadas
2. Verificar escala Retina (deve ser 2x)
3. Garantir que janela do jogo está em tela cheia

### Problema: Banco de dados não conecta

**Soluções:**
1. Verificar credenciais no `.env`
2. Testar conexão:
   ```bash
   python3 -c "from server.db import getDb; import asyncio; asyncio.run(getDb())"
   ```

---

## ✅ Checklist Final

Antes de deixar rodando em produção:

- [ ] Instalação completa sem erros
- [ ] Calibração salva em `config_macos.json`
- [ ] OCR detectando texto corretamente
- [ ] Coleta manual funcionando
- [ ] Dados aparecendo no web app
- [ ] Scheduler rodando sem erros
- [ ] Alertas por email configurados (opcional)

---

## 📞 Suporte

Se encontrar problemas:
1. Verifique logs em `logs/`
2. Revise configuração em `config_macos.json`
3. Teste cada componente individualmente
4. Reporte problemas com screenshots e logs

---

## 🎉 Próximos Passos

Após testes bem-sucedidos:

1. **Configurar como serviço** (rodar em background)
2. **Adicionar itens de interesse** no web app
3. **Configurar alertas** de preço
4. **Monitorar oportunidades** de arbitragem
5. **Lucrar!** 💰
