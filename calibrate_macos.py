#!/usr/bin/env python3
"""
Script de calibração para macOS M1 com tela Retina
Ajuda a identificar coordenadas corretas da interface do Mega MU
"""

import pyautogui
import time
import json
import os
from PIL import Image, ImageDraw, ImageFont
import sys

# Configurar PyAutoGUI para macOS
pyautogui.FAILSAFE = True  # Mover mouse para canto superior esquerdo para abortar
pyautogui.PAUSE = 0.5

# Detectar escala Retina
RETINA_SCALE = 2  # Telas Retina do Mac têm escala 2x

class Calibrator:
    def __init__(self):
        self.config = {
            "retina_scale": RETINA_SCALE,
            "market_button_key": "p",
            "coordinates": {}
        }
        self.config_file = "config_macos.json"
        
    def show_mouse_position(self):
        """Mostra posição do mouse em tempo real"""
        print("\n" + "="*60)
        print("🖱️  RASTREADOR DE POSIÇÃO DO MOUSE")
        print("="*60)
        print("\nMova o mouse para a posição desejada e pressione CTRL+C")
        print("Posições serão ajustadas automaticamente para tela Retina\n")
        
        try:
            while True:
                x, y = pyautogui.position()
                # Ajustar para escala Retina
                retina_x = x * RETINA_SCALE
                retina_y = y * RETINA_SCALE
                
                position_str = f"Posição: X={x:4d} Y={y:4d} (Retina: X={retina_x:4d} Y={retina_y:4d})"
                print(position_str, end='\r')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n✅ Rastreamento finalizado")
            return x, y
    
    def capture_region(self, name, description):
        """Captura uma região da tela"""
        print(f"\n📍 {description}")
        print("   Mova o mouse para a posição e pressione ENTER...")
        input()
        
        x, y = pyautogui.position()
        print(f"   ✅ Posição capturada: X={x}, Y={y}")
        
        self.config["coordinates"][name] = {"x": x, "y": y}
        return x, y
    
    def test_screenshot(self):
        """Testa captura de screenshot"""
        print("\n" + "="*60)
        print("📸 TESTE DE SCREENSHOT")
        print("="*60)
        
        print("\nCapturando screenshot da tela inteira...")
        screenshot = pyautogui.screenshot()
        
        filename = f"screenshots/test_screenshot_{int(time.time())}.png"
        screenshot.save(filename)
        
        print(f"✅ Screenshot salvo: {filename}")
        print(f"   Tamanho: {screenshot.size}")
        
        return filename
    
    def calibrate_market_interface(self):
        """Calibra interface do mercado do Mega MU"""
        print("\n" + "="*60)
        print("🎯 CALIBRAÇÃO DA INTERFACE DO MERCADO")
        print("="*60)
        
        print("\n⚠️  IMPORTANTE:")
        print("   1. Abra o Mega MU")
        print("   2. Pressione 'P' para abrir o mercado")
        print("   3. Deixe a janela do mercado visível")
        print("\nPressione ENTER quando estiver pronto...")
        input()
        
        # Capturar posições importantes
        print("\n📋 Vamos capturar as seguintes posições:\n")
        
        # 1. Botão de próxima página
        self.capture_region(
            "next_page_button",
            "1. Botão de PRÓXIMA PÁGINA (seta →)"
        )
        
        # 2. Botão de página anterior
        self.capture_region(
            "prev_page_button",
            "2. Botão de PÁGINA ANTERIOR (seta ←)"
        )
        
        # 3. Primeira loja da lista
        self.capture_region(
            "first_shop",
            "3. PRIMEIRA LOJA da lista"
        )
        
        # 4. Região de itens na loja aberta
        print("\n   Agora clique em uma loja para abri-la...")
        input("   Pressione ENTER quando a loja estiver aberta...")
        
        self.capture_region(
            "first_item_slot",
            "4. PRIMEIRO SLOT DE ITEM na loja aberta"
        )
        
        # 5. Botão de fechar loja
        self.capture_region(
            "close_shop_button",
            "5. Botão de FECHAR LOJA (X)"
        )
        
        print("\n✅ Calibração concluída!")
        
    def save_config(self):
        """Salva configuração"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"\n💾 Configuração salva em: {self.config_file}")
    
    def load_config(self):
        """Carrega configuração existente"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Configuração carregada de: {self.config_file}")
            return True
        return False
    
    def show_menu(self):
        """Menu principal"""
        while True:
            print("\n" + "="*60)
            print("🎮 CALIBRADOR MEGA MU TRADER - macOS M1")
            print("="*60)
            print("\n1. 🖱️  Rastrear posição do mouse")
            print("2. 📸 Testar captura de screenshot")
            print("3. 🎯 Calibrar interface do mercado")
            print("4. 💾 Salvar configuração")
            print("5. 📋 Ver configuração atual")
            print("6. 🚪 Sair")
            
            choice = input("\nEscolha uma opção: ").strip()
            
            if choice == "1":
                self.show_mouse_position()
            elif choice == "2":
                self.test_screenshot()
            elif choice == "3":
                self.calibrate_market_interface()
            elif choice == "4":
                self.save_config()
            elif choice == "5":
                print("\n📋 Configuração atual:")
                print(json.dumps(self.config, indent=2))
            elif choice == "6":
                print("\n👋 Até logo!")
                break
            else:
                print("\n❌ Opção inválida")

def main():
    print("🚀 Iniciando calibrador para macOS M1...")
    
    # Criar diretórios necessários
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    calibrator = Calibrator()
    calibrator.load_config()
    calibrator.show_menu()

if __name__ == "__main__":
    main()
