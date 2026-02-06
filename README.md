# Mega MU Trader - Bot Híbrido

Sistema automatizado de coleta de dados do mercado do Mega MU com estratégia híbrida: coleta seletiva diária + coleta completa semanal.

## 📋 Requisitos do Sistema

### Software Necessário

- **Python 3.8+** instalado
- **Tesseract OCR** instalado
- **Mega MU** instalado e funcionando
- **Windows 10/11** (recomendado)

### Instalação do Tesseract OCR

**Windows:**
1. Baixe o instalador: https://github.com/UB-Mannheim/tesseract/wiki
2. Instale em `C:\Program Files\Tesseract-OCR\`
3. Adicione ao PATH do sistema

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

## 🚀 Instalação do Bot

### Passo 1: Instalar Dependências Python

```bash
cd bot
pip install -r requirements.txt
```

### Passo 2: Configurar Banco de Dados

Crie um arquivo `.env` na pasta `bot/`:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=mega_mu_trader
```

**Nota:** Use as mesmas credenciais do banco de dados do sistema web.

### Passo 3: Calibrar Coordenadas

Antes de usar o bot, você precisa calibrar as coordenadas da interface do jogo:

```bash
python hybrid_collector.py --mode calibrate
```

**Instruções de Calibração:**

1. Abra o Mega MU e vá para o mercado (pressione P)
2. Execute o comando de calibração acima
3. Siga as instruções na tela:
   - Posicione o mouse sobre o **botão de próxima página (→)**
   - Pressione **ESPAÇO**
   - Posicione o mouse sobre o **botão de página anterior (←)**
   - Pressione **ESPAÇO**
   - Posicione o mouse sobre o **botão de fechar loja (X)**
   - Pressione **ESPAÇO**

As coordenadas serão salvas em `calibration.json`.

## 🎯 Estratégia de Coleta

O bot oferece três formas de executar coletas:

### 1. Coletas Automáticas (4x/dia)

**Horários:** 5h, 10h, 17h, 23h

**Tipo:** COMPLETA (todas as lojas, todos os itens)

**Funcionamento:**
- Executa automaticamente nos horários programados
- Varre todo o mercado
- Duração: 30-60 minutos por coleta
- Gerenciado pelo `hybrid_scheduler.py`

### 2. Coletas Manuais (Sob Demanda)

**Coleta Seletiva:**
- Coleta apenas itens de interesse configurados
- Mais rápida (5-15 minutos)
- Execute via dashboard web ou comando: `python hybrid_collector.py --mode selective`

**Coleta Completa:**
- Varre todas as lojas e todos os itens
- Duração: 30-60 minutos
- Execute via dashboard web ou comando: `python hybrid_collector.py --mode complete`

### 3. Agendamentos Personalizados

**Funcionamento:**
- Agende coletas para horários específicos via dashboard web
- Escolha entre coleta seletiva ou completa
- Agendamentos são executados automaticamente pelo `scheduled_runner.py`
- Exemplo: "Agendar coleta completa para amanhã às 9h"

## 🤖 Como Funciona o Bot

### Processo de Coleta

1. **Abre o mercado** (pressiona tecla P)
2. **Navega entre as lojas** da lista
3. **Para cada loja:**
   - Clica na loja
   - Detecta o grid de itens
   - Move o mouse sobre cada slot do inventário
   - Aguarda o tooltip aparecer (1.5s)
   - Captura screenshot do tooltip
   - Extrai dados com OCR (Tesseract)
   - Salva no banco de dados
4. **Fecha a loja** e vai para a próxima
5. **Navega para próxima página** quando termina a página atual

### Detecção de Tooltips

O bot usa **Computer Vision** (OpenCV) para detectar automaticamente quando um tooltip aparece na tela:

- Detecta a cor azul escura característica dos tooltips do Mega MU
- Identifica o contorno do tooltip
- Captura apenas a área relevante
- Aplica pré-processamento para melhorar a precisão do OCR

### Extração de Dados (OCR)

O Tesseract OCR extrai:
- **Nome do item**
- **Preço** (Zen/MC/MP)
- **Quantidade**
- **Atributos** (defesa, durabilidade, requisitos, etc.)

## 🔧 Uso Manual

### Executar Coleta Seletiva (Manual)

