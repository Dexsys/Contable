#!/bin/bash

# Script interactivo para instalar certificados de origen de Cloudflare

echo "=============================================="
echo "Instalador de Certificado de Origen Cloudflare"
echo "=============================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Este script debe ejecutarse con sudo${NC}"
    exit 1
fi

echo "Este script te ayudará a instalar el certificado de origen de Cloudflare."
echo ""
echo -e "${YELLOW}ANTES DE CONTINUAR, debes:${NC}"
echo "1. Ir a: https://dash.cloudflare.com"
echo "2. Seleccionar dominio: dexsys.cl"
echo "3. Ir a: SSL/TLS → Origin Server"
echo "4. Click en 'Create Certificate'"
echo "5. Dejar opciones por defecto (15 años)"
echo "6. Click 'Create'"
echo ""
echo "Cloudflare te mostrará 2 cuadros de texto:"
echo "  - Origin Certificate (el certificado)"
echo "  - Private Key (la llave privada)"
echo ""
read -p "¿Ya tienes ambos textos copiados? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Por favor, ve a Cloudflare y genera el certificado primero."
    echo "Luego ejecuta este script nuevamente."
    exit 0
fi

echo ""
echo -e "${YELLOW}Paso 1: Instalar certificado${NC}"
echo "Por favor, pega el CERTIFICADO (Origin Certificate) completo."
echo "Debe empezar con: -----BEGIN CERTIFICATE-----"
echo "y terminar con: -----END CERTIFICATE-----"
echo ""
echo "Pega el certificado y presiona Ctrl+D cuando termines:"
echo ""

# Leer certificado
CERT_FILE="/etc/nginx/ssl/cloudflare_origin.crt"
cat > "$CERT_FILE"

if [ ! -s "$CERT_FILE" ]; then
    echo -e "${RED}Error: El certificado está vacío${NC}"
    exit 1
fi

# Verificar que es un certificado válido
if grep -q "BEGIN CERTIFICATE" "$CERT_FILE"; then
    echo -e "${GREEN}✓ Certificado guardado correctamente${NC}"
    chmod 644 "$CERT_FILE"
else
    echo -e "${RED}Error: No parece ser un certificado válido${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Paso 2: Instalar llave privada${NC}"
echo "Ahora pega la LLAVE PRIVADA (Private Key)."
echo "Debe empezar con: -----BEGIN PRIVATE KEY-----"
echo "y terminar con: -----END PRIVATE KEY-----"
echo ""
echo "Pega la llave privada y presiona Ctrl+D cuando termines:"
echo ""

# Leer llave privada
KEY_FILE="/etc/nginx/ssl/cloudflare_origin.key"
cat > "$KEY_FILE"

if [ ! -s "$KEY_FILE" ]; then
    echo -e "${RED}Error: La llave privada está vacía${NC}"
    exit 1
fi

# Verificar que es una llave privada válida
if grep -q "BEGIN PRIVATE KEY" "$KEY_FILE" || grep -q "BEGIN RSA PRIVATE KEY" "$KEY_FILE"; then
    echo -e "${GREEN}✓ Llave privada guardada correctamente${NC}"
    chmod 600 "$KEY_FILE"
else
    echo -e "${RED}Error: No parece ser una llave privada válida${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=============================================="
echo "¡Certificados instalados exitosamente!"
echo "==============================================${NC}"
echo ""
echo "Archivos creados:"
echo "  - $CERT_FILE"
echo "  - $KEY_FILE"
echo ""
echo "Siguiente paso:"
echo "  Ejecuta: sudo bash /home/ubuntu/Developer/Flask/Recetas/switch_to_domain.sh"
echo ""
