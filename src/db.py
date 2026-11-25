"""Conexion a la BD (lee variables de entorno; valores por defecto = docker-compose)."""
import os

import psycopg


def conectar(dbname=None, autocommit=False):
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5433")),
        dbname=dbname or os.environ.get("DB_NAME", "tarea2"),
        user=os.environ.get("DB_USER", "redes"),
        password=os.environ.get("DB_PASSWORD", "redes"),
        autocommit=autocommit,
    )
