#!/bin/bash

echo "🚀 Instalando Mega MU Trader Bot para macOS M1..."
echo ""

# Verificar Python
echo "1️⃣ Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.9 ou superior."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION encontrado"
echo ""

# Verificar Homebrew
echo "2️⃣ Verificando Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew não encontrado. Instalando..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew já instalado"
fi
echo ""

# Instalar Tesseract OCR
echo "3️⃣ Instalando Tesseract OCR..."
if ! command -v tesseract &> /dev/null; then
    echo "Instalando Tesseract via Homebrew..."
    brew install tesseract
else
    echo "✅ Tesseract já instalado"
fi
echo ""

# Criar ambiente virtual
echo "4️⃣ Criando ambiente virtual Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Ambiente virtual criado"
else
    echo "✅ Ambiente virtual já existe"
fi
echo ""

# Ativar ambiente virtual e instalar dependências
echo "5️⃣ Instalando dependências Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependências instaladas"
echo ""

# Criar arquivo .env se não existir
echo "6️⃣ Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado"
    echo ""
    echo "⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais do banco de dados!"
    echo "   Você pode encontrar as credenciais no painel de Configurações do Manus."
else
    echo "✅ Arquivo .env já existe"
fi
echo ""

# Criar diretório de screenshots
mkdir -p screenshots
mkdir -p logs

echo "✅ Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "   1. Edite o arquivo .env com suas credenciais"
echo "   2. Execute: source venv/bin/activate"
echo "   3. Execute: python3 calibrate_macos.py"
echo ""
