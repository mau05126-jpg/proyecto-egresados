#!/usr/bin/env python3
"""
Script para inicializar la base de datos en Vercel
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

with app.app_context():
    print("🔧 Inicializando base de datos en Vercel...")
    db.create_all()
    print("✅ Base de datos lista")