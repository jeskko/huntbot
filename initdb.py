#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('hunt.db')

cursor = conn.cursor()

with open('./seed.sql') as f:
    cursor.executescript(f.read())
