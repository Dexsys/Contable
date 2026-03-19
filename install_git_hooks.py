#!/usr/bin/env python3
"""
Instalador de Git Hooks para actualización automática del historial.
Ejecutar una sola vez para configurar los hooks en el repositorio.
"""

import os
import sys
from pathlib import Path
import platform

def install_hooks():
    """Instala los Git Hooks necesarios"""
    
    # Identificar el directorio del repositorio
    repo_root = Path(__file__).parent
    git_hooks_dir = repo_root / '.git' / 'hooks'
    
    if not git_hooks_dir.exists():
        print("Error: No se encontró el directorio .git/hooks")
        print(f"Asegúrate de ejecutar este script desde la raíz del repositorio Git")
        return False
    
    # Crear el hook post-commit
    post_commit_hook = git_hooks_dir / 'post-commit'
    
    # Contenido del hook (shell script para Unix/Linux/Mac)
    if platform.system() == 'Windows':
        hook_content = f"""@echo off
REM Git Hook: post-commit (Windows)
REM Actualiza el historial automáticamente después de cada commit

{sys.executable} "{repo_root}/update_history_on_commit.py"
exit /b 0
"""
        post_commit_hook = git_hooks_dir / 'post-commit.bat'
    else:
        hook_content = f"""#!/bin/bash
# Git Hook: post-commit
# Actualiza el historial automáticamente después de cada commit

cd "$(dirname "$0")/../../"
python3 update_history_on_commit.py
exit 0
"""
    
    try:
        with open(post_commit_hook, 'w') as f:
            f.write(hook_content)
        
        # En Unix, hacer el archivo ejecutable
        if platform.system() != 'Windows':
            os.chmod(post_commit_hook, 0o755)
        
        print(f"✓ Git Hook instalado: {post_commit_hook}")
        print("\nCada vez que hagas un commit, el historial.md se actualizará automáticamente.")
        print("La entrada se agregará a la versión del día correspondiente.")
        return True
    
    except Exception as e:
        print(f"Error instalando hook: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("  Instalador de Git Hooks")
    print("  Sistema de actualización automática del historial")
    print("=" * 60)
    print()
    
    if install_hooks():
        print("\n" + "=" * 60)
        print("  ✅ Instalación completada exitosamente")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("  ❌ Error en la instalación")
        print("=" * 60)
        sys.exit(1)