```bash
python hybrid_collector.py --mode selective
```

### Executar Coleta Completa (Manual)

```bash
python hybrid_collector.py --mode complete
```

## ⏰ Execução Automática

### Coletas Automáticas (4x/dia)

```bash
python hybrid_scheduler.py
```

**O que faz:**
- Executa coletas COMPLETAS 4x/dia (5h, 10h, 17h, 23h)
- Gera logs em `hybrid_scheduler.log`

### Agendamentos Personalizados

```bash
python scheduled_runner.py
```

**O que faz:**
- Monitora o banco de dados por agendamentos pendentes
- Executa coletas agendadas via dashboard web
- Atualiza status dos agendamentos
- Gera logs em `scheduled_runner.log`

**Recomendação:** Execute ambos os scripts simultaneamente para ter coletas automáticas + agendamentos personalizados

### Executar como Serviço (Windows)

**Opção 1: Task Scheduler**

1. Abra o **Agendador de Tarefas** do Windows
2. Criar Tarefa Básica
3. Nome: "Mega MU Bot Scheduler"
4. Disparador: "Quando o computador iniciar"
5. Ação: "Iniciar um programa"
6. Programa: `python`
7. Argumentos: `C:\caminho\para\bot\hybrid_scheduler.py`
8. Marcar: "Executar com privilégios mais altos"

**Opção 2: NSSM (Recomendado)**

```bash
# Instalar NSSM
choco install nssm

# Criar serviço
nssm install MegaMUBot python C:\caminho\para\bot\hybrid_scheduler.py
nssm start MegaMUBot
```

## 📊 Monitoramento

### Logs

Todos os logs são salvos em:
- `hybrid_collector.log` - Logs de coleta
- `hybrid_scheduler.log` - Logs do agendador

### Dashboard Web

Acesse `http://localhost:3000/dashboard` para ver:
- Histórico de coletas
- Itens coletados
- Oportunidades de arbitragem
- Alertas configurados

## 🐛 Troubleshooting

### Problema: OCR não está lendo corretamente

**Solução:**
1. Verifique se o Tesseract está instalado corretamente
2. Ajuste o threshold de confiança em `CONFIG['OCR_CONFIDENCE']`
3. Verifique os screenshots salvos em `screenshots/` para debug

### Problema: Bot não encontra os botões

**Solução:**
1. Execute novamente a calibração: `python hybrid_collector.py --mode calibrate`
2. Certifique-se de que o jogo está em tela cheia ou janela maximizada
3. Verifique se a resolução do jogo não mudou

### Problema: Tooltips não são detectados

**Solução:**
1. Ajuste o delay em `CONFIG['TOOLTIP_DELAY']` (aumentar para 2.0s)
2. Verifique se a cor do tooltip no seu jogo é azul escura
3. Ajuste os valores de `lower_blue` e `upper_blue` em `TooltipDetector.detect_tooltip()`

### Problema: Bot está muito lento

**Solução:**
1. Use coleta seletiva em vez de completa
2. Reduza o número de itens de interesse
3. Ajuste os delays em `CONFIG`

## ⚠️ Avisos Importantes

1. **Mantenha o jogo visível**: O bot precisa que a janela do Mega MU esteja visível (não minimizada)

2. **Não mexa no mouse durante a coleta**: O bot controla o mouse automaticamente

3. **Resolução da tela**: Se mudar a resolução do jogo, recalibre as coordenadas

4. **Conta logada**: Deixe sua conta logada no jogo antes de iniciar o bot

5. **Backup**: O bot salva screenshots em `screenshots/` - limpe periodicamente para economizar espaço

## 📈 Próximos Passos

Após configurar o bot:

1. **Configure itens de interesse** no dashboard web
2. **Execute uma coleta manual** para testar
3. **Verifique os logs** para garantir que está funcionando
4. **Ative o agendador** para coletas automáticas
5. **Configure alertas** para oportunidades de arbitragem

## 🆘 Suporte

Se encontrar problemas:
1. Verifique os logs em `hybrid_collector.log`
2. Teste a calibração novamente
3. Verifique se todas as dependências estão instaladas
4. Consulte a documentação do projeto principal

---

**Desenvolvido para Mega MU Trader**
Sistema de Arbitragem e Monitoramento de Preços
