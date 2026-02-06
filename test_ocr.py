#!/usr/bin/env python3
"""
Script de teste de OCR para verificar detecção de texto em screenshots do Mega MU
"""

import sys
import pytesseract
from PIL import Image
import cv2
import numpy as np

def test_ocr(image_path):
    """Testa OCR em uma imagem"""
    print(f"\n📸 Testando OCR em: {image_path}")
    print("="*60)
    
    try:
        # Carregar imagem
        img = Image.open(image_path)
        print(f"✅ Imagem carregada: {img.size}")
        
        # Converter para OpenCV
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Converter para escala de cinza
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Aplicar threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # OCR básico
        print("\n🔍 Executando OCR...")
        text = pytesseract.image_to_string(thresh, lang='eng')
        
        print("\n📝 Texto detectado:")
        print("-"*60)
        print(text)
        print("-"*60)
        
        # OCR com dados detalhados
        data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
        
        # Filtrar palavras com alta confiança
        print("\n🎯 Palavras detectadas (confiança > 60%):")
        print("-"*60)
        
        detected_words = []
        for i, word in enumerate(data['text']):
            conf = int(data['conf'][i])
            if conf > 60 and word.strip():
                detected_words.append((word, conf))
                print(f"   {word:30s} (confiança: {conf}%)")
        
        print("-"*60)
        print(f"\n✅ Total de palavras detectadas: {len(detected_words)}")
        
        # Tentar detectar padrões de preços
        print("\n💰 Tentando detectar preços...")
        prices = []
        for word, conf in detected_words:
            # Remover caracteres não numéricos
            clean_word = ''.join(c for c in word if c.isdigit() or c == '.')
            if clean_word and len(clean_word) >= 2:
                try:
                    price = float(clean_word)
                    if price > 0:
                        prices.append((price, conf))
                        print(f"   Preço detectado: {price} MCoin (confiança: {conf}%)")
                except ValueError:
                    pass
        
        if prices:
            print(f"\n✅ Total de preços detectados: {len(prices)}")
        else:
            print("\n⚠️  Nenhum preço detectado")
        
        # Salvar imagem processada
        processed_path = image_path.replace('.png', '_processed.png')
        cv2.imwrite(processed_path, thresh)
        print(f"\n💾 Imagem processada salva: {processed_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao processar imagem: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_ocr.py <caminho_da_imagem>")
        print("\nExemplo:")
        print("  python3 test_ocr.py screenshots/test_market.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("\n🚀 Teste de OCR - Mega MU Trader")
    print("="*60)
    
    success = test_ocr(image_path)
    
    if success:
        print("\n✅ Teste concluído com sucesso!")
        print("\n💡 Dicas:")
        print("   - Se o texto não foi detectado corretamente, tente:")
        print("     1. Capturar screenshot com melhor qualidade")
        print("     2. Aumentar tamanho da fonte no jogo")
        print("     3. Ajustar threshold de processamento")
    else:
        print("\n❌ Teste falhou. Verifique o arquivo de imagem.")

if __name__ == "__main__":
    main()
