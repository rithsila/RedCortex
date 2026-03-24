#!/usr/bin/env python3
"""Initialize SQLite database"""
import os
import sqlite3

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

conn = sqlite3.connect('data/library.db')
cursor = conn.cursor()

# books table
cursor.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT CHECK(category IN ('security', 'red_hat', 'ai_engineering', 'other')),
    file_path TEXT UNIQUE,
    total_pages INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# chunks table
cursor.execute('''
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    parent_id INTEGER,
    qdrant_id TEXT,
    content TEXT,
    summary TEXT,
    page_start INTEGER,
    page_end INTEGER,
    token_count INTEGER,
    is_hot BOOLEAN DEFAULT 0,
    embedding_blob BLOB
);
''')

# queries table
cursor.execute('''
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY,
    question TEXT,
    model_used TEXT,
    cost_usd REAL,
    latency_ms INTEGER,
    rating INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

conn.commit()
conn.close()
print("✅ data/library.db initialized successfully!")
